"""N 1239 EV-TONE (round1_prose.md "## Amendment - EXP round 5"): Loughran-McDonald tone of out-of-session 8-Ks, traded
from the next open cross to the close of day 1 (primary) / day 5 (secondary), vs SPY. Fixed rule, no fit.
Reuses edgar_sess.py's submissions cache (acceptanceDateTime, items), universe/CIK map (Sharadar tickers.secfilings,
includes delisted names) and day-clustered t. Text: EDGAR full-submission .txt, streamed, main 8-K doc + EX-99.1.
usage: PYTHONPATH=. python3 -m research.sim.exp_evtone events | fetch | run
"""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from swingtrader.config import get_env

from . import edgar_sess as es

D = es.ROOT / "data/research/exp_evtone"
EV = D / "events.parquet"
TX = D / "text"                      # one json per accession: word counts (+ text kept only for 2026-07..09)
LM = D / "lm/Loughran-McDonald_MasterDictionary_1993-2025.csv"
OUT = es.ROOT / "research/sim/exp_evtone_out.txt"
START, END, HALF = "2019-01-01", "2026-09-30", "2022-12-31"
ITEMS = {"1.01", "2.01", "2.02", "7.01", "8.01"}
EXCH = ["NASDAQ", "NYSE", "NYSEMKT"]
NCHAR = 20000
SEED = 1239
MAX_EVENTS = 50000                   # pre-declared 2026-11-21 from the count (205,506 events) before any outcome
RPS = 8.0                            # under SEC's 10 req/s
NPLAC = 1000


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with OUT.open("a") as f:
        f.write(s + "\n")


# ----------------------------------------------------------------------------------------------------------- calendar/px
def calendar() -> pd.DatetimeIndex:
    s = pd.read_parquet(es.SH / "funds.parquet", columns=["ticker", "date"], filters=[("ticker", "==", "SPY")])
    return pd.DatetimeIndex(sorted(pd.to_datetime(s.date)))


def entry_date(acc: pd.Series, cal: pd.DatetimeIndex) -> pd.Series:
    """Next official open cross strictly after acceptance: same day if accepted before 09:15 on a session day, else the
    next session (after 16:00, weekends, holidays). Calendar = SPY's Sharadar session dates (the real exchange calendar)."""
    day = acc.dt.tz_localize(None).dt.normalize()
    hm = acc.dt.hour * 60 + acc.dt.minute
    pre = hm < 9 * 60 + 15
    i = cal.searchsorted(day.values, side="left")          # first session >= day
    same = (i < len(cal)) & (cal[np.minimum(i, len(cal) - 1)] == day.values)
    j = np.where(pre & same, i, np.where(same, i + 1, i))
    ok = j < len(cal)
    out = pd.Series(pd.NaT, index=acc.index, dtype="datetime64[ns]")
    out[ok] = cal[j[ok]]
    return out


