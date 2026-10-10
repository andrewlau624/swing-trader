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


def _m1_insider(key: str):
    """Track M1 (round1_prose.md): an insider idea killed only on judge t < 2, read against its prediction."""
    def read(state: Path, logs: Path) -> dict:
        from . import insider_shadow as s
        rows = s._read(state / s.LOG_NAME)
        g = s.m1_gate(rows)[key]
        wk = sum(1 for r in rows if r.get("status") == "scored" and r.get("m1") and r["date"] >= _week_ago()
                 and (key == "id1" or r.get(key)))
        line = (f"{g['verdict']}; live {_bp(g['live_bp'])} vs predicted {g['pred_bp']:+.1f}bp, t {g['t']:+.2f}"
                if g["n"] else f"{g['verdict']}; predicted {g['pred_bp']:+.1f}bp/trade")
        return dict(n=g["n"], week=wk, line=line)
    return read


def _m1_n2(state: Path, logs: Path) -> dict:
    from . import events as ev
    p = state / "book-daily-live.json"
    b = json.loads(p.read_text()) if p.exists() else {}
    g = ev.n2_score(b.get("closed", []), b.get("equity_log", []))
    wk = sum(1 for c in b.get("closed", []) if c.get("leg") == "night" and str(c.get("exit_date", "")) >= _week_ago()
             and c.get("exit_date") and dt.date.fromisoformat(c["exit_date"][:10]) in ev.release_mornings())
    stale = ev.release_stale_warning(dt.date.today())
    line = (f"{g['verdict']}; release nights {_bp(g['event_bp'])} vs other {_bp(g['other_bp'])} "
            f"(diff {_bp(g['diff_bp'])}, predicted {g['pred_bp']:+.1f}bp)") + (f"; {stale}" if stale else "")
    return dict(n=g["n"], week=wk, line=line)


def _cef_activist(state: Path, logs: Path) -> dict:
    from . import cef_activist_watch as c
    rows = _jsonl(state / c.LOG_NAME)
    g = c.gate(rows)
    wk = sum(1 for r in rows if str(r.get("seen", "")) >= _week_ago())
    line = (f"{g['verdict']}; mean {g['mean_excess']:+.2%} vs PCEF" if g["n"] else g["verdict"]) + f"; {len(rows)} logged"
    return dict(n=g["n"], week=wk, line=line)


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


def _nx_s2(state: Path, logs: Path) -> dict:
    """Taxable night exits since the profile went live (logs/daily-fills-live.jsonl); the increment itself is read in
    `make review` (night-leg P&L vs the 0.5 counterfactual on the same fills)."""
    rows = [r for r in _jsonl(logs / "daily-fills-live.jsonl")
            if r.get("leg") == "night" and r.get("side") == "sell" and str(r.get("filled_at", ""))[:10] >= "2026-10-10"]
    wk = [r for r in rows if str(r.get("filled_at", ""))[:10] >= _week_ago()]
    return dict(n=len(rows), week=len(wk),
                line=f"{len(rows)} taxable night exits since 2026-10-10 at the S2 weight; set DAILY_LIVE_PROFILE=nx_s2 "
                     "in .env on him to arm (null = base 0.5)")


def _letf_night(state: Path, logs: Path) -> dict:
    from . import letf_night_shadow as w
    rows = _jsonl(state / w.LOG_NAME)
    s = w.summary(rows)
    wk = {r["date"] for r in rows if r.get("treated") and r.get("status") == "scored" and r["date"] >= _week_ago()}
    return dict(n=s["days"], week=len(wk), line=w.line(rows))


def _gamma_state(state: Path, logs: Path) -> dict:
    from . import gamma_state_shadow as w
    rows = _jsonl(state / w.LOG_NAME)
    f = w.summary(rows, True)
    wk = [r for r in rows if r.get("status") == "scored" and r["date"] >= _week_ago()]
    return dict(n=f["short"]["n"], week=len(wk), line=w.line(rows))


def _log_tag(tag: str, sub: str = ""):
    """Count `[tag]` lines in the executor's daily logs (logs/daily-YYYY-MM-DD.log); 0 this week = silent.
    `sub` narrows to `[tag] sub...` (the night leg logs hundreds of `[night]` lines; AU3 is only `[night] tow`)."""
    pat = re.compile(r"\[" + re.escape(tag) + r"\] " + re.escape(sub) + r"\b" if sub else r"\[" + re.escape(tag) + r"[\]: ]")

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


