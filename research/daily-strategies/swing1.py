import sys,pickle,time; sys.path.insert(0,"/Users/andrewlau/documents/code/projects/swing-trader/data/research/swing")
from h import *
b=bars(); t=time.time()
def cap(c): c.selection.top_n=999; c.portfolio.position_pct=0.10; c.walkforward.trade_days=1; c.walkforward.step_days=1
s,res=run(b,'swing_1d_uncapped_ovn',cfgmod=cap,min_overnight_share=0.3); print(s,round(time.time()-t),'s',flush=True)
d=pickle.load(open("/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/swing_eq.pkl","rb")); d['swing_1d']=res.equity; pickle.dump(d,open("/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/swing_eq.pkl","wb")); print("DONE",flush=True)
