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
W_IN, DPI = 5.6, 200                     # shown at 560px wide, 2x for sharp screens


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
    ax.tick_params(colors=MUTE, labelsize=10, length=0)
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
    fig, ax = _axes(3.3)
    style = {"This bot": (S1, "-"), "Backtest, everything on": (S2, "-"), "Backtest": (INK, (0, (1, 2))),
             "Everything on": (S1, (0, (6, 2))), "Index fund": (REF, (0, (4, 3)))}
    ends = []
    for name, ys in lines.items():
        c, ls = style.get(name, (REF, "-"))
        ax.plot(years, ys, color=c, linewidth=2.6, linestyle=ls, solid_capstyle="round")
        ends.append((ys[-1], name, c))
    # direct labels at the right end, nudged apart so they never overlap
    ends.sort()
    gap = 0.085 * max(v for v, _, _ in ends)       # in axis units: one 10pt line + air on a 0-based axis
    placed = []
    for v, name, c in ends:
        y = v
        if placed and y - placed[-1] < gap:
            y = placed[-1] + gap
        placed.append(y)
        # name only: the table under the chart carries the values, keyed by the same colored dots
        ax.annotate(name, xy=(years[-1], v), xytext=(years[-1] + 0.3, y),
                    color=INK, fontsize=10, fontweight="bold",
                    va="center", annotation_clip=False)
        ax.plot([years[-1]], [v], "o", color=c, markersize=6)
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


def pnl_png(dates: list, live: list[float], backtest: list[float], plan: list[float], sd: list[float]) -> bytes:
    """Cumulative P&L from closed trades (deposits excluded) vs the backtest's pace on the same balances,
    with its normal range (+-2 sd shaded), and the planning pace as a dashed reference."""
    import numpy as np
    fig, ax = _axes(2.6)
    bt, sd = np.asarray(backtest), np.asarray(sd)
    ax.fill_between(dates, bt - 2 * sd, bt + 2 * sd, color=INK, alpha=0.07, linewidth=0)
    ax.plot(dates, bt, color=INK, linewidth=1.8, linestyle=(0, (1, 2)))
    ax.plot(dates, plan, color=REF, linewidth=1.8, linestyle=(0, (4, 3)))
    c = "#1a7f37" if live[-1] >= 0 else "#cf222e"
    ax.plot(dates, live, color=c, linewidth=2.6, solid_capstyle="round")
    ax.axhline(0, color=GRID, linewidth=1)
    ends = sorted([(live[-1], "Your trades"), (bt[-1], "Backtest pace"), (plan[-1], "Plan pace")])
    lo, hi = ax.get_ylim()
    gap, placed = 0.09 * (hi - lo), []
    for v, name in ends:
        y = v if not placed or v - placed[-1] >= gap else placed[-1] + gap
        placed.append(y)
        ax.annotate(name, xy=(dates[-1], v), xytext=(8, 0), textcoords="offset points", color=INK, fontsize=10,
                    fontweight="bold", va="center", annotation_clip=False)
        if y != v:
            ax.texts[-1].set_position((8, (y - v) / (hi - lo) * 2.6 * 72 * 0.8))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: ("-" if v < 0 else "") + f"${abs(v):,.0f}"))
    ax.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator(maxticks=5))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %-d"))
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return buf.getvalue()
