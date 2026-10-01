"""Signals for the daily-cadence book. Pure functions, no I/O.

Each one is a port of the research code in research/daily-strategies/, and
tests/test_daily.py pins it to that behaviour. Three legs:

  ibs    - IBS < 0.2 on tech ETFs, decided on the last COMPLETE daily bar and
           held open -> next open. (research: etfport.py, "@nextopen")
  night  - stocks down >= 8% on the day, trading within 10% of the day's low,
           decided at ~15:40 ET from what is known THEN, bought at the close
           auction and sold at the next open auction. (research: t1550.py)
  noise  - QQQ "noise area" intraday momentum. (research: noise.py)

The night leg is the one where lookahead did the most damage in research:
computed from the final close it showed 58% CAGR, computed at 15:50 it showed
31%. Nothing here may be fed the closing print.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

ET = "America/New_York"


# ------------------------------------------------------------------ IBS leg
def ibs(high: float, low: float, close: float) -> float:
    """Internal bar strength: where the close sits in the day's range, 0..1."""
    rng = high - low
    if not np.isfinite(rng) or rng <= 0:
        return np.nan
    return (close - low) / rng


def ibs_targets(last_bars: dict[str, dict], ibs_max: float) -> list[str]:
    """ETFs to HOLD from the next open. `last_bars[sym]` is the last complete
    daily bar {high, low, close}. Re-evaluated every morning: a name still
    below the threshold stays held, one that recovered is sold."""
    out = []
    for sym, b in last_bars.items():
        v = ibs(b["high"], b["low"], b["close"])
        if np.isfinite(v) and v < ibs_max:
            out.append(sym)
    return sorted(out)


def equal_weights(symbols: list[str], leg_equity: float,
                  max_name_pct: float = 1.0) -> dict[str, float]:
    """Dollar allocation per name: 1/n of the leg, capped per name."""
    if not symbols:
        return {}
    per = leg_equity * min(1.0 / len(symbols), max_name_pct)
    return {s: per for s in symbols}


def momentum_top(closes: pd.DataFrame, today: pd.Timestamp, k: int,
                 lookback: int = 252, skip: int = 21) -> list[str]:
    """Top-k ETFs by 12-1 month momentum, ranked at the last month-end BEFORE
    today and held for the month (research: h5a.py, "top-3 by 12m momentum").
    Replaces a hand-picked tech list: same idea, chosen by rule, so it rotates
    on its own if tech stops leading. closes: session-date index, one column
    per ETF, bars strictly before today."""
    if closes is None or closes.empty or not isinstance(closes.index, pd.DatetimeIndex):
        return []                     # no data today: hold nothing rather than crash
    c = closes[closes.index < today]
    mom = c.shift(skip) / c.shift(lookback) - 1
    month_ends = mom.groupby([mom.index.year, mom.index.month]).tail(1)
    month_ends = month_ends[month_ends.index.to_period("M") < today.to_period("M")]
    if month_ends.empty:
        return []
    last = month_ends.iloc[-1].dropna()
    return sorted(last.sort_values(ascending=False).index[:k])


# ------------------------------------------------ regular session (23/5-proof)
# From 2026-12-06 US exchanges trade 21:00-20:00 ET (23/5). The official 09:30
# open and 16:00 close auctions are unchanged, and every leg trades only them
# or the regular session. So the book takes its session from the exchange's
# REGULAR-hours calendar and treats the broker clock as a cross-check: a
# clock whose next_close moves to 20:00 would otherwise make every day look
# like an early close and silently switch the night and intraday legs off.
REGULAR_OPENS = {(9, 30)}
REGULAR_CLOSES = {(16, 0), (13, 0)}         # 13:00 = scheduled half day


def regular_clock(now, sessions) -> SimpleNamespace:
    """sessions: [(open, close)] tz-aware ET datetimes from the exchange
    calendar, covering today and the next few sessions. Returns a clock with
    the broker-clock fields in REGULAR-session meaning. Raises ValueError if
    a session is not a 09:30 open with a 16:00 / 13:00 close (a calendar
    whose meaning changed must not be trusted either)."""
    ss = sorted(sessions)
    for o, c in ss:
        if (o.hour, o.minute) not in REGULAR_OPENS or (c.hour, c.minute) not in REGULAR_CLOSES:
            raise ValueError(f"calendar session {o:%Y-%m-%d %H:%M}-{c:%H:%M} is not regular hours")
    nxt_open = next((o for o, _ in ss if o > now), None)
    nxt_close = next((c for _, c in ss if c > now), None)
    if nxt_open is None or nxt_close is None:
        raise ValueError("calendar does not reach the next session")
    return SimpleNamespace(is_open=any(o <= now < c for o, c in ss), next_open=nxt_open,
                           next_close=nxt_close, source="calendar")


