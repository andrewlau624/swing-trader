"""Jump hunt EDGAR full-text ideas: R2-2 going-concern doubt removed, R2-13 listing compliance regained.

R2-2: FTS 10-K hits for "substantial doubt" AND "going concern", year by year 2014-2026. For every CIK with such a 10-K,
its NEXT 10-K (EDGAR form.idx, by filing date) is an event if that 10-K is not itself a hit (the doubt language is
gone); fd = the next 10-K's filing date. ADV$ < $20M.
R2-13: FTS 8-K hits for "regained compliance" (Nasdaq/NYSE listing-rule letters); fd = the 8-K's file date; first per
company in 365 days. ADV$ < $20M.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_edgar r2_2|r2_13
"""
from __future__ import annotations

import sys

import pandas as pd

from . import event_fetch as F
from .jump_common import first_in, resolve, save, small_only


def _fts(q: str, forms: str, y0: int = 2014, y1: int = 2026) -> pd.DataFrame:
    rows = []
    for y in range(y0, y1 + 1):
        for h in F.fts(q, forms, f"{y}-01-01", f"{y}-06-30") + F.fts(q, forms, f"{y}-07-01", f"{y}-12-31"):
            for cik, nm in zip(h["ciks"], h["names"]):
                rows.append(dict(adsh=h["adsh"], form=h["form"], date=pd.Timestamp(h["date"]), cik=str(int(cik)), name=nm))
        print(q, y, len(rows), flush=True)
    return pd.DataFrame(rows).drop_duplicates(["adsh", "cik"])


def r2_2() -> pd.DataFrame:
    H = _fts('"substantial doubt" "going concern"', "10-K")
    H = H[H.form == "10-K"]
    hit = set(H.adsh)
    I = pd.concat([F.full_index(y, q) for y in range(2014, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)])
    K = I[I.form == "10-K"].copy()
    K["adsh"] = K.path.str.extract(r"/(\d{10}-\d{2}-\d{6})\.txt$")[0]
    K["date"] = pd.to_datetime(K.date)
    K = K.sort_values(["cik", "date"])
    K["nxt_adsh"], K["nxt_date"] = K.groupby("cik").adsh.shift(-1), K.groupby("cik").date.shift(-1)
    G = K[K.adsh.isin(hit) & K.nxt_adsh.notna() & ~K.nxt_adsh.isin(hit)]
    G = G[(G.nxt_date - G.date).dt.days.between(300, 430)]           # the next ANNUAL report, not an amendment burst
    names = H.drop_duplicates("cik").set_index("cik").name
    E = pd.DataFrame(dict(cik=G.cik.astype(str), fd=G.nxt_date))
    E["name"] = E.cik.map(names).fillna("")
    E = E[E.fd >= "2016-01-01"]
    return small_only(resolve(E), 20e6)


def r2_13() -> pd.DataFrame:
    H = _fts('"regained compliance"', "8-K", 2015)
    H = H[H.form == "8-K"].rename(columns={"date": "fd"})
    E = resolve(H[H.fd >= "2016-01-01"])
    return small_only(first_in(E[["sym", "fd"]], 365), 20e6)


BIG = {'"Amazon.com Services"': "1018724", '"Amazon Web Services"': "1018724", '"Walmart Inc."': "104169",
       '"Apple Inc."': "320193", '"Microsoft Corporation"': "789019", '"NVIDIA Corporation"': "1045810",
       '"Google LLC"': "1652044", '"Tesla, Inc."': "1318605", '"Meta Platforms"': "1326801",
       '"Department of Defense"': ""}


def r2_20() -> pd.DataFrame:
    """8-K with "Item 1.01" (material definitive agreement) naming a big counterparty, filed by someone other than
    that company; first per filer in 365 days; ADV$ < $20M."""
    parts = []
    for q, own in BIG.items():
        H = _fts(f'"Item 1.01" {q}', "8-K", 2015)
        H = H[(H.form == "8-K") & (H.cik != own)]
        parts.append(H)
    H = pd.concat(parts).rename(columns={"date": "fd"})
    E = resolve(H[H.fd >= "2016-01-01"])
    return small_only(first_in(E[["sym", "fd"]], 365), 20e6)


if __name__ == "__main__":
    what = sys.argv[1]
    save(globals()[what](), what)
