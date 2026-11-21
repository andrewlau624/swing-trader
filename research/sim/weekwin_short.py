"""WEEKWIN-SHORT (N 1223-1224, pre-registered in round1_prose.md 2026-11-20): short the top-10 5-day winners close -> next close.

    PYTHONPATH=. python3 -m research.sim.weekwin_short
Judge 1998-02..2010-12; 2011-20 reported only (touched by the D2a benchmark row).
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .exp_rl_universe import load_stocks, load_etfs, _next_ret, PRICE_MIN, ADV_MIN

OUT = pathlib.Path(__file__).resolve().parent / "weekwin_short_out.txt"
K, COST, BORROW, COST_X, BORROW_X = 10, 2.5e-4, 10e-4, 5e-4, 20e-4
J0, J1, R1 = "1998-02-01", "2010-12-31", "2020-12-31"


def tstat(x: np.ndarray, lags: int = 5) -> float:
    m = x.mean(); d = x - m; n = len(x)
    v = d @ d / n
    for L in range(1, lags + 1):
        v += 2 * (1 - L / (lags + 1)) * (d[L:] @ d[:-L]) / n
    return float(m / np.sqrt(v / n))


def main():
    b = load_stocks()
    sessions = np.unique(b.date.to_numpy("datetime64[ns]"))
    b = _next_ret(b, sessions)
    el = b[(b.pos >= 20) & (b.closeunadj >= PRICE_MIN) & (b.adv20 >= ADV_MIN) & np.isfinite(b.ret5)
           & (b.date >= J0) & (b.date <= R1)][["sidx", "date", "ticker", "code", "ret5", "nxt", "miss"]].copy()
    del b
    el["rk"] = el.groupby("sidx")["ret5"].rank(ascending=False, method="first")
    top = el[el.rk <= K]
    cnt = top.groupby("sidx").size(); top = top[top.sidx.isin(cnt.index[cnt == K])]
    day = top.groupby("sidx").agg(date=("date", "first"), bask=("nxt", "mean"), miss=("miss", lambda m: int((m > 0).sum())),
                                  r5=("ret5", "mean"))
    # turnover: equal weights 1/K; sum |dw| = (names entering + names leaving) / K
    sets = top.groupby("sidx")["code"].apply(frozenset)
    prev = sets.shift(1)
    turn = [1.0 if not isinstance(p, frozenset) else (len(s - p) + len(p - s)) / K for s, p in zip(sets, prev)]
    day["turn"] = turn
    spy = _next_ret(load_etfs(["SPY"]), sessions)
    spy = spy.set_index("sidx")["nxt"]
    day["spy"] = spy.reindex(day.index).fillna(0.0).to_numpy()
    # placebo pool: per-session eligible next returns
    elg = el.sort_values("sidx")
    pool = {s: g.to_numpy() for s, g in elg.groupby("sidx")["nxt"]}
    del el, elg
    day["short"] = -day.bask
    fitb = day[(day.date >= J0) & (day.date <= "2004-12-31")]
    beta = float(np.cov(fitb.bask, fitb.spy)[0, 1] / fitb.spy.var())

    def net(d, c, br):
        return d.short - c * d.turn - br

    L = [f"WEEKWIN-SHORT: top-{K} 5-day winners, short close->close, $5+/ADV $10M+ SEP common (delisted kept); beta(1998-2004) {beta:.2f}"]
    rng = np.random.default_rng(0)
    for tag, d in (("JUDGE 1998-02..2010", day[(day.date >= J0) & (day.date <= J1)]),
                   ("REPORT 2011-20 (touched)", day[(day.date > J1) & (day.date <= R1)])):
        L.append(f"\n=== {tag}: {len(d)} days, missing next bar {int(d.miss.sum())} of {len(d) * K} slots, mean ret5 of picks {d.r5.mean():.1%}, turnover {d.turn.mean():.2f}/day")
        L.append(f"  gross short {d.short.mean() * 1e4:+.1f}bp/day (median {d.short.median() * 1e4:+.1f}, t {tstat(d.short.to_numpy()):+.2f}); SPY {d.spy.mean() * 1e4:+.1f}")
        # placebo (gross short of 10 random eligible names)
        pl = np.zeros(200)
        for s in d.index:
            p = pool[s]
            pl += -p[rng.integers(0, len(p), (200, K))].mean(axis=1)
        pl /= len(d)
        pct = (pl < d.short.mean()).mean() * 100
        L.append(f"  placebo random-10 gross short mean {pl.mean() * 1e4:+.1f}bp, 95th {np.percentile(pl, 95) * 1e4:+.1f}; real at pct {pct:.1f}")
        for name, hedge in (("WW-S1 raw (N 1223)", 0.0), ("WW-S2 SPY-hedged (N 1224)", beta)):
            x = net(d, COST, BORROW) + hedge * d.spy
            xs = net(d, COST_X, BORROW_X) + hedge * d.spy
            h1, h2 = x[d.date <= "2004-12-31"], x[d.date > "2004-12-31"]
            srt = np.sort(x.to_numpy())
            eq = np.cumprod(1 + 0.5 * x.to_numpy()); dd = (eq / np.maximum.accumulate(eq) - 1).min()
            y08 = x[d.date.dt.year == 2008].mean() * 1e4; y02 = x[(d.date.dt.year >= 2000) & (d.date.dt.year <= 2002)].mean() * 1e4
            t = tstat(x.to_numpy())
            L.append(f"  {name}: net {x.mean() * 1e4:+.1f}bp/day t {t:+.2f} | halves {h1.mean() * 1e4:+.1f} / {h2.mean() * 1e4:+.1f} | median {x.median() * 1e4:+.1f}"
                     f" hit {(x > 0).mean():.2f} | ex-top5 {srt[:-5].mean() * 1e4:+.1f} | shock {xs.mean() * 1e4:+.1f} | worst day {srt[0] * 100:+.1f}%"
                     f" | maxDD@0.5x {dd:.0%} | 2000-02 {y02:+.1f} 2008 {y08:+.1f}")
            if tag.startswith("JUDGE"):
                g = [x.mean() > 0 and t >= 2, h1.mean() > 0 and h2.mean() > 0, x.median() > 0, srt[:-5].mean() > 0,
                     xs.mean() > 0, pct >= 95, x.mean() >= 15e-4]
                L.append("    GATES: " + " | ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in zip(
                    ("t>=2", "halves", "median", "ex-top5", "shock", "placebo95", "ceiling15bp"), g))
                         + f" -> {'PASS' if all(g) else 'KILL'}")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
