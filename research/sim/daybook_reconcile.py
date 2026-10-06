"""Phase 1 reconciliation: daybook engine vs the reference/live noise rule.

Reimplements research/daily-strategies/noise.py VERBATIM (its data dir was moved) and
runs it against swingtrader/daybook/engine.py on identical dates, toggling one
implementation difference at a time so each is attributable.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.daybook_reconcile
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.daybook import DaybookConfig
from swingtrader.daybook.engine import simulate

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "research" / "program" / "daytrade_scan_cache.pkl"


def ref_noise(A391, dates, lookback=14, vm=1.0, step=30, first=30, cost_bps=2.0,
              target=0.02, maxlev=4.0, vwap_basis="close", nmin=390,
              drop_halfdays=False, close_at_1600=False):
    """Verbatim port of research/daily-strategies/noise.py::noise (with toggles)."""
    A = A391
    O = A[:, 0, 0].astype(float)                     # day open (m=0)
    C = A[:, 3, :nmin].astype(float)
    V = A[:, 4, :nmin].astype(float)
    H, L = A[:, 1, :nmin].astype(float), A[:, 2, :nmin].astype(float)
    n = len(dates)
    keep = np.ones(n, dtype=bool)
    if drop_halfdays:
        keep = V[:, 300:].sum(axis=1) > 0
    move = np.abs(C / O[:, None] - 1.0)
    dclose = C[:, -1]
    prevc = np.r_[np.nan, dclose[:-1]]
    dret = pd.Series(dclose).pct_change()
    vol14 = dret.rolling(14).std().shift(1).values
    if vwap_basis == "close":
        pv = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    else:
        tp = (H + L + C) / 3.0
        pv = np.cumsum(tp * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    out = np.zeros(n)
    lastm = 390 if (close_at_1600 and A.shape[2] > 390) else nmin - 1
    AC = A[:, 3] if lastm == 390 else C
    for i in range(lookback + 1, n):
        if not keep[i]:
            continue
        sig = move[i - lookback:i].mean(axis=0) * vm
        ub = np.maximum(O[i], prevc[i]) * (1 + sig)
        lb = np.minimum(O[i], prevc[i]) * (1 - sig)
        lev = min(maxlev, target / vol14[i]) if np.isfinite(vol14[i]) and vol14[i] > 0 else np.nan
        if not np.isfinite(lev):
            continue
        pos = 0; entry = 0.0; pnl = 0.0; trades = 0
        grid = list(range(first, nmin, step))
        for m in grid:
            p = C[i, m]
            if pos == 1 and p < max(ub[m], pv[i, m]):
                pnl += p / entry - 1; pos = 0; trades += 1
            elif pos == -1 and p > min(lb[m], pv[i, m]):
                pnl += 1 - p / entry; pos = 0; trades += 1
            if pos == 0:
                if p > ub[m]:
                    pos = 1; entry = p; trades += 1
                elif p < lb[m]:
                    pos = -1; entry = p; trades += 1
        p = AC[i, lastm]
        if pos == 1:
            pnl += p / entry - 1; trades += 1
        elif pos == -1:
            pnl += 1 - p / entry; trades += 1
        out[i] = lev * (pnl - trades * cost_bps / 1e4)
    return pd.Series(out, index=dates)


def stat(s, lab):
    out = []
    for lo, hi, nm in [("2016", "2020", "16-20"), ("2021", "2026", "21-26"), ("2016", "2026", "full")]:
        x = s[(s.index >= f"{lo}-01-01") & (s.index <= f"{hi}-12-31")].fillna(0)
        if len(x) < 50:
            out.append(f"{nm} n/a"); continue
        yrs = len(x) / 252
        cagr = (1 + x).prod() ** (1 / yrs) - 1
        sh = x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
        t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if x.std() > 0 else 0
        out.append(f"{nm} {cagr*100:6.1f}%/{sh:5.2f} mean{x.mean()*1e4:+6.2f}bp t{t:+5.2f}")
    print(f"{lab:44s} " + " | ".join(out))


def main():
    P = pickle.load(open(CACHE, "rb"))
    d = P["QQQ"]
    A, dates = d["A"], d["dates"]
    print("QQQ days", len(dates), dates.min().date(), "..", dates.max().date())

    # --- reference, verbatim (noise.py defaults: cost 2, maxlev 4, vwap close, nmin 390) ---
    stat(ref_noise(A, dates, cost_bps=2.0, maxlev=4.0, vwap_basis="close", nmin=390),
         "REF verbatim (cost2 maxlev4 vwap-close n390)")
    # --- reference with live config values ---
    stat(ref_noise(A, dates, cost_bps=0.5, maxlev=3.5, vwap_basis="close", nmin=390),
         "REF live-config (cost.5 maxlev3.5)")
    # --- toggle each difference ---
    stat(ref_noise(A, dates, cost_bps=0.5, maxlev=3.5, vwap_basis="typical", nmin=390),
         "REF + vwap=typical(H+L+C)/3")
    stat(ref_noise(A, dates, cost_bps=0.5, maxlev=3.5, vwap_basis="close", nmin=390,
                   close_at_1600=True),
         "REF + close at 16:00 bar")
    stat(ref_noise(A, dates, cost_bps=0.5, maxlev=3.5, vwap_basis="close", nmin=390,
                   drop_halfdays=True),
         "REF + drop half-days")
    # --- daybook engine, same instruments/config ---
    panel = {"QQQ": d}
    eng = {}
    for tgt, ml, cb in [(0.02, 4.0, 2.0), (0.02, 3.5, 0.5), (0.02, 3.5, 1.0)]:
        total, _, _ = simulate(panel, DaybookConfig(core={"QQQ": 1.0}, conviction={},
                                                     target_vol=tgt, max_lev=ml, cost_bps=cb))
        eng[(tgt, ml, cb)] = total
        stat(total, f"DAYBOOK engine (tgt{tgt} maxlev{ml} cost{cb})")

    # --- direct per-day diff: REF live-config vs engine (same params) ---
    ref = ref_noise(A, dates, cost_bps=0.5, maxlev=3.5, vwap_basis="close", nmin=390)
    e = eng[(0.02, 3.5, 0.5)]
    both = pd.concat([ref.rename("ref"), e.rename("eng")], axis=1).dropna()
    print(f"\nper-day corr(ref,engine) = {both['ref'].corr(both['eng']):.3f}")
    print(f"days ref!=0: {(both['ref']!=0).sum()}  eng!=0: {(both['eng']!=0).sum()}  "
          f"both!=0: {((both['ref']!=0)&(both['eng']!=0)).sum()}")
    print(f"mean_ref {both['ref'].mean()*1e4:+.2f}bp  mean_eng {both['eng'].mean()*1e4:+.2f}bp  "
          f"ratio {both['eng'].mean()/both['ref'].mean():.2f}")
    d = (both["eng"] - both["ref"]).abs().sort_values(ascending=False)
    print("largest per-day gaps:")
    print(both.loc[d.index[:6]].assign(diff=(both["eng"] - both["ref"]).loc[d.index[:6]]).to_string())


if __name__ == "__main__":
    main()
