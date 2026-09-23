import sys, os, time, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO)
import pandas as pd
from swingtrader.data import _clients
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
SP=os.path.dirname(os.path.abspath(__file__))
x=pd.read_pickle(f'{SP}/dtime.pkl'); x=x[x['T']==1540]
idx=pd.read_pickle(f'{SP}/panel.pkl')['close'].index
nxt={d:idx[i+1] for i,d in enumerate(idx[:-1])}
jobs=sorted({(nxt[d],) + () for d in x.date if d in nxt})
by={}
for d,s in zip(x.date,x.sym):
    if d in nxt: by.setdefault(nxt[d],set()).add(s)
days=sorted(by); part=int(sys.argv[1]); days=days[part::2]
c,_=_clients()
for d in days:
    p=f"{SP}/am1/{d.date()}.parquet"
    if os.path.exists(p): continue
    st=(d+pd.Timedelta(hours=9,minutes=30)).tz_localize('America/New_York').tz_convert('UTC')
    en=(d+pd.Timedelta(hours=10,minutes=31)).tz_localize('America/New_York').tz_convert('UTC')
    for a in range(4):
        try:
            df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=sorted(by[d]),timeframe=TimeFrame.Minute,start=st,end=en,feed='sip',adjustment='all')).df; break
        except Exception as e: print('err',d,str(e)[:100],flush=True); time.sleep(5); df=None
    if df is not None and len(df): df.reset_index().to_parquet(p)
print("DONE",flush=True)
