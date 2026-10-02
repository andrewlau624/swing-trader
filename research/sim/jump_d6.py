"""Jump hunt D6: first profitable quarter after a long losing streak (death-dodge of TEXTBOOK earnings drift: a
milestone, not a surprise).

Candidates from XBRL frames (us-gaap NetIncomeLoss, USD, calendar quarters CY2014Q1..CY2026Q2). For each candidate
CIK, companyfacts gives every reported quarterly NetIncomeLoss with the ORIGINAL filing (form 10-Q/10-K, `filed`).
Event = the first filing that reports a positive quarterly net income (a ~90-day duration fact) after >= 6
consecutive negative reported quarters; fd = that filing's `filed` date (traded at the next open). Small caps only
(20-day ADV$ < $20M). Ticker via jump_common.resolve.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_d6
"""
from __future__ import annotations

import json

import pandas as pd

from .jump_common import ROOT, resolve, save, small_only
from .tender_fetch import get

C = ROOT / "data/research/jump/xbrl"


def frames() -> pd.DataFrame:
    rows = []
    for q in pd.period_range("2014Q1", "2026Q2", freq="Q"):
        f = C / f"ni_{q}.json"
        if not f.exists():
            C.mkdir(parents=True, exist_ok=True)
            j = get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/NetIncomeLoss/USD/CY{q.year}Q{q.quarter}.json") or {}
            json.dump(j.get("data", []), open(f, "w"))
        for x in json.load(open(f)):
            rows.append((x["cik"], str(q), x["val"], x.get("entityName", "")))
    return pd.DataFrame(rows, columns=["cik", "q", "val", "name"])


def candidates(Fr: pd.DataFrame) -> list[int]:
    out = []
    for cik, g in Fr.sort_values("q").groupby("cik"):
        v = g.val.to_numpy()
        for i in range(6, len(v)):
            if v[i] > 0 and (v[i - 6:i] < 0).all():
                out.append(cik); break
    return out


def facts(cik: int) -> list[dict]:
    f = C / f"cf_{cik}.json"
    if not f.exists():
        j = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json") or {}
        units = (((j.get("facts") or {}).get("us-gaap") or {}).get("NetIncomeLoss") or {}).get("units", {}).get("USD", [])
        json.dump(dict(name=j.get("entityName", ""), ni=units), open(f, "w"))
    return json.load(open(f))


def build() -> pd.DataFrame:
    Fr = frames()
    cands = candidates(Fr)
    print(len(cands), "candidate CIKs", flush=True)
    rows = []
    for cik in cands:
        j = facts(cik)
        X = pd.DataFrame(j["ni"])
        if not len(X) or "start" not in X:
            continue
        X = X[X.form.isin(["10-Q", "10-K", "10-Q/A", "10-K/A"])].copy()
        X["start"], X["end"], X["filed"] = (pd.to_datetime(X[c]) for c in ("start", "end", "filed"))
        X = X[(X.end - X.start).dt.days.between(80, 100)]
        first = X.sort_values("filed").drop_duplicates("end")            # the original report of each quarter
        first = first.sort_values("end")
        v = first.val.to_numpy()
        for i in range(6, len(v)):
            if v[i] > 0 and (v[i - 6:i] < 0).all():
                rows.append(dict(cik=cik, name=j["name"], fd=first.filed.iat[i])); break
    E = pd.DataFrame(rows)
    E = E[E.fd >= "2016-01-01"]
    return small_only(resolve(E), 20e6)


if __name__ == "__main__":
    E = build()
    E.to_csv(ROOT / "data/research/jump/d6_events.csv", index=False)
    save(E, "d6")
