"""Odd-lot tender watch (Round 31, research/drafts/study_oddlot_tenders.md) — ALERT ONLY, never trades.

An oversubscribed issuer tender prorates every holder of >= 100 shares, but when the offer grants odd-lot
priority a holder of <= 99 shares who tenders all of them is bought in full. 2016-26: cash offers with odd-lot
priority whose guaranteed price (fixed, or the low end of a Dutch range) was >= 1% above the market made money
every time (14-15 deals, median +5.5-6.3%, ~$90-150 per deal on <= 99 shares).

Run once a weekday (`make tender-watch`): reads the previous session-days' new SC TO-I filings from EDGAR's daily
index, extracts the price terms and the odd-lot clause, compares the floor with the last close, and logs every
candidate to state/tender-watch.jsonl; candidates with floor >= +1% and explicit priority are emailed (Notifier).
Tendering is a manual Schwab election; the 99-share limit counts ALL of the owner's accounts together.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path

import numpy as np

from .insider_shadow import _read, _sec_get, filing_days

LOG_NAME = "tender-watch.jsonl"
MONEY = r"\$\s?(\d[\d,]*\.\d{2,4})"
MIN_FLOOR = 0.01
BAD = ("par value", "dividend", "exercise price", "conversion price", "warrant", "liquidation preference")
YES = re.compile(r"odd[ -]lots?\W{0,3} first\b|odd[ -]lot[^.]{0,300}?(priority|first (?:purchase|accept)|not be subject to (?:the )?pro ?ration|"
                 r"without pro ?ration|accepted in full|before (?:pro ?ration|purchasing))|"
                 r"(priority|first purchase|accept all)[^.]{0,200}?odd[ -]lot", re.I)
NO = re.compile(r"odd[ -]lot[^.]{0,200}?(still|also|will be|are) subject to pro ?ration|"
                r"no (?:priority|preference) (?:for|to) odd", re.I)


def _num(x: str) -> float:
    return float(x.replace(",", ""))


def clean(text: str) -> str:
    t = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(t))


def terms(text: str) -> dict:
    """Price terms and odd-lot clause of an offer to purchase (plain text)."""
    t = clean(text)
    rng = re.search(r"not (?:greater|more) than " + MONEY + r"[^$]{0,40}(?:nor|and not|or|and) (?:less|lower) than "
                    + MONEY, t, re.I)
    lo = hi = fixed = np.nan
    if rng:
        a, b = _num(rng.group(1)), _num(rng.group(2)); lo, hi = min(a, b), max(a, b)
    else:
        for m in re.finditer(r"(?:at|for) a (?:purchase |cash )?price of " + MONEY + r",? (?:per|a) [Ss]hare", t):
            if not any(w in t[max(0, m.start() - 25):m.end()].lower() for w in BAD):
                fixed = _num(m.group(1)); break
    nav = bool(re.search(r"(?:\d{2}(?:\.\d+)?%|percent) of (?:the )?(?:\w+ )?(?:net asset value|NAV)", t, re.I))
    odd = "N" if NO.search(t) else "Y" if YES.search(t) else "none"
    floor = fixed if np.isfinite(fixed) else lo
    return dict(lo=lo, hi=hi, fixed=fixed, nav=nav, odd_lot=odd, floor=floor)


def header_company(sub: str) -> tuple[str | None, str | None]:
    """(subject company CIK, conformed name) from an EDGAR full-submission header."""
    m = re.search(r"SUBJECT COMPANY:.*?COMPANY CONFORMED NAME:\s*(.+?)\n.*?CENTRAL INDEX KEY:\s*(\d+)", sub, re.S)
    return (m.group(2).lstrip("0"), m.group(1).strip()) if m else (None, None)


def idx_paths(idx_text: str, form: str = "SC TO-I") -> list[str]:
    out = []
    for line in idx_text.splitlines():
        if line.startswith(form + " ") and not line.startswith(form + "/A"):
            m = re.search(r"(edgar/data/\S+\.txt)", line)
            if m:
                out.append(m.group(1))
    return sorted(set(out))


def candidate(t: dict, last_close: float | None) -> dict:
    g = (t["floor"] / last_close - 1) if (last_close and np.isfinite(t["floor"])) else np.nan
    alert = bool(np.isfinite(g) and g >= MIN_FLOOR and t["odd_lot"] == "Y" and not t["nav"])
    return dict(floor_gain=None if not np.isfinite(g) else round(float(g), 4), alert=alert)


def run(state_dir: Path, today: dt.date | None = None, email: bool = True, log=print) -> list[dict]:
    from . import marketdata as md
    from ..data import trading_days
    from ..live.notify import Notifier
    from .news_judge import _cik_map
    path = Path(state_dir) / LOG_NAME
    seen = {r["path"] for r in _read(path)}
    today = today or dt.date.today()
    sess = [d.date() for d in trading_days(today - dt.timedelta(days=10), today)]
    prev = [d for d in sess if d < today][-1]
    cik2tk = {str(v): k for k, v in _cik_map(Path(state_dir)).items()}
    new = []
    for day in filing_days(prev, today):
        q = (day.month - 1) // 3 + 1
        idx = _sec_get(f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{q}/form.{day:%Y%m%d}.idx")
        for p in idx_paths(idx or ""):
            if p in seen:
                continue
            sub = _sec_get(f"https://www.sec.gov/Archives/{p}") or ""
            cik, name = header_company(sub)
            tk = cik2tk.get(cik or "")
            t = terms(sub)
            close = None
            if tk:
                b = md.sip_daily([tk.replace("-", ".")], today - dt.timedelta(days=10)).get(tk.replace("-", "."))
                close = float(b.close.iloc[-1]) if b is not None and len(b) else None
            r = dict(date=str(day), path=p, cik=cik, name=name, ticker=tk, last_close=close,
                     **{k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in t.items()},
                     **candidate(t, close))
            new.append(r)
            log(f"[tender] {day} {tk or '?'} {name}: floor {r['floor']} vs close {close} -> "
                f"{r['floor_gain']} odd-lot {r['odd_lot']}{'  ** ALERT **' if r['alert'] else ''}")
    with path.open("a") as f:
        for r in new:
            f.write(json.dumps(r) + "\n")
    hits = [r for r in new if r["alert"]]
    if hits and email:
        body = "\n".join(f"{r['ticker']} ({r['name']}): guaranteed {r['floor']} vs last close {r['last_close']} "
                         f"= {r['floor_gain']:+.1%}; buy <= 99 shares in TOTAL across accounts, tender all, certify odd lot. "
                         f"https://www.sec.gov/Archives/{r['path']}" for r in hits)
        Notifier(Path(state_dir)).alert(f"odd-lot tender: {', '.join(r['ticker'] for r in hits)}", body)
    log(f"[tender] {len(new)} new SC TO-I, {len(hits)} odd-lot alerts")
    return new


if __name__ == "__main__":
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = dt.date.fromisoformat(args[0]) if args else None
    run(Path(__file__).resolve().parents[2] / "state", day, email="--no-email" not in sys.argv)
