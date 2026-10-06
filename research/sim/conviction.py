"""Study CC - Conviction Concentration / Leverage: the RGTI $14-$16 level test.

    PYTHONPATH=. .venv/bin/python -m research.sim.conviction > data/research/program/conviction_out.txt

PRE-REGISTERED (research/drafts/study_conviction.md, round1_prose.md N 820 -> 821), one look.
Exploratory only: no deployment, no margin change, no live trade. The band is hindsight-chosen
by the user, so no split is a clean OOS; the judge is conditional-vs-unconditional + band placebo
+ chronological split. If the primary FAILs, the branch stops (no search expansion, no leverage).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import book as B

ROOT = Path(__file__).resolve().parents[2]
BARS = ROOT / "data" / "cache" / "bars"
OUT = ROOT / "data" / "research" / "program"
BAND = (14.00, 16.00)
ADV_FLOOR = 5e6
RNG = np.random.default_rng(20261005)
BANDS = [(8, 10), (10, 12), (12, 14), (14, 16), (16, 18), (18, 20), (20, 22)]


def px(sym: str) -> pd.DataFrame:
    d = pd.read_parquet(BARS / f"{sym}.parquet").sort_index()
    d = d[~d.index.duplicated(keep="last")]
    d["dv"] = d["close"] * d["volume"]
    d["adv20"] = d["dv"].rolling(20).median()
    d["ret"] = d["close"] / d["close"].shift(1) - 1
    return d


def stats(x: np.ndarray) -> dict:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n == 0:
        return dict(n=0)
    srt = np.sort(x)
    ex5 = srt[:-5].mean() if n > 5 else np.nan
    se = x.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return dict(n=n, win=(x > 0).mean(), mean=x.mean(), med=np.median(x), worst=x.min(),
                best=x.max(), p5=np.percentile(x, 5), p95=np.percentile(x, 95),
                sd=x.std(ddof=1), t=(x.mean() / se if se else np.nan), ex5=ex5)


def line(lab: str, s: dict) -> str:
    if s.get("n", 0) == 0:
        return f"  {lab:<34} n 0"
    return (f"  {lab:<34} n {s['n']:>4}  win {s['win']*100:5.1f}%  mean {s['mean']*1e4:+7.1f}bp  "
            f"med {s['med']*1e4:+7.1f}  sd {s['sd']*1e4:6.1f}  worst {s['worst']*100:+7.1f}%  "
            f"p5 {s['p5']*1e4:+7.1f}  t {s['t']:+5.2f}  ex5 {s['ex5']*1e4:+7.1f}")


def sec(t: str) -> None:
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def main() -> None:
    g = px("RGTI")
    g["entry"] = g["open"].shift(-1)
    g["exit_c"] = g["close"].shift(-1)
    g["exit_o"] = g["open"].shift(-1)          # same as entry; placeholder for open-exit variant
    g["open_c"] = g["close"].shift(-1) / g["close"] - 1        # overnight+day (enter close d)
    g["day_gap"] = g["open"].shift(-1) / g["close"] - 1        # overnight gap into entry
    # raw long->close next session; low is the worst excursion while long
    g["gross"] = g["exit_c"] / g["entry"] - 1
    g["worst_path"] = g["low"].shift(-1) / g["entry"] - 1
    g["gross2"] = g["close"].shift(2) / g["entry"] - 1         # hold two sessions
    g["r0"] = g["ret"]                                        # day-d return (conditioning)

    # cost per side at entry price / adv, tier and tier_hi
    adv = g["adv20"].values
    entry = g["entry"].values
    g["c_tier"] = B.cost_bps("tier", entry, adv) / 1e4
    g["c_hi"] = B.cost_bps("tier_hi", entry, adv) / 1e4
    g["net"] = g["gross"] - 2 * g["c_tier"]
    g["net_hi"] = g["gross"] - 2 * g["c_hi"]

    liquid = (g["adv20"] >= ADV_FLOOR) & g["gross"].notna()
    inband = liquid & (g["close"] >= BAND[0]) & (g["close"] <= BAND[1])
    d = g[liquid].copy()

    print("STUDY CC - Conviction Concentration / Leverage: RGTI $14-$16")
    print("PRE-REGISTERED one look (study_conviction.md; round1_prose.md N 820 -> 821).")
    print(f"RGTI {g.index.min().date()}..{g.index.max().date()}  {len(g)} sessions; band {BAND}; "
          f"adv20 floor ${ADV_FLOOR/1e6:.0f}M; entry open(d+1), exit close(d+1); tier 10bp, tier_hi 15bp/side.")

    # ---- 3/4/5/7: signal stats -------------------------------------------------
    sec("1-3. RGTI $14-$16: occurrences, win rate, distribution (pre-registered rule)")
    cond = stats(g.loc[inband, "net"].values)
    unc = stats(g.loc[liquid, "net"].values)
    unc24 = stats(g.loc[liquid & (g.index >= "2024-01-01"), "net"].values)
    print(line("conditional (in band)", cond))
    print(line("unconditional (liquid, all yrs)", unc))
    print(line("unconditional (liquid, 2024-26)", unc24))
    print(f"  -> excess conditional - uncond(all): {(cond['mean']-unc['mean'])*1e4:+.1f}bp/trade "
          f"(gross {(g.loc[inband,'gross'].mean()-g.loc[liquid,'gross'].mean())*1e4:+.1f}bp)")
    print(f"  -> excess conditional - uncond(2024-26): {(cond['mean']-unc24['mean'])*1e4:+.1f}bp "
          f"-- the honest same-period comparison")

    net = g.loc[inband, "net"]
    print(f"  max consecutive in-band run: {_maxrun(inband.values)} sessions")
    print(f"  signals: {int(inband.sum())}; distinct in-band episodes: {_episodes(inband.values)}")

    sec("4-6. Gross vs net, cost shock, and the same rule at tier_hi")
    for lab, col in [("gross (no cost)", "gross"), ("net @ tier", "net"), ("net @ tier_hi", "net_hi")]:
        print(line(lab, stats(g.loc[inband, col].values)))
    print(line("net @ tier, fresh cross only", stats(g.loc[inband & _fresh(inband), "net"].values)))
    print(line("net @ tier, 2-session hold", stats(
        g.loc[inband, "gross2"].values - 2 * g.loc[inband, "c_tier"].values)))

    sec("6/9. Distribution detail and conditional slices")
    q = g.loc[inband, "net"]
    print(f"  P5..P95: {np.percentile(q,5)*1e4:+.0f} .. {np.percentile(q,95)*1e4:+.0f} bp; "
          f"skew {q.skew():+.2f}; kurtosis {q.kurtosis():+.1f}")
    print(f"  share > +5%: {(q>0.05).mean()*100:.0f}%;  share < -5%: {(q<-0.05).mean()*100:.0f}%;  "
          f"share < -10%: {(q<-0.10).mean()*100:.0f}%")
    print("\n  by half / year (in-band net):")
    for lo, hi, tag in [("2021-01-01", "2023-12-31", "2021-23"), ("2024-01-01", "2026-12-31", "2024-26")]:
        m = inband & (g.index >= lo) & (g.index <= hi)
        print("   " + line(tag, stats(g.loc[m, "net"].values))[1:])
    for yr in sorted(set(g.index[inband].year)):
        m = inband & (g.index.year == yr)
        print("   " + line(str(yr), stats(g.loc[m, "net"].values))[1:])
    print("\n  by trailing-20d RGTI vol tercile (in-band):")
    vol = g["close"].pct_change().rolling(20).std().shift(1)
    t = vol.loc[inband].dropna()
    if len(t) > 6:
        qs = np.quantile(t, [1/3, 2/3])
        for lab, m in [("low vol", t <= qs[0]), ("mid vol", (t > qs[0]) & (t <= qs[1])), ("high vol", t > qs[1])]:
            print("   " + line(lab, stats(g.loc[m.index[m.values], "net"].values))[1:])
    print("\n  by day-d return bucket (in-band):")
    for lab, m in [("d down <= -5%", g["r0"] <= -0.05), ("d flat (-5%,+5%)", g["r0"].abs() < 0.05),
                   ("d up >= +5%", g["r0"] >= 0.05)]:
        mm = inband & m
        print("   " + line(lab, stats(g.loc[mm, "net"].values))[1:])
    print(f"\n  overnight gap into entry: mean {g.loc[inband,'day_gap'].mean()*1e4:+.1f}bp, "
          f"worst {g.loc[inband,'day_gap'].min()*100:+.1f}%, p5 {np.percentile(g.loc[inband,'day_gap'],5)*100:+.1f}%")
    print(f"  worst intraday excursion while long: {g.loc[inband,'worst_path'].min()*100:+.1f}% "
          f"(p5 {np.percentile(g.loc[inband,'worst_path'],5)*100:+.1f}%)")
    print(f"  liquidity at signal: median adv20 ${g.loc[inband,'adv20'].median()/1e6:.0f}M; "
          f"median signal-day $vol ${(g.loc[inband,'close']*g.loc[inband,'volume']).median()/1e6:.0f}M")

    sec("2. ARTIFACT CONTROLS")
    print("B. equal-width band placebo (same liquidity floor, same rule):")
    for lo, hi in BANDS:
        m = liquid & (g["close"] >= lo) & (g["close"] <= hi)
        s = stats(g.loc[m, "net"].values)
        star = "   <-- prereg band" if (lo, hi) == BAND else ""
        print("   " + line(f"[{lo},{hi}]", s)[1:] + star)
    print("\nD/E. random-entry placebo (days drawn from the same liquid pool, 2000 draws):")
    pool = g.loc[liquid, "net"].values
    n = int(inband.sum())
    draws = np.array([RNG.choice(pool, n, replace=True).mean() for _ in range(2000)])
    pct = (draws < cond["mean"]).mean()
    print(f"   conditional mean {cond['mean']*1e4:+.1f}bp vs placebo mean {draws.mean()*1e4:+.1f}bp, "
          f"sd {draws.std()*1e4:.1f}bp; percentile of conditional {pct*100:.1f}%")
    print("\nF. hidden market exposure (same-window SPY/QQQ open->close):")
    for sym in ("SPY", "QQQ"):
        b = px(sym)
        j = pd.DataFrame({"r": g.loc[inband, "gross"], "d": g.index[inband]}).set_index("d")
        sb = (b["close"] / b["open"] - 1).reindex(j.index)
        j = j.assign(m=sb.values).dropna()
        beta = np.polyfit(j["m"], j["r"], 1)
        print(f"   RGTI in-band vs {sym}: beta {beta[0]:+.2f}, alpha {beta[1]*1e4:+.1f}bp "
              f"(uncond RGTI gross {(g.loc[liquid,'gross'].mean())*1e4:+.1f}bp)")

    sec("13. JUDGED PRIMARY vs pre-registered gate")
    c, u = cond["mean"], unc["mean"]
    h1 = stats(g.loc[inband & (g.index <= "2023-12-31"), "net"].values)
    h2 = stats(g.loc[inband & (g.index >= "2024-01-01"), "net"].values)
    gates = {
        "cond net >= +50bp": c >= 0.005,
        "cond > uncond": c > u,
        "positive 2021-23": h1.get("mean", -1) > 0,
        "positive 2024-26": h2.get("mean", -1) > 0,
        "ex-best-5 > 0": cond["ex5"] > 0,
        "positive at tier_hi": stats(g.loc[inband, "net_hi"].values)["mean"] > 0,
    }
    for k, v in gates.items():
        print(f"   {'PASS' if v else 'FAIL'}  {k}")
    passed = sum(gates.values())
    if c <= 0 or not gates["positive 2024-26"] or not gates["ex-best-5 > 0"]:
        verdict = "REJECTED"
    elif all(gates.values()):
        verdict = "VALIDATED"
    elif passed >= 4:
        verdict = "PROMISING"
    else:
        verdict = "REJECTED"
    print(f"   -> {passed}/6 gates; VERDICT: {verdict}")

    sec("14. LEVERAGE (only meaningful if at least PROMISING)")
    if verdict == "REJECTED":
        print("   Primary REJECTED -> per the pre-registration the leverage study is NOT run "
              "(leverage must not make a weak edge look profitable).")
    else:
        _leverage(g.loc[inband, "net"].values, g.loc[inband, "worst_path"].values)

    sec("MECHANISM / NOTES")
    print("""   The band is hindsight-chosen by the user (RGTI trades ~$16 now): tests D/E cannot be
   fully cleared. No PIT earnings calendar for RGTI -> earnings conditioning is DATA-LIMITED.
   Single name, alive: survivorship is structural (we chose a winner). Capacity: one name at
   $2-25k is fine; the binding limit is the signal frequency and the tail, not ADV.""")


def _fresh(mask: pd.Series) -> pd.Series:
    prev = mask.shift(1).fillna(False).astype(bool)
    return mask & ~prev


def _maxrun(a: np.ndarray) -> int:
    best = cur = 0
    for v in a:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def _episodes(a: np.ndarray) -> int:
    return int(np.sum(a & ~np.r_[False, a[:-1]]))


def _leverage(net: np.ndarray, worst: np.ndarray) -> None:
    rate = 0.08
    print(f"   {'L':>4} {'fin/trade':>10} {'final x':>9} {'maxDD':>8} {'worst day':>10} "
          f"{'forced-liq':>11} {'ruin':>6}")
    for L in (1.0, 1.5, 2.0, 3.0, 4.0):
        borrow = (L - 1) * rate / 252
        eq, peak, mdd, liq = 1.0, 1.0, 0.0, 0
        for r, w in zip(net, worst):
            # forced liquidation if intraday worst breaches 25% maintenance
            if 1 + L * w - borrow <= 0.25:
                liq += 1
            eq *= max(1 + L * r - borrow, 0.0)
            peak = max(peak, eq)
            mdd = max(mdd, (peak - eq) / peak if peak else 0)
        ruin = int((1 + L * net.min() - borrow) <= 0)
        print(f"   {L:>4} {borrow*1e4:>9.1f}bp {eq:>8.2f}x {mdd*100:>7.1f}% "
              f"{(L*net.min()-borrow)*100:>9.1f}% {liq:>11} {ruin:>6}")


if __name__ == "__main__":
    main()
