"""SEO-QP (N 1241): follow-on offering research quiet-period run-up. Sibling of QP-RUNUP (N 1201, memory 95).

Pre-registration: research/drafts/round1_prose.md "Amendment - EXP round 6" (N 1241).
Rule history (verified from primary sources, see exp_seoqp_out.txt header):
  NASD 2711(f)(1)(B): 10 calendar days after a secondary offering, managers/co-managers; SEC approval 2002-05-10
    (Rel. 34-45908), quiet-period provisions effective +60 days = 2002-07-09. Exception: Rule 139 research on issuers with
    "actively-traded securities" (Reg M 101(c)(1): ADTV >= $1M and public float >= $150M).
  FINRA 2241(b)(2)(I): minimum 3 days after a secondary offering, managers/co-managers; effective 2015-09-25
    (Reg. Notice 15-30). Same actively-traded / Rule 139 exception; EGCs exempt.
  => Q = 10 for P < 2015-09-25, Q = 3 from 2015-09-25.

Stages (each cached in data/research/exp_seoqp/):
  index   EDGAR quarterly form.gz -> 424B4/424B5 rows (2003Q1..2026Q4)
  cand    map CIK -> Sharadar ticker, price/ADV/IPO filters (no forward returns read)
  heads   stream the first ~96KB of each candidate submission (.txt): SGML header (acceptance time) + cover page
  build   classify (common fixed-price takedown vs ATM / debt / preferred / units / non-underwritten), dedupe -> events
  run     the one judged run (prints the sha256 of this file first)

Usage: PYTHONPATH=. python research/sim/exp_seoqp.py {index|cand|heads|build|run}
SEC_USER_AGENT comes from swingtrader.config.get_env via news_judge.sec_headers(); it is never printed or stored.
"""
from __future__ import annotations

import gzip
import hashlib
import html
import io
import json
import math
import pathlib
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests
import scipy.stats as SS

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/exp_seoqp"
HEADS = CACHE / "heads"
OUT = ROOT / "research/sim/exp_seoqp_out.txt"
S = pathlib.Path.home() / "data" / "sharadar"
N_PROGRAM = 1241
RULE_2241 = pd.Timestamp("2015-09-25")
JUDGE = (pd.Timestamp("2003-01-01"), RULE_2241 - pd.Timedelta(days=1))   # 2003-01-01..2015-09-24 at Q=10
HALF_SPLIT = pd.Timestamp("2010-01-01")
REPORT = (RULE_2241, pd.Timestamp("2026-12-31"))                          # Q=3 era (touched by G31's all-events arm)
COST_SIDE = 0.0005
SAMPLE_SEED, SAMPLE_PER_YEAR = 1241, None    # set before any outcome is read if the head pull is too large
LINES: list[str] = []
_H: dict | None = None


def P(s=""):
    print(s, flush=True)
    LINES.append(str(s))


def headers() -> dict:
    global _H
    if _H is None:
        sys.path.insert(0, str(ROOT))
        from swingtrader.daily.news_judge import sec_headers
        _H = sec_headers()
    return _H


_LOCK = threading.Lock()
_LAST = [0.0]


def _pace(min_gap: float = 0.125):
    """Global pacing across threads: at most 8 requests/s (SEC's limit is 10/s)."""
    with _LOCK:
        w = _LAST[0] + min_gap - time.time()
        if w > 0:
            time.sleep(w)
        _LAST[0] = time.time()


def fetch(url: str, head_bytes: int | None = None) -> bytes | None:
    for k in range(6):
        _pace()
        try:
            r = requests.get(url, headers=headers(), timeout=60, stream=head_bytes is not None)
            if r.status_code in (429, 503):
                time.sleep(3 * (k + 1)); continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            if head_bytes is None:
                b = r.content
            else:
                b = b""
                for ch in r.iter_content(16384):
                    b += ch
                    if len(b) >= head_bytes:
                        break
                r.close()
            return b
        except requests.RequestException:
            time.sleep(3 * (k + 1))
    return None


