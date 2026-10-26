"""Study GAP-NIGHT (round1_prose.md "## Amendment - Study GAP-NIGHT", N 1050): gap names bought at the close cross, sold at the next
open cross, vs the universe overnight premium. usage: PYTHONPATH=. .venv/bin/python -m research.sim.gap_night"""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
SH = Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/gap_night_out.txt"
JUDGE_END, H1_END = "2021-12-31", "2018-12-31"


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with OUT.open("a") as f: f.write(s + "\n")


def clus_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else float("nan")


def nstats(s: pd.Series) -> str:
    """per-night series (already EW within the night)."""
    x = s.dropna().to_numpy(float)
    if len(x) < 3: return f"n {len(x)}"
    top = np.sort(x)[-5:].sum()
    return f"nights {len(x)} mean {x.mean():+.1f} med {np.median(x):+.1f} hit {np.mean(x > 0):.2f} t {clus_t(x):.2f} ex-top5 {(x.sum() - top) / (len(x) - 5):+.1f}"


def main():
    if OUT.exists(): OUT.unlink()
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"])
    st = st[st.ticker.isin(ok)]; st["date"] = pd.to_datetime(st.date)
    st = st[st.date >= "2015-10-01"].sort_values(["ticker", "date"])
    g = st.groupby("ticker")
    st["pc"] = g.close.shift(1); st["pcu"] = g.closeunadj.shift(1)
    st["adv"] = (st.closeunadj * st.volume).groupby(st.ticker).transform(lambda x: x.shift(1).rolling(20, min_periods=15).median())
    st["gap"] = st.open / st.pc - 1
    st["dr"] = st.close / st.pc - 1
    st["ibs"] = (st.close - st.low) / (st.high - st.low).replace(0, np.nan)
    st["on"] = (g.open.shift(-1) / st.close - 1) * 1e4           # close d -> open d+1, bp
    st = st[(st.date >= "2016-01-01") & (st.date <= "2026-09-30") & (st.pcu >= 5) & (st.adv >= 5e7) & st.on.notna()]
    spy = pd.read_parquet(SH / "funds.parquet", columns=["ticker", "date", "open", "close"], filters=[("ticker", "==", "SPY")])
    spy["date"] = pd.to_datetime(spy.date); spy = spy.sort_values("date")
    spy["spy_on"] = (spy.open.shift(-1) / spy.close - 1) * 1e4
    spy = spy.set_index("date").spy_on
    night_pick = (st.dr <= -0.08) & (st.ibs < 0.10)
    univ = st.groupby("date").on.mean().rename("univ")
    univ_x = st[~night_pick].groupby("date").on.mean().rename("univ_xnight")
    gaps = st[st.gap.abs() >= 0.03]
    log(f"GAP-NIGHT (N 1050) form A: {len(gaps):,} gap name-days (|gap|>=3%, px>=5, ADV>=50M) on {gaps.date.nunique():,} nights, "
        f"{gaps.date.min().date()}..{gaps.date.max().date()}; universe {len(st):,} name-days; night-leg picks inside gaps {int((night_pick & (st.gap.abs() >= 0.03)).sum()):,}")
    arms = {"all": gaps, "up": gaps[gaps.gap > 0], "down": gaps[gaps.gap < 0], "3-5%": gaps[gaps.gap.abs() < 0.05],
            "5-10%": gaps[(gaps.gap.abs() >= 0.05) & (gaps.gap.abs() < 0.10)], "10%+": gaps[gaps.gap.abs() >= 0.10],
            "all ex-night-picks": gaps[~((gaps.dr <= -0.08) & (gaps.ibs < 0.10))]}
    for nm, a in arms.items():
        p = a.groupby("date").on.mean().rename("gap")
        d = pd.concat([p, univ, univ_x, spy], axis=1).dropna(subset=["gap"])
        d["x_univ"] = d.gap - d.univ; d["x_univx"] = d.gap - d.univ_xnight; d["x_spy"] = d.gap - d.spy_on
        b = np.polyfit(d.spy_on.fillna(0), d.gap, 1)[0] if len(d) > 10 else np.nan
        d["x_beta"] = d.gap - b * d.spy_on.fillna(0)
        J = d[d.index <= JUDGE_END]; T = d[d.index > JUDGE_END]
        log(f"\n=== arm {nm}: names/night median {a.groupby('date').size().median():.0f}; SPY-beta {b:.2f}")
        log(f"  JUDGE 2016-21 raw      {nstats(J.gap)}")
        log(f"  JUDGE 2016-21 x univ   {nstats(J.x_univ)}  | x univ-ex-night {nstats(J.x_univx)}")
        log(f"  JUDGE 2016-21 x SPY    {nstats(J.x_spy)}  | beta-adj {nstats(J.x_beta)}")
        log(f"    halves x univ: 2016-18 {nstats(J[J.index <= H1_END].x_univ)} | 2019-21 {nstats(J[J.index > H1_END].x_univ)}")
        log(f"    by year raw/x_univ: " + ", ".join(f"{y} {g.gap.mean():+.0f}/{g.x_univ.mean():+.0f}" for y, g in d.groupby(d.index.year)))
        log(f"  touched 2022-26 raw {nstats(T.gap)} | x univ {nstats(T.x_univ)}")
        if nm == "all":
            x = J.x_univ.dropna()
            ok = dict(mean=x.mean() >= 8, t=clus_t(x) >= 2, median=x.median() > 0, h1=J[J.index <= H1_END].x_univ.mean() > 0,
                      h2=J[J.index > H1_END].x_univ.mean() > 0, extop5=(x.sum() - np.sort(x)[-5:].sum()) / (len(x) - 5) > 0,
                      beta=J.x_beta.mean() > 0, xnight=J.x_univx.mean() >= 8)
            log(f"  GATES (arm all) {ok} -> {'PASS' if all(ok.values()) else 'KILL'}")
    log(f"\nuniverse overnight (EW, all eligible): 2016-21 {nstats(univ[univ.index <= JUDGE_END])}; 2022-26 {nstats(univ[univ.index > JUDGE_END])}; "
        f"SPY overnight 2016-21 {nstats(spy[(spy.index >= '2016-01-01') & (spy.index <= JUDGE_END)])}")
    # form B: PIT inplay pool G
    pools = pd.read_parquet(ROOT / "data/research/inplay/pools.parquet"); pools["date"] = pd.to_datetime(pools.date)
    G = pools[pools.pool == "G"][["date", "ticker"]].merge(st[["ticker", "date", "on", "gap"]], on=["ticker", "date"], how="inner")
    p = G.groupby("date").on.mean().rename("gap")
    d = pd.concat([p, univ, spy], axis=1).dropna(subset=["gap"]); d["x_univ"] = d.gap - d.univ
    log(f"\n=== form B (inplay pool G, PIT, 2019-26): {len(G):,} name-days matched; JUDGE 2019-21 raw {nstats(d[d.index <= JUDGE_END].gap)} | "
        f"x univ {nstats(d[d.index <= JUDGE_END].x_univ)}; touched 2022-26 raw {nstats(d[d.index > JUDGE_END].gap)} | x univ {nstats(d[d.index > JUDGE_END].x_univ)}")
    log("Disclosed: daily opens as the open cross, daily closes as the close cross; per-night EW; t = per-night (nights are the cluster).")


if __name__ == "__main__":
    main()
