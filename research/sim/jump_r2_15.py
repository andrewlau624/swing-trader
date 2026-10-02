"""Jump hunt R2-15: a small company's share count shrinks >= 3% (and < 50%) between consecutive cover-page counts.

XBRL frames dei EntityCommonStockSharesOutstanding (CY2014Q1I..CY2026Q3I, one fact per filer per quarter). The cover
count is "as of" a date shortly before the filing, so fd = the filing date of the fact's accession (EDGAR form.idx),
else the cover date + 45 days. Consecutive counts must be 30-200 days apart; no reverse split (Alpaca corporate
actions) between them. ADV$ < $20M; first per ticker in 180 days.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_r2_15
"""
from __future__ import annotations

import pandas as pd

from . import event_fetch as F
from .jump_common import ROOT, cik_sym, first_in, save, small_only
from .tender_fetch import get


def build() -> pd.DataFrame:
    cs = cik_sym()
    rows = []
    for q in pd.period_range("2014Q1", "2026Q3", freq="Q"):
        j = get(f"https://data.sec.gov/api/xbrl/frames/dei/EntityCommonStockSharesOutstanding/shares/CY{q.year}Q{q.quarter}I.json") or {}
        for x in j.get("data", []):
            s = cs.get(str(x["cik"]))
            if s:
                rows.append((s, pd.Timestamp(x["end"]), float(x["val"]), x["accn"]))
    D = pd.DataFrame(rows, columns=["sym", "end", "shares", "accn"]).drop_duplicates(["sym", "end"]).sort_values(["sym", "end"])
    I = pd.concat([F.full_index(y, q) for y in range(2014, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)])
    I["accn"] = I.path.str.extract(r"/(\d{10}-\d{2}-\d{6})\.txt$")[0]
    filed = I.drop_duplicates("accn").set_index("accn").date
    D["filed"] = pd.to_datetime(D.accn.map(filed))
    D["fd"] = D.filed.fillna(D.end + pd.Timedelta(days=45))
    D["prev"], D["prev_end"] = D.groupby("sym").shares.shift(1), D.groupby("sym").end.shift(1)
    X = D[(D.shares <= 0.97 * D.prev) & (D.shares >= 0.5 * D.prev) & (D.end - D.prev_end).dt.days.between(30, 200)]
    RS = pd.read_parquet(ROOT / "data/research/events/alpaca_reverse_splits.parquet")
    rs = RS.groupby("symbol").ex.apply(lambda x: x.sort_values().to_numpy())
    keep = []
    for r in X.itertuples():
        a = rs.get(r.sym)
        keep.append(a is None or not ((a >= r.prev_end.to_datetime64()) & (a <= r.fd.to_datetime64())).any())
    E = first_in(X[keep][["sym", "fd"]], 180)
    return small_only(E[E.fd >= "2016-01-01"], 20e6)


if __name__ == "__main__":
    save(build(), "r2_15")
