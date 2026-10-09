"""Crowded-night hold shadow (OPENSIG lead, round1_prose.md 2026-10-09): logs, never orders.

Lead: night picks that are held from the opening cross to the closing cross gain open->close only on crowded washout
nights (many signals, a market-wide reversal); on thin nights they keep falling (OPENSIG per-trade vs per-day split,
both research windows touched, so it can only be judged forward).

Reads state/night-candidates.jsonl (every 15:40 night-rule signal, before dedupe / vol / cash / wash filters; written by
the night leg via repeat_shadow.log_candidates). For each signal night, scores every candidate on official SIP crosses:
close cross on the signal day (c0) -> next session's opening cross (o1) -> its closing cross (c1).
hold = (c1 - o1) / c0, the extra P&L per dollar bought of holding to the close instead of selling at the open.
crowded = >= CROWD candidates that night (the replay's 80th percentile of raw signals per night, 2020-11..2026-09).

Gate (frozen): NEED crowded nights scored. PASS = mean per-night hold on crowded nights >= +20bp, night t >= 2, both
halves > 0, median night > 0; KILL = mean <= 0. Thin nights are the control (expected <= 0). A PASS means a pilot of
"hold to the close cross on crowded nights", a user decision.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics as st
from pathlib import Path

LOG_NAME = "crowd-hold.jsonl"
CAND = "night-candidates.jsonl"
CROWD = 16
NEED = 30
GATE_BP = 20


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


def score_night(date: str, syms: list[str], X: dict) -> dict | None:
    """One row per signal night, or None while the next session's closing cross is not in yet."""
    holds, ovns = [], []
    nxt = None
    for s in syms:
        p = X.get(s, {})
        c0 = (p.get(date) or (None,) * 4)[2]
        later = sorted(d for d in p if d > date)
        if not later:
            continue
        nxt = nxt or later[0]
        o1, _, c1, _ = p[later[0]]
        if not (c0 and o1 and c1):
            continue
        holds.append((c1 - o1) / c0)
        ovns.append(o1 / c0 - 1)
    if not holds:
        return None
    return dict(date=date, exit=nxt, n=len(syms), crowded=len(syms) >= CROWD, scored=len(holds),
                hold_bp=round(1e4 * st.mean(holds), 2), ovn_bp=round(1e4 * st.mean(ovns), 2),
                hold_med_bp=round(1e4 * st.median(holds), 2))


def summary(rows: list[dict], crowded: bool = True) -> dict:
    v = [r["hold_bp"] for r in sorted(rows, key=lambda r: r["date"]) if r.get("crowded") == crowded]
    if not v:
        return dict(nights=0, mean_bp=None, t=None, med_bp=None, halves=None)
    t = st.mean(v) / st.stdev(v) * math.sqrt(len(v)) if len(v) > 2 and st.stdev(v) > 0 else None
    h = len(v) // 2
    halves = (st.mean(v[:h]), st.mean(v[h:])) if h >= 1 else None
    return dict(nights=len(v), mean_bp=st.mean(v), t=t, med_bp=st.median(v), halves=halves)


def line(rows: list[dict]) -> str:
    c, q = summary(rows, True), summary(rows, False)
    if not c["nights"] and not q["nights"]:
        return "no nights scored yet"
    f = lambda s: (f"{s['mean_bp']:+.0f}bp/night (median {s['med_bp']:+.0f}, t {'-' if s['t'] is None else round(s['t'], 2)})"
                   if s["nights"] else "-")
    s = f"crowded (>= {CROWD} signals) {c['nights']}/{NEED} nights: hold-to-close {f(c)}; thin {q['nights']}: {f(q)}"
    if c["nights"] >= NEED:
        ok = (c["mean_bp"] >= GATE_BP and (c["t"] or 0) >= 2 and c["halves"] and min(c["halves"]) > 0
              and c["med_bp"] > 0)
        s += " -> PASS" if ok else " -> KILL" if c["mean_bp"] <= 0 else " -> HOLD"
    return s


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None) -> dict:
    from .exdate_open_shadow import _headers
    from .pref_ex_shadow import crosses
    path = Path(state_dir) / LOG_NAME
    rows = _read(path)
    done = {r["date"] for r in rows}
    today = today or dt.date.today()
    by: dict[str, set] = {}
    for r in _read(Path(state_dir) / CAND):
        by.setdefault(r["date"], set()).add(r["sym"])
    todo = sorted(d for d in by if d not in done and d < str(today))
    if todo:
        H = H or _headers()
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for d in todo:
            syms = sorted(by[d])
            X: dict = {}
            for i in range(0, len(syms), 40):
                X.update(crosses(syms[i:i + 40], d, end, H))
            r = score_night(d, syms, X)
            if r and r["exit"] < str(today):
                rows.append(r)
            elif d <= str(today - dt.timedelta(days=6)):
                rows.append(dict(date=d, n=len(syms), crowded=len(syms) >= CROWD, status="no_cross"))
    rows = sorted(rows, key=lambda r: r["date"])
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    scored = [r for r in rows if "hold_bp" in r]
    log(f"[crowd-hold] {line(scored)}")
    return dict(n=sum(1 for r in scored if r["crowded"]))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