def clock_drift(broker_clock, regular) -> str | None:
    """None when the broker clock still means the regular session; otherwise
    what differs (the 23/5 canary)."""
    diffs = []
    for f in ("next_open", "next_close"):
        a, b = pd.Timestamp(getattr(broker_clock, f)), pd.Timestamp(getattr(regular, f))
        if abs((a - b).total_seconds()) > 60:
            diffs.append(f"{f} broker {a.tz_convert(ET):%m-%d %H:%M} vs regular {b.tz_convert(ET):%m-%d %H:%M}")
    if bool(broker_clock.is_open) != bool(regular.is_open):
        diffs.append(f"is_open broker {bool(broker_clock.is_open)} vs regular {bool(regular.is_open)}")
    return "; ".join(diffs) or None


def bar_semantics_issues(sym: str, bar: dict, rth: dict, bar_ts=None,
                         tol_bps: float = 5.0) -> list[str]:
    """23/5 canary for a vendor DAILY bar of a liquid ETF vs the same session's
    regular-hours SIP minutes. Baseline (Sep 2026, SPY/QQQ): stamp 00:00 ET,
    open/high/low equal the RTH minutes (0bp median, <0.3bp max). A daily bar
    that starts including the 21:00 overnight session shows up as an open, high
    or low outside the RTH values, or an evening stamp. Volume already includes
    pre/post (x1.2) and the research used the same, so it is not checked."""
    out = []
    if bar_ts is not None:
        t = pd.Timestamp(bar_ts).tz_convert(ET)
        if (t.hour, t.minute) != (0, 0):
            out.append(f"{sym} daily bar stamped {t:%H:%M} ET (was 00:00)")
    for f, bad in (("open", lambda b, r: abs(b / r - 1) * 1e4 > tol_bps),
                   ("high", lambda b, r: (b / r - 1) * 1e4 > tol_bps),
                   ("low", lambda b, r: (1 - b / r) * 1e4 > tol_bps)):
        b, r = float(bar.get(f, np.nan)), float(rth.get(f, np.nan))
        if np.isfinite(b) and np.isfinite(r) and r > 0 and bad(b, r):
            out.append(f"{sym} daily {f} {b:.2f} vs regular-hours {r:.2f} ({(b / r - 1) * 1e4:+.0f}bp)")
    return out


def official_open(schwab_open: float, sip_open: float, tol_bps: float = 10.0) -> tuple[float, str]:
    """The regular-session open for the intraday bands. Schwab's quote open is
    the official one today; the consolidated 09:30 minute is regular-hours by
    construction. If they disagree (23/5: a quote 'open' could become the 21:00
    overnight print), trust the minute bar."""
    s_ok, m_ok = np.isfinite(schwab_open), np.isfinite(sip_open) and sip_open > 0
    if s_ok and m_ok:
        return ((schwab_open, "schwab") if abs(schwab_open / sip_open - 1) * 1e4 <= tol_bps
                else (sip_open, "sip-minute (schwab open disagreed)"))
    if s_ok:
        return schwab_open, "schwab"
    return (sip_open, "sip-minute") if m_ok else (float("nan"), "none")


# ---------------------------------------------------------------- night leg
def loser_picks(rows: pd.DataFrame, *, day_ret_max: float, ibs_max: float,
                price_min: float, price_max: float) -> pd.DataFrame:
    """Rows: one per symbol with columns
         price       - latest trade at decision time (~15:40 ET)
         prev_close  - yesterday's official close
         high, low   - the day's range AS KNOWN AT DECISION TIME
       Returns the qualifying rows, most-beaten first, with day_ret and ibs.
    """
    if rows.empty:
        return rows.assign(day_ret=[], ibs=[])
    r = rows.copy()
    r["high"] = np.maximum(r["high"], r["price"])
    r["low"] = np.minimum(r["low"], r["price"])
    r["day_ret"] = r["price"] / r["prev_close"] - 1.0
    rng = (r["high"] - r["low"]).where(lambda x: x > 0)
    r["ibs"] = (r["price"] - r["low"]) / rng
    m = ((r["day_ret"] <= day_ret_max) & (r["ibs"] < ibs_max)
         & (r["price"] >= price_min) & (r["price"] <= price_max)
         & np.isfinite(r["day_ret"]) & np.isfinite(r["ibs"]))
    return r[m].sort_values("day_ret")


def prev_close_mismatch(rows: pd.DataFrame, tol: float = 0.03) -> pd.Series:
    """True where yesterday's close from our daily bars disagrees with the
    quote feed's own previous close. That is a split or other corporate action
    our bars have not absorbed yet, and it fakes the day's move: a 1:10 split
    reads as -90%. The research data had exactly these (a -94% "day" followed
    by +1,250% "overnight"). Rows without a feed value are never flagged."""
    if "feed_prev_close" not in rows:
        return pd.Series(False, index=rows.index)
    fp = rows["feed_prev_close"].astype(float)
    bad = (fp / rows["prev_close"].astype(float) - 1.0).abs() > tol
    return bad & np.isfinite(fp) & (fp > 0)


