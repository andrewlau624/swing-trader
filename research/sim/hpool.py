"""Study H-POOL (pre-registered in round1_prose.md, "Study H-POOL", program N 795 -> 796): the insider-buy next-session
open -> close effect as ONE pooled rule (ID1 | EV1 causal | EV2), judged once on the untouched 2006-15 decade.

    PYTHONPATH=. .venv/bin/python -m research.sim.hpool build   # Form 345 + Yahoo bars, events, data gates (no outcomes)
    PYTHONPATH=. .venv/bin/python -m research.sim.hpool judge   # the one look

Bars: Yahoo Finance chart API daily (regular session; Alpaca SIP starts 2016). Survivor-only (no delisted tickers).
Output: data/research/program/hpool_out.txt
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import zipfile

import numpy as np
import pandas as pd
import requests

from . import book as B
from .event_fetch import raw_bars
from .tender_fetch import get as sec_get, sec_headers
from swingtrader.daily.marketdata import trade_date

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
DIR = ROOT / "data/research/hpool"
N_PROG = 796
WIN = ("2006-01-01", "2015-12-31")
HALVES = (("2006-01-01", "2010-12-31"), ("2011-01-01", "2015-12-31"))
SLEEVE, CAP_EQ, CAP_ADV = 0.63, 0.10, 0.01
QS = [f"{y}q{q}" for y in range(2006, 2016) for q in range(1, 5)]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def out():
    f = open(PROG / "hpool_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


# ------------------------------------------------------------------ Form 345
def zips():
    (DIR / "insider").mkdir(parents=True, exist_ok=True)
    H = sec_headers()
    for q in QS:
        f = DIR / "insider" / f"{q}_form345.zip"
        if f.exists() and f.stat().st_size > 1e5:
            continue
        r = requests.get(f"https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{q}_form345.zip",
                         headers=H, timeout=120)
        r.raise_for_status()
        f.write_bytes(r.content); print(q, len(r.content), flush=True); time.sleep(0.2)
    return [DIR / "insider" / f"{q}_form345.zip" for q in QS]


def buys() -> pd.DataFrame:
    """As goal_g2.buys(), 2006q1..2015q4, keeping the issuer CIK."""
    f = DIR / "buys.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows = []
    for z in zips():
        Z = zipfile.ZipFile(z)
        rd = lambda n: pd.read_csv(Z.open(n), sep="\t", dtype=str, low_memory=False, on_bad_lines="skip")
        S = rd("SUBMISSION.tsv")[["ACCESSION_NUMBER", "FILING_DATE", "ISSUERCIK", "ISSUERTRADINGSYMBOL", "DOCUMENT_TYPE"]]
        N = rd("NONDERIV_TRANS.tsv")[["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_ACQUIRED_DISP_CD", "TRANS_SHARES", "TRANS_PRICEPERSHARE"]]
        R = rd("REPORTINGOWNER.tsv")[["ACCESSION_NUMBER", "RPTOWNER_RELATIONSHIP"]]
        N = N[(N.TRANS_CODE == "P") & (N.TRANS_ACQUIRED_DISP_CD == "A")].copy()
        N["sh"] = pd.to_numeric(N.TRANS_SHARES, errors="coerce")
        N["usd"] = N.sh * pd.to_numeric(N.TRANS_PRICEPERSHARE, errors="coerce")
        g = N.groupby("ACCESSION_NUMBER")[["usd", "sh"]].sum().reset_index()
        rel = R.groupby("ACCESSION_NUMBER").RPTOWNER_RELATIONSHIP.agg(lambda x: " ".join(map(str, x))).rename("rel").reset_index()
        g = g.merge(S, on="ACCESSION_NUMBER").merge(rel, on="ACCESSION_NUMBER", how="left")
        rows.append(g[g.DOCUMENT_TYPE.isin(["4", "4/A"])])
        print(z.name, len(rows[-1]), flush=True)
    X = pd.concat(rows)
    X["fd"] = pd.to_datetime(X.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    X["sym"] = X.ISSUERTRADINGSYMBOL.fillna("").str.upper().str.strip().str.replace("-", ".", regex=False)
    X["cik"] = pd.to_numeric(X.ISSUERCIK, errors="coerce")
    X["insider"] = X.rel.fillna("").str.contains("Director|Officer", case=False)
    X = X.dropna(subset=["fd", "usd", "cik"]).drop_duplicates("ACCESSION_NUMBER")
    X = X[["fd", "cik", "sym", "usd", "sh", "insider", "ACCESSION_NUMBER"]]
    X.to_parquet(f)
    return X


def candidates(X: pd.DataFrame) -> pd.DataFrame:
    """One row per (cik, fd) with officer/director code-P buys: $, $-weighted price, cluster / first flags."""
    I = X[X.insider & (X.usd > 0)].groupby(["cik", "fd"]).agg(usd=("usd", "sum"), sh=("sh", "sum"),
                                                                 sym=("sym", "last")).reset_index()
    I["px"] = I.usd / I.sh
    allf = {c: np.sort(g.fd.unique()) for c, g in X.groupby("cik")}
    insf = {c: np.sort(g.fd.unique()) for c, g in X[X.insider].groupby("cik")}
    clus, first = [], []
    for c, fd in zip(I.cik, I.fd):
        f64 = np.datetime64(fd)
        a = insf[c]
        clus.append(bool(((a < f64) & (a >= f64 - np.timedelta64(5, "D"))).any()))
        b = allf[c]
        j = np.searchsorted(b, f64) - 1
        first.append(fd >= pd.Timestamp("2008-01-01") and (j < 0 or (f64 - b[j]) > np.timedelta64(730, "D")))
    I["cluster"], I["first"] = clus, first
    return I[(I.fd >= WIN[0]) & (I.fd <= WIN[1])]


# ------------------------------------------------------------------ Yahoo bars
def yahoo(sym: str) -> pd.DataFrame | None:
    """Daily regular-session bars 2005-06..2016-02, split-adjusted -> raw via split events. Cached JSON."""
    (DIR / "yahoo").mkdir(parents=True, exist_ok=True)
    f = DIR / "yahoo" / f"{sym.replace('/', '_')}.json"
    if f.exists():
        j = json.loads(f.read_text())
    else:
        y = sym.replace(".", "-")
        u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{y}?period1=1117584000&period2=1456790400"
             f"&interval=1d&events=split&includePrePost=false")
        j = None
        for k in range(6):
            try:
                r = requests.get(u, headers=UA, timeout=30)
                if r.status_code == 429:
                    time.sleep(5 * (k + 1)); continue
                j = r.json(); break
            except (requests.RequestException, ValueError):
                time.sleep(3 * (k + 1))
        if j is None:
            return None
        f.write_text(json.dumps(j))
        time.sleep(0.25)
    try:
        res = j["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        ts = pd.to_datetime(res["timestamp"], unit="s", utc=True)
    except (KeyError, TypeError, IndexError):
        return None
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close", "volume")}, dtype=float)
    df.index = pd.DatetimeIndex(trade_date(pd.Series(ts)).values)
    df = df[~df.index.duplicated()].dropna(subset=["open", "close"])
    # Yahoo prices/volumes are split-adjusted for every split up to today: raw = adj x prod(num/den of later splits).
    # The fetch window ends 2016-02; later splits come from a second, split-only call (cached).
    sp = dict(res.get("events", {}).get("splits", {}))
    sp.update(later_splits(sym))
    fac = pd.Series(1.0, index=df.index)
    for v in sp.values():
        t = trade_date(pd.Timestamp(v["date"], unit="s", tz="UTC"))
        fac[df.index < t] *= v["numerator"] / v["denominator"]
    df["ro"], df["rc"] = df.open * fac, df.close * fac
    df["dv"] = df.close * df.volume                      # split-invariant $ volume
    return df


def later_splits(sym: str) -> dict:
    f = DIR / "yahoo" / f"{sym.replace('/', '_')}.splits.json"
    if f.exists():
        return json.loads(f.read_text())
    y = sym.replace(".", "-")
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{y}?period1=1456790400&period2=1790000000&interval=1mo&events=split"
    sp = {}
    for k in range(6):
        try:
            r = requests.get(u, headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(5 * (k + 1)); continue
            res = (r.json()["chart"]["result"] or [{}])[0]
            sp = res.get("events", {}).get("splits", {}); break
        except (requests.RequestException, ValueError, KeyError, TypeError):
            time.sleep(3 * (k + 1))
    f.write_text(json.dumps(sp)); time.sleep(0.25)
    return sp


def cik_ticker() -> dict:
    f = DIR / "company_tickers.json"
    if not f.exists():
        f.write_text(json.dumps(sec_get("https://www.sec.gov/files/company_tickers.json")))
    j = json.loads(f.read_text())
    return {int(v["cik_str"]): v["ticker"].upper().replace("-", ".") for v in j.values()}


def calendar() -> pd.DatetimeIndex:
    """Exchange sessions = SPY's Yahoo bar dates (regular sessions only)."""
    return yahoo("SPY").index


