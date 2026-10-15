"""Study GUF-LOW (N 882): short >= 5% gap-ups with low FINRA days-to-cover, 09:31 VWAP -> 15:59; judge 2016-01..2020-10.

    PYTHONPATH=. .venv/bin/python -m research.sim.guf_low si          # FINRA consolidated SI 2015-11..2020-10 (key-less)
    PYTHONPATH=. .venv/bin/python -m research.sim.guf_low fetch [w W] # raw SIP 1-min for gap-up candidate days
    PYTHONPATH=. .venv/bin/python -m research.sim.guf_low             # judge -> guf_low_out.txt
"""
from __future__ import annotations

import pathlib
import sys
import time

import numpy as np
import pandas as pd
import requests

from . import ssr_rd as m

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/guf"
OUT = pathlib.Path(__file__).with_name("guf_low_out.txt")
URL = "https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest"
START, END = "2016-01-01", "2020-10-31"


def fetch_si():
    (D / "si").mkdir(parents=True, exist_ok=True)
    for mo in pd.date_range("2017-12-01", "2020-10-01", freq="MS"):
        f = D / "si" / f"{mo.date()}.parquet"
        if f.exists():
            continue
        rows, off = [], 0
        while True:
            q = {"limit": 5000, "offset": off, "fields": ["symbolCode", "daysToCoverQuantity", "settlementDate"],
                 "dateRangeFilters": [{"fieldName": "settlementDate", "startDate": str(mo.date()),
                                       "endDate": str((mo + pd.offsets.MonthEnd(1)).date())}]}
            for a in range(10):
                try:
                    r = requests.post(URL, json=q, headers={"Accept": "application/json"}, timeout=60)
                    if r.status_code == 200:
                        break
                except requests.RequestException as ex:
                    print("err", mo.date(), str(ex)[:80], flush=True)
                time.sleep(10 * (a + 1))
            j = r.json() if r.text.strip() else []
            rows += j
            if len(j) < 5000:
                break
            off += 5000
        if not rows:
            print("EMPTY", mo.date(), flush=True)
            continue
        pd.DataFrame(rows).to_parquet(f)
        print(mo.date(), len(rows), flush=True)


def events() -> pd.DataFrame:
    b = m.load()
    g = b.groupby("ticker", sort=False)
    b["G"] = b.open / g.close.shift(1) - 1
    b["praw"] = g.closeunadj.shift(1)
    b["adv"] = (b.close * b.volume).groupby(b.ticker).transform(
        lambda s: s.shift(1).rolling(20, min_periods=15).mean())
    e = b[(b.praw >= 3) & (b.adv >= 5e6) & (b.G >= 0.045) & (b.date >= START) & (b.date <= END)
          & b.ticker.str.fullmatch(r"[A-Z]{1,5}")]
    return e[["ticker", "date", "G", "adv", "praw", "closeunadj"]].reset_index(drop=True)


def fetch(w=0, W=1):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    (D / "m1").mkdir(parents=True, exist_ok=True)
    ef = D / "events.parquet"
    if not ef.exists():
        events().to_parquet(ef)
    e = pd.read_parquet(ef)
    c, _ = _clients()
    for i, (d, x) in enumerate(e.groupby("date")):
        p = D / "m1" / f"{pd.Timestamp(d).date()}.parquet"
        if p.exists() or i % W != w:
            continue
        syms = sorted(set(x.ticker))
        s = (pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
        f = (pd.Timestamp(d) + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
        for a in range(8):
            try:
                df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=s,
                                                       end=f, feed="sip", adjustment="raw")).df
                df.reset_index().to_parquet(p)
                break
            except Exception as ex:  # noqa: BLE001
                msg = str(ex)
                print("err", d, msg[:100], flush=True)
                if "invalid symbol:" in msg:
                    bad = msg.split("invalid symbol:")[1].split('"')[0].strip()
                    syms = [y for y in syms if y != bad]
                    if not syms:
                        break
                    continue
                time.sleep(5 * (a + 1))
        if i % 100 == 0:
            print(i, d, flush=True)
    print("DONE", flush=True)


def ct(x, dates):
    dm = x.groupby(np.asarray(dates)).mean()
    return dm.mean(), dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))), len(dm), dm


