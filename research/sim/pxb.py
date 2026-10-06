"""Study PXB: passive limit buy at the 14:00 NBBO bid on the ex-eve, MOC fallback (pre-reg round1_prose.md, N 874).

    PYTHONPATH=. .venv/bin/python -m research.sim.pxb fetch    # resumable, cached per ex-eve
    PYTHONPATH=. .venv/bin/python -m research.sim.pxb          # judge
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from .auction_fetch import _env
from .exdiv_open import crosses
from .ovx import ROOT, _bars, _utc
from .ovx_q import _last_quotes

CACHE = ROOT / "data/research/pxb"
OUT = ROOT / "data/research/program/pxb_out.txt"


def events() -> pd.DataFrame:
    out = []
    for s in ("pref", "etdx"):
        D = ROOT / "data/research" / s
        cr = pd.read_parquet(D / "cross_rows.parquet")
        ev = pd.read_parquet(D / "events.parquet").drop_duplicates(["ticker", "date"]).rename(columns={"ticker": "t", "date": "d"})
        x = cr.merge(ev[["t", "d", "sym", "d0", "div"]], on=["t", "d"])
        for d, g in x.groupby("d"):
            j = json.load(open(D / "x" / f"{pd.Timestamp(d).date()}.json"))
            for r in g.itertuples():
                c = crosses(j.get(r.sym, []))
                d0 = pd.Timestamp(r.d0)
                if d0 in c.index and d in c.index:
                    out.append(dict(src=s, t=r.t, sym=r.sym, d=d, d0=d0, div=r.div, c0=c.loc[d0, "cp"],
                                    o1=c.loc[d, "op"], c1=c.loc[d, "cp"], co=r.co, cc=r.cc))
    return pd.DataFrame(out).dropna(subset=["c0", "o1", "c1"])


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    e, H = events(), _env()
    e.to_parquet(CACHE / "events.parquet")
    for i, (d0, g) in enumerate(e.groupby("d0")):
        f = CACHE / f"{d0.date()}.json"
        if f.exists():
            continue
        syms = sorted(set(g.sym))
        json.dump({"q": _last_quotes(syms, _utc(d0, 13, 59), _utc(d0, 14, 0), H),
                   "b": _bars(syms, _utc(d0, 14, 0), _utc(d0, 15, 50), "sip", H)}, open(f, "w"))
        if i % 50 == 0:
            print(i, d0.date(), flush=True)


def tstat(x: pd.Series, d: pd.Series) -> str:
    day = x.groupby(d).mean()
    t = day.mean() / day.std() * np.sqrt(len(day))
    return f"n {len(x):5d} mean {x.mean()*1e4:+6.1f} med {x.median()*1e4:+6.1f} t(day) {t:+5.2f}"


def main():
    e = pd.read_parquet(CACHE / "events.parquet")
    rows = []
    for d0, g in e.groupby("d0"):
        f = CACHE / f"{d0.date()}.json"
        if not f.exists():
            continue
        j = json.load(open(f))
        for r in g.itertuples():
            q = j["q"].get(r.sym)
            bid = q["bp"] if q and (q["ap"] - q["bp"]) / q["bp"] <= 0.05 else np.nan
            bars = j["b"].get(r.sym, [])
            filled = bool(np.isfinite(bid) and any(b["l"] <= bid - 0.01 for b in bars))
            entry = bid if filled else r.c0
            rows.append(dict(src=r.src, d=r.d, filled=filled, quoted=np.isfinite(bid),
                             half=(q["ap"] - q["bp"]) / (q["ap"] + q["bp"]) if q else np.nan,
                             bidsz=q["bs"] * 100 * q["bp"] if q else np.nan,
                             co_b=(r.o1 + r.div) / entry - 1, cc_b=(r.c1 + r.div) / entry - 1,
                             co_m=(r.o1 + r.div) / r.c0 - 1, cc_m=(r.c1 + r.div) / r.c0 - 1,
                             gap=r.c0 / bid - 1 if filled else np.nan))
    x = pd.DataFrame(rows)
    L = [f"PXB: {len(x)} events, quoted at 14:00 {x.quoted.mean():.0%}, filled {x.filled.mean():.0%}, "
         f"median half-spread {x.half.median()*1e4:.1f}bp, median bid size ${x.bidsz.median():,.0f}"]
    for c in ["co", "cc"]:
        L.append(f"\n{c.upper()}: MOC baseline {tstat(x[c + '_m'], x.d)}")
        L.append(f"    blended       {tstat(x[c + '_b'], x.d)}")
        dlt = x[c + "_b"] - x[c + "_m"]
        L.append(f"    blended - MOC {tstat(dlt, x.d)}")
        for lab, q in [("2021-23", x.d < "2024"), ("2024-26", x.d >= "2024"), ("pref", x.src == "pref"), ("etdx", x.src == "etdx")]:
            L.append(f"      {lab:8s} {tstat(dlt[q], x.d[q])}")
        fl = x[x.filled]
        L.append(f"    filled-only: at bid {tstat(fl[c + '_b'], fl.d)} | same events at MOC {tstat(fl[c + '_m'], fl.d)}")
    fl = x[x.filled]
    L.append(f"\nfilled events: close cross vs our bid median {fl.gap.median()*1e4:+.1f}bp (>0 = price recovered by the close)")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    fetch() if sys.argv[1:] == ["fetch"] else main()
