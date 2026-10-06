"""Study A-OPEX runner: pre-registered in research/drafts/study_A_opex_pin.md.

Pulls Databento OPRA `statistics` (open interest = stat_type 9) for SPY on each monthly OPEX
day 2023-2024, finds the max-OI strike within +/-3% of the prior close, and tests whether SPY
converges to it from open to close (vs the second-max-OI strike placebo). Mechanism probe.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.opex_pin
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/contest/opex_pin"
OUT = ROOT / "data/research/program/opex_pin_out.txt"


def opex_dates(start="2023-01-01", end="2025-01-01"):
    ds = pd.date_range(start, end, freq="WOM-3FRI")
    return [d for d in ds if d < pd.Timestamp(end)]


def parse_osi(s):
    # 'SPY   240119C00400000' -> (expiry, cp, strike)
    root, rest = s[:6], s[6:]
    try:
        exp = pd.Timestamp("20" + rest[:6][:2] + "-" + rest[:6][2:4] + "-" + rest[:6][4:6])
        cp = rest[6]
        k = int(rest[7:]) / 1000.0
        return exp, cp, k
    except Exception:
        return None, None, None


def pull_day(day):
    f = CACHE / f"SPY_{day:%Y%m%d}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    import databento as db
    c = db.Historical(os.environ["DATABENTO_API_KEY"])
    try:
        df = c.timeseries.get_range(dataset="OPRA.PILLAR", schema="statistics",
                                    symbols="SPY.OPT", stype_in="parent",
                                    start=day.strftime("%Y-%m-%d"),
                                    end=(day + pd.Timedelta(days=1)).strftime("%Y-%m-%d")).to_df().reset_index()
    except Exception as exc:  # noqa: BLE001
        print(f"  pull {day.date()} failed: {str(exc)[:90]}", flush=True)
        return None
    df = df[df["stat_type"] == 9][["symbol", "quantity"]].dropna(subset=["symbol"])
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(f)
    return df


def main():
    P = D.etf()
    O, C = P["open"]["SPY"], P["close"]["SPY"]
    rows = []
    for day in opex_dates():
        prior = C.loc[:day].iloc[:-1]
        if prior.empty or day not in O.index:
            continue
        pc = prior.iloc[-1]
        df = pull_day(day)
        if df is None or df.empty:
            continue
        oi = df.groupby("symbol")["quantity"].max().reset_index()
        oi[["exp", "cp", "strike"]] = oi["symbol"].apply(lambda s: pd.Series(parse_osi(s)))
        oi = oi[oi["exp"] == day]
        oi = oi[(oi.strike >= pc * 0.97) & (oi.strike <= pc * 1.03)]
        if oi.empty:
            continue
        byk = oi.groupby("strike")["quantity"].sum().sort_values(ascending=False)
        if len(byk) < 3:
            continue
        K1, K2 = byk.index[0], byk.index[1]
        op, cl = O.get(day), C.get(day)
        if not (np.isfinite(op) and np.isfinite(cl)):
            continue
        rows.append(dict(day=day, pc=pc, K1=K1, K2=K2, open=op, close=cl,
                         d1=K1 - op, d2=K2 - op, ret=cl / op - 1))
    R = pd.DataFrame(rows)
    if R.empty:
        print("no events"); return
    b, cost = 1e4, 1.0  # 0.5bp/side round trip
    lines = ["Study A-OPEX: max-OI-strike pinning on SPY monthly OPEX (2023-2024)",
             f"events={len(R)}  (OI is the prior-close report; open->close trade, 1bp round-trip cost)", ""]
    for lab, dcol in [("K1 (max-OI)", "d1"), ("K2 (2nd-OI placebo)", "d2")]:
        ms = R[R[dcol].abs() / R["open"] > 0.002].copy()  # only when spot is >0.2% from the strike
        if len(ms) < 5:
            lines.append(f"{lab}: n={len(ms)} (too few)"); continue
        ms["pnl"] = np.sign(ms[dcol]) * ms["ret"] - cost / b
        hit = (np.sign(ms[dcol]) * ms["ret"] > 0).mean()
        t = ms["pnl"].mean() / ms["pnl"].std() * np.sqrt(len(ms))
        lines.append(f"{lab}: n={len(ms)} hit={hit*100:3.0f}% mean_net={ms['pnl'].mean()*b:6.1f}bp "
                     f"t={t:5.2f} med={ms['pnl'].median()*b:6.1f}bp")
    # convergence magnitude: correlation of |K-open| with |close-open| direction
    conv = (np.sign(R["d1"]) * R["ret"])
    lines += ["", f"convergence toward K1 (all {len(R)} OPEX): mean={conv.mean()*b:.1f}bp "
                  f"hit={(conv>0).mean()*100:.0f}%"]
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
