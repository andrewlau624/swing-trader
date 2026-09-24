"""Charge #4 data: 15:30-16:00 SIP minute bars for every name whose day LOW
was <= -6% and that data/research/night/lm1 does not already hold. Selecting on
the low (not the close) keeps names that bounced into the close -- the
addendum-14 lookahead lesson. Writes data/research/night/lm6/<date>.parquet.

    .venv/bin/python -m research.sim.fetch_depth
"""
import glob, os, time
import pandas as pd
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from swingtrader.data import _clients
from .data import DATA

P = pd.read_pickle(DATA / "panel.pkl"); C, V, L = P["close"], P["volume"], P["low"]
C1 = C.shift(1); adv = (C * V).rolling(20).mean().shift(1)
low = (L / C1 - 1).where((C1 >= 3) & (adv >= 5e6) & (C1 <= 2000))
c, _ = _clients()
for f in sorted(glob.glob(str(DATA / "lm1" / "*.parquet"))):
    d = pd.Timestamp(os.path.basename(f)[:10])
    out = DATA / "lm6" / f"{d.date()}.parquet"
    if out.exists() or d not in low.index:
        continue
    have = set(pd.read_parquet(f, columns=["symbol"]).symbol)
    s = low.loc[d]; syms = sorted(set(s[s <= -0.06].index) - have)
    if not syms:
        pd.DataFrame(columns=["symbol", "timestamp"]).to_parquet(out); continue
    st = (d + pd.Timedelta(hours=15, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
    en = (d + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
    df = None
    for a in range(5):
        try:
            df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute,
                                                   start=st, end=en, feed="sip", adjustment="all")).df
            break
        except Exception as e:
            print("err", d.date(), str(e)[:100], flush=True); time.sleep(5)
    if df is not None:
        (df.reset_index() if len(df) else pd.DataFrame(columns=["symbol", "timestamp"])).to_parquet(out)
    print(d.date(), len(syms), flush=True)
print("DONE", flush=True)
