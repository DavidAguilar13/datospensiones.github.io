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

    temas, graficos = [], []
    for fn, args in ((tema_novedades, (hist,)), (tema_salarios, (hist, wages)), (tema_desigualdad, (desi,))):
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
                  "salarios_ultimo_trimestre": list(wages)[-1]},
        "web": "https://davidaguilar13.github.io/datospensiones.github.io/",
        "temas": temas,
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
