import sys, os
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO); os.chdir(REPO)
import pandas as pd
from swingtrader.data import _clients
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
c,_=_clients()
for s in ("QQQ","SMH"):
    parts=[]
    for a,b in [("2026-05-01","2026-06-15"),("2026-06-15","2026-08-01"),("2026-08-01","2026-09-15"),("2026-09-15","2026-10-08")]:
        df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=[s],timeframe=TimeFrame.Minute,start=pd.Timestamp(a,tz="UTC"),end=pd.Timestamp(b,tz="UTC"),feed="sip",adjustment="all")).df.reset_index()
        parts.append(df); print(s,a,len(df),flush=True)
    pd.concat(parts).to_parquet(f"data/research/recent/qm/{s}_recent.parquet")
