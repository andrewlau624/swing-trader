import pandas as pd, numpy as np, glob, os, sys, pickle
SP=os.path.dirname(os.path.abspath(__file__))
def load(sym):
    pk=f"{SP}/m1/{sym}_mat.pkl"
    if os.path.exists(pk): return pickle.load(open(pk,'rb'))
    df=pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{SP}/m1/{sym}_20*.parquet"))])
    t=df.timestamp.dt.tz_convert('America/New_York')
    df['date']=t.dt.tz_localize(None).dt.normalize(); df['m']=(t.dt.hour*60+t.dt.minute)-570
    df=df[(df.m>=0)&(df.m<390)]
    M={}
    for f in ['open','high','low','close','volume']:
        M[f]=df.pivot_table(index='date',columns='m',values=f,aggfunc='last').reindex(columns=range(390))
    # drop half-days (fewer than 300 minutes with trades before 13:00 close) -> keep; mark
    M['close']=M['close'].ffill(axis=1)
    for f in ['open','high','low']: M[f]=M[f].fillna(M['close'])
    M['volume']=M['volume'].fillna(0)
    days=M['close'].index
    # half days: no trades after minute 210
    full=M['volume'].iloc[:,300:].sum(axis=1)>0
    for f in M: M[f]=M[f][full]
    pickle.dump(M,open(pk,'wb')); return M
def stats(r, lab=""):
    r=r.fillna(0); out=[]
    for sl in [slice('2016','2020'),slice('2021','2026'),slice('2016','2026')]:
        x=r[sl]; 
        if len(x)<50: out.append('   n/a'); continue
        yrs=len(x)/252; cagr=(1+x).prod()**(1/yrs)-1; sh=x.mean()/x.std()*np.sqrt(252) if x.std()>0 else 0
        eq=(1+x).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append(f"{cagr*100:6.1f}%/{sh:5.2f}/{dd*100:4.0f}")
    pm=r.resample('ME').apply(lambda x:(1+x).prod()-1); 
    return f"{lab:34s} " + "  ".join(out) + f"  pos-months {100*(pm>0).mean():3.0f}%"
