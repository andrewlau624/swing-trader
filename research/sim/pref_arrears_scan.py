"""Branch G descriptive scan: preferred/ETD dividend catch-ups (>=3x regular) and suspensions. Touched, descriptive."""
import pathlib, numpy as np, pandas as pd, pyarrow.dataset as ds
S = pathlib.Path.home()/"data"/"sharadar"
t = ds.dataset(S/"tickers.parquet").to_table().to_pandas()
t = t[((t.table=="SEP")&t.category.isin(["Domestic Preferred Stock","ADR Preferred Stock","Canadian Preferred Stock"]))|((t.table=="SFP")&t.category.isin(["ETD","CEF Preferred"]))]
t = t.drop_duplicates("ticker"); meta=t.set_index("ticker")
a = ds.dataset(S/"actions.parquet").to_table(columns=["date","action","ticker","value","name"]).to_pandas()
a = a[(a.action=="dividend")&a.ticker.isin(meta.index)].copy(); a["date"]=pd.to_datetime(a.date)
a = a.groupby(["ticker","date"],as_index=False).agg(div=("value","sum"),name=("name","first")).sort_values(["ticker","date"])
rows=[]; susp=[]
for tk,g in a.groupby("ticker"):
    d=g["div"].values; dt=g.date.values
    for i in range(4,len(g)):
        reg=np.median(d[i-4:i])
        if reg>0 and d[i]>=3*reg: rows.append((tk,pd.Timestamp(dt[i]),d[i],reg,d[i]/reg))
    # suspensions: gap >= 2.2x median gap of prior 4 intervals, regular payer
    ds_=np.diff(dt).astype("timedelta64[D]").astype(int)
    for i in range(4,len(ds_)):
        m=np.median(ds_[i-4:i])
        if 20<=m<=130 and ds_[i]>=2.2*m: susp.append((tk,pd.Timestamp(dt[i]),pd.Timestamp(dt[i+1]),ds_[i],m,d[i-4:i+1].mean()))
c=pd.DataFrame(rows,columns=["tk","ex","div","reg","mult"])
# raw price guard
b=ds.dataset(S/"stocks.parquet").to_table(columns=["ticker","date","close","closeunadj","open","volume"],filter=ds.field("ticker").isin(list(c.tk.unique()))).to_pandas()
f=ds.dataset(S/"funds.parquet").to_table(columns=["ticker","date","close","closeunadj","open","volume"],filter=ds.field("ticker").isin(list(c.tk.unique()))).to_pandas()
b=pd.concat([b,f]);b["date"]=pd.to_datetime(b.date);b=b.sort_values(["ticker","date"]);b["open"]=b.open*b.closeunadj/b.close
b["pc"]=b.groupby("ticker").closeunadj.shift(1)
m=c.merge(b[["ticker","date","open","closeunadj","pc"]],left_on=["tk","ex"],right_on=["ticker","date"],how="left")
m["y"]=m["div"]/m.pc; m["drop_open"]=(m.pc-m.open); m["ratio"]=m.drop_open/m["div"]; m["ret_co"]=(m.open+m["div"])/m.pc-1
m["name"]=m.tk.map(meta.name); m["cat"]=m.tk.map(meta.category)
m.to_csv("/tmp/x/catch.csv",index=False)
print("candidates",len(m),"with price",m.pc.notna().sum())
mm=m[(m.y>0.0)&(m.y<0.6)&m.pc.between(3,80)]
print(mm.groupby(mm.ex.dt.year).size().to_string())
print(mm.sort_values("y",ascending=False).head(40)[["tk","name","ex","div","reg","mult","pc","y","ratio","ret_co"]].to_string())
s=pd.DataFrame(susp,columns=["tk","last","next","gap","medgap","avgdiv"]);s["name"]=s.tk.map(meta.name);s.to_csv("/tmp/x/susp.csv",index=False)
print("susp gaps",len(s),s.tk.nunique()); print(s.groupby(s["last"].dt.year).size().to_string())
