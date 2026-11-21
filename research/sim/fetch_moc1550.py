"""MOC-1550 cache: 15:50 ET snapshot prices for the liquid universe, 2016-01 .. 2026-11-20. Infrastructure only (no returns).
  PYTHONPATH=. python3 research/sim/fetch_moc1550.py            # fetch (resumable; finished months are skipped)
  PYTHONPATH=. python3 research/sim/fetch_moc1550.py --check    # coverage per year + spot checks vs daily bars
Universe: each session, the 1,000 highest-ADV20 Sharadar SEP common names (nx.is_common) at $5+, both measured on the PREVIOUS
session (known at 15:50, no same-day lookahead); through 2026-10-05 from ~/data/sharadar/stocks.parquet, after that from the
scratchpad recent_bars.parquet (Alpaca SIP daily, adjustment=all; common names only, ETFs dropped). Requests use the union of
each month's daily top-1000; `member` marks the sym-dates that are in that day's top-1000.
Clock: regular sessions only. Session dates = SPY's daily-bar dates; open/close times from Alpaca's exchange calendar
(/v2/calendar, the source of swingtrader.daily.brokers.regular_sessions), checked against signals.REGULAR_OPENS/CLOSES.
Window = [close-30m, close-10m) ET: 15:30-15:50 on a 16:00 session; 12:30-12:50 on a 13:00 half day (15:50 is after the close).
Minute bars: GET data.alpaca.markets/v2/stocks/bars, 1Min, feed=sip, adjustment=raw, 200 symbols per request; bar t=15:49 is
15:49:00-15:50:00, so its close is the 15:50 price. Stored per sym-date: px (close of the last bar at or before the snap minute),
last_hm (that bar's ET HHMM), vol (sum of bar volume in the window), nbars; plus sh_close (the day's Sharadar/Alpaca daily close,
unadjusted) for data QC only. Alpaca uses current symbols: old Sharadar tickers that changed or were reused can be missing or wrong;
see --check (sh_close ratio flags reused tickers)."""
from __future__ import annotations
import argparse
import os
import pathlib
import re
import sys
import time

import numpy as np
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.nx import is_common  # noqa: E402
from swingtrader.config import get_env  # noqa: E402
from swingtrader.daily.marketdata import ET  # noqa: E402
from swingtrader.daily.signals import REGULAR_OPENS, REGULAR_CLOSES  # noqa: E402

SH = pathlib.Path.home() / "data/sharadar"
SP = pathlib.Path("/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/"
                  "f8b1efd9-fa49-4233-8b45-d15823460ce9/scratchpad")
RECENT = SP / "recent_bars.parquet"
LOG = SP / "moc1550_fetch.log"
OUT = ROOT / "data/research/moc1550"
START, END, SH_END = "2016-01-01", "2026-11-20", pd.Timestamp("2026-10-05")
TOPN, PX_MIN, BATCH = 1000, 5.0, 200
URL = "https://data.alpaca.markets/v2/stocks/bars"
CAL = "https://paper-api.alpaca.markets/v2/calendar"
ETFS = {'SPY', 'QQQ', 'IWM', 'DIA', 'XLK', 'XLF', 'XLE', 'XLV', 'XLP', 'XLU', 'XLI', 'XLB', 'XLY', 'XLC', 'XLRE', 'SMH', 'GLD',
        'TLT', 'KRE', 'XBI', 'ITB', 'IGV'}


def log(s):
    line = f"{pd.Timestamp.now():%H:%M:%S} {s}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def headers():
    return {"APCA-API-KEY-ID": get_env("ALPACA_API_KEY"), "APCA-API-SECRET-KEY": get_env("ALPACA_SECRET_KEY")}


NREQ = [0]
INVALID: set[str] = set()   # symbols Alpaca rejects (HTTP 400 "invalid symbol"); skipped for the rest of the run


def get(url, params, H, tries=8):
    back = 2.0
    for a in range(tries):
        NREQ[0] += 1
        try:
            r = requests.get(url, headers=H, params=params, timeout=60)
        except requests.RequestException as e:
            log(f"net err {type(e).__name__}; retry in {back:.0f}s"); time.sleep(back); back = min(back * 2, 120); continue
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("Retry-After", back))
            log(f"HTTP {r.status_code}; backoff {wait:.0f}s"); time.sleep(wait); back = min(back * 2, 120); continue
        if r.status_code == 400:
            return {"_err": r.text}
        r.raise_for_status()
        rem = r.headers.get("X-RateLimit-Remaining"); rst = r.headers.get("X-RateLimit-Reset")
        if rem is not None and int(rem) < 3 and rst:
            time.sleep(max(0.0, float(rst) - time.time()) + 0.5)
        return r.json()
    raise RuntimeError(f"gave up after {tries} tries: {url}")