def night_exit_cost(fills: list[dict], opens: dict, window: int = 30) -> tuple[int, float]:
    """Mean cost of the last `window` night-leg SELLS against the official
    opening print, in bps per side (+ = sold below the open). The whole night
    edge is in the open auction (RESULTS.md addendum 10), and every 5bp/side
    here costs ~8pp/yr; it is gone near 28bp (addendum 14). `opens` maps
    (sym, 'YYYY-MM-DD') -> official open. Returns (n measured, mean bps)."""
    costs = night_exit_costs(fills, opens, window)
    return len(costs), (float(np.mean(costs)) if costs else float("nan"))


def night_exit_costs(fills: list[dict], opens: dict, window: int = 30) -> list[float]:
    """The per-sell costs behind night_exit_cost, bps/side (+ = below the open)."""
    sells = [f for f in fills if f.get("leg") == "night" and f.get("side") == "sell"]
    costs = []
    for f in sells[-window:]:
        o = opens.get((f["sym"], str(f.get("filled_at", ""))[:10]))
        if o and o > 0 and f.get("fill_px"):
            costs.append(-(float(f["fill_px"]) / o - 1.0) * 1e4)
    return costs


def cost_upper_bound(costs, z: float = 1.645) -> float:
    """One-sided 95% upper bound on the mean cost (normal approximation, fine
    from ~20 exits). Reporting only: the lever gate stays the pre-registered
    mean <= LEVER_MAX_EXIT_BPS over LEVER_MIN_EXITS. It says how much the mean
    could still move, e.g. a -2bp mean with a +12bp bound is not yet proof."""
    c = np.asarray(costs, float)
    if len(c) < 2:
        return float("nan")
    return float(c.mean() + z * c.std(ddof=1) / np.sqrt(len(c)))


def night_exit_costs_by_day(fills: list[dict], opens: dict, window: int = 30) -> list[tuple[str, float]]:
    """(exit day, cost bps/side) for the scored night sells: the input to the
    day-clustered bound. Sells on one morning share that morning's auctions,
    so they are not independent (addendum 38)."""
    sells = [f for f in fills if f.get("leg") == "night" and f.get("side") == "sell"]
    out = []
    for f in sells[-window:]:
        day = str(f.get("filled_at", ""))[:10]
        o = opens.get((f["sym"], day))
        if o and o > 0 and f.get("fill_px"):
            out.append((day, -(float(f["fill_px"]) / o - 1.0) * 1e4))
    return out


# Lever gate G1 (addendum 38, SHADOW): open from 20 exits once the one-sided
# 95% DAY-CLUSTERED upper bound on the mean exit cost is <= 10bp. Logged
# beside the live gate (G0 = lever_ok); lever_ok itself is unchanged. The
# verifier found a clustered SE from 3-5 exit days unreliable, so G1 also
# needs G1_MIN_DAYS distinct exit days.
G1_MIN_EXITS = 20
G1_MIN_DAYS = 8
G1_Z = 1.645


def clustered_upper_bound(costs, days, z: float = G1_Z) -> tuple[float, float, int]:
    """(mean, one-sided upper bound, n clusters) of per-exit costs clustered by
    exit day: SE^2 = G/(G-1) * sum_g (sum_i in g (c_i - mean))^2 / n^2."""
    c = np.asarray(costs, float)
    if len(c) == 0:
        return float("nan"), float("nan"), 0
    m = float(c.mean())
    groups: dict = {}
    for d, x in zip(days, c):
        groups[d] = groups.get(d, 0.0) + (x - m)
    g = len(groups)
    if g < 2:
        return m, float("nan"), g
    var = g / (g - 1) * sum(v * v for v in groups.values()) / len(c) ** 2
    return m, float(m + z * np.sqrt(var)), g


def lever_g1(pairs: list[tuple[str, float]]) -> dict:
    """G1 shadow verdict from (day, cost) pairs. Reporting only."""
    days, costs = [p[0] for p in pairs], [p[1] for p in pairs]
    m, ub, g = clustered_upper_bound(costs, days)
    n = len(costs)
    would = bool(n >= G1_MIN_EXITS and g >= G1_MIN_DAYS and np.isfinite(ub)
                 and ub <= LEVER_MAX_EXIT_BPS)
    return {"n": n, "days": g, "mean": m, "ub": ub, "would_open": would}


