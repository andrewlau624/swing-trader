"""Noise leg (daybook PROD QQQ+SMH) 2016..2026-10-07: m1 cache + data/research/recent/qm (SIP, Alpaca, 2026-05-01..10-07). Reuses noise_recent.trades_for/stats. No tuning.
Run: PYTHONPATH=. .venv/bin/python research/sim/recent_noise.py"""
import sys; sys.path.insert(0,"/Users/andrewlau/Documents/Code/Projects/swing-trader")
import numpy as np, pandas as pd, glob
from swingtrader.daybook import shadow as sh
from research.sim.noise_recent import trades_for, stats, W
R="data/research/recent/qm"
def sess(sym):
    S=sh._sessions_cache(sym,14,None)
    df=pd.read_parquet(f"{R}/{sym}_recent.parquet")
    t=pd.to_datetime(df["timestamp"],utc=True).dt.tz_convert("America/New_York")
    df=df.assign(date=t.dt.tz_localize(None).dt.normalize(),m=t.dt.hour*60+t.dt.minute-570); df=df[(df.m>=0)&(df.m<390)]
    for d,g in df.groupby("date"):
        c=np.full(390,np.nan); v=np.zeros(390); c[g.m.values]=g.close.values; v[g.m.values]=g.volume.values
        S[d]={"close":pd.Series(c).ffill().values,"volume":v,"open":float(g.sort_values("m").open.iloc[0])}
    return dict(sorted(S.items()))
S={s:sess(s) for s in W}; print({s:(min(v),max(v),len(v)) for s,v in S.items()})
ad=pd.DatetimeIndex(sorted(set(S["QQQ"])&set(S["SMH"])))
T={lag:pd.concat([trades_for(S[s],s,W[s],lag) for s in W]) for lag in (0,30)}
pers={"2016-2025 avg":("2016-01-01","2025-12-31"),"2021-2025":("2021-01-01","2025-12-31"),"2026-01..05":("2026-01-01","2026-05-31"),"2026-06..10-07":("2026-06-01","2026-10-07"),
      "2026 YTD":("2026-01-01","2026-10-07"),"2026-06..09-21":("2026-06-01","2026-09-21"),"live 09-23..10-07":("2026-09-23","2026-10-07")}
for lag in (0,30):
    print("LAG",lag)
    for k,(a,b) in pers.items():
        d=T[lag][(T[lag].date>=a)&(T[lag].date<=b)]; dd=ad[(ad>=a)&(ad<=b)]
        for c in (0.5,1.0,2.0):
            s=stats(d,dd,c)
            if s: print(f"  {k:20s} c={c}/fill n={s['n']:4d} mean={s['mean']:6.2f} med={s['med']:6.1f} t={s['t']:5.2f} hit={s['hit']:3.0f}% sharpe={s['sharpe']:5.2f}")
    # by month 2026
    d=T[lag][T[lag].date>="2026-01-01"].copy(); d["net"]=d.gross-1.0
    print("  monthly 2026 (c=0.5/fill):",d.groupby(d.date.dt.month).net.agg(["size","mean"]).round(1).T.to_dict())
x=T[30][T[30].date>="2026-09-23"]; print(x.assign(date=x.date.dt.date).round(1).to_string())
x=T[0][T[0].date>="2026-09-23"]; print("nolag live-window"); print(x.assign(date=x.date.dt.date).round(1).to_string())
