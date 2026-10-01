"""Study Lab-BH: announcement-return drift proxy (daytrade/plans/event_drift.md, round1_prose.md Lab Round 32).

Reads (all completed REGULAR sessions; before 2026-12-06 a vendor daily bar is the regular session):
- raw SIP daily bars (cached by Study Lab-AU) for the event filters;
- split/dividend-adjusted SIP daily bars for the event names and SPY, for holding-period returns
  (entry = day 1's open = the opening cross; exit = day H's close = the closing cross).

  python -m daytrade.research.bh_replay
"""
from __future__ import annotations

import datetime as dt
import json
import math
import random
from collections import defaultdict

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A
from . import au_replay as U

OUT = DATA / "research" / "bh"
GAP, VOLX, PRICE_MIN, ADV_MIN = 0.05, 3.0, 5.0, 20e6
SPLIT = "2024-06-01"


def events(d: pd.DataFrame) -> pd.DataFrame:
    keep = set(A.universe())
    d = d[d.symbol.isin(keep)].sort_values(["symbol", "date"])
    out = []
    for sym, g in d.groupby("symbol", sort=False):
        g = g.reset_index(drop=True)
        pc = g.close.shift(1)
        adv = (g.close * g.volume).shift(1).rolling(20, min_periods=20).mean()
        avs = g.volume.shift(1).rolling(20, min_periods=20).mean()
        m = (g.open / pc - 1 >= GAP) & (g.volume >= VOLX * avs) & (pc >= PRICE_MIN) & (adv >= ADV_MIN)
        m &= g.date >= pd.Timestamp(A.START)
        for i in np.flatnonzero(m.values):
            out.append({"sym": sym, "day0": g.date.iat[i], "volx": float(g.volume.iat[i] / avs.iat[i]),
                        "gap": float(g.open.iat[i] / pc.iat[i] - 1)})
    return pd.DataFrame(out)


def adjusted(symbols) -> pd.DataFrame:
    p = OUT / "adjusted.parquet"
    if p.exists():
        return pd.read_parquet(p)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    data, _ = A._clients()
    parts = []
    syms = sorted(set(symbols) | {"SPY"})
    for i in range(0, len(syms), 300):
        df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms[i:i + 300], timeframe=TimeFrame.Day,
                                                  start=pd.Timestamp(A.START - dt.timedelta(days=10), tz="UTC"),
                                                  end=pd.Timestamp(A.END + dt.timedelta(days=1), tz="UTC"),
                                                  feed="sip", adjustment="all")).df
        if df is not None and len(df):
            parts.append(df.reset_index()[["symbol", "timestamp", "open", "close"]])
        A.log(f"adjusted {min(i + 300, len(syms))}/{len(syms)}")
    x = pd.concat(parts)
    x["date"] = trade_date(x["timestamp"])
    x = x.drop(columns="timestamp")
    OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(p)
    return x


