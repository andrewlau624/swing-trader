"""Study TL (round1_prose.md, N 809 -> 810): Reg SHO threshold-list forced buy-in on the 13-day clock. One look.

  PYTHONPATH=. .venv/bin/python -m research.sim.threshold_tl bars   # Alpaca SIP daily bars (adjusted + raw) for episode names
  PYTHONPATH=. .venv/bin/python -m research.sim.threshold_tl run    # the registered judge + reported diagnostics
"""
import sys
import time

import numpy as np
import pandas as pd
from dotenv import dotenv_values

D = "data/research/threshold"
START = pd.Timestamp("2016-01-04")
MIN_PX, MIN_ADV = 1.0, 2.5e5
ENTRY, EXIT = 10, 13            # buy open of list day 10, sell close of list day 13
PLACEBO = (6, 9)
ET = "America/New_York"


def episodes():
    ep = pd.read_parquet(f"{D}/episodes.parquet")
    return ep[~ep.fund & (ep["last"] >= START - pd.Timedelta(days=40))]


def bars():
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import Adjustment
    env = dotenv_values(".env")
    c = StockHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    syms = sorted(set(episodes().sym.str.replace(".", "/", regex=False))) + ["IWM"]
    for adj, tag in ((Adjustment.ALL, "adj"), (Adjustment.RAW, "raw")):
        out = []
        for i in range(0, len(syms), 200):
            for attempt in range(4):
                try:
                    df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms[i:i + 200], timeframe=TimeFrame.Day,
                                                           start=pd.Timestamp("2015-10-01"),
                                                           end=pd.Timestamp("2026-10-02"), feed="sip",
                                                           adjustment=adj)).df.reset_index()
                    out.append(df[["symbol", "timestamp", "open", "high", "low", "close", "volume"]])
                    break
                except Exception as exc:
                    print(tag, i, type(exc).__name__, str(exc)[:80], flush=True)
                    time.sleep(5)
        b = pd.concat(out)
        b["day"] = b.timestamp.dt.tz_convert(ET).dt.tz_localize(None).dt.normalize()
        b["symbol"] = b.symbol.str.replace("/", ".", regex=False)
        b.drop(columns="timestamp").to_parquet(f"{D}/bars_{tag}.parquet")
        print(tag, len(b), b.symbol.nunique(), flush=True)


def corwin_schultz(h, l):
    """Mean Corwin-Schultz (2012) spread from daily high/low arrays (negative estimates -> 0)."""
    h, l = np.asarray(h, float), np.asarray(l, float)
    if len(h) < 3 or (l <= 0).any():
        return np.nan
    b = np.log(h[:-1] / l[:-1]) ** 2 + np.log(h[1:] / l[1:]) ** 2
    g = np.log(np.maximum(h[:-1], h[1:]) / np.minimum(l[:-1], l[1:])) ** 2
    k = 3 - 2 * np.sqrt(2)
    a = (np.sqrt(2 * b) - np.sqrt(b)) / k - np.sqrt(g / k)
    s = 2 * (np.exp(a) - 1) / (1 + np.exp(a))
    return float(np.nanmean(np.clip(s, 0, None)))


def clustered_t(x, keys):
    s = pd.Series(np.asarray(x, float)).groupby(np.asarray(keys)).mean()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 and s.std() > 0 else np.nan


def build():
    st = pd.read_parquet(f"{D}/fetch_status.parquet")
    cal = pd.DatetimeIndex(pd.to_datetime(st.day))
    pos = {d: i for i, d in enumerate(cal)}
    adj = {s: g.set_index("day").sort_index() for s, g in pd.read_parquet(f"{D}/bars_adj.parquet").groupby("symbol")}
    raw = {s: g.set_index("day").sort_index() for s, g in pd.read_parquet(f"{D}/bars_raw.parquet").groupby("symbol")}
    iwm = adj["IWM"]
    rows, skipped = [], {"no bars": 0, "missing days": 0, "price": 0, "adv": 0}
    for e in episodes().itertuples():
        if e.days < ENTRY:
            continue
        i0 = pos[e.first]
        if i0 + 16 >= len(cal):
            continue
        lday = {k: cal[i0 + k - 1] for k in range(-19, 17) if 0 <= i0 + k - 1 < len(cal)}   # list day k -> session
        if lday[ENTRY] < START:
            continue
        a, r = adj.get(e.sym), raw.get(e.sym)
        if a is None or r is None:
            skipped["no bars"] += 1
            continue
        need = [lday[k] for k in range(PLACEBO[0] - 1, EXIT + 1)]
        if not all(d in a.index for d in need) or not all(d in iwm.index for d in need):
            skipped["missing days"] += 1
            continue
        pre = r.loc[(r.index < e.first)].tail(20)
        if len(pre) < 10:
            skipped["missing days"] += 1
            continue
        px9 = r.close.get(lday[ENTRY - 1], np.nan)
        adv = float((pre.close * pre.volume).mean())
        if not px9 >= MIN_PX:
            skipped["price"] += 1
            continue
        if not adv >= MIN_ADV:
            skipped["adv"] += 1
            continue
        oc = lambda s, k0, k1: s.close[lday[k1]] / s.open[lday[k0]] - 1
        ar = oc(a, ENTRY, EXIT) - oc(iwm, ENTRY, EXIT)
        ar_pl = oc(a, *PLACEBO) - oc(iwm, *PLACEBO)
        spread = max(corwin_schultz(pre.high.values, pre.low.values), 0.001)
        v0 = pre.volume.mean()
        path = {}
        for k in range(1, 17):
            d, dp = lday.get(k), lday.get(k - 1)
            if d in a.index and dp in a.index and d in iwm.index and dp in iwm.index:
                path[f"on{k}"] = (a.open[d] / a.close[dp] - 1) - (iwm.open[d] / iwm.close[dp] - 1)
                path[f"id{k}"] = (a.close[d] / a.open[d] - 1) - (iwm.close[d] / iwm.open[d] - 1)
                path[f"v{k}"] = r.volume.get(d, np.nan) / v0 if v0 > 0 else np.nan
        rows.append(dict(sym=e.sym, first=e.first, days=e.days, entry=lday[ENTRY], px=px9, adv=adv, spread=spread,
                         ar=ar, ar_pl=ar_pl, reentry=e.reentry_gap, **path))
    return pd.DataFrame(rows), skipped


