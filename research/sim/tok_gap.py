"""TOK-GAP (pre-registered 2026-10-16, N 1009->1010): tokenized US-stock certificates (Gate
MSTRX/NVDAX/AAPLX/TSLAX) as an overnight sensor; judge the open->close DRIFT of the US-listed
underlying conditional on the residualized token mark, at the 09:30 official open.

STATUS 2026-10-16: DATA-BLOCKED at $0. Gate serves only ~2 weeks of 5m history (all four pairs
start 2026-10-01); Kraken does not expose xStock pairs to the public API; GeckoTerminal minute
OHLCV depth is far short of the registered 2025-06.. window. NEST (arXiv 2610.21491) used a
trade-level Gate reconstruction for GAP prediction only; the drift question needs months of
marks that no free API serves.

The one look is consumed ONLY when the minimum-n guard passes:
  each judged token needs >= 60 qualified token-days in BOTH halves (>= 120 per token panel).
Below that the runner prints coverage and exits without judging.
"""
import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

TOK = os.path.expanduser("~/Documents/Code/Projects/swing-trader/data/research/tok")
SH = os.path.expanduser("~/data/sharadar")
JUDGED = ["NVDAX_USDT", "AAPLX_USDT", "MSTRX_USDT"]
PLACEBO = "TSLAX_USDT"
UNDERLYING = {"MSTRX_USDT": "MSTR", "NVDAX_USDT": "NVDA", "AAPLX_USDT": "AAPL", "TSLAX_USDT": "TSLA"}
MIN_PER_HALF = 60


def et(ts):
    return pd.DatetimeIndex(pd.to_datetime(ts, utc=True)).tz_convert("America/New_York")


def load_tokens(pair):
    df = pq.read_table(os.path.join(TOK, f"{pair}_5m.parquet")).to_pandas()
    df["et"] = et(df["dt"])
    return df.set_index("et").sort_index()


def load_us(ticker):
    s = pq.read_table(os.path.join(SH, "stocks.parquet")).to_pandas()
    s = s[s["ticker"] == ticker].copy()
    s["d"] = pd.to_datetime(s["date"]).dt.tz_localize("America/New_York")
    s = s.set_index("d").sort_index()[["open", "close", "closeadj"]]
    acts = pq.read_table(os.path.join(SH, "actions.parquet")).to_pandas()
    a = acts[(acts["ticker"] == ticker) & (acts["action"] == "split")].copy()
    a["d"] = pd.to_datetime(a["date"]).dt.tz_localize("America/New_York")
    split_days = set(a.loc[a["value"].fillna(1) != 1, "d"])
    bad = set()
    for d0 in split_days:
        bad |= {d0, d0 + pd.Timedelta(days=1), d0 + pd.Timedelta(days=2)}
    return s[~s.index.isin(bad)]


def marks(pair, tc):
    out = []
    days = tc.index.normalize().unique()
    for d0 in days:
        try:
            close_t = pd.Timestamp(d0) + pd.Timedelta(hours=15, minutes=55)
            m09 = tc.loc[(tc.index >= d0 + pd.Timedelta(hours=8, minutes=30)) & (tc.index <= d0 + pd.Timedelta(hours=9))]["close"]
            m04 = tc.loc[(tc.index >= d0 + pd.Timedelta(hours=3, minutes=30)) & (tc.index <= d0 + pd.Timedelta(hours=4))]["close"]
            ref = tc.loc[(tc.index >= d0 - pd.Timedelta(days=1) + pd.Timedelta(hours=15, minutes=55)) & (tc.index <= d0 - pd.Timedelta(days=1) + pd.Timedelta(hours=17))]["close"]
            if len(m09) == 0 or len(m04) == 0 or len(ref) == 0:
                continue
            M09, M04, R = m09.iloc[-1], m04.iloc[-1], ref.iloc[0]
            m09_age = m09.index[-1] - (d0 + pd.Timedelta(hours=9))
            n_candles = len(tc.loc[(tc.index > d0 - pd.Timedelta(days=1) + pd.Timedelta(hours=16)) & (tc.index <= d0 + pd.Timedelta(hours=9))])
            if n_candles < 8 or m09_age < pd.Timedelta(minutes=-30):
                continue
            out.append(dict(d=d0, M09=M09, M04=M04, R=R))
        except Exception:
            continue
    return pd.DataFrame(out).set_index("d")


