"""Reverse-split round-up: the automatic 1-share buys and sells (Round 32 B1; user-approved 2026-10-02).

Runs inside `roundup_watch.run` every weekday morning, only when ROUNDUP_AUTO=1 in .env. For every alerted split
whose buy-by session is today or later, it places ONE 1-share DAY limit buy in each account in ROUNDUP_ACCOUNTS
(default "live,roth"), so the share is held at the last pre-split close. After the ex-date it watches the position:
1+ share from 2 days after the ex-date (never earlier: an unprocessed split still shows the old share) -> "rounded" (the round-up was paid) and a 1-share DAY market sell is placed; still 0 shares 21
days after the ex-date -> "cash" (Schwab paid cash in lieu). Kill switch per account: once 2 deals are "cash" and none
"rounded", that account stops buying and an email says so. Each resolved account gets a payout (sell fill - buy fill;
cash in lieu estimated from the ask / ratio), and once the whole deal is resolved the total is booked in the CPC ledger.

Caps: price <= $25, at most 3 buys per account per day, never a symbol the account already holds (the daily book's
or anyone's). The executor treats these shares as foreign (never trades or sizes on them).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
from pathlib import Path

ORDERS_NAME = "roundup-orders.json"
MAX_PRICE, MAX_PER_DAY, CASH_AFTER_DAYS, KILL_CASH, SETTLE_DAYS = 25.0, 3, 21, 2, 2


def enabled() -> bool:
    return os.environ.get("ROUNDUP_AUTO", "0").strip() == "1"


def accounts() -> list[str]:
    return [a.strip() for a in os.environ.get("ROUNDUP_ACCOUNTS", "live,roth").split(",") if a.strip()]


def buy_limit(price: float) -> float:
    """Just above the ask so a 1-share order fills. Schwab rejects limits far from the last trade, so stay within ~2%;
    sub-$1 names are priced to 4 decimals."""
    if price < 1:
        return math.ceil(round(price * 1.02 * 1e4, 6)) / 1e4
    return math.ceil(round(price * 1.01 * 100, 6)) / 100


def ask(ad, sym: str) -> float | None:
    """Schwab's own ask (falls back to the last trade); None when there is no quote."""
    try:
        q = ad.c.get_quote(sym).json()[sym]["quote"]
        return float(q.get("askPrice") or q.get("lastPrice") or 0) or None
    except Exception:
        return None


def killed(st: dict, acct: str) -> bool:
    res = [d[acct]["status"] for d in st.values() if acct in d and d[acct].get("status") in ("rounded", "cash", "sold")]
    return res.count("cash") >= KILL_CASH and not any(s in ("rounded", "sold") for s in res)


def _load(state_dir: Path) -> dict:
    p = Path(state_dir) / ORDERS_NAME
    return json.loads(p.read_text()) if p.exists() else {}


def _save(state_dir: Path, st: dict) -> None:
    (Path(state_dir) / ORDERS_NAME).write_text(json.dumps(st, indent=1))


def place(ad, sym: str, side: str, limit: float | None = None) -> str:
    from schwab.orders.common import Duration, Session
    from schwab.orders.equities import equity_buy_limit, equity_sell_market
    px = (f"{limit:.4f}" if limit < 1 else f"{limit:.2f}") if limit is not None else None
    o = (equity_buy_limit(sym, 1, px) if side == "buy" else equity_sell_market(sym, 1))
    resp = ad.c.place_order(ad.hash, o.set_duration(Duration.DAY).set_session(Session.NORMAL).build())
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Schwab rejected {side} 1 {sym}: {resp.status_code} {resp.text[:160]}")
    oid = resp.headers.get("Location", "").rstrip("/").split("/")[-1]
    try:                                   # Schwab accepts the request, then may reject the order itself
        r = ad.c.get_order(oid, ad.hash).json()
        if r.get("status") == "REJECTED":
            raise RuntimeError(f"Schwab rejected {side} 1 {sym} @ {px}: {r.get('statusDescription', '')[:120]}")
    except RuntimeError:
        raise
    except Exception:
        pass
    return oid


