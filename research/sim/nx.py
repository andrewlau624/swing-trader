"""Study NX: the exact live night leg judged on survivorship-free 2003-15 Sharadar data.

Pre-registration: the "Study NX" amendment at the end of research/drafts/round1_prose.md
(registered in commit 5be14c7, FROZEN). This file is the frozen code for the single look.

  fetch     bulk-export SHARADAR/{SEP,TICKERS,ACTIONS,SFP} (NASDAQ_DATA_LINK_API_KEY) into
            data/research/nx/raw/ (resumable; prints counts only)
  validate  DAY-1 data checks; prints PASS/FAIL; exit 1 if a CRITICAL check fails. Computes NO
            night-rule return. Writes data/research/nx/validate_passed.json on success.
  run       the registered rule + pass bar -> data/research/program/nx_out.txt. Refuses without a
            passing validate, and refuses a second run unless --force (sentinel: timestamp + git hash).

Schema ASSUMPTIONS to confirm on day 1 (validate prints evidence for each):
  SEP/SFP : ticker,date,open,high,low,close,volume,closeunadj ; open/high/low/close/volume are
            SPLIT-adjusted (not dividend-adjusted), closeunadj is raw.  raw O/H/L = x * closeunadj/close.
  TICKERS : one row per (table, ticker); columns permaticker,ticker,name,exchange,isdelisted(Y/N),
            category,sector (or famasector),firstpricedate,lastpricedate,table. A reused ticker string
            is a DIFFERENT ticker string (vendor suffix) so (ticker,date) identifies one security.
  ACTIONS : date,action,ticker,value ; 'split' value = ratio ; 'dividend' value = cash/share ;
            delisting actions {delisted,bankruptcyliquidation,regulatorydelisting,voluntarydelisting}
            value = delisting price when present.
  SFP     : same bar columns as SEP (IWM expected here); closeunadj absent -> close is used.

Run: PYTHONPATH=. .venv/bin/python research/sim/nx.py fetch|validate|run [--force]
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import numpy as np
import pandas as pd

from research.sim import book
from swingtrader.daily import signals as sg

ROOT = pathlib.Path(__file__).resolve().parents[2]
TABLES = ("SEP", "TICKERS", "ACTIONS", "SFP")
INGEST_LO, INGEST_HI = pd.Timestamp("1997-06-01"), pd.Timestamp("2021-01-15")
JUDGE = (pd.Timestamp("2003-01-02"), pd.Timestamp("2015-12-31"))
REPORTED = {"1998-2002": (pd.Timestamp("1998-01-02"), pd.Timestamp("2002-12-31")),
            "2016-2020": (pd.Timestamp("2016-01-04"), pd.Timestamp("2020-12-30"))}
SUBPERIODS = {"2003-07": ("2003", "2007"), "2008-09": ("2008", "2009"), "2010-15": ("2010", "2015")}

# frozen live constants (config.yaml 2026-10-04)
DAY_RET_MAX, IBS_MAX, PRICE_MIN, PRICE_MAX = -0.08, 0.10, 5.0, 2000.0
ADV_MIN, VOL_MIN, CROWD_N, MAX_CORR = 1e7, 0.60, 30, 0.7
TILT_K, WEEKEND_SCALE, NAME_CAP = 0.25, 0.5, 0.10
NIGHT_W, S2_W, S2_CAP, S1_MULT, S1_THRESH = 0.5, 0.65, 0.15, 2.0, -0.02

DELIST_ACTIONS = {"delisted", "bankruptcyliquidation", "regulatorydelisting", "voluntarydelisting"}
END_ACTIONS = DELIST_ACTIONS | {"acquisitionof"}
LISTED = {"NYSE", "NASDAQ", "NYSEMKT", "NYSE MKT", "AMEX", "NYSEAMERICAN", "NYSE AMERICAN", "NYSEARCA", "BATS"}
PRIMARY_EXCH = {"NYSE", "NASDAQ", "NYSEMKT", "NYSE MKT", "AMEX", "NYSEAMERICAN", "NYSE AMERICAN"}
FUND_CATS = ("ETF", "ETN", "ETD", "ETMF", "CEF")


@dataclasses.dataclass(frozen=True)
class Spec:
    years: tuple = tuple(range(2003, 2016))
    cov_range: tuple = (4000, 9000)
    min_delist_cmp: int = 100
    named: tuple = (  # (regex on TICKERS.name, last-bar window lo, hi, critical)
        (r"LEHMAN BROTHERS HOLDINGS", "2008-09-01", "2009-03-31", True),
        (r"WASHINGTON MUTUAL", "2008-09-01", "2009-03-31", True),
        (r"BEAR STEARNS", "2008-03-01", "2008-12-31", True),
        (r"CIRCUIT CITY", "2008-11-01", "2010-01-31", True),
        (r"ENRON", None, None, False),
        (r"WORLDCOM", None, None, False))
    # (ticker, date, raw close, tolerance); AAPL 7:1 split effective 2014-06-09
    checkpoints: tuple = (("AAPL", "2014-06-06", 645.57, 0.01), ("AAPL", "2014-06-09", 93.70, 0.01))
    split_pair: tuple = ("AAPL", "2014-06-06", "2014-06-09", 7.0)       # f(d0)/f(d1) ~ 7
    volume_cp: tuple = ("AAPL", "2014-06-06", 5e6, 5e7)                 # raw volume band
    div_only: tuple = ("JNJ", "XOM")                                    # no splits since 2001: close == closeunadj
    lo: str = "2002-06-01"
    min_delist_share: float = 0.20
    independent: object = None                                          # {year: count} from --independent


SPEC = Spec()


@dataclasses.dataclass
class Paths:
    root: pathlib.Path = ROOT

    @property
    def nx(self): return self.root / "data/research/nx"
    @property
    def raw(self): return self.nx / "raw"
    @property
    def prog(self): return self.root / "data/research/program"
    @property
    def out(self): return self.prog / "nx_out.txt"
    @property
    def valid_sentinel(self): return self.nx / "validate_passed.json"
    @property
    def run_sentinel(self): return self.nx / "run_done.json"


# ------------------------------------------------------------------ NYSE calendar
def nyse_holidays(year: int) -> set:
    from dateutil.easter import easter
    D = dt.date

    def nth(m, wd, n):
        d = D(year, m, 1)
        d += dt.timedelta(days=(wd - d.weekday()) % 7 + 7 * (n - 1))
        return d

    def last(m, wd):
        d = D(year, m + 1, 1) - dt.timedelta(days=1) if m < 12 else D(year, 12, 31)
        return d - dt.timedelta(days=(d.weekday() - wd) % 7)

    def obs(d):  # weekend holiday observed Fri/Mon (Jan 1 on a Saturday is NOT observed)
        if d.weekday() == 5: return d - dt.timedelta(days=1)
        if d.weekday() == 6: return d + dt.timedelta(days=1)
        return d

    h = set()
    ny = D(year, 1, 1)
    if ny.weekday() != 5: h.add(obs(ny))
    h |= {nth(1, 0, 3), nth(2, 0, 3), easter(year) - dt.timedelta(days=2), last(5, 0),
          obs(D(year, 7, 4)), nth(9, 0, 1), nth(11, 3, 4), obs(D(year, 12, 25))}
    if year >= 2022: h.add(obs(D(year, 6, 19)))
    special = {D(2001, 9, 11), D(2001, 9, 12), D(2001, 9, 13), D(2001, 9, 14), D(2004, 6, 11),
               D(2007, 1, 2), D(2012, 10, 29), D(2012, 10, 30), D(2018, 12, 5), D(2025, 1, 9)}
    h |= {d for d in special if d.year == year}
    return {d for d in h if d.year == year}


def nyse_sessions(year: int) -> pd.DatetimeIndex:
    days = pd.bdate_range(f"{year}-01-01", f"{year}-12-31")
    hol = {pd.Timestamp(d) for d in nyse_holidays(year)}
    return pd.DatetimeIndex([d for d in days if d not in hol])


# ------------------------------------------------------------------ IO
STORE_NAMES = {"SEP": "stocks", "SFP": "funds", "TICKERS": "tickers", "ACTIONS": "actions"}


def store_dir() -> pathlib.Path:
    """The direct-API Sharadar store filled by the sharadar-data repo's `sharadar-download` (2026-10-06 clarification:
    the data was bought direct from sharadar.com, not via Nasdaq Data Link; same tables, same legacy schema)."""
    return pathlib.Path(os.environ.get("SHARADAR_DATA", pathlib.Path.home() / "data" / "sharadar")).expanduser()


def _files(P: Paths, name: str):
    raw = sorted(P.raw.glob(f"SHARADAR_{name}*.zip")) + sorted(P.raw.glob(f"SHARADAR_{name}*.csv"))
    st = store_dir() / f"{STORE_NAMES.get(name, name.lower())}.parquet"
    return raw or ([st] if st.exists() else [])


def _chunks(f: pathlib.Path, kw: dict):
    if f.suffix == ".parquet":
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(f)
        cols = [c for c in pf.schema_arrow.names if kw.get("usecols") is None or kw["usecols"](c)]
        for b in pf.iter_batches(batch_size=kw["chunksize"], columns=cols):
            yield b.to_pandas()
    else:
        yield from pd.read_csv(f, **kw)


def read_table(P: Paths, name: str, lo=INGEST_LO, hi=INGEST_HI) -> pd.DataFrame | None:
    """Raw export -> lower-case columns -> parquet cache (SEP/SFP filtered to [lo, hi])."""
    cache = P.nx / f"cache_{name}.parquet"
    files = _files(P, name)
    if cache.exists() and (not files or cache.stat().st_mtime >= max(f.stat().st_mtime for f in files)):
        return pd.read_parquet(cache)
    if not files:
        return None
    bars = name in ("SEP", "SFP")
    want = {"ticker", "date", "open", "high", "low", "close", "volume", "closeunadj"}
    parts = []
    for f in files:
        kw = dict(chunksize=2_000_000, low_memory=False)
        if bars:
            kw["usecols"] = lambda c: c.lower() in want
        for ch in _chunks(f, kw):
            ch.columns = [c.lower() for c in ch.columns]
            if "date" in ch:
                ch["date"] = pd.to_datetime(ch["date"])
                if bars:
                    ch = ch[(ch["date"] >= lo) & (ch["date"] <= hi)]
            if bars:
                if "closeunadj" not in ch: ch["closeunadj"] = ch["close"]
                ch = ch.astype({"open": "float32", "high": "float32", "low": "float32"}).astype(
                    {"close": "float64", "closeunadj": "float64", "volume": "float64"})
            parts.append(ch)
    df = pd.concat(parts, ignore_index=True)
    for c in ("firstpricedate", "lastpricedate"):
        if c in df: df[c] = pd.to_datetime(df[c], errors="coerce")
    if name == "TICKERS" and "table" in df:
        df["table"] = df["table"].astype(str).str.upper()
    P.nx.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df


def load_bars(P: Paths, lo, hi) -> pd.DataFrame:
    """SEP + SFP bars in [lo, hi], sorted by (ticker, date)."""
    parts = []
    for nm in ("SEP", "SFP"):
        t = read_table(P, nm)
        if t is not None and len(t):
            parts.append(t[(t["date"] >= pd.Timestamp(lo)) & (t["date"] <= pd.Timestamp(hi))])
    if not parts:
        raise SystemExit("no SEP bars found under " + str(P.raw))
    b = pd.concat(parts, ignore_index=True)
    return b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def load_master(P: Paths) -> pd.DataFrame:
    """One row per ticker string (SEP rows win over SFP), with flags."""
    t = read_table(P, "TICKERS")
    if t is None:
        raise SystemExit("TICKERS missing")
    if "table" in t:
        t = t[t["table"].isin(["SEP", "SFP"])].copy()
        t["_pri"] = (t["table"] != "SEP").astype(int)
        t = t.sort_values("_pri", kind="mergesort")
    else:
        t = t.copy(); t["table"] = "SEP"
    for c in ("category", "exchange", "name", "sector", "famasector", "isdelisted"):
        if c not in t: t[c] = ""
        t[c] = t[c].fillna("").astype(str)
    for c in ("firstpricedate", "lastpricedate"):
        if c not in t: t[c] = pd.NaT
    t["sector"] = np.where(t["sector"] != "", t["sector"], t["famasector"])
    t["delisted"] = t["isdelisted"].str.upper().str.startswith("Y")
    t["common"] = is_common(t["category"])
    t["fund"] = t["category"].str.upper().apply(lambda s: any(s.startswith(k) for k in FUND_CATS))
    t["exch"] = t["exchange"].str.upper()
    return t


def is_common(cat: pd.Series) -> pd.Series:
    u = cat.str.upper()
    return u.str.contains("COMMON STOCK") & ~u.str.contains("WARRANT|PREFERRED|UNIT")


def master_by_ticker(m: pd.DataFrame) -> pd.DataFrame:
    return m.drop_duplicates("ticker", keep="first").set_index("ticker")


# ------------------------------------------------------------------ panel features (causal, no outcomes)
def _roll_prior(x: np.ndarray, w: int) -> np.ndarray:
    """sum of x[i-w:i] (window ends at the PREVIOUS row). Caller masks rows with pos < w."""
    cs = np.r_[0.0, np.cumsum(x)]
    i = np.arange(len(x))
    return cs[i] - cs[np.maximum(i - w, 0)]


def build_panel(bars: pd.DataFrame) -> dict:
    """Column arrays for sorted bars. Everything on row i uses bars strictly before i except the
    day-i fields. pos = index of the bar within its ticker; prior-20 stats need pos >= 20."""
    n = len(bars)
    code = pd.factorize(bars["ticker"].astype(str))[0]
    newg = np.r_[True, code[1:] != code[:-1]]
    start = np.maximum.accumulate(np.where(newg, np.arange(n), 0))
    pos = np.arange(n) - start
    c = bars["close"].to_numpy(float); cu = bars["closeunadj"].to_numpy(float)
    o = bars["open"].to_numpy(float); h = bars["high"].to_numpy(float); l = bars["low"].to_numpy(float)
    v = bars["volume"].to_numpy(float)
    date = bars["date"].to_numpy("datetime64[ns]")
    sessions = np.unique(date)
    sidx = np.searchsorted(sessions, date)

    def prev(x):
        out = np.full(n, np.nan); out[1:] = x[:-1]; out[pos == 0] = np.nan; return out

    c_prev, cu_prev = prev(c), prev(cu)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.log(c / c_prev)
        f = cu / c
    ok = np.isfinite(lr)
    lr0 = np.where(ok, lr, 0.0)
    dv = np.nan_to_num(c * v)
    adv = np.where(pos >= 20, _roll_prior(dv, 20) / 20.0, np.nan)
    cnt = _roll_prior(ok.astype(float), 20)
    s1, s2 = _roll_prior(lr0, 20), _roll_prior(lr0 ** 2, 20)
    with np.errstate(divide="ignore", invalid="ignore"):
        var = (s2 - s1 ** 2 / cnt) / (cnt - 1)
    vol20 = np.where((pos >= 20) & (cnt >= 19), np.sqrt(np.maximum(var, 0)) * np.sqrt(252), np.nan)
    nxt_same = np.r_[(code[1:] == code[:-1]) & (sidx[1:] == sidx[:-1] + 1), False]
    o_next = np.full(n, np.nan); o_next[:-1] = o[1:]; o_next[~nxt_same] = np.nan
    c_next = np.full(n, np.nan); c_next[:-1] = c[1:]; c_next[~nxt_same] = np.nan
    return dict(n=n, code=code, tickers=bars["ticker"].astype(str).to_numpy(), pos=pos, start=start, c=c, cu=cu,
                o=o, h=h, l=l, v=v, f=f, date=date, sessions=sessions, sidx=sidx, c_prev=c_prev,
                cu_prev=cu_prev, lr=lr, adv=adv, vol20=vol20, has_next=nxt_same, o_next=o_next, c_next=c_next,
                ovn=o_next / c - 1.0)


def eligible_mask(pn: dict) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return (pn["pos"] >= 20) & (pn["cu_prev"] >= PRICE_MIN) & (pn["adv"] >= ADV_MIN)


def universe_mask(pn: dict, master: pd.DataFrame, which: str) -> np.ndarray:
    mt = master_by_ticker(master)
    uniq = pd.Series(pn["tickers"]).drop_duplicates().to_numpy()
    cat = mt["common"].reindex(uniq).fillna(False).astype(bool).to_numpy()
    exch = mt["exch"].reindex(uniq).fillna("").to_numpy()
    if which == "primary":
        ok = cat & np.isin(exch, list(PRIMARY_EXCH))
    else:
        ok = np.isin(exch, list(LISTED))
    lut = dict(zip(uniq, ok))
    # map per row through the factor codes (one lookup per ticker, not per row)
    first = np.unique(pn["code"], return_index=True)[1]
    by_code = np.array([lut.get(pn["tickers"][i], False) for i in first])
    return by_code[pn["code"]]


# ------------------------------------------------------------------ validate
def _res(label, ok, detail, critical=True):
    return dict(label=label, ok=ok, detail=detail, critical=critical)


def _session_pos(sessions, d):
    return np.searchsorted(sessions, np.asarray(d, dtype="datetime64[ns]"))


def validate(P: Paths, spec: Spec = SPEC) -> list:
    res = []
    master = load_master(P)
    mt = master_by_ticker(master)
    act = read_table(P, "ACTIONS")
    lo, hi = pd.Timestamp(spec.lo), pd.Timestamp(f"{max(spec.years)}-12-31")
    bars = load_bars(P, lo, hi)
    sep = bars[bars["ticker"].isin(master.loc[master["table"] == "SEP", "ticker"])]
    pn = build_panel(sep)
    sessions = pn["sessions"]

    # (1) permaticker uniqueness
    dup_master = int(master.duplicated(["table", "ticker"]).sum())
    dup_bars = int(sep.duplicated(["ticker", "date"]).sum())
    missing = sorted(set(sep["ticker"]) - set(mt.index))
    inrange = sep.merge(mt[["firstpricedate", "lastpricedate"]], left_on="ticker", right_index=True, how="left")
    bad = ((inrange["date"] < inrange["firstpricedate"]) | (inrange["date"] > inrange["lastpricedate"]
           + pd.Timedelta(days=7))).sum()
    frac_in = 1 - bad / max(len(sep), 1)
    perma_ok = ("permaticker" not in master) or (master.drop_duplicates("ticker")["permaticker"].is_unique)
    res.append(_res("1 permaticker uniqueness: (ticker,date) -> one security",
                    dup_master == 0 and dup_bars == 0 and not missing and frac_in >= 0.99 and perma_ok,
                    f"dup TICKERS rows {dup_master}, dup (ticker,date) {dup_bars}, SEP tickers absent from TICKERS "
                    f"{len(missing)}, bars inside [first,last]pricedate {frac_in:.4%}, one ticker per permaticker {perma_ok}"))

    # (2) delisted names
    d = master[(master["table"] == "SEP") & master["delisted"]]
    d_in = d[(d["lastpricedate"] >= lo) & (d["lastpricedate"] <= hi)]
    lastbar = sep.groupby("ticker")["date"].max()
    agree = total = 0
    if act is not None and len(act):
        ea = act[act["action"].str.lower().isin(END_ACTIONS)]
        ad = ea.groupby("ticker")["date"].max()
        for tk in d_in["ticker"]:
            if tk in lastbar.index and tk in ad.index:
                total += 1
                agree += abs(int(_session_pos(sessions, lastbar[tk])) - int(_session_pos(sessions, ad[tk]))) <= 5
    share = agree / total if total else float("nan")
    res.append(_res("2 delisted names: isdelisted=Y, lastpricedate, ACTIONS date vs last bar (<=5 sessions)",
                    len(d_in) > 0 and d_in["lastpricedate"].notna().all() and total >= spec.min_delist_cmp and share >= 0.95,
                    f"delisted rows {len(d)}, in window {len(d_in)}, compared with ACTIONS {total} (need >= {spec.min_delist_cmp}), "
                    f"agree within 5 sessions {share:.1%}"))

    # (3) named securities
    for pat, w_lo, w_hi, crit in spec.named:
        hit = master[master["name"].str.upper().str.contains(pat, regex=True) & (master["table"] == "SEP")]
        found = False; lines = []
        for _, r in hit.iterrows():
            b = sep[sep["ticker"] == r["ticker"]]
            if b.empty:
                continue
            last5 = ", ".join(f"{x:.2f}" for x in b["close"].tail(5))
            lines.append(f"{r['ticker']}({r['name'][:28]}) {b['date'].min().date()}..{b['date'].max().date()} last5 [{last5}]")
            if w_lo is None or (pd.Timestamp(w_lo) <= b["date"].max() <= pd.Timestamp(w_hi)):
                found = True
        if w_lo is None:   # pre-2003 names: presence anywhere in TICKERS/SEP is enough
            found = found or len(hit) > 0
        res.append(_res(f"3 named security /{pat}/ with bars through final weeks", found,
                        "; ".join(lines[:3]) or "not found by name in TICKERS (table SEP) or no bars in window", crit))

    # (4) raw-price reconstruction
    fch = pd.Series(pn["f"]).groupby(pn["code"]).pct_change().abs().to_numpy()
    big = (fch > 0.01) & (pn["c"] >= 1) & (pn["cu"] >= 1) & (pn["pos"] > 0)
    noise = (fch > 1e-3) & (fch <= 0.01) & (pn["c"] >= 5) & (pn["pos"] > 0)
    noise_share = noise.sum() / max((pn["pos"] > 0).sum(), 1)
    matched = 0
    if act is not None and len(act) and big.any():
        sp = act[act["action"].str.lower() == "split"]
        keys = set()
        for tk, dd in zip(sp["ticker"], sp["date"]):
            si = int(_session_pos(sessions, dd))
            keys |= {(tk, si + k) for k in (-1, 0, 1)}
        matched = sum((pn["tickers"][i], int(pn["sidx"][i])) in keys for i in np.flatnonzero(big))
    nbig = int(big.sum())
    res.append(_res("4a ratio closeunadj/close piecewise-constant; changes only on split actions",
                    noise_share < 1e-3 and (nbig == 0 or matched / nbig >= 0.99),
                    f"ratio changes >1%: {nbig}, within 1 session of a split action {matched / nbig if nbig else float('nan'):.2%} "
                    f"(need >= 99%), sub-1% jitter share {noise_share:.5%}"))
    cps = []; ok_cp = True
    for tk, ds, raw, tol in spec.checkpoints:
        b = sep[(sep["ticker"] == tk) & (sep["date"] == pd.Timestamp(ds))]
        if b.empty:
            ok_cp = False; cps.append(f"{tk} {ds} missing"); continue
        got = float(b["closeunadj"].iloc[0]); good = abs(got / raw - 1) <= tol
        ok_cp &= good; cps.append(f"{tk} {ds} raw {got:.2f} vs {raw} {'ok' if good else 'BAD'}")
    tk, d0, d1, ratio = spec.split_pair
    b0 = sep[(sep["ticker"] == tk) & (sep["date"] == pd.Timestamp(d0))]; b1 = sep[(sep["ticker"] == tk) & (sep["date"] == pd.Timestamp(d1))]
    if len(b0) and len(b1):
        r = float((b0.closeunadj.iloc[0] / b0.close.iloc[0]) / (b1.closeunadj.iloc[0] / b1.close.iloc[0]))
        ok_cp &= abs(r / ratio - 1) < 0.01; cps.append(f"{tk} factor ratio across split {r:.3f} vs {ratio}")
    else:
        ok_cp = False; cps.append(f"{tk} split pair missing")
    res.append(_res("4b hard-coded raw checkpoints (AAPL 2014-06-06 645.57, 2014-06-09 93.70)", ok_cp, "; ".join(cps)))
    dv_ok = True; dv_lines = []
    for tk in spec.div_only:
        b = sep[sep["ticker"] == tk]
        if b.empty: dv_lines.append(f"{tk} absent"); continue
        dev = float((b["close"] / b["closeunadj"] - 1).abs().max())
        dv_lines.append(f"{tk} max|close/closeunadj-1| {dev:.2e}"); dv_ok &= dev < 1e-3
    res.append(_res("4c dividend-only names: close == closeunadj (SEP close is split-, not dividend-adjusted)",
                    dv_ok and len(dv_lines) > 0 and not all("absent" in s for s in dv_lines), "; ".join(dv_lines)))

    # (5) volume reconstruction
    rv = pn["v"] / pn["f"]
    samp = (pn["c"] >= 5) & (pn["v"] >= 1e5)
    frac_int = float((np.abs(rv[samp] - np.round(rv[samp])) <= 1e-3 * rv[samp] + 1).mean()) if samp.any() else float("nan")
    tk, ds, vlo, vhi = spec.volume_cp
    b = pn["tickers"] == tk
    m5 = b & (pn["date"] == np.datetime64(ds))
    rvv = float(rv[m5][0]) if m5.any() else float("nan")
    res.append(_res("5 raw volume = volume*close/closeunadj: integer-ish; AAPL 2014-06-06 in tens of millions",
                    frac_int >= 0.98 and vlo <= rvv <= vhi,
                    f"integer-ish share {frac_int:.2%} (need >= 98%), {tk} {ds} raw volume {rvv:,.0f} (band {vlo:,.0f}-{vhi:,.0f})"))

    # (6) calendar
    yrs = [y for y in spec.years]
    allb = bars.assign(y=bars["date"].dt.year)
    hol_hits = 0; wrong = []
    for y in yrs:
        hol = {pd.Timestamp(x) for x in nyse_holidays(y)}
        dts = set(allb.loc[allb["y"] == y, "date"].unique())
        hol_hits += len(dts & hol)
        want = len(nyse_sessions(y))
        if len(dts) != want:
            wrong.append(f"{y}:{len(dts)}!={want}")
    res.append(_res("6 calendar: no bars on NYSE holidays; distinct dates/yr == NYSE sessions",
                    hol_hits == 0 and not wrong, f"holiday bars {hol_hits}; year mismatches {wrong or 'none'}"))

    # (7) classification
    cats = master.groupby(["category"]).size().sort_values(ascending=False)
    kinds = {"common": master["common"], "fund": master["fund"]}
    lines = []
    for y in yrs:
        yb = allb[allb["y"] == y]["ticker"].unique()
        mm = mt.reindex(yb)
        lines.append(f"{y}: common {int(mm['common'].fillna(False).sum())}, ETF/ETN/CEF {int(mm['fund'].fillna(False).sum())}, "
                     f"other {int(len(yb) - mm['common'].fillna(False).sum() - mm['fund'].fillna(False).sum())}")
    nocat = float((master["category"] == "").mean())
    res.append(_res("7 classification: category separates common stock from ETF/ETN/CEF",
                    kinds["common"].any() and kinds["fund"].any() and nocat < 0.01,
                    f"categories {len(cats)} (top: {', '.join(f'{k}={v}' for k, v in cats.head(6).items())}); blank {nocat:.2%}; "
                    f"exchanges: {', '.join(f'{k}={v}' for k, v in master['exch'].value_counts().head(8).items())}"))
    res.append(_res("7b per-year counts (securities with a bar)", True, " | ".join(lines), False))

    # (8) coverage + eligibility counts (data coverage, not an outcome)
    prim = universe_mask(pn, master, "primary")
    el = eligible_mask(pn) & prim
    comm = mt["common"].reindex(pn["tickers"]).fillna(False).to_numpy(bool)
    yr = pd.DatetimeIndex(pn["date"]).year.to_numpy()
    cov_lines = []; cov_ok = True; vend_ok = True; vend_lines = []
    elig_names = {}
    for y in yrs:
        my = yr == y
        ncom = len(set(pn["tickers"][my & comm]))
        nel = len(set(pn["tickers"][my & el]))
        elig_names[y] = set(pn["tickers"][my & el])
        daily = pd.Series(el[my]).groupby(pn["date"][my]).sum().mean() if my.any() else 0
        cov_ok &= spec.cov_range[0] <= ncom <= spec.cov_range[1]
        cov_lines.append(f"{y}: common {ncom}, eligible any-day {nel}, eligible/day {daily:.0f}")
        alive = master[(master["table"] == "SEP") & master["common"] & (master["firstpricedate"] <= pd.Timestamp(f"{y}-12-31"))
                       & (master["lastpricedate"].isna() | (master["lastpricedate"] >= pd.Timestamp(f"{y}-01-01")))]
        r = ncom / max(len(alive), 1)
        vend_ok &= abs(r - 1) <= 0.15; vend_lines.append(f"{y}:{r:.2f}")
    res.append(_res(f"8 coverage: common-stock permatickers with >=1 bar per year in {spec.cov_range[0]}-{spec.cov_range[1]}",
                    cov_ok, " | ".join(cov_lines)))
    res.append(_res("8b registered coverage gate (vendor's own active+delisted totals, +/-15%): SEP common with bars / TICKERS common alive",
                    vend_ok, "ratios " + " ".join(vend_lines)))
    if spec.independent:
        diffs = {y: elig_names_count / spec.independent[y] - 1 for y in yrs if y in spec.independent
                 for elig_names_count in [len(elig_names[y])]}
        ok = all(abs(v) <= 0.15 for v in diffs.values()) and len(diffs) == len(yrs)
        res.append(_res("8c registered coverage gate vs INDEPENDENT count (+/-15%)", ok,
                        " ".join(f"{y}:{v:+.0%}" for y, v in diffs.items())))
    else:
        res.append(_res("8c registered coverage gate vs INDEPENDENT count (+/-15%)", None,
                        "UNCHECKED: no --independent year,count file supplied; eligible counts printed in check 8. "
                        "Judge it by hand before reading the run output.", False))

    # (9) delisting-name share
    all_el = set().union(*elig_names.values()) if elig_names else set()
    ny_total = sum(len(s) for s in elig_names.values())
    ny_del = 0
    for y, s in elig_names.items():
        for tk in s:
            if tk in mt.index and bool(mt.at[tk, "delisted"]) and pd.notna(mt.at[tk, "lastpricedate"]) \
                    and mt.at[tk, "lastpricedate"].year == y:
                ny_del += 1
    names_del = sum(1 for tk in all_el if tk in mt.index and bool(mt.at[tk, "delisted"])
                    and pd.notna(mt.at[tk, "lastpricedate"]) and mt.at[tk, "lastpricedate"] <= hi)
    sh_names = names_del / max(len(all_el), 1)
    res.append(_res(f"9 delisting-name share (registered gate >= {spec.min_delist_share:.0%} of eligible names end in a delisting)",
                    sh_names >= spec.min_delist_share,
                    f"distinct eligible names {len(all_el)}, ending in a delisting by {hi.date()}: {sh_names:.1%} (GATED); "
                    f"per eligible-name-year: {ny_del}/{ny_total} = {ny_del / max(ny_total, 1):.1%} (annual-rate reading, reported)"))
    return res


def report_validate(res: list) -> tuple[str, bool]:
    lines = []; fail = False
    for r in res:
        tag = "INFO" if r["ok"] is None else ("PASS" if r["ok"] else ("FAIL" if r["critical"] else "WARN"))
        if r["ok"] is False and r["critical"]: fail = True
        lines.append(f"[{tag}] {r['label']}{'' if r['critical'] else ' (non-critical)'}\n        {r['detail']}")
    lines.append("\nVALIDATE: " + ("FAILED (critical)" if fail else "PASSED"))
    return "\n".join(lines), not fail


# ------------------------------------------------------------------ run
def git_state() -> str:
    h = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "research/sim/nx.py"], capture_output=True,
                                text=True, cwd=ROOT, check=True).stdout.strip())
    return h + ("+dirty-nx.py" if dirty else "")


def _sector_arrays(pn, master):
    mt = master_by_ticker(master)
    sec = mt["sector"].reindex(pn["tickers"]).fillna("").to_numpy()
    return sec


def collect_trades(pn: dict, master: pd.DataFrame, act: pd.DataFrame | None, which: str, lo, hi) -> dict:
    """Apply the registered rule to every session in [lo, hi]. Returns trades + nights + aux series."""
    mt = master_by_ticker(master)
    prim = universe_mask(pn, master, which)
    el = eligible_mask(pn) & prim
    sec = _sector_arrays(pn, master)
    date = pn["date"]
    inwin = (date >= np.datetime64(lo)) & (date <= np.datetime64(hi))
    nights = pd.DatetimeIndex(pn["sessions"])
    nights = nights[(nights >= lo) & (nights <= hi)]
    sess = pn["sessions"]

    # delisting prices / dividends
    dprice, divs = {}, {}
    if act is not None and len(act):
        a = act.copy(); a["action"] = a["action"].str.lower()
        for tk, g in a[a["action"].isin(DELIST_ACTIONS)].groupby("ticker"):
            g = g.sort_values("date"); v = pd.to_numeric(g["value"], errors="coerce")
            dprice[tk] = (g["date"].iloc[-1], float(v.iloc[-1]) if np.isfinite(v.iloc[-1]) and v.iloc[-1] > 0 else None)
        dv = a[a["action"] == "dividend"]
        for tk, d_, v in zip(dv["ticker"], dv["date"], pd.to_numeric(dv["value"], errors="coerce")):
            if np.isfinite(v): divs[(tk, np.datetime64(d_, "ns"))] = float(v)

    cand = np.flatnonzero(el & inwin & np.isfinite(pn["c_prev"]) & (pn["c"] / pn["c_prev"] - 1 <= DAY_RET_MAX))
    by_date: dict = {}
    for i in cand:
        by_date.setdefault(pn["date"][i], []).append(i)
    rows = []
    for dd, idx in sorted(by_date.items()):
        idx = np.array(idx)
        df = pd.DataFrame({"price": pn["cu"][idx], "prev_close": pn["c_prev"][idx] * pn["f"][idx],
                           "high": pn["h"][idx] * pn["f"][idx], "low": pn["l"][idx] * pn["f"][idx],
                           "vol20": pn["vol20"][idx], "adv": pn["adv"][idx], "row": idx},
                          index=pn["tickers"][idx])
        picks = sg.loser_picks(df, day_ret_max=DAY_RET_MAX, ibs_max=IBS_MAX, price_min=PRICE_MIN, price_max=PRICE_MAX)
        if picks.empty:
            continue
        rets = {}
        for tk, i in zip(picks.index, picks["row"].astype(int)):
            j0 = max(i - 20, pn["start"][i] + 1)
            rets[tk] = [float(x) if np.isfinite(x) else 0.0 for x in pn["lr"][j0:i]]
        picks, _ = sg.dedupe_correlated(picks, rets, MAX_CORR)
        kept, frac = sg.night_sizing(picks, vol_min=VOL_MIN, crowd_n=CROWD_N, max_name_pct=NAME_CAP)
        if kept.empty:
            continue
        si = int(np.searchsorted(sess, dd))
        nxt = pd.Timestamp(sess[si + 1]) if si + 1 < len(sess) else None
        if nxt is None:
            continue   # no next session in the data: no outcome (end of the dataset, not a delisting)
        gs = sg.gap_scale(pd.Timestamp(dd), nxt, WEEKEND_SCALE)
        w = sg.night_tilt(kept["vol20"].values, kept["day_ret"].values, TILT_K)
        x = frac * w * gs
        for k, (tk, r) in enumerate(kept.iterrows()):
            i = int(r["row"]); kind = "open"
            if pn["has_next"][i]:
                ret = pn["o_next"][i] / pn["c"][i] - 1.0
                dvd = divs.get((tk, np.datetime64(nxt, "ns")))
                if dvd and 0 < dvd / pn["cu"][i] < 0.25:
                    ret += dvd / pn["cu"][i]
            else:
                lastbar = mt.at[tk, "lastpricedate"] if tk in mt.index else pd.NaT
                gone = bool(mt.at[tk, "delisted"]) if tk in mt.index else False
                if pd.isna(lastbar):
                    lastbar = pd.Timestamp(pn["date"][pn["start"][i]:][pn["tickers"][pn["start"][i]:] == tk][-1])
                ended = gone and pd.Timestamp(lastbar) <= pd.Timestamp(dd)
                px = dprice.get(tk, (None, None))[1] if ended else None
                if ended and px is not None and 0 < px / pn["cu"][i] <= 5:
                    ret, kind = px / pn["cu"][i] - 1.0, "delist_price"
                elif ended:
                    ret, kind = -1.0, "delist_nopx"
                else:
                    ret, kind = -1.0, "nobar_halt"
            rows.append(dict(date=pd.Timestamp(dd), ticker=tk, x=float(x[k]), per=float(min(x[k], NAME_CAP)),
                             cu=float(r["price"]), adv=float(r["adv"]), vol20=float(r["vol20"]), day_ret=float(r["day_ret"]),
                             ret=float(ret), kind=kind, sector=sec[i], gap=float(gs), row=i))
    tr = pd.DataFrame(rows)

    # aux: equal-weight overnight of eligible names (proxy benchmark) and by sector
    m = el & inwin & np.isfinite(pn["ovn"])
    ovn = pd.Series(pn["ovn"][m], index=pd.DatetimeIndex(pn["date"][m]))
    proxy = ovn.groupby(level=0).mean().reindex(nights)
    secm = pd.DataFrame({"d": pn["date"][m], "s": sec[m], "r": pn["ovn"][m]}).groupby(["d", "s"])["r"].mean()
    # sector-adjustment lookup
    if len(tr):
        key = pd.MultiIndex.from_arrays([tr["date"].to_numpy("datetime64[ns]"), tr["sector"].to_numpy()])
        tr["sec_ovn"] = secm.reindex(key).to_numpy()
    return dict(trades=tr, nights=nights, proxy=proxy)


def iwm_overnight(P: Paths, lo, hi) -> pd.Series | None:
    """Close(t) -> open(next session) of IWM, split-adjusted basis, indexed by t."""
    for nm in ("SFP", "SEP"):
        t = read_table(P, nm)
        if t is None: continue
        b = t[(t["ticker"] == "IWM") & (t["date"] >= pd.Timestamp(lo) - pd.Timedelta(days=45))].sort_values("date")
        b = b[b["date"] <= pd.Timestamp(hi) + pd.Timedelta(days=10)]
        if len(b) > 20:
            s = pd.Series(b["open"].shift(-1).to_numpy(float) / b["close"].to_numpy(float) - 1, index=b["date"])
            vol = np.log(b["close"].astype(float)).diff().rolling(20).std().shift(1) * np.sqrt(252)
            vol.index = b["date"]
            return pd.DataFrame({"ovn": s, "rv": vol})
    return None


def cost_model(model: str, cu, adv):
    if model == "2x_tier_hi":
        return 2 * book.cost_bps("tier_hi", cu, adv)
    return book.cost_bps(model, cu, adv)


def tstat(x) -> float:
    x = np.asarray(x, float)
    if len(x) < 3 or x.std(ddof=1) == 0: return float("nan")
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def leg_series(tr: pd.DataFrame, nights, model: str, w_col="per") -> pd.Series:
    if tr.empty:
        return pd.Series(0.0, index=nights)
    c = cost_model(model, tr["cu"].to_numpy(), tr["adv"].to_numpy())
    net = tr["ret"].to_numpy() - 2 * c / 1e4
    return pd.Series(tr[w_col].to_numpy() * net).groupby(tr["date"].to_numpy()).sum().reindex(nights, fill_value=0.0)


def beta_adjust(L: pd.Series, bench: pd.Series):
    b = bench.reindex(L.index)
    ok = b.notna()
    if ok.sum() < 30 or b[ok].var() == 0:
        return float("nan"), float("nan"), float("nan")
    beta = float(np.cov(L[ok], b[ok])[0, 1] / b[ok].var())
    resid = L[ok] - beta * b[ok]
    return beta, float(resid.mean()), tstat(resid)


def judge_stats(tr, nights, model, bench) -> dict:
    L = leg_series(tr, nights, model)
    d = dict(model=model, n_nights=len(L), n_trade_nights=int((L != 0).sum()), n_trades=len(tr), L=L)
    d["mean"], d["t"] = float(L.mean()), tstat(L)
    d["mean_trade_nights"] = float(L[L != 0].mean()) if (L != 0).any() else float("nan")
    d["sub"] = {k: float(L[(L.index >= f"{a}-01-01") & (L.index <= f"{b}-12-31")].mean()) for k, (a, b) in SUBPERIODS.items()}
    if len(tr):
        c = cost_model(model, tr["cu"].to_numpy(), tr["adv"].to_numpy())
        net = tr["ret"].to_numpy() - 2 * c / 1e4
        d["med_trade"], d["hit_net"], d["hit_gross"] = float(np.median(net)), float((net > 0).mean()), float((tr["ret"] > 0).mean())
        d["trade_net"] = net
    else:
        d["med_trade"] = d["hit_net"] = d["hit_gross"] = float("nan"); d["trade_net"] = np.array([])
    d["ex5"] = float(L.drop(L.sort_values().index[-5:]).mean()) if len(L) > 5 else float("nan")
    d["beta"], d["adj_mean"], d["adj_t"] = beta_adjust(L, bench) if bench is not None else (float("nan"),) * 3
    return d


def verdict(d: dict) -> tuple[str, list]:
    """Mechanical PASS / WEAK / FAIL from the registered bar (primary universe, tier costs)."""
    sub_pos = sum(1 for v in d["sub"].values() if v > 0)
    checks = [("mean > 0 and t >= 2", d["mean"] > 0 and d["t"] >= 2),
              ("positive in >= 2 of 3 subperiods", sub_pos >= 2),
              ("per-trade median > 0", d["med_trade"] > 0),
              ("mean > 0 ex best 5 nights", d["ex5"] > 0),
              ("mean > 0 after beta x IWM", np.isfinite(d["adj_mean"]) and d["adj_mean"] > 0)]
    if not (d["mean"] > 0) or not (d["t"] >= 1):
        return "FAIL", checks
    return ("PASS" if all(ok for _, ok in checks) else "WEAK"), checks


def _bp(x): return f"{x * 1e4:8.2f}bp" if np.isfinite(x) else "     nan  "


def fmt_stats(d, label) -> list:
    return [f"{label}: nights {d['n_nights']} (with trades {d['n_trade_nights']}), trades {d['n_trades']}",
            f"  leg mean/night {_bp(d['mean'])}  night-clustered t {d['t']:.2f}   (trade-nights only {_bp(d['mean_trade_nights'])})",
            "  subperiods: " + "  ".join(f"{k} {_bp(v)}" for k, v in d["sub"].items()),
            f"  per-trade median {_bp(d['med_trade'])}  hit net {d['hit_net']:.1%} gross {d['hit_gross']:.1%}  ex-best-5 {_bp(d['ex5'])}",
            f"  beta vs bench {d['beta']:.3f}  beta-adjusted mean {_bp(d['adj_mean'])} (t {d['adj_t']:.2f})"]


def run_window_report(P, pn, master, act, which, lo, hi, bench_df, label, judged) -> tuple[list, dict]:
    col = collect_trades(pn, master, act, which, lo, hi)
    tr, nights = col["trades"], col["nights"]
    # benchmark: IWM overnight, else equal-weight eligible proxy
    if bench_df is not None:
        bench = bench_df["ovn"]; bname = "IWM close->open"
        rv = bench_df["rv"]
    else:
        bench = col["proxy"]; bname = "PROXY: equal-weight overnight of all eligible names (no IWM in SFP/SEP)"
        rv = None
    out = [f"== {label} | universe {which} | benchmark: {bname}" + ("" if judged else "   ** REPORTED ONLY, NOT JUDGED **")]
    kinds = tr["kind"].value_counts().to_dict() if len(tr) else {}
    out.append(f"  outcome kinds: {kinds}")
    st = {m: judge_stats(tr, nights, m, bench) for m in ("tier", "tier_hi", "2x_tier_hi")}
    out += fmt_stats(st["tier"], "TIER (5-15bp/side)")
    for m in ("tier_hi", "2x_tier_hi"):
        out.append(f"  stress {m}: mean {_bp(st[m]['mean'])} t {st[m]['t']:.2f}  subs " +
                   " ".join(f"{k} {_bp(v)}" for k, v in st[m]["sub"].items()))
    if len(tr):
        t = tr.assign(net=st["tier"]["trade_net"], yr=tr["date"].dt.year)
        out.append("  ADV buckets (per-trade net at tier):")
        edges = [1e7, 2.5e7, 5e7, 1e8, 2.5e8, np.inf]
        for a, b in zip(edges[:-1], edges[1:]):
            g = t[(t["adv"] >= a) & (t["adv"] < b)]
            if len(g): out.append(f"    ADV ${a / 1e6:.0f}M-{'inf' if b == np.inf else f'{b / 1e6:.0f}M'}: n {len(g)} mean {_bp(g['net'].mean())} median {_bp(g['net'].median())}")
        L = st["tier"]["L"]
        out.append("  per year (leg mean/night at tier | trades):")
        for y, g in L.groupby(L.index.year):
            out.append(f"    {y}: {_bp(g.mean())} | {int((t['yr'] == y).sum())}")
        # sector-adjusted residual (leg level)
        sa = t.dropna(subset=["sec_ovn"])
        if len(sa):
            res_ = pd.Series(sa["per"].to_numpy() * (sa["ret"].to_numpy() - sa["sec_ovn"].to_numpy())).groupby(sa["date"].to_numpy()).sum()
            res_ = res_.reindex(nights, fill_value=0.0)
            out.append(f"  sector-adjusted residual (gross, minus same-night same-sector eligible mean): mean {_bp(res_.mean())} t {tstat(res_):.2f}")
        else:
            out.append("  sector-adjusted residual: no sector data in TICKERS")
        # regime split
        if rv is not None:
            r = rv.reindex(nights); ok = r.notna()
            if ok.sum() > 90:
                q = r[ok].quantile([1 / 3, 2 / 3]).values
                L = st["tier"]["L"]
                parts = [("low", r <= q[0]), ("mid", (r > q[0]) & (r <= q[1])), ("high", r > q[1])]
                out.append("  vol regime (prior-20d realized vol of IWM, terciles of this window; VIX not in the bundle): " +
                           "  ".join(f"{n} {_bp(L[m.reindex(L.index).fillna(False)].mean())}" for n, m in parts))
        else:
            out.append("  vol regime: skipped (no IWM bars)")
    # sensitivity: literal -100% for gap-no-bar vs fill with nothing -> report count only
    if kinds.get("nobar_halt"):
        out.append(f"  NOTE: {kinds['nobar_halt']} picks had no next-session bar but later bars exist (halt/gap); scored -100% as registered.")
        if kinds["nobar_halt"] > 0.01 * len(tr):   # 2026-10-06 clarification: sensitivity line, verdict unchanged
            alt = leg_series(tr[tr["kind"] != "nobar_halt"], nights, "tier")
            out.append(f"  SENSITIVITY (not judged): tier-net leg mean with those picks left out {_bp(alt.mean())}")
    return out, dict(tr=tr, nights=nights, st=st, bench=bench)


def secondary(tr, nights) -> list:
    """NX-S1 / NX-S2 on the primary universe (leg-level; the IBS leg is not in this data -> increment is the night leg's
    contribution to equity: night_w * leg return)."""
    out = ["== SECONDARY (judged only because primary PASSED); night leg only, equity units (night_weight 0.5)"]
    base = leg_series(tr, nights, "tier") * NIGHT_W
    # S1: yesterday's equal-weight picks' net return <= -2% -> x2
    c = cost_model("tier", tr["cu"].to_numpy(), tr["adv"].to_numpy())
    ew = pd.Series(tr["ret"].to_numpy() - 2 * c / 1e4).groupby(tr["date"].to_numpy()).mean().reindex(nights)
    flag = (ew.shift(1) <= S1_THRESH)         # yesterday's outcome is known at tonight's decision
    mult = pd.Series(np.where(flag.fillna(False), S1_MULT, 1.0), index=nights)
    s1 = base * mult
    # S2: 1.3x with name cap .15 (leg weight 0.65 relative cap .15)
    t2 = tr.assign(per2=np.minimum(tr["x"], S2_CAP))
    s2 = leg_series(t2, nights, "tier", "per2") * S2_W

    def mdd(r):
        eq = (1 + r).cumprod(); return float((1 - eq / eq.cummax()).max())

    for name, s in (("NX-S1 losing-night x2", s1), ("NX-S2 moderate 1.3x cap .15", s2)):
        inc = s - base
        sub = {k: float(inc[(inc.index >= f"{a}-01-01") & (inc.index <= f"{b}-12-31")].mean()) for k, (a, b) in SUBPERIODS.items()}
        dd_b, dd_s = mdd(base), mdd(s)
        ok = inc.mean() > 0 and sum(v > 0 for v in sub.values()) >= 2 and dd_s <= 1.5 * dd_b
        out.append(f"  {name}: increment/night {_bp(inc.mean())} t {tstat(inc):.2f}; subs " +
                   " ".join(f"{k} {_bp(v)}" for k, v in sub.items()) +
                   f"; maxDD {dd_s:.1%} vs base {dd_b:.1%} (limit 1.5x) -> {'PASS' if ok else 'FAIL'}"
                   + (f"; S1 flagged nights {int(flag.sum())}" if name.startswith("NX-S1") else ""))
    return out


def run(P: Paths, force=False, spec: Spec = SPEC, judge=JUDGE, reported=None, universes=("primary", "secondary")) -> str:
    if not P.valid_sentinel.exists():
        raise SystemExit("REFUSED: run validate first (no validate_passed.json).")
    vs = json.loads(P.valid_sentinel.read_text())
    if not vs.get("ok"):
        raise SystemExit("REFUSED: last validate did not pass.")
    raws = [f for nm in TABLES for f in _files(P, nm)]
    if raws and max(f.stat().st_mtime for f in raws) > P.valid_sentinel.stat().st_mtime:
        raise SystemExit("REFUSED: raw data changed since validate; re-run validate.")
    if P.run_sentinel.exists() and not force:
        s = json.loads(P.run_sentinel.read_text())
        raise SystemExit(f"REFUSED: Study NX already run at {s['timestamp']} (code {s['git']}). A second look is a new study; --force to override.")
    reported = REPORTED if reported is None else reported
    master = load_master(P); act = read_table(P, "ACTIONS")
    out = [f"STUDY NX output | code {git_state()} | validate {vs['timestamp']} | run {dt.datetime.now().isoformat(timespec='seconds')}",
           "Rule: registered amendment (round1_prose.md, 5be14c7), daily-bar form; close stands in for 15:40.", ""]
    ctx = {}
    lo, hi = judge
    bars = load_bars(P, lo - pd.Timedelta(days=60), hi + pd.Timedelta(days=10))
    pn = build_panel(bars)
    bench_df = iwm_overnight(P, lo, hi)
    out.append("coverage gate vs independent count: " + ("checked by validate (8c)" if vs.get("independent") else "UNCHECKED (no independent series supplied)"))
    out.append("")
    for which in universes:
        lines, c = run_window_report(P, pn, master, act, which, lo, hi, bench_df, f"JUDGE {lo.date()}..{hi.date()}", True)
        out += lines + [""]
        ctx[which] = c
    prim = ctx["primary"]
    v, checks = verdict(prim["st"]["tier"])
    out.append("REGISTERED BAR (primary, tier, 2003-15):")
    out += [f"  [{'ok' if ok else 'NO'}] {n}" for n, ok in checks]
    out.append(f"  FAIL rule (mean <= 0 or t < 1): {'yes' if v == 'FAIL' else 'no'}")
    out.append(f"VERDICT: {v}")
    out.append("")
    if v == "PASS":
        out += secondary(prim["tr"], prim["nights"]) + [""]
    else:
        out += ["Secondary NX-S1/NX-S2 not computed (primary verdict is not PASS)."]
    del pn, bars
    for nm, (rlo, rhi) in reported.items():
        out.append(f"######## REPORTED ONLY, NOT JUDGED: {nm} ########")
        try:
            b2 = load_bars(P, rlo - pd.Timedelta(days=60), rhi + pd.Timedelta(days=10))
            if not (b2["date"].between(rlo, rhi)).any():
                out += ["  no bars in this window", ""]; continue
            p2 = build_panel(b2)
            bd = iwm_overnight(P, rlo, rhi)
            for which in universes:
                lines, _ = run_window_report(P, p2, master, act, which, rlo, rhi, bd, nm, False)
                out += lines + [""]
        except SystemExit:
            out += ["  no data", ""]
    text = "\n".join(out)
    P.prog.mkdir(parents=True, exist_ok=True)
    P.out.write_text(text)
    P.run_sentinel.write_text(json.dumps({"timestamp": dt.datetime.now().isoformat(timespec="seconds"), "git": git_state(),
                                          "verdict": v, "forced": bool(force)}))
    return text


# ------------------------------------------------------------------ fetch
def fetch(P: Paths, tables=TABLES, poll_s=20, max_wait_s=5400) -> None:
    import requests
    key = os.environ.get("NASDAQ_DATA_LINK_API_KEY")
    if not key:
        from swingtrader.config import load_dotenv
        load_dotenv(); key = os.environ.get("NASDAQ_DATA_LINK_API_KEY")
    if not key:
        raise SystemExit("set NASDAQ_DATA_LINK_API_KEY (env or .env)")
    P.raw.mkdir(parents=True, exist_ok=True)
    for tb in tables:
        final = P.raw / f"SHARADAR_{tb}.zip"; part = final.with_suffix(".zip.part")
        if final.exists():
            print(f"{tb}: already downloaded ({final.stat().st_size:,} bytes)"); continue
        url = f"https://data.nasdaq.com/api/v3/datatables/SHARADAR/{tb}.json"
        link = None; t0 = time.time()
        while time.time() - t0 < max_wait_s:
            try:
                r = requests.get(url, params={"qopts.export": "true", "api_key": key}, timeout=60)
            except requests.RequestException as e:
                print(f"{tb}: request error {type(e).__name__}"); time.sleep(poll_s); continue
            if r.status_code != 200:
                print(f"{tb}: HTTP {r.status_code} ({'optional, skipped' if tb == 'SFP' else 'fatal'})")
                if tb == "SFP": break
                raise SystemExit(1)
            f = (r.json().get("datatable_bulk_download") or {}).get("file") or {}
            if f.get("status") == "fresh" and f.get("link"):
                link = f["link"]; break
            print(f"{tb}: export status {f.get('status')}, waiting"); time.sleep(poll_s)
        if not link:
            print(f"{tb}: no export link"); continue
        have = part.stat().st_size if part.exists() else 0
        for attempt in range(5):
            try:
                have = part.stat().st_size if part.exists() else 0
                with requests.get(link, stream=True, timeout=120, headers={"Range": f"bytes={have}-"} if have else {}) as resp:
                    if resp.status_code not in (200, 206):
                        print(f"{tb}: download HTTP {resp.status_code}"); time.sleep(10); continue
                    mode = "ab" if resp.status_code == 206 else "wb"
                    with open(part, mode) as fh:
                        for ch in resp.iter_content(1 << 20):
                            fh.write(ch)
                part.rename(final); break
            except requests.RequestException as e:
                print(f"{tb}: download error {type(e).__name__}, retrying")
        if final.exists():
            print(f"{tb}: downloaded {final.stat().st_size:,} bytes")
    for tb in tables:
        d = read_table(P, tb)
        print(f"{tb}: {0 if d is None else len(d):,} rows")


# ------------------------------------------------------------------ cli
def main(argv=None, root=ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["fetch", "validate", "run"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--independent", help="CSV year,count of independently counted eligible names (registered coverage gate)")
    a = ap.parse_args(argv)
    P = Paths(pathlib.Path(root))
    if a.cmd == "fetch":
        fetch(P); return 0
    if a.cmd == "validate":
        spec = SPEC
        if a.independent:
            ind = pd.read_csv(a.independent); spec = dataclasses.replace(SPEC, independent=dict(zip(ind.iloc[:, 0].astype(int), ind.iloc[:, 1])))
        text, ok = report_validate(validate(P, spec))
        print(text)
        P.nx.mkdir(parents=True, exist_ok=True)
        if ok:
            P.valid_sentinel.write_text(json.dumps({"ok": True, "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
                                                    "git": git_state(), "independent": bool(spec.independent)}))
        else:
            P.valid_sentinel.unlink(missing_ok=True)
        return 0 if ok else 1
    print(run(P, force=a.force))
    return 0


if __name__ == "__main__":
    sys.exit(main())
