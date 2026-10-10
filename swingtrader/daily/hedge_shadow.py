"""Hedge shadow (HEDGE-SHADOW, round1_prose.md 2026-10-10): logs, never orders.

An online learner over a FIXED grid of night configs, trained only on forward nights (the one data no study has touched).
Grid: drop cutoff {-8, -10, -12, -15}% x top_k {all, 2, 4} (12 configs). Each config's nightly return = mean of the
candidates it keeps (official close cross -> next opening cross, scored by repeat_shadow; every 15:40 signal before
dedupe / vol / cash / wash filters), net 5bp/side, 0 when it keeps nothing. Exponential weights (Hedge): w_c ~ exp(ETA x
cumulative return in %). Before each night the highest-weight config is "chosen", using only earlier nights.

Gate (frozen): NEED scored nights. PASS = chosen series - live series (cutoff -8%, all) >= +10bp/night, night t >= 2,
halves > 0; KILL = mean diff <= 0. A PASS is evidence that adapting the night filter forward beats the fixed rule.
"""
from __future__ import annotations

import json
import math
import statistics as st
from pathlib import Path

LOG_NAME = "hedge-shadow.jsonl"
CAND = "night-candidates.jsonl"
CUTS = (-0.08, -0.10, -0.12, -0.15)
TOPK = (None, 2, 4)
GRID = [(c, k) for c in CUTS for k in TOPK]
ETA = 0.5
COST = 5e-4
NEED = 120


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


def name(cfg) -> str:
    c, k = cfg
    return f"{c * 100:.0f}%/{'all' if k is None else k}"


def cfg_ret(sc: list[dict], cfg) -> float:
    c, k = cfg
    keep = sorted((r for r in sc if r["day_ret"] <= c), key=lambda r: r["day_ret"])
    if k is not None:
        keep = keep[:k]
    return st.mean(r["ret"] for r in keep) - 2 * COST if keep else 0.0


def learn(cands: list[dict]) -> list[dict]:
    by: dict[str, list[dict]] = {}
    for r in cands:
        by.setdefault(r["date"], []).append(r)
    cum = [0.0] * len(GRID)
    out = []
    for d, rs in sorted(by.items()):
        if any(r.get("status") == "pending" for r in rs):
            break                                          # nights are learned strictly in order
        sc = [r for r in rs if r.get("status") == "scored" and r.get("ret") is not None]
        if not sc:
            continue
        m = max(cum)
        w = [math.exp(ETA * (x - m)) for x in cum]
        tot = sum(w)
        pick = max(range(len(GRID)), key=lambda i: (w[i], -i))
        rets = [cfg_ret(sc, g) for g in GRID]
        live = rets[GRID.index((-0.08, None))]
        out.append(dict(date=d, n=len(sc), chosen=name(GRID[pick]), chosen_bp=round(1e4 * rets[pick], 2),
                        live_bp=round(1e4 * live, 2), diff_bp=round(1e4 * (rets[pick] - live), 2),
                        weights={name(g): round(x / tot, 4) for g, x in zip(GRID, w)}))
        cum = [x + 100 * r for x, r in zip(cum, rets)]         # cumulative return in %
    return out


def line(rows: list[dict]) -> str:
    if not rows:
        return f"0/{NEED} nights"
    d = [r["diff_bp"] for r in rows]
    top = max(rows[-1]["weights"].items(), key=lambda kv: kv[1])
    s = f"{len(d)}/{NEED} nights: chosen - live {st.mean(d):+.0f}bp/night"
    if len(d) > 2 and st.stdev(d) > 0:
        t = st.mean(d) / st.stdev(d) * math.sqrt(len(d))
        s += f" (t {t:.2f})"
    s += f"; leading config {top[0]} (w {top[1]:.2f})"
    if len(d) >= NEED:
        h = len(d) // 2
        t = st.mean(d) / st.stdev(d) * math.sqrt(len(d)) if st.stdev(d) > 0 else 0
        ok = st.mean(d) >= 10 and t >= 2 and st.mean(d[:h]) > 0 and st.mean(d[h:]) > 0
        s += " -> PASS" if ok else " -> KILL" if st.mean(d) <= 0 else " -> HOLD"
    return s


def run(state_dir: Path, logs_dir: Path, log=print) -> dict:
    rows = learn(_read(Path(state_dir) / CAND))
    (Path(state_dir) / LOG_NAME).write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[hedge] {line(rows)}")
    return dict(n=len(rows))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
