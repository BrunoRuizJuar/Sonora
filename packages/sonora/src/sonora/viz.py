"""Shared static-figure style for SONORA evidence notebooks (matplotlib).

Colors follow the validated reference categorical palette (fixed order, never cycled):
an entity keeps its color in every figure (e.g. ``tag`` -> slot). Magnitudes use one
sequential hue. Text never wears series colors.
"""
from __future__ import annotations

from pathlib import Path

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
TAG_ORDER = ["pop", "rap", "rock", "rb", "country"]
TAG_COLORS = dict(zip(TAG_ORDER, CATEGORICAL))
SPLIT_ORDER = ["train", "validation", "test"]
SPLIT_COLORS = dict(zip(SPLIT_ORDER, CATEGORICAL[:3]))
SEQUENTIAL = "#2a78d6"
MUTED = "#8a8984"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
SURFACE = "#fcfcfb"
GRID = "#e4e3df"


def apply_style() -> None:
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT_SECONDARY, "axes.titlecolor": TEXT,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 10, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "xtick.color": TEXT_SECONDARY, "ytick.color": TEXT_SECONDARY, "xtick.labelsize": 9,
        "ytick.labelsize": 9, "legend.frameon": False, "legend.fontsize": 9,
        "lines.linewidth": 2.0, "font.size": 10, "figure.dpi": 110, "savefig.dpi": 150,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
    })


def caption(ax, text: str) -> None:
    """Small note under the axes: universe / sample, units and source."""
    ax.annotate(text, xy=(0, -0.2), xycoords="axes fraction", fontsize=8, color=TEXT_SECONDARY,
                ha="left", va="top", wrap=True)


def save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    return path


def thousands():
    """Axis formatter with a thin space as thousands separator (1 336 051)."""
    from matplotlib.ticker import FuncFormatter

    return FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " "))
