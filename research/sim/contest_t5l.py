"""Study T5L (round1_prose.md, N 805 -> 806): the earnings iron fly on liquid large caps, far-side fills, judged on the
untouched 2016-22 period (2023-26 = selection, reported only).

  PYTHONPATH=. .venv/bin/python -m research.sim.contest_t5l earnings   # Nasdaq calendar 2016-02..2022-12
  PYTHONPATH=. .venv/bin/python -m research.sim.contest_t5l bars       # Alpaca raw daily close + volume
  PYTHONPATH=. .venv/bin/python -m research.sim.contest_t5l fetch      # OPRA NBBO, 15:49-15:54 windows on t-1 and t+1
  PYTHONPATH=. .venv/bin/python -m research.sim.contest_t5l run        # the one look
"""
import os
import sys
import time

import numpy as np
import pandas as pd
import requests
from dotenv import dotenv_values

from research.sim.contest_options import ET, FEE
from research.sim.contest_straddle import (EARN, OUT5, Q_MIN, boot_mean, fetch_windows, grid, osi, quotes,
                                           third_friday)

D = "data/research/contest"
EARN_OLD = f"{D}/earnings_2016_22.parquet"
BARS = f"{D}/t5l_raw_bars.parquet"
OUT = f"{D}/opra_t5l"
JUDGE = ("2016-02-01", "2022-12-31")
SELECT_END = "2023-01-01"        # registered split: judge 2016-22, selection 2023-26
MIN_ADV, MIN_PX = 1e9, 20.0
GATE = 0.10                # entry half-spread cost <= 10% of far-side max loss
RISK = 0.05
SIZES = (2300, 10000, 25000)


def fetch_earnings():
    rows = []
    for d in pd.bdate_range("2016-01-25", "2022-12-31"):
        data = []
        for attempt in range(3):
            try:
                r = requests.get("https://api.nasdaq.com/api/calendar/earnings", params={"date": f"{d:%Y-%m-%d}"},
                                 timeout=20, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
                data = (r.json().get("data") or {}).get("rows") or []
                break
            except Exception:
                time.sleep(2 + 3 * attempt)
        rows += [(d, x.get("symbol"), x.get("time")) for x in data]
        time.sleep(0.3)
    pd.DataFrame(rows, columns=["date", "symbol", "time"]).to_parquet(EARN_OLD)
    print(len(rows))


def all_events():
    a = pd.read_parquet(EARN_OLD)[["date", "symbol"]]
    b = pd.read_parquet(EARN)[["date", "symbol"]]
    e = pd.concat([a, b[b.date >= "2023-01-01"]])
    e = e[e.symbol.str.fullmatch(r"[A-Z]{1,5}", na=False)]
    return e.drop_duplicates(["symbol", "date"])


def fetch_bars():
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    env = dotenv_values(".env")
    c = StockHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    syms = sorted(set(all_events().symbol)) + ["SPY"]
    out = []
    for i in range(0, len(syms), 200):
        for attempt in range(3):
            try:
                df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms[i:i + 200], timeframe=TimeFrame.Day,
                                                       start=pd.Timestamp("2015-12-01"), end=pd.Timestamp("2026-10-01"),
                                                       feed="sip", adjustment="raw")).df.reset_index()
                out.append(df[["symbol", "timestamp", "close", "volume"]])
                break
            except Exception as exc:
                print(i, type(exc).__name__, str(exc)[:80], flush=True)
                time.sleep(5)
        print(i, flush=True)
    b = pd.concat(out)
    b["day"] = b.timestamp.dt.tz_convert(ET).dt.tz_localize(None).dt.normalize()
    b[["symbol", "day", "close", "volume"]].to_parquet(BARS)


