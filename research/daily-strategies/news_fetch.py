import sys, os, time, pickle
sys.path.insert(0,"/Users/andrewlau/Documents/Code/Projects/swing-trader")
import pandas as pd
from swingtrader.config import require_alpaca_keys
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest
SP=os.path.dirname(os.path.abspath(__file__))
x=pd.read_pickle(f"{SP}/night_trades.pkl")
k,s=require_alpaca_keys(); c=NewsClient(k,s)
out=f"{SP}/news.pkl"; got=pickle.load(open(out,'rb')) if os.path.exists(out) else {}
days=sorted(x.date.unique())
for i,d in enumerate(days):
    if d in got: continue
    syms=sorted(x[x.date==d].sym.unique())
    d=pd.Timestamp(d); prev=d-pd.Timedelta(days=4)   # generous; filtered below to prev close
    start=(prev).tz_localize('America/New_York'); end=(d+pd.Timedelta(hours=15,minutes=40)).tz_localize('America/New_York')
    items=[]
    for j in range(0,len(syms),40):
        tok=None
        for _ in range(20):
            try:
                r=c.get_news(NewsRequest(symbols=",".join(syms[j:j+40]),start=start,end=end,limit=50,page_token=tok)).dict()
            except Exception as e:
                time.sleep(3); continue
            items+=r.get('news',[]); tok=r.get('next_page_token')
            if not tok: break
    got[d]=[(str(n['created_at']),n['symbols'],n['headline']) for n in items]
    if i%50==0: pickle.dump(got,open(out,'wb')); print(i,len(days),flush=True)
pickle.dump(got,open(out,'wb')); print("DONE",flush=True)
