# DESCRIPTIVE: first close <=80% of $25 par inside each window (non-peeking trigger), raw closes, no costs. Not a judged test.
import pandas as pd, numpy as np, os
H=os.path.expanduser('~/data/sharadar/')
t=pd.read_parquet(H+'tickers.parquet'); c=t[(t.table=='SFP')&(t.category=='CEF Preferred')]
f=pd.read_parquet(H+'funds.parquet'); f=f[f.ticker.isin(c.ticker)].copy(); f['date']=pd.to_datetime(f['date'])
px=f.pivot_table(index='date',columns='ticker',values='closeunadj'); vol=f.pivot_table(index='date',columns='ticker',values='volume')
W={'2018Q4':('2018-10-01','2019-01-31'),'2020-03':('2020-02-15','2020-05-29'),'2022':('2022-01-01','2022-12-31'),'2023-03':('2023-03-01','2023-05-31')}
par10={'TYG-PB','TYG-PC','NTX-PC','NXJ-PC'}
for thr in (0.85,0.80):
  print('\n######## trigger close <= %.0f%% of $25'%(thr*100))
  for k,(a,b) in W.items():
    rows=[]
    for tk in px.columns:
        if tk in par10: continue
        s=px[tk].loc[a:b].dropna()
        hit=s[s<=25*thr]
        if hit.empty: continue
        d=hit.index[0]; e=hit.iloc[0]; full=px[tk].dropna(); i=full.index.get_loc(d)
        r=lambda n: full.iloc[i+n]/e-1 if i+n<len(full) else np.nan
        v=(vol[tk].loc[:d].tail(5).mean()*e)
        # last obs
        rows.append((tk,d.date(),e,r(20),r(60),r(120),full.iloc[-1]/e-1 if full.index[-1]>d else np.nan,v,full.iloc[i:i+120].min()/e-1))
    d=pd.DataFrame(rows,columns=['tk','entry','px','r20','r60','r120','r_last','dvol5','mae120'])
    print('\n==',k,'n',len(d))
    if len(d):
        print('median r20 %.3f r60 %.3f r120 %.3f | mean r60 %.3f | hit60 %.2f | min r60 %.3f | median MAE120 %.3f | median 5d$vol %.0f'%(d.r20.median(),d.r60.median(),d.r120.median(),d.r60.mean(),(d.r60>0).mean(),d.r60.min(),d.mae120.median(),d.dvol5.median()))
        print(d.round(3).to_string(index=False))