def manage(state_dir: Path, alerts: list[dict], today: dt.date, adapters: dict | None = None, prices: dict | None = None,
           placer=place, notify=None, log=print, events: list | None = None) -> dict:
    """Buy what is due, then follow each held deal to rounded/cash; returns the order state. `events` collects
    (kind, account, symbol, detail) for this run's email: bought / sold / cash."""
    ev = events if events is not None else []
    st = _load(state_dir)
    if adapters is None:
        from .brokers import make_adapter
        adapters = {}
        for a in accounts():
            try:
                adapters[a] = make_adapter(a)
            except Exception as exc:
                log(f"[roundup] {a} unavailable: {str(exc)[:80]}")
    held = {a: ad.positions() for a, ad in adapters.items()}
    # 1. buys: alerted, buy-by today or later, not after the ex-date
    bought_today = {a: 0 for a in adapters}
    for r in alerts:
        key = f"{r['ticker']}-{r['trade_date']}"
        if r["buy_by"] < str(today) or r["trade_date"] <= str(today):
            continue
        for a, ad in adapters.items():
            d = st.setdefault(key, {})
            if a in d or killed(st, a) or bought_today[a] >= MAX_PER_DAY or r["ticker"] in held[a]:
                continue
            px = (prices or {}).get(r["ticker"]) if prices is not None else ask(ad, r["ticker"])
            if not px or px > MAX_PRICE:
                log(f"[roundup] {a}: no usable quote for {r['ticker']} ({px}) - retry next run"); continue
            lim = buy_limit(float(px))
            try:
                oid = placer(ad, r["ticker"], "buy", lim)
            except Exception as exc:
                log(f"[roundup] {a} BUY 1 {r['ticker']} failed: {str(exc)[:120]}"); continue
            d[a] = dict(status="ordered", order_id=oid, limit=lim, placed=str(today), ex=r["trade_date"], ratio=r["ratio"])
            bought_today[a] += 1
            ev.append(("bought", a, r["ticker"], f"1 share, limit ${lim:g}, split {r['trade_date'][5:]}"))
            log(f"[roundup] {a}: BUY 1 {r['ticker']} limit ${lim:.2f} (ex {r['trade_date']}, 1-for-{r['ratio']:g}) order {oid}")
    # 2. follow-up
    for key, d in st.items():
        sym = key.rsplit("-", 3)[0]
        for a, s in d.items():
            if a not in adapters:
                continue
            q = float(getattr(held[a].get(sym), "qty", 0.0) or 0.0)
            ex = dt.date.fromisoformat(s["ex"])
            if s["status"] == "ordered" and today < ex:
                s["status"] = "held" if q >= 1 else ("ordered" if s["placed"] == str(today) else "unfilled")
            elif s["status"] in ("ordered", "held", "waiting") and today < ex + dt.timedelta(days=SETTLE_DAYS):
                s["status"] = "waiting"          # the broker may not have processed the split yet: decide nothing
            elif s["status"] in ("ordered", "held", "waiting"):
                if q >= 1:
                    s.update(status="rounded", rounded=str(today), post_qty=q)
                    try:
                        s["sell_order"] = placer(adapters[a], sym, "sell")
                        s["status"] = "sold"
                        ev.append(("sold", a, sym, f"round-up PAID: {q:g} post-split share(s); selling 1 at the open"))
                        log(f"[roundup] {a}: {sym} round-up PAID ({q:g} sh) -> SELL 1 at market")
                    except Exception as exc:
                        log(f"[roundup] {a}: {sym} rounded, sell failed: {str(exc)[:120]}")
                elif (today - ex).days >= CASH_AFTER_DAYS:
                    s.update(status="cash", resolved=str(today))
                    ev.append(("cash", a, sym, f"no post-split share {CASH_AFTER_DAYS} days after the split: cash in lieu"))
                    log(f"[roundup] {a}: {sym} no post-split share after {CASH_AFTER_DAYS} days -> cash in lieu")
                    if killed(st, a) and notify:
                        from ..live import mail as M
                        deals = [k for k, x in st.items() if x.get(a, {}).get("status") == "cash"]
                        notify(f"round-up auto-buy STOPPED in {a}", M.page(
                            "Reverse-split round-up", f"Auto-buy stopped in {a}", "Schwab pays cash instead of a share",
                            [M.action("Stopped", "No more round-up buys in this account", lines=[
                                f"Schwab paid cash in lieu (no post-split share) on {len(deals)} deals and rounded none "
                                f"up in {a}, so the edge does not exist there."], tone="warn"),
                             M.bullets(deals, "Deals"),
                             M.fine("To re-enable after checking with Schwab, remove those deals from "
                                    "state/roundup-orders.json.")]))
                else:
                    s["status"] = "waiting"
    _book(state_dir, st, adapters, log)
    _save(state_dir, st)
    return st


def _fill(ad, oid) -> float | None:
    try:
        status, fq, avg, _ = ad.order_status(None, {"broker_id": str(oid)})
    except Exception:
        return None
    return avg if status == "filled" and fq >= 1 else None


def _book(state_dir: Path, st: dict, adapters: dict, log) -> None:
    """Payout per account once a deal resolves: sold -> sell fill - buy fill (buy limit if the fill is unknown);
    cash -> cash in lieu estimated as today's ask / ratio - buy. When every account in the deal is resolved, the
    total goes to the CPC ledger (COMPLETED; a wrong MISSED is reopened first)."""
    from . import cpc_ledger as L
    for key, d in st.items():
        sym, ex = key.rsplit("-", 3)[0], key[-10:]
        for a, s in d.items():
            if "pnl" in s or a not in adapters or s.get("status") not in ("sold", "cash"):
                continue
            buy = _fill(adapters[a], s.get("order_id")) or s.get("limit")
            if s["status"] == "sold":
                px = _fill(adapters[a], s.get("sell_order"))
                if px is None:
                    continue                                     # the sell has not filled yet
                s.update(sell_px=px, pnl=round(px - buy, 2), est=False)
            else:
                px = ask(adapters[a], sym)
                if not px or not s.get("ratio"):
                    continue
                s.update(cil_est=round(px / s["ratio"], 4), pnl=round(px / s["ratio"] - buy, 2), est=True)
            s["buy_px"] = buy
            log(f"[roundup] {a}: {sym} {s['status']} -> ${s['pnl']:+.2f}" + (" (cash in lieu estimated)" if s["est"] else ""))
        done = [s for s in d.values() if s.get("status") in ("sold", "cash")]
        if not done or any(s.get("booked") for s in done) or any("pnl" not in s for s in done) \
                or any(s.get("status") in ("ordered", "held", "waiting", "rounded") for s in d.values()):
            continue
        pnl = round(sum(s["pnl"] for s in done), 2)
        note = "; ".join(f"{a} {s['status']} ${s['pnl']:+.2f}" + (" est" if s["est"] else "") for a, s in d.items()
                         if s in done)
        eid = L.settle(Path(state_dir) / L.LOG_NAME, "REVERSE_SPLIT_ROUNDUP",
                       lambda v: v.get("security") == sym and v.get("event_date") == ex, pnl,
                       note=f"auto from roundup tracking: {note}",
                       reopen_note=f"1-share buys in {', '.join(a for a, s in d.items() if s in done)}; the MISSED was wrong",
                       log=log)
        for s in done:
            s["booked"] = eid or True
