"""Gap + premarket volume, pullback to VWAP, reclaim entry. Plan: daytrade/plans/gap_vwap_reclaim.md
(Study Lab-AS). Every threshold below is fixed by the plan; changing one is a new variant."""
from __future__ import annotations

from ..events import TICK, Order
from .base import Strategy

GAP_MIN = 0.04
PREMARKET_MIN = 250_000
PRICE_MIN, PRICE_MAX = 5.0, 1000.0
ADV_MIN = 5e6
CAP = 5
PULLBACK_FROM = "09:36"     # a pullback bar must END at or after this
SELECT_AT = "09:32"         # every 09:30 bar has arrived by now; selection uses only their opens
SIGNAL_BY = "11:30"
R_MIN, R_MAX = 0.002, 0.05
TARGET_R = 2.0


class GapVwapReclaim(Strategy):
    name = "gap_vwap_reclaim"
    status = "dead: Study Lab-AS (−18.9bp/trade, gross −1.7bp)"

    def on_session_start(self, ctx) -> list:
        self.first_open: dict[str, float] = {}
        self.pv: dict[str, float] = {}
        self.vol: dict[str, float] = {}
        self.prev_high: dict[str, float] = {}
        self.touched: dict[str, bool] = {}
        self.pull_low: dict[str, float] = {}
        self.done: set[str] = set()
        self.picks: list[str] | None = None
        return []

    def _select(self, ctx) -> list[str]:
        rows = []
        for sym, op in self.first_open.items():
            d = ctx.day_info(sym)
            if d is None or not (PRICE_MIN <= d.prev_close <= PRICE_MAX):
                continue
            if d.adv20_usd < ADV_MIN or d.premarket_volume < PREMARKET_MIN:
                continue
            if op / d.prev_close - 1 >= GAP_MIN:
                rows.append((d.premarket_volume, sym))
        return [s for _, s in sorted(rows, reverse=True)[:CAP]]

    def on_bar(self, ctx, bar) -> list:
        s = bar.sym
        if s not in self.first_open:
            if bar.start < ctx.session.open or bar.start > ctx.session.at("09:30"):
                return []           # no 09:30 bar: no official open for this name today
            self.first_open[s] = bar.open
        self.pv[s] = self.pv.get(s, 0.0) + (bar.high + bar.low + bar.close) / 3 * bar.volume
        self.vol[s] = self.vol.get(s, 0.0) + bar.volume
        if self.picks is None and bar.ts >= ctx.session.at(SELECT_AT):
            self.picks = self._select(ctx)
        out = []
        if self.picks and s in self.picks and s not in self.done and self.vol[s] > 0:
            out = self._step(ctx, bar)
        self.prev_high[s] = bar.high
        return out

    def _step(self, ctx, bar) -> list:
        s = bar.sym
        vwap = self.pv[s] / self.vol[s]
        prev_close = ctx.day_info(s).prev_close
        if not self.touched.get(s):
            if bar.ts >= ctx.session.at(PULLBACK_FROM) and bar.low <= vwap and vwap > prev_close:
                self.touched[s] = True
                self.pull_low[s] = bar.low
            else:
                return []
        else:
            self.pull_low[s] = min(self.pull_low[s], bar.low)
        ph = self.prev_high.get(s)
        if bar.ts > ctx.session.at(SIGNAL_BY) or ph is None:
            return []
        if bar.close > vwap and bar.close > ph:
            stop = round(self.pull_low[s] - TICK, 2)
            r = bar.close - stop
            if not (R_MIN <= r / bar.close <= R_MAX):
                return []           # this signal is skipped; a later valid one may still trade
            self.done.add(s)
            return [Order(s, "buy", ref_price=bar.close, stop=stop,
                          target=round(bar.close + TARGET_R * r, 2),
                          reason=f"VWAP reclaim (vwap {vwap:.2f}, pullback low {self.pull_low[s]:.2f})")]
        return []
