import sys,pickle; sys.path.insert(0,"/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/a8c2ed99-2407-460f-90bd-79c42fa36e6e/scratchpad")
from h import *
b=bars()
def cap(c): c.selection.top_n=999; c.portfolio.position_pct=0.10
out={}
for lab,cm,kw in [('swing_current',None,{}),('swing_uncapped_ovn',cap,{'min_overnight_share':0.3})]:
    s,res=run(b,lab,cfgmod=cm,**kw); print(s,flush=True); out[lab]=res.equity
pickle.dump(out,open("/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/b545e432-8693-429a-8b21-0970cd88b5e7/scratchpad/swing_eq.pkl","wb")); print("DONE")