# ---------------------------------------------------------------- stage: index
def stage_index():
    d = CACHE / "index"
    d.mkdir(parents=True, exist_ok=True)
    for y in range(2003, 2027):
        for q in range(1, 5):
            f = d / f"{y}Q{q}.parquet"
            if f.exists():
                continue
            if pd.Timestamp(f"{y}-{3*q-2:02d}-01") > pd.Timestamp.now():
                continue
            b = fetch(f"https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/form.gz")
            if not b:
                print("missing", y, q); continue
            t = gzip.decompress(b).decode("latin-1")
            rows = []
            for line in t.splitlines():
                if not line.startswith("424B4") and not line.startswith("424B5"):
                    continue
                m = re.match(r"^(\S+)\s+(.+?)\s{2,}(\d+)\s+(\d{4}-?\d{2}-?\d{2})\s+(edgar/\S+)", line)
                if m and m.group(1) in ("424B4", "424B5"):
                    rows.append(dict(form=m.group(1), company=m.group(2).strip(), cik=m.group(3).lstrip("0"),
                                     fd=pd.Timestamp(m.group(4)), path=m.group(5)))
            pd.DataFrame(rows).to_parquet(f)
            print(y, q, len(rows), flush=True)


def index() -> pd.DataFrame:
    return pd.concat([pd.read_parquet(f) for f in sorted((CACHE / "index").glob("*.parquet"))], ignore_index=True)


# ---------------------------------------------------------------- prices (Sharadar)
def sharadar_map() -> pd.DataFrame:
    tk = pd.read_parquet(S / "tickers.parquet")
    tk = tk[tk.table == "SEP"].copy()
    cats = tk.category.fillna("")
    tk = tk[cats.str.startswith("Domestic Common") | cats.str.startswith("ADR Common") | cats.str.startswith("Canadian Common")]
    tk["cik"] = tk.secfilings.fillna("").str.extract(r"CIK=0*(\d+)")[0]
    tk = tk.dropna(subset=["cik"])
    tk["f0"] = pd.to_datetime(tk.firstpricedate)
    tk["f1"] = pd.to_datetime(tk.lastpricedate)
    return tk[["cik", "ticker", "f0", "f1", "category", "siccode", "name", "isdelisted"]]


def load_prices(tickers) -> dict[str, pd.DataFrame]:
    st = pd.read_parquet(S / "stocks.parquet", columns=["ticker", "date", "closeadj", "closeunadj", "volume"],
                         filters=[("ticker", "in", sorted(set(tickers)))])
    st["date"] = pd.to_datetime(st.date)
    return {k: v.sort_values("date").reset_index(drop=True) for k, v in st.groupby("ticker")}


# ---------------------------------------------------------------- stage: cand
def stage_cand():
    """Universe filters that use only data at or before P (no forward return is read here)."""
    I = index()
    print("424B4/424B5 rows", len(I), I.groupby([I.fd.dt.year, "form"]).size().unstack().to_string())
    M = sharadar_map()
    X = I.merge(M, on="cik")
    X = X[(X.fd >= X.f0) & (X.fd <= X.f1 + pd.Timedelta(days=5))]
    X = X[X.siccode.fillna(0).astype(int) != 6770]                       # blank checks
    print("mapped to a Sharadar common-stock ticker live at P:", len(X))
    # first 424B4 of a CIK in the index = IPO candidate (also enforced below by >= 60 prior sessions)
    first4 = I[I.form == "424B4"].sort_values("fd").drop_duplicates("cik")[["cik", "path"]]
    X = X[~X.path.isin(set(first4.path))]
    g = load_prices(X.ticker.unique())
    keep = []
    for r in X.itertuples():
        d = g.get(r.ticker)
        if d is None:
            continue
        i = d.date.searchsorted(r.fd)                    # first session >= P
        if i < 60 or i >= len(d):
            continue                                     # < 60 prior sessions: IPO / new listing
        h = d.iloc[i - 20:i]
        px = d.closeunadj.iloc[i - 1]
        adv = float(np.median(h.closeunadj * h.volume))
        if px >= 5 and adv >= 1e7:
            keep.append(dict(r._asdict(), px_prev=px, adv=adv))
    C = pd.DataFrame(keep).drop(columns=["Index"])
    C.to_parquet(CACHE / "cand.parquet")
    print("candidates ($5+, ADV20 median $10M+, >= 60 prior sessions, not first 424B4):", len(C))
    print(C.groupby([C.fd.dt.year, "form"]).size().unstack().to_string())


