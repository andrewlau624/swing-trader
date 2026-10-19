import sys, json, datetime as dt, numpy as np, pandas as pd, pyarrow.dataset as ds
sys.path.insert(0,'/Users/andrewlau/Documents/Code/Projects/swing-trader')
from research.sim.ovx import _bars, _utc, ET
from research.sim.auction_fetch import _env
S='/Users/andrewlau/data/sharadar/'
ev=pd.read_parquet(S+'events.parquet'); ev['date']=pd.to_datetime(ev.date)
ev=ev[ev.eventcodes.astype(str).str.split('|').apply(lambda x:'22' in x)&(ev.date>='2024-10-02')&(ev.date<='2026-09-15')]
sp=pd.read_parquet(S+'sp500.parquet'); tk=set(sp.ticker.dropna())
ev=ev[ev.ticker.isin(tk)]
px=ds.dataset(S+'stocks.parquet').to_table(filter=ds.field('ticker').isin(sorted(set(ev.ticker))) ).to_pandas()
px['date']=pd.to_datetime(px.date); px=px[px.date>='2024-09-25'].sort_values(['ticker','date'])
px['cu']=px.closeunadj
g=px.groupby('ticker')
px['gap']=g.open.shift(-1)/px.close-1   # open t+1 vs close t (adj consistent if split-free)
px['nd']=g.date.shift(-1)
m=ev.merge(px[['ticker','date','gap','nd','cu','volume']],on=['ticker','date']).dropna(subset=['gap'])
m=m[(m.cu*m.volume>=2e7)]
print('candidates',len(m),file=sys.stderr)
H=_env(); rows=[]
for r in m.itertuples():
    d,n=r.date,r.nd
    try:
        sip=_bars([r.ticker],_utc(d,15,50),_utc(n,9,30),'sip',H).get(r.ticker,[])
        bo=_bars([r.ticker],_utc(d,20,0),_utc(n,4,0),'boats',H).get(r.ticker,[])
    except Exception as e: continue
    def t(b): return pd.Timestamp(b['t']).tz_convert(ET)
    reg=[b for b in sip if t(b).date()==d.date() and t(b).hour==15 and t(b).minute==59]
    if not reg: continue
    c=reg[-1]['c']
    post=[b for b in sip if t(b).date()==d.date() and (t(b).hour in (16,17,18,19)) and t(b).minute>=0 and not(t(b).hour==16 and t(b).minute<5) and b['v']]
    pre=[b for b in sip if t(b).date()==n.date() and t(b).hour*60+t(b).minute>=9*60+15 and b['v']]
    if not post: continue
    pv=sum(b['vw']*b['v'] for b in post)/sum(b['v'] for b in post)
    def at(bars,h,mi,w=30):
        lo=h*60+mi
        x=[b for b in bars if abs((t(b).hour*60+t(b).minute)-lo)<=w//2 or (False)]
        # handle wrap: t on n date only
        x=[b for b in bars if t(b).date()==n.date() and abs(t(b).hour*60+t(b).minute-lo)<=w and b['v']]
        return (sum(b['vw']*b['v'] for b in x)/sum(b['v'] for b in x), sum(b['v'] for b in x)) if x else (np.nan,0)
    b2,v2=at(bo,2,0); b4,v4=at(bo,3,45,15)
    bt=[b for b in bo if b['v']]; nv=sum(b['v'] for b in bt); nvw=sum(b['vw']*b['v'] for b in bt)/nv if nv else np.nan
    p9=pre[-1]['c'] if pre else np.nan
    rows.append(dict(sym=r.ticker,d=d.date(),c=c,post=pv/c-1,boats_all=nvw/c-1 if nv else np.nan,boats_n=len(bt),boats_sh=nv,b02=b2/c-1,b02v=v2,b0345=b4/c-1,b0345v=v4,pre0928=p9/c-1,gap=r.gap))
df=pd.DataFrame(rows); df.to_csv('/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/bad619c6-1952-49ad-9cea-d66d4400c09e/scratchpad/q_probe_all.csv',index=False)
print(len(df)); print(df.describe().T.to_string())
