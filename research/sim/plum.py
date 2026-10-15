"""Study PLUM runner (pre-reg research/drafts/round1_prose.md N 864).

Daily financing-plumbing stress states (SOFR-DTB3 / SOFR-IORB) -> next-session equity.
Gate research for the book's -10% lever; judged first as standalone states.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.plum
"""
from __future__ import annotations

import pathlib
import urllib.request

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/plum_out.txt"
CACHEDIR = ROOT / "data/research/fred"
CACHEDIR.mkdir(parents=True, exist_ok=True)
B = 1e4


def fred(series: str) -> pd.Series:
    f = CACHEDIR / f"{series}.csv"
    if not f.exists():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
        urllib.request.urlretrieve(url, f)
    d = pd.read_csv(f)
    s = pd.Series(pd.to_numeric(d[series], errors="coerce").values,
                  index=pd.to_datetime(d["observation_date"]).values, name=series).dropna()
    s.index = s.index.astype("datetime64[ns]")
    return s


def spot() -> pd.DataFrame:
    from sharadar import prices as SP
    p = SP(["SPY"], adjust="raw").reset_index()
    p["date"] = p["date"].astype("datetime64[ns]")
    return p.set_index("date")[["open", "close"]].astype(float)


def main():
    sofr, dtb3, iorb = fred("SOFR"), fred("DTB3"), fred("IORB")
    S = spot()
    idx = sofr.index.union(dtb3.index).union(iorb.index).union(S.index).astype("datetime64[ns]")
    idx = idx[idx >= pd.Timestamp("2018-04-03")]
    D = pd.DataFrame({
        "sofr": sofr.reindex(idx), "dtb3": dtb3.reindex(idx), "iorb": iorb.reindex(idx),
        "o": S["open"].reindex(idx), "c": S["close"].reindex(idx),
    }, index=idx)
    # forward-fill FRED holiday gaps only for rates (unchanged rates), NOT for SPY
    D[["sofr", "dtb3", "iorb"]] = D[["sofr", "dtb3", "iorb"]].ffill()
    D["s1"] = (D["sofr"] - D["dtb3"]) >= 0.25
    D["s2"] = (D["sofr"] - D["iorb"]) >= 0.15
    D["qe"] = D.index.is_quarter_end | (D.index.shift(1, freq="B").is_quarter_end)
    D["oc1"] = D["c"].shift(-1) / D["o"].shift(-1) - 1
    D["oo3"] = D["o"].shift(-4) / D["o"].shift(-1) - 1
    D = D.dropna(subset=["o", "c"])

    parts = ["Study PLUM: daily financing-plumbing stress states -> next-session SPY",
             "S1 = SOFR-DTB3 >= 25bp; S2 = SOFR-IORB >= 15bp; S3 = S1 x quarter-end",
             "BOTH directions judged (short=forced-unwind continuation, long=relief); net 1bp/side",
             f"window {D.index.min().date()}..{D.index.max().date()} n={len(D)}", ""]
    for st in ("s1", "s2", "s3"):
        if st == "s3":
            mask = D["s1"] & D["qe"]
        else:
            mask = D[st]
        sub = D[mask].dropna(subset=["oc1"])
        n = len(sub)
        if n == 0:
            parts.append(f"  {st}: no events"); continue
        line = [f"  {st}: n={n} freq={n/len(D)*100:.1f}% dates {sub.index.min().date()}..{sub.index.max().date()}"]
        for arm, dr in (("long", 1.0), ("short", -1.0)):
            for h, col in (("1d_oc", "oc1"), ("3d_oo", "oo3")):
                x = sub.dropna(subset=[col]).copy()
                x["net"] = dr * x[col] - 2e-4
                g = x.groupby(x.index)["net"].mean()
                t = g.mean() / g.std() * np.sqrt(len(g)) if len(g) > 2 and g.std() > 0 else np.nan
                x = x.sort_index()
                k = len(x) // 2
                line.append(f"    {arm:5s} {h} net={x['net'].mean()*B:6.1f}bp t={t:5.2f} med={x['net'].median()*B:6.1f} "
                            f"halves={x['net'].iloc[:k].mean()*B:6.1f}/{x['net'].iloc[k:].mean()*B:6.1f} hit={(x['net']>0).mean()*100:3.0f}%")
        parts += line
        parts.append("    events: " + " ".join(str(d.date()) for d in sub.index[-12:]))
    x = D.dropna(subset=["oc1"])
    g = x.groupby(x.index)["oc1"].mean()
    parts.append(f"  uncond oc1={x['oc1'].mean()*B:.2f}bp t={g.mean()/g.std()*np.sqrt(len(g)):.2f}")
    text = "\n".join(parts) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