def run():
    d = pd.read_parquet(U.OUT / "daily_ohlc.parquet")
    ev = events(d)
    A.log(f"events {len(ev)}")
    adj = adjusted(ev.sym.unique())
    px = {s: g.set_index("date").sort_index() for s, g in adj.groupby("symbol")}
    spy = px["SPY"]
    spy_idx = {t: i for i, t in enumerate(spy.index)}
    res = {"events": len(ev)}
    for name, H in (("Lab-BH1", 20), ("Lab-BH2", 5)):
        rows = []
        for r in ev.itertuples(index=False):
            g = px.get(r.sym)
            if g is None or r.day0 not in g.index:
                continue
            i = g.index.get_loc(r.day0)
            if i + 1 >= len(g):
                continue
            j = min(i + H, len(g) - 1)              # delisted before day H: exit at its last close
            t1, tH = g.index[i + 1], g.index[j]
            if tH > pd.Timestamp(A.END) or t1 not in spy_idx or tH not in spy_idx:
                continue
            ret = g.close.iat[j] / g.open.iat[i + 1] - 1
            mkt = spy.close.iat[spy_idx[tH]] / spy.open.iat[spy_idx[t1]] - 1
            rows.append({"sym": r.sym, "day": str(r.day0.date()), "ret": ret, "mkt": mkt, "volx": r.volx,
                         "t1": t1, "tH": tH, "complete": j == i + H})
        t = pd.DataFrame(rows)
        v = {"n": len(t), "complete_share": float(t.complete.mean())}
        for mult, c in (("1x", 10), ("2x", 20)):
            t[f"ex_{mult}"] = (t.ret - t.mkt) * 1e4 - 2 * c
            t[f"net_{mult}"] = t.ret * 1e4 - 2 * c
        for mult in ("1x", "2x"):
            v[mult] = {h: {"n": len(p), "excess_bp": float(p[f"ex_{mult}"].mean()), "net_bp": float(p[f"net_{mult}"].mean()),
                           "median_excess": float(p[f"ex_{mult}"].median())}
                       for h, p in (("all", t), ("h1", t[t.day < SPLIT]), ("h2", t[t.day >= SPLIT]))}
        # month-clustered t on the 1x excess
        x = t.ex_1x.values; m = x.mean()
        cl = defaultdict(float)
        for mo, xv in zip(t.day.str[:7], x):
            cl[mo] += xv - m
        se = math.sqrt(sum(z * z for z in cl.values())) / len(x)
        v["t_month"] = float(m / se)
        xs = np.sort(x)
        v["without_top20"] = float(xs[:-20].mean())
        v["by_year_excess_1x"] = {y: float(g.ex_1x.mean()) for y, g in t.groupby(t.day.str[:4])}
        # placebo: random non-event dates for the same stocks, same H
        evd = defaultdict(set)
        for r in ev.itertuples(index=False):
            evd[r.sym].add(r.day0)
        pool = {}
        for s in t.sym.unique():
            g = px[s]
            idx = g.index
            bad = set()
            for e in evd[s]:
                if e in idx:
                    k = idx.get_loc(e)
                    bad |= set(idx[max(0, k - 5):k + 6])
            opts = []
            for k in range(1, len(idx) - H - 1):
                if idx[k] in bad or idx[k] < pd.Timestamp(A.START):
                    continue
                t1, tH = idx[k + 1], idx[k + H]
                if t1 in spy_idx and tH in spy_idx:
                    ex = (g.close.iat[k + H] / g.open.iat[k + 1] - 1) - (spy.close.iat[spy_idx[tH]] / spy.open.iat[spy_idx[t1]] - 1)
                    opts.append(ex * 1e4 - 20)
            pool[s] = opts or [0.0]
        rng = random.Random(47)
        means = [np.mean([rng.choice(pool[s]) for s in t.sym]) for _ in range(1000)]
        v["placebo_pct"] = float(np.mean(np.array(means) < m) * 100)
        v["placebo_mean_bp"] = float(np.mean(means))
        a2 = v["2x"]
        v["verdict"] = ("PASS (to paper)" if a2["h1"]["excess_bp"] > 0 and a2["h2"]["excess_bp"] > 0 and v["t_month"] >= 2
                        and v["placebo_pct"] >= 95 and v["without_top20"] > 0 else "DEAD")
        v["dollars"] = portfolio(t, ev, px, H)
        res[name] = v
        t.to_csv(OUT / f"events_{name}.csv", index=False)
        print(name, v["verdict"], json.dumps({"n": v["n"], "ex1": v["1x"]["all"]["excess_bp"], "t": v["t_month"],
                                              "h": [v["2x"]["h1"]["excess_bp"], v["2x"]["h2"]["excess_bp"]],
                                              "noTop20": v["without_top20"], "placebo": v["placebo_pct"]}), flush=True)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))


def portfolio(t, ev, px, H, slots=10, cost_bp=10):
    """10 slots of 10% each; new events by volume ratio when a slot frees; whole shares; 1x costs."""
    out = {}
    days = sorted(set(pd.Timestamp(x) for x in t.t1))
    by_t1 = defaultdict(list)
    for r in t.itertuples(index=False):
        by_t1[pd.Timestamp(r.t1)].append(r)
    for label, eq0 in (("$2.3k", 2_300), ("$10k", 10_000), ("$25k", 25_000)):
        cash, open_ = eq0, []
        for day in days:
            for p in [p for p in open_ if p["tH"] <= day]:
                cash += p["sh"] * p["exit"] * (1 - cost_bp / 1e4)
                open_.remove(p)
            eq = cash + sum(p["sh"] * p["entry"] for p in open_)
            for r in sorted(by_t1.get(day, []), key=lambda z: -z.volx):
                if len(open_) >= slots:
                    break
                g = px[r.sym]
                entry = float(g.open.loc[r.t1]); exit_ = float(g.close.loc[r.tH])
                sh = math.floor(eq / slots / (entry * (1 + cost_bp / 1e4)))
                if sh < 1 or sh * entry > cash:
                    continue
                cash -= sh * entry * (1 + cost_bp / 1e4)
                open_.append({"sh": sh, "entry": entry, "exit": exit_, "tH": pd.Timestamp(r.tH)})
        for p in open_:
            cash += p["sh"] * p["exit"] * (1 - cost_bp / 1e4)
        yrs = (days[-1] - days[0]).days / 365.25
        out[label] = {"end": round(cash, 2), "cagr": (cash / eq0) ** (1 / yrs) - 1 if cash > 0 else -1}
    return out


if __name__ == "__main__":
    run()
