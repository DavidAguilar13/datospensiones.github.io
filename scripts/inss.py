"""Código común para leer y validar las estadísticas de pensiones del INSS
y la serie del IPC del INE.

Lo usan update_data.py (último mes) y build_history.py (histórico completo).
"""
from __future__ import annotations

import html as htmllib
import re
import time
import unicodedata
from datetime import date
from pathlib import Path

try:
    # Usa los certificados del sistema operativo si está instalado `truststore`.
    # Hace falta en Windows con antivirus que inspeccionan HTTPS (p. ej. Avast).
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / ".cache" / "inss"

BASE_URL = "https://www.seg-social.es"
EST = BASE_URL + "/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST23"
PAGE_CA = EST + "/EST24"                                   # pensiones en vigor (último mes)
PAGE_PTAS = EST + "/26bce586-014b-4c4e-9484-009cee21e271"  # pensionistas (último mes)
PAGE_HISTORY = EST + "/2575"                               # histórico por años

IPC_SERIES = "IPC290751"  # INE: Nacional. Índice general. Índice (base 2025)
IPC_URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/{}?nult=600"

USER_AGENT = "Mozilla/5.0 (datospensiones; actualizador de datos)"
SHEET = "CA_Total sistema"

# Bloques de columnas del Excel → clave en el JSON
TYPES = {
    "total pensiones": "total",
    "incapacidad permanente": "ip",
    "jubilacion": "jub",
    "viudedad": "viu",
    "orfandad": "orf",
    "favor de familiares": "fam",
}
TYPE_ORDER = ["total", "jub", "ip", "viu", "orf", "fam"]

# Rangos razonables de pensión media (€/mes) desde 2010. Fuera de esto, algo va mal.
MEDIA_RANGES = {
    "total": (500, 2500),
    "jub": (550, 2800),
    "ip": (450, 2500),
    "viu": (350, 1800),
    "orf": (200, 1200),
    "fam": (300, 1800),
}
NATIONAL_TOTAL_RANGE = (8_000_000, 14_000_000)
# Variación máxima admitida entre dos meses seguidos (num y media del total, por provincia)
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

# Variantes de nombre que aparecen en los Excel del INSS (2010–hoy) → código INE.
ALIASES = {
    "araba/alava": "01", "alava": "01", "araba": "01",
    "alicante/alacant": "03", "alacant": "03",
    "balears (illes)": "07", "i. balears": "07", "illes balears": "07", "baleares": "07",
    "islas baleares": "07",
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
    "andalucia", "aragon", "canarias", "castilla - la mancha", "castilla- la mancha",
    "castilla-la mancha", "castilla la mancha", "castilla y leon", "cataluna",
    "comunitat valenciana", "comunidad valenciana", "c.valenciana", "c. valenciana",
    "extremadura", "galicia", "pais vasco",
}
NATIONAL_LABELS = {"total sistema", "total"}

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}


class ValidationError(Exception):
    pass