def _fomc(state: Path, logs: Path) -> dict:
    """F3 only acts on the eve of a scheduled FOMC decision, so 'silent' is normal between meetings: say when the next eve is."""
    from . import events as ev
    read = _log_tag("fomc")(state, logs)
    nxt = ev.next_fomc(dt.date.today())
    since = [d for d in ev.fomc_dates() if "2026-09-22" <= str(d) <= str(dt.date.today())]
    tail = f"next decision {nxt} (eve = the night before)" if nxt else "FOMC calendar has run out"
    read["line"] = f"{read['week']} [fomc] log lines this week; {len(since)} FOMC decision(s) since 2026-09-22; {tail}"
    if not read["n"] and since and any(d < dt.date.today() for d in since):
        read["line"] += " (a decision has passed with no [fomc] line: check it runs)"
    return read


def _ibs_lev(state: Path, logs: Path) -> dict:
    from . import ibs_lev_shadow as s
    rows = s._read(state / s.LOG_NAME)
    wk = sum(1 for r in rows if r["date"] >= _week_ago())
    return dict(n=len(rows), week=wk, line=s.line(rows))


def _pick_cost(state: Path, logs: Path) -> dict:
    from . import pick_cost_watch as w
    rows = [r for r in w._jsonl(state / w.LOG_NAME) if "buy_cost_bp" in r]
    cheap = sum(1 for r in rows if r["bucket"] == "$5-10")
    wk = sum(1 for r in rows if r["buy_at"] >= _week_ago())
    return dict(n=cheap, week=wk, line=w.line(rows) if rows else "no live night trips scored yet (make pick-cost)")


def _pref_ex(state: Path, logs: Path) -> dict:
    from . import pref_ex_shadow as w
    rows = _jsonl(state / w.LOG_NAME)
    fwd = {r["ex"] for r in rows if r.get("status") == "scored" and r.get("eligible") and r["ex"] >= w.FORWARD_FROM
           and w._cls(r["sym"]) == "pref"}
    wk = sum(1 for d in fwd if d >= _week_ago())
    stk = _jsonl(state / w.STACK_LOG)
    extra = f" | ROTH-STACK {len(stk)} nights" + (f", last {stk[-1]['ex']} strict pref-first ${stk[-1]['alloc']['strict_pref']['usd']:.0f}"
                                                  if stk else " (snapshots from 2026-10-09)")
    return dict(n=len(fwd), week=wk, line=(w.lines(rows) if rows else "no events logged yet (make pref-ex)") + extra)


def _cef_rv(state: Path, logs: Path) -> dict:
    from . import cef_rv_shadow as w
    rows = [r for r in _jsonl(state / w.LOG_NAME) if r.get("signal", "") >= w.FORWARD_FROM]
    closed = [r for r in rows if r.get("status") == "closed" and "x_oo" in r]
    wk = sum(1 for r in closed if r.get("logged", "") >= _week_ago())
    return dict(n=len(closed), week=wk, line=w.line(_jsonl(state / w.LOG_NAME)) if rows or closed
                else "no forward signals yet (make cef-rv)")


def _hedge(state: Path, logs: Path) -> dict:
    from . import hedge_shadow as w
    rows = _jsonl(state / w.LOG_NAME)
    wk = sum(1 for r in rows if r["date"] >= _week_ago())
    return dict(n=len(rows), week=wk, line=w.line(rows) if rows else "no scored nights yet")


def _top2(state: Path, logs: Path) -> dict:
    from . import top2_shadow as w
    rows = [r for r in _jsonl(state / w.LOG_NAME) if r.get("judged")]
    wk = sum(1 for r in rows if r["date"] >= _week_ago())
    return dict(n=len(rows), week=wk, line=w.line(rows) if rows else "no judged nights yet")


