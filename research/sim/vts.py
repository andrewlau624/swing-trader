"""Study VTS runner (pre-reg research/drafts/round1_prose.md N 859->860).

VIX term-structure state as an options sensor: contango -> LONG SPY, inversion -> SHORT SPY.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.vts
"""
from __future__ import annotations

import json
import pathlib
import urllib.request

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/vts_out.txt"
CACHEDIR = ROOT / "data/research/cot"
CACHEDIR.mkdir(parents=True, exist_ok=True)
B = 1e4


def yahoo(sym: str) -> pd.Series:
    f = CACHEDIR / f"y_{sym.replace('^', '')}.parquet"
    if f.exists():
        return pd.read_parquet(f)["close"]
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           f"?period1=0&period2={int(pd.Timestamp.now().timestamp())}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.load(r)
    res = j["chart"]["result"][0]
    ts = res["timestamp"]
    c = res["indicators"]["quote"][0]["close"]
    s = pd.Series(c, index=pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None), name="close").dropna()
    s.index = s.index.astype("datetime64[ns]")
    s = s[~s.index.duplicated()]
    s.to_frame().to_parquet(f)
    return s


def spot() -> pd.DataFrame:
    from sharadar import prices as SP
    p = SP(["SPY"], adjust="raw").reset_index()
    p["date"] = p["date"].astype("datetime64[ns]")
    return p.set_index("date")[["open", "close"]].astype(float)


def main():
    import urllib.parse  # noqa: F401
    v9, v3, v6, vx = yahoo("^VIX9D"), yahoo("^VIX3M"), yahoo("^VIX6M"), yahoo("^VIX")
    S = spot()
    idx = v9.index.union(v3.index).union(S.index).astype("datetime64[ns]")
    D = pd.DataFrame({
        "r93": v3.reindex(idx) / v9.reindex(idx),
        "r63": v6.reindex(idx) / v3.reindex(idx),
        "o": S["open"].reindex(idx), "c": S["close"].reindex(idx),
    }, index=idx).dropna(subset=["r93"])
    D["contango"] = D["r93"] >= 1.10
    D["inversion"] = D["r93"] <= 0.98
    D["oc1"] = D["c"].shift(-1) / D["o"].shift(-1) - 1
    D["oo5"] = D["o"].shift(-6) / D["o"].shift(-1) - 1
    D["oo1"] = D["o"].shift(-2) / D["o"].shift(-1) - 1
    D = D[D.index >= "2007-01-01"]

    parts = ["Study VTS: VIX term-structure state as options sensor",
             "contango VIX3M/VIX9D>=1.10 -> LONG SPY next O->C; inversion <=0.98 -> SHORT; frozen thresholds",
             "net at 1bp/side; shock 3bp/side", ""]
    for name, mask, dr in (("contango_long", D["contango"], 1.0), ("inversion_short", D["inversion"], -1.0)):
        sub = D[mask].dropna(subset=["oc1"]).copy()
        for h, col in (("1d_oc", "oc1"), ("5d_oo", "oo5")):
            x = sub.dropna(subset=[col]).copy()
            if len(x) < 100:
                parts.append(f"  {name:16s} {h} n={len(x)} (too few)"); continue
            x["net"] = dr * x[col] - 2e-4
            x["shk"] = dr * x[col] - 6e-4
            g = x.groupby(x.index)["net"].mean()
            t = g.mean() / g.std() * np.sqrt(len(g)) if g.std() > 0 else np.nan
            x = x.sort_index()
            k = len(x) // 2
            parts.append(f"  {name:16s} {h} n={len(x):5d} net={x['net'].mean()*B:6.2f}bp t={t:5.2f} "
                         f"med={x['net'].median()*B:6.2f} ex5={x.nsmallest(max(len(x)-5,1),'net')['net'].mean()*B:6.2f} "
                         f"halves={x['net'].iloc[:k].mean()*B:6.2f}/{x['net'].iloc[k:].mean()*B:6.2f} "
                         f"shock={x['shk'].mean()*B:6.2f} hit={(x['net']>0).mean()*100:3.0f}% "
                         f"freq={len(x)/len(D)*100:4.1f}%")
    # unconditional reference
    x = D.dropna(subset=["oc1"])
    g = x.groupby(x.index)["oc1"].mean()
    parts.append(f"  (uncond oc1 mean={x['oc1'].mean()*B:.2f}bp t={g.mean()/g.std()*np.sqrt(len(g)):.2f}; "
                 f"condango days {D['contango'].mean()*100:.0f}%, inversion {D['inversion'].mean()*100:.0f}%)")
    # per-year stability of the two arms
    for name, mask, dr in (("contango_long", D["contango"], 1.0), ("inversion_short", D["inversion"], -1.0)):
        x = D[mask].dropna(subset=["oc1"]).copy()
        x["net"] = dr * x["oc1"] - 2e-4
        yr = x.groupby(x.index.year)["net"].mean() * B
        parts.append(f"  {name}: per-year " + " ".join(f"{y}:{v:+.0f}" for y, v in yr.items()))
    text = "\n".join(parts) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
