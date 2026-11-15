"""Actualiza los datos de la web con lo último publicado por el INSS y el INE.

  - data/pensiones.json   último mes, por provincia (fichero CAaaaamm.xlsx)
  - data/historico.json   serie mensual desde 2010 + IPC (añade el mes nuevo)
  - data/desigualdad.json pensionistas por tramos de cuantía (fichero PTASaaaamm.xlsx)

Todo se valida antes de escribir. Si algo falla, no se escribe nada.

Uso:
    python scripts/update_data.py             # descarga lo último y actualiza si hay novedades
    python scripts/update_data.py --dry-run   # valida pero no escribe
    python scripts/update_data.py --ca CA202610.xlsx --ptas PTAS202610.xlsx   # ficheros locales
    python scripts/update_data.py --force     # rehace aunque no haya mes nuevo

Códigos de salida:
    0  datos actualizados, o ya estaban al día
    1  la validación ha fallado: no se escribe nada
    2  no se ha podido descargar o leer algún fichero
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import build_history
import inss
from inss import DATA, ValidationError

PENSIONES = DATA / "pensiones.json"
HISTORICO = DATA / "historico.json"
DESIGUALDAD = DATA / "desigualdad.json"


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def write_json(path: Path, doc: dict, compact=False) -> None:
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) if compact \
        else json.dumps(doc, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def fetch(page: str, prefix: str, local: Path | None, current: str | None, force: bool):
    """Devuelve (ruta, nombre) del fichero a procesar, o None si no hay nada nuevo."""
    if local:
        return local, local.name
    period, name, url = inss.latest_link(page, prefix)
    print(f"Último {prefix} publicado: {name}")
    if current and current >= period and not force:
        print(f"  ya está al día ({current})")
        return None
    dest = Path(tempfile.mkdtemp(prefix="inss_")) / name
    inss.download(url, dest)
    return dest, name


def pensiones_doc(parsed: dict, filename: str) -> dict:
    f = parsed["fecha"]
    return {
        "periodo": inss.period_of(parsed),
        "fecha_datos": f.isoformat(),
        "fuente": {
            "nombre": "Instituto Nacional de la Seguridad Social (INSS)",
            "url": "https://www.seg-social.es",
            "fichero": filename,
            "hoja": inss.SHEET,
        },
        "nacional": inss.clean_block(parsed["nacional"]),
        "provincias": {c: {"nombre": inss.PROVINCES[c], **inss.clean_block(parsed["provincias"][c])}
                       for c in sorted(parsed["provincias"])},
    }


def desigualdad_doc(p: dict, filename: str) -> dict:
    ineq = inss.inequality(p)
    sexes = ("ambos", "mujeres", "hombres")
    return {
        "periodo": f"{p['fecha'].year}-{p['fecha'].month:02d}",
        "fecha_datos": p["fecha"].isoformat(),
        "fuente": {
            "nombre": "Instituto Nacional de la Seguridad Social (INSS)",
            "url": "https://www.seg-social.es",
            "fichero": filename,
            "hojas": [inss.SUMMARY_SHEET, inss.BRACKET_SHEET],
        },
        "pensionistas": {k: int(p["pensionistas"][k]) for k in sexes},
        "importe_medio": {k: round(p["importe_medio"][k], 2) for k in sexes},
        "minimos": {k: int(p["minimos"][k]) for k in sexes},
        "minimos_pct": {k: round(p["minimos_pct"][k], 4) for k in sexes},
        "brecha_genero": round(1 - p["importe_medio"]["mujeres"] / p["importe_medio"]["hombres"], 4),
        "gini": ineq["gini"],
        "mediana_tramo": ineq["mediana_tramo"],
        "tramos": [{k: t[k] for k in ("etiqueta", "desde", "hasta", "ambos", "mujeres", "hombres")}
                   for t in p["tramos"]],
        "tramos_100": inss.bins_100(p["tramos"]),
        "por_sexo": {k: inss.distribution(p["tramos"], k, p["pensionistas"][k], p["importe_medio"][k])
                     for k in sexes},
        "smi": {
            "nacional": p["provincias"]["nacional"],
            "provincias": {c: {"nombre": inss.PROVINCES[c], **b}
                           for c, b in sorted(p["provincias"]["provincias"].items())},
        },
        "nota": "Pensionistas (personas), no pensiones. El importe de cada tramo es la suma de "
                "las pensiones que cobra cada persona. El índice de Gini es aproximado: usa el "
                "punto medio de cada tramo.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ca", type=Path, help="CAaaaamm.xlsx ya descargado")
    ap.add_argument("--ptas", type=Path, help="PTASaaaamm.xlsx ya descargado")
    ap.add_argument("--dry-run", action="store_true", help="valida sin escribir")
    ap.add_argument("--force", action="store_true", help="procesa aunque no haya mes nuevo")
    args = ap.parse_args()

    pens_old, hist_old, desi_old = load(PENSIONES), load(HISTORICO), load(DESIGUALDAD)
    outputs: dict[Path, tuple[dict, bool]] = {}

    try:
        # 1. Pensiones por provincia (CA) + histórico
        got = fetch(inss.PAGE_CA, "CA", args.ca, pens_old and pens_old["periodo"], args.force)
        ipc = inss.fetch_ipc()
        months = build_history.to_parsed(hist_old) if hist_old else {}
        if got:
            parsed = inss.parse_ca(got[0])
            period = inss.period_of(parsed)
            prev_p = max((p for p in months if p < period), default=None)
            consecutive = prev_p and build_history.next_period(prev_p) == period
            inss.validate_ca(parsed, months[prev_p]["provincias"] if consecutive else None, period)
            outputs[PENSIONES] = (pensiones_doc(parsed, got[1]), False)
            months[period] = {"nacional": inss.clean_block(parsed["nacional"]),
                              "provincias": {c: inss.clean_block(b) for c, b in parsed["provincias"].items()}}
            print(f"  CA {period} válido: {parsed['nacional']['total']['num']:,} pensiones, "
                  f"media {parsed['nacional']['total']['media']} €/mes")
        if months:
            hist = build_history.build(months, ipc)
            if hist != hist_old:
                outputs[HISTORICO] = (hist, True)

        # 2. Pensionistas por tramos (PTAS)
        got = fetch(inss.PAGE_PTAS, "PTAS", args.ptas, desi_old and desi_old["periodo"], args.force)
        if got:
            p = inss.parse_ptas(got[0])
            inss.validate_ptas(p)
            doc = desigualdad_doc(p, got[1])
            outputs[DESIGUALDAD] = (doc, False)
            print(f"  PTAS {doc['periodo']} válido: {doc['pensionistas']['ambos']:,} pensionistas, "
                  f"Gini ≈ {doc['gini']}")
    except ValidationError as e:
        print(f"ERROR de validación: {e}", file=sys.stderr)
        print("No se ha escrito nada.", file=sys.stderr)
        return 1
    except Exception as e:  # red, fichero corrupto…
        print(f"ERROR al obtener o leer los datos: {e}", file=sys.stderr)
        return 2

    if not outputs:
        print("Todo al día. Nada que escribir.")
        return 0
    if args.dry_run:
        print("--dry-run: no se escribe nada. Se actualizarían: " +
              ", ".join(p.name for p in outputs))
        return 0
    for path, (doc, compact) in outputs.items():
        write_json(path, doc, compact)
        print(f"Escrito data/{path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