# ----------------------------------------------------------------------------------------------------------------- events
def events() -> None:
    D.mkdir(parents=True, exist_ok=True)
    t = pd.read_parquet(es.SH / "tickers.parquet")
    t = t[(t.table == "SEP") & t.category.str.startswith("Domestic Common", na=False) & t.exchange.isin(EXCH)]
    t = t[pd.to_datetime(t.lastpricedate) >= START].copy()
    t["cik"] = t.secfilings.str.extract(r"CIK=(\d+)")[0]
    u = t.dropna(subset=["cik"])
    rows = []
    for c in sorted(set(u.cik)):
        f = es.SUB / f"{c}.json"
        if not f.exists():
            continue
        j = json.loads(f.read_text())
        if not j:
            continue
        if not j or "acceptanceDateTime" not in j:
            continue
        x = pd.DataFrame(j)
        x = x[x.form == "8-K"]
        x = x[[bool(ITEMS & set(str(v).split(","))) for v in x["items"]]]
        if x.empty:
            continue
        x["acc"] = pd.to_datetime(x.acceptanceDateTime, utc=True, errors="coerce").dt.tz_convert(es.ET)
        x = x[(x.acc >= pd.Timestamp(START, tz=es.ET)) & (x.acc < pd.Timestamp(END, tz=es.ET) + pd.Timedelta(days=1))]
        hm = x.acc.dt.hour * 60 + x.acc.dt.minute
        x = x[(hm >= 16 * 60) | (hm < 9 * 60 + 15)]
        for r in x.itertuples():
            rows.append((c, r.accessionNumber, r.acc, r.items))
    e = pd.DataFrame(rows, columns=["cik", "acc_no", "acc", "items"]).drop_duplicates(["cik", "acc_no"])
    cal = calendar()
    e["entry"] = entry_date(e.acc, cal)
    e = e.dropna(subset=["entry"])
    tick = u.groupby("cik").ticker.apply(list).to_dict()
    allt = sorted(set(u.ticker))
    sep = pd.read_parquet(es.SH / "stocks.parquet", columns=["ticker", "date", "open", "close", "closeunadj", "volume"],
                          filters=[("ticker", "in", allt), ("date", ">=", pd.Timestamp("2018-11-01").date())])
    sep["date"] = pd.to_datetime(sep.date)
    sep = sep.sort_values(["ticker", "date"])
    g = sep.groupby("ticker")
    sep["dv"] = sep.close * sep.volume                     # split-adjusted px x split-adjusted volume = raw dollar volume
    sep["adv"] = g.dv.transform(lambda s: s.rolling(20, min_periods=20).mean().shift(1))
    sep["pclose_raw"] = g.closeunadj.shift(1)
    key = sep.set_index(["ticker", "date"])[["adv", "pclose_raw", "open"]]
    have = set(key.index)
    out = []
    for r in e.itertuples():
        for tk in tick.get(r.cik, []):
            if (tk, r.entry) in have:
                out.append((r.cik, r.acc_no, r.acc, r.items, r.entry, tk))
                break
    ev = pd.DataFrame(out, columns=["cik", "acc_no", "acc", "items", "entry", "ticker"])
    v = key.loc[list(zip(ev.ticker, ev.entry))].reset_index(drop=True)
    ev = pd.concat([ev.reset_index(drop=True), v], axis=1)
    ev = ev[(ev.pclose_raw >= 1) & (ev.adv >= 1e6) & ev.open.notna() & (ev.open > 0)].drop(columns="open")
    ev["acc"] = ev.acc.astype(str)
    # one trade per (ticker, entry open); all its qualifying filings are pooled for tone
    ev["eid"] = ev.ticker + "_" + ev.entry.dt.strftime("%Y%m%d")
    ev.to_parquet(EV)
    n_e = ev.eid.nunique()
    print(len(ev), "filings,", n_e, "events (ticker x entry)", flush=True)
    print(ev.drop_duplicates("eid").groupby(ev.entry.dt.year).size().to_string(), flush=True)


def sample() -> pd.DataFrame:
    """Fixed-seed random permutation of event ids; the sample is its first MAX_EVENTS (nested if the cap must shrink).
    Returned in permutation order so a partial fetch is itself a random sample."""
    ev = pd.read_parquet(EV)
    ids = np.array(sorted(ev.eid.unique()))
    ids = ids[np.random.default_rng(SEED).permutation(len(ids))][:MAX_EVENTS]
    rank = pd.Series(np.arange(len(ids)), index=ids)
    ev = ev[ev.eid.isin(rank.index)].copy()
    ev["_rk"] = ev.eid.map(rank)
    return ev.sort_values("_rk").drop(columns="_rk")


# ------------------------------------------------------------------------------------------------------------------ fetch
_lock = threading.Lock()
_next = [0.0]


def _throttle():
    with _lock:
        now = time.monotonic()
        w = _next[0] - now
        _next[0] = max(now, _next[0]) + 1.0 / RPS
    if w > 0:
        time.sleep(w)


_DOC = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.S)
_TYPE = re.compile(r"<TYPE>([^\n<]+)")
_TEXT = re.compile(r"<TEXT>(.*)", re.S)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
EX99 = ("EX-99.1", "EX-99.01", "EX-99")


def _clean(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|ix:header)[^>]*>.*?</\1>", " ", raw)   # ix:header = hidden inline-XBRL facts
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", raw))).strip()