def _crowd_hold(state: Path, logs: Path) -> dict:
    from . import crowd_hold_shadow as w
    rows = [r for r in _jsonl(state / w.LOG_NAME) if "hold_bp" in r]
    crowded = [r for r in rows if r["crowded"]]
    wk = sum(1 for r in crowded if r["date"] >= _week_ago())
    return dict(n=len(crowded), week=wk, line=w.line(rows) if rows else "no nights scored yet")


def _repeat(state: Path, logs: Path) -> dict:
    from . import repeat_shadow as w
    rows = _jsonl(state / w.LOG_NAME)
    w.flag(rows)
    rep = [r for r in rows if r.get("status") == "scored" and r.get("repeat")]
    wk = sum(1 for r in rep if r["date"] >= _week_ago())
    return dict(n=len(rep), week=wk, line=w.line(rows) if rows else "no candidates logged yet (first night run)")


def _exdate_open(state: Path, logs: Path) -> dict:
    from . import exdate_open_shadow as w
    rows = _jsonl(state / w.LOG_NAME)
    fwd = [r for r in rows if r.get("status") == "scored" and r.get("eligible") and not r.get("fund")
           and r["ex"] >= w.FORWARD_FROM]
    wk = sum(1 for r in fwd if r["ex"] >= _week_ago())
    return dict(n=len(fwd), week=wk, line=w.line(rows) if rows else "no events logged yet (make exdate-open)")


# ---------------------------------------------------------------- the list

def _tme_l(state: Path, logs: Path) -> dict:
    allr = _jsonl(state / "tme-shadow.jsonl")
    rows = [r for r in allr if r.get("status") == "scored"]
    scored = {r.get("T") for r in rows}
    stuck = sorted({r.get("T") for r in allr if r.get("status") == "missing_prints"} - scored)
    today = dt.date.today()
    last_me = today.replace(day=1) - dt.timedelta(days=1)                     # last weekday of the previous month
    while last_me.weekday() >= 5:                                              # (approx. month-end; holidays ignored)
        last_me -= dt.timedelta(days=1)
    overdue = (last_me >= dt.date(2026, 10, 30) and (today - last_me).days > 7
               and not any(str(x).startswith(last_me.strftime("%Y-%m")) for x in scored))
    warn = (f"; FAILED: {len(stuck)} window(s) awaiting prints ({', '.join(stuck)})" if stuck else "") + \
           (f"; OVERDUE: {last_me:%Y-%m} not scored (check make tme-shadow runs)" if overdue else "")
    if not rows:
        return dict(n=0, week=0, line="no forward window scored yet (first: Oct-2026 month-end; make tme-shadow)" + warn)
    wk = sum(1 for r in rows if str(r.get("T", "")) >= _week_ago())
    m = {k: sum(r["pnl"][k] for r in rows) / len(rows) for k in ("L1", "L2", "L3")}
    return dict(n=len(rows), week=wk, line=" ".join(f"{k} {_bp(v * 1e4)}" for k, v in m.items()) + " per window (of sleeve C)" + warn)

def _cpc(state: Path, logs: Path) -> dict:
    from . import cpc_ledger
    return cpc_ledger.digest_read(state, logs)


def _daybook(config: str):
    def read(state: Path, logs: Path) -> dict:
        from swingtrader.daybook import shadow as s
        rows = _jsonl(state / s.LOG_NAME)
        days = [r for r in rows if r.get("kind") == "daily" and r.get("config") == config]
        trades = [r for r in rows if r.get("kind") == "trade" and r.get("config") == config]
        n = len(days)
        wk = [r for r in days if str(r.get("date")) >= _week_ago()]
        if not days:
            return dict(n=0, week=0, line="no sessions logged")
        net = [r.get("net_return", 0.0) for r in days]
        mean = sum(net) / len(net)
        return dict(n=n, week=len(wk),
                    line=f"{n} sessions, mean {mean*1e4:+.1f}bp/day, {len(trades)} trades")
    return read


def _size(state: Path, logs: Path) -> dict:
    from . import size_shadow as s
    rows = _jsonl(state / s.LOG_NAME)
    wk = sum(1 for r in rows if str(r.get("date")) >= _week_ago())
    return dict(n=len(rows), week=wk, line=s.line(rows) if rows else "no sessions logged yet (make size-shadow)")


