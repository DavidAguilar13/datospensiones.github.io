"""Construye data/historico.json con la serie mensual de pensiones desde 2010:
nacional y por provincia, por tipo de pensión, más el IPC del INE para
calcular la evolución en términos reales.

Recorre el histórico de estadísticas del INSS, descarga cada CA mensual
(se guardan en .cache/inss/ para no repetir descargas), lo lee y lo valida.
Un mes que no pase la validación no entra en la serie: se informa y queda
como hueco.

Uso:
    python scripts/build_history.py
    python scripts/build_history.py --desde 2015-01
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import inss
from inss import CACHE, DATA, TYPE_ORDER, ValidationError

OUT = DATA / "historico.json"


def next_period(p: str) -> str:
    y, m = map(int, p.split("-"))
    return f"{y + 1}-01" if m == 12 else f"{y}-{m + 1:02d}"


def empty_series() -> dict:
    return {t: {"num": [], "media": []} for t in TYPE_ORDER}


def build(months: dict[str, dict], ipc: dict[str, float]) -> dict:
    """months: {periodo: parsed CA}. Devuelve el documento de historico.json."""
    periods = sorted(months)
    # rellena huecos para que el eje temporal sea continuo
    first, last = periods[0], periods[-1]
    y, m = map(int, first.split("-"))
    allp = []
    while f"{y}-{m:02d}" <= last:
        allp.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    nat = empty_series()
    provs = {c: empty_series() for c in inss.PROVINCES}
    for p in allp:
        d = months.get(p)
        for t in TYPE_ORDER:
            nat[t]["num"].append(d["nacional"][t]["num"] if d else None)
            nat[t]["media"].append(d["nacional"][t]["media"] if d else None)
            for c in inss.PROVINCES:
                blk = d["provincias"][c][t] if d else None
                provs[c][t]["num"].append(blk["num"] if blk else None)
                provs[c][t]["media"].append(blk["media"] if blk else None)

    return {
        "periodos": allp,
        "huecos": [p for p in allp if p not in months],
        "fuente": {
            "nombre": "Instituto Nacional de la Seguridad Social (INSS)",
            "url": inss.PAGE_HISTORY,
            "descripcion": "Pensiones contributivas en vigor por provincia (ficheros CA mensuales), total sistema",
        },
        "ipc": {
            "nombre": "IPC. Índice general nacional",
            "fuente": "Instituto Nacional de Estadística (INE)",
            "serie": inss.IPC_SERIES,
            "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=50902",
            "valores": [ipc.get(p) for p in allp],
        },
        "nacional": nat,
        "provincias": provs,
    }


def to_parsed(doc: dict) -> dict[str, dict]:
    """Inversa de build(): {periodo: {'nacional':…, 'provincias':…}} (solo meses con datos)."""
    out = {}
    for i, p in enumerate(doc["periodos"]):
        if doc["nacional"]["total"]["num"][i] is None:
            continue
        blk = lambda s: {t: {"num": s[t]["num"][i], "media": s[t]["media"][i]} for t in TYPE_ORDER}
        out[p] = {"nacional": blk(doc["nacional"]),
                  "provincias": {c: blk(s) for c, s in doc["provincias"].items()}}
    return out


def write(doc: dict, path=OUT) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                    encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default="2010-01", help="primer mes (AAAA-MM)")
    args = ap.parse_args()

    print("Buscando ficheros en el histórico del INSS…")
    links = {p: v for p, v in inss.history_ca_links().items() if p >= args.desde}
    # el último mes publicado puede no estar aún en el histórico
    try:
        p, name, url = inss.latest_link(inss.PAGE_CA, "CA")
        links.setdefault(p, (name, url))
    except Exception as e:
        print(f"Aviso: no se ha podido consultar el último mes: {e}")
    print(f"{len(links)} meses encontrados ({min(links)} a {max(links)})")

    months, failed = {}, {}
    prev = None
    for period, (name, url) in sorted(links.items()):
        dest = CACHE / f"CA_{period}.xlsx"
        try:
            if not dest.exists():
                inss.download(url, dest)
                time.sleep(0.5)  # sin prisa: no saturar el servidor
            parsed = inss.parse_ca(dest)
            got = inss.period_of(parsed)
            if got != period:
                raise ValidationError(f"el fichero {name} dice ser de {got}")
            # la comparación con el mes anterior solo tiene sentido si es el inmediatamente anterior
            consecutive = prev is not None and next_period(inss.period_of(prev)) == period
            inss.validate_ca(parsed, prev["provincias"] if consecutive else None)
        except ValidationError as e:
            failed[period] = str(e)
            print(f"  {period} ✗ {e}")
            continue
        except Exception as e:
            failed[period] = f"descarga/lectura: {e}"
            print(f"  {period} ✗ descarga/lectura: {e}")
            continue
        months[period] = parsed
        prev = parsed
        print(f"  {period} ✓ {parsed['nacional']['total']['num']:,} pensiones, "
              f"media {parsed['nacional']['total']['media']} €")

    if len(months) < 12:
        print("ERROR: muy pocos meses válidos; no se escribe nada.", file=sys.stderr)
        return 1

    print("Descargando el IPC del INE…")
    ipc = inss.fetch_ipc()
    doc = build({p: {"nacional": inss.clean_block(d["nacional"]),
                     "provincias": {c: inss.clean_block(b) for c, b in d["provincias"].items()}}
                 for p, d in months.items()}, ipc)
    write(doc)
    size = OUT.stat().st_size
    print(f"\nEscrito {OUT.relative_to(inss.ROOT)} ({size / 1024:.0f} KB): "
          f"{len(months)} meses válidos, {len(doc['huecos'])} huecos, {len(failed)} descartados")
    for p, e in failed.items():
        print(f"  descartado {p}: {' '.join(e.split())[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