# Wash guard G4s (addendum 31, POST-HOC, SHADOW). The live guard
# (executor._wash_symbols) is symmetric: each real-money book avoids every
# name the other one holds, has an open order in, or closed in the last 31
# days, on every leg; the brokerage book runs first each phase, so it claims
# the shared names and starves the Roth (~35pp/yr in the study). G4s: the
# Roth goes first. The brokerage book yields its NIGHT names to anything the
# Roth traded in 31 days (its IBS and intraday legs are unrestricted, since
# the Roth avoids them); the Roth night leg skips only names the brokerage
# book sold at a LOSS in 30 days (plus names it holds or has orders in right
# now); the Roth IBS leg trades a different-index look-alike, and skips the
# same-index/no-look-alike names the brokerage book traded in 31 days.
# The live version is daily.wash_guard: roth_first (executor._roth_night_wash,
# _roth_ibs_targets); it keeps the taxable book's IBS/intraday legs symmetric.
WASH_LOOKALIKE = {"SPY": "SPLG", "QQQ": "QQQM", "IWM": "VTWO", "MDY": "IJH", "XLK": "VGT",
                  "XLF": "VFH", "XLE": "VDE", "XLV": "VHT", "XLI": "VIS", "XLY": "VCR",
                  "XLP": "VDC", "XLU": "VPU", "XLB": "VAW", "SMH": "SOXX", "EEM": "IEMG",
                  "EFA": "IEFA"}                    # DIA, XBI: none
WASH_SAME_INDEX = {"SPY", "QQQ", "IWM", "MDY", "EEM"}   # look-alike tracks the SAME index: not used
WASH_SAFE_LOOKALIKE = {k: v for k, v in WASH_LOOKALIKE.items() if k not in WASH_SAME_INDEX}


def _cut(today: str, days: int) -> str:
    return (pd.Timestamp(today) - pd.Timedelta(days=days)).date().isoformat()


def book_now(b: dict, terminal=frozenset()) -> set[str]:
    """Names a book (its saved json) holds or has a live order in."""
    out = set(b.get("positions", {}))
    out |= {o.get("sym") for o in (b.get("orders") or {}).values()
            if o.get("sym") and o.get("status") not in terminal}
    return out


def book_recent(b: dict, today: str, days: int = 31, terminal=frozenset()) -> set[str]:
    """Held, pending, or closed (exit date) in the last `days`: the live guard's set."""
    cut = _cut(today, days)
    return book_now(b, terminal) | {c["sym"] for c in b.get("closed", [])
                                    if str(c.get("exit_date", "")) >= cut}


def book_loss_sales(b: dict, today: str, days: int = 30) -> set[str]:
    """Names the book closed at a loss in the last `days` (the wash-sale trigger)."""
    cut = _cut(today, days)
    return {c["sym"] for c in b.get("closed", [])
            if str(c.get("exit_date", "")) >= cut and closed_at_loss(c)}


def closed_at_loss(c: dict) -> bool:
    """A closed round trip (book.py writes "pnl") lost money. No pnl: work it
    out from qty/entry/exit; nothing to work it out from: call it a loss (a
    wrongly blocked name costs one trade, a missed wash sale costs the loss)."""
    if c.get("pnl") is not None:
        return float(c["pnl"]) < 0
    try:
        return float(c.get("qty", 1.0)) * (float(c["exit_px"]) - float(c["entry_px"])) < 0
    except (KeyError, TypeError, ValueError):
        return True


def wash_g4s(account: str, other: dict, today: str, ibs_targets=(), cash_sym: str | None = None,
             terminal=frozenset()) -> dict:
    """What G4s would block vs the live symmetric guard, for `account`
    ("live" = brokerage, "roth") given the OTHER book's saved state.
      current   names the live guard blocks on every leg
      night     names G4s blocks for this account's night leg
      other     names G4s blocks for this account's IBS / intraday legs
      ibs_subs  Roth IBS target -> look-alike it would trade instead
      ibs_skip  Roth IBS targets G4s would skip (same-index or no look-alike, other traded 31d)
      ibs_take  IBS targets the account would hold under G4s (after subs)."""
    recent = book_recent(other, today, 31, terminal)
    recent.discard(cash_sym)
    out = {"current": set(recent), "ibs_subs": {}, "ibs_skip": [], "ibs_take": []}
    if account == "roth":
        night = book_loss_sales(other, today, 30) | book_now(other, terminal)
        night.discard(cash_sym)
        out.update(night=night, other=set())
        for s in ibs_targets:
            if s in WASH_SAFE_LOOKALIKE:
                out["ibs_subs"][s] = WASH_SAFE_LOOKALIKE[s]
                out["ibs_take"].append(WASH_SAFE_LOOKALIKE[s])
            elif s in recent:
                out["ibs_skip"].append(s)
            else:
                out["ibs_take"].append(s)
    else:
        out.update(night=set(recent), other=set())
        out["ibs_take"] = list(ibs_targets)
    return out


def exit_cost_by_route(fills: list[dict], opens: dict, window: int = 60) -> dict:
    """Open-sell quality per route (NASDAQ/NYSE/... = directed to the listing
    exchange's auction, AUTO = Schwab's routing, "" = broker OPG orders).
    Returns {route: (n, mean bps/side, auction hit rate)}. A fill within half
    a cent of the official open counts as an auction fill: that is the direct
    evidence the emulated market-on-open is reaching the auction."""
    sells = [f for f in fills if f.get("leg") == "night" and f.get("side") == "sell"][-window:]
    by: dict[str, list] = {}
    for f in sells:
        o = opens.get((f["sym"], str(f.get("filled_at", ""))[:10]))
        if not (o and o > 0 and f.get("fill_px")):
            continue
        px = float(f["fill_px"])
        by.setdefault(str(f.get("route") or ""), []).append(
            (-(px / o - 1.0) * 1e4, abs(px - o) <= 0.005))
    return {r: (len(v), float(np.mean([c for c, _ in v])), float(np.mean([h for _, h in v])))
            for r, v in by.items()}


