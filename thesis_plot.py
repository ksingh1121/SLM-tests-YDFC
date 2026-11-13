r"""
thesis_plot.py — consistent, print-accurate figures for a Typst thesis.

Based on physics.mplstyle (Arial, inward ticks on all four sides), but every
size is given in absolute points for the *printed* page. Each panel is drawn
at its exact final width, so text looks identical whether a figure is
full-width, two-per-row or three-per-row.

Usage
-----
    import thesis_plot as tp

    tp.apply_style()

    fig, ax = tp.panel(ncols=3)          # one panel of a three-panel row
    ax.plot(x, y)
    ax.set_xlabel(r"Detuning $\Delta/2\pi$ (MHz)")
    tp.save(fig, "rabi_a")               # -> figures/rabi_a.svg

    fig, axs = tp.row(ncols=3, sharey=True)   # whole row as ONE figure
    tp.label_panels(axs)                      # adds (a), (b), (c)
    tp.save(fig, "rabi_row")

In Typst, include WITHOUT a width argument so nothing gets rescaled:

    #figure(
      grid(columns: 3, column-gutter: 8pt,
        image("figures/rabi_a.svg"),
        image("figures/rabi_b.svg"),
        image("figures/rabi_c.svg")),
      caption: [...],
    )
"""

from pathlib import Path
import string
import warnings

import matplotlib as mpl
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Page geometry — set these ONCE to match your Typst document.
# Get the text width by putting  #layout(size => [#size.width])  in the body.
# Typst "pt" = 1/72 inch.
# ---------------------------------------------------------------------------
TEXTWIDTH_PT = 453.54   # A4 with 2.5 cm margins; replace with your value
GUTTER_PT = 8.0         # must equal column-gutter of your Typst grid
FIG_DIR = Path("figures")
DEFAULT_FORMAT = "svg"  # "svg" or "pdf" (Typst >= 0.14); "png" for images

PT = 1 / 72             # inches per Typst point
GOLDEN = (5 ** 0.5 - 1) / 2

# ---------------------------------------------------------------------------
# Style: your physics.mplstyle, rescaled for print.
# Original values (made for a 5.5 x 3.5 in screen figure) in comments.
# ---------------------------------------------------------------------------
BASE_FONT = 9  # pt on paper; ~ caption size

STYLE = {
    # FIGURE
    "figure.dpi": 150,
    "figure.constrained_layout.use": True,    # fixed size, axes fit inside
    "figure.constrained_layout.h_pad": 2 * PT,
    "figure.constrained_layout.w_pad": 2 * PT,

    # FONT (your choice: Arial, sans-serif)
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": BASE_FONT,                   # 13
    "figure.titlesize": BASE_FONT,            # 15

    # MATH FONT (your choice: Arial for math)
    "mathtext.fontset": "custom",
    "mathtext.rm": "Arial:regular",
    "mathtext.it": "Arial:italic",
    "mathtext.bf": "Arial:bold",
    "mathtext.default": "it",
    "mathtext.fallback": "stixsans",

    # AXES
    "axes.labelsize": BASE_FONT,              # 14
    "axes.titlesize": BASE_FONT,              # 12
    "axes.linewidth": 0.7,                    # 1.0
    "axes.labelpad": 2.0,

    # TICKS (your choice: inward, on all four sides)
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "xtick.labelsize": BASE_FONT - 1,
    "ytick.labelsize": BASE_FONT - 1,
    "xtick.major.pad": 3.5,                   # 7.0 (too wide for small panels)
    "ytick.major.pad": 3.5,
    "xtick.major.size": 3.0,                  # 4.0
    "ytick.major.size": 3.0,
    "xtick.major.width": 0.7,                 # 1.0
    "ytick.major.width": 0.7,
    "xtick.minor.visible": False,
    "ytick.minor.visible": False,
    "xtick.minor.size": 1.5,                  # 2.0
    "ytick.minor.size": 1.5,
    "xtick.minor.width": 0.5,
    "ytick.minor.width": 0.5,

    # LINES
    "lines.linewidth": 1.2,                   # 1.5
    "lines.markeredgewidth": 1.0,             # 1.5
    "lines.markersize": 4,                    # 6
    "errorbar.capsize": 1.5,

    # LEGEND (your settings, smaller)
    "legend.edgecolor": "white",
    "legend.facecolor": "white",
    "legend.fancybox": False,
    "legend.framealpha": 0.8,
    "legend.fontsize": BASE_FONT - 1,         # 12
    "legend.handlelength": 1.0,
    "legend.columnspacing": 1.0,
    "legend.borderpad": 0.3,
    "legend.labelspacing": 0.3,

    # SAVEFIG — "tight" would change the size, so it is OFF here
    "savefig.bbox": "standard",               # was: tight
    "savefig.pad_inches": 0.0,
    "savefig.facecolor": "none",
    "savefig.dpi": 600,                       # only matters for raster parts
    "svg.fonttype": "path",                   # looks identical everywhere
    "pdf.fonttype": 42,

    # COLORMAP
    "image.cmap": "Blues",
}


