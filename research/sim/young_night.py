"""Study YOUNG-NIGHT (N 922 -> 924): listing-age tilt on the night leg (peeked lead). Pre-reg research/drafts/round1_prose.md. Harness = TREND-NIGHT. Run once.
  PYTHONPATH=. .venv/bin/python -m research.sim.young_night"""
import numpy as np, pandas as pd
from research.sim import shar_surv as ss, nx
OUT = ss.ROOT / "data/research/program/young_night_out.txt"
COST = 5e-4; YOUNG_DAYS = 365; CRASH = {2000, 2001, 2002, 2008, 2009, 2020}; ZBAR = 3.06; NPLAC = 200
L = []
def P(s=""): print(s, flush=True); L.append(s)
M = ss.load_master(); MS = M[M.table == "SEP"].drop_duplicates("ticker").set_index("ticker")
FPD = pd.to_datetime(MS.firstpricedate)

def picks(lo, hi):
    bars = ss.load_bars(lo - pd.Timedelta(days=60), hi + pd.Timedelta(days=10))
    pn = nx.build_panel(bars)
    tr = nx.collect_trades(pn, M, ss.load_actions(), "primary", lo, hi)["trades"].copy()
    tr["age"] = (tr.date - FPD.reindex(tr.ticker).to_numpy()).dt.days
    tr["young"] = tr.age < YOUNG_DAYS
    tr["r"] = tr.ret - 2 * COST; tr["r2"] = tr.ret - 4 * COST
    tr["cat"] = MS.category.reindex(tr.ticker).fillna("NA").to_numpy()
    return tr

def nightly(tr, col, w):
    ww = w.loc[tr.index]; return (tr[col] * ww).groupby(tr.date).sum() / ww.groupby(tr.date).sum()

def weights(tr, y, arm):
    if arm == "Y1": return pd.Series(np.where(y, 2.0, 1.0), index=tr.index)
    has = y.groupby(tr.date).transform("any")
    return pd.Series(np.where(has, y.astype(float), 1.0), index=tr.index)

def tstat(s): return s.mean() / s.std(ddof=1) * np.sqrt(len(s))

def evaluate(tr, y, arm, col="r"):
    base = nightly(tr, col, pd.Series(1.0, index=tr.index)); a = nightly(tr, col, weights(tr, y, arm)).reindex(base.index).fillna(0.0)
    return base, a, a - base

def judge(name, tr, arm):
    base, a, dd = evaluate(tr, tr.young, arm); t = tstat(dd); mid = dd.index[len(dd) // 2]
    h = (dd[dd.index < mid].mean(), dd[dd.index >= mid].mean()); ex5 = dd.drop(dd.abs().nlargest(5).index).mean(); med = dd[dd != 0].median()
    _, _, dd2 = evaluate(tr, tr.young, arm, "r2"); exc = dd[~dd.index.year.isin(CRASH)].mean(); lev = base.mean() * a.std() / base.std()
    rng = np.random.default_rng(0); share = tr.young.mean(); plac = []
    for _ in range(NPLAC):
        fake = pd.Series(rng.random(len(tr)) < share, index=tr.index); plac.append(evaluate(tr, fake, arm)[2].mean())
    p99 = np.quantile(plac, 0.99); sh = lambda s: s.mean() / s.std() * np.sqrt(252)
    ok = dd.mean() >= 1e-3 and t >= ZBAR and min(h) > 0 and med > 0 and ex5 > 0 and dd2.mean() > 0 and exc > 0 and a.mean() > lev and dd.mean() > p99
    P(f"  {arm} {name}: arm {a.mean()*1e4:+6.1f}bp/night (std {a.std()*1e4:4.0f}, Sharpe {sh(a):4.2f}) vs base {base.mean()*1e4:+6.1f} (std {base.std()*1e4:4.0f}, Sharpe {sh(base):4.2f}) | "
      f"diff {dd.mean()*1e4:+6.2f} t {t:+5.2f} halves {h[0]*1e4:+6.2f}/{h[1]*1e4:+6.2f} median(!=0) {med*1e4:+6.2f} ex-top5 {ex5*1e4:+6.2f} 2xcost {dd2.mean()*1e4:+6.2f} ex-crash {exc*1e4:+6.2f} "
      f"| levered-base {lev*1e4:+6.1f} | placebo 99th {p99*1e4:+5.2f} (mean {np.mean(plac)*1e4:+5.2f}) => {'PASS' if ok else 'FAIL'}")
    return ok

res = {}
for name, lo, hi in [("1999-2015", "1999-01-04", "2015-12-31"), ("2016-26", "2016-01-04", "2026-09-18")]:
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi); tr = picks(lo, hi); tr = tr[tr.date >= lo]
    P(f"== {name}: picks {len(tr)}, nights {tr.date.nunique()}, young {tr.young.sum()} ({tr.young.mean()*100:.1f}%), nights with a young pick {tr.groupby('date').young.any().mean()*100:.0f}%")
    b = pd.cut(tr.age / 365.25, [-1, 0.5, 1, 2, 5, 100], labels=["<0.5y", "0.5-1y", "1-2y", "2-5y", "5y+"])
    g = tr.groupby(b, observed=True).r.agg(["count", "mean", "median"]); P("  age buckets (net bp): " + "  ".join(f"{k}: n {int(v['count'])} mean {v['mean']*1e4:+.0f} med {v['median']*1e4:+.0f}" for k, v in g.iterrows()))
    yb = tr.groupby([tr.date.dt.year, "young"]).r.mean().unstack(); P("  young-old by year (bp): " + " ".join(f"{y}:{(yb.loc[y, True]-yb.loc[y, False])*1e4:+.0f}" for y in yb.index if True in yb.columns and pd.notna(yb.loc[y, True])))
    for lab, sub in (("young", tr[tr.young]), ("old", tr[~tr.young])):
        P(f"  {lab}: ADV median ${sub.adv.median()/1e6:.1f}M, price median ${sub.cu.median():.1f}, vol20 {sub.vol20.median():.2f}, day_ret {sub.day_ret.median()*100:.1f}%, kinds {sub.kind.value_counts().to_dict()}, cat top {sub.cat.value_counts().head(4).to_dict()}")
    for arm in ("Y1", "Y2"): res[(arm, name)] = judge(name, tr, arm)
    P()
for arm in ("Y1", "Y2"): P(f"{arm}: {'PASS' if res[(arm, '1999-2015')] and res[(arm, '2016-26')] else 'FAIL'} (needs both windows)")
OUT.write_text("\n".join(L))
