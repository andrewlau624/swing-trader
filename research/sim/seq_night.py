"""Studies SEQ-NIGHT (A, N 1038) and SEQ-ENTRY (B, N 1039): indicator SEQUENCES as a night-pool ranker and as a stand-alone entry.
Registration: research/drafts/round1_prose.md (2026-10-19).

Phases:
  build : per-ticker wide-frame features from Sharadar SEP (split-adjusted OHLCV), universe rows (closeunadj >= 5, ADV20 >= $10M,
          >= 60 bars) -> data/research/program/seq_feats/batch_*.parquet; night-pool rows -> seq_feats_night.parquet
  a     : SEQ-NIGHT  -> data/research/program/seq_night_out.txt
  b     : SEQ-ENTRY  -> data/research/program/seq_entry_out.txt

Run:  PYTHONPATH=. .venv/bin/python research/sim/seq_night.py --phase all
"""
from __future__ import annotations

import argparse
import glob
import pathlib
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data" / "research" / "program"
FEAT = PROG / "seq_feats"
S = pathlib.Path.home() / "data" / "sharadar"
SEED = 20261019
GBM = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200, l2_regularization=1.0)
COST_RT = 0.0010
SECTORS = ["Technology", "Healthcare", "Industrials", "Financial Services", "Consumer Cyclical",
           "Communication Services", "Real Estate", "Basic Materials", "Energy", "Consumer Defensive", "Utilities"]
MKT = ["spy_ret1", "spy_ret5", "spy_ret20", "spy_vol20", "spy_c_s200", "breadth50", "breadth200", "dow"]
NONFEAT = {"date", "ticker", "l1", "l3", "l1x", "l3x", "spy_l1", "spy_l3", "c_gt_s50", "c_gt_s200"}


# ----------------------------------------------------------------------------- wide-frame helpers
def run_len(B: pd.DataFrame) -> pd.DataFrame:
    cs = B.astype(np.int32).cumsum()
    return (cs - cs.where(~B).ffill().fillna(0)).astype(np.float32)


def days_since(E: pd.DataFrame) -> pd.DataFrame:
    idx = np.broadcast_to(np.arange(len(E), dtype=float)[:, None], E.shape)
    I = pd.DataFrame(idx, index=E.index, columns=E.columns)
    return (I - I.where(E).ffill()).astype(np.float32)


def flip(B: pd.DataFrame, valid: pd.DataFrame) -> pd.DataFrame:
    return (B.astype(float).diff() != 0) & valid & valid.shift(1, fill_value=False)


def signed_run(B_pos: pd.DataFrame, B_neg: pd.DataFrame) -> pd.DataFrame:
    return run_len(B_pos) - run_len(B_neg)


def wma(x: pd.DataFrame, n: int) -> pd.DataFrame:
    w = np.arange(n, 0, -1, dtype=float)      # weight n for lag 0 ... 1 for lag n-1
    acc = None
    for i in range(n):
        t = x.shift(i) * w[i]
        acc = t if acc is None else acc + t
    return acc / w.sum()


def laguerre_rsi(c: pd.DataFrame, g: float = 0.8) -> pd.DataFrame:
    x = c.to_numpy(float)
    n, m = x.shape
    out = np.full((n, m), np.nan)
    L0p = L1p = L2p = L3p = np.zeros(m)
    started = np.zeros(m, bool)
    for t in range(n):
        xt = x[t]
        ok = ~np.isnan(xt)
        p = np.where(ok, xt, L0p)
        p = np.where(started, p, np.where(ok, xt, 0.0))
        L0 = (1 - g) * p + g * L0p
        L1 = -g * L0 + L0p + g * L1p
        L2 = -g * L1 + L1p + g * L2p
        L3 = -g * L2 + L2p + g * L3p
        cu_ = np.maximum(L0 - L1, 0) + np.maximum(L1 - L2, 0) + np.maximum(L2 - L3, 0)
        cd_ = np.maximum(L1 - L0, 0) + np.maximum(L2 - L1, 0) + np.maximum(L3 - L2, 0)
        tot = cu_ + cd_
        out[t] = np.where(ok & started & (tot > 0), cu_ / np.where(tot > 0, tot, 1), np.nan)
        started = started | ok
        L0p, L1p, L2p, L3p = L0, L1, L2, L3
    return pd.DataFrame(out, index=c.index, columns=c.columns)