# ---------------------------------------------------------------- calendar
def sessions(H):
    f = OUT / "_sessions.parquet"
    if f.exists():
        return pd.read_parquet(f)
    spy = pd.read_parquet(SH / "funds.parquet", columns=["ticker", "date"], filters=[("ticker", "==", "SPY")])
    d1 = pd.to_datetime(spy.date); d1 = d1[(d1 >= START) & (d1 <= SH_END)]
    rb = pd.read_parquet(RECENT, columns=["sym", "date"]); d2 = rb.date[(rb.sym == "SPY") & (rb.date > SH_END) & (rb.date <= END)]
    days = pd.DatetimeIndex(sorted(set(d1) | set(d2)))
    cal0 = pd.DataFrame(get(CAL, {"start": START, "end": END}, H))
    cal0["date"] = pd.to_datetime(cal0["date"])
    extra = set(cal0.date) - set(days)
    cal = cal0.set_index("date").reindex(days)
    bad = cal.open.isna().sum()
    if bad:
        raise ValueError(f"{bad} SPY session dates missing from the exchange calendar")
    for o, c in zip(cal.open, cal.close):
        oh, ch = tuple(int(x) for x in o.split(":")), tuple(int(x) for x in c.split(":"))
        if oh not in REGULAR_OPENS or ch not in REGULAR_CLOSES:
            raise ValueError(f"calendar session {o}-{c} is not regular hours")
    s = pd.DataFrame({"date": days, "close_hm": [int(c.replace(":", "")) for c in cal.close]})
    OUT.mkdir(parents=True, exist_ok=True); s.to_parquet(f)
    log(f"sessions {len(s)} ({s.date.min().date()}..{s.date.max().date()}); half days {(s.close_hm == 1300).sum()}; "
        f"calendar sessions not in SPY dates: {sorted(x.date() for x in extra)[:10]}")
    return s


# ---------------------------------------------------------------- universe
def universe(sess):
    f = OUT / "_universe_v2.parquet"   # v1 (_universe.parquet) used closeunadj x volume: kept for the diff, not used
    if f.exists():
        return pd.read_parquet(f)
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"]); tk = tk[tk.table == "SEP"]
    common = sorted(set(tk.ticker[is_common(tk.category.fillna("").astype(str))]))
    s = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "close", "closeunadj", "volume"],
                        filters=[("date", ">=", pd.Timestamp("2015-10-01")), ("ticker", "in", common)])
    s["date"] = pd.to_datetime(s.date)
    rb = pd.read_parquet(RECENT, columns=["sym", "date", "c", "v"])
    rb = rb[~rb.sym.isin(ETFS) & rb.sym.isin(set(common)) & (rb.date > SH_END - pd.Timedelta(days=60))]
    rb = rb.rename(columns={"sym": "ticker", "v": "volume"}); rb["close"] = rb.c; rb["closeunadj"] = rb.c; rb = rb.drop(columns="c")
    # recent bars (Alpaca daily) replace Sharadar only after SH_END; the 60-day overlap is only ADV warm-up for the switch
    s = pd.concat([s, rb[rb.date > SH_END]], ignore_index=True)
    s = s.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    # SEP volume is split-adjusted, so dollar volume = split-adjusted close x volume (as NX); closeunadj x volume overstates
    # the pre-split ADV of every name that later split. Alpaca daily bars (adjustment=all) are adjusted on both sides too.
    s["dv"] = (s.close * s.volume).astype("float64")
    g = s.groupby("ticker", sort=False)
    s["adv20"] = g["dv"].rolling(20, min_periods=20).mean().reset_index(level=0, drop=True)
    # known at 15:50 of the NEXT session in this ticker's own row sequence
    s["adv_prev"] = g["adv20"].shift(1); s["px_prev"] = g["closeunadj"].shift(1)
    s = s[s.date.isin(set(sess.date)) & (s.px_prev >= PX_MIN) & s.adv_prev.notna()]
    s["rk"] = s.groupby("date")["adv_prev"].rank(ascending=False, method="first")
    u = s[s.rk <= TOPN][["date", "ticker", "rk", "closeunadj"]].rename(columns={"closeunadj": "sh_close"})
    u["src"] = np.where(u.date > SH_END, "alpaca_daily", "sharadar")
    u.to_parquet(f)
    n = u.groupby("date").size()
    log(f"universe: {len(u):,} member sym-dates, per day min {n.min()} median {n.median():.0f}; months {u.date.dt.to_period('M').nunique()}")
    return u


