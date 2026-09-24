import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO)
from panel import *
from swingtrader.data import _clients
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
P=panel(); O,C,V=P['open'],P['close'],P['volume']
C1=C.shift(1); adv=(C*V).rolling(20).mean().shift(1)
H,L=P['high'],P['low']
# Candidates must be chosen from what could be true at 15:50, not from the
# close. The first version kept names whose FINAL close was <= -6%, which
# silently dropped every name that was <= -8% at 15:50 and then bounced into
# the close (~3% of candidates rally >= 2.2% in the last 10 minutes, and those
# are the worst overnight trades). Any name at <= -8% at 15:50 has a day LOW at
# <= -8%, so selecting on the low is a superset with no lookahead.
elig=(C1>=3)&(adv>=5e6)&(C1<=2000)
low=(L/C1-1).where(elig)
cands={d:list(low.loc[d][low.loc[d]<=-0.08].index) for d in low.index[25:]}
cands={d:v for d,v in cands.items() if v}
pickle.dump(cands,open(f"{SP}/late_cands.pkl","wb")); print(sum(len(v) for v in cands.values()),flush=True)
c,_=_clients()
for d,syms in cands.items():
    p=f"{SP}/lm1/{d.date()}.parquet"
    have=pd.read_parquet(p) if os.path.exists(p) else None
    if have is not None:
        syms=[s for s in syms if s not in set(have.symbol)]   # top up, do not refetch
        if not syms: continue
    st=(pd.Timestamp(d)+pd.Timedelta(hours=15,minutes=30)).tz_localize('America/New_York').tz_convert('UTC')
    en=(pd.Timestamp(d)+pd.Timedelta(hours=16,minutes=0)).tz_localize('America/New_York').tz_convert('UTC')
    df=None
    for a in range(5):
        try: df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms,timeframe=TimeFrame.Minute,start=st,end=en,feed='sip',adjustment='all')).df; break
        except Exception as e: print('err',d,str(e)[:120],flush=True); time.sleep(5)
    if df is not None and len(df):
        df=df.reset_index()
        if have is not None: df=pd.concat([have,df],ignore_index=True)
        df.to_parquet(p)
    print(d.date(),len(syms),flush=True)
print("DONE",flush=True)
