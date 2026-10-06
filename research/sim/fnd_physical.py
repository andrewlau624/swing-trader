"""Study FND: physically-settled commodity futures around first-notice day (pre-reg study_fnd_physical.md).

Object = the nearby/deferred calendar spread, around the appearance of physical-delivery
constraints (first notice day, FND ~ the 25th of the month preceding the delivery month for CL;
for NG ~ the last business day of the month preceding delivery). LTD (last trade day) is the
contract `expiration`. FND is hardcoded as the standard calendar rule (not fitted).

Data: Databento GLBX.MDP3 ohlcv-1d (individual CL/NG contracts, 2011-2025) + definition (expiry).
Run: PYTHONPATH=. .venv/bin/python -m research.sim.fnd_physical
"""
from __future__ import annotations

import os
import pathlib
import re

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/fnd_physical_out.txt"
MON = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6, "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}
TICK = {"CL": 0.01, "NG": 0.001}


def last_trade_dates():
    """From the cached definition would be ideal; here derive from the daily data (last date a
    contract's F1 identity flips) — but FND needs the exchange calendar. Use the known rule:
    CL FND = the 25th of the month preceding delivery (roll to next business day if holiday);
    contract `expiration` (from definition) is LTD. Hardcode FND from delivery month."""
    pass


def fnd_for(root, deliv_year, deliv_month):
    # CL: first notice day ~ 25th of the month BEFORE delivery. NG: last business day of the
    # month BEFORE delivery. Both shift to the next business day; approximate with the 25th / month-end.
    m = deliv_month - 1
    y = deliv_year
    if m == 0:
        m, y = 12, y - 1
    if root == "CL":
        d = pd.Timestamp(year=y, month=m, day=25)
    else:  # NG
        d = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
    # next business day
    return d + pd.offsets.BDay(0)


def load(root):
    d = pd.read_parquet(ROOT / "data/research/program" / f"glbx_{root}_daily.parquet")
    d["date"] = pd.to_datetime(d["ts_event"], utc=True).dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    pat = re.compile(rf"^{root}([FGHJKMNQUVXZ])(\d)$")
    keep = []
    for sym, g in d.groupby("symbol"):
        m = pat.match(str(sym))
        if not m:
            continue
        mo = MON[m.group(1)]
        yy = 2010 + int(m.group(2))
        keep.append(pd.DataFrame({"date": g["date"].values, "sym": sym, "close": g["close"].values,
                                  "volume": g["volume"].values, "oi": g.get("oi", pd.Series(dtype=float)).values if "oi" in g else np.nan,
                                  "exp": yy * 100 + mo, "mo": mo, "yy": yy}))
    return pd.concat(keep) if keep else pd.DataFrame()


def study(root):
    d = load(root)
    rows = []
    b = 1e4
    for date, g in d.groupby("date"):
        g = g[g.close > 0].sort_values("exp")
        if len(g) < 2:
            continue
        f1, f2 = g.iloc[0], g.iloc[1]
        rows.append(dict(date=date, f1=f1.sym, mo=f1.mo, yy=f1.yy, f2c=f2.close,
                         sp=(f1.close - f2.close) / f2.close, sp_abs=f1.close - f2.close,
                         f1v=f1.volume, f2v=f2.volume))
    R = pd.DataFrame(rows).set_index("date").sort_index()
    # event: for each front contract, FND from its delivery month
    ev = []
    idx = R.index
    for (mo, yy), g in R.groupby(["mo", "yy"]):
        fnd = fnd_for(root, yy, mo)
        j = idx.searchsorted(fnd)
        if j < 21 or j + 10 >= len(idx):
            continue
        if g["f1"].iloc[0] != g["f1"].iloc[-1]:
            continue  # the front changed inside the window -> skip (roll happened already)
        r_pre = (R["sp"].iloc[j] - R["sp"].iloc[j - 20]) * b            # 20d into FND
        r_pre5 = (R["sp"].iloc[j] - R["sp"].iloc[j - 5]) * b
        r_post5 = (R["sp"].iloc[j + 5] - R["sp"].iloc[j]) * b
        r_post10 = (R["sp"].iloc[j + 10] - R["sp"].iloc[j]) * b
        ev.append(dict(fnd=fnd, r_pre=r_pre, r_pre5=r_pre5, r_post5=r_post5, r_post10=r_post10))
    E = pd.DataFrame(ev)
    lines = [f"===== {root}  events={len(E)}  (spread = nearby - deferred, bp of deferred)"]
    if E.empty:
        return "\n".join(lines) + "\n", None

    def line(x, lab):
        x = x.dropna()
        if len(x) < 8:
            return f"  {lab:22s} n={len(x)}"
        t = x.mean() / x.std() * np.sqrt(len(x))
        return (f"  {lab:22s} n={len(x):3d} mean={x.mean():7.1f}bp med={x.median():7.1f} "
                f"t={t:5.2f} hit={(x>0).mean()*100:3.0f}% ex5={x.sort_values().iloc[:-5].mean():7.1f}" if len(x) > 10
                else f"  {lab:22s} n={len(x):3d} mean={x.mean():7.1f}bp")

    lines += [line(E["r_pre"], "spread -20d->FND"),
              line(E["r_pre5"], "spread -5d->FND"),
              line(E["r_post5"], "spread FND->+5d"),
              line(E["r_post10"], "spread FND->+10d")]
    return "\n".join(lines) + "\n", E


def main():
    parts = ["Study FND: physically-settled CL/NG calendar spread around first notice day",
             "FND = 25th (CL) / month-end (NG) of the month BEFORE delivery; spread = nearby - deferred,",
             "bp of the deferred price. Pre>0/post<0 would be a delivery-constraint signature.", ""]
    for root in ["CL", "NG"]:
        txt, E = study(root)
        parts.append(txt)
    text = "\n".join(parts) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
