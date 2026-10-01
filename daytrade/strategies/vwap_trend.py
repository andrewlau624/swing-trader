"""VWAP trend (Zarattini & Aziz 2023). Plan: daytrade/plans/vwap_trend.md (Study AW). Long while the signal
instrument's 1-minute close is above its session VWAP, short below; reverse on a cross."""
from __future__ import annotations

from ..events import Order
from .base import Strategy

STOP_PCT = 0.02          # catastrophe stop; the signal is the real exit


class VwapTrend(Strategy):
    name = "vwap_trend"

    def __init__(self, signal: str = "QQQ", trade: str = "QQQ"):
        self.signal, self.trade = signal, trade

    def on_session_start(self, ctx) -> list:
        self.pv = self.vol = 0.0
        self.side = 0
        self.desired = 0
        self.desired_ts = None
        return []

    def on_bar(self, ctx, bar) -> list:
        if bar.start < ctx.session.open:
            return []
        if bar.sym == self.signal:
            self.pv += (bar.high + bar.low + bar.close) / 3 * bar.volume
            self.vol += bar.volume
            if self.vol > 0:
                vwap = self.pv / self.vol
                if bar.close > vwap:
                    self.desired = 1
                elif bar.close < vwap:
                    self.desired = -1
                self.desired_ts = bar.ts
        if bar.sym != self.trade or self.desired_ts != bar.ts or self.desired in (0, self.side):
            return []
        out = []
        if ctx.position(self.trade) != 0:
            out.append(Order(self.trade, "sell" if ctx.position(self.trade) > 0 else "buy", entry=False,
                             reason="VWAP cross"))
        px = bar.close
        long = self.desired > 0
        out.append(Order(self.trade, "buy" if long else "sell", ref_price=px,
                         stop=round(px * (1 - STOP_PCT) if long else px * (1 + STOP_PCT), 2),
                         reason=f"{'above' if long else 'below'} VWAP"))
        self.side = self.desired
        return out