def _leap(state: Path, logs: Path) -> dict:
    rows = [r for r in _jsonl(logs / "leap-shadow.jsonl") if r.get("rule") == "ibs_fwd"]
    wk = sum(1 for r in rows if str(r.get("date")) >= _week_ago())
    if not rows:
        return dict(n=0, week=0, line="no SOXL IBS trade scored yet (make leap-shadow)")
    m = sum(r["r_bp"] for r in rows) / len(rows)
    return dict(n=len(rows), week=wk, line=f"{len(rows)} trades, mean {_bp(m)}/trade (2016-26 backtest: positive in every block)")


REGISTRY: list[Test] = [
    Test("Night auction cost by price bucket (pick-quality lead)", "do $5-10 night names really cost ~15bp/side live, or ~0 in the auctions? (gross bounce $5-10 +40bp vs $50+ ~0)",
         "2026-10-02", 100, "$5-10 live trips", _pick_cost, "make pick-cost; pick_quality_log.md", ["pick_cost_watch"]),
    Test("Book stacked on index beta (index-beat FOUND)", "taxable = SPY 1.0x + live legs on margin; Roth = 1/3 UPRO + 2/3 book: does it beat both the live accounts and SPY?",
         "2026-10-02", 250, "sessions", _stack, "make stack-shadow; study_ib_found_stack.md", ["stack_shadow"]),
    Test("Capacity shadow: live decisions at $30k/$100k/$250k", "where does the night leg stop scaling (net of square-root impact, % of ADV), and how far do whole MNQ contracts drift from the ideal noise leg?",
         "2026-10-05", 60, "sessions", _size, "make size-shadow; swingtrader/daily/size_shadow.py", ["size_shadow"]),
    Test("Leap SOXL IBS (forward)", "SOXL IBS < 0.2 -> next open to following open, scored forward from daily bars (no orders)",
         "2026-10-05", 40, "trades", _leap, "make leap-shadow; RESULTS.md addendum 24", ["leap"]),
    Test("IBS 1.25x 3x-ETF overlay (Study ACC)", "does the non-callable 1.25x 3x-ETF IBS overlay beat the live 1x leg forward, "
         "inside a 25% DD budget? (kill: maxDD < -25% or delta <= 0 at 60 sessions)",
         "2026-10-05", 60, "sessions", _ibs_lev, "make ibs-lev-shadow; study_acc_account_structure.md",
         ["ibs_lev_shadow"]),
    Test("Insider-day (ID3)", "buy the open / sell the close the session after an officer/director buy",
         "2026-10-02", 300, "scored trades", _insider(None), "make forward-status", ["insider_shadow", "insider_day"]),
    Test("EV2: first insider buy in 2+ years", "is ID3 ~2x stronger when nobody bought in the open market for 2 years?",
         "2026-10-02", 60, "scored EV2 trades", _insider("ev2"), "make forward-status; study_ev2_first_insider_buy.md"),
    Test("EV2 x buy >= $500k", "post-judge cut (forward data only): EV2 names with a big purchase",
         "2026-10-02", 60, "scored trades", _insider("ev2_big"), "make forward-status; study_ev2_first_insider_buy.md"),
    Test("ID3 x buy >= $500k (any silence)", "Goal G3: does the buy SIZE alone carry ID3? (holdout report row +35.7bp)",
         "2026-10-02", 60, "scored trades", _insider("id3_big"), "make forward-status; study_goal_g2.md"),
    Test("M1 ID1: every insider buy, ADV >= $1M", "Track M1: killed only on judge t 1.18; is the forward mean > 0 "
         "(predicted +14.6bp/trade at live cost)?", "2026-10-05", 5400, "scored trades", _m1_insider("id1"),
         "make insider-shadow; round1_prose.md Methodology track M1"),
    Test("M1 ID2: insider buy, ADV $1-20M", "Track M1: killed only on judge t 0.86; forward mean > 0 (predicted +15.6bp)?",
         "2026-10-05", 2650, "scored trades", _m1_insider("id2"), "make insider-shadow; round1_prose.md Methodology track M1"),
    Test("M1 EV1: cluster insider buys", "Track M1: 2+ officer/director buy filings within 5 days, killed only on judge "
         "t 1.85; forward mean > 0 (predicted +20.5bp)?", "2026-10-05", 560, "scored trades", _m1_insider("ev1"),
         "make insider-shadow; round1_prose.md Methodology track M1"),
    Test("M1 N2: night leg on CPI/NFP mornings", "Track M1: does the live night leg earn more on nights into an 08:30 "
         "CPI/NFP release (predicted +8.8bp of equity vs other nights)?", "2026-10-05", 48, "release nights", _m1_n2,
         "make testing; round1_prose.md Methodology track M1"),
    Test("CEF activist 13D (G45-F)", "does the first activist 13D on a closed-end fund beat PCEF by >= 1.5% over 60 sessions?",
         "2026-10-02", 30, "scored events", _cef_activist, "make cef-activist-watch; study_goal_g45.md", ["cef_activist_watch"]),
    Test("Odd-lot tenders", "issuer tenders with odd-lot priority >= 1% over market (manual, <= 99 shares)",
         "2026-10-02", 0, "alerts", _alerts("tender-watch.jsonl", "tenders"), "make tender-watch",
         ["tender_watch", "tender_buy"]),
    Test("Split-off exchange offers", "odd lots accepted in full in split-off exchange offers (manual)",
         "2026-10-02", 0, "alerts", _alerts("splitoff-watch.jsonl", "offers"), "make splitoff-watch", ["splitoff_watch"]),
    Test("Reverse-split round-up", "1 share before a reverse split that rounds fractions up (manual)",
         "2026-10-02", 0, "alerts", _alerts("roundup-watch.jsonl", "splits"), "make roundup-watch", ["roundup_watch"]),
    Test("Forced-flow discovery (EDGAR forms)", "does the SC 14D-9 / DEFM14C / 425 / 8-K 2.01+5.01 / 25-NSE / "
         "S-4 / SC 13E3 scanner surface per-holder-capped, guaranteed-floor events? (discovery only)",
         "2026-10-05", 0, "candidates", _alerts("forced-flow-discovery.jsonl", "filings"),
         "make forced-flow-discovery", ["forced_flow_discovery"]),
    Test("LLM news judge", "does Claude's 'fundamental' label pick the night picks that keep falling?",
         "2026-09-24", 300, "picks judged", _news, "make forward-status", ["news_judge"]),
    Test("15:40 quote imbalance", "does the bid/ask size at 15:40 predict the night pick's bounce?",
         "2026-09-24", 300, "picks logged", _quote_imbalance, "make forward-status"),
    Test("Conviction trade (shadow)", "TQQQ conviction weight on breakout days, logged not traded",
         "2026-09-22", 0, "log lines", _log_tag("conv"), "make review section 7", ["conviction_mode"]),
    Test("Oversold index buy (V6) + Roth A2", "SPY/QQQ close -> open after 3 down closes / RSI(2) < 10",
         "2026-09-22", 0, "log lines", _log_tag("oversold"), "make review", ["oversold_mode"]),
    Test("FOMC-eve QQQ filler (F3)", "QQQ close -> open on spare night cash before FOMC decisions",
         "2026-09-22", 0, "log lines", _fomc, "make review", ["fomc_filler_mode"]),
    Test("Roth night cash (M2L)", "requested vs funded night notional in the Roth",
         "2026-09-22", 0, "log lines", _log_tag("roth-cash"), "make review", ["roth_night_cash_log"]),
    Test("Lever gate G1", "day-clustered 95% upper-bound gate beside the live lever gate",
         "2026-09-22", 0, "log lines", _log_tag("lever-g1"), "make review", ["lever_g1_log"]),
    Test("NX-S2 night size-up (taxable, profile nx_s2)", "night leg at 0.65 (IBS 0.5, cap .15) on the margin book: does "
         "the +0.59bp/night NX increment show up live while auction cost stays ~0bp?",
         "2026-10-10", 0, "night exits", _nx_s2, "deploy_loop_2026-10-10.md item 3; make review 2b/4", ["nx_s2"]),
    Test("Wash guard G4s", "what the Roth-first wash-sale guard would change vs the live one",
         "2026-09-22", 0, "log lines", _log_tag("wash-guard"), "make review", ["wash_guard_mode"]),
    Test("Tug-of-war night tilt (AU3)", "tilt night picks by the tug-of-war score (logged, not sized)",
         "2026-09-22", 0, "log lines", _log_tag("night", "tow"), "make review section 9 (SINCE=2026-09-22)"),
    Test("TME-L: leveraged month-end Treasury sleeve", "does 2x (TLT on margin) / 3x (TMF) keep >= 80% / 73% of "
         "the theoretical multiple of the VALIDATED month-end TLT window without breaching the tail limits?",
         "2026-10-27", 24, "month-end windows", _tme_l, "make tme-shadow; round1_prose.md Study TME-L",
         ["tme_shadow"]),
    Test("CPC forward validation", "do the personal-scale contract payoffs (UMH plan cash, odd-lot tenders, split-off "
         "priority, round-ups) pay forward: >= 2 independent events, >= +8pp/yr at $10k after costs and 35% tax, "
         "not one event, over ~12 months (personal-scale economics, not scalable alpha)?",
         "2026-10-04", 2, "independent completed events", _cpc, "make cpc-status; research/drafts/study_cpc.md",
         ["cpc_ledger"]),
    Test("PREF-EX: preferred ex-dividend auction capture", "buy a $25-par preferred's closing cross before its "
         "ex-date, sell the ex-date opening cross (CO) or closing cross (CC, MOC both legs): does the ~0.8x-dividend "
         "drop (official 2021-26 CO +38bp, CC +28bp) survive forward net of 10bp + impact at a $10k Roth, 5% of the "
         "auction? Also logs ETDX (baby bonds, same rule, official CO +44bp / CC +39bp), gated separately; the PREF-CHAIN arm (buy "
         "the close 10 sessions earlier, vs PFF; added 2026-10-08; own gate at 60 forward nights: >= +20bp vs PFF net of "
         "MEASURED cost, t >= 2, and beats T-1) and the measured closing-cross cost vs the 15:59 mid. ROTH-STACK arm (from 2026-10-09, log-only): each ex-eve "
         "snapshots the cash-Roth idle cash and logs strict/lenient x PREF-first/night-first whole-share allocation at the 5% "
         "cap plus realized CC cost vs the 10bp assumption (state/pref-ex-roth-stack.jsonl; research/sim/roth_stack.py).",
         "2026-10-07", 60, "forward ex-nights", _pref_ex,
         "make pref-ex; research/sim/pref_exec_out.txt; round1_prose.md Study PREF-EX", ["pref_ex_shadow"]),
    Test("CEF-RV: CEF discount reversion vs the CEF universe", "buy a CEF at its own 52-week 10th-percentile "
         "discount (weekly NAV), sell at its median: does it beat the equal-weight CEF universe forward (research "
         "+125bp/trade 2016-26, t 5.6; raw is ~2/3 market) at official opening crosses, net 50bp? Gate: excess >= +60bp, "
         "t >= 2 across >= 10 entry weeks; kill <= 0. Each trade also carries cut42 (distribution cut 0-42 days before the "
         "signal; research -255bp vs the rest, not validated), read beside the gate.", "2026-10-09", 60, "closed forward trades", _cef_rv,
         "make cef-rv; research/sim/cef_alpha_out.txt; round1_prose.md Study CEF-ALPHA / CEF-RV-FWD",
         ["cef_rv_shadow"]),
    Test("Hedge: online learner over night filter configs", "exponential weights (eta 0.5) over 12 fixed night configs "
         "(cutoff -8/-10/-12/-15% x top-k all/2/4), trained only on forward nights; does the config it picks each night beat "
         "the fixed live rule? Gate: chosen - live >= +10bp/night, t >= 2, halves > 0; kill <= 0.", "2026-10-10", 120,
         "scored nights", _hedge, "state/hedge-shadow.jsonl; round1_prose.md HEDGE-SHADOW", ["hedge_shadow"]),
    Test("TOP2: night leg on only the 2 deepest drops", "every night-rule signal scored close cross -> next opening "
         "cross (repeat_shadow): does keeping only the night's 2 deepest drops beat the equal-weight night risk-adjusted "
         "(judge 1999-2015 +14bp/night t 3.4, Sharpe 2.34 vs 2.21; 2016-26 same Sharpe at 1.57x std = mostly leverage)? "
         "Gate: diff >= +10bp, t >= 2, halves > 0 and TOP2 Sharpe > base; kill <= 0.", "2026-10-10", 60,
         "judged nights", _top2, "state/top2-shadow.jsonl; round1_prose.md Study CAT-MOM + DEPTH", ["top2_shadow"]),
    Test("LETF-NIGHT: single-stock LETF close rebalancing -> overnight reversal", "names down <= 5% with lagged single-stock "
         "LETF $vol share > 2%: closing cross -> next opening cross vs the no-LETF control (forward-only registration, N 852)",
         "2026-10-10", 120, "event days", _letf_night, "state/letf-night.jsonl; round1_prose.md Amendment LETF-NIGHT",
         ["letf_night_shadow"]),
    Test("GAMMA-FREE: SPY last-30-min continuation on short-gamma days", "free SqueezeMetrics GEX sign (prior session) -> SPY "
         "15:30 -> closing-cross continuation vs long-gamma days (the $0 falsification before any OPRA purchase, N 932)",
         "2026-10-10", 120, "short-gamma days", _gamma_state, "state/gamma-state.jsonl; round1_prose.md Amendment GAMMA-FREE",
         ["gamma_state_shadow"]),
    Test("Crowded-night hold (OPENSIG lead): hold night picks to the close cross", "every night-rule signal is "
         "scored close cross -> next opening cross -> its closing cross: on crowded nights (>= 16 signals) does holding "
         "to the close beat selling at the open (research: per-trade gains sit on crowded washout days; per-day "
         "OPENSIG null, both windows touched)? Gate: crowded-night mean >= +20bp, t >= 2, halves > 0, median > 0; "
         "kill <= 0. Thin nights are the control.", "2026-10-09", 30, "crowded nights scored", _crowd_hold,
         "state/crowd-hold.jsonl; round1_prose.md Study OPENSIG / CROWD-HOLD", ["crowd_hold_shadow"]),
    Test("Repeat loser (L1): night signals picked again within 5 sessions", "every 15:40 night-rule signal is "
         "logged (before dedupe / vol / cash / wash filters) and scored close cross -> next opening cross: do repeats "
         "(same symbol a signal 1-5 sessions earlier) out-bounce first-time signals forward (research +85..+103bp "
         "night-paired, t 3.4-4.1, tail-driven)? Gate: paired >= +30bp, t >= 2, halves same sign; kill <= 0.",
         "2026-10-08", 150, "scored repeat candidates", _repeat,
         "state/night-candidates.jsonl; research/drafts/window_signals_loop_2026-10-07.md rounds 6/8/37",
         ["repeat_shadow"]),
    Test("Ex-date open: split + spin-off night (SPLIT-T0 / SPIN-T0)", "close cross before a forward-split or "
         "spin-off ex-date -> ex-date opening cross (parent + child): does the retail open premium (official 2016-20 "
         "split median +57bp, 2021-26 +17bp; spins +54bp) hold forward on common stocks?",
         "2026-10-07", 40, "forward common-stock events", _exdate_open,
         "make exdate-open; research/drafts/golden_egg_2026-10-06.md", ["exdate_open_shadow"]),
    Test("Daybook PROD (QQQ+SMH noise, forward)", "production-equivalent intraday noise leg, replayed as a "
         "no-order forward shadow: does the edge survive live (esp. the 2024-26 decay)?",
         "2026-10-04", 60, "sessions", _daybook("PROD"), "make daybook-shadow; make daybook-report",
         ["daybook_shadow"]),
    Test("Daybook Config B (moderate risk)", "QQQ/SMH core + conviction TQQQ/SOXL at 0.02 vol target; "
         "does the leveraged basket beat the production leg forward net of realistic fills?",
         "2026-10-04", 60, "sessions", _daybook("B"), "make daybook-shadow; make daybook-report",
         ["daybook_shadow"]),
    Test("Daybook Config C (high risk, research-only)", "2x risk profile (0.04 vol target, 7x cap) — "
         "is the 43% historical CAGR reproducible forward, or does the drawdown dominate?",
         "2026-10-04", 60, "sessions", _daybook("C"), "make daybook-shadow; make daybook-report",
         ["daybook_shadow"]),
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