def features(o, h, l, c, v, cu) -> dict[str, pd.DataFrame]:
    F: dict[str, pd.DataFrame] = {}
    valid = c.notna()
    pc_ = c.shift(1)
    r1 = c / pc_ - 1
    F["day_ret"] = r1
    for w in (5, 20, 63, 252):
        F[f"ret{w}"] = c / c.shift(w) - 1
    lr = np.log(c / pc_)
    F["vol20"] = lr.rolling(20).std() * np.sqrt(252)
    F["vol60"] = lr.rolling(60).std() * np.sqrt(252)
    F["gap"] = o / pc_ - 1
    F["low_ret"] = l / pc_ - 1
    F["high_ret"] = h / pc_ - 1
    F["prev_low_ret"] = F["low_ret"].shift(1)
    rng = h - l
    F["ibs"] = ((c - l) / rng).where(rng > 0)
    F["range_pct"] = rng / c
    tr = np.maximum(np.maximum(h - l, (h - pc_).abs()), (l - pc_).abs())
    atr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()
    F["atr_pct"] = atr14 / c
    adv20 = (c * v).rolling(20).mean()
    F["log_adv"] = np.log(adv20)
    F["log_px"] = np.log(cu)
    hi252 = c.rolling(252, min_periods=120).max()
    lo252 = c.rolling(252, min_periods=120).min()
    F["dist_hi"] = c / hi252 - 1
    F["dist_lo"] = c / lo252 - 1
    F["days_since_hi"] = days_since(c >= hi252)
    F["days_since_lo"] = days_since(c <= lo252)
    vmed = v.rolling(20).median()
    F["volratio"] = v / vmed
    F["vol5_20"] = v.rolling(5).mean() / v.rolling(20).mean()
    F["climax_age"] = days_since(v > 3 * vmed)
    F["dryup_run"] = run_len(v < 0.5 * vmed)
    F["down_run"] = run_len(r1 < 0)
    F["up_run"] = run_len(r1 > 0)
    F["nbig_dn20"] = (r1 <= -0.03).rolling(20).sum()
    F["nbig_up20"] = (r1 >= 0.03).rolling(20).sum()
    F["ngap20"] = (F["gap"].abs() > 0.02).rolling(20).sum()
    # moving-average stack
    s20, s50, s200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    F["c_s20"], F["c_s50"], F["c_s200"] = c / s20 - 1, c / s50 - 1, c / s200 - 1
    b1, b2, b3 = s20 > s50, s50 > s200, c > s200
    ok200 = s200.notna()
    F["stack"] = (b1.astype(float) + b2.astype(float) + b3.astype(float)).where(ok200)
    F["stack_bull_run"] = run_len(b1 & b2 & b3)
    F["stack_bear_run"] = run_len(~b1 & ~b2 & ~b3 & ok200)
    F["age_c_s50"] = days_since(flip(c > s50, s50.notna()))
    F["age_c_s200"] = days_since(flip(b3, ok200))
    F["age_s20_s50"] = days_since(flip(b1, s50.notna()))
    F["age_s50_s200"] = days_since(flip(b2, ok200))
    F["c_gt_s50"] = (c > s50).where(s50.notna()).astype(float)
    F["c_gt_s200"] = b3.where(ok200).astype(float)
    # EMA ribbon 8/13/21/34/55 (SlimRibbons)
    e = [c.ewm(span=n, adjust=False).mean() for n in (8, 13, 21, 34, 55)]
    align = sum((e[i] > e[i + 1]).astype(float) for i in range(4))
    F["ribbon_align"] = align
    F["ribbon_bull_run"] = run_len(align == 4)
    F["ribbon_bear_run"] = run_len((align == 0) & valid)
    F["ribbon_width"] = (e[0] - e[4]) / c
    # MACD 12/26/9
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=9, adjust=False).mean()
    hist = macd - sig
    F["macd_pct"] = macd / c
    F["hist_pct"] = hist / c
    F["hist_run"] = signed_run(hist > 0, hist < 0)
    F["hist_slope"] = (hist - hist.shift(1)) / c
    F["hist_rise_run"] = run_len(hist > hist.shift(1))
    F["hist_fall_run"] = run_len(hist < hist.shift(1))
    F["macd_cross_age"] = days_since(flip(hist > 0, valid))
    F["macd_zero_run"] = signed_run(macd > 0, macd < 0)
    # RSI 14 (Wilder)
    d = c.diff()
    au = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    ad = (-d).clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + au / ad.where(ad > 0))
    rsi = rsi.where(ad > 0, 100.0).where(valid)
    F["rsi"] = rsi
    F["rsi_lt30_run"] = run_len(rsi < 30)
    F["rsi_gt70_run"] = run_len(rsi > 70)
    F["rsi_lt30_age"] = days_since(rsi < 30)
    F["rsi_gt70_age"] = days_since(rsi > 70)
    F["rsi_min20"] = rsi.rolling(20).min()
    F["rsi_max20"] = rsi.rolling(20).max()
    F["rsi_chg5"] = rsi - rsi.shift(5)
    cl20, ch20 = c.rolling(20).min(), c.rolling(20).max()
    bull_div = (c <= cl20) & (rsi > F["rsi_min20"] + 5)
    bear_div = (c >= ch20) & (rsi < F["rsi_max20"] - 5)
    F["bull_div"] = bull_div.astype(float).where(valid)
    F["bear_div"] = bear_div.astype(float).where(valid)
    F["bull_div_age"] = days_since(bull_div)
    F["bear_div_age"] = days_since(bear_div)
    # RSI Laguerre (gamma .8)
    lag = laguerre_rsi(c, 0.8)
    F["lag_rsi"] = lag
    F["lag_lt2_run"] = run_len(lag < 0.2)
    F["lag_gt8_run"] = run_len(lag > 0.8)
    # ADX / DMI 14
    up, dn = h - h.shift(1), l.shift(1) - l
    pdm = up.where((up > dn) & (up > 0), 0.0)
    mdm = dn.where((dn > up) & (dn > 0), 0.0)
    atrw = tr.ewm(alpha=1 / 14, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1 / 14, adjust=False).mean() / atrw
    mdi = 100 * mdm.ewm(alpha=1 / 14, adjust=False).mean() / atrw
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).where((pdi + mdi) > 0)
    adx = dx.ewm(alpha=1 / 14, adjust=False).mean()
    F["adx"] = adx
    F["di_diff"] = pdi - mdi
    F["di_cross_age"] = days_since(flip(pdi > mdi, valid))
    F["adx_rise_run"] = run_len(adx > adx.shift(1))
    F["adx_gt25_run"] = run_len(adx > 25)
    # Bollinger 20/2, bandwidth, Keltner, TTM squeeze, Squeeze Pro levels
    sd = c.rolling(20).std()
    bb_up, bb_lo = s20 + 2 * sd, s20 - 2 * sd
    F["pctb"] = (c - bb_lo) / (bb_up - bb_lo).where((bb_up - bb_lo) > 0)
    bw = (bb_up - bb_lo) / s20 * 100
    F["bw"] = bw
    bw60 = bw.rolling(60).mean()
    F["bw_ratio"] = bw / bw60
    F["explosive"] = ((bw60 > 30) & (bw < 15)).astype(float).where(valid)
    F["bw_pct120"] = bw.rolling(120, min_periods=60).rank(pct=True)
    kc_mid = c.ewm(span=20, adjust=False).mean()
    atr20 = tr.rolling(20).mean()
    sq = {}
    for k in (1.0, 1.5, 2.0):
        sq[k] = (bb_up < kc_mid + k * atr20) & (bb_lo > kc_mid - k * atr20)
    F["sq_on"] = sq[1.5].astype(float).where(valid)
    F["sq_on_run"] = run_len(sq[1.5])
    rel = (~sq[1.5]) & sq[1.5].shift(1, fill_value=False).astype(bool)
    F["sq_rel_age"] = days_since(rel)
    F["sq_fired5"] = ((F["sq_rel_age"] <= 5) & ~sq[1.5]).astype(float).where(valid)
    F["sq_level"] = (sq[1.0].astype(float) * 3 + (sq[1.5] & ~sq[1.0]).astype(float) * 2
                     + (sq[2.0] & ~sq[1.5]).astype(float)).where(valid)
    F["sq_tight_run"] = run_len(sq[1.0])
    hh20, ll20 = h.rolling(20).max(), l.rolling(20).min()
    val = c - ((hh20 + ll20) / 2 + s20) / 2
    F["ttm_mom"] = val / c
    F["ttm_mom_run"] = signed_run(val > 0, val < 0)
    F["ttm_mom_rise_run"] = run_len(val > val.shift(1))
    F["ttm_mom_slope"] = (val - val.shift(19)) / 19 / c
    # Hull MA 20: concavity, turning points
    hma = wma(2 * wma(c, 10) - wma(c, 20), 4)
    dh = hma.diff()
    F["c_hma"] = c / hma - 1
    F["hma_slope"] = dh / c
    F["hma_concave"] = np.sign(dh.diff()).where(valid)
    F["hma_turn_age"] = days_since(flip(dh > 0, hma.notna()))
    F["hma_up_run"] = signed_run(dh > 0, dh < 0)
    # Three weeks tight; buy-the-dip; stochastic; CCI; Donchian
    rng15 = c.rolling(15).max() / c.rolling(15).min() - 1
    F["tight15"] = rng15
    F["tight_run"] = run_len(rng15 < 0.015)
    F["btd"] = ((c <= cl20 * 1.02) & (rsi < 30) & b3).astype(float).where(valid)
    hh14, ll14 = h.rolling(14).max(), l.rolling(14).min()
    k_ = (c - ll14) / (hh14 - ll14).where((hh14 - ll14) > 0) * 100
    d_ = k_.rolling(3).mean()
    F["stoch_k"], F["stoch_d"] = k_, d_
    F["stoch_cross_age"] = days_since(flip(k_ > d_, valid))
    F["stoch_lt20_run"] = run_len(k_ < 20)
    F["stoch_gt80_run"] = run_len(k_ > 80)
    tp = (h + l + c) / 3
    F["cci"] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std()).where(tp.rolling(20).std() > 0)
    brk_up = c > hh20.shift(1)
    brk_dn = c < ll20.shift(1)
    F["brk_up_age"] = days_since(brk_up)
    F["brk_dn_age"] = days_since(brk_dn)
    F["obv_slope"] = (np.sign(d) * v).cumsum().diff(20) / (v.rolling(20).sum())
    return F