def attach(I: pd.DataFrame, log) -> pd.DataFrame:
    """Trade session d, raw open/close, prior raw close, ADV$, guard; one series per (cik, fd)."""
    cal = calendar()
    ct = cik_ticker()
    want = sorted({s for s in set(I.sym) | {ct.get(int(c), "") for c in I.cik} if s and s.replace(".", "").isalnum()})
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(6) as ex:
        for n, _ in enumerate(ex.map(yahoo, want)):
            if n % 500 == 0:
                print(f"  yahoo {n}/{len(want)}", flush=True)
    bars: dict[str, pd.DataFrame | None] = {}
    rows, nomap, noguard, nod = [], 0, 0, 0
    for n, r in enumerate(I.itertuples()):
        if n % 2000 == 0:
            print(f"  attach {n}/{len(I)} (series {len(bars)})", flush=True)
        i = cal.searchsorted(r.fd + pd.Timedelta(days=1))
        if i >= len(cal):
            continue
        d, dp = cal[i], cal[i - 1]
        tried, hit = [], None
        for s in dict.fromkeys([r.sym, ct.get(int(r.cik), "")]):
            if not s or not s.replace(".", "").isalnum():
                continue
            if s not in bars:
                bars[s] = yahoo(s)
            b = bars[s]
            tried.append(s)
            if b is None or d not in b.index or dp not in b.index:
                continue
            j = b.index.get_loc(d)
            if j < 20:
                continue
            pc = b.rc.iloc[j - 1]
            if not (0.67 <= r.px / pc <= 1.5):
                continue
            hit = (s, b, j)
            break
        if hit is None:
            if not tried or all(bars.get(s) is None for s in tried):
                nomap += 1
            elif not any(bars[s] is not None and d in bars[s].index for s in tried):
                nod += 1
            else:
                noguard += 1
            continue
        s, b, j = hit
        h = b.iloc[j - 20:j]
        rows.append(dict(cik=r.cik, sym=s, fd=r.fd, d=d, usd=r.usd, cluster=r.cluster, first=r.first,
                         o=b.ro.iloc[j], c=b.rc.iloc[j], pc=b.rc.iloc[j - 1], vol=b.volume.iloc[j],
                         adv=h.dv.mean(), stale=(d - r.fd).days))
    T = pd.DataFrame(rows)
    log(f"  (cik, fd) groups {len(I)}: no Yahoo series {nomap}, no bar on d / d-1 or < 20 sessions {nod}, "
        f"ticker guard fails {noguard}, mapped {len(T)}")
    return T


