"""$0 free-proxy falsification: signed dealer gamma -> SPY last-30-min continuation.

Pre-registration: research/drafts/shadow_dealer_gamma.md:11,14-18.
    SPY last-30-minute continuation on short-gamma days (enter 15:30 in the direction of the
    09:30-15:30 move, exit at the closing auction).
    Free proxy: SqueezeMetrics GEX in DIX.csv (data/research/gamma/DIX.csv, SPX GEX 2011-05+).
    Gate: >= +5bp net/trade at t >= 2 on an untouched window; kill if <= 0 net.

No optimization, no variants. Untouched judge window = 2016-2020 (user: prior probe was
2021-26). 2021-26 reported only for continuity/comparison and is the touched window.

Run:  PYTHONPATH=. .venv/bin/python -m research.sim.dealer_gamma_free
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
M1 = ROOT / "data" / "research" / "night" / "m1"
DIX = ROOT / "data" / "research" / "gamma" / "DIX.csv"
OUT = ROOT / "data" / "research" / "program" / "dealer_gamma_out.txt"

UNTOUCHED = (pd.Timestamp("2016-01-01"), pd.Timestamp("2020-12-31"))
TOUCHED = (pd.Timestamp("2021-01-01"), pd.Timestamp("2026-12-31"))

# Cost scenarios, bp round-trip. Realistic SPY: 15:30 market entry (half-spread ~0.5bp)
# + closing-auction exit (~0bp) => ~1bp. Stress = 3bp and 6bp.
COSTS = {"0bp": 0.0, "1bp": 1.0, "3bp": 3.0, "6bp": 6.0}


def load_gex() -> pd.DataFrame:
    g = pd.read_csv(DIX)
    g["date"] = pd.to_datetime(g["date"])
    g["date"] = pd.to_datetime(g["date"]).astype("datetime64[ns]")
    g = g[["date", "gex"]].dropna().sort_values("date").reset_index(drop=True)
    # No-lookahead: the value dated d is only used for d+1. A conservative lag-1 read.
    g["gex_lag1"] = g["gex"].shift(1)
    g["gex_lag1_date"] = g["date"].shift(1)
    return g


def load_spy_days() -> pd.DataFrame:
    rows = []
    for yr in range(2016, 2027):
        f = M1 / f"SPY_{yr}.parquet"
        if not f.exists():
            continue
        df = pd.read_parquet(f)
        ts = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York")
        df = df.assign(et=ts, hm=ts.dt.strftime("%H:%M"), d=ts.dt.date)
        rth = df[(df["hm"] >= "09:30") & (df["hm"] <= "16:00")]
        for d, grp in rth.groupby("d"):
            grp = grp.sort_values("et")
            o = grp[grp["hm"] == "09:30"]
            e = grp[grp["hm"] == "15:30"]
            x = grp[grp["hm"] == "16:00"]
            if len(o) == 0 or len(e) == 0 or len(x) == 0:
                continue  # half day / missing
            open_p = float(o["open"].iloc[0])
            entry = float(e["close"].iloc[0])
            exit_p = float(x["close"].iloc[0])
            if open_p <= 0 or entry <= 0:
                continue
            rows.append(
                dict(date=pd.Timestamp(d), open0930=open_p, entry1530=entry, close1600=exit_p)
            )
    r = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    r["date"] = pd.to_datetime(r["date"]).astype("datetime64[ns]")
    r["ret"] = r["close1600"] / r["entry1530"] - 1.0          # last-30-min (15:31->16:00) return
    r["move"] = r["entry1530"] / r["open0930"] - 1.0          # 09:30 -> 15:30 move
    r["dir"] = np.sign(r["move"])
    r["pnl"] = r["dir"] * r["ret"]                            # directional continuation
    r["c2c"] = r["close1600"] / r["close1600"].shift(1) - 1.0
    return r


def merge(gex: pd.DataFrame, days: pd.DataFrame) -> pd.DataFrame:
    # attach lag-1 GEX whose date is the prior trading day present in DIX
    right = (
        gex[["gex_lag1_date", "gex_lag1"]]
        .rename(columns={"gex_lag1_date": "date"})
        .dropna(subset=["date"])
        .sort_values("date")
    )
    m = pd.merge_asof(
        days.sort_values("date"),
        right,
        on="date",
        direction="backward",
        tolerance=pd.Timedelta("7D"),
    )
    # enforce the lag really is the prior session (not same day)
    m["short_gamma"] = m["gex_lag1"] < 0
    return m


def stats(x: pd.Series) -> dict:
    x = x.dropna()
    n = len(x)
    if n == 0:
        return dict(n=0, mean=np.nan, med=np.nan, t=np.nan, win=np.nan, worst=np.nan, best=np.nan)
    sd = x.std(ddof=1)
    t = x.mean() / (sd / np.sqrt(n)) if sd > 0 else np.nan
    return dict(
        n=n,
        mean=x.mean() * 1e4,
        med=x.median() * 1e4,
        t=t,
        win=(x > 0).mean(),
        worst=x.min() * 1e4,
        best=x.max() * 1e4,
    )


def ex_best(x: pd.Series, k: int) -> float:
    x = x.dropna().sort_values()
    if len(x) <= k:
        return np.nan
    return x.iloc[: len(x) - k].mean() * 1e4


def fmt(row: pd.Series) -> str:
    return (
        f"n {int(row.n):3d}  mean {row['mean']:+7.2f}bp  med {row['med']:+7.2f}  "
        f"t {row.t:+5.2f}  win {row.win*100:4.1f}%  worst {row.worst:+8.1f}  best {row.best:+8.1f}"
    )


def block(m: pd.DataFrame, label: str, lo, hi) -> None:
    d = m[(m["date"] >= lo) & (m["date"] <= hi)]
    sg = d[d["short_gamma"]]
    lg = d[~d["short_gamma"]]
    print(f"\n=== {label}  ({lo.date()}..{hi.date()}) ===")
    print(f"rows {len(d)}   short-gamma days {len(sg)} ({len(sg)/max(len(d),1)*100:.1f}%)")
    print("\n[gross, 0 cost]")
    print("  short-gamma :", fmt(pd.Series(stats(sg['pnl']))))
    print("  long-gamma  :", fmt(pd.Series(stats(lg['pnl']))))
    print("  all days    :", fmt(pd.Series(stats(d['pnl']))))
    print("\n[net of costs, short-gamma days]")
    for name, c in COSTS.items():
        s = stats(sg["pnl"] - c * 1e-4)
        print(f"  {name:>4} : {fmt(pd.Series(s))}")

    # annualized return on deployable capital (1x notional, idle cash on non-trade days)
    print("\n[annualized return on the account, 1x notional on short-gamma days, flat otherwise]")
    for name, c in COSTS.items():
        ann = (sg["pnl"] - c * 1e-4).groupby(sg["date"].dt.year).sum()
        print(f"  {name:>4} : " + "  ".join(f"{y}:{v*100:+.2f}%" for y, v in ann.items())
              + f"   | mean/yr {ann.mean()*100:+.2f}%")

    # max drawdown on the sequence of short-gamma trades (1x notional per trade)
    eq = (sg["pnl"] - 1e-4).cumsum()
    dd = (eq - eq.cummax())
    print(f"\n[maxDD on sequential short-gamma 1x trades, net 1bp]  maxDD {dd.min()*100:+.2f}%  "
          f"trades {len(sg)}  capital-deployed (trade-days x 100% notional) {len(sg)}")

    # robustness
    base = sg["pnl"] - COSTS["1bp"] * 1e-4
    print("\n[robustness, net 1bp]")
    print(f"  50% haircut of gross edge (net): {((sg['pnl']*0.5)-1e-4).mean()*1e4:+.2f}bp  t "
          f"{((sg['pnl']*0.5)-1e-4).mean()/(((sg['pnl']*0.5)-1e-4).std(ddof=1)/np.sqrt(len(sg))):+.2f}")
    print(f"  ex-best1 {ex_best(base,1):+.2f}bp   ex-best5 {ex_best(base,5):+.2f}bp   "
          f"ex-best10 {ex_best(base,10):+.2f}bp")

    # placebo: permute short-gamma membership within year, keep day set and direction
    rng = np.random.default_rng(7)
    obs = base.mean()
    picks = sg.index
    pool = d.index
    draws = []
    for _ in range(2000):
        sel = rng.choice(pool, size=len(picks), replace=False)
        draws.append((d.loc[sel, "pnl"] - COSTS["1bp"] * 1e-4).mean())
    draws = np.array(draws)
    print(f"  placebo (random day set of same size): pct of observed = {(draws < obs).mean()*100:.1f}%")


def regimes(m: pd.DataFrame, lo, hi) -> None:
    d = m[(m["date"] >= lo) & (m["date"] <= hi)].copy()
    sg = d[d["short_gamma"]].copy()
    if len(sg) == 0:
        return
    # 20d realized vol on close-to-close
    v = d["c2c"].rolling(20).std()
    d["vol20"] = v
    sg = d.loc[sg.index, ["date", "pnl", "vol20"]].dropna()
    print("\n[regimes within the window, short-gamma days, net 1bp]")
    if len(sg) >= 6:
        try:
            sg["volter"] = pd.qcut(sg["vol20"], 3, labels=["lowvol", "midvol", "hivol"])
            for k, g in sg.groupby("volter", observed=True):
                s = (g["pnl"] - 1e-4)
                print(f"  {k:>7}: n {len(g):3d}  mean {s.mean()*1e4:+7.2f}bp  t "
                      f"{s.mean()/(s.std(ddof=1)/np.sqrt(len(s))):+4.2f}")
        except Exception as e:
            print("  vol terciles:", e)
    ma200 = d["c2c"].add(1).cumprod().rolling(200).mean()
    px = d["c2c"].add(1).cumprod()
    bull = (px > ma200).reindex(sg.index)
    for lab, mask in [("above200MA", bull), ("below200MA", ~bull)]:
        g = sg[mask.fillna(False)]
        if len(g):
            s = (g["pnl"] - 1e-4)
            print(f"  {lab:>10}: n {len(g):3d}  mean {s.mean()*1e4:+7.2f}bp  t "
                  f"{s.mean()/(s.std(ddof=1)/np.sqrt(len(s))):+4.2f}")


def main() -> None:
    gex = load_gex()
    days = load_spy_days()
    m = merge(gex, days)
    lines = []
    import sys
    class Tee:
        def __init__(self, *fs): self.fs = fs
        def write(self, s):
            for f in self.fs: f.write(s)
        def flush(self):
            for f in self.fs: f.flush()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as fh:
        old = sys.stdout
        sys.stdout = Tee(old, fh)
        try:
            print("Dealer-gamma free-proxy falsification (SqueezeMetrics DIX.csv, GEX<0 = short gamma)")
            print("Rule: enter 15:31 in the direction of the 09:30->15:30 move, exit 16:00 auction.")
            print(f"SPY days {m['date'].min().date()}..{m['date'].max().date()};  "
                  f"GEX file {gex['date'].min().date()}..{gex['date'].max().date()}")
            print(f"short-gamma days overall: {int(m['short_gamma'].sum())} of {len(m)} "
                  f"({m['short_gamma'].mean()*100:.1f}%)")
            block(m, "UNTOUCHED judge window", *UNTOUCHED)
            regimes(m, *UNTOUCHED)
            block(m, "TOUCHED window (reference only)", *TOUCHED)
            print("\n=== year by year, short-gamma days, net 1bp ===")
            sg = m[m["short_gamma"]].copy()
            sg["net"] = sg["pnl"] - 1e-4
            for y, g in sg.groupby(sg["date"].dt.year):
                s = g["net"]
                t = s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 1 and s.std(ddof=1) > 0 else np.nan
                print(f"  {y}: n {len(g):2d}  mean {s.mean()*1e4:+7.2f}bp  t {t:+5.2f}  "
                      f"win {(s>0).mean()*100:4.0f}%  sum {s.sum()*100:+6.2f}%")
        finally:
            sys.stdout = old
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
