"""Insider-purchase session (Round 31 Study ID3, study_id_insider_day.md) — SHADOW ONLY.

Research: an officer's or director's open-market purchase (Form 4, code P, >= $10k) is public by the next session;
buying that session's opening cross and selling its closing cross earned +16.6bp/trade net of 2.5bp/side in names
with 20-day ADV$ >= $20M (registered pass, judge-half t 2.31, DSR 0.105, cost break-even ~10.8bp/side).

This module never places an order. Run once a weekday before the open (`make insider-shadow`):
  1. score: every planned entry whose session has a completed daily bar gets its open -> close return;
  2. fetch: the previous business day's Form 4 filings from EDGAR's daily form index, parsed for code-P buys;
  3. plan: today's would-be trades (ADV$ >= $20M, prior close >= $5) are appended to state/insider-day.jsonl.
`gate()` reads the log: the switch may only be proposed to the user after 300 scored trades with mean net > 0
and NW t >= 2; mean net <= 0 at 300 retires the shadow (kill rule).

EV2 (Round 33, study_ev2_first_insider_buy.md; registered PASS at N 760): each planned trade also logs
`silence_days`, the days since the issuer's previous Form 4 open-market purchase by ANY owner (None = none within
1,095 days), and the $ bought. Two forward-only weights are scored inside the same log (no orders, no sizing):
EV2 = silence >= 730 days, and EV2 x big = EV2 with >= $500k bought (found post-judge, so forward data only).
Each gets its own gate at 60 scored trades: mean <= 0 -> drop the weight; mean > 0 and t >= 2 -> may propose a 2x
weight inside ID3.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .news_judge import sec_headers

LOG_NAME = "insider-day.jsonl"
MIN_USD, MIN_ADV, MIN_PRICE = 1e4, 2e7, 5.0
COST_BPS = 2.5                     # per side, as judged in research; live MOO/MOC cost is the open question
GATE_N = 300
SILENCE_DAYS, BIG_USD, SILENCE_CAP, SUB_GATE_N = 730, 5e5, 1095, 60


# ---------------------------------------------------------------- parsing (pure)
def _tag(block: str, name: str) -> str | None:
    m = re.search(rf"<{name}>\s*(?:<value>)?\s*([^<]*?)\s*(?:</value>)?\s*</{name}>", block, re.S)
    return m.group(1).strip() if m else None


def parse_form4(text: str) -> dict | None:
    """Return {sym, usd, insider} for a Form 4 with >= 1 non-derivative code-P acquisition, else None."""
    m = re.search(r"<ownershipDocument>.*?</ownershipDocument>", text, re.S)
    if not m:
        return None
    doc = m.group(0)
    if (_tag(doc, "documentType") or "") not in ("4", "4/A"):
        return None
    sym = (_tag(doc, "issuerTradingSymbol") or "").upper().replace("-", ".").strip()
    cik = _tag(doc, "issuerCik") or ""
    rel = " ".join(re.findall(r"<reportingOwnerRelationship>.*?</reportingOwnerRelationship>", doc, re.S))
    insider = bool(re.search(r"<(isDirector|isOfficer)>\s*(1|true)\s*</", rel, re.I))
    usd = 0.0
    for t in re.findall(r"<nonDerivativeTransaction>.*?</nonDerivativeTransaction>", doc, re.S):
        if _tag(t, "transactionCode") != "P" or _tag(t, "transactionAcquiredDisposedCode") != "A":
            continue
        try:
            usd += float(_tag(t, "transactionShares") or 0) * float(_tag(t, "transactionPricePerShare") or 0)
        except ValueError:
            continue
    if usd <= 0 or not sym:
        return None
    return dict(sym=sym, usd=usd, insider=insider, issuer_cik=int(cik) if cik.strip().isdigit() else None)


def form4_paths(idx_text: str) -> list[str]:
    """Unique Form 4 / 4/A submission paths from an EDGAR daily form.idx."""
    out = []
    for line in idx_text.splitlines():
        if re.match(r"^4(/A)?\s", line):
            m = re.search(r"(edgar/data/\S+\.txt)", line)
            if m:
                out.append(m.group(1))
    return sorted(set(out))


def plan_rows(buys: list[dict], bars: dict[str, pd.DataFrame], session: str) -> list[dict]:
    """Today's shadow trades from yesterday's buys: officer/director, >= $10k per symbol, ADV$ and price filters
    on bars that end before `session`."""
    agg: dict[str, float] = {}
    for b in buys:
        if b["insider"]:
            agg[b["sym"]] = agg.get(b["sym"], 0.0) + b["usd"]
    rows = []
    for sym, usd in sorted(agg.items()):
        if usd < MIN_USD or sym not in bars:
            continue
        g = bars[sym]
        g = g[g.index < pd.Timestamp(session)]
        if len(g) < 15:
            continue
        adv = float((g.close * g.volume).tail(20).mean())
        pc = float(g.close.iloc[-1])
        if adv >= MIN_ADV and pc >= MIN_PRICE:
            rows.append(dict(date=session, sym=sym, usd=round(usd), adv=round(adv), prev_close=pc, status="planned"))
    return rows


def silence_days(filings: list[tuple[dt.date, str]], fd: dt.date, has_purchase, cap: int = SILENCE_CAP) -> int | None:
    """Days from `fd` back to the issuer's latest Form 4 filed BEFORE `fd` that has an open-market purchase by any
    owner (Study EV2's definition). `filings` = [(filing date, url)]; `has_purchase(url)` reads one. Newest first,
    stops at the first purchase; None when there is none within `cap` days."""
    lo = fd - dt.timedelta(days=cap)
    for d, url in sorted(filings, reverse=True):
        if d >= fd:
            continue
        if d < lo:
            break
        if has_purchase(url):
            return (fd - d).days
    return None


def ev2_flags(r: dict) -> tuple[bool, bool]:
    """(EV2, EV2 x big) for a logged row; rows from before the EV2 fields existed are neither."""
    if "silence_days" not in r:
        return False, False
    ev2 = r["silence_days"] is None or r["silence_days"] >= SILENCE_DAYS
    return ev2, ev2 and float(r.get("usd", 0)) >= BIG_USD


def _stats(x: pd.DataFrame) -> tuple[float, float]:
    day = x.groupby("date").ret_net.mean()
    t = float(day.mean() / day.std() * np.sqrt(len(day))) if len(day) > 2 and day.std() > 0 else float("nan")
    return float(x.ret_net.mean()), t


def _sub_gate(x: pd.DataFrame, rest: pd.DataFrame) -> dict:
    if not len(x):
        return dict(n=0, verdict=f"shadowing (0/{SUB_GATE_N})")
    mean, t = _stats(x)
    if len(x) < SUB_GATE_N:
        v = f"shadowing ({len(x)}/{SUB_GATE_N})"
    elif mean <= 0:
        v = "KILL: drop the weight"
    elif t >= 2:
        v = "PASS: may propose a 2x weight inside ID3"
    else:
        v = "keep shadowing (t < 2)"
    vs = float(rest.ret_net.mean()) * 1e4 if len(rest) else float("nan")
    return dict(n=len(x), mean_bp=mean * 1e4, t=t, rest_bp=vs, verdict=v)


def gate(records: list[dict]) -> dict:
    s = [r for r in records if r.get("status") == "scored"]
    if not s:
        return dict(n=0, verdict="no scored trades yet")
    x = pd.DataFrame(s)
    mean, t = _stats(x)
    if len(x) < GATE_N:
        v = f"shadowing ({len(x)}/{GATE_N})"
    elif mean > 0 and t >= 2:
        v = "PASS: may be proposed to the user (needs live MOO/MOC cost check)"
    elif mean <= 0:
        v = "KILL: retire the shadow"
    else:
        v = "keep shadowing (t < 2)"
    f = [ev2_flags(r) for r in s]
    tagged = np.array(["silence_days" in r for r in s])
    e2, big = np.array([a for a, _ in f]), np.array([b for _, b in f])
    return dict(n=len(x), mean_bp=mean * 1e4, t=t, verdict=v,
                ev2=_sub_gate(x[e2], x[tagged & ~e2]), ev2_big=_sub_gate(x[big], x[tagged & ~big]))


# ---------------------------------------------------------------- I/O
def _read(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _sec_get(url: str) -> str | None:
    for k in range(5):
        try:
            r = requests.get(url, headers=sec_headers(), timeout=30)
            if r.status_code == 404:
                return None
            if r.status_code in (429, 503):
                time.sleep(2 * (k + 1)); continue
            r.raise_for_status()
            time.sleep(0.12)
            return r.text
        except requests.RequestException:
            time.sleep(2 * (k + 1))
    return None


def issuer_form4s(cik: int, since: dt.date) -> list[tuple[dt.date, str]]:
    """(filing date, .txt url) of every Form 4 / 4/A in the issuer's EDGAR submissions filed on or after `since`."""
    base = "https://data.sec.gov/submissions/"
    t = _sec_get(f"{base}CIK{cik:010d}.json")
    if not t:
        return []
    j = json.loads(t)
    pages = [j.get("filings", {}).get("recent", {})]
    for f in j.get("filings", {}).get("files", []):
        if f.get("filingTo", "9999") >= str(since):
            more = _sec_get(base + f["name"])
            if more:
                pages.append(json.loads(more))
    out = []
    for p in pages:
        for form, d, acc in zip(p.get("form", []), p.get("filingDate", []), p.get("accessionNumber", [])):
            if form in ("4", "4/A") and d >= str(since):
                out.append((dt.date.fromisoformat(d),
                            f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{acc}.txt"))
    return out


def tag_silence(rows: list[dict], fd: dt.date, cik_of, log=print) -> None:
    """Add silence_days to today's planned rows (EV2). Network: the issuer's Form 4 list, then filings newest first
    until a purchase (~0.2 s each). Failures leave silence_days out (the row is then neither EV2 nor rest)."""
    for r in rows:
        try:
            cik = cik_of(r["sym"])
            if cik is None:
                log(f"[insider] {r['sym']}: no CIK, EV2 silence not logged"); continue
            fl = issuer_form4s(cik, fd - dt.timedelta(days=SILENCE_CAP))

            def has_purchase(url, cik=cik):
                t = _sec_get(url)
                p = parse_form4(t) if t else None
                return bool(p) and p.get("issuer_cik") in (None, cik)    # not a purchase the issuer made elsewhere
            r["silence_days"] = silence_days(fl, fd, has_purchase)
            r["ev2"], r["ev2_big"] = ev2_flags(r)
        except Exception as exc:                                         # shadow only: never break the run
            log(f"[insider] {r['sym']}: EV2 silence failed ({type(exc).__name__}: {str(exc)[:80]})")


def fetch_buys(day: dt.date, log=print) -> list[dict]:
    q = (day.month - 1) // 3 + 1
    idx = _sec_get(f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{q}/form.{day:%Y%m%d}.idx")
    if not idx:
        log(f"[insider] {day}: no EDGAR daily index (weekend/holiday, or not posted yet)")
        return []
    paths = form4_paths(idx)
    print(f"[insider] {day}: reading {len(paths)} Form 4 filings from EDGAR "
          f"(~{len(paths) * 0.18 / 60:.0f} min at SEC's rate limit)", flush=True)
    out = []
    for i, p in enumerate(paths):
        if i and i % 250 == 0:
            print(f"[insider]   {i}/{len(paths)} read, {len(out)} purchases so far", flush=True)
        t = _sec_get(f"https://www.sec.gov/Archives/{p}")
        r = parse_form4(t) if t else None
        if r:
            out.append(r)
    return out


def filing_days(prev_session: dt.date, session: dt.date) -> list[dt.date]:
    """EDGAR filing dates whose trade session is `session`: every calendar day from the previous session up to the
    day before (a filing dated on a market holiday, e.g. Good Friday, trades at the next session)."""
    n = (session - prev_session).days
    return [prev_session + dt.timedelta(days=k) for k in range(n) if (prev_session + dt.timedelta(days=k)).weekday() < 5]


def run(state_dir: Path, today: dt.date | None = None, log=print) -> dict:
    """Bars: `sip_daily` session bars (labelled by trade date); their open/close are the regular-session official
    crosses (checked against Alpaca auction prints on 500 events: median difference 0.0bp)."""
    from . import marketdata as md
    from ..data import trading_days
    path = Path(state_dir) / LOG_NAME
    rows = _read(path)
    today = today or dt.date.today()
    sess = [d.date() for d in trading_days(today - dt.timedelta(days=10), today)]
    # 1. score planned entries whose session is complete (official open / close = the crosses)
    pend = [r for r in rows if r["status"] == "planned" and r["date"] < str(today)]
    if pend:
        syms = sorted({r["sym"] for r in pend})
        bars = md.sip_daily(syms, min(r["date"] for r in pend))
        for r in pend:
            g = bars.get(r["sym"])
            d = pd.Timestamp(r["date"])
            if g is not None and d in g.index:
                o, c = float(g.at[d, "open"]), float(g.at[d, "close"])
                r.update(status="scored", open=o, close=c, ret_net=c / o - 1 - 2 * COST_BPS / 1e4)
            elif (pd.Timestamp(today) - d).days > 5:
                r.update(status="no_bar")
    # 2-3. filings since the previous session -> today's plan (only on a session; once a day)
    if today in sess and len(sess) >= 2 and not any(r["date"] == str(today) for r in rows):
        prev = sess[-2]
        buys = [b for d in filing_days(prev, today) for b in fetch_buys(d, log)]
        syms = sorted({b["sym"] for b in buys if b["insider"]})
        bars = md.sip_daily(syms, pd.Timestamp(today) - pd.Timedelta(days=45)) if syms else {}
        new = plan_rows(buys, bars, str(today))
        if new:
            from .news_judge import _cik_map
            cmap = _cik_map(Path(state_dir))
            tag_silence(new, min(filing_days(prev, today)), lambda s: cmap.get(s.upper().replace(".", "-")), log)
            log(f"[insider] EV2: " + ", ".join(f"{r['sym']} {r.get('silence_days', '?')}d ${r['usd']:,}" for r in new))
        rows += new
        log(f"[insider] {prev}: {len(buys)} code-P Form 4s, {len(syms)} officer/director symbols -> {len(new)} shadow trades for {today}")
    _write(path, rows)
    g = gate(rows)
    log(f"[insider] gate: {g}")
    return g


if __name__ == "__main__":
    import sys
    from ..config import Config
    cfg = Config.load()
    if getattr(cfg.daily, "insider_day", "shadow") == "off":
        print("[insider] daily.insider_day is off"); sys.exit(0)
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    run(Path(__file__).resolve().parents[2] / "state", day)
