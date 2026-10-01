"""Weekly digest: balances, every switch's gate, what each shadow idea would have made on the real
days so far, and where the accounts end up in 1 / 3 / 5 years with and without the levers.

    python scripts/weekly_digest.py            # print
    python scripts/weekly_digest.py --send     # print + email (Resend, NOTIFY_EMAIL)

Two kinds of "what if" numbers, labelled as such:
- REALIZED: the shadow logs replayed on the account's actual trades/days (small n early on: noise).
- PROJECTED: compound growth at planning rates (PLAN below; the honest, haircut numbers from the
  Round 19-25 summary), not forecasts. Deposits included (Roth $7,500/yr).
Read-only: never touches a book, an order or a switch.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import signals as sg

# ---------------------------------------------------------------- planning assumptions
# Realistic (haircut) yearly rates, pre-tax, from study_round19_summary + the session's guidance:
# base = the live book as it runs today; each lever = its probability-weighted gain if switched on.
PLAN = {
    "taxable": {"base": 0.17, "levers": {"conviction": 0.014, "intraday_x4": 0.005, "overnight_1.3x": 0.018,
                                         "tow_tilt": 0.006, "llm_judge": 0.005, "quote_imbalance": 0.003}},
    "roth":    {"base": 0.15, "levers": {"tow_tilt": 0.006, "llm_judge": 0.005, "quote_imbalance": 0.003}},
}
ROTH_DEPOSIT_YR = 7500.0
TAXABLE_TAX = 0.32                      # short-term federal + state, the program's planning rate
HORIZONS = (1, 3, 5)
LEVER_LABEL = {"conviction": "conviction trade", "intraday_x4": "4x intraday margin",
               "overnight_1.3x": "overnight 1.3x", "tow_tilt": "tug-of-war tilt",
               "llm_judge": "LLM news judge", "quote_imbalance": "quote imbalance"}


def project(start: float, rate: float, years: int, deposit_yr: float = 0.0) -> float:
    """Monthly compounding with deposits spread monthly."""
    e, m = start, (1 + rate) ** (1 / 12) - 1
    for _ in range(12 * years):
        e = e * (1 + m) + deposit_yr / 12
    return e


def projections(balances: dict, taxable_monthly: float = 0.0) -> list[dict]:
    rows = []
    for acct, bal in balances.items():
        kind = "roth" if acct == "roth" else "taxable"
        p = PLAN[kind]
        dep = ROTH_DEPOSIT_YR if kind == "roth" else 12 * taxable_monthly
        up = p["base"] + sum(p["levers"].values())
        for y in HORIZONS:
            a, b = project(bal, p["base"], y, dep), project(bal, up, y, dep)
            rows.append(dict(account=acct, years=y, without=a, with_levers=b, deposits=dep * y,
                             base_rate=p["base"], lever_rate=up))
    return rows


# ---------------------------------------------------------------- inputs
def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


@dataclass
class Account:
    name: str
    equity: float
    week_ago: float | None
    closed: list
    conviction: list
    oversold: list
    fomc: list
    equity_log: list


def load_account(name: str, state: Path, start_equity: float) -> Account | None:
    from .book import DailyBook, book_file
    f = state / book_file(name)
    if not f.exists():
        return None
    b = DailyBook.load(state, start_equity, book_file(name))
    eq = b.equity_log[-1]["equity"] if b.equity_log else b.cash
    cut = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    old = [e["equity"] for e in b.equity_log if e["date"] <= cut]
    return Account(name, float(eq), float(old[-1]) if old else None, list(b.closed),
                   list(b.conviction.get("history", [])), list(b.oversold.get("history", [])),
                   list(b.fomc.get("history", [])), list(b.equity_log))


# ---------------------------------------------------------------- realized "what if"
def _night_trades(acct: Account) -> list[dict]:
    return [c for c in acct.closed if c.get("leg") == "night"]


def whatif_realized(acct: Account, decisions: list[dict], verdicts: dict, conviction_w: float) -> list[dict]:
    """$ the account would have made or lost from each shadow idea, on its real trades so far."""
    out = []
    eq_on = {e["date"]: e["equity"] for e in acct.equity_log}
    # conviction trade: weight x equity that day x the shadow's net return on TQQQ
    if acct.conviction:
        usd = sum(conviction_w * eq_on.get(x["date"], acct.equity) * x["ret"] for x in acct.conviction)
        out.append(dict(idea="conviction trade", n=len(acct.conviction), usd=usd))
    if acct.oversold:
        k = "usd_a2" if any("usd_a2" in x for x in acct.oversold) else "usd"
        out.append(dict(idea="oversold SPY/QQQ (V6)", n=len(acct.oversold),
                        usd=sum(x["ret"] * x.get(k, 0.0) for x in acct.oversold)))
    if acct.fomc:
        out.append(dict(idea="FOMC-eve QQQ", n=len(acct.fomc),
                        usd=sum(x["ret"] * x.get("usd", 0.0) for x in acct.fomc)))
    night = _night_trades(acct)
    dec = {(d.get("date"), d.get("sym")): d for d in decisions}
    # tug-of-war tilt: re-weight each night's trades by TOW (mean-preserving), $ change = sum (w-1) pnl
    by_night: dict = {}
    for c in night:
        d = dec.get((c.get("entry_date"), c["sym"]))
        if d is not None:
            by_night.setdefault(c["entry_date"], []).append((c, d))
    tow_usd, tow_n, qi_usd, qi_n = 0.0, 0, 0.0, 0
    for day, rows in by_night.items():
        tows = np.array([np.nan if r[1].get("tow") is None else float(r[1]["tow"]) for r in rows])
        if np.isfinite(tows).any():
            w = sg.night_tilt_tow(np.ones(len(rows)), tows)
            tow_usd += float(sum((wi - 1) * r[0]["pnl"] for wi, r in zip(w, rows))); tow_n += len(rows)
        bs = np.array([r[1].get("bid_size") or np.nan for r in rows], float)
        as_ = np.array([r[1].get("ask_size") or np.nan for r in rows], float)
        ok = np.isfinite(bs) & np.isfinite(as_) & ((bs + as_) > 0)
        if ok.any():
            qi = np.where(ok, (bs - as_) / np.where(ok, bs + as_, 1), 0.0)
            w = np.clip(1 + 0.5 * qi, 0.5, 1.5); w = w / w.mean()
            qi_usd += float(sum((wi - 1) * r[0]["pnl"] for wi, r in zip(w, rows))); qi_n += int(ok.sum())
    if tow_n:
        out.append(dict(idea="tug-of-war tilt", n=tow_n, usd=tow_usd))
    if qi_n:
        out.append(dict(idea="quote imbalance tilt", n=qi_n, usd=qi_usd))
    # LLM judge BA1: picks judged fundamental with confidence >= 0.7 at weight 0.25
    hit = [(c, verdicts[(c.get("entry_date"), c["sym"])]) for c in night if (c.get("entry_date"), c["sym"]) in verdicts]
    if hit:
        usd = sum(-0.75 * c["pnl"] for c, v in hit if v.get("verdict") == "fundamental" and (v.get("confidence") or 0) >= 0.7)
        out.append(dict(idea="LLM news judge (x0.25 on 'fundamental')", n=len(hit), usd=usd))
    return out


# ---------------------------------------------------------------- gates
def gates(accts: dict, logs: Path, state: Path) -> list[dict]:
    live = accts.get("live")
    fl = _jsonl(logs / "daily-fills-live.jsonl")
    fr = _jsonl(logs / "daily-fills-roth.jsonl")
    intraday_days = sorted({r.get("filled_at", "")[:10] for r in fl if r.get("leg") == "noise"})
    night_sells = [r for r in fl if r.get("leg") == "night" and r.get("side") == "sell"]
    roth_night = [r for r in fr if r.get("leg") == "night"]
    rt = len(_night_trades(live)) if live else 0
    verdicts = [v for v in _jsonl(state / "news-judge.jsonl") if v.get("verdict")]
    snaps = {(d.get("date"), d.get("sym")) for f in logs.glob("daily-decisions*.jsonl")
             for d in _jsonl(f) if d.get("bid_size") is not None}

    def row(name, n, need, action, where, note=""):
        return dict(gate=name, n=n, need=need, ready=n >= need, action=action, where=where, note=note)

    ms = np.mean([r["slippage_bps"] for r in night_sells]) if night_sells else float("nan")
    return [
        row("Conviction trade on", len(intraday_days), 5, "DAILY_LIVE_PROFILE=moderate10c in .env",
            "make review §7", "days with live intraday fills; §7 must call them clean"),
        row("4x intraday margin", len(intraday_days), 15, "DAILY_INTRADAY_MULT=4 in .env",
            "Schwab.com Balances", "2 weeks after conviction, and Intraday BP >= 3.5x equity"),
        row("Overnight 1.3x", len(night_sells), sg.LEVER_MIN_EXITS, "lever_weight: 0.65 in config.yaml",
            "make review §2b", f"needs mean <= {sg.LEVER_MAX_EXIT_BPS:g}bp vs the auction (vs decision ref now {ms:+.1f}bp)"),
        row("Roth night cost check", len(roth_night), 20, "if > ~3bp/side vs auction: Roth IBS-only",
            "make review §2 (roth)"),
        row("Tug-of-war tilt", rt, sg.TOW_GATE_N, "night_tilt_tow: true in config.yaml (if §9 says on)",
            "make review §9"),
        row("LLM news judge verdict", len(verdicts), 300, "verdict read once", "make forward-status"),
        row("Quote imbalance verdict", len(snaps), 300, "verdict read once", "make forward-status"),
    ]


# ---------------------------------------------------------------- render
def money(x: float) -> str:
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"


def build(state: Path, logs: Path, start_equity: float, conviction_w: float, taxable_monthly: float = 0.0):
    accts = {n: a for n in ("live", "roth", "paper") if (a := load_account(n, state, start_equity))}
    decisions = [d for f in logs.glob("daily-decisions*.jsonl") for d in _jsonl(f)]
    verdicts = {(v["date"], v["sym"]): v for v in _jsonl(state / "news-judge.jsonl") if v.get("verdict")}
    real = {n: a for n, a in accts.items() if n in ("live", "roth")}
    bal = {n: a.equity for n, a in real.items()}
    return dict(accounts=accts, gates=gates(accts, logs, state),
                whatif={n: whatif_realized(a, decisions, verdicts, conviction_w) for n, a in accts.items()},
                proj=projections(bal, taxable_monthly))


def render(d: dict) -> tuple[str, str, str]:
    """(subject, html, text)."""
    A, G = d["accounts"], d["gates"]
    T = []
    for n in ("live", "roth", "paper"):
        a = A.get(n)
        if a:
            wk = f"{money(a.equity - a.week_ago)} this week" if a.week_ago is not None else "first week"
            T.append(f"{n:5s} {money(a.equity):>9s}  ({wk})")
    T.append("")
    nxt = next((g for g in G if not g["ready"]), None)
    ready = [g for g in G if g["ready"] and not g["action"].startswith("verdict")]
    T.append("GATES (flip one at a time, >= 2 weeks apart)")
    for g in G:
        T.append(f"  [{'READY' if g['ready'] else ' .. '}] {g['gate']:26s} {g['n']:>4}/{g['need']:<4} "
                 f"-> {g['action']}  ({g['where']}{'; ' + g['note'] if g['note'] else ''})")
    T.append("")
    T.append("IF IT HAD BEEN ON (realized, on your actual days; small samples are noise)")
    for n, rows in d["whatif"].items():
        for r in rows:
            T.append(f"  {n:5s} {r['idea']:42s} n {r['n']:>4}  {money(r['usd']):>8s}")
    if not any(d["whatif"].values()):
        T.append("  (no shadow results yet)")
    T.append("")
    T.append("PROJECTED (planning rates, not forecasts; Roth incl. $7,500/yr deposits; taxable pre-tax)")
    for p in d["proj"]:
        extra = p["with_levers"] - p["without"]
        T.append(f"  {p['account']:5s} {p['years']}y  without {money(p['without']):>9s}  "
                 f"with levers {money(p['with_levers']):>9s}  (+{money(extra)}; "
                 f"{p['base_rate']:.0%} vs {p['lever_rate']:.0%}/yr"
                 + (f"; {money(p['deposits'])} of it deposits" if p["deposits"] else "") + ")")
    tax = [p for p in d["proj"] if p["account"] == "live"]
    if tax:
        p5 = tax[-1]
        T.append(f"  live after {TAXABLE_TAX:.0%} short-term tax, {p5['years']}y: without "
                 f"{money(p5['without'] - (p5['without'] - A['live'].equity) * TAXABLE_TAX)}, with levers "
                 f"{money(p5['with_levers'] - (p5['with_levers'] - A['live'].equity) * TAXABLE_TAX)} (approx.)")
    T.append("")
    T.append("PER LEVER, if it works (planning gain x today's balance, per year)")
    for acct in ("live", "roth"):
        if acct in A:
            kind = "roth" if acct == "roth" else "taxable"
            for k, v in PLAN[kind]["levers"].items():
                T.append(f"  {acct:5s} {LEVER_LABEL[k]:22s} +{v*100:.1f}pp = +{money(v * A[acct].equity)}/yr")
    text = "\n".join(T)
    live = A.get("live"); roth = A.get("roth")
    subj = ("Weekly: " + ", ".join(f"{n} {money(a.equity)}" for n, a in (("live", live), ("roth", roth)) if a)
            + (f" — ready: {ready[0]['gate']}" if ready else (f" — next: {nxt['gate']}" if nxt else "")))
    html = "<pre style='font-family:ui-monospace,Menlo,monospace;font-size:13px'>" + (
        text.replace("&", "&amp;").replace("<", "&lt;")) + "</pre>"
    return subj, html, text
