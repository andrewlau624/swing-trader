import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO)
from panel import *
from swingtrader.data import _clients
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
P=panel(); O,C,V=P['open'],P['close'],P['volume']
C1=C.shift(1); adv=(C*V).rolling(20).mean().shift(1)
elig=(C>=3)&(adv>=5e6)&(C<=2000)
day=(C/C1-1).where(elig)
cands={d:list(day.loc[d][day.loc[d]<=-0.06].index) for d in day.index[25:]}
cands={d:v for d,v in cands.items() if v}
pickle.dump(cands,open(f"{SP}/late_cands.pkl","wb")); print(sum(len(v) for v in cands.values()),flush=True)
c,_=_clients()
for d,syms in cands.items():
    p=f"{SP}/lm1/{d.date()}.parquet"
    if os.path.exists(p): continue
    st=(pd.Timestamp(d)+pd.Timedelta(hours=15,minutes=30)).tz_localize('America/New_York').tz_convert('UTC')
    en=(pd.Timestamp(d)+pd.Timedelta(hours=16,minutes=0)).tz_localize('America/New_York').tz_convert('UTC')
    df=None
    for a in range(5):
        try: df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms,timeframe=TimeFrame.Minute,start=st,end=en,feed='sip',adjustment='all')).df; break
        except Exception as e: print('err',d,str(e)[:120],flush=True); time.sleep(5)
    if df is not None and len(df): df.reset_index().to_parquet(p)
    print(d.date(),len(syms),flush=True)
print("DONE",flush=True)
