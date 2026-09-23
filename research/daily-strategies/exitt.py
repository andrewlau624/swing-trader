from panel import *
import glob
P=panel(); C=P['close']; O=P['open']; idx=C.index
nxt={d:idx[i+1] for i,d in enumerate(idx[:-1])}
x=pd.read_pickle(f'{SP}/dtime.pkl'); x=x[x['T']==1540].copy()
x['n_raw']=x.groupby('date').sym.transform('count'); x=x[x.vol20>=0.6]
am={}
for f in glob.glob(f'{SP}/am1/*.parquet'):
    df=pd.read_parquet(f); t=df.timestamp.dt.tz_convert('America/New_York'); df['hm']=t.dt.hour*100+t.dt.minute
    am[pd.Timestamp(f.split('/')[-1][:10])]=df
EX={'open (auction)':None,'9:35':935,'9:45':945,'10:00':1000,'10:30':1030}
rows=[]
for d,s,c in zip(x.date,x.sym,[C.at[a,b] for a,b in zip(x.date,x.sym)]):
    nd=nxt.get(d); 
    if nd is None or nd not in am: continue
    g=am[nd]; g=g[g.symbol==s].set_index('hm')
    r={'date':d,'sym':s,'open (auction)':O.at[nd,s]/c-1}
    for k,hm in EX.items():
        if hm is None: continue
        pre=g[g.index<hm]
        r[k]=(pre.close.iloc[-1]/c-1) if len(pre) else np.nan
    rows.append(r)
R=pd.DataFrame(rows).dropna(); R=R.merge(x[['date','sym','n_raw']],on=['date','sym'])
n=R.groupby('date').sym.transform('count'); R['w']=np.minimum(1/n,0.1)*np.minimum(1,30/R.n_raw)
days=pd.read_pickle(f'{SP}/series2.pkl').index
print(f"{'exit at':16s} {'per-trade bp':>12s} {'2021-23':>16s} {'2024-26':>16s} {'full':>16s}")
for k in EX:
    extra=0 if k.startswith('open') else 5
    R['p']=R.w*(R[k]-(15+extra)/1e4)
    r=R.groupby('date').p.sum().shift(1).reindex(days).fillna(0)
    out=[]
    for sl in [slice('2021','2023'),slice('2024','2026'),slice('2021','2026')]:
        v=r[sl]; y=len(v)/252; eq=(1+v).cumprod()
        out.append(f"{((1+v).prod()**(1/y)-1)*100:6.1f}%/{v.mean()/v.std()*np.sqrt(252):4.2f}/{(eq/eq.cummax()-1).min()*100:4.0f}")
    print(f"{k:16s} {R[k].clip(-.1,.1).mean()*1e4:10.1f}   "+"  ".join(out))
