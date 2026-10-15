"""U1 minute-bar fill check (spec frozen in window_signals_loop_2026-10-07.md "U1 MINUTE-BAR FILL CHECK")."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from research.sim import winsig as w, winsig_fam as F, uts as U
import re
import time


def fetch_day(d, syms):
    """SIP minute bars for one day; drops symbols Alpaca calls invalid and retries. None on persistent error."""
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.config import require_alpaca_keys
    k, sec = require_alpaca_keys()
    cli = StockHistoricalDataClient(k, sec)
    syms = list(syms)
    for _ in range(len(syms) + 3):
        if not syms:
            return pd.DataFrame()
        try:
            df = cli.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=syms, timeframe=TimeFrame.Minute,
                start=pd.Timestamp(d, tz="America/New_York").tz_convert("UTC").to_pydatetime(),
                end=pd.Timestamp(d + pd.Timedelta(days=1), tz="America/New_York").tz_convert("UTC").to_pydatetime(),
                feed="sip")).df
        except Exception as exc:  # noqa: BLE001
            m = re.search(r"invalid symbol: ([^\"]+)", str(exc))
            if m and m.group(1) in syms:
                syms.remove(m.group(1)); continue
            print(f"  {d:%Y-%m-%d} err {str(exc)[:80]}", flush=True); time.sleep(2); continue
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df["ts"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York")
        return df
    return None

CACHE = w.CACHE.parent / "u1_minute"
OUT = w.CACHE.parent / "program" / "u1_minute_out.txt"


def fills():
    t = w.load_panel(kind="stock")
    E = U.Eng(t)
    sig = (t.close > F.sma(t, t.close, 100)) & (U.rsi_n(t, 2) < 10)
    ex = t.closeadj > w.lag(t, t.closeadj)
    L = t.close - F.sma(t, F.true_range(t), 10)
    tr = E.trades(sig, ex, limit=L)
    tr = tr[(tr.date >= pd.Timestamp(w.DISC[0])) & (tr.date <= pd.Timestamp(w.DISC[1]))]
    i = tr.index.to_numpy()
    raw = (t.closeunadj / t.close).to_numpy("float64")
    tr["ticker"] = t.ticker.to_numpy()[i]
    tr["fill_date"] = t.date.to_numpy()[i + 1]
    tr["L_raw"] = L.to_numpy("float64")[i] * raw[i + 1]
    tr["low_raw"] = t.low.to_numpy("float64")[i + 1] * raw[i + 1]
    return tr


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    fp = CACHE / "fills.parquet"
    tr = pd.read_parquet(fp) if fp.exists() else fills()
    tr.to_parquet(fp)
    res = []
    for d, g in tr.groupby("fill_date"):
        cf = CACHE / f"{pd.Timestamp(d):%Y%m%d}.parquet"
        if cf.exists():
            m = pd.read_parquet(cf)
        else:
            m = fetch_day(pd.Timestamp(d), sorted(set(g.ticker)))
            if m is None:
                m = pd.DataFrame(columns=["symbol", "ts", "high", "low", "close", "volume"])
            elif not m.empty:
                m = m[["symbol", "ts", "high", "low", "close", "volume"]]
                hm = m.ts.dt.hour * 60 + m.ts.dt.minute
                m = m[(hm >= 570) & (hm < 960)]
            if not m.empty:
                m.to_parquet(cf)
        by = {s: x for s, x in m.groupby("symbol")} if len(m) else {}
        for idx, r in g.iterrows():
            x = by.get(r.ticker)
            if x is None or x.empty:
                res.append((idx, "nodata", np.nan, 0.0)); continue
            L = r.L_raw
            mlow = x.low.min()
            deep = x.loc[x.high < L, "volume"].sum()
            if deep >= 1000:
                cls = "G3"
            elif (x.close < L).any():
                cls = "G2"
            elif mlow <= L:
                cls = "G1"
            else:
                cls = "G0"
            res.append((idx, cls, mlow / L - 1, float(deep)))
        if len(res) % 2000 < len(g):
            print(f"  {pd.Timestamp(d):%Y-%m-%d} done {len(res)}/{len(tr)}", flush=True)
    c = pd.DataFrame(res, columns=["idx", "cls", "mlow_vs_L", "deep_vol"]).set_index("idx")
    tr = tr.join(c)
    tr.to_parquet(CACHE / "classified.parquet")
    lines = [f"U1 minute fill check, 2016-26, n fills {len(tr)}; coverage {tr.cls.ne('nodata').mean():.1%}"]
    for cls in ["G0", "G1", "G2", "G3", "nodata"]:
        s = tr[tr.cls == cls]
        if len(s) < 30:
            lines.append(f"  {cls:6} n {len(s)}"); continue
        st = U.stats(s, *w.DISC)
        lines.append(U.fmt(f"{cls} ({len(s)/len(tr):.0%} of fills)", st))
    g23 = tr[tr.cls.isin(["G2", "G3"])]
    lines.append(U.fmt("G2+G3 (any trade-through)", U.stats(g23, *w.DISC)))
    s3 = U.stats(tr[tr.cls == "G3"], *w.DISC)
    ok = s3["net"] >= 25 and s3["t"] >= 3 and s3["med"] > 0 and min(s3["h"]) > 0
    lines.append(f"  -> survival bar (G3): {'SURVIVES' if ok else 'FAILS'}")
    txt = "\n".join(lines)
    print(txt)
    OUT.write_text(txt + "\n")


if __name__ == "__main__":
    main()
