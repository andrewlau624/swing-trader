"""Index-beat R3-2: special (>= 3% yield) dividends captured overnight in the Roth (explore, select ex-dates 2021-23).

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_r32 fetch | explore
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd
import requests

from .exdiv_roth import _env
from .jump_runner import cost_side

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/ib/divs_all.json"
RAWB = ROOT / "data/research/program/ib/divbars"


def fetch():
    H = _env(); out = []
    for y in range(2021, 2024):
        for a, z in ((f"{y}-01-01", f"{y}-06-30"), (f"{y}-07-01", f"{y}-12-31")):
            tok = None
            while True:
                q = {"types": "cash_dividend", "start": a, "end": z, "limit": 1000}
                if tok:
                    q["page_token"] = tok
                for k in range(8):
                    r = requests.get("https://data.alpaca.markets/v1/corporate-actions", params=q, headers=H, timeout=60)
                    if r.status_code != 429:
                        break
                    time.sleep(5 * (k + 1))
                r.raise_for_status(); j = r.json()
                out.extend(j.get("corporate_actions", {}).get("cash_dividends", []))
                tok = j.get("next_page_token")
                if not tok:
                    break
                time.sleep(0.6)
        print(y, len(out), flush=True)
    json.dump(out, open(OUT, "w"))


def raw_bars(syms):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import _clients, trade_date
    c, _ = _clients(); RAWB.mkdir(parents=True, exist_ok=True)
    need = [s for s in sorted(set(syms)) if not (RAWB / f"{s}.parquet").exists()]
    for i in range(0, len(need), 50):
        ch = need[i:i + 50]
        try:
            df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=ch, timeframe=TimeFrame.Day, start=pd.Timestamp("2020-11-01", tz="UTC"),
                                                   end=pd.Timestamp("2024-01-31", tz="UTC"), feed="sip", adjustment="raw")).df
        except Exception as exc:
            print("err", str(exc)[:60]); continue
        df = df.reset_index(); df["date"] = trade_date(df["timestamp"])
        got = {s: g.set_index("date")[["open", "high", "low", "close", "volume"]] for s, g in df.groupby("symbol")}
        for s in ch:
            got.get(s, pd.DataFrame(columns=["open", "close", "volume"])).to_parquet(RAWB / f"{s}.parquet")
        print("bars", i + len(ch), "/", len(need), flush=True)


def explore():
    D = pd.DataFrame(json.load(open(OUT)))
    D["ex"] = pd.to_datetime(D.ex_date)
    D = D[(D.ex >= "2021-01-01") & (D.ex <= "2023-12-31") & (D.foreign != True)]
    big = D[D.rate >= 0.10]                      # coarse pre-filter before bars ($0.10+); the 3% test needs the close
    raw_bars(big.symbol.unique())
    rows = []
    for r in big.itertuples():
        f = RAWB / f"{r.symbol}.parquet"
        if not f.exists():
            continue
        b = pd.read_parquet(f)
        if b.empty:
            continue
        b.index = pd.to_datetime(b.index)
        if r.ex not in b.index:
            continue
        i = b.index.get_loc(r.ex)
        if i < 21:
            continue
        c0, o1 = b.close.iloc[i - 1], b.open.iloc[i]
        y = r.rate / c0
        adv = float((b.close * b.volume).iloc[i - 21:i - 1].median())
        if y < 0.03 or adv < 1e6 or not (np.isfinite(c0) and np.isfinite(o1)) or c0 < 1:
            continue
        net = (o1 + r.rate) / c0 - 1 - 2 * cost_side(adv)
        rows.append(dict(sym=r.symbol, ex=r.ex, y=y, special=r.special, adv=adv, gross=(o1 + r.rate) / c0 - 1, net=net,
                         drop=(c0 - o1) / r.rate))
    T = pd.DataFrame(rows)
    T.to_pickle(ROOT / "data/research/program/ib/r32_events.pkl")
    for lab, s in (("all >= 3%", T), ("flagged special", T[T.special == True]), ("regular >= 3%", T[T.special != True])):
        if not len(s):
            continue
        n = s.net * 1e4; top5 = n.nlargest(5).index
        print(f"{lab:16s}: n {len(s)} ({len(s) / 3:.0f}/yr), yield median {s.y.median():.1%}, drop ratio median {s.drop.median():.2f}, "
              f"gross {s.gross.mean() * 1e4:+.0f}bp, net {n.mean():+.0f}bp (median {n.median():+.0f}, t {n.mean() / n.std() * np.sqrt(len(n)):+.2f}), "
              f"ex-top-5 {n.drop(top5).mean():+.0f}bp; by year " + " ".join(f"{y}: {g.mean():+.0f}" for y, g in n.groupby(s.ex.dt.year)))


if __name__ == "__main__":
    fetch() if sys.argv[1] == "fetch" else explore()
