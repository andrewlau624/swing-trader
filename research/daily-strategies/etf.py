import pandas as pd, numpy as np, sys
SP=sys.argv[0].rsplit('/',1)[0]
d=pd.read_parquet(f'{SP}/etf_daily.parquet')
d['date']=d.timestamp.dt.tz_convert('America/New_York').dt.normalize().dt.tz_localize(None)
P={f:d.pivot(index='date',columns='symbol',values=f) for f in ['open','high','low','close','volume']}
O,H,L,C=P['open'],P['high'],P['low'],P['close']
def stats(r, name, cost_per_trade=0, ntr=None):
    r=r.fillna(0)
    out={}
    for lab,sl in [('IS16-20',slice('2016','2020')),('OOS21-26',slice('2021','2026'))]:
        x=r[sl]; yrs=len(x)/252
        cagr=(1+x).prod()**(1/yrs)-1
        sh=x.mean()/x.std()*np.sqrt(252) if x.std()>0 else 0
        eq=(1+x).cumprod(); dd=(eq/eq.cummax()-1).min()
        out[lab]=f"cagr {cagr*100:6.1f} sh {sh:5.2f} dd {dd*100:6.1f}"
    return out
def ibs(): return (C-L)/(H-L).replace(0,np.nan)
def rsi(n=2):
    ch=C.diff(); up=ch.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-ch.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+up/dn)
cost=float(sys.argv[1]) if len(sys.argv)>1 else 2  # bps per side
cc=cost/1e4
nxt_cc=C.shift(-1)/C-1   # close->next close
on=O.shift(-1)/C-1       # overnight close->next open
intr=C/O-1               # open->close
res=[]
I=ibs(); R=rsi(2); S200=C.rolling(200).mean(); S5=C.rolling(5).mean()
for s in C.columns:
    rows={}
    # buy-and-hold
    rows['BH']=nxt_cc[s]
    # IBS<0.2 hold 1 day at close
    sig=(I[s]<0.2)
    rows['IBS<.2']=(nxt_cc[s]-2*cc)*sig
    # IBS<0.2 exec next open (conservative) -> open to next close? use next open to next-next open
    oo=O[s].shift(-2)/O[s].shift(-1)-1
    rows['IBS<.2@open']=(oo-2*cc)*sig
    # overnight every day
    rows['overnight']=on[s]-2*cc
    rows['intraday']=intr[s]-2*cc
    # RSI2 Connors: in position when rsi<10 & >SMA200 entry, exit close>S5
    pos=np.zeros(len(C)); inpos=False
    rr=R[s].values; c=C[s].values; s2=S200[s].values; s5=S5[s].values
    for t in range(len(C)):
        if not inpos and rr[t]<10 and c[t]>s2[t]: inpos=True; pos[t]=1; continue
        if inpos:
            if c[t]>s5[t]: inpos=False; pos[t]=0
            else: pos[t]=1
    pos=pd.Series(pos,index=C.index)
    trades=(pos.diff().abs()>0).astype(float)
    rows['RSI2']=pos*nxt_cc[s]-trades*cc
    for k,v in rows.items():
        st=stats(v,k); res.append(dict(sym=s,rule=k,expo=round(float((v!=0).mean()),2),**st))
df=pd.DataFrame(res)
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
for rule in ['BH','IBS<.2','IBS<.2@open','RSI2','overnight','intraday']:
    print(df[df.rule==rule].to_string(index=False)); print()
