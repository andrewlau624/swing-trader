import pandas as pd, numpy as np
m=pd.read_parquet('/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/bad619c6-1952-49ad-9cea-d66d4400c09e/scratchpad/j/m.parquet').dropna(subset=['open_'])
m['yr']=m.date.dt.year
for r in ['ZA','SE']:
    g=m[m.region==r]
    print(r,'by-year co med bp/n:',' '.join(f"{y}:{x.co.median()*1e4:.0f}/{len(x)}" for y,x in g.groupby('yr')))
    print('  cc med',g.cc.median()*1e4,'open==close share',(g.open_==g.close_).mean().round(2),'live-names 2024+ events',len(g[g.yr>=2024]),'names',g[g.yr>=2024].infocode.nunique(), 'distinct ex-dates/yr 2019+', g[g.yr>=2019].groupby('yr').date.nunique().mean().round(0))
    print('  2019+ names:',sorted(g[g.yr>=2024].dsqtname.str[:26].unique())[:12])
