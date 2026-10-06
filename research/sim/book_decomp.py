"""PHASE 1b: decompose the live book into market / style / vol / residual alpha.

Returns in `book.Sim.replay` are recorded on the DECISION date d, and each leg earns
over a specific window, so the market factor must be matched to that window:
  night leg : close(d) -> open(d+1)            `on`  = O.shift(-1)/C - 1
  IBS leg   : open(d+1) -> open(d+2)           `oo`  = O.shift(-2)/O.shift(-1) - 1
  noise leg : intraday day d                   `id`  = C/O - 1
A close-to-close SPY factor is therefore off by a day and destroys the correlation —
the first version of this file made exactly that mistake (R^2 0.02).

The book's Sharpe has never been separated from long liquid-equity/tech beta. This
regresses each leg on its MATCHED market and tech factor, with Newey-West HAC t-stats,
and reports the alpha that survives.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.book_decomp
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import book as B
from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/book_decomp_out.txt"


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
    se = np.sqrt(np.diag(cov))
    r2 = 1 - resid.var() / y.var() if y.var() > 0 else 0.0
    return beta, beta / se, r2


def main():
    s = B.Sim()
    r = s.replay()
    P = D.etf()
    O, C = P["open"], P["close"]
    days = r.index

    def on(sym):   # close d -> open d+1
        return (O[sym].shift(-1) / C[sym] - 1).reindex(days)

    def oo(sym):   # open d+1 -> open d+2
        return (O[sym].shift(-2) / O[sym].shift(-1) - 1).reindex(days)

    def id_(sym):  # intraday d
        return (C[sym] / O[sym] - 1).reindex(days)

    def mk(f, g):
        return pd.DataFrame({"MKT": f("SPY"), "TECH": f("QQQ") - f("SPY"), "SIZE": f("IWM") - f("SPY"),
                             "VOLT": f("UVXY")}).loc[days]

    specs = {
        "r_night": mk(on, None),
        "r_ibs": mk(oo, None),
        "r_noise": mk(id_, None),   # noise is QQQ/SMH intraday; QQQ=MKT here
    }
    lines = ["Book factor decomposition, WINDOW-MATCHED factors (Sim.replay; NW-HAC(5))",
             "night=close->open, ibs=open->open(next), noise=intraday; qqq=mkt in noise", ""]
    for leg, fac in specs.items():
        df = pd.concat([r[[leg]], fac], axis=1).dropna()
        y = df[leg].values
        cols = list(fac.columns)
        X = np.column_stack([np.ones(len(df)), df[cols].values])
        beta, t, r2 = _ols(y, X)
        ann = (1 + y.mean()) ** 252 - 1
        a_ann = (1 + beta[0]) ** 252 - 1
        lines.append(f"{leg:8s} n={len(df):4d} ann={ann*100:6.1f}% alpha={a_ann*100:6.1f}% "
                     f"a_t={t[0]:5.2f} R2={r2:4.2f} | " +
                     "  ".join(f"{c}:{b*100:6.2f}/{tt:5.2f}" for c, b, tt in zip(cols, beta[1:], t[1:])))
        lines.append(f"         corr with matched MKT = {df[leg].corr(df[cols[0]]):+.2f}")

    # total book vs a same-window overnight + intraday SPY split (both known at d)
    tot = pd.concat([r[["r"]], pd.DataFrame({"on": on("SPY"), "id": id_("SPY")}).loc[days]], axis=1).dropna()
    X = np.column_stack([np.ones(len(tot)), tot["on"].values, tot["id"].values])
    beta, t, r2 = _ols(tot["r"].values, X)
    lines += ["", f"TOTAL book vs [overnight SPY, intraday SPY]: betas "
                  f"{beta[1]*100:.1f}/{beta[2]*100:.1f} (t {t[1]:.2f}/{t[2]:.2f}), R2={r2:.2f}, "
                  f"alpha={( (1+beta[0])**252-1)*100:.1f}%/yr (t {t[0]:.2f})"]
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
