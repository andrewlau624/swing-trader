"""Split-off exchange offer: the odd-lot buy, placed only when YOU run it and confirm (Round 32 B2).

    make splitoff-buy PARENT=MDT          # on the server; the entry-window email prints this exact command

It re-checks the offer live (implied gain >= +1% with the upper limit applied, >= 3 business days to expiry, <= 99
parent shares in total across Roth + Brokerage), shows the plan, and places ONE DAY limit buy only after you type the
ticker. Nothing in the daily jobs calls this. After it fills, the morning split-off watch emails "BOUGHT - tender now".
Tendering is manual at Schwab (Corporate actions / Voluntary reorganization, odd-lot box).
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np

from .insider_shadow import _read
from .splitoff_watch import LOG_NAME, MIN_GAIN, implied_gain, instructions, open_offers

ORDERS_NAME = "splitoff-orders.json"
MIN_BDAYS_LEFT = 3


def limit_price(price: float) -> float:
    return math.ceil(round(price * 1.002 * 100, 6)) / 100


def plan(r: dict, held: dict, cash: dict, pp: float, pr: float, today: dt.date) -> tuple[dict | None, str]:
    left = int(np.busday_count(today, dt.date.fromisoformat(r["expires"])))
    if left < MIN_BDAYS_LEFT:
        return None, f"only {left} business days to expiry - too close to settle and tender"
    g = implied_gain(r, pp, pr)
    if g < MIN_GAIN:
        return None, f"implied gain {g:+.1%} is below +{MIN_GAIN:.0%} at the current prices"
    n = 99 - int(sum(held.values()))
    if n <= 0:
        return None, f"you already hold {int(sum(held.values()))} {r['parent']} (odd lot = 99 or fewer in TOTAL)"
    lim = limit_price(pp)
    for acct in ("roth", "live"):
        q = min(n, int(cash.get(acct, 0.0) // lim))
        if q >= 1:
            return dict(account=acct, qty=q, limit=lim, cost=q * lim, gain=q * pp * g, implied=g), ""
    return None, "not enough cash for one share in either account"


def main(parent: str, state_dir: Path, confirm=input, adapters=None, quotes=None, today: dt.date | None = None,
         out=print) -> int:
    from .tender_buy import place_limit
    today = today or dt.date.today()
    offers = {r["parent"]: r for r in open_offers(_read(Path(state_dir) / LOG_NAME), today)}
    r = offers.get(parent.upper())
    if not r:
        out(f"no open split-off offer for {parent!r} in state/{LOG_NAME} (make splitoff-add sets one)"); return 2
    tk = r["parent"]
    if adapters is None:
        from .brokers import make_adapter
        adapters = {}
        for a in ("roth", "live"):
            try:
                adapters[a] = make_adapter(a)
            except Exception as exc:
                out(f"  ({a} account unavailable: {str(exc)[:80]})")
    held = {a: float(getattr(ad.positions().get(tk), "qty", 0.0) or 0.0) for a, ad in adapters.items()}
    cash = {}
    for a, ad in adapters.items():
        try:
            cash[a] = max(float(ad.account().cash), 0.0)
        except Exception:
            cash[a] = 0.0
    if quotes is None:
        from . import marketdata as md
        q = md.live_rows([tk, r["recv"]])
        quotes = {s: float(q.at[s, "price"]) for s in q.index}
    pp, pr = quotes.get(tk), quotes.get(r["recv"])
    if not pp or not pr:
        out(f"  no live price for {tk} / {r['recv']} - try again in a minute"); return 1
    p, why = plan(r, held, cash, pp, pr, today)
    out(f"\n{tk} -> {r['recv']}: ${r['per100']:.2f} per $100, upper limit {r['cap']}, expires {r['expires']}; "
        f"now {tk} ${pp:.2f}, {r['recv']} ${pr:.2f} -> implied {implied_gain(r, pp, pr):+.2%}")
    out("  you hold: " + ", ".join(f"{a} {int(x)}" for a, x in held.items()) + "; cash: " +
        ", ".join(f"{a} ${c:,.0f}" for a, c in cash.items()))
    if p is None:
        out(f"  NOT BUYING: {why}"); return 1
    out(f"  PLAN: BUY {p['qty']} {tk} in {p['account'].upper()}, DAY limit ${p['limit']:.2f} (max ${p['cost']:,.0f}); "
        f"value gain at today's prices ~${p['gain']:,.0f}")
    out("  After it fills you MUST tender ALL of them on schwab.com (odd-lot box) before Schwab's deadline.")
    if confirm(f"  Type {tk} to place the order (anything else cancels): ").strip().upper() != tk.upper():
        out("  cancelled - nothing placed"); return 1
    oid = place_limit(adapters[p["account"]], tk, p["qty"], p["limit"])
    path = Path(state_dir) / ORDERS_NAME
    st = json.loads(path.read_text()) if path.exists() else {}
    st[f"{tk}-{r['expires']}"] = dict(ticker=tk, recv=r["recv"], expires=r["expires"], status="ordered", order_id=oid,
                                      placed=str(today), **p)
    path.write_text(json.dumps(st, indent=1))
    out(f"  PLACED Schwab order {oid}. Tomorrow morning's split-off watch emails you when it has filled.\n")
    out(instructions(r, implied_gain(r, pp, pr), pp, pr))
    return 0


def track(state_dir: Path, today: dt.date, adapters=None, notify=None, log=print) -> dict:
    """Morning bookkeeping (no orders): ordered -> bought (email: tender now) -> tendered when the parent shares are
    gone; an unfilled DAY order -> 'unfilled' (email: run the command again)."""
    path = Path(state_dir) / ORDERS_NAME
    if not path.exists():
        return {}
    st = json.loads(path.read_text())
    live = {k: s for k, s in st.items() if s.get("status") in ("ordered", "bought")}
    if not live:
        return st
    if adapters is None:
        from .brokers import make_adapter
        adapters = {}
        for a in {s["account"] for s in live.values()}:
            try:
                adapters[a] = make_adapter(a)
            except Exception as exc:
                log(f"[splitoff] {a} unavailable: {str(exc)[:80]}")
    for s in live.values():
        ad = adapters.get(s["account"])
        if ad is None:
            continue
        q = float(getattr(ad.positions().get(s["ticker"]), "qty", 0.0) or 0.0)
        if s["status"] == "ordered" and q >= 1:
            s.update(status="bought", held=int(q), bought=str(today))
            if notify:
                notify(f"BOUGHT {int(q)} {s['ticker']} in {s['account'].upper()} - TENDER NOW (expires {s['expires']})",
                       f"Your approved order filled. Tender ALL {int(q)} {s['ticker']} shares in the exchange offer for "
                       f"{s['recv']}: schwab.com > Accounts > Positions > {s['ticker']} > Corporate actions / Voluntary "
                       f"reorganization (or 1-800-435-4000). Tick the odd-lot certification. Schwab's deadline is "
                       f"usually 1-2 business days before {s['expires']}.")
        elif s["status"] == "ordered" and s.get("placed", "") < str(today):
            s.update(status="unfilled")
            if notify:
                notify(f"split-off {s['ticker']}: yesterday's buy did not fill",
                       f"Run again if it still qualifies:  make splitoff-buy PARENT={s['ticker']}")
        elif s["status"] == "bought" and q < 1:
            s.update(status="tendered", tendered=str(today))
            log(f"[splitoff] {s['ticker']}: shares gone - tendered")
    path.write_text(json.dumps(st, indent=1))
    return st


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: make splitoff-buy PARENT=<TICKER>   (from the alert email)"); sys.exit(2)
    sys.exit(main(sys.argv[1], Path(__file__).resolve().parents[2] / "state"))
