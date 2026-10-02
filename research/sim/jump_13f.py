"""Jump hunt R3-6: 13F discovery — >= 3 different institutions open a NEW position in the same thinly held stock in
one reporting period.

SEC Form 13F data sets (2013Q2..2026-08): original 13F-HR filings only (no amendments). A filer's position in CUSIP c
at period P is NEW if the filer also filed for the previous period and did not hold c then. A (c, P) event needs
>= 3 new holders and <= 30 holders of c at the previous period (thinly held = small); fd = the FILING date of the third
new holder's 13F (public then). CUSIP -> symbol: the most common symbol for that CUSIP in the SEC fails-to-deliver
files (jump_ftd). ADV$ < $20M; first per ticker in 120 days.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_13f fetch
    PYTHONPATH=. .venv/bin/python -m research.sim.jump_13f
"""
from __future__ import annotations

import re
import sys
import zipfile

import pandas as pd
import requests

from .jump_common import ROOT, first_in, save, small_only

D = ROOT / "data/research/jump/13f"


def fetch():
    from swingtrader.daily.news_judge import sec_headers
    H = sec_headers()
    D.mkdir(parents=True, exist_ok=True)
    page = requests.get("https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets", headers=H, timeout=60).text
    for link in sorted(set(re.findall(r'href="([^"]+form13f\.zip)"', page))):
        out = D / (link.split("/")[-1].replace(".zip", ".parquet"))
        if out.exists():
            continue
        zf = D / "tmp.zip"
        with requests.get("https://www.sec.gov" + link, headers=H, timeout=600, stream=True) as r:
            with open(zf, "wb") as f:
                for ch in r.iter_content(1 << 20):
                    f.write(ch)
        Z = zipfile.ZipFile(zf)
        nm = {n.split("/")[-1].upper(): n for n in Z.namelist()}
        S = pd.read_csv(Z.open(nm["SUBMISSION.TSV"]), sep="\t", dtype=str, usecols=["ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "CIK", "PERIODOFREPORT"])
        S = S[S.SUBMISSIONTYPE == "13F-HR"]
        I = pd.read_csv(Z.open(nm["INFOTABLE.TSV"]), sep="\t", dtype=str, usecols=["ACCESSION_NUMBER", "CUSIP"], on_bad_lines="skip")
        X = I.merge(S, on="ACCESSION_NUMBER").drop_duplicates(["CIK", "PERIODOFREPORT", "CUSIP"])
        X = pd.DataFrame(dict(cik=X.CIK, period=pd.to_datetime(X.PERIODOFREPORT, format="%d-%b-%Y", errors="coerce"),
                              filed=pd.to_datetime(X.FILING_DATE, format="%d-%b-%Y", errors="coerce"), cusip=X.CUSIP.str.upper().str[:9]))
        X.dropna().to_parquet(out)
        print(out.name, len(X), flush=True)
    (D / "tmp.zip").unlink(missing_ok=True)


def build() -> pd.DataFrame:
    """Streamed: per file keep only (cusip, period) cells with <= 80 holders (the rule needs <= 30 at P-1 and new ones
    at P, so busier cells can't qualify), plus every (cik, period) that filed at all."""
    keep, filed, counts = [], [], []
    for f in sorted(D.glob("*.parquet")):
        X = pd.read_parquet(f)
        filed.append(X[["cik", "period"]].drop_duplicates())
        counts.append(X.groupby(["cusip", "period"]).cik.nunique())
        n = X.groupby(["cusip", "period"]).cik.transform("nunique")
        keep.append(X[n <= 80])
    X = pd.concat(keep, ignore_index=True).sort_values("filed").drop_duplicates(["cik", "period", "cusip"])
    filed_for = pd.concat(filed).drop_duplicates()
    periods = sorted(filed_for.period.unique())
    prevp = dict(zip(periods[1:], periods[:-1]))
    X["prev_period"] = X.period.map(prevp)
    nh = pd.concat(counts).groupby(level=[0, 1]).sum().rename("n_prev").reset_index().rename(columns={"period": "prev_period"})
    X = X.merge(filed_for.rename(columns={"period": "prev_period"}).assign(filed_prev=True), on=["cik", "prev_period"], how="left")
    X = X[X.filed_prev.fillna(False).astype(bool)]
    held = X[["cik", "period", "cusip"]].rename(columns={"period": "prev_period"}).assign(held=True)
    X = X.merge(held, on=["cik", "prev_period", "cusip"], how="left")
    new = X[X.held.isna()].merge(nh, on=["cusip", "prev_period"], how="left")
    new = new[new.n_prev.fillna(0) <= 30]          # a cusip absent at P-1 had 0 holders there (all rows counted)
    rows = []
    for (u, p), g in new.groupby(["cusip", "period"]):
        if len(g) >= 3:
            rows.append(dict(cusip=u, fd=g.filed.sort_values().iat[2]))
    E = pd.DataFrame(rows)
    from .jump_ftd import D as FD
    M = pd.concat([pd.read_parquet(f, columns=["cusip", "sym"]) for f in sorted(FD.glob("*.parquet"))], ignore_index=True)
    cmap = M.groupby("cusip").sym.agg(lambda x: x.value_counts().index[0])
    E["sym"] = E.cusip.map(cmap)
    E = first_in(E.dropna(subset=["sym"])[["sym", "fd"]], 120)
    return small_only(E[E.fd >= "2016-01-01"], 20e6)

if __name__ == "__main__":
    if sys.argv[1:] == ["fetch"]:
        fetch()
    else:
        save(build(), "r3_6")