def plan():
    b = pd.read_parquet(BARS)
    cal = pd.DatetimeIndex(sorted(b[b.symbol == "SPY"].day.unique()))
    b["dv"] = b.close * b.volume
    px = b.set_index(["symbol", "day"]).close
    adv = {s: g.set_index("day").dv for s, g in b.groupby("symbol")}
    rows = []
    for r in all_events().itertuples():
        t = pd.Timestamp(r.date)
        if t not in cal or t < pd.Timestamp(JUDGE[0]):
            continue
        i = cal.get_loc(t)
        if i < 22 or i + 1 >= len(cal):
            continue
        p = px.get((r.symbol, cal[i - 2]))
        a = adv.get(r.symbol)
        if p is None or a is None or not np.isfinite(p) or p < MIN_PX:
            continue
        hist = a.reindex(cal[i - 21:i - 1])
        if hist.notna().sum() < 15 or hist.mean() < MIN_ADV:
            continue
        t1 = cal[i + 1]
        fri = t1 + pd.Timedelta(days=(4 - t1.weekday()) % 7)
        tf = third_friday(t1.year, t1.month)
        if tf < t1:
            tf = third_friday(t1.year + (t1.month == 12), t1.month % 12 + 1)
        rows.append((r.symbol, t, cal[i - 1], t1, p, hist.mean(), sorted({fri, tf}),
                     grid(p), grid(p * 1.1), grid(p * 0.9)))
    return pd.DataFrame(rows, columns=["sym", "t", "d_in", "d_out", "px", "adv", "exps", "ks", "kh", "kl"])


def fetch():
    pl = plan()
    pl = pl[pl.t < SELECT_END]                    # 2023-26 quotes already exist in OUT5 (T5)
    print(f"{len(pl)} judge-period events", flush=True)
    need = {}
    for r in pl.itertuples():
        syms = [osi(r.sym, e, "C", k) for e in r.exps for k in r.ks + r.kh] + \
               [osi(r.sym, e, "P", k) for e in r.exps for k in r.ks + r.kl]
        for d in (r.d_in, r.d_out):
            need.setdefault(d, set()).update(syms)
    fetch_windows(need, OUT, (15, 49))


def price(pl, Q):
    """Far-side and mid P&L per event (per share), plus the entry gate inputs."""
    ok = lambda s, d: (Q.get((s, d)) or (0, 0))[1] > 0
    rows, unpriced = [], 0
    for r in pl.itertuples():
        for e in r.exps:
            ks = [k for k in r.ks if ok(osi(r.sym, e, "C", k), r.d_in) and ok(osi(r.sym, e, "P", k), r.d_in)]
            kh = [k for k in r.kh if ok(osi(r.sym, e, "C", k), r.d_in)]
            kl = [k for k in r.kl if ok(osi(r.sym, e, "P", k), r.d_in)]
            if not (ks and kh and kl):
                continue
            k = min(ks, key=lambda x: abs(x - r.px))
            hi = min(kh, key=lambda x: abs(x - r.px * 1.1))
            lo = min(kl, key=lambda x: abs(x - r.px * 0.9))
            if not (lo < k < hi):
                break
            legs = [(-1, osi(r.sym, e, "C", k)), (-1, osi(r.sym, e, "P", k)),
                    (1, osi(r.sym, e, "C", hi)), (1, osi(r.sym, e, "P", lo))]
            qi = [Q[(x, r.d_in)] for _, x in legs]
            if any(not (q[0] > 0) for (sg, _), q in zip(legs, qi) if sg < 0):
                break
            qo = [Q.get((x, r.d_out)) for _, x in legs]
            if any(q is None or not (q[1] > 0) for (sg, _), q in zip(legs, qo) if sg < 0):
                unpriced += 1
                break
            width = max(hi - k, k - lo)
            cost = sum(a if sg > 0 else -b for (sg, _), (b, a) in zip(legs, qi))         # -credit at far side
            mid_in = sum(sg * (b + a) / 2 for (sg, _), (b, a) in zip(legs, qi))
            bid = lambda q: q[0] if q and q[0] > 0 else 0.0
            val = sum(bid(q) if sg > 0 else -q[1] for (sg, _), q in zip(legs, qo))
            hs_out = sum(((q[1] - q[0]) / 2 if q and q[0] > 0 else 0.0) for q in qo)
            mid_out = val + hs_out
            fees = FEE * 8 / 100
            risk = width + cost + fees
            rows.append(dict(sym=r.sym, t=r.t, d_out=r.d_out, adv=r.adv, width=width, cost=cost, val=val, fees=fees,
                             risk=risk, hs_in=cost - mid_in, hs_out=hs_out, mid_pnl=mid_out - mid_in))
            break
    p = pd.DataFrame(rows)
    p["pnl"] = p.val - p.cost - p.fees
    p["r"] = p.pnl / p.risk
    p["r_mid"] = p.mid_pnl / p.risk
    p["r_shock"] = (p.pnl - p.hs_out) / p.risk                  # every exit half-spread doubled
    p["gate"] = p.hs_in <= GATE * (p.width + p.cost)
    return p[p.risk > 0], unpriced


