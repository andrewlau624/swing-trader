"""CRYPTO-TA adversarial checks on R7 (clustering, per coin/year, BTC-only, threshold, placebo, 2022+)."""
import sys; sys.path.insert(0, "research/sim")
import numpy as np, pandas as pd, crypto_ta as C
p=pd.read_parquet("data/research/crypto_spot/panel.parquet",columns=["date","symbol","close","low"])
p["date"]=pd.to_datetime(p.date)
def run(coins,thr=70,start=C.START):
    q=p[p.symbol.isin(coins)]
    F={s:C.frame(g.set_index("date").sort_index()).loc[start:] for s,g in q.groupby("symbol")}
    MU={s:np.log(f.close).diff().mean() for s,f in F.items()}
    ent=lambda f,i: C.cross_up(f.rsi14.values,np.full(len(f),float(thr)),i)
    ext=lambda f,i,e: f.rsi14.values[i]<50 or i-e>=20
    tr=[]
    for s,f in F.items():
        t,_=C.event_trades(f,ent,ext,MU[s]); tr+=[(s,)+x for x in t]
    return pd.DataFrame(tr,columns=["sym","date","days","ret","exc"]),F,MU
df,F,MU=run(C.COINS)
df["net"]=df.exc-0.015
def ct(x,key):
    g=x.groupby(key).mean(); return g.mean()/(g.std(ddof=1)/np.sqrt(len(g)))
print("cluster t: date %.2f week %.2f month %.2f"%(ct(df.net,df.date),ct(df.net,df.date.dt.to_period('W')),ct(df.net,df.date.dt.to_period('M'))))
print("per coin (net bp mean/median/n):"); print(df.groupby("sym").net.agg(['mean','median','count']).mul([1e4,1e4,1]).round(0))
print("per year:"); print(df.groupby(df.date.dt.year).net.agg(['mean','median','count']).mul([1e4,1e4,1]).round(0))
for coins in (["BTCUSDT"],["BTCUSDT","ETHUSDT"]):
    d,_,_=run(coins); n=d.exc-0.015
    print(coins,"n",len(d),"net mean %+.0f med %+.0f t(month) %.2f halves %+.0f/%+.0f"%(n.mean()*1e4,n.median()*1e4,ct(n,d.date.dt.to_period('M')),n[d.date<C.SPLIT].mean()*1e4,n[d.date>=C.SPLIT].mean()*1e4))
for thr in (60,65,75,80):
    d,_,_=run(C.COINS,thr); n=d.exc-0.015
    print("thr",thr,"n",len(d),"net mean %+.0f med %+.0f t(month) %.2f"%(n.mean()*1e4,n.median()*1e4,ct(n,d.date.dt.to_period('M'))))
# placebo: random entry days per coin, same count and hold lengths, excess vs drift
rng=np.random.default_rng(1); pm=[]
for k in range(1000):
    v=[]
    for s,g in df.groupby("sym"):
        c=F[s].close.values; n=len(c)
        for h in g.days.values:
            e=rng.integers(0,n-h); v.append(c[e+h]/c[e]-1-(np.exp(MU[s]*h)-1))
    pm.append(np.mean(v))
pm=np.array(pm); print("placebo gross excess mean %+.0f bp, real %+.0f, pct %.1f"%(pm.mean()*1e4,df.exc.mean()*1e4,(pm<df.exc.mean()).mean()*100))
# from 2021 (all 5 coins live, post SOL/AVAX listing pump)
d,_,_=run(C.COINS,start="2022-01-01"); n=d.exc-0.015
print("2022+ n",len(d),"net mean %+.0f med %+.0f t(month) %.2f"%(n.mean()*1e4,n.median()*1e4,ct(n,d.date.dt.to_period('M'))))
