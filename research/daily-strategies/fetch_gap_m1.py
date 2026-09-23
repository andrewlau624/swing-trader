import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO)
from panel import *
from swingtrader.data import _clients
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
P=panel(); O,C,V=P['open'],P['close'],P['volume']
C1=C.shift(1); adv=(C*V).rolling(20).mean().shift(1)
elig=(C1>=3)&(adv>=5e6)
gap=(O/C1-1).where(elig)
K=40
cands={}
for d in gap.index[25:]:
    g=gap.loc[d].dropna(); g=g[g.abs()>=0.03]
    cands[d]=list(g.abs().sort_values(ascending=False).index[:K])
pickle.dump(cands,open(f"{SP}/gap_cands.pkl","wb"))
c,_=_clients()
days=list(cands)
for d in days:
    p=f"{SP}/gm1/{d.date()}.parquet"
    if os.path.exists(p) or not cands[d]: continue
    for a in range(5):
        try:
            df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=cands[d],timeframe=TimeFrame.Minute,start=(pd.Timestamp(d)+pd.Timedelta(hours=9,minutes=30)).tz_localize('America/New_York').tz_convert('UTC'),end=(pd.Timestamp(d)+pd.Timedelta(hours=16,minutes=1)).tz_localize('America/New_York').tz_convert('UTC'),feed='sip',adjustment='all')).df
            break
        except Exception as e:
            print('err',d,str(e)[:150],flush=True); time.sleep(5); df=None
    if df is not None and len(df): df.reset_index().to_parquet(p)
    print(d.date(), len(cands[d]), 0 if df is None else len(df), flush=True)
print("DONE",flush=True)
