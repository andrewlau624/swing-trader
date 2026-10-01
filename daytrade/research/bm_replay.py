"""Study Lab-BM: drift after forward-split ex-dates (round1_prose.md Lab Round 37). Raw SIP daily bars (Lab-BI 2016-22 +
Lab-AU 2021-26 caches), regular sessions; SPY adjusted (Lab-BK cache) for the excess.

  python -m daytrade.research.bm_replay
"""
from __future__ import annotations

import json
import math
import random
from collections import defaultdict

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A

OUT = DATA / "research" / "bm"
KS = (2, 3, 4, 5, 10, 20)
H = 60
SPLIT = "2022-01-01"


def raw_daily():
    a = pd.read_parquet(DATA / "research" / "bi" / "raw.parquet")[["symbol", "date", "open", "close", "volume"]]
    b = pd.read_parquet(DATA / "research" / "au" / "daily_ohlc.parquet")[["symbol", "date", "open", "close", "volume"]]
    x = pd.concat([a[a.date < pd.Timestamp("2021-11-01")], b[b.date >= pd.Timestamp("2021-11-01")]])
    return x.drop_duplicates(["symbol", "date"]).sort_values(["symbol", "date"])


def split_factor(ratio):
    for k in KS:
        if abs(ratio * k - 1) <= 0.06:
            return k
    return None


def run():
    d = raw_daily()
    spy = pd.read_parquet(DATA / "research" / "bk" / "daily.parquet")["SPY"].dropna()
    si = {t: i for i, t in enumerate(spy.index)}
    keep = set(A.universe())
    rows, pools = [], {}
    for sym, g in d[d.symbol.isin(keep)].groupby("symbol", sort=False):
        g = g.reset_index(drop=True)
        if len(g) < H + 30:
            continue
        pc = g.close.shift(1)
        ratio = (g.open / pc).values
        adv = (g.close * g.volume).shift(1).rolling(20, min_periods=20).mean().values
        # forward-split factor per day (to chain within holding windows)
        fac = np.array([split_factor(r) or 1 for r in np.nan_to_num(ratio, nan=1.0)], dtype=float)
        cum = np.cumprod(fac)                       # price x cum = split-adjusted level (forward splits only)
        adjc = g.close.values * cum
        def window_ret(i):
            j = i + H
            if j >= len(g) or g.date.iat[i] not in si or g.date.iat[j] not in si:
                return None
            ret = adjc[j] / adjc[i] - 1
            mkt = spy.iat[si[g.date.iat[j]]] / spy.iat[si[g.date.iat[i]]] - 1
            return (ret - mkt) * 1e4
        ev_idx = []
        for i in range(21, len(g) - 1):
            k = split_factor(ratio[i]) if np.isfinite(ratio[i]) else None
            if k and g.open.iat[i] >= 5 and adv[i] >= 5e6 and pd.Timestamp("2017-01-01") <= g.date.iat[i] <= pd.Timestamp("2026-09-30"):
                w = window_ret(i)
                if w is not None:
                    rows.append({"sym": sym, "day": str(g.date.iat[i].date()), "k": k, "ex": w})
                    ev_idx.append(i)
        if ev_idx:
            bad = set()
            for i in ev_idx:
                bad |= set(range(i - 5, i + H + 1))
            opts = [window_ret(i) for i in range(21, len(g) - H - 1, 3)
                    if i not in bad and g.date.iat[i] >= pd.Timestamp("2017-01-01")]
            pools[sym] = [o for o in opts if o is not None] or [0.0]
    t = pd.DataFrame(rows)
    res = {"events": len(t), "by_k": t.k.value_counts().to_dict()}
    for mult, c in (("1x", 10), ("2x", 20)):
        net = t.ex - 2 * c
        res[mult] = {"all": float(net.mean()), "h1": float(net[t.day < SPLIT].mean()), "h2": float(net[t.day >= SPLIT].mean()),
                     "n_h1": int((t.day < SPLIT).sum()), "n_h2": int((t.day >= SPLIT).sum())}
        if mult == "1x":
            x = net.values; m = x.mean()
            cl = defaultdict(float)
            for mo, v in zip(t.day.str[:7], x):
                cl[mo] += v - m
            res["t_month"] = float(m / (math.sqrt(sum(z * z for z in cl.values())) / len(x)))
            res["median_1x"] = float(np.median(x))
            res["without_best10"] = float(np.sort(x)[:-10].mean())
            res["by_year_1x"] = {y: [float(v.mean()), len(v)] for y, v in pd.Series(x, index=t.day.str[:4]).groupby(level=0)}
            rng = random.Random(67)
            means = [np.mean([rng.choice(pools[s]) - 20 for s in t.sym]) for _ in range(1000)]
            res["placebo_pct"] = float(np.mean(np.array(means) < m) * 100)
            res["placebo_mean_bp"] = float(np.mean(means))
    a2 = res["2x"]
    res["verdict"] = ("PASS (to paper)" if a2["h1"] > 0 and a2["h2"] > 0 and res["t_month"] >= 2 and res["placebo_pct"] >= 95
                      and res["without_best10"] > 0 else "DEAD")
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / "events.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
