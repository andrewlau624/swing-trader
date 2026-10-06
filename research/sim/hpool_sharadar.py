"""Study H-POOL on Sharadar SF2 (registered judgment; program N 796, unchanged).

Pre-registration: `research/drafts/round1_prose.md` "Study H-POOL" (~:2759) and the
"Clarification - Study H-POOL, Sharadar data substitution and the SF2 2008 start" (~:3961).
This runner is the frozen one look; it does not edit or reuse `hpool.py` (Yahoo/survivor-only).

Rule. Officer/director (`isdirector=="Y"` or `isofficer=="Y"`) Form 4 / 4-A (`formtype` 4 or
"RESTATED - 4") non-derivative code-P acquisitions (`transactioncode=="P"`,
`securityadcode=="NA"`), summed per (ticker, filing date fd = SF2 `date`). Eligible if ANY of
  (a) ID1  : summed $ >= $10,000 and 20-session ADV$ (to the session before d) >= $1M
  (b) EV1  : ADV$ >= $20M and another officer/director purchase filing fd' in [fd-5d, fd)
  (c) EV2  : ADV$ >= $20M and no code-P filing by anyone at the issuer in the 730d before fd
             (evaluable only for fd >= 2010-01-01).
Common: raw prior close >= $5; next session d within 7d of fd; volume on d > 0; |open->close|
>= 50% dropped. Trade session d = the first regular session strictly after fd; one trade per
(ticker, d). Buy the opening cross of d, sell the closing cross of d; net = gross - 2 x per-side
cost (book.cost_bps "tier", "tier_hi"; 2.5bp/side comparison). Bars: Sharadar stocks+funds,
split-adjusted -> raw via closeunadj/close; delisted-complete.

Judged 2008-01-01..2015-12-31, halves 2008-10 and 2011-15. Pass bar at `tier`, SE clustered
by trade date: (1) mean net > 0 and t >= 2.0; (2) mean net > 0 in both halves; (3) n >= 500.
Robust if (1)+(2) also hold at `tier_hi`.

Run: PYTHONPATH=. .venv/bin/python research/sim/hpool_sharadar.py
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew

from research.sim import book as B
from sharadar import prices as sh_prices
from sharadar import table as sh_table

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "sim" / "hpool_sharadar_out.txt"
N_PROG = 796
WIN = (pd.Timestamp("2008-01-01"), pd.Timestamp("2015-12-31"))
HALVES = ((pd.Timestamp("2008-01-01"), pd.Timestamp("2010-12-31")),
          (pd.Timestamp("2011-01-01"), pd.Timestamp("2015-12-31")))
IN_LO, IN_HI = pd.Timestamp("2008-01-01"), pd.Timestamp("2015-12-31")
BAR_LO, BAR_HI = pd.Timestamp("2007-06-01"), pd.Timestamp("2016-03-01")
EV2_LO = pd.Timestamp("2010-01-01")
SLEEVE, CAP_EQ, CAP_ADV = 0.63, 0.10, 0.01
CHUNK = 1200
COLS = ["ticker", "date", "formtype", "isdirector", "isofficer", "transactioncode",
        "securityadcode", "transactionshares", "transactionpricepershare", "transactionvalue"]


def log_open():
    f = open(OUT, "w")

    def log(*a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        f.write(s + "\n")
        f.flush()
    return log, f


# ------------------------------------------------------------------ events
def events(log) -> tuple[pd.DataFrame, dict]:
    t = sh_table("insiders", columns=COLS,
                 filters=[("date", ">=", IN_LO.date()), ("date", "<=", IN_HI.date())])
    log(f"  SF2 insiders rows {IN_LO.date()}..{IN_HI.date()}: {len(t):,}")
    ft = t.formtype.astype(str)
    form4 = ft.str.startswith("4") | ft.str.startswith("RESTATED - 4")
    P4 = t[form4 & (t.transactioncode == "P")].copy()
    log(f"  Form 4 / RESTATED-4 code-P rows: {len(P4):,}  "
        f"(securityadcode {P4.securityadcode.value_counts().to_dict()})")
    da = int((P4.securityadcode == "DA").sum())
    P = P4[P4.securityadcode == "NA"].copy()              # non-derivative acquired, as hpool
    log(f"  code-P non-derivative acquired (NA): {len(P):,}  (derivative acquired DA excluded: {da:,})")
    P["fd"] = pd.to_datetime(P.date)
    P["usd"] = P.transactionvalue.astype(float)
    blank = int(P.usd.isna().sum())
    P["usd"] = P.usd.fillna(P.transactionshares.astype(float) * P.transactionpricepershare.astype(float))
    P["sh"] = P.transactionshares.astype(float)
    P = P[P.usd.notna() & (P.usd > 0) & (P.sh > 0)]
    log(f"  with usable $ and shares: {len(P):,}  "
        f"(transactionvalue blank, filled from shares*price: {blank:,})")
    P["insider"] = (P.isdirector == "Y") | (P.isofficer == "Y")
    log(f"  officer/director rows: {int(P.insider.sum()):,}  issuers {P.ticker.nunique():,}")

    allf = {k: np.sort(g.fd.values) for k, g in P.groupby("ticker")}
    insf = {k: np.sort(g.fd.values) for k, g in P[P.insider].groupby("ticker")}
    I = (P[P.insider].groupby(["ticker", "fd"], as_index=False)
         .agg(usd=("usd", "sum"), sh=("sh", "sum")))
    I["px"] = I.usd / I.sh
    clus = np.zeros(len(I), bool)
    first = np.zeros(len(I), bool)
    for k, (tk, fd) in enumerate(zip(I.ticker.values, I.fd.values)):
        a = insf.get(tk)
        if a is not None:
            j = np.searchsorted(a, fd)                    # side='left': strictly before fd
            clus[k] = j > 0 and (fd - a[j - 1]) <= np.timedelta64(5, "D")
        b = allf.get(tk)
        if b is not None:
            j = np.searchsorted(b, fd)
            ok = fd >= np.datetime64(EV2_LO)
            first[k] = bool(ok and (j == 0 or (fd - b[j - 1]) > np.timedelta64(730, "D")))
    I["cluster"], I["first"] = clus, first
    log(f"  officer/director (ticker, fd) groups: {len(I):,}; >= $10k {int((I.usd >= 1e4).sum()):,}; "
        f"cluster {int(I.cluster.sum()):,}; first-in-730d (fd>=2010-01) {int(I['first'].sum()):,}")
    return I, dict(rows=len(t), form4=len(P))


# ------------------------------------------------------------------ bars / attach
def calendar(log):
    sp = sh_prices(["SPY"], BAR_LO, BAR_HI, adjust="split")
    sp["date"] = pd.to_datetime(sp["date"])
    cal = pd.DatetimeIndex(np.sort(sp["date"].unique()))
    log(f"  sessions (SPY bars) {cal[0].date()}..{cal[-1].date()}: {len(cal):,}")
    return cal


def attach(I, cal, log):
    calv = cal.values
    rows, nomap, nod, noguard, stale = [], 0, 0, 0, 0
    cand: dict[str, np.ndarray] = {}
    tks = sorted(I.ticker.unique())
    for c0 in range(0, len(tks), CHUNK):
        chunk = tks[c0:c0 + CHUNK]
        G = I[I.ticker.isin(chunk)]
        b = sh_prices(chunk, BAR_LO, BAR_HI, adjust="split")
        if b is None or not len(b):
            nomap += len(G)
            continue
        b["date"] = pd.to_datetime(b["date"])
        k = (b.closeunadj.fillna(b.close) / b.close).to_numpy(float)
        b["ro"] = b.open.to_numpy(float) * k
        b["rc"] = b.close.to_numpy(float) * k
        b["dv"] = b.close.to_numpy(float) * b.volume.to_numpy(float)
        b["adv20"] = b.groupby("ticker").dv.transform(lambda s: s.rolling(20).mean().shift(1))
        bars: dict = {}
        for tk, g in b.groupby("ticker"):
            g = g.sort_values("date").reset_index(drop=True)
            m = ((g.date >= WIN[0]) & (g.date <= WIN[1]) & (g.adv20 > 0) &
                 (g.ro > 0) & (g.rc > 0)).to_numpy()
            if m.any():
                cst = B.cost_bps("tier", g.ro.to_numpy(float)[m], g.adv20.to_numpy(float)[m])
                cand[tk] = (g.rc.to_numpy(float)[m] / g.ro.to_numpy(float)[m] - 1.0) - 2 * cst / 1e4
            bars[tk] = g
        for r in G.itertuples():
            bb = bars.get(r.ticker)
            if bb is None:
                nomap += 1
                continue
            arr = bb.date.values
            fd = np.datetime64(r.fd, "ns")
            j = np.searchsorted(calv, fd + np.timedelta64(1, "D"))
            if j >= len(calv):
                continue
            d, dp = calv[j], calv[j - 1]
            if (d - fd) > np.timedelta64(7, "D"):
                stale += 1
                continue
            i = np.searchsorted(arr, d)
            if i >= len(arr) or arr[i] != d or i < 20:
                nod += 1
                continue
            ip = i - 1
            if ip < 0 or arr[ip] != dp:
                nod += 1
                continue
            pc = float(bb.rc.values[ip])
            if pc <= 0:
                nod += 1
                continue
            if not (0.67 <= r.px / pc <= 1.5):
                noguard += 1
                continue
            rows.append(dict(ticker=r.ticker, fd=r.fd, d=pd.Timestamp(d), usd=float(r.usd),
                             cluster=bool(r.cluster), first=bool(r.first),
                             o=float(bb.ro.values[i]), c=float(bb.rc.values[i]), pc=pc,
                             adv=float(bb.dv.values[i - 20:i].mean()),
                             vol=float(bb.volume.values[i]), stale=int((pd.Timestamp(d) - r.fd).days)))
        log(f"  attach {min(c0 + CHUNK, len(tks))}/{len(tks)} tickers: mapped groups {len(rows):,}")
    log(f"  groups lost: no Sharadar series {nomap:,}, no bar on d/dp or <20 sessions {nod:,}, "
        f"ticker guard fails {noguard:,}, stale >7d {stale:,}; mapped {len(rows):,}")
    return pd.DataFrame(rows), cand


def eligible(T, log):
    a = (T.usd >= 1e4) & (T.adv >= 1e6)
    big = T.adv >= 2e7
    T = T.assign(id1=a, ev1=big & T.cluster, ev2=big & T["first"])
    T = T[(T.id1 | T.ev1 | T.ev2) & (T.pc >= 5) & (T.stale <= 7) & (T.o > 0)]
    log(f"  eligible (union, pc>=5, stale<=7, o>0): {len(T):,}")
    nv = int((T.vol <= 0).sum())
    T = T[T.vol > 0]
    T = (T.sort_values("fd").groupby(["ticker", "d"], as_index=False)
         .agg(o=("o", "first"), c=("c", "first"), adv=("adv", "first"), usd=("usd", "sum"),
              id1=("id1", "any"), ev1=("ev1", "any"), ev2=("ev2", "any")))
    T["ret"] = T.c / T.o - 1
    nb = int((T.ret.abs() >= 0.5).sum())
    T = T[T.ret.abs() < 0.5]
    T = T[(T.d >= WIN[0]) & (T.d <= WIN[1])]
    log(f"  dropped: volume 0 on d {nv}; |ret|>=50% {nb}; trades {len(T):,} on {T.d.nunique():,} sessions")
    return T


# ------------------------------------------------------------------ stats
def ctstat(x, g) -> tuple[float, float]:
    m = x.mean()
    e = pd.Series(x - m).groupby(g).sum().values
    G, n = len(e), len(x)
    se = np.sqrt((e ** 2).sum() * G / (G - 1)) / n
    return m, m / se


def net(T, cost):
    c = B.cost_bps(cost, T.o.values, T.adv.values) if isinstance(cost, str) else np.full(len(T), float(cost))
    return T.ret.values - 2 * c / 1e4


def dsr(x, N):
    """Repo convention (research/sim/shar_ibs.py:144): per-obs SR, V[SR]=1/T."""
    x = np.asarray(x, float)
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    em = 0.5772156649
    sr0 = np.sqrt(1 / T) * ((1 - em) * norm.ppf(1 - 1 / N) + em * norm.ppf(1 - 1 / (N * np.e)))
    den = np.sqrt(1 - skew(x) * sr + (kurtosis(x, fisher=False) - 1) / 4 * sr ** 2)
    return norm.cdf((sr - sr0) * np.sqrt(T - 1) / den), sr, sr0


def sleeve(T, days, E, cost):
    T = T.assign(nr=net(T, cost))
    g = {d: x for d, x in T.groupby("d")}
    v = []
    for d in days:
        x = g.get(d)
        if x is None:
            v.append(0.0)
            continue
        per = np.minimum(np.minimum(SLEEVE * E / len(x), CAP_EQ * E), CAP_ADV * x.adv.values)
        sh = np.floor(per / x.o.values)
        v.append(float((sh * x.o.values * x.nr.values).sum()) / E)
    return pd.Series(v, index=days)


def placebo(T, cand, log, draws=200):
    rng = np.random.default_rng(N_PROG)
    tk = T.ticker.values
    real = net(T, "tier").mean()
    ys = []
    for _ in range(draws):
        vals = np.empty(len(tk))
        for i, s in enumerate(tk):
            a = cand[s]
            vals[i] = a[rng.integers(len(a))]
        ys.append(vals.mean())
    ys = np.array(ys)
    log(f"  placebo (random non-event session per trade, {draws} draws, tier): mean {ys.mean()*1e4:+.1f}bp  "
        f"sd {ys.std(ddof=1)*1e4:.1f}  pctile of real {100*np.mean(ys < real):.0f}%  "
        f"real {real*1e4:+.1f}bp")
    return ys


def judge(log):
    t0 = time.time()
    log(f"=== H-POOL on Sharadar (registered judgment, N {N_PROG}) {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    log("causality: filings <= fd; prior close/ADV/guard/cluster/silence <= the session before d;")
    log("the only same-session inputs are volume>0 and the |ret|>=50% drop (counts reported).")
    I, counts = events(log)
    cal = calendar(log)
    T0, cand = attach(I, cal, log)
    T = eligible(T0, log)
    g = T.d.values
    n = len(T)
    for lab, cost in (("gross", 0.0), ("2.5bp", 2.5), ("tier", "tier"), ("tier_hi", "tier_hi")):
        x = net(T, cost)
        m, t = ctstat(x, g)
        q = np.quantile(x, 0.99)
        log(f"  {lab:8s} n {n}  mean {m*1e4:+.1f}bp  t(date-cl) {t:+.2f}  median {np.median(x)*1e4:+.1f}  "
            f"hit {np.mean(x > 0):.1%}  ex-top-1% {x[x < q].mean()*1e4:+.1f}bp")
    res = {}
    for cost in ("tier", "tier_hi"):
        x = net(T, cost)
        m, t = ctstat(x, g)
        hv = []
        for a, b in HALVES:
            k = ((T.d >= a) & (T.d <= b)).values
            hv.append((*ctstat(x[k], g[k]), int(k.sum())))
        yr = pd.Series(x, index=T.d.dt.year.values).groupby(level=0)
        log(f"  [{cost}] halves: " + "  ".join(
            f"{HALVES[i][0].year}-{HALVES[i][1].year} {h[0]*1e4:+.1f}bp t {h[1]:+.2f} n {h[2]}"
            for i, h in enumerate(hv)))
        log(f"  [{cost}] by year: " + " ".join(
            f"{y}:{v.mean()*1e4:+.1f}({len(v)})" for y, v in yr))
        res[cost] = (m > 0 and t >= 2.0, all(h[0] > 0 for h in hv))
    for k in ("id1", "ev1", "ev2"):
        y = T[T[k]]
        if len(y) > 2:
            m, t = ctstat(net(y, "tier"), y.d.values)
            log(f"  subset {k.upper()}-eligible: n {len(y)}  tier net {m*1e4:+.1f}bp  t {t:+.2f}")
    y = T[~T.id1]
    if len(y) > 2:
        m, t = ctstat(net(y, "tier"), y.d.values)
        log(f"  subset added by EV1/EV2 only: n {len(y)}  tier net {m*1e4:+.1f}bp  t {t:+.2f}")
    log(f"  trades/yr {n / (len(cal[(cal >= WIN[0]) & (cal <= WIN[1])]) / 252):.0f}; "
        f"sessions with >= 1 trade {T.d.nunique() / len(cal[(cal >= WIN[0]) & (cal <= WIN[1])]):.0%}")
    placebo(T, cand, log)
    xd = pd.Series(net(T, "tier"), index=T.d).groupby(level=0).mean()
    d, sr, sr0 = dsr(xd.values, N_PROG)
    log(f"  DSR at N {N_PROG}: daily (per trade-date) SR {sr:.3f} vs E[SR] {sr0:.3f} -> DSR {d:.3f} "
        f"(T {len(xd)} dates)")
    days = cal[(cal >= WIN[0]) & (cal <= WIN[1])]
    for E in (2300, 10000, 25000, 100000):
        parts = []
        for cost in ("tier", "tier_hi"):
            s = sleeve(T, days, E, cost)
            nwt = s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))
            parts.append(f"{cost} {s.mean()*252*100:+.1f}%/yr ${s.mean()*252*E:+,.0f}/yr (t {nwt:+.2f})")
        log(f"  sleeve ${E:,}: " + "  |  ".join(parts))
    p = res["tier"]
    ok = p[0] and p[1] and n >= 500
    rob = ok and all(res["tier_hi"])
    log(f"  bar: (1) tier mean>0 & t>=2 {p[0]}  (2) both halves >0 {p[1]}  (3) n>=500 {n >= 500}  "
        f"tier_hi (1)&(2) {all(res['tier_hi'])}")
    log(f"  -> {'PASS (robust)' if rob else 'PASS' if ok else 'FAIL'}")
    log(f"elapsed {time.time()-t0:.1f}s")


if __name__ == "__main__":
    log, f = log_open()
    try:
        judge(log)
    finally:
        f.close()
