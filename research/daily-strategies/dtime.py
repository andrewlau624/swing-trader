from panel import *
import glob
P=panel(); O,H,L,C,V=[P[k].astype('float64') for k in ['open','high','low','close','volume']]
C1=C.shift(1); advp=(C*V).rolling(20).mean().shift(1)
vol20=(np.log(C/C1).rolling(20).std()*np.sqrt(252)).shift(1)
Onext=O.shift(-1)
TIMES=[1530,1535,1540,1545,1549]
rows=[]
for f in sorted(glob.glob(f'{SP}/lm1/*.parquet')):
    d=pd.Timestamp(f.split('/')[-1][:10]); df=pd.read_parquet(f)
    t=df.timestamp.dt.tz_convert('America/New_York'); df['hm']=t.dt.hour*100+t.dt.minute
    for s,g in df.groupby('symbol'):
        if s not in C.columns: continue
        pc=C1.at[d,s]; a=advp.at[d,s]
        if not (pc>=5 and a>=10e6): continue
        Ld,Hd=L.at[d,s],H.at[d,s]; g=g.sort_values('hm')
        for T in TIMES:
            pre=g[g.hm<T]; post=g[g.hm>=T]
            if pre.empty: continue
            p=pre.close.iloc[-1]
            L_=Ld if (post.low.min() if len(post) else np.inf)>Ld+1e-9 else pre.low.min()
            H_=Hd if (post.high.max() if len(post) else -np.inf)<Hd-1e-9 else pre.high.max()
            L_=min(L_,p); H_=max(H_,p)
            day=p/pc-1; ib=(p-L_)/(H_-L_) if H_>L_ else np.nan
            if day<=-0.08 and ib<0.1:
                rows.append((T,d,s,vol20.at[d,s],Onext.at[d,s]/C.at[d,s]-1))
x=pd.DataFrame(rows,columns=['T','date','sym','vol20','ret']).dropna()
x.to_pickle(f'{SP}/dtime.pkl')
days=pd.read_pickle(f'{SP}/series2.pkl').index
for T in TIMES:
    g=x[x['T']==T].copy(); g['n_raw']=g.groupby('date').sym.transform('count')
    g=g[g.vol20>=0.6]; n=g.groupby('date').sym.transform('count')
    g['w']=np.minimum(1/n,0.1)*np.minimum(1,30/g.n_raw); g['p']=g.w*(g.ret-15/1e4)
    r=g.groupby('date').p.sum().shift(1).reindex(days).fillna(0)
    out=[]
    for sl in [slice('2021','2023'),slice('2024','2026'),slice('2021','2026')]:
        v=r[sl]; y=len(v)/252; eq=(1+v).cumprod()
        out.append(f"{((1+v).prod()**(1/y)-1)*100:5.1f}%/{v.mean()/v.std()*np.sqrt(252):4.2f}/{(eq/eq.cummax()-1).min()*100:4.0f}")
    print(f"signal at {T//100}:{T%100:02d}  trades/day {len(g)/len(days):4.1f}   "+"  ".join(out))