def eligible(T: pd.DataFrame, log) -> pd.DataFrame:
    a = (T.usd >= 1e4) & (T.adv >= 1e6)
    big = T.adv >= 2e7
    T = T.assign(id1=a, ev1=big & T.cluster, ev2=big & T["first"])
    T = T[(T.id1 | T.ev1 | T.ev2) & (T.pc >= 5) & (T.stale <= 7) & (T.o > 0)]
    nv = int((T.vol <= 0).sum())
    T = T[T.vol > 0]
    # one trade per (symbol, d): flags OR-ed across the fds that map to it
    T = T.sort_values("fd").groupby(["sym", "d"]).agg(o=("o", "first"), c=("c", "first"), adv=("adv", "first"),
                                                      usd=("usd", "sum"), id1=("id1", "any"), ev1=("ev1", "any"),
                                                      ev2=("ev2", "any")).reset_index()
    T["ret"] = T.c / T.o - 1
    nb = int((T.ret.abs() >= 0.5).sum())
    T = T[T.ret.abs() < 0.5]
    T = T[(T.d >= WIN[0]) & (T.d <= WIN[1])]
    log(f"  dropped: volume 0 on d {nv}, |ret| >= 50% {nb}; trades {len(T)} on {T.d.nunique()} sessions")
    return T


