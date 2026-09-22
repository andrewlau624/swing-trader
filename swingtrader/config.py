"""Config loading: .env for secrets, config.yaml for parameters.

Follows llm-trader's Config.load(path, **overrides) shape, with two changes:
sections are nested rather than one flat 60-field namespace, and unknown keys
warn instead of being silently dropped -- in a backtest a silently-ignored key
means you believe you swept a parameter and in fact did not.
"""
from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Populate os.environ from .env. Real environment wins (setdefault)."""
    p = Path(path) if path else ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def get_env(name: str, default: str | None = None) -> str | None:
    load_dotenv()
    return os.environ.get(name, default)


def alpaca_keys() -> tuple[str | None, str | None]:
    return get_env("ALPACA_API_KEY"), get_env("ALPACA_SECRET_KEY")


def require_alpaca_keys() -> tuple[str, str]:
    k, s = alpaca_keys()
    if not (k and s):
        raise RuntimeError(
            "ALPACA_API_KEY / ALPACA_SECRET_KEY missing - add paper keys to .env"
        )
    return k, s


@dataclass
class DataCfg:
    start: str = "2021-01-01"
    end: str = "2026-09-18"
    feed: str = "iex"
    adjustment: str = "all"


@dataclass
class WalkForwardCfg:
    formation_days: int = 126
    trade_days: int = 42
    step_days: int = 42


@dataclass
class SelectionCfg:
    halflife_min: float = 3.0
    halflife_max: float = 15.0
    hurst_max: float = 0.5
    max_abs_drift_t: float = 2.5
    min_amplitude_pct: float = 6.0
    max_efficiency_ratio: float = 0.25
    top_n: int = 8


@dataclass
class CohortCfg:
    price_min: float = 5.0
    price_max: float = 50.0
    min_iex_dollar_vol: float = 2_000_000
    min_annual_vol: float = 0.0


@dataclass
class StrategyCfg:
    z_window: int = 20
    z_entry: float = -2.0
    z_exit: float = 0.0
    time_stop_days: int = 20
    stop_pct: float | None = None
    min_overnight_share: float | None = None
    overnight_window: int = 5


@dataclass
class PortfolioCfg:
    equity: float = 100_000.0
    max_positions: int = 8
    slippage_bps: float = 20.0
    commission_per_share: float = 0.0
    position_pct: float | None = None    # None -> 1/max_positions
    max_gross_pct: float = 100.0         # cap on total exposure
    cash_yield_annual: float = 0.0       # idle cash parked in T-bills


@dataclass
class Config:
    data: DataCfg = field(default_factory=DataCfg)
    walkforward: WalkForwardCfg = field(default_factory=WalkForwardCfg)
    selection: SelectionCfg = field(default_factory=SelectionCfg)
    cohorts: dict[str, CohortCfg] = field(default_factory=dict)
    strategy: StrategyCfg = field(default_factory=StrategyCfg)
    portfolio: PortfolioCfg = field(default_factory=PortfolioCfg)

    @classmethod
    def load(cls, path: Path | None = None, **overrides: Any) -> "Config":
        load_dotenv()
        p = Path(path) if path else ROOT / "config.yaml"
        raw: dict[str, Any] = {}
        if p.exists():
            raw = yaml.safe_load(p.read_text()) or {}

        known = {f.name for f in fields(cls)}
        for k in raw:
            if k not in known:
                warnings.warn(f"config.yaml: unknown section {k!r} ignored", stacklevel=2)

        def build(dc, d):
            names = {f.name for f in fields(dc)}
            for k in d:
                if k not in names:
                    warnings.warn(
                        f"config.yaml: unknown key {k!r} in {dc.__name__} ignored",
                        stacklevel=2,
                    )
            return dc(**{k: v for k, v in d.items() if k in names})

        cfg = cls(
            data=build(DataCfg, raw.get("data", {})),
            walkforward=build(WalkForwardCfg, raw.get("walkforward", {})),
            selection=build(SelectionCfg, raw.get("selection", {})),
            cohorts={
                name: build(CohortCfg, c) for name, c in (raw.get("cohorts") or {}).items()
            },
            strategy=build(StrategyCfg, raw.get("strategy", {})),
            portfolio=build(PortfolioCfg, raw.get("portfolio", {})),
        )

        # dotted overrides from argparse: strategy__z_entry=-2.5
        for key, val in overrides.items():
            if val is None:
                continue
            section, _, attr = key.partition("__")
            if not attr or not hasattr(cfg, section):
                raise KeyError(f"unknown override {key!r}")
            sec = getattr(cfg, section)
            if not hasattr(sec, attr):
                raise KeyError(f"unknown override {key!r}")
            setattr(sec, attr, val)
        return cfg

    def cohort(self, name: str) -> CohortCfg:
        if name not in self.cohorts:
            raise KeyError(f"unknown cohort {name!r}; have {sorted(self.cohorts)}")
        return self.cohorts[name]
