# DESCRIPTIVE ONLY. Sharadar SFP 'CEF Preferred' raw closes in crisis windows. No rule, no judged backtest.
import pandas as pd, numpy as np, os
H=os.path.expanduser('~/data/sharadar/')
t=pd.read_parquet(H+'tickers.parquet'); c=t[(t.table=='SFP')&(t.category=='CEF Preferred')]
f=pd.read_parquet(H+'funds.parquet'); print(f.columns.tolist())
f=f[f.ticker.isin(c.ticker)].copy(); f['date']=pd.to_datetime(f['date'])
px=f.pivot_table(index='date',columns='ticker',values='closeunadj')
print(px.shape, px.index.min())
W={'2015-16 energy/HY':('2015-10-01','2016-03-31'),'2018Q4':('2018-10-01','2019-01-31'),
   '2020-03':('2020-02-15','2020-05-29'),'2022':('2022-01-01','2022-12-31'),'2023-03':('2023-03-01','2023-05-31')}
for k,(a,b) in W.items():
    s=px.loc[a:b]; rows=[]
    for tk in s.columns:
        x=s[tk].dropna()
        if len(x)<20: continue
        pre=px[tk].loc[:a].dropna()
        p0=pre.iloc[-1] if len(pre) else np.nan
        lo=x.min(); dl=x.idxmin()
        full=px[tk].dropna(); i=full.index.get_loc(dl)
        r20=full.iloc[i+20]/lo-1 if i+20<len(full) else np.nan
        r60=full.iloc[i+60]/lo-1 if i+60<len(full) else np.nan
        rows.append((tk,p0,lo,lo/25-1,dl.date(),r20,r60))
    d=pd.DataFrame(rows,columns=['tk','pre','low','low_vs_par','low_date','r20','r60'])
    print('\n==',k,'n issues',len(d))
    if len(d):
        print('median low vs par %.3f  n<=-10%%: %d  n<=-20%%: %d'%(d.low_vs_par.median(),(d.low_vs_par<=-.1).sum(),(d.low_vs_par<=-.2).sum()))
        print('median r20 from trough low (look-ahead, upper bound) %.3f r60 %.3f'%(d.r20.median(),d.r60.median()))
        print(d.sort_values('low_vs_par').head(12).round(3).to_string(index=False))
# end-of-life: last price for delisted
last=[]
for tk in c[c.isdelisted=='Y'].ticker:
    x=px[tk].dropna()
    if len(x): last.append((tk,x.index[-1].date(),x.iloc[-1]))
l=pd.DataFrame(last,columns=['tk','last_date','last_px']); 
print('\nDelisted CEF pref last close: n',len(l),' <23:',(l.last_px<23).sum(),' 23-26:',((l.last_px>=23)&(l.last_px<=26)).sum(),' >26:',(l.last_px>26).sum())
print(l[l.last_px<23].to_string(index=False))
