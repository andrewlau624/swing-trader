"""Preferred ex-dividend shadow (PREF-EX, clean-slate loop 2026-10-06): logs, never orders.

Rule (round1_prose.md "Study PREF-EX"; research/sim/pref_exec_out.txt): buy a $25-par preferred's official closing cross
on the session before its cash-dividend ex-date E, collect the dividend, and sell either at E's opening cross (CO) or at
E's closing cross (CC: MOC on both legs, the form Schwab can place -- it has no market-on-open). Official 2021-26:
CO +38bp mean / +35 median, CC +28 / +26; edge survives ~25bp (CO) / ~15bp (CC) round-trip degradation.

Execution model logged per event (Roth, no leverage): ACCT split equally across the night's eligible events, each order
capped at PART of the name's trailing-20-session median closing-cross $, whole shares; participation = order $ / that
day's actual cross $ per leg; modeled slippage = COST round trip + impact (half the quoted spread is unknown here, so the
research model's 10bp-per-leg cap at PART=5% is used: sqrt(p/1%)/10 x HALF_SPR per leg). net_* = gross - slippage.
Broker eligibility (Schwab MOC on preferred symbols, open-auction fill of an AUTO-routed open sell) is NOT verifiable
from data: logged as "unverified" until a live test order sets it.

Each run: pull Alpaca cash dividends (process-date window), keep ".PR" symbols with ex-date >= BACKFILL, log upcoming
events, score every event whose E session has printed. Rows with E < FORWARD_FROM are backfill, shown separately.
Gate: NEED forward ex-nights with >= 1 eligible event. Pass = night-mean net CO >= +20bp, median event > 0 and t >= 2;
kill = night-mean net CO <= +5bp. CC is reported alongside.

ETDX (round1_prose.md "Study ETDX", 2026-10-06): the same rule on $25-par exchange-traded debt (baby bonds, plain symbols
listed in etd_symbols.txt; CEF preferreds are ".PR" and already in the preferred set). Official 2021-26 CO +44bp, CC
+39bp. Logged in the same file with cls="etd" and gated separately with the same thresholds; the preferred gate counts
preferreds only. Both classes share the account on a night (the combined book).

PREF-CHAIN arm (window-signal loop 2026-10-07, research/drafts/window_signals_loop_2026-10-07.md): buy the closing
cross 10 sessions before E instead of E-1, same exit (E's closing cross), dividend included. Research: 2016-26 +68bp
excess vs the EW preferred universe, 2005-15 +57bp gross (every year > 0) but +17bp net of 40bp RT -> failed its net
bar; it is logged to MEASURE it forward, not because it passed. Forward comparator: PFF over the same closes (ch_x,
and cc_x for the T-1 arm on the same footing). Only events whose 3 prior payouts exist and agree within 2% (and the
current one is within 10% of their median) count ("stable"), as in the research rule.

Measured execution cost (the number three loop findings wait on): for every scored eligible event the last SIP quote
in 15:55-16:00 ET is pulled for each closing-cross leg (T-10 entry, E-1 entry, E exit). cost_buy_* = cross / mid - 1,
cost_sell_* = 1 - cross / mid (+ = worse than mid), hs_* = quoted half-spread. These replace the slip_* MODEL for the
chain and CC reads (the model stays in the file for the original gate).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics as st
from pathlib import Path

from .exdate_open_shadow import CA_URL, _get, _headers

LOG_NAME = "pref-ex.jsonl"
BACKFILL = "2026-09-01"
FORWARD_FROM = "2026-10-07"
NEED = 60
ACCT = 10_000.0
PART = 0.05
COST = 0.0010                         # round trip, both forms
HALF_SPR = {"close": 0.00192, "open": 0.00441}   # median quoted half-spreads (research/sim/pref_quotes.py, n 296)
MIN_PX, MAX_PX = 10.0, 60.0
MIN_YLD, MAX_YLD = 0.002, 0.04
MIN_CROSS = 1_400.0                   # = research screen 20d median $vol >= $100k x 0.014 (cross $ / daily $vol)
AU_URL = "https://data.alpaca.markets/v2/stocks/auctions"
QURL = "https://data.alpaca.markets/v2/stocks/quotes"
BENCH = "PFF"
CHAIN_N = 10                          # sessions before E for the PREF-CHAIN entry
ETD = frozenset(ln.strip() for ln in (Path(__file__).with_name("etd_symbols.txt")).read_text().splitlines()
                if ln.strip() and not ln.startswith("#"))


def _cls(sym: str) -> str:
    return "pref" if ".PR" in sym else "etd"


def events(today: dt.date, H: dict) -> list[dict]:
    """Preferred ('XXX.PRY') and baby-bond (ETD list) cash dividends with process date in [today-60, today+90]."""
    out, tok = [], None
    while True:
        q = {"types": "cash_dividend", "start": str(today - dt.timedelta(days=60)),
             "end": str(today + dt.timedelta(days=90)), "limit": 1000}
        if tok:
            q["page_token"] = tok
        j = _get(CA_URL, q, H)
        for x in (j.get("corporate_actions") or {}).get("cash_dividends", []):
            s = x.get("symbol", "")
            if (".PR" in s or s in ETD) and not x.get("special") and not x.get("foreign") and (x.get("rate") or 0) > 0:
                out.append(dict(sym=s, ex=x["ex_date"], div=float(x["rate"]), cls=_cls(s)))
        tok = j.get("next_page_token")
        if not tok:
            return list({(e["sym"], e["ex"]): e for e in out}.values())


def crosses(syms: list[str], start: str, end: str, H: dict) -> dict[str, dict[str, tuple]]:
    """sym -> date -> (open px, open size, close px, close size); largest-size print per auction = the cross."""
    out: dict[str, dict[str, tuple]] = {}
    tok = None
    while True:
        q = {"symbols": ",".join(syms), "start": start, "end": end, "feed": "sip", "limit": 10000}
        if tok:
            q["page_token"] = tok
        j = _get(AU_URL, q, H)
        for s, rows in (j.get("auctions") or {}).items():
            for x in rows:
                o = max(x["o"], key=lambda p: p.get("s", 0)) if x.get("o") else None
                c = max(x["c"], key=lambda p: p.get("s", 0)) if x.get("c") else None
                out.setdefault(s, {})[x["d"]] = (o["p"] if o else None, o["s"] if o else None,
                                                   c["p"] if c else None, c["s"] if c else None)
        tok = j.get("next_page_token")
        if not tok:
            return out


def dividends(syms: list[str], start: str, end: str, H: dict) -> dict[str, list[tuple[str, float]]]:
    """sym -> [(ex_date, cash rate)] from Alpaca corporate actions (non-foreign cash dividends)."""
    out: dict[str, list[tuple[str, float]]] = {}
    for i in range(0, len(syms), 50):
        tok = None
        while True:
            q = {"types": "cash_dividend", "symbols": ",".join(syms[i:i + 50]), "start": start, "end": end,
                 "limit": 1000}
            if tok:
                q["page_token"] = tok
            j = _get(CA_URL, q, H)
            for x in (j.get("corporate_actions") or {}).get("cash_dividends", []):
                if (x.get("rate") or 0) > 0 and not x.get("foreign"):
                    out.setdefault(x["symbol"], []).append((x["ex_date"], float(x["rate"])))
            tok = j.get("next_page_token")
            if not tok:
                break
    return out


def close_quotes(syms: list[str], day: str, H: dict) -> dict[str, tuple[float, float]]:
    """sym -> (bid, ask) of the last valid SIP quote in 15:55-16:00 ET on `day`: the book the closing cross met."""
    from zoneinfo import ZoneInfo
    a = dt.datetime.fromisoformat(f"{day}T15:55:00").replace(tzinfo=ZoneInfo("America/New_York")).astimezone(dt.timezone.utc)
    b = a + dt.timedelta(minutes=5)
    out: dict[str, tuple[float, float]] = {}
    for i in range(0, len(syms), 50):
        tok = None
        while True:
            q = {"symbols": ",".join(syms[i:i + 50]), "start": a.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "end": b.strftime("%Y-%m-%dT%H:%M:%SZ"), "feed": "sip", "limit": 10000}
            if tok:
                q["page_token"] = tok
            j = _get(QURL, q, H)
            for sym, rows in (j.get("quotes") or {}).items():
                for x in rows:                                    # ascending in time: the last valid quote wins
                    if (x.get("bp") or 0) > 0 and (x.get("ap") or 0) > x["bp"]:
                        out[sym] = (float(x["bp"]), float(x["ap"]))
            tok = j.get("next_page_token")
            if not tok:
                break
    return out


def stable(hist: list[tuple[str, float]], ex: str, div: float) -> bool | None:
    """The research rule's payout filter: 3 prior payouts exist, agree within 2%, current within 10% of their median.
    None when fewer than 3 priors are known (history too short to say)."""
    prior = [r for e, r in sorted(hist) if e < ex][-3:]
    if len(prior) < 3:
        return None
    return max(prior) / min(prior) - 1 <= 0.02 and abs(div / st.median(prior) - 1) <= 0.10


def _divsum(divs: dict, sym: str, a: str, b: str) -> float:
    return sum(r for e, r in divs.get(sym, []) if a < e <= b)


def chain(r: dict, p: dict, bench: dict, bdivs: dict) -> dict:
    """PREF-CHAIN fields for one scored row: T-10 closing cross -> E closing cross (+ dividend), and the same window
    (and the T-1 window) for the PFF comparator. Empty when fewer than CHAIN_N prior closing crosses exist."""
    prev = [d for d in sorted(p) if d < r["ex"] and p[d][2]]
    if len(prev) < CHAIN_N:
        return {}
    t10 = prev[-CHAIN_N]
    c10 = p[t10][2]
    out = dict(t10=t10, t10_px=c10, ch=(r["exit_close_px"] + r["div"]) / c10 - 1, pre=r["close_px"] / c10 - 1)
    a, b, c = bench.get(t10), bench.get(r["d0"]), bench.get(r["ex"])
    if a and b and c and a[2] and b[2] and c[2]:
        out["ch_bench"] = (c[2] + _divsum(bdivs, BENCH, t10, r["ex"])) / a[2] - 1
        out["cc_bench"] = (c[2] + _divsum(bdivs, BENCH, r["d0"], r["ex"])) / b[2] - 1
        out["ch_x"] = out["ch"] - out["ch_bench"]
        out["cc_x"] = r["cc"] - out["cc_bench"]
    return out


def costs(r: dict, Q: dict) -> dict:
    """Measured cross-vs-mid cost per closing-cross leg from Q[(sym, day)] = (bid, ask)."""
    out = {}
    for leg, day, px, side in (("t10", r.get("t10"), r.get("t10_px"), "buy"), ("d0", r["d0"], r["close_px"], "buy"),
                               ("E", r["ex"], r["exit_close_px"], "sell")):
        q = Q.get((r["sym"], day)) if day else None
        if not q or not px:
            continue
        mid = (q[0] + q[1]) / 2
        out[f"hs_{leg}"] = (q[1] - q[0]) / 2 / mid
        out[f"cost_{side}_{leg}"] = px / mid - 1 if side == "buy" else 1 - px / mid
    return out


def score(ev: dict, X: dict) -> dict | None:
    """Gross CO / CC of close cross E-1 -> E (+ dividend); None until E's closing cross has printed."""
    p = X.get(ev["sym"], {})
    e = p.get(ev["ex"])
    if not e or not e[0] or not e[2]:
        return None
    prev = [d for d in sorted(p) if d < ev["ex"] and p[d][2]]
    if not prev:
        return None
    d0 = prev[-1]
    c0, cs0 = p[d0][2], p[d0][3] or 0
    hist = [p[d][2] * (p[d][3] or 0) for d in prev[-21:-1]]   # 20 sessions before d0 (ex-ante size)
    med_cross = st.median(hist) if hist else 0.0
    o1, os1, c1, cs1 = e
    co = (o1 + ev["div"]) / c0 - 1
    cc = (c1 + ev["div"]) / c0 - 1
    if abs(co) > 0.25 or abs(cc) > 0.25:                       # tape and dividend record disagree
        return dict(ev, status="mismatch", co=co, cc=cc)
    yld = ev["div"] / c0
    return dict(ev, status="scored", d0=d0, close_px=c0, close_usd=c0 * cs0, open_px=o1, open_usd=o1 * (os1 or 0),
                exit_close_px=c1, exit_close_usd=c1 * (cs1 or 0), med_cross_usd=med_cross, yld=yld, co=co, cc=cc,
                eligible=(MIN_PX <= c0 <= MAX_PX and MIN_YLD <= yld <= MAX_YLD and med_cross >= MIN_CROSS))


