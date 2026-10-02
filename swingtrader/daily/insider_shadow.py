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
    return dict(sym=sym, usd=usd, insider=insider)


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


def gate(records: list[dict]) -> dict:
    s = [r for r in records if r.get("status") == "scored"]
    if not s:
        return dict(n=0, verdict="no scored trades yet")
    x = pd.DataFrame(s)
    day = x.groupby("date").ret_net.mean()
    t = float(day.mean() / day.std() * np.sqrt(len(day))) if len(day) > 2 and day.std() > 0 else float("nan")
    mean = float(x.ret_net.mean())
    if len(x) < GATE_N:
        v = f"shadowing ({len(x)}/{GATE_N})"
    elif mean > 0 and t >= 2:
        v = "PASS: may be proposed to the user (needs live MOO/MOC cost check)"
    elif mean <= 0:
        v = "KILL: retire the shadow"
    else:
        v = "keep shadowing (t < 2)"
    return dict(n=len(x), mean_bp=mean * 1e4, t=t, verdict=v)


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


def fetch_buys(day: dt.date) -> list[dict]:
    q = (day.month - 1) // 3 + 1
    idx = _sec_get(f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{q}/form.{day:%Y%m%d}.idx")
    if not idx:
        return []
    out = []
    for p in form4_paths(idx):
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
        buys = [b for d in filing_days(prev, today) for b in fetch_buys(d)]
        syms = sorted({b["sym"] for b in buys if b["insider"]})
        bars = md.sip_daily(syms, pd.Timestamp(today) - pd.Timedelta(days=45)) if syms else {}
        new = plan_rows(buys, bars, str(today))
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