# ----------------------------------------------------------------------------- build
def load_sep() -> pd.DataFrame:
    t = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "category", "sector", "lastupdated"])
    t = t[(t.table == "SEP") & t.category.fillna("").str.contains("Common Stock")]
    t = t[~t.category.fillna("").str.contains("Secondary")]
    tks = sorted(t.ticker.unique())
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj"]
    tab = pq.read_table(S / "stocks.parquet", columns=cols, filters=[("ticker", "in", tks), ("date", ">=", pd.Timestamp("1997-06-01").date())])
    df = tab.to_pandas()
    df["ticker"] = df["ticker"].astype("category")
    df["date"] = pd.to_datetime(df["date"])
    for c_ in ["open", "high", "low", "close", "volume", "closeadj", "closeunadj"]:
        df[c_] = df[c_].astype("float32")
    return df


def build() -> None:
    FEAT.mkdir(parents=True, exist_ok=True)
    for f in FEAT.glob("batch_*.parquet"):
        f.unlink()
    t0 = time.time()
    df = load_sep()
    print(f"SEP loaded {len(df):,} rows, {df.ticker.nunique()} tickers, {time.time()-t0:.0f}s", flush=True)
    # ever-eligible tickers (superset): any day with closeunadj >= 5 and close*volume >= $10M
    elig = df[(df.closeunadj >= 5) & (df.close * df.volume >= 1e7)].ticker.unique()
    df = df[df.ticker.isin(elig)]
    df["ticker"] = df["ticker"].cat.remove_unused_categories()
    tks = list(df.ticker.cat.categories)
    print(f"eligible-ever tickers {len(tks)}, rows {len(df):,}", flush=True)
    picks = pd.read_parquet(PROG / "sel_night_names_primary.parquet")
    if "rule" in picks.columns:
        picks = picks[picks.rule == "current"]
    pick_keys = set(zip(pd.to_datetime(picks.date), picks.ticker))
    night_parts = []
    B = 150
    df = df.set_index(["date", "ticker"]).sort_index()
    for bi in range(0, len(tks), B):
        bt = tks[bi:bi + B]
        sub = df.loc[(slice(None), bt), :]
        W = {k: sub[k].unstack("ticker") for k in ["open", "high", "low", "close", "volume", "closeadj", "closeunadj"]}
        o, h, l, c, v, ca, cu = (W[k].astype(float) for k in ["open", "high", "low", "close", "volume", "closeadj", "closeunadj"])
        F = features(o, h, l, c, v, cu)
        adv20 = (c * v).rolling(20).mean()
        mask = (cu >= 5) & (adv20 >= 1e7) & c.shift(60).notna() & (c.index.to_series() >= "1999-01-01").to_numpy()[:, None]
        l1 = o.shift(-1) / c - 1
        l3 = ca.shift(-3) / ca - 1
        mask = mask & l1.notna()
        ii, jj = np.where(mask.to_numpy())
        out = {"date": c.index.to_numpy()[ii], "ticker": np.asarray(c.columns)[jj]}
        for k, Fk in F.items():
            out[k] = Fk.to_numpy(np.float32)[ii, jj]
        out["l1"] = l1.to_numpy(np.float32)[ii, jj]
        out["l3"] = l3.to_numpy(np.float32)[ii, jj]
        res = pd.DataFrame(out)
        res.to_parquet(FEAT / f"batch_{bi//B:03d}.parquet", index=False)
        key = list(zip(res.date, res.ticker))
        inn = np.fromiter((k in pick_keys for k in key), bool, len(key))
        if inn.any():
            night_parts.append(res[inn])
        print(f"batch {bi//B:3d}: tickers {len(bt)} rows {len(res):,} night {int(inn.sum())} {time.time()-t0:.0f}s", flush=True)
    night = pd.concat(night_parts, ignore_index=True)
    night.to_parquet(PROG / "seq_feats_night.parquet", index=False)
    # market state by date: SPY + breadth
    spy = pd.read_parquet(S / "funds.parquet", columns=["ticker", "date", "open", "close", "closeadj"], filters=[("ticker", "in", ["SPY", "QQQ"])])
    spy["date"] = pd.to_datetime(spy.date)
    sp = spy[spy.ticker == "SPY"].sort_values("date").set_index("date")
    m = pd.DataFrame(index=sp.index)
    m["spy_l1"] = sp.open.shift(-1) / sp.close - 1
    m["spy_l3"] = sp.closeadj.shift(-3) / sp.closeadj - 1
    m["spy_ret1"] = sp.close.pct_change()
    m["spy_ret5"] = sp.close / sp.close.shift(5) - 1
    m["spy_ret20"] = sp.close / sp.close.shift(20) - 1
    m["spy_vol20"] = np.log(sp.close).diff().rolling(20).std() * np.sqrt(252)
    m["spy_c_s200"] = sp.close / sp.close.rolling(200).mean() - 1
    br = pd.concat([pd.read_parquet(f, columns=["date", "c_gt_s50", "c_gt_s200"]) for f in sorted(FEAT.glob("batch_*.parquet"))])
    br = br.groupby("date").agg(breadth50=("c_gt_s50", "mean"), breadth200=("c_gt_s200", "mean"))
    m = m.join(br, how="left")
    m["dow"] = m.index.dayofweek.astype(float)
    qq = spy[spy.ticker == "QQQ"].sort_values("date").set_index("date").closeadj.rename("qqq")
    m = m.join(qq, how="left")
    m.reset_index().to_parquet(PROG / "seq_market.parquet", index=False)
    print(f"build done: night rows {len(night):,} of {len(pick_keys):,} picks; market rows {len(m)}; {time.time()-t0:.0f}s", flush=True)


