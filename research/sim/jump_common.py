"""Shared helpers for the jump hunt's event builders (research/sim/jump_<name>.py).

`fd_of(ts)`: the ET date to file a timestamped signal under, so jump_runner buys the first open AFTER it is public:
a signal before 09:30 ET is traded at that day's open (fd = previous calendar day), anything later at the next
session's open (fd = that day). `stock_symbols()`: Alpaca assets on NASDAQ / NYSE / AMEX that don't look like funds.
`save(events, name)`: writes data/research/program/events_jump_<name>.parquet (sym, fd) and prints counts by year.
"""
from __future__ import annotations

import json
import pathlib
import re

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
FUNDISH = re.compile(r"\b(ETF|ETN|FUND|TRUST|PROSHARES|DIREXION|ISHARES|SPDR|INVESCO|VANECK|GLOBAL X|WISDOMTREE|"
                     r"ACQUISITION|ACQ|CAPITAL CORP|WARRANT|RIGHTS?|UNITS?|PREFERRED|NOTES?|DEPOSITARY SHARES? REP)\b", re.I)


def fd_of(ts) -> pd.Series:
    t = pd.to_datetime(ts, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return (t - pd.Timedelta(hours=9, minutes=30)).dt.normalize()


def stock_symbols(otc: bool = True) -> set[str]:
    """Alpaca assets (incl. inactive) that don't look like funds. `otc` keeps symbols Alpaca now lists as OTC: names
    delisted to OTC keep their ticker, so dropping them would drop failed companies' listed years (survivorship)."""
    m = json.load(open(ROOT / "data/research/night/asset_meta.json"))
    ex = ("NASDAQ", "NYSE", "AMEX") + (("OTC",) if otc else ())
    return {s for s, v in m.items() if v.get("exchange") in ex
            and not FUNDISH.search(v.get("name") or "") and re.fullmatch(r"[A-Z]{1,5}", s)}


def first_in(E: pd.DataFrame, gap_days: int) -> pd.DataFrame:
    """Keep an event only if the same symbol had no event in the previous `gap_days` calendar days."""
    E = E.sort_values(["sym", "fd"])
    prev = E.groupby("sym").fd.shift(1)
    return E[prev.isna() | ((E.fd - prev).dt.days > gap_days)]


def _norm(s) -> str:
    s = re.sub(r"\(.*?\)", " ", str(s).upper())
    s = re.sub(r"[^A-Z0-9 ]", " ", s.replace("/DE", " ").replace("/NV", " "))
    s = re.sub(r"\b(INC|CORP|CORPORATION|CO|LTD|LIMITED|PLC|HOLDINGS?|GROUP|COMMON STOCK|CLASS [A-C]|ORDINARY SHARES|"
               r"N ?V|S ?A|LLC|LP|THE|CIK \d+)\b", " ", s)
    return " ".join(s.split())


def resolve(E: pd.DataFrame) -> pd.DataFrame:
    """Add `sym` to rows with `cik` and `name` (EDGAR display or conformed name): the tickers printed in an FTS display
    name, else EDGAR's current tickers for the CIK, else an exact normalized-name match to an Alpaca asset (Alpaca
    keeps inactive symbols, so delisted companies are kept). Rows with no 1-5 letter ticker are dropped."""
    from . import event_fetch as F
    ct = F.company_tickers()
    alp = json.load(open(ROOT / "data/research/events/alpaca_asset_names.json"))
    by_name: dict[str, str] = {}
    for sym, nm in alp.items():
        if re.fullmatch(r"[A-Z]{1,5}", sym):
            by_name.setdefault(_norm(nm), sym)
    out = []
    for r in E.itertuples():
        cand = F.ticker_of(r.name) + ct.get(str(int(r.cik)), [])
        cand = [t for t in cand if re.fullmatch(r"[A-Z]{1,5}", t)]
        s = cand[0] if cand else by_name.get(_norm(r.name))
        out.append(s)
    E = E.assign(sym=out)
    return E[E.sym.notna()]


def small_only(E: pd.DataFrame, max_adv: float) -> pd.DataFrame:
    """Keep events whose 20-session ADV$ (raw bars, sessions before the trade) is below max_adv."""
    from . import event_fetch as F
    bars = F.raw_bars(sorted(E.sym.unique()))
    keep = []
    for r in E.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            keep.append(False); continue
        b = b[pd.to_datetime(b.index) <= r.fd].tail(20)
        keep.append(len(b) >= 15 and float((b.close * b.volume).mean()) < max_adv)
    return E[keep]


def cik_sym() -> dict[str, str]:
    """CIK -> ticker: EDGAR's current tickers, else any name the CIK filed under in form.idx 2016-2026 matched exactly
    (normalized) to an Alpaca asset name (incl. inactive). Cached."""
    f = ROOT / "data/research/jump/cik_sym.json"
    if f.exists():
        return json.load(open(f))
    from . import event_fetch as F
    alp = json.load(open(ROOT / "data/research/events/alpaca_asset_names.json"))
    by_name: dict[str, str] = {}
    for sym, nm in alp.items():
        if re.fullmatch(r"[A-Z]{1,5}", sym):
            by_name.setdefault(_norm(nm), sym)
    out = {c: [t for t in ts if re.fullmatch(r"[A-Z]{1,5}", t)][0] for c, ts in F.company_tickers().items()
           if any(re.fullmatch(r"[A-Z]{1,5}", t) for t in ts)}
    I = pd.concat([F.full_index(y, q) for y in range(2016, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)])
    I = I[I.form.isin(["10-K", "10-Q", "8-K", "10-K405", "20-F", "S-1", "DEF 14A"])].drop_duplicates(["cik", "company"])
    for cik, nm in zip(I.cik.astype(str), I.company):
        if cik not in out:
            s = by_name.get(_norm(nm))
            if s:
                out[cik] = s
    json.dump(out, open(f, "w"))
    return out


def shares_hist() -> pd.DataFrame:
    """(sym, end, shares): dei EntityCommonStockSharesOutstanding from XBRL frames CY2014Q1I..CY2026Q3I (cover-page
    counts; `end` = the cover date, about the filing date). Cached."""
    f = ROOT / "data/research/jump/shares_hist.parquet"
    if f.exists():
        return pd.read_parquet(f)
    from .tender_fetch import get
    cs = cik_sym()
    rows = []
    for q in pd.period_range("2014Q1", "2026Q3", freq="Q"):
        j = get(f"https://data.sec.gov/api/xbrl/frames/dei/EntityCommonStockSharesOutstanding/shares/CY{q.year}Q{q.quarter}I.json") or {}
        for x in j.get("data", []):
            s = cs.get(str(x["cik"]))
            if s:
                rows.append((s, pd.Timestamp(x["end"]), float(x["val"])))
    D = pd.DataFrame(rows, columns=["sym", "end", "shares"]).sort_values(["sym", "end"])
    D.to_parquet(f)
    return D


def save(E: pd.DataFrame, name: str) -> pathlib.Path:
    E = E[["sym", "fd"]].drop_duplicates().sort_values("fd").reset_index(drop=True)
    f = PROG / f"events_jump_{name}.parquet"
    f.parent.mkdir(parents=True, exist_ok=True)
    E.to_parquet(f)
    print(f"{name}: {len(E)} events, {E.sym.nunique()} symbols; by year:",
          E.fd.dt.year.value_counts().sort_index().to_dict())
    return f
