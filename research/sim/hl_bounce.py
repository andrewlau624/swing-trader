"""HL-BOUNCE (N 1055): confirmed bounce from a higher pivot low inside rising pivot highs.

Pre-registration: research/drafts/round1_prose.md "Study HL-BOUNCE". Daily Sharadar panels from winsig.load_panel
(stocks / non-leveraged ETFs, delisted included). Pivots with k=3, confirmed at t+3; signal s = first close in
[t+3, t+10] above the pivot bar's high with no earlier close above it. Buy open s+1, excess vs the EW liq universe.
Run: .venv/bin/python -m research.sim.hl_bounce  ->  data/research/program/hl_bounce_out.txt
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from . import winsig as W

OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "program" / "hl_bounce_out.txt"
K, WIN = 3, 10
PERIODS = {"2016-26": W.DISC, "2003-15": W.CONF}
COLS = ["ticker", "date", "open", "high", "low", "close", "closeadj", "adv20", "liq", "f1", "f3", "f5", "f10"]


def load(kind: str) -> pd.DataFrame:
    f = W.CACHE / {"stock": "panel.parquet", "etf": "panel_etf.parquet"}[kind]
    t = pd.read_parquet(f, columns=COLS) if f.exists() else W.load_panel(kind=kind)[COLS]
    keep = t.groupby("ticker", sort=False)["liq"].transform("any")
    t = t[keep].reset_index(drop=True)
    return W.add_bench(t)


def pivots(t: pd.DataFrame) -> pd.DataFrame:
    """Per-ticker structure state at every bar, using only pivots confirmed at or before the bar."""
    g = t.groupby("ticker", sort=False)
    lo, hi, cl = t["low"], t["high"], t["close"]
    lmin_l = pd.concat([g["low"].shift(k) for k in range(1, K + 1)], axis=1).min(axis=1)
    lmin_r = pd.concat([g["low"].shift(-k) for k in range(1, K + 1)], axis=1).min(axis=1)
    hmax_l = pd.concat([g["high"].shift(k) for k in range(1, K + 1)], axis=1).max(axis=1)
    hmax_r = pd.concat([g["high"].shift(-k) for k in range(1, K + 1)], axis=1).max(axis=1)
    is_pl = (lo < lmin_l) & (lo <= lmin_r)
    is_ph = (hi > hmax_l) & (hi >= hmax_r)
    t["bar"] = g.cumcount()
    # values known at the confirmation bar t+K
    def conf(x):
        return x.groupby(t["ticker"], sort=False).shift(K)
    pl_val = conf(lo.where(is_pl))
    pl_bar = conf(t["bar"].where(is_pl))
    pl_high = conf(hi.where(is_pl))
    pl_cmax = conf(pd.concat([g["close"].shift(-1), g["close"].shift(-2)], axis=1).max(axis=1).where(is_pl))  # closes t+1..t+2
    ph_val = conf(hi.where(is_ph))
    # running pivot-high chain (confirmed)
    ph1 = ph_val.groupby(t["ticker"], sort=False).ffill()
    ph_prev_at_ph = ph1.where(ph_val.notna()).groupby(t["ticker"], sort=False).shift(1)
    ph_prev_at_ph = ph_prev_at_ph.where(ph_val.notna())
    # ph_prev: at a new pivot-high confirmation take the previous chain value
    ph_prev_pts = ph1.groupby(t["ticker"], sort=False).shift(1).where(ph_val.notna())
    ph2 = ph_prev_pts.groupby(t["ticker"], sort=False).ffill()
    # pivot-low chain
    plc = pl_val.groupby(t["ticker"], sort=False).ffill()
    pl_prev_pts = plc.groupby(t["ticker"], sort=False).shift(1).where(pl_val.notna())
    plp = pl_prev_pts.groupby(t["ticker"], sort=False).ffill()
    # at a pivot-low confirmation freeze the ph chain as of that moment (highs confirmed before the low's confirmation)
    seg = pl_bar.groupby(t["ticker"], sort=False).ffill()
    t["pl_cur"], t["pl_prev"], t["pl_bar"] = plc, plp, seg
    t["pl_high"] = pl_high.groupby(t["ticker"], sort=False).ffill()
    t["ph1"] = ph1.where(pl_val.notna()).groupby(t["ticker"], sort=False).ffill()
    t["ph2"] = ph2.where(pl_val.notna()).groupby(t["ticker"], sort=False).ffill()
    # first-cross bookkeeping: max close since t+1 up to s-1
    start_cmax = pl_cmax.groupby(t["ticker"], sort=False).ffill()
    key = [t["ticker"], seg]
    cm = cl.groupby(key, sort=False).cummax()
    prev_cm = cm.groupby(key, sort=False).shift(1)
    t["prev_cmax"] = np.fmax(prev_cm.fillna(-np.inf), start_cmax.fillna(-np.inf))
    age = t["bar"] - seg
    t["sig"] = (age >= K) & (age <= WIN) & (cl > t["pl_high"]) & (t["prev_cmax"] <= t["pl_high"]) & seg.notna()
    t["sma200"] = g["close"].transform(lambda s: s.rolling(200, min_periods=200).mean())
    t["depth"] = t["pl_cur"] / t["ph1"] - 1
    return t


def paired(t, m1, m2, lo, hi, H=5):
    sel = t[t.liq & (t.date >= lo) & (t.date <= hi)]
    a = sel[m1.loc[sel.index]].groupby("date")[f"x{H}"].mean()
    b = sel[m2.loc[sel.index]].groupby("date")[f"x{H}"].mean()
    d = (a - b).dropna()
    return d.mean() * 1e4, W.nw_t(d, H), len(d)


def run(kind: str, lines: list[str]):
    t = pivots(load(kind))
    sig = t["sig"]
    up = sig & (t.pl_cur > t.pl_prev) & (t.ph1 > t.ph2)
    ll = sig & (t.pl_cur < t.pl_prev)
    lines.append(f"\n=== {kind.upper()} : {t.ticker.nunique()} names, {int((sig & t.liq).sum())} liq signals ===")
    for pname, (lo, hi) in PERIODS.items():
        lines.append(f"-- {pname} --")
        for lab, m in [("A1 HL-UP higher low + rising highs (PRIMARY)", up), ("A2 LL lower low (control)", ll),
                       ("A3 ALL pivot-low bounces", sig), ("A1 & close>SMA200", up & (t.close > t.sma200)),
                       ("A1 & close<SMA200", up & (t.close <= t.sma200))]:
            r = W.judge(t, m, lo, hi, lab)
            lines.append(W.fmt(r))
        d, tt, n = paired(t, up, ll, lo, hi)
        lines.append(f"   A1 - A2 date-paired H5: {d:+.1f}bp (t {tt:+.2f}, {n} dates)  [bar >= +10]")
        d, tt, n = paired(t, up, sig & ~up, lo, hi)
        lines.append(f"   A1 - not-A1 date-paired H5: {d:+.1f}bp (t {tt:+.2f}, {n} dates)")
        selu = t[up & t.liq & (t.date >= lo) & (t.date <= hi)]
        if len(selu) > 100:
            for col, name in [("depth", "pullback depth"), ("adv20", "ADV20")]:
                q = pd.qcut(selu[col], 3, labels=["T1 low", "T2", "T3 high"], duplicates="drop")
                s = selu.groupby(q, observed=True)["x5"].agg(["mean", "median", "size"])
                lines.append(f"   A1 by {name}: " + " | ".join(f"{i}: {v['mean']*1e4:+.1f}/{v['median']*1e4:+.1f} n{int(v['size'])}" for i, v in s.iterrows()))
    selu = t[up & t.liq]
    yr = selu.groupby(selu.date.dt.year)["x5"].agg(["mean", "size"])
    lines.append("   A1 by year (H5 excess bp / n): " + " ".join(f"{y}:{v['mean']*1e4:+.0f}/{int(v['size'])}" for y, v in yr.iterrows()))
    return t


def main():
    lines = [f"HL-BOUNCE (N 1055) one look {pd.Timestamp.today():%Y-%m-%d}. k={K}, window {WIN}, cost {W.COST*1e4:.0f}bp RT, shock {W.SHOCK*1e4:.0f}bp. "
             "Excess vs EW liq universe, buy open s+1, H5 primary."]
    verdict = []
    for kind in ("etf", "stock"):
        t = run(kind, lines)
        up = t["sig"] & (t.pl_cur > t.pl_prev) & (t.ph1 > t.ph2)
        ok = all(W.passes(W.judge(t, up, lo, hi, "")) for lo, hi in PERIODS.values())
        ok = ok and all(paired(t, up, t["sig"] & (t.pl_cur < t.pl_prev), lo, hi)[0] >= 10 for lo, hi in PERIODS.values())
        verdict.append(f"{kind}: {'PASS' if ok else 'KILL'}")
        del t
    lines.append("\nVERDICT (registered bar, A1 both periods + A1-A2 >= +10bp): " + "; ".join(verdict))
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