def judge():
    e = pd.read_parquet(D / "events.parquet")
    out, bad = [], 0
    for d, x in e.groupby("date"):
        p = D / "m1" / f"{pd.Timestamp(d).date()}.parquet"
        if not p.exists():
            continue
        b = pd.read_parquet(p)
        if "timestamp" not in b:
            continue
        ts = pd.to_datetime(b.timestamp).dt.tz_convert("America/New_York")
        b["mi"] = (ts.dt.hour - 9) * 60 + ts.dt.minute - 30
        b = b[(b.mi >= 0) & (b.mi < 390)]
        for r in x.itertuples():
            s = b[b.symbol == r.ticker].set_index("mi").sort_index()
            if len(s) < 30 or s.index.min() > 0 or 1 not in s.index or 389 - s.index.max() > 5 \
                    or abs(s.close.iloc[-1] / r.closeunadj - 1) > 0.01:
                bad += 1
                continue
            g = s.open.iloc[0] / r.praw - 1
            if g < 0.05:
                continue
            en = s.vwap.loc[1]
            out.append(dict(date=pd.Timestamp(d), sym=r.ticker, gap=g, adv=r.adv, praw=r.praw,
                            r=s.close.iloc[-1] / en - 1, maxup=s.high.loc[1:].max() / en - 1))
    r = pd.DataFrame(out).sort_values("date")
    si = pd.concat(pd.read_parquet(f) for f in sorted((D / "si").glob("*.parquet")))
    si["avail"] = pd.to_datetime(si.settlementDate) + pd.offsets.BDay(10)
    si = si.rename(columns={"symbolCode": "sym", "daysToCoverQuantity": "dtc"})[["sym", "avail", "dtc"]].sort_values("avail")
    r["date"] = r.date.astype("datetime64[ns]")
    si["avail"] = si.avail.astype("datetime64[ns]")
    r = pd.merge_asof(r, si, left_on="date", right_on="avail", by="sym", direction="backward",
                      tolerance=pd.Timedelta(days=45))
    r["arm"] = np.where(r.dtc >= 5, "HIGH", np.where(r.dtc >= 2, "MID", np.where(r.dtc >= 0, "LOW", "NA")))
    r["sn"] = -r.r - 0.002
    x0 = r[r.date < "2018-01-01"]
    r = r[r.date >= pd.Timestamp(si.avail.min())]
    L = []
    pr = lambda s_: (print(s_), L.append(s_))  # noqa: E731
    pr(f"GUF-LOW judge {r.date.min().date()}..2020-10: gap-ups {len(r)} (dropped {bad}); arms {r.arm.value_counts().to_dict()}")
    m0, t0, n0, _ = ct(x0.sn, x0.date)
    pr(f"descriptive 2016-17 ALL-DTC short: n {len(x0)} EWday {m0*1e4:+.1f}bp t {t0:+.2f} trade med {x0.sn.median()*1e4:+.1f}")
    for nm, q in [("LOW PRIMARY", r.arm == "LOW"), ("LOW liquid $10/$20M", (r.arm == "LOW") & (r.praw >= 10) & (r.adv >= 2e7)),
                  ("MID", r.arm == "MID"), ("HIGH", r.arm == "HIGH"), ("NA", r.arm == "NA")]:
        x = r[q]
        if len(x) < 30:
            continue
        mu, t, nd, dm = ct(x.sn, x.date)
        h1, h2 = x.sn[x.date < "2020-01-01"].mean(), x.sn[x.date >= "2020-01-01"].mean()
        win, los = x.sn[x.sn > 0], x.sn[x.sn <= 0]
        yrs = " ".join(f"{y}:{v*1e4:+.0f}" for y, v in x.sn.groupby(x.date.dt.year).mean().items())
        pr(f"\n{nm}: n {len(x)} days {nd} ({len(x)/max(nd,1):.1f}/day) | SHORT net EWday {mu*1e4:+.1f}bp t {t:+.2f} | trade "
           f"mean {x.sn.mean()*1e4:+.1f} med {x.sn.median()*1e4:+.1f} hit {(x.sn>0).mean():.2f} | ex-top5 "
           f"{dm.sort_values().iloc[:-5].mean()*1e4:+.1f} | halves {h1*1e4:+.1f} / {h2*1e4:+.1f} | 25bp/side "
           f"{(-x.r-0.005).mean()*1e4:+.1f}")
        pr(f"   med win {win.median()*1e4:+.0f} med loss {los.median()*1e4:+.0f} worst trade {x.sn.min()*1e4:+.0f} "
           f"share losing >20% {(x.sn<-0.2).mean():.3f} worst day {dm.min()*1e4:+.0f} | p90 adverse {x.maxup.quantile(.9)*1e4:+.0f} | {yrs}")
    lo = r[r.arm == "LOW"].groupby("date").sn.mean()
    hi = r[r.arm == "HIGH"].groupby("date").sn.mean()
    diff = lo.mean() - hi.mean()
    se = np.sqrt(lo.var() / len(lo) + hi.var() / len(hi))
    pr(f"\nLOW short - HIGH short (EW-day pooled): {diff*1e4:+.1f}bp t {diff/se:+.2f}")
    r.to_parquet(D / "rows.parquet")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    if a == "si":
        fetch_si()
    elif a == "fetch":
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        judge()
