"""Tradable universe, including delisted names.

Survivorship bias is not a footnote for this strategy, it is the single bias
most likely to manufacture a fake edge. Mean reversion is flattered by it
precisely because the stocks that dipped and never bounced are the ones that
got delisted and vanish from a current-assets query. Screening on today's
survivors would systematically delete this strategy's worst trades.

So the historical universe is ACTIVE + INACTIVE assets unioned together, and
the scan reports what fraction was inactive so the reader can judge how much
of the problem actually got fixed.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import pandas as pd

from .config import CohortCfg, ROOT, require_alpaca_keys
from .metrics import annual_vol, dollar_volume

CACHE = ROOT / "data" / "cache"
MAJOR = {"NASDAQ", "NYSE", "AMEX", "ARCA", "BATS"}

# Plain common stock only: 1-5 letters, optional single-letter share class.
# Excludes warrants (FOO.WS), rights, units, and CVR junk like "750CVR029" --
# one of which will reject an entire 200-symbol bar request if left in.
TICKER_RE = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")


def valid_symbol(sym: str) -> bool:
    return bool(TICKER_RE.match(sym))


@dataclass
class UniverseInfo:
    symbols: list[str]
    n_active: int
    n_inactive: int

    @property
    def inactive_pct(self) -> float:
        tot = self.n_active + self.n_inactive
        return 100.0 * self.n_inactive / tot if tot else 0.0


def all_assets(use_cache: bool = True) -> UniverseInfo:
    """Every US equity Alpaca knows about, live or delisted."""
    path = CACHE / "assets.json"
    if use_cache and path.exists():
        d = json.loads(path.read_text())
        return UniverseInfo(d["symbols"], d["n_active"], d["n_inactive"])

    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import AssetClass, AssetStatus
    from alpaca.trading.requests import GetAssetsRequest

    k, s = require_alpaca_keys()
    client = TradingClient(k, s, paper=True)

    def pull(status):
        try:
            return client.get_all_assets(
                GetAssetsRequest(asset_class=AssetClass.US_EQUITY, status=status)
            )
        except Exception as exc:
            print(f"  WARNING: {status} asset query failed: {type(exc).__name__}: {exc}")
            return []

    active = pull(AssetStatus.ACTIVE)
    inactive = pull(AssetStatus.INACTIVE)

    def keep(a):
        ex = str(getattr(a, "exchange", "")).split(".")[-1]
        return ex in MAJOR and valid_symbol(a.symbol)

    act = sorted({a.symbol for a in active if keep(a)})
    ina = sorted({a.symbol for a in inactive if keep(a)} - set(act))
    info = UniverseInfo(sorted(set(act) | set(ina)), len(act), len(ina))

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"symbols": info.symbols, "n_active": info.n_active, "n_inactive": info.n_inactive}
    ))
    return info


def passes_cohort(bars: pd.DataFrame, cohort: CohortCfg) -> bool:
    """Liquidity / price / volatility prefilter, measured on the window given.

    Callers must pass formation-window bars only. Prefiltering on recent data
    and then trading an earlier window would leak the future into selection.
    """
    if bars.empty or len(bars) < 30:
        return False
    px = float(bars["close"].iloc[-1])
    if not (cohort.price_min <= px <= cohort.price_max):
        return False
    if dollar_volume(bars) < cohort.min_iex_dollar_vol:
        return False
    if annual_vol(bars["close"]) < cohort.min_annual_vol:
        return False
    return True
