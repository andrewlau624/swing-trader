"""Opening L1 quote imbalance + signed trade flow on the core ETFs. Plan:
daytrade/plans/open_imbalance.md (Study Lab-AT). Needs the lab's own L1 recording; minute bars
cannot drive it (it ignores bars)."""
from __future__ import annotations

import math

from ..events import TICK, Order
from .base import Strategy

SYMBOLS = ("QQQ", "SPY", "TQQQ", "IWM", "SMH")
WINDOW_START, WINDOW_END = "09:30:00", "09:35:00"     # [start, end)
EXIT_AT = "10:05:00"
QI_MIN, FLOW_MIN = 0.20, 0.10


class OpenImbalance(Strategy):
    name = "open_imbalance"

    def on_session_start(self, ctx) -> list:
        self.t0 = ctx.session.at(WINDOW_START)
        self.t1 = ctx.session.at(WINDOW_END)
        self.t_exit = ctx.session.at(EXIT_AT)
        self.last_q: dict[str, object] = {}
        self.sampled_to: dict[str, int] = {}
        self.qi: dict[str, list] = {s: [] for s in SYMBOLS}
        self.flow_num = dict.fromkeys(SYMBOLS, 0.0)
        self.flow_den = dict.fromkeys(SYMBOLS, 0.0)
        self.last_px: dict[str, float] = {}
        self.last_sign: dict[str, int] = {}
        self.lo: dict[str, float] = {}
        self.hi: dict[str, float] = {}
        self.decided = self.exited = False
        return []

    def _sample(self, ctx) -> None:
        """One QI sample per elapsed second inside the window, from the last known quote."""
        upto = min(int((min(ctx.now, self.t1) - self.t0).total_seconds()), 300)
        for s, q in self.last_q.items():
            start = self.sampled_to.get(s, 0)
            if upto <= start:
                continue
            tot = q.bid_size + q.ask_size
            if tot > 0:
                self.qi[s].extend([(q.bid_size - q.ask_size) / tot] * (upto - start))
            self.sampled_to[s] = upto

    def on_quote(self, ctx, q) -> list:
        if q.sym in SYMBOLS and ctx.now < self.t1:
            if ctx.now >= self.t0:
                self._sample(ctx)
            self.last_q[q.sym] = q
        return []

    def on_trade(self, ctx, t) -> list:
        s = t.sym
        if s not in SYMBOLS or not (self.t0 <= ctx.now < self.t1) or t.size <= 0:
            return []
        q = self.last_q.get(s)
        prev = self.last_px.get(s)
        if q is not None and t.price >= q.ask:
            sign = 1
        elif q is not None and t.price <= q.bid:
            sign = -1
        elif prev is not None and t.price != prev:
            sign = 1 if t.price > prev else -1
        else:
            sign = self.last_sign.get(s, 0)
        self.last_sign[s], self.last_px[s] = sign, t.price
        self.flow_num[s] += sign * t.size
        self.flow_den[s] += t.size
        self.lo[s] = min(self.lo.get(s, math.inf), t.price)
        self.hi[s] = max(self.hi.get(s, -math.inf), t.price)
        return []

    def on_clock(self, ctx) -> list:
        out = []
        if not self.decided and ctx.now >= self.t1:
            self._sample(ctx)
            self.decided = True
            for s in SYMBOLS:
                q, n = self.last_q.get(s), len(self.qi[s])
                if q is None or n == 0 or self.flow_den[s] <= 0 or s not in self.lo:
                    continue
                qi, flow = sum(self.qi[s]) / n, self.flow_num[s] / self.flow_den[s]
                mid = (q.bid + q.ask) / 2
                why = f"QI {qi:+.2f} FLOW {flow:+.2f}"
                if qi >= QI_MIN and flow >= FLOW_MIN:
                    out.append(Order(s, "buy", ref_price=mid, stop=round(self.lo[s] - TICK, 2), reason=why))
                elif qi <= -QI_MIN and flow <= -FLOW_MIN and not ctx.is_cash_account():
                    out.append(Order(s, "sell", ref_price=mid, stop=round(self.hi[s] + TICK, 2), reason=why))
        if not self.exited and ctx.now >= self.t_exit:
            self.exited = True
            out += [Order(s, "sell" if ctx.position(s) > 0 else "buy", entry=False, reason="10:05 exit")
                    for s in SYMBOLS if ctx.position(s) != 0]
        return out
