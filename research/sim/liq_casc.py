"""Study LIQ-CASC (N 883): fade perp liquidation cascades (OI drop + price move) in BTC/ETH.

    PYTHONPATH=. .venv/bin/python -m research.sim.liq_casc fetch   # Binance UM metrics zips + Alpaca ETH 1-min
    PYTHONPATH=. .venv/bin/python -m research.sim.liq_casc         # judge -> liq_casc_out.txt

BTC 1-min prices are reused from data/research/btc_fix (Alpaca BTC/USD).
"""
from __future__ import annotations

import io
import pathlib
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/liq_casc"
OUT = pathlib.Path(__file__).with_name("liq_casc_out.txt")
U = "https://data.binance.vision/data/futures/um/daily/metrics/{s}/{s}-metrics-{d}.zip"
DAYS = pd.date_range("2021-12-01", "2026-09-30")


def _one(sd):
    s, d = sd
    try:
        r = requests.get(U.format(s=s, d=d.date()), timeout=60)
        if r.status_code != 200:
            return None
        z = zipfile.ZipFile(io.BytesIO(r.content))
        return pd.read_csv(z.open(z.namelist()[0]))[["create_time", "sum_open_interest"]]
    except Exception:  # noqa: BLE001
        return None


def fetch():
    D.mkdir(parents=True, exist_ok=True)
    for s in ["BTCUSDT", "ETHUSDT"]:
        f = D / f"{s}_oi.parquet"
        if f.exists():
            continue
        with ThreadPoolExecutor(16) as ex:
            parts = [p for p in ex.map(_one, [(s, d) for d in DAYS]) if p is not None]
        x = pd.concat(parts)
        x.to_parquet(f)
        print(s, len(parts), "days", len(x), "rows", flush=True)
    f = D / "eth_1m.parquet"
    if not f.exists():
        from alpaca.data.historical import CryptoHistoricalDataClient
        from alpaca.data.requests import CryptoBarsRequest
        from alpaca.data.timeframe import TimeFrame
        c = CryptoHistoricalDataClient()
        parts = []
        for m in pd.date_range("2021-12-01", "2026-09-01", freq="MS"):
            parts.append(c.get_crypto_bars(CryptoBarsRequest(
                symbol_or_symbols="ETH/USD", timeframe=TimeFrame.Minute, start=m.tz_localize("UTC"),
                end=(m + pd.offsets.MonthBegin(1)).tz_localize("UTC"))).df.reset_index())
        pd.concat(parts).to_parquet(f)
        print("eth 1m done", flush=True)


def prices(sym):
    if sym == "BTCUSDT":
        b = pd.concat(pd.read_parquet(f) for f in sorted((ROOT / "data/research/btc_fix").glob("*.parquet")))
    else:
        b = pd.read_parquet(D / "eth_1m.parquet")
    px = b.assign(ts=pd.to_datetime(b.timestamp, utc=True)).set_index("ts").close.sort_index()
    px = px[~px.index.duplicated()]
    return px.resample("1min").last().ffill()


def events(sym):
    oi = pd.read_parquet(D / f"{sym}_oi.parquet")
    oi["ts"] = pd.to_datetime(oi.create_time, utc=True)
    oi = oi.drop_duplicates("ts").set_index("ts").sum_open_interest.sort_index()
    oi = oi.resample("5min").last()
    px = prices(sym)
    p5 = px.reindex(oi.index)
    doi = oi / oi.shift(3) - 1
    dpx = p5 / p5.shift(3) - 1
    df = pd.DataFrame({"doi": doi, "dpx": dpx}).dropna()
    out = []
    for kind, q in [("LONG-LIQ", (df.doi <= -0.03) & (df.dpx <= -0.015)), ("SHORT-SQZ", (df.doi <= -0.03) & (df.dpx >= 0.015)),
                    ("CTRL-DOWN", (df.doi >= 0) & (df.dpx <= -0.015)), ("CTRL-UP", (df.doi >= 0) & (df.dpx >= 0.015))]:
        last = None
        for t in df.index[q]:
            if last is not None and t - last < pd.Timedelta(hours=4):
                continue
            last = t
            t0 = t + pd.Timedelta(minutes=5)
            e0 = px.asof(t0)
            sgn = 1.0 if kind in ("LONG-LIQ", "CTRL-DOWN") else -1.0
            r = {f"r{h}": sgn * (px.asof(t0 + pd.Timedelta(minutes=h)) / e0 - 1) for h in (60, 240)}
            et = t0.tz_convert("America/New_York")
            us = et.weekday() < 5 and (9 * 60 + 35) <= et.hour * 60 + et.minute <= 15 * 60
            out.append(dict(kind=kind, t=t, date=t.tz_convert(None).normalize(), doi=df.doi[t], dpx=df.dpx[t], us=us, **r))
    return pd.DataFrame(out)


def ct(x, d):
    dm = x.groupby(np.asarray(d)).mean()
    return dm.mean(), (dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))) if len(dm) > 2 else np.nan


def judge():
    L = []
    pr = lambda s_: (print(s_), L.append(s_))  # noqa: E731
    for sym in ["BTCUSDT", "ETHUSDT"]:
        e = events(sym)
        e.to_parquet(D / f"{sym}_events.parquet")
        pr(f"\n=== {sym}: events {e.kind.value_counts().to_dict()} ({e.t.min()} .. {e.t.max()})")
        for kind in ["LONG-LIQ", "SHORT-SQZ", "CTRL-DOWN", "CTRL-UP"]:
            for h in (60, 240):
                x = e[e.kind == kind]
                if len(x) < 5:
                    continue
                net = x[f"r{h}"] - 0.001
                mu, t = ct(net, x.date)
                h1 = net[x.t < pd.Timestamp("2024-01-01", tz="UTC")].mean()
                h2 = net[x.t >= pd.Timestamp("2024-01-01", tz="UTC")].mean()
                ex5 = net.sort_values().iloc[:-5].mean() if len(net) > 10 else np.nan
                us = net[x.us]
                pr(f"  {kind:9s} {h:3d}m n {len(x):4d} net mean {net.mean()*1e4:+7.1f}bp med {net.median()*1e4:+7.1f} "
                   f"hit {(net>0).mean():.2f} t {t:+5.2f} | halves {h1*1e4:+7.1f} / {h2*1e4:+7.1f} | ex-top5 {ex5*1e4:+7.1f} "
                   f"| 25bp/side {(x[f'r{h}']-0.005).mean()*1e4:+7.1f} | US-hours n {len(us)} {us.mean()*1e4:+7.1f}")
        a = e[e.kind == "LONG-LIQ"].r60 - 0.001
        b = e[e.kind == "CTRL-DOWN"].r60 - 0.001
        if len(a) > 2 and len(b) > 2:
            dd = a.mean() - b.mean()
            pr(f"  LONG-LIQ - CTRL-DOWN (60m): {dd*1e4:+.1f}bp t {dd/np.sqrt(a.var()/len(a)+b.var()/len(b)):+.2f}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    fetch() if len(sys.argv) > 1 and sys.argv[1] == "fetch" else judge()