def dedupe_correlated(picks: pd.DataFrame, rets: dict, max_corr: float = 0.9) -> tuple[pd.DataFrame, list]:
    """One position per underlying bet. Walk the picks most-beaten first and
    drop any whose last-20-day returns correlate above max_corr with one
    already kept. Seven 2x SpaceX ETFs from seven issuers are one bet, not
    seven; so are a stock and its own leveraged ETF. No name parsing, so new
    products are handled as they launch. Returns (kept, [(dropped, kept_as)])."""
    kept, dropped, series = [], [], []
    for sym in picks.index:
        r = np.asarray(rets.get(sym) or [], dtype=float)
        dup = None
        if len(r) >= 10 and np.std(r) > 0:
            for k, rk in series:
                n = min(len(r), len(rk))
                if n >= 10 and np.std(rk[-n:]) > 0 and np.corrcoef(r[-n:], rk[-n:])[0, 1] > max_corr:
                    dup = k; break
        if dup is None:
            kept.append(sym)
            if len(r) >= 10:
                series.append((sym, r))
        else:
            dropped.append((sym, dup))
    return picks.loc[kept], dropped


def gap_scale(today, next_open, scale: float) -> float:
    """Night-leg exposure multiplier: `scale` when the position is held over
    more than one calendar night (weekend, holiday), else 1. Weekend nights
    earn the same per trade but swing harder (std 6.2% vs 5.5%, fatter left
    tail), and a crash's worst gaps land there: 2020-03-06 -> 03-09, five oil
    producers at -33..-53% after OPEC broke over the weekend (addendum 18)."""
    try:
        gap = (pd.Timestamp(next_open).date() - pd.Timestamp(today).date()).days
    except Exception:
        return 1.0
    return float(scale) if gap > 1 else 1.0


def night_sizing(picks: pd.DataFrame, *, vol_min: float, crowd_n: int,
                 max_name_pct: float) -> tuple[pd.DataFrame, float]:
    """Filter and size the night leg (research: h1.py / h1port.py, rule R6).

    - drop names whose 20-day volatility is under `vol_min`: in quiet names a
      -8% day is news, not overreaction (-33bp/trade, t -8)
    - count the day's raw signals BEFORE that filter; on days with more than
      `crowd_n` of them the selloff is market-wide and the bounce is weak
      (-9bp vs +25bp on ordinary days), so exposure scales by crowd_n / n.
    Returns (kept picks, fraction of the leg per name)."""
    n_raw = len(picks)
    kept = picks[picks["vol20"] >= vol_min] if "vol20" in picks else picks
    if kept.empty:
        return kept, 0.0
    per = min(1.0 / len(kept), max_name_pct) * min(1.0, crowd_n / max(n_raw, 1))
    return kept, per


def night_impact_cap(adv, vol20, edge_bps: float, impact_y: float) -> np.ndarray:
    """Largest night order ($) per name that still raises expected profit
    (research/drafts Study X). Under the square-root law each auction costs
    Y * sigma * sqrt(q / ADV), so q * (g - 2 Y sigma sqrt(q/ADV)) peaks at
    q* = ADV * (g / (3 Y sigma))^2. Thin or volatile names are capped first;
    at a few $k of equity no order comes near q*. sigma = daily sd from the
    annualised vol20. Returns +inf where the inputs are missing."""
    adv = np.asarray(adv, float)
    sig = np.asarray(vol20, float) / np.sqrt(252)
    with np.errstate(divide="ignore", invalid="ignore"):
        q = adv * (edge_bps / 1e4 / (3 * impact_y * sig)) ** 2
    return np.where(np.isfinite(q) & (adv > 0) & (sig > 0), q, np.inf)


def impact_fit(cost_bps, x_bps, days=None) -> dict:
    """Fit the square-root impact coefficient Y from live night fills:
    cost_bps = Y * x_bps, x = sigma_daily * sqrt(order $ / ADV) in bp, through
    the origin (the spread is ~0 at the auctions, NEXT.md). SE clustered by
    day when `days` is given (one morning's sells share its auctions).
    `identified` = the 95% interval is narrower than +-1, i.e. it can tell the
    Study X choices (Y 1 / 2 / 4) apart. Tiny orders give x ~ 1bp and leave Y
    unidentified: that is the expected answer at a few $k."""
    c = np.asarray(cost_bps, float); x = np.asarray(x_bps, float)
    ok = np.isfinite(c) & np.isfinite(x) & (x > 0)
    c, x = c[ok], x[ok]
    n = len(c)
    if n < 5 or (x ** 2).sum() <= 0:
        return {"n": n, "y": float("nan"), "se": float("nan"), "ub": float("nan"),
                "mean_x": float(x.mean()) if n else float("nan"), "identified": False}
    y = float((c * x).sum() / (x ** 2).sum())
    e = c - y * x
    g = np.asarray(days)[ok] if days is not None else np.arange(n)
    sx = pd.Series(e * x).groupby(g).sum().to_numpy()
    se = float(np.sqrt((sx ** 2).sum()) / (x ** 2).sum())
    return {"n": n, "y": y, "se": se, "ub": y + 1.96 * se, "mean_x": float(x.mean()),
            "identified": bool(1.96 * se < 1.0)}


