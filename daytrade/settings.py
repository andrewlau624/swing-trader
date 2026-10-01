"""Paths and defaults for the lab. Everything lives under its own directories:
data/daytrade (recordings), state/daytrade (HALT, journal, token copy), logs/daytrade."""
from __future__ import annotations

from dataclasses import dataclass

from swingtrader.config import ROOT, get_env

DATA = ROOT / "data" / "daytrade"
STATE = ROOT / "state" / "daytrade"
LOGS = ROOT / "logs" / "daytrade"
HALT = STATE / "HALT"
LIVE_APPROVAL = STATE / "LIVE_APPROVED"

ET = "America/New_York"
CORE = ("QQQ", "SPY", "TQQQ", "IWM", "SMH")
GAPPER_CAP = 10                 # gappers added to the recorder's watchlist each morning
LIVE_CAPITAL_MAX = 500.0        # the first real-money test is at most $500 (README, section 8)
CASH_ONLY_BELOW = 2000.0        # under $2k a Schwab account is cash-only (no margin, no intraday BP)


@dataclass
class Limits:
    """Hard limits, enforced by the engine (daytrade/risk.py), never by a strategy."""
    daily_loss_pct: float = 0.02         # flatten and stop for the day at -2% of start-of-day equity
    risk_per_trade_pct: float = 0.005    # size so that the stop loses at most 0.5% of equity
    max_position_pct: float = 1.0        # one position's notional <= 1.0 x equity
    max_positions: int = 3
    entry_cutoff_min: int = 15           # no new entries in the last 15 minutes (15:45 on a full day)
    flat_min: int = 5                    # flat by close - 5 minutes (15:55; 12:55 on a half day)
    intraday_mult: float = 4.0           # margin >= $2k: Schwab intraday buying power, up to 4x (add. 40)


def env(name: str, default: str | None = None) -> str | None:
    return get_env(name, default)
