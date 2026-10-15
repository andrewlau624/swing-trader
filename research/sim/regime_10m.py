"""Study REGIME-10M (N 919 -> 922): Faber 10-month SMA SPY gate on the daily-bar book (0.5 IBS + 0.5 night), judge 1999-2015, report 2016-26.
Pre-reg research/drafts/round1_prose.md. Harness = SHAR-CRASH functions. Run once.
  PYTHONPATH=. .venv/bin/python -m research.sim.regime_10m"""
import numpy as np, pandas as pd
from research.sim import shar_crash as sc, nx
from sharadar import prices as sh_prices
OUT = sc.ROOT / "data/research/program/regime_10m_out.txt"
COST = 5e-4
L = []
def P(s=""): print(s, flush=True); L.append(s)

def etf_frames(lo, hi):
    df = sh_prices(sc.EQ18, lo, hi, adjust="split", source="funds"); df = df[df.ticker.isin(sc.EQ18)].assign(date=pd.to_datetime(df.date))
    return [df.pivot(index="date", columns="ticker", values=c).sort_index() for c in ("open", "high", "low", "close")]

def ibs_net(O, H, L_, C):
    # ibs_daily returns EW gross return per signal day; cost = 2 sides on the deployed leg
    return sc.ibs_daily(O, H, L_, C) - 2 * COST

def night_net(lo, hi, sep, sfp, master, act):
    parts = [t[(t.date >= lo - sc.PAD) & (t.date <= hi + sc.PAD)] for t in (sep, sfp)]
    bars = pd.concat(parts, ignore_index=True).sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    pn = nx.build_panel(bars); tr = nx.collect_trades(pn, master, act, "primary", lo, hi)["trades"]
    return tr.groupby("date").apply(lambda g: float((g.per * (g.ret - 2 * COST)).sum())).sort_index()

def spy_gate():
    s = sh_prices(["SPY"], "1998-01-01", "2026-10-09", adjust="split", source="funds"); s = s[s.ticker == "SPY"].assign(date=pd.to_datetime(s.date)).set_index("date").close.sort_index()
    me = s.resample("ME").last(); sma = me.rolling(10).mean()
    on = (me > sma)                                   # state known at month-end m-1
    on.index = on.index.to_period("M") + 1            # applies to month m
    return on, me, sma

def stats(r):
    r = r.fillna(0.0); eq = (1 + r).cumprod(); yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1; sh = r.mean() / r.std() * np.sqrt(252); mdd = (eq / eq.cummax() - 1).min()
    return cagr, sh, mdd

def mdd_window(r, lo, hi):
    x = r[(r.index >= lo) & (r.index <= hi)].fillna(0.0); eq = (1 + x).cumprod(); return float((eq / eq.cummax() - 1).min())

def tstat(s): return s.mean() / s.std(ddof=1) * np.sqrt(len(s)) if len(s) > 2 else np.nan

on_m, me, sma = spy_gate()
P(f"SPY gate: months {on_m.index.min()}..{on_m.index.max()}, OFF share {(~on_m.dropna().astype(bool)).mean()*100:.0f}%")
Pp = nx.Paths(); master = nx.load_master(Pp); act = nx.read_table(Pp, "ACTIONS"); sep = nx.read_table(Pp, "SEP"); sfp = nx.read_table(Pp, "SFP")
WIN = {"JUDGE 1999-2015": ("1999-01-04", "2015-12-31", [("2000-02", "2000-01-01", "2002-12-31"), ("2007-09", "2007-10-01", "2009-12-31"), ("2011", "2011-01-01", "2011-12-31"), ("2015-16", "2015-08-01", "2016-02-29")]),
       "REPORT 2016-26 (touched)": ("2016-01-04", "2026-09-18", [("2018Q4", "2018-10-01", "2018-12-31"), ("2020", "2020-02-01", "2020-04-30"), ("2022", "2022-01-01", "2022-12-31")])}
for name, (lo, hi, wins) in WIN.items():
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi); gate = name.startswith("JUDGE")
    O, H, L_, C = etf_frames((lo - pd.Timedelta(days=420)).strftime("%Y-%m-%d"), (hi + pd.Timedelta(days=10)).strftime("%Y-%m-%d"))
    idx = C.index[(C.index >= lo) & (C.index <= hi)]
    ibs = ibs_net(O, H, L_, C).reindex(idx).fillna(0.0); ngt = night_net(lo, hi, sep, sfp, master, act).reindex(idx).fillna(0.0)
    on = on_m.reindex(idx.to_period("M")).fillna(True).astype(bool).to_numpy()
    base = 0.5 * ibs + 0.5 * ngt
    arms = {"G1 book OFF": 0.5 * ibs * on + 0.5 * ngt * on, "G2 night OFF": 0.5 * ibs + 0.5 * ngt * on, "G3 IBS OFF": 0.5 * ibs * on + 0.5 * ngt}
    bc, bs, bm = stats(base)
    P(f"== {name}: sessions {len(idx)}, OFF sessions {(~on).sum()} ({(~on).mean()*100:.0f}%) | base CAGR {bc*100:5.1f}% Sharpe {bs:4.2f} maxDD {bm*100:6.1f}% | "
      + " ".join(f"{w}:{mdd_window(base, a, b)*100:6.1f}%" for w, a, b in wins))
    off = base[~on]; mid = idx[len(idx) // 2]
    offh = (off[off.index < mid], off[off.index >= mid]); onr = base[on]
    P(f"  base on OFF sessions: mean {off.mean()*1e4:+6.1f}bp/day (t {tstat(off):+5.2f}) halves {offh[0].mean()*1e4:+6.1f} (t {tstat(offh[0]):+4.2f}) / {offh[1].mean()*1e4:+6.1f} (t {tstat(offh[1]):+4.2f}); ON sessions {onr.mean()*1e4:+6.1f}bp/day; "
      f"night leg OFF {ngt[~on].mean()*1e4:+6.1f} vs ON {ngt[on].mean()*1e4:+6.1f}; IBS leg OFF {ibs[~on].mean()*1e4:+6.1f} vs ON {ibs[on].mean()*1e4:+6.1f}")
    for an, a in arms.items():
        ac, as_, am = stats(a); dd = a - base
        wm = {w: (mdd_window(a, x, y), mdd_window(base, x, y)) for w, x, y in wins}
        P(f"  {an:12s} CAGR {ac*100:5.1f}% (base {bc*100:5.1f}) Sharpe {as_:4.2f} maxDD {am*100:6.1f}% | " + " ".join(f"{w}:{v[0]*100:6.1f}% ({(v[0]-v[1])*100:+4.1f}pp)" for w, v in wm.items())
          + f" | diff/day {dd.mean()*1e4:+5.2f}bp t {tstat(dd):+5.2f} halves {dd[dd.index < mid].mean()*1e4:+5.2f}/{dd[dd.index >= mid].mean()*1e4:+5.2f}")
        if gate:
            ok_a = ac >= bc - 0.005; ok_b = all(wm[w][0] - wm[w][1] >= 0.05 for w in ("2000-02", "2007-09")); ok_c = as_ > bs
            offa = (base - a)[~on]   # what the arm removed on OFF days (positive = removed gains)
            ok_d = all(tstat(x) <= 0 for x in ((base - a)[~on & (idx < mid)], (base - a)[~on & (idx >= mid)]))
            P(f"     gates: CAGR {ok_a} DD {ok_b} Sharpe {ok_c} OFF<=0 both halves {ok_d} => {'PASS' if ok_a and ok_b and ok_c and ok_d else 'FAIL'}")
    P()
OUT.write_text("\n".join(L))