def apply_style(retina=True):
    """Activate the thesis style (call once per script/notebook)."""
    mpl.rcParams.update(STYLE)
    if retina:
        try:  # sharper inline plots in Jupyter; harmless elsewhere
            from matplotlib_inline.backend_inline import set_matplotlib_formats
            set_matplotlib_formats("retina")
        except Exception:
            pass
    # Only warn once if Arial is missing, instead of on every draw.
    names = {f.name for f in mpl.font_manager.fontManager.ttflist}
    if "Arial" not in names:
        warnings.warn("Arial not found; falling back to Helvetica/DejaVu Sans. "
                      "Install Arial and delete matplotlib's font cache.")
        import logging
        logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# Sizes
# ---------------------------------------------------------------------------
def panel_width_pt(ncols=1):
    """Width (pt) of one panel when ncols panels share a row."""
    return (TEXTWIDTH_PT - (ncols - 1) * GUTTER_PT) / ncols


def panel_size(ncols=1, aspect=None, span=1):
    """(width, height) in inches for one panel.

    ncols  : panels per row (1, 2, 3, ...)
    aspect : height/width. Default: golden ratio for 1-2 columns,
             0.85 for 3+ columns (narrow panels need relatively more height).
    span   : panel spans this many columns (e.g. 2 of 3), gutters included.
    """
    if aspect is None:
        aspect = GOLDEN if ncols <= 2 else 0.85
    w = span * panel_width_pt(ncols) + (span - 1) * GUTTER_PT
    return (w * PT, w * PT * aspect)


def panel(ncols=1, aspect=None, span=1, **kwargs):
    """Single-panel figure sized for one cell of an ncols-wide Typst grid."""
    fig, ax = plt.subplots(figsize=panel_size(ncols, aspect, span), **kwargs)
    if ncols >= 3:
        slim_ticks(ax)
    return fig, ax


def row(ncols=2, nrows=1, aspect=None, width=1.0, **kwargs):
    """Several panels as ONE full-width figure (include with no grid in Typst).

    width : fraction of the text width the whole figure occupies.
    Extra kwargs go to plt.subplots (e.g. sharey=True).
    """
    if aspect is None:
        aspect = GOLDEN if ncols <= 2 else 0.85
    w = width * TEXTWIDTH_PT * PT
    h = nrows * (w / ncols) * aspect
    fig, axs = plt.subplots(nrows, ncols, figsize=(w, h), **kwargs)
    if ncols >= 3:
        for ax in getattr(axs, "flat", [axs]):
            slim_ticks(ax)
    return fig, axs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slim_ticks(ax, nbins=4):
    """Fewer tick labels for narrow panels so they don't collide."""
    ax.xaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=nbins))
    ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=nbins))


def label_panels(axs, fmt="({})", loc=(0.03, 0.97), start=0, **kwargs):
    """Write (a), (b), ... inside the top-left corner of each axis.

    Use this for row() figures. For separate panel files, let Typst's
    `subpar` package do the labelling instead.
    """
    axs = getattr(axs, "flat", axs)
    letters = string.ascii_lowercase[start:]
    style = dict(fontsize=BASE_FONT, fontweight="bold",
                 ha="left", va="top")
    style.update(kwargs)
    for ax, letter in zip(axs, letters):
        ax.text(*loc, fmt.format(letter), transform=ax.transAxes, **style)


def save(fig, name, fmt=None, folder=None, close=True):
    """Save at the exact designed size (no tight bbox) and report it."""
    fmt = fmt or DEFAULT_FORMAT
    folder = Path(folder) if folder else FIG_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.{fmt}"
    fig.savefig(path, format=fmt, bbox_inches=None)
    w, h = fig.get_size_inches() / PT
    print(f"saved {path}  ({w:.1f} pt x {h:.1f} pt)")
    if close:
        plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Demo: python thesis_plot.py  -> writes example figures to ./figures
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import numpy as np

    apply_style()
    t = np.linspace(0, 4, 400)

    # Two separate half-width panels
    for i, omega in enumerate([1.0, 2.0]):
        fig, ax = panel(ncols=2)
        ax.plot(t, np.sin(np.pi * omega * t / 2) ** 2, label=r"$\Omega_R$")
        ax.set_xlabel(r"Pulse duration $t$ ($\mu$s)")
        ax.set_ylabel(r"$P_{e}$")
        ax.legend(loc="upper right")
        save(fig, f"demo_two_{'ab'[i]}")

    # Three separate third-width panels
    for i, gamma in enumerate([0.1, 0.5, 1.0]):
        fig, ax = panel(ncols=3)
        ax.plot(t, np.exp(-gamma * t) * np.sin(np.pi * t) ** 2)
        ax.set_xlabel(r"$t$ ($\mu$s)")
        ax.set_ylabel(r"$P_{e}$")
        save(fig, f"demo_three_{'abc'[i]}")

    # One full-width figure with three panels and shared y-axis
    fig, axs = row(ncols=3, sharey=True)
    for ax, gamma in zip(axs, [0.1, 0.5, 1.0]):
        ax.plot(t, np.exp(-gamma * t) * np.sin(np.pi * t) ** 2)
        ax.set_xlabel(r"$t$ ($\mu$s)")
    axs[0].set_ylabel(r"$P_{e}$")
    label_panels(axs)
    save(fig, "demo_row")
