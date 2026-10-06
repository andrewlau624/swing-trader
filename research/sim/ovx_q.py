"""Study OVX-Q: sell night picks at the pre-market SIP NBBO bid (pre-reg round1_prose.md, N 872).

    PYTHONPATH=. .venv/bin/python -m research.sim.ovx_q fetch    # resumable, cached per night
    PYTHONPATH=. .venv/bin/python -m research.sim.ovx_q          # judge
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd
import requests

from .auction_fetch import _env
from .ovx import ROOT, SPLIT, _utc, picks, stat

CACHE = ROOT / "data/research/ovx_q"
OUT = ROOT / "data/research/program/ovx_q_out.txt"
QURL = "https://data.alpaca.markets/v2/stocks/quotes"
TAUS = [(8, 0), (9, 0), (9, 15), (9, 24)]


def _last_quotes(syms, start, end, H):
    last, tok = {}, None
    while True:
        q = {"symbols": ",".join(syms), "start": start, "end": end, "feed": "sip", "limit": 10000}
        if tok:
            q["page_token"] = tok
        for k in range(5):
            r = requests.get(QURL, params=q, headers=H, timeout=60)
            if r.status_code == 200:
                break
            time.sleep(2 * (k + 1))
        j = r.json()
        for s, qs in (j.get("quotes") or {}).items():
            ok = [x for x in qs if x.get("bp", 0) > 0 and x.get("ap", 0) > x.get("bp", 0)]
            if ok:
                last[s] = {k: ok[-1][k] for k in ("bp", "ap", "bs", "as", "t")}
        tok = j.get("next_page_token")
        if not tok:
            return last


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    p, H = picks(), _env()
    for i, ((d, n), x) in enumerate(p.groupby(["d", "n"])):
        f = CACHE / f"{d.date()}.json"
        if f.exists():
            continue
        syms = sorted(set(x.sym))
        out = {}
        for h, m in TAUS:
            m0, h0 = (m - 1, h) if m else (59, h - 1)
            out[f"{h:02d}{m:02d}"] = _last_quotes(syms, _utc(n, h0, m0), _utc(n, h, m), H)
        json.dump(out, open(f, "w"))
        if i % 50 == 0:
            print(i, d.date(), flush=True)


def fetch_ctrl():
    """Control: the same names on the PICK day d itself (no prior-day crash): 09:24 bid on d vs d's open cross."""
    from .auction_fetch import fetch as auctions
    (CACHE / "ctrl").mkdir(parents=True, exist_ok=True)
    p, H = picks(), _env()
    for i, (d, x) in enumerate(p.groupby("d")):
        f = CACHE / "ctrl" / f"{d.date()}.json"
        if f.exists():
            continue
        syms = sorted(set(x.sym))
        json.dump({"q": _last_quotes(syms, _utc(d, 9, 23), _utc(d, 9, 24), H),
                   "a": auctions(syms, str(d.date()), str(d.date()), H)}, open(f, "w"))
        if i % 50 == 0:
            print("ctrl", i, d.date(), flush=True)


def ctrl() -> str:
    import glob
    import pathlib
    from .exdiv_open import crosses
    xs = []
    for f in sorted(glob.glob(str(CACHE / "ctrl" / "*.json"))):
        d = pd.Timestamp(pathlib.Path(f).stem)
        j = json.load(open(f))
        for s, q in j["q"].items():
            a = j["a"].get(s)
            if not a or (q["ap"] - q["bp"]) / q["bp"] > 0.10:
                continue
            c = crosses(a)
            if d in c.index and c.loc[d, "op"] > 0:
                xs.append((d, q["bp"] / c.loc[d, "op"] - 1))
    x = pd.DataFrame(xs, columns=["d", "x"])
    return f"CONTROL (same names, pick day d, before the crash close): 09:24 bid vs d's open cross: {stat(x.x, x.d)}"


def main():
    p = picks()
    rows = []
    for (d, n), x in p.groupby(["d", "n"]):
        f = CACHE / f"{d.date()}.json"
        if not f.exists():
            continue
        j = json.load(open(f))
        for r in x.itertuples():
            row = dict(d=d, sym=r.sym, adv=r.adv, c=r.c_auc, o=r.o_auc)
            for k, qs in j.items():
                qq = qs.get(r.sym)
                if qq and (qq["ap"] - qq["bp"]) / qq["bp"] <= 0.10:
                    row[f"b{k}"], row[f"m{k}"] = qq["bp"], (qq["bp"] + qq["ap"]) / 2
                    row[f"bs{k}"] = qq["bs"] * 100 * qq["bp"]          # SIP sizes are round lots
            rows.append(row)
    t = pd.DataFrame(rows)
    L = [f"OVX-Q: {len(t)} picks, {t.d.nunique()} nights", f"base close->open cross: {stat(t.o / t.c - 1, t.d)}", ""]
    for h, m in TAUS:
        k = f"{h:02d}{m:02d}"
        if f"b{k}" not in t:
            continue
        cov = t[f"b{k}"].notna().mean()
        hs = ((t[f"m{k}"] - t[f"b{k}"]) / t[f"m{k}"]).median()
        L.append(f"{k} cov {cov:4.0%} med half-spread {hs*1e4:5.1f}bp med bid size ${t[f'bs{k}'].median():,.0f}")
        L.append(f"   bid vs open: {stat(t[f'b{k}'] / t.o - 1, t.d)}")
        L.append(f"   mid vs open: {stat(t[f'm{k}'] / t.o - 1, t.d)}")
        L.append(f"   close->bid : {stat(t[f'b{k}'] / t.c - 1, t.d)}")
    x = t.b0924 / t.o - 1
    L.append("")
    L.append("== primary 09:24 bid vs open cross ==")
    for lab, q in [("half 1", t.d <= SPLIT), ("half 2", t.d > SPLIT), ("ADV top half", t.adv >= t.adv.median()),
                   ("ADV bottom half", t.adv < t.adv.median())]:
        L.append(f"{lab:16s} {stat(x[q], t.d[q])}")
    if (CACHE / "ctrl").exists():
        L += ["", ctrl()]
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    t.to_parquet(CACHE / "table.parquet")


if __name__ == "__main__":
    {"fetch": fetch, "ctrl": fetch_ctrl}.get((sys.argv[1:] or ["main"])[0], main)()
