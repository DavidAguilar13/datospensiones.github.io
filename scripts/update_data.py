"""Descarga el último Excel mensual de pensiones del INSS, lo convierte al JSON
de la web (data/pensiones.json) y lo valida antes de escribirlo.

Uso:
    python scripts/update_data.py                 # descarga el último mes publicado
    python scripts/update_data.py --file CA202610.xlsx   # usa un Excel ya descargado
    python scripts/update_data.py --dry-run       # valida pero no escribe nada

Códigos de salida:
    0  datos actualizados, o ya estaban al día
    1  la validación ha fallado: no se escribe nada
    2  no se ha podido descargar o leer el Excel
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

try:
    # Usa los certificados del sistema operativo si está instalado `truststore`.
    # Hace falta en Windows con antivirus que inspeccionan HTTPS (p. ej. Avast).
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "pensiones.json"

SOURCE_PAGE = (
    "https://www.seg-social.es/wps/portal/wss/internet/"
    "EstadisticasPresupuestosEstudios/Estadisticas/EST23/EST24"
)
BASE_URL = "https://www.seg-social.es"
SHEET = "CA_Total sistema"
USER_AGENT = "Mozilla/5.0 (datospensiones; actualizador de datos)"

# Bloques de columnas del Excel → clave en el JSON
TYPES = {
    "total pensiones": "total",
    "incapacidad permanente": "ip",
    "jubilacion": "jub",
    "viudedad": "viu",
    "orfandad": "orf",
    "favor de familiares": "fam",
}

# Rangos razonables de pensión media (€/mes). Fuera de esto, algo va mal.
MEDIA_RANGES = {
    "total": (600, 2500),
    "jub": (700, 2800),
    "ip": (500, 2500),
    "viu": (400, 1800),
    "orf": (200, 1200),
    "fam": (300, 1800),
}
NATIONAL_TOTAL_RANGE = (8_000_000, 14_000_000)
# Variación máxima admitida respecto al mes anterior (num y media, por provincia)
MAX_MONTHLY_CHANGE = 0.15

# Código INE → nombre que usa la web
PROVINCES = {
    "01": "Álava", "02": "Albacete", "03": "Alicante", "04": "Almería", "05": "Ávila",
    "06": "Badajoz", "07": "Illes Balears", "08": "Barcelona", "09": "Burgos", "10": "Cáceres",
    "11": "Cádiz", "12": "Castellón", "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña",
    "16": "Cuenca", "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Gipuzkoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León", "25": "Lleida",
    "26": "La Rioja", "27": "Lugo", "28": "Madrid", "29": "Málaga", "30": "Murcia",
    "31": "Navarra", "32": "Ourense", "33": "Asturias", "34": "Palencia", "35": "Las Palmas",
    "36": "Pontevedra", "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
    "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona", "44": "Teruel",
    "45": "Toledo", "46": "Valencia", "47": "Valladolid", "48": "Bizkaia", "49": "Zamora",
    "50": "Zaragoza", "51": "Ceuta", "52": "Melilla",
}

# Variantes de nombre que aparecen en los Excel del INSS → código INE.
# Se comparan normalizadas (sin tildes, minúsculas, solo letras).
ALIASES = {
    "araba/alava": "01", "alava": "01", "araba": "01",
    "alicante/alacant": "03", "alacant": "03",
    "balears (illes)": "07", "illes balears": "07", "baleares": "07", "islas baleares": "07",
    "castellon/castello": "12", "castello": "12",
    "coruna (a)": "15", "a coruna": "15", "la coruna": "15",
    "gipuzkoa/guipuzcoa": "20", "guipuzcoa": "20",
    "rioja (la)": "26",
    "madrid (com. de)": "28", "madrid (comunidad de)": "28", "comunidad de madrid": "28",
    "murcia (region de)": "30", "region de murcia": "30",
    "navarra (com. foral de)": "31", "navarra (comunidad foral de)": "31",
    "comunidad foral de navarra": "31",
    "asturias (principado de)": "33", "principado de asturias": "33",
    "palmas (las)": "35",
    "s.c.tenerife": "38", "s.c. tenerife": "38", "sc tenerife": "38",
    "santa cruz de tenerife": "38", "tenerife": "38",
    "valencia/valencia": "46",
    "bizkaia/vizcaya": "48", "vizcaya": "48",
}

# Filas de comunidades autónomas con más de una provincia: se ignoran.
CCAA = {
    "andalucia", "aragon", "canarias", "castilla - la mancha", "castilla-la mancha",
    "castilla la mancha", "castilla y leon", "cataluna", "comunitat valenciana",
    "comunidad valenciana", "extremadura", "galicia", "pais vasco",
}

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}


class ValidationError(Exception):
    pass


def norm(text: str) -> str:
    """'Coruña (A)' → 'coruna (a)'; sin tildes, minúsculas, espacios simples."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


NAME_TO_CODE = {norm(n): c for c, n in PROVINCES.items()}
NAME_TO_CODE.update({norm(a): c for a, c in ALIASES.items()})