# ---------------------------------------------------------------- fetch
def snap_hm(close_hm):
    """ET HHMM of the snapshot = session close - 10 minutes (1550 on a 16:00 session, 1250 on a 13:00 half day)."""
    ch, cm = divmod(int(close_hm), 100); tot = ch * 60 + cm - 10
    return (tot // 60) * 100 + tot % 60


def fetch_day(day, close_hm, syms, H, asof=None):
    """Window aggregates per QUERY symbol. asof None = Alpaca's default (current-symbol mapping, so META returns FB's
    history); asof '-' = no mapping (the raw symbol as it traded that day). Invalid symbols (HTTP 400) are dropped."""
    ch, cm = divmod(close_hm, 100)
    c = pd.Timestamp(day).tz_localize(ET) + pd.Timedelta(hours=ch, minutes=cm)
    st, en = c - pd.Timedelta(minutes=30), c - pd.Timedelta(minutes=11)   # keep bars stamped close-30 .. close-11 (inclusive)
    rows = []; syms = [s for s in dict.fromkeys(syms) if s not in INVALID]; dropped = []
    for i in range(0, len(syms), BATCH):
        chunk = syms[i:i + BATCH]
        while chunk:
            p = {"symbols": ",".join(chunk), "timeframe": "1Min", "start": st.tz_convert("UTC").isoformat(),
                 "end": (en + pd.Timedelta(minutes=1)).tz_convert("UTC").isoformat(), "feed": "sip", "adjustment": "raw",
                 "limit": 10000}
            if asof is not None:
                p["asof"] = asof
            buf = []; bad = None
            while True:
                j = get(URL, p, H)
                if "_err" in j:
                    msg = j["_err"]; bad = msg.split("invalid symbol:")[-1].strip().strip('"}').strip() if "invalid symbol" in msg else None
                    break
                for sym, bs in (j.get("bars") or {}).items():
                    for x in bs:
                        buf.append((sym, x["t"], x["c"], x["v"]))
                if not j.get("next_page_token"):
                    break
                p["page_token"] = j["next_page_token"]
            if bad is None and buf is not None and not ("_err" in j):
                rows += buf; break
            if bad and bad in chunk:
                chunk = [s for s in chunk if s != bad]; dropped.append(bad); INVALID.add(bad); continue
            raise RuntimeError(f"HTTP 400 not an invalid-symbol error: {j.get('_err', '')[:200]}")
    if not rows:
        return pd.DataFrame(columns=["q", "px", "last_hm", "vol", "nbars"]), dropped
    b = pd.DataFrame(rows, columns=["q", "t", "c", "v"])
    b["t"] = pd.to_datetime(b.t, utc=True).dt.tz_convert(ET)
    b = b[(b.t >= st) & (b.t <= en)].sort_values(["q", "t"])
    out = b.groupby("q").agg(px=("c", "last"), t=("t", "last"), vol=("v", "sum"), nbars=("c", "size")).reset_index()
    out["last_hm"] = out.t.dt.hour * 100 + out.t.dt.minute
    return out.drop(columns="t"), dropped


def query_symbol(tk):
    """Sharadar marks a reused ticker's earlier holder with a digit suffix (ADT1 = the old ADT); Alpaca knows the bare symbol."""
    m = re.match(r"^([A-Z][A-Z.]*?)\d+$", tk)
    return m.group(1) if m else tk


def alternates(tk, related):
    alts = []
    if len(tk) >= 4 and tk.endswith("Q"):
        alts.append(tk[:-1])                       # bankruptcy Q suffix: traded without it before
    alts += [x for x in str(related or "").split() if x and x not in (tk, query_symbol(tk))]
    return list(dict.fromkeys(query_symbol(a) for a in alts))


BAND = (0.8, 1.25)   # identity check: a ticker-month whose median px / daily close is outside this band is the wrong entity


def _fetch_modes(day, chm, pairs, H):
    """pairs: [(query symbol, mode)] with mode 'map' (Alpaca default asof) or 'raw' (asof '-'). Returns q, mode, aggregates."""
    out = []
    for mode, asof in (("map", None), ("raw", "-")):
        qs = sorted({q for q, md in pairs if md == mode})
        if qs:
            r, _ = fetch_day(day, chm, qs, H, asof=asof); r["mode"] = mode; out.append(r)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["q", "mode", "px", "last_hm", "vol", "nbars"])


