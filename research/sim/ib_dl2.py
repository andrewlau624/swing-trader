"""Index-beat DL-IB2: reverse splits with a round-lot top-up (rule: round1_prose.md DL-IB2, 0f32a57).

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_dl2
"""
from __future__ import annotations

import pathlib
import pickle
import re

import numpy as np
import pandas as pd

from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
FORMS = ("8-K", "DEF 14A", "DEF 14C", "PRE 14A", "PRE 14C", "DEFA14A", "PRER14A", "PRER14C", "424B3", "424B4", "S-1", "S-1/A")
FUND = re.compile(r"\b(TRUST|FUNDS?|ETF|PORTFOLIOS?|SERIES)\b", re.I)
TOPUP = re.compile(r"(round[- ]lot|100 shares|one hundred \(100\) shares|one hundred shares)", re.I)
PROTECT = re.compile(r"(not (?:be )?reduce[ds]? (?:\w+ ){0,4}(?:below|to less than|under)|at least (?:a round lot|100 shares)|"
                     r"(?:receive|retain|hold) (?:a minimum of|at least) (?:100|one hundred|a round lot)|"
                     r"(?:less than|fewer than) (?:a round lot|100 shares)[^.]{0,120}(?:receive|issued|increase|rounded up))", re.I)


def sentences(t):
    t = re.sub(r"<[^>]+>|&nbsp;|&#160;", " ", t)
    return [s for s in re.split(r"(?<=[.;])\s+", re.sub(r"\s+", " ", t))]


def topup_docs():
    H = pickle.load(open(ROOT / "data/research/program/ib/dl_ib2_fts.pkl", "rb"))
    H = [h for h in H if h["form"] in FORMS and not FUND.search(h["names"][0])]
    out = []
    for h in H:
        try:
            t = F.doc(h["ciks"][0], h["adsh"], h["id"].split(":", 1)[1]) or ""
        except Exception:
            continue
        hit = [s for s in sentences(t) if re.search("split", s, re.I) and TOPUP.search(s) and PROTECT.search(s)
               and not re.search(r"participant level|Cede", s, re.I)]
        if hit:
            out.append(dict(names=h["names"], date=pd.Timestamp(h["date"]), form=h["form"], cik=h["ciks"][0], sent=hit[0][:300]))
    return out


def main():
    docs = topup_docs()
    print(f"documents with a split + round-lot protection sentence: {len(docs)} from "
          f"{len({d['cik'] for d in docs})} issuers")
    RS = F.reverse_splits(); RS["N"] = RS.old / RS.new
    RS = RS[(RS.N >= 2) & (RS.ex >= "2016-01-01")]
    tk = {}
    for d in docs:
        for nm in d["names"]:
            for t in F.ticker_of(nm):
                tk.setdefault(t.replace("-", "."), []).append(d)
    rows = []
    for r in RS.itertuples():
        ds = [d for d in tk.get(r.symbol, []) if r.ex - pd.Timedelta(days=90) <= d["date"] < r.ex]
        if ds:
            rows.append(dict(symbol=r.symbol, ex=r.ex, N=r.N, sent=ds[0]["sent"]))
    E = pd.DataFrame(rows)
    print(f"reverse splits with such a filing in the 90 days before ex: {len(E)}; by year "
          f"{E.ex.dt.year.value_counts().sort_index().to_dict() if len(E) else {}}")
    if len(E):
        F.raw_bars(sorted(E.symbol.unique()))
        res = []
        for r in E.itertuples():
            b = F.raw_bars([r.symbol]).get(r.symbol)
            if b is None or b.empty:
                continue
            b = b.copy(); b.index = pd.to_datetime(b.index)
            pre = b[b.index < r.ex]; post = b[b.index >= r.ex]
            if len(pre) < 1 or len(post) < 3:
                continue
            ps, pe2 = float(pre.close.iloc[-1]), float(post.close.iloc[2])
            res.append(dict(symbol=r.symbol, ex=r.ex.date(), N=r.N, ps=ps, pe2=pe2, cap=100 * ps,
                            topped=100 * pe2 - 100 * ps, not_topped=100 / r.N * pe2 - 100 * ps))
        R = pd.DataFrame(res)
        pd.set_option("display.width", 200)
        print(R.to_string())
        if len(R):
            ok = R[R.ps <= 3]
            be = (-ok.not_topped.mean()) / (ok.topped.mean() - ok.not_topped.mean()) if len(ok) else np.nan
            print(f"price <= $3: n {len(ok)}, topped mean ${ok.topped.mean():+,.0f} median ${ok.topped.median():+,.0f} worst "
                  f"${ok.topped.min():+,.0f}; not topped mean ${ok.not_topped.mean():+,.0f}; break-even P(top-up) {be:.1%}")
        for d in docs[:8]:
            print("  e.g.", d["names"][0][:40], d["date"].date(), "|", d["sent"][:220])


if __name__ == "__main__":
    main()
