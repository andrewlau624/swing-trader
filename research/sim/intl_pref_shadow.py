"""INTL-PREF paper-trading prototype (log-only, never places orders): PREF-EX rule on TSX $25-par preferreds.

Rule (round1_prose.md "Study INTL-PREF", N 1022; verify note research/drafts/intl_pref_verify_2026-10-17.md): buy a TSX preferred's
close on the session before its ex-dividend date E, collect the dividend, sell at E's open (CO, primary) or E's close (CC).
Research (Datastream 2005-25): CO +32bp net of 10bp RT, CC +16bp. Frozen filters: raw price C$10-30, 20d median C$ value traded
>= C$50k, CAD dividend.

Sources (probed 2026-10-18): FORWARD ex-dates = TMX Money GraphQL (https://app-money.tmx.com/graphql, no key, UA header):
getQuoteBySymbol{exDividendDate dividendAmount dividendCurrency} gives the last declared ex-date (future once declared, past
otherwise); getQuoteForSymbols{price volume} is a cheap batch existence check. Yahoo quoteSummary needs a crumb (401), Yahoo
chart events=div only lists past dividends. Yahoo chart (raw open/close/volume/div, '.TO') is used for scoring and filters.
Limitation: TMX shows only the NEXT declared ex-date, so scan sees events typically 2-6 weeks ahead, never a full calendar.

Usage (.venv/bin/python -m research.sim.intl_pref_shadow <cmd>):
  universe            refresh data/research/intl_pref/live_universe.csv (TMX existence scan + Yahoo '.TO' mapping check)
  scan [--asof D]     log declared ex-events within the next 5 TSX sessions (with 10k / 25k paper sizing) to shadow.jsonl
  score               score logged events whose ex-date E has printed (CO / CC net 10bp, 0% and 15% withholding)
  report              stats, $ P&L, forward gate
  backfill --days 60  replay the last N sessions from past Yahoo dividends (BACKFILL rows: pipeline proof, not evidence)

How to validate: run `universe`, then `backfill --days 60` (should print n scored, CO mean positive-ish, no exceptions), then
daily `scan` (before 16:00 ET) and `score` (after the next open); `report` shows the forward gate (60 scored forward events,
CO net mean >= +15bp at 0% withholding, day-clustered t >= 2). Compare scored opens with a broker/TMX screenshot on 2-3 events:
Yahoo opens must equal the TSX opening-auction print. Backfill rows never count toward the gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics as st
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

D = Path("data/research/intl_pref")
UNIV = D / "live_universe.csv"
LOG = D / "shadow.jsonl"
UA = {"User-Agent": "Mozilla/5.0 (research; andrewlau2007@gmail.com)"}
TMX = "https://app-money.tmx.com/graphql"
YCH = "https://query1.finance.yahoo.com/v8/finance/chart/{}?period1={}&period2={}&interval=1d&events=div"

COST = 0.0010                     # round trip
WH = 0.15                         # alternative withholding on the dividend
MIN_PX, MAX_PX, MIN_VAL = 10.0, 30.0, 50_000.0
PART, AUCTION_SHARE = 0.05, 0.25  # <= 5% of the auction, auction ~ 25% of day volume (override with --auction-share)
SIZES = (10_000.0, 25_000.0)      # USD Roth sizes
FX = 1.37                         # CAD per USD (approx., paper only)
NEED, GATE_MEAN = 60, 15.0
FORWARD_FROM = "2026-10-19"       # rows with E before this are labelled backfill
HOLIDAYS = {dt.date(2026, 10, 12), dt.date(2026, 12, 25), dt.date(2026, 12, 28), dt.date(2027, 1, 1), dt.date(2027, 2, 15),
            dt.date(2027, 3, 26), dt.date(2027, 5, 24), dt.date(2027, 7, 1), dt.date(2027, 8, 2), dt.date(2027, 9, 6)}
# Issuer roots of TSX preferred shares (curated; Datastream active names in info.parquet contributed BCE, POW, PWF, ELF, SLF,
# GWO, BAM, BPO, ENB, TRP, TRI, FFH, CU, EMA, etc.). Brute-forced as ROOT.PR.<A-Z> / ROOT.PF.<A-Z> against TMX.
ROOTS = ("AC AD AFN AIF ALA AQN ATA ATH ATD BAM BCE BEK BEP BIP BIR BN BMO BNS BPO BPY BRF BR BSC CCS CF CGI CHE CIU CJR CM CPX CU CVE "
         "CWB DFN DGS ECN EFN EIF ELF EMA ENB EP FFH FTS FTT GWO H HCA HSE IAG IFC IGM IPL KEY LB LBS MFC MIC MRU NA NPI OBS PBH POW PPL "
         "PWF RY SBN SLF SU T TA TCA TD TECK TIH TRI TRP VB W WCP WFS WN X YPG POW GMP AX BBD BYD CAS CRT DC EQB FCR GEI HR IIP JFS KMP "
         "LNF MKP NVU PEY PIF PRM PSI RBA SRV SOT TCL TF TRZ VNR XTC").split()


def tmx(q: str) -> dict:
    req = urllib.request.Request(TMX, json.dumps({"query": q}).encode(), {**UA, "Content-Type": "application/json"})
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=30))
        except Exception:
            time.sleep(1 + i)
    return {}


def yget(sym: str, d0: dt.date, d1: dt.date):
    """Yahoo daily chart -> (DataFrame date/open/close/volume, {ex_date: div}); raw (unadjusted) prices."""
    p1, p2 = int(dt.datetime.combine(d0, dt.time()).timestamp()), int(dt.datetime.combine(d1 + dt.timedelta(days=2), dt.time()).timestamp())
    for i in range(3):
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(YCH.format(sym, p1, p2), headers=UA), timeout=30))
            r = j["chart"]["result"][0]
            break
        except Exception:
            r = None
            time.sleep(1 + i)
    if not r or "timestamp" not in r:
        return None, {}, None
    off = r["meta"].get("gmtoffset", -14400)
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"date": [(dt.datetime.fromtimestamp(t + off, dt.UTC)).date() for t in r["timestamp"]],
                       "open": q["open"], "close": q["close"], "volume": q["volume"]}).dropna(subset=["close"])
    divs = {(dt.datetime.fromtimestamp(v["date"] + off, dt.UTC)).date(): float(v["amount"]) for v in (r.get("events", {}).get("dividends", {}) or {}).values()}
    return df.drop_duplicates("date").reset_index(drop=True), divs, r["meta"].get("currency")


def tmx_hist(tsym: str, d0: dt.date, d1: dt.date):
    """TMX getCompanyPriceHistory (raw, unadjusted) + getDividendsForSymbol (CAD) -> same (DataFrame, {ex: div}, 'CAD') shape as yget.
    Fallback price source for TSX prefs Yahoo lacks or covers only sparsely (e.g. BN.PF.B: Yahoo 1 bar/3mo, TMX 25)."""
    q = ('query { getCompanyPriceHistory(symbol:%s, start:"%s", end:"%s", adjusted:false, unadjusted:true) '
         '{ datetime openPrice closePrice volume } }' % (json.dumps(tsym), d0, d1))
    rows = (tmx(q).get("data") or {}).get("getCompanyPriceHistory") or []
    if not rows:
        return None, {}, None
    df = pd.DataFrame({"date": [dt.date.fromisoformat(r["datetime"][:10]) for r in rows], "open": [r["openPrice"] for r in rows],
                       "close": [r["closePrice"] for r in rows], "volume": [r["volume"] for r in rows]}).dropna(subset=["close"])
    dq = 'query { getDividendsForSymbol(symbol:%s) { dividends { exDate amount currency } } }' % json.dumps(tsym)
    dv = ((tmx(dq).get("data") or {}).get("getDividendsForSymbol") or {}).get("dividends") or []
    divs = {dt.date.fromisoformat(x["exDate"][:10]): float(x["amount"]) for x in dv if x.get("currency") == "CAD" and x.get("amount")}
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True), divs, "CAD"


def pget(sym: str, d0: dt.date, d1: dt.date):
    """Price history by symbol style: Yahoo '.TO' symbols via yget, TMX-style ('BN.PF.B') via tmx_hist."""
    return yget(sym, d0, d1) if sym.endswith(".TO") else tmx_hist(sym, d0, d1)


def ymap(tsym: str) -> str:
    """TMX 'BMO.PR.E' -> Yahoo 'BMO-PE.TO'; 'ENB.PF.V' -> 'ENB-PFV.TO'."""
    root, kind, ser = tsym.split(".")
    return f"{root}-{'P' if kind == 'PR' else 'PF'}{ser}.TO"


def sessions(a: dt.date, n: int):
    out, d = [], a
    while len(out) < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5 and d not in HOLIDAYS:
            out.append(d)
    return out


def prev_session(d: dt.date) -> dt.date:
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5 or d in HOLIDAYS:
        d -= dt.timedelta(days=1)
    return d


# ---------------------------------------------------------------- universe
def cmd_universe(_a):
    cands = [f"{r}.{k}.{s}" for r in dict.fromkeys(ROOTS) for k in ("PR", "PF") for s in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
    chunks = [cands[i:i + 50] for i in range(0, len(cands), 50)]

    def one(ch):
        q = "query { getQuoteForSymbols(symbols:[%s]) { symbol longname price volume currency exchange } }" % ",".join(json.dumps(s) for s in ch)
        return (tmx(q).get("data") or {}).get("getQuoteForSymbols") or []

    with ThreadPoolExecutor(6) as ex:
        rows = [r for part in ex.map(one, chunks) for r in part if r.get("price")]
    print(f"TMX existence scan: {len(cands)} candidates -> {len(rows)} live")

    def det(r):
        d = (tmx('query { getQuoteBySymbol(symbol:%s,locale:"en") { exDividendDate dividendAmount dividendCurrency } }' % json.dumps(r["symbol"])).get("data") or {}).get("getQuoteBySymbol") or {}
        return {**r, "ex_date": (d.get("exDividendDate") or "")[:10], "div_amt": d.get("dividendAmount"), "div_ccy": d.get("dividendCurrency")}

    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(det, rows))
    today = dt.date.today()

    def chk(r):
        y = ymap(r["symbol"])
        df, _, ccy = yget(y, today - dt.timedelta(days=45), today)
        ok = df is not None and len(df) >= 5 and abs(df.close.iloc[-1] / r["price"] - 1) < 0.05
        usd = r["currency"] == "USD" or r["div_ccy"] == "USD" or r["symbol"].endswith(".U")
        src, sym, tn = ("yahoo", y, 0) if ok else ("", y, 0)
        if not ok:   # fallback: TMX daily history (no history = stale/redeemed placeholder with a par price and no volume)
            th, _, _ = tmx_hist(r["symbol"], today - dt.timedelta(days=45), today)
            tn = 0 if th is None else len(th)
            if tn >= 5 and abs(th.close.iloc[-1] / r["price"] - 1) < 0.05:
                src, sym = "tmx", r["symbol"]
            else:
                src = "stale" if tn == 0 else "sparse"
        return {"tmx_symbol": r["symbol"], "yahoo": sym, "name": r["longname"], "price": r["price"], "ccy": r["currency"],
                "div_ccy": r["div_ccy"], "ex_date": r["ex_date"], "div_amt": r["div_amt"], "yahoo_ok": bool(ok),
                "yahoo_n": 0 if df is None else len(df), "src": src, "tmx_n": tn, "usd": bool(usd)}

    with ThreadPoolExecutor(4) as ex:
        out = pd.DataFrame(list(ex.map(chk, rows))).sort_values("tmx_symbol")
    out.to_csv(UNIV, index=False)
    bad = out[~out.src.isin(["yahoo", "tmx"])]
    print(f"saved {UNIV}: {len(out)} TMX-listed prefs; priced via Yahoo {int((out.src == 'yahoo').sum())}, via TMX fallback "
          f"{int((out.src == 'tmx').sum())}; unpriced {len(bad)} (stale/no-volume placeholders {int((bad.src == 'stale').sum())}, sparse {int((bad.src == 'sparse').sum())})")
    print(f"USD series (excluded from the CAD rule): {', '.join(out[out.usd].tmx_symbol)}")
    print(f"declared ex-date >= today: {(out.ex_date >= str(today)).sum()}; CAD-dividend: {(out.div_ccy == 'CAD').sum()}")


def load_univ():
    if not UNIV.exists():
        raise SystemExit("run `universe` first")
    u = pd.read_csv(UNIV, dtype={"ex_date": str})
    return u[u.src.isin(["yahoo", "tmx"]) & ~u.usd]   # USD series are listed in `universe`, never traded by the CAD rule


# ---------------------------------------------------------------- log
def load_log() -> dict:
    return {json.loads(l)["key"]: json.loads(l) for l in LOG.read_text().splitlines() if l.strip()} if LOG.exists() else {}


def save_log(d: dict):
    LOG.write_text("\n".join(json.dumps(v, sort_keys=True) for v in sorted(d.values(), key=lambda v: (v["ex"], v["symbol"]))) + "\n")


def eligible(hist: pd.DataFrame, E: dt.date, ccy):
    """Frozen filters at the E-1 close. Returns (close_prev, med20 C$ value) or None."""
    h = hist[hist.date < E].tail(20)
    if len(h) < 10 or ccy != "CAD":
        return None
    c = float(h.close.iloc[-1])
    med = float((h.close * h.volume.fillna(0)).median())
    return (c, med) if MIN_PX <= c <= MAX_PX and med >= MIN_VAL else None


def size_night(events: list, share: float):
    """Equal split of capital over the night's events, each capped at PART x share x 20d median C$ volume, whole shares."""
    for e in events:
        for cap in SIZES:
            per = min(cap * FX / len(events), PART * share * e["med20"])
            e[f"sh_{int(cap/1000)}k"] = int(per // e["px_ref"])
    return events


def put_events(log: dict, evs: list, kind: str, share: float):
    by = {}
    for e in evs:
        by.setdefault(e["ex"], []).append(e)
    for ex_, es in by.items():
        for e in size_night(es, share):
            k = f"{e['symbol']}|{ex_}"
            if k in log and log[k].get("scored"):
                continue
            log[k] = {**log.get(k, {}), **e, "key": k, "kind": kind, "logged_at": log.get(k, {}).get("logged_at") or dt.datetime.now().isoformat(timespec="seconds"), "scored": False}


# ---------------------------------------------------------------- scan
def cmd_scan(a):
    asof = dt.date.fromisoformat(a.asof) if a.asof else dt.date.today()
    win = set(sessions(asof - dt.timedelta(days=1), 5))   # ex-dates E over the next 5 sessions (asof session included)
    u = load_univ()
    u = u[u.ex_date.isin({str(d) for d in win}) & (u.div_ccy == "CAD")]
    evs = []
    for _, r in u.iterrows():
        E = dt.date.fromisoformat(r.ex_date)
        hist, _, ccy = pget(r.yahoo, E - dt.timedelta(days=60), asof)
        if hist is None:
            continue
        el = eligible(hist, E, ccy)
        if el:
            evs.append({"symbol": r.yahoo, "tmx": r.tmx_symbol, "ex": r.ex_date, "px_ref": el[0], "med20": el[1], "div": float(r.div_amt), "div_src": "tmx"})
    log = load_log()
    put_events(log, evs, "forward", a.auction_share)
    save_log(log)
    print(f"scan {asof}: window {min(win)}..{max(win)}; universe rows with CAD ex-date in window {len(u)}; eligible {len(evs)}")
    for e in sorted(evs, key=lambda e: e["ex"]):
        k = log[f"{e['symbol']}|{e['ex']}"]
        print(f"  E {e['ex']} {e['symbol']:12s} px {e['px_ref']:.2f} div {e['div']:.4f} ({e['div']/e['px_ref']*100:.2f}%) med20 C${e['med20']:,.0f} sh10k {k['sh_10k']} sh25k {k['sh_25k']}")
    # one-line preview of what is declared beyond the window
    fut = load_univ(); fut = fut[(fut.ex_date > str(max(win))) & (fut.div_ccy == "CAD")]
    print(f"declared beyond window: {len(fut)} (next {fut.ex_date.min() if len(fut) else 'n/a'})")


# ---------------------------------------------------------------- score
def score_one(v: dict, hist: pd.DataFrame, divs: dict):
    E = dt.date.fromisoformat(v["ex"])
    pr, bar = hist[hist.date < E], hist[hist.date == E]
    if bar.empty or pr.empty:
        return None
    c0, o, c1 = float(pr.close.iloc[-1]), bar.open.iloc[0], float(bar.close.iloc[0])
    if pd.isna(o):
        return None
    div = divs.get(E, v["div"])
    # TSX: no opening trade => the reported open is the prior (cum-div) close, not a fill;
    # score CO as unfilled at the open and sold at the ex-date close (3.4% of 2005-25 ex events)
    stale = float(o) == c0
    out = {"px_buy": c0, "px_open": float(o), "px_close": c1, "div_scored": div, "div_yahoo": divs.get(E),
           "open_stale": stale}
    for nm, p in (("co", c1 if stale else o), ("cc", c1)):
        g0, g15 = (p - c0 + div) / c0, (p - c0 + div * (1 - WH)) / c0
        out[f"{nm}_net"], out[f"{nm}_net_wh"] = g0 - COST, g15 - COST
        out[f"{nm}_pl_per_share"] = p - c0 + div - COST * c0
    return out


def cmd_score(_a=None, quiet=False):
    log = load_log()
    today = dt.date.today()
    todo = [v for v in log.values() if not v["scored"] and dt.date.fromisoformat(v["ex"]) <= today]
    n = 0
    for sym in sorted({v["symbol"] for v in todo}):
        vs = [v for v in todo if v["symbol"] == sym]
        hist, divs, _ = pget(sym, min(dt.date.fromisoformat(v["ex"]) for v in vs) - dt.timedelta(days=10), today)
        if hist is None:
            continue
        for v in vs:
            r = score_one(v, hist, divs)
            if r:
                v.update(r, scored=True, scored_at=dt.datetime.now().isoformat(timespec="seconds"))
                n += 1
    save_log(log)
    if not quiet:
        print(f"scored {n} of {len(todo)} due events")
    return n


# ---------------------------------------------------------------- backfill
def cmd_backfill(a):
    today = dt.date.today()
    first = prev_session(today)
    for _ in range(a.days - 1):
        first = prev_session(first)
    u = load_univ()
    evs = []
    for _, r in u.iterrows():
        hist, divs, ccy = pget(r.yahoo, first - dt.timedelta(days=60), today)
        if hist is None:
            continue
        for E, amt in divs.items():
            if first <= E < today:
                el = eligible(hist, E, ccy)
                if el:
                    evs.append({"symbol": r.yahoo, "tmx": r.tmx_symbol, "ex": str(E), "px_ref": el[0], "med20": el[1], "div": amt, "div_src": "yahoo" if r.yahoo.endswith(".TO") else "tmx"})
    log = load_log()
    put_events(log, evs, "backfill", a.auction_share)
    save_log(log)
    print(f"backfill {first}..{today}: {len(evs)} eligible past ex-events logged (BACKFILL, not evidence)")
    cmd_score()
    cmd_report(a, kinds=("backfill",))


# ---------------------------------------------------------------- report
def _tstat(df: pd.DataFrame, col: str) -> float:
    day = df.groupby("ex")[col].mean()
    return float(day.mean() / day.std() * math.sqrt(len(day))) if len(day) > 2 and day.std() > 0 else float("nan")


def cmd_report(_a=None, kinds=("forward", "backfill")):
    log = load_log()
    for kind in kinds:
        rows = [v for v in log.values() if v["scored"] and v["kind"] == kind]
        pend = [v for v in log.values() if not v["scored"] and v["kind"] == kind]
        tag = "FORWARD" if kind == "forward" else "BACKFILL (pipeline proof, not evidence)"
        print(f"\n== {tag}: scored {len(rows)}, pending {len(pend)}")
        if not rows:
            continue
        df = pd.DataFrame(rows)
        for nm in ("co", "cc"):
            for suf, lab in (("_net", "0% wh"), ("_net_wh", "15% wh")):
                c = nm + suf
                print(f"  {nm.upper()} net {lab:6s}: mean {df[c].mean()*1e4:+7.1f}bp median {df[c].median()*1e4:+7.1f} hit {(df[c]>0).mean():.2f} day-t {_tstat(df, c):+.2f}")
        for k in ("10k", "25k"):
            sh = df[f"sh_{k}"]
            for nm in ("co", "cc"):
                pl = (sh * df[f"{nm}_pl_per_share"]).sum() / FX
                wh = (sh * (df[f"{nm}_pl_per_share"] - df.div_scored * WH)).sum() / FX
                print(f"  ${k} Roth {nm.upper()} P&L over {df.ex.nunique()} nights: US${pl:+,.0f} (15% wh US${wh:+,.0f}); deployed-shares in {int((sh>0).sum())}/{len(df)} events")
        print(f"  drop/div (CO): {((df.px_buy - df.px_open) / df.div_scored).median():.2f} median")
        if kind == "forward":
            m, t = df.co_net.mean() * 1e4, _tstat(df, "co_net")
            ok = len(df) >= NEED and m >= GATE_MEAN and t >= 2
            print(f"  GATE (>= {NEED} scored, CO net mean >= +{GATE_MEAN:.0f}bp at 0% wh, day-t >= 2): "
                  f"{'PASS' if ok else 'not met'} [n {len(df)}/{NEED}, mean {m:+.1f}, t {t:+.2f}]; 15% wh view mean {df.co_net_wh.mean()*1e4:+.1f}bp")
    if "forward" in kinds and not any(v["kind"] == "forward" and v["scored"] for v in log.values()):
        print("\nGATE: 0/%d forward events scored yet" % NEED)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["universe", "scan", "score", "report", "backfill"])
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--asof")
    ap.add_argument("--auction-share", type=float, default=AUCTION_SHARE)
    a = ap.parse_args()
    D.mkdir(parents=True, exist_ok=True)
    {"universe": cmd_universe, "scan": cmd_scan, "score": cmd_score, "report": cmd_report, "backfill": cmd_backfill}[a.cmd](a)


if __name__ == "__main__":
    main()
