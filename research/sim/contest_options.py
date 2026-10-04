"""Contest hunt T1 / T2: QQQ 0DTE options on the noise-leg signal (round1_prose.md, N 791 -> 795).

  PYTHONPATH=. .venv/bin/python -m research.sim.contest_options fetch [--dry]   # NBBO for the contracts the rules need
  PYTHONPATH=. .venv/bin/python -m research.sim.contest_options run             # price, judge, report

Signal = research/daily-strategies/noise.py (lookback 14, step 30, first 30, VWAP stop, long/short) on the SIP
minute matrix. Fills on the Databento OPRA cbbo-1m record of minute m+1 after a decision at minute m: buy at the
ask, sell at the bid, $0.65/contract/leg. Forced exit at minute 380 (15:50). Sizing: max loss per trade <= 5% of equity,
whole contracts, skip if one contract is too big.
"""
import os
import sys

import numpy as np
import pandas as pd
from dotenv import dotenv_values

from research.sim.contest_opra_fetch import osi

sys.path.insert(0, "research/daily-strategies")
import intra  # noqa: E402

intra.SP = "data/research/night"

OUT = "data/research/contest/opra_sig"
RAW_FACTOR = "data/research/contest/qqq_raw_factor.parquet"   # Alpaca daily close raw / adjusted
START, END = "2023-01-03", "2026-09-22"
SELECT_END = "2025-01-01"
FEE = 0.65
RISK = 0.05
EXIT_M = 380
CAP_USD = 5.0
LOOKBACK, STEP, FIRST = 14, 30, 30
SIZES = (2300, 10000, 25000)
TAX = 0.30
ET = "America/New_York"


# ------------------------------------------------------------------ signal
def signal(M):
    """Noise-rule trades and condor days, exactly noise.py's state machine (exits at decision points,
    flip = exit then re-enter on the same bar), forced exit moved to EXIT_M."""
    C = M["close"].values
    O = M["open"].values[:, 0]
    V = M["volume"].values
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    pv = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    trades, condors = [], []
    for i in range(LOOKBACK + 1, len(days)):
        d = days[i]
        if not (pd.Timestamp(START) <= d < pd.Timestamp(END)):
            continue
        sig = move[i - LOOKBACK:i].mean(axis=0)
        ub = max(O[i], prevc[i]) * (1 + sig)
        lb = min(O[i], prevc[i]) * (1 - sig)
        pos, entry = 0, None
        for m in range(FIRST, 390, STEP):
            if m > EXIT_M:
                break
            p = C[i, m]
            if pos == 1 and p < max(ub[m], pv[i, m]):
                trades.append((d, entry[0], 1, entry[1], m)); pos = 0
            elif pos == -1 and p > min(lb[m], pv[i, m]):
                trades.append((d, entry[0], -1, entry[1], m)); pos = 0
            if pos == 0:
                if p > ub[m]:
                    pos, entry = 1, (m, p)
                elif p < lb[m]:
                    pos, entry = -1, (m, p)
            if m == FIRST and pos == 0:
                condors.append((d, p, ub[389], lb[389]))
        if pos != 0:
            trades.append((d, entry[0], pos, entry[1], EXIT_M))
    t = pd.DataFrame(trades, columns=["day", "m_in", "dir", "px", "m_out"])
    c = pd.DataFrame(condors, columns=["day", "px", "ub", "lb"])
    # The matrix is dividend-adjusted (adjustment='all', ~2% low in 2023); strikes need raw prices.
    f = pd.read_parquet(RAW_FACTOR)["factor"]
    t["px"] *= t.day.map(f).values
    for k in ("px", "ub", "lb"):
        c[k] *= c.day.map(f).values
    assert t.px.notna().all() and c.px.notna().all(), "missing raw factor"
    return t, c


def legs_t1(day, d, px):
    """{variant: [(sign, osi)]}: +1 bought, -1 sold."""
    cp = "C" if d == 1 else "P"
    atm = int(np.ceil(px)) if d == 1 else int(np.floor(px))
    otm = int(round(px * (1 + 0.005 * d)))
    return {"T1a": [(1, osi(day, cp, atm))],
            "T1b": [(1, osi(day, cp, atm)), (-1, osi(day, cp, atm + 2 * d))],
            "T1c": [(1, osi(day, cp, otm))]}