def norm(text) -> str:
    """'Coruña (A)' → 'coruna (a)'; sin tildes, minúsculas, espacios simples."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def letters(text) -> str:
    """'P. media\\n(€/mes)' → 'pmediames'"""
    return re.sub(r"[^a-z]", "", norm(text))


NAME_TO_CODE = {norm(n): c for c, n in PROVINCES.items()}
NAME_TO_CODE.update({norm(a): c for a, c in ALIASES.items()})


# ─── Red ───────────────────────────────────────────────────────────────────────

_session = None


def session():
    global _session
    if _session is None:
        import requests

        _session = requests.Session()
        _session.headers["User-Agent"] = USER_AGENT
    return _session


def get_text(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            r = session().get(url, timeout=60)
            r.raise_for_status()
            return r.text
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def download(url: str, dest: Path, retries: int = 3) -> Path:
    for attempt in range(retries):
        try:
            r = session().get(url, timeout=120)
            r.raise_for_status()
            if not r.content.startswith(b"PK"):  # un .xlsx es un zip
                raise RuntimeError(f"La descarga no parece un Excel ({len(r.content)} bytes): {url}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return dest
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def page_links(page: str) -> list[tuple[str, str]]:
    """[(url absoluta, texto del enlace)]"""
    out = []
    for href, text in re.findall(r'href="([^"]+)"[^>]*>\s*([^<]{0,160})', page):
        href = htmllib.unescape(href)
        if href.startswith("/"):
            href = BASE_URL + href
        out.append((href, htmllib.unescape(text).strip()))
    return out


def xlsx_links(page_url: str, prefix: str) -> dict[str, str]:
    """{nombre de fichero: url} de los Excel de una página cuyo nombre empieza por `prefix`."""
    found = {}
    for href, _ in page_links(get_text(page_url)):
        m = re.search(r"/([^/?]+\.xlsx?)(?:\?|$)", href, re.I)
        if m:
            name = m.group(1).replace("%28", "(").replace("%29", ")")
            if name.upper().startswith(prefix.upper()):
                found[name] = href
    return found


def period_from_filename(name: str) -> str | None:
    """CA202610.xlsx → '2026-10'; CA2201901.xlsx → '2019-01'; CA2(012010).xlsx → '2010-01'."""
    digits = re.sub(r"\D", "", re.sub(r"\.xlsx?$", "", name, flags=re.I))
    for d in (digits, digits[1:]):  # CA2… lleva un 2 delante
        if len(d) == 6:
            if d.startswith("20") and 1 <= int(d[4:]) <= 12:
                return f"{d[:4]}-{d[4:]}"
            if d[2:].startswith("20") and 1 <= int(d[:2]) <= 12:
                return f"{d[2:]}-{d[:2]}"
    return None


def latest_link(page_url: str, prefix: str) -> tuple[str, str, str]:
    """(periodo, nombre, url) del fichero más reciente con ese prefijo en la página."""
    links = {}
    for name, url in xlsx_links(page_url, prefix).items():
        p = period_from_filename(name)
        if p and re.fullmatch(prefix + r"\d{6}\.xlsx", name, re.I):
            links[p] = (name, url)
    if not links:
        raise RuntimeError(f"No se ha encontrado ningún {prefix}aaaamm.xlsx en {page_url}")
    p = max(links)
    return p, links[p][0], links[p][1]


def history_ca_links(log=print) -> dict[str, tuple[str, str]]:
    """Recorre el histórico (años → pensiones en vigor → CCAA y provincias) y
    devuelve {periodo: (nombre, url)} de todos los CA mensuales."""
    out = {}
    years = [(h, t) for h, t in page_links(get_text(PAGE_HISTORY)) if re.match(r"Año\s+\d{4}", t)]
    for yurl, ytext in years:
        year = re.search(r"\d{4}", ytext).group()
        sub = lambda url, words: [
            h for h, t in page_links(get_text(url))
            if h.startswith(yurl + "/") and "!ut" not in h and any(w in norm(t) for w in words)
        ]
        found = {}
        for vigor in sub(yurl, ["en vigor"])[:1]:
            for prov in sub(vigor, ["ccaa", "provincia"])[:1]:
                for name, url in xlsx_links(prov, "CA").items():
                    p = period_from_filename(name)
                    if p:
                        found[p] = (name, url)
        log(f"  {year}: {len(found)} meses")
        out.update(found)
    return dict(sorted(out.items()))


# ─── Excel de pensiones por provincia (CA) ─────────────────────────────────────

def parse_ca(path: Path) -> dict:
    """Lee un CA*.xlsx (formato 2010–2020 o actual).
    Devuelve {'fecha': date, 'nacional': bloque, 'provincias': {código: bloque}}."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows, columns, data_start = total_sheet(wb)
    fecha = parse_date(rows)

    national = None
    provinces: dict[str, dict] = {}
    unknown = []
    for row in rows[data_start:]:
        # La etiqueta está en la primera columna de texto (algunos años llevan
        # delante una columna con el código de provincia).
        label = next((c for c in (row or [])[:2] if isinstance(c, str) and c.strip()), None)
        if label is None:
            continue
        key = norm(label)
        if key in NATIONAL_LABELS:
            block = read_block(row, columns, label)
            # algunos meses de 2020 repiten el total al principio y al final
            if national is not None and clean_block(national) != clean_block(block):
                raise ValidationError(f"Dos filas de total nacional con datos distintos: {label}")
            national = block
        elif key in NAME_TO_CODE:
            code = NAME_TO_CODE[key]
            if code in provinces:
                raise ValidationError(f"Provincia repetida: {label} ({code})")
            provinces[code] = read_block(row, columns, label)
        elif key in CCAA:
            continue
        elif key.startswith(("fuente", "nota", "(", "*")):
            continue
        else:
            unknown.append(str(label))

    if unknown:
        raise ValidationError(f"Filas con nombres desconocidos: {unknown}")
    if national is None:
        raise ValidationError("No se ha encontrado la fila del total nacional")
    return {"fecha": fecha, "nacional": national, "provincias": provinces}