def _med_ratio(g, um):
    x = g.merge(um[["date", "ticker", "sh_close"]], on=["date", "ticker"])
    return (x.px / x.sh_close).groupby(x.ticker).median()


def fetch_month(um, sess, rel, H):
    """Pass 1: bare symbol, Alpaca's current-symbol mapping ('map'); digit-suffixed old holders (ADT1, DD1) as raw symbols
    on the day ('raw', asof '-'), because the mapping would return the current holder's predecessor (DD -> Dow).
    Pass 2: members still missing on a day -> alternates (bankruptcy Q stripped, Sharadar relatedtickers), raw.
    Pass 3 (identity repair): a ticker whose month-median px / daily close is outside BAND, or that has no bar all month, is
    refetched with every candidate (other mode, alternates) and the candidate with the in-band median closest to 1 is kept;
    if none is in band the pass-1/2 rows stay, flagged qc_ok False."""
    syms = sorted(um.ticker.unique()); days = sorted(um.date.unique())
    chm_of = dict(zip(sess.date, sess.close_hm))
    q1 = {s: query_symbol(s) for s in syms}; mode1 = {s: ("raw" if q1[s] != s else "map") for s in syms}
    parts = []
    for day in days:
        chm = int(chm_of[day]); mem_day = set(um.ticker[um.date == day])
        r = _fetch_modes(day, chm, [(q1[s], mode1[s]) for s in syms], H)
        a = pd.DataFrame({"ticker": syms}); a["q"] = a.ticker.map(q1); a["mode"] = a.ticker.map(mode1)
        a["member"] = a.ticker.isin(mem_day)
        a = a.sort_values("member", ascending=False).drop_duplicates(["q", "mode"])   # shared symbol: the day's member keeps it
        g1 = a.drop(columns="member").merge(r, on=["q", "mode"]); g1["how"] = g1["mode"]
        miss = [s for s in mem_day if s not in set(g1.ticker)]
        alt = {s: v for s in miss if (v := alternates(s, rel.get(s)))}
        g2 = pd.DataFrame()
        if alt:
            r2 = _fetch_modes(day, chm, [(x, "raw") for v in alt.values() for x in v], H); have = set(r2.q)
            pick = pd.DataFrame([(s, next(x for x in v if x in have)) for s, v in alt.items() if any(x in have for x in v)],
                                columns=["ticker", "q"])
            if len(pick):
                g2 = pick.merge(r2, on="q"); g2["how"] = "alt"
        g = pd.concat([g1, g2], ignore_index=True); g["date"] = pd.Timestamp(day); parts.append(g)
    got = pd.concat(parts, ignore_index=True)
    # pass 3
    memrows = got.merge(um[["date", "ticker"]], on=["date", "ticker"])
    med = _med_ratio(memrows, um)
    bad = sorted(set(s for s in syms if s in set(um.ticker)) - set(med.index[(med >= BAND[0]) & (med <= BAND[1])]))
    fixed = 0
    if bad:
        cands = {s: list(dict.fromkeys([(q1[s], "raw" if mode1[s] == "map" else "map")]
                                       + [(x, "raw") for x in alternates(s, rel.get(s))] + [(q1[s], "map"), (s, "raw")]))
                 for s in bad}
        pairs = sorted({c for v in cands.values() for c in v}); rp = []
        for day in days:
            r = _fetch_modes(day, int(chm_of[day]), pairs, H); r["date"] = pd.Timestamp(day); rp.append(r)
        rp = pd.concat(rp, ignore_index=True)
        for s in bad:
            best, bd = None, None
            for q, md in cands[s]:
                x = rp[(rp.q == q) & (rp["mode"] == md)].assign(ticker=s)
                x = x.merge(um[(um.ticker == s)][["date", "ticker", "sh_close"]], on=["date", "ticker"])
                if len(x) == 0:
                    continue
                mr = float((x.px / x.sh_close).median())
                if BAND[0] <= mr <= BAND[1] and (bd is None or abs(np.log(mr)) < bd):
                    best, bd = (q, md), abs(np.log(mr))
            if best:
                q, md = best
                new = rp[(rp.q == q) & (rp["mode"] == md)].assign(ticker=s, how=f"fix_{md}")
                got = pd.concat([got[got.ticker != s], new], ignore_index=True); fixed += 1
    med = _med_ratio(got.merge(um[["date", "ticker"]], on=["date", "ticker"]), um)
    got["qc_ok"] = got.ticker.map((med >= BAND[0]) & (med <= BAND[1])).fillna(False).astype(bool)
    return got, len(bad), fixed


