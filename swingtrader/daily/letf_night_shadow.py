"""LETF-NIGHT forward shadow (round1_prose.md "Amendment -- Study LETF-NIGHT", N 851 -> 852): logs, never orders.

Mechanism: a daily-reset single-stock LETF with leverage L must trade L(L-1) x AUM x r at the close, in the day's direction;
the hedge desk is forced into the closing cross and the next open reverts. Rule (FROZEN at registration, 2026-10-06): a name
with close >= $5, session $vol >= $10M, close-to-close r <= -5%, and the PRIOR session's 20d single-stock-LETF $vol on the name
/ the name's own 20d $vol > 2% -> buy the closing cross, sell the next opening cross, equal weight per event day. Control: the
same screens on names that have NO listed single-stock LETF (share == 0). Gate: NEED forward event days. PASS = mean net
(2.5bp/side) > +15bp/event-day, median > 0 and the control lower by >= 15bp; KILL = mean <= 0 or control not lower.
Overlap with the live night leg (state/night-candidates.jsonl) is reported per event.

Data: LETF -> underlying map swingtrader/daily/letf_map.json (package data, committed) (Sharadar fund names; refresh from the Mac with
research/sim/letf_map_build.py); the universe = the night leg's eligibility cache state/daily-universe-*.json (close >= $5,
20d $vol >= $10M: the registered screens); SIP daily bars (marketdata.sip_daily) for the day's returns and 20d $vol; official
auction prints (pref_ex_shadow.crosses) for the scored legs. Caveat: the universe cache carries ETFs as well as common stock
(no asset-class field), so the control can include non-LETF funds; LETF tickers themselves are excluded from both arms.
Each run scans every session since the last scanned one (<= 10 days back), logs the events, then scores pending rows whose
next-session opening cross has printed.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics as st
from pathlib import Path

import pandas as pd

LOG_NAME = "letf-night.jsonl"
CAND = "night-candidates.jsonl"
MAP = Path(__file__).resolve().with_name("letf_map.json")
R_MAX = -0.05
PX_MIN = 5.0
USD_MIN = 10e6
SHARE_MIN = 0.02
COST = 2.5e-4            # per side
NEED = 120
GATE_BP = 15.0
BENCH = "SPY"
LOOKBACK_DAYS = 10


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def letf_map(path: Path = MAP) -> dict[str, str]:
    """LETF ticker -> underlying (long and inverse funds both count: both sell the underlying on a down day)."""
    d = json.loads(path.read_text())["map"]
    return {k: v["under"] for k, v in d.items()}


def universe(state_dir: Path) -> list[str]:
    files = sorted(Path(state_dir).glob("daily-universe-*.json"))
    if not files:
        return []
    rows = json.loads(files[-1].read_text())
    return sorted({r["symbol"] for r in rows if isinstance(r, dict) and "symbol" in r})


def screen(day: str, bars: dict[str, pd.DataFrame], lmap: dict[str, str]) -> list[dict]:
    """Events on session `day`: every universe name (not itself an LETF) with the registered price / $vol / return screens;
    treated if its lagged LETF share > SHARE_MIN, control if the name has no LETF at all. Names with LETFs below the share
    bar are logged with treated=False, control=False (reported, not gated)."""
    by_under: dict[str, list[str]] = {}
    for l, u in lmap.items():
        by_under.setdefault(u, []).append(l)
    d = pd.Timestamp(day)
    out = []
    for sym, b in bars.items():
        if sym in lmap or b is None or d not in b.index:
            continue
        i = b.index.get_loc(d)
        if i < 1:
            continue
        c0, cp = float(b["close"].iloc[i]), float(b["close"].iloc[i - 1])
        usd = c0 * float(b["volume"].iloc[i])
        if not (cp > 0 and c0 >= PX_MIN and usd >= USD_MIN):
            continue
        r = c0 / cp - 1
        if r > R_MAX:
            continue
        own = b.iloc[max(0, i - 20):i]                       # 20 sessions ending the PRIOR session (lagged)
        own_usd = float((own["close"] * own["volume"]).sum())
        letf_usd = 0.0
        for l in by_under.get(sym, []):
            lb = bars.get(l)
            if lb is None or lb.empty:
                continue
            w = lb[lb.index < d].iloc[-20:]
            letf_usd += float((w["close"] * w["volume"]).sum())
        share = letf_usd / own_usd if own_usd > 0 else 0.0
        has = bool(by_under.get(sym))
        out.append(dict(date=day, sym=sym, r=round(r, 5), close=c0, usd=round(usd), share=round(share, 4),
                        letf_usd=round(letf_usd), treated=share > SHARE_MIN, control=not has, status="pending"))
    return out


def score(r: dict, X: dict) -> dict | None:
    """Closing cross on the signal day -> next session's opening cross (+ SPY on the same legs); None until it prints."""
    p = X.get(r["sym"], {})
    c0 = (p.get(r["date"]) or (None,) * 4)[2]
    later = sorted(d for d in p if d > r["date"])
    if not c0 or not later:
        return None
    o1 = p[later[0]][0]
    if not o1:
        return None
    ret = o1 / c0 - 1
    sp = X.get(BENCH, {})
    b0, b1 = (sp.get(r["date"]) or (None,) * 4)[2], (sp.get(later[0]) or (None,) * 4)[0]
    bench = (b1 / b0 - 1) if (b0 and b1) else None
    return dict(r, status="scored", exit=later[0], c0=c0, o1=o1, ret=round(ret, 6), net=round(ret - 2 * COST, 6),
                bench=None if bench is None else round(bench, 6), xs=None if bench is None else round(ret - bench, 6))


