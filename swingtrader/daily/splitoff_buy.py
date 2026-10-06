"""Split-off exchange offer: the odd-lot buy, placed only when YOU run it and confirm (Round 32 B2).

    make splitoff-buy PARENT=MDT          # on the server; the entry-window email prints this exact command

It re-checks the offer live (implied gain >= +1% with the upper limit applied, >= 3 business days to expiry, <= 99
parent shares in total across Roth + Brokerage), shows the plan, and places ONE DAY limit buy only after you type the
ticker. Nothing in the daily jobs calls this. After it fills, the morning split-off watch emails "BOUGHT - tender now".
Tendering is manual at Schwab (Corporate actions / Voluntary reorganization, odd-lot box). The one order the morning
job places itself (user-approved 2026-10-06): when the received shares land, a DAY market sell of exactly those shares;
the payout is then taken from the fill and written to the CPC ledger.
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


def track(state_dir: Path, today: dt.date, adapters=None, notify=None, log=print, seller=None) -> dict:
    """Morning bookkeeping: ordered -> bought (email: tender now) -> tendered when the parent shares are gone ->
    selling when the received shares land (the ONLY order this places: a DAY market sell of exactly those shares, at
    the open) -> sold when it fills (payout from the fill, CPC ledger COMPLETED, email). If the sell cannot be placed,
    the payout is taken at the delivery mark ('delivered') and the email says to sell by hand. An unfilled DAY buy
    -> 'unfilled' (email: run the command again)."""
    seller = seller or place_sell
    path = Path(state_dir) / ORDERS_NAME
    if not path.exists():
        return {}
    st = json.loads(path.read_text())
    live = {k: s for k, s in st.items() if s.get("status") in ("ordered", "bought", "tendered", "selling")}
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
        held = ad.positions()
        q = float(getattr(held.get(s["ticker"]), "qty", 0.0) or 0.0)
        if s["status"] == "tendered":
            recv = held.get(s["recv"])
            got = float(getattr(recv, "qty", 0.0) or 0.0) - s.get("recv_before", 0.0)
            if got >= 1 and getattr(recv, "current_price", None):
                _deliver(Path(state_dir), s, ad, int(got), float(recv.current_price), today, notify, log, seller)
            continue
        if s["status"] == "selling":
            _sold(Path(state_dir), s, ad, today, notify, log, seller)
            continue
        if s["status"] == "ordered" and q >= 1:
            s.update(status="bought", held=int(q), bought=str(today))
            if notify:
                from ..live import mail as M
                tk = s["ticker"]
                notify(f"BOUGHT {int(q)} {tk} - TENDER NOW (expires {s['expires']})",
                       M.page("Split-off exchange offer", f"Tender your {int(q)} {tk} now",
                              f"for {s['recv']} · bought in {s['account'].upper()} · expires {s['expires']}",
                              [M.action("Do it now", f"Tender ALL {int(q)} {tk} shares at Schwab", lines=[
                                  f"schwab.com > Accounts > Positions > {tk} > Corporate actions / Voluntary reorganization "
                                  "(or call 1-800-435-4000).", "Tick the odd-lot certification. Fee $0."]),
                               M.para("Schwab's own deadline is usually 1-2 business days before the expiry. Keep the "
                                      "confirmation number; this stops once the shares are gone.", muted=True)]))
        elif s["status"] == "ordered" and s.get("placed", "") < str(today):
            s.update(status="unfilled")
            if notify:
                from ..live import mail as M
                notify(f"split-off {s['ticker']}: yesterday's buy did not fill",
                       M.page("Split-off exchange offer", f"{s['ticker']}: the buy did not fill", f"expires {s['expires']}",
                              [M.action("Run again if you still want it", "Re-check and buy",
                                        f"make splitoff-buy PARENT={s['ticker']}",
                                        ["It re-checks the offer first and refuses if it no longer qualifies."], tone="wait")]))
        elif s["status"] == "bought" and q < 1:
            s.update(status="tendered", tendered=str(today),
                     recv_before=float(getattr(held.get(s["recv"]), "qty", 0.0) or 0.0))
            log(f"[splitoff] {s['ticker']}: shares gone - tendered")
    path.write_text(json.dumps(st, indent=1))
    return st


def place_sell(ad, sym: str, qty: int) -> str:
    from schwab.orders.common import Duration, Session
    from schwab.orders.equities import equity_sell_market
    resp = ad.c.place_order(ad.hash, equity_sell_market(sym, qty).set_duration(Duration.DAY)
                            .set_session(Session.NORMAL).build())
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Schwab rejected SELL {qty} {sym}: {resp.status_code} {resp.text[:160]}")
    return resp.headers.get("Location", "").rstrip("/").split("/")[-1]


def payout(s: dict, got: float, px: float, cap: float | None) -> dict:
    """Value of what the tender returned (at the sale price, or the delivery mark if not sold) minus what the parent
    shares cost. Fractional shares come back as cash in lieu: counted at the same price when the upper limit set the
    ratio (held x cap rounds down to exactly the shares delivered), otherwise left out (< 1 share) and said so."""
    frac = None
    if cap and math.floor(s["held"] * cap + 1e-9) == int(got):
        frac = s["held"] * cap - int(got)
    value = got * px + (frac or 0.0) * px
    pnl = value - s["cost"]
    return dict(recv_qty=got, recv_px=round(px, 4), cash_in_lieu=round(frac * px, 2) if frac is not None else None,
                value=round(value, 2), pnl=round(pnl, 2), ret=round(pnl / s["cost"], 5))


def _cap(state_dir: Path, s: dict) -> float | None:
    return next((r.get("cap") for r in _read(state_dir / LOG_NAME)
                 if r.get("parent") == s["ticker"] and r.get("expires") == s["expires"] and r.get("cap")), None)


def _deliver(state_dir: Path, s: dict, ad, got: int, mark: float, today: dt.date, notify, log, seller) -> None:
    s.update(delivered=str(today), recv_qty=got, recv_mark=mark)
    try:
        s["sell_order"] = seller(ad, s["recv"], got)
        s.update(status="selling", sell_placed=str(today))
        log(f"[splitoff] {s['recv']} delivered ({got} sh) -> SELL {got} at market (order {s['sell_order']})")
    except Exception as exc:
        log(f"[splitoff] {s['recv']} delivered, sell failed: {str(exc)[:120]} - payout taken at the mark")
        _complete(state_dir, s, got, mark, today, notify, log, sold=False)


def _sold(state_dir: Path, s: dict, ad, today: dt.date, notify, log, seller) -> None:
    status, fq, avg, _ = ad.order_status(None, {"broker_id": s["sell_order"]})
    if status == "filled" and fq >= 1:
        _complete(state_dir, s, fq, avg, today, notify, log, sold=True)
    elif status not in ("filled", "new") and s.get("sell_placed", "") < str(today):
        log(f"[splitoff] {s['recv']} sell {status} - placing it again")      # a DAY order that expired unfilled
        _deliver(state_dir, s, ad, int(s["recv_qty"]), s["recv_mark"], today, notify, log, seller)


def _complete(state_dir: Path, s: dict, got: float, px: float, today: dt.date, notify, log, sold: bool) -> None:
    from . import cpc_ledger as L
    p = payout(s, got, px, _cap(state_dir, s))
    s.update(status="sold" if sold else "delivered", resolved=str(today), **p)
    cil = (f" + cash in lieu ~${p['cash_in_lieu']:,.2f}" if p["cash_in_lieu"] is not None
           else " (cash in lieu for the fraction not counted: under one share)")
    line = (f"{s['ticker']}->{s['recv']}: {got:g} {s['recv']} {'sold' if sold else 'marked'} @ ${px:,.2f}{cil} = "
            f"${p['value']:,.2f} vs ${s['cost']:,.2f} paid -> ${p['pnl']:+,.2f} ({p['ret']:+.1%})")
    log(f"[splitoff] {line}")
    eid = L.settle(state_dir / L.LOG_NAME, "SPLIT_OFF",
                   lambda v: v.get("issuer") == s["ticker"] and v.get("deadline", "").startswith(s["expires"]),
                   p["pnl"], note=f"auto from splitoff tracking ({s['account']}): {line}",
                   reopen_note=f"bought {s['held']} {s['ticker']} in {s['account']} on {s['bought']} and tendered; "
                               "the earlier MISSED was wrong", log=log)
    if eid:
        s["ledger"] = eid
    if notify:
        from ..live import mail as M
        tail = ("Sold at the open; done." if sold else
                f"The automatic sell could not be placed: sell the {got:g} {s['recv']} yourself if you do not want "
                f"to hold them. The payout is measured at this delivery mark.")
        notify(f"split-off {s['ticker']}: {s['recv']} {'sold' if sold else 'delivered'}, payout ${p['pnl']:+,.2f}",
               M.page("Split-off exchange offer", f"{s['recv']} {'sold' if sold else 'delivered'}: ${p['pnl']:+,.2f}",
                      f"{s['account'].upper()} · recorded in the CPC ledger",
                      [M.para(line), M.para(tail, muted=True)]))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: make splitoff-buy PARENT=<TICKER>   (from the alert email)"); sys.exit(2)
    sys.exit(main(sys.argv[1], Path(__file__).resolve().parents[2] / "state"))
