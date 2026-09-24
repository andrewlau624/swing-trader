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
    # Duplicate-bet filter (RESULTS.md addendum 13). Walk candidates best-ranked
    # first and drop any whose trailing returns correlate above max_corr with an
    # already-held (or same-bar pending) name. Same rule the night leg uses
    # (daily.night_max_corr, addendum 11): eight slots should be eight bets.
    # null = off. Backtest on the uncapped config: 0.7 lifts Sharpe 1.16 -> 1.33
    # and cuts maxDD -15.3% -> -10.3%; a matched random-drop control reaches
    # only 12 risk-matched vs the cap's 28.
    max_corr: float | None = None
    corr_window: int = 20
    # which cohort the live swing executor selects from (backtest scripts use
    # "highvol"; kept configurable so live and backtest cannot silently drift)
    live_cohort: str = "highvol"


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
class DailyCfg:
    """The daily-cadence book (RESULTS.md addendum 6). Runs beside the swing
    book on the same account but owns disjoint symbols and tracks its own
    virtual equity, so the experiment compounds from its own fills only."""
    enabled: bool = True
    # Which accounts run this book. "paper" shares the swing book's paper
    # account with a virtual start_equity; "live" is a dedicated real-money
    # account (ALPACA_LIVE_API_KEY) sized from its actual equity. Both may run
    # side by side: `make daily-live-on` / `make daily-live-off`.
    accounts: list = field(default_factory=lambda: ["paper"])
    live_broker: str = "schwab"      # broker for the "live" account: schwab | alpaca
    # Schwab has no market-on-open order. "primary" directs the night leg's
    # open sells to each stock's listing exchange, so they join its opening
    # auction; "auto" leaves routing to Schwab (a wholesaler fills "at the
    # open", not necessarily at the auction print). A refused route falls back
    # to "auto" for that order and is retried after a few days.
    schwab_open_route: str = "primary"
    # Real-money capital. The live book sizes from the account's FREE equity:
    # equity minus the market value of positions it does not own (your own
    # holdings), so it never borrows against them. live_capital (dollars)
    # optionally caps it further; None = all free equity.
    live_capital: float | None = None
    live_min_capital: float = 500.0  # below this the live book places no new buys
    # 15:40 scan prices: auto = Schwab real-time consolidated quotes when a
    # login exists (both books, so paper vs live differ only in execution),
    # else Alpaca IEX. alpaca | schwab force one.
    quote_source: str = "auto"
    # NOTE: the real-money switch itself lives in .env (DAILY_LIVE=on), not
    # here -- `make pull` does `git reset --hard`, which would silently revert
    # a switch stored in this tracked file. See resolved_accounts().
    # auto: the intraday leg places orders once equity >= daytrade_min_equity.
    #       FINRA retired the pattern-day-trader rule (Rule 4210 amendments,
    #       effective 2026-06-04; Alpaca 06-04, Schwab 06-08): no day-trade
    #       count, no $25k floor. What remains is Reg T's $2,000 margin minimum.
    # off:  intraday leg stays shadow forever
    daytrade_mode: str = "auto"
    start_equity: float = 3_000.0
    # Intraday (QQQ) leg is SHADOW below this. $2,000 = Reg T margin minimum.
    daytrade_min_equity: float = 2_000.0
    # leg 1: IBS on tech ETFs. Signal on the last complete bar, enter at the
    # next open, re-evaluated every morning.
    ibs_symbols: list = field(default_factory=lambda: [
        "SPY", "QQQ", "IWM", "DIA", "MDY", "XLK", "XLF", "XLE", "XLV", "XLI",
        "XLY", "XLP", "XLU", "XLB", "SMH", "XBI", "EEM", "EFA"])
    ibs_top_k: int | None = 3        # trade the top-k by 12-1 momentum (monthly); None = all
    ibs_max: float = 0.2
    ibs_cash_symbol: str | None = "SGOV"   # idle IBS money sits here; None = cash
    ibs_weight: float = 0.5          # fraction of book equity for this leg
    # leg 2: overnight loser bounce. Scan ~15:40 ET, buy at the close auction,
    # sell at the next open auction.
    night_weight: float = 0.5
    # Overnight leverage: BOTH overnight legs move to this weight once
    # signals.lever_ok passes on live fills (50 night exits at <= 10bp/side,
    # no kill, drawdown within 10%), and back when it stops passing.
    # 0.65 + 0.65 = 1.3x overnight gross. None = never lever.
    lever_weight: float | None = 0.65
    night_max_name_pct: float = 0.10 # of the leg, per name
    night_day_ret_max: float = -0.08
    night_ibs_max: float = 0.10
    night_price_min: float = 5.0
    night_price_max: float = 2_000.0
    night_adv_min: float = 10_000_000.0   # SIP 20-day dollar volume
    night_vol_min: float = 0.60      # 20-day annualised vol floor
    night_crowd_n: int = 30          # more raw signals than this = market-wide selloff: scale down
    night_max_corr: float = 0.9      # one position per underlying (e.g. seven 2x SpaceX ETFs = one bet)
    # night exposure multiplier when held over a weekend/holiday (addendum 18)
    night_weekend_scale: float = 0.5
    # size night names by predicted edge (signals.night_tilt, addendum 16); 0 = equal weight
    night_tilt_k: float = 0.25
    # leg 3: QQQ noise-area intraday momentum (shadow until the gate trips)
    noise_symbol: str = "QQQ"
    # traded instead when another leg (IBS) already holds noise_symbol --
    # Alpaca nets positions per symbol, so two legs cannot share one
    noise_alt_symbol: str = "QQQM"
    # further instruments sharing the intraday budget equally, signal symbol ->
    # stand-in traded when another leg holds it. {} = QQQ alone.
    noise_extra: dict = field(default_factory=dict)
    noise_lookback: int = 14
    noise_target_vol: float = 0.02
    noise_max_lev: float = 3.5       # 4x intraday limit minus the IBS leg

    def resolved_accounts(self) -> list[str]:
        """config accounts, plus "live" when .env says DAILY_LIVE=on."""
        acc = [a for a in self.accounts if a != "live"]
        if (get_env("DAILY_LIVE", "off") or "off").strip().lower() == "on":
            acc.append("live")
        return acc


@dataclass
class Config:
    data: DataCfg = field(default_factory=DataCfg)
    walkforward: WalkForwardCfg = field(default_factory=WalkForwardCfg)
    selection: SelectionCfg = field(default_factory=SelectionCfg)
    cohorts: dict[str, CohortCfg] = field(default_factory=dict)
    strategy: StrategyCfg = field(default_factory=StrategyCfg)
    portfolio: PortfolioCfg = field(default_factory=PortfolioCfg)
    daily: DailyCfg = field(default_factory=DailyCfg)

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
            daily=build(DailyCfg, raw.get("daily", {})),
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
