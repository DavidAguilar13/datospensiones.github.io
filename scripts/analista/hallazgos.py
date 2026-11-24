"""Calcula los hallazgos de la semana y genera los gráficos del analista.

Lee los datos ya validados de la web (data/*.json) y la serie de salarios del INE,
y escribe:
  - analisis/hallazgos.json  cifras, comparaciones y advertencias, cada una con su fuente
  - analisis/graficos/*.png  gráficos con el estilo de David

Aquí se calculan TODAS las cifras. El agente redactor solo puede usar las que
aparecen en hallazgos.json (ver ANALISTA.md).

Uso:
    python scripts/analista/hallazgos.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/

import inss  # noqa: E402  (certificados, descarga, validación del IPC)
import estilo  # noqa: E402
from estilo import AZUL, NARANJA, ROJO, VERDE, num_es  # noqa: E402

ROOT = inss.ROOT
OUT = ROOT / "analisis"
GRAF = OUT / "graficos"

WAGE_SERIES = "ETCL1527"
WAGE_URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/{}?nult=400"
WAGE_INFO = {
    "nombre": "Coste salarial total por trabajador y mes (ETCL)",
    "fuente": "INE, Encuesta Trimestral de Coste Laboral",
    "serie": WAGE_SERIES,
    "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=6038",
}
SRC_PENS = "INSS, pensiones contributivas en vigor (total sistema)"
SRC_IPC = "INE, IPC general"
SRC_PTAS = "INSS, pensionistas por tramos de cuantía"
BASE_YEAR = 2010

BDE_CSV = "https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/be{}.csv"
BDE_WEB = "https://www.bde.es/webbe/es/estadisticas/temas/administraciones-publicas.html"
SRC_BDE = "Banco de España, Boletín Estadístico, cap. 11 (PDE, SEC 2010)"
# (tabla, código de serie) → nombre interno. Valores en miles de euros salvo los «_pib».
BDE_SERIES = {
    ("1103", "DTNSEC2010_S00000_ASG"): "saldo",        # capacidad (+) / necesidad (-) de financiación, flujo trimestral
    ("1106", "DTNPDE2010_P00000_PS_ASG"): "deuda",     # deuda PDE de la Seguridad Social, saldo a fin de trimestre
    ("1106", "DTNPDE2010_A00030_AS_ASG"): "activos",   # activos financieros frente a otras AAPP
    ("1106", "DTNPDE2010_P0000N_PS_ASG"): "neta",      # deuda neta de esos activos
    ("1107", "DTNPDE2010_P0000P_PS_ASG"): "deuda_pib", # deuda PDE, % del PIB
    ("1101", "DTNSEC2010_PIBPM"): "pib",               # PIB nominal, suma de 4 trimestres
}
TRIM_BDE = {"MAR": 1, "JUN": 2, "SEP": 3, "DIC": 4}
DEUDA_SS_BASE = 2016  # último año antes de los préstamos anuales del Estado a la Seguridad Social

TIPO_NOMBRE = {"total": "total del sistema", "jub": "jubilación", "ip": "incapacidad permanente",
               "viu": "viudedad", "orf": "orfandad", "fam": "favor de familiares"}


def load(name: str) -> dict:
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def pct(a: float, b: float) -> float:
    return round((b / a - 1) * 100, 1)


def fetch_wages() -> dict[str, float]:
    """{'2010-T1': euros, …}. Validado: sin saltos absurdos, valores en rango."""
    data = json.loads(inss.get_text(WAGE_URL.format(WAGE_SERIES)))
    out = {}
    for d in data["Data"]:
        q = d["FK_Periodo"] - 18  # el INE codifica T1..T4 como 19..22
        if d.get("Valor") is not None and 1 <= q <= 4:
            out[f"{d['Anyo']}-T{q}"] = float(d["Valor"])
    if len(out) < 40:
        raise inss.ValidationError(f"Serie de salarios con muy pocos datos: {len(out)}")
    for k, v in out.items():
        if not 1000 <= v <= 5000:
            raise inss.ValidationError(f"Salario fuera de rango en {k}: {v}")
    return dict(sorted(out.items()))


def fetch_bde() -> dict[str, dict[str, float]]:
    """{'2026-T2': {'deuda': miles €, …}, …} con las series de BDE_SERIES.

    Validado: existen todas las series con su descripción esperada, hay bastantes
    trimestres, los valores están en rango, la deuda no salta de forma absurda,
    deuda neta = deuda − activos y el último dato no tiene más de un año.
    """
    import csv
    import io

    out: dict[str, dict[str, float]] = {}
    for tabla in sorted({t for t, _ in BDE_SERIES}):
        r = inss.session().get(BDE_CSV.format(tabla), timeout=60)
        r.raise_for_status()
        filas = list(csv.reader(io.StringIO(r.content.decode("latin-1"))))
        cab = filas[0]
        for (t, cod), nombre in BDE_SERIES.items():
            if t != tabla:
                continue
            if cod not in cab:
                raise inss.ValidationError(f"Banco de España be{tabla}: falta la serie {cod}")
            j = cab.index(cod)
            desc = filas[3][j]
            if nombre != "pib" and "Seguridad Social" not in desc:
                raise inss.ValidationError(f"be{tabla} {cod} ya no es de la Seguridad Social: {desc}")
            for f in filas[6:]:
                m = f and len(f) > j and f[0].strip().split(" ")
                if not m or len(m) != 2 or m[0] not in TRIM_BDE or not m[1].isdigit():
                    continue
                v = f[j].strip()
                if v in ("", "_"):
                    continue
                out.setdefault(f"{m[1]}-T{TRIM_BDE[m[0]]}", {})[nombre] = float(v)

    completos = {p: d for p, d in sorted(out.items()) if len(d) == len(BDE_SERIES)}
    if len(completos) < 80:
        raise inss.ValidationError(f"Banco de España: pocos trimestres completos ({len(completos)})")
    prev = None
    for p, d in completos.items():
        if not 0 <= d["deuda"] <= 500e6:
            raise inss.ValidationError(f"Deuda de la Seguridad Social fuera de rango en {p}: {d['deuda']}")
        if not 0 <= d["deuda_pib"] <= 30:
            raise inss.ValidationError(f"Deuda de la Seguridad Social (% PIB) fuera de rango en {p}: {d['deuda_pib']}")
        if not -40e6 <= d["saldo"] <= 40e6:
            raise inss.ValidationError(f"Saldo trimestral de la Seguridad Social fuera de rango en {p}: {d['saldo']}")
        if not 300e6 <= d["pib"] <= 5000e6:
            raise inss.ValidationError(f"PIB fuera de rango en {p}: {d['pib']}")
        if abs(d["deuda"] - d["activos"] - d["neta"]) > 0.01 * d["deuda"] + 1000:
            raise inss.ValidationError(f"Deuda neta ≠ deuda − activos en {p}")
        calc_pib = d["deuda"] / d["pib"] * 100
        if abs(calc_pib - d["deuda_pib"]) > 0.3:
            raise inss.ValidationError(f"Deuda/PIB no cuadra en {p}: {calc_pib:.1f} frente a {d['deuda_pib']}")
        if prev and abs(d["deuda"] - completos[prev]["deuda"]) > 30e6:
            raise inss.ValidationError(f"Salto de deuda absurdo entre {prev} y {p}")
        prev = p
    ultimo = list(completos)[-1]
    if int(ultimo[:4]) < datetime.now(timezone.utc).year - 1:
        raise inss.ValidationError(f"Banco de España: el último trimestre ({ultimo}) es demasiado antiguo")
    return completos


def mm(miles: float) -> float:
    """miles de euros → miles de millones de euros, con un decimal."""
    return round(miles / 1e6, 1)


def trim_es(p: str) -> str:
    """'2026-T2' → '2.º trimestre de 2026'"""
    return f"{p[-1]}.º trimestre de {p[:4]}"


# ─── Deuda y déficit de la Seguridad Social ────────────────────────────────────

def tema_deuda_ss(bde: dict) -> tuple[dict, list[str]]:
    P = list(bde)
    ult = P[-1]
    d_ult = bde[ult]
    anyos = sorted({int(p[:4]) for p in P})
    # años completos: los 4 trimestres (el saldo es un flujo trimestral; se suma por año)
    completos = [y for y in anyos if all(f"{y}-T{q}" in bde for q in range(1, 5))]
    anual = {}
    for y in completos:
        saldo = sum(bde[f"{y}-T{q}"]["saldo"] for q in range(1, 5))
        dic = bde[f"{y}-T4"]
        anual[y] = {"saldo": saldo, "saldo_pib": round(saldo / dic["pib"] * 100, 2),
                    "deuda": dic["deuda"], "neta": dic["neta"], "deuda_pib": dic["deuda_pib"]}
    y_fin = completos[-1]
    if DEUDA_SS_BASE not in anual or BASE_YEAR not in anual:
        raise inss.ValidationError("Banco de España: faltan años base para la deuda de la Seguridad Social")
    for y, a in anual.items():
        if not -5 <= a["saldo_pib"] <= 3:
            raise inss.ValidationError(f"Saldo anual de la Seguridad Social fuera de rango en {y}: {a['saldo_pib']} % PIB")
    desde = [y for y in completos if y >= BASE_YEAR]
    con_deficit = [y for y in desde if anual[y]["saldo"] < 0]
    acumulado = sum(anual[y]["saldo"] for y in desde)
    base = anual[DEUDA_SS_BASE]

    cifras = [
        {"id": "deuda_ss_ultima", "texto": f"Deuda de la Seguridad Social ({trim_es(ult)})", "valor": mm(d_ult["deuda"]), "unidad": "miles de millones de €", "fuente": SRC_BDE},
        {"id": "deuda_ss_pib_ultima", "texto": f"Deuda de la Seguridad Social en % del PIB ({trim_es(ult)})", "valor": d_ult["deuda_pib"], "unidad": "% del PIB", "fuente": SRC_BDE},
        {"id": "deuda_ss_base", "texto": f"Deuda de la Seguridad Social a final de {DEUDA_SS_BASE}", "valor": mm(base["deuda"]), "unidad": "miles de millones de €", "fuente": SRC_BDE},
        {"id": "deuda_ss_veces_base", "texto": f"Veces que se ha multiplicado la deuda de la Seguridad Social desde final de {DEUDA_SS_BASE} ({trim_es(ult)})", "valor": round(d_ult["deuda"] / base["deuda"], 1), "unidad": "veces", "fuente": f"{SRC_BDE}; cálculo propio"},
        {"id": "deuda_ss_neta_ultima", "texto": f"Deuda de la Seguridad Social neta de sus activos frente a otras AAPP ({trim_es(ult)})", "valor": mm(d_ult["neta"]), "unidad": "miles de millones de €", "fuente": SRC_BDE},
        {"id": "activos_ss_ultimo", "texto": f"Activos financieros de la Seguridad Social frente a otras AAPP ({trim_es(ult)})", "valor": mm(d_ult["activos"]), "unidad": "miles de millones de €", "fuente": SRC_BDE},
        {"id": "saldo_ss_ultimo_anyo", "texto": f"Saldo de la Seguridad Social en {y_fin} (negativo = déficit)", "valor": mm(anual[y_fin]["saldo"]), "unidad": "miles de millones de €", "fuente": f"{SRC_BDE}; suma de los 4 trimestres"},
        {"id": "saldo_ss_pib_ultimo_anyo", "texto": f"Saldo de la Seguridad Social en {y_fin}, % del PIB (negativo = déficit)", "valor": round(anual[y_fin]["saldo_pib"], 1), "unidad": "% del PIB", "fuente": f"{SRC_BDE}; cálculo propio"},
        {"id": "anyos_deficit_ss", "texto": f"Años con déficit de la Seguridad Social entre {desde[0]} y {y_fin}", "valor": len(con_deficit), "unidad": f"de {len(desde)}", "detalle": con_deficit, "fuente": SRC_BDE},
        {"id": "saldo_ss_acumulado", "texto": f"Saldo acumulado de la Seguridad Social {desde[0]}–{y_fin} (negativo = déficit)", "valor": mm(acumulado), "unidad": "miles de millones de €", "fuente": f"{SRC_BDE}; cálculo propio"},
    ]

    # Gráfico 1: deuda bruta y neta a fin de año (y el último trimestre si el año no está cerrado)
    g1 = GRAF / "seguridad_social_deuda.png"
    puntos = [(str(y), anual[y]) for y in range(2007, y_fin + 1) if y in anual]
    if ult != f"{y_fin}-T4":
        puntos.append((f"{ult[-2:]} {ult[:4]}", {"deuda": d_ult["deuda"], "neta": d_ult["neta"]}))
    xs = list(range(len(puntos)))
    bruta = [mm(a["deuda"]) for _, a in puntos]
    neta = [mm(a["neta"]) for _, a in puntos]
    fig, ax = estilo.figura(f"Deuda de la Seguridad Social (miles de millones de €). España {puntos[0][0]}-{puntos[-1][0][-4:]}")
    ax.bar(xs, bruta, color=[AZUL] * (len(xs) - 1) + [ROJO], width=0.65, label="Deuda (PDE)")
    ax.plot(xs, neta, color=NARANJA, lw=2.6, marker="o", ms=5, label="Deuda neta de activos frente a otras AAPP")
    for x, v in zip(xs, bruta):
        ax.text(x, v + max(bruta) * 0.015, num_es(v, 0), ha="center", fontsize=10.5)
    ax.axhline(0, color="#7F7F7F", lw=1)
    ax.set_xticks(xs, [e for e, _ in puntos], rotation=45, ha="right")
    ax.grid(axis="x", visible=False)
    estilo.eje_es(ax, 0)
    ax.legend(loc="upper left")
    estilo.guardar(fig, g1, f"{SRC_BDE}, tabla 11.6. Datos a 31 de diciembre de cada año"
                   + (f" y al {trim_es(ult)}" if ult != f"{y_fin}-T4" else ""))

    # Gráfico 2: saldo anual en % del PIB
    g2 = GRAF / "seguridad_social_deficit_pib.png"
    ys_ = [y for y in completos if y >= 2007]
    vs = [round(anual[y]["saldo_pib"], 1) for y in ys_]
    fig, ax = estilo.figura(f"Saldo de la Seguridad Social (% del PIB; negativo = déficit). España {ys_[0]}-{ys_[-1]}")
    ax.bar(ys_, vs, color=[VERDE if v >= 0 else ROJO for v in vs], width=0.65)
    for x, v in zip(ys_, vs):
        ax.text(x, v + (0.04 if v >= 0 else -0.04), num_es(v, 1), ha="center", va="bottom" if v >= 0 else "top", fontsize=10.5)
    ax.axhline(0, color="#7F7F7F", lw=1)
    ax.set_xticks(ys_)
    ax.tick_params(axis="x", rotation=45)
    ax.set_ylim(min(vs) * 1.25 if min(vs) < 0 else -0.2, max(max(vs) * 1.4, 0.3))
    estilo.eje_es(ax, 1, " %")
    estilo.guardar(fig, g2, f"{SRC_BDE}, tablas 11.3 y 11.1 (PIB). Suma de los 4 trimestres de cada año")

    return {
        "id": "deuda_seguridad_social",
        "titulo": "Deuda y déficit de la Seguridad Social",
        "pregunta": "¿Se están pagando las pensiones con deuda?",
        "cifras": cifras,
        "serie_anual": [{"anyo": y, "deuda_mm": mm(a["deuda"]), "deuda_neta_mm": mm(a["neta"]),
                         "deuda_pib": a["deuda_pib"], "saldo_mm": mm(a["saldo"]),
                         "saldo_pib": round(a["saldo_pib"], 1)} for y, a in anual.items() if y >= 2007],
        "graficos": [g1.name, g2.name],
        "advertencias": [
            "La deuda de la Seguridad Social es, sobre todo, préstamos del Estado. En la deuda pública total de España (la que se compara con la UE) se consolida: no se suma otra vez.",
            "La deuda neta resta lo que la Seguridad Social tiene invertido en deuda de otras Administraciones (como el Fondo de Reserva). Por eso fue negativa durante años: tenía más activos que deudas.",
            "El saldo es el de contabilidad nacional (SEC 2010): las transferencias del Estado cuentan como ingresos. No mide cuánto del gasto en pensiones no cubren las cotizaciones; eso es otro dato que el analista todavía no tiene.",
            "El saldo trimestral tiene mucha estacionalidad (pagas extra), por eso solo se usan años completos.",
            "Datos del Protocolo de Déficit Excesivo; el Banco de España los revisa a veces hacia atrás.",
        ],
        "fuentes": [
            {"nombre": f"{SRC_BDE}, tabla 11.6 (deuda por subsectores)", "url": BDE_CSV.format("1106")},
            {"nombre": f"{SRC_BDE}, tabla 11.7 (deuda en % del PIB)", "url": BDE_CSV.format("1107")},
            {"nombre": f"{SRC_BDE}, tabla 11.3 (capacidad o necesidad de financiación)", "url": BDE_CSV.format("1103")},
            {"nombre": "Banco de España, estadísticas de Administraciones Públicas", "url": BDE_WEB},
        ],
    }, [g1.name, g2.name]


# ─── Pensiones frente a salarios reales ────────────────────────────────────────

def tema_salarios(hist: dict, wages: dict) -> tuple[dict, list[str]]:
    periods, media = hist["periodos"], hist["nacional"]["total"]["media"]
    ipc = hist["ipc"]["valores"]
    by_year: dict[int, dict] = {}
    for p, m, i in zip(periods, media, ipc):
        y = int(p[:4])
        by_year.setdefault(y, {"pens": [], "ipc": []})
        if m is not None:
            by_year[y]["pens"].append(m)
        if i is not None:
            by_year[y]["ipc"].append(i)
    for k, v in wages.items():
        y = int(k[:4])
        by_year.setdefault(y, {"pens": [], "ipc": []}).setdefault("sal", []).append(v)

    years = [y for y in sorted(by_year) if y >= BASE_YEAR and len(by_year[y]["pens"]) == 12
             and len(by_year[y]["ipc"]) == 12 and len(by_year[y].get("sal", [])) == 4]
    if BASE_YEAR not in years or len(years) < 5:
        raise inss.ValidationError(f"Años completos insuficientes para comparar: {years}")
    rows = []
    for y in years:
        d = by_year[y]
        rows.append({"anyo": y, "pension_media": round(mean(d["pens"]), 2),
                     "salario_medio": round(mean(d["sal"]), 2), "ipc": round(mean(d["ipc"]), 3)})
    b = rows[0]
    for r in rows:
        r["pension_real_idx"] = round(r["pension_media"] / r["ipc"] / (b["pension_media"] / b["ipc"]) * 100, 1)
        r["salario_real_idx"] = round(r["salario_medio"] / r["ipc"] / (b["salario_medio"] / b["ipc"]) * 100, 1)
        r["ratio_pension_salario"] = round(r["pension_media"] / r["salario_medio"] * 100, 1)
    last = rows[-1]
    gana = [r["anyo"] for prev, r in zip(rows, rows[1:])
            if r["pension_real_idx"] / prev["pension_real_idx"] > r["salario_real_idx"] / prev["salario_real_idx"]]

    y0, y1 = b["anyo"], last["anyo"]
    cifras = [
        {"id": "pension_real_acum", "texto": f"Pensión media real {y0}–{y1}", "valor": round(last["pension_real_idx"] - 100, 1), "unidad": "%", "fuente": f"{SRC_PENS}; {SRC_IPC}"},
        {"id": "salario_real_acum", "texto": f"Salario medio real {y0}–{y1}", "valor": round(last["salario_real_idx"] - 100, 1), "unidad": "%", "fuente": f"{WAGE_INFO['fuente']}; {SRC_IPC}"},
        {"id": "ratio_inicio", "texto": f"Pensión media / salario medio en {y0}", "valor": b["ratio_pension_salario"], "unidad": "%", "fuente": f"{SRC_PENS}; {WAGE_INFO['fuente']}"},
        {"id": "ratio_fin", "texto": f"Pensión media / salario medio en {y1}", "valor": last["ratio_pension_salario"], "unidad": "%", "fuente": f"{SRC_PENS}; {WAGE_INFO['fuente']}"},
        {"id": "anyos_pension_gana", "texto": f"Años entre {y0 + 1} y {y1} en que la pensión media real creció más que el salario real", "valor": len(gana), "unidad": f"de {len(rows) - 1}", "detalle": gana, "fuente": "Cálculo propio"},
        {"id": "pension_media_nominal_fin", "texto": f"Pensión media mensual (media de {y1})", "valor": last["pension_media"], "unidad": "€", "fuente": SRC_PENS},
        {"id": "salario_medio_nominal_fin", "texto": f"Coste salarial medio por trabajador y mes (media de {y1})", "valor": last["salario_medio"], "unidad": "€", "fuente": WAGE_INFO["fuente"]},
    ]

    # Gráfico 1: índices reales
    g1 = GRAF / "pensiones_vs_salarios_real_indice.png"
    fig, ax = estilo.figura(f"Pensión media vs salario medio, en términos reales ({y0} = 100). España {y0}-{y1}")
    xs = [r["anyo"] for r in rows]
    ax.plot(xs, [r["pension_real_idx"] for r in rows], color=ROJO, lw=3, marker="o", ms=5, label="Pensión media real")
    ax.plot(xs, [r["salario_real_idx"] for r in rows], color=AZUL, lw=3, marker="o", ms=5, label="Salario medio real")
    ax.axhline(100, color="#7F7F7F", lw=1, ls="--")
    for key, col in (("pension_real_idx", ROJO), ("salario_real_idx", AZUL)):
        ax.annotate(num_es(rows[-1][key], 1), (xs[-1], rows[-1][key]), xytext=(8, 0), textcoords="offset points",
                    color=col, fontweight="bold", va="center")
    ax.set_xticks(xs)
    ax.tick_params(axis="x", rotation=0)
    estilo.eje_es(ax, 0)
    ax.set_ylabel(f"Índice, {y0} = 100 (deflactado con IPC)")
    ax.legend(loc="upper left", ncols=2)
    estilo.guardar(fig, g1, f"{SRC_PENS}; {WAGE_INFO['fuente']} (coste salarial total por trabajador y mes); {SRC_IPC}")

    # Gráfico 2: pensión media como % del salario medio
    g2 = GRAF / "pension_como_porcentaje_del_salario.png"
    fig, ax = estilo.figura(f"Pensión media como % del salario medio. España {y0}-{y1}")
    ys = [r["ratio_pension_salario"] for r in rows]
    ax.bar(xs, ys, color=[VERDE] * (len(xs) - 1) + [ROJO], width=0.65)
    for x, v in zip(xs, ys):
        ax.text(x, v + 0.6, num_es(v, 1), ha="center", fontsize=11)
    ax.set_xticks(xs)
    ax.set_ylim(0, max(ys) * 1.15)
    estilo.eje_es(ax, 0, " %")
    estilo.guardar(fig, g2, f"{SRC_PENS}; {WAGE_INFO['fuente']}")

    tema = {
        "id": "pensiones_vs_salarios",
        "titulo": "Pensiones frente a salarios reales",
        "pregunta": "¿Han ganado o perdido poder adquisitivo las pensiones frente a los salarios?",
        "cifras": cifras,
        "serie_anual": rows,
        "graficos": [g1.name, g2.name],
        "advertencias": [
            "La pensión media no es la revalorización: sube también porque las pensiones nuevas son más altas que las que se dan de baja (efecto sustitución). No describe lo que le pasa a un pensionista concreto.",
            "El salario es el coste salarial total por trabajador asalariado y mes (ETCL): incluye pagas extra prorrateadas y no incluye a los autónomos.",
            "La pensión media es por pensión (no por pensionista) y en 14 pagas; el salario, por mes en 12. Por eso el cociente pensión/salario sirve para ver la tendencia, no como tasa de sustitución.",
            f"Se comparan medias anuales de años completos ({y0}-{y1}).",
        ],
        "fuentes": [
            {"nombre": SRC_PENS, "url": inss.PAGE_HISTORY},
            {"nombre": f"{WAGE_INFO['fuente']} — {WAGE_INFO['nombre']} ({WAGE_SERIES})", "url": WAGE_INFO["url"]},
            {"nombre": f"{SRC_IPC} ({inss.IPC_SERIES})", "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=50902"},
        ],
    }
    return tema, [g1.name, g2.name]


# ─── Novedades del último mes ──────────────────────────────────────────────────

def tema_novedades(hist: dict) -> tuple[dict, list[str]]:
    P = hist["periodos"]
    ipc = hist["ipc"]["valores"]
    last = max(i for i, v in enumerate(hist["nacional"]["total"]["media"]) if v is not None)
    prev, yago = last - 1, last - 12
    nat = hist["nacional"]["total"]
    real = lambda i, j, s: pct(s[i] / ipc[i], s[j] / ipc[j]) if ipc[i] and ipc[j] else None

    cifras = [
        {"id": "media_ultimo_mes", "texto": f"Pensión media del sistema ({P[last]})", "valor": nat["media"][last], "unidad": "€/mes", "fuente": SRC_PENS},
        {"id": "num_pensiones", "texto": f"Número de pensiones ({P[last]})", "valor": nat["num"][last], "unidad": "pensiones", "fuente": SRC_PENS},
        {"id": "var_mensual_num", "texto": f"Pensiones nuevas netas en el último mes ({P[prev]} → {P[last]})", "valor": nat["num"][last] - nat["num"][prev], "unidad": "pensiones", "fuente": SRC_PENS},
        {"id": "var_interanual_media_nominal", "texto": f"Variación interanual de la pensión media, nominal ({P[yago]} → {P[last]})", "valor": pct(nat["media"][yago], nat["media"][last]), "unidad": "%", "fuente": SRC_PENS},
        {"id": "var_interanual_media_real", "texto": f"Variación interanual de la pensión media, real ({P[yago]} → {P[last]})", "valor": real(yago, last, nat["media"]), "unidad": "%", "fuente": f"{SRC_PENS}; {SRC_IPC}"},
        {"id": "var_interanual_num", "texto": f"Variación interanual del número de pensiones ({P[yago]} → {P[last]})", "valor": pct(nat["num"][yago], nat["num"][last]), "unidad": "%", "fuente": SRC_PENS},
    ]
    # provincias: mayor y menor subida interanual de la pensión media
    var = []
    for c, s in hist["provincias"].items():
        a, b = s["total"]["media"][yago], s["total"]["media"][last]
        if a and b:
            var.append((pct(a, b), inss.PROVINCES[c]))
    var.sort()
    cifras.append({"id": "prov_mas_sube", "texto": "Provincia donde más sube la pensión media en un año", "valor": var[-1][0], "unidad": "%", "detalle": var[-1][1], "fuente": SRC_PENS})
    cifras.append({"id": "prov_menos_sube", "texto": "Provincia donde menos sube la pensión media en un año", "valor": var[0][0], "unidad": "%", "detalle": var[0][1], "fuente": SRC_PENS})

    # por tipo de pensión
    for t in ("jub", "viu", "ip"):
        s = hist["nacional"][t]
        cifras.append({"id": f"var_interanual_real_{t}", "texto": f"Variación interanual real de la pensión media de {TIPO_NOMBRE[t]}", "valor": real(yago, last, s["media"]), "unidad": "%", "fuente": f"{SRC_PENS}; {SRC_IPC}"})

    # Gráfico 3: pensión media nominal vs real, mensual
    g3 = GRAF / "pension_media_nominal_vs_real.png"
    base = max(i for i, v in enumerate(ipc) if v is not None)
    first = next(i for i, v in enumerate(nat["media"]) if v is not None)
    xs = list(range(first, last + 1))
    nom = [nat["media"][i] for i in xs]
    rea = [nat["media"][i] * ipc[base] / ipc[i] if ipc[i] else None for i in xs]
    fig, ax = estilo.figura(f"Pensión media nominal vs real (€/mes, euros de {P[base]}). España {P[first][:4]}-{P[last][:4]}")
    ax.plot(xs, nom, color=ROJO, lw=2.6, label="Nominal")
    ax.plot(xs, rea, color=VERDE, lw=2.6, label=f"Real (euros de {P[base]})")
    ticks = [i for i in xs if P[i].endswith("-01") and int(P[i][:4]) % 2 == 0]
    ax.set_xticks(ticks, [P[i][:4] for i in ticks])
    estilo.eje_es(ax, 0, " €")
    ax.legend(loc="upper left", ncols=2)
    estilo.guardar(fig, g3, f"{SRC_PENS}; {SRC_IPC}")

    # Gráfico 4: ranking provincial, variación real desde 2010
    g4 = GRAF / "provincias_variacion_real_desde_2010.png"
    i0 = P.index(f"{BASE_YEAR}-01")
    rk = []
    for c, s in hist["provincias"].items():
        a, b = s["total"]["media"][i0], s["total"]["media"][last]
        if a and b and ipc[i0] and ipc[last]:
            rk.append((pct(a / ipc[i0], b / ipc[last]), inss.PROVINCES[c]))
    rk.sort()
    fig, ax = estilo.figura(f"Variación real de la pensión media por provincia (%). {P[i0]} a {P[last]}", alto=13)
    ax.grid(axis="x", color=estilo.GRIS_REJILLA)
    ax.grid(axis="y", visible=False)
    nac = pct(nat["media"][i0] / ipc[i0], nat["media"][last] / ipc[last])
    ax.barh([n for _, n in rk], [v for v, _ in rk], color=[ROJO if v < nac else AZUL for v, _ in rk], height=0.7)
    ax.axvline(nac, color=NARANJA, lw=2, ls="--", label=f"España: {num_es(nac, 1)} %")
    ax.tick_params(axis="y", labelsize=10)
    estilo.eje_es(ax, 0, " %", eje="x")
    ax.legend(loc="lower right")
    ax.margins(y=0.005)
    estilo.guardar(fig, g4, f"{SRC_PENS}; {SRC_IPC}")
    cifras.append({"id": "real_desde_2010_nacional", "texto": f"Variación real de la pensión media en España, {P[i0]} a {P[last]}", "valor": nac, "unidad": "%", "fuente": f"{SRC_PENS}; {SRC_IPC}"})
    cifras.append({"id": "real_desde_2010_max", "texto": "Provincia con mayor subida real desde 2010", "valor": rk[-1][0], "unidad": "%", "detalle": rk[-1][1], "fuente": f"{SRC_PENS}; {SRC_IPC}"})
    cifras.append({"id": "real_desde_2010_min", "texto": "Provincia con menor subida real desde 2010", "valor": rk[0][0], "unidad": "%", "detalle": rk[0][1], "fuente": f"{SRC_PENS}; {SRC_IPC}"})

    return {
        "id": "novedades_mes",
        "titulo": f"Pensiones: lo nuevo de {P[last]}",
        "pregunta": "¿Qué ha cambiado en el último dato publicado?",
        "cifras": cifras,
        "graficos": [g3.name, g4.name],
        "advertencias": ["La pensión media sube también por efecto sustitución (altas con pensiones más altas que las bajas)."],
        "fuentes": [{"nombre": SRC_PENS, "url": inss.PAGE_HISTORY},
                    {"nombre": f"{SRC_IPC} ({inss.IPC_SERIES})", "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=50902"}],
    }, [g3.name, g4.name]


# ─── Desigualdad ───────────────────────────────────────────────────────────────

def tema_desigualdad(d: dict) -> tuple[dict, list[str]]:
    S = d["por_sexo"]
    smi = sorted(d["smi"]["provincias"].values(), key=lambda b: b["bajo_smi_pct"])
    cifras = [
        {"id": "gini", "texto": "Índice de Gini de los pensionistas (aprox.)", "valor": S["ambos"]["gini"], "unidad": "", "fuente": SRC_PTAS},
        {"id": "brecha_genero", "texto": "Brecha de género en el importe medio por pensionista", "valor": round(d["brecha_genero"] * 100, 1), "unidad": "%", "fuente": SRC_PTAS},
        {"id": "mediana", "texto": "Pensionista mediano (aprox.)", "valor": S["ambos"]["percentiles"]["p50"], "unidad": "€/mes", "fuente": SRC_PTAS},
        {"id": "mediana_mujeres", "texto": "Pensionista mediana, mujeres (aprox.)", "valor": S["mujeres"]["percentiles"]["p50"], "unidad": "€/mes", "fuente": SRC_PTAS},
        {"id": "mediana_hombres", "texto": "Pensionista mediano, hombres (aprox.)", "valor": S["hombres"]["percentiles"]["p50"], "unidad": "€/mes", "fuente": SRC_PTAS},
        {"id": "p90_p10", "texto": "P90/P10", "valor": S["ambos"]["p90_p10"], "unidad": "veces", "fuente": SRC_PTAS},
        {"id": "cuota_50_inferior", "texto": "Parte del importe total que cobra el 50 % que menos cobra", "valor": round(S["ambos"]["cuota_50_inferior"] * 100, 1), "unidad": "%", "fuente": SRC_PTAS},
        {"id": "cuota_10_superior", "texto": "Parte del importe total que cobra el 10 % que más cobra", "valor": round(S["ambos"]["cuota_10_superior"] * 100, 1), "unidad": "%", "fuente": SRC_PTAS},
        {"id": "bajo_smi", "texto": "Pensionistas por debajo del SMI", "valor": round(d["smi"]["nacional"]["bajo_smi_pct"] * 100, 1), "unidad": "%", "fuente": SRC_PTAS},
        {"id": "bajo_smi_max", "texto": "Provincia con más pensionistas bajo el SMI", "valor": round(smi[-1]["bajo_smi_pct"] * 100, 1), "unidad": "%", "detalle": smi[-1]["nombre"], "fuente": SRC_PTAS},
        {"id": "bajo_smi_min", "texto": "Provincia con menos pensionistas bajo el SMI", "valor": round(smi[0]["bajo_smi_pct"] * 100, 1), "unidad": "%", "detalle": smi[0]["nombre"], "fuente": SRC_PTAS},
        {"id": "minimos", "texto": "Pensionistas con complemento a mínimos", "valor": round(d["minimos_pct"]["ambos"] * 100, 1), "unidad": "%", "fuente": SRC_PTAS},
    ]
    g5 = GRAF / "pensionistas_por_tramo_mujeres_hombres.png"
    T = d["tramos_100"]
    fig, ax = estilo.figura(f"Pensionistas por cuantía mensual, mujeres y hombres. España, {d['periodo']}")
    xs = range(len(T))
    ax.bar(xs, [t["mujeres"] for t in T], color=ROJO, width=0.75, label="Mujeres")
    ax.bar(xs, [t["hombres"] for t in T], bottom=[t["mujeres"] for t in T], color=NARANJA, width=0.75, label="Hombres")
    ax.set_xticks(list(xs), [t["etiqueta"] for t in T], rotation=60, ha="right", fontsize=9.5)
    estilo.eje_es(ax, 0)
    ax.set_ylabel("Pensionistas")
    ax.legend(loc="upper right")
    estilo.guardar(fig, g5, f"{SRC_PTAS} ({d['fuente']['fichero']})")
    return {
        "id": "desigualdad",
        "titulo": "Desigualdad entre pensionistas",
        "pregunta": "¿Cómo se reparte el dinero de las pensiones entre las personas que las cobran?",
        "cifras": cifras,
        "graficos": [g5.name],
        "advertencias": [
            "Cuenta personas (pensionistas), no pensiones: el importe es la suma de todas las pensiones de cada persona.",
            "Gini, percentiles y cuotas son aproximados: se calculan a partir de tramos de cuantía.",
            "Estar por debajo del SMI no implica pobreza: muchos pensionistas tienen otros ingresos o pensiones de viudedad/orfandad que no sustituyen un salario.",
            "La brecha de género por pensionista (que incluye viudedad) es menor que la de las pensiones de jubilación; no mezclar con cifras de otras fuentes que miden otra cosa.",
        ],
        "fuentes": [{"nombre": SRC_PTAS, "url": inss.PAGE_PTAS}],
    }, [g5.name]


def main() -> int:
    GRAF.mkdir(parents=True, exist_ok=True)
    hist, desi, pens = load("historico.json"), load("desigualdad.json"), load("pensiones.json")
    try:
        wages = fetch_wages()
    except Exception as e:
        print(f"ERROR al obtener los salarios del INE: {e}", file=sys.stderr)
        return 2

    # La deuda de la Seguridad Social es un tema más: si el Banco de España falla, se avisa
    # en hallazgos.json («temas_sin_datos») y el resto del analista sigue.
    calculos = [(tema_novedades, (hist,)), (tema_salarios, (hist, wages)), (tema_desigualdad, (desi,))]
    sin_datos, bde = [], None
    try:
        bde = fetch_bde()
        calculos.append((tema_deuda_ss, (bde,)))
    except Exception as e:
        print(f"AVISO: sin datos del Banco de España, se omite la deuda de la Seguridad Social: {e}", file=sys.stderr)
        sin_datos.append({"id": "deuda_seguridad_social", "motivo": f"{type(e).__name__}: {e}"[:300]})

    temas, graficos = [], []
    for fn, args in calculos:
        t, g = fn(*args)
        temas.append(t)
        graficos += g

    # limpia gráficos antiguos que ya no se generan
    for f in GRAF.glob("*.png"):
        if f.name not in graficos:
            f.unlink()

    doc = {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "datos": {"pensiones": pens["periodo"], "pensionistas": desi["periodo"],
                  "salarios_ultimo_trimestre": list(wages)[-1],
                  "seguridad_social_ultimo_trimestre": list(bde)[-1] if bde else None},
        "web": "https://davidaguilar13.github.io/datospensiones.github.io/",
        "temas": temas,
        "temas_sin_datos": sin_datos,
    }
    (OUT / "hallazgos.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Escrito analisis/hallazgos.json: {len(temas)} temas, {sum(len(t['cifras']) for t in temas)} cifras, "
          f"{len(graficos)} gráficos")
    for t in temas:
        print(f"\n## {t['titulo']}")
        for c in t["cifras"]:
            det = f" ({c['detalle']})" if "detalle" in c and not isinstance(c["detalle"], list) else ""
            print(f"  - {c['texto']}: {c['valor']} {c['unidad']}{det}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
