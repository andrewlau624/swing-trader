exec(open(__file__.replace('ovnout.py','ovnport.py')).read().split("rules={")[0])
vol20=np.log(C/C1).rolling(20).std()*np.sqrt(252)
def yr(r): return " ".join(f"{v:5.0f}" for v in (r.groupby(r.index.year).apply(lambda x:(1+x).prod()-1)*100).values)
base=(day<=-0.08)&(ibs<0.1)
for lab,sig in [('base',base),('base & vol20>=0.6',base&(vol20>=0.6))]:
    for cap in [None,0.25,0.10]:
        global on
        on0=on.copy()
        if cap is not None: on=on0.clip(-cap,cap)
        r,n=port(sig,-day,maxw=0.1,cost=5); print(stats(r,f"{lab} winsor±{cap}"), 'yrs',yr(r))
        on=on0
    # per-day equal weight trade mean and median
    x=on.where(sig&elig)
    dm=x.mean(axis=1).dropna(); print(f"   per-night mean {dm.mean()*1e4:.1f}bp  median-night {dm.median()*1e4:.1f}bp  %nights>0 {100*(dm>0).mean():.1f}  per-trade median {np.nanmedian(x.values)*1e4:.1f}bp")
