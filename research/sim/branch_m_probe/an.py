import pandas as pd, numpy as np
D='/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/bad619c6-1952-49ad-9cea-d66d4400c09e/scratchpad/m/'
px=pd.read_parquet(D+'px.parquet');dv=pd.read_parquet(D+'dv.parquet')
px['date']=pd.to_datetime(px.marketdate);px=px.sort_values(['infocode','date']).drop_duplicates(['infocode','date'])
g=px.groupby('infocode')
px['pc']=g.close_.shift(1);px['gap']=(px.date-g.date.shift(1)).dt.days
px['rc']=px.close_/px.pc-1;px['ro']=px.open_/px.pc-1
px['dv20']=(px.close_*px.volume).groupby(px.infocode).transform(lambda s:s.rolling(20,min_periods=10).mean().shift(1))
ok=(px.gap<=6)&px.rc.abs().lt(.3)
mk=px[ok].groupby('date').agg(mc=('rc','median'),mo=('ro','median'),n=('rc','size'))
mk=mk[mk.n>500]
# forward market cum return index (close-to-close)
mi=(1+mk.mc).cumprod()
px=px.join(mk[['mc','mo']],on='date')
# stock forward closes +5,+10 sessions
for h in (5,10):
    px[f'f{h}']=g.close_.shift(-h)/px.close_-1
dates=mk.index
pos={d:i for i,d in enumerate(dates)}
def mfwd(d,h):
    i=pos.get(d);
    return np.nan if i is None or i+h>=len(dates) else mi.iloc[i+h]/mi.iloc[i]-1
dv=dv[(dv.isocurrcode=='JPY')&(dv.effdateestflag.fillna('A')!='E')&dv.divtypecode.isin(['FIN','INT','YR','HYR'])]
dv['date']=pd.to_datetime(dv.effectivedate)
dv=dv.groupby(['infocode','date']).divrate.sum().reset_index()
m=px.merge(dv,on=['infocode','date'])
m=m[(m.gap<=6)&(m.pc>0)&m.mc.notna()]
m['y']=m.divrate/m.pc
m=m[(m.y<.1)&(m.rc.abs()<.25)]
m['eo']=m.ro-m.mo+m.y   # excess open move, dividend added back (>0 => under-adjust)
m['ec']=m.rc-m.mc+m.y
for h in (5,10): m[f'ef{h}']=m[f'f{h}']-[mfwd(d,h) for d in m.date]
m['mon']=m.date.dt.month;m['dom']=m.date.dt.day;m['yr']=m.date.dt.year
m['eom']=m.dom>=24
m['grp']=np.where(m.mon.isin([3,9])&m.eom,'A_perkmonth_Mar/Sep_end',np.where(m.mon.isin([6,12])&m.eom,'B_Jun/Dec_end',np.where(m.eom,'C_other_month_end','D_not_month_end')))
m['sz']=pd.qcut(m.dv20.rank(method='first'),3,labels=['small','mid','large']).astype(str)  # crude, pooled
m=m[m.dv20.notna()]
m['sz']=m.groupby('yr').dv20.transform(lambda s:pd.qcut(s.rank(method='first'),3,labels=False)).map({0:'small',1:'mid',2:'large'})
bp=lambda s:s*1e4
def rep(x,name):
    r=x.groupby(name).agg(n=('ec','size'),y_med=('y','median'),ex_open_med=('eo','median'),ex_close_med=('ec','median'),f5=('ef5','median'),f10=('ef10','median'))
    print((r*[1,1e4,1e4,1e4,1e4,1e4]).round(1).to_string())
print('ALL events',len(m));rep(m,'grp')
print('\nby size within A');rep(m[m.grp.str.startswith('A')],'sz')
print('\nby size within C (control)');rep(m[m.grp.str.startswith('C')],'sz')
print('\nA vs C, by size & month 3 vs 9');rep(m[m.grp.str[0].isin(['A','C'])&(m.sz=='small')],['grp','mon'])
# year-by-year sign for A small and C small: ec median
a=m[m.grp.str.startswith('A')&(m.sz!='large')].groupby('yr').agg(n=('ec','size'),ec=('ec','median'),f5=('ef5','median'),f10=('ef10','median'))
c=m[m.grp.str.startswith('C')&(m.sz!='large')].groupby('yr').agg(nC=('ec','size'),ecC=('ec','median'),f5C=('ef5','median'),f10C=('ef10','median'))
yy=a.join(c);print((yy*[1,1e4,1e4,1e4,1,1e4,1e4,1e4]).round(1).to_string())
d=(yy.ec-yy.ecC);print('A-C ec>0 years',(d>0).sum(),'/',d.notna().sum(),'  ec<0 yrs A',(yy.ec<0).sum())
m.to_parquet(D+'m.parquet')
