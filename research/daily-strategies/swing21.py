import sys,pickle; sys.path.insert(0,"/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/a8c2ed99-2407-460f-90bd-79c42fa36e6e/scratchpad")
from h import *
b=bars()
def cap(c): c.selection.top_n=999; c.portfolio.position_pct=0.10; c.walkforward.trade_days=21; c.walkforward.step_days=21
s,res=run(b,'swing_21d_uncapped_ovn',cfgmod=cap,min_overnight_share=0.3); print(s,flush=True)
d=pickle.load(open("/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/b545e432-8693-429a-8b21-0970cd88b5e7/scratchpad/swing_eq.pkl","rb")); d['swing_21d']=res.equity; pickle.dump(d,open("/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/b545e432-8693-429a-8b21-0970cd88b5e7/scratchpad/swing_eq.pkl","wb")); print("DONE")
