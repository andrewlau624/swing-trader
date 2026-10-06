"""PREF+ETDX stacked on the taxable book's overnight Reg-T headroom (economics, no N).

The book (V7 params, night_w 0.5 + IBS 0.5) holds night + IBS positions overnight. Reg T allows 2x equity overnight, so
headroom = 2E - (night $ + IBS $). On each ex-night PREF/ETDX deploys min(headroom, capacity) (equal split, p of the
ex-ante auction, whole shares); financing on the incremental debit at the book's margin rate. Equity fixed per run
(no compounding), official crosses 2021-26, 10bp round trip.

    PYTHONPATH=. .venv/bin/python -m research.sim.etdx_stack
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .book import Params, Sim
from .etdx_exec import rows
from .growth import V7

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/etdx_stack_out.txt"


def main():
    sim = Sim(noise_syms=("QQQ", "TQQQ") if "TQQQ" in str(V7.get("noise")) else ("QQQ",))
    p = Params(**{k: v for k, v in V7.items() if k in Params.__dataclass_fields__ and k != "noise"})
    both = pd.concat([rows("pref"), rows("etdx")], ignore_index=True).dropna(subset=["pc", "cap_close_ea", "cap_open_ea"])
    ev = pd.concat([pd.read_parquet(ROOT / f"data/research/{s}/events.parquet")[["ticker", "date", "d0"]]
                    for s in ("pref", "etdx")]).rename(columns={"ticker": "t", "date": "d"}).drop_duplicates(["t", "d"])
    both = both.merge(ev, on=["t", "d"], how="left").dropna(subset=["d0"])
    L = ["PREF+ETDX stacked on the taxable book's overnight headroom (Reg T 2x), V7 params, 10bp round trip"]
    for eq in [2300, 5000, 10000, 25000]:
        expo = {}
        for d0 in sorted(both.d0.unique()):
            d0 = pd.Timestamp(d0)
            if d0 in sim.C.index:
                _, info = sim.day_pnl(eq, d0, p)
                expo[d0] = info["night_v"] + max(info["ibs_v"], p.ibs_w * eq)   # idle IBS cash sits in BIL (uses buying power)
        hr = pd.Series({d: max(2 * eq - v, 0.0) for d, v in expo.items()})
        for col in ["co", "cc"]:
            pnl, fin, used = 0.0, 0.0, []
            for d0, g in both[both.d0.isin(hr.index)].groupby("d0"):
                cap = np.minimum(g.cap_close_ea.values, (g.cap_open_ea if col == "co" else g.cap_close_ea).values) * 0.05
                alloc, rem = np.zeros(len(g)), hr[d0]
                for k, i in enumerate(np.argsort(cap)):
                    a = min(cap[i], rem / (len(g) - k))
                    alloc[i] = np.floor(a / g.pc.values[i]) * g.pc.values[i]
                    rem -= alloc[i]
                debit_before = max(expo[d0] - eq, 0.0)
                extra = max(expo[d0] + alloc.sum() - eq, 0.0) - debit_before
                days = max((pd.Timestamp(g.d.iloc[0]) - d0).days, 1)
                f = extra * p.margin_rate * days / 360
                pnl += (alloc * (g[col].values - 0.0010)).sum() - f; fin += f; used.append(alloc.sum() / eq)
            yrs = (both.d.max() - both.d.min()).days / 365.25
            L.append(f"${eq:>6,} {col.upper()}: book overnight expo on ex-eves median {np.median(list(expo.values()))/eq:.2f}x, "
                     f"headroom median {hr.median()/eq:.2f}x | stacked ${pnl/yrs:6,.0f}/yr pre-tax ({pnl/yrs/eq*100:4.1f}%), "
                     f"financing ${fin/yrs:,.0f}/yr, mean deployed {np.mean(used)*100:.0f}% of equity")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
