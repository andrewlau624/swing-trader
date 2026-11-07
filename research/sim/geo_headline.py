"""Study GEO-HEADLINE (N 1115-1116): Caldara-Iacoviello daily GPR 'acts' spikes -> drift from the next regular-hours
auction in SPY / USO / XLE / ITA / GLD. Pre-reg research/drafts/round1_prose.md "Study GEO-HEADLINE". One look.

Trigger: GPRD_ACT(D) >= 99th pct of trailing 365 calendar entries (excl. D), declustered 14 calendar days.
Signal session T = first session with date >= D. Primary: long SPY close(T) -> close(T+5). Judge 2008-2026.
Yahoo daily bars are the regular-hours session (open ~ opening cross, close = closing cross); returns use adjclose
ratios, opens are adjusted by adjclose/close of the same day.

  PYTHONPATH=.:<dir with xlrd> python3 -m research.sim.geo_headline
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .vt_flow import yahoo_ohlc

ROOT = pathlib.Path(__file__).resolve().parents[2]
GPR = ROOT / "data/research/geo_headline/data_gpr_daily_recent.xls"
OUT = ROOT / "data/research/program/geo_headline_out.txt"
SIDE = 1e-4
JUDGE = ("2008-01-01", "2026-11-02")
HALVES = (("2008-01-01", "2016-12-31"), ("2017-01-01", "2026-11-02"))
NPROG = 1116
L: list[str] = []
RNG = np.random.default_rng(1115)


def P(s=""):
    print(s, flush=True); L.append(s)


def triggers(q: float) -> pd.DatetimeIndex:
    x = pd.read_excel(GPR, usecols=["date", "GPRD_ACT"]).dropna()
    s = x.set_index("date")["GPRD_ACT"].sort_index()
    thr = s.shift(1).rolling(365, min_periods=300).quantile(q)
    keep, last = [], None
    for d in s.index[s >= thr]:
        if last is None or (d - last).days > 14:
            keep.append(d); last = d
    return pd.DatetimeIndex(keep)


def bars(sym: str) -> pd.DataFrame:
    df = yahoo_ohlc(sym).copy()
    f = df["adjclose"] / df["close"]
    df["o"], df["c"] = df["open"] * f, df["adjclose"]
    return df[["o", "c"]]


def legs(df: pd.DataFrame, trig: pd.DatetimeIndex, entry: str, h: int) -> pd.DataFrame:
    """Per event: gap close(T-1)->open(T), day open(T)->close(T), trade from entry to close(T+h)."""
    idx = df.index
    rows = []
    for d in trig:
        i = idx.searchsorted(d)
        if i < 1 or i + h + 1 >= len(idx):
            continue
        T = idx[i]
        o, c = df["o"].values, df["c"].values
        if entry == "closeT":
            r = c[i + h] / c[i] - 1
        elif entry == "openT1":
            r = c[i + h] / o[i + 1] - 1
        else:  # openT (optimistic, live replica only)
            r = c[i + h - 1] / o[i] - 1 if h >= 1 else np.nan
        rows.append(dict(D=d, T=T, gap=o[i] / c[i - 1] - 1, day=c[i] / o[i] - 1, pre=c[i - 1] / c[i - 2] - 1, r=r))
    return pd.DataFrame(rows).set_index("T") if rows else pd.DataFrame()


def uncond(df: pd.DataFrame, a, b, entry: str, h: int) -> np.ndarray:
    o, c = df["o"].values, df["c"].values
    n = len(df)
    i = np.arange(2, n - h - 1)
    if entry == "closeT":
        r = c[i + h] / c[i] - 1
    elif entry == "openT1":
        r = c[i + h] / o[i + 1] - 1
    else:
        r = c[i + h - 1] / o[i] - 1
    m = (df.index[i] >= a) & (df.index[i] <= b)
    return r[m]


def summ(r: pd.Series, u: np.ndarray, label: str, cost=2 * SIDE):
    r = r.dropna()
    n = len(r)
    if n < 3:
        P(f"  {label:34s} n {n}"); return
    net = r - cost
    t = net.mean() / net.std(ddof=1) * np.sqrt(n)
    ex5 = net.sort_values().iloc[:-5].mean() if n > 6 else np.nan
    draws = np.array([RNG.choice(u, n, replace=False).mean() for _ in range(2000)])
    pct = (draws < r.mean()).mean() * 100
    P(f"  {label:34s} n {n:3d} mean {net.mean()*1e4:+7.1f}bp med {net.median()*1e4:+7.1f} hit {(net>0).mean()*100:4.0f}% "
      f"t {t:+5.2f} ex5 {ex5*1e4:+7.1f} 3xcost {(r-3*cost).mean()*1e4:+7.1f} | uncond mean {u.mean()*1e4:+6.1f} "
      f"med {np.median(u)*1e4:+6.1f} placebo pct {pct:4.1f}")


def main():
    P("GEO-HEADLINE (N 1115-1116) one look, run " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))
    tr99, tr95 = triggers(0.99), triggers(0.95)
    P(f"triggers 99th declustered {len(tr99)} (2008+: {(tr99 >= JUDGE[0]).sum()}), 95th {len(tr95)} (2008+: {(tr95 >= JUDGE[0]).sum()})")
    data = {s: bars(s) for s in ("SPY", "USO", "GLD", "XLE", "ITA")}

    P("\n== PRIMARY N 1115: long SPY close(T)->close(T+5), 99th, judge 2008-2026, cost 1bp/side")
    spy = data["SPY"]
    ev = legs(spy, tr99, "closeT", 5)
    for (a, b), lab in [(JUDGE, "judge 2008-26"), (HALVES[0], "half1 2008-16"), (HALVES[1], "half2 2017-26"),
                        (("1993-02-01", "2007-12-31"), "pre 1993-2007 (report)")]:
        e = ev[(ev.index >= a) & (ev.index <= b)]
        summ(e["r"], uncond(spy, a, b, "closeT", 5), lab)
    ej = ev[(ev.index >= JUDGE[0])]
    P(f"  gap-vs-trade (judge, SPY, mean / median bp): pre-day close(T-2)->close(T-1) {ej.pre.mean()*1e4:+.1f}/{ej.pre.median()*1e4:+.1f}, "
      f"gap close(T-1)->open(T) {ej.gap.mean()*1e4:+.1f}/{ej.gap.median()*1e4:+.1f}, day open(T)->close(T) "
      f"{ej.day.mean()*1e4:+.1f}/{ej.day.median()*1e4:+.1f}, trade close(T)->close(T+5) {ej.r.mean()*1e4:+.1f}/{ej.r.median()*1e4:+.1f}")

    P("\n== SECONDARY N 1116 (family, not judged on): entries x horizons, judge 2008-26")
    for sym in ("SPY", "USO", "GLD", "XLE", "ITA"):
        df = data[sym]
        a = max(pd.Timestamp(JUDGE[0]), df.index[300])
        for entry in ("openT", "closeT", "openT1"):
            for h in (1, 3, 5):
                e = legs(df, tr99, entry, h)
                e = e[e.index >= a]
                summ(e["r"], uncond(df, a, JUDGE[1], entry, h), f"{sym} {entry} h{h}")
        e = legs(df, tr99, "closeT", 5); e = e[e.index >= a]
        P(f"    {sym} gap/day/trade mean bp: {e.gap.mean()*1e4:+.1f} / {e.day.mean()*1e4:+.1f} / {e.r.mean()*1e4:+.1f}")
    P("\n  95th-pct trigger, SPY close(T)->close(T+5):")
    ev95 = legs(spy, tr95, "closeT", 5)
    for (a, b), lab in [(JUDGE, "95th judge"), (HALVES[0], "95th half1"), (HALVES[1], "95th half2")]:
        e = ev95[(ev95.index >= a) & (ev95.index <= b)]
        summ(e["r"], uncond(spy, a, b, "closeT", 5), lab)

    P("\n== Judge events (99th, SPY close(T)->close(T+5), USO same)")
    uso = legs(data["USO"], tr99, "closeT", 5)["r"]
    for T, row in ej.iterrows():
        P(f"  {row.D.date()} T {T.date()} SPY gap {row.gap*1e4:+6.0f} day {row.day*1e4:+6.0f} trade {row.r*1e4:+6.0f}bp "
          f"USO trade {uso.get(T, np.nan)*1e4:+6.0f}bp")

    n_yr = (tr99 >= JUDGE[0]).sum() / 18.84
    net = ej.r.mean() - 2 * SIDE
    P(f"\n== Ceiling (primary): {n_yr:.2f} ev/yr x {net*1e4:+.1f}bp net x 100% x capture 0.5 = {n_yr*net*0.5*100:+.2f} pp/yr "
      "at $2.3k / $10k / $25k alike (one ETF, whole shares ~0.3% rounding at $2.3k); gate +8pp at $10k.")
    P(f"DSR threshold at N {NPROG}: t* ~ {np.sqrt(2*np.log(NPROG)):.2f}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
