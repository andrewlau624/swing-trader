import pandas as pd, numpy as np, glob, os, pickle
SP=os.path.dirname(os.path.abspath(__file__))
def panel():
    pk=f"{SP}/panel.pkl"
    if os.path.exists(pk): return pickle.load(open(pk,'rb'))
    df=pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{SP}/sipd/*.parquet"))])
    df['date']=df.timestamp.dt.tz_convert('America/New_York').dt.tz_localize(None).dt.normalize()
    P={}
    for f in ['open','high','low','close','volume','vwap','trade_count']:
        P[f]=df.pivot_table(index='date',columns='symbol',values=f,aggfunc='last').astype('float32')
    pickle.dump(P,open(pk,'wb'),protocol=4); return P
def stats(r, lab="", ppy=252):
    r=r.fillna(0); out=[]
    for sl in [slice('2021','2023'),slice('2024','2026'),slice('2021','2026')]:
        x=r[sl]; yrs=len(x)/ppy
        cagr=(1+x).prod()**(1/yrs)-1; sh=x.mean()/x.std()*np.sqrt(ppy) if x.std()>0 else 0
        eq=(1+x).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append(f"{cagr*100:7.1f}%/{sh:5.2f}/{dd*100:4.0f}")
    pm=r.resample('ME').apply(lambda x:(1+x).prod()-1)
    return f"{lab:40s} "+"  ".join(out)+f"  +mo {100*(pm>0).mean():3.0f}%"
