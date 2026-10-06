"""Per-day simulation of the intraday day book across a basket of instruments.

All decisions occur on the shared 30-minute grid; P&L accrues on the held position between
decision minutes. Costs are charged on every position change (bp x |delta position|).
A portfolio-level daily-loss stop flattens everything for the rest of the day when breached.

No lookahead: sigma uses prior sessions; bounds use the day open and prior close; the
running VWAP and prices used at a decision are those observable at that minute.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .signals import (
    DaybookConfig,
    breakout_strength,
    noise_bounds,
    noise_decide,
    noise_sigma,
    vol_leverage,
)

NMIN = 391  # 09:30 .. 16:00 inclusive


def _prepare(panel: dict, lookback: int = 14, close_min: int = 389) -> dict:
    """Precompute per-instrument sigma[minute] history and running VWAP."""
    out = {}
    for s, d in panel.items():
        A = d["A"]                      # [n, 5, NMIN]
        O, H, L, C, Vol = A[:, 0], A[:, 1], A[:, 2], A[:, 3], A[:, 4]
        n = C.shape[0]
        cm = min(close_min, C.shape[1] - 1)
        # |close_m / open_day - 1| per day, per minute
        with np.errstate(invalid="ignore", divide="ignore"):
            moves = np.abs(C / O[:, [0]] - 1.0)
        # rolling mean of the PREVIOUS `lookback` days (no lookahead)
        sig = np.full((n, NMIN), np.nan)
        for i in range(n):
            lo = max(0, i - lookback)
            if i - lo >= 1:
                sig[i] = np.nanmean(moves[lo:i], axis=0)
        tp = (H + L + C) / 3.0
        cum_pv = np.cumsum(tp * Vol, axis=1)
        cum_v = np.cumsum(Vol, axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            vwap = cum_pv / cum_v
        vwap = np.where(np.isfinite(vwap), vwap, C)
        out[s] = dict(dates=d["dates"], O=O, C=C, sig=sig, vwap=vwap, close_min=cm)
        out[s]["prev_close"] = np.concatenate([[np.nan], C[:-1, cm]])
    return out


def simulate(panel: dict, cfg: DaybookConfig):
    """Return (daily_total, per_instrument_daily, trades) arrays/DataFrames."""
    P = _prepare(panel, cfg.lookback, cfg.close_min)
    syms = list(panel.keys())
    dates = panel[syms[0]]["dates"]
    n = len(dates)

    dec = list(range(cfg.first, cfg.last + 1, cfg.step))
    w = {**cfg.core, **cfg.conviction}

    total = np.zeros(n)
    per = {s: np.zeros(n) for s in syms}
    nfill = {s: 0 for s in syms}

    for i in range(n):
        if not (np.isfinite(P[syms[0]]["prev_close"][i])):
            continue
        # per-instrument static sizing for the day
        lev, ub, lb = {}, {}, {}
        ok = {}
        for s in syms:
            d = P[s]
            cm = d["close_min"]
            closes = d["C"][:i, cm]                # PRIOR days only (no lookahead)
            lv = vol_leverage(closes, cfg.target_vol, cfg.max_lev)
            lev[s] = lv if w.get(s, 0) > 0 else 0.0
            if not np.isfinite(d["O"][i, 0]) or lv <= 0:
                ok[s] = False
                continue
            ok[s] = True
            ub[s], lb[s] = noise_bounds(d["O"][i, 0], d["prev_close"][i], d["sig"][i])
        cur = {s: 0 for s in syms}
        taken = {s: False for s in syms}
        stopped = False
        day_pnl = 0.0
        cost_bps = cfg.cost_bps

        def pos_of(s, m):
            if stopped or cur[s] == 0:
                return 0.0
            return cur[s] * lev[s] * w.get(s, 0.0)

        close_i = P[syms[0]]["close_min"]
        for k, m in enumerate(dec):
            nxt = dec[k + 1] if k + 1 < len(dec) else close_i
            cfill = 0.0
            for s in syms:
                if not ok[s]:
                    continue
                price = P[s]["C"][i, m]
                newd = noise_decide(cur[s], price, ub[s][m], lb[s][m], P[s]["vwap"][i, m])
                # conviction only on the first breakout of the day in the conviction set
                if s in cfg.conviction and not taken[s] and newd != 0 and cfg.conviction_mult != 1.0:
                    _, stg = breakout_strength(price, ub[s][m], lb[s][m], P[s]["sig"][i, m])
                    if stg >= cfg.conviction_strength:
                        taken[s] = True
                if newd != cur[s]:
                    cfill += cost_bps * abs(newd - cur[s]) * 1e-4 * lev[s] * w.get(s, 0.0)
                    nfill[s] += 1
                    cur[s] = newd
            # interval return
            interval = 0.0
            for s in syms:
                if not ok[s]:
                    continue
                r = P[s]["C"][i, nxt] / P[s]["C"][i, m] - 1.0
                mult = lev[s] * w.get(s, 0.0)
                if s in cfg.conviction and taken[s]:
                    mult *= cfg.conviction_mult
                interval += cur[s] * mult * (r if np.isfinite(r) else 0.0)
                per[s][i] += cur[s] * mult * (r if np.isfinite(r) else 0.0)
            step = interval - cfill
            day_pnl += step
            total[i] += step
            if cfg.max_daily_loss > 0 and day_pnl < -cfg.max_daily_loss:
                # flatten everything (pay the exit cost) and stop for the day
                for s in syms:
                    if cur[s] != 0:
                        total[i] += -cost_bps * abs(cur[s]) * 1e-4 * lev[s] * w.get(s, 0.0)
                        per[s][i] += -cost_bps * abs(cur[s]) * 1e-4 * lev[s] * w.get(s, 0.0)
                        cur[s] = 0
                stopped = True
        # flatten at the close (the last interval already ran to NMIN-1; charge exit)
        for s in syms:
            if cur[s] != 0:
                ex = -cost_bps * abs(cur[s]) * 1e-4 * lev[s] * w.get(s, 0.0)
                total[i] += ex
                per[s][i] += ex
                nfill[s] += 1

    cols = pd.DatetimeIndex(dates)
    total_s = pd.Series(total, index=cols, name="total")
    per_df = pd.DataFrame({s: per[s] for s in syms}, index=cols)
    return total_s, per_df, nfill