def execution(rows: list[dict], acct: float = ACCT, part: float = PART) -> None:
    """Fill in intended order $, participation per leg, modeled slippage and net CO / CC for each scored eligible row."""
    imp = min(math.sqrt(part / 0.01) / 10, 1.0)
    by_night: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("status") == "scored" and r.get("eligible"):
            by_night.setdefault(r["ex"], []).append(r)
    for night in by_night.values():
        rem = acct
        for k, r in enumerate(sorted(night, key=lambda r: r["med_cross_usd"])):
            want = min(part * r["med_cross_usd"], rem / (len(night) - k))
            sh = math.floor(want / r["close_px"])
            r["order_usd"] = sh * r["close_px"]
            rem -= r["order_usd"]
            r["part_close"] = r["order_usd"] / r["close_usd"] if r["close_usd"] else None
            r["part_open"] = r["order_usd"] / r["open_usd"] if r["open_usd"] else None
            r["part_exit_close"] = r["order_usd"] / r["exit_close_usd"] if r["exit_close_usd"] else None
            r["slip_co"] = COST + imp * (HALF_SPR["close"] + HALF_SPR["open"])
            r["slip_cc"] = COST + imp * 2 * HALF_SPR["close"]
            r["net_co"] = r["co"] - r["slip_co"]
            r["net_cc"] = r["cc"] - r["slip_cc"]
            r["broker"] = "unverified"


