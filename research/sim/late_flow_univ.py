"""LATE-FLOW universe from CRSP dsf (all inputs strictly before d): common 10/11, exch 1/2/3, prior |close|>=5, top 1000 by 20d median $vol."""
import numpy as np, pandas as pd
D = "data/research/late_flow/"
def load():
    f = pd.read_parquet(D + "dsf.parquet")
    for c in ("prc", "openprc", "ret", "vol", "shrout"): f[c] = pd.to_numeric(f[c], errors="coerce").astype("float64")
    f["permno"] = f.permno.astype("int64"); f = f.sort_values(["permno", "date"]).reset_index(drop=True)
    f["ap"] = f.prc.abs(); f["dv"] = f.ap * f.vol
    g = f.groupby("permno")
    f["adv_sh"] = g.vol.transform(lambda s: s.shift(1).rolling(20, min_periods=15).median())
    f["adv_dv"] = g.dv.transform(lambda s: s.shift(1).rolling(20, min_periods=15).median())
    f["pclose"] = g.ap.shift(1); f["pdate"] = g.date.shift(1)
    return f
def names():
    n = pd.read_parquet(D + "names.parquet"); n["permno"] = n.permno.astype("int64"); return n
def universe(f, nm, d):
    x = f[f.date == d].dropna(subset=["adv_dv", "pclose"])
    x = x[(x.pclose >= 5) & (x.adv_dv > 0) & (x.adv_sh > 0)]
    nn = nm[(nm.namedt <= d) & (nm.nameendt >= d) & nm.shrcd.isin([10, 11]) & nm.exchcd.isin([1, 2, 3])]
    x = x[x.permno.isin(nn.permno)]
    return x.nlargest(1000, "adv_dv")