def run():
    H = headers()
    if not H["APCA-API-KEY-ID"]:
        raise SystemExit("ALPACA_API_KEY not set")
    OUT.mkdir(parents=True, exist_ok=True)
    sess = sessions(H); u = universe(sess)
    rel = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "relatedtickers"])
    rel = rel[rel.table == "SEP"].set_index("ticker").relatedtickers.to_dict()
    u["month"] = u.date.dt.to_period("M")
    t0 = time.time(); months = sorted(u.month.unique())
    order = list(enumerate(months))[::-1] if os.environ.get("MOC_REVERSE") else list(enumerate(months))
    for k, m in order:                     # MOC_REVERSE=1: a second worker from the newest month down (shares the 200/min cap)
        f = OUT / f"{m}.parquet"
        um = u[u.month == m]; tm = time.time(); nreq0 = NREQ[0]; syms = sorted(um.ticker.unique()); topup = ""
        if f.exists():
            old = pd.read_parquet(f)
            if "univ" in old.columns:
                continue
            # file built on universe v1: keep its rows, fetch the names v2 adds and re-repair v2 members that fail the identity band
            cols = ["date", "ticker", "q", "px", "last_hm", "vol", "nbars", "how"]
            og = old[old.px.notna()][cols].copy(); og["last_hm"] = og.last_hm.astype("float64")
            med = _med_ratio(og.merge(um[["date", "ticker"]], on=["date", "ticker"]), um)
            okt = set(med.index[(med >= BAND[0]) & (med <= BAND[1])])
            need = sorted(set(syms) - okt)
            nadd = len(set(syms) - set(old.ticker))
            if need:
                gn, nbad, nfix = fetch_month(um[um.ticker.isin(need)], sess, rel, H)
                got = pd.concat([og[~og.ticker.isin(need)], gn], ignore_index=True)
            else:
                got, nbad, nfix = og, 0, 0
            topup = f" [top-up of v1 file: {nadd} names new in v2, refetched {len(need)}]"
        else:
            got, nbad, nfix = fetch_month(um, sess, rel, H)
        med = _med_ratio(got.merge(um[["date", "ticker"]], on=["date", "ticker"]), um)
        got["qc_ok"] = got.ticker.map((med >= BAND[0]) & (med <= BAND[1])).astype("boolean").fillna(False).astype(bool)
        if "mode" not in got.columns:
            got["mode"] = None
        grid = pd.MultiIndex.from_product([sorted(um.date.unique()), syms], names=["date", "ticker"]).to_frame(index=False)
        d = grid.merge(got.drop(columns="mode"), on=["date", "ticker"], how="left").merge(
            um[["date", "ticker", "rk", "sh_close", "src"]], on=["date", "ticker"], how="left")
        d["member"] = d.rk.notna(); d["nbars"] = d.nbars.fillna(0).astype("int16")
        d["qc_ok"] = d.qc_ok.astype("boolean").fillna(False).astype(bool)
        d["last_hm"] = d.last_hm.astype("Int16")
        d["snap_hm"] = d.date.map(dict(zip(sess.date, sess.close_hm.map(snap_hm)))).astype("int16")
        d = d[d.member | d.px.notna()].reset_index(drop=True)
        for c in ("px", "vol", "sh_close", "rk"):
            d[c] = d[c].astype("float32")
        d["univ"] = "v2"
        tmp = f.with_suffix(f".tmp{os.getpid()}"); d.to_parquet(tmp, index=False); os.replace(tmp, f)
        mem = d[d.member]
        log(f"{m}: {len(syms)} syms x {um.date.nunique()} sessions, member coverage {mem.px.notna().mean()*100:.1f}%, "
            f"qc_ok {(mem.px.notna() & mem.qc_ok).mean()*100:.1f}%, alt {(mem.how == 'alt').mean()*100:.1f}%, "
            f"identity repair {nfix}/{nbad}, invalid {len(INVALID)}, {time.time()-tm:.0f}s, requests {NREQ[0]-nreq0} "
            f"(month {k+1}/{len(months)}, elapsed {(time.time()-t0)/60:.1f} min){topup}")
    log("DONE")