def _stats(rows: list[dict], key: str) -> dict:
    nights: dict[str, list[float]] = {}
    for r in rows:
        nights.setdefault(r["ex"], []).append(r[key])
    nm = [st.mean(v) for v in nights.values()]
    ev = [r[key] for r in rows]
    t = st.mean(nm) / st.stdev(nm) * math.sqrt(len(nm)) if len(nm) > 2 and st.stdev(nm) > 0 else None
    return dict(nights=len(nm), n=len(ev), night_mean_bp=st.mean(nm) * 1e4 if nm else None,
                median_bp=st.median(ev) * 1e4 if ev else None, hit=sum(v > 0 for v in ev) / len(ev) if ev else None,
                t=t)


def summary(rows: list[dict], cls: str = "pref") -> dict:
    out = {}
    rows = [r for r in rows if _cls(r["sym"]) == cls]
    for tag, fwd in (("forward", True), ("backfill", False)):
        x = [r for r in rows if r.get("status") == "scored" and r.get("eligible") and "net_co" in r
             and (r["ex"] >= FORWARD_FROM) == fwd]
        out[tag] = {k: _stats(x, k) for k in ("co", "net_co", "cc", "net_cc")}
        out[tag]["order_usd_per_night"] = (sum(r["order_usd"] for r in x) / len({r["ex"] for r in x})) if x else None
        parts = [r["part_close"] for r in x if r.get("part_close") is not None]
        out[tag]["median_part_close"] = st.median(parts) if parts else None
    out["upcoming"] = sorted({(r["ex"], r["sym"]) for r in rows if r.get("status") == "upcoming"})
    out["chain"] = chain_summary(rows)
    return out


