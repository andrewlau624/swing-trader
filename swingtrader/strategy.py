"""Entry/exit signals, plus the falsification controls.

All signal functions take the history available *up to and including the
decision bar* and return a decision acted on at the NEXT bar's open. Nothing
here may read the bar it trades into.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import StrategyCfg

LONG, SHORT = 1, -1


@dataclass
class Signal:
    side: int          # LONG or SHORT
    z: float


def entry_signal(z_now: float, cfg: StrategyCfg, allow_short: bool) -> Signal | None:
    """Long when price is stretched below its mean; mirror for short."""
    if not np.isfinite(z_now):
        return None
    if z_now <= cfg.z_entry:
        return Signal(LONG, z_now)
    if allow_short and z_now >= -cfg.z_entry:
        return Signal(SHORT, z_now)
    return None


def exit_on_reversion(z_now: float, side: int, cfg: StrategyCfg) -> bool:
    """Exit when price has reverted to its mean."""
    if not np.isfinite(z_now):
        return False
    return z_now >= cfg.z_exit if side == LONG else z_now <= -cfg.z_exit


def apply_control(sig: Signal | None, control: str | None, rng) -> Signal | None:
    """Falsification controls, ported in spirit from llm-trader's scan.py.

    'flip'   - invert every signal. Should lose money. If it profits, the
               engine has a sign error or a lookahead leak.
    'random' - keep the signal rate but randomise direction. Weak as a test:
               a short entered at z = -2 already satisfies its exit (z <= 0)
               and so closes on the very next bar, holding 1.7 bars against
               the long leg's 12.5. Its short half barely participates.

    'shuffle' - handled in backtest.run, not here. Keeps direction long and
               the per-symbol entry RATE identical, but fires on random days
               instead of on z < -2. This is the control that matters: it
               separates "the scanner picks good stocks" from "the dip-buying
               rule has timing edge". If shuffle matches the strategy, the
               selection is doing all the work and the entry rule is decoration.

    A control run that makes money means stop and debug the simulator; it does
    not mean a second strategy was discovered.
    """
    if sig is None or not control:
        return sig
    if control == "flip":
        return Signal(-sig.side, sig.z)
    if control == "random":
        return Signal(LONG if rng.random() < 0.5 else SHORT, sig.z)
    raise ValueError(f"unknown control {control!r}")
