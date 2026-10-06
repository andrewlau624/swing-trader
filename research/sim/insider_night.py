"""Study IN1/IN2: the insider-buy gap, captured from the filing (pre-registered in round1_prose.md, "Study IN").

IN1 (rule-compliant): officer/director open-market buy (>= $10k, ID3 universe) whose Form 4 is PUBLIC on a regular
session between 09:30 and 15:50 ET -> buy that session's official closing cross, sell the next official opening cross.
IN2 (research only; would need a user exception to the sessions rule): public 16:00-20:00 ET -> buy the first
extended-hours SIP minute bar starting >= public + 2 min (price = max(bar high, bar close + half the modelled spread)),
sell the next official opening cross.

    PYTHONPATH=. .venv/bin/python -m research.sim.insider_night events     # Form 4 groups + EDGAR headers (no prices)
    PYTHONPATH=. .venv/bin/python -m research.sim.insider_night fetch      # auctions, extended-hours minutes, quotes
    PYTHONPATH=. .venv/bin/python -m research.sim.insider_night run        # the one look (all halves at once)

Output: data/research/program/insider_night_out.txt
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

from . import book as B
from . import event_fetch as F
from .auction_fetch import _env
from .goal_g12 import buys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
CACHE = ROOT / "data/research/events/innight"
EVF = PROG / "insider_night_events.parquet"
LAG = pd.Timedelta(minutes=2)          # entry bar must start >= public + LAG
PUB = pd.Timedelta(minutes=1)          # public dissemination assumed <= acceptance + 1 min (Rogers-Skinner-Zechman 2017)
URL = "https://data.alpaca.markets/v2/stocks"


def out():
    f = open(PROG / "insider_night_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def _cal():
    s = F.raw_bars(["SPY"])["SPY"]
    return pd.DatetimeIndex(pd.to_datetime(s.index)).sort_values()


# ----------------------------------------------------------------------------- events (no outcome data)
def events():
    log = out()
    log(f"=== IN events {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    X = buys()
    X = X[X.insider & (X.usd >= 1e4) & (X.usd < 1e10)].copy()
    cal = _cal()
    # cheap pre-filter on the filing date's prior session (exact filters are re-applied at the public time)
    bars = F.raw_bars(sorted(X.sym.unique()))
    keep = []
    for s, g in X.groupby("sym"):
        b = bars.get(s)
        if b is None or len(b) < 25:
            continue
        b = b.copy(); b.index = pd.to_datetime(b.index); b = b.sort_index()
        adv = (b.close * b.volume).rolling(20, min_periods=15).mean()
        i = b.index.searchsorted(g.fd.values) - 1          # last session strictly before fd
        ok = (i >= 0)
        a = np.where(ok, adv.values[np.clip(i, 0, None)], np.nan)
        pc = np.where(ok, b.close.values[np.clip(i, 0, None)], np.nan)
        keep.append(g[(a >= 1.5e7) & (pc >= 4)])
    X = pd.concat(keep)
    log(f"  officer/director >= $10k accessions passing the loose ADV/price pre-filter: {len(X)}")
    have = {p.stem for p in (ROOT / "data/research/events/hdr").glob("*.json")}
    need = [r for r in X.itertuples() if r.ACCESSION_NUMBER not in have]
    log(f"  headers cached {len(X) - len(need)}, to fetch {len(need)}")
    for j, r in enumerate(need):
        F.hdr(r.ISSUERCIK, r.ACCESSION_NUMBER)
        if j % 1000 == 0:
            print(f"  hdr {j}/{len(need)}", flush=True)
    acc = []
    for r in X.itertuples():
        h = F.hdr(r.ISSUERCIK, r.ACCESSION_NUMBER)
        acc.append(F.accepted_et(h))
    X["acc"] = pd.to_datetime(acc)
    X = X.dropna(subset=["acc"])
    X.to_parquet(EVF)
    log(f"  with acceptance stamps: {len(X)}")


def classify(X: pd.DataFrame, cal: pd.DatetimeIndex) -> pd.DataFrame:
    """Per (sym, acceptance calendar day): the earliest acceptance; its public time; the window it falls in."""
    X = X.sort_values("acc").copy()
    X["aday"] = X.acc.dt.normalize()
    X["pub"] = X.acc + PUB
    # $ known by the entry: only accessions accepted no later than the group's first one + 0 (the first filing)
    g = X.groupby(["sym", "aday"]).agg(acc=("acc", "first"), pub=("pub", "first"), usd_first=("usd", "first"),
                                        usd_day=("usd", "sum"), fd=("fd", "first"), n=("usd", "size")).reset_index()
    hm = g.pub.dt.hour * 60 + g.pub.dt.minute
    sess = g.aday.isin(cal)
    g["win"] = np.select([sess & (hm >= 570) & (hm < 950), sess & (hm >= 960) & (hm < 1200)], ["IN1", "IN2"], "other")
    return g


# ----------------------------------------------------------------------------- price fetches
def _get(path, q, H):
    for k in range(6):
        try:
            r = requests.get(f"{URL}/{path}", params=q, headers=H, timeout=40)
            if r.status_code == 429:
                time.sleep(3 * (k + 1)); continue
            r.raise_for_status(); return r.json()
        except requests.RequestException:
            time.sleep(2 * (k + 1))
    return {}


def _paged(path, key, q, H):
    rows, tok = {}, None
    while True:
        qq = dict(q, **({"page_token": tok} if tok else {}))
        j = _get(path, qq, H)
        for s, v in (j.get(key) or {}).items():
            rows.setdefault(s, []).extend(v)
        tok = j.get("next_page_token")
        if not tok:
            return rows


def _day(d):
    return pd.Timestamp(d).strftime("%Y-%m-%d")


def fetch_auctions(day_syms: dict, H, log):
    """official crosses: data/research/events/innight/auc/<day>.json = {sym: [auction rows]} (day's open+close)."""
    todo = [(d, s) for d, s in day_syms.items() if not (CACHE / "auc" / f"{_day(d)}.json").exists()]
    (CACHE / "auc").mkdir(parents=True, exist_ok=True)
    log(f"  auctions: {len(todo)} days to fetch")

    def one(a):
        d, syms = a
        rows = {}
        syms = sorted(syms)
        for i in range(0, len(syms), 100):
            rows.update(_paged("auctions", "auctions", {"symbols": ",".join(syms[i:i + 100]), "start": _day(d),
                                                        "end": _day(d), "feed": "sip", "limit": 10000}, H))
        json.dump(rows, open(CACHE / "auc" / f"{_day(d)}.json", "w"))
    with ThreadPoolExecutor(4) as ex:
        for j, _ in enumerate(ex.map(one, todo)):
            if j % 200 == 0:
                print(f"  auc {j}/{len(todo)}", flush=True)


def fetch_ext(day_syms: dict, H, log):
    """extended-hours SIP minute bars 16:00-20:00 ET on the filing day: innight/ext/<day>.json."""
    (CACHE / "ext").mkdir(parents=True, exist_ok=True)
    todo = [(d, s) for d, s in day_syms.items() if not (CACHE / "ext" / f"{_day(d)}.json").exists()]
    log(f"  extended-hours minutes: {len(todo)} days to fetch")

    def one(a):
        d, syms = a
        a0 = pd.Timestamp(_day(d) + " 15:59", tz="America/New_York").tz_convert("UTC")
        a1 = pd.Timestamp(_day(d) + " 20:00", tz="America/New_York").tz_convert("UTC")
        syms = sorted(syms)
        rows = {}
        for i in range(0, len(syms), 100):
            rows.update(_paged("bars", "bars", {"symbols": ",".join(syms[i:i + 100]), "timeframe": "1Min",
                                                "start": a0.isoformat().replace("+00:00", "Z"),
                                                "end": a1.isoformat().replace("+00:00", "Z"),
                                                "feed": "sip", "adjustment": "raw", "limit": 10000}, H))
        json.dump(rows, open(CACHE / "ext" / f"{_day(d)}.json", "w"))
    with ThreadPoolExecutor(4) as ex:
        for j, _ in enumerate(ex.map(one, todo)):
            if j % 200 == 0:
                print(f"  ext {j}/{len(todo)}", flush=True)


def fetch_quotes(ev: pd.DataFrame, H, log):
    """NBBO around each IN2 entry minute (entry minute .. +1 min): innight/q/<sym>_<stamp>.json."""
    (CACHE / "q").mkdir(parents=True, exist_ok=True)
    todo = [r for r in ev.itertuples() if not (CACHE / "q" / f"{r.sym}_{r.t:%Y%m%d%H%M}.json").exists()]
    log(f"  quotes: {len(todo)} entry minutes to fetch")

    def one(r):
        a0 = pd.Timestamp(r.t, tz="America/New_York").tz_convert("UTC")
        j = _get("quotes", {"symbols": r.sym, "start": a0.isoformat().replace("+00:00", "Z"),
                            "end": (a0 + pd.Timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                            "feed": "sip", "limit": 1000}, H)
        q = (j.get("quotes") or {}).get(r.sym, [])
        json.dump([{"bp": x.get("bp"), "ap": x.get("ap")} for x in q],
                  open(CACHE / "q" / f"{r.sym}_{r.t:%Y%m%d%H%M}.json", "w"))
    with ThreadPoolExecutor(4) as ex:
        for j, _ in enumerate(ex.map(one, todo)):
            if j % 500 == 0:
                print(f"  q {j}/{len(todo)}", flush=True)


# ----------------------------------------------------------------------------- assembly
def auction_px(day, sym, side):
    """Official cross print of `day` (side "o" open / "c" close): the largest-size print among the day's cross prints whose
    ET timestamp falls on that trade date (the repo's max-by-size rule; the vendor day can start the evening before, so
    prints stamped on another ET date are dropped). Also returns the print's ET hour (13 = half-day close)."""
    f = CACHE / "auc" / f"{_day(day)}.json"
    if not f.exists():
        return np.nan, np.nan
    d = _day(day)
    for x in json.load(open(f)).get(sym, []):
        if x.get("d") != d:
            continue
        lst = []
        for q in x.get(side) or []:
            t = pd.Timestamp(q["t"]).tz_convert("America/New_York")
            if t.strftime("%Y-%m-%d") == d:
                lst.append((q.get("s", 0), q["p"], t.hour))
        if lst:
            s_, p_, h_ = max(lst)
            return p_, h_
    return np.nan, np.nan


def ext_bars(day, sym) -> pd.DataFrame:
    f = CACHE / "ext" / f"{_day(day)}.json"
    if not f.exists():
        return pd.DataFrame()
    v = json.load(open(f)).get(sym, [])
    if not v:
        return pd.DataFrame()
    m = pd.DataFrame(v)
    m["t"] = pd.to_datetime(m.t).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return m.set_index("t")


def base(log):
    """events with filters re-applied at the public time, next session, both windows."""
    cal = _cal()
    G = classify(pd.read_parquet(EVF), cal)
    G = G[G.win != "other"].copy()
    nxt = {a: b for a, b in zip(cal[:-1], cal[1:])}
    G["nxt"] = G.aday.map(nxt)
    G = G.dropna(subset=["nxt"])
    bars = F.raw_bars(sorted(G.sym.unique()))
    rows = []
    for r in G.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            continue
        b = b.copy(); b.index = pd.to_datetime(b.index); b = b.sort_index()
        i = b.index.searchsorted(r.aday)                          # session index of the filing day (bars <= prior session known)
        if i < 20 or i >= len(b) or b.index[i] != r.aday:
            continue
        h = b.iloc[i - 20:i]
        adv, pc = float((h.close * h.volume).mean()), float(b.close.iloc[i - 1])
        if adv < 2e7 or pc < 5:
            continue
        rows.append(dict(r._asdict(), adv=adv, pc=pc, pcd=b.index[i - 1]))
    T = pd.DataFrame(rows).drop(columns=["Index"])
    log(f"  events after ADV >= $20M and prior close >= $5 (to the prior session): {len(T)} "
        f"(IN1 {int((T.win == 'IN1').sum())}, IN2 {int((T.win == 'IN2').sum())})")
    return T


def need_lists(T):
    au, ex = {}, {}
    for r in T.itertuples():
        au.setdefault(r.aday, set()).update({r.sym, "SPY"})
        au.setdefault(r.nxt, set()).update({r.sym, "SPY"})
        au.setdefault(r.pcd, set()).update({r.sym, "SPY"})
        if r.win == "IN2":
            ex.setdefault(r.aday, set()).update({r.sym, "SPY"})
    return au, ex


def fetch():
    log = out()
    log(f"=== IN fetch {pd.Timestamp.now():%Y-%m-%d %H:%M} (prices only; no returns computed) ===")
    T = base(log)
    T.to_parquet(PROG / "insider_night_base.parquet")
    au, ex = need_lists(T)
    H = _env()
    fetch_auctions(au, H, log)
    fetch_ext(ex, H, log)
    E = entries(T[T.win == "IN2"])
    fetch_quotes(E.dropna(subset=["t"])[["sym", "t"]], H, log)


def entries(T2: pd.DataFrame, lag=LAG, within=pd.Timedelta(minutes=30)) -> pd.DataFrame:
    """IN2 entry minute: the first extended-hours bar starting >= public + lag and before public + lag + within."""
    rows = []
    for r in T2.itertuples():
        m = ext_bars(r.aday, r.sym)
        t = hi = cl = v = n_ = pre = np.nan
        if len(m):
            m = m[m.index >= pd.Timestamp(_day(r.aday) + " 16:00")]
            e = m[(m.index >= r.pub + lag) & (m.index < r.pub + lag + within)]
            p = m[m.index < r.pub]
            pre = p.c.iloc[-1] if len(p) else np.nan
            if len(e):
                x = e.iloc[0]
                t, hi, cl, v, n_ = e.index[0], x.h, x.c, x.v, x.get("n", np.nan)
        rows.append(dict(sym=r.sym, aday=r.aday, t=t, hi=hi, cl=cl, bvol=v, bn=n_, pre=pre))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- the one look
SEL, JUD, OLD = ("2022-01-01", "2023-12-31"), ("2024-01-01", "2026-03-31"), ("2016-01-01", "2021-12-31")


def _spy_ext(day, t):
    m = ext_bars(day, "SPY")
    if not len(m):
        return np.nan
    m = m[m.index <= t]
    return m.c.iloc[-1] if len(m) else np.nan


def half_spreads(E):
    hs = []
    for r in E.itertuples():
        f = CACHE / "q" / f"{r.sym}_{r.t:%Y%m%d%H%M}.json" if pd.notna(r.t) else None
        v = np.nan
        if f is not None and f.exists():
            q = pd.DataFrame(json.load(open(f)))
            if len(q):
                q = q[(q.bp > 0) & (q.ap > q.bp)]
                mid = (q.ap + q.bp) / 2
                q = q[(q.ap - q.bp) < 0.1 * mid]
                if len(q):
                    v = float(((q.ap - q.bp) / 2 / ((q.ap + q.bp) / 2)).median())
        hs.append(v)
    return np.array(hs)


def assemble(log):
    T = pd.read_parquet(PROG / "insider_night_base.parquet")
    spy_c = {d: auction_px(d, "SPY", "c") for d in T.aday.unique()}
    half = {d for d, (p, h) in spy_c.items() if np.isfinite(h) and h < 14}
    log(f"  half-day sessions dropped: {int(T.aday.isin(half).sum())} events on {len(half)} days")
    T = T[~T.aday.isin(half)].copy()
    o = [auction_px(r.nxt, r.sym, "o")[0] for r in T.itertuples()]
    T["xo"] = o
    T["xc_next"] = [auction_px(r.nxt, r.sym, "c")[0] for r in T.itertuples()]
    T["cc"] = [auction_px(r.aday, r.sym, "c")[0] for r in T.itertuples()]
    T["spy_o"] = [auction_px(r.nxt, "SPY", "o")[0] for r in T.itertuples()]
    T["spy_c"] = [spy_c[r.aday][0] for r in T.itertuples()]
    T["claim"] = T.xo / T.cc - 1                           # official close of the filing day -> next official open
    # IN1
    A = T[T.win == "IN1"].copy()
    A["entry"], A["spy_e"], A["hs"] = A.cc, A.spy_c, 0.0
    # IN2
    Bq = T[T.win == "IN2"].copy()
    E = entries(Bq)
    Bq = Bq.reset_index(drop=True).join(E[["t", "hi", "cl", "bvol", "bn", "pre"]])
    hs = half_spreads(Bq)
    Bq["hs_q"] = hs
    pb = np.where(Bq.cl < 10, 0, np.where(Bq.cl < 20, 1, 2)); ab = (Bq.adv >= 5e7).astype(int)
    Bq["bucket"] = pb * 2 + ab
    med = Bq.groupby("bucket").hs_q.median()
    Bq["hs"] = np.maximum(Bq.hs_q.fillna(Bq.bucket.map(med)), 0.005 / Bq.cl)
    Bq["entry"] = np.maximum(Bq.hi, Bq.cl * (1 + Bq.hs))
    Bq["spy_e"] = [_spy_ext(r.aday, r.t) if pd.notna(r.t) else np.nan for r in Bq.itertuples()]
    X = pd.concat([A, Bq], ignore_index=True)
    X["gross"] = X.xo / X.entry - 1
    for m in ("tier", "tier_hi"):
        c = B.cost_bps(m, X.entry.values, X.adv.values) / 1e4
        X[f"net_{m}"] = X.gross - 2 * c
        X[f"adj_{m}"] = X[f"net_{m}"] - (X.spy_o / X.spy_e - 1)
    X["oc_next"] = X.xc_next / X.xo - 1
    X.to_parquet(PROG / "insider_night_trades.parquet")
    return X, med


def tstat(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std() / np.sqrt(len(x))) if len(x) > 2 else np.nan


def stats(T, col):
    x = T[col]
    if len(x) < 3:
        return dict(n=len(x))
    q = x.quantile(0.99)
    return dict(n=len(x), mean=x.mean() * 1e4, med=x.median() * 1e4, hit=(x > 0).mean(),
                dayt=tstat(T.groupby("aday")[col].mean()), ex1=x[x < q].mean() * 1e4)


def fmt(name, s):
    if s.get("n", 0) < 3:
        return f"    {name:28s} n {s.get('n', 0)}"
    return (f"    {name:28s} n {s['n']:5d} mean {s['mean']:+7.1f}bp med {s['med']:+7.1f} hit {s['hit']:.0%} "
            f"day-t {s['dayt']:+5.2f} ex-top1% {s['ex1']:+6.1f}")


def period(T, p):
    return T[(T.aday >= p[0]) & (T.aday <= p[1])]


def run():
    log = out()
    log(f"\n=== IN RUN (one look) {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    X, med = assemble(log)
    log(f"  IN2 half-spread model (bucket price<10/10-20/>=20 x ADV<50M/>=50M -> median quoted half-spread): "
        + " ".join(f"{k}:{v * 1e4:.0f}bp" for k, v in med.items()))
    for v in ("IN1", "IN2"):
        V = X[X.win == v]
        miss = V.entry.isna() | V.xo.isna() | V.spy_e.isna() | V.spy_o.isna()
        V = V[~miss]
        big = (V.gross.abs() >= 0.5)
        log(f"\n  --- {v}: {len(V) + int(miss.sum())} events, {int(miss.sum())} without an entry/exit/SPY price, "
            f"{int(big.sum())} with |gross| >= 50% dropped (split/print guard, inherited from ID/G12) ---")
        V = V[~big]
        verdict = {}
        for nm, p in (("select 2022-23", SEL), ("JUDGE 2024-26", JUD), ("2016-21", OLD)):
            P = period(V, p)
            sa, sr, sh = stats(P, "adj_tier"), stats(P, "net_tier"), stats(P, "adj_tier_hi")
            log(f"  {nm}:"); log(fmt("SPY-adj net (tier) JUDGED", sa)); log(fmt("raw net (tier)", sr)); log(fmt("SPY-adj net tier_hi", sh))
            log(fmt("claim window close->open", stats(P, "claim")))
            for sub, m in (("EV2-like n/a", None), (">= $500k first accession", P.usd_first >= 5e5)):
                if m is not None:
                    log(fmt(f"  subset {sub}", stats(P[m], "adj_tier")))
            verdict[nm] = sa
        j, s = verdict["JUDGE 2024-26"], verdict["select 2022-23"]
        ok = (j.get("n", 0) >= 3 and j["mean"] >= 25 and j["med"] > 0 and j["dayt"] >= 2 and j["ex1"] > 0
              and s.get("n", 0) >= 3 and s["mean"] > 0)
        log(f"  {v} VERDICT: {'PASS' if ok else 'DEAD'}")
        yrs = V.groupby(V.aday.dt.year).adj_tier.agg(["mean", "size"])
        log("  by year SPY-adj net: " + " ".join(f"{y}:{m * 1e4:+.0f}({n})" for y, (m, n) in yrs.iterrows()))
        x = V.adj_tier.sort_values(ascending=False); tot = x.sum()
        log(f"  concentration: top 1% of trades = {x.iloc[:max(1, len(x) // 100)].sum() / tot:.0%} of summed P&L, "
            f"top 5% = {x.iloc[:max(1, len(x) // 20)].sum() / tot:.0%}")
    # ------------------------------------------------ artifact checks
    log("\n  --- artifact checks ---")
    R = pd.read_parquet(EVF)
    R["dd"] = (R.fd - R.acc.dt.normalize()).dt.days
    hb = pd.cut(R.acc.dt.hour * 60 + R.acc.dt.minute, [0, 570, 960, 1050, 1200, 1321, 1440],
                labels=["<09:30", "09:30-16", "16-17:30", "17:30-20", "20-22", ">=22"], right=False)
    tab = R.groupby(hb, observed=True).dd.agg(n="size", same=lambda d: (d == 0).mean(), later=lambda d: (d > 0).mean(),
                                              earlier=lambda d: (d < 0).mean())
    log("  (a) FILING_DATE minus acceptance date, by acceptance time:\n" + tab.to_string(float_format=lambda v: f"{v:.3f}"))
    I2 = X[(X.win == "IN2")]
    has = I2.t.notna()
    log(f"  (c) IN2 events with no SIP trade in [public+2, public+32) min: {1 - has.mean():.0%} of {len(I2)}; "
        f"any ext bar 16:00-20:00 at all: {I2.cl.notna().mean():.0%}")
    I2 = I2[has & I2.xo.notna() & (I2.gross.abs() < 0.5)]
    pre = I2.pre / I2.cc - 1
    log(f"  (b) IN2 (n {len(I2)}): close cross -> last print before public {pre.mean() * 1e4:+.1f}bp (median {pre.median() * 1e4:+.1f}, "
        f"n {pre.notna().sum()}); close cross -> entry {(I2.entry / I2.cc - 1).mean() * 1e4:+.1f}bp; "
        f"entry -> next open {I2.gross.mean() * 1e4:+.1f}bp; claim close -> open {I2.claim.mean() * 1e4:+.1f}bp; "
        f"modelled half-spread median {I2.hs.median() * 1e4:.0f}bp (quoted share {I2.hs_q.notna().mean():.0%}); "
        f"entry high vs close {((I2.hi / I2.cl - 1).mean()) * 1e4:+.1f}bp")
    bd = I2.bvol * I2.cl
    for E in (2300, 1e4, 2.5e4, 1e5):
        log(f"      order 0.25x${E:,.0f} <= 20% of entry-bar $vol: {(0.25 * E <= 0.2 * bd).mean():.0%}  (median bar $vol ${bd.median():,.0f})")
    lag = entries(X[X.win == "IN2"], lag=pd.Timedelta(minutes=15))
    log(f"  IN2 +15 min lag: share with a bar {lag.t.notna().mean():.0%} (gross vs next open reported in sizing)")
    sizing(X, log)


def sizing(X, log):
    log("\n  --- sizing (judge 2024-26 and select 2022-23; raw net at tier, no compounding) ---")
    N = B.night_days(raw_price=True, max_corr=0.7)
    nr = pd.Series({d: float(np.mean(nd.ret)) for d, nd in N.items() if len(nd.syms)})
    nsy = {d: set(map(str, nd.syms)) for d, nd in N.items()}
    for v in ("IN1", "IN2"):
        V = X[(X.win == v) & X.entry.notna() & X.xo.notna() & (X.gross.abs() < 0.5)].copy()
        for nm, p in (("select", SEL), ("judge", JUD)):
            P = period(V, p)
            yrs = (pd.Timestamp(p[1]) - pd.Timestamp(p[0])).days / 365.25
            dly = P.groupby("aday").net_tier.mean()
            sh = dly.index.isin(nr.index)
            same = np.mean([s in nsy.get(d, ()) for s, d in zip(P.sym, P.aday)]) if len(P) else np.nan
            c = np.corrcoef(dly[sh], nr.reindex(dly.index[sh]))[0, 1] if sh.sum() > 5 else np.nan
            oc = P.oc_next.dropna()
            c2 = np.corrcoef(P.loc[oc.index, "net_tier"], oc)[0, 1] if len(oc) > 5 else np.nan
            pct = []
            for E in (2300, 1e4, 2.5e4, 1e5):
                pnl = 0.0
                for d, g in P.groupby("aday"):
                    a = min(0.5 * E / len(g), 0.25 * E)
                    sh_ = np.floor(a / g.entry.values)
                    if v == "IN2":
                        sh_ = np.minimum(sh_, np.floor(0.2 * (g.bvol * g.cl).values / g.entry.values))
                    pnl += float((sh_ * g.entry.values * g.net_tier.values).sum())
                pct.append(pnl / E / yrs * 100)
            log(f"  {v} {nm}: {len(P) / yrs:.0f} events/yr on {dly.size / yrs:.0f} nights/yr; nights shared with the night leg "
                f"{sh.mean():.0%}, same name {same:.1%}; corr(daily, night leg) {c:+.2f}; corr(trade, next open->close) {c2:+.2f}; "
                f"%/yr at $2.3k/$10k/$25k/$100k: " + " / ".join(f"{x:+.1f}" for x in pct))


if __name__ == "__main__":
    {"events": events, "fetch": fetch, "run": run}[sys.argv[1]]()
