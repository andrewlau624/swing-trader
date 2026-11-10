"""Refuse stale or broken Schwab quotes before sizing an order.

Schwab's `lastPrice` on a thin preferred can be hours old (`tradeTime`) while the quote itself (`quoteTime`, bid/ask)
is current, and a halted or delayed feed looks just like a live one. PREF-EX (15:25, in session) and CEF-RV (09:05,
pre-open) used `lastPrice` with no check. Rules:

- in session (PREF-EX): quote no older than IN_SESSION_AGE_S, status Normal, two-sided, not crossed, spread <= MAX_SPREAD;
  price = last if it sits inside the quote (+-BAND), else the mid.
- pre-open (CEF-RV): the prior session's quote is expected; quote no older than PRE_OPEN_AGE_S (covers a long weekend),
  status Normal or Closed (Nasdaq names off-hours), price = last (else mark, else close) within +-PRE_OPEN_BAND of the prior close.

`fetch()` returns the usable prices plus a per-symbol detail dict (bid/ask/mid/age/reason) that callers log.
"""
from __future__ import annotations

import time

IN_SESSION_AGE_S = 300
PRE_OPEN_AGE_S = 4 * 86400
MAX_SPREAD = 0.10
BAND = 0.03
PRE_OPEN_BAND = 0.15
OK_STATUS = (None, "", "Normal")
OFF_HOURS_OK = OK_STATUS + ("Closed",)    # Schwab marks Nasdaq listings "Closed" outside 09:30-16:00 (NYSE stay "Normal")


def check(q: dict, now_s: float, *, in_session: bool) -> tuple[float | None, dict]:
    """(price or None, detail). detail always carries bid/ask/mid/age_s; 'reason' is set when the price is refused."""
    bid, ask = float(q.get("bidPrice") or 0), float(q.get("askPrice") or 0)
    last = float(q.get("lastPrice") or 0)
    close = float(q.get("closePrice") or 0)
    qt = q.get("quoteTime")
    age = None if not qt else round(now_s - float(qt) / 1000, 1)
    mid = round((bid + ask) / 2, 4) if bid > 0 and ask >= bid else None
    d = dict(bid=bid or None, ask=ask or None, mid=mid, last=last or None, close=close or None, age_s=age,
             status=q.get("securityStatus"))

    def no(why: str):
        d["reason"] = why
        return None, d

    if q.get("securityStatus") not in (OK_STATUS if in_session else OFF_HOURS_OK):
        return no(f"status {q.get('securityStatus')}")
    if age is None:
        return no("no quote time")
    if age < -60:
        return no(f"quote {-age:.0f}s in the future")
    if in_session:
        if age > IN_SESSION_AGE_S:
            return no(f"quote {age:.0f}s old")
        if mid is None:
            return no("one-sided or crossed quote")
        if (ask - bid) / mid > MAX_SPREAD:
            return no(f"spread {(ask - bid) / mid:.1%}")
        px = last if last and bid * (1 - BAND) <= last <= ask * (1 + BAND) else mid
    else:
        if age > PRE_OPEN_AGE_S:
            return no(f"quote {age / 86400:.1f}d old")
        px = last or float(q.get("mark") or 0) or close
        if not px:
            return no("no price")
        if close and abs(px / close - 1) > PRE_OPEN_BAND:
            return no(f"price {px} is {px / close - 1:+.0%} from the prior close {close}")
    d["px"] = round(float(px), 4)
    return float(px), d


def fetch(ad, syms: list[str], *, in_session: bool, now_s: float | None = None) -> tuple[dict[str, float], dict[str, dict]]:
    """Usable prices and per-symbol details (including refused symbols, with a reason)."""
    if not syms:
        return {}, {}
    j = ad.c.get_quotes(syms).json() or {}
    now_s = time.time() if now_s is None else now_s
    px, det = {}, {}
    for s in syms:
        q = (j.get(s) or {}).get("quote") or {}
        p, d = check(q, now_s, in_session=in_session) if q else (None, {"reason": "no quote"})
        det[s] = d
        if p:
            px[s] = p
    return px, det


def refused(det: dict[str, dict]) -> dict[str, str]:
    return {s: d["reason"] for s, d in det.items() if d.get("reason")}
