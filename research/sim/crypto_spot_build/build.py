import zipfile,glob,os,io,re,json,requests
import pandas as pd
R="/Users/andrewlau/Documents/Code/Projects/swing-trader/data/research/crypto_spot"
cols=["ot","open","high","low","close","volume","ct","quote_volume","trades","tb","tq","ig"]
dfs=[];bad=0
for f in sorted(glob.glob(R+"/raw/*/*.zip")):
    sym=f.split("/")[-2]
    with zipfile.ZipFile(f) as z:
        raw=z.read(z.namelist()[0])
    d=pd.read_csv(io.BytesIO(raw),header=None,names=cols,usecols=range(9))
    if d.empty: continue
    if d.ot.iloc[0]=="open_time": d=d.iloc[1:].astype({c:float for c in cols[:9]})
    ot=d.ot.astype("int64")
    unit=pd.Series("ms",index=d.index).where(ot<10**14,"us")
    d["date"]=[pd.to_datetime(v,unit=u).normalize() for v,u in zip(ot,unit)]
    d["symbol"]=sym
    dfs.append(d[["date","symbol","open","high","low","close","volume","quote_volume","trades"]])
p=pd.concat(dfs,ignore_index=True)
p["trades"]=p.trades.astype("int64")
p=p.drop_duplicates(["symbol","date"]).sort_values(["symbol","date"]).reset_index(drop=True)
STABLE={"USDC","BUSD","TUSD","FDUSD","DAI","USDP","USDS","USDSB","UST","USTC","PAX","PAXG_","SUSD","EUR","GBP","AEUR","EURI","TRY","BRL","AUD","RUB","UAH","NGN","ZAR","IDRT","BIDR","PLN","RON","ARS","JPY","CZK","MXN","COP","USD1","XUSD","BFUSD","USDE","RLUSD","PYUSD","UUSD","VAI","USDT"}
LEV=re.compile(r"(UP|DOWN|BULL|BEAR)$")
def base(s): return s[:-4]
g=p.groupby("symbol").date.agg(first_date="min",last_date="max")
g["base"]=[base(s) for s in g.index]
g["is_stable_fiat"]=g.base.isin(STABLE)
g["is_leveraged"]=[bool(LEV.search(b)) and b not in {"SUP","JUP","PUP","SYN"} and len(b)>3 and b not in {"SETUP"} for b in g.base]
# restrict leveraged to known historical suffix tokens (e.g., BTCUP); guard false positives
fp=g[g.is_leveraged].base.tolist()
g["delisted"]=g.last_date<pd.Timestamp("2026-09-01")
try:
    cb=requests.get("https://api.exchange.coinbase.com/products",timeout=30).json()
    cbb={x["base_currency"] for x in cb if x["quote_currency"]=="USD" and x["status"]=="online"}
except Exception as e: print("cb fail",e);cbb=set()
g["on_coinbase_us"]=g.base.isin(cbb)
print("coinbase bases",len(cbb))
p=p.merge(g.reset_index()[["symbol","base","first_date","last_date","delisted","is_stable_fiat","is_leveraged","on_coinbase_us"]],on="symbol")
p.to_parquet(R+"/panel.parquet",index=False)
print(len(p),p.date.min(),p.date.max(),p.symbol.nunique())
print("lev flagged",sorted(fp)[:60],len(fp))
print("stable",g[g.is_stable_fiat].index.tolist())
tr=g[~g.is_stable_fiat&~g.is_leveraged]
print("tradable-universe n",len(tr),"delisted",tr.delisted.sum(),"before2026",(tr.last_date<'2026-01-01').sum(),"allbefore2026",(g.last_date<'2026-01-01').sum(),"alldelisted",g.delisted.sum(),"cb",tr.on_coinbase_us.sum())
for y in range(2017,2027):
    a=p[p.date.dt.year==y].groupby("symbol").size()
    print(y,len(a),end=" | ")
print()
# gaps
dd=p.groupby("symbol").date.agg(["min","max","count"]);dd["span"]=(dd["max"]-dd["min"]).dt.days+1
print("symbols with internal gaps",(dd.span>dd["count"]).sum(),"missing days",(dd.span-dd["count"]).sum())
print(p[p.symbol=="BTCUSDT"].date.min(), p[(p.symbol=="BTCUSDT")&p.date.isin(pd.to_datetime(["2020-03-12","2022-11-09","2024-12-31","2025-06-15"]))][["date","close"]].to_string())
g.reset_index().to_csv(R+"/symbols.csv",index=False)
