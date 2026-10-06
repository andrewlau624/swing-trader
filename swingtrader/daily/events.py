"""Scheduled macro-event calendar for the live daily book (addendum 33).

Only SCHEDULED FOMC decision days (the second day of each meeting, statement
at 14:00 ET). Unscheduled actions are never known in advance and never count.
Copied from research/sim/event_calendar.py (2026) plus the 2027 schedule and
the first 2028 meeting from federalreserve.gov/monetarypolicy/fomccalendars.htm
(fetched 2026-09-28; the Fed marks each date tentative until the meeting
before it confirms it).

The calendar is hard-coded, so it goes stale. `days_left()` says how far it
reaches; the executor and `make daily-status` warn loudly once fewer than
STALE_DAYS of future dates remain. To extend it, append the next year's
decision days to FOMC_SCHEDULED.
"""
from __future__ import annotations

import datetime as dt
import math

FOMC_SCHEDULED = """
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28 2026-12-09
2027-01-27 2027-03-17 2027-04-28 2027-06-09 2027-07-28 2027-09-15 2027-10-27 2027-12-08
2028-01-26
"""
STALE_DAYS = 60

# F3 (addendum 33): QQQ close -> next open with the night leg's unused money on
# the eve of a scheduled FOMC decision. Taxable only (a Roth QQQ buy within 30
# days of a taxable QQQ intraday loss sale disallows that loss for good).
FOMC_FILLER_SYMBOL = "QQQ"
FOMC_COST_BPS = 3.0          # per side, shadow scoring (the study's pass bar cost)
FOMC_DISABLE_N = 16          # pre-registered: switch off if mean net < 0 after 16 events


def fomc_dates() -> list[dt.date]:
    return sorted(dt.date.fromisoformat(s) for s in FOMC_SCHEDULED.split())


def is_fomc_eve(next_session: dt.date) -> bool:
    """True when the NEXT trading session is a scheduled FOMC decision day,
    i.e. tonight's close -> next open spans the pre-FOMC night."""
    return next_session in set(fomc_dates())


def next_fomc(today: dt.date) -> dt.date | None:
    return next((d for d in fomc_dates() if d >= today), None)


def days_left(today: dt.date) -> int:
    """Calendar days from today to the last date in the calendar (negative = run out)."""
    return (fomc_dates()[-1] - today).days


def stale_warning(today: dt.date) -> str | None:
    left = days_left(today)
    if left >= STALE_DAYS:
        return None
    return (f"FOMC calendar in swingtrader/daily/events.py runs out {fomc_dates()[-1]} "
            f"({left} days left, < {STALE_DAYS}): add next year's scheduled decision days "
            "from federalreserve.gov/monetarypolicy/fomccalendars.htm, or the FOMC-eve shadow "
            "silently stops firing")


def filler_spare(budget: float, planned: float, cash_left: float | None = None,
                 floor: float = 0.0) -> float:
    """Spare night money = night budget - planned night notional (research
    book.day_pnl filler), never more than the book cash left above its floor."""
    spare = max(0.0, budget - planned)
    if cash_left is not None:
        spare = min(spare, max(0.0, cash_left - floor))
    return spare


def filler_shares(spare: float, price: float) -> int:
    """Whole shares: the close/open auctions take whole shares only."""
    if not (price and price > 0 and math.isfinite(price)):
        return 0
    return int(math.floor(spare / price))


def fomc_score(history: list[dict]) -> tuple[int, float, bool]:
    """(n events, mean net bp, auto-disable proposed?) over scored events."""
    r = [float(h["ret"]) for h in history if h.get("ret") is not None]
    if not r:
        return 0, float("nan"), False
    m = sum(r) / len(r) * 1e4
    return len(r), m, (len(r) >= FOMC_DISABLE_N and m < 0)


# ---------------------------------------------------------------- Track M1: N2 (CPI / NFP exit mornings)
# N2 (addendum 33, RESULTS.md:2992): the night leg earns more on nights whose exit morning has an 08:30 CPI or NFP
# release (+18.7bp of equity vs other nights 2021-23, t 2.44; +9.0bp 2024-26, t 0.74). Killed on the judge t; Track M1
# (round1_prose.md) scores it forward on the live taxable book's own night round trips: log-only, no sizing.
# 2026 dates copied from research/sim/event_calendar.py; Oct-Dec 2026 from bls.gov/schedule/news_release/cpi.htm and
# empsit.htm (fetched 2026-10-04; BLS had not posted 2027). Append each new schedule; `release_stale_warning` says when.
CPI_RELEASES = """
2026-01-13 2026-02-13 2026-03-11 2026-04-10 2026-05-12 2026-06-10 2026-07-14 2026-08-12 2026-09-11
2026-10-14 2026-11-10 2026-12-10
"""
NFP_RELEASES = """
2026-01-09 2026-02-11 2026-03-06 2026-04-03 2026-05-08 2026-06-05 2026-07-02 2026-08-07 2026-09-04
2026-10-02 2026-11-06 2026-12-04
"""
N2_PRED_BP, N2_NEED, N2_STOP = 8.8, 48, "2028-10-04"     # prediction: 0.63 x pooled +14.0bp; sign read at 48 event nights


def release_mornings() -> set[dt.date]:
    return {dt.date.fromisoformat(s) for s in (CPI_RELEASES + NFP_RELEASES).split()}


def release_stale_warning(today: dt.date) -> str | None:
    last = max(release_mornings())
    return None if (last - today).days >= STALE_DAYS else (
        f"CPI/NFP calendar in swingtrader/daily/events.py runs out {last}: add the next BLS schedule (N2 shadow)")


def n2_score(closed: list[dict], equity_log: list[dict], since: str = "2026-10-05") -> dict:
    """Night-leg P&L per night as bp of the account's equity on the entry day, release nights (exit morning is a
    CPI/NFP day) vs other nights, from the book's closed round trips with leg == "night" and exit_date >= since.
    Returns n (release nights), n_other, event_bp, other_bp, diff_bp, t (Welch), pred_bp, verdict."""
    eq = {e["date"]: float(e["equity"]) for e in equity_log}
    by: dict[str, float] = {}
    for c in closed:
        x, d0 = str(c.get("exit_date") or "")[:10], str(c.get("entry_date") or "")[:10]
        if c.get("leg") != "night" or not x or x < since or not eq.get(d0):
            continue
        by[x] = by.get(x, 0.0) + float(c.get("pnl") or 0.0) / eq[d0] * 1e4
    rel = release_mornings()
    ev = [v for d, v in by.items() if dt.date.fromisoformat(d) in rel]
    ot = [v for d, v in by.items() if dt.date.fromisoformat(d) not in rel]
    mean = lambda a: sum(a) / len(a) if a else float("nan")
    var = lambda a: sum((v - mean(a)) ** 2 for v in a) / (len(a) - 1) if len(a) > 1 else float("nan")
    diff = mean(ev) - mean(ot) if ev and ot else float("nan")
    se = math.sqrt(var(ev) / len(ev) + var(ot) / len(ot)) if len(ev) > 1 and len(ot) > 1 else float("nan")
    done = len(ev) >= N2_NEED or str(dt.date.today()) >= N2_STOP
    v = (("positive" if diff > 0 else "NOT positive") + " at the gate") if done and ev else f"M1 reading ({len(ev)}/{N2_NEED})"
    return dict(n=len(ev), n_other=len(ot), event_bp=mean(ev), other_bp=mean(ot), diff_bp=diff,
                t=diff / se if se and se == se and se > 0 else float("nan"), pred_bp=N2_PRED_BP, verdict=v)