# Night sizing tilt (RESULTS.md addendum 16). OLS of the next-open return on
# (log vol20, day return), fitted on 2021-23 ONLY and judged on 2024-26: live
# book 41.3% -> 46.8% there, beating a shuffled-weight placebo (42.9%). The
# deeper the day's drop, the bigger the bounce; vol20 adds a little. These
# numbers are frozen: refitting on data that includes the holdout would
# erase the evidence that justified them.
NIGHT_TILT = {"mu": (0.0959, -0.1232), "sd": (0.4992, 0.0610),
              "beta_bp": (1.14, -11.54), "pred_sd_bp": 12.07}


def night_tilt(vol20, day_ret, k: float = 0.25) -> np.ndarray:
    """Per-name weights with mean 1 (so the leg's gross is unchanged):
    1 + k * predicted edge / its spread, clipped to [0.25, 2]. k = 0 -> equal."""
    vol20 = np.asarray(vol20, float); day_ret = np.asarray(day_ret, float)
    if k == 0 or len(vol20) == 0:
        return np.ones(len(vol20))
    t = NIGHT_TILT
    x = np.column_stack([np.log(np.maximum(vol20, 1e-3)), day_ret])
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    z = (x - np.array(t["mu"])) / np.array(t["sd"])
    w = np.clip(1 + k * (z @ (np.array(t["beta_bp"]) / 1e4)) / (t["pred_sd_bp"] / 1e4), 0.25, 2.0)
    return w / w.mean()


# Tug-of-war tilt (Round 19, Study AU3, research/drafts/study_au_tow.md; SHADOW, off by
# default). TOW = sessions among the last 20 completed ones with open > previous close and
# close < open (Akbas-Boehmer-Jiang-Koch 2022). z constants frozen from the 2021-23 picks.
TOW_MU, TOW_SD, TOW_MIN_SESSIONS = 5.14, 2.10, 15


def tug_of_war(opens, closes, n: int = 20) -> float:
    """Count of the last n sessions (oldest first; completed sessions only, today excluded)
    with an up gap (open_t > close_{t-1}) and a down day (close_t < open_t). Sessions with
    a missing price or a |move| > 100% (bad bar) are skipped; NaN if fewer than
    TOW_MIN_SESSIONS of the last n are valid (needs n + 1 bars for n gaps)."""
    o = np.asarray(opens, float); c = np.asarray(closes, float)
    if len(o) < 2:
        return float("nan")
    gap = o[1:] / c[:-1] - 1
    intr = c[1:] / o[1:] - 1
    gap, intr = gap[-n:], intr[-n:]
    ok = np.isfinite(gap) & np.isfinite(intr) & (np.abs(gap) <= 1) & (np.abs(intr) <= 1)
    if ok.sum() < TOW_MIN_SESSIONS:
        return float("nan")
    return float(((gap > 0) & (intr < 0) & ok).sum())


# The AU3 gate (pre-registered in study_au_tow.md): research tercile cut points (2021-23 picks:
# low < 4, high >= 6). On after >= TOW_GATE_N live picks if high-TOW net > low-TOW net; same rule kills it.
TOW_LOW_BELOW, TOW_HIGH_FROM, TOW_GATE_N = 4, 6, 300


def tow_gate(tows, rets) -> dict:
    """Live check of the AU3 tilt: mean net return of high- vs low-TOW night round trips."""
    t = np.asarray(tows, float); r = np.asarray(rets, float)
    ok = np.isfinite(t) & np.isfinite(r)
    t, r = t[ok], r[ok]
    lo, hi = r[t < TOW_LOW_BELOW], r[t >= TOW_HIGH_FROM]
    n = int(len(r))
    spread = float(hi.mean() - lo.mean()) if len(lo) and len(hi) else float("nan")
    verdict = ("wait" if n < TOW_GATE_N or not np.isfinite(spread)
               else ("on" if spread > 0 else "off"))
    return dict(n=n, n_lo=int(len(lo)), n_hi=int(len(hi)), lo=float(lo.mean()) if len(lo) else float("nan"),
                hi=float(hi.mean()) if len(hi) else float("nan"), spread=spread, verdict=verdict)


