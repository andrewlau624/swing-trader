"""Weekly review (`make daytrade-review`): per strategy and mode, trades, net bp, fill drift against
the replay model, rule events, and a written decision: drop / continue / change course.

The decision line is proposed from each plan's drop condition; edit the file to overrule it, with
the reason. A "change course" means a new plan variant (PLAN_CHANGES.md, new N)."""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from pathlib import Path

from .journal import load
from .settings import STATE

REVIEWS = Path(__file__).resolve().parent / "reviews"
PAPER_MIN_TRADES = 40                      # both plans: the paper drop check runs at 40 round trips
PAPER_MIN_NET_BP = {"gap_vwap_reclaim": 5.0, "open_imbalance": 0.0}


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _t(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 3:
        return None
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    return m / (sd / math.sqrt(len(xs))) if sd > 0 else None


def decide(strategy: str, mode: str, all_trades: list[dict], replay_edge_bp: float | None) -> tuple[str, str]:
    from .strategies import REGISTRY
    st = getattr(REGISTRY.get(strategy), "status", "")
    if st.startswith("dead"):
        return "drop", st                    # the registered study already failed; nothing trades it
    n = len(all_trades)
    net = _mean([t["net_bp"] for t in all_trades])
    drift = _mean([(t.get("entry_drift_bp") or 0) + (t.get("exit_drift_bp") or 0) for t in all_trades
                   if t.get("entry_drift_bp") is not None or t.get("exit_drift_bp") is not None])
    if mode == "replay":
        return "continue", "replay only; the study's pass bar decides (research/drafts)"
    if n < PAPER_MIN_TRADES:
        return "continue", f"{n} of {PAPER_MIN_TRADES} round trips: too few to judge"
    floor = PAPER_MIN_NET_BP.get(strategy, 0.0)
    if net is not None and net < floor:
        return "drop", f"mean net {net:+.1f}bp < the plan's {floor:+.1f}bp at {n} trades"
    if replay_edge_bp is not None and net is not None and net < replay_edge_bp / 2:
        return "drop", f"mean net {net:+.1f}bp < half the replay edge ({replay_edge_bp:+.1f}bp)"
    if drift is not None and replay_edge_bp is not None and drift > replay_edge_bp:
        return "drop", f"fill drift {drift:+.1f}bp > the replay edge {replay_edge_bp:+.1f}bp"
    return "continue", f"{n} trades, mean net {net:+.1f}bp, drift {drift if drift is not None else 0:+.1f}bp"


def build(days: int = 7, today: dt.date | None = None, root: Path = STATE,
          replay_edges: dict | None = None) -> str:
    today = today or dt.date.today()
    since = (today - dt.timedelta(days=days)).isoformat()
    lines = [f"# Day-trading lab review, {today.isoformat()} (last {days} days)", ""]
    any_rows = False
    for mode in ("paper", "live", "replay"):
        trades = load(Path(root) / f"journal-{mode}.jsonl")
        events = load(Path(root) / f"events-{mode}.jsonl")
        if not trades and not events:
            continue
        any_rows = True
        by = defaultdict(list)
        for t in trades:
            by[t["strategy"]].append(t)
        ev_by = defaultdict(list)
        for e in events:
            if e.get("day", "") >= since:
                ev_by[e.get("strategy", "")].append(e)
        lines += [f"## {mode}", "",
                  "| strategy | trades (week / all) | net bp week | net bp all | t all | win % | "
                  "drift bp (entry+exit) | rule events week | decision | reason |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for strat in sorted(set(by) | {k for k in ev_by if k}):
            allt = by.get(strat, [])
            week = [t for t in allt if t.get("day", "") >= since]
            drift = _mean([(t.get("entry_drift_bp") or 0) + (t.get("exit_drift_bp") or 0) for t in week
                           if t.get("entry_drift_bp") is not None or t.get("exit_drift_bp") is not None])
            nets = [t["net_bp"] for t in allt]
            win = 100 * sum(1 for x in nets if x > 0) / len(nets) if nets else None
            d, why = decide(strat, mode, allt, (replay_edges or {}).get(strat))
            f = lambda x, fmt: "—" if x is None else format(x, fmt)  # noqa: E731
            lines.append(f"| {strat} | {len(week)} / {len(allt)} | {f(_mean([t['net_bp'] for t in week]), '+.1f')} "
                         f"| {f(_mean(nets), '+.1f')} | {f(_t(nets), '.2f')} | {f(win, '.0f')} | {f(drift, '+.1f')} "
                         f"| {len(ev_by.get(strat, []))} | **{d}** | {why} |")
        breaks = [e for e in events if e.get("day", "") >= since and e["kind"] in
                  ("held at end of data", "order after halt/flat", "late fill after cancel")]
        limits = [e for e in events if e.get("day", "") >= since and e["kind"] in ("daily loss limit", "halt")]
        lines += ["", f"Rule BREAKS this week (must be 0 for the $500 gate): {len(breaks)}",
                  f"Limits that fired (working as designed): {len(limits)}", ""]
        for e in (breaks + limits)[:20]:
            lines.append(f"- {e['ts']} {e['kind']}: {e['detail']}")
        lines.append("")
    if not any_rows:
        lines.append("No journal yet: nothing has traded in replay, paper or live.")
    lines += ["", "Decision notes (write the reason for any override here):", ""]
    return "\n".join(lines) + "\n"


def main(days: int = 7) -> int:
    REVIEWS.mkdir(parents=True, exist_ok=True)
    text = build(days)
    p = REVIEWS / f"{dt.date.today().isoformat()}.md"
    p.write_text(text)
    print(text)
    print(f"written to {p}")
    return 0
