"""PNG charts for the weekly digest email (inline CID images: Gmail strips SVG and scripts).

Palette validated with the dataviz skill's validator (light surface, protan/deutan/tritan): series 1
#2a78d6 (this bot as is), series 2 #eb6834 (everything on); the index fund is a neutral dashed reference
line. 2px lines, recessive axes, direct end labels (identity never by color alone).
"""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

INK, MUTE, GRID = "#1f2328", "#6e7781", "#e6e8eb"
S1, S2, REF = "#2a78d6", "#eb6834", "#8c959f"
W_IN, DPI = 5.2, 200                     # shown at 520px wide, 2x for sharp screens


def _usd(v, _=None) -> str:
    v = float(v)
    if _ is not None and v == 0:
        return ""                        # the corner belongs to the x axis's "now"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.1f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:.0f}k"
    return f"${v:,.0f}"


def _axes(h_in: float):
    fig, ax = plt.subplots(figsize=(W_IN, h_in), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTE, labelsize=8, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.tight_layout(pad=0.6)
    fig.savefig(buf, format="png", dpi=DPI, facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def projection_png(years: list[float], lines: dict[str, list[float]]) -> bytes:
    """lines: {"This bot": [...], "Everything on": [...], "Index fund": [...]} on the same `years` grid."""
    fig, ax = _axes(2.6)
    style = {"This bot": (S1, "-"), "Everything on": (S2, "-"), "Index fund": (REF, (0, (4, 3)))}
    ends = []
    for name, ys in lines.items():
        c, ls = style.get(name, (REF, "-"))
        ax.plot(years, ys, color=c, linewidth=2, linestyle=ls, solid_capstyle="round")
        ends.append((ys[-1], name, c))
    # direct labels at the right end, nudged apart so they never overlap
    ends.sort()
    gap = 0.075 * max(v for v, _, _ in ends)       # in axis units: ~one label height on a 0-based axis
    placed = []
    for v, name, c in ends:
        y = v
        if placed and y - placed[-1] < gap:
            y = placed[-1] + gap
        placed.append(y)
        ax.annotate(f"{name}  {_usd(v)}", xy=(years[-1], v), xytext=(years[-1] + 0.25, y),
                    color=INK, fontsize=8, va="center", annotation_clip=False,
                    arrowprops=None)
        ax.plot([years[-1]], [v], "o", color=c, markersize=4)
    ax.yaxis.set_major_formatter(FuncFormatter(_usd))
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_xticklabels(["now", "2y", "4y", "6y", "8y", "10y"])
    ax.set_xlim(0, years[-1])
    ax.set_ylim(bottom=0)
    fig.subplots_adjust(right=0.70)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return buf.getvalue()


def pnl_png(dates: list, cum: list[float]) -> bytes:
    """Cumulative P&L from closed trades (deposits excluded)."""
    fig, ax = _axes(1.5)
    c = "#1a7f37" if cum[-1] >= 0 else "#cf222e"
    ax.plot(dates, cum, color=c, linewidth=2, solid_capstyle="round")
    ax.axhline(0, color=GRID, linewidth=1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: ("-" if v < 0 else "") + f"${abs(v):,.0f}"))
    ax.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator(maxticks=5))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %-d"))
    return _png(fig)