def night_tilt_tow(base_w, tow, k: float = 0.25) -> np.ndarray:
    """base_w x clip(1 + k z(TOW), 0.25, 2), renormalised to base_w's mean (the leg's
    gross is unchanged). Unknown TOW -> z = 0 (no tilt from it)."""
    base_w = np.asarray(base_w, float)
    if len(base_w) == 0:
        return base_w
    t = np.asarray(tow, float)
    z = np.where(np.isfinite(t), (t - TOW_MU) / TOW_SD, 0.0)
    w = base_w * np.clip(1 + k * z, 0.25, 2.0)
    return w * base_w.mean() / w.mean()


# Tilt v2 (RESULTS.md addendum 23): adds YESTERDAY's return. A name that rose
# hard yesterday and crashed today bounces more (+31bp per sd; t 2.0 / 2.6 per
# half). Fitted on 2021-23 only, frozen, judged on 2024-26. OFF by default
# (daily.night_tilt_model: v1): it was the best of 9 screened features and
# its sign was the opposite of the prior written down before testing.
NIGHT_TILT_V2 = {"mu": (0.1706, -0.1298, 0.0096), "sd": (0.5344, 0.0602, 0.1097),
                 "lo": (-0.4912, -0.4212, -0.2612), "hi": (1.8496, -0.0804, 0.6134),
                 "beta_bp": (6.60, -17.49, 31.43), "pred_sd_bp": 41.04}


def night_tilt_v2(vol20, day_ret, prev_ret, k: float = 0.25) -> np.ndarray:
    """night_tilt with a third input, yesterday's return (close t-1 / close t-2 - 1).
    Inputs are winsorised to the fit's 1st-99th percentiles, then z-scored."""
    vol20 = np.asarray(vol20, float); n = len(vol20)
    if k == 0 or n == 0:
        return np.ones(n)
    t = NIGHT_TILT_V2
    x = np.column_stack([np.log(np.maximum(vol20, 1e-3)), np.asarray(day_ret, float),
                         np.asarray(prev_ret, float)])
    x = np.where(np.isfinite(x), x, np.array(t["mu"]))      # unknown input -> no tilt from it
    x = np.clip(x, t["lo"], t["hi"])
    z = (x - np.array(t["mu"])) / np.array(t["sd"])
    w = np.clip(1 + k * (z @ np.array(t["beta_bp"])) / t["pred_sd_bp"], 0.25, 2.0)
    return w / w.mean()


# ------------------------------------------------------------ kill rules
# Pre-registered 2026-09-24, BEFORE any live results (RESULTS.md addendum 16).
# Written down now so that a losing leg is switched off by a rule, not kept
# alive by hope. Do not loosen these after seeing live numbers.
#   leg: (min round trips before judging, t-stat below which a losing leg dies)
KILL_MIN_TRADES = {"night": 100, "noise": 120, "ibs": 60, "conv": 60}
KILL_T = -1.0
KILL_EXIT_COST_BPS = 25.0     # night open sells this far below the official open: edge gone (~28bp)
KILL_EXIT_COST_MIN_N = 30
HALT_DRAWDOWN = 0.25          # realised-P&L drawdown / equity; backtest worst is ~-20%


def kill_check(closed: list[dict], min_trades: dict = KILL_MIN_TRADES,
               t_max: float = KILL_T) -> dict[str, str]:
    """{leg: reason} for every leg whose live round trips (net of real fills)
    lose money with t < t_max once it has min_trades of them. Round trips
    booked out at an unknown price (`note`) are left out."""
    out = {}
    for leg, n_min in min_trades.items():
        r = np.array([c["ret"] for c in closed if c.get("leg") == leg and not c.get("note")], float)
        if len(r) < n_min:
            continue
        m, sd = float(r.mean()), float(r.std(ddof=1))
        t = m / (sd / np.sqrt(len(r))) if sd > 0 else 0.0
        if m < 0 and t < t_max:
            out[leg] = f"{len(r)} live round trips average {m*1e4:+.1f}bp (t {t:.2f} < {t_max})"
    return out


def realised_drawdown(closed: list[dict], equity: float) -> float:
    """Worst peak-to-trough of cumulative realised P&L, as a fraction of
    current equity. Built from P&L, not the equity log, so $1k deposits
    cannot hide a losing streak."""
    if not closed or equity <= 0:
        return 0.0
    cum = np.cumsum([float(c.get("pnl") or 0.0) for c in sorted(
        closed, key=lambda c: str(c.get("exit_date", "")))])
    return float(min(0.0, (cum - np.maximum.accumulate(np.r_[0.0, cum])[1:]).min()) / equity)


# Oversold overnight (addendum 27, SHADOW). SPY/QQQ after 3 down closes in a
# row or RSI(2) < 10, bought at the close auction with the IBS leg's idle
# money and sold at the next open. research/sim/oversold.py honest_1540 is the
# reference: the 15:40 price stands in for today's close.
OVERSOLD_SYMBOLS = ("SPY", "QQQ")
OVERSOLD_RSI_MAX = 10.0
OVERSOLD_COST_BPS = 1.0       # per side, shadow scoring (research tier)


