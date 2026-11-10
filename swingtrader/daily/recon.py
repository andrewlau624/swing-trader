"""Live-vs-backtest reconciliation, per leg and per live trade day (read-only: places nothing, changes no book).

For every live trade (real books only: `live` taxable, `roth`; paper fills are the simulator's, never counted) it asks
what the repo's own rule says should have happened that day, on data the rule could have seen, and splits the gap:

    total gap = A - C = pick + sizing + timing + fill            (asserted exactly in `decompose`)
      A  backtest:  the rule's picks, rule weights, official auction prints, the rule's own holding period
      C  live:      the live names, live notional weights, live fills, the live holding period
      pick    EW mean of the rule's picks - EW mean of the live names (both at prints, rule holding period)
      sizing  rule weighting effect - live weighting effect (tilt vs whole shares / caps)
      timing  live names: print return over the rule's holding period - over the live holding period
      fill    live names: print return over the live holding period - live fill return
    residual = sizing + timing.  SIGN: every gap is backtest minus live, so POSITIVE = LIVE WORSE.
    Per-side fill gap (bp): buy = fill / print - 1, sell = 1 - fill / print, so POSITIVE = LIVE WORSE on both sides.

Legs and the backtest side used:
  night   15:40 rule replayed on SIP regular-hours minutes (bars stamped <= 15:39, so data ends before the 15:40
          decision) + eligibility from daily bars dated before the day (marketdata.eligibility_rows), then the live
          code's own filters in the executor's order: signals.loser_picks -> vol20 floor -> dedupe_correlated ->
          night_sizing -> night tilt. Prints: official closing cross D -> opening cross of the next session.
  ibs     signals.momentum_top + ibs_targets on SIP daily bars before each morning (executor._ibs_open). Prints:
          opening cross -> opening cross of the first morning the name is no longer a target.
  pref    PREF-EX shadow events (state/pref-ex.jsonl) through pref_ex_live.screen_reason, ranked by yield on the
          PREVIOUS closing cross (known at 15:25), <= MAX_NAMES. Prints: closing cross D -> closing cross on the
          ex-date, + dividend.
  cef     CEF-RV shadow rows (state/cef-rv.jsonl): entries per execution session (cef_rv_live.exec_session). No live
          round trip has closed yet, so pick match and fill gap only.
Official prints: Alpaca SIP auctions (pref_ex_shadow.crosses). Trade dates: marketdata.trade_date.

Data checks fail loudly: an `error` (duplicate fill id, non-positive qty/price, slippage_bps that does not
recompute = unit drift) raises ReconDataError after every issue is listed; `warn` issues (fill outside the auction
window, order-id date != trade date, decision/fill qty mismatch, missing decision row) are printed and kept.

    python -m swingtrader.daily.recon            # writes state/recon.jsonl (the REGISTRY reader) and prints
    python -m swingtrader.daily.recon --print    # prints only, writes nothing

Runtime ~17 min on the server for 25 night days (the SIP daily pull for ~14.8k symbols x2 and one minute-bar pull per
day dominate), so it is NOT in research-shadows (< 1 min rule): run it weekly (make recon, or a weekly timer).
Limits: the replay uses TODAY's config (a rule change since a trade day shows up as pick mismatch, e.g. the
duplicate-bet check); the night universe is today's asset list; "wash guard (likely)" is inferred from the books'
fills, not from the executor's guard set.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import statistics as st
from pathlib import Path

import numpy as np
import pandas as pd

from . import signals as sg

ROOT = Path(__file__).resolve().parents[2]
LOG_NAME = "recon.jsonl"                  # state/: day rows + one summary row per (book, leg) per run
BOOKS = ("live", "roth")                  # real money only; paper fills are fake
AUCTION_LEGS = ("night", "ibs", "tbill")  # legs whose fills must be official auction fills
AUCTION_TOL_S = 90                        # a fill stamped this long after the auction time is still the auction
SLIP_TOL_BP = 1.0                         # logged slippage_bps must recompute from fill/ref within this
TOP = 5
ET = "America/New_York"


class ReconDataError(RuntimeError):
    pass


def _jsonl(p: Path) -> list[dict]:
    from .digest import _jsonl as j
    return j(Path(p))


# ---------------------------------------------------------------- sign conventions (asserted, not just documented)
def fill_gap_bp(side: str, fill: float, ref: float) -> float:
    """Live fill vs the official print, bp; POSITIVE = LIVE WORSE (paid above on a buy, sold below on a sell)."""
    if side not in ("buy", "sell"):
        raise ValueError(f"side must be buy/sell, got {side!r}")
    x = round((float(fill) / float(ref) - 1.0) * 1e4, 6)      # float noise below 1e-6bp is not a cost
    return x if side == "buy" else -x


assert fill_gap_bp("buy", 10.1, 10.0) > 0 and fill_gap_bp("sell", 9.9, 10.0) > 0, "fill-gap sign inverted"


# ---------------------------------------------------------------- loading + data quality
def _issue(sev: str, book: str, check: str, detail: str) -> dict:
    return dict(sev=sev, book=book, check=check, detail=detail)


def load_fills(logs: Path, book: str) -> list[dict]:
    """logs/daily-fills-{book}.jsonl with trade date (marketdata.trade_date) and ET time attached."""
    from .marketdata import trade_date
    out = []
    for i, f in enumerate(_jsonl(Path(logs) / f"daily-fills-{book}.jsonl"), 1):
        t = pd.Timestamp(f.get("filled_at"))
        out.append(dict(f, book=book, line=i, td=str(trade_date(t).date()), et=t.tz_convert(ET)))
    return out


def _auction_time(f: dict) -> list[tuple[int, int]]:
    """Expected auction (hour, minute) ET for a fill: night buy -> the closing cross, everything else -> the open."""
    if f.get("leg") == "night" and f.get("side") == "buy":
        return sorted(sg.REGULAR_CLOSES)
    return sorted(sg.REGULAR_OPENS)


def check_fills(fills: list[dict]) -> list[dict]:
    issues, seen, keys = [], {}, {}
    for f in fills:
        b, ln = f["book"], f.get("line")
        ev = f"daily-fills-{b}.jsonl:{ln} {f.get('coid')}"
        c = f.get("coid")
        if c in seen:
            issues.append(_issue("error", b, "duplicate fill", f"{ev} repeats line {seen[c]}"))
        seen[c] = ln
        q, px, ref = f.get("qty"), f.get("fill_px"), f.get("ref_px")
        if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (q, px)):
            issues.append(_issue("error", b, "qty/price", f"{ev} qty {q} fill_px {px}"))
            continue
        if isinstance(ref, (int, float)) and ref > 0:
            if not 0.5 <= px / ref <= 2.0:
                issues.append(_issue("warn", b, "units", f"{ev} fill {px} vs ref {ref}: off by {px / ref:.2f}x"))
            if f.get("slippage_bps") is not None:
                re_ = fill_gap_bp(f["side"], px, ref)
                if abs(re_ - float(f["slippage_bps"])) > SLIP_TOL_BP:
                    issues.append(_issue("error", b, "units", f"{ev} slippage_bps {f['slippage_bps']:.1f} does not "
                                                              f"recompute ({re_:.1f}) from fill/ref"))
        m = re.search(r"\.(\d{4}-\d{2}-\d{2})\.", c or "")
        if m and m.group(1) != f["td"]:
            issues.append(_issue("warn", b, "trade date", f"{ev} order date {m.group(1)} != trade date {f['td']}"))
        if f.get("leg") in AUCTION_LEGS:
            et = f["et"]
            secs = [(et - et.normalize() - pd.Timedelta(hours=h, minutes=mi)).total_seconds() for h, mi in _auction_time(f)]
            if not any(-5 <= s <= AUCTION_TOL_S for s in secs):
                want = " or ".join(f"{h:02d}:{mi:02d}" for h, mi in _auction_time(f))
                issues.append(_issue("warn", b, "auction window", f"{ev} {f['leg']} {f['side']} filled {et:%H:%M:%S} "
                                                                  f"ET, not the {want} auction"))
        k = (f.get("leg"), f.get("sym"), f.get("side"), f["td"])
        if k in keys and f.get("leg") in AUCTION_LEGS:          # the intraday leg trades a name several times a day
            issues.append(_issue("warn", b, "duplicate fill", f"{ev}: second {k[0]} {k[2]} {k[1]} on {k[3]} "
                                                              f"(first line {keys[k]})"))
        keys[k] = ln
    return issues


def check_decisions(decisions: list[dict], fills: list[dict], book: str) -> list[dict]:
    """Night decision rows (one per pick at 15:40) vs the night buy fills."""
    issues, dec = [], {}
    for i, d in enumerate(decisions, 1):
        k = (d.get("date"), d.get("sym"))
        if k in dec:
            issues.append(_issue("warn", book, "duplicate decision", f"daily-decisions-{book}.jsonl:{i} {k}"))
        dec[k] = (i, d)
    first = min((d.get("date") for d in decisions), default=None)
    for f in fills:
        if f.get("leg") != "night" or f.get("side") != "buy":
            continue
        k = (f["td"], f["sym"])
        if k not in dec:
            if first is None or f["td"] >= first:
                issues.append(_issue("warn", book, "missing decision", f"daily-fills-{book}.jsonl:{f['line']} "
                                                                       f"{f['sym']} {f['td']} has no decision row"))
            else:
                issues.append(_issue("warn", book, "missing decision", f"daily-fills-{book}.jsonl:{f['line']} "
                                                                       f"{f['sym']} {f['td']}: before the decision log starts ({first})"))
            continue
        i, d = dec[k]
        if d.get("qty") is not None and float(d["qty"]) != float(f["qty"]):
            issues.append(_issue("warn", book, "qty mismatch", f"daily-decisions-{book}.jsonl:{i} qty {d['qty']} vs "
                                                                f"daily-fills-{book}.jsonl:{f['line']} {f['sym']} {f['td']} filled {f['qty']:g}"))
    return issues


def raise_on_errors(issues: list[dict], log=print) -> None:
    for i in issues:
        log(f"  [{i['sev'].upper()}] {i['book']} {i['check']}: {i['detail']}")
    errs = [i for i in issues if i["sev"] == "error"]
    if errs:
        raise ReconDataError(f"{len(errs)} data error(s); first: {errs[0]['detail']}")


# ---------------------------------------------------------------- live round trips
def round_trips(fills: list[dict], leg: str) -> tuple[list[dict], list[dict]]:
    """FIFO buy -> sell lots per symbol for one leg. Returns (closed trips, still-open lots)."""
    trips, lots = [], {}
    for f in sorted((f for f in fills if f.get("leg") == leg), key=lambda f: (f["et"], f.get("side") != "buy")):
        if f["side"] == "buy":
            lots.setdefault(f["sym"], []).append(dict(qty=float(f["qty"]), px=float(f["fill_px"]), td=f["td"],
                                                      coid=f.get("coid"), et=f["et"]))
            continue
        q = float(f["qty"])
        while q > 1e-9 and lots.get(f["sym"]):
            lot = lots[f["sym"]][0]
            take = min(q, lot["qty"])
            trips.append(dict(sym=f["sym"], qty=take, entry=lot["td"], exit=f["td"], buy_px=lot["px"],
                              sell_px=float(f["fill_px"]), buy_et=lot["et"], sell_et=f["et"],
                              buy_coid=lot["coid"], sell_coid=f.get("coid")))
            lot["qty"] -= take
            q -= take
            if lot["qty"] <= 1e-9:
                lots[f["sym"]].pop(0)
    return trips, [dict(sym=s, **l) for s, ls in lots.items() for l in ls]


# ---------------------------------------------------------------- the decomposition
def decompose(rule: list[dict], live: list[dict]) -> dict:
    """rule: [{sym, w, bt}] (bt over the rule's holding period); live: [{sym, w, bt_rh, bt_same, ret}] (w = notional;
    bt_rh = prints over the rule's holding period, bt_same = prints over the live holding period, ret = live fills).
    Weights are normalised within each side. Empty side = cash (0). Returns fractions; asserts the parts sum."""
    def norm(xs):
        s = sum(x["w"] for x in xs)
        return [x["w"] / s for x in xs] if s > 0 else []
    wr, wl = norm(rule), norm(live)
    A = sum(w * x["bt"] for w, x in zip(wr, rule))
    ew_r = st.fmean(x["bt"] for x in rule) if rule else 0.0
    ew_l = st.fmean(x["bt_rh"] for x in live) if live else 0.0
    wl_rh = sum(w * x["bt_rh"] for w, x in zip(wl, live))
    wl_same = sum(w * x["bt_same"] for w, x in zip(wl, live))
    C = sum(w * x["ret"] for w, x in zip(wl, live))
    out = dict(A=A, C=C, total=A - C, pick=ew_r - ew_l, sizing=(A - ew_r) - (wl_rh - ew_l),
               timing=wl_rh - wl_same, fill=wl_same - C)
    out["residual"] = out["sizing"] + out["timing"]
    parts = out["pick"] + out["sizing"] + out["timing"] + out["fill"]
    assert abs(parts - out["total"]) <= 1e-12 * max(1.0, abs(out["total"])), f"decomposition does not sum: {out}"
    return out


def jaccard(a, b) -> float | None:
    a, b = set(a), set(b)
    return None if not a | b else len(a & b) / len(a | b)


# ---------------------------------------------------------------- statistics
def tstat(x) -> dict:
    x = [float(v) for v in x if v is not None and math.isfinite(v)]
    n = len(x)
    if not n:
        return dict(n=0, mean=None, median=None, t=None)
    sd = st.stdev(x) if n > 1 else 0.0
    return dict(n=n, mean=st.fmean(x), median=st.median(x), t=st.fmean(x) / (sd / math.sqrt(n)) if n > 1 and sd > 0 else None)


def clustered(values, days) -> dict:
    """Mean and day-clustered t (fills on one day share that day's auctions): SE from signals.clustered_upper_bound."""
    v = [float(x) for x in values]
    if not v:
        return dict(n=0, days=0, mean=None, median=None, t=None)
    m, ub, g = sg.clustered_upper_bound(v, list(days))
    se = (ub - m) / sg.G1_Z if math.isfinite(ub) else float("nan")
    return dict(n=len(v), days=g, mean=m, median=st.median(v), t=m / se if se and math.isfinite(se) and se > 0 else None)


def ex_top(days: list[dict], key: str = "total", k: int = TOP) -> dict:
    """Mean without the k days that push hardest in the direction of the mean; concentrated if that flips the sign or
    removes more than half of it, or if there are fewer than 2k days to judge from."""
    x = sorted(((d[key], d["day"]) for d in days), reverse=True)
    if not x:
        return dict(mean=None, concentrated=None, top=[])
    m = st.fmean(v for v, _ in x)
    order = x if m >= 0 else x[::-1]
    rest = [v for v, _ in order[k:]]
    em = st.fmean(rest) if rest else None
    conc = len(x) < 2 * k or em is None or (em * m <= 0) or abs(em) < 0.5 * abs(m)
    return dict(mean=em, concentrated=bool(conc), top=[(dd, v) for v, dd in order[:k]])


# ---------------------------------------------------------------- backtest rules (pure; data passed in)
def night_rule(rows: pd.DataFrame, elig: pd.DataFrame, d) -> tuple[pd.DataFrame, dict]:
    """The live 15:40 selection on decision-time rows (price/high/low through 15:39) joined to the day's eligibility,
    in the executor's order (_phase_close_night). Returns (picks with weight `w`, {sym: why dropped})."""
    why = {}
    r = rows.join(elig[[c for c in ("prev_close", "vol20", "adv20", "rets", "tow") if c in elig.columns]], how="inner")
    picks = sg.loser_picks(r, day_ret_max=d.night_day_ret_max, ibs_max=d.night_ibs_max,
                           price_min=d.night_price_min, price_max=d.night_price_max)
    quiet = ~(picks["vol20"] >= d.night_vol_min)
    for s in picks.index[quiet]:
        why[s] = f"vol20 {picks.at[s, 'vol20']:.0%} < {d.night_vol_min:.0%}"
    n_quiet = int(quiet.sum())
    picks = picks[~quiet]
    if not picks.empty and "rets" in elig.columns:
        rets = {s: (v if isinstance(v, list) else []) for s, v in elig["rets"].items()}
        picks, dropped = sg.dedupe_correlated(picks, rets, d.night_max_corr)
        for s, k in dropped:
            why[s] = f"duplicate bet of {k}"
    if picks.empty:
        return picks.assign(w=[]), why
    picks, _ = sg.night_sizing(picks, vol_min=d.night_vol_min, crowd_n=d.night_crowd_n,
                               max_name_pct=d.night_max_name_pct, n_raw=len(picks) + n_quiet)
    v20 = picks["vol20"].values
    if d.night_tilt_model == "v2":
        prev = np.array([np.expm1(x[-1]) if isinstance(x, list) and x else np.nan for x in picks.get("rets", [])])
        w = sg.night_tilt_v2(v20, picks["day_ret"].values, prev, d.night_tilt_k)
    else:
        w = sg.night_tilt(v20, picks["day_ret"].values, d.night_tilt_k)
    if d.night_tilt_tow and "tow" in picks:
        w = sg.night_tilt_tow(w, pd.to_numeric(picks["tow"], errors="coerce").values.astype(float), d.night_tilt_k)
    return picks.assign(w=w), why


def night_superset(raw: dict[str, pd.DataFrame], elig: pd.DataFrame, day: pd.Timestamp, day_ret_max: float) -> list[str]:
    """Eligible names whose day low reached prev_close x (1 + day_ret_max). A 15:39 price at or below that level
    implies such a low, so this only prunes names that cannot qualify: the picks are identical to scanning all names."""
    out = []
    for s in elig.index:
        b = raw.get(s)
        if b is not None and day in b.index and float(b.at[day, "low"]) <= float(elig.at[s, "prev_close"]) * (1 + day_ret_max):
            out.append(s)
    return out


def ibs_targets_on(bars: dict[str, pd.DataFrame], day: pd.Timestamp, d) -> list[str]:
    """executor._ibs_open's raw targets for the morning of `day` from bars strictly before it (no guards)."""
    b = {s: x[x.index < day] for s, x in bars.items() if s in d.ibs_symbols and len(x[x.index < day])}
    closes = pd.DataFrame({s: x["close"] for s, x in b.items()})
    universe = sg.momentum_top(closes, day, d.ibs_top_k) if d.ibs_top_k else list(closes.columns)
    return sg.ibs_targets({s: b[s].iloc[-1].to_dict() for s in universe if s in b}, d.ibs_max)


def pref_rule(events: list[dict], X: dict, day: str, nxt: str) -> tuple[list[dict], dict]:
    """PREF-EX picks for a buy at `day`'s close (ex-date `nxt`): pref_ex_live's class/screen/ranking with the price =
    the last closing cross BEFORE `day` and the median cross $ of the LOOKBACK sessions before `day` (both known at
    the 15:25 decision). Returns (picks, {sym: why not picked})."""
    from .pref_ex_live import CLASSES, LOOKBACK, MAX_NAMES, screen_reason
    why, ok = {}, []
    for e in {(e["sym"], e["ex"]): e for e in events}.values():
        if e.get("ex") != nxt or e.get("cls") not in CLASSES or not e.get("div"):
            continue
        p = X.get(e["sym"], {})
        prev = [k for k in sorted(p) if k < day and p[k][2]]
        px = p[prev[-1]][2] if prev else None
        usd = [p[k][2] * (p[k][3] or 0) for k in prev[-LOOKBACK:]]
        r = screen_reason(e, px, float(st.median(usd)) if usd else 0.0)
        if r:
            why[e["sym"]] = r
        else:
            ok.append(dict(e, px=px, yld=float(e["div"]) / px))
    ok.sort(key=lambda e: -e["yld"])
    for e in ok[MAX_NAMES:]:
        why[e["sym"]] = f"rank > {MAX_NAMES} by yield"
    return ok[:MAX_NAMES], why


def cef_rule(rows: list[dict], session: str) -> list[str]:
    """CEF-RV forward entries whose execution session is `session` (exit signals are ignored: unknown at entry)."""
    from .cef_rv_live import FORWARD_FROM, exec_session
    return sorted({r["sym"] for r in rows if r.get("sym") and r.get("signal") and r["signal"] >= FORWARD_FROM
                   and exec_session(r["signal"]).isoformat() == session})


# ---------------------------------------------------------------- prints
def next_print(p: dict, day: str, k: int) -> str | None:
    """First date after `day` with print k (0 = open cross, 2 = close cross) for one symbol."""
    return next((x for x in sorted(p) if x > day and p[x][k]), None)


def px(X: dict, sym: str, day: str | None, k: int) -> float | None:
    v = X.get(sym, {}).get(day) if day else None
    return float(v[k]) if v and v[k] else None


# ---------------------------------------------------------------- per-leg day rows
def _day_row(book, leg, day, rule_syms, live_syms, dec, reasons, n_excl) -> dict:
    j = jaccard(rule_syms, live_syms)
    return dict(kind="day", book=book, leg=leg, day=day, rule=sorted(rule_syms), live=sorted(live_syms),
                jaccard=j, rule_only=sorted(set(rule_syms) - set(live_syms)),
                live_only=sorted(set(live_syms) - set(rule_syms)), reasons=reasons, excluded=n_excl,
                **{k: v * 1e4 for k, v in dec.items()})


def night_days(trips: list[dict], rule_by_day: dict, X: dict, book: str, reasons_by_day: dict) -> tuple[list, list]:
    """Day rows + per-trade rows for the night leg of one book."""
    days, trades = [], []
    by_day: dict = {}
    for t in trips:
        by_day.setdefault(t["entry"], []).append(t)
    for day in sorted(by_day):
        rp = rule_by_day.get(day)
        if rp is None:
            continue
        rule, live, excl = [], [], 0
        for s, w in rp:
            c0, nx = px(X, s, day, 2), next_print(X.get(s, {}), day, 0)
            o1 = px(X, s, nx, 0)
            if c0 and o1:
                rule.append(dict(sym=s, w=w, bt=o1 / c0 - 1))
            else:
                excl += 1
        for t in by_day[day]:
            c0 = px(X, t["sym"], day, 2)
            o_rh = px(X, t["sym"], next_print(X.get(t["sym"], {}), day, 0), 0)
            o_same = px(X, t["sym"], t["exit"], 0)
            if not (c0 and o_rh and o_same):
                excl += 1
                continue
            row = dict(sym=t["sym"], w=t["qty"] * t["buy_px"], bt_rh=o_rh / c0 - 1, bt_same=o_same / c0 - 1,
                       ret=t["sell_px"] / t["buy_px"] - 1)
            live.append(row)
            trades.append(dict(row, book=book, leg="night", day=day, exit=t["exit"],
                               buy_bp=fill_gap_bp("buy", t["buy_px"], c0), sell_bp=fill_gap_bp("sell", t["sell_px"], o_same)))
        dec = decompose(rule, live)
        days.append(_day_row(book, "night", day, [r["sym"] for r in rule], [r["sym"] for r in live], dec,
                             reasons_by_day.get(day, {}), excl))
    return days, trades


def ibs_reason(text: str, sym: str, base_of: dict) -> str | None:
    """Why the live IBS run did not buy a rule target, from its `[ibs] ... -> hold [...]` and `[wash]` lines."""
    m = re.search(r"\[ibs\] IBS last bar: (.*?) -> hold \[([^\]]*)\]", text or "")
    if not m:
        return None
    held = {base_of.get(x, x) for x in re.findall(r"'([^']+)'", m.group(2))}
    vals = dict((a, float(b)) for a, b in re.findall(r"(\S+) ([\d.]+)", m.group(1)))
    if sym in held:
        return "live held it as a target (bought on another day / already held)"
    w = re.search(r"\[wash\][^\n]*skipped \[([^\]]*)\]", text)
    if w and sym in re.findall(r"'([^']+)'", w.group(1)):
        return "wash guard (roth_first skipped it)"
    if sym in vals and vals[sym] >= 0.2:
        return f"data difference: live IBS {vals[sym]:.2f}"
    if re.search(r"\[wash\] roth_first: taxable[^\n]*blocks", text):
        return "wash guard (roth_first: taxable blocks names the Roth held/closed in 31d)"
    return "not bought live, log gives no reason"


def ibs_days(trips: list[dict], targets: dict[str, list[str]], sessions: list[str], X: dict, book: str,
             base_of: dict, texts: dict | None = None) -> tuple[list, list]:
    """IBS: entries per morning. Rule entry = target today, not yesterday; rule exit = first morning not a target."""
    def rule_exit(base: str, day: str) -> str | None:
        for s in sessions:
            if s > day and s in targets and base not in targets[s]:
                return s
        return None
    days, trades = [], []
    by_day: dict = {}
    for t in trips:
        by_day.setdefault(t["entry"], []).append(t)
    for day in sorted(by_day):
        if day not in targets:
            continue
        i = sessions.index(day)
        prev = set(targets.get(sessions[i - 1], [])) if i else set()
        rule, live, excl = [], [], 0
        for s in sorted(set(targets[day]) - prev):
            o0, o1 = px(X, s, day, 0), px(X, s, rule_exit(s, day), 0)
            if o0 and o1:
                rule.append(dict(sym=s, w=1.0, bt=o1 / o0 - 1))
            else:
                excl += 1
        live_syms = []
        for t in by_day[day]:
            base = base_of.get(t["sym"], t["sym"])
            o0, o_same = px(X, t["sym"], day, 0), px(X, t["sym"], t["exit"], 0)
            ex = rule_exit(base, day) if base in targets[day] else t["exit"]
            o_rh = px(X, t["sym"], ex, 0)
            if not (o0 and o_same and o_rh):
                excl += 1
                continue
            row = dict(sym=base, w=t["qty"] * t["buy_px"], bt_rh=o_rh / o0 - 1, bt_same=o_same / o0 - 1,
                       ret=t["sell_px"] / t["buy_px"] - 1)
            live.append(row)
            live_syms.append(base)
            trades.append(dict(row, traded=t["sym"], book=book, leg="ibs", day=day, exit=t["exit"],
                               buy_bp=fill_gap_bp("buy", t["buy_px"], o0), sell_bp=fill_gap_bp("sell", t["sell_px"], o_same)))
        dec = decompose(rule, live)
        reasons = {s: "rule already held it (entered earlier in the rule's path)" for s in set(live_syms) & prev}
        for s in set(r["sym"] for r in rule) - set(live_syms):
            reasons[s] = (f"live held {s} already" if any(t["entry"] < day < t["exit"] and base_of.get(t["sym"], t["sym"]) == s
                                                          for t in trips)
                          else ibs_reason((texts or {}).get(day, ""), s, base_of) or "not bought live (no log)")
        days.append(_day_row(book, "ibs", day, [r["sym"] for r in rule], live_syms, dec, reasons, excl))
    return days, trades


def pref_live_trips(rows: list[dict]) -> list[dict]:
    """PREF-EX live round trips from logs/pref-ex-live.jsonl: buy rows + their scored fills, paired FIFO with scored
    sells that actually filled (rejected SELL_SHORT sells score qty 0 and are skipped)."""
    sc = {r["order_id"]: r for r in rows if r.get("cmd") == "score" and r.get("qty") and r.get("fill")}
    buys = [dict(r, s=sc[r["order_id"]]) for r in rows if r.get("cmd") == "buy" and not r.get("dry_run")
            and r.get("order_id") in sc]
    sells = sorted((r for r in sc.values() if r["side"] == "sell"), key=lambda r: r["day"])
    out = []
    for b in sorted(buys, key=lambda r: r["s"]["day"]):
        s = next((x for x in sells if x["sym"] == b["sym"] and x["day"] > b["s"]["day"] and not x.get("_used")), None)
        if not s:
            continue
        s["_used"] = True
        out.append(dict(sym=b["sym"], qty=float(b["s"]["qty"]), entry=b["s"]["day"], exit=s["day"], ex=b["ex"],
                        div=float(b["div"]), buy_px=float(b["s"]["fill"]), sell_px=float(s["fill"])))
    return out


def pref_days(trips: list[dict], rule_by_day: dict, X: dict, reasons_by_day: dict) -> tuple[list, list]:
    days, trades = [], []
    by_day: dict = {}
    for t in trips:
        by_day.setdefault(t["entry"], []).append(t)
    for day in sorted(by_day):
        rule, live, excl = [], [], 0
        for e in rule_by_day.get(day, []):
            c0, c1 = px(X, e["sym"], day, 2), px(X, e["sym"], e["ex"], 2)
            if c0 and c1:
                rule.append(dict(sym=e["sym"], w=1.0, bt=(c1 + e["div"]) / c0 - 1))
            else:
                excl += 1
        for t in by_day[day]:
            c0, c_rh, c_same = px(X, t["sym"], day, 2), px(X, t["sym"], t["ex"], 2), px(X, t["sym"], t["exit"], 2)
            if not (c0 and c_rh and c_same):
                excl += 1
                continue
            row = dict(sym=t["sym"], w=t["qty"] * t["buy_px"], bt_rh=(c_rh + t["div"]) / c0 - 1,
                       bt_same=(c_same + t["div"]) / c0 - 1, ret=(t["sell_px"] + t["div"]) / t["buy_px"] - 1)
            live.append(row)
            trades.append(dict(row, book="roth", leg="pref", day=day, exit=t["exit"],
                               buy_bp=fill_gap_bp("buy", t["buy_px"], c0), sell_bp=fill_gap_bp("sell", t["sell_px"], c_same)))
        dec = decompose(rule, live)
        days.append(_day_row("roth", "pref", day, [r["sym"] for r in rule], [r["sym"] for r in live], dec,
                             reasons_by_day.get(day, {}), excl))
    return days, trades


# ---------------------------------------------------------------- mismatch reasons (night)
LOG_PATTERNS = (
    (re.compile(r"skip (\S+): \$[\d,.]+ buys 0 shares"), "zero shares (whole-share rounding)"),
    (re.compile(r"skip (\S+): book cash exhausted"), "book cash exhausted"),
    (re.compile(r"  (\S+): impact cap"), "impact cap"),
)


def night_reasons(rule_only, live_only, text: str, cands: set | None, why_rule: dict, sip: dict, dec: dict,
                  wash: set) -> dict:
    """Why each mismatched name differs, from the day's executor log, the night-candidates log (the live rule's own
    15:40 signals), the replay's drop reasons and the live decision row."""
    out = {}
    hits: dict = {}
    for pat, why in LOG_PATTERNS:
        for m in pat.finditer(text or ""):
            hits.setdefault(m.group(1), why)
    for m in re.finditer(r"duplicate bet\(s\) dropped[^:]*: (.*)", text or ""):
        for a, b in re.findall(r"(\S+) ~ (\S+?)(?:,|$)", m.group(1)):
            hits.setdefault(a, f"live dedupe: duplicate of {b}")
    for m in re.finditer(r"previous close disagrees[^\[]*\[([^\]]*)\]", text or ""):
        for s in re.findall(r"'([^']+)'", m.group(1)):
            hits.setdefault(s, "quote refused (prev close disagrees with the feed)")
    m = re.search(r"\[night\] (\d+) names eligible today", text or "")
    tiny = int(m.group(1)) if m and int(m.group(1)) < 1000 else None
    for s in rule_only:
        if s in hits:
            out[s] = hits[s]
        elif tiny is not None:
            out[s] = f"live universe was only {tiny} names that day (asset fetch broken)"
        elif s in wash:
            out[s] = "wash guard / held elsewhere (likely: traded by a real book within 31 days)"
        elif cands is not None and s not in cands:
            out[s] = "data difference: live 15:40 quotes did not flag it"
        elif cands is not None:
            out[s] = "live filter after the signal (vol / dedupe / guard), no log line"
        else:
            out[s] = "undetermined (no candidate log for this day)"
    for s in live_only:
        if s in why_rule:
            out[s] = f"replay dropped it: {why_rule[s]}"
            continue
        v, d = sip.get(s), dec.get(s)
        live_v = f"live {d['day_ret']:+.1%} / ibs {d['ibs']:.2f}" if d else "live values not logged"
        sip_v = (f"SIP 15:39 {v['day_ret']:+.1%} / ibs {v['ibs']:.2f}" if v else "SIP: low never reached the threshold")
        out[s] = f"data difference: {sip_v} vs {live_v}"
    return out


# ---------------------------------------------------------------- summary
def summarize(days: list[dict], trades: list[dict], book: str, leg: str) -> dict:
    tot = tstat([d["total"] for d in days])
    s = dict(kind="summary", book=book, leg=leg, n_days=len(days), n_trades=len(trades),
             pick_match=st.fmean([d["jaccard"] for d in days if d["jaccard"] is not None]) if days else None,
             total=tot, ex_top=ex_top(days) if days else None)
    for k in ("A", "C", "pick", "sizing", "timing", "fill", "residual"):
        s[k] = tstat([d[k] for d in days])
    s["buy_bp"] = clustered([t["buy_bp"] for t in trades], [t["day"] for t in trades])
    s["sell_bp"] = clustered([t["sell_bp"] for t in trades], [t["exit"] for t in trades])
    s["worst"] = [(d["day"], d["total"]) for d in sorted(days, key=lambda d: -d["total"])[:TOP]]
    if days and tot["mean"] is not None:
        # sign check in code: fill term and per-side gaps must agree in sign when both sides agree
        for t in trades:
            ft = t["bt_same"] - t["ret"]
            if t["buy_bp"] > 0.5 and t["sell_bp"] > 0.5:
                assert ft > 0, f"fill term sign inverted for {t}"
            if t["buy_bp"] < -0.5 and t["sell_bp"] < -0.5:
                assert ft < 0, f"fill term sign inverted for {t}"
    return s


def _f(x, nd=1) -> str:
    return "n/a" if x is None else f"{x:+.{nd}f}"


def fmt(s: dict) -> list[str]:
    """Report lines; every label carries its sign convention next to the value."""
    t = s["total"]
    pm = "n/a" if s["pick_match"] is None else f"{s['pick_match']:.0%}"
    head = f"{s['book']:5s} {s['leg']:5s} days {s['n_days']:3d} trades {s['n_trades']:3d}  pick match (Jaccard) {pm}"
    if not s["n_days"]:
        return [head + "  (no reconcilable day)"]
    L = [head,
         f"    backtest A {_f(s['A']['mean'])}bp/day  live C {_f(s['C']['mean'])}bp/day",
         f"    total gap (backtest - live, + = live worse) mean {_f(t['mean'])}bp median {_f(t['median'])}bp "
         f"t {_f(t['t'], 2)} = pick {_f(s['pick']['mean'])} + fill {_f(s['fill']['mean'])} + residual "
         f"{_f(s['residual']['mean'])} (sizing {_f(s['sizing']['mean'])}, timing {_f(s['timing']['mean'])})",
         f"    fill gap per side (+ = live worse): buy {_f(s['buy_bp']['mean'])}bp med {_f(s['buy_bp']['median'])} "
         f"t {_f(s['buy_bp']['t'], 2)} (n {s['buy_bp']['n']}, {s['buy_bp']['days']} days); sell "
         f"{_f(s['sell_bp']['mean'])}bp med {_f(s['sell_bp']['median'])} t {_f(s['sell_bp']['t'], 2)} "
         f"(n {s['sell_bp']['n']}, {s['sell_bp']['days']} days)"]
    e = s["ex_top"]
    L.append(f"    ex-top-{TOP} gap {_f(e['mean'])}bp -> {'CONCENTRATED in < 5 days' if e['concentrated'] else 'not concentrated'}"
             f"; worst days " + ", ".join(f"{d} {_f(v, 0)}" for d, v in s["worst"]))
    return L


def line(rows: list[dict]) -> str:
    """REGISTRY reader: the latest run's per-leg total gap (+ = live worse) and its split."""
    sm = [r for r in rows if r.get("kind") == "summary"]
    if not sm:
        return "no recon run yet (make recon)"
    last = max(r["run"] for r in sm)
    out = []
    for r in sm:
        if r["run"] != last or r["book"] != "all" or not r["n_days"]:
            continue
        t = r["total"]
        out.append(f"{r['leg']} {_f(t['mean'], 0)}bp t {_f(t['t'], 1)} (fill {_f(r['fill']['mean'], 0)}, "
                   f"pick {_f(r['pick']['mean'], 0)}) n {r['n_days']}d")
    return f"{last}: live-minus-backtest gap, + = live worse: " + "; ".join(out) if out else f"{last}: nothing reconcilable"


# ---------------------------------------------------------------- run (network: the server)
def _sessions(start: dt.date, end: dt.date) -> list[str]:
    from .cpc_ledger import is_session
    out, d = [], start
    while d <= end:
        if is_session(d):
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def _crosses(syms, start: str, end: str) -> dict:
    from .exdate_open_shadow import _headers
    from .pref_ex_shadow import crosses
    H, X = _headers(), {}
    syms = sorted(set(syms))
    for i in range(0, len(syms), 40):
        X.update(crosses(syms[i:i + 40], f"{start}T00:00:00Z", end, H))
    return X


def _sip_values(rows: pd.DataFrame, elig: pd.DataFrame) -> dict:
    r = rows.join(elig[["prev_close"]], how="inner")
    out = {}
    for s, x in r.iterrows():
        hi, lo = max(x["high"], x["price"]), min(x["low"], x["price"])
        out[s] = dict(day_ret=x["price"] / x["prev_close"] - 1, ibs=(x["price"] - lo) / (hi - lo) if hi > lo else float("nan"))
    return out


def _wash_set(fills_all: dict, book: str, day: str) -> set:
    """Names a real book traded in the 31 days before `day` (the other book: any trade; this book: a sale)."""
    lo = (dt.date.fromisoformat(day) - dt.timedelta(days=31)).isoformat()
    out = set()
    for b, fs in fills_all.items():
        for f in fs:
            if lo <= f["td"] < day and (b != book or f["side"] == "sell"):
                out.add(f["sym"])
    return out


def night_replay(days: list[str], live_syms: dict, d, log=print) -> tuple[dict, dict, dict]:
    """Rule picks per day on SIP data: {day: [(sym, w)]}, {day: {sym: why dropped}}, {day: {sym: SIP values}}."""
    from . import marketdata as md
    from ..universe import all_assets, valid_symbol
    syms = [s for s in all_assets().symbols if valid_symbol(s)]
    t0 = pd.Timestamp(min(days)) - pd.Timedelta(days=45)
    t1 = pd.Timestamp(max(days)) + pd.Timedelta(days=1)
    log(f"[recon] night replay: SIP daily bars for {len(syms)} symbols, {t0.date()}..{max(days)} (raw + split)")
    raw = md.sip_daily(syms, t0, t1, adjustment="raw")
    spl = md.sip_daily(syms, t0, t1, adjustment="split")
    picks, whys, sipv = {}, {}, {}
    for day in days:
        D = pd.Timestamp(day)
        er = pd.DataFrame(md.eligibility_rows(raw, D, price_min=d.night_price_min, adv_min=d.night_adv_min))
        es = pd.DataFrame(md.eligibility_rows(spl, D, price_min=0.0, adv_min=0.0))
        if er.empty:
            continue
        elig = er.set_index("symbol")[["prev_close", "adv20"]].join(
            es.set_index("symbol")[["vol20", "rets", "tow"]], how="left")
        elig["vol20"] = elig["vol20"].fillna(0.0)
        elig["rets"] = elig["rets"].apply(lambda v: v if isinstance(v, list) else [])
        sup = sorted(set(night_superset(raw, elig, D, d.night_day_ret_max)) | (live_syms.get(day, set()) & set(elig.index)))
        rows = md.rth_minutes(sup, D, until_hm=1539) if sup else pd.DataFrame(columns=["close", "high", "low"])
        rows = rows.rename(columns={"close": "price"})[["price", "high", "low"]] if len(rows) else \
            pd.DataFrame(columns=["price", "high", "low"])
        p, why = night_rule(rows, elig, d)
        picks[day], whys[day], sipv[day] = list(zip(p.index, p["w"])), why, _sip_values(rows, elig)
        log(f"[recon]   {day}: {len(elig)} eligible, {len(sup)} touched the threshold, {len(p)} rule picks")
    return picks, whys, sipv


def run(state_dir: Path, logs_dir: Path, log=print, write: bool = True, cfg=None, night_days_max: int | None = None) -> dict:
    from ..config import Config
    from .signals import WASH_LOOKALIKE
    state_dir, logs_dir = Path(state_dir), Path(logs_dir)
    cfg = cfg or Config.load()
    fills = {b: load_fills(logs_dir, b) for b in BOOKS}
    issues = []
    for b in BOOKS:
        issues += check_fills(fills[b])
        issues += check_decisions(_jsonl(logs_dir / f"daily-decisions-{b}.jsonl"), fills[b], b)
    log(f"[recon] data checks: {sum(i['sev'] == 'error' for i in issues)} error(s), "
        f"{sum(i['sev'] == 'warn' for i in issues)} warning(s)")
    raise_on_errors(issues, log)

    all_f = [f for b in BOOKS for f in fills[b]]
    if not all_f:
        log("[recon] no live fills")
        return {}
    first, last = min(f["td"] for f in all_f), max(f["td"] for f in all_f)
    sessions = _sessions(dt.date.fromisoformat(first) - dt.timedelta(days=40), dt.date.today())
    trips = {(b, leg): round_trips(fills[b], leg)[0] for b in BOOKS for leg in ("night", "ibs")}
    days_all, trades_all = [], []

    # night
    nd = sorted({t["entry"] for b in BOOKS for t in trips[(b, "night")]})[-night_days_max:] if night_days_max else \
        sorted({t["entry"] for b in BOOKS for t in trips[(b, "night")]})
    d_live = cfg.daily.for_account("live")[0]
    live_syms = {}
    for b in BOOKS:
        for t in trips[(b, "night")]:
            live_syms.setdefault(t["entry"], set()).add(t["sym"])
    rpicks, rwhy, rsip = night_replay(nd, live_syms, d_live, log) if nd else ({}, {}, {})
    cands = {}
    for r in _jsonl(state_dir / "night-candidates.jsonl"):
        cands.setdefault(r["date"], set()).add(r["sym"])
    # ibs
    base_of = {v: k for k, v in WASH_LOOKALIKE.items()}
    d_ibs = cfg.daily.for_account("live")[0]
    from . import marketdata as md
    ibs_syms = list(d_ibs.ibs_symbols) + [v for v in WASH_LOOKALIKE.values()]
    ib = md.sip_daily(ibs_syms, pd.Timestamp(first) - pd.Timedelta(days=420), pd.Timestamp(last) + pd.Timedelta(days=10))
    ib_sess = [s for s in sessions if s >= first]
    targets = {s: ibs_targets_on(ib, pd.Timestamp(s), d_ibs) for s in ib_sess}
    # prints for every name either side touches
    syms = {t["sym"] for v in trips.values() for t in v} | {s for v in rpicks.values() for s, _ in v} \
        | {s for v in targets.values() for s in v}
    pref_rows = _jsonl(logs_dir / "pref-ex-live.jsonl")
    ptrips = pref_live_trips(pref_rows)
    events = _jsonl(state_dir / "pref-ex.jsonl")
    p_sess = [s for s in sessions if ptrips and min(t["entry"] for t in ptrips) <= s <= max(t["entry"] for t in ptrips)]
    p_ev = [e for e in events if any(e.get("ex") == _next(s, sessions) for s in p_sess)]
    syms |= {e["sym"] for e in p_ev} | {t["sym"] for t in ptrips}
    log(f"[recon] official auction prints for {len(syms)} symbols")
    # end 20 minutes ago: the data plan refuses SIP newer than 15 minutes (as repeat_shadow does)
    end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    X = _crosses(syms, (dt.date.fromisoformat(first) - dt.timedelta(days=30)).isoformat(), end)

    for b in BOOKS:
        rb = {}
        for day in {t["entry"] for t in trips[(b, "night")]}:
            if day not in rpicks:
                continue
            rule_s = {s for s, _ in rpicks[day]}
            live_s = {t["sym"] for t in trips[(b, "night")] if t["entry"] == day}
            txt = (logs_dir / f"daily-{b}-{day}.log")
            dec = {d["sym"]: d for d in _jsonl(logs_dir / f"daily-decisions-{b}.jsonl") if d.get("date") == day}
            rb[day] = night_reasons(rule_s - live_s, live_s - rule_s, txt.read_text() if txt.exists() else "",
                                    cands.get(day) if day >= min(cands, default="9999") else None, rwhy.get(day, {}),
                                    rsip.get(day, {}), dec, _wash_set(fills, b, day))
        dn, tn = night_days(trips[(b, "night")], rpicks, X, b, rb)
        texts = {}
        for day in {t["entry"] for t in trips[(b, "ibs")]}:
            fp = logs_dir / f"daily-{b}-{day}.log"
            texts[day] = fp.read_text() if fp.exists() else ""
        di, ti = ibs_days(trips[(b, "ibs")], targets, ib_sess, X, b, base_of, texts)
        days_all += dn + di
        trades_all += tn + ti
    # pref (Roth only)
    p_rule, p_why = {}, {}
    for s in p_sess:
        p_rule[s], p_why[s] = pref_rule(p_ev, X, s, _next(s, sessions))
    skips = {}
    for r in pref_rows:
        if r.get("cmd") == "buy-skip":
            skips.setdefault(r["ts"][:10], {})[r["sym"]] = f"live skip: {r.get('reason')}"
    reasons = {s: {**p_why.get(s, {}), **skips.get(s, {})} for s in p_sess}
    dp, tp = pref_days(ptrips, p_rule, X, reasons)
    days_all += dp
    trades_all += tp

    # summaries
    sums = []
    for leg in ("night", "ibs", "pref"):
        for b in BOOKS + ("all",):
            dd = [d for d in days_all if d["leg"] == leg and (b == "all" or d["book"] == b)]
            tt = [t for t in trades_all if t["leg"] == leg and (b == "all" or t["book"] == b)]
            if b == "all":
                # pooled over books: one row per calendar day (average the books' gaps that day)
                byd: dict = {}
                for d in dd:
                    byd.setdefault(d["day"], []).append(d)
                dd = [dict(g[0], book="all", **{k: st.fmean(x[k] for x in g) for k in
                                                ("A", "C", "total", "pick", "sizing", "timing", "fill", "residual")},
                           jaccard=st.fmean([x["jaccard"] for x in g if x["jaccard"] is not None] or [0.0]))
                      for g in byd.values()]
            if leg == "pref" and b == "live":
                continue
            sums.append(summarize(dd, tt, b, leg))
    cef = cef_section(state_dir, logs_dir, sessions)
    run_d = dt.date.today().isoformat()
    log("\n== Live vs backtest, per leg (gaps are backtest - live: + = LIVE WORSE) ==")
    for s in sums:
        for ln in fmt(s):
            log(ln)
    log(cef["line"])
    log("\n== Mismatched names (rule-only / live-only) with reasons ==")
    for d in sorted(days_all, key=lambda d: (d["leg"], d["book"], d["day"])):
        if d["rule_only"] or d["live_only"]:
            log(f"  {d['leg']:5s} {d['book']:4s} {d['day']} J {d['jaccard'] if d['jaccard'] is None else round(d['jaccard'], 2)}: "
                + "; ".join(f"{s} {'rule-only' if s in d['rule_only'] else 'live-only'}: {d['reasons'].get(s, '?')}"
                            for s in d["rule_only"] + d["live_only"]))
    out = dict(days=days_all, trades=trades_all, summaries=sums, issues=issues, cef=cef)
    if write:
        p = state_dir / LOG_NAME
        keep = [r for r in _jsonl(p) if r.get("run") != run_d]
        new = [dict(r, run=run_d) for r in days_all + sums]
        p.write_text("".join(json.dumps(r, default=str) + "\n" for r in keep + new))
        log(f"[recon] wrote {len(new)} rows to {p}")
    return out


def _next(day: str, sessions: list[str]) -> str | None:
    return next((s for s in sessions if s > day), None)


def cef_section(state_dir: Path, logs_dir: Path, sessions: list[str]) -> dict:
    """CEF-RV: rule entries per execution session vs live buys, with the live log's reason; fill gap from score rows."""
    rows = _jsonl(state_dir / "cef-rv.jsonl")
    lr = _jsonl(logs_dir / "cef-rv-live.jsonl")
    live = [r for r in lr if r.get("mode") == "live"]
    buys = {}
    for r in live:
        if r.get("cmd") == "buy" and r.get("order_id"):
            buys.setdefault(r["ts"][:10], set()).add(r["sym"])
    why = {}     # (sym, session) -> reason; a buy-skip / buy-rejected logged on the session beats a later "missed" row
    for r in live:
        if r.get("cmd") in ("missed", "buy-skip", "buy-rejected"):
            k = (r["sym"], r.get("session") if r["cmd"] == "missed" else r["ts"][:10])
            if r["cmd"] != "missed" or k not in why:
                why[k] = f"{r['cmd']}: {r.get('reason', '')}".strip(": ")
    start = min((r["ts"][:10] for r in live), default=None)
    rule_n = live_n = both = 0
    miss = {}
    for s in sessions:
        if start is None or s < start or s > dt.date.today().isoformat():
            continue
        rs, ls = set(cef_rule(rows, s)), buys.get(s, set())
        rule_n, live_n, both = rule_n + len(rs), live_n + len(ls), both + len(rs & ls)
        for x in rs - ls:
            k = why.get((x, s), "no live row")
            miss[k.split(":")[0]] = miss.get(k.split(":")[0], 0) + 1
    sc = [r for r in live if r.get("cmd") == "score" and r.get("diff_bp") is not None]
    gaps = [fill_gap_bp(r["side"], r["fill"], r["open_cross"]) for r in sc if r.get("open_cross")]
    closed = sum(1 for r in sc if r["side"] == "sell")
    ln = (f"roth  cef   rule entries {rule_n}, live buys {live_n}, both {both} (entry match "
          f"{both / rule_n:.0%})" if rule_n else "roth  cef   no rule entries in the live window")
    ln += (f"; misses by reason {miss}; fill gap vs opening cross (+ = live worse) "
           f"{_f(st.fmean(gaps) if gaps else None)}bp over {len(gaps)} fills; {closed} closed round trips "
           f"(no return gap until one closes)")
    return dict(rule=rule_n, live=live_n, both=both, miss=miss, gaps=gaps, closed=closed, line=ln)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="print only, write nothing to state/")
    a = ap.parse_args(argv)
    run(ROOT / "state", ROOT / "logs", write=not a.print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
