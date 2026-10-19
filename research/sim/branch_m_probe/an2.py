import pandas as pd, numpy as np
D='/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/bad619c6-1952-49ad-9cea-d66d4400c09e/scratchpad/m/'
m=pd.read_parquet(D+'m.parquet')
a=m[m.grp.str.startswith('A')&m.ef10.notna()].copy()
print('A raw: median drop/div open',((-a.ro*a.pc/a.divrate)).median().round(2) if False else '')
a['rawo']=-a.ro  # not market adj; placeholder
a['dr']=(a.pc-a.open_)/a.divrate   # drop ratio (open)
a['drc']=(a.pc-a.close_)/a.divrate
print('A drop ratio median open/close',a.dr.median().round(2),a.drc.median().round(2))
# date-relative: demean vs same-date ex cohort (all A names that date)
for c in ['eo','ec','ef5','ef10']:
    a[c+'_r']=a[c]-a.groupby('date')[c].transform('median')
a['ytile']=a.groupby('yr').y.transform(lambda s:pd.qcut(s.rank(method='first'),3,labels=['lowY','midY','highY']).astype(str))
r=a.groupby(['sz','ytile']).agg(n=('y','size'),y=('y','median'),dr_c=('drc','median'),eo_r=('eo_r','median'),ec_r=('ec_r','median'),f5_r=('ef5_r','median'),f10_r=('ef10_r','median'))
r[['y','eo_r','ec_r','f5_r','f10_r']]*=1e4
print(r.round(2).to_string())
# year sign for small+lowY relative close excess and relative +10 drift
s=a[(a.sz=='small')&(a.ytile=='lowY')]
t=s.groupby('yr').agg(n=('y','size'),ec_r=('ec_r','median'),f5_r=('ef5_r','median'),f10_r=('ef10_r','median'))*[1,1e4,1e4,1e4]
t['n']=s.groupby('yr').size();print(t.round(1).T.to_string())
print('years ec_r<0:',(t.ec_r<0).sum(),'/',len(t),' f10_r>0:',(t.f10_r>0).sum())
# recovery: ratio of cohort-relative drift to relative extra drop
print('overall small-lowY: ec_r',s.ec_r.median()*1e4,'f5_r',s.ef5_r.median()*1e4,'f10_r',s.ef10_r.median()*1e4)