def run():
    t, skipped = build()
    t["net"] = t.ar - t.spread
    t["net2"] = t.ar - 2 * t.spread
    t["id"] = t.ar - t.ar_pl
    t["wk"] = t.entry.dt.to_period("W").astype(str)
    t.to_parquet(f"{D}/tl_trades.parquet")
    n = len(t)
    srt = t.net.sort_values()
    ex5, ex1 = srt.iloc[:-5].mean(), srt.iloc[:-max(1, int(0.01 * n))].mean()
    yrs = t.groupby(t.entry.dt.year).net.mean()
    g = dict(n=n >= 150, mean_t=t.net.mean() > 0 and clustered_t(t.net, t.wk) >= 2, median=t.net.median() > 0,
             ex_top=ex5 > 0 and ex1 > 0, timing=t.id.mean() > 0 and clustered_t(t.id, t.wk) >= 2,
             years=(yrs > 0).mean() >= 0.6, cost2x=t.net2.mean() > 0)
    print(f"skipped at entry: {skipped}")
    print(f"TL1: n {n} | gross AR mean {t.ar.mean():+.4f} median {t.ar.median():+.4f} | net mean {t.net.mean():+.4f} "
          f"t {clustered_t(t.net, t.wk):.2f} median {t.net.median():+.4f} win {(t.net > 0).mean():.2f} | ex-top5 {ex5:+.4f} "
          f"ex-top1% {ex1:+.4f} | 2x cost {t.net2.mean():+.4f} | median spread {t.spread.median():.4f}")
    print(f"TL1-ID: AR[10-13] - AR[6-9] mean {t.id.mean():+.4f} t {clustered_t(t.id, t.wk):.2f} | AR[6-9] {t.ar_pl.mean():+.4f}")
    print("years (net mean, n):", {y: (round(v, 4), int((t.entry.dt.year == y).sum())) for y, v in yrs.items()})
    print("GATES:", g, "->", "ALL PASS" if all(g.values()) else "FAIL")
    print("\nby list day k: mean overnight AR / intraday AR / median volume ratio")
    for k in range(1, 17):
        if f"on{k}" in t:
            print(f"  k={k:2d}  on {t[f'on{k}'].mean():+.4f}  id {t[f'id{k}'].mean():+.4f}  vol x{t[f'v{k}'].median():.2f}  (n {t[f'on{k}'].notna().sum()})")
    t["reach13"] = t.days >= 13
    print("\nreached day 13 vs removed at 10-12 (descriptive; conditions on the future):",
          t.groupby("reach13").net.agg(["mean", "median", "size"]).round(4).to_dict())
    t["pxb"] = pd.cut(t.px, [0, 2, 5, 20, 1e9], labels=["$1-2", "$2-5", "$5-20", "$20+"])
    t["advb"] = pd.qcut(t.adv, 3, labels=["low", "mid", "high"])
    print("by price:", t.groupby("pxb", observed=True).net.agg(["mean", "median", "size"]).round(4).to_dict("index"))
    print("by $ADV tercile:", t.groupby("advb", observed=True).net.agg(["mean", "median", "size"]).round(4).to_dict("index"))
    print("re-entries vs first episodes:", t.groupby(t.reentry.notna()).net.agg(["mean", "size"]).round(4).to_dict("index"))
    pnl = t.net.sort_values(ascending=False)
    print(f"\neconomics: entries/yr {n / ((t.entry.max() - t.entry.min()).days / 365.25):.1f}; median $ADV "
          f"${t.adv.median():,.0f}; capital/trade at 1% / 5% ADV: ${0.01 * t.adv.median():,.0f} / "
          f"${0.05 * t.adv.median():,.0f}; worst trade {t.net.min():+.3f}; top-5 share of summed net "
          f"{pnl.iloc[:5].sum() / pnl.sum() if pnl.sum() > 0 else float('nan'):.2f}")


if __name__ == "__main__":
    {"bars": bars, "run": run}[sys.argv[1]]()
