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


def events(today: dt.date, H: dict) -> list[dict]:
    """Preferred cash dividends (symbol 'XXX.PRY') with process date in [today-60, today+90]."""
    out, tok = [], None
    while True:
        q = {"types": "cash_dividend", "start": str(today - dt.timedelta(days=60)),
             "end": str(today + dt.timedelta(days=90)), "limit": 1000}
        if tok:
            q["page_token"] = tok
        j = _get(CA_URL, q, H)
        for x in (j.get("corporate_actions") or {}).get("cash_dividends", []):
            s = x.get("symbol", "")
            if ".PR" in s and not x.get("special") and not x.get("foreign") and (x.get("rate") or 0) > 0:
                out.append(dict(sym=s, ex=x["ex_date"], div=float(x["rate"])))
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


def summary(rows: list[dict]) -> dict:
    out = {}
    for tag, fwd in (("forward", True), ("backfill", False)):
        x = [r for r in rows if r.get("status") == "scored" and r.get("eligible") and "net_co" in r
             and (r["ex"] >= FORWARD_FROM) == fwd]
        out[tag] = {k: _stats(x, k) for k in ("co", "net_co", "cc", "net_cc")}
        out[tag]["order_usd_per_night"] = (sum(r["order_usd"] for r in x) / len({r["ex"] for r in x})) if x else None
        parts = [r["part_close"] for r in x if r.get("part_close") is not None]
        out[tag]["median_part_close"] = st.median(parts) if parts else None
    out["upcoming"] = sorted({(r["ex"], r["sym"]) for r in rows if r.get("status") == "upcoming"})
    return out


def line(rows: list[dict]) -> str:
    s = summary(rows)
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
    todo = [e for e in evs if old.get((e["sym"], e["ex"]), {}).get("status") not in ("scored", "mismatch", "no_cross")]
    printed = [e for e in todo if e["ex"] < str(today)]          # E's closing cross must have printed
    X: dict = {}
    if printed:
        syms = sorted({e["sym"] for e in printed})
        start = str(dt.date.fromisoformat(min(e["ex"] for e in printed)) - dt.timedelta(days=40))
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(0, len(syms), 40):
            X.update(crosses(syms[i:i + 40], start, end, H))
    for e in todo:
        r = score(e, X) if e["ex"] < str(today) else None
        if r is None:
            stale = e["ex"] <= str(today - dt.timedelta(days=5))
            r = dict(e, status="upcoming" if e["ex"] >= str(today) else ("no_cross" if stale else "pending"))
        r["logged"] = str(today)
        old[(e["sym"], e["ex"])] = r
    rows = sorted(old.values(), key=lambda r: (r["ex"], r["sym"]))
    execution(rows)
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[pref-ex] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
