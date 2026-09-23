import pandas as pd, numpy as np
def ema(x,n): return x.ewm(span=n,adjust=False).mean()
def tmo(O,C,length=14,calc=5,smooth=3):
    data=sum(np.sign(C-O.shift(i)) for i in range(length))
    main=ema(ema(data,calc),smooth); sig=ema(main,smooth)
    ob=round(length*0.7)
    return main,sig,ob
def linreg_last(x,n=20):
    # value of linear regression line at last bar (ToS Inertia)
    idx=np.arange(n); w=(idx-idx.mean())/((idx-idx.mean())**2).sum()
    slope=x.rolling(n).apply(lambda v:(w*v).sum(),raw=True) if isinstance(x,pd.Series) else None
    return slope
def ttm(H,L,C,n=20,bbm=2.0,kcm=1.5):
    sma=C.rolling(n).mean(); sd=C.rolling(n).std(ddof=0)
    tr=pd.concat([H-L,(H-C.shift()).abs(),(L-C.shift()).abs()]).groupby(level=0).max() if isinstance(C,pd.Series) else np.maximum(H-L,np.maximum((H-C.shift()).abs(),(L-C.shift()).abs()))
    atr=tr.rolling(n).mean()
    sq=(sma+bbm*sd<sma+kcm*atr)&(sma-bbm*sd>sma-kcm*atr)
    delta=C-((H.rolling(n).max()+L.rolling(n).min())/2+sma)/2
    # linreg value at last point = mean + slope*(n-1)/2
    k=np.arange(n)-(n-1)/2; den=(k**2).sum()
    slope=sum(delta.shift(n-1-j)*k[j] for j in range(n))/den
    mom=delta.rolling(n).mean()+slope*(n-1)/2
    return sq,mom