def boot_3m(j, e0, n=2000, horizon=63, seed=3):
    """3-month paths: blocks of event dates drawn from the judge calendar's per-day trade lists, 5% risk per trade."""
    rng = np.random.default_rng(seed)
    days = sorted(j.d_out.unique())
    span = pd.bdate_range(j.d_out.min(), j.d_out.max())
    by = {d: g[["risk", "pnl"]].values for d, g in j.groupby("d_out")}
    k, fin, hit = len(span), [], 0
    for _ in range(n):
        eq, low = e0, False
        s = rng.integers(0, k - horizon)
        for d in span[s:s + horizon]:
            for risk, pnl in by.get(d, ()):
                c = int(RISK * eq // (100 * risk))
                if c >= 1:
                    eq += c * 100 * pnl
            low |= eq <= 0.7 * e0
        fin.append(eq / e0 - 1)
        hit += low
    f = np.array(fin)
    return np.median(f), np.percentile(f, 10), np.percentile(f, 90), hit / n


def main():
    pl = plan()
    Q = quotes(OUT, Q_MIN)
    Q.update(quotes(OUT5, Q_MIN))
    p, unpriced = price(pl, Q)
    p.to_parquet(f"{D}/t5l_trades.parquet")
    g = p[p.gate]
    print(f"events {len(pl)} (liquid), priced {len(p)}, unpriced exits {unpriced}, pass entry gate {len(g)}")
    for lab, x in (("JUDGE 2016-22", g[g.t < SELECT_END]), ("select 2023-26 (seen)", g[g.t >= SELECT_END]),
                   ("judge, no gate (report)", p[p.t < SELECT_END])):
        if not len(x):
            print(lab, "no trades")
            continue
        pb = boot_mean({d: v.r.values for d, v in x.groupby("t")})
        ex5 = x.sort_values("pnl").iloc[:-5]
        print(f"{lab}: n {len(x)} | far-side r mean {x.r.mean():+.4f} median {x.r.median():+.4f} win {(x.pnl > 0).mean():.2f}"
              f" P(<=0) {pb:.3f} ex-best-5 {(ex5.pnl / ex5.risk).mean():+.4f} | 2x exit spread {x.r_shock.mean():+.4f}"
              f" | mid {x.r_mid.mean():+.4f} | worst {x.r.min():+.2f} | half-spread in/out per risk "
              f"{(x.hs_in / x.risk).median():.3f}/{(x.hs_out / x.risk).median():.3f}")
        print("   by year:", {y: (round(v.r.mean(), 4), len(v)) for y, v in x.groupby(x.t.dt.year)})
    j = g[g.t < SELECT_END]
    if len(j):
        for e0 in SIZES:
            m, p10, p90, p30 = boot_3m(j, e0)
            print(f"   3-month @ ${e0:,}: median {m:+.3f} p10 {p10:+.3f} p90 {p90:+.3f} P(-30%) {p30:.3f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"earnings": fetch_earnings, "bars": fetch_bars, "fetch": fetch, "run": main}[cmd]()
