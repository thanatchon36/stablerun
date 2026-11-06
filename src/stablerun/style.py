"""House style for every figure: serif font matching the paper (TeX Gyre Pagella when available), light
horizontal grid, thin spines, bold left-aligned panel titles, Okabe-Ito colour-blind-safe palette."""
from __future__ import annotations

import subprocess
from pathlib import Path

import matplotlib
from matplotlib import font_manager

PALETTE = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
           "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7", "grey": "#7F7F7F"}


def _register_pagella() -> str | None:
    try:
        root = subprocess.run(["kpsewhich", "-var-value=TEXMFDIST"], capture_output=True, text=True, timeout=10).stdout.strip()
        files = list((Path(root) / "fonts" / "opentype" / "public" / "tex-gyre").glob("texgyrepagella-*.otf"))
        for f in files:
            font_manager.fontManager.addfont(str(f))
        return "TeX Gyre Pagella" if files else None
    except Exception:
        return None


def apply() -> None:
    fam = _register_pagella()
    serif = ([fam] if fam else []) + ["STIXGeneral", "DejaVu Serif"]
    rc = {
        "font.family": "serif", "font.serif": serif,
        "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 7.5,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.titlelocation": "left", "axes.titleweight": "bold", "axes.titlepad": 6,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
        "axes.edgecolor": "#444444", "axes.labelcolor": "#222222",
        "xtick.color": "#444444", "ytick.color": "#444444", "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 3, "ytick.major.size": 3,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#dddddd", "grid.linewidth": 0.5, "axes.axisbelow": True,
        "legend.frameon": False, "legend.handlelength": 2.2, "legend.borderaxespad": 0.4,
        "lines.linewidth": 1.5, "lines.markersize": 3.5,
        "figure.dpi": 110, "savefig.dpi": 300, "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    }
    if fam:
        rc.update({"mathtext.fontset": "custom", "mathtext.rm": fam, "mathtext.it": f"{fam}:italic", "mathtext.bf": f"{fam}:bold"})
    else:
        rc["mathtext.fontset"] = "stix"
    matplotlib.rcParams.update(rc)


def save(fig, stem) -> Path:
    stem = Path(stem)
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    matplotlib.pyplot.close(fig)
    return stem.with_suffix(".png")