def total_sheet(wb) -> tuple[list, dict, int]:
    """Encuentra la hoja del «Total sistema». Según el año se llama «CA_Total sistema»,
    «Total Sistema» o «CA2»; se elige por contenido: «TOTAL SISTEMA» en la cabecera
    y las columnas de tipos de pensión."""
    names = sorted(wb.sheetnames, key=lambda n: (norm(n) not in ("ca_total sistema", "total sistema", "ca2"), n))
    tried = []
    for name in names:
        rows = [list(r) for r in wb[name].iter_rows(max_row=12, values_only=True)]
        head = {norm(c) for r in rows[:6] for c in (r or []) if isinstance(c, str)}
        if "total sistema" not in head and norm(name) not in ("ca_total sistema", "total sistema"):
            continue
        tried.append(name)
        try:
            columns, start = find_columns(rows)
        except ValidationError:
            continue
        return [list(r) for r in wb[name].iter_rows(values_only=True)], columns, start
    raise ValidationError(f"No se encuentra la hoja del total del sistema. Hojas: {wb.sheetnames} "
                          f"(probadas: {tried})")


def parse_date(rows) -> date:
    for row in rows[:6]:
        for cell in row or []:
            if not cell:
                continue
            m = re.search(r"a\s+(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})", norm(cell))
            if m and m.group(2) in MONTHS:
                return date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    raise ValidationError("No se ha encontrado la fecha («A 1 DE … DE …») en la cabecera")


def find_columns(rows) -> tuple[dict, int]:
    """Busca la fila con los tipos de pensión y, debajo, 'Número / [Importe] / P. media'.
    Devuelve ({tipo: (col_num, col_importe|None, col_media)}, fila donde empiezan los datos)."""
    for i, row in enumerate(rows[:15]):
        groups = {TYPES[norm(c)]: j for j, c in enumerate(row or []) if c and norm(c) in TYPES}
        if len(groups) < len(TYPES):
            continue
        sub = [letters(c) if c else "" for c in rows[i + 1]]
        sub += [""] * 4
        columns = {}
        for t, j in groups.items():
            span = range(j, j + 3)
            num_col = next((k for k in span if sub[k].startswith("numero")), None)
            imp_col = next((k for k in span if sub[k].startswith("importe")), None)
            med_col = next((k for k in span if sub[k].startswith("pmedia")), None)
            if None in (num_col, med_col):
                raise ValidationError(f"Columnas inesperadas bajo «{t}»: {rows[i + 1][j:j + 3]}")
            columns[t] = (num_col, imp_col, med_col)
        return columns, i + 2
    raise ValidationError("No se han encontrado las columnas esperadas: " + ", ".join(TYPES))


def read_block(row, columns, label) -> dict:
    out = {}
    for t, (cn, ci, cm) in columns.items():
        num, media = row[cn], row[cm]
        imp = row[ci] if ci is not None else None
        if num in (None, "", "-"):
            num, imp, media = 0, 0, None
        if not isinstance(num, (int, float)) or (media is not None and not isinstance(media, (int, float))):
            raise ValidationError(f"Valor no numérico en {label} / {t}: {num!r}, {media!r}")
        out[t] = {
            "num": int(round(num)),
            "media": round(float(media), 2) if media not in (None, 0) else None,
            "_importe": float(imp) if isinstance(imp, (int, float)) else None,
        }
    return out


