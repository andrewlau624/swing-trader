import os, sys
sys.path.insert(0, "/Users/andrewlau/Documents/Code/Projects/swing-trader")
os.chdir("/Users/andrewlau/Documents/Code/Projects/swing-trader")
from dotenv import dotenv_values
import databento as db, pandas as pd, numpy as np

c = db.Historical(dotenv_values(".env")["DATABENTO_API_KEY"])
OUT = "data/research/program/fnd_oi_out.txt"

def oi_series(root):
    """Open interest (stat_type 9) per (date, contract) from GLBX statistics, 2011-2025."""
    f = f"data/research/program/{root}_oi.parquet"
    if os.path.exists(f):
        return pd.read_parquet(f)
    df = c.timeseries.get_range(dataset="GLBX.MDP3", schema="statistics", symbols=f"{root}.FUT",
                                stype_in="parent", start="2011-01-01", end="2026-01-01").to_df().reset_index()
    df = df[df["stat_type"] == 9].copy()
    df["date"] = pd.to_datetime(df["ts_ref"], utc=True, errors="coerce").dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    df = df[df["date"].notna()][["date", "symbol", "quantity"]].rename(columns={"quantity": "oi"})
    df = df.dropna().groupby(["date", "symbol"], as_index=False)["oi"].last()
    df.to_parquet(f)
    return df

MON = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6, "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}
import re

def study(root, fnd_rule):
    oi = oi_series(root)
    oi["sym"] = oi["symbol"].astype(str)
    pat = re.compile(rf"^{root}([FGHJKMNQUVXZ])(\d)$")
    keep = []
    for s in oi["sym"].unique():
        m = pat.match(s)
        if m:
            keep.append((s, MON[m.group(1)], 2010 + int(m.group(2))))
    kmap = {s: (mo, yy) for s, mo, yy in keep}
    oi = oi[oi["sym"].isin(kmap)]
    pivot = oi.pivot_table(index="date", columns="sym", values="oi", aggfunc="last")
    letters = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M", 7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
    res = {h: [] for h in [-20, -10, -5, -2, 0, 2, 5, 10]}
    for (mo, yy) in sorted(set(kmap.values())):
        f1 = f"{root}{letters[mo]}{yy % 10}"
        f2mo = mo % 12 + 1
        f2 = f"{root}{letters[f2mo]}{(yy + (1 if f2mo == 1 else 0)) % 10}"
        if f1 not in pivot.columns or f2 not in pivot.columns:
            continue
        fnd = fnd_rule(yy, mo)
        idx = pivot.index
        j = idx.searchsorted(fnd)
        if j < 25 or j + 12 >= len(idx):
            continue
        # OI migration: nearby share = OI(f1)/(OI(f1)+OI(f2))
        for h in res:
            k = j + h
            if 0 <= k < len(idx):
                v1, v2 = pivot[f1].iloc[k], pivot[f2].iloc[k]
                if v1 and v2 and (v1 + v2) > 0:
                    res[h].append(v1 / (v1 + v2))
    lines = [f"{root}: nearby OI share by days-to-FND (physical-settled if CL/NG)"]
    for h in sorted(res):
        x = np.array(res[h])
        if len(x):
            lines.append(f"  FND{h:+3d}: share={x.mean():.3f} n={len(x)}")
    return "\n".join(lines) + "\n"

def cl_fnd(yy, mo):
    m, y = (mo - 1, yy) if mo > 1 else (12, yy - 1)
    return (pd.Timestamp(year=y, month=m, day=25) + pd.offsets.BDay(0))

def ng_fnd(yy, mo):
    m, y = (mo - 1, yy) if mo > 1 else (12, yy - 1)
    return pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)

def es_fnd(yy, mo):
    # equity index: roll into the 3rd Friday; approximate FND-equivalent = 8 days before expiry
    # (used only as a FINANCIAL control). Use the 3rd Friday of the month BEFORE delivery.
    m, y = (mo - 1, yy) if mo > 1 else (12, yy - 1)
    d = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.Week(weekday=4) + pd.offsets.Week(2)
    return d

if __name__ == "__main__":
    txt = ("FND open-interest migration: nearby share = OI(near)/(OI(near)+OI(next))\n"
           "Physically-settled CL/NG vs financially-settled ES (control).\n\n")
    txt += study("CL", cl_fnd)
    txt += "\n" + study("NG", ng_fnd)
    txt += "\n" + study("ES", es_fnd)
    open(OUT, "w").write(txt)
    print(txt)
