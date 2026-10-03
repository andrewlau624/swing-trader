"""Closed-end fund activist watch (Goal hunt G45-F, research/drafts/study_goal_g45.md) — LOG ONLY, never trades or emails.

Study G45: the first SC 13D by a known CEF activist (Saba, Karpus, Bulldog, City of London, 1607, Almitas) on a listed
closed-end fund was followed by +2.0..+3.6% per 60-session trade vs PCEF in all three periods (2016-20 / 2021-23 / 2024-26),
but the sleeve missed the Goal add-on bar. G45-F, the forward test: log every new first 13D and score it at 60 sessions
(dividend-adjusted, vs PCEF). Gate at 30 scored events: mean >= +1.5% vs PCEF and the hedged sleeve >= +5pp/yr after tax,
else DEAD (round1_prose.md, G45-F).

Run once a weekday (`make cef-activist-watch`): EDGAR full-text search for the last 10 days' SC 13D / SCHEDULE 13D filings
by the six activists; new (fund, activist) pairs go to state/cef-activist-watch.jsonl; rows 60+ sessions old get scored.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .insider_shadow import _read, _sec_get, _write

LOG_NAME = "cef-activist-watch.jsonl"
ACTIVISTS = ("Saba Capital", "Karpus", "Bulldog Investors", "City of London Investment", "1607 Capital", "Almitas")
ACT_RE = re.compile(r"saba|karpus|bulldog|city of london|1607|almitas", re.I)
FUND_RE = re.compile(r"fund|trust|income|municipal|opportunit|strategic|dividend|global|capital", re.I)
HOLD, GATE_N = 60, 30


def ticker_of(name: str) -> str | None:
    m = re.search(r"\(([A-Z][A-Z0-9.\-, ]{0,30})\)\s+\(CIK", name)
    return m.group(1).split(",")[0].strip().replace("-", ".") if m else None


def events_from_hits(hits: list[dict]) -> list[dict]:
    """(fund ticker, activist, filing date) for original 13Ds whose subject looks like a listed fund."""
    out = []
    for x in hits:
        s = x.get("_source", {})
        if s.get("form") not in ("SC 13D", "SCHEDULE 13D"):
            continue
        names = s.get("display_names", [])
        act = next((m.group(0).lower() for n in names for m in [ACT_RE.search(n)] if m), None)
        subj = [n for n in names if not ACT_RE.search(n) and ticker_of(n) and FUND_RE.search(n)]
        if act and subj:
            out.append(dict(sym=ticker_of(subj[0]), name=subj[0][:60], act=act, date=s.get("file_date"),
                            adsh=s.get("adsh")))
    return out


def fetch(start: dt.date, end: dt.date) -> list[dict]:
    rows = []
    for a in ACTIVISTS:
        u = (f"https://efts.sec.gov/LATEST/search-index?q=%22{a.replace(' ', '%20')}%22&forms=SC%2013D,SCHEDULE%2013D"
             f"&dateRange=custom&startdt={start}&enddt={end}")
        t = _sec_get(u)
        if t:
            rows += events_from_hits(json.loads(t).get("hits", {}).get("hits", []))
    return rows


def score(r: dict) -> dict | None:
    """60-session dividend-adjusted return minus PCEF from the first session after the filing date (None if not due)."""
    import pandas as pd
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from .marketdata import _clients, trade_date
    data, _ = _clients()
    start = pd.Timestamp(r["date"], tz="UTC") + pd.Timedelta(days=1)
    df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=[r["sym"], "PCEF"], timeframe=TimeFrame.Day, start=start,
                                              end=start + pd.Timedelta(days=120), feed="sip", adjustment="all")).df
    if df is None or not len(df):
        return None
    df = df.reset_index()
    df["d"] = trade_date(df["timestamp"])
    out = {}
    for s, g in df.groupby("symbol"):
        g = g.sort_values("d")
        if len(g) < HOLD:
            return None
        out[s] = (g.close.iloc[HOLD - 1] / g.open.iloc[0] - 1, str(g.d.iloc[0]), str(g.d.iloc[HOLD - 1]))
    if r["sym"] not in out or "PCEF" not in out:
        return None
    return dict(ret=out[r["sym"]][0], bench=out["PCEF"][0], excess=out[r["sym"]][0] - out["PCEF"][0],
                entry=out[r["sym"]][1], exit=out[r["sym"]][2])


def gate(rows: list[dict]) -> dict:
    sc = [r for r in rows if r.get("status") == "scored"]
    n = len(sc)
    if not n:
        return dict(n=0, verdict=f"shadowing (0/{GATE_N})")
    m = sum(r["excess"] for r in sc) / n
    v = f"shadowing ({n}/{GATE_N})" if n < GATE_N else ("PASS bar 1 (check the hedged sleeve)" if m >= 0.015 else "DEAD")
    return dict(n=n, mean_excess=m, verdict=v)


def run(state_dir: Path, today: dt.date | None = None, log=print) -> dict:
    today = today or dt.date.today()
    path = state_dir / LOG_NAME
    rows = _read(path)
    seen = {(r["sym"], r["act"]) for r in rows}
    new = []
    for e in fetch(today - dt.timedelta(days=10), today):
        if (e["sym"], e["act"]) in seen:                            # one row per (fund, activist), even across queries
            continue
        e.update(status="open", seen=str(today), alert=True)
        seen.add((e["sym"], e["act"]))
        new.append(e)
    rows += new
    for r in rows:
        if r.get("status") == "open" and (today - dt.date.fromisoformat(r["date"])).days >= 95:
            try:
                s = score(r)
            except Exception as exc:                                  # data hiccup: try again tomorrow
                log(f"[cef-activist] score {r['sym']} failed: {str(exc)[:80]}")
                s = None
            if s:
                r.update(status="scored", **s)
    _write(path, rows)
    g = gate(rows)
    log(f"[cef-activist] {len(new)} new 13D(s) on CEFs: " + ", ".join(f"{e['sym']} ({e['act']})" for e in new)
        + f" | gate: {g}")
    return g


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[2] / "state")
