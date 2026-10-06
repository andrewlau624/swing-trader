"""PREF+ETDX in the TAXABLE margin account: Reg-T leverage m on ex-nights, margin interest on the borrowed part.

Tax note (why this is not Roth-only): held one night, the distribution is ordinary income (holding period for qualified
treatment not met) and the ex-date drop is a short-term capital loss; against the book's short-term gains both are taxed
at the ordinary rate, so after-tax = (1 - tau) x pre-tax, like any short-term trade (wash sales only defer; quarterly
payers rarely trigger them).

Sim (L=1, official crosses 2021-26, ex-ante capacity at p of each auction, whole shares): each ex-night deploy up to m x
equity, equal split capped by capacity; financing = max(0, deployed - equity) x RATE x calendar days (d0 -> d) / 360.

    PYTHONPATH=. .venv/bin/python -m research.sim.etdx_margin
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .etdx_exec import rows

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/etdx_margin_out.txt"
RATE = 0.13                      # Schwab base margin rate band for small debit balances (approx.)
TAU = 0.30


def sim(df, eq, m, p, col, cost):
    pnl, fin, worst = 0.0, 0.0, 0.0
    for d, g in df.groupby("d"):
        cap = np.minimum(g.cap_close_ea.values, (g.cap_open_ea if col == "co" else g.cap_close_ea).values) * p
        alloc, rem = np.zeros(len(g)), eq * m
        for k, i in enumerate(np.argsort(cap)):
            a = min(cap[i], rem / (len(g) - k))
            alloc[i] = np.floor(a / g.pc.values[i]) * g.pc.values[i]
            rem -= alloc[i]
        days = max((d - pd.Timestamp(g.d0.iloc[0])).days, 1) if "d0" in g else 1
        f = max(alloc.sum() - eq, 0) * RATE * days / 360
        night = (alloc * (g[col].values - cost)).sum() - f
        pnl += night; fin += f; worst = min(worst, night / eq)
    yrs = (df.d.max() - df.d.min()).days / 365.25
    return pnl / yrs, fin / yrs, worst


def main():
    both = pd.concat([rows("pref"), rows("etdx")], ignore_index=True).dropna(subset=["pc", "cap_close_ea", "cap_open_ea"])
    ev = pd.concat([pd.read_parquet(ROOT / f"data/research/{s}/events.parquet")[["ticker", "date", "d0"]]
                    for s in ("pref", "etdx")]).rename(columns={"ticker": "t", "date": "d"}).drop_duplicates(["t", "d"])
    both = both.merge(ev, on=["t", "d"], how="left")
    L = [f"PREF+ETDX taxable margin, official crosses {both.d.min().date()}..{both.d.max().date()}, rate {RATE:.0%}, "
         f"tau {TAU:.0%}, 10bp round trip; cell = pre-tax $/yr (%), financing $/yr, worst night % of equity"]
    for col in ["co", "cc"]:
        for p in [0.05, 0.10]:
            L.append(f"\n{col.upper()} p {p:.0%}")
            for eq in [2300, 5000, 10000, 25000]:
                cells = []
                for m in [1.0, 1.25, 1.5, 2.0]:
                    v, f, w = sim(both, eq, m, p, col, 0.0010)
                    cells.append(f"{m:.2f}x ${v:6,.0f} ({v/eq*100:4.1f}%) fin ${f:4,.0f} worst {w*100:+.1f}%")
                L.append(f"  ${eq:>6,}: " + " | ".join(cells))
    L.append(f"\nafter tax at tau {TAU:.0%}: multiply pre-tax by {1-TAU:.2f} (ordinary dividend + ST loss vs ST gains)")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
