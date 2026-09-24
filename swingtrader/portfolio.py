"""Portfolio accounting for N concurrent positions with a daily equity curve.

llm-trader's LocalAccount holds a single position slot, which is architectural
rather than incidental, so this is written fresh. Two disciplines carried over
from it: equity is the source of truth (never a running sum of trade results,
which silently drops costs), and the equity curve is sampled every bar rather
than only on trade close -- without a time-indexed curve you cannot compute a
daily return series, and therefore cannot compute Sharpe at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import pandas as pd


@dataclass
class Position:
    symbol: str
    side: int
    qty: float
    entry_px: float          # after slippage
    entry_date: pd.Timestamp
    stop_px: float | None = None
    peak: float = 0.0        # high-water mark since entry, for trailing exits
    bars_held: int = 0
    mfe: float = 0.0         # max favourable excursion, %
    mae: float = 0.0         # max adverse excursion, %
    last_px: float = 0.0     # last observed mark; avoids freezing at entry_px

    def unrealized(self, px: float) -> float:
        return (px - self.entry_px) * self.qty * self.side

    def pct(self, px: float) -> float:
        return (px / self.entry_px - 1.0) * 100.0 * self.side


@dataclass
class Trade:
    symbol: str
    side: int
    qty: float
    entry_date: pd.Timestamp
    entry_px: float
    exit_date: pd.Timestamp
    exit_px: float
    pnl: float
    pnl_pct: float
    bars_held: int
    exit_reason: str
    mfe: float
    mae: float
    fold: int = -1

    def to_dict(self) -> dict:
        d = asdict(self)
        d["entry_date"] = str(self.entry_date.date())
        d["exit_date"] = str(self.exit_date.date())
        d["side"] = "long" if self.side > 0 else "short"
        return d


class Portfolio:
    def __init__(self, equity: float, max_positions: int,
                 slippage_bps: float, commission_per_share: float = 0.0,
                 position_pct: float | None = None,
                 max_gross_pct: float = 100.0,
                 cash_yield_annual: float = 0.0,
                 cash_returns: "pd.Series | None" = None):
        """position_pct: fraction of equity per position.

        Defaults to 1/max_positions, which is what a naive equal-weight scheme
        does -- and which turns out to be the single biggest drag in this
        strategy. Signals are rare enough that mean concurrent positions is
        1.29 against 8 slots, so equal-weighting on the CAP deploys ~16% of
        capital on average and leaves 86% of position-days idle. Sizing against
        typical usage instead of worst-case usage, with a gross cap to bound
        the tail, is worth more than any signal improvement tested so far.
        """
        self.position_pct = position_pct if position_pct else 1.0 / max_positions
        self.max_gross_pct = max_gross_pct
        # Prefer an actual daily return series (e.g. BIL, the 1-3mo T-bill ETF)
        # over a flat assumed rate. Rates ran from -0.10% in 2021 to 5.18% in
        # 2024; a flat 4% would invent ~4 points of return in 2021 that did not
        # exist, which is exactly the kind of quiet fiction this project is
        # built to avoid.
        self.cash_returns = cash_returns
        self.cash_rate_daily = (1.0 + cash_yield_annual) ** (1.0 / 252.0) - 1.0
        self.cash = equity
        self.start_equity = equity
        self.max_positions = max_positions
        self.slip = slippage_bps / 10_000.0
        self.commission = commission_per_share
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.curve: list[tuple[pd.Timestamp, float]] = []
        self.rejected_no_slot = 0

    # -- costs ----------------------------------------------------------
    def fill_price(self, px: float, side: int, opening: bool) -> float:
        """Slippage always works against us, on entry and on exit."""
        sign = side if opening else -side
        return px * (1.0 + sign * self.slip)

    # -- equity ---------------------------------------------------------
    def equity(self, marks: dict[str, float]) -> float:
        """Cash plus the signed market value of open positions.

        Shorts are signed NEGATIVE. Opening a short already credits the sale
        proceeds to cash, so the open position is a liability to buy back --
        valuing it positively double-counts and mints equity out of nothing.
        An earlier version did exactly that: a 25k short instantly created 50k
        of equity, which let long/short runs post a 1.09 Sharpe alongside a
        -24% CAGR and a -100% drawdown.
        """
        eq = self.cash
        for sym, p in self.positions.items():
            if sym in marks:
                p.last_px = float(marks[sym])
            # fall back to the LAST observed mark, not the entry price: a halted
            # symbol with no bar today must not freeze its P&L at cost
            px = p.last_px or p.entry_px
            eq += p.qty * px * p.side
        return eq

    def accrue_cash(self, date=None) -> None:
        """Idle cash earns the short rate. With 86% of position-days idle this
        is not a rounding error -- it is most of the capital, most of the time."""
        if self.cash <= 0:
            return
        if self.cash_returns is not None and date is not None:
            try:
                r = float(self.cash_returns.loc[date])
            except (KeyError, TypeError):
                return
            if r == r:  # not NaN
                self.cash *= 1.0 + r
        elif self.cash_rate_daily:
            self.cash *= 1.0 + self.cash_rate_daily

    def mark(self, date: pd.Timestamp, marks: dict[str, float]) -> None:
        self.curve.append((date, self.equity(marks)))

    # -- trading --------------------------------------------------------
    def can_open(self, symbol: str) -> bool:
        if symbol in self.positions:
            return False
        if len(self.positions) >= self.max_positions:
            self.rejected_no_slot += 1
            return False
        return True

    def open(self, symbol: str, side: int, raw_px: float, date: pd.Timestamp,
             equity_now: float, stop_pct: float | None) -> Position | None:
        px = self.fill_price(raw_px, side, opening=True)
        if px <= 0:
            return None
        # cap gross exposure so a rare cluster of signals cannot over-lever
        gross = sum(abs(q.qty) * q.entry_px for q in self.positions.values())
        room = max(0.0, equity_now * self.max_gross_pct / 100.0 - gross)
        budget = min(equity_now * self.position_pct, room)
        if budget <= 0:
            return None
        qty = budget / px
        if qty <= 0:
            return None
        cost = qty * px * (1 if side > 0 else -1) + self.commission * qty
        if side > 0 and cost > self.cash:
            qty = max(0.0, (self.cash - self.commission * 1) / px)
            if qty <= 0:
                return None
            cost = qty * px + self.commission * qty
        self.cash -= cost
        stop = None
        if stop_pct is not None:
            stop = px * (1 - stop_pct / 100.0) if side > 0 else px * (1 + stop_pct / 100.0)
        pos = Position(symbol, side, qty, px, date, stop, peak=px, last_px=px)
        self.positions[symbol] = pos
        return pos

    def close(self, symbol: str, raw_px: float, date: pd.Timestamp,
              reason: str, fold: int = -1) -> Trade:
        pos = self.positions.pop(symbol)
        px = self.fill_price(raw_px, pos.side, opening=False)
        proceeds = pos.qty * px * (1 if pos.side > 0 else -1) - self.commission * pos.qty
        self.cash += proceeds
        pnl = (px - pos.entry_px) * pos.qty * pos.side - self.commission * pos.qty * 2
        t = Trade(
            symbol=symbol, side=pos.side, qty=pos.qty,
            entry_date=pos.entry_date, entry_px=pos.entry_px,
            exit_date=date, exit_px=px, pnl=pnl,
            pnl_pct=(px / pos.entry_px - 1.0) * 100.0 * pos.side,
            bars_held=pos.bars_held, exit_reason=reason,
            mfe=pos.mfe, mae=pos.mae, fold=fold,
        )
        self.trades.append(t)
        return t

    def equity_series(self) -> pd.Series:
        if not self.curve:
            return pd.Series(dtype=float)
        s = pd.Series({d: e for d, e in self.curve}).sort_index()
        return s[~s.index.duplicated(keep="last")]
