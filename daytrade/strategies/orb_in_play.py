"""5-minute opening-range breakout on Stocks in Play (Zarattini, Barbon & Aziz 2024). Plan:
daytrade/plans/orb_in_play.md (Study Lab-AU). Thresholds are fixed by the plan."""
from __future__ import annotations

from ..events import Order
from .base import Strategy

OPEN_MIN = 5.0
AVG_VOL_MIN = 1_000_000
ATR_MIN = 0.50
RVOL_MIN = 1.0
TOP_N = 20
OR_BARS = 5                 # 09:30-09:34
STOP_ATR = 0.10


class OrbInPlay(Strategy):
    name = "orb_in_play"
    status = "dead: Study Lab-AU (−23.5bp/trade; optimistic bound below costs)"

    def __init__(self, long_only: bool = False):
        self.long_only = long_only

    def on_session_start(self, ctx) -> list:
        self.bars: dict[str, list] = {}
        self.sent = False
        return []

    def on_bar(self, ctx, bar) -> list:
        if bar.start < ctx.session.open:
            return []
        n = len(self.bars.setdefault(bar.sym, []))
        if n < OR_BARS and bar.start == ctx.session.open.replace(minute=30 + n):
            self.bars[bar.sym].append(bar)
        if self.sent or bar.ts < ctx.session.at("09:35"):
            return []
        # decide once every symbol's 09:34 bar is in (they arrive one by one at the same time);
        # a name with a missing opening minute cannot hold the others past the next minute
        complete = all(len(bs) >= OR_BARS for bs in self.bars.values())
        if not complete and bar.ts <= ctx.session.at("09:35"):
            return []
        self.sent = True
        return self._orders(ctx)

    def _orders(self, ctx) -> list:
        rows = []
        for sym, bs in self.bars.items():
            d = ctx.day_info(sym)
            if d is None or len(bs) < OR_BARS or d.or_volume_avg14 <= 0:
                continue
            if bs[0].open <= OPEN_MIN or d.avg_volume14 < AVG_VOL_MIN or d.atr14 <= ATR_MIN:
                continue
            rvol = sum(b.volume for b in bs) / d.or_volume_avg14
            if rvol >= RVOL_MIN:
                rows.append((rvol, sym))
        out = []
        for rvol, sym in sorted(rows, reverse=True)[:TOP_N]:
            bs, atr = self.bars[sym], ctx.day_info(sym).atr14
            o, c = bs[0].open, bs[-1].close
            hi, lo = max(b.high for b in bs), min(b.low for b in bs)
            why = f"ORB rvol {rvol:.1f}"
            if c > o:
                out.append(Order(sym, "buy", "stop", stop_px=hi, ref_price=hi,
                                 stop=round(hi - STOP_ATR * atr, 2), reason=why))
            elif c < o and not self.long_only:
                out.append(Order(sym, "sell", "stop", stop_px=lo, ref_price=lo,
                                 stop=round(lo + STOP_ATR * atr, 2), reason=why))
        return out
