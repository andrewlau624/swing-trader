"""Jump hunt insider ideas: D8 (first officer/director open-market buy in 2 years, no Benzinga story in the prior 60
days) and C6 (any officer/director buy with no story in the prior 90 days).

Form 4 open-market purchases (code P, acquired) from SEC's insider-transaction data sets, 2014Q1..2026 (2014-19 zips
in data/research/jump/insider, 2020+ in data/research/night/insider; same parsing as outside_box.insider_buys, which
is left untouched). A Form 4 is public on its filing date (often after the close): fd = filing date.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_insider d8|c6
"""
from __future__ import annotations

import glob
import sys
import zipfile

import pandas as pd

from .jump_common import ROOT, first_in, save, small_only

OUTF = ROOT / "data/research/jump/insider_buys_2014_2026.parquet"


def buys() -> pd.DataFrame:
    if OUTF.exists():
        return pd.read_parquet(OUTF)
    rows = []
    zs = sorted(glob.glob(str(ROOT / "data/research/jump/insider/*_form345.zip"))) + \
        sorted(glob.glob(str(ROOT / "data/research/night/insider/*_form345.zip")))
    for z in zs:
        Z = zipfile.ZipFile(z)
        rd = lambda n: pd.read_csv(Z.open(n), sep="\t", dtype=str, low_memory=False, on_bad_lines="skip")
        S = rd("SUBMISSION.tsv")[["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL", "DOCUMENT_TYPE"]]
        N = rd("NONDERIV_TRANS.tsv")[["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_ACQUIRED_DISP_CD", "TRANS_SHARES", "TRANS_PRICEPERSHARE"]]
        R = rd("REPORTINGOWNER.tsv")[["ACCESSION_NUMBER", "RPTOWNER_RELATIONSHIP"]]
        N = N[(N.TRANS_CODE == "P") & (N.TRANS_ACQUIRED_DISP_CD == "A")].copy()
        N["usd"] = pd.to_numeric(N.TRANS_SHARES, errors="coerce") * pd.to_numeric(N.TRANS_PRICEPERSHARE, errors="coerce")
        g = N.groupby("ACCESSION_NUMBER").usd.sum().rename("usd").reset_index()
        rel = R.groupby("ACCESSION_NUMBER").RPTOWNER_RELATIONSHIP.agg(lambda x: " ".join(map(str, x))).rename("rel").reset_index()
        g = g.merge(S, on="ACCESSION_NUMBER").merge(rel, on="ACCESSION_NUMBER", how="left")
        rows.append(g[g.DOCUMENT_TYPE.isin(["4", "4/A"])])
        print(z.split("/")[-1], len(rows[-1]), flush=True)
    X = pd.concat(rows)
    X["fd"] = pd.to_datetime(X.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    X["sym"] = X.ISSUERTRADINGSYMBOL.str.upper().str.strip().str.replace("-", ".", regex=False)
    X["insider"] = X.rel.fillna("").str.contains("Director|Officer", case=False)
    X = X.dropna(subset=["fd", "usd"])[["fd", "sym", "usd", "insider", "ACCESSION_NUMBER"]].drop_duplicates("ACCESSION_NUMBER")
    X.to_parquet(OUTF)
    return X


def _no_news(E: pd.DataFrame, days: int) -> pd.DataFrame:
    from .jump_news import news
    L = news()[["sym", "fd"]].drop_duplicates()
    last = {}
    for s, g in L.groupby("sym"):
        last[s] = g.fd.sort_values().to_numpy()
    keep = []
    for r in E.itertuples():
        a = last.get(r.sym)
        if a is None:
            keep.append(True); continue
        lo, hi = (r.fd - pd.Timedelta(days=days)).to_datetime64(), r.fd.to_datetime64()
        keep.append(not ((a >= lo) & (a <= hi)).any())
    return E[keep]


def d8() -> pd.DataFrame:
    X = buys()
    X = X[X.insider & (X.usd >= 1e3)]
    E = first_in(X[["sym", "fd"]], 730)
    E = E[E.fd >= "2016-01-01"]
    return small_only(_no_news(E, 60), 1e12)


def c6() -> pd.DataFrame:
    X = buys()
    X = X[X.insider & (X.usd >= 1e3)]
    E = first_in(X[["sym", "fd"]], 30)
    E = E[E.fd >= "2016-04-01"]
    return small_only(_no_news(E, 90), 1e12)


def _adv_ret(E: pd.DataFrame, n: int) -> pd.DataFrame:
    """Attach 20-session ADV$ and the n-session return to fd (raw bars, sessions on/before fd)."""
    from . import event_fetch as F
    bars = F.raw_bars(sorted(E.sym.unique()))
    adv, ret = [], []
    for r in E.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            adv.append(float("nan")); ret.append(float("nan")); continue
        b = b[pd.to_datetime(b.index) <= r.fd]
        adv.append(float((b.close * b.volume).tail(20).mean()) if len(b) >= 15 else float("nan"))
        ret.append(float(b.close.iat[-1] / b.close.iat[-1 - n] - 1) if len(b) > n else float("nan"))
    return E.assign(adv=adv, ret=ret)


def r2_4() -> pd.DataFrame:
    """Officer/director open-market buy >= $100k that is >= 20% of the 20-day ADV$, with ADV$ < $5M."""
    X = buys()
    X = X[X.insider & (X.usd >= 1e5) & (X.fd >= "2016-01-01")]
    X = X.groupby(["sym", "fd"]).usd.sum().reset_index()
    X = _adv_ret(X, 1)
    X = X[(X.adv < 5e6) & (X.usd >= 0.2 * X.adv)]
    return first_in(X[["sym", "fd"]], 30)


def r2_5() -> pd.DataFrame:
    """Officer/director open-market buy (>= $1k) while the stock is down >= 30% over the prior 60 sessions."""
    X = buys()
    X = X[X.insider & (X.usd >= 1e3) & (X.fd >= "2016-01-01")].dropna(subset=["sym"])
    X = first_in(X[["sym", "fd"]].drop_duplicates(), 30)
    X = _adv_ret(X, 60)
    return X[X.ret <= -0.30][["sym", "fd"]]


def r2_17() -> pd.DataFrame:
    """Officer/director open-market buy (>= $1k; first per stock in 30 days) while the latest PUBLISHED FINRA
    days-to-cover (settlement + 12 days <= fd) is >= 5."""
    from .jump_reddit import _last_si
    X = buys()
    X = X[X.insider & (X.usd >= 1e3) & (X.fd >= "2020-07-01")].dropna(subset=["sym"])
    E = first_in(X[["sym", "fd"]].drop_duplicates(), 30)
    E = _last_si(E)
    return small_only(E[E.dtc >= 5][["sym", "fd"]], 1e12)


if __name__ == "__main__":
    what = sys.argv[1]
    save(globals()[what](), what)
