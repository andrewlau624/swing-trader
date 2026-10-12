import pandas as pd,requests,datetime as dt
R="/Users/andrewlau/Documents/Code/Projects/swing-trader/data/research/crypto_spot"
p=pd.read_parquet(R+"/panel.parquet")
p.loc[p.base=="SYRUP","is_leveraged"]=False
p.to_parquet(R+"/panel.parquet",index=False)
s=p.drop_duplicates("symbol")[["symbol","base","first_date","last_date","delisted","is_stable_fiat","is_leveraged","on_coinbase_us"]]
s.to_csv(R+"/symbols.csv",index=False)
print(s.is_leveraged.sum(),s.is_stable_fiat.sum())
t0=int(dt.datetime(2019,1,1).timestamp());t1=int(dt.datetime(2026,9,30).timestamp())
j=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?period1={t0}&period2={t1}&interval=1d",headers={"User-Agent":"Mozilla/5.0"}).json()["chart"]["result"][0]
y=pd.Series(j["indicators"]["quote"][0]["close"],index=pd.to_datetime(j["timestamp"],unit="s").normalize())
b=p[p.symbol=="BTCUSDT"].set_index("date").close
d=pd.concat([b,y],axis=1,keys=["bn","yh"]).dropna()
d["rel"]=(d.bn/d.yh-1).abs()
print(len(d),"median rel diff",d.rel.median(),"p95",d.rel.quantile(.95),"share<0.5%",(d.rel<.005).mean())
print(d.loc[pd.to_datetime(["2019-06-03","2021-05-03","2023-03-15","2025-01-10","2026-03-02","2026-08-12"])])