def parse_submission(txt: str) -> dict:
    main = ex = None
    for d in _DOC.findall(txt):
        ty = (_TYPE.search(d).group(1).strip().upper() if _TYPE.search(d) else "")
        m = _TEXT.search(d)
        body = m.group(1) if m else ""
        if main is None and ty == "8-K":
            main = _clean(body)[:NCHAR]
        elif ex is None and ty in EX99:
            ex = _clean(body)[:NCHAR]
    return {"main": main or "", "ex": ex or "", "has_ex": ex is not None}


def _fetch_one(r, H):
    f = TX / f"{r.acc_no}.json"
    if f.exists():
        return 0
    url = f"https://www.sec.gov/Archives/edgar/data/{int(r.cik)}/{r.acc_no.replace('-', '')}/{r.acc_no}.txt"
    buf = b""
    for k in range(5):
        _throttle()
        try:
            with requests.get(url, headers=H, timeout=60, stream=True) as resp:
                if resp.status_code == 404:
                    f.write_text(json.dumps({"err": 404}))
                    return 1
                if resp.status_code != 200:
                    time.sleep(5 * (k + 1))
                    continue
                buf = b""
                for ch in resp.iter_content(65536):
                    buf += ch
                    # stop once an EX-99 doc is complete (8-K doc precedes it), after 10 complete docs, or after 6 MB
                    if len(buf) > 6e6:
                        break
                    s = buf.decode("latin-1")
                    nd = s.count("</DOCUMENT>")
                    tys = [t.strip().upper() for t in _TYPE.findall(s)][:nd]
                    if any(t in EX99 for t in tys) or nd >= 10:
                        break
                break
        except requests.RequestException:
            time.sleep(5 * (k + 1))
    else:
        return 0
    p = parse_submission(buf.decode("latin-1"))
    keep = {"has_ex": p["has_ex"], "nmain": len(p["main"]), "nex": len(p["ex"])}
    keep["text"] = p["main"] + " \n " + p["ex"]
    f.write_bytes(gzip.compress(json.dumps(keep).encode()))
    return 1