# ---------------------------------------------------------------- stage: heads
def _head_file(path: str) -> pathlib.Path:
    return HEADS / (path.rsplit("/", 1)[-1].replace(".txt", "") + ".txt.gz")


def _get_head(path: str):
    f = _head_file(path)
    if f.exists():
        return
    b = fetch("https://www.sec.gov/Archives/" + path, head_bytes=96_000)
    if b is None:
        return
    f.write_bytes(gzip.compress(b))


def sample(C: pd.DataFrame) -> pd.DataFrame:
    if not SAMPLE_PER_YEAR:
        return C
    return (C.groupby(C.fd.dt.year, group_keys=False)
             .apply(lambda g: g.sample(min(len(g), SAMPLE_PER_YEAR), random_state=SAMPLE_SEED)))


def stage_heads():
    HEADS.mkdir(parents=True, exist_ok=True)
    C = sample(pd.read_parquet(CACHE / "cand.parquet"))
    todo = [p for p in C.path if not _head_file(p).exists()]
    print("heads to fetch", len(todo), "of", len(C), flush=True)
    with ThreadPoolExecutor(8) as ex:   # I/O-bound threads, globally paced to <= 8 req/s; CPU stays < 1 core
        for j, _ in enumerate(ex.map(_get_head, todo)):
            if j % 500 == 0:
                print("  ", j, time.strftime("%H:%M:%S"), flush=True)


# ---------------------------------------------------------------- stage: build (classification)
def _text(path: str) -> tuple[str, str]:
    """(SGML header, first-document plain text)."""
    f = _head_file(path)
    if not f.exists():
        return "", ""
    raw = gzip.decompress(f.read_bytes()).decode("latin-1", "ignore")
    i = raw.find("<DOCUMENT>")
    hdr, body = raw[: i if i > 0 else 4000], raw[i if i > 0 else 0:]
    body = re.sub(r"(?is)<(style|script)[^>]*>.*?(</\1>|$)", " ", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = html.unescape(body)
    body = re.sub(r"[\u200b-\u200d\ufeff]", " ", body)
    body = body.translate({0x2019: "'", 0x2018: "'", 0x201c: '"', 0x201d: '"', 0x2013: "-", 0x2014: "-", 0x2011: "-"})
    body = re.sub(r"\s+", " ", body)
    return hdr, body


ATM = re.compile(r"at[- ]the[- ]market|equity distribution agreement|(?:equity |open market )?sales agreement|"
                 r"distribution agreement|sales agency (?:financing )?agreement|controlled equity offering|"
                 r"equity offering sales agreement|ordinary brokers'? transactions|sales agents?\b", re.I)
OTHER = re.compile(r"warrants?\b|\bunits\b|rights offering|subscription rights|exchange offer|dividend reinvestment|"
                   r"direct stock purchase|stock purchase plan|purchase contracts|preferred|"
                   r"notes due|debentures|% notes|convertible", re.I)
NONUW = re.compile(r"placement agents?|registered direct", re.I)
BLOCK = re.compile(r"agreed to purchase (?:all of )?(?:the )?[\d,]+ (?:shares|common shares|ordinary shares)[^$]{0,120}"
                   r"(?:aggregate )?purchase price", re.I)
PRECOVER = re.compile(r"notes due|% notes|debentures|preferred|equity units|\bunits\b|warrants|up to \$|"
                      r"aggregate offering price of up to|sales agreement|distribution agreement|sales agents?", re.I)
PRELIM = re.compile(r"subject to completion|preliminary prospectus supplement|is not complete and may be changed", re.I)
COMMON = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)? million)\s+(?:(?:shares|ordinary shares|american depositary shares|ADSs)"
                    r"\b[^$]{0,140}?\b(?:common stock|common shares|ordinary shares|class [a-c] (?:common|ordinary)|"
                    r"american depositary shares|ADSs)|common shares|shares of common stock)", re.I)
