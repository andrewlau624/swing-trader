"""NOISE-GATE (N 934): realized-intraday-vol regime gate on the PROD noise leg. Pre-reg round1_prose.md "Study NOISE-GATE".

    PYTHONPATH=. .venv/bin/python -m research.sim.noise_gate    # -> data/research/program/noise_gate_out.txt
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from research.sim.noise_recent import W, stats, trades_for
from swingtrader.daybook import shadow as sh

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/noise_gate_out.txt"
LAG, COST, VOL_N, MED_N = 30, 0.5, 20, 252
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def gate_series(S_qqq: dict) -> pd.Series:
    """True on sessions whose trailing-20 realized intraday vol (to d-1) exceeds its trailing-252 median (to d-1)."""
    days = sorted(S_qqq)
    oc = pd.Series([S_qqq[d]["close"][-1] / S_qqq[d]["open"][0] - 1.0 for d in days], index=pd.DatetimeIndex(days))
    rv = oc.rolling(VOL_N).std().shift(1)                       # ends d-1
    med = rv.rolling(MED_N, min_periods=126).median().shift(1)  # ends d-2 of the rv series = uses rv through d-1
    return (rv > med).where(med.notna())


def sharpe_of(T: pd.DataFrame, days: pd.DatetimeIndex) -> dict | None:
    return stats(T, days, COST) if len(T) else None


def main() -> int:
    S = {s: sh._sessions_cache(s, 14, None) for s in W}
    T = pd.concat([trades_for(S[s], s, W[s], LAG) for s in W]).reset_index(drop=True)
    T["date"] = pd.to_datetime(T["date"])
    alld = pd.DatetimeIndex(sorted(set(S["QQQ"]) & set(S["SMH"])))
    g = gate_series(S["QQQ"]).reindex(alld)
    known = g.notna()
    alld, g = alld[known.to_numpy()], g[known].astype(bool)
    T = T[T["date"].isin(alld)]
    on_days, off_days = alld[g.to_numpy()], alld[~g.to_numpy()]
    T_on, T_off = T[T["date"].isin(on_days)], T[T["date"].isin(off_days)]
    say(f"NOISE-GATE: lag {LAG}, {COST}bp/fill; sessions {len(alld)} ({alld[0].date()}..{alld[-1].date()}), "
        f"ON {len(on_days)} ({len(on_days)/len(alld):.0%}); trades all {len(T)} ON {len(T_on)} OFF {len(T_off)}")

    def row(lab, Tx, dx):
        s = sharpe_of(Tx, dx)
        if s is None:
            say(f"  {lab:28s} (no trades)"); return None
        say(f"  {lab:28s} n {s['n']:5d} mean {s['mean']:+6.2f}bp med {s['med']:+6.2f} t {s['t']:5.2f} hit {s['hit']:4.1f}% "
            f"Sharpe {s['sharpe']:+5.2f} ann {s['ann']:+5.1f}%  trades/day {s['n']/max(len(dx),1):.2f}")
        return s

    res = {}
    for per, lo, hi in (("all", "2016-01-01", "2027-01-01"), ("2016-20", "2016-01-01", "2021-01-01"),
                        ("2021-26", "2021-01-01", "2027-01-01"), ("2025-26", "2025-01-01", "2027-01-01")):
        m = (alld >= lo) & (alld < hi)
        d_all, d_on, d_off = alld[m], on_days[(on_days >= lo) & (on_days < hi)], off_days[(off_days >= lo) & (off_days < hi)]
        say(f"\n== {per}: sessions {len(d_all)}, ON {len(d_on)} ({len(d_on)/max(len(d_all),1):.0%})")
        res[per] = dict(all=row("ungated", T[T["date"].isin(d_all)], d_all),
                        on=row("ON (vol > 1y median)", T_on[T_on["date"].isin(d_on)], d_on),
                        off=row("OFF", T_off[T_off["date"].isin(d_off)], d_off))
    say("\nby year: ON share | ungated Sharpe | ON Sharpe | OFF Sharpe | OFF mean bp")
    for y in range(alld[0].year, alld[-1].year + 1):
        dy = alld[alld.year == y]
        if not len(dy):
            continue
        oy, fy = on_days[on_days.year == y], off_days[off_days.year == y]
        sa, so, sf = (sharpe_of(T[T["date"].isin(dy)], dy), sharpe_of(T_on[T_on["date"].isin(oy)], oy),
                      sharpe_of(T_off[T_off["date"].isin(fy)], fy))
        f = lambda s, k: f"{s[k]:+.2f}" if s else "  --"
        say(f"  {y}: {len(oy)/len(dy):4.0%} | {f(sa,'sharpe')} | {f(so,'sharpe')} | {f(sf,'sharpe')} | {f(sf,'mean')}")
    # placebo: random 50% day masks
    rng = np.random.default_rng(934)
    gap = res["all"]["on"]["sharpe"] - (res["all"]["off"]["sharpe"] if res["all"]["off"] else 0.0)
    gaps = []
    for _ in range(200):
        mask = rng.random(len(alld)) < 0.5
        d1, d0 = alld[mask], alld[~mask]
        s1, s0 = sharpe_of(T[T["date"].isin(d1)], d1), sharpe_of(T[T["date"].isin(d0)], d0)
        gaps.append((s1["sharpe"] if s1 else 0) - (s0["sharpe"] if s0 else 0))
    pct = (np.array(gaps) < gap).mean() * 100
    say(f"\nplacebo: ON-OFF Sharpe gap {gap:+.2f} beats {pct:.0f}% of 200 random 50% masks (random gap p95 {np.percentile(gaps, 95):+.2f})")
    a, on, off = res["all"]["all"], res["all"]["on"], res["all"]["off"]
    on1, on2 = res["2016-20"]["on"], res["2021-26"]["on"]
    checks = dict(on_sharpe_h1=on1["sharpe"] >= 0.8, on_sharpe_h2=on2["sharpe"] >= 0.8, off_mean_le0=off["mean"] <= 0,
                  on_mean_4bp=on["mean"] >= 4.0, on_beats_ungated=on["sharpe"] >= a["sharpe"] + 0.3, placebo95=pct >= 95)
    kill = on["mean"] <= off["mean"] or min(on1["sharpe"], on2["sharpe"]) < 0.3
    verdict = "PASS" if all(checks.values()) else ("KILL" if kill else "WEAK")
    say(f"\nGATE N 934: {verdict}  " + " ".join(f"{k}={'Y' if v else 'n'}" for k, v in checks.items()))
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
