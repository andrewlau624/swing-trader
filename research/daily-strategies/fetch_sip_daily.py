import sys, os, json, time
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO); os.chdir(REPO)
import pandas as pd
from swingtrader.data import _clients
from swingtrader.universe import valid_symbol
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
OUT=sys.argv[1]
syms=[s for s in json.load(open('data/cache/assets.json'))['symbols'] if valid_symbol(s)]
print(len(syms), flush=True)
c,_=_clients()
B=250
for i in range(0,len(syms),B):
    p=f"{OUT}/b{i:05d}.parquet"
    if os.path.exists(p): continue
    chunk=syms[i:i+B]
    for attempt in range(5):
        try:
            df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=chunk,timeframe=TimeFrame.Day,start=pd.Timestamp('2020-10-01'),end=pd.Timestamp('2026-09-22'),feed='sip',adjustment='all')).df
            break
        except Exception as e:
            msg=str(e)
            print('err',i,msg[:200],flush=True)
            if 'invalid symbol' in msg.lower():
                # drop bad ones by bisecting: simplest - fetch individually
                parts=[]
                for s in chunk:
                    try:
                        parts.append(c.get_stock_bars(StockBarsRequest(symbol_or_symbols=[s],timeframe=TimeFrame.Day,start=pd.Timestamp('2020-10-01'),end=pd.Timestamp('2026-09-22'),feed='sip',adjustment='all')).df)
                    except Exception: pass
                df=pd.concat([x for x in parts if len(x)]) if parts else pd.DataFrame()
                break
            time.sleep(5)
    if len(df):
        df=df.reset_index()[['symbol','timestamp','open','high','low','close','volume','vwap','trade_count']]
        df.to_parquet(p)
    print(i, len(df), flush=True)
print("DONE",flush=True)
