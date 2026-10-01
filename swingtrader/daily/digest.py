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
    week_pnl: float
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
    # what the TRADES made this week: equity also moves with deposits / DAILY_*_CAPITAL
    wk = sum(float(c.get("pnl", 0.0)) for c in b.closed if str(c.get("exit_date", "")) > cut)
    return Account(name, float(eq), float(old[-1]) if old else None, wk, list(b.closed),
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

    def row(name, n, need, action, where, note="", unit=""):
        return dict(gate=name, n=n, need=need, ready=n >= need, action=action, where=where, note=note, unit=unit)

    ms = np.mean([r["slippage_bps"] for r in night_sells]) if night_sells else float("nan")
    return [
        row("Conviction trade on", len(intraday_days), 5, "DAILY_LIVE_PROFILE=moderate10c in .env",
            "make review §7", "days with live intraday fills; §7 must call them clean", "intraday days"),
        row("4x intraday margin", len(intraday_days), 15, "DAILY_INTRADAY_MULT=4 in .env",
            "Schwab.com Balances", "2 weeks after conviction, and Intraday BP >= 3.5x equity", "intraday days"),
        row("Overnight 1.3x", len(night_sells), sg.LEVER_MIN_EXITS, "lever_weight: 0.65 in config.yaml",
            "make review §2b", f"needs mean <= {sg.LEVER_MAX_EXIT_BPS:g}bp vs the auction (vs decision ref now {ms:+.1f}bp)", "night exits"),
        row("Roth night cost check", len(roth_night), 20, "if > ~3bp/side vs auction: Roth IBS-only",
            "make review §2 (roth)", unit="Roth night fills"),
        row("Tug-of-war tilt", rt, sg.TOW_GATE_N, "night_tilt_tow: true in config.yaml (if §9 says on)",
            "make review §9", unit="night trades"),
        row("LLM news judge verdict", len(verdicts), 300, "verdict read once", "make forward-status", unit="picks judged"),
        row("Quote imbalance verdict", len(snaps), 300, "verdict read once", "make forward-status", unit="picks logged"),
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


NAME = {"live": "Brokerage", "roth": "Roth IRA"}
C = dict(bg="#f3f4f6", card="#ffffff", ink="#111827", mute="#6b7280", line="#e5e7eb",
         up="#047857", down="#b91c1c", accent="#2563eb", ready="#ecfdf5", next="#eff6ff")
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif"  # no quotes: it sits inside style='...'


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _signed(x: float) -> str:
    return ("+" if x >= 0 else "-") + f"${abs(x):,.0f}"


def _bar(frac: float, color: str) -> str:
    w = max(0, min(100, round(frac * 100)))
    return (f"<div style='background:{C['line']};border-radius:4px;height:8px;width:100%'>"
            f"<div style='background:{color};border-radius:4px;height:8px;width:{w}%'></div></div>")


def _plan(G: list) -> tuple[dict | None, list, list]:
    """(the one next step, the following switches, the running experiments)."""
    switches = [g for g in G if not g["action"].startswith("verdict")]
    tests = [g for g in G if g["action"].startswith("verdict")]
    ready = [g for g in switches if g["ready"]]
    step = ready[0] if ready else next((g for g in switches if not g["ready"]), None)
    rest = [g for g in switches if g is not step and not g["ready"]][:3]
    return step, rest, tests


def render(d: dict) -> tuple[str, str, str]:
    """(subject, html, text)."""
    A, G = d["accounts"], d["gates"]
    real = [(n, A[n]) for n in ("live", "roth") if n in A]
    step, rest, tests = _plan(G)
    ideas = [(n, r) for n, rows in d["whatif"].items() if n in ("live", "roth") for r in rows if r["n"]]
    proj = {(p["account"], p["years"]): p for p in d["proj"]}
    far = max(HORIZONS)

    # ---------------- plain text (terminal)
    T = []
    for n, a in real:
        wk = f"  {_signed(a.week_pnl)} from trades this week"
        T.append(f"{NAME[n]:10s} {money(a.equity):>9s}{wk}")
    if step:
        T += ["", ("READY: " if step["ready"] else "NEXT: ") + f"{step['gate']}  "
              f"({min(step['n'], step['need'])} of {step['need']} {step['unit']})",
              f"  then: {step['action']}"]
    if rest:
        T += ["", "Coming up: " + " · ".join(f"{g['gate']} {g['n']}/{g['need']}" for g in rest)]
    if tests:
        T.append("Experiments: " + " · ".join(f"{g['gate'].replace(' verdict', '')} {g['n']}/{g['need']}" for g in tests))
    if ideas:
        T += ["", "If these had been on:"] + [f"  {NAME[n]:10s} {r['idea'][:34]:34s} {_signed(r['usd']):>7s}" for n, r in ideas]
    T.append("")
    for n, a in real:
        p = proj.get((n, far))
        if p:
            T.append(f"In {far} years, {NAME[n]}: {money(p['without'])} as is, {money(p['with_levers'])} with everything on")
    text = "\n".join(T)

    # ---------------- HTML (email)
    def card(inner: str, bg: str = C["card"]) -> str:
        return (f"<tr><td style='font-family:{FONT};padding:0 0 12px'><div style='font-family:{FONT};background:{bg};border-radius:12px;"
                f"padding:18px 20px;border:1px solid {C['line']}'>{inner}</div></td></tr>")

    def h(s: str) -> str:
        return f"<div style='font-family:{FONT};font-size:13px;color:{C['mute']};font-weight:600;letter-spacing:.02em;margin-bottom:10px'>{s}</div>"

    H = []
    cells = []
    for i, (n, a) in enumerate(real):
        gut = "0 6px 0 0" if i == 0 else "0 0 0 6px"
        x = a.week_pnl
        chg = (f"<div style='font-family:{FONT};font-size:14px;color:{C['up'] if x >= 0 else C['down']};margin-top:2px'>"
               f"{_signed(x)} from trades this week</div>")
        cells.append(f"<td style='font-family:{FONT};width:50%;vertical-align:top;padding:{gut}'><div style='font-family:{FONT};background:{C['card']};"
                     f"border-radius:12px;padding:16px 18px;border:1px solid {C['line']}'>"
                     f"<div style='font-family:{FONT};font-size:13px;color:{C['mute']}'>{NAME[n]}</div>"
                     f"<div style='font-family:{FONT};font-size:28px;font-weight:700;color:{C['ink']};margin-top:2px'>{money(a.equity)}</div>"
                     f"{chg}</div></td>")
    if cells:
        H.append(f"<tr><td style='font-family:{FONT};padding:0 0 12px'><table role='presentation' width='100%' cellspacing='0' "
                 f"cellpadding='0' style='font-family:{FONT};table-layout:fixed'><tr>{''.join(cells)}</tr></table></td></tr>")
    if step:
        k = min(step["n"], step["need"]) / step["need"]
        lab = "Ready to switch on" if step["ready"] else "Next step"
        col = C["up"] if step["ready"] else C["accent"]
        H.append(card(
            f"<div style='font-family:{FONT};font-size:13px;font-weight:600;color:{col};margin-bottom:4px'>{lab}</div>"
            f"<div style='font-family:{FONT};font-size:20px;font-weight:700;color:{C['ink']};margin-bottom:10px'>{_esc(step['gate'])}</div>"
            + _bar(k, col)
            + f"<div style='font-family:{FONT};font-size:13px;color:{C['mute']};margin:6px 0 12px'>"
              f"{min(step['n'], step['need'])} of {step['need']} {_esc(step['unit'])}</div>"
            + f"<div style='font-family:{FONT};font-size:14px;color:{C['ink']}'>{'Do now' if step['ready'] else 'When full'}: "
              f"<code style='font-family:ui-monospace,Menlo,Consolas,monospace;background:{C['bg']};padding:2px 6px;border-radius:4px;font-size:12px;word-break:break-all'>"
              f"{_esc(step['action'])}</code></div>",
            C["ready"] if step["ready"] else C["next"]))
    if rest or tests:
        rows = ""
        for g in rest + tests:
            k = min(g["n"], g["need"]) / g["need"]
            rows += (f"<tr><td style='font-family:{FONT};padding:6px 0;font-size:14px;color:{C['ink']};width:46%'>"
                     f"{_esc(g['gate'].replace(' verdict', ''))}</td>"
                     f"<td style='font-family:{FONT};padding:6px 10px;width:38%'>{_bar(k, C['accent'] if g in rest else '#9ca3af')}</td>"
                     f"<td style='font-family:{FONT};padding:6px 0;font-size:13px;color:{C['mute']};text-align:right;white-space:nowrap'>"
                     f"{g['n']}/{g['need']}</td></tr>")
        H.append(card(h("COMING UP") + f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0'>{rows}</table>"))
    if ideas:
        rows = ""
        for n, r in ideas:
            col = C["up"] if r["usd"] >= 0 else C["down"]
            who = f" · {NAME[n]}" if len(real) > 1 else ""
            rows += (f"<tr><td style='font-family:{FONT};padding:5px 0;font-size:14px;color:{C['ink']}'>{_esc(r['idea'].split(' (')[0][:1].upper() + r['idea'].split(' (')[0][1:])}"
                     f"<span style='font-family:{FONT};color:{C['mute']};font-size:12px'>{who}</span></td>"
                     f"<td style='font-family:{FONT};padding:5px 0;font-size:15px;font-weight:600;color:{col};text-align:right'>"
                     f"{_signed(r['usd'])}</td></tr>")
        small = sum(r["n"] for _, r in ideas) < 100
        H.append(card(h("IF THESE HAD BEEN ON") + f"<table role='presentation' width='100%' cellspacing='0' "
                      f"cellpadding='0'>{rows}</table>"
                      + (f"<div style='font-family:{FONT};font-size:12px;color:{C['mute']};margin-top:8px'>Early days: a few trades "
                         f"swing these a lot.</div>" if small else "")))
    pr = ""
    for n, a in real:
        p = proj.get((n, far))
        if not p:
            continue
        dep = f" · includes {money(p['deposits'])} of deposits" if p["deposits"] else ""
        pr += (f"<tr><td style='font-family:{FONT};padding:8px 0;vertical-align:top'>"
               f"<div style='font-family:{FONT};font-size:14px;color:{C['ink']};font-weight:600'>{NAME[n]}</div>"
               f"<div style='font-family:{FONT};font-size:12px;color:{C['mute']}'>{p['base_rate']:.0%} vs {p['lever_rate']:.0%} a year{dep}</div></td>"
               f"<td style='font-family:{FONT};padding:8px 0;text-align:right;vertical-align:top;white-space:nowrap'>"
               f"<div style='font-family:{FONT};font-size:13px;color:{C['mute']}'>as is <b style='font-family:{FONT};color:{C['ink']};font-size:15px'>"
               f"{money(p['without'])}</b></div>"
               f"<div style='font-family:{FONT};font-size:13px;color:{C['mute']}'>all on <b style='font-family:{FONT};color:{C['up']};font-size:15px'>"
               f"{money(p['with_levers'])}</b></div></td></tr>")
    if pr:
        H.append(card(h(f"IN {far} YEARS") + f"<table role='presentation' width='100%' cellspacing='0' "
                      f"cellpadding='0'>{pr}</table><div style='font-family:{FONT};font-size:12px;color:{C['mute']};margin-top:6px'>"
                      f"Planning rates, not a forecast. Before tax.</div>"))
    html = (f"<div style='font-family:{FONT};background:{C['bg']};padding:24px 12px;font-family:{FONT}'>"
            f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0' "
            f"style='font-family:{FONT};max-width:560px;margin:0 auto'>"
            f"<tr><td style='font-family:{FONT};padding:0 0 14px;font-size:13px;color:{C['mute']}'>Week of "
            f"{dt.date.today():%b %-d}</td></tr>{''.join(H)}</table></div>")
    tot = sum(a.equity for _, a in real)
    subj = (f"{money(tot)} total" + (" · " + ", ".join(f"{NAME[n]} {money(a.equity)}" for n, a in real) if len(real) > 1 else "")
            + (f" · ready: {step['gate']}" if step and step["ready"] else ""))
    return subj, html, text
