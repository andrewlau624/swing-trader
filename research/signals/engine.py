"""Research copy of swingtrader.backtest.run with three extra, default-off hooks.

Production code is left untouched on purpose. This file is validated against the
published baseline before any result from it is believed.

Extra hooks vs the package engine:
  max_corr / corr_window : skip a new entry whose trailing return correlation
                           with an already-held (or same-bar pending) name is
                           above the cap. Mirrors the night-leg duplicate-bet
                           filter (RESULTS.md addendum 11).
  size_fn                : per-symbol position-size multiplier, e.g. inverse-vol.
  target_pct             : fixed take-profit exit.

Everything else is byte-for-byte the package loop.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from swingtrader.config import Config
from swingtrader.metrics import factor_returns, overnight_share, residual_zscore, zscore
from swingtrader.portfolio import Portfolio
from swingtrader import backtest as _bt
from swingtrader.strategy import LONG, SHORT, Signal, apply_control, entry_signal, exit_on_reversion


def run2(bars, cfg, cohort_name, allow_short=False, stop_pct=None, control=None,
         regime_filter=False, cash_symbol=None, exit_mode="reversion",
         trail_pct=None, trail_atr=None, trail_after_pct=0.0, time_stop_days=None,
         select_mode="reversion", z_entry_override=None, min_overnight_share=None,
         residual=False, overnight_window=5, seed=7, verbose=False,
         max_corr=None, corr_window=20, size_fn=None, target_pct=None,
         z_fn=None):
    cohort = cfg.cohort(cohort_name)
    sel, strat, pcfg = cfg.selection, cfg.strategy, cfg.portfolio
    tstop = strat.time_stop_days if time_stop_days is None else time_stop_days
    rng = np.random.default_rng(seed)

    if "SPY" in bars and len(bars["SPY"]):
        dates = pd.DatetimeIndex(sorted(bars["SPY"].index))
    else:
        dates = pd.DatetimeIndex(sorted({d for f in bars.values() for d in f.index}))
    from swingtrader.backtest import make_folds
    folds = make_folds(dates, cfg)

    pf = Portfolio(pcfg.equity, pcfg.max_positions, pcfg.slippage_bps,
                   pcfg.commission_per_share, position_pct=pcfg.position_pct,
                   max_gross_pct=pcfg.max_gross_pct,
                   cash_yield_annual=pcfg.cash_yield_annual,
                   cash_returns=(bars[cash_symbol]["close"].pct_change()
                                 if cash_symbol and cash_symbol in bars else None))
    factors = factor_returns(bars) if residual else pd.DataFrame()
    regime_ok = None
    if regime_filter and "SPY" in bars:
        spy = bars["SPY"]["close"]
        regime_ok = (spy > spy.rolling(200).mean())

    retcache: dict[str, pd.Series] = {}
    if max_corr is not None:
        for sym, d in bars.items():
            retcache[sym] = np.log(d["close"].astype(float)).diff()

    cand_rows, active = [], []
    zcache: dict[str, pd.Series] = {}
    p_entry: dict[str, float] = {}
    atrcache: dict[str, pd.Series] = {}
    pending_entries: dict[str, int] = {}
    pending_size: dict[str, float] = {}
    pending_exits: dict[str, str] = {}

    for fold in folds:
        form = {}
        for sym, d in bars.items():
            w = d.loc[(d.index >= fold.form_start) & (d.index <= fold.form_end)]
            if len(w) >= cfg.walkforward.formation_days * 0.8:
                form[sym] = w
        picked = _bt.scan_window(form, cohort, sel, mode=select_mode)
        fold.candidates = list(picked.index)
        active = list(dict.fromkeys(fold.candidates))
        if not picked.empty:
            p = picked.copy()
            p["fold"] = fold.index
            p["trade_start"] = fold.trade_start
            cand_rows.append(p)

        zcache, atrcache = {}, {}
        for sym in list(dict.fromkeys(list(active) + sorted(pf.positions))):
            if sym not in bars:
                continue
            d = bars[sym]
            hist = d.loc[d.index <= fold.trade_end, "close"]
            if z_fn is not None:
                zcache[sym] = z_fn(d.loc[d.index <= fold.trade_end], strat.z_window, fold.form_end)
            elif residual:
                z = residual_zscore(hist, factors, strat.z_window, fold.form_end)
                zcache[sym] = z if z.notna().any() else zscore(hist, strat.z_window)
            else:
                zcache[sym] = zscore(hist, strat.z_window)
            if trail_atr:
                dd = d.loc[d.index <= fold.trade_end]
                tr = pd.concat([dd["high"] - dd["low"],
                                (dd["high"] - dd["close"].shift()).abs(),
                                (dd["low"] - dd["close"].shift()).abs()], axis=1).max(axis=1)
                atrcache[sym] = tr.rolling(14).mean()
            zf = zcache[sym].loc[(zcache[sym].index >= fold.form_start)
                                 & (zcache[sym].index <= fold.form_end)].dropna()
            p_entry[sym] = float((zf <= strat.z_entry).mean()) if len(zf) else 0.0

        tdates = dates[(dates >= fold.trade_start) & (dates <= fold.trade_end)]

        def corr_ok(sym, t):
            if max_corr is None or sym not in retcache:
                return True
            held = list(pf.positions) + list(pending_entries)
            held = [h for h in held if h != sym and h in retcache]
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

        for t in tdates:
            marks: dict[str, float] = {}

            for sym, reason in list(pending_exits.items()):
                if sym in pf.positions and sym in bars and t in bars[sym].index:
                    pf.close(sym, float(bars[sym].loc[t, "open"]), t, reason, fold.index)
            pending_exits.clear()

            eq_now = pf.equity({s: float(bars[s].loc[t, "open"])
                                for s in pf.positions if t in bars[s].index})
            for sym, side in list(pending_entries.items()):
                if sym in bars and t in bars[sym].index and pf.can_open(sym):
                    mult = pending_size.get(sym, 1.0)
                    if mult is None or not np.isfinite(mult) or mult <= 0:
                        continue
                    base = pf.position_pct
                    pf.position_pct = base * mult
                    pf.open(sym, side, float(bars[sym].loc[t, "open"]), t, eq_now, stop_pct)
                    pf.position_pct = base
            pending_entries.clear()
            pending_size.clear()

            for sym, pos in list(pf.positions.items()):
                if sym not in bars or t not in bars[sym].index:
                    continue
                bar = bars[sym].loc[t]
                o, hi, lo, c = (float(bar["open"]), float(bar["high"]),
                                float(bar["low"]), float(bar["close"]))
                marks[sym] = c
                pos.mfe = max(pos.mfe, pos.pct(hi if pos.side > 0 else lo))
                pos.mae = min(pos.mae, pos.pct(lo if pos.side > 0 else hi))
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
                            tl = pos.peak - give if pos.side > 0 else pos.peak + give
                            pos.stop_px = (max(pos.stop_px or -1e18, tl) if pos.side > 0
                                           else min(pos.stop_px or 1e18, tl))

                if target_pct is not None:
                    tgt = (pos.entry_px * (1 + target_pct / 100.0) if pos.side > 0
                           else pos.entry_px * (1 - target_pct / 100.0))
                    hit = hi >= tgt if pos.side > 0 else lo <= tgt
                    if hit:
                        px = max(o, tgt) if pos.side > 0 else min(o, tgt)
                        pf.close(sym, px, t, "target", fold.index)
                        continue

                if pos.stop_px is not None:
                    hit = lo <= pos.stop_px if pos.side > 0 else hi >= pos.stop_px
                    if hit:
                        px = min(o, pos.stop_px) if pos.side > 0 else max(o, pos.stop_px)
                        reason = ("trail" if exit_mode in ("trail", "hybrid")
                                  and pos.peak > pos.entry_px else "stop")
                        pf.close(sym, px, t, reason, fold.index)
                        continue
                pos.bars_held += 1

            for sym, pos in pf.positions.items():
                if tstop and pos.bars_held >= tstop:
                    pending_exits[sym] = "time_stop"
                    continue
                if exit_mode == "trail":
                    continue
                if exit_mode == "hybrid" and pos.pct(pos.peak) >= trail_after_pct:
                    continue
                z = zcache.get(sym)
                if z is None or t not in z.index:
                    continue
                if exit_on_reversion(float(z.loc[t]), pos.side, strat):
                    pending_exits[sym] = "reversion"

            if regime_ok is not None and t in regime_ok.index and not bool(regime_ok.loc[t]):
                pf.accrue_cash(t)
                for sym in pf.positions:
                    if sym in bars and t in bars[sym].index and sym not in marks:
                        marks[sym] = float(bars[sym].loc[t, "close"])
                pf.mark(t, marks)
                continue

            for sym in active:
                if sym in pf.positions or sym in pending_exits:
                    continue
                z = zcache.get(sym)
                if z is None or t not in z.index:
                    continue
                zt = float(z.loc[t])
                if not np.isfinite(zt):
                    continue
                ze = strat.z_entry if z_entry_override is None else z_entry_override
                if min_overnight_share is not None:
                    hist = bars[sym].loc[bars[sym].index <= t]
                    if len(hist) < overnight_window + 2:
                        continue
                    osh = overnight_share(hist, overnight_window)
                    if not np.isfinite(osh) or osh < min_overnight_share:
                        continue
                if control == "shuffle":
                    sig = (Signal(LONG, zt) if rng.random() < p_entry.get(sym, 0.0) else None)
                elif select_mode == "momentum":
                    raw = Signal(LONG, zt) if zt <= ze else None
                    sig = apply_control(raw, control, rng)
                else:
                    sig = apply_control(entry_signal(zt, strat, allow_short), control, rng)
                if sig is not None and len(pf.positions) + len(pending_entries) < pcfg.max_positions:
                    if not corr_ok(sym, t):
                        continue
                    pending_entries[sym] = sig.side
                    pending_size[sym] = (size_fn(sym, bars, t) if size_fn is not None else 1.0)

            pf.accrue_cash(t)
            for sym in pf.positions:
                if sym in bars and t in bars[sym].index and sym not in marks:
                    marks[sym] = float(bars[sym].loc[t, "close"])
            pf.mark(t, marks)

    last = dates[-1]
    for sym in list(pf.positions):
        d = bars[sym]
        px = float(d.loc[d.index <= last, "close"].iloc[-1])
        pf.close(sym, px, last, "end_of_test", -1)

    from swingtrader.backtest import Result
    cands = pd.concat(cand_rows) if cand_rows else pd.DataFrame()
    return Result(trades=pf.trades, equity=pf.equity_series(), folds=folds,
                  candidates=cands, rejected_no_slot=pf.rejected_no_slot,
                  config={"cohort": cohort_name, "max_corr": max_corr,
                          "target_pct": target_pct, "size_fn": size_fn is not None})