# ----------------------------------------------------------------------------- shared judge helpers
def nw_t(x: np.ndarray, lags: int = 0) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    e = x - x.mean()
    s = (e * e).sum()
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (e[L:] * e[:-L]).sum()
    se = np.sqrt(s) / n
    return x.mean() / se if se > 0 else float("nan")


def market() -> pd.DataFrame:
    m = pd.read_parquet(PROG / "seq_market.parquet")
    m["date"] = pd.to_datetime(m.date)
    return m


def fit_gbm(X: np.ndarray, y: np.ndarray, seed: int = 0, **kw) -> HistGradientBoostingRegressor:
    p = dict(GBM); p.update(kw)
    return HistGradientBoostingRegressor(random_state=seed, **p).fit(X, y)


def shuffle_within(df: pd.DataFrame, col: str, rng: np.random.Generator) -> np.ndarray:
    y = df[col].to_numpy(float).copy()
    order = np.argsort(df.date.to_numpy(), kind="stable")
    y_sorted = y[order]
    dates_sorted = df.date.to_numpy()[order]
    bounds = np.flatnonzero(np.r_[True, dates_sorted[1:] != dates_sorted[:-1], True])
    for a, b in zip(bounds[:-1], bounds[1:]):
        y_sorted[a:b] = rng.permutation(y_sorted[a:b])
    out = np.empty_like(y); out[order] = y_sorted
    return out


