"""Real brokers for the lab's paper and live modes. Same interface as fills.SimBroker:
submit(order, qty, now) -> id, cancel(id), on_event(ev) -> [Fill], open_orders().

Paper: the lab's OWN Alpaca paper account (ALPACA_DAYTRADE_API_KEY), never the live book's.
Live: Schwab, the account named by SCHWAB_DAYTRADE_ACCOUNT_NUMBER, after the account guard, the
written approval file and a capital cap of $500. No live order is possible without all three.
Fills are polled at most every `poll_s` seconds.
"""
from __future__ import annotations

import datetime as dt
import time

from .events import Fill, Order
from .guard import AccountGuardError, OTHER_ENVS, check_lab_account, check_paper_keys, check_resolved
from .settings import LIVE_APPROVAL, LIVE_CAPITAL_MAX, env


class AlpacaLabPaper:
    def __init__(self, poll_s: float = 2.0, trading=None):
        if trading is None:
            from alpaca.trading.client import TradingClient
            k, s = check_paper_keys()
            trading = TradingClient(k, s, paper=True)
        self.t = trading
        self.ids: dict[int, str] = {}
        self.orders: dict[int, Order] = {}
        self.seen: dict[int, float] = {}
        self.poll_s, self._last = poll_s, 0.0

    def equity(self) -> float:
        return float(self.t.get_account().equity)

    def submit(self, o: Order, qty: int, now) -> int:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest, StopOrderRequest
        side = OrderSide.BUY if o.side == "buy" else OrderSide.SELL
        common = dict(symbol=o.sym, qty=qty, side=side, time_in_force=TimeInForce.DAY,
                      client_order_id=f"dt-{o.strategy[:12]}-{o.id}-{int(time.time())}")
        if o.kind == "limit":
            req = LimitOrderRequest(limit_price=round(o.limit, 2), **common)
        elif o.kind == "stop":
            req = StopOrderRequest(stop_price=round(o.stop_px, 2), **common)
        else:
            req = MarketOrderRequest(**common)
        self.ids[o.id] = str(self.t.submit_order(req).id)
        self.orders[o.id] = o
        return o.id

    def cancel(self, oid: int) -> None:
        bid = self.ids.get(oid)
        if bid:
            try:
                self.t.cancel_order_by_id(bid)
            except Exception:
                pass                       # already filled or gone; a late fill is still reported

    def cancel_all(self) -> None:
        self.t.cancel_orders()

    def open_orders(self) -> list[Order]:
        return list(self.orders.values())

    def on_event(self, ev) -> list[Fill]:
        if time.time() - self._last < self.poll_s:
            return []
        self._last = time.time()
        out = []
        for oid, bid in list(self.ids.items()):
            bo = self.t.get_order_by_id(bid)
            fq = float(bo.filled_qty or 0)
            new = fq - self.seen.get(oid, 0.0)
            status = str(bo.status).split(".")[-1].lower()
            if new > 0 and status == "filled":
                self.seen[oid] = fq
                ts = bo.filled_at or dt.datetime.now(dt.timezone.utc)
                o = self.orders[oid]
                out.append(Fill(oid, o.sym, o.side, int(fq), float(bo.filled_avg_price), ts, "paper"))
            if status in ("filled", "canceled", "expired", "rejected"):
                self.ids.pop(oid, None)
                self.orders.pop(oid, None)
        return out


def live_allowed(capital: float) -> None:
    """Every condition for a real-money order, or raise. README section 8 is the gate."""
    check_lab_account()
    if (env("DAYTRADE_LIVE") or "").strip().lower() != "on":
        raise AccountGuardError("DAYTRADE_LIVE is not 'on'")
    if not LIVE_APPROVAL.exists():
        raise AccountGuardError(f"no written approval at {LIVE_APPROVAL} (README section 8)")
    if capital > LIVE_CAPITAL_MAX:
        raise AccountGuardError(f"lab capital ${capital:,.0f} is over the ${LIVE_CAPITAL_MAX:,.0f} test cap")


class SchwabLabLive:
    """Schwab orders on the lab account only. Built on the live book's Schwab login (read-only use
    of its helpers); the account is resolved by SCHWAB_DAYTRADE_ACCOUNT_NUMBER and checked against
    every other book's resolved account before anything is sent."""

    def __init__(self, capital: float, client=None, poll_s: float = 2.0):
        live_allowed(capital)
        from swingtrader.daily.brokers import SchwabAdapter
        self.a = SchwabAdapter(client=client, account_env="SCHWAB_DAYTRADE_ACCOUNT_NUMBER")
        self.c = self.a.c
        nums = {x["hashValue"]: x["accountNumber"] for x in self.c.get_account_numbers().json()}
        lab_full = nums[self.a.hash]
        others = {}
        for name in OTHER_ENVS:
            want = "".join(ch for ch in (env(name) or "") if ch.isdigit())
            if want:
                others.update({name: n for n in nums.values() if n == want or n.endswith(want)})
        check_resolved(lab_full, others)
        self.capital = capital
        self.ids: dict[int, str] = {}
        self.orders: dict[int, Order] = {}
        self.poll_s, self._last = poll_s, 0.0

    def equity(self) -> float:
        return min(self.a.account().equity, self.capital)

    def submit(self, o: Order, qty: int, now) -> int:
        from schwab.orders.common import Duration, OrderType, Session
        from schwab.orders.equities import (equity_buy_limit, equity_buy_market, equity_sell_limit,
                                            equity_sell_market)
        if o.side == "sell" and o.entry:
            raise AccountGuardError("the live lab is long-only until a short plan passes paper")
        if o.kind == "limit":
            b = (equity_buy_limit if o.side == "buy" else equity_sell_limit)(o.sym, qty, f"{o.limit:.2f}")
        elif o.kind == "stop":
            b = equity_sell_market(o.sym, qty).set_order_type(OrderType.STOP).set_stop_price(f"{o.stop_px:.2f}")
        else:
            b = (equity_buy_market if o.side == "buy" else equity_sell_market)(o.sym, qty)
        order = b.set_duration(Duration.DAY).set_session(Session.NORMAL).build()
        r = self.c.place_order(self.a.hash, order)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Schwab rejected {o.side} {qty} {o.sym}: {r.status_code} {r.text[:160]}")
        self.ids[o.id] = r.headers.get("Location", "").rstrip("/").split("/")[-1]
        self.orders[o.id] = o
        return o.id

    def cancel(self, oid: int) -> None:
        bid = self.ids.get(oid)
        if bid:
            try:
                self.c.cancel_order(int(bid), self.a.hash)
            except Exception:
                pass

    def cancel_all(self) -> None:
        for oid in list(self.ids):
            self.cancel(oid)

    def open_orders(self) -> list[Order]:
        return list(self.orders.values())

    def on_event(self, ev) -> list[Fill]:
        if time.time() - self._last < self.poll_s:
            return []
        self._last = time.time()
        out = []
        for oid, bid in list(self.ids.items()):
            status, fq, avg, when = self.a.order_status(None, {"broker_id": bid})
            if status == "filled" and fq > 0:
                o = self.orders[oid]
                out.append(Fill(oid, o.sym, o.side, int(fq), avg, dt.datetime.now(dt.timezone.utc), "live"))
            if status in ("filled", "canceled", "expired", "rejected", "replaced"):
                self.ids.pop(oid, None)
                self.orders.pop(oid, None)
        return out
