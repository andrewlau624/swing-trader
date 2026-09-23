"""Alpaca paper broker wrapper.

Three disciplines, each learned from a specific failure in llm-trader:

1. **Reconcile, don't remember.** Every run re-derives truth from Alpaca's
   positions and orders. Local state is a cache, never the source.
2. **Idempotent orders.** Every order carries a deterministic client_order_id,
   so re-running the same day cannot double-fill. llm-trader had no such id and
   relied on reconciliation alone.
3. **Never hold unprotected overnight.** Every open position must carry a
   working GTC stop; missing stops are re-armed on every cycle.

Entries are market-on-open (TIF=OPG), which is the live equivalent of the
backtest's "decide on today's close, fill at tomorrow's open". The protective
stop is attached after the fill rather than as a bracket, because OPG and
bracket order classes do not combine.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from ..config import require_alpaca_keys


@dataclass
class Fill:
    symbol: str
    side: str
    qty: float
    fill_px: float
    ref_px: float           # the price the signal was computed against
    slippage_bps: float
    order_id: str
    filled_at: str


class PaperBroker:
    def __init__(self, paper: bool = True, key: str | None = None,
                 secret: str | None = None):
        from alpaca.trading.client import TradingClient
        if key is None or secret is None:
            key, secret = require_alpaca_keys()
        if paper and not key.startswith("PK"):
            raise RuntimeError(
                f"key {key[:4]}... is not a paper key; refusing to run live")
        if not paper and key.startswith("PK"):
            raise RuntimeError(
                "live mode was given a PAPER key (PK...); set ALPACA_LIVE_API_KEY "
                "to the real-money key")
        self.client = TradingClient(key, secret, paper=paper)
        self.key = key
        self.secret = secret

    # ---------------------------------------------------------------- state
    def account(self):
        return self.client.get_account()

    def clock(self):
        return self.client.get_clock()

    def positions(self) -> dict:
        return {p.symbol: p for p in self.client.get_all_positions()}

    def open_orders(self) -> list:
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest
        return self.client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))

    def recent_orders(self, days: int = 5) -> list:
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest
        after = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
        return self.client.get_orders(
            GetOrdersRequest(status=QueryOrderStatus.ALL, after=after, limit=500))

    # ---------------------------------------------------------------- orders
    @staticmethod
    def coid(book: str, symbol: str, day: str, kind: str) -> str:
        """Deterministic id: re-running the same decision cannot double-fill."""
        return f"{book}.{symbol}.{day}.{kind}"[:48]

    def submit_entry(self, book: str, symbol: str, qty: float, day: str,
                     ref_px: float) -> tuple[object | None, str]:
        """Market-on-open buy. Returns (order, note)."""
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest
        q = int(qty)   # OPG will not accept fractional quantities
        if q < 1:
            return None, f"qty {qty:.2f} rounds to 0 shares"
        try:
            o = self.client.submit_order(MarketOrderRequest(
                symbol=symbol, qty=q, side=OrderSide.BUY,
                time_in_force=TimeInForce.OPG,
                client_order_id=self.coid(book, symbol, day, "entry")))
            return o, f"submitted MOO buy {q} {symbol} (ref {ref_px:.2f})"
        except Exception as exc:
            msg = str(exc)
            if "client_order_id" in msg or "duplicate" in msg.lower():
                return None, f"{symbol}: already submitted today (idempotent skip)"
            return None, f"{symbol}: entry rejected - {type(exc).__name__}: {msg[:120]}"

    def submit_exit(self, book: str, symbol: str, qty: float, day: str,
                    reason: str) -> tuple[object | None, str]:
        """Close at the open. Cancels the protective stop first -- leaving it
        live alongside a sell would risk selling the same shares twice and
        flipping the account short."""
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest
        self.cancel_stops(symbol)
        q = int(qty)
        if q < 1:
            return None, f"{symbol}: nothing to sell"
        try:
            o = self.client.submit_order(MarketOrderRequest(
                symbol=symbol, qty=q, side=OrderSide.SELL,
                time_in_force=TimeInForce.OPG,
                client_order_id=self.coid(book, symbol, day, f"exit-{reason}")))
            return o, f"submitted MOO sell {q} {symbol} ({reason})"
        except Exception as exc:
            msg = str(exc)
            if "client_order_id" in msg or "duplicate" in msg.lower():
                return None, f"{symbol}: exit already submitted today"
            return None, f"{symbol}: exit rejected - {type(exc).__name__}: {msg[:120]}"

    def cancel_stops(self, symbol: str) -> int:
        n = 0
        for o in self.open_orders():
            if o.symbol == symbol and str(o.order_type).endswith("stop"):
                try:
                    self.client.cancel_order_by_id(o.id)
                    n += 1
                except Exception:
                    pass
        return n

    def stops_by_symbol(self) -> dict:
        out = {}
        for o in self.open_orders():
            if str(o.order_type).endswith("stop"):
                out[o.symbol] = o
        return out

    def ensure_protection(self, symbol: str, stop_px: float,
                          qty: float) -> tuple[bool, str]:
        """Guarantee a working GTC stop. Swing positions hold overnight, so an
        unprotected position is exposed to exactly the gap risk the -10% stop
        exists to bound."""
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import StopOrderRequest
        existing = self.stops_by_symbol().get(symbol)
        if existing is not None:
            return False, ""
        q = int(qty)
        if q < 1:
            return False, f"{symbol}: no shares to protect"
        try:
            self.client.submit_order(StopOrderRequest(
                symbol=symbol, qty=q, side=OrderSide.SELL,
                stop_price=round(float(stop_px), 2),
                time_in_force=TimeInForce.GTC))
            return True, f"armed stop {symbol} @ {stop_px:.2f} ({q} sh)"
        except Exception as exc:
            return False, f"{symbol}: STOP FAILED - {type(exc).__name__}: {str(exc)[:110]}"

    def unprotected(self, expected_stops: dict[str, float]) -> list[str]:
        held, stops = self.positions(), self.stops_by_symbol()
        return [s for s in held if s in expected_stops and s not in stops]

    # ------------------------------------------------------------ slippage
    def measure_fills(self, refs: dict[str, dict]) -> list[Fill]:
        """Compare each filled order to the price its signal was computed on.

        This is the single number the whole live exercise exists to produce:
        the backtest assumed 20bps per side, and only real fills can say
        whether that was optimistic.
        """
        out = []
        for o in self.recent_orders(days=5):
            if not o.filled_at or not o.filled_avg_price:
                continue
            coid = o.client_order_id or ""
            ref = refs.get(coid)
            if ref is None:
                continue
            fill = float(o.filled_avg_price)
            rp = float(ref["ref_px"])
            side = str(o.side).split(".")[-1].lower()
            # slippage always measured as cost: positive = worse than reference
            bps = (fill / rp - 1.0) * 10_000 * (1 if side == "buy" else -1)
            out.append(Fill(symbol=o.symbol, side=side, qty=float(o.filled_qty),
                            fill_px=fill, ref_px=rp, slippage_bps=bps,
                            order_id=str(o.id), filled_at=str(o.filled_at)))
        return out