# ----------------------------------------------------------------------------- A: SEQ-NIGHT
def night_frame() -> tuple[pd.DataFrame, list[str]]:
    nm = pd.read_parquet(PROG / "sel_night_names_primary.parquet")
    if "rule" in nm.columns:
        nm = nm[nm.rule == "current"].drop(columns=["rule"])
    nm["date"] = pd.to_datetime(nm.date)
    ft = pd.read_parquet(PROG / "seq_feats_night.parquet")
    ft["date"] = pd.to_datetime(ft.date)
    drop = [c_ for c_ in ft.columns if c_ in {"day_ret", "vol20", "log_adv", "log_px"}]   # keep the pool's own values
    d = nm.merge(ft.drop(columns=drop), on=["date", "ticker"], how="inner")
    d["log_adv"] = np.log(d.adv); d["log_px"] = np.log(d.price)
    m = market()
    d = d.merge(m.drop(columns=["qqq", "spy_l1", "spy_l3"]), on="date", how="left")
    t = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "sector", "lastupdated"])
    t = t[t.table == "SEP"].sort_values("lastupdated").drop_duplicates("ticker", keep="last").set_index("ticker")
    d["sector"] = d.ticker.map(t.sector)
    for s_ in SECTORS:
        d[f"sec_{s_[:6]}"] = (d.sector == s_).astype(float)
    d["ssr"] = ((d.low_ret <= -0.10) | (d.prev_low_ret <= -0.10)).astype(float)
    d["n_picks"] = d.groupby("date").ticker.transform("size").astype(float)
    sess = np.sort(d.date.unique()); pos = {x: i for i, x in enumerate(sess)}
    d["si"] = d.date.map(pos)
    d = d.sort_values(["ticker", "si"])
    d["repeat"] = ((d.si - d.groupby("ticker").si.shift(1)) <= 5).astype(float)
    d = d.sort_values(["date", "ticker"]).reset_index(drop=True)
    d["label"] = (d.r - d.groupby("date").r.transform("mean")).clip(-0.5, 0.5)
    feats = [c_ for c_ in d.columns if c_ not in {"date", "ticker", "r", "per", "frac", "w", "price", "adv", "sector", "si", "label",
                                                   "l1", "l3", "c_gt_s50", "c_gt_s200"}]
    return d, feats


def judge_night(df: pd.DataFrame, pred: np.ndarray, label: str) -> tuple[list[str], float]:
    d = df.assign(p=pred)
    rows = []
    for dt, g in d.groupby("date"):
        if len(g) < 4:
            continue
        o = np.argsort(g.p.to_numpy()); r = g.r.to_numpy(); half = len(g) // 2
        rows.append(dict(date=dt, tmb=(r[o[-half:]].mean() - r[o[:half]].mean()) * 1e4,
                         rho=pd.Series(r).corr(g.p.reset_index(drop=True), method="spearman")))
    t = pd.DataFrame(rows)
    x = t.tmb.to_numpy(); s = np.sort(x)
    h1 = t[t.date < "2021-01-01"].tmb; h2 = t[t.date >= "2021-01-01"].tmb
    dec = d.assign(q=d.groupby("date").p.rank(pct=True)).assign(q=lambda z: np.minimum((z.q * 5).astype(int), 4))
    decm = dec.groupby("q").r.mean() * 1e4
    return [f"  {label}: nights {len(t)}; top-half minus bottom-half {x.mean():+.1f}bp t {nw_t(x):.2f} med {np.median(x):+.1f} "
            f"hit {(x > 0).mean():.3f} h1(2016-20) {h1.mean():+.1f} h2(2021-26) {h2.mean():+.1f} ex-top-5 {s[:-5].mean():+.1f}; "
            f"Spearman {t.rho.mean():+.3f}; pred quintile means bp {decm.round(0).tolist()}"], float(x.mean())


