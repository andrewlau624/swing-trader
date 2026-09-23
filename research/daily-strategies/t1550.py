exec(open(__file__.replace('t1550.py','ovnport.py')).read().split("rules={")[0])
import glob
vol20=np.log(C/C1).rolling(20).std()*np.sqrt(252)
rows=[]
for f in sorted(glob.glob(f'{SP}/lm1/*.parquet')):
    d=pd.Timestamp(f.split('/')[-1][:10]); df=pd.read_parquet(f)
    t=df.timestamp.dt.tz_convert('America/New_York'); df['hm']=t.dt.hour*100+t.dt.minute
    for s,g in df.groupby('symbol'):
        if s not in C.columns: continue
        pre=g[g.hm<1550]; post=g[g.hm>=1550]
        if pre.empty: continue
        p50=pre.close.iloc[-1]
        Ld,Hd=L.at[d,s],H.at[d,s]
        low_late = post.low.min() if len(post) else np.inf
        L50 = Ld if low_late>Ld+1e-9 else pre.low.min()
        high_late= post.high.max() if len(post) else -np.inf
        H50 = Hd if high_late<Hd-1e-9 else pre.high.max()
        rows.append(dict(date=d,sym=s,p50=p50,L50=L50,H50=max(H50,p50)))
x=pd.DataFrame(rows)
x['pc']=[C1.at[a,b] for a,b in zip(x.date,x.sym)]
x['day50']=x.p50/x.pc-1; x['ibs50']=(x.p50-x.L50)/(x.H50-x.L50).replace(0,np.nan)
S50=pd.DataFrame(False,index=C.index,columns=C.columns); SC=S50.copy().astype(float)*np.nan
m=(x.day50<=-0.08)&(x.ibs50<0.1)
for a,b,dv in zip(x.date[m],x.sym[m],x.day50[m]): S50.at[a,b]=True; SC.at[a,b]=-dv
dates=x.date.unique(); covered=C.index.isin(dates)
cl=(day<=-0.08)&(ibs<0.1)
cl=cl & pd.DataFrame(np.repeat(covered[:,None],C.shape[1],1),index=C.index,columns=C.columns)
for lab,sig,sc in [('close-signal (lookahead)',cl,-day),('15:50-signal (honest)',S50,SC)]:
    for vf in [False,True]:
        s=sig&(vol20>=0.6) if vf else sig
        for cost in [5,10]:
            r,n=port(s,sc,maxw=0.1,cost=cost); r=r[r.index.isin(dates)|True]
            print(stats(r.loc[x.date.min():x.date.max()],f"{lab}{' vol>=.6' if vf else ''} c{cost}"), f"names {n[n>0].mean():.1f}")
ov=(S50&cl).sum().sum(); print('overlap', ov, 'close-only', (cl&~S50).sum().sum(), '1550-only', (S50&~cl).sum().sum(), 'coverage days', len(dates))
# variant: enter at 15:50 price instead of MOC
ON50=pd.DataFrame(np.nan,index=C.index,columns=C.columns)
for a,b,p in zip(x.date[m],x.sym[m],x.p50[m]): ON50.at[a,b]=O.shift(-1).at[a,b]/p-1
on_save=on
on=ON50
for cost in [5,10,15]:
    r,n=port(S50,SC,maxw=0.1,cost=cost); print(stats(r.loc['2021':],f"enter@15:50 price c{cost}"))
on=on_save
import sys; sys.path.insert(0,SP); from noise import noise
rN,_=port(S50,SC,maxw=0.1,cost=5); rN10,_=port(S50,SC,maxw=0.1,cost=10)
B,_=noise('QQQ',cost_bps=0.5)
df=pd.concat([rN.rename('n5'),rN10.rename('n10'),B.rename('q')],axis=1,sort=True).loc['2021-02':].fillna(0)
print('corr',df.corr().round(2).values[0,2])
print(stats(df.n5+df.q,'HONEST night c5 + QQQ noise'))
print(stats(df.n10+df.q,'HONEST night c10 + QQQ noise'))
print(stats(0.5*df.n5+df.q,'HONEST 0.5 night c5 + QQQ noise'))
