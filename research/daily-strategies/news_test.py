import pandas as pd, numpy as np, pickle, re, os
SP=os.path.dirname(os.path.abspath(__file__))
x=pd.read_pickle(f"{SP}/night_trades.pkl"); news=pickle.load(open(f"{SP}/news.pkl","rb"))
idx=pd.read_pickle(f"{SP}/panel.pkl")['close'].index; prevd={d:idx[i-1] for i,d in enumerate(idx) if i}
CATS={'dilution':r'offering|priced|pricing|registered direct|private placement|at-the-market|\bATM\b|warrant|shelf|dilut',
      'fda_trial':r'\bFDA\b|\bCRL\b|complete response|clinical hold|topline|top-line|endpoint|\btrial\b|PDUFA',
      'legal':r'lawsuit|class action|investigat|subpoena|fraud|investor alert|shareholder alert|securities litigation|\bSEC\b',
      'distress':r'bankrupt|chapter 11|delist|going concern|default|restructur|nasdaq notice|deficiency',
      'earnings':r'earnings|results|guidance|revenue|quarter|\bQ[1-4]\b|\bEPS\b',
      'downgrade':r'downgrad|cuts? .*target|lowers? .*target|price target cut'}
def heads(d,s):
    lo=pd.Timestamp(prevd.get(d,d)).tz_localize('America/New_York')+pd.Timedelta(hours=16)
    out=[]
    for t,syms,h in news.get(d,[]):
        if s in syms and pd.Timestamp(t).tz_convert('America/New_York')>=lo: out.append(h)
    return out
x['heads']=[heads(d,s) for d,s in zip(x.date,x.sym)]
x['n_news']=x.heads.apply(len)
for k,p in CATS.items(): x[k]=x.heads.apply(lambda hs: any(re.search(p,h,re.I) for h in hs))
x['no_news']=x.n_news==0
x['r']=x.ret.clip(-.1,.1); x['yr']=x.date.dt.year
x=x[x.vol20>=0.6]                               # the live rule set
x.to_pickle(f"{SP}/night_news.pkl")
print(f"honest night trades (vol>=60%): {len(x)}; with any news before 15:40: {100*(x.n_news>0).mean():.0f}%\n")
def row(m,lab):
    g=x[m]; 
    if len(g)<50: print(f"{lab:14s} n={len(g)} too few"); return
    a=g[g.yr<=2023].r; b=g[g.yr>=2024].r
    t=g.r.mean()/g.r.std()*np.sqrt(len(g))
    print(f"{lab:14s} n={len(g):5d} ({100*len(g)/len(x):4.1f}%)  mean {g.r.mean()*1e4:6.1f}bp  t {t:5.1f}  | 21-23 {a.mean()*1e4:6.1f}  24-26 {b.mean()*1e4:6.1f}  win {100*(g.r>0).mean():4.1f}%")
row(x.r==x.r,'ALL'); row(x.no_news,'no news'); row(~x.no_news,'any news')
for k in CATS: row(x[k],k)
print("\nexcess vs same-day others (controls for market-wide nights):")
dm=x.groupby('date').r.transform('mean'); x['ex']=x.r-dm
for k in ['no_news']+list(CATS):
    g=x[x[k] if k!='no_news' else x.no_news]; g=g[x.groupby('date').sym.transform('count').loc[g.index]>1]
    if len(g)>=50: print(f"  {k:12s} excess {g.ex.mean()*1e4:6.1f}bp  t {g.ex.mean()/g.ex.std()*np.sqrt(len(g)):5.1f}  n={len(g)}")
