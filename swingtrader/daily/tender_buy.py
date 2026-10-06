"""Odd-lot tender: the one buy, placed only when YOU run it and confirm (Round 31, study_oddlot_tenders.md).

    make tender-buy ID=UTMD-2026-10-01          # on the server; the alert email prints this exact command

It re-checks the deal live (guaranteed price >= 1% over the current price, >= 3 business days to expiry, <= 99 shares
in total across Roth + Brokerage), shows the plan, and places ONE DAY limit buy only after you type the ticker.
Nothing in the daily jobs ever calls this: the bot never buys a tender position on its own. After it fills, the
morning tender watch emails "BOUGHT - tender now" and deadline reminders until the shares are gone.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np

from .insider_shadow import _read
from .tender_watch import LOG_NAME, MIN_FLOOR, instructions

ORDERS_NAME = "tender-orders.json"
MIN_BDAYS_LEFT = 3          # settle T+1, Schwab's cutoff ~1 business day before expiry, one spare day
PAY_BDAYS = 3               # issuers pay "promptly" after expiry; judge the outcome this many business days later


def offer_id(r: dict) -> str:
    return f"{r.get('ticker') or 'X'}-{r['date']}"


def limit_price(floor: float) -> float:
    return math.floor(round(floor * 0.99 * 100, 6)) / 100


def bdays_left(today: dt.date, expires: str) -> int:
    return int(np.busday_count(today, dt.date.fromisoformat(expires)))


def plan(r: dict, held: dict[str, float], cash: dict[str, float], price: float, today: dt.date) -> tuple[dict | None, str]:
    """({account, qty, limit, cost, gain} or None, reason). Roth first (tax-free), then Brokerage."""
    if not r.get("expires"):
        return None, "the expiry date was not found in the filing - check the offer document and buy by hand"
    left = bdays_left(today, r["expires"])
    if left < MIN_BDAYS_LEFT:
        return None, f"only {left} business days to expiry - too close to settle and tender"
    lim = limit_price(float(r["floor"]))
    if not price or price > lim or float(r["floor"]) / price - 1 < MIN_FLOOR:
        return None, f"price ${price:.2f} is no longer >= 1% under the guaranteed ${float(r['floor']):.2f}"
    n = 99 - int(sum(held.values()))
    if n <= 0:
        return None, f"you already hold {int(sum(held.values()))} shares (odd lot = 99 or fewer in TOTAL)"
    for acct in ("roth", "live"):
        q = min(n, int(cash.get(acct, 0.0) // lim))
        if q >= 1:
            return dict(account=acct, qty=q, limit=lim, cost=q * lim, gain=q * (float(r["floor"]) - lim)), ""
    return None, "not enough cash for one share in either account"


def place_limit(ad, sym: str, qty: int, limit: float) -> str:
    from schwab.orders.common import Duration, Session
    from schwab.orders.equities import equity_buy_limit
    order = equity_buy_limit(sym, qty, f"{limit:.2f}").set_duration(Duration.DAY).set_session(Session.NORMAL).build()
    resp = ad.c.place_order(ad.hash, order)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Schwab rejected BUY {qty} {sym} @ {limit:.2f}: {resp.status_code} {resp.text[:160]}")
    return resp.headers.get("Location", "").rstrip("/").split("/")[-1]


def main(oid: str, state_dir: Path, confirm=input, adapters=None, quote=None, today: dt.date | None = None,
         out=print) -> int:
    today = today or dt.date.today()
    rows = [r for r in _read(Path(state_dir) / LOG_NAME) if r.get("alert") and offer_id(r) == oid]
    if not rows:
        out(f"no alerted offer {oid!r} in state/{LOG_NAME}"); return 2
    r = rows[-1]
    tk = r["ticker"]
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
    if quote is None:
        from . import marketdata as md
        rows_q = md.live_rows([tk])
        price = float(rows_q.at[tk, "price"]) if tk in rows_q.index else float(r["last_close"])
    else:
        price = float(quote)
    p, why = plan(r, held, cash, price, today)
    out(f"\n{tk} ({r['name']}): guaranteed ${float(r['floor']):.2f}, now ${price:.2f}, expires {r.get('expires')}")
    out(f"  you hold: " + ", ".join(f"{a} {int(q)}" for a, q in held.items()) + f"; cash: " +
        ", ".join(f"{a} ${c:,.0f}" for a, c in cash.items()))
    if p is None:
        out(f"  NOT BUYING: {why}"); return 1
    out(f"  PLAN: BUY {p['qty']} {tk} in {p['account'].upper()}, DAY limit ${p['limit']:.2f} "
        f"(max ${p['cost']:,.0f}); expected gain if tendered ~${p['gain']:,.0f}")
    out("  After it fills you MUST tender all of them on schwab.com (odd-lot box) before Schwab's deadline.")
    if confirm(f"  Type {tk} to place the order (anything else cancels): ").strip().upper() != tk.upper():
        out("  cancelled - nothing placed"); return 1
    oid_b = place_limit(adapters[p["account"]], tk, p["qty"], p["limit"])
    path = Path(state_dir) / ORDERS_NAME
    st = json.loads(path.read_text()) if path.exists() else {}
    st[r["path"]] = dict(ticker=tk, offer=oid, expires=r.get("expires"), status="ordered", order_id=oid_b,
                         placed=str(today), **p)
    path.write_text(json.dumps(st, indent=1))
    out(f"  PLACED Schwab order {oid_b}. Tomorrow morning's tender watch emails you when it has filled.\n")
    out(instructions(r))
    return 0


def track(state_dir: Path, today: dt.date, adapters=None, notify=None, log=print) -> dict:
    """Morning bookkeeping (no orders): ordered -> bought when the shares show up (email: tender now);
    bought -> tendered when they are gone -> paid PAY_BDAYS business days after expiry (payout computed, CPC ledger
    COMPLETED, email); an unfilled DAY order -> 'expired' (email: run the command again)."""
    path = Path(state_dir) / ORDERS_NAME
    if not path.exists():
        return {}
    st = json.loads(path.read_text())
    live = {k: s for k, s in st.items() if s.get("status") in ("ordered", "bought", "tendered")}
    if not live:
        return st
    if adapters is None:
        from .brokers import make_adapter
        adapters = {}
        for a in {s["account"] for s in live.values()}:
            try:
                adapters[a] = make_adapter(a)
            except Exception as exc:
                log(f"[tender] {a} unavailable: {str(exc)[:80]}")
    offers = {r["path"]: r for r in _read(Path(state_dir) / LOG_NAME)}
    for k, s in live.items():
        ad = adapters.get(s["account"])
        if ad is None:
            continue
        pos = ad.positions().get(s["ticker"])
        q = float(getattr(pos, "qty", 0.0) or 0.0)
        r = offers.get(k, {})
        if s["status"] == "tendered":
            if s.get("expires") and np.busday_count(dt.date.fromisoformat(s["expires"]), today) >= PAY_BDAYS:
                _paid(Path(state_dir), s, r, q, float(getattr(pos, "current_price", 0.0) or 0.0), today, notify, log)
            continue
        if s["status"] == "ordered" and q >= 1:
            s.update(status="bought", held=int(q), bought=str(today))
            if notify:
                from ..live import mail as M
                tk = s["ticker"]
                notify(f"BOUGHT {int(q)} {tk} - TENDER NOW (expires {s['expires']})",
                       M.page("Odd-lot tender", f"Tender your {int(q)} {tk} now", f"bought in {s['account'].upper()} · "
                              f"offer expires {s['expires']}",
                              [M.action("Do it now", f"Tender ALL {int(q)} {tk} shares at Schwab", lines=[
                                  "schwab.com > Accounts > Positions > " + tk + " > Corporate actions / Voluntary "
                                  "reorganization (or call 1-800-435-4000).",
                                  "Tick the odd-lot certification. Dutch auction: 'at the purchase price'. Not conditional."]),
                               M.para("Schwab's own deadline is usually 1 business day before the expiry. Keep the "
                                      "confirmation number; this email stops once the shares are gone.", muted=True)]
                              + ([M.link(f"https://www.sec.gov/Archives/{r['path']}", "Offer document (SEC)")] if r else [])))
        elif s["status"] == "ordered" and s.get("placed", "") < str(today):
            s.update(status="unfilled")
            if notify:
                from ..live import mail as M
                notify(f"odd-lot tender {s['ticker']}: yesterday's buy did not fill",
                       M.page("Odd-lot tender", f"{s['ticker']}: the buy did not fill", f"offer expires {s['expires']}",
                              [M.action("Run again if you still want it", "Re-check and buy", f"make tender-buy ID={s['offer']}",
                                        ["It re-checks the deal first and refuses if it no longer qualifies."], tone="wait")]))
        elif s["status"] == "bought" and q < 1:
            s.update(status="tendered", tendered=str(today))
            log(f"[tender] {s['ticker']}: shares gone - tendered")
    path.write_text(json.dumps(st, indent=1))
    return st


def payout(s: dict, r: dict, returned: float, mark: float) -> dict:
    """Cash received for the shares bought, minus their cost. Price: the fixed offer price, or for a Dutch auction
    the guaranteed low end (the real purchase price can only be higher). Shares back in the account after expiry
    (offer terminated, or prorated after all) count at today's mark. Cost is the buy limit (fills are at or under)."""
    price = float(r.get("fixed") or r.get("floor") or 0.0)
    bought = s["held"] - returned
    value = bought * price + returned * mark
    pnl = value - s["cost"]
    return dict(price=price, dutch=not r.get("fixed"), returned=returned, value=round(value, 2),
                pnl=round(pnl, 2), ret=round(pnl / s["cost"], 5))


