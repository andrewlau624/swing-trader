"""Extend night/noise research data to the latest complete session into data/research/recent (separate cache).
daily SIP bars (adjustment=all) for the night universe 2026-09-17..END; candidate-day 15:30-16:00 minutes; QQQ/SMH full minute 2026-05-15..END."""
import sys, os, json, time, pickle
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO); os.chdir(REPO)
import pandas as pd, numpy as np
from swingtrader.data import _clients
from swingtrader.universe import valid_symbol
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
OUT=f"{REPO}/data/research/recent"; END=pd.Timestamp(sys.argv[1])  # exclusive
c,_=_clients()
syms=[s for s in json.load(open('data/cache/assets.json'))['symbols'] if valid_symbol(s)]
B=250
for i in range(0,len(syms),B):
    p=f"{OUT}/sipd/b{i:05d}.parquet"
    if os.path.exists(p): continue
    chunk=syms[i:i+B]; df=None
    for a in range(5):
        try: df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=chunk,timeframe=TimeFrame.Day,start=pd.Timestamp('2026-09-17'),end=END,feed='sip',adjustment='all')).df; break
        except Exception as e:
            if 'invalid symbol' in str(e).lower():
                parts=[]
                for s in chunk:
                    try: parts.append(c.get_stock_bars(StockBarsRequest(symbol_or_symbols=[s],timeframe=TimeFrame.Day,start=pd.Timestamp('2026-09-17'),end=END,feed='sip',adjustment='all')).df)
                    except Exception as e1:
                        if 'invalid symbol' not in str(e1).lower(): raise
                        print("skip invalid", s, flush=True)
                df=pd.concat(parts) if parts else None; break
            time.sleep(5)
    if df is not None and len(df): df.reset_index().to_parquet(p)
    print(i,flush=True)
print("DAILY DONE",flush=True)
