"""Repeat-loser shadow (L1, window-signal loop 2026-10-07): logs, never orders.

Claim (research/drafts/window_signals_loop_2026-10-07.md, rounds 6/8/37): a night-leg signal whose symbol was ALSO a
signal 1-5 sessions earlier bounces more overnight than a first-time signal. Daily-bar proxy 2016-26, delisted-complete:
night-paired +85bp (t 3.4); independent re-implementation +103bp (t 4.1), halves stable; gap 6-20 looks like a first
pick; the effect is a fatter right tail (medians close after 2021). Not judgeable from fills (repeats were 4 of the
first 75 live night trades), so every 15:40 signal is logged here, before dedupe / vol / cash / wash filters.

Logging: the night leg calls log_candidates() right after the rule scan (both accounts; one row per date x symbol).
Scoring (research-shadows, next morning): official closing cross on the signal day -> official opening cross of the
next session, the live leg's two auctions. repeat = the symbol was logged 1-5 logged sessions earlier; first = not in
the prior 20.

Gate (frozen): NEED repeat candidates scored. PASS = night-paired (repeat - first) >= +30bp, t >= 2, both halves of the
forward sample the same sign; KILL = paired <= 0. If it passes, the action is a sizing tilt on repeats (Roth first: a
taxable re-buy within 30 days of a loss is a wash sale), decided with tilt v2 (NEXT.md addendum 23), never a new leg.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics as st
from pathlib import Path

LOG_NAME = "night-candidates.jsonl"
NEED = 150
REPEAT = 5
FIRST = 20


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


def log_candidates(state_dir: Path, today: str, picks, account: str) -> int:
    """Append today's rule signals (a DataFrame indexed by symbol with price / day_ret / ibs); one row per symbol a day."""
    path = Path(state_dir) / LOG_NAME
    have = {(r["date"], r["sym"]) for r in _read(path) if r.get("date") == today}
    new = []
    for sym, r in picks.iterrows():
        if (today, sym) in have:
            continue
        new.append(dict(date=today, sym=str(sym), account=account, price=round(float(r["price"]), 4),
                        day_ret=round(float(r["day_ret"]), 5), ibs=round(float(r["ibs"]), 4), status="pending"))
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write("".join(json.dumps(x) + "\n" for x in new))
    return len(new)


def flag(rows: list[dict]) -> None:
    """gap = logged sessions since the symbol's previous signal (None if never); repeat / first by the frozen bands."""
    days = sorted({r["date"] for r in rows})
    pos = {d: i for i, d in enumerate(days)}
    last: dict[str, int] = {}
    for r in sorted(rows, key=lambda r: (r["date"], r["sym"])):
        k = pos[r["date"]]
        g = k - last[r["sym"]] if r["sym"] in last else None
        r["gap"] = g
        r["repeat"] = g is not None and 1 <= g <= REPEAT
        r["first"] = g is None or g > FIRST
        last[r["sym"]] = k


def score(r: dict, p: dict) -> dict:
    """Close cross of the signal day -> opening cross of the next session with prints (p: date -> (o, os, c, cs))."""
    d = p.get(r["date"])
    nxt = next((x for x in sorted(p) if x > r["date"] and p[x][0]), None)
    if not d or not d[2] or not nxt:
        return r
    ret = p[nxt][0] / d[2] - 1
    if abs(ret) > 0.9:                                      # split / bad print, not a night
        return dict(r, status="mismatch", ret=ret)
    return dict(r, status="scored", exit=nxt, close_cross=d[2], open_cross=p[nxt][0], ret=ret)


def paired(rows: list[dict]) -> dict:
    """Night-paired mean of (repeat mean - first mean) over nights that have both, with its t."""
    nights: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        if r.get("status") != "scored":
            continue
        k = "rep" if r.get("repeat") else "first" if r.get("first") else None
        if k:
            nights.setdefault(r["date"], {}).setdefault(k, []).append(r["ret"])
    d = sorted((n, st.mean(v["rep"]) - st.mean(v["first"])) for n, v in nights.items() if "rep" in v and "first" in v)
    x = [v for _, v in d]
    t = st.mean(x) / st.stdev(x) * math.sqrt(len(x)) if len(x) > 2 and st.stdev(x) > 0 else None
    h = len(x) // 2
    halves = (st.mean(x[:h]) * 1e4, st.mean(x[h:]) * 1e4) if h >= 1 and len(x) - h >= 1 else None
    return dict(nights=len(x), mean_bp=st.mean(x) * 1e4 if x else None, t=t, halves=halves)


def line(rows: list[dict]) -> str:
    sc = [r for r in rows if r.get("status") == "scored"]
    rep = [r["ret"] for r in sc if r.get("repeat")]
    fst = [r["ret"] for r in sc if r.get("first")]
    if not sc:
        return f"{len(rows)} candidates logged, none scored yet"
    p = paired(rows)
    s = (f"{len(sc)} scored ({len(rep)} repeat / {len(fst)} first-time): repeat "
         f"{(st.mean(rep) * 1e4 if rep else float('nan')):+.0f}bp vs first {(st.mean(fst) * 1e4 if fst else float('nan')):+.0f}bp")
    if p["nights"]:
        s += f"; night-paired {p['mean_bp']:+.0f}bp over {p['nights']} nights (t {p['t'] if p['t'] is None else round(p['t'], 2)})"
    if len(rep) >= NEED:
        ok = (p["mean_bp"] or 0) >= 30 and (p["t"] or 0) >= 2 and p["halves"] and min(p["halves"]) > 0
        s += " -> PASS" if ok else " -> KILL" if (p["mean_bp"] or 0) <= 0 else " -> HOLD"
    return s


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None) -> dict:
    from .exdate_open_shadow import _headers
    from .pref_ex_shadow import crosses
    path = Path(state_dir) / LOG_NAME
    rows = _read(path)
    today = today or dt.date.today()
    todo = [r for r in rows if r.get("status") == "pending" and r["date"] < str(today)]
    if todo:
        H = H or _headers()
        syms = sorted({r["sym"] for r in todo})
        start = min(r["date"] for r in todo)
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        X: dict = {}
        for i in range(0, len(syms), 40):
            X.update(crosses(syms[i:i + 40], start, end, H))
        stale = str(today - dt.timedelta(days=6))
        out = []
        for r in rows:
            if r in todo:
                r = score(r, X.get(r["sym"], {}))
                if r.get("status") == "pending" and r["date"] <= stale:
                    r = dict(r, status="no_cross")
            out.append(r)
        rows = out
    flag(rows)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[repeat] {line(rows)}")
    return dict(n=sum(1 for r in rows if r.get("status") == "scored" and r.get("repeat")))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
