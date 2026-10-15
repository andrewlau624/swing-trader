"""Study DRIP-PAY (N 927 -> 930): dividend pay-date reinvestment pressure, 2021-2026. Pre-reg research/drafts/round1_prose.md. Run once.
  PYTHONPATH=. .venv/bin/python -m research.sim.drip_pay"""
import numpy as np, pandas as pd
from research.sim import shar_surv as ss
from sharadar import prices as sh_prices, table
OUT = ss.ROOT / "data/research/program/drip_pay_out.txt"
COST = 5e-4; ZBAR = 3.06; PMIN = 5.0; ADVMIN = 5e6
L = []
def P(s=""): print(s, flush=True); L.append(s)

lo, hi = pd.Timestamp("2020-11-01"), pd.Timestamp("2026-10-05")
bars = ss.load_bars(lo, hi); bars["volume"] = bars.volume.astype(float)
g = bars.groupby("ticker", sort=False)
bars["adv20"] = g.apply(lambda x: (x.close * x.volume).rolling(20).mean().shift(1), include_groups=False).reset_index(level=0, drop=True) if False else (bars.close * bars.volume).groupby(bars.ticker).transform(lambda s: s.rolling(20).mean().shift(1))
bars["cprev"] = g.close.shift(1); bars["cc"] = bars.close / bars.cprev - 1; bars["oc"] = bars.close / bars.open - 1; bars["co"] = bars.open / bars.cprev - 1
spy = sh_prices(["SPY"], str(lo.date()), str(hi.date()), adjust="split", source="funds"); spy = spy[spy.ticker == "SPY"].assign(date=pd.to_datetime(spy.date)).set_index("date").sort_index()
spy = spy.assign(cc=spy.close / spy.close.shift(1) - 1, oc=spy.close / spy.open - 1, co=spy.open / spy.close.shift(1) - 1)
sess = spy.index.to_numpy()
mc = table("DAILY"); mc = mc[["ticker", "date", "marketcap"]]; mc["date"] = pd.to_datetime(mc.date); mc = mc[mc.date >= lo]
M = ss.load_master(); sec = M[M.table == "SEP"].drop_duplicates("ticker").set_index("ticker").sector
B = bars.set_index(["ticker", "date"]).sort_index()
P(f"bars {len(bars):,} rows, {bars.ticker.nunique():,} tickers; sessions {len(sess)} ({pd.Timestamp(sess[0]).date()}..{pd.Timestamp(sess[-1]).date()})")

dv = pd.read_parquet(ss.ROOT / "data/research/events/alpaca_cash_divs.parquet")
dv = dv[dv.payable_date.notna() & (dv.rate > 0) & (~dv.special.astype(bool)) & (~dv.foreign.astype(bool))].copy()
dv["pay"] = pd.to_datetime(dv.payable_date); dv["ex"] = pd.to_datetime(dv.ex_date)
dv = dv[(dv.pay >= pd.Timestamp("2021-01-04")) & (dv.pay <= pd.Timestamp("2026-09-30"))]
si = np.searchsorted(sess, dv.pay.to_numpy()); dv = dv[si < len(sess)].assign(si=si[si < len(sess)]); dv["D"] = sess[dv.si.to_numpy()]
dv = dv[dv.si >= 6]; dv = dv.drop_duplicates(["symbol", "D"])
exset = set(zip(dv.symbol, dv.ex)); dv = dv[[(s, d) not in exset for s, d in zip(dv.symbol, dv.D)]]
P(f"alpaca cash dividends with pay date 2021-01..2026-09: {len(dv):,} (symbols {dv.symbol.nunique():,}); same-day-ex dropped")

def features(df, shift):
    """row features for pay date shifted by `shift` sessions (0 = real, -5/+5 = placebo)."""
    s = df.si.to_numpy() + shift; ok = (s >= 1) & (s < len(sess)); s = np.where(ok, s, 1)
    D = sess[s]; Dm = sess[s - 1]
    k = pd.MultiIndex.from_arrays([df.symbol.to_numpy(), D]); km = pd.MultiIndex.from_arrays([df.symbol.to_numpy(), Dm])
    r = B.reindex(k); rm = B.reindex(km)
    out = pd.DataFrame({"symbol": df.symbol.to_numpy(), "D": D, "rate": df.rate.to_numpy(),
                        "cc": r.cc.to_numpy() - spy.cc.reindex(D).to_numpy(), "oc": r.oc.to_numpy() - spy.oc.reindex(D).to_numpy(), "co": r.co.to_numpy() - spy.co.reindex(D).to_numpy(),
                        "pu": rm.closeunadj.to_numpy(), "adv": rm.adv20.to_numpy(), "cl": rm.close.to_numpy()})
    out = out[ok & np.isfinite(out.cc) & (out.pu >= PMIN) & (out.adv >= ADVMIN)]
    m = mc.set_index(["ticker", "date"]).marketcap.reindex(pd.MultiIndex.from_arrays([out.symbol.to_numpy(), sess[np.searchsorted(sess, out.D.to_numpy()) - 1]])).to_numpy()
    out["press"] = (out.rate / out.cl) * m / out.adv
    out["mon"] = pd.DatetimeIndex(out.D).to_period("M"); out["sector"] = sec.reindex(out.symbol).to_numpy()
    out["top"] = out.groupby("mon").press.transform(lambda x: x >= x.quantile(2 / 3)) & out.press.notna()
    return out