def _day_means(rows: list[dict], key: str) -> list[float]:
    by: dict[str, list[float]] = {}
    for r in rows:
        if r.get(key) is not None:
            by.setdefault(r["date"], []).append(float(r[key]))
    return [st.mean(v) for _, v in sorted(by.items())]


def summary(rows: list[dict]) -> dict:
    sc = [r for r in rows if r.get("status") == "scored"]
    tr = [r for r in sc if r.get("treated")]
    ct = [r for r in sc if r.get("control")]
    t_days, c_days = _day_means(tr, "net"), _day_means(ct, "net")
    out = dict(events=len(tr), days=len(t_days), ctl_events=len(ct), ctl_days=len(c_days),
               mean_bp=round(1e4 * st.mean(t_days), 1) if t_days else None,
               median_bp=round(1e4 * st.median(t_days), 1) if t_days else None,
               ev_median_bp=round(1e4 * st.median(r["net"] for r in tr), 1) if tr else None,
               hit=round(sum(r["net"] > 0 for r in tr) / len(tr), 2) if tr else None,
               ctl_mean_bp=round(1e4 * st.mean(c_days), 1) if c_days else None,
               xs_bp=round(1e4 * st.mean(r["xs"] for r in tr if r.get("xs") is not None), 1) if any(r.get("xs") is not None for r in tr) else None,
               overlap=sum(1 for r in tr if r.get("night_pick")), pending=sum(1 for r in rows if r.get("status") == "pending" and r.get("treated")))
    if len(t_days) >= 2:
        sd = st.pstdev(t_days)
        out["t"] = round(st.mean(t_days) / (sd / len(t_days) ** 0.5), 2) if sd > 0 else None
    return out


def verdict(s: dict) -> str:
    if s["days"] < NEED or s["mean_bp"] is None:
        return ""
    diff = s["mean_bp"] - (s["ctl_mean_bp"] if s["ctl_mean_bp"] is not None else 0.0)
    if s["mean_bp"] <= 0 or diff <= 0:
        return " -> KILL (mean <= 0 or control not lower)"
    if s["mean_bp"] > GATE_BP and (s["median_bp"] or 0) > 0 and diff >= GATE_BP:
        return " -> PASS (mean > 15bp, median > 0, beats control by >= 15bp)"
    return " -> HOLD"