FIXPX = re.compile(r"(?:public offering price|price to (?:the )?public|offering price)[^$]{0,120}\$\s?(\d{1,4}\.\d{2,4})", re.I)
PX = re.compile(r"(?:per share|per ads)\W{0,60}\$\s?(\d{1,4}\.\d{2,4})|(?:from (?:us|the selling \w+)|purchase the shares) at "
                r"(?:a price of )?\$\s?(\d{1,4}\.\d{2,4}) per (?:share|ADS)", re.I)


def _price(rx, t: str) -> float | None:
    """First per-share price >= $0.50 not preceded by 'par value' (fee tables / par values are skipped)."""
    for m in rx.finditer(t):
        v = float(next(x for x in m.groups() if x))
        if v >= 0.5 and "par value" not in t[max(0, m.start() - 40): m.start() + 20].lower():
            return v
    return None


def classify(body: str) -> tuple[str, float]:
    """Heuristic on the prospectus-supplement cover (frozen before any outcome was read).

    The cover's offered security = the first '<N> Shares ... Common Stock' match in the first 4,000 chars (or the first
    10,000 when a fee table pushes the cover down, unless debt/preferred/units/warrants/ATM words precede the match).
      prelim  : 'subject to completion' / preliminary supplement in the first 1,500 chars (no final price)
      atm     : at-the-market / sales or distribution agreement / sales agent within the cover window
                (match-300 .. match+700 chars), OR no fixed per-share price parsed (public offering price in the first
                12,000 chars, or 'Per Share ... $X' / 'from us at $X per share' in the first 40,000)
                (a 424B5 with no fixed-price takedown is treated as an ATM or continuous offering, not an SEO)
      other   : warrants / units / rights / DRIP / purchase contracts / preferred / notes / convertible in the cover title
                (match-300 .. match+150 chars)
      nonuw   : placement agent / registered direct in the first 6,000 chars (no manager -> no manager quiet period)
      nocommon: no common-share count on the cover (debt, preferred, structured notes, plan prospectuses)
      block   : no per-share price but 'agreed to purchase N shares ... aggregate purchase price' (kept as an event)
      common  : everything else, incl. block trades / bought deals offered 'from time to time' at market prices
    """
    if PRELIM.search(body[:1500]):
        return "prelim", float("nan")
    m = COMMON.search(body[:4000])
    if not m:                    # cover pushed down by a fee table / legends: look further, unless the cover is something else
        m = COMMON.search(body[:10000])
        if m and PRECOVER.search(body[:m.start()]):
            m = None
    if not m:
        return "nocommon", float("nan")
    w = body[max(0, m.start() - 300): m.end() + 700]
    if ATM.search(w) or ATM.search(body[:1500]):
        return "atm", float("nan")
    if OTHER.search(body[max(0, m.start() - 300): m.end() + 150]):
        return "other", float("nan")
    if NONUW.search(body[:6000]):
        return "nonuw", float("nan")
    q = _price(FIXPX, body[:12000]) or _price(PX, body[:40000])
    if not q and BLOCK.search(body[:12000]):
        return "block", float("nan")      # bought deal priced only in aggregate: a fixed-size takedown, kept
    if not q:
        return "atm", float("nan")
    return "common", q


