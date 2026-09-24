"""Addendum 17: every version of the strategy in dollars, and what to expect.

    .venv/bin/python -m research.sim.versions

Same account for every version: $3,000 on 2021-07-06 plus $1,000 every 21
sessions, whole shares, tiered night costs (7.5-15bp/side). The window starts
in July 2021 because that is where the swing book's series begins.

Forward: 2,000 paired Monte Carlo paths from 2026-09-24 ($3k + $1k/month),
21-session blocks resampled from 2021-07 -> 2026-09, every version and SPY on
the SAME days. Three scenarios:
  A  history repeats (tiered costs)
  B  pessimistic costs (tier_hi, 7.5-25bp/side)
  C  the edge halves: night and intraday P&L x 0.5 (IBS and cash unchanged)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import book as B
from .data import DATA
from .validate import load_sim

START = pd.Timestamp("2021-07-06")
S2 = {"QQQ": 0.5, "SMH": 0.5}
VERSIONS = {  # label: (first live date, Params kwargs)
    "V1 daily book, IBS + night": ("2026-09-22", dict(noise_on=False)),
    "V2 + QQQ intraday (live 09-23)": ("2026-09-23", dict()),
    "V3 + tilt + QQQ/SMH (shipped 09-24)": ("2026-09-24", dict(tilt="live", noise=S2)),
    "V4 V3 + 1.3x overnight (gated)": ("when 50 exits prove costs",
                                       dict(tilt="live", noise=S2, night_w=0.65, ibs_w=0.65,
                                            noise_cap=1.35)),
}


def dollars(r: pd.Series, start=3000.0, monthly=1000.0) -> pd.DataFrame:
    E, dep, rows = start, start, []
    for i, (d, x) in enumerate(r.items()):
        if i and i % 21 == 0:
            E += monthly; dep += monthly
        E *= 1 + (x if np.isfinite(x) else 0.0)
        rows.append((d, E, dep))
    return pd.DataFrame(rows, columns=["date", "E", "dep"]).set_index("date")


def history(s, cost="tier"):
    days = s.days[s.days >= START]
    out = {}
    sw = pd.read_pickle(DATA / "swing_eq.pkl")["swing_1d"].pct_change().reindex(days).fillna(0)
    out["V0 swing book (paper, live cadence)"] = sw
    comps = {}
    for lab, (_, kw) in VERSIONS.items():
        df = s.replay(B.Params(night_cost=cost, **kw), dates=days)
        out[lab] = df.r
        comps[lab] = df
    out["SPY buy & hold"] = s.spy.reindex(days).fillna(0)
    return pd.DataFrame(out), comps


def year_table(R: pd.DataFrame) -> None:
    marks = [pd.Timestamp(x) for x in ("2021-12-31", "2022-12-30", "2023-12-29",
                                       "2024-12-31", "2025-12-31")] + [R.index[-1]]
    D = {c: dollars(R[c]) for c in R}
    dep = D[R.columns[0]].dep
    idx = [R.index[R.index <= m][-1] for m in marks]
    print(f"{'account value on':40s}" + "".join(f"{d:%Y-%m-%d}".rjust(12) for d in idx))
    print(f"{'  deposited':40s}" + "".join(f"${dep[d]:>10,.0f}" for d in idx))
    for c in R:
        print(f"{c:40s}" + "".join(f"${D[c].E[d]:>10,.0f}" for d in idx))
    print()
    print(f"{'calendar-year return':40s}" + "".join(f"{y:>9d}" for y in range(2021, 2027)))
    for c in R:
        yr = (1 + R[c]).groupby(R.index.year).prod() - 1
        print(f"{c:40s}" + "".join(f"{yr.get(y, np.nan)*100:8.1f}%" for y in range(2021, 2027)))
    print()
    for c in R:
        cagr, sh, dd = B.stats(R[c])
        print(f"{c:40s} TWR {cagr*100:5.1f}%/yr  Sharpe {sh:4.2f}  maxDD {dd*100:5.1f}%  "
              f"worst month {((1+R[c]).resample('ME').prod()-1).min()*100:5.1f}%")


def monte_carlo(R: pd.DataFrame, n_paths=2000, block=21, seed=7,
                horizons=(252, 756, 1260), start=3000.0, monthly=1000.0) -> dict:
    rng = np.random.default_rng(seed)
    X = R.to_numpy(); T = len(X)
    H = max(horizons)
    out = {h: [] for h in horizons}
    for _ in range(n_paths):
        starts = rng.integers(0, T - block, size=H // block + 1)
        path = np.vstack([X[s:s + block] for s in starts])[:H]
        E = np.full(X.shape[1], start)
        for t in range(H):
            if t and t % 21 == 0:
                E = E + monthly
            E = E * (1 + path[t])
            if t + 1 in out:
                out[t + 1].append(E.copy())
    return {h: np.array(v) for h, v in out.items()}


def mc_table(R: pd.DataFrame, label: str) -> None:
    res = monte_carlo(R)
    dates = {252: "2027-09", 756: "2029-09", 1260: "2031-09"}
    deposited = {252: 14_000, 756: 38_000, 1260: 62_000}
    spy = list(R.columns).index("SPY buy & hold")
    print(f"--- {label}")
    print(f"{'':40s}" + "".join(f"{dates[h]} (dep ${deposited[h]//1000}k)".rjust(26) for h in res))
    for j, c in enumerate(R.columns):
        cells = []
        for h, v in res.items():
            p10, p50, p90 = np.percentile(v[:, j], [10, 50, 90])
            beat = (v[:, j] > v[:, spy]).mean() if j != spy else np.nan
            cells.append(f"${p50/1e3:6.1f}k ({p10/1e3:4.0f}-{p90/1e3:4.0f})"
                         + (f" {beat:4.0%}" if j != spy else "     "))
        print(f"{c:40s}" + "".join(x.rjust(26) for x in cells))
    print("  median (p10-p90), then P(ahead of SPY)\n")


def main():
    s = load_sim()
    R, comps = history(s)
    print("=== history: $3k on 2021-07-06 + $1k every 21 sessions, tiered night costs ===\n")
    year_table(R)
    print("\n=== forward from 2026-09-24: $3k + $1k/month ===\n")
    mc_table(R, "A: history repeats (tiered costs)")
    Rb, _ = history(s, cost="tier_hi")
    mc_table(Rb, "B: pessimistic costs (tier_hi)")
    Rc = R.copy()
    for lab, df in comps.items():
        Rc[lab] = df.r_ibs + df.r_cash + 0.5 * (df.r_night + df.r_noise)
    Rc["V0 swing book (paper, live cadence)"] = 0.5 * R["V0 swing book (paper, live cadence)"]
    mc_table(Rc, "C: the edge halves (night + intraday P&L x 0.5)")


if __name__ == "__main__":
    main()
