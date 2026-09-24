import sys,pickle; sys.path.insert(0,"/Users/andrewlau/documents/code/projects/swing-trader/data/research/swing")
from h import *
b=bars()
def cap(c): c.selection.top_n=999; c.portfolio.position_pct=0.10
out={}
for lab,cm,kw in [('swing_current',None,{}),('swing_uncapped_ovn',cap,{'min_overnight_share':0.3})]:
    s,res=run(b,lab,cfgmod=cm,**kw); print(s,flush=True); out[lab]=res.equity
pickle.dump(out,open("/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/swing_eq.pkl","wb")); print("DONE")
