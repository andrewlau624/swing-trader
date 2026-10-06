"""ETDX/PREF-EX capacity lever: ladder the ENTRY over the T-3/T-2/T-1 closing crosses (the close leg binds; pre-ex
sessions are flat: Sharadar 2005-26 T-3..T-1 night+day ~ -5..+5bp, median 0), exit at the T opening cross (CO) or
T closing cross (CC).

Day-level Roth account sim on official 2021-26 cross rows (PREF + ETDX): on each session close, free cash (account minus
open positions) is split equally across events whose ex-date is 1..L sessions ahead; each tranche <= p x the name's
ex-ante closing-cross $, each event's total <= p x its ex-ante opening-cross $ (CO) or closing-cross $ (CC). Tranche
P&L = event CO/CC (official T-1 close -> T) - HAIRCUT per extra pre-ex session held - cost. Whole shares.

    PYTHONPATH=. .venv/bin/python -m research.sim.etdx_ladder
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from .etdx_exec import rows
from .pref_exec import ACCTS

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/etdx_ladder_out.txt"
S = pathlib.Path.home() / "data" / "sharadar"
HAIRCUT = 0.0003            # per extra pre-ex session held (conservative vs the measured ~-2..+1bp)


def sessions() -> pd.DatetimeIndex:
    b = ds.dataset(S / "funds.parquet").to_table(columns=["date"], filter=ds.field("ticker") == "SPY").to_pandas()
    return pd.DatetimeIndex(sorted(pd.to_datetime(b.date)))


def sim(df: pd.DataFrame, cal: pd.DatetimeIndex, acct: float, p: float, L: int, col: str, cost: float) -> tuple:
    pos = {cal.get_loc(d) for d in df.d.unique()}
    df = df.assign(ti=[cal.get_loc(d) for d in df.d]).reset_index(drop=True)
    cap_in = df.cap_close_ea.values * p
    cap_out = (df.cap_open_ea if col == "co" else df.cap_close_ea).values * p
    held = np.zeros(len(df)); pnl = 0.0; used = []
    for t in range(min(df.ti) - L, max(df.ti)):
        # positions whose ex-date session index <= t are closed before this close (exit at T open/close)
        live = (df.ti > t).values & (df.ti <= t + L).values
        open_cap = held[(df.ti > t).values].sum()
        free = acct - open_cap
        idx = np.where(live)[0]
        if len(idx) and free > 0:
            room = np.minimum(cap_in[idx], cap_out[idx] - held[idx]).clip(min=0)
            order = idx[np.argsort(room)]
            rem = free
            for k, i in enumerate(order):
                a = min(min(cap_in[i], cap_out[i] - held[i]), rem / (len(order) - k))
                if a <= 0:
                    continue
                a = np.floor(a / df.pc.values[i]) * df.pc.values[i]
                extra = df.ti.values[i] - 1 - t                 # pre-ex sessions held beyond T-1
                pnl += a * (df[col].values[i] - cost - HAIRCUT * extra)
                held[i] += a; rem -= a
        exn = (df.ti.values == t + 1)
        if exn.any():
            used.append(held[exn].sum() / acct)
    yrs = (df.d.max() - df.d.min()).days / 365.25
    return pnl / yrs, pnl / yrs / acct


def main():
    cal = sessions()
    both = pd.concat([rows("pref"), rows("etdx")], ignore_index=True)
    both = both[both.d.isin(cal)].dropna(subset=["pc", "cap_close_ea", "cap_open_ea"])
    L_ = [f"Entry ladder, PREF+ETDX official crosses {both.d.min().date()}..{both.d.max().date()}, {len(both)} events; "
          f"haircut {HAIRCUT*1e4:.0f}bp per extra pre-ex session, cost 10bp round trip",
          "form p   ladder " + " ".join(f"{'$'+format(int(a),','):>16s}" for a in ACCTS)]
    for col in ["co", "cc"]:
        for p in [0.05, 0.10]:
            for L in [1, 2, 3]:
                cells = [sim(both, cal, a, p, L, col, 0.0010) for a in ACCTS]
                L_.append(f"{col.upper()}  {p:3.0%} L={L}    " + " ".join(f"${d:7,.0f} {r*100:5.1f}%" for d, r in cells))
            L_.append("")
    L_.append("cell = gross-of-nothing net $/yr (after 10bp + haircut) and %/yr of the account; L=1 = T-1 close only")
    OUT.write_text("\n".join(L_) + "\n")
    print("\n".join(L_))


if __name__ == "__main__":
    main()
