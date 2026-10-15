"""Study SQZ (N 881): gap-ups >= 5% split by FINRA days-to-cover; long 09:31 VWAP -> 15:59 close.

    PYTHONPATH=. .venv/bin/python -m research.sim.sqz      # -> sqz_out.txt

Minute bars: data/research/night/gm1 (adjustment=all; ratios within a day are unaffected). Prior close: the same-adjusted
daily panel (data/research/night/panel.py). Short interest usable from settlementDate + 10 business days.
"""
from __future__ import annotations

import glob
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
N = ROOT / "data/research/night"
OUT = pathlib.Path(__file__).with_name("sqz_out.txt")
sys.path.insert(0, str(N))


def si() -> pd.DataFrame:
    f = [x for x in glob.glob(str(N / "finra_si" / "*.parquet"))]
    s = pd.concat(pd.read_parquet(x) for x in f)
    s["avail"] = pd.to_datetime(s.settlementDate) + pd.offsets.BDay(10)
    return s.rename(columns={"symbolCode": "sym", "daysToCoverQuantity": "dtc"})[["sym", "avail", "dtc"]].sort_values("avail")


def rows() -> pd.DataFrame:
    from panel import panel
    C = panel()["close"]
    out = []
    for f in sorted(glob.glob(str(N / "gm1" / "*.parquet"))):
        d = pd.Timestamp(pathlib.Path(f).stem)
        if d not in C.index:
            continue
        i = C.index.get_loc(d)
        if i == 0:
            continue
        pc = C.iloc[i - 1]
        b = pd.read_parquet(f)
        ts = pd.to_datetime(b.timestamp).dt.tz_convert("America/New_York")
        b["mi"] = (ts.dt.hour - 9) * 60 + ts.dt.minute - 30
        b = b[(b.mi >= 0) & (b.mi < 390)]
        for sym, s in b.groupby("symbol"):
            s = s.set_index("mi").sort_index()
            if s.index.min() > 0 or 1 not in s.index or 389 - s.index.max() > 5 or sym not in pc.index or not pc[sym] > 0:
                continue
            g = s.open.iloc[0] / pc[sym] - 1
            if g < 0.05:
                continue
            en = s.vwap.loc[1]
            out.append(dict(date=d, sym=sym, gap=g, r=s.close.iloc[-1] / en - 1))
    return pd.DataFrame(out)


def ct(x, dates):
    dm = x.groupby(np.asarray(dates)).mean()
    return dm.mean(), dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))), len(dm), dm


def main():
    r = rows().sort_values("date")
    s = si()
    r = pd.merge_asof(r, s, left_on="date", right_on="avail", by="sym", direction="backward",
                      tolerance=pd.Timedelta(days=45))
    r["arm"] = np.where(r.dtc >= 5, "HIGH", np.where(r.dtc >= 2, "MID", np.where(r.dtc >= 0, "LOW", "NA")))
    r["net"] = r.r - 0.002
    L = []
    pr = lambda s_: (print(s_), L.append(s_))  # noqa: E731
    pr(f"SQZ gap-ups >= 5%: {len(r)} ({r.date.min().date()} .. {r.date.max().date()}); arms {r.arm.value_counts().to_dict()}")
    for a in ["HIGH", "MID", "LOW", "NA"]:
        x = r[r.arm == a]
        if len(x) < 30:
            continue
        mu, t, nd, dm = ct(x.net, x.date)
        h1, h2 = x.net[x.date < "2024-01-01"].mean(), x.net[x.date >= "2024-01-01"].mean()
        win, los = x.net[x.net > 0], x.net[x.net <= 0]
        yrs = " ".join(f"{y}:{v*1e4:+.0f}" for y, v in x.net.groupby(x.date.dt.year).mean().items())
        pr(f"\n{a}: n {len(x)} days {nd} | net EWday {mu*1e4:+.1f}bp t {t:+.2f} | trade mean {x.net.mean()*1e4:+.1f} "
           f"med {x.net.median()*1e4:+.1f} hit {(x.net>0).mean():.2f} | ex-top5 {dm.sort_values().iloc[:-5].mean()*1e4:+.1f} "
           f"| halves {h1*1e4:+.1f} / {h2*1e4:+.1f} | 20bp/side {(x.r-0.004).mean()*1e4:+.1f}")
        pr(f"   med win {win.median()*1e4:+.0f} med loss {los.median()*1e4:+.0f} worst trade {x.net.min()*1e4:+.0f} "
           f"worst day {dm.min()*1e4:+.0f} | median gap {x.gap.median():.3f} | {yrs}")
    hi = r[r.arm == "HIGH"].groupby("date").net.mean()
    lo = r[r.arm == "LOW"].groupby("date").net.mean()
    pd_ = (hi - lo).dropna()
    pooled = hi.mean() - lo.mean()
    se = np.sqrt(hi.var() / len(hi) + lo.var() / len(lo))
    pr(f"\nHIGH - LOW: paired days {len(pd_)} diff {pd_.mean()*1e4:+.1f}bp t {pd_.mean()/(pd_.std()/np.sqrt(len(pd_))):+.2f} | "
       f"pooled EW-day diff {pooled*1e4:+.1f}bp t {pooled/se:+.2f}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
