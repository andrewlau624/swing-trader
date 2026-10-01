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
TAXABLE_MONTHLY_DEFAULT = 1000.0       # the user's plan: $1k a month into the brokerage account
TAXABLE_TAX = 0.32                      # short-term federal + state, the program's planning rate
HORIZONS = (1, 3, 5)
INDEX_RATE = 0.10                       # S&P 500 long-run nominal, held (no yearly tax), the benchmark
# What the research backtest says (auction-corrected, Study AW; 2.5bp/side stress, fixed capital ~$2-25k):
# V7 brokerage book ~31%/yr, Roth cash IBS+night ~20%/yr; daily vol from the same runs (Sharpe ~1.95 / ~1.5).
BACKTEST = {"taxable": {"rate": 0.31, "sd_day": 0.010}, "roth": {"rate": 0.20, "sd_day": 0.0085}}
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
INK, MUTE, RULE, ACC, UP, DOWN = "#1f2328", "#6e7781", "#e6e8eb", "#0b5cad", "#1a7f37", "#cf222e"
SANS = "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif"   # unquoted: inside style='...'
SERIF = "Georgia,Times New Roman,serif"


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _signed(x: float) -> str:
    return ("+" if x >= 0 else "−") + f"${abs(x):,.0f}"


def _plan(G: list) -> tuple[dict | None, list, list]:
    """(the one next step, the following switches, the running experiments)."""
    switches = [g for g in G if not g["action"].startswith("verdict")]
    tests = [g for g in G if g["action"].startswith("verdict")]
    ready = [g for g in switches if g["ready"]]
    step = ready[0] if ready else next((g for g in switches if not g["ready"]), None)
    rest = [g for g in switches if g is not step and not g["ready"]][:3]
    return step, rest, tests


def ten_year(acct: str, bal: float, taxable_monthly: float = 0.0) -> tuple[list, dict, dict]:
    """(years grid, {line: values}, {line: (5y, 10y)}). Brokerage lines are AFTER yearly short-term tax
    (the book's gains are taxed every year; a held index fund is not, until sold)."""
    kind = "roth" if acct == "roth" else "taxable"
    p = PLAN[kind]
    dep = ROTH_DEPOSIT_YR if kind == "roth" else 12 * taxable_monthly
    k = (1 - TAXABLE_TAX) if kind == "taxable" else 1.0
    rates = {"This bot": p["base"] * k, "Everything on": (p["base"] + sum(p["levers"].values())) * k,
             "Backtest": BACKTEST[kind]["rate"] * k, "Index fund": INDEX_RATE}
    years = [m / 12 for m in range(0, 121)]
    lines = {n: [project(bal, r, 0, dep)] for n, r in rates.items()}
    for n, r in rates.items():
        e, mr = bal, (1 + r) ** (1 / 12) - 1
        vals = [e]
        for _ in range(120):
            e = e * (1 + mr) + dep / 12
            vals.append(e)
        lines[n] = vals
    marks = {n: (v[60], v[120]) for n, v in lines.items()}
    return years, lines, marks


def pace(acct: Account) -> dict | None:
    """Live trading P&L vs what the backtest's rate and the planning rate would have made on the same
    balances over the same days, with the backtest's normal range (+-1 and 2 sd). None before 5 trades."""
    import pandas as pd
    cl = [c for c in acct.closed if c.get("exit_date")]
    if len(cl) < 5 or not acct.equity_log:
        return None
    kind = "roth" if acct.name == "roth" else "taxable"
    s = pd.Series([float(c["pnl"]) for c in cl], index=pd.to_datetime([str(c["exit_date"]) for c in cl]))
    s = s.groupby(level=0).sum().sort_index()
    eq = pd.Series({pd.Timestamp(e["date"]): float(e["equity"]) for e in acct.equity_log}).sort_index()
    days = eq.index[eq.index >= s.index[0] - pd.Timedelta(days=1)]
    if len(days) < 2:
        days = pd.DatetimeIndex(sorted(set(s.index) | set(eq.index[-1:])))
    e = eq.reindex(days, method="ffill").fillna(acct.equity)
    bt, sd = BACKTEST[kind]["rate"], BACKTEST[kind]["sd_day"]
    live = s.reindex(days.union(s.index)).fillna(0).cumsum().reindex(days, method="ffill").fillna(0)
    return dict(days=list(days), live=list(live.values),
                backtest=list((e * bt / 252).cumsum().values), plan=list((e * PLAN[kind]["base"] / 252).cumsum().values),
                sd=list(((e * sd) ** 2).cumsum().pow(0.5).values), n=len(cl))