# ---------------------------------------------------------------- checks
def check():
    fs = sorted(p for p in OUT.glob("20*.parquet"))
    d = pd.concat([pd.read_parquet(p) for p in fs], ignore_index=True)
    m = d[d.member].copy()
    m["ratio"] = m.px / m.sh_close
    m["yr"] = m.date.dt.year
    print(f"{len(fs)} month files, {len(d):,} rows, {len(m):,} member sym-dates, {m.date.nunique()} sessions")
    g = m.groupby("yr")
    tab = pd.DataFrame({"sessions": g.date.nunique(), "member_symdates": g.size(), "coverage_%": g.px.apply(lambda x: x.notna().mean() * 100),
                        "full20bars_%": g.nbars.apply(lambda x: (x >= 20).mean() * 100),
                        "ratio_off_%": g.ratio.apply(lambda x: ((x < 0.8) | (x > 1.25)).sum() / max(1, x.notna().sum()) * 100),
                        "med_abs_log_ratio_bp": g.ratio.apply(lambda x: np.nanmedian(np.abs(np.log(x))) * 1e4)})
    print(tab.round(2).to_string())
    print("half-day snaps:", sorted(m[m.snap_hm == 1250].date.dt.date.unique().tolist())[:20])
    # daily-bar consistency (Sharadar SEP through 2026-10-05; split-adjusted high/low/volume rescaled to unadjusted)
    s = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "high", "low", "close", "closeunadj", "volume"],
                        filters=[("date", ">=", pd.Timestamp(START))])
    s["date"] = pd.to_datetime(s.date); k = s.closeunadj / s.close
    s["hi_u"] = s.high * k; s["lo_u"] = s.low * k; s["vol_u"] = s.volume / k
    x = m[m.px.notna()].merge(s[["ticker", "date", "hi_u", "lo_u", "vol_u"]], on=["ticker", "date"])
    x["inrange"] = (x.px >= x.lo_u * 0.999) & (x.px <= x.hi_u * 1.001)
    x["volshare"] = x.vol / x.vol_u
    print(f"vs Sharadar daily bars ({len(x):,} sym-dates): px inside [low, high] {x.inrange.mean()*100:.2f}% "
          f"(qc_ok rows {x[x.qc_ok].inrange.mean()*100:.2f}%); 15:30-15:50 volume share of day median {x.volshare.median()*100:.1f}%, "
          f"> 100% {(x.volshare > 1).mean()*100:.2f}%")
    print(x.groupby(x.date.dt.year).inrange.mean().mul(100).round(2).to_dict())
    picks = [("AAPL", "2016-03-15"), ("JPM", "2020-03-16"), ("NVDA", "2024-11-26"),
             ("AAPL", "2026-11-27" if False else "2026-11-20"), ("XOM", "2018-12-24"), ("DD1", "2016-06-01")]
    rb = pd.read_parquet(RECENT)
    for tk, dte in picks:
        r = m[(m.ticker == tk) & (m.date == dte)]
        dd = s[(s.ticker == tk) & (s.date == dte)]
        ref = (f"Sharadar low {dd.lo_u.iloc[0]:.2f} high {dd.hi_u.iloc[0]:.2f} close {dd.closeunadj.iloc[0]:.2f} vol {dd.vol_u.iloc[0]:,.0f}"
               if len(dd) else "")
        if not len(dd):
            q = rb[(rb.sym == tk) & (rb.date == dte)]
            ref = f"Alpaca daily (adj=all) low {q.l.iloc[0]:.2f} high {q.h.iloc[0]:.2f} close {q.c.iloc[0]:.2f} vol {q.v.iloc[0]:,.0f}" if len(q) else "no daily bar"
        if len(r):
            r = r.iloc[0]
            print(f"  {tk} {dte}: px@{r.snap_hm} {r.px:.2f} (last bar {r.last_hm}, {r.nbars} bars, vol {r.vol:,.0f}, via {r.how}) | {ref}")
        else:
            print(f"  {tk} {dte}: not in cache | {ref}")
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    check() if a.check else run()
