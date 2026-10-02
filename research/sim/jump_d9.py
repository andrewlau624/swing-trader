"""Jump hunt D9: a small listed sponsor's first Phase 3 trial posted on ClinicalTrials.gov (death-dodge of the
GAP-killed FDA / topline events: a slow registry, months before any readout).

ClinicalTrials.gov API v2: industry-sponsored Phase 3 (incl. Phase 2/3) studies, StudyFirstPostDate 2014..2026.
Event = a lead sponsor's first Phase 3 posting with none by the same sponsor in the prior 730 days; fd = the first
post date (the registry publishes during the day; traded at the next open). Sponsor -> ticker by exact normalized
name match to Alpaca assets (incl. inactive), small caps only (20-day ADV$ < $20M).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_d9
"""
from __future__ import annotations

import json
import re

import pandas as pd
import requests

from .jump_common import ROOT, _norm, first_in, save, small_only

C = ROOT / "data/research/jump/ctgov_phase3.json"


def fetch() -> list[dict]:
    if C.exists():
        return json.load(open(C))
    rows, tok = [], None
    q = ("AREA[Phase](PHASE3) AND AREA[LeadSponsorClass]INDUSTRY AND "
         "AREA[StudyFirstPostDate]RANGE[2014-01-01,2026-09-30]")
    while True:
        p = {"query.term": q, "fields": "NCTId,LeadSponsorName,StudyFirstPostDate,Phase", "pageSize": 1000}
        if tok:
            p["pageToken"] = tok
        j = requests.get("https://clinicaltrials.gov/api/v2/studies", params=p, timeout=120).json()
        for s in j.get("studies", []):
            ps = s["protocolSection"]
            rows.append(dict(nct=ps["identificationModule"]["nctId"],
                             sponsor=ps["sponsorCollaboratorsModule"]["leadSponsor"]["name"],
                             date=ps["statusModule"]["studyFirstPostDateStruct"]["date"]))
        tok = j.get("nextPageToken")
        print(len(rows), flush=True)
        if not tok:
            break
    json.dump(rows, open(C, "w"))
    return rows


def build() -> pd.DataFrame:
    X = pd.DataFrame(fetch())
    X["fd"] = pd.to_datetime(X.date)
    alp = json.load(open(ROOT / "data/research/events/alpaca_asset_names.json"))
    by_name: dict[str, str] = {}
    for sym, nm in alp.items():
        if re.fullmatch(r"[A-Z]{1,5}", sym):
            by_name.setdefault(_norm(nm), sym)
    X["sym"] = X.sponsor.map(lambda s: by_name.get(_norm(s)))
    X = X.dropna(subset=["sym"])
    E = first_in(X[["sym", "fd"]], 730)
    E = E[E.fd >= "2016-01-01"]
    return small_only(E, 20e6)


if __name__ == "__main__":
    save(build(), "d9")