def line(rows: list[dict]) -> str:
    s = summary(rows)
    if not s["days"]:
        return f"0/{NEED} event days scored ({s['pending']} treated events pending)"
    body = (f"{s['days']}/{NEED} event days, {s['events']} events: net {s['mean_bp']:+.1f}bp/day (median day {s['median_bp']:+.1f}, "
            f"median event {s['ev_median_bp']:+.1f}, hit {s['hit']:.0%}" + (f", t {s['t']}" if s.get("t") is not None else "") + ")"
            + (f"; vs SPY {s['xs_bp']:+.1f}" if s["xs_bp"] is not None else "")
            + (f"; control {s['ctl_days']} days {s['ctl_mean_bp']:+.1f}bp" if s["ctl_mean_bp"] is not None else "; control: none yet")
            + f"; night-leg overlap {s['overlap']}/{s['events']}")
    return body + verdict(s)


def sessions_to_scan(bench_bars: pd.DataFrame, done: set[str], today: dt.date) -> list[str]:
    days = [str(d.date()) for d in bench_bars.index if d.date() < today]
    return sorted(d for d in days if d not in done)


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None,
        bars_fn=None, crosses_fn=None) -> dict:
    from . import marketdata as md
    from .exdate_open_shadow import _headers
    from .pref_ex_shadow import crosses as _crosses
    bars_fn = bars_fn or md.sip_daily
    crosses_fn = crosses_fn or _crosses
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    today = today or dt.date.today()
    lmap = letf_map()
    uni = universe(state_dir)
    done = {r["date"] for r in rows if r.get("status") in ("scanned",)} | {r["date"] for r in rows if "sym" in r}
    start = today - dt.timedelta(days=LOOKBACK_DAYS)
    # 1) which sessions still need a scan (SPY's bars define the sessions)
    bench = bars_fn([BENCH], start, today).get(BENCH)
    todo = sessions_to_scan(bench, done, today) if bench is not None and uni else []
    if todo:
        # cheap pass: 2 sessions of bars for the whole universe -> the <= -5% names; then 30 sessions for those + their LETFs
        thin = bars_fn(uni, pd.Timestamp(todo[0]) - pd.Timedelta(days=7), today)
        cands: set[str] = set()
        for s, b in thin.items():
            if s in lmap or b is None or len(b) < 2:
                continue
            r = b["close"] / b["close"].shift(1) - 1
            if (r.loc[[pd.Timestamp(d) for d in todo if pd.Timestamp(d) in r.index]] <= R_MAX).any():
                cands.add(s)
        letfs = [l for l, u in lmap.items() if u in cands]
        full = bars_fn(sorted(cands) + letfs, pd.Timestamp(todo[0]) - pd.Timedelta(days=45), today) if cands else {}
        night = {}
        for r in _read(state_dir / CAND):
            night.setdefault(r.get("date"), set()).add(r.get("sym"))
        for d in todo:
            ev = screen(d, full, lmap)
            for e in ev:
                e["night_pick"] = e["sym"] in night.get(d, set())
            rows += ev
            rows.append(dict(date=d, status="scanned", n_events=sum(e["treated"] for e in ev), n_control=sum(e["control"] for e in ev)))
            log(f"[letf-night] {d}: {sum(e['treated'] for e in ev)} treated / {sum(e['control'] for e in ev)} control events "
                f"({', '.join(e['sym'] + f' {e['share']:.0%}' for e in ev if e['treated'])[:200]})")
    # 2) score pending rows whose next opening cross has printed
    pend = [r for r in rows if r.get("status") == "pending" and r["date"] < str(today)]
    if pend:
        H = H or _headers()
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        syms = sorted({r["sym"] for r in pend} | {BENCH})
        d0 = min(r["date"] for r in pend)
        X: dict = {}
        for i in range(0, len(syms), 40):
            X.update(crosses_fn(syms[i:i + 40], d0, end, H))
        new = []
        for r in rows:
            if r.get("status") == "pending" and r["date"] < str(today):
                s = score(r, X)
                if s:
                    r = s
                elif r["date"] <= str(today - dt.timedelta(days=6)):
                    r = dict(r, status="no_cross")
            new.append(r)
        rows = new
    rows = sorted(rows, key=lambda r: (r["date"], r.get("sym", "")))
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[letf-night] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
