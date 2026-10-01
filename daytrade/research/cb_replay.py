"""Studies Lab-CB / CC: Cboe equity put/call and SKEW as predictors of 20-day market returns (Lab Round 50).

  python -m daytrade.research.cb_replay
"""
from __future__ import annotations

import io
import json
import math

import numpy as np
import pandas as pd
import requests

from ..settings import DATA
from .ca_replay import daily_ff

OUT = DATA / "research" / "cb"


def nw_t(x, lags=20):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    n = len(x); m = x.mean(); e = x - m
    g0 = (e @ e) / n
    s = g0 + 2 * sum((1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n for k in range(1, lags + 1))
    return float(m / math.sqrt(s / n))


def fetch(url, name):
    p = OUT / name
    if not p.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        p.write_text(requests.get(url, timeout=30).text)
    return p.read_text()


def series_pc():
    txt = fetch("https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv", "equitypc.csv")
    lines = txt.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("DATE"))
    df = pd.read_csv(io.StringIO("\n".join(lines[i:])), skipinitialspace=True)
    df["d"] = pd.to_datetime(df.DATE, format="mixed")
    return df.set_index("d")["P/C Ratio"].astype(float)


def series_skew():
    txt = fetch("https://cdn.cboe.com/api/global/us_indices/daily_prices/SKEW_History.csv", "SKEW_History.csv")
    df = pd.read_csv(io.StringIO(txt))
    df["d"] = pd.to_datetime(df.DATE, format="mixed")
    return df.set_index("d").SKEW.astype(float)


def test(sig_raw, smooth, sign, halves, mkt):
    s = sig_raw.rolling(smooth).mean() if smooth > 1 else sig_raw
    z = (s - s.rolling(252).mean()) / s.rolling(252).std()
    fwd = (1 + mkt).rolling(20).apply(np.prod, raw=True).shift(-20) - 1        # t+1..t+20
    d = pd.DataFrame({"z": z, "fwd": fwd}).dropna()
    d = d[d.index.isin(mkt.index)]
    hi = d.z >= 1.0
    diff_series = np.where(hi, d.fwd - d.fwd[~hi].mean(), np.nan)
    res = {"n_signal_days": int(hi.sum()), "n_days": len(d)}
    for name, a, b in halves:
        m = (d.index >= a) & (d.index <= b)
        res[name] = {"fwd_signal_bp": float(d.fwd[m & hi].mean() * 1e4), "fwd_other_bp": float(d.fwd[m & ~hi].mean() * 1e4),
                     "diff_bp": float((d.fwd[m & hi].mean() - d.fwd[m & ~hi].mean()) * 1e4), "n_signal": int((m & hi).sum())}
    # NW t on the daily series of (signal indicator x fwd) regression: fwd = a + b*hi
    y = d.fwd.values; x = hi.values.astype(float)
    xc = x - x.mean()
    b = (xc @ (y - y.mean())) / (xc @ xc)
    resid = y - y.mean() - b * xc
    u = xc * resid
    n = len(u); g = (u @ u) / n + 2 * sum((1 - k / 21) * (u[k:] @ u[:-k]) / n for k in range(1, 21))
    se = math.sqrt(g / n) / ((xc @ xc) / n)
    res["diff_all_bp"] = float(b * 1e4); res["nw_t"] = float(b / se)
    ok = all(np.sign(res[h[0]]["diff_bp"]) == sign for h in halves) and abs(res["nw_t"]) >= 2 and np.sign(res["nw_t"]) == sign
    res["verdict"] = "PASS" if ok else "DEAD"
    return res


def run():
    mkt = daily_ff().mkt
    out = {"Lab-CB put/call (high -> higher)": test(series_pc(), 10, +1, (("h1", "2006-11-01", "2012-12-31"), ("h2", "2013-01-01", "2019-10-31")), mkt),
           "Lab-CC SKEW (high -> lower)": test(series_skew(), 1, -1, (("h1", "1990-01-01", "2007-12-31"), ("h2", "2008-01-01", "2026-08-31")), mkt)}
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    run()