def daily(ev, col, mask=None):
    e = ev if mask is None else ev[mask]; return e.groupby("D")[col].mean() - 2 * COST

def tstat(s): return s.mean() / s.std(ddof=1) * np.sqrt(len(s))

real = features(dv, 0); plm, plp = features(dv, -5), features(dv, +5)
P(f"qualifying events (price >= $5, ADV >= $5M): {len(real):,} on {real.D.nunique()} sessions ({len(real)/real.D.nunique():.1f}/day); top-tercile {real.top.sum():,}; "
  f"press median {real.press.median():.3f} (top {real[real.top].press.median():.3f}) days of volume; sectors top: {real.sector.value_counts().head(5).to_dict()}")
P("pressure tercile means (cc abnormal, gross bp): " + " ".join(f"T{i+1}:{real[real.groupby('mon').press.transform(lambda x: pd.qcut(x.rank(method='first'), 3, labels=False)) == i].cc.mean()*1e4:+.1f}" for i in range(3)))
P(f"P2 night piece close(D-1)->open(D): {real[real.top].co.mean()*1e4:+.1f}bp gross; P2 intraday open->close {real[real.top].oc.mean()*1e4:+.1f}bp gross")
P()
ARMS = {"P1 all cc": ("cc", None), "P2 top-tercile cc": ("cc", "top"), "P3 top-tercile oc": ("oc", "top")}
res = {}
for name, (col, mk) in ARMS.items():
    msk = lambda e: None if mk is None else e[mk].to_numpy()
    d = daily(real, col, msk(real)); mid = d.index[len(d) // 2]
    h = (d[d.index < mid].mean(), d[d.index >= mid].mean()); ex5 = d.drop(d.nlargest(5).index).mean(); d2 = d - 2 * COST
    pm, pp = daily(plm, col, msk(plm)), daily(plp, col, msk(plp))
    nonru = daily(real, col, (~real.sector.isin(["Real Estate", "Utilities"])).to_numpy() & (np.ones(len(real), bool) if mk is None else real[mk].to_numpy()))
    ok = d.mean() >= 1e-3 and tstat(d) >= ZBAR and min(h) > 0 and d.median() > 0 and ex5 > 0 and d2.mean() > 0 and (d.mean() - pm.mean() >= 8e-4) and (d.mean() - pp.mean() >= 8e-4) and abs(pm.mean()) < d.mean() / 2 and abs(pp.mean()) < d.mean() / 2 and nonru.mean() > 0
    res[name] = (ok, d.mean())
    P(f"{name}: days {len(d)} | net {d.mean()*1e4:+6.1f}bp/day t {tstat(d):+5.2f} median {d.median()*1e4:+6.1f} halves {h[0]*1e4:+6.1f}/{h[1]*1e4:+6.1f} ex-top5 {ex5*1e4:+6.1f} 2xcost {d2.mean()*1e4:+6.1f} "
      f"| placebo D-5 {pm.mean()*1e4:+6.1f} (t {tstat(pm):+4.2f}) D+5 {pp.mean()*1e4:+6.1f} (t {tstat(pp):+4.2f}) | ex-REIT/util {nonru.mean()*1e4:+6.1f} | hit {(d>0).mean()*100:.0f}% => {'PASS' if ok else 'FAIL'}")
if res["P1 all cc"][0] and not res["P2 top-tercile cc"][1] > res["P1 all cc"][1]: P("P1 passes but P2 is not larger than P1: mechanism unsupported -> FAIL")
P("\nby year (P2 net bp/day): " + " ".join(f"{y}:{v*1e4:+.1f}" for y, v in daily(real, 'cc', real.top.to_numpy()).groupby(lambda d: d.year).mean().items()))
OUT.write_text("\n".join(L))