# ------------------------------------------------------------------ data gates
def gate_alpaca(syms: list[str], log) -> bool:
    rng = np.random.default_rng(796)
    syms = sorted(syms)
    pick = list(rng.choice(syms, size=min(300, len(syms)), replace=False))
    A = raw_bars(pick)
    diffs = []
    for s in pick:
        a = A.get(s)
        if a is None or not len(a):
            continue
        y = yahoo_range(s, "2016-01-01", "2019-12-31")
        if y is None:
            continue
        a = a[(a.index >= "2016-01-01") & (a.index <= "2019-12-31")]
        m = a.join(y[["open", "close"]], rsuffix="_y", how="inner")
        m = m[(m.open > 0) & (m.open_y > 0)]
        if not len(m):
            continue
        ra, ry = m.close / m.open - 1, m.close_y / m.open_y - 1
        ok = (ra.abs() < 0.5) & (ry.abs() < 0.5)
        diffs.append(pd.DataFrame({"a": ra[ok], "y": ry[ok], "s": s}))
    D = pd.concat(diffs)
    bias, corr = (D.y - D.a).mean() * 1e4, D.y.corr(D.a)
    med = (D.y - D.a).abs().median() * 1e4
    ok = abs(bias) <= 5 and corr >= 0.95
    log(f"  gate (i) Yahoo vs Alpaca 2016-19: {D.s.nunique()} symbols, {len(D)} name-days; mean(Y-A) {bias:+.2f}bp, "
        f"median |Y-A| {med:.2f}bp, corr {corr:.3f} -> {'OK' if ok else 'FAIL'}")
    return ok


def yahoo_range(sym, a, b):
    (DIR / "yahoo1619").mkdir(parents=True, exist_ok=True)
    f = DIR / "yahoo1619" / f"{sym.replace('/', '_')}.json"
    if not f.exists():
        y = sym.replace(".", "-")
        p1, p2 = int(pd.Timestamp(a).timestamp()), int(pd.Timestamp(b).timestamp()) + 86400
        j = None
        for k in range(6):
            try:
                r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{y}?period1={p1}&period2={p2}&interval=1d",
                                 headers=UA, timeout=30)
                if r.status_code == 429:
                    time.sleep(5 * (k + 1)); continue
                j = r.json(); break
            except (requests.RequestException, ValueError):
                time.sleep(3 * (k + 1))
        if j is None:
            return None
        f.write_text(json.dumps(j)); time.sleep(0.25)
    j = json.loads(f.read_text())
    try:
        res = j["chart"]["result"][0]; q = res["indicators"]["quote"][0]
    except (KeyError, TypeError, IndexError):
        return None
    df = pd.DataFrame({k: q[k] for k in ("open", "close")}, dtype=float)
    df.index = pd.DatetimeIndex(trade_date(pd.Series(pd.to_datetime(res["timestamp"], unit="s", utc=True))).values)
    return df[~df.index.duplicated()].dropna()


def build():
    log = out()
    log(f"=== H-POOL build {pd.Timestamp.now():%Y-%m-%d %H:%M} (events + data gates; no outcome printed) ===")
    X = buys()
    log(f"  Form 4 code-P accessions {len(X)}  {X.fd.min():%Y-%m-%d}..{X.fd.max():%Y-%m-%d}")
    I = candidates(X)
    log(f"  officer/director (cik, fd) groups in window {len(I)}; >= $10k {int((I.usd >= 1e4).sum())}; "
        f"cluster {int(I.cluster.sum())}; first-in-730d {int(I['first'].sum())}")
    T = attach(I, log)
    T.to_parquet(DIR / "mapped.parquet")
    k = I.usd >= 1e4
    cov = T[T.usd >= 1e4].groupby(["cik", "fd"]).ngroups / max(int(k.sum()), 1)
    log(f"  gate (ii) coverage of >= $10k groups: {cov:.1%} -> {'OK' if cov >= 0.40 else 'FAIL'}")
    log(f"  coverage by year: " + " ".join(
        f"{y}:{T[(T.usd >= 1e4) & (T.fd.dt.year == y)].groupby(['cik', 'fd']).ngroups / max(int((k & (I.fd.dt.year == y)).sum()), 1):.0%}"
        for y in range(2006, 2016)))
    E = eligible(T, log)
    E[["sym", "d", "o", "adv", "usd", "id1", "ev1", "ev2"]].to_parquet(DIR / "events.parquet")   # no outcome columns
    log(f"  eligible trades by year: {E.groupby(E.d.dt.year).size().to_dict()}; ID1 {int(E.id1.sum())} "
        f"EV1 {int(E.ev1.sum())} EV2 {int(E.ev2.sum())}")
    gate_alpaca(sorted(E.sym.unique()), log)


# ------------------------------------------------------------------ judge
def ctstat(x: np.ndarray, g: np.ndarray) -> tuple[float, float]:
    """Mean and t with the standard error clustered by g (trade date)."""
    m = x.mean()
    e = pd.Series(x - m).groupby(g).sum().values
    G, n = len(e), len(x)
    se = np.sqrt((e ** 2).sum() * G / (G - 1)) / n
    return m, m / se


