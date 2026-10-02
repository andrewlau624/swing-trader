"""Jump hunt D5: a company renames itself into a hot word (death-dodge of GAP-killed index/spin-off events; wildcard).

EDGAR quarterly form.idx 2016Q1..2026Q3 lists every filing with the filer's conformed name AT THAT TIME. A rename =
a CIK whose name on a 10-K/10-Q/8-K/S-1/S-3/DEF 14A/... differs from its previous filing's name. Event = the first
filing date under a new name that matches HOT while the old name did not (public by then; the press release may be
earlier, so this is conservative). Ticker: the CIK's EDGAR tickers if any, else an exact normalized-name match to
an Alpaca asset (Alpaca keeps inactive symbols), so delisted renamers are kept.

HOT (fixed before any outcome): blockchain, crypto, bitcoin, digital asset(s), AI (word or .ai), artificial
intelligence, quantum, metaverse, cannabis, hemp, CBD, marijuana, lithium, uranium, hydrogen, EV (word), electric
vehicle, solar, nuclear, drone, robotic(s), space (word), genomic(s), psychedelic(s).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_d5
"""
from __future__ import annotations

import json
import re

import pandas as pd

from . import event_fetch as F
from .jump_common import ROOT, save

HOT = re.compile(r"BLOCKCHAIN|CRYPTO|BITCOIN|DIGITAL ASSETS?|\bAI\b|\.AI\b|ARTIFICIAL INTELLIGENCE|QUANTUM|METAVERSE|"
                 r"CANNABIS|HEMP|\bCBD\b|MARIJUANA|LITHIUM|URANIUM|HYDROGEN|\bEV\b|ELECTRIC VEHICLE|SOLAR|NUCLEAR|DRONE|"
                 r"ROBOTICS?|\bSPACE\b|GENOMICS?|PSYCHEDELICS?")
SUFFIX = re.compile(r"\b(INC|CORP|CORPORATION|CO|LTD|LIMITED|PLC|HOLDINGS?|GROUP|COMMON STOCK|CLASS [A-C]|ORDINARY SHARES|"
                    r"N ?V|S ?A|LLC|LP|THE)\b")


def norm(s: str) -> str:
    s = re.sub(r"[^A-Z0-9 ]", " ", str(s).upper().replace("/DE", " ").replace("/NV", " "))
    return " ".join(SUFFIX.sub(" ", s).split())


def renames() -> pd.DataFrame:
    I = pd.concat([F.full_index(y, q) for y in range(2016, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)])
    I = I[~I.form.str.startswith(("13F", "SC 13", "4", "3", "5", "N-", "497", "485", "D"))]
    I = I.sort_values(["cik", "date"]).drop_duplicates(["cik", "date", "company"])
    I["prev"] = I.groupby("cik").company.shift(1)
    R = I[I.prev.notna() & (I.company.map(norm) != I.prev.map(norm))]
    R = R[R.company.str.upper().str.contains(HOT) & ~R.prev.str.upper().str.contains(HOT)]
    return R.drop_duplicates("cik")[["cik", "company", "prev", "date"]]


def tickers(R: pd.DataFrame) -> pd.DataFrame:
    ct = F.company_tickers()
    alp = json.load(open(ROOT / "data/research/events/alpaca_asset_names.json"))
    by_name: dict[str, list[str]] = {}
    for sym, nm in alp.items():
        if re.fullmatch(r"[A-Z]{1,5}", sym):
            by_name.setdefault(norm(nm), []).append(sym)
    rows = []
    for r in R.itertuples():
        syms = [t for t in ct.get(str(int(r.cik)), []) if re.fullmatch(r"[A-Z]{1,5}", t)]
        if not syms:
            syms = by_name.get(norm(r.company), [])
        for s in syms[:1]:
            rows.append(dict(sym=s, fd=pd.Timestamp(r.date), company=r.company, prev=r.prev))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    R = renames()
    print(len(R), "hot renames (CIKs)")
    E = tickers(R)
    print(len(E), "with a ticker")
    E.to_csv(ROOT / "data/research/jump/d5_renames.csv", index=False)
    save(E, "d5")