def oversold_trigger(closes, price: float) -> tuple[bool, str]:
    """(fires?, why) from prior daily closes (oldest -> newest, through
    yesterday) and the decision-time price. RSI(2) is Wilder-style EWM with
    alpha 0.5 over the prior changes, updated with today's change."""
    c = np.asarray(closes, float)
    if len(c) < 4 or not np.isfinite(price):
        return False, "not enough history"
    d = pd.Series(np.diff(c))
    up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean().iloc[-1]
    dn = (-d.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean().iloc[-1]
    chg = price - c[-1]
    up_t, dn_t = 0.5 * up + 0.5 * max(chg, 0.0), 0.5 * dn + 0.5 * max(-chg, 0.0)
    rsi = 100.0 if dn_t == 0 else 100 - 100 / (1 + up_t / dn_t)
    down3 = price < c[-1] < c[-2] < c[-3]
    why = " + ".join(x for x, on in (("3 down closes", down3),
                                      (f"RSI(2) {rsi:.1f} < {OVERSOLD_RSI_MAX:g}", rsi < OVERSOLD_RSI_MAX)) if on)
    return bool(down3 or rsi < OVERSOLD_RSI_MAX), why or f"RSI(2) {rsi:.1f}"


# Overnight leverage gate (addendum 16). 1.3x overnight gross adds ~+7pp/yr
# in both halves at backtest costs, and nearly nothing at pessimistic costs.
# So it switches on only once live fills PROVE the costs, and off again the
# moment they stop doing so.
LEVER_MIN_EXITS = 50          # night open sells scored against the official open
LEVER_MAX_EXIT_BPS = 10.0     # mean cost per side over those exits (backtest assumes 7.5)
LEVER_MAX_DD = 0.10           # no leverage while realised drawdown is deeper than this


def lever_ok(n_exits: int, exit_bps: float, killed: dict, drawdown: float,
             multiplier: float) -> tuple[bool, str]:
    """(on?, why). Every condition must hold on every check."""
    if killed:
        return False, f"a kill rule is active ({', '.join(killed)})"
    if multiplier < 2:
        return False, "not a margin account"
    if n_exits < LEVER_MIN_EXITS:
        return False, f"{n_exits}/{LEVER_MIN_EXITS} night exits measured"
    if not np.isfinite(exit_bps) or exit_bps > LEVER_MAX_EXIT_BPS:
        return False, f"night exits cost {exit_bps:+.1f}bp/side (need <= {LEVER_MAX_EXIT_BPS:g})"
    if drawdown < -LEVER_MAX_DD:
        return False, f"realised drawdown {drawdown:.0%} (limit -{LEVER_MAX_DD:.0%})"
    return True, f"{n_exits} exits at {exit_bps:+.1f}bp/side, drawdown {drawdown:.0%}"


# ---------------------------------------------------------------- noise leg
NOISE_STEP = 30      # decisions at 10:00, 10:30, ... 15:30 (minutes from open)
NOISE_FIRST = 30


def noise_sigma(history_moves: np.ndarray) -> np.ndarray:
    """history_moves: (days, 390) array of |close_m / open_day - 1| for the
    previous `lookback` sessions. Returns sigma per minute-of-day."""
    return np.nanmean(history_moves, axis=0)


def noise_bounds(day_open: float, prev_close: float,
                 sigma: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ub = max(day_open, prev_close) * (1.0 + sigma)
    lb = min(day_open, prev_close) * (1.0 - sigma)
    return ub, lb


def noise_decide(pos: int, price: float, ub: float, lb: float,
                 vwap: float) -> int:
    """One decision point. pos in {-1, 0, 1}. Exit when price falls back
    through the band or VWAP (whichever is tighter), then re-test for entry.
    Mirrors research/noise.py exactly, including re-entry on the same bar."""
    if pos == 1 and price < max(ub, vwap):
        pos = 0
    elif pos == -1 and price > min(lb, vwap):
        pos = 0
    if pos == 0:
        if price > ub:
            pos = 1
        elif price < lb:
            pos = -1
    return pos


def breakout_strength(price: float, ub: float, lb: float, sigma: float) -> tuple[int, float]:
    """(direction, strength) of a noise-area breakout: +1 above the band, -1
    below, 0 inside. Strength = distance past the band in units of that
    minute's sigma (research/daily-strategies/dt3.py)."""
    if not (np.isfinite(price) and sigma > 0):
        return 0, 0.0
    if price > ub:
        return 1, (price / ub - 1) / sigma
    if price < lb:
        return -1, (1 - price / lb) / sigma
    return 0, 0.0


def noise_leverage(daily_closes: pd.Series, target_vol: float,
                   max_lev: float) -> float:
    """Vol-targeted size from the prior 14 daily returns (known pre-open)."""
    r = daily_closes.pct_change().dropna().iloc[-14:]
    sd = float(r.std())
    if not np.isfinite(sd) or sd <= 0:
        return 0.0
    return float(min(max_lev, target_vol / sd))
