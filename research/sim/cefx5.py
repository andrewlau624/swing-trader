"""Study CEFX5 (round1_prose.md, N 1023): CEF y>5% ex-night at OFFICIAL SIP crosses, 2021-01..2026-09. One look.

    PYTHONPATH=. .venv/bin/python -m research.sim.cefx5
"""
from __future__ import annotations

import json
import pathlib
import time

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import requests

from . import fxd
from .auction_fetch import _env, fetch
from .exdiv_open import crosses

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/cefx5"
OUT = ROOT / "data/research/program/cefx5_out.txt"
RT = 0.0010


def events():
    e = fxd.load()
    e = e[(e.cat == "CEF") & (e.bin == ">5%") & (e.date >= "2021-01-01") & (e.date <= "2026-09-30")].copy()
    b = ds.dataset(fxd.S / "funds.parquet").to_table(columns=["ticker", "date"],
                                                     filter=ds.field("ticker").isin(list(e.ticker.unique()))).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["ticker", "date"])
    b["d0"] = b.groupby("ticker").date.shift(1)
    return e.merge(b, on=["ticker", "date"], how="left").reset_index(drop=True)


def stat(x, c):
    day = x.groupby("date")[c].mean()
    t = day.mean() / day.std() * np.sqrt(len(day)) if len(day) > 1 else np.nan
    s = np.sort(x[c].values)
    return (f"n {len(x):4d} mean {x[c].mean()*1e4:+7.1f} med {x[c].median()*1e4:+7.1f} t(day) {t:+5.2f} "
            f"ex-top5 {s[:-5].mean()*1e4:+7.1f} hit {(x[c] > 0).mean():.2f}")


def main():
    D.mkdir(parents=True, exist_ok=True)
    e = events()
    L = [f"CEFX5: FXD CEF y>5% events 2021-01..2026-09: {len(e)} ({e.ticker.nunique()} funds)"]
    e["sym"] = e.ticker
    bad = ~e.sym.str.fullmatch(r"[A-Z]{1,6}")
    L.append(f"tickers not plain-Alpaca-mappable (hyphen etc.): {int(bad.sum())} events -> no official cross, reported not dropped silently")
    f = D / "auctions.json"
    if f.exists():
        raw = json.load(open(f))
    else:
        H = _env(); raw = {}
        for i, r in enumerate(e[~bad].itertuples()):
            k = f"{r.sym}|{r.date.date()}"
            try:
                raw[k] = fetch([r.sym], str(r.d0.date()), str(r.date.date()), H).get(r.sym, [])
            except requests.RequestException as ex:  # network failure -> no cross, counted in the output
                raw[k] = []; print("err", k, ex)
            time.sleep(0.1)
        json.dump(raw, open(f, "w"))
    c0, c1, o1, cs0, cs1 = [], [], [], [], []
    for r in e.itertuples():
        rows = raw.get(f"{r.sym}|{r.date.date()}", [])
        v = [np.nan] * 5
        if rows:
            x = crosses(rows)
            if r.d0 in x.index and r.date in x.index:
                v = [x.loc[r.d0, "cp"], x.loc[r.date, "cp"], x.loc[r.date, "op"], x.loc[r.d0, "cs"] * x.loc[r.d0, "cp"],
                     x.loc[r.date, "cs"] * x.loc[r.date, "cp"]]
        c0.append(v[0]); c1.append(v[1]); o1.append(v[2]); cs0.append(v[3]); cs1.append(v[4])
    e["c0"], e["c1"], e["o1"], e["cusd0"], e["cusd1"] = c0, c1, o1, cs0, cs1
    e["occ"] = (e.c1 + e["div"]) / e.c0 - 1
    e["oco"] = (e.o1 + e["div"]) / e.c0 - 1
    e["xocc"] = e.occ - e.cc_base - RT
    e["xoco"] = e.oco - e.co_base - RT
    e["xvcc"] = e.xcc - RT
    e["xvco"] = e.xco - RT
    e["odrop"] = (e.c0 - e.c1) / e["div"]
    have = e.dropna(subset=["xocc"]).copy()
    hc = have.dropna(subset=["xoco"])
    L.append(f"events with BOTH official crosses (CC): {len(have)}; missing {len(e)-len(have)} (excluded from official stats, "
             f"vendor stats shown on all and on matched); CO needs open cross too: {len(hc)}")
    L.append("")
    L.append("== PRIMARY: CC excess at official crosses, net 10bp RT ==")
    L.append("CC official  " + stat(have, "xocc"))
    L.append("CO official  " + stat(hc, "xoco"))
    L.append(f"drop/div (official, median) {have.odrop.median():.2f}; vendor drop/div (all) {e['drop'].median():.2f}")
    L.append("")
    L.append("== vendor bars, same events (net 10bp RT) ==")
    L.append("CC vendor matched " + stat(have, "xvcc"))
    L.append("CO vendor matched " + stat(hc, "xvco"))
    L.append("CC vendor all     " + stat(e, "xvcc"))
    L.append("CO vendor all     " + stat(e, "xvco"))
    L.append("")
    L.append("== 3x cost (30bp RT) ==")
    have["x3"] = have.xocc - 2 * RT
    L.append("CC official 3x    " + stat(have, "x3"))
    L.append("")
    L.append("== per year CC official (mean bp, n) ==")
    for y, g in have.groupby(have.date.dt.year):
        L.append(f"{y}: {g.xocc.mean()*1e4:+7.1f} med {g.xocc.median()*1e4:+7.1f} (n {len(g)})")
    L.append(f"cross $ median: close T-1 ${have.cusd0.median():,.0f}, close T ${have.cusd1.median():,.0f}")
    gm = have.xocc.mean(); vm = have.xvcc.mean()
    g = [("mean >= +20bp", gm >= 2e-3), ("median > 0", have.xocc.median() > 0),
         ("day-clustered t >= 2", None), ("ex-top-5 mean > 0", np.sort(have.xocc.values)[:-5].mean() > 0)]
    day = have.groupby("date").xocc.mean(); t = day.mean() / day.std() * np.sqrt(len(day))
    g[2] = (g[2][0], t >= 2)
    half = gm >= 0.5 * vm
    L.append("")
    L.append("== GATE ==")
    for k, v in g:
        L.append(f"{k}: {'PASS' if v else 'FAIL'}")
    L.append(f"official effect >= half vendor-bar effect (official {gm*1e4:+.1f} vs vendor matched {vm*1e4:+.1f}): {'PASS' if half else 'FAIL'}")
    L.append("VERDICT: " + ("PASS" if all(v for _, v in g) and half else "KILL"))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
