import sys; sys.path.insert(0,"/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/a8c2ed99-2407-460f-90bd-79c42fa36e6e/scratchpad"); sys.path.insert(0,"/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/b545e432-8693-429a-8b21-0970cd88b5e7/scratchpad")
from h import *
from tos import tmo
import swingtrader.backtest as bt
from swingtrader.metrics import overnight_share as OS
b=bars()
def gate(mode):
    def f(hist,w):
        if mode=='ovn': return OS(hist,w)
        h=hist.iloc[-60:]; main,sig,ob=tmo(h['open'],h['close'])
        up_recent=((main>sig)&(main.shift()<=sig.shift())&(main.shift()<-ob)).iloc[-3:].any()
        if mode=='veto_up': return 0.0 if up_recent else 1.0
        if mode=='need_os': return 1.0 if main.iloc[-1]< -ob else 0.0
        if mode=='veto_os': return 0.0 if main.iloc[-1]< -ob else 1.0
        if mode=='need_ob': return 1.0 if main.iloc[-1]> 0 else 0.0
    return f
def cap(c): c.selection.top_n=999; c.portfolio.position_pct=0.10
for label,cm in [('current top8',None),('uncapped',cap)]:
    print(summ(run(b,label+' base',cfgmod=cm)[1],label+' base'))
    for mode,thr in [('veto_up',0.5),('need_os',0.5),('veto_os',0.5),('need_ob',0.5),('ovn',0.3)]:
        bt.overnight_share=gate(mode)
        s,_=run(b,f'{label} {mode}',cfgmod=cm,min_overnight_share=thr); print(s)
    bt.overnight_share=OS
