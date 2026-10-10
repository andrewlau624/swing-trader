"""TOP2 shadow (Study DEPTH, round1_prose.md 2026-10-10): logs, never orders.

Claim: keeping only the night's 2 deepest drops beats the equal-weight night (judge 1999-2015 +14.2bp/night t 3.37, Sharpe
2.34 vs 2.21) but in 2016-26 it was the same Sharpe at ~1.57x the nightly std, i.e. mostly concentration. Forward question:
does TOP2 beat the base risk-adjusted, not just in mean?

Reads state/night-candidates.jsonl after repeat_shadow has scored it (ret = official close cross -> next opening cross; every
15:40 signal before dedupe / vol / cash / wash filters). Per night: base = mean ret of all scored candidates, top2 = mean of the
2 most negative day_ret. Nights with < 3 scored candidates are logged but not judged (TOP2 = base there).

Gate (frozen): NEED judged nights. PASS = mean (top2 - base) >= +10bp, night t >= 2, both halves > 0 AND top2 Sharpe > base
Sharpe; KILL = mean diff <= 0. A PASS is a sizing/concentration decision for the user, not a new leg.
"""
from __future__ import annotations

import json
import math
import statistics as st
from pathlib import Path

LOG_NAME = "top2-shadow.jsonl"
CAND = "night-candidates.jsonl"
NEED = 60
K = 2
MIN_N = 3


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


def nights(cands: list[dict]) -> list[dict]:
    """One row per night whose candidates are all scored or resolved (none pending)."""
    by: dict[str, list[dict]] = {}
    for r in cands:
        by.setdefault(r["date"], []).append(r)
    out = []
    for d, rs in sorted(by.items()):
        if any(r.get("status") == "pending" for r in rs):
            continue
        sc = [r for r in rs if r.get("status") == "scored" and r.get("ret") is not None]
        if not sc:
            continue
        deep = sorted(sc, key=lambda r: r["day_ret"])[:K]
        base = st.mean(r["ret"] for r in sc)
        top = st.mean(r["ret"] for r in deep)
        out.append(dict(date=d, n=len(sc), judged=len(sc) >= MIN_N, base_bp=round(1e4 * base, 2), top2_bp=round(1e4 * top, 2),
                        diff_bp=round(1e4 * (top - base), 2), top2=[r["sym"] for r in deep]))
    return out


def summary(rows: list[dict]) -> dict:
    j = [r for r in rows if r["judged"]]
    if len(j) < 3:
        return dict(nights=len(j), mean_bp=None, t=None, halves=None, sharpe=None)
    d = [r["diff_bp"] for r in j]
    sd = st.stdev(d)
    t = st.mean(d) / sd * math.sqrt(len(d)) if sd > 0 else None
    h = len(d) // 2
    sh = lambda k: st.mean(r[k] for r in j) / st.stdev(r[k] for r in j) * math.sqrt(252) if st.stdev(r[k] for r in j) > 0 else 0.0
    return dict(nights=len(j), mean_bp=st.mean(d), t=t, halves=(st.mean(d[:h]), st.mean(d[h:])), sharpe=(sh("top2_bp"), sh("base_bp")))


def line(rows: list[dict]) -> str:
    s = summary(rows)
    if s["mean_bp"] is None:
        return f"{s['nights']}/{NEED} judged nights (need >= {MIN_N} scored candidates a night)"
    out = (f"{s['nights']}/{NEED} nights: top2 - base {s['mean_bp']:+.0f}bp/night (t {'-' if s['t'] is None else round(s['t'], 2)}), "
           f"Sharpe top2 {s['sharpe'][0]:.2f} vs base {s['sharpe'][1]:.2f}")
    if s["nights"] >= NEED:
        ok = s["mean_bp"] >= 10 and (s["t"] or 0) >= 2 and min(s["halves"]) > 0 and s["sharpe"][0] > s["sharpe"][1]
        out += " -> PASS" if ok else " -> KILL" if s["mean_bp"] <= 0 else " -> HOLD"
    return out


def run(state_dir: Path, logs_dir: Path, log=print) -> dict:
    rows = nights(_read(Path(state_dir) / CAND))
    (Path(state_dir) / LOG_NAME).write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[top2] {line(rows)}")
    return dict(n=sum(1 for r in rows if r["judged"]))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