def validate_ca(parsed: dict, previous: dict | None = None, label: str = "") -> None:
    """Lanza ValidationError con todos los problemas encontrados.
    `previous` es el mes anterior en el mismo formato (bloques por código)."""
    errors = []
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
            num, media, imp = p[t]["num"], p[t]["media"], p[t]["_importe"]
            if num == 0:
                continue
            if media is None or not mlo <= media <= mhi:
                errors.append(f"{name} / {t}: pensión media fuera de rango ({media})")
                continue
            if imp is not None and abs(imp / num - media) > 1:
                errors.append(f"{name} / {t}: la media ({media}) no cuadra con importe/número ({imp / num:.2f})")
        parts = sum(p[t]["num"] for t in TYPE_ORDER if t != "total")
        if parts != p["total"]["num"]:
            errors.append(f"{name}: la suma por tipos ({parts}) no da el total ({p['total']['num']})")

    if not missing:
        for t in TYPE_ORDER:
            s = sum(p[t]["num"] for p in provs.values())
            if s != nat[t]["num"]:
                errors.append(f"{t}: la suma de provincias ({s}) no da el total nacional ({nat[t]['num']})")

    if previous and not errors:
        for code, p in provs.items():
            old = previous.get(code)
            if not old:
                continue
            for field in ("num", "media"):
                a, b = old["total"][field], p["total"][field]
                if a and b and abs(b - a) / a > MAX_MONTHLY_CHANGE:
                    errors.append(
                        f"{PROVINCES[code]}: el total ({field}) cambia un {100 * (b - a) / a:+.1f}% "
                        f"respecto al mes anterior ({a} → {b})"
                    )

    if errors:
        head = f"{label}: " if label else ""
        raise ValidationError(head + "\n  - " + "\n  - ".join(errors))


def clean_block(block: dict) -> dict:
    return {t: {"num": block[t]["num"], "media": block[t]["media"]} for t in TYPE_ORDER}


def period_of(parsed: dict) -> str:
    return f"{parsed['fecha'].year}-{parsed['fecha'].month:02d}"


# ─── Excel de pensionistas (PTAS): reparto por tramos de cuantía ───────────────

BRACKET_SHEET = "Tramos (concurrencia)"
SUMMARY_SHEET = "Resumen de datos"


