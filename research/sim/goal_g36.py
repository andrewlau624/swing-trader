"""Goal hunt Study G36 (pre-registered in round1_prose.md, commit 06716e0): >= 5 distinct reporting owners filing code-F
(tax-withholding) Form 4s at one issuer within 2 calendar days = a vest date; buy the 2nd session after, hold 5, vs SPY.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g36 build
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g36 select     # 2021-23, one look

Output: data/research/program/goal_g36_out.txt
"""
from __future__ import annotations

import glob
import pathlib
import sys
import zipfile

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g36_events.parquet"
SEL = ("2021-01-01", "2023-12-31")
HOLD = 5


def out():
    f = open(PROG / "goal_g36_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def code_f() -> pd.DataFrame:
    f = PROG / "goal_g36_codef.parquet"
    if f.exists():
        return pd.read_parquet(f)
    zs = sorted(glob.glob(str(ROOT / "data/research/jump/insider/201[4-9]q?_form345.zip"))) + \
        sorted(glob.glob(str(ROOT / "data/research/night/insider/20[2-9]?q?_form345.zip")))
    rows = []
    for z in zs:
        Z = zipfile.ZipFile(z)
        rd = lambda n, c: pd.read_csv(Z.open(n), sep="\t", dtype=str, low_memory=False, on_bad_lines="skip", usecols=c)
        S = rd("SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL", "DOCUMENT_TYPE"])
        N = rd("NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_CODE"])
        R = rd("REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK"])
        a = N[N.TRANS_CODE == "F"].ACCESSION_NUMBER.unique()
        g = S[S.ACCESSION_NUMBER.isin(a) & S.DOCUMENT_TYPE.isin(["4", "4/A"])].merge(R, on="ACCESSION_NUMBER")
        rows.append(g)
        print(z.split("/")[-1], len(g), flush=True)
    X = pd.concat(rows)
    X["fd"] = pd.to_datetime(X.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    X["sym"] = X.ISSUERTRADINGSYMBOL.str.upper().str.strip().str.replace("-", ".", regex=False)
    X = X.dropna(subset=["fd", "sym"])[["fd", "sym", "RPTOWNERCIK"]].drop_duplicates()
    X.to_parquet(f)
    return X


def clusters(X: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s, g in X.groupby("sym"):
        d = g.groupby("fd").RPTOWNERCIK.apply(set).sort_index()
        dates = list(d.index)
        last = None
        for i, t in enumerate(dates):
            own = set()
            for u in dates[:i + 1][::-1]:
                if (t - u).days > 2:
                    break
                own |= d[u]
            if len(own) >= 5 and (last is None or (t - last).days > 28):
                rows.append((s, t, len(own)))
                last = t
    return pd.DataFrame(rows, columns=["sym", "cd", "owners"])


def build():
    log = out()
    log(f"=== G36 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    X = code_f()
    C = clusters(X)
    log(f"  code-F filings {len(X)}; clusters (>= 5 owners in 2 days) {len(C)}")
    bars = F.raw_bars(sorted(C.sym.unique()))
    rows = []
    for r in C.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            continue
        b = b.sort_index(); idx = pd.DatetimeIndex(b.index)
        i = idx.searchsorted(r.cd + pd.Timedelta(days=1)) + 1          # 2nd session after the cluster date
        if i < 21 or i + HOLD - 1 >= len(idx) or (idx[i] - r.cd).days > 10:
            continue
        h = b.iloc[i - 21:i - 1]
        pc, adv = b.close.iloc[i - 1], (h.close * h.volume).mean()
        seg = b.close.iloc[i - 1:i + HOLD]
        rr = (seg / seg.shift(1)).dropna()
        if pc < 5 or adv < 5e7 or ((rr > 1.8) | (rr < 0.55)).any():
            continue
        rows.append(dict(sym=r.sym, cd=r.cd, d=idx[i], dx=idx[i + HOLD - 1], o=b.open.iloc[i], c=b.close.iloc[i + HOLD - 1], adv=adv))
    T = pd.DataFrame(rows)
    T.to_parquet(EVF)
    log(f"  events with bars, price >= $5, ADV >= $50M: {len(T)} by year {T.groupby(T.d.dt.year).size().to_dict()}")


def select():
    from .goal_g2 import spy_adj
    log = out()
    log(f"\n=== G36 SELECT 2021-23 {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    T = pd.read_parquet(EVF)
    V = T[(T.d >= SEL[0]) & (T.d <= SEL[1])].copy()
    S = spy_adj(); S.index = pd.DatetimeIndex(S.index)
    prev = np.array([S.loc[:d].iloc[-2] for d in V.d])
    cb = B.cost_bps("tier", V.o.values, V.adv.values) / 1e4
    V["x"] = (V.c / V.o - 1).values - (S.reindex(V.dx).values / prev - 1) - 2 * cb
    dm = V.groupby("d").x.mean()
    t = dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))
    log(f"  n {len(V)} on {len(dm)} dates; mean {V.x.mean():+.2%} median {V.x.median():+.2%} hit {(V.x > 0).mean():.0%} | "
        f"date-level mean {dm.mean():+.2%} t {t:+.2f} | by year " +
        " ".join(f"{y}:{m:+.2%}" for y, m in V.groupby(V.d.dt.year).x.mean().items()))
    ok = V.x.mean() >= 0.003 and t >= 2
    log(f"  select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": select}[sys.argv[1]]()