def stage_build():
    C = sample(pd.read_parquet(CACHE / "cand.parquet"))
    rows = []
    for r in C.itertuples():
        hdr, body = _text(r.path)
        if not body:
            rows.append(dict(path=r.path, cls="nohead", acc=None, offer=np.nan)); continue
        acc = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", hdr)
        cls, offer = classify(body)
        rows.append(dict(path=r.path, cls=cls, acc=acc.group(1) if acc else None, offer=offer))
    K = C.merge(pd.DataFrame(rows), on="path")
    K["acc"] = pd.to_datetime(K.acc, format="%Y%m%d%H%M%S", errors="coerce")
    print(K.groupby([K.fd.dt.year, "cls"]).size().unstack(fill_value=0).to_string())
    E = K[K.cls.isin(["common", "block"])].copy()
    E = E[(E.offer / E.px_prev).between(0.5, 1.2) | (E.cls == "block")]   # parse guard (as G31): offer 50-120% of prior close
    E = E.sort_values(["ticker", "fd"])
    keep, last = [], {}
    for r in E.itertuples():
        if r.ticker in last and (r.fd - last[r.ticker]).days <= 30:
            continue
        last[r.ticker] = r.fd
        keep.append(r.Index)
    E = E.loc[keep]
    K.to_parquet(CACHE / "classified.parquet")
    E.to_parquet(CACHE / "events.parquet")
    print("events (common fixed-price, parse guard, one per ticker per 30d):", len(E))
    print("  by year", E.groupby(E.fd.dt.year).size().to_dict())


# ---------------------------------------------------------------- stage: run (the one judged run)
def Q_of(p: pd.Timestamp) -> int:
    return 10 if p < RULE_2241 else 3


def day_t(x, dates):
    df = pd.DataFrame({"x": np.asarray(x, float), "d": np.asarray(dates)}).dropna()
    m = df.x.mean()
    gsum = df.groupby("d").x.apply(lambda s: (s - m).sum())
    se = math.sqrt((gsum ** 2).sum()) / len(df)
    return m / se if se > 0 else float("nan")


def dsr(x, n_trials):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False)
    g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


def stats(x, dates):
    x = pd.Series(np.asarray(x, float)).dropna()
    d = pd.Series(np.asarray(dates))[x.index]
    srt = x.sort_values()
    return dict(n=len(x), mean=x.mean(), med=x.median(), hit=(x > 0).mean(), t=day_t(x.values, d.values),
                ex5=srt.iloc[:-5].mean() if len(x) > 5 else np.nan)


def summ(name, x, dates):
    s = stats(x, dates)
    if s["n"] < 5:
        P(f"  {name:44s} n {s['n']}"); return s
    P(f"  {name:44s} n {s['n']:5d} mean {s['mean']*1e4:+7.1f}bp med {s['med']*1e4:+7.1f} hit {100*s['hit']:4.1f}% "
      f"t_day {s['t']:+5.2f} ex-top5 {s['ex5']*1e4:+7.1f}")
    return s


def windows(E, g, spy, Qcol):
    out = []
    for r in E.itertuples():
        d = g.get(r.ticker)
        if d is None:
            continue
        Q = getattr(r, Qcol)
        ix = np.flatnonzero(d.date.values >= np.datetime64(r.fd + pd.Timedelta(days=int(Q))))
        if not len(ix):
            continue
        x = ix[0]
        e, xx = x - 3, x - 1
        if e < 1:
            continue
        de, dx = d.date.iloc[e], d.date.iloc[xx]
        acc = r.acc if not pd.isna(r.acc) else pd.Timestamp(r.fd) + pd.Timedelta(hours=12)
        tradeable = acc < de + pd.Timedelta(hours=16)         # filing public before the entry close
        ret = d.closeadj.iloc[xx] / d.closeadj.iloc[e] - 1
        sp = spy.get(dx, np.nan) / spy.get(de, np.nan) - 1
        out.append(dict(ticker=r.ticker, fd=r.fd, Q=Q, de=de, dx=dx, ret=ret, spy=sp, tradeable=tradeable,
                        gap_x=(d.date.iloc[x] - r.fd).days, last=d.date.iloc[-1], delisted=r.isdelisted == "Y",
                        offer=r.offer, px_prev=r.px_prev, adv=r.adv))
    R = pd.DataFrame(out)
    R["net"] = R.ret - 2 * COST_SIDE
    R["xspy"] = R.ret - R.spy - 2 * COST_SIDE
    return R