def chain_summary(rows: list[dict], fwd: bool | None = None) -> dict:
    """PREF-CHAIN vs the T-1 (CC) arm on the same stable events, both vs PFF, gross and net of MEASURED cross cost.
    fwd=True / False keeps forward (ex >= FORWARD_FROM) / backfill events only; None keeps both."""
    x = [r for r in rows if r.get("status") == "scored" and r.get("eligible") and r.get("stable")
         and "ch_x" in r and "cc_x" in r and (fwd is None or (r["ex"] >= FORWARD_FROM) == fwd)]
    out = dict(n=len(x), nights=len({r["ex"] for r in x}))
    if not x:
        return out
    out["ch_x"] = _stats(x, "ch_x")
    out["cc_x"] = _stats(x, "cc_x")
    d = [dict(ex=r["ex"], v=r["ch_x"] - r["cc_x"]) for r in x]
    out["diff"] = _stats(d, "v")
    m = [dict(r, ch_x_net=r["ch_x"] - r["cost_buy_t10"] - r["cost_sell_E"],
              cc_x_net=r["cc_x"] - r["cost_buy_d0"] - r["cost_sell_E"])
         for r in x if "cost_buy_t10" in r and "cost_buy_d0" in r and "cost_sell_E" in r]
    if m:
        out["measured"] = dict(n=len(m), ch_x_net=_stats(m, "ch_x_net"), cc_x_net=_stats(m, "cc_x_net"),
                               diff_net=_stats([dict(ex=r["ex"], v=r["ch_x_net"] - r["cc_x_net"]) for r in m], "v"))
    legs = {k: [r[k] for r in rows if r.get("status") == "scored" and r.get("eligible") and k in r]
            for k in ("cost_buy_t10", "cost_buy_d0", "cost_sell_E", "hs_d0", "hs_E")}
    out["cost_legs"] = {k: (len(v), st.median(v) * 1e4) for k, v in legs.items() if v}
    return out


