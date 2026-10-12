import requests, re, os, time, json, sys
from concurrent.futures import ThreadPoolExecutor
S3="https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
OUT="/Users/andrewlau/Documents/Code/Projects/swing-trader/data/research/crypto_spot/raw"
sess=requests.Session()
def get(url,params=None,tries=5):
    for i in range(tries):
        try:
            r=sess.get(url,params=params,timeout=60)
            if r.status_code==200: return r
            if r.status_code==404: return None
        except Exception: pass
        time.sleep(1+i*2)
    raise RuntimeError(url)
def list_prefix(prefix,delim=None):
    keys=[];pre=[];marker=""
    while True:
        p={"prefix":prefix,"marker":marker}
        if delim:p["delimiter"]=delim
        x=get(S3,p).text
        keys+=re.findall(r"<Key>([^<]+)</Key>",x)
        pre+=re.findall(r"<Prefix>([^<]+)</Prefix>",x[x.find("</Prefix>"):] if False else x)
        if "<IsTruncated>true" in x:
            m=re.search(r"<NextMarker>([^<]+)",x)
            marker=m.group(1) if m else (keys[-1] if keys else pre[-1])
        else: break
    return keys,pre
_,pre=list_prefix("data/spot/monthly/klines/","/")
syms=sorted({p.split("/")[-2] for p in pre if p.count("/")==5})
print(len(syms),"symbols total")
usdt=[s for s in syms if s.endswith("USDT")]
btc=[s for s in syms if s.endswith("BTC")]
print(len(usdt),"USDT",len(btc),"BTC")
json.dump({"all":syms,"usdt":usdt,"btc":btc},open("syms.json","w"))
def lst(s):
    k,_=list_prefix(f"data/spot/monthly/klines/{s}/1d/")
    return [x for x in k if x.endswith(".zip")]
with ThreadPoolExecutor(16) as ex: files=dict(zip(usdt,ex.map(lst,usdt)))
allk=[k for v in files.values() for k in v]
print(len(allk),"zips")
def dl(k):
    s=k.split("/")[-3]; d=f"{OUT}/{s}"; os.makedirs(d,exist_ok=True)
    f=f"{d}/{os.path.basename(k)}"
    if os.path.exists(f): return
    r=get("https://data.binance.vision/"+k)
    if r: open(f,"wb").write(r.content)
with ThreadPoolExecutor(16) as ex: list(ex.map(dl,allk))
print("done")