def night_replays(df: pd.DataFrame, pred: np.ndarray) -> list[str]:
    d = df.assign(p=pred)
    base_t, tilt, filt = [], [], []
    for dt, g in d.groupby("date"):
        w = g.per.to_numpy(); r = g.r.to_numpy(); n = len(g)
        z = (g.p - g.p.mean()).to_numpy(); z = z / (z.std() if z.std() > 0 else 1)
        mlt = np.clip(1 + 0.25 * z, 0.25, 2); mlt = mlt / mlt.mean()
        base_t.append((w * r).sum()); tilt.append((w * mlt * r).sum())
        q = g.p.rank(pct=True).to_numpy()
        keep = q > 0.2 if n >= 5 else np.ones(n, bool)
        leg0 = min(1.0, 0.15 * n) * r.mean()
        leg1 = min(1.0, 0.15 * keep.sum()) * r[keep].mean() if keep.any() else 0.0
        filt.append(leg1 - leg0)
    b, a, f = np.array(base_t) * 1e4, np.array(tilt) * 1e4, np.array(filt) * 1e4
    return [f"  tilt replay (k .25): {b.mean():+.2f} -> {a.mean():+.2f} bp/night, diff {(a-b).mean():+.2f} t {nw_t(a-b):.2f} "
            f"= {(a-b).mean()*250/100*0.65:+.2f}pp/yr at w .65",
            f"  filter replay (drop bottom predicted quintile, cap .15n): diff {f.mean():+.2f} bp/night t {nw_t(f):.2f} "
            f"med {np.median(f):+.2f} = {f.mean()*250/100*0.65:+.2f}pp/yr at w .65"]


def phase_a() -> None:
    t0 = time.time()
    d, feats = night_frame()
    L = [f"SEQ-NIGHT (N 1038): indicator-sequence ranker on the night pool; rows {len(d):,} (coverage of SEL-NIGHT picks), features {len(feats)}", ""]
    train = d[d.date <= "2015-12-31"]; test = d[d.date >= "2016-01-01"]
    L.append(f"fit 1999-2015 (n {len(train):,}) -> judge 2016-2026 (n {len(test):,})")
    X_tr, y_tr, X_te = train[feats].to_numpy(np.float32), train.label.to_numpy(), test[feats].to_numpy(np.float32)
    mdl = fit_gbm(X_tr, y_tr)
    pred = mdl.predict(X_te)
    line, real = judge_night(test, pred, "GBM judge 2016-26"); L += line
    L += night_replays(test, pred)
    L += judge_night(train, mdl.predict(X_tr), "GBM in-sample 1999-2015 (fit quality only)")[0]
    mu, sd = X_tr.mean(0), X_tr.std(0) + 1e-9
    Xn_tr = np.nan_to_num((X_tr - mu) / sd); Xn_te = np.nan_to_num((X_te - mu) / sd)
    L += judge_night(test, Ridge(alpha=10.0).fit(Xn_tr, y_tr).predict(Xn_te), "Ridge judge 2016-26")[0]
    rng = np.random.default_rng(SEED)
    plc = []
    for i in range(20):
        ys = shuffle_within(train, "label", rng)
        plc.append(judge_night(test, fit_gbm(X_tr, ys, seed=i).predict(X_te), "p")[1])
    plc = np.array(plc)
    L.append(f"  placebo (20 shuffled-label fits): mean {plc.mean():+.1f}bp sd {plc.std():.1f} 95th {np.percentile(plc, 95):+.1f}; "
             f"real {real:+.1f} -> beats 95th: {real > np.percentile(plc, 95)}")
    imp = []
    for j, f in enumerate(feats):
        Xp = X_te.copy(); Xp[:, j] = rng.permutation(Xp[:, j])
        imp.append((f, real - judge_night(test, mdl.predict(Xp), "i")[1]))
    imp.sort(key=lambda z: -z[1])
    L.append("  permutation importance (bp of top-minus-bottom lost): " + ", ".join(f"{f} {v:+.1f}" for f, v in imp[:12]))
    L.append("== walk-forward (expanding fit, judge each year 2006-2026) ==")
    wf = []
    for y in range(2006, 2027):
        tr = d[d.date < f"{y}-01-01"]; te = d[(d.date >= f"{y}-01-01") & (d.date <= f"{y}-12-31")]
        if len(te) < 200:
            continue
        m3 = fit_gbm(tr[feats].to_numpy(np.float32), tr.label.to_numpy(), max_iter=200)
        wf.append(te.assign(p=m3.predict(te[feats].to_numpy(np.float32))))
    wf = pd.concat(wf)
    L += judge_night(wf, wf.p.to_numpy(), "walk-forward 2006-26")[0]
    L += night_replays(wf, wf.p.to_numpy())
    L.append("  by year top-minus-bottom bp: " + " ".join(f"{y}:{judge_night(g, g.p.to_numpy(), 'y')[1]:+.0f}" for y, g in wf.groupby(wf.date.dt.year)))
    L.append(f"\n({time.time()-t0:.0f}s)")
    txt = "\n".join(L) + "\n"
    (PROG / "seq_night_out.txt").write_text(txt)
    print(txt, flush=True)