def legs_t2(day, ub, lb):
    kc, kp = int(np.ceil(ub)), int(np.floor(lb))
    return [(-1, osi(day, "C", kc)), (1, osi(day, "C", kc + 1)),
            (-1, osi(day, "P", kp)), (1, osi(day, "P", kp - 1))]


def needed(t, c):
    rows = []
    for r in t.itertuples():
        for legs in legs_t1(r.day, r.dir, r.px).values():
            rows += [(r.day, s) for _, s in legs]
    for r in c.itertuples():
        rows += [(r.day, s) for _, s in legs_t2(r.day, r.ub, r.lb)]
    return pd.DataFrame(rows, columns=["day", "sym"]).drop_duplicates()


# ------------------------------------------------------------------ fetch
def fetch(dry):
    import databento as db
    client = db.Historical(dotenv_values(".env")["DATABENTO_API_KEY"])
    t, c = signal(intra.load("QQQ"))
    need = needed(t, c)
    need["mo"] = need.day.dt.strftime("%Y-%m")
    os.makedirs(OUT, exist_ok=True)
    plan, total = [], 0.0
    for mo, g in need.groupby("mo"):
        path = f"{OUT}/QQQ_{mo}.parquet"
        if os.path.exists(path):
            continue
        syms = sorted(g.sym.unique())
        start = g.day.min().strftime("%Y-%m-%d")
        end = (g.day.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        cost = client.metadata.get_cost(dataset="OPRA.PILLAR", symbols=syms, stype_in="raw_symbol",
                                        schema="cbbo-1m", start=start, end=end)
        total += cost
        plan.append((mo, syms, start, end, path))
        print(f"{mo}: {len(syms)} symbols ${cost:.3f} (running ${total:.2f})", flush=True)
        if total > CAP_USD:
            sys.exit(f"ABORT: planned ${total:.2f} > cap ${CAP_USD}")
    print(f"planned ${total:.2f}, {len(plan)} months; trades {len(t)}, condor days {len(c)}")
    if dry:
        return
    def one(job):
        mo, syms, start, end, path = job
        df = client.timeseries.get_range(dataset="OPRA.PILLAR", symbols=syms, stype_in="raw_symbol",
                                         schema="cbbo-1m", start=start, end=end).to_df().reset_index()
        keep = [k for k in ("ts_event", "ts_recv", "symbol", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00")
                if k in df.columns]
        df[keep].rename(columns=lambda k: k.replace("_00", "")).to_parquet(path)
        print(f"{mo}: {len(df):,} rows", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:   # one month per request is slow (~8 min); run months side by side
        list(ex.map(one, plan))


# ------------------------------------------------------------------ pricing
class Book:
    """As-of NBBO lookup: quote of minute m = last record stamped before the end of minute m (ET)."""

    def __init__(self, out=OUT):
        fs = sorted(f for f in os.listdir(out) if f.endswith(".parquet"))
        q = pd.concat([pd.read_parquet(f"{out}/{f}") for f in fs])
        ts = pd.to_datetime(q["ts_recv"] if "ts_recv" in q else q["ts_event"], utc=True).dt.tz_convert(ET)
        q["day"] = ts.dt.tz_localize(None).dt.normalize()
        q["sec"] = (ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second) - 34200
        q = q.sort_values(["symbol", "day", "sec"])
        self.g = {k: (v.sec.values, v.bid_px.values, v.ask_px.values)
                  for k, v in q.groupby(["symbol", "day"], sort=False)}

    def quote(self, sym, day, m):
        """(bid, ask) at the end of minute m; None if no record in the 5 minutes before."""
        x = self.g.get((sym, day))
        if x is None:
            return None
        sec, b, a = x
        j = np.searchsorted(sec, (m + 1) * 60, side="right") - 1   # ts_recv = end of the record's minute
        if j < 0 or sec[j] < (m + 1) * 60 - 300:
            return None
        bid, ask = float(b[j]), float(a[j])
        if not (np.isfinite(ask) and ask > 0):
            return None
        return (bid if np.isfinite(bid) and bid > 0 else 0.0), ask


def price_trade(book, legs, day, m_in, m_out):
    """Per-contract-set: (cost_in, value_out, max_loss) in $/share; None if any leg lacks an entry quote."""
    qin, qout = [], []
    for sgn, s in legs:
        a = book.quote(s, day, m_in + 1)
        if a is None:
            return None
        qin.append(a)
        b = book.quote(s, day, m_out + 1)
        qout.append(b if b is not None else (0.0, np.nan))
    cost = sum(a if sgn > 0 else -b for (sgn, _), (b, a) in zip(legs, qin))
    val = 0.0
    for (sgn, _), (b, a) in zip(legs, qout):
        if sgn > 0:
            val += b
        else:
            if not np.isfinite(a):
                return None
            val -= a
    fees = FEE * len(legs) * 2 / 100
    return cost, val, fees


def max_loss(variant, legs, cost):
    if variant == "T2a":
        k = sorted(int(s[-8:]) / 1000 for _, s in legs)
        width = max(k[1] - k[0], k[3] - k[2])
        return width + cost          # cost < 0 for a credit
    return cost


def priced(book, t, c):
    rows, skipped = [], 0
    for r in t.itertuples():
        for v, legs in legs_t1(r.day, r.dir, r.px).items():
            x = price_trade(book, legs, r.day, r.m_in, r.m_out)
            if x is None:
                skipped += 1
                continue
            cost, val, fees = x
            rows.append((v, r.day, r.m_in, r.m_out, r.dir, cost, val, fees, max_loss(v, legs, cost)))
    for r in c.itertuples():
        legs = legs_t2(r.day, r.ub, r.lb)
        x = price_trade(book, legs, r.day, FIRST, EXIT_M)
        if x is None:
            skipped += 1
            continue
        cost, val, fees = x
        rows.append(("T2a", r.day, FIRST, EXIT_M, 0, cost, val, fees, max_loss("T2a", legs, cost)))
    p = pd.DataFrame(rows, columns=["v", "day", "m_in", "m_out", "dir", "cost", "val", "fees", "risk"])
    p["pnl"] = p.val - p.cost - p.fees                      # $/share per contract set
    p["risk"] = p.risk + p.fees
    p["r"] = p.pnl / p.risk                                 # return on risk
    return p[p.risk > 0], skipped


# ------------------------------------------------------------------ money
def run_equity(p, e0):
    """Chronological whole-contract sim. Returns daily equity Series (pre-tax), after-tax, skipped share."""
    eq, rows, skip = e0, [], 0
    for day, g in p.groupby("day"):
        start = eq
        for x in g.itertuples():
            n = int(RISK * eq // (100 * x.risk))
            if n < 1:
                skip += 1
                continue
            eq += n * 100 * x.pnl
        rows.append((day, eq, start))
    s = pd.DataFrame(rows, columns=["day", "eq", "start"]).set_index("day")
    return s, skip / max(len(p), 1)


def after_tax(daily_ret):
    """30% of each year's net gain paid Dec 31 (losses carried forward)."""
    eq, carry, out = 1.0, 0.0, []
    for yr, g in daily_ret.groupby(daily_ret.index.year):
        y0 = eq
        for r in g:
            eq *= 1 + r
            out.append(eq)
        gain = eq - y0 + carry
        if gain > 0:
            eq -= TAX * gain
            out[-1] = eq
            carry = 0.0
        else:
            carry = gain
    return pd.Series(out, index=daily_ret.index)


def cagr(eq_series, e0):
    yrs = (eq_series.index[-1] - eq_series.index[0]).days / 365.25
    return (eq_series.iloc[-1] / e0) ** (1 / max(yrs, 1e-9)) - 1


def boot_mean(r_by_day, n=4000, block=5, seed=0):
    """P(mean per-trade r <= 0) under a day-block bootstrap."""
    rng = np.random.default_rng(seed)
    days = list(r_by_day)
    k = len(days)
    hits = 0
    for _ in range(n):
        idx = []
        while len(idx) < k:
            s = rng.integers(0, k)
            idx += [(s + j) % k for j in range(block)]
        x = np.concatenate([r_by_day[days[i]] for i in idx[:k]])
        hits += x.mean() <= 0
    return hits / n


def boot_3m(p, cal, e0, n=2000, block=5, horizon=63, seed=1):
    """3-month paths from 5-day blocks of judge-period sessions (no-trade days included)."""
    rng = np.random.default_rng(seed)
    by = {d: g[["risk", "pnl"]].values for d, g in p.groupby("day")}
    k = len(cal)
    fin, hit30 = [], 0
    for _ in range(n):
        eq, peak_loss = e0, False
        idx = []
        while len(idx) < horizon:
            s = rng.integers(0, k)
            idx += [(s + j) % k for j in range(block)]
        for i in idx[:horizon]:
            for risk, pnl in by.get(cal[i], ()):
                c = int(RISK * eq // (100 * risk))
                if c >= 1:
                    eq += c * 100 * pnl
            if eq <= 0.7 * e0:
                peak_loss = True
        fin.append(eq / e0 - 1)
        hit30 += peak_loss
    f = np.array(fin)
    return np.median(f), np.percentile(f, 10), np.percentile(f, 90), hit30 / n


def report(p, cal):
    out = []
    for v, g in p.groupby("v"):
        sel, jud = g[g.day < SELECT_END], g[g.day >= SELECT_END]
        jcal = [d for d in cal if d >= pd.Timestamp(SELECT_END)]
        rbd = {d: x.r.values for d, x in jud.groupby("day")}
        pb = boot_mean(rbd)
        ex5 = jud.pnl.sort_values().iloc[:-5].sum()
        line = dict(v=v, n_sel=len(sel), r_sel=sel.r.mean(), n_jud=len(jud), r_jud=jud.r.mean(),
                    win_jud=(jud.pnl > 0).mean(), p_le0=pb, ex5_jud=ex5,
                    med_risk=g.risk.median() * 100)
        for e0 in SIZES:
            s, skip = run_equity(jud, e0)
            full = s["eq"].reindex(pd.DatetimeIndex(jcal).astype(s.index.dtype)).ffill().fillna(e0)
            dr = full.pct_change().fillna(full.iloc[0] / e0 - 1)
            at = after_tax(dr) * e0
            med, p10, p90, p30 = boot_3m(jud, jcal, e0)
            line.update({f"cagr_{e0}": cagr(full, e0), f"cagr_tax_{e0}": cagr(at, e0),
                         f"dd_{e0}": (full / full.cummax() - 1).min(), f"worst_{e0}": dr.min(),
                         f"m3_{e0}": med, f"p10_{e0}": p10, f"p90_{e0}": p90, f"p30_{e0}": p30,
                         f"skip_{e0}": skip})
        line["PASS"] = bool(line["r_jud"] > 0 and pb <= 0.05 and line["r_sel"] > 0 and ex5 > 0
                            and line["p30_2300"] <= 0.10)
        out.append(line)
    return pd.DataFrame(out)


# ------------------------------------------------------------------ T4: overnight short 1DTE condor / fly
OUT4 = "data/research/contest/opra_t4"
T4_IN, T4_OUT = 381, 5        # sell on the 15:51 record, buy back on the 09:35 record next session


def t4_days(M):
    """(day, next session, raw 15:50 price) for every session with a next one."""
    f = pd.read_parquet(RAW_FACTOR)["factor"]
    days = [d for d in M["close"].index if pd.Timestamp(START) <= d < pd.Timestamp(END)]
    rows = [(d, d1, float(M["close"].loc[d][EXIT_M]) * f[d]) for d, d1 in zip(days, days[1:])]
    return pd.DataFrame(rows, columns=["day", "nxt", "px"])


def legs_t4(nxt, px):
    def condor(k):
        kc, kp = int(np.ceil(px * (1 + k))), int(np.floor(px * (1 - k)))
        return [(-1, osi(nxt, "C", kc)), (1, osi(nxt, "C", kc + 1)),
                (-1, osi(nxt, "P", kp)), (1, osi(nxt, "P", kp - 1))]
    a = int(round(px))
    return {"T4a": condor(0.005), "T4b": condor(0.010),
            "T4c": [(-1, osi(nxt, "C", a)), (1, osi(nxt, "C", a + 2)),
                    (-1, osi(nxt, "P", a)), (1, osi(nxt, "P", a - 2))]}


def fetch4(dry):
    """One request per night, windowed 15:49 -> 09:37 next session (month-wide windows cost ~$5)."""
    import databento as db
    client = db.Historical(dotenv_values(".env")["DATABENTO_API_KEY"])
    d4 = t4_days(intra.load("QQQ"))
    os.makedirs(OUT4, exist_ok=True)
    jobs = []
    for r in d4.itertuples():
        path = f"{OUT4}/QQQ_{r.day:%Y-%m-%d}.parquet"
        if os.path.exists(path):
            continue
        syms = sorted({x for legs in legs_t4(r.nxt, r.px).values() for _, x in legs})
        start = pd.Timestamp(r.day).tz_localize(ET) + pd.Timedelta(hours=15, minutes=49)
        end = pd.Timestamp(r.nxt).tz_localize(ET) + pd.Timedelta(hours=9, minutes=37)
        jobs.append((syms, start.tz_convert("UTC").isoformat(), end.tz_convert("UTC").isoformat(), path))
    sample = jobs[:: max(1, len(jobs) // 20)]
    est = sum(client.metadata.get_cost(dataset="OPRA.PILLAR", symbols=j[0], stype_in="raw_symbol",
                                       schema="cbbo-1m", start=j[1], end=j[2]) for j in sample)
    total = est / max(len(sample), 1) * len(jobs)
    print(f"{len(jobs)} nights, estimated ${total:.2f}", flush=True)
    if total > CAP_USD:
        sys.exit(f"ABORT: estimated ${total:.2f} > cap ${CAP_USD}")
    if dry:
        return

    def one(job):
        syms, start, end, path = job
        df = client.timeseries.get_range(dataset="OPRA.PILLAR", symbols=syms, stype_in="raw_symbol",
                                         schema="cbbo-1m", start=start, end=end).to_df().reset_index()
        keep = [k for k in ("ts_event", "ts_recv", "symbol", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00")
                if k in df.columns]
        df[keep].rename(columns=lambda k: k.replace("_00", "")).to_parquet(path)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, jobs))
    print("done", flush=True)


def priced4(book, d4):
    rows, skipped = [], 0
    for r in d4.itertuples():
        for v, legs in legs_t4(r.nxt, r.px).items():
            qin, qout = [], []
            for _, sym in legs:
                qin.append(book.quote(sym, r.day, T4_IN))
                qout.append(book.quote(sym, r.nxt, T4_OUT))
            if any(q is None for q in qin + qout):
                skipped += 1
                continue
            cost = sum(a if sg > 0 else -b for (sg, _), (b, a) in zip(legs, qin))
            val = sum(b if sg > 0 else -a for (sg, _), (b, a) in zip(legs, qout))
            fees = FEE * len(legs) * 2 / 100
            k = sorted(int(x[-8:]) / 1000 for _, x in legs)
            risk = max(k[1] - k[0], k[3] - k[2]) + cost + fees
            rows.append((v, r.day, cost, val, fees, risk))
    p = pd.DataFrame(rows, columns=["v", "day", "cost", "val", "fees", "risk"])
    p["pnl"] = p.val - p.cost - p.fees
    p["r"] = p.pnl / p.risk
    return p[p.risk > 0], skipped


def main4():
    M = intra.load("QQQ")
    d4 = t4_days(M)
    p, skipped = priced4(Book(OUT4), d4)
    p.to_parquet("data/research/contest/t4_trades.parquet")
    cal = [d for d in M["close"].index if pd.Timestamp(START) <= d < pd.Timestamp(END)]
    print(f"T4 nights {len(d4)}, variant-nights unpriced {skipped}")
    rep = report(p, cal)
    pd.set_option("display.width", 250, "display.max_columns", 60)
    print(rep.round(4).T.to_string())
    rep.to_csv("data/research/contest/t4_report.csv", index=False)


# ------------------------------------------------------------------ T6: QQQ 0DTE long straddle 09:45 -> 15:50
OUT6 = "data/research/contest/opra_t6"
T6_DEC, T6_OUT = 15, 381


def t6_days(M):
    f = pd.read_parquet(RAW_FACTOR)["factor"]
    days = [d for d in M["close"].index if pd.Timestamp(START) <= d < pd.Timestamp(END)]
    return pd.DataFrame([(d, float(M["close"].loc[d][T6_DEC]) * f[d]) for d in days], columns=["day", "px"])


def legs_t6(day, px):
    k = int(round(px))
    return [(1, osi(day, "C", k)), (1, osi(day, "P", k))]


def fetch6():
    import databento as db
    client = db.Historical(dotenv_values(".env")["DATABENTO_API_KEY"])
    os.makedirs(OUT6, exist_ok=True)
    jobs = []
    for r in t6_days(intra.load("QQQ")).itertuples():
        syms = [x for _, x in legs_t6(r.day, r.px)]
        for tag, (h, m) in (("a", (9, 44)), ("b", (15, 49))):
            path = f"{OUT6}/QQQ_{r.day:%Y-%m-%d}{tag}.parquet"
            if not os.path.exists(path):
                st = pd.Timestamp(r.day).tz_localize(ET) + pd.Timedelta(hours=h, minutes=m)
                jobs.append((syms, st.tz_convert("UTC").isoformat(),
                             (st + pd.Timedelta(minutes=5)).tz_convert("UTC").isoformat(), path))

    def one(job):
        syms, start, end, path = job
        try:
            df = client.timeseries.get_range(dataset="OPRA.PILLAR", symbols=syms, stype_in="raw_symbol",
                                             schema="cbbo-1m", start=start, end=end).to_df().reset_index()
        except Exception as exc:
            print(f"{path}: {type(exc).__name__} {str(exc)[:100]}", flush=True)
            return
        keep = [k for k in ("ts_recv", "symbol", "bid_px_00", "ask_px_00") if k in df.columns]
        df[keep].rename(columns=lambda k: k.replace("_00", "")).to_parquet(path)

    print(f"{len(jobs)} windows", flush=True)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, jobs))
    print("done", flush=True)


def main6():
    M = intra.load("QQQ")
    book = Book(OUT6)
    rows, skipped = [], 0
    for r in t6_days(M).itertuples():
        x = price_trade(book, legs_t6(r.day, r.px), r.day, T6_DEC, T6_OUT - 1)
        if x is None:
            skipped += 1
            continue
        cost, val, fees = x
        rows.append(("T6", r.day, cost, val, fees))
    p = pd.DataFrame(rows, columns=["v", "day", "cost", "val", "fees"])
    p["risk"] = p.cost + p.fees
    p["pnl"] = p.val - p.cost - p.fees
    p["r"] = p.pnl / p.risk
    p.to_parquet("data/research/contest/t6_trades.parquet")
    cal = [d for d in M["close"].index if pd.Timestamp(START) <= d < pd.Timestamp(END)]
    print(f"T6 days priced {len(p)}, unpriced {skipped}")
    rep = report(p, cal)
    pd.set_option("display.width", 250, "display.max_columns", 60)
    print(rep.round(4).T.to_string())
    rep.to_csv("data/research/contest/t6_report.csv", index=False)


def main():
    t, c = signal(intra.load("QQQ"))
    book = Book()
    p, skipped = priced(book, t, c)
    os.makedirs("data/research/contest", exist_ok=True)
    p.to_parquet("data/research/contest/t1t2_trades.parquet")
    cal = [d for d in intra.load("QQQ")["close"].index if pd.Timestamp(START) <= d < pd.Timestamp(END)]
    print(f"signal trades {len(t)}, condor days {len(c)}, legs-sets unpriced {skipped}")
    rep = report(p, cal)
    pd.set_option("display.width", 250, "display.max_columns", 60)
    print(rep.round(4).T.to_string())
    rep.to_csv("data/research/contest/t1t2_report.csv", index=False)


if __name__ == "__main__":
    if sys.argv[1:2] == ["fetch"]:
        fetch("--dry" in sys.argv)
    elif sys.argv[1:2] == ["fetch4"]:
        fetch4("--dry" in sys.argv)
    elif sys.argv[1:2] == ["run4"]:
        main4()
    elif sys.argv[1:2] == ["fetch6"]:
        fetch6()
    elif sys.argv[1:2] == ["run6"]:
        main6()
    else:
        main()
