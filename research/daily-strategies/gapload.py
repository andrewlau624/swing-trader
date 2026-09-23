import sys,os,glob,pickle; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from panel import *
def build():
    pk=f"{SP}/gap_arr.pkl"
    if os.path.exists(pk): return pickle.load(open(pk,'rb'))
    P=panel(); O,H,L,C,V=[P[k].astype('float64') for k in ['open','high','low','close','volume']]
    C1=C.shift(1); adv=(C*V).rolling(20).mean().shift(1); advs=V.rolling(20).mean().shift(1)
    tr=np.maximum(H-L,np.maximum((H-C1).abs(),(L-C1).abs())); atr=tr.rolling(14).mean().shift(1)
    ret5=(C1/C.shift(6)-1)
    spy=(C['SPY']/C1['SPY']-1)
    recs=[]; arrs=[]
    for f in sorted(glob.glob(f"{SP}/gm1/*.parquet")):
        d=pd.Timestamp(os.path.basename(f)[:10]); df=pd.read_parquet(f)
        t=df.timestamp.dt.tz_convert('America/New_York'); df['m']=t.dt.hour*60+t.dt.minute-570
        df=df[(df.m>=0)&(df.m<390)]
        for s,g in df.groupby('symbol'):
            a=np.full((5,390),np.nan,dtype='float32')
            for j,k in enumerate(['open','high','low','close','volume']): a[j,g.m.values]=g[k].values
            c=pd.Series(a[3]).ffill().values; a[3]=c
            for j in range(3): a[j]=np.where(np.isnan(a[j]),c,a[j])
            a[4]=np.nan_to_num(a[4])
            if np.isnan(a[3,0]) or np.isnan(a[3,-1]): continue
            try:
                recs.append(dict(date=d,sym=s,pc=C1.at[d,s],dopen=O.at[d,s],dclose=C.at[d,s],adv=adv.at[d,s],advs=advs.at[d,s],atr=atr.at[d,s],ret5=ret5.at[d,s]))
            except KeyError: continue
            arrs.append(a)
    meta=pd.DataFrame(recs); A=np.stack(arrs)
    meta['gap']=meta.dopen/meta.pc-1
    meta['rv5']=A[:,4,:5].sum(axis=1)/(meta.advs/78)
    meta['or5_ret']=A[:,3,4]/A[:,0,0]-1
    pickle.dump((meta,A),open(pk,'wb'),protocol=4); return meta,A
if __name__=="__main__":
    meta,A=build(); print(meta.shape,A.shape); print(meta.describe().T[['mean','50%']])
    # sanity: minute open vs daily open, minute last close vs daily close
    print('open match', np.nanmedian(np.abs(A[:,0,0]/meta.dopen-1)), 'close match',np.nanmedian(np.abs(A[:,3,-1]/meta.dclose-1)))
