"""Shared chart style: gold on near-black, Playfair Display / Inter with DejaVu fallback."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

BG, GOLD, TEXT, MUTED = "#111111", "#D4AF37", "#EDEAE2", "#8A8A8A"
GOLD_DIM, LINE = "#8C7526", "#2A2A2A"
IMG = Path(__file__).resolve().parent.parent / "docs" / "img"


def _family(name: str, fallback: str) -> str:
    for f in font_manager.findSystemFonts():
        if name.replace(" ", "") in Path(f).name.replace(" ", "") and "Italic" not in f:
            font_manager.fontManager.addfont(f)
            return name
    return fallback


SERIF = _family("Playfair Display", "DejaVu Serif")
SANS = _family("Inter", "DejaVu Sans")


def style() -> None:
    plt.rcParams.update({
        "font.family": SANS, "figure.facecolor": BG, "axes.facecolor": BG,
        "savefig.facecolor": BG, "axes.edgecolor": LINE, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": MUTED, "text.color": TEXT,
        "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150,
        "axes.grid": True, "grid.color": LINE, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "legend.labelcolor": TEXT,
    })


def title(ax: plt.Axes, text: str, sub: str | None = None) -> None:
    ax.set_title(text, fontfamily=SERIF, fontsize=16, color=TEXT, loc="left", pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=MUTED, va="bottom")