def stage_run():
    sha = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    P(f"SEO-QP (N 1241) run {pd.Timestamp.now():%Y-%m-%d %H:%M}; code sha256 {sha}")
    P("rule history: NASD 2711(f)(1)(B) 10 cal days (eff. 2002-07-09, SEC Rel. 34-45908) -> FINRA 2241(b)(2)(I) min 3 days "
      "(eff. 2015-09-25, Reg. Notice 15-30); both exempt Rule 139 research on Reg M 101(c)(1) actively-traded issuers")
    P("primary = net excess vs SPY (close->close, 5bp/side); raw net reported. Q = 10 if P < 2015-09-25 else 3.")
    E = pd.read_parquet(CACHE / "events.parquet")
    E["Q"] = E.fd.map(Q_of)
    E["Q3"] = 3
    g = load_prices(E.ticker.unique())
    fu = pd.read_parquet(S / "funds.parquet", columns=["ticker", "date", "closeadj"], filters=[("ticker", "in", ["SPY"])])
    spy = fu.assign(date=pd.to_datetime(fu.date)).set_index("date").closeadj
    R = windows(E, g, spy, "Q")
    PL = windows(E, g, spy, "Q3")
    P(f"events {len(E)}; with a window {len(R)}; by year " + " ".join(f"{y}:{n}" for y, n in R.groupby(R.fd.dt.year).size().items()))

    J = R[(R.fd >= JUDGE[0]) & (R.fd <= JUDGE[1])]
    P(f"\nJUDGE 2003-01..2015-09-24 (Q=10): x = first session >= P+10d; buy close x-3, sell close x-1")
    s = summ("net excess vs SPY [primary]", J.xspy, J.de)
    summ("net raw", J.net, J.de)
    summ("net excess, 2x cost", J.xspy - 2 * COST_SIDE, J.de)
    h1 = summ("half 2003-09", J[J.fd < HALF_SPLIT].xspy, J[J.fd < HALF_SPLIT].de)
    h2 = summ("half 2010-15", J[J.fd >= HALF_SPLIT].xspy, J[J.fd >= HALF_SPLIT].de)
    P("  by year (mean bp, n): " + " ".join(f"{y}:{m*1e4:+.0f}({n})" for y, (m, n) in
                                          J.groupby(J.fd.dt.year).xspy.agg(["mean", "count"]).iterrows()))
    tk5 = J.groupby("ticker").xspy.sum().sort_values().index[-5:]
    P(f"  ex-top-5 issuers mean {J[~J.ticker.isin(tk5)].xspy.mean()*1e4:+.1f}bp")
    D = dsr(J.xspy.values, N_PROGRAM)
    P(f"  DSR (N {N_PROGRAM}): {D:.3f}")
    res = SS.linregress(J.spy.values, (J.ret - 2 * COST_SIDE).values)
    P(f"  vs SPY: beta {res.slope:+.2f} alpha {res.intercept*1e4:+.1f}bp t {res.intercept/res.intercept_stderr:+.2f}")

    PJ = PL[(PL.fd >= JUDGE[0]) & (PL.fd <= JUDGE[1])]
    P("\nPLACEBO 2003-01..2015-09-24: same window at P+3 (should be ~0, t < 1)")
    p_all = summ("placebo P+3, as registered", PJ.xspy, PJ.de)
    p_tr = summ("placebo P+3, entry after filing public", PJ[PJ.tradeable].xspy, PJ[PJ.tradeable].de)
    P(f"  share of placebo entries before the filing was public: {1-PJ.tradeable.mean():.0%}")

    RP = R[R.fd >= REPORT[0]]
    P("\nREPORT 2015-09-25..2026 (Q=3, FINRA 2241; touched by G31's all-events arm)")
    summ("net excess vs SPY, as registered", RP.xspy, RP.de)
    summ("net excess vs SPY, entry after filing public", RP[RP.tradeable].xspy, RP[RP.tradeable].de)
    summ("net raw, entry after filing public", RP[RP.tradeable].net, RP[RP.tradeable].de)
    P(f"  share of Q=3 entries before the filing was public: {1-RP.tradeable.mean():.0%}")
    P("  reported: Q=10 window in the Q=3 era (regime contrast, not judged)")
    R10 = windows(E[E.fd >= REPORT[0]].assign(Q10=10), g, spy, "Q10")
    summ("2015-09..2026 at Q=10", R10.xspy, R10.de)

    P("\nGATES (judge 2003-01..2015-09-24):")
    gates = [("net >= +20bp", s["mean"] >= 0.0020), ("median > 0", s["med"] > 0), ("date-clustered t >= 2.5", s["t"] >= 2.5),
             ("both halves > 0", h1["mean"] > 0 and h2["mean"] > 0), ("ex-top-5 > 0", s["ex5"] > 0),
             ("placebo t < 1 (as registered)", abs(p_all["t"]) < 1), ("DSR >= 0.95", D >= 0.95)]
    for k, v in gates:
        P(f"  {k:34s} {'PASS' if v else 'FAIL'}")
    P(f"  VERDICT: {'PASS' if all(v for _, v in gates) else 'KILL'}")
    yrs = (JUDGE[1] - JUDGE[0]).days / 365.25
    P(f"  ceiling: {len(J)/yrs:.0f}/yr x {s['mean']*1e4:+.1f}bp x 33% x 50% = {len(J)/yrs*s['mean']*0.33*0.5*100:+.1f}pp/yr")

    P("\nAUDITS")
    acc = E.acc.dropna()
    P(f"  acceptance time known {len(acc)}/{len(E)}; after 16:00 ET {(acc.dt.hour >= 16).mean():.0%}; "
      f"before 09:30 {((acc.dt.hour*60+acc.dt.minute) < 570).mean():.0%}")
    lag = []
    for r in E.itertuples():
        _, body = _text(r.path)
        m = re.search(r"(?:prospectus supplement|prospectus) is (?:dated )?([A-Z][a-z]+ \d{1,2}, \d{4})", body)
        if m:
            try:
                lag.append(np.busday_count(pd.Timestamp(m.group(1)).date(), r.fd.date()))
            except Exception:
                pass
    lag = pd.Series(lag)
    P(f"  cover date parsed {len(lag)}/{len(E)}; business days cover-date -> EDGAR filing date: "
      + " ".join(f"{k}:{v:.0%}" for k, v in lag.clip(-1, 4).value_counts(normalize=True).sort_index().items()))
    P(f"  judged windows: entry date - P calendar days median {(J.de - J.fd).dt.days.median():.0f}, min {(J.de - J.fd).dt.days.min()}")
    P(f"  survivorship: tickers delisted by now {J.delisted.mean():.0%} of judged events; "
      f"events whose ticker's last bar is before the planned exit {(J["last"] < J.dx).sum()}")
    mc = pd.read_parquet(S / "daily.parquet", columns=["ticker", "date", "marketcap"],
                         filters=[("ticker", "in", sorted(J.ticker.unique()))])
    mc["date"] = pd.to_datetime(mc.date)
    mm = pd.merge_asof(J.sort_values("fd")[["ticker", "fd"]], mc.sort_values("date"), left_on="fd", right_on="date",
                       by="ticker", direction="backward", tolerance=pd.Timedelta(days=10))
    P(f"  Reg M actively-traded proxy (ADV20 >= $1M by construction, market cap >= $150M): "
      f"{(mm.marketcap >= 150).mean():.0%} of judged events with cap known ({mm.marketcap.notna().sum()}); Sharadar "
      f"marketcap in $M; float < cap, so this is an upper bound on exemption eligibility")
    J.to_parquet(CACHE / "judged.parquet"); RP.to_parquet(CACHE / "report.parquet"); PJ.to_parquet(CACHE / "placebo.parquet")
    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    {"index": stage_index, "cand": stage_cand, "heads": stage_heads, "build": stage_build, "run": stage_run}[sys.argv[1]]()