def net(T, cost):
    c = B.cost_bps(cost, T.o.values, T.adv.values) if isinstance(cost, str) else np.full(len(T), float(cost))
    return T.ret.values - 2 * c / 1e4


def sleeve(T, days, E, cost):
    T = T.assign(nr=net(T, cost))
    g = {d: x for d, x in T.groupby("d")}
    v = []
    for d in days:
        x = g.get(d)
        if x is None:
            v.append(0.0); continue
        per = np.minimum(np.minimum(SLEEVE * E / len(x), CAP_EQ * E), CAP_ADV * x.adv.values)
        sh = np.floor(per / x.o.values)
        v.append(float((sh * x.o.values * x.nr.values).sum()) / E)
    return pd.Series(v, index=days)


def judge():
    log = out()
    log(f"=== H-POOL judge {pd.Timestamp.now():%Y-%m-%d %H:%M} (the one look; N {N_PROG}) ===")
    X = buys(); I = candidates(X)
    T = pd.read_parquet(DIR / "mapped.parquet")
    T = eligible(T, log)
    g = T.d.values
    for lab, cost in (("gross", 0.0), ("2.5bp", 2.5), ("tier", "tier"), ("tier_hi", "tier_hi")):
        x = net(T, cost)
        m, t = ctstat(x, g)
        q = np.quantile(x, 0.99)
        log(f"  {lab:8s} n {len(x)}  mean {m*1e4:+.1f}bp  t(date-cl) {t:+.2f}  median {np.median(x)*1e4:+.1f}  "
            f"hit {np.mean(x > 0):.1%}  ex-top-1% {x[x < q].mean()*1e4:+.1f}bp")
    res = {}
    for cost in ("tier", "tier_hi"):
        x = net(T, cost)
        m, t = ctstat(x, g)
        hv = []
        for a, b in HALVES:
            k = (T.d >= a) & (T.d <= b)
            hm, ht = ctstat(x[k.values], g[k.values])
            hv.append((hm, ht, int(k.sum())))
        yr = pd.Series(x, index=T.d.dt.year.values).groupby(level=0)
        log(f"  [{cost}] halves: " + "  ".join(f"{HALVES[i][0][:4]}-{HALVES[i][1][2:4]} {h[0]*1e4:+.1f}bp t {h[1]:+.2f} n {h[2]}"
                                               for i, h in enumerate(hv)))
        log(f"  [{cost}] by year: " + " ".join(f"{y}:{v.mean()*1e4:+.1f}({len(v)})" for y, v in yr))
        res[cost] = (m > 0 and t >= 2.0, all(h[0] > 0 for h in hv))
    for k in ("id1", "ev1", "ev2"):
        y = T[T[k]]
        if len(y) > 2:
            m, t = ctstat(net(y, "tier"), y.d.values)
            log(f"  context {k.upper()}-eligible: n {len(y)}  tier net {m*1e4:+.1f}bp  t {t:+.2f}")
    y = T[~T.id1]
    if len(y) > 2:
        m, t = ctstat(net(y, "tier"), y.d.values)
        log(f"  context added by EV1/EV2 only (not ID1): n {len(y)}  tier net {m*1e4:+.1f}bp  t {t:+.2f}")
    cal = calendar()
    days = cal[(cal >= WIN[0]) & (cal <= WIN[1])]
    yrs = len(days) / 252
    log(f"  trades/yr {len(T)/yrs:.0f}; sessions with >= 1 trade {T.d.nunique()/len(days):.0%}")
    for E in (2300, 10000, 25000, 100000):
        parts = []
        for cost in ("tier", "tier_hi"):
            s = sleeve(T, days, E, cost)
            nwt = s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))
            parts.append(f"{cost} {s.mean()*252*100:+.1f}%/yr ${s.mean()*252*E:+,.0f}/yr (t {nwt:+.2f}; "
                         f"halves {s[s.index <= HALVES[0][1]].mean()*252*100:+.1f}/{s[s.index >= HALVES[1][0]].mean()*252*100:+.1f}%)")
        log(f"  sleeve ${E:,}: " + "  |  ".join(parts))
    p = res["tier"]
    ok = p[0] and p[1] and len(T) >= 500
    rob = ok and all(res["tier_hi"])
    log(f"  bar: (1) tier mean>0 & t>=2 {p[0]}  (2) both halves >0 {p[1]}  (3) n>=500 {len(T) >= 500}  "
        f"tier_hi (1)&(2) {all(res['tier_hi'])}")
    log(f"  -> {'PASS (robust)' if rob else 'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    {"build": build, "judge": judge}[sys.argv[1]]()