def _euros(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def parse_bracket(label: str) -> tuple[float, float | None]:
    t = norm(label)
    if m := re.match(r"hasta ([\d.,]+)", t):
        return 0.0, _euros(m.group(1))
    if m := re.match(r"de ([\d.,]+) a ([\d.,]+)", t):
        return _euros(m.group(1)), _euros(m.group(2))
    if m := re.match(r"mas de ([\d.,]+)", t):
        return _euros(m.group(1)), None
    raise ValidationError(f"Tramo de cuantía no reconocido: {label!r}")


def parse_ptas(path: Path) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for s in (BRACKET_SHEET, SUMMARY_SHEET):
        if s not in wb.sheetnames:
            raise ValidationError(f"No existe la hoja «{s}». Hojas: {wb.sheetnames}")

    # Resumen: número de pensionistas, importe medio y mínimos, por sexo
    rows = [list(r) for r in wb[SUMMARY_SHEET].iter_rows(values_only=True)]
    fecha = parse_date(rows)
    hdr = next((i for i, r in enumerate(rows) if r and "ambos sexos" in " ".join(norm(c) for c in r if c)), None)
    if hdr is None:
        raise ValidationError("Resumen: no se encuentra la cabecera «Ambos sexos / Mujeres / Hombres»")
    cols = {}
    for j, c in enumerate(rows[hdr]):
        if c and norm(c).startswith("ambos sexos"):
            cols["ambos"] = j
        elif c and norm(c) == "mujeres":
            cols["mujeres"] = j
        elif c and norm(c) == "hombres":
            cols["hombres"] = j
    if len(cols) != 3:
        raise ValidationError(f"Resumen: columnas de sexo inesperadas: {rows[hdr]}")

    def row_values(start: int, label: str) -> dict:
        for r in rows[start:]:
            if r and r[0] and norm(r[0]).startswith(label):
                return {k: r[j] for k, j in cols.items()}
        raise ValidationError(f"Resumen: no se encuentra la fila «{label}»")

    pensionistas = row_values(hdr, "numero de pensionistas")
    importe = row_values(hdr, "importe medio mensual")
    i_min = next(i for i, r in enumerate(rows) if r and r[0] and norm(r[0]).startswith("pensionistas con minimos"))
    minimos = row_values(i_min, "numero")
    minimos_pct = row_values(i_min, "porcentaje")

    # Tramos: TOTAL PERCEPTORES por sexo
    rows = [list(r) for r in wb[BRACKET_SHEET].iter_rows(values_only=True)]
    hdr = next((i for i, r in enumerate(rows) if r and r[0] and norm(r[0]).startswith("tramo de cuantia")), None)
    if hdr is None:
        raise ValidationError("Tramos: no se encuentra la cabecera «TRAMO DE CUANTÍA»")
    sex = next(i for i in range(hdr + 1, hdr + 4) if rows[i] and any(c and norm(c) == "mujeres" for c in rows[i]))
    # Las tres primeras columnas de sexo son el TOTAL PERCEPTORES
    c_amb = next(j for j, c in enumerate(rows[sex]) if c and norm(c).startswith("ambos sexos"))
    c_muj, c_hom = c_amb + 1, c_amb + 2
    if norm(rows[sex][c_muj]) != "mujeres" or norm(rows[sex][c_hom]) != "hombres":
        raise ValidationError(f"Tramos: columnas de sexo inesperadas: {rows[sex]}")
    if "total perceptores" not in norm(rows[hdr][c_amb] or ""):
        raise ValidationError(f"Tramos: se esperaba «TOTAL PERCEPTORES» y hay {rows[hdr][c_amb]!r}")

    total = None
    tramos = []
    for r in rows[sex + 1:]:
        if not r or not r[0]:
            continue
        lab = norm(r[0])
        if lab == "total":
            total = {"ambos": r[c_amb], "mujeres": r[c_muj], "hombres": r[c_hom]}
        elif lab.startswith(("hasta", "de ", "mas de")):
            lo, hi = parse_bracket(r[0])
            tramos.append({"etiqueta": str(r[0]).strip(), "desde": lo, "hasta": hi,
                           "ambos": int(r[c_amb]), "mujeres": int(r[c_muj]), "hombres": int(r[c_hom])})
    if total is None:
        raise ValidationError("Tramos: no se encuentra la fila TOTAL")

    return {"fecha": fecha, "pensionistas": pensionistas, "importe_medio": importe,
            "minimos": minimos, "minimos_pct": minimos_pct, "total_tramos": total, "tramos": tramos}


def validate_ptas(p: dict) -> None:
    errors = []
    tr = p["tramos"]
    if len(tr) < 20:
        errors.append(f"Solo hay {len(tr)} tramos de cuantía")
    for k in ("ambos", "mujeres", "hombres"):
        s = sum(t[k] for t in tr)
        if s != p["total_tramos"][k]:
            errors.append(f"Tramos ({k}): la suma ({s}) no da el TOTAL ({p['total_tramos'][k]})")
        if p["pensionistas"][k] != p["total_tramos"][k]:
            errors.append(f"Pensionistas ({k}) del resumen y de los tramos no coinciden")
    if not 7_000_000 <= p["pensionistas"]["ambos"] <= 12_000_000:
        errors.append(f"Número de pensionistas fuera de rango: {p['pensionistas']['ambos']}")
    for k, v in p["importe_medio"].items():
        if not 500 <= v <= 3000:
            errors.append(f"Importe medio ({k}) fuera de rango: {v}")
    if not 0.05 <= p["minimos_pct"]["ambos"] <= 0.5:
        errors.append(f"Porcentaje con mínimos fuera de rango: {p['minimos_pct']['ambos']}")
    prev_hi = 0
    for t in tr:
        if t["desde"] + 0.02 < prev_hi:
            errors.append(f"Tramos desordenados o solapados en {t['etiqueta']}")
        prev_hi = t["hasta"] or prev_hi
    if tr and tr[-1]["hasta"] is not None:
        errors.append("El último tramo debería ser abierto («Más de …»)")
    if errors:
        raise ValidationError("\n  - " + "\n  - ".join(errors))


def inequality(p: dict) -> dict:
    """Gini aproximado a partir de los tramos (punto medio de cada tramo; el tramo
    abierto se ajusta para que el importe total cuadre con el importe medio)."""
    tr = p["tramos"]
    n = p["pensionistas"]["ambos"]
    total_income = p["importe_medio"]["ambos"] * n
    means = [(t["desde"] + t["hasta"]) / 2 for t in tr[:-1]]
    rest = total_income - sum(m * t["ambos"] for m, t in zip(means, tr))
    top = tr[-1]
    top_mean = rest / top["ambos"] if top["ambos"] else top["desde"]
    if top_mean <= top["desde"]:  # no debería pasar; por si acaso
        top_mean = top["desde"] * 1.1
    means.append(top_mean)

    cum_n = cum_y = 0.0
    gini = 1.0
    for m, t in zip(means, tr):
        x0, y0 = cum_n / n, cum_y / total_income
        cum_n += t["ambos"]
        cum_y += m * t["ambos"]
        x1, y1 = cum_n / n, cum_y / total_income
        gini -= (x1 - x0) * (y1 + y0)

    def quantile_bracket(q: float) -> dict:
        acc = 0
        for t in tr:
            acc += t["ambos"]
            if acc >= q * n:
                return t
        return tr[-1]

    med = quantile_bracket(0.5)
    return {
        "gini": round(gini, 3),
        "media_tramo_abierto": round(top_mean, 2),
        "mediana_tramo": {"desde": med["desde"], "hasta": med["hasta"]},
    }


def bins_100(tramos: list[dict]) -> list[dict]:
    """Agrupa los tramos en intervalos de 100 € (el primero «hasta 300»; los dos
    últimos se dejan aparte: pensión máxima y por encima de ella)."""
    out: dict[tuple, dict] = {}
    for t in tramos:
        if t["hasta"] is None:
            key = (t["desde"], None, f"Más de {t['desde']:,.0f} €")
        elif t["hasta"] <= 300:
            key = (0, 300, "Hasta 300 €")
        elif t["desde"] >= 3300:
            key = (3300, tramos[-1]["desde"], "Pensión máxima")
        else:
            lo = int((t["desde"] - 0.01) // 100 * 100)
            key = (lo, lo + 100, f"{lo:,}–{lo + 100:,} €")
        b = out.setdefault(key, {"etiqueta": key[2].replace(",", "."), "desde": key[0], "hasta": key[1],
                                 "ambos": 0, "mujeres": 0, "hombres": 0})
        for k in ("ambos", "mujeres", "hombres"):
            b[k] += t[k]
    return list(out.values())


# ─── IPC (INE) ─────────────────────────────────────────────────────────────────

def fetch_ipc() -> dict[str, float]:
    """{'2010-01': 72.759, …} del índice general nacional del IPC."""
    import json

    data = json.loads(get_text(IPC_URL.format(IPC_SERIES)))
    out = {}
    for d in data["Data"]:
        if d.get("Valor") is not None:
            out[f"{d['Anyo']}-{d['FK_Periodo']:02d}"] = float(d["Valor"])
    if len(out) < 100:
        raise ValidationError(f"La serie del IPC ({IPC_SERIES}) tiene muy pocos datos: {len(out)}")
    vals = list(dict(sorted(out.items())).values())
    for a, b in zip(vals, vals[1:]):
        if abs(b - a) / a > 0.05:
            raise ValidationError(f"Salto mensual del IPC mayor del 5 %: {a} → {b}")
    return dict(sorted(out.items()))