def run_pair(pair, us, btc5):
    tc = load_tokens(pair)
    mk = marks(pair, tc)
    tk = UNDERLYING[pair]
    u = us.loc[us.index.isin(mk.index)]
    j = mk.join(u[["open", "close"]], how="inner")
    if len(j) < 20:
        return None
    j["tok_day"] = np.log(j["M09"] / j["R"])
    j["tok_late"] = np.log(j["M09"] / j["M04"])
    j["drift"] = np.log(j["close"] / j["open"])
    if btc5 is not None:
        bt = btc5.copy()
        # BTC return over the same [R, M09] window (previous US close 16:00 -> 09:00 ET)
        rows = []
        for d0, row in j.iterrows():
            t0 = d0 - pd.Timedelta(days=1) + pd.Timedelta(hours=16)
            t1 = d0 + pd.Timedelta(hours=9)
            w = bt.loc[(bt.index > t0) & (bt.index <= t1)]
            rows.append(np.log(w["close"].iloc[-1] / w["close"].iloc[0]) if len(w) > 3 else np.nan)
        j["btc_day"] = rows
    else:
        j["btc_day"] = np.nan
    # rolling trailing-60 residualization (past-only)
    resid = np.full(len(j), np.nan)
    X = j[["btc_day", "tok_late"]].values
    y = j["tok_day"].values
    for i in range(len(j)):
        if i < 60:
            continue
        sl = slice(i - 60, i)
        yy, xx = y[sl], X[sl]
        ok = ~np.isnan(yy) & ~np.isnan(xx).any(axis=1)
        if ok.sum() < 40:
            continue
        xa, ya = xx[ok], yy[ok]
        A = np.column_stack([np.ones(len(xa)), xa])
        try:
            beta, *_ = np.linalg.lstsq(A, ya, rcond=None)
            if np.isnan(X[i]).any():
                resid[i] = np.nan
            else:
                resid[i] = y[i] - A[i - i] @ beta if False else y[i] - (beta[0] + X[i] @ beta[1:])
        except Exception:
            resid[i] = np.nan
    j["resid"] = resid
    w60 = pd.Series(np.abs(resid), index=j.index)
    j["resid_z"] = j["resid"] / w60.rolling(60, min_periods=40).median().replace(0, np.nan).shift(1)
    return j


def main():
    btc5 = None
    bp = os.path.join(TOK, "BTC_USDT_5m.parquet")
    if os.path.exists(bp):
        btc5 = load_tokens("BTC_USDT")
    panels = {}
    print("TOK-GAP runner (one look guarded; judge only at >= 60 qualified days per half per token)")
    for pair in JUDGED + [PLACEBO]:
        p = os.path.join(TOK, f"{pair}_5m.parquet")
        if not os.path.exists(p):
            print(pair, "no cache"); continue
        us = load_us(UNDERLYING[pair])
        j = run_pair(pair, us, btc5)
        if j is None:
            print(pair, "insufficient overlap with US bars"); continue
        h1 = j[j.index <= "2025-12-31"]; h2 = j[j.index > "2025-12-31"]
        n1, n2 = j["resid_z"].loc[h1.index].notna().sum(), j["resid_z"].loc[h2.index].notna().sum()
        print(f"{pair}: days {j.index.min().date()}..{j.index.max().date()}  qualified H1={n1} H2={n2}")
        panels[pair] = j
    ok = bool(panels) and all(p in panels for p in JUDGED) and all(
        panels[p]["resid_z"].loc[panels[p].index <= "2025-12-31"].notna().sum() >= MIN_PER_HALF
        and panels[p]["resid_z"].loc[panels[p].index > "2025-12-31"].notna().sum() >= MIN_PER_HALF
        for p in JUDGED if p in panels
    )
    if not ok:
        print()
        print("DATA-BLOCKED: minimum-n guard not met -> the registered one look is NOT consumed.")
        print("Options: (i) start a log-only Gate 5m collector now and judge after ~6 months;")
        print("         (ii) obtain token-mark history (paid archive or Dune) and rerun.")
        return
    import statsmodels.api as sm
    print("GUARD PASSED - judging (one look).")
    # TODO judged statistic when the data exists (pooled day-clustered slope + halves + ex-top-5 + TSLAX placebo)
    raise SystemExit("judge implementation gated on data arrival")


if __name__ == "__main__":
    main()
