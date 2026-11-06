"""Study HMM-REBAL (N 1080-1081): Harvey-Mazzoleni-Melone 60/40 rebalancing front-run, published form, judged out of the
paper's sample (pre-registered in round1_prose.md, 2026-11-06).

    PYTHONPATH=. python3 -m research.sim.hmm_rebal fetch   # Yahoo SPY/IEF/^SP500TR adjclose + ^TNX (10y yield)
    PYTHONPATH=. python3 -m research.sim.hmm_rebal run     # the one look

A1 FULL  w = 0.5 * (-Th / 1.5%) + 0.5 * Cm ;  A2 CAL-ONLY w = Cm.  Return_{t+1} = w_t * (Rs - Rb)_{t+1}.
J1 SPY vs IEF 2023-03-20..last; J2 ^SP500TR vs ^TNX-built 10y par bond 1988-01-05..1997-09-09.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

from .ibs_voltilt import dsr, nw_t
from .tme_treasury import fetch_px

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/hmm_rebal"
OUT = ROOT / "data/research/program/hmm_rebal_out.txt"
COST = 2.0  # bp per side per leg
N_PROGRAM = 1081
DELTAS = np.round(np.arange(0, 26) / 1000, 4)  # 0.0% .. 2.5%


def fetch() -> None:
    D.mkdir(parents=True, exist_ok=True)
    for t, start in (("SPY", "1993-01-01"), ("IEF", "2002-07-01"), ("^SP500TR", "1987-12-01")):
        fetch_px(t, start).to_csv(D / f"px_{t.replace('^', '')}.csv")
    fetch_px("^TNX", "1987-12-01").to_csv(D / "px_TNX.csv")  # FRED timed out; ^TNX = CBOE 10y yield x1 (%)
    print("fetched", sorted(p.name for p in D.iterdir()))


def px(t: str) -> pd.Series:
    return pd.read_csv(D / f"px_{t}.csv", parse_dates=["date"]).set_index("date")["adjclose"]


def bond10(dates: pd.DatetimeIndex) -> pd.Series:
    y = pd.read_csv(D / "px_TNX.csv", parse_dates=["date"]).set_index("date")["close"]
    y = y.dropna().reindex(dates).ffill() / 100
    dy = y.diff()
    y0 = y.shift()
    dm = (1 - (1 + y0 / 2) ** -20) / y0  # modified duration of a 10y semiannual par bond
    conv = dm ** 2 + dm / (2 * (1 + y0 / 2))  # approx convexity
    return y0 / 252 - dm * dy + 0.5 * conv * dy ** 2


def pair(kind: str) -> pd.DataFrame:
    if kind == "etf":
        s, b = px("SPY"), px("IEF")
        df = pd.concat({"s": s, "b": b}, axis=1).dropna()
        return pd.DataFrame({"Rs": df.s.pct_change(), "Rb": df.b.pct_change()}).dropna()
    s = px("SP500TR").dropna()
    return pd.DataFrame({"Rs": s.pct_change(), "Rb": bond10(s.index)}).dropna()


def signals(R: pd.DataFrame) -> pd.DataFrame:
    idx = R.index
    # calendar position needs the month's remaining sessions: extend the live month with NYSE sessions to 2026-12-31
    # (holidays left in 2026: Nov 26, Dec 25) so the last partial month is not mistaken for a month end
    fut = pd.bdate_range(idx[-1] + pd.Timedelta(days=1), "2026-12-31")
    fut = fut[~fut.isin(pd.to_datetime(["2026-11-26", "2026-12-25"]))]
    full = idx.append(fut)
    ymf = full.to_period("M")
    pfe_full = pd.Series(1, index=full).groupby(ymf).cumsum()
    pfe_full = pfe_full.groupby(ymf).transform("max") - pfe_full
    ym = idx.to_period("M")
    pos_from_end = pfe_full.reindex(idx)  # 0 = last session
    last = pos_from_end == 0
    first = pd.Series(ym, index=idx) != pd.Series(ym, index=idx).shift(1)
    rs, rb = R.Rs.to_numpy(), R.Rb.to_numpy()
    n = len(R)
    wT = np.full(len(DELTAS), 0.6)
    wC = 0.6
    th = np.zeros(n); cal = np.zeros(n)
    lastv = last.to_numpy()
    for i in range(n):
        dT = wT * (1 + rs[i]) / (wT * (1 + rs[i]) + (1 - wT) * (1 + rb[i]))
        sT = dT - 0.6
        th[i] = sT.mean()
        wT = np.where(np.abs(sT) >= DELTAS - 1e-12, 0.6, dT)
        dC = wC * (1 + rs[i]) / (wC * (1 + rs[i]) + (1 - wC) * (1 + rb[i]))
        cal[i] = dC - 0.6
        wC = 0.6 if lastv[i] else dC
    S = pd.DataFrame({"th": th, "cal": cal, "pfe": pos_from_end.to_numpy(), "first": first.to_numpy()}, index=idx)
    cm = np.zeros(n)
    cal_tm4 = np.nan
    pfe, fst = S.pfe.to_numpy(), S["first"].to_numpy()
    for i in range(n):
        if fst[i] and np.isfinite(cal_tm4):
            cm[i] = np.sign(cal_tm4)
        if pfe[i] <= 4:
            cm[i] = np.sign(-cal[i])
        if pfe[i] == 4:
            cal_tm4 = cal[i]
    S["cm"] = cm
    S["w_full"] = 0.5 * (-S.th / 0.015) + 0.5 * S.cm
    S["w_cal"] = S.cm
    return S


def strat(R: pd.DataFrame, w: pd.Series, lag: int = 0, cost_mult: float = 1.0) -> pd.Series:
    x = (R.Rs - R.Rb)
    ww = w.shift(1 + lag)  # w_t applied to return t+1
    tc = 2 * COST * cost_mult / 1e4 * w.diff().abs().shift(1 + lag)  # trade at close t, both legs
    return (ww * x - tc).dropna()


def stats(r: pd.Series, tag: str) -> list[str]:
    if len(r) < 30:
        return [f"  {tag}: n {len(r)} (too few)"]
    a = r.to_numpy()
    ann = a.mean() * 252; vol = a.std() * np.sqrt(252)
    act = a[a != 0]
    ex5 = np.sort(a)[:-5].mean() * 252
    return [f"  {tag}: n {len(a)} active {len(act)} | ann {ann*100:+.2f}% vol {vol*100:.2f}% Sh {ann/vol if vol else 0:+.2f} "
            f"NW t {nw_t(a):+.2f} | ex-top-5d ann {ex5*100:+.2f}% | active-day mean {act.mean()*1e4 if len(act) else 0:+.2f}bp "
            f"median {np.median(act)*1e4 if len(act) else 0:+.2f}bp hit {np.mean(act>0)*100 if len(act) else 0:.0f}%"]


def placebo(R: pd.DataFrame, w: pd.Series, real: float, rng, k=500) -> float:
    x = (R.Rs - R.Rb)
    sh = []
    wv = w.to_numpy()
    for _ in range(k):
        s = rng.integers(21, len(wv) - 21)
        ws = pd.Series(np.roll(wv, s), index=w.index)
        r = strat(R, ws)
        sh.append(r.mean() / r.std())
    return float(np.mean(np.array(sh) < real) * 100)


def run() -> None:
    done = D / "run_done"
    if done.exists() and "--force-rerender" not in sys.argv:
        sys.exit("one look already taken")
    L: list[str] = ["Study HMM-REBAL (N 1080 A1 FULL, N 1081 A2 CAL-ONLY); cost 2bp/side/leg; w_t on close t -> close t+1"]
    E, P = pair("etf"), pair("idx")
    SE, SP = signals(E), signals(P)
    J1 = ("2023-03-20", None); J2 = ("1988-01-05", "1997-09-09")
    rng = np.random.default_rng(1080)
    for arm, col in (("A1 FULL", "w_full"), ("A2 CAL-ONLY", "w_cal")):
        L.append(f"\n=== {arm} ===")
        rE, rP = strat(E, SE[col]), strat(P, SP[col])
        j1, j2 = rE.loc[J1[0]:], rP.loc[J2[0]:J2[1]]
        L += stats(j1, "J1 SPY-IEF 2023-03-20..last (JUDGE)")
        L += stats(j2, "J2 SP500TR-10y 1988..1997-09 (JUDGE)")
        pooled = pd.concat([j1, j2])
        L.append(f"  pooled J1+J2 NW t {nw_t(pooled.to_numpy()):+.2f}  DSR(N={N_PROGRAM}) {dsr(pooled.to_numpy(), N_PROGRAM):.3f}")
        L += stats(strat(E, SE[col], cost_mult=3).loc[J1[0]:], "J1 3x cost")
        L += stats(strat(P, SP[col], cost_mult=3).loc[J2[0]:J2[1]], "J2 3x cost")
        L += stats(strat(E, SE[col], lag=1).loc[J1[0]:], "J1 lag-1 (sensitivity)")
        L += stats(strat(P, SP[col], lag=1).loc[J2[0]:J2[1]], "J2 lag-1 (sensitivity)")
        L += stats(j1.loc[:"2024-12-31"], "J1 half 2023-03..2024")
        L += stats(j1.loc["2025-01-01":], "J1 half 2025..last")
        L += stats(j2.loc[:"1992-12-31"], "J2 half 1988-92")
        L += stats(j2.loc["1993-01-01":], "J2 half 1993-97")
        # placebo on the judge windows
        pe = placebo(E.loc["2023-03-01":], SE[col].loc["2023-03-01":], j1.mean() / j1.std(), rng)
        pp = placebo(P.loc[:"1997-09-09"], SP[col].loc[:"1997-09-09"], j2.mean() / j2.std(), rng)
        L.append(f"  placebo (500 circular shifts) real Sharpe pct: J1 {pe:.0f}  J2 {pp:.0f}")
        L.append("  -- description only (touched / paper sample) --")
        L += stats(rP.loc["1997-09-10":"2023-03-17"], "proxy SP500TR-10y 1997-09..2023-03 (paper period)")
        L += stats(rE.loc["2002-08-01":"2015-12-31"], "ETF 2002-08..2015")
        L += stats(rE.loc["2016-01-01":"2023-03-17"], "ETF 2016..2023-03 (touched add. 34)")
        L += stats(rE.loc["2002-08-01":"2023-03-17"].pipe(lambda r: r[~((r.index >= "2008-09-01") & (r.index <= "2009-03-31")) &
                                                                   ~((r.index >= "2020-03-01") & (r.index <= "2020-03-31"))]),
                   "ETF 2002-23 ex GFC/Mar-2020")
    # descriptive: today
    L.append("\n=== Today (descriptive) ===")
    t = SE.tail(8)
    for d, row in t.iterrows():
        L.append(f"  {d.date()} Th {row.th*100:+.2f}pp Cal {row.cal*100:+.2f}pp Cm {row.cm:+.0f} w_full {row.w_full:+.2f} "
                 f"(+ = long SPY/short IEF)  pfe {row.pfe}")
    mtd = E.loc[E.index.to_period('M') == E.index[-1].to_period('M')]
    L.append(f"  MTD to {E.index[-1].date()}: SPY {((1+mtd.Rs).prod()-1)*100:+.2f}% IEF {((1+mtd.Rb).prod()-1)*100:+.2f}%")
    qtd = E.loc[E.index.to_period('Q') == E.index[-1].to_period('Q')]
    L.append(f"  QTD: SPY {((1+qtd.Rs).prod()-1)*100:+.2f}% IEF {((1+qtd.Rb).prod()-1)*100:+.2f}%")
    OUT.write_text("\n".join(L) + "\n")
    done.write_text("1")
    print("\n".join(L))


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