# ----------------------------------------------------------------------------- B: SEQ-ENTRY
def load_universe() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    files = sorted(FEAT.glob("batch_*.parquet"))
    cols = [c_ for c_ in pq.ParquetFile(files[0]).schema_arrow.names if c_ not in {"c_gt_s50", "c_gt_s200"}]
    feats = [c_ for c_ in cols if c_ not in NONFEAT]
    rng = np.random.default_rng(SEED)
    m = market()
    tr_parts, te_parts = [], []
    for f in files:
        x = pd.read_parquet(f, columns=cols)
        x["date"] = pd.to_datetime(x.date)
        x = x.merge(m[["date"] + MKT + ["spy_l1", "spy_l3"]], on="date", how="left")
        te_parts.append(x[x.date >= "2016-01-01"])
        tr_parts.append(x[x.date <= "2015-12-31"])
    tr = pd.concat(tr_parts, ignore_index=True); del tr_parts
    te = pd.concat(te_parts, ignore_index=True); del te_parts
    if len(tr) > 1_500_000:
        tr = tr.iloc[np.sort(rng.choice(len(tr), 1_500_000, replace=False))].reset_index(drop=True)
    feats = feats + MKT
    for x in (tr, te):
        x["l1x"] = (x.l1 - x.spy_l1).clip(-0.3, 0.3)
        x["l3x"] = (x.l3 - x.spy_l3).clip(-0.5, 0.5)
    return tr, te, feats


def portfolio(te: pd.DataFrame, pred: np.ndarray, lab: str) -> pd.DataFrame:
    """Daily series: top-decile EW raw return, net of COST_RT, excess over SPY same window."""
    d = te[["date", lab, f"spy_{lab}"]].assign(p=pred)
    d = d[d[lab].notna()]
    q = d.groupby("date").p.rank(pct=True)
    top = d[q > 0.9]
    s = top.groupby("date").agg(raw=(lab, "mean"), n=(lab, "size"), spy=(f"spy_{lab}", "first"))
    s = s[s.n >= 10]
    s["net"] = s.raw - COST_RT
    s["exc"] = s.net - s.spy
    return s


def judge_entry(s: pd.DataFrame, m: pd.DataFrame, lab: str, label: str) -> tuple[list[str], float]:
    lags = 0 if lab == "l1" else 2
    x = s.exc.to_numpy() * 1e4
    srt = np.sort(x)
    yr = s.index.year
    h1, h2 = x[yr <= 2020], x[yr >= 2021]
    y22 = x[yr == 2022]
    # alpha vs window-matched SPY
    X = np.c_[np.ones(len(s)), s.spy.to_numpy()]
    beta = np.linalg.lstsq(X, s.net.to_numpy(), rcond=None)[0]
    resid = s.net.to_numpy() - X @ beta
    alpha_t = nw_t(resid + beta[0], lags)
    # total net vs QQQ hold 2016-26 (L3: 1/3 capital per daily cohort)
    daily = s.net / (1 if lab == "l1" else 3)
    tot = float(np.prod(1 + daily) - 1)
    qq = m.set_index("date").qqq.reindex(s.index).ffill()
    qtot = float(qq.iloc[-1] / qq.iloc[0] - 1)
    by = " ".join(f"{y}:{x[yr == y].mean():+.0f}" for y in sorted(set(yr)))
    return [f"  {label}: days {len(s)} names/day {s.n.mean():.0f}; net excess {x.mean():+.1f}bp/trade t(NW{lags}) {nw_t(x, lags):.2f} "
            f"med {np.median(x):+.1f} hit {(x > 0).mean():.3f} | halves {h1.mean():+.1f} / {h2.mean():+.1f} 2022 {y22.mean():+.1f} "
            f"ex-top-5 {srt[:-5].mean():+.1f} | beta {beta[1]:.2f} alpha {beta[0]*1e4:+.1f}bp t {alpha_t:.2f} | "
            f"raw net {s.net.mean()*1e4:+.1f}bp | total net {tot*100:+.0f}% vs QQQ hold {qtot*100:+.0f}% | by year {by}"], float(x.mean())


