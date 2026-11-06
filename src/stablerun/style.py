"""House style for every figure.

Serif text in TeX Gyre Pagella, the open Palatino that matches the paper's mathpazo, with STIX as the fallback;
the Okabe-Ito colour-blind-safe palette; a light horizontal grid; no top or right spine; left-aligned panel titles
with a bold letter; frameless legends. PDFs are written without a timestamp so that a rebuild is reproducible
byte for byte. Pagella is looked for in .tools/fonts (fetched by scripts/fetch_fonts.sh), in the TeX distribution
(kpsewhich) and among the system fonts.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[2]

PALETTE = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
           "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7", "grey": "#7F7F7F"}
INK = "#1a1a1a"        # text and the darkest lines
INK_2 = "#505050"      # axes, ticks, secondary text
GRID = "#e4e4e4"


def _pagella_files() -> list[Path]:
    files = sorted((ROOT / ".tools" / "fonts").glob("texgyrepagella-*.otf"))
    if not files:
        try:
            root = subprocess.run(["kpsewhich", "-var-value=TEXMFDIST"], capture_output=True, text=True, timeout=10).stdout.strip()
            files = sorted((Path(root) / "fonts" / "opentype" / "public" / "tex-gyre").glob("texgyrepagella-*.otf"))
        except Exception:
            files = []
    if not files:
        files = [Path(f) for f in font_manager.findSystemFonts() if Path(f).name.lower().startswith("texgyrepagella")]
    return files


def _register_pagella() -> str | None:
    files = _pagella_files()
    for f in files:
        font_manager.fontManager.addfont(str(f))
    return "TeX Gyre Pagella" if files else None


def apply() -> None:
    fam = _register_pagella()
    serif = ([fam] if fam else []) + ["STIXGeneral", "DejaVu Serif"]
    rc = {
        "font.family": "serif", "font.serif": serif,
        "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 8, "legend.title_fontsize": 8,
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "axes.titlelocation": "left", "axes.titleweight": "normal", "axes.titlepad": 8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
        "axes.edgecolor": INK_2, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK_2, "ytick.color": INK_2, "xtick.labelcolor": INK, "ytick.labelcolor": INK,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 3, "ytick.major.size": 3,
        "xtick.direction": "out", "ytick.direction": "out",
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True,
        "legend.frameon": False, "legend.handlelength": 2.0, "legend.borderaxespad": 0.3, "legend.labelspacing": 0.35,
        "legend.handletextpad": 0.6, "legend.columnspacing": 1.4,
        "lines.linewidth": 1.5, "lines.markersize": 3.5, "lines.solid_capstyle": "round",
        "figure.dpi": 110, "savefig.dpi": 300, "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.04,
    }
    if fam:
        rc.update({"mathtext.fontset": "custom", "mathtext.rm": fam, "mathtext.it": f"{fam}:italic",
                   "mathtext.bf": f"{fam}:bold", "mathtext.cal": f"{fam}:italic"})
    else:
        rc["mathtext.fontset"] = "stix"
    matplotlib.rcParams.update(rc)


def panel_title(ax, letter: str, text: str, sub: str | None = None, size: float | None = None, pad_pt: float = 6.0):
    """Left-aligned panel title above the axes: a bold '(a)' followed by the title in regular weight, with an
    optional smaller subtitle on a second line. Built from offset boxes so that the whole letter is bold."""
    from matplotlib.offsetbox import AnchoredOffsetbox, HPacker, TextArea, VPacker
    from matplotlib.transforms import offset_copy

    size = size or matplotlib.rcParams["axes.titlesize"]
    line = HPacker(children=[TextArea(f"({letter})", textprops=dict(size=size, weight="bold", color=INK)),
                             TextArea(text, textprops=dict(size=size, color=INK))], pad=0, sep=3)
    box = line if sub is None else VPacker(children=[line, TextArea(sub, textprops=dict(size=size - 1, color=INK_2))],
                                           pad=0, sep=2, align="left")
    tr = offset_copy(ax.transAxes, fig=ax.figure, x=0, y=pad_pt, units="points")
    ax.add_artist(AnchoredOffsetbox(loc="lower left", child=box, pad=0, borderpad=0, frameon=False,
                                    bbox_to_anchor=(0, 1), bbox_transform=tr))


def end_labels(ax, items, x, merge_tol, min_gap, joiner=None, fontsize=7.8, pad_pt=4.0, bold=False):
    """Direct labels at the right end of the lines instead of a legend.

    items: (y, text, colour) per line. Lines whose end values differ by less than merge_tol share one label
    (texts joined with ', ' or with joiner(texts)); labels are then pushed apart until none are closer than
    min_gap, so nothing overlaps. Both tolerances are in data units.
    """
    joiner = joiner or (lambda texts: ", ".join(texts))
    groups: list[dict] = []
    for i, (y, text, colour) in sorted(enumerate(items), key=lambda it: it[1][0]):
        if groups and abs(y - groups[-1]["y"][-1]) < merge_tol:
            groups[-1]["y"].append(y)
            groups[-1]["members"].append((i, text))
        else:
            groups.append({"y": [y], "members": [(i, text)], "colour": colour})
    ys = [float(np.mean(g["y"])) for g in groups]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < min_gap:
            ys[i] = ys[i - 1] + min_gap
    for g, y in zip(groups, ys):
        texts = [text for _, text in sorted(g["members"])]  # in the order the lines were given
        ax.annotate(joiner(texts), xy=(x, y), xytext=(pad_pt, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=fontsize, color=g["colour"], annotation_clip=False,
                    fontweight="bold" if bold else "normal")


def text_colour_on(rgba) -> str:
    """Black or white text, whichever reads better on the given fill colour."""
    r, g, b = rgba[:3]
    return "white" if 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.55 else INK


def save(fig, stem) -> Path:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    meta = {"Creator": "stablerun", "Producer": "matplotlib", "CreationDate": None, "ModDate": None}
    fig.savefig(stem.with_suffix(".pdf"), metadata=meta)
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    matplotlib.pyplot.close(fig)
    return stem.with_suffix(".png")
