import pandas as pd, numpy as np
from research.sim.borrow_xs import conn
db=conn()
sets={}
for r in ['AU','GB','NZ','SG','HK','JP','CH','SE','AT','DE','NL','FR','IT','BE','NO','MX','PL','ZA']:
    d=db.raw_sql(f"select infocode,dsqtname,region,primisocurrcode cur,typecode from tr_ds_equities.ds2ctryqtinfo where region='{r}' and (typecode='PREF' or dsqtname ~* 'HYB|PERP|SUB RED|BBSW|NCPS|CAPS|RESET|PREF')")
    sets[r]=d
allq=pd.concat(sets.values()); print(allq.groupby('region').size().to_dict())
ics=[int(x) for x in allq.infocode.unique()]
px=[];dv=[]
for i in range(0,len(ics),150):
    ch=",".join(map(str,ics[i:i+150]))
    px.append(db.raw_sql(f"select infocode,marketdate,open_,close_,volume,isocurrcode from tr_ds_equities.ds2primqtprc where infocode in ({ch}) and marketdate>='2004-01-01' and close_>0"))
    dv.append(db.raw_sql(f"select infocode,divtypecode,divrate,isocurrcode dcur,effectivedate,effdateestflag from tr_ds_equities.ds2div where infocode in ({ch}) and effectivedate>='2004-06-01'"))
px=pd.concat(px);dv=pd.concat(dv)
px.to_parquet('/tmp/x.parquet') if False else None
px['date']=pd.to_datetime(px.marketdate);px=px.sort_values(['infocode','date']).drop_duplicates(['infocode','date'])
px['pc']=px.groupby('infocode').close_.shift(1);px['gap']=(px.date-px.groupby('infocode').date.shift(1)).dt.days
dv['date']=pd.to_datetime(dv.effectivedate);dv=dv[(dv.divrate>0)&(dv.effdateestflag.fillna('A')!='E')]
dv=dv.groupby(['infocode','date']).agg(div=('divrate','sum'),dcur=('dcur','first')).reset_index()
print(len(px),len(dv),dv.dcur.value_counts().head(5).to_dict(),px.isocurrcode.value_counts().head(5).to_dict());m=px.merge(dv,on=['infocode','date']);print('merged',len(m),(m.dcur==m.isocurrcode).sum(),(m.gap<=5).sum())
m=m[(m.dcur==m.isocurrcode)&(m.gap<=5)&(m.pc>0)].merge(allq[['infocode','region','dsqtname']],on='infocode')
m['y']=m['div']/m.pc
m=m[(m.y<0.08)&(m.y>0)&((m.close_/m.pc-1).abs()<0.25)]
m['co']=m.open_/m.pc-1+0; m['co_ret']=m.pc/m.open_-1  # holder: buy pc, sell open
m['co']=m.open_/m.pc-1+m['div']/m.pc
m['cc']=m.close_/m.pc-1+m['div']/m.pc
m['dr_o']=(m.pc-m.open_)/m['div'];m['dr_c']=(m.pc-m.close_)/m['div']
def f(g):
    return pd.Series(dict(n=len(g),names=g.infocode.nunique(),y_med=g.y.median(),yr0=g.date.dt.year.min(),yr1=g.date.dt.year.max(),co_med_bp=g.co.median()*1e4,cc_med_bp=g.cc.median()*1e4,co_mean=g.co.clip(-.05,.05).mean()*1e4,drop_o=g.dr_o.median(),drop_c=g.dr_c.median(),px_med=g.pc.median()))
print(m.groupby('region').apply(f).round(2).to_string())
m.to_parquet('/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/bad619c6-1952-49ad-9cea-d66d4400c09e/scratchpad/j/m.parquet')