def chain_verdict(rows: list[dict]) -> str:
    """Frozen PREF-CHAIN gate (2026-10-08), forward events only, net of MEASURED cross cost, read at NEED ex-nights:
    PASS = T-10 night-mean >= +20bp vs PFF, t >= 2, and T-10 minus T-1 night-mean > 0; KILL = T-10 <= +5bp or the
    difference <= 0; else HOLD. '' until NEED forward nights have measured costs."""
    m = chain_summary(rows, fwd=True).get("measured")
    if not m or m["ch_x_net"]["nights"] < NEED:
        return ""
    ch, d = m["ch_x_net"], m["diff_net"]
    if ch["night_mean_bp"] >= 20 and (ch["t"] or 0) >= 2 and d["night_mean_bp"] > 0:
        return " -> CHAIN PASS (>= +20bp vs PFF net of measured cost, t >= 2, beats T-1)"
    if ch["night_mean_bp"] <= 5 or d["night_mean_bp"] <= 0:
        return " -> CHAIN KILL (<= +5bp, or no better than T-1)"
    return " -> CHAIN HOLD"


def chain_line(rows: list[dict]) -> str:
    f = chain_summary(rows, fwd=True)
    fm = f.get("measured")
    head = (f"CHAIN forward {fm['ch_x_net']['nights']}/{NEED} nights: T-10 net {fm['ch_x_net']['night_mean_bp']:+.0f}bp vs "
            f"T-1 net {fm['cc_x_net']['night_mean_bp']:+.0f}bp{chain_verdict(rows)} | " if fm
            else f"CHAIN forward 0/{NEED} nights | ")
    c = chain_summary(rows, fwd=False)
    if not c["n"]:
        return head + "backfill: no stable events with PFF"
    s = head + (f"backfill {c['n']} stable events/{c['nights']} nights, excess vs PFF: T-10 "
         f"{c['ch_x']['night_mean_bp']:+.0f}bp (median {c['ch_x']['median_bp']:+.0f}) vs T-1 "
         f"{c['cc_x']['night_mean_bp']:+.0f}bp; difference {c['diff']['night_mean_bp']:+.0f}bp (t "
         f"{c['diff']['t'] if c['diff']['t'] is None else round(c['diff']['t'], 2)})")
    if "measured" in c:
        mm = c["measured"]
        s += (f"; net of MEASURED cross cost (n {mm['n']}): T-10 {mm['ch_x_net']['night_mean_bp']:+.0f}bp vs T-1 "
              f"{mm['cc_x_net']['night_mean_bp']:+.0f}bp")
    if c.get("cost_legs"):
        s += "; cross vs mid (median bp, + = worse): " + ", ".join(f"{k} {v:+.1f} (n {n})"
                                                                 for k, (n, v) in c["cost_legs"].items())
    return s


