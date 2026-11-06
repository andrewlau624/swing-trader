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

import datetime as dt
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


def _read_assets_cache(path) -> dict | None:
    try:
        d = json.loads(path.read_text())
    except Exception:
        return None
    return d if d and d.get("symbols") else None


def _cache_fresh(d: dict, max_age_days: float) -> bool:
    fetched = d.get("fetched_at")
    if not fetched:
        return False                      # legacy cache: refresh once, then it is dated
    try:
        age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(fetched)
        return age.days < max_age_days
    except Exception:
        return False


def all_assets(use_cache: bool = True, max_age_days: float = 7) -> UniverseInfo:
    """Every US equity Alpaca knows about, live or delisted.

    The cache is dated and expires: new listings and delistings must enter the
    universe on their own. An undated (legacy) cache is refreshed once and then
    carries a `fetched_at`. If the refresh fails (offline, no keys) a stale
    universe is used rather than crashing.
    """
    path = CACHE / "assets.json"
    cached = _read_assets_cache(path) if (use_cache and path.exists()) else None
    # A cache with no active names is a failed fetch (2026-10-23: alpaca-py rejected the new
    # TXSE exchange code and the night leg scanned ~40 names for two weeks); never trust it.
    if cached is not None and cached.get("n_active", 0) > 0 and _cache_fresh(cached, max_age_days):
        return UniverseInfo(cached["symbols"], cached["n_active"], cached["n_inactive"])
    try:
        info = _fetch_assets()
    except Exception:
        if cached is not None:
            return UniverseInfo(cached["symbols"], cached["n_active"], cached["n_inactive"])
        raise
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "symbols": info.symbols, "n_active": info.n_active, "n_inactive": info.n_inactive,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }))
    return info


def _fetch_assets() -> UniverseInfo:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import AssetClass, AssetStatus
    from alpaca.trading.requests import GetAssetsRequest

    k, s = require_alpaca_keys()
    # raw_data: plain dicts, so a new exchange code (TXSE) cannot fail validation of the whole list
    client = TradingClient(k, s, paper=True, raw_data=True)

    def pull(status):
        try:
            return client.get_all_assets(
                GetAssetsRequest(asset_class=AssetClass.US_EQUITY, status=status)
            )
        except Exception as exc:
            print(f"  WARNING: {status} asset query failed: {type(exc).__name__}: {exc}")
            return []

    active = pull(AssetStatus.ACTIVE)
    if not active:
        raise RuntimeError("active asset query returned nothing")
    inactive = pull(AssetStatus.INACTIVE)

    def keep(a):
        return str(a.get("exchange", "")) in MAJOR and valid_symbol(a["symbol"])

    act = sorted({a["symbol"] for a in active if keep(a)})
    ina = sorted({a["symbol"] for a in inactive if keep(a)} - set(act))
    return UniverseInfo(sorted(set(act) | set(ina)), len(act), len(ina))


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