def _paid(state_dir: Path, s: dict, r: dict, q: float, mark: float, today: dt.date, notify, log) -> None:
    from . import cpc_ledger as L
    if not (r.get("fixed") or r.get("floor")):
        log(f"[tender] {s['ticker']}: no offer price on file - record it by hand (make cpc-done)"); return
    p = payout(s, r, min(q, s["held"]), mark)
    s.update(status="paid", paid=str(today), **p)
    line = (f"{s['ticker']}: {s['held'] - p['returned']:g} sh @ ${p['price']:,.2f}"
            + (" (Dutch: guaranteed low end; the final price may be higher)" if p["dutch"] else "")
            + (f" + {p['returned']:g} returned @ ${mark:,.2f}" if p["returned"] else "")
            + f" = ${p['value']:,.2f} vs ${s['cost']:,.2f} paid -> ${p['pnl']:+,.2f} ({p['ret']:+.1%})")
    log(f"[tender] paid {line}")
    eid = L.settle(state_dir / L.LOG_NAME, "ODD_LOT_TENDER",
                   lambda v: v.get("security") == s["ticker"] and s["offer"] == f"{s['ticker']}-{v.get('event_date')}",
                   p["pnl"], note=f"auto from tender tracking ({s['account']}): {line}",
                   reopen_note=f"bought {s['held']} {s['ticker']} in {s['account']} on {s.get('bought')} and tendered; "
                               "the earlier MISSED was wrong", log=log)
    if eid:
        s["ledger"] = eid
    if notify:
        from ..live import mail as M
        notify(f"odd-lot tender {s['ticker']}: paid, payout ${p['pnl']:+,.2f}",
               M.page("Odd-lot tender", f"{s['ticker']} paid: ${p['pnl']:+,.2f}",
                      f"{s['account'].upper()} · recorded in the CPC ledger",
                      [M.para(line), M.para("Measured from the offer terms, not the cash entry; check the Schwab "
                                            "statement if the numbers look off.", muted=True)]))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: make tender-buy ID=<TICKER-YYYY-MM-DD>   (the id is in the alert email)"); sys.exit(2)
    sys.exit(main(sys.argv[1], Path(__file__).resolve().parents[2] / "state"))