def line(rows: list[dict], cls: str = "pref") -> str:
    s = summary(rows, cls)
    parts = []
    for tag in ("forward", "backfill"):
        v = s[tag]
        if not v["co"]["n"]:
            parts.append(f"{tag} 0 events")
            continue
        parts.append(f"{tag} {v['co']['nights']} nights/{v['co']['n']} events: net CO night-mean "
                     f"{v['net_co']['night_mean_bp']:+.0f}bp (gross {v['co']['night_mean_bp']:+.0f}, median "
                     f"{v['co']['median_bp']:+.0f}, hit {v['co']['hit']*100:.0f}%), net CC {v['net_cc']['night_mean_bp']:+.0f}bp, "
                     f"${v['order_usd_per_night']:,.0f}/night at ${ACCT:,.0f}, median close participation "
                     f"{(v['median_part_close'] or 0)*100:.1f}%")
    nxt = ", ".join(f"{s_} {e}" for e, s_ in s["upcoming"][:5])
    verdict = ""
    f = s["forward"]["net_co"]
    if f["nights"] >= NEED:
        verdict = (" -> PASS (net >= 20bp, median > 0, t >= 2)" if f["night_mean_bp"] >= 20 and f["median_bp"] > 0
                   and (f["t"] or 0) >= 2 else " -> KILL (net <= 5bp)" if f["night_mean_bp"] <= 5 else " -> HOLD")
    return "; ".join(parts) + (f"; next: {nxt}" if nxt else "") + verdict


def lines(rows: list[dict]) -> str:
    return f"{line(rows)} | ETDX: {line(rows, 'etd')} | {chain_line(rows)}"


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None) -> dict:
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    H = H or _headers()
    today = today or dt.date.today()
    old = {}
    if path.exists():
        for ln in path.read_text().splitlines():
            try:
                r = json.loads(ln)
                old[(r["sym"], r["ex"])] = r
            except (ValueError, KeyError):
                continue
    evs = [e for e in events(today, H) if BACKFILL <= e["ex"] <= str(today + dt.timedelta(days=14))]
    def _done(o: dict) -> bool:
        st_ = o.get("status")
        return st_ in ("mismatch", "no_cross") or (st_ == "scored" and "chain_v" in o)
    todo = [e for e in evs if not _done(old.get((e["sym"], e["ex"]), {}))]
    printed = [e for e in todo if e["ex"] < str(today)]          # E's closing cross must have printed
    X: dict = {}
    if printed:
        syms = sorted({e["sym"] for e in printed})
        start = str(dt.date.fromisoformat(min(e["ex"] for e in printed)) - dt.timedelta(days=40))
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(0, len(syms), 40):
            X.update(crosses(syms[i:i + 40], start, end, H))
        X.update(crosses([BENCH], start, end, H))
        hist = dividends(syms + [BENCH], str(dt.date.fromisoformat(start) - dt.timedelta(days=400)), str(today), H)
    scored: list[dict] = []
    for e in todo:
        r = score(e, X) if e["ex"] < str(today) else None
        if r is not None and r.get("status") == "scored":
            r.update(chain(r, X.get(e["sym"], {}), X.get(BENCH, {}), hist))
            r["stable"] = stable(hist.get(e["sym"], []), e["ex"], e["div"])
            r["chain_v"] = 1
            scored.append(r)
        if r is None:
            stale = e["ex"] <= str(today - dt.timedelta(days=5))
            r = dict(e, status="upcoming" if e["ex"] >= str(today) else ("no_cross" if stale else "pending"))
        r["logged"] = str(today)
        old[(e["sym"], e["ex"])] = r
    legs: dict[str, set[str]] = {}
    for r in scored:
        if r.get("eligible"):
            for day in (r.get("t10"), r["d0"], r["ex"]):
                if day:
                    legs.setdefault(day, set()).add(r["sym"])
    Q: dict = {}
    for day, ss in legs.items():
        for sym, q in close_quotes(sorted(ss), day, H).items():
            Q[(sym, day)] = q
    for r in scored:
        if r.get("eligible"):
            r.update(costs(r, Q))
    rows = sorted(old.values(), key=lambda r: (r["ex"], r["sym"]))
    execution(rows)
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[pref-ex] {lines(rows)}")
    return summary(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
