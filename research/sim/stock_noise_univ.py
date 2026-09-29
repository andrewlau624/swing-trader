"""stock_noise helper: the point-in-time liquid-stock universe (LOCKED run: loads the SIP panel).

    until mkdir $SCR/heavy.lock 2>/dev/null; do sleep 10; done; \
      PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise_univ; rmdir $SCR/heavy.lock

Rule (fixed ex ante, no tickers): on the first session of each month, rank every listed
COMMON STOCK by the median of close x volume over the 63 sessions that ended on the previous
session (point in time; SIP daily bars 2016-01..2020-09 from add. 28's sipd1520, then the
research panel). Common stock = in asset_meta.json on a US exchange, not an ETF/ETN/fund by
new_listings.etf_kind, not on ARCA, no fund-issuer / levered / FUND-ETF-ETN-LP word in the name,
and not a warrant / unit / right / preferred / note by name. One share class per company (the
more traded one; same symbol root or same issuer name). A symbol
that is not in asset_meta (delisted before the meta fetch) cannot be classified and is kept
only if its name is unknown AND it is not flagged by the same regexes (so delisted stocks stay
in; the survivorship check is reported). Duplicate histories (renamed tickers carried under
two symbols) are removed: identical closes on >= 90% of 63 shared sessions -> keep one.

Output: data/research/program/stock_noise_univ.pkl
  rank : DataFrame (month start, rank 1..200) -> symbol
  dv   : same shape, the median dollar volume
  meta : {symbol: (name, exchange, in_meta)}
"""
from __future__ import annotations

import glob
import pickle
import re

import numpy as np
import pandas as pd

from . import data as D
from . import new_listings as NL

SP = str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program"
OUT = f"{SP}/stock_noise_univ.pkl"
TOPK = 200
FUNDISH = re.compile(r"\b(FUND|ETF|ETN|TRUST SHARES|L\.?P\.?|PORTFOLIO)\b")
CUT = re.compile(r"\s+(CLASS\b|COMMON\b|CAPITAL STOCK|ORDINARY|AMERICAN DEPOSITARY|ADS\b|NEW YORK REGISTRY|SUBORDINATE).*$")


def company_key(sym: str, name: str) -> tuple[str, str]:
    """(symbol root, normalised issuer name): two share classes of one company share either."""
    nm = CUT.sub("", (name or "").upper())
    nm = re.sub(r"[.,]", " ", nm)
    nm = " ".join(t for t in nm.split() if t not in {"INC", "CORP", "CORPORATION", "CO", "LTD", "PLC", "THE"})
    return sym.split(".")[0], nm
NONCOMMON = re.compile(r"\b(WARRANT|WARRANTS|UNIT|UNITS|RIGHT|RIGHTS|PREFERRED|PFD|NOTES?|DEBENTURES?|"
                       r"DEPOSITARY SHARES? REPRESENTING|% )\b|\bWT\b")


def load_wide():
    old = pd.concat([pd.read_parquet(f, columns=["symbol", "timestamp", "close", "volume"])
                     for f in sorted(glob.glob(f"{NL.SIPD1520}/*.parquet"))])
    old["date"] = old.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    new = D.panel()
    c0 = new["close"].index.min()
    C0 = old.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").astype("float32")
    V0 = old.pivot_table(index="date", columns="symbol", values="volume", aggfunc="last").astype("float32")
    del old
    C0, V0 = C0[C0.index < c0], V0[V0.index < c0]
    C1, V1 = new["close"].astype("float32"), new["volume"].astype("float32")
    cols = sorted(set(C0.columns) | set(C1.columns))
    C = pd.concat([C0.reindex(columns=cols), C1.reindex(columns=cols)]).sort_index()
    V = pd.concat([V0.reindex(columns=cols), V1.reindex(columns=cols)]).sort_index()
    return C, V


def main():
    meta = NL.load_meta()
    C, V = load_wide()
    print("wide", C.shape, C.index.min().date(), C.index.max().date(), flush=True)
    DV = (C * V)
    # cheap prefilter: any 63d median >= $50M somewhere
    med = DV.rolling(63, min_periods=50).median()
    keep = med.max() >= 5e7
    med = med.loc[:, keep]
    Ck = C.loc[:, keep]
    print("prefilter symbols", int(keep.sum()), flush=True)

    def common(sym):
        m = meta.get(sym)
        if m is None:
            return True, "", "", False
        if m.get("exchange") not in NL.EXCH:
            return False, m.get("name", ""), m.get("exchange", ""), True
        if NL.etf_kind(sym, meta) is not None:
            return False, m.get("name", ""), m.get("exchange", ""), True
        nm = (m.get("name") or "").upper()
        if (NONCOMMON.search(nm) or m.get("exchange") == "ARCA" or re.search(NL.ISSUER, nm)
                or NL.LEV_RE.search(nm) or FUNDISH.search(nm)):
            return False, nm, m.get("exchange", ""), True
        return True, nm, m.get("exchange", ""), True

    info = {s: common(s) for s in med.columns}
    ok = [s for s in med.columns if info[s][0]]
    med = med[ok]
    print("common-stock candidates", len(ok), " not in meta:", sum(not info[s][3] for s in ok), flush=True)
    days = med.index
    firsts = pd.Series(days, index=days).groupby([days.year, days.month]).first().values
    rank, dvs = {}, {}
    for d in firsts:
        i = days.get_loc(d)
        if i < 63:
            continue
        row = med.iloc[i - 1].dropna().sort_values(ascending=False)
        # duplicate histories: identical closes over the window
        top, keys = [], set()
        win = Ck.iloc[i - 63:i]
        for s in row.index:
            kr, kn = company_key(s, info[s][1])
            if kr in keys or (kn and kn in keys):
                continue                                   # a second share class of a listed company
            dup = False
            for t in top:
                a, b = win[s].values, win[t].values
                both = np.isfinite(a) & np.isfinite(b)
                if both.sum() >= 30 and (np.abs(a[both] - b[both]) <= 1e-4 * np.abs(b[both])).mean() >= 0.9:
                    dup = True; break
            if not dup:
                top.append(s); keys.add(kr)
                if kn:
                    keys.add(kn)
            if len(top) >= TOPK:
                break
        rank[pd.Timestamp(d)] = top
        dvs[pd.Timestamp(d)] = row.reindex(top).values
    R = pd.DataFrame.from_dict(rank, orient="index", columns=range(1, TOPK + 1))
    DVm = pd.DataFrame.from_dict(dvs, orient="index", columns=range(1, TOPK + 1))
    syms = sorted(set(R.values.ravel()) - {None})
    out = dict(rank=R, dv=DVm, meta={s: info[s][1:] for s in syms},
               close=C.reindex(columns=syms), volume=V.reindex(columns=syms))
    pickle.dump(out, open(OUT, "wb"), protocol=4)
    for n in (5, 10, 20, 50):
        u = sorted(set(R.loc[:, 1:n].values.ravel()))
        print(f"top{n}: {len(u)} distinct symbols", flush=True)
    print("not-in-meta in top 50 ever:", sorted({s for s in R.loc[:, 1:50].values.ravel() if not info[s][3]}))
    print("written", OUT, R.index.min().date(), R.index.max().date())


if __name__ == "__main__":
    main()