def fetch() -> None:
    TX.mkdir(parents=True, exist_ok=True)
    ua = (get_env("SEC_USER_AGENT") or "").strip()
    if not ua:
        raise RuntimeError("SEC_USER_AGENT missing from .env")
    H = {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}
    s = sample().drop_duplicates("acc_no")
    todo = [r for r in s.itertuples() if not (TX / f"{r.acc_no}.json").exists()]
    print(len(s), "filings in sample;", len(todo), "to fetch", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(6) as ex:
        for i, _ in enumerate(ex.map(lambda r: _fetch_one(r, H), todo)):
            if i % 1000 == 0:
                el = time.time() - t0
                print(f"  {i}/{len(todo)}  {el/60:.1f} min  {i/max(el,1):.1f}/s", flush=True)


# ------------------------------------------------------------------------------------------------------------------- tone
def lm_words():
    d = pd.read_csv(LM, usecols=["Word", "Negative", "Positive"], keep_default_na=False)
    return set(d.Word[d.Positive != 0].str.upper()), set(d.Word[d.Negative != 0].str.upper())


def _read(f: Path):
    b = f.read_bytes()
    try:
        return json.loads(gzip.decompress(b))
    except OSError:
        return json.loads(b)


def tone_table(acc_nos) -> pd.DataFrame:
    pos, neg = lm_words()
    rows = []
    for a in acc_nos:
        f = TX / f"{a}.json"
        if not f.exists():
            continue
        j = _read(f)
        if "text" not in j:
            continue
        w = re.findall(r"[A-Z]+", j["text"].upper())
        c = Counter(w)
        P = sum(v for k, v in c.items() if k in pos)
        N = sum(v for k, v in c.items() if k in neg)
        rows.append((a, P, N, len(w), j["has_ex"]))
    return pd.DataFrame(rows, columns=["acc_no", "P", "N", "nw", "has_ex"])


# -------------------------------------------------------------------------------------------------------------------- run
def returns(ev: pd.DataFrame) -> pd.DataFrame:
    """Split-adjusted open(entry) -> close(day1) and close(day5, entry = day1); SPY over the same window."""
    tk = sorted(set(ev.ticker))
    sep = pd.read_parquet(es.SH / "stocks.parquet", columns=["ticker", "date", "open", "close"],
                          filters=[("ticker", "in", tk), ("date", ">=", pd.Timestamp("2018-12-01").date())])
    sep["date"] = pd.to_datetime(sep.date)
    sep = sep.sort_values(["ticker", "date"])
    cal = calendar()
    pos = pd.Series(np.arange(len(cal)), index=cal)
    spy = pd.read_parquet(es.SH / "funds.parquet", columns=["ticker", "date", "open", "close"],
                          filters=[("ticker", "==", "SPY")])
    spy["date"] = pd.to_datetime(spy.date)
    spy = spy.set_index("date").reindex(cal)
    out = []
    for t, g in sep.groupby("ticker"):
        e = ev[ev.ticker == t]
        if e.empty:
            continue
        g = g.set_index("date")
        for r in e.itertuples():
            if r.entry not in g.index:
                continue
            o = g.at[r.entry, "open"]
            c1 = g.at[r.entry, "close"]
            i = pos[r.entry]
            if i + 4 < len(cal):
                w = g.loc[r.entry:cal[i + 4], "close"].dropna()
                w = w[w.index.isin(cal)]
                c5 = w.iloc[-1] if len(w) else np.nan     # delisted inside the window -> last available close
                d5x = w.index[-1] if len(w) else pd.NaT
            else:                                          # day 5 beyond the data end
                c5, d5x = np.nan, pd.NaT
            s1 = spy.at[r.entry, "close"] / spy.at[r.entry, "open"] - 1
            s5 = spy.at[d5x, "close"] / spy.at[r.entry, "open"] - 1 if pd.notna(d5x) else np.nan
            out.append((r.eid, (c1 / o - 1 - s1) * 1e4, (c5 / o - 1 - s5) * 1e4, (c1 / o - 1) * 1e4))
    return pd.DataFrame(out, columns=["eid", "x1", "x5", "raw1"])


def tercile_cut(e: pd.DataFrame) -> pd.Series:
    """Tercile from cutoffs of the tone of events with entry strictly earlier (trailing 365 days, >= 300 events):
    no look-ahead in the cutoffs. 2 = top, 0 = bottom."""
    e = e.sort_values("entry")
    days = np.array(sorted(e.entry.unique()))
    lab = pd.Series(np.nan, index=e.index)
    ent, tn = e.entry.values, e.tone.values
    for d in days:
        m = (ent < d) & (ent >= d - np.timedelta64(365, "D"))
        if m.sum() < 300:
            continue
        lo, hi = np.quantile(tn[m], [1 / 3, 2 / 3])
        idx = ent == d
        lab[e.index[idx]] = np.where(tn[idx] >= hi, 2, np.where(tn[idx] <= lo, 0, 1))
    return lab


def stats(x: pd.Series, d: pd.Series) -> str:
    if len(x) < 5:
        return f"n={len(x)}"
    ex5 = x.sort_values().iloc[:-5].mean()
    return (f"n={len(x):6d} mean={x.mean():+7.2f}bp med={x.median():+7.2f} hit={(x > 0).mean():.3f} "
            f"t_day={es.nw_t_day(x.values, d.values):+5.2f} ex-top5={ex5:+7.2f}")


def run(dry: bool = False) -> None:
    """dry=True: code-path test only; returns are replaced by noise and output goes to the scratch path given in argv."""
    global OUT, NPLAC
    if dry:
        OUT, NPLAC = Path(sys.argv[2]), 20
    code = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    OUT.write_text("")
    log("N 1239 EV-TONE  (round1_prose.md 'Amendment - EXP round 5')   code sha256[:16]", code)
    log(f"LM dictionary: {LM.name}  sha256[:16] {hashlib.sha256(LM.read_bytes()).hexdigest()[:16]}")
    ev_all = pd.read_parquet(EV)
    log(f"population: {len(ev_all)} filings, {ev_all.eid.nunique()} events; sample cap {MAX_EVENTS} seed {SEED}")
    ev = sample()
    tt = tone_table(ev.acc_no.unique())
    log(f"sample: {ev.eid.nunique()} events, {ev.acc_no.nunique()} filings; text fetched for {len(tt)} filings; "
        f"with EX-99: {tt.has_ex.mean():.2f}")
    m = ev.merge(tt, on="acc_no")
    m["ex_items"] = m["items"].astype(str)
    g = m.groupby("eid").agg(ticker=("ticker", "first"), entry=("entry", "first"), adv=("adv", "first"),
                             P=("P", "sum"), N=("N", "sum"), nw=("nw", "sum"), items=("ex_items", ",".join),
                             acc=("acc", "min"))
    g = g[(g.P + g.N) > 0].reset_index()
    g["entry"] = pd.to_datetime(g.entry)
    g["tone"] = (g.P - g.N) / (g.P + g.N)
    g["e202"] = g["items"].str.contains("2.02")
    r = returns(g)
    if dry:
        nz = np.random.default_rng(0)
        r["x1"] = nz.normal(0, 300, len(r))
        r["x5"] = np.where(r.x5.notna(), nz.normal(0, 600, len(r)), np.nan)
    g = g.merge(r, on="eid")
    g = g.dropna(subset=["x1"])
    log(f"data check (not a filter): |raw day-1| > 50%: {(g.raw1.abs() > 5000).sum()}; x5 missing: {g.x5.isna().sum()}")
    g["cost"] = np.where(g.adv < 1e7, 10.0, 5.0)
    g["terc"] = tercile_cut(g)
    g = g.dropna(subset=["terc"])
    g["h"] = np.where(g.entry <= HALF, "H1 2019-22", "H2 2023-26")
    log(f"tradable events with tone + cutoff: {len(g)}  ({g.entry.min().date()} .. {g.entry.max().date()}); "
        f"zero-hit events dropped; tone mean {g.tone.mean():+.3f} sd {g.tone.std():.3f}")
    log("")
    res = {}
    for hz in ("x1", "x5"):
        log(f"=== {'PRIMARY day-1 (open -> close of entry day)' if hz == 'x1' else 'SECONDARY day-5 (open -> close of day 5)'}"
            f", excess vs SPY, bp ===")
        z = g.dropna(subset=[hz])
        for mult, lab in ((1, "net"), (2, "net 2x cost")):
            log(f"-- {lab}")
            for part, q in [("ALL", z)] + list(z.groupby("h")):
                top = q[q.terc == 2]
                bot = q[q.terc == 0]
                log(f"  {part:11s} TOP  {stats(top[hz] - mult * top.cost, top.entry)}")
                log(f"  {part:11s} BOT  {stats(bot[hz] - mult * bot.cost, bot.entry)}")
                # T-B: daily (top mean - bottom mean) on dates with both legs; costs on both legs
                a = (top.assign(v=top[hz] - mult * top.cost).groupby("entry").v.mean())
                b = (bot.assign(v=bot[hz] + mult * bot.cost).groupby("entry").v.mean())
                ls = (a - b).dropna()
                tls = ls.mean() / (ls.std() / np.sqrt(len(ls))) if len(ls) > 2 else np.nan
                log(f"  {part:11s} T-B  days={len(ls)} mean={ls.mean():+7.2f}bp/day t={tls:+5.2f}")
                if mult == 1:
                    res[(hz, part)] = (top[hz] - top.cost)
        log(f"-- gross by tercile (ALL):  " + "  ".join(
            f"T{int(k)} {v.mean():+6.2f} (n {len(v)})" for k, v in z.groupby("terc")[hz]))
        log(f"-- unconditional (all terciles) net: {stats(z[hz] - z.cost, z.entry)}")
        log("")
    # placebo: shuffle tone within entry date, recompute tercile membership with the same cutoffs path
    rng = np.random.default_rng(SEED)
    obs = {hz: (g[g.terc == 2][hz] - g[g.terc == 2].cost).mean() for hz in ("x1", "x5")}
    obs_ls = {}
    for hz in ("x1", "x5"):
        obs_ls[hz] = g[g.terc == 2][hz].mean() - g[g.terc == 0][hz].mean()
    pl = {hz: [] for hz in ("x1", "x5")}
    pl_ls = {hz: [] for hz in ("x1", "x5")}
    gi = g.groupby("entry").indices
    terc = g.terc.values
    for _ in range(NPLAC):
        perm = np.empty(len(g), dtype=int)
        for idx in gi.values():
            perm[idx] = rng.permutation(idx)
        t2 = terc[perm]                       # tercile labels follow the shuffled tone within the date
        for hz in ("x1", "x5"):
            v = g[hz].values
            c = g.cost.values
            ok = ~np.isnan(v)
            pl[hz].append(np.mean(v[(t2 == 2) & ok] - c[(t2 == 2) & ok]))
            pl_ls[hz].append(np.mean(v[(t2 == 2) & ok]) - np.mean(v[(t2 == 0) & ok]))
    log(f"=== placebo: tone shuffled within entry date ({NPLAC} draws; dates with one event cannot move) ===")
    for hz in ("x1", "x5"):
        p1 = (np.array(pl[hz]) < obs[hz]).mean()
        p2 = (np.array(pl_ls[hz]) < obs_ls[hz]).mean()
        log(f"  {hz}: TOP net obs {obs[hz]:+.2f}bp, placebo pctile {p1*100:.1f}; T-B gross obs {obs_ls[hz]:+.2f}bp, "
            f"pctile {p2*100:.1f}")
    single = (g.groupby("entry").size() == 1).sum()
    log(f"  single-event dates: {single} of {g.entry.nunique()}")
    log("")
    log("=== diagnostics (not gates) ===")
    for lab, q in (("2.02 earnings", g[g.e202]), ("non-2.02", g[~g.e202])):
        top = q[q.terc == 2]
        log(f"  {lab:14s} TOP x1 net {stats(top.x1 - top.cost, top.entry)}")
    for lab, q in (("ADV<10M", g[g.adv < 1e7]), ("ADV>=10M", g[g.adv >= 1e7])):
        top = q[q.terc == 2]
        log(f"  {lab:14s} TOP x1 net {stats(top.x1 - top.cost, top.entry)}")
    # full-sample tercile (look-ahead cutoffs) sensitivity
    lo, hi = g.tone.quantile([1 / 3, 2 / 3])
    top = g[g.tone >= hi]
    log(f"  full-sample cutoffs TOP x1 net {stats(top.x1 - top.cost, top.entry)}")
    log("")
    a1, h1, h2 = res[("x1", "ALL")], res[("x1", "H1 2019-22")], res[("x1", "H2 2023-26")]
    top = g[g.terc == 2]
    t_day = es.nw_t_day((top.x1 - top.cost).values, top.entry.values)
    ex5 = (top.x1 - top.cost).sort_values().iloc[:-5].mean()
    p1 = (np.array(pl["x1"]) < obs["x1"]).mean()
    gates = {"TOP net > 0 in H1": h1.mean() > 0, "TOP net > 0 in H2": h2.mean() > 0, "day-clustered t >= 2": t_day >= 2,
             "ex-top-5 > 0": ex5 > 0, "placebo >= 95th": p1 >= 0.95}
    log("=== GATES (primary day-1, TOP tercile net excess vs SPY) ===")
    for k, v in gates.items():
        log(f"  {'PASS' if v else 'FAIL'}  {k}")
    log(f"VERDICT: {'PASS' if all(gates.values()) else 'FAIL'}   (mean {a1.mean():+.2f}bp, t {t_day:+.2f})")
    # ceiling at the registered shape: ~events/yr x net/event x 20% deployable, 1-day
    yrs = (g.entry.max() - g.entry.min()).days / 365.25
    frac = g.eid.nunique() / ev_all.eid.nunique()          # tradable-with-tone share of the population
    log(f"top-tercile events/yr in population ~{len(top) / yrs / frac:.0f}; registration ceiling needs >= +40bp "
        f"net/event at 1-day x 20% deployable")


if __name__ == "__main__":
    {"events": events, "fetch": fetch, "run": run, "dry": lambda: run(dry=True)}[sys.argv[1]]()
