"""Everything being tested forward, in one list, for the weekly digest's "Being tested" section.

STANDING RULE (CLAUDE.md): any new shadow, watch, alert, log-only switch or forward-only weight gets an entry in
REGISTRY in the same commit that adds it. tests/test_testing_registry.py fails if a module with a state log
(`LOG_NAME`) or a `shadow` config key under `daily:` has no entry, so nothing runs untracked.

Each entry's `read(state, logs)` returns dict(n=<count toward the gate>, week=<new this week>, line=<one-line read
of where it stands>). Read-only: never touches a book, an order or a switch.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Test:
    name: str
    what: str                      # one plain sentence: what is being tested
    started: str                   # YYYY-MM-DD
    need: int                      # count at which the verdict / decision is read (0 = alert, no gate)
    unit: str
    read: Callable[[Path, Path], dict]
    where: str                     # where to look for the details
    covers: list[str] = field(default_factory=list)    # module names / config keys this entry accounts for


def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _week_ago() -> str:
    return str(dt.date.today() - dt.timedelta(days=7))


def _bp(x) -> str:
    return "n/a" if x is None or x != x else f"{x:+.1f}bp"


# ---------------------------------------------------------------- readers
def _insider(key: str | None):
    def read(state: Path, logs: Path) -> dict:
        from . import insider_shadow as s
        rows = s._read(state / s.LOG_NAME)
        sc = [r for r in rows if r.get("status") == "scored"]
        g = s.gate(rows)
        if key:
            sub = [r for r in sc if (s.id3_big(r) if key == "id3_big" else s.ev2_flags(r)[0 if key == "ev2" else 1])]
            g2 = g.get(key, dict(n=0, verdict="no scored trades yet"))
            line = (f"{g2['verdict']}; mean {_bp(g2.get('mean_bp'))} vs rest {_bp(g2.get('rest_bp'))}, "
                    f"t {g2.get('t', float('nan')):+.2f}" if g2["n"] else g2["verdict"])
            return dict(n=g2["n"], week=sum(1 for r in sub if r["date"] >= _week_ago()), line=line)
        line = f"{g['verdict']}; mean {_bp(g.get('mean_bp'))}, t {g.get('t', float('nan')):+.2f}" if g["n"] else g["verdict"]
        return dict(n=g["n"], week=sum(1 for r in sc if r["date"] >= _week_ago()), line=line)
    return read


def _alerts(log_name: str, label: str):
    def read(state: Path, logs: Path) -> dict:
        rows = _jsonl(state / log_name)
        al = [r for r in rows if r.get("alert")]
        wk = [r for r in al if str(r.get("date") or r.get("alerted") or r.get("seen") or "") >= _week_ago()]
        return dict(n=len(al), week=len(wk), line=f"{len(rows)} {label} seen, {len(al)} alerted")
    return read


def _news(state: Path, logs: Path) -> dict:
    v = [r for r in _jsonl(state / "news-judge.jsonl") if r.get("verdict")]
    f = sum(1 for r in v if r["verdict"] == "fundamental")
    return dict(n=len(v), week=sum(1 for r in v if str(r.get("date", "")) >= _week_ago()),
                line=f"{f} of {len(v)} picks called 'fundamental'; verdict read once at 300 (make forward-status)")


def _quote_imbalance(state: Path, logs: Path) -> dict:
    snaps = [(d.get("date"), d.get("sym")) for f in logs.glob("daily-decisions*.jsonl")
             for d in _jsonl(f) if d.get("bid_size") is not None]
    return dict(n=len(set(snaps)), week=len({s for s in snaps if str(s[0]) >= _week_ago()}),
                line="15:40 bid/ask sizes logged per night pick; verdict once at 300 (make forward-status)")


def _log_tag(tag: str):
    """Count `[tag]` lines in the executor's daily logs (logs/daily-YYYY-MM-DD.log); 0 this week = silent."""
    pat = re.compile(r"\[" + re.escape(tag) + r"[\]: ]")

    def read(state: Path, logs: Path) -> dict:
        n = wk = 0
        for f in logs.glob("daily-*.log"):
            m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
            if not m:
                continue
            k = sum(1 for line in f.read_text(errors="ignore").splitlines() if pat.search(line))
            n += k
            wk += k if m.group(1) >= _week_ago() else 0
        return dict(n=n, week=wk, line=f"{wk} [{tag}] log lines this week" + ("" if wk else " (silent: check it runs)"))
    return read


def _stack(state: Path, logs: Path) -> dict:
    from . import stack_shadow as s
    rows = s._read(state / s.LOG_NAME)
    wk = sum(1 for r in rows if r["date"] >= _week_ago())
    return dict(n=len(rows), week=wk, line=s.line(rows) if rows else "no sessions logged yet (make stack-shadow)")


def _pick_cost(state: Path, logs: Path) -> dict:
    from . import pick_cost_watch as w
    rows = [r for r in w._jsonl(state / w.LOG_NAME) if "buy_cost_bp" in r]
    cheap = sum(1 for r in rows if r["bucket"] == "$5-10")
    wk = sum(1 for r in rows if r["buy_at"] >= _week_ago())
    return dict(n=cheap, week=wk, line=w.line(rows) if rows else "no live night trips scored yet (make pick-cost)")