# ─── Descarga ──────────────────────────────────────────────────────────────────

def find_latest_url() -> tuple[str, str]:
    """Devuelve (periodo 'AAAAMM', url) del último CAaaaamm.xlsx de la página del INSS."""
    import requests

    html = requests.get(SOURCE_PAGE, headers={"User-Agent": USER_AGENT}, timeout=60).text
    links = re.findall(r'href="([^"]*?/CA(\d{6})\.xlsx[^"]*)"', html)
    if not links:
        raise RuntimeError("No se ha encontrado ningún enlace CAaaaamm.xlsx en la página del INSS")
    href, period = max(links, key=lambda x: x[1])
    href = href.replace("&amp;", "&")
    return period, urljoin(BASE_URL, href)


def download(url: str, dest: Path) -> None:
    import requests

    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    if not r.content.startswith(b"PK"):  # un .xlsx es un zip
        raise RuntimeError(f"La descarga no parece un Excel ({len(r.content)} bytes)")
    dest.write_bytes(r.content)


# ─── Lectura del Excel ─────────────────────────────────────────────────────────

def parse_excel(path: Path) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if SHEET not in wb.sheetnames:
        raise ValidationError(f"No existe la hoja «{SHEET}». Hojas: {wb.sheetnames}")
    rows = [list(r) for r in wb[SHEET].iter_rows(values_only=True)]

    fecha = parse_date(rows)
    columns, data_start = find_columns(rows)

    national = None
    provinces: dict[str, dict] = {}
    unknown = []
    for row in rows[data_start:]:
        label = row[0]
        if label is None or str(label).strip() == "":
            continue
        key = norm(label)
        if key == "total sistema":
            national = read_block(row, columns, label)
        elif key in NAME_TO_CODE:
            code = NAME_TO_CODE[key]
            if code in provinces:
                raise ValidationError(f"Provincia repetida: {label} ({code})")
            provinces[code] = read_block(row, columns, label)
        elif key in CCAA:
            continue
        elif key.startswith(("fuente", "nota", "(")):
            continue
        else:
            unknown.append(str(label))

    if unknown:
        raise ValidationError(f"Filas con nombres desconocidos: {unknown}")
    if national is None:
        raise ValidationError("No se ha encontrado la fila «Total sistema»")

    return {"fecha": fecha, "nacional": national, "provincias": provinces}


def parse_date(rows) -> date:
    for row in rows[:5]:
        for cell in row:
            if not cell:
                continue
            m = re.search(r"a\s+(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})", norm(cell))
            if m and m.group(2) in MONTHS:
                return date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    raise ValidationError("No se ha encontrado la fecha («A 1 DE … DE …») en la cabecera")


def find_columns(rows) -> tuple[dict, int]:
    """Busca la fila de tipos de pensión y la de 'Número / P. media' bajo ella.
    Devuelve ({tipo: (col_num, col_importe, col_media)}, fila donde empiezan los datos)."""
    for i, row in enumerate(rows[:15]):
        groups = {TYPES[norm(c)]: j for j, c in enumerate(row) if c and norm(c) in TYPES}
        if len(groups) < len(TYPES):
            continue
        sub = [norm(c) if c else "" for c in rows[i + 1]]
        columns = {}
        for t, j in groups.items():
            num_col = next((k for k in range(j, j + 3) if sub[k].startswith("numero")), None)
            imp_col = next((k for k in range(j, j + 3) if sub[k].startswith("importe")), None)
            med_col = next((k for k in range(j, j + 3) if sub[k].startswith("p. media")), None)
            if None in (num_col, imp_col, med_col):
                raise ValidationError(f"Columnas inesperadas bajo «{t}»: {rows[i + 1][j:j + 3]}")
            columns[t] = (num_col, imp_col, med_col)
        return columns, i + 2
    raise ValidationError(
        "No se han encontrado las columnas esperadas: " + ", ".join(TYPES)
    )


def read_block(row, columns, label) -> dict:
    out = {}
    for t, (cn, ci, cm) in columns.items():
        num, imp, media = row[cn], row[ci], row[cm]
        if num in (None, "", "-"):
            num, imp, media = 0, 0, None
        if not isinstance(num, (int, float)) or (media is not None and not isinstance(media, (int, float))):
            raise ValidationError(f"Valor no numérico en {label} / {t}: {num!r}, {media!r}")
        out[t] = {
            "num": int(round(num)),
            "media": round(float(media), 2) if media is not None else None,
            "_importe": float(imp or 0),
        }
    return out


# ─── Validación ────────────────────────────────────────────────────────────────

