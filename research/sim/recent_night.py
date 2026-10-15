"""Night leg exact 15:40 rule, 2021-02..latest, on lm1 (15:30-16:00 candidate minutes) + data/research/recent extension.
Rule (live cfg): day_ret(15:40)<=-8%, IBS(15:40)<0.10 (H/L through 15:40), price 5-2000, vol20>=.6, ADV20>=$10M; buy close, sell next open.
No dedup/tilt/crowd scaling: equal-weight per-trade. Candidate fetch = low touched -8% (superset). No tuning.
Run: PYTHONPATH=. .venv/bin/python research/sim/recent_night.py fetch|eval"""
import sys, os, glob, time
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO); os.chdir(REPO)
sys.path.insert(0,f"{REPO}/data/research/night")
import numpy as np, pandas as pd
from panel import panel
R=f"{REPO}/data/research/recent"
def full_panel():
    P=panel()
    rec=pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{R}/sipd/*.parquet"))])
    rec['date']=pd.to_datetime(rec.timestamp).dt.tz_convert('America/New_York').dt.tz_localize(None).dt.normalize()
    Q={f:rec.pivot_table(index='date',columns='symbol',values=f,aggfunc='last').astype('float32') for f in ['open','high','low','close','volume']}
    out={}
    for f in Q:
        old=P[f]; old=old[old.index<'2026-09-17']
        out[f]=pd.concat([old,Q[f]]).sort_index()
    return out
if sys.argv[1]=="fetch":
    from swingtrader.data import _clients
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    P=full_panel(); C,L,V=P['close'],P['low'],P['volume']; C1=C.shift(1); adv=(C*V).rolling(20).mean().shift(1)
    elig=(C1>=3)&(adv>=5e6)&(C1<=2000); low=(L/C1-1).where(elig)
    c,_=_clients()
    for d in low.index[low.index>='2026-09-22']:
        syms=list(low.loc[d][low.loc[d]<=-0.08].index)
        st=(d+pd.Timedelta(hours=15,minutes=30)).tz_localize('America/New_York').tz_convert('UTC'); en=(d+pd.Timedelta(hours=16)).tz_localize('America/New_York').tz_convert('UTC')
        df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms,timeframe=TimeFrame.Minute,start=st,end=en,feed='sip',adjustment='all')).df.reset_index()
        df.to_parquet(f"{R}/lm1/{d.date()}.parquet"); print(d.date(),len(syms),len(df),flush=True)
    sys.exit()
P=full_panel(); O,H,L,C,V=[P[k] for k in ['open','high','low','close','volume']]
C1=C.shift(1); adv=(C*V).rolling(20).mean().shift(1); vol20=np.log(C/C1).rolling(20).std().shift(1)*np.sqrt(252)
NO=O.shift(-1)
files=sorted(glob.glob(f"{REPO}/data/research/night/lm1/*.parquet")+glob.glob(f"{R}/lm1/*.parquet"))
rows=[]
for f in files:
    d=pd.Timestamp(os.path.basename(f)[:10])
    if d not in C.index: continue
    df=pd.read_parquet(f)
    if df.empty: continue
    t=pd.to_datetime(df.timestamp).dt.tz_convert('America/New_York'); df['hm']=t.dt.hour*100+t.dt.minute
    for s,g in df.groupby('symbol'):
        if s not in C.columns: continue
        pre=g[g.hm<=1540]; post=g[g.hm>1540]
        if pre.empty: continue
        p=pre.close.iloc[-1]; Ld,Hd=L.at[d,s],H.at[d,s]
        L40=Ld if (len(post)==0 or post.low.min()>Ld+1e-9) else pre.low.min()
        H40=Hd if (len(post)==0 or post.high.max()<Hd-1e-9) else pre.high.max()
        H40=max(H40,p); L40=min(L40,p)
        pc=C1.at[d,s]; ret=p/pc-1; ibs=(p-L40)/(H40-L40) if H40>L40 else np.nan
        rows.append(dict(date=d,sym=s,p40=p,day_ret=ret,ibs=ibs,vol20=vol20.at[d,s],adv=adv.at[d,s],close=C.at[d,s],nopen=NO.at[d,s]))
x=pd.DataFrame(rows)
sel=x[(x.day_ret<=-.08)&(x.ibs<.10)&(x.p40.between(5,2000))&(x.vol20>=.6)&(x.adv>=1e7)&x.nopen.notna()].copy()
sel['ret']=(sel.nopen/sel.close-1)*1e4
sel=sel[sel.ret.abs()<6000]
sel.to_parquet(f"{R}/night_replay.parquet"); print(len(x),len(sel),sel.date.min(),sel.date.max())
def st(d,c):
    r=d.ret-2*c; n=len(r)
    if n<3: return f"n={n}"
    dm=r.groupby(d.date).mean(); nd=len(dm)
    tc=dm.mean()/(dm.std()/np.sqrt(nd)) if nd>2 and dm.std()>0 else np.nan
    return f"n={n:4d} days={nd:3d} mean={r.mean():7.1f} med={r.median():7.1f} hit={(r>0).mean()*100:3.0f}% dayclust_t={tc:5.2f}"
per={"2021-26 (02..09-21 baseline)":(sel.date<'2026-09-22'),"2026-06..10-07":(sel.date>='2026-06-01'),"2026 YTD":(sel.date>='2026-01-01'),
     "2026-06..09-21":(sel.date.between('2026-06-01','2026-09-21')),"live window 09-23..10-07":(sel.date>='2026-09-23'),"2021":(sel.date.dt.year==2021)}
for y in range(2022,2027): per[str(y)]=(sel.date.dt.year==y)
for k,m in per.items():
    print(k)
    for c in (0,2.5,7.5): print(f"  {c:4.1f}bp/side {st(sel[m],c)}")
print(sel[sel.date>='2026-09-22'].sort_values(['date','sym'])[['date','sym','day_ret','ibs','ret']].round(3).to_string())
