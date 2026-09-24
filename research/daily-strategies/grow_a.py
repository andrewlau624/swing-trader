from grow import *
nz = noise_series(0.5, 1.5); nz4 = noise_series(0.5, 3.5)
def summ(df, lab):
    r = (df.E.diff() - df.dep.diff()) / df.E.shift()        # deposit-neutral daily return
    r = r.dropna(); yrs = len(r) / 252
    tw = (1 + r).prod() ** (1 / yrs) - 1; sh = r.mean() / r.std() * np.sqrt(252)
    dd = ((1 + r).cumprod() / (1 + r).cumprod().cummax() - 1).min()
    print(f"{lab:52s} end ${df.E.iloc[-1]:>10,.0f}  deposited ${df.dep.iloc[-1]:>8,.0f}  "
          f"TWR {tw*100:5.1f}%  Sharpe {sh:4.2f}  maxDD {dd*100:5.1f}%   | SPY same deposits ${df.spy.iloc[-1]:>9,.0f}")
print("Historical replay 2021-02 -> 2026-09, $3k start + $1k every 21 sessions\n")
summ(replay(whole=False, nz=nz), "ideal: fractional shares, intraday 1.5x")
summ(replay(whole=True, resplit=False, nz=nz), "LIVE NOW: whole shares, skip unbuyable, 1.5x")
summ(replay(whole=True, resplit=True, nz=nz), "+ night re-split among buyable names")
summ(replay(whole=True, resplit=True, ibs_frac=True, nz=nz), "+ IBS via cheap twins (~fractional)")
summ(replay(whole=True, resplit=True, ibs_frac=True, nz=None, intraday_on=False), "same, intraday leg OFF")
summ(replay(whole=True, resplit=True, ibs_frac=True, nz=nz4), "same, intraday 3.5x (needs a 4x account)")
summ(replay(whole=True, resplit=True, ibs_frac=True, nz=noise_series(1.5,1.5), night_cost=17.5), "CONSERVATIVE: +10bp night, 1.5bp intraday")