def phase_b() -> None:
    t0 = time.time()
    tr, te, feats = load_universe()
    m = market()
    L = [f"SEQ-ENTRY (N 1039): indicator-sequence entry, universe common stocks closeunadj >= $5, ADV20 >= $10M; "
         f"train rows {len(tr):,} (subsampled, 1999-2015) judge rows {len(te):,} (2016-26, {te.date.nunique()} days); features {len(feats)}", ""]
    print(L[0], f"{time.time()-t0:.0f}s", flush=True)
    X_tr = tr[feats].to_numpy(np.float32); X_te = te[feats].to_numpy(np.float32)
    rng = np.random.default_rng(SEED)
    for lab in ("l1", "l3"):
        y_all = tr[f"{lab}x"].to_numpy()
        ok = np.isfinite(y_all)
        y_tr, X_ok = y_all[ok], X_tr[ok]
        mdl = fit_gbm(X_ok, y_tr)
        pred = mdl.predict(X_te)
        line, real = judge_entry(portfolio(te, pred, lab), m, lab, f"GBM {lab} top-decile 2016-26"); L += line
        print(line[0], f"{time.time()-t0:.0f}s", flush=True)
        # bottom decile (short side, for information) and quintile means
        d = te[["date", f"{lab}x"]].assign(p=pred)
        q = np.minimum((d.groupby("date").p.rank(pct=True) * 10).astype(int), 9)
        dm = d.groupby(q)[f"{lab}x"].mean() * 1e4
        L.append(f"    pred-decile means of SPY-excess {lab} (bp): {dm.round(1).tolist()}")
        mu, sd = np.nanmean(X_tr, 0), np.nanstd(X_tr, 0) + 1e-9
        rg = Ridge(alpha=10.0).fit(np.nan_to_num((X_ok - mu) / sd), y_tr)
        L += judge_entry(portfolio(te, rg.predict(np.nan_to_num((X_te - mu) / sd)), lab), m, lab, f"Ridge {lab} top-decile 2016-26")[0]
        plc = []
        for i in range(20):
            ys = shuffle_within(tr[ok], f"{lab}x", rng)
            plc.append(judge_entry(portfolio(te, fit_gbm(X_ok, ys, seed=i).predict(X_te), lab), m, lab, "p")[1])
            print(f"    placebo {i} {plc[-1]:+.1f} {time.time()-t0:.0f}s", flush=True)
        plc = np.array(plc)
        L.append(f"    placebo (20 shuffled-label fits): mean {plc.mean():+.1f}bp sd {plc.std():.1f} 95th {np.percentile(plc, 95):+.1f}; "
                 f"real {real:+.1f} -> beats 95th: {real > np.percentile(plc, 95)}")
        # permutation importance on a 400-day subsample of the judge set
        days = rng.choice(np.sort(te.date.unique()), 400, replace=False)
        sub = te[te.date.isin(days)]; Xs = sub[feats].to_numpy(np.float32)
        base = judge_entry(portfolio(sub, mdl.predict(Xs), lab), m, lab, "b")[1]
        imp = []
        for j, f in enumerate(feats):
            Xp = Xs.copy(); Xp[:, j] = rng.permutation(Xp[:, j])
            imp.append((f, base - judge_entry(portfolio(sub, mdl.predict(Xp), lab), m, lab, "i")[1]))
        imp.sort(key=lambda z: -z[1])
        L.append("    permutation importance (bp of net excess lost, 400 judge days): " + ", ".join(f"{f} {v:+.1f}" for f, v in imp[:12]))
        L.append("")
        print(f"  {lab} done {time.time()-t0:.0f}s", flush=True)
    # walk-forward (secondary), l1 and l3, expanding fit by year, train subsample 1M
    L.append("== walk-forward (expanding fit, judge each year 2006-2026; secondary) ==")
    full = pd.concat([tr, te], ignore_index=True)
    for lab in ("l1", "l3"):
        parts = []
        for y in range(2006, 2027):
            trn = full[(full.date < f"{y}-01-01") & full[f"{lab}x"].notna()]; tst = full[(full.date >= f"{y}-01-01") & (full.date <= f"{y}-12-31")]
            if len(tst) < 5000:
                continue
            if len(trn) > 1_000_000:
                trn = trn.iloc[np.sort(rng.choice(len(trn), 1_000_000, replace=False))]
            m3 = fit_gbm(trn[feats].to_numpy(np.float32), trn[f"{lab}x"].to_numpy(), max_iter=200)
            parts.append(portfolio(tst, m3.predict(tst[feats].to_numpy(np.float32)), lab))
        s = pd.concat(parts)
        L += judge_entry(s, m, lab, f"walk-forward {lab} 2006-26")[0]
        s16 = s[s.index >= "2016-01-01"]
        L += judge_entry(s16, m, lab, f"walk-forward {lab} 2016-26 only")[0]
        print(f"  wf {lab} done {time.time()-t0:.0f}s", flush=True)
    L.append(f"\n({time.time()-t0:.0f}s)")
    txt = "\n".join(L) + "\n"
    (PROG / "seq_entry_out.txt").write_text(txt)
    print(txt, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all", choices=["build", "a", "b", "all"])
    a = ap.parse_args()
    if a.phase in ("build", "all"):
        build()
    if a.phase in ("a", "all"):
        phase_a()
    if a.phase in ("b", "all"):
        phase_b()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
