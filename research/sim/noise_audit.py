"""PHASE 2: audit the intraday "noise" leg's residual alpha (~13%, t~3) from book_decomp.

Questions:
  1. Is the alpha a vol-targeting artifact? Compare the LEVERED leg (x lev) with the
     UNLEVERED signal, and to a constant 1x leg.
  2. Is it an omitted-factor artifact? Regress on a parsimonious matched intraday factor
     set (QQQ, UVXY, IWM) instead of the collinear 4-factor set.
  3. Is it stable? By year / half.
  4. Does it survive realistic costs and the per-trade count?

Run: PYTHONPATH=. .venv/bin/python -m research.sim.noise_audit
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import book as B
from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/noise_audit_out.txt"


def _ols(y, X, lags=5):
    n, k = X.shape
    XtXi = np.linalg.pinv(X.T @ X)
    beta = XtXi @ X.T @ y
    resid = y - X @ beta
    S = np.zeros((k, k))
    for i in range(n):
        xi = X[i][:, None]
        S += xi @ xi.T * resid[i] ** 2
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        for i in range(l, n):
            xi, xj = X[i][:, None], X[i - l][:, None]
            S += w * (xi @ xj.T * resid[i] * resid[i - l] + xj @ xi.T * resid[i - l] * resid[i])
    cov = XtXi @ S @ XtXi
    return beta, beta / np.sqrt(np.diag(cov)), 1 - resid.var() / y.var() if y.var() > 0 else 0.0


def sharpe(r):
    r = r.dropna()
    return r.mean() / r.std() * np.sqrt(252) if len(r) > 20 and r.std() else np.nan


def main():
    q = B.noise_days("QQQ", cost=0.5)
    P = D.etf()
    O, C = P["open"], P["close"]
    idq = (C["QQQ"] / O["QQQ"] - 1).reindex(q.index)
    idu = (C["UVXY"] / O["UVXY"] - 1).reindex(q.index)
    idi = (C["IWM"] / O["IWM"] - 1).reindex(q.index)
    cap = 3.5
    lev = q["lev"].clip(upper=cap)
    unlev = q["ret"]
    levered = (lev * q["ret"])
    const1 = q["ret"]  # constant 1x (unlevered)
    df = pd.DataFrame({"unlev": unlev, "levered": levered, "lev": lev,
                       "QQQ": idq, "UVXY": idu, "IWM": idi}).dropna()
    lines = ["Noise-leg audit (QQQ, Sim.noise_days, cost 0.5bp/trade)", ""]
    lines.append(f"trades/day mean={q['trades'].mean():.2f}  levered Sharpe={sharpe(df['levered']):.2f} "
                 f"unlev Sharpe={sharpe(df['unlev']):.2f}")
    lines.append(f"annual: levered={(1+df['levered'].mean())**252-1:.1%} unlev={(1+df['unlev'].mean())**252-1:.1%}")
    for lab, y in [("unlevered", df["unlev"]), ("levered(x<=3.5)", df["levered"])]:
        for fset, nm in [(["QQQ"], "QQQ"), (["QQQ", "UVXY"], "QQQ+UVXY"),
                         (["QQQ", "IWM", "UVXY"], "QQQ+IWM+UVXY")]:
            X = np.column_stack([np.ones(len(df)), df[fset].values])
            b, t, r2 = _ols(y.values, X)
            a_ann = (1 + b[0]) ** 252 - 1
            lines.append(f"{lab:16s} ~ {nm:14s} alpha={a_ann*100:6.1f}% t={t[0]:5.2f} R2={r2:4.2f} | " +
                         "  ".join(f"{c}:{bb:.2f}({tt:.1f})" for c, bb, tt in zip(fset, b[1:], t[1:])))
    lines += ["", "levered leg by year: mean_bp Sharpe"]
    for y, g in df.groupby(df.index.year):
        if len(g) > 30:
            lines.append(f"  {y}: mean={g['levered'].mean()*1e4:6.1f}bp Sharpe={sharpe(g['levered']):5.2f} "
                         f"(21-23 split mean={g['levered'].mean()*1e4:.1f})")
    lines += ["", "cost sensitivity (levered annual, Sharpe):"]
    for c in [0.5, 1.0, 2.0, 4.0]:
        qc = B.noise_days("QQQ", cost=c)
        lc = (qc["lev"].clip(upper=cap) * qc["ret"]).reindex(df.index).dropna()
        lines.append(f"  {c:.1f}bp/trade: ann={(1+lc.mean())**252-1:6.1%} Sharpe={sharpe(lc):4.2f}")
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
