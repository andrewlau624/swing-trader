"""Walk-forward backtest driver.

The structure that matters: every fold measures range behaviour on a FORMATION
window and trades only in a strictly later, disjoint TRADE window.

    fold k:   [ formation 126d ][ trade 42d ]
    fold k+1:          [ formation 126d ][ trade 42d ]

Without that split you select stocks *because* they ranged and then congratulate
yourself for trading the range, which produces a beautiful and entirely
fictional equity curve. Everything else here is bookkeeping by comparison.

Within the trade window the loop is two-phase, after llm-trader's scan.py:
decide using bars strictly at or before day t, then fill at day t+1's OPEN.
Decisions never touch the bar they trade into.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import Config
from .metrics import factor_returns, overnight_share, residual_zscore, zscore
from .portfolio import Portfolio, Trade
from .scan import scan_window
from .strategy import (LONG, SHORT, Signal, apply_control, entry_signal,
                       exit_on_reversion)


# A held name whose bars simply stop has been delisted (or its data has). The
# last print is not an exit: a bankruptcy delisting trades on at a fraction of
# it, and without this rule the position also never closes, because every exit
# needs a bar. Bars cannot tell a failure from a cash takeover, so book the
# average performance-delisting return (Shumway 1997: about -30%). On the
# 2021-26 run no trade hits this; it is a guard, not a result.
DELIST_RET = -0.30


class LookaheadError(AssertionError):
    """Raised when a decision would read a bar at or after the bar it trades."""


@dataclass
class Fold:
    index: int
    form_start: pd.Timestamp
    form_end: pd.Timestamp
    trade_start: pd.Timestamp
    trade_end: pd.Timestamp
    candidates: list[str] = field(default_factory=list)


@dataclass
class Result:
    trades: list[Trade]
    equity: pd.Series
    folds: list[Fold]
    candidates: pd.DataFrame
    rejected_no_slot: int
    config: dict


def make_folds(dates: pd.DatetimeIndex, cfg: Config) -> list[Fold]:
    w = cfg.walkforward
    # step < trade makes consecutive trade windows overlap, and the loop then
    # walks the same dates twice: positions are marked and traded twice and the
    # curve compounds on itself. step=21/trade=42 "returned" 91% CAGR this way.
    if w.step_days < w.trade_days:
        raise ValueError(f"step_days ({w.step_days}) < trade_days ({w.trade_days}): "
                         "trade windows would overlap and double-count days")
    out, i, k = [], 0, 0
    while i + w.formation_days + w.trade_days <= len(dates):
        fs, fe = dates[i], dates[i + w.formation_days - 1]
        ts = dates[i + w.formation_days]
        te = dates[min(i + w.formation_days + w.trade_days - 1, len(dates) - 1)]
        out.append(Fold(k, fs, fe, ts, te))
        i += w.step_days
        k += 1
    return out


def run(
    bars: dict[str, pd.DataFrame],
    cfg: Config,
    cohort_name: str,
    allow_short: bool = False,
    stop_pct: float | None = None,
    control: str | None = None,
    regime_filter: bool = False,
    cash_symbol: str | None = None,
    exit_mode: str = "reversion",     # reversion | trail | hybrid
    trail_pct: float | None = None,   # give-back from peak, in percent
    trail_atr: float | None = None,   # give-back from peak, in ATR multiples
    trail_after_pct: float = 0.0,     # hybrid: start trailing once up this much
    time_stop_days: int | None = None,
    select_mode: str = "reversion",
    z_entry_override: float | None = None,
    min_overnight_share: float | None = None,
    residual: bool = False,
    overnight_window: int = 5,
    max_corr: float | None = None,
    corr_window: int = 20,
    seed: int = 7,
    verbose: bool = True,
) -> Result:
    cohort = cfg.cohort(cohort_name)
    sel, strat, pcfg = cfg.selection, cfg.strategy, cfg.portfolio
    tstop = strat.time_stop_days if time_stop_days is None else time_stop_days
    if exit_mode not in ("reversion", "trail", "hybrid"):
        raise ValueError(f"unknown exit_mode {exit_mode!r}")
    if max_corr is None:
        max_corr = strat.max_corr
    if corr_window is None:
        corr_window = strat.corr_window
    rng = np.random.default_rng(seed)

    # master calendar: SPY's own session index, not the union of every symbol's
    # bar dates. A union shifts the fold boundaries when the universe changes
    # (and can pick up a stray bad bar), which makes results incomparable across
    # runs. SPY is the real NYSE session set; fall back to the union for tests.
    if "SPY" in bars and len(bars["SPY"]):
        dates = pd.DatetimeIndex(sorted(bars["SPY"].index))
    else:
        dates = pd.DatetimeIndex(sorted({d for f in bars.values() for d in f.index}))
    folds = make_folds(dates, cfg)
    if not folds:
        raise ValueError("not enough history for a single fold")

    pf = Portfolio(pcfg.equity, pcfg.max_positions, pcfg.slippage_bps,
                   pcfg.commission_per_share,
                   position_pct=pcfg.position_pct,
                   max_gross_pct=pcfg.max_gross_pct,
                   cash_yield_annual=pcfg.cash_yield_annual,
                   cash_returns=(bars[cash_symbol]["close"].pct_change()
                                 if cash_symbol and cash_symbol in bars else None))

    # market regime: block new entries when SPY is below its own 200d average.
    # Computed causally (rolling mean of past closes) and only ever read for
    # dates at or before the decision bar.
    factors = factor_returns(bars) if residual else pd.DataFrame()
    if residual and factors.empty:
        raise ValueError("residual=True needs SPY, IWM, IWB, IWD and IWF in bars")

    regime_ok = None
    if regime_filter and "SPY" in bars:
        spy = bars["SPY"]["close"]
        regime_ok = (spy > spy.rolling(200).mean())

    # trailing log-returns, built lazily only when the duplicate-bet filter is on
    retcache: dict[str, pd.Series] = {}
    if max_corr is not None:
        retcache = {s: np.log(d["close"].astype(float)).diff()
                    for s, d in bars.items()}
    cand_rows: list[pd.DataFrame] = []
    active: set[str] = set()
    zcache: dict[str, pd.Series] = {}
    p_entry: dict[str, float] = {}   # per-symbol entry rate, for the shuffle control
    atrcache: dict[str, pd.Series] = {}
    pending_entries: dict[str, int] = {}
    pending_exits: dict[str, str] = {}

    def corr_ok(sym: str, t) -> bool:
        """False if `sym` is a duplicate bet of a held/pending name.

        Uses returns only through the decision bar t (the fill is at t+1), and
        keeps the best-ranked candidate: `active` is walked best-first, so the
        first of a correlated cluster is the one retained.
        """
        if max_corr is None or sym not in retcache:
            return True
        held = [h for h in list(pf.positions) + list(pending_entries)
                if h != sym and h in retcache]
        if not held:
            return True
        rc = retcache[sym].loc[:t].iloc[-corr_window:].dropna()
        for h in held:
            rh = retcache[h].loc[:t].iloc[-corr_window:].dropna()
            j = rc.index.intersection(rh.index)
            if len(j) < 10:
                continue
            a, c = rc.loc[j].values, rh.loc[j].values
            if a.std() > 0 and c.std() > 0:
                rho = float(np.corrcoef(a, c)[0, 1])
                if np.isfinite(rho) and rho > max_corr:
                    return False
        return True

    for fold in folds:
        # ---- selection: formation window ONLY -------------------------
        form = {}
        for sym, d in bars.items():
            w = d.loc[(d.index >= fold.form_start) & (d.index <= fold.form_end)]
            if len(w) >= cfg.walkforward.formation_days * 0.8:
                form[sym] = w
        picked = scan_window(form, cohort, sel, mode=select_mode)
        fold.candidates = list(picked.index)
        # sorted, not a set: set iteration order varies with PYTHONHASHSEED,
        # which changes WHICH symbols win the last free slots and made the same
        # config return 18.1%, 18.3% and 20.6% CAGR across three processes.
        active = list(dict.fromkeys(fold.candidates))
        if not picked.empty:
            p = picked.copy()
            p["fold"] = fold.index
            p["trade_start"] = fold.trade_start
            cand_rows.append(p)

        # z-series for every candidate AND every symbol still held. Held
        # symbols matter: once a name drops out of the candidate set its
        # position must still be managed, or it becomes immortal and rides the
        # market to the end of the test. That bug made 8 never-closed positions
        # contribute 99% of profit in an earlier run -- buy-and-hold wearing a
        # strategy's clothes.
        zcache, atrcache = {}, {}
        for sym in list(dict.fromkeys(list(active) + sorted(pf.positions))):
            if sym not in bars:
                continue
            d = bars[sym]
            hist = d.loc[d.index <= fold.trade_end, "close"]
            if residual:
                # betas fitted on formation bars only, then held fixed
                z = residual_zscore(hist, factors, strat.z_window, fold.form_end)
                zcache[sym] = z if z.notna().any() else zscore(hist, strat.z_window)
            else:
                zcache[sym] = zscore(hist, strat.z_window)
            # entry rate measured on FORMATION bars only, so the shuffle
            # control gets the same trade frequency without seeing the future
            if trail_atr:
                dd = d.loc[d.index <= fold.trade_end]
                tr = pd.concat([
                    dd["high"] - dd["low"],
                    (dd["high"] - dd["close"].shift()).abs(),
                    (dd["low"] - dd["close"].shift()).abs()], axis=1).max(axis=1)
                atrcache[sym] = tr.rolling(14).mean()
            zf = zcache[sym].loc[
                (zcache[sym].index >= fold.form_start) & (zcache[sym].index <= fold.form_end)
            ].dropna()
            p_entry[sym] = float((zf <= strat.z_entry).mean()) if len(zf) else 0.0

        tdates = dates[(dates >= fold.trade_start) & (dates <= fold.trade_end)]

        if verbose:
            print(f"  fold {fold.index:2d} form {fold.form_start.date()}..{fold.form_end.date()} "
                  f"trade {fold.trade_start.date()}..{fold.trade_end.date()} "
                  f"picked {len(fold.candidates)}")

        # ---- trading window -------------------------------------------
        for t in tdates:
            marks: dict[str, float] = {}

            # PHASE 0: positions whose data ended before today were delisted
            for sym in list(pf.positions):
                d = bars[sym]
                if len(d) and d.index[-1] < t:
                    px = float(d["close"].iloc[-1]) * (1.0 + DELIST_RET)
                    pf.close(sym, px, t, "delisted", fold.index)
                    pending_exits.pop(sym, None)

            # PHASE 1: execute yesterday's decisions at today's OPEN
            for sym, reason in list(pending_exits.items()):
                if sym in pf.positions and sym in bars and t in bars[sym].index:
                    pf.close(sym, float(bars[sym].loc[t, "open"]), t, reason, fold.index)
            pending_exits.clear()

            eq_now = pf.equity({s: float(bars[s].loc[t, "open"])
                                for s in pf.positions if t in bars[s].index})
            for sym, side in list(pending_entries.items()):
                if sym in bars and t in bars[sym].index and pf.can_open(sym):
                    pf.open(sym, side, float(bars[sym].loc[t, "open"]), t, eq_now, stop_pct)
            pending_entries.clear()

            # PHASE 2: intraday management, INCLUDING the bar we just filled on.
            # Skipping the fill bar would hand every position a free day in
            # which its stop cannot trigger.
            for sym, pos in list(pf.positions.items()):
                if sym not in bars or t not in bars[sym].index:
                    continue
                bar = bars[sym].loc[t]
                o, hi, lo, c = (float(bar["open"]), float(bar["high"]),
                                float(bar["low"]), float(bar["close"]))
                marks[sym] = c
                pos.mfe = max(pos.mfe, pos.pct(hi if pos.side > 0 else lo))
                pos.mae = min(pos.mae, pos.pct(lo if pos.side > 0 else hi))

                # ratchet the high-water mark, then raise the stop behind it.
                # The stop only ever moves in our favour -- a trailing stop
                # that can loosen is just a wider fixed stop with extra steps.
                pos.peak = max(pos.peak, hi) if pos.side > 0 else min(pos.peak or lo, lo)
                if exit_mode in ("trail", "hybrid"):
                    gain = pos.pct(pos.peak)
                    if exit_mode == "trail" or gain >= trail_after_pct:
                        give = None
                        if trail_pct is not None:
                            give = pos.peak * trail_pct / 100.0
                        elif trail_atr is not None:
                            a = atrcache.get(sym)
                            if a is not None and t in a.index and np.isfinite(a.loc[t]):
                                give = float(a.loc[t]) * trail_atr
                        if give is not None:
                            trail_level = (pos.peak - give if pos.side > 0
                                           else pos.peak + give)
                            pos.stop_px = (max(pos.stop_px or -1e18, trail_level)
                                           if pos.side > 0
                                           else min(pos.stop_px or 1e18, trail_level))

                if pos.stop_px is not None:
                    hit = lo <= pos.stop_px if pos.side > 0 else hi >= pos.stop_px
                    if hit:
                        # a gap through the stop fills at the open, not the stop
                        px = min(o, pos.stop_px) if pos.side > 0 else max(o, pos.stop_px)
                        reason = ("trail" if exit_mode in ("trail", "hybrid")
                                  and pos.peak > pos.entry_px else "stop")
                        pf.close(sym, px, t, reason, fold.index)
                        continue
                pos.bars_held += 1

            # PHASE 3: decide for TOMORROW using bars at or before today
            for sym, pos in pf.positions.items():
                # time stop is unconditional: it must not depend on a z-score
                # being available, or a position can outlive its own exit rule
                if tstop and pos.bars_held >= tstop:
                    pending_exits[sym] = "time_stop"
                    continue
                if exit_mode == "trail":
                    continue          # the trailing stop is the only exit
                if exit_mode == "hybrid" and pos.pct(pos.peak) >= trail_after_pct:
                    continue          # it ran; hand it to the trailing stop
                z = zcache.get(sym)
                if z is None or t not in z.index:
                    continue
                if exit_on_reversion(float(z.loc[t]), pos.side, strat):
                    pending_exits[sym] = "reversion"

            if regime_ok is not None and t in regime_ok.index and not bool(regime_ok.loc[t]):
                for sym in pf.positions:
                    pass  # existing positions run their course; only entries stop
                pf.accrue_cash(t)
                for sym in pf.positions:
                    if sym in bars and t in bars[sym].index and sym not in marks:
                        marks[sym] = float(bars[sym].loc[t, "close"])
                pf.mark(t, marks)
                continue

            for sym in active:          # deterministic order, ranked best-first
                if sym in pf.positions or sym in pending_exits:
                    continue
                z = zcache.get(sym)
                if z is None or t not in z.index:
                    continue
                zt = float(z.loc[t])
                if not np.isfinite(zt):
                    continue
                ze = strat.z_entry if z_entry_override is None else z_entry_override
                # quality gate: was this dip made of overnight gaps or of
                # intraday selling? Computed from bars at or before the
                # decision bar only.
                if min_overnight_share is not None:
                    hist = bars[sym].loc[bars[sym].index <= t]
                    if len(hist) < overnight_window + 2:
                        continue
                    osh = overnight_share(hist, overnight_window)
                    if not np.isfinite(osh) or osh < min_overnight_share:
                        continue

                if control == "shuffle":
                    # same stock, same entry rate, random day instead of z < -2
                    sig = (Signal(LONG, zt)
                           if rng.random() < p_entry.get(sym, 0.0) else None)
                elif select_mode == "momentum":
                    # buy a pullback inside an established uptrend.
                    # MUST route through apply_control like every other mode --
                    # an earlier version built the Signal directly and silently
                    # bypassed the falsification controls, so a flip run
                    # returned results identical to the real one and the sleeve
                    # looked validated when nothing had been tested at all.
                    raw = Signal(LONG, zt) if zt <= ze else None
                    sig = apply_control(raw, control, rng)
                else:
                    sig = apply_control(entry_signal(zt, strat, allow_short), control, rng)
                if sig is not None and len(pf.positions) + len(pending_entries) < pcfg.max_positions:
                    if not corr_ok(sym, t):
                        continue
                    pending_entries[sym] = sig.side

            # PHASE 4: accrue on idle cash, then mark to market on today's close
            pf.accrue_cash(t)
            for sym in pf.positions:
                if sym in bars and t in bars[sym].index and sym not in marks:
                    marks[sym] = float(bars[sym].loc[t, "close"])
            pf.mark(t, marks)

    # flush anything still open at the very end of the test
    last = dates[-1]
    for sym in list(pf.positions):
        d = bars[sym]
        px = float(d.loc[d.index <= last, "close"].iloc[-1])
        pf.close(sym, px, last, "end_of_test", -1)

    cands = pd.concat(cand_rows) if cand_rows else pd.DataFrame()
    return Result(
        trades=pf.trades,
        equity=pf.equity_series(),
        folds=folds,
        candidates=cands,
        rejected_no_slot=pf.rejected_no_slot,
        config={
            "cohort": cohort_name, "allow_short": allow_short,
            "stop_pct": stop_pct, "control": control,
            "slippage_bps": pcfg.slippage_bps, "max_positions": pcfg.max_positions,
            "z_entry": strat.z_entry, "z_exit": strat.z_exit,
            "residual": residual, "min_overnight_share": min_overnight_share, "exit_mode": exit_mode, "trail_pct": trail_pct, "trail_atr": trail_atr,
            "max_corr": max_corr, "corr_window": corr_window,
            "trail_after_pct": trail_after_pct, "time_stop_days": tstop,
            "position_pct": pf.position_pct, "max_gross_pct": pcfg.max_gross_pct,
            "cash_yield": cash_symbol or pcfg.cash_yield_annual, "regime_filter": regime_filter,
            "formation_days": cfg.walkforward.formation_days,
            "trade_days": cfg.walkforward.trade_days,
        },
    )