def render(d: dict, charts: bool = True, taxable_monthly: float = 0.0) -> tuple[str, str, str, list]:
    """(subject, html, text, images); images = [(content_id, png)] for the email's cid: references."""
    A, G = d["accounts"], d["gates"]
    real = [(n, A[n]) for n in ("live", "roth") if n in A]
    step, rest, tests = _plan(G)
    ideas = [(n, r) for n, rows in d["whatif"].items() if n in ("live", "roth") for r in rows if r["n"]]
    tot = sum(a.equity for _, a in real)
    proj = {n: ten_year(n, a.equity, taxable_monthly) for n, a in real}
    images = []

    # ---------------- plain text (terminal)
    T = [f"Total {money(tot)}"]
    for n, a in real:
        T.append(f"  {NAME[n]:10s} {money(a.equity):>9s}  {_signed(a.week_pnl)} from trades this week")
    if step:
        T += ["", ("Ready: " if step["ready"] else "Next: ") + f"{step['gate']} — "
              f"{min(step['n'], step['need'])} of {step['need']} {step['unit']}", f"  then {step['action']}"]
    for g in rest + tests:
        T.append(f"  {g['gate'].replace(' verdict', ''):26s} {g['n']:>4} of {g['need']}")
    if ideas:
        T += ["", "If these had been on:"] + [f"  {NAME[n]:10s} {r['idea'][:34]:34s} {_signed(r['usd']):>7s}" for n, r in ideas]
    for n, _ in real:
        _, _, mk = proj[n]
        T += ["", f"{NAME[n]}{' (after tax)' if n == 'live' else ''}:     5 years    10 years"]
        T += [f"  {k:14s} {money(v5):>10s}  {money(v10):>10s}" for k, (v5, v10) in mk.items()]
    text = "\n".join(T)

    # ---------------- HTML (email): a statement with clear structure
    BAND, PANEL, LINE = "#0f2a44", "#f6f8fa", "#d8dee4"

    def p(s, size=16, color=INK, extra=""):
        return f"<p style='margin:0;font-family:{SANS};font-size:{size}px;line-height:1.5;color:{color};{extra}'>{s}</p>"

    def section(title, sub=""):
        return (f"<p style='margin:34px 0 14px;font-family:{SANS};font-size:19px;font-weight:700;color:{INK};"
                f"letter-spacing:-.01em'>{title}"
                + (f"<span style='display:block;font-size:14px;font-weight:400;color:{MUTE};margin-top:2px'>{sub}</span>" if sub else "")
                + "</p>")

    def bar(frac, color=ACC, h=6):
        w = max(0, min(100, round(frac * 100)))
        return (f"<div style='background:#e1e6eb;height:{h}px;border-radius:{h // 2}px;width:100%'><div style='background:{color};"
                f"height:{h}px;border-radius:{h // 2}px;width:{w}%'></div></div>")

    def table(head_cells, rows_html):
        th = "".join(f"<td style='font-family:{SANS};font-size:13px;font-weight:600;color:{MUTE};padding:0 0 8px;"
                     f"border-bottom:2px solid {LINE};{'text-align:right;' if i else ''}'>{c}</td>"
                     for i, c in enumerate(head_cells))
        return (f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0'>"
                f"<tr>{th}</tr>{rows_html}</table>")

    cell = f"font-family:{SANS};font-size:16px;color:{INK};padding:12px 0;border-bottom:1px solid {LINE};"
    numc = cell + "text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;font-weight:600;"
    H = []
    # header band
    acc_rows = "".join(
        f"<td style='padding:14px 0 0;vertical-align:top;width:50%'>"
        f"<div style='font-family:{SANS};font-size:14px;color:#a8bccf'>{NAME[n]}</div>"
        f"<div style='font-family:{SANS};font-size:24px;font-weight:700;color:#ffffff;font-variant-numeric:tabular-nums'>{money(a.equity)}</div>"
        f"<div style='font-family:{SANS};font-size:14px;font-weight:600;color:{'#7ee2a8' if a.week_pnl >= 0 else '#ff9b9b'}'>"
        f"{_signed(a.week_pnl)} <span style='font-weight:400;color:#a8bccf'>from trades this week</span></div></td>"
        for n, a in real)
    H.append(f"<div style='background:{BAND};padding:24px 26px 22px'>"
             f"<div style='font-family:{SANS};font-size:14px;color:#a8bccf'>Week of {dt.date.today():%B %-d, %Y}</div>"
             f"<div style='font-family:{SERIF};font-size:44px;color:#ffffff;margin-top:4px;font-variant-numeric:tabular-nums'>{money(tot)}</div>"
             f"<div style='font-family:{SANS};font-size:14px;color:#a8bccf'>total across your accounts</div>"
             f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='margin-top:6px'><tr>{acc_rows}</tr></table></div>")
    B = []          # body
    if step:
        k = min(step["n"], step["need"]) / step["need"]
        col = UP if step["ready"] else ACC
        lead = "READY TO SWITCH ON" if step["ready"] else "NEXT STEP"
        B.append(f"<div style='background:{'#eef8f1' if step['ready'] else '#eef4fb'};border-left:5px solid {col};"
                 f"padding:18px 20px;margin-top:26px'>"
                 f"<div style='font-family:{SANS};font-size:12px;font-weight:700;letter-spacing:.06em;color:{col}'>{lead}</div>"
                 f"<div style='font-family:{SANS};font-size:22px;font-weight:700;color:{INK};margin:4px 0 12px'>{_esc(step['gate'])}</div>"
                 + bar(k, col, 8)
                 + f"<div style='font-family:{SANS};font-size:15px;color:{INK};margin:8px 0 12px'><b>{min(step['n'], step['need'])}</b> of "
                   f"{step['need']} {_esc(step['unit'])}</div>"
                 + f"<div style='font-family:{SANS};font-size:15px;color:{INK}'>{'Do it now:' if step['ready'] else 'When it fills:'}</div>"
                 + f"<div style='font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px;background:#ffffff;"
                   f"border:1px solid {LINE};padding:8px 10px;margin-top:6px;word-break:break-all;color:{INK}'>{_esc(step['action'])}</div>"
                 + "</div>")
    if rest or tests:
        rr = "".join(
            f"<tr><td style='{cell}width:44%'>{_esc(g['gate'].replace(' verdict', ''))}"
            + (f"<div style='font-size:12px;color:{MUTE}'>experiment</div>" if g in tests else "")
            + f"</td><td style='{cell}width:32%;padding-left:14px;padding-right:14px'>{bar(min(g['n'], g['need']) / g['need'], ACC if g in rest else '#8c959f')}</td>"
              f"<td style='{numc}'>{g['n']} <span style='font-weight:400;color:{MUTE}'>of {g['need']}</span></td></tr>"
            for g in rest + tests)
        B += [section("Also counting"), table(["", "", "Progress"], rr)]
    for n, a in real:
        yrs, lines, mk = proj[n]
        dep = ROTH_DEPOSIT_YR / 12 if n == "roth" else taxable_monthly
        sub = (f"${dep:,.0f} a month in deposits" + (" · after short-term tax" if n == "live" else " · tax-free"))
        B.append(section(f"{NAME[n]} over 10 years", sub))
        if charts:
            cid = f"proj-{n}"
            from .digest_charts import projection_png
            images.append((cid, projection_png(yrs, lines)))
            B.append(f"<img src='cid:{cid}' width='560' alt='{NAME[n]} projection: "
                     + "; ".join(f"{k} {money(v10)} in 10 years" for k, (_, v10) in mk.items())
                     + "' style='display:block;width:100%;max-width:560px;height:auto;margin:0 0 14px'>")
        dot = {"This bot": "#2a78d6", "Everything on": "#eb6834", "Backtest": INK, "Index fund": "#8c959f"}
        best = max(v10 for _, v10 in mk.values())
        rr = "".join(
            f"<tr><td style='{cell}'><span style='display:inline-block;width:10px;height:10px;border-radius:5px;"
            f"background:{dot[k]};margin-right:8px'></span>{k}</td><td style='{numc}'>{money(v5)}</td>"
            f"<td style='{numc}{'color:' + UP + ';' if v10 == best else ''}'>{money(v10)}</td></tr>"
            for k, (v5, v10) in mk.items())
        B.append(table(["", "In 5 years", "In 10 years"], rr))
        idx = mk["Index fund"][1]
        diff = mk["This bot"][1] - idx
        B.append(p(f"After 10 years this bot, as it runs today, is <b style='color:{UP if diff >= 0 else DOWN}'>"
                   f"{money(abs(diff))} {'ahead of' if diff >= 0 else 'behind'}</b> an index fund.", 14, MUTE, "margin-top:10px"))
    if ideas:
        rr = "".join(
            f"<tr><td style='{cell}'>{_esc(r['idea'].split(' (')[0][:1].upper() + r['idea'].split(' (')[0][1:])}"
            f"<div style='font-size:12px;color:{MUTE}'>{NAME[n]} · {r['n']} trade{'s' if r['n'] != 1 else ''}</div></td>"
            f"<td style='{numc}color:{UP if r['usd'] >= 0 else DOWN}'>{_signed(r['usd'])}</td></tr>" for n, r in ideas)
        B += [section("If these had been on", "what each idea still in testing would have made on your real days"),
              table(["", "Would have made"], rr),
              p("A handful of trades swings these a lot; they settle as the count grows.", 13, MUTE, "margin-top:8px")]
    for n, a in real:
        pc = pace(a)
        if not pc:
            continue
        lv, bt, pl, sd = pc["live"][-1], pc["backtest"][-1], pc["plan"][-1], pc["sd"][-1]
        inside = abs(lv - bt) <= 2 * sd
        B.append(section(f"{NAME[n]} trades so far", f"{pc['n']} trades since {pc['days'][0]:%b %-d} · deposits excluded"))
        if charts:
            from .digest_charts import pnl_png
            cid = f"pnl-{n}"
            images.append((cid, pnl_png(pc["days"], pc["live"], pc["backtest"], pc["plan"], pc["sd"])))
            B.append(f"<img src='cid:{cid}' width='560' alt='{NAME[n]}: trades made {_signed(lv)}; backtest pace "
                     f"{_signed(bt)}; plan pace {_signed(pl)}' style='display:block;width:100%;max-width:560px;"
                     f"height:auto;margin:0 0 12px'>")
        dot = {"Your trades": UP if lv >= 0 else DOWN, "Backtest pace": INK, "Plan pace": "#8c959f"}
        rr = "".join(f"<tr><td style='{cell}'><span style='display:inline-block;width:10px;height:10px;border-radius:5px;"
                     f"background:{dot[k]};margin-right:8px'></span>{k}</td><td style='{numc}'>{_signed(v)}</td></tr>"
                     for k, v in (("Your trades", lv), ("Backtest pace", bt), ("Plan pace", pl)))
        B.append(table(["", "So far"], rr))
        rng = f"(backtest pace {_signed(bt)} ± {money(2 * sd)})"
        msg = (f"Inside the backtest's normal range {rng}. Too few trades to tell the backtest from the plan yet; "
               f"that takes months, not weeks." if inside else
               f"<b>Outside</b> the backtest's normal range {rng}. Worth a look: paste <code>make review</code> to Claude.")
        B.append(p(msg, 14, MUTE, "margin-top:10px"))
    B.append(p(f"Projections use planning rates, not forecasts: this bot {PLAN['taxable']['base']:.0%} a year "
               f"(Roth {PLAN['roth']['base']:.0%}), everything on {PLAN['taxable']['base'] + sum(PLAN['taxable']['levers'].values()):.0%}, "
               f"backtest {BACKTEST['taxable']['rate']:.0%} (Roth {BACKTEST['roth']['rate']:.0%}; research results usually shrink live), "
               f"index fund {INDEX_RATE:.0%}. Every line gets the same deposits. Brokerage figures assume {TAXABLE_TAX:.0%} short-term "
               f"tax each year; the index fund is shown before you sell it.", 13, MUTE,
               f"margin-top:34px;padding-top:16px;border-top:1px solid {LINE}"))
    html = (f"<div style='background:#eaeef2;padding:24px 10px'><div style='max-width:600px;margin:0 auto;background:#ffffff;"
            f"border:1px solid {LINE}'>" + "".join(H)
            + f"<div style='padding:0 26px 28px'>" + "".join(B) + "</div></div></div>")
    subj = (f"{money(tot)} total" + (" · " + ", ".join(f"{NAME[n]} {money(a.equity)}" for n, a in real) if len(real) > 1 else "")
            + (f" · ready: {step['gate']}" if step and step["ready"] else ""))
    return subj, html, text, images
