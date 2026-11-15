"""Radar de datos: detecta qué han publicado esta semana las fuentes que interesan a David.

Lo hace solo con código, sin IA: compara lo publicado con lo que vio la ejecución anterior
(radar/estado.json) y escribe:
  - radar/novedades.json  novedades de la semana, cada una con fuente, tema, fecha y enlace
  - radar/novedades.md    el mismo listado en texto, para el issue semanal

El agente del radar (rutina de Claude, ver RADAR.md) lee después novedades.json, comenta
por qué importa cada cosa y, si un dato encaja, propone añadirlo al analista.

Fuentes:
  - INE: operaciones estadísticas (fecha de última modificación de sus tablas)
  - Eurostat: último periodo con dato para España
  - Banco de España: último trimestre de déficit y deuda de las AAPP (be1101.csv)
  - BOE: disposiciones generales (sección I) cuyo título toca los temas de David
  - AIReF: publicaciones de su web (RSS)

Uso:
    python scripts/radar/radar.py            # semana normal
    python scripts/radar/radar.py --dias 7   # fuerza la ventana de días (BOE, AIReF, INE)

Códigos de salida: 0 bien; 2 si fallan TODAS las fuentes (si falla alguna, se avisa en
novedades.json → «errores» y el resto sigue).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/

import inss  # noqa: E402  (sesión HTTP con certificados del sistema y reintentos)
from defusedxml import ElementTree  # noqa: E402

ROOT = inss.ROOT
OUT = ROOT / "radar"
ESTADO = OUT / "estado.json"

TEMAS = {
    "pensiones": "Pensiones y Seguridad Social",
    "estado": "Estado y deuda",
    "demografia": "Demografía",
    "vivienda": "Vivienda y desigualdad",
    "otros": "Otras publicaciones (sin palabra clave de tus temas)",
}

# ─── Fuentes ───────────────────────────────────────────────────────────────────

# INE: código de operación → (temas, ¿ya la usa el analista?)
INE_OPERACIONES = {
    "ETCL": (["pensiones", "vivienda"], True),    # salarios (pensiones frente a salarios reales)
    "IPC": (["pensiones", "vivienda"], True),     # inflación (pensión real)
    "EPA": (["estado", "pensiones"], False),      # empleo, empleo público, paro
    "ECV": (["vivienda"], False),                 # renta, pobreza, Gini
    "EAES": (["vivienda"], False),                # estructura salarial (desigualdad salarial)
    "IPV": (["vivienda"], False),                 # precios de la vivienda
    "IPVA": (["vivienda"], False),                # precios del alquiler
    "IRAV": (["vivienda"], False),                # índice de referencia de alquileres
    "EMN": (["demografia"], False),               # nacimientos (estimación mensual)
    "MNPN": (["demografia"], False),              # nacimientos (definitivos)
    "ECP": (["demografia", "pensiones"], False),  # población (envejecimiento)
    "PROP": (["demografia", "pensiones"], False), # proyecciones de población
    "EMCR": (["demografia"], False),              # migraciones
}
INE_OPS_URL = "https://servicios.ine.es/wstempus/js/ES/OPERACIONES_DISPONIBLES"
INE_TABLAS_URL = "https://servicios.ine.es/wstempus/js/ES/TABLAS_OPERACION/{}"

EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{}&lastTimePeriod=4"
EUROSTAT = [
    # (id, consulta, nombre, temas)
    ("gov_10q_ggdebt", "gov_10q_ggdebt?geo=ES&unit=PC_GDP&sector=S13&na_item=GD",
     "Deuda pública trimestral (% del PIB)", ["estado"]),
    ("gov_10a_exp_vejez", "gov_10a_exp?geo=ES&unit=PC_GDP&sector=S13&na_item=TE&cofog99=GF1002",
     "Gasto público en vejez, COFOG (% del PIB)", ["pensiones", "estado"]),
    ("gov_10a_exp_total", "gov_10a_exp?geo=ES&unit=PC_GDP&sector=S13&na_item=TE&cofog99=TOTAL",
     "Gasto público total, COFOG (% del PIB)", ["estado"]),
    ("spr_exp_pens", "spr_exp_pens?geo=ES&unit=PC_GDP&spdepb=TOTAL&spdepm=TOTAL",
     "Gasto en pensiones, SEEPROS (% del PIB)", ["pensiones"]),
    ("demo_find", "demo_find?geo=ES&indic_de=TOTFERRT",
     "Tasa de fecundidad", ["demografia"]),
    ("ilc_di12", "ilc_di12?geo=ES",
     "Coeficiente de Gini de la renta disponible", ["vivienda"]),
    ("prc_hpi_q", "prc_hpi_q?geo=ES&purchase=TOTAL&unit=I15_Q",
     "Índice de precios de la vivienda (trimestral)", ["vivienda"]),
]

BDE_URL = "https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/be1101.csv"
BDE_WEB = "https://www.bde.es/webbe/es/estadisticas/temas/administraciones-publicas.html"
MESES_BDE = {"MAR": "T1", "JUN": "T2", "SEP": "T3", "DIC": "T4"}

BOE_URL = "https://www.boe.es/datosabiertos/api/boe/sumario/{}"
BOE_SECCIONES = {"1"}  # I. Disposiciones generales
BOE_CLAVES = {
    "pensiones": ["pensi", "seguridad social", "cotizaci", "revaloriz", "jubilaci",
                  "fondo de reserva", "equidad intergeneracional", "clases pasivas",
                  "ingreso mínimo vital", "incapacidad permanente"],
    "estado": ["presupuestos generales", "deuda pública", "deuda del estado", "empleo público",
               "oferta de empleo", "retribuciones", "estabilidad presupuestaria",
               "techo de gasto", "déficit", "sector público"],
    "demografia": ["natalidad", "nacimiento", "familias numerosas", "crianza", "extranjer",
                   "inmigra", "permiso parental"],
    "vivienda": ["vivienda", "arrendamiento", "alquiler", "salario mínimo", "iprem",
                 "desigualdad", "pobreza"],
}

AIREF_RSS = "https://www.airef.es/es/feed/"
AIREF_CLAVES = {
    "pensiones": ["pensi", "seguridad social", "equidad intergeneracional", "gasto en pensiones"],
    "estado": ["deuda", "déficit", "gasto", "presupuest", "estabilidad", "sostenibilidad",
               "administraciones públicas", "fiscal", "spending review"],
    "demografia": ["demogr", "población", "envejec", "migra"],
    "vivienda": ["vivienda", "desigualdad", "renta"],
}


# ─── Utilidades ────────────────────────────────────────────────────────────────

def http_json(url: str, headers: dict | None = None):
    for attempt in range(3):
        try:
            r = inss.session().get(url, timeout=60, headers=headers or {})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == 2:
                raise


def temas_por_claves(texto: str, claves: dict[str, list[str]]) -> list[str]:
    t = texto.lower()
    return [tema for tema, palabras in claves.items() if any(p in t for p in palabras)]


def fecha_ine(s: str) -> datetime:
    """'Wed Oct 21 09:00:00 CEST 2026' → datetime (se ignora la zona horaria)."""
    partes = s.split()
    return datetime.strptime(" ".join(partes[:4] + partes[5:]), "%a %b %d %H:%M:%S %Y")


def novedad(fuente, temas, titulo, url, fecha, detalle="", en_analista=False, id_=None):
    return {"id": id_ or f"{fuente}:{titulo}"[:120], "fuente": fuente, "temas": temas,
            "titulo": titulo, "detalle": detalle, "fecha": fecha, "url": url,
            "en_analista": en_analista}


# ─── Comprobaciones por fuente ─────────────────────────────────────────────────

def radar_ine(desde: date, estado: dict) -> list[dict]:
    ops = {o.get("Codigo"): o for o in http_json(INE_OPS_URL)}
    nuevas, previo = [], estado.get("ine", {})
    for cod, (temas, en_analista) in INE_OPERACIONES.items():
        op = ops.get(cod)
        if not op:
            raise RuntimeError(f"INE: no existe la operación {cod}")
        tablas = http_json(INE_TABLAS_URL.format(cod)) or []
        fechas = [fecha_ine(t["Ultima_Modificacion"]) for t in tablas
                  if t.get("Ultima_Modificacion") not in (None, "", "null")]
        if not fechas:
            continue
        ultima = max(fechas)
        cambiadas = sorted({t["Nombre"].strip() for t in tablas if t.get("Ultima_Modificacion")
                            not in (None, "", "null") and fecha_ine(t["Ultima_Modificacion"]) == ultima})
        anterior = previo.get(cod)
        es_nueva = (ultima.isoformat() > anterior) if anterior else (ultima.date() >= desde)
        if es_nueva:
            nombre = op["Nombre"].strip()
            detalle = f"{len(cambiadas)} tabla(s) actualizada(s), p. ej.: {cambiadas[0][:150]}"
            url = op.get("Url", "")
            url = url if url.startswith("http") else "https://www.ine.es" + url
            nuevas.append(novedad("INE", temas, nombre, url,
                                  ultima.date().isoformat(), detalle, en_analista, f"INE:{cod}"))
        estado.setdefault("ine", {})[cod] = ultima.isoformat()
    return nuevas


def radar_eurostat(desde: date, estado: dict) -> list[dict]:
    nuevas, previo = [], estado.get("eurostat", {})
    for id_, consulta, nombre, temas in EUROSTAT:
        d = http_json(EUROSTAT_URL.format(consulta))
        tiempos = d["dimension"]["time"]["category"]["index"]  # {'2024': 0, …}
        con_dato = [t for t, i in tiempos.items() if str(i) in d.get("value", {})]
        if not con_dato:
            raise RuntimeError(f"Eurostat {id_}: sin datos para España")
        ultimo = max(con_dato)
        anterior = previo.get(id_)
        if anterior and ultimo != anterior:
            nuevas.append(novedad(
                "Eurostat", temas, nombre,
                f"https://ec.europa.eu/eurostat/databrowser/view/{consulta.split('?')[0]}/default/table",
                (d.get("updated") or "")[:10], f"Nuevo periodo para España: {ultimo} (antes {anterior})",
                id_=f"Eurostat:{id_}:{ultimo}"))
        estado.setdefault("eurostat", {})[id_] = ultimo
    return nuevas


def radar_bde(desde: date, estado: dict) -> list[dict]:
    r = inss.session().get(BDE_URL, timeout=60)
    r.raise_for_status()
    filas = list(csv.reader(io.StringIO(r.content.decode("latin-1"))))
    periodos = []
    for f in filas:
        m = re.fullmatch(r"(MAR|JUN|SEP|DIC) (\d{4})", f[0].strip()) if f else None
        if m and any(c.strip() not in ("", "_") for c in f[1:]):
            periodos.append(f"{m.group(2)}-{MESES_BDE[m.group(1)]}")
    if not periodos:
        raise RuntimeError("Banco de España: be1101.csv sin periodos reconocibles")
    ultimo, anterior = max(periodos), estado.get("bde", {}).get("be1101")
    estado.setdefault("bde", {})["be1101"] = ultimo
    if anterior and ultimo != anterior:
        return [novedad("Banco de España", ["estado", "pensiones"],
                        "Déficit y deuda de las AAPP por subsectores (PDE), incluida la Seguridad Social",
                        BDE_WEB, date.today().isoformat(),
                        f"Nuevo trimestre: {ultimo} (antes {anterior}). Fichero: {BDE_URL}",
                        id_=f"BdE:be1101:{ultimo}")]
    return []


def _lista(x):
    return x if isinstance(x, list) else ([x] if x else [])


def radar_boe(desde: date, estado: dict) -> list[dict]:
    nuevas, dia, hoy = [], desde, date.today()
    while dia <= hoy:
        d = http_json(BOE_URL.format(dia.strftime("%Y%m%d")), {"Accept": "application/json"})
        dia_txt = dia.isoformat()
        dia += timedelta(days=1)
        if not d:  # domingo o día sin BOE
            continue
        for diario in _lista(d["data"]["sumario"].get("diario")):
            for sec in _lista(diario.get("seccion")):
                if str(sec.get("codigo")) not in BOE_SECCIONES:
                    continue
                for dep in _lista(sec.get("departamento")):
                    items = _lista(dep.get("item"))
                    for ep in _lista(dep.get("epigrafe")):
                        items += _lista(ep.get("item"))
                    for it in items:
                        titulo = it.get("titulo", "")
                        temas = temas_por_claves(titulo, BOE_CLAVES)
                        if temas:
                            nuevas.append(novedad("BOE", temas, titulo, it.get("url_html", ""),
                                                  dia_txt, dep.get("nombre", ""),
                                                  id_=f"BOE:{it.get('identificador')}"))
    return nuevas


def radar_airef(desde: date, estado: dict) -> list[dict]:
    raiz = ElementTree.fromstring(inss.get_text(AIREF_RSS).encode("utf-8"))
    nuevas = []
    for item in raiz.iter("item"):
        titulo = (item.findtext("title") or "").strip()
        fecha = parsedate_to_datetime(item.findtext("pubDate")).astimezone(timezone.utc).date()
        if fecha < desde:
            continue
        temas = temas_por_claves(titulo, AIREF_CLAVES) or ["otros"]
        nuevas.append(novedad("AIReF", temas, titulo, item.findtext("link") or "",
                              fecha.isoformat(),
                              id_=f"AIReF:{item.findtext('link')}"))
    return nuevas


FUENTES = [("INE", radar_ine), ("Eurostat", radar_eurostat), ("Banco de España", radar_bde),
           ("BOE", radar_boe), ("AIReF", radar_airef)]


# ─── Salida ────────────────────────────────────────────────────────────────────

def markdown(res: dict) -> str:
    l = [f"Novedades publicadas entre el **{res['desde']}** y el **{res['hasta']}** en las fuentes "
         "que vigila el radar. Listado hecho por código (`scripts/radar/radar.py`); el agente del "
         "radar comentará aquí por qué importa cada cosa.", ""]
    if res["primera_ejecucion"]:
        l += ["> Primera ejecución: Eurostat y Banco de España solo guardan el estado inicial; "
              "avisarán a partir de la próxima semana.", ""]
    for tema, nombre in TEMAS.items():
        items = [n for n in res["novedades"] if n["temas"][0] == tema]
        if not items:
            continue
        l.append(f"### {nombre}")
        for n in items:
            extra = " · *ya lo usa el analista*" if n["en_analista"] else ""
            l.append(f"- **{n['fuente']}** ({n['fecha']}): [{n['titulo']}]({n['url']}){extra}")
            if n["detalle"]:
                l.append(f"  <br>{n['detalle']}")
        l.append("")
    if not res["novedades"]:
        l += ["Sin novedades esta semana.", ""]
    if res["errores"]:
        l.append("### ⚠️ Fuentes que han fallado")
        l += [f"- {e}" for e in res["errores"]]
    return "\n".join(l) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, help="ventana en días (por defecto, desde la última ejecución)")
    args = ap.parse_args()

    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    hoy = date.today()
    if args.dias:
        desde = hoy - timedelta(days=args.dias)
    elif estado.get("ultima_ejecucion"):
        desde = max(date.fromisoformat(estado["ultima_ejecucion"]) + timedelta(days=1),
                    hoy - timedelta(days=21))
    else:
        desde = hoy - timedelta(days=7)

    novedades, errores = [], []
    for nombre, funcion in FUENTES:
        try:
            nuevas = funcion(desde, estado)
            print(f"{nombre}: {len(nuevas)} novedad(es)")
            novedades += nuevas
        except Exception as e:  # una fuente caída no tumba el radar
            print(f"{nombre}: ERROR {e}", file=sys.stderr)
            errores.append(f"{nombre}: {type(e).__name__}: {e}"[:300])
    if len(errores) == len(FUENTES):
        print("Han fallado todas las fuentes; no se escribe nada.", file=sys.stderr)
        return 2

    vistos, unicas = set(), []
    for n in novedades:
        if n["id"] not in vistos:
            vistos.add(n["id"])
            unicas.append(n)
    orden = list(TEMAS)
    unicas.sort(key=lambda n: (orden.index(n["temas"][0]), n["fuente"], n["fecha"]))

    res = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "desde": desde.isoformat(), "hasta": hoy.isoformat(),
        "primera_ejecucion": "ultima_ejecucion" not in estado,
        "temas": TEMAS, "novedades": unicas, "errores": errores,
    }
    estado["ultima_ejecucion"] = hoy.isoformat()
    OUT.mkdir(exist_ok=True)
    (OUT / "novedades.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "novedades.md").write_text(markdown(res), encoding="utf-8")
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Total: {len(unicas)} novedad(es), {len(errores)} fuente(s) con error.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
