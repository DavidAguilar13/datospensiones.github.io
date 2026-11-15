"""Estilo de los gráficos del analista, copiado de los gráficos de David
(GRÁFICOS/PNG): título en negrita con unidades y años, rejilla gris horizontal,
rojo / verde / azul oscuro / naranja y un pie con la fuente a la izquierda y
davidaguilar.substack.com a la derecha.

Reglas que se aplican siempre:
- Nunca se suavizan las líneas: se dibujan los datos tal cual.
- Números en formato español (1.234,5).
- Cada gráfico lleva su fuente.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

ROJO = "#C00000"
VERDE = "#548235"
AZUL = "#1F4E79"
AZUL_CLARO = "#4472C4"
NARANJA = "#ED7D31"
GRIS = "#7F7F7F"
GRIS_REJILLA = "#BFBFBF"
FIRMA = "davidaguilar.substack.com"

_PREFERIDAS = ["Lato", "Carlito", "Calibri", "DejaVu Sans"]
_disponibles = {f.name for f in font_manager.fontManager.ttflist}
FUENTE = next((f for f in _PREFERIDAS if f in _disponibles), "DejaVu Sans")

plt.rcParams.update({
    "font.family": FUENTE,
    "font.size": 13,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": GRIS,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRIS_REJILLA,
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "xtick.color": "#262626",
    "ytick.color": "#262626",
    "legend.frameon": False,
    "figure.dpi": 100,
    "savefig.dpi": 200,
})


def num_es(x: float, dec: int = 0) -> str:
    """1234567.8 → '1.234.567,8'"""
    s = f"{x:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def eje_es(ax, dec: int = 0, sufijo: str = "", eje: str = "y") -> None:
    fmt = FuncFormatter(lambda v, _: num_es(v, dec) + sufijo)
    (ax.yaxis if eje == "y" else ax.xaxis).set_major_formatter(fmt)


TITULO_IN = 0.85   # alto reservado arriba para el título (pulgadas)
PIE_IN = 0.75      # alto reservado abajo para el pie (pulgadas)


def figura(titulo: str, ancho: float = 12, alto: float = 7.2):
    fig, ax = plt.subplots(figsize=(ancho, alto))
    fig.suptitle(titulo, fontsize=20, fontweight="bold", y=1 - 0.42 / alto, va="center")
    return fig, ax


def guardar(fig, ruta, fuente: str) -> None:
    """Ajusta márgenes al contenido, añade el pie (fuente + firma) y guarda en PNG."""
    import textwrap

    w, h = fig.get_size_inches()
    texto = f"Fuente: {fuente}. Elaboración propia."
    lineas = textwrap.wrap(texto, width=int(w * 10.5))  # deja sitio a la firma
    pie = PIE_IN + 0.2 * (len(lineas) - 1)
    fig.tight_layout(rect=(0.005, pie / h, 0.995, 1 - TITULO_IN / h))
    fig.add_artist(plt.Line2D([0.01, 0.99], [(pie - 0.12) / h] * 2, color="#D9D9D9", lw=1,
                              transform=fig.transFigure))
    fig.text(0.012, (pie - 0.42) / h, "\n".join(lineas), fontsize=11, color="#595959", va="center",
             linespacing=1.4)
    fig.text(0.988, (pie - 0.42) / h, FIRMA, fontsize=12.5, fontweight="bold", color="#262626",
             ha="right", va="center")
    fig.savefig(ruta, facecolor="white")
    plt.close(fig)
