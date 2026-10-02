"""Jump hunt D1: a small listed company's 510(k) clearance, bought when it is in the FDA database and before the
company's own press release (death-dodge of the GAP + LOTTERY-killed FDA approvals).

openFDA device/510k: every clearance (decision_code SESE/SESD...) 2014..2026 with applicant and decision_date. FDA's
database is updated weekly, so a clearance is treated as public at decision_date + 14 calendar days (conservative):
fd = decision_date + 14. Applicant -> ticker by exact normalized-name match to Alpaca assets (incl. inactive). Kept
only if no Benzinga story on the ticker mentions 510(k)/clearance from decision_date - 3 to fd (no press release yet).
ADV$ < $20M; first per ticker in 30 days.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_d1
"""
from __future__ import annotations

import json
import re

import pandas as pd
import requests

from .jump_common import ROOT, _norm, first_in, save, small_only

C = ROOT / "data/research/jump/openfda_510k.json"


def fetch() -> list[dict]:
    if C.exists():
        return json.load(open(C))
    rows = []
    for m in pd.period_range("2014-01", "2026-09", freq="M"):
        a, b = m.start_time.strftime("%Y%m%d"), m.end_time.strftime("%Y%m%d")
        skip = 0
        while True:
            r = requests.get("https://api.fda.gov/device/510k.json", params={
                "search": f"decision_date:[{a} TO {b}]", "limit": 1000, "skip": skip}, timeout=120)
            if r.status_code == 404:
                break
            j = r.json()
            for x in j.get("results", []):
                rows.append(dict(k=x.get("k_number"), applicant=x.get("applicant", ""), date=x.get("decision_date"),
                                 code=x.get("decision_code", ""), device=x.get("device_name", "")))
            skip += 1000
            if skip >= j["meta"]["results"]["total"]:
                break
        print(m, len(rows), flush=True)
    json.dump(rows, open(C, "w"))
    return rows


def build() -> pd.DataFrame:
    X = pd.DataFrame(fetch())
    X["date"] = pd.to_datetime(X.date)
    X = X[X.code.str.startswith("SE")]
    alp = json.load(open(ROOT / "data/research/events/alpaca_asset_names.json"))
    by_name: dict[str, str] = {}
    for sym, nm in alp.items():
        if re.fullmatch(r"[A-Z]{1,5}", sym):
            by_name.setdefault(_norm(nm), sym)
    X["sym"] = X.applicant.map(lambda s: by_name.get(_norm(s)))
    X = X.dropna(subset=["sym"])
    X["fd"] = X.date + pd.Timedelta(days=14)
    from .jump_news import news
    L = news()
    L = L[L.headline.str.contains(r"510\(?k\)?|clearance|cleared", case=False) | L.summary.str.contains(r"510\(?k\)?", case=False)]
    pr = L.groupby("sym").fd.apply(lambda x: x.sort_values().to_numpy())
    keep = []
    for r in X.itertuples():
        a = pr.get(r.sym)
        keep.append(a is None or not ((a >= (r.date - pd.Timedelta(days=3)).to_datetime64()) & (a <= r.fd.to_datetime64())).any())
    E = first_in(X[keep][["sym", "fd"]], 30)
    E = E[E.fd >= "2016-01-01"]
    return small_only(E, 20e6)


if __name__ == "__main__":
    save(build(), "d1")
