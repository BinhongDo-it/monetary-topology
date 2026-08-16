"""Figure helpers.

Plain matplotlib, Agg backend, no seaborn. Figures are written to disk rather
than shown, so the experiment scripts run identically in CI and on a laptop.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

# A restrained palette. Layer 1 warm, Layer 2 cool, instrument grey.
COLOR_LAYER1 = "#b3452e"
COLOR_LAYER2 = "#1f5c8b"
COLOR_INSTRUMENT = "#5c5c5c"
COLOR_ACCENT = "#c98a1c"

RC = {
    "figure.dpi": 130,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.6,
    "legend.frameon": False,
    "legend.fontsize": 8.5,
    "lines.linewidth": 1.8,
}


def apply_style() -> None:
    plt.rcParams.update(RC)


def save(fig: plt.Figure, path: Path) -> Path:
    """Write ``fig`` to ``path``, creating parent directories.

    ``metadata={"Software": None}`` suppresses the PNG ``tEXt`` chunk
    matplotlib writes by default, which reads
    ``Software\0Matplotlib version3.11.1, https://matplotlib.org/``.
    `CLAUDE.md`'s generated-files rule 2 forbids library version strings in
    files that are committed, and figures are committed: `.gitignore` says so in
    as many words. Without this, every figure in the repository changes on any
    environment refresh and twelve spurious modifications sit in `git status`
    hiding the real ones, which is how the record drift in `a3_asset_channel`
    and `a6_siphon_cost` stayed unnoticed.

    **The metadata is the cheap half.** Pixel content still depends on the
    matplotlib and freetype versions, because ``savefig.bbox = "tight"`` sizes
    the canvas from rendered text extents, so the load-bearing fix is the pin in
    `requirements.txt` and `pyproject.toml`.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
    return path


def annotate(ax: plt.Axes, text: str, *, loc: str = "lower left") -> None:
    """Attach a short note inside the axes.

    Used to state on the figure itself what the figure does and does not claim,
    so a screenshot separated from the README stays honest.
    """
    positions = {
        "lower left": (0.02, 0.04, "left", "bottom"),
        "lower right": (0.98, 0.04, "right", "bottom"),
        "upper left": (0.02, 0.96, "left", "top"),
        "upper right": (0.98, 0.96, "right", "top"),
        "center left": (0.02, 0.50, "left", "center"),
        "center right": (0.98, 0.50, "right", "center"),
    }
    x, y, ha, va = positions[loc]
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=8,
        color="#404040",
        bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 3},
    )
