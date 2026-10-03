"""Index-beat FOUND (2026-10-02, research/drafts/study_ib_found_stack.md): the book stacked on index beta — SHADOW, never orders.

What it would change (a user decision, not built): the taxable account holds SPY at 1.0x and runs the live legs on top on
margin; the Roth holds 1/3 in UPRO (3x daily S&P, ~1.0x beta) and runs the Roth book on the other 2/3. This module only
logs, each weekday, what those two accounts would have earned next to what the live accounts earned and what SPY did:
  stacked taxable = r_taxable + r_SPY - DEBIT x MARGIN / 252     (r_taxable: the live account's day, SPY: close -> close)
  stacked Roth    = 2/3 r_roth + 1/3 r_UPRO
Account days come from state/book-daily-{live,roth}.json `equity_log`; a day whose move is > MAX_DAY (a deposit or a
transfer) is logged but left out of the sums. SPY/UPRO from regular-session daily bars (`marketdata.sip_daily`, labelled by
trade date). Read at NEED sessions: does stacked beat both the live account and SPY, net of the modelled interest?
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

LOG_NAME = "stack-shadow.jsonl"
DEBIT, MARGIN, MAX_DAY, NEED = 0.40, 0.12, 0.15, 250
ACCOUNTS = {"taxable": "book-daily-live.json", "roth": "book-daily-roth.json"}


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def day_returns(equity_log: list[dict]) -> dict[str, float | None]:
    """date -> the account's return that day (None when the move looks like a deposit/transfer, or no prior day)."""
    out, prev = {}, None
    for row in sorted(equity_log, key=lambda r: r["date"]):
        e = float(row.get("equity") or 0.0)
        if prev and prev > 0 and e > 0:
            r = e / prev - 1
            out[row["date"]] = r if abs(r) <= MAX_DAY else None
        prev = e
    return out


def overlay(r_tax: float | None, r_roth: float | None, r_spy: float, r_upro: float) -> dict:
    return dict(stack_taxable=None if r_tax is None else r_tax + r_spy - DEBIT * MARGIN / 252,
                stack_roth=None if r_roth is None else 2 / 3 * r_roth + 1 / 3 * r_upro)


def summary(rows: list[dict]) -> dict:
    def cum(key):
        x = [r[key] for r in rows if r.get(key) is not None]
        v = 1.0
        for a in x:
            v *= 1 + a
        return len(x), v - 1
    out = {"n": len(rows)}
    for k in ("r_taxable", "stack_taxable", "r_roth", "stack_roth", "r_spy"):
        out[k] = cum(k)
    return out


def line(rows: list[dict]) -> str:
    s = summary(rows)
    f = lambda k: f"{s[k][1] * 100:+.1f}%"
    return (f"{s['n']} sessions: taxable {f('r_taxable')} vs stacked {f('stack_taxable')}; Roth {f('r_roth')} vs stacked "
            f"{f('stack_roth')}; SPY {f('r_spy')}")


def run(state_dir: Path, today: dt.date | None = None, log=print, bars=None) -> dict:
    """Append every complete session not yet logged. `bars` = {sym: DataFrame(index=trade date, close)} for tests."""
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    done = {r["date"] for r in rows}
    acct = {}
    for k, f in ACCOUNTS.items():
        p = state_dir / f
        acct[k] = day_returns(json.loads(p.read_text()).get("equity_log", [])) if p.exists() else {}
    dates = sorted(set(acct["taxable"]) | set(acct["roth"]))
    new_dates = [d for d in dates if d not in done and (today is None or d < str(today))]
    if new_dates:
        if bars is None:
            import pandas as pd
            from . import marketdata as md
            bars = md.sip_daily(["SPY", "UPRO"], pd.Timestamp(min(new_dates)) - pd.Timedelta(days=10))
        import pandas as pd
        cl = {s: bars[s]["close"] for s in ("SPY", "UPRO") if s in bars}
        for d in new_dates:
            t = pd.Timestamp(d)
            rr = {}
            for s, c in cl.items():
                c = c[c.index <= t]
                if len(c) >= 2 and c.index[-1] == t:
                    rr[s] = float(c.iloc[-1] / c.iloc[-2] - 1)
            if len(rr) < 2:
                continue
            row = dict(date=d, r_taxable=acct["taxable"].get(d), r_roth=acct["roth"].get(d), r_spy=rr["SPY"], r_upro=rr["UPRO"])
            row.update(overlay(row["r_taxable"], row["r_roth"], rr["SPY"], rr["UPRO"]))
            rows.append(row)
        rows.sort(key=lambda r: r["date"])
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[stack] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    import sys
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    run(Path(__file__).resolve().parents[2] / "state", day)
