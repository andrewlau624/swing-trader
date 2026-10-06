"""Systematic Intraday Day Book (daybook) — a standalone intraday-momentum day trader.

Mechanism: the intraday "noise-area" breakout on ultra-liquid ETFs. A 30-minute decision
grid enters in the direction of a breakout beyond +/-k*sigma_m where sigma_m is the mean
absolute close-from-open move at that minute over the prior `lookback` sessions; positions
exit back through the band or VWAP and are flattened at the close. Vol-targeted sizing.

This is the only intraday mechanism in the project with robust, OOS evidence
(book_decomp intraday residual alpha t~3; QQQ first-breakout OOS Sharpe ~0.97).

Modules:
    signals  - sigma/bounds/decision/strength/sizing primitives (mirror swingtrader.daily.signals)
    engine   - per-day, per-instrument simulation with realistic fills and costs
    metrics  - performance reporting (Sharpe/CAGR/DD/annual $/robustness)
    config   - the strategy configuration dataclass
"""
from .signals import DaybookConfig  # noqa: F401