def validate(parsed: dict, previous: dict | None) -> list[str]:
    """Lanza ValidationError si algo es inaceptable. Devuelve avisos no bloqueantes."""
    errors, warnings = [], []
    provs, nat = parsed["provincias"], parsed["nacional"]

    missing = sorted(set(PROVINCES) - set(provs))
    if missing:
        errors.append("Faltan provincias: " + ", ".join(f"{c} {PROVINCES[c]}" for c in missing))
    if len(provs) != 52:
        errors.append(f"Hay {len(provs)} provincias, se esperaban 52")

    lo, hi = NATIONAL_TOTAL_RANGE
    if not lo <= nat["total"]["num"] <= hi:
        errors.append(f"Total nacional de pensiones fuera de rango: {nat['total']['num']}")

    for code, p in [("ES", nat)] + sorted(provs.items()):
        name = "Nacional" if code == "ES" else PROVINCES[code]
        if p["total"]["num"] <= 0:
            errors.append(f"{name}: sin pensiones")
        for t, (mlo, mhi) in MEDIA_RANGES.items():
            num, media = p[t]["num"], p[t]["media"]
            if num == 0:
                continue
            if media is None or not mlo <= media <= mhi:
                errors.append(f"{name} / {t}: pensión media fuera de rango ({media})")
                continue
            calc = p[t]["_importe"] / num
            if abs(calc - media) > 1:
                errors.append(f"{name} / {t}: la media ({media}) no cuadra con importe/número ({calc:.2f})")
        parts = sum(p[t]["num"] for t in TYPES.values() if t != "total")
        if parts != p["total"]["num"]:
            errors.append(f"{name}: la suma por tipos ({parts}) no da el total ({p['total']['num']})")

    if not missing:
        for t in TYPES.values():
            s = sum(p[t]["num"] for p in provs.values())
            if s != nat[t]["num"]:
                errors.append(f"{t}: la suma de provincias ({s}) no da el total nacional ({nat[t]['num']})")

    if previous and previous.get("provincias") and not errors:
        for code, p in provs.items():
            old = previous["provincias"].get(code)
            if not old:
                continue
            for field in ("num", "media"):
                a, b = old["total"][field], p["total"][field]
                if a and abs(b - a) / a > MAX_MONTHLY_CHANGE:
                    errors.append(
                        f"{PROVINCES[code]}: el total ({field}) cambia un {100 * (b - a) / a:+.1f}% "
                        f"respecto a {previous['periodo']} ({a} → {b})"
                    )

    if errors:
        raise ValidationError("\n  - " + "\n  - ".join(errors))
    return warnings


# ─── Salida ────────────────────────────────────────────────────────────────────

def clean(block: dict) -> dict:
    return {t: {"num": v["num"], "media": v["media"]} for t, v in block.items()}


def build_json(parsed: dict, filename: str) -> dict:
    f = parsed["fecha"]
    order = ["total", "jub", "ip", "viu", "orf", "fam"]
    reorder = lambda b: {t: b[t] for t in order}
    return {
        "periodo": f"{f.year}-{f.month:02d}",
        "fecha_datos": f.isoformat(),
        "fuente": {
            "nombre": "Instituto Nacional de la Seguridad Social (INSS)",
            "url": "https://www.seg-social.es",
            "fichero": filename,
            "hoja": SHEET,
        },
        "nacional": reorder(clean(parsed["nacional"])),
        "provincias": {
            c: {"nombre": PROVINCES[c], **reorder(clean(parsed["provincias"][c]))}
            for c in sorted(parsed["provincias"])
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path, help="Excel CAaaaamm.xlsx ya descargado")
    ap.add_argument("--out", type=Path, default=OUT_PATH, help="JSON de salida")
    ap.add_argument("--dry-run", action="store_true", help="valida sin escribir")
    ap.add_argument("--force", action="store_true", help="escribe aunque el periodo no sea más reciente")
    args = ap.parse_args()

    previous = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else None

    try:
        if args.file:
            xlsx, filename = args.file, args.file.name
        else:
            period, url = find_latest_url()
            filename = f"CA{period}.xlsx"
            print(f"Último fichero publicado: {filename}")
            if previous and previous["periodo"].replace("-", "") >= period and not args.force:
                print(f"Los datos ya están al día ({previous['periodo']}). Nada que hacer.")
                return 0
            xlsx = Path(tempfile.mkdtemp(prefix="inss_")) / filename
            download(url, xlsx)
            print(f"Descargado: {xlsx} ({xlsx.stat().st_size:,} bytes)")
        parsed = parse_excel(xlsx)
    except ValidationError as e:
        print(f"ERROR de validación: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # red, fichero corrupto…
        print(f"ERROR al obtener o leer el Excel: {e}", file=sys.stderr)
        return 2

    doc = build_json(parsed, filename)
    if previous and previous["periodo"] >= doc["periodo"] and not args.force:
        print(f"El fichero es de {doc['periodo']} y los datos ya son de {previous['periodo']}. Nada que hacer.")
        return 0

    try:
        for w in validate(parsed, previous):
            print("Aviso:", w)
    except ValidationError as e:
        print(f"ERROR de validación ({doc['periodo']}): {e}", file=sys.stderr)
        print("No se ha escrito nada.", file=sys.stderr)
        return 1

    nat = doc["nacional"]["total"]
    print(f"Validación correcta: {doc['periodo']}, 52 provincias, "
          f"{nat['num']:,} pensiones, media {nat['media']} €/mes")
    if args.dry_run:
        print("--dry-run: no se escribe nada.")
        return 0
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Escrito {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