# ---------------------------------------------------------------- the list
REGISTRY: list[Test] = [
    Test("Night auction cost by price bucket (pick-quality lead)", "do $5-10 night names really cost ~15bp/side live, or ~0 in the auctions? (gross bounce $5-10 +40bp vs $50+ ~0)",
         "2026-10-02", 100, "$5-10 live trips", _pick_cost, "make pick-cost; pick_quality_log.md", ["pick_cost_watch"]),
    Test("Book stacked on index beta (index-beat FOUND)", "taxable = SPY 1.0x + live legs on margin; Roth = 1/3 UPRO + 2/3 book: does it beat both the live accounts and SPY?",
         "2026-10-02", 250, "sessions", _stack, "make stack-shadow; study_ib_found_stack.md", ["stack_shadow"]),
    Test("Insider-day (ID3)", "buy the open / sell the close the session after an officer/director buy",
         "2026-10-02", 300, "scored trades", _insider(None), "make forward-status", ["insider_shadow", "insider_day"]),
    Test("EV2: first insider buy in 2+ years", "is ID3 ~2x stronger when nobody bought in the open market for 2 years?",
         "2026-10-02", 60, "scored EV2 trades", _insider("ev2"), "make forward-status; study_ev2_first_insider_buy.md"),
    Test("EV2 x buy >= $500k", "post-judge cut (forward data only): EV2 names with a big purchase",
         "2026-10-02", 60, "scored trades", _insider("ev2_big"), "make forward-status; study_ev2_first_insider_buy.md"),
    Test("ID3 x buy >= $500k (any silence)", "Goal G3: does the buy SIZE alone carry ID3? (holdout report row +35.7bp)",
         "2026-10-02", 60, "scored trades", _insider("id3_big"), "make forward-status; study_goal_g2.md"),
    Test("Odd-lot tenders", "issuer tenders with odd-lot priority >= 1% over market (manual, <= 99 shares)",
         "2026-10-02", 0, "alerts", _alerts("tender-watch.jsonl", "tenders"), "make tender-watch",
         ["tender_watch", "tender_buy"]),
    Test("Split-off exchange offers", "odd lots accepted in full in split-off exchange offers (manual)",
         "2026-10-02", 0, "alerts", _alerts("splitoff-watch.jsonl", "offers"), "make splitoff-watch", ["splitoff_watch"]),
    Test("Reverse-split round-up", "1 share before a reverse split that rounds fractions up (manual)",
         "2026-10-02", 0, "alerts", _alerts("roundup-watch.jsonl", "splits"), "make roundup-watch", ["roundup_watch"]),
    Test("LLM news judge", "does Claude's 'fundamental' label pick the night picks that keep falling?",
         "2026-09-24", 300, "picks judged", _news, "make forward-status", ["news_judge"]),
    Test("15:40 quote imbalance", "does the bid/ask size at 15:40 predict the night pick's bounce?",
         "2026-09-24", 300, "picks logged", _quote_imbalance, "make forward-status"),
    Test("Conviction trade (shadow)", "TQQQ conviction weight on breakout days, logged not traded",
         "2026-09-22", 0, "log lines", _log_tag("conv"), "make review section 7", ["conviction_mode"]),
    Test("Oversold index buy (V6) + Roth A2", "SPY/QQQ close -> open after 3 down closes / RSI(2) < 10",
         "2026-09-22", 0, "log lines", _log_tag("oversold"), "make review", ["oversold_mode"]),
    Test("FOMC-eve QQQ filler (F3)", "QQQ close -> open on spare night cash before FOMC decisions",
         "2026-09-22", 0, "log lines", _log_tag("fomc"), "make review", ["fomc_filler_mode"]),
    Test("Roth night cash (M2L)", "requested vs funded night notional in the Roth",
         "2026-09-22", 0, "log lines", _log_tag("roth-cash"), "make review", ["roth_night_cash_log"]),
    Test("Lever gate G1", "day-clustered 95% upper-bound gate beside the live lever gate",
         "2026-09-22", 0, "log lines", _log_tag("lever-g1"), "make review", ["lever_g1_log"]),
    Test("Wash guard G4s", "what the Roth-first wash-sale guard would change vs the live one",
         "2026-09-22", 0, "log lines", _log_tag("wash-guard"), "make review", ["wash_guard_mode"]),
    Test("Tug-of-war night tilt (AU3)", "tilt night picks by the tug-of-war score (logged, not sized)",
         "2026-09-22", 0, "log lines", _log_tag("night"), "make review section 9 (SINCE=2026-09-22)"),
]


def status(state: Path, logs: Path) -> list[dict]:
    """One row per entry: name, what, started, n, need, week, line, where. A reader that fails says so."""
    out = []
    for t in REGISTRY:
        try:
            r = t.read(Path(state), Path(logs))
        except Exception as exc:                       # the digest must still go out
            r = dict(n=0, week=0, line=f"could not read ({type(exc).__name__})")
        out.append(dict(name=t.name, what=t.what, started=t.started, need=t.need, unit=t.unit, where=t.where, **r))
    return out
