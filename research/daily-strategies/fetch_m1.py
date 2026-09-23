import sys, os, time
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO); os.chdir(REPO)
import pandas as pd
from swingtrader.data import _clients
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
OUT=sys.argv[1]; syms=sys.argv[2].split(',')
c,_=_clients()
for s in syms:
  for y in range(2016,2027):
    p=f"{OUT}/{s}_{y}.parquet"
    if os.path.exists(p): continue
    for a in range(5):
      try:
        df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=[s],timeframe=TimeFrame.Minute,start=pd.Timestamp(f'{y}-01-01'),end=min(pd.Timestamp(f'{y}-12-31 23:59'),pd.Timestamp('2026-09-21 23:00')),feed='sip',adjustment='all')).df
        break
      except Exception as e: print('err',s,y,str(e)[:150],flush=True); time.sleep(10)
    df=df.reset_index(); df.to_parquet(p); print(s,y,len(df),flush=True)
print('DONE',flush=True)
