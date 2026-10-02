"""Round 32 family A (pre-registered in round1_prose.md, commit cf5d8cf): the session after a filing, ID3's frame.

A1: Schedule 13D originals (EDGAR quarterly full index, subject company from each header).
A2: Form 4 code-P purchases by 10% owners with no director/officer among the reporting owners (SEC Form 345 sets).
Buy the opening cross, sell the closing cross of the first session after the filing date; evaluated by
`insider_day.run` (the registered ID machinery). Program N 757.

    PYTHONPATH=. .venv/bin/python -m research.sim.filing_day fetch|run
"""
from __future__ import annotations

import glob
import pathlib
import sys
import zipfile

import numpy as np
import pandas as pd

from . import event_fetch as F
from . import insider_day as I
from .outside_box import NIGHT

ROOT = pathlib.Path(__file__).resolve().parents[2]
N_PROG = 757
QTRS = [(y, q) for y in range(2020, 2027) for q in range(1, 5) if (2020, 3) <= (y, q) <= (2026, 3)]
VAR = {"A1 13D": "a1", "A2 10%-owner buys": "a2"}


def a1_filings() -> pd.DataFrame:
    D = pd.concat([F.full_index(y, q) for y, q in QTRS])
    D = D[D.form.isin(["SC 13D", "SCHEDULE 13D"])].drop_duplicates("path")
    D["adsh"] = D.path.str.extract(r"(\d{10}-\d{2}-\d{6})")
    return D


def a1_events() -> pd.DataFrame:
    D = a1_filings()
    tk = F.company_tickers()
    rows = []
    for r in D.itertuples():
        h = F.hdr(r.cik, r.adsh)
        s = h.get("subject")
        for t in tk.get(s or "", [])[:1]:
            rows.append((pd.Timestamp(r.date), t))
    X = pd.DataFrame(rows, columns=["fd", "sym"]).drop_duplicates()
    print(f"A1: {len(D)} 13D originals, {len(X)} mapped to a current ticker", flush=True)
    return X


def a2_events() -> pd.DataFrame:
    rows = []
    for z in sorted(glob.glob(str(NIGHT / "insider/*_form345.zip"))):
        Z = zipfile.ZipFile(z)
        rd = lambda n: pd.read_csv(Z.open(n), sep="\t", dtype=str, low_memory=False, on_bad_lines="skip")
        S = rd("SUBMISSION.tsv")[["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL", "DOCUMENT_TYPE"]]
        N = rd("NONDERIV_TRANS.tsv")[["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_ACQUIRED_DISP_CD", "TRANS_SHARES", "TRANS_PRICEPERSHARE"]]
        R = rd("REPORTINGOWNER.tsv")[["ACCESSION_NUMBER", "RPTOWNER_RELATIONSHIP"]]
        N = N[(N.TRANS_CODE == "P") & (N.TRANS_ACQUIRED_DISP_CD == "A")].copy()
        N["usd"] = pd.to_numeric(N.TRANS_SHARES, errors="coerce") * pd.to_numeric(N.TRANS_PRICEPERSHARE, errors="coerce")
        g = N.groupby("ACCESSION_NUMBER").usd.sum().rename("usd").reset_index()
        rel = R.groupby("ACCESSION_NUMBER").RPTOWNER_RELATIONSHIP.agg(lambda x: ",".join(map(str, x))).rename("rel").reset_index()
        g = g.merge(S, on="ACCESSION_NUMBER").merge(rel, on="ACCESSION_NUMBER", how="left")
        rows.append(g[g.DOCUMENT_TYPE.isin(["4", "4/A"])])
    X = pd.concat(rows)
    X["fd"] = pd.to_datetime(X.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    X["sym"] = X.ISSUERTRADINGSYMBOL.str.upper().str.strip().str.replace("-", ".", regex=False)
    r = X.rel.fillna("")
    X = X[r.str.contains("TenPercentOwner") & ~r.str.contains("Director|Officer")].dropna(subset=["fd", "usd"])
    X = X.groupby(["sym", "fd"]).usd.sum().reset_index()
    X = X[X.usd >= 1e4]
    return X[["fd", "sym"]]


def trades(X: pd.DataFrame, end) -> tuple[pd.DataFrame, pd.Index]:
    """ID's events(): session after fd, raw open/close/prior close (Alpaca raw), ADV$ from the panel."""
    P = pd.read_pickle(NIGHT / "panel.pkl")
    C, V = P["close"], P["volume"]
    adv = (C * V).rolling(20, min_periods=15).mean()
    cal = C.index
    syms = sorted(set(X.sym) & set(C.columns))
    bars = F.raw_bars(syms)
    rows = []
    for s, fd in zip(X.sym, X.fd):
        i = cal.searchsorted(fd + pd.Timedelta(days=1))
        if i <= 0 or i >= len(cal) or s not in adv.columns or cal[i] > end:
            continue
        b = bars.get(s)
        if b is None or not len(b):
            continue
        b = b.copy(); b.index = pd.to_datetime(b.index)
        d, dp = cal[i], cal[i - 1]
        o = b.open.get(d, np.nan); c = b.close.get(d, np.nan); pc = b.close.get(dp, np.nan)
        rows.append((d, s, o, c, pc, adv.at[dp, s]))
    T = pd.DataFrame(rows, columns=["d", "sym", "o", "c", "pc", "adv"]).dropna()
    T = T[(T.pc >= 5) & (T.adv >= 1e6) & (T.o > 0)].drop_duplicates(["d", "sym"])
    T["ret"] = T.c / T.o - 1
    return T[T.ret.abs() < 0.5], cal


def raw_frames(T: pd.DataFrame):
    bars = F.raw_bars(sorted(T.sym.unique()))
    o = {s: b.open for s, b in bars.items() if len(b)}
    c = {s: b.close for s, b in bars.items() if len(b)}
    RO, RC = pd.DataFrame(o), pd.DataFrame(c)
    RO.index = pd.to_datetime(RO.index); RC.index = pd.to_datetime(RC.index)
    return RO, RC


def fetch():
    a1_events().to_parquet(F._cache("a1_events.parquet"))
    a2_events().to_parquet(F._cache("a2_events.parquet"))
    P = pd.read_pickle(NIGHT / "panel.pkl")
    for k in ("a1", "a2"):
        X = pd.read_parquet(F._cache(f"{k}_events.parquet"))
        F.raw_bars(sorted(set(X.sym) & set(P["close"].columns)))


def run():
    f = open(ROOT / "data/research/program/filing_day_out.txt", "w")

    def log(*a):
        x = " ".join(str(i) for i in a); print(x, flush=True); f.write(x + "\n"); f.flush()
    id3 = pd.read_pickle(ROOT / "data/research/program/insider_day_trades.pkl")
    id3 = set(zip(id3[id3.adv >= 2e7].d, id3[id3.adv >= 2e7].sym))
    for lab, k in VAR.items():
        X = pd.read_parquet(F._cache(f"{k}_events.parquet"))
        end = pd.Timestamp("2026-09-18") if k == "a1" else pd.Timestamp("2026-03-31")
        T, cal = trades(X, end)
        RO, RC = raw_frames(T)
        ov = np.mean([(d, s) in id3 for d, s in zip(T.d, T.sym)])
        log(f"\n######## {lab}: {len(X)} filing events -> {len(T)} trades; overlap with ID3 trades {ov:.1%}")
        I.run(T, X, cal, RO, RC, {lab: (1e6, np.inf)}, log, end, N_PROG, lab, h2=("2024-01-01", str(end.date())))
        T.to_pickle(ROOT / f"data/research/program/filing_day_{k}_trades.pkl")


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
