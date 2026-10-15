"""Study FUND-STATE (N 901): night-leg picks split by the loser's trailing-earnings state (Sharadar DAILY pe).
Pre-reg: research/drafts/round1_prose.md "Study FUND-STATE". Harness = winsig_l.py (nx daily-bar proxy, delisted-complete).
Primary: A = pe > 0 (profitable, trailing EPS>0) at the PRIOR session, B = pe <= 0 (loss-making). Gated paired A-B.
Judge 1999-2015 (window never used to look at this variable); 2016-26 reported as confirm. Run once.
  PYTHONPATH=. .venv/bin/python -m research.sim.fundstate"""
import numpy as np, pandas as pd
from research.sim import shar_surv as ss, nx
N_PROG = 901
OUT = ss.ROOT / "data/research/program/fundstate_out.txt"
rng = np.random.default_rng(900)
L = []
def P(s=""): print(s); L.append(s)

d = pd.read_parquet(ss.STORES / "daily.parquet", columns=["ticker", "date", "pe", "marketcap"])
d["date"] = pd.to_datetime(d["date"]); d = d.sort_values(["ticker", "date"])
d["pe_prev"] = d.groupby("ticker")["pe"].shift(1); d["mc_prev"] = d.groupby("ticker")["marketcap"].shift(1)
d = d.set_index(["ticker", "date"])[["pe_prev", "mc_prev"]]

def picks(lo, hi):
    bars = ss.load_bars(lo - pd.Timedelta(days=90), hi + pd.Timedelta(days=10))
    pn = nx.build_panel(bars)
    tr = nx.collect_trades(pn, ss.load_master(), ss.load_actions(), "primary", lo, hi)["trades"].copy()
    k = pd.MultiIndex.from_arrays([tr.ticker, tr.date])
    tr["pe"] = d["pe_prev"].reindex(k).to_numpy(); tr["mc"] = d["mc_prev"].reindex(k).to_numpy()
    return tr

def tstat(x): x = np.asarray(x); return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 5 else np.nan

def split(tr, lab, a, b, cost=0.0):
    t = tr.copy(); t["r"] = t.ret - 2 * cost
    A, B = t[a], t[b]
    da, db = A.groupby("date").r.mean(), B.groupby("date").r.mean()
    dd = (da - db).dropna(); t_ = tstat(dd)
    mid = dd.index[len(dd) // 2]; h = (dd[dd.index < mid].mean(), dd[dd.index >= mid].mean())
    t["dm"] = t.r - t.groupby("date").r.transform("mean")
    md = A.r.median() - B.r.median()
    # ex-top-5: drop the 5 largest |night diffs|
    ex5 = dd.drop(dd.abs().nlargest(5).index).mean()
    # placebo: shuffle the label within nights
    lab_arr = np.where(a, 1, np.where(b, 0, -1)); t["lab"] = lab_arr; sub = t[t.lab >= 0]
    obs = dd.mean(); cnt = 0; B_ = 300
    g = [(x.r.to_numpy(), x.lab.to_numpy()) for _, x in sub.groupby("date") if 0 < x.lab.sum() < len(x)]
    for _ in range(B_):
        s = []
        for r, l in g:
            p = rng.permutation(l); s.append(r[p == 1].mean() - r[p == 0].mean())
        cnt += np.mean(s) < obs
    pct = cnt / B_ * 100
    P(f"{lab:34} A n {len(A):5} {A.r.mean()*1e4:+6.1f}bp med {A.r.median()*1e4:+5.1f} hit {(A.r>0).mean()*100:4.1f}% | B n {len(B):5} {B.r.mean()*1e4:+6.1f}bp med {B.r.median()*1e4:+5.1f} hit {(B.r>0).mean()*100:4.1f}%"
      f" | paired {obs*1e4:+6.1f} (t {t_:+5.2f}, nights {len(dd)}) halves {h[0]*1e4:+6.1f}/{h[1]*1e4:+6.1f} med-diff {md*1e4:+5.1f} ex-top5 {ex5*1e4:+6.1f} placebo {pct:.0f}th")
    return obs, t_, h, md, ex5, pct

def report(tr, name):
    P(f"== {name}: picks {len(tr)}, nights {tr.date.nunique()}, mean overnight {tr.ret.mean()*1e4:+.1f}bp; pe coverage {tr.pe.notna().mean()*100:.1f}%")
    tr = tr[tr.pe.notna()]
    A, B = tr.pe > 0, tr.pe <= 0
    P(f"   share loss-making {B.mean()*100:.1f}%")
    res = split(tr, "PRIMARY pe>0 vs pe<=0 (0bp)", A, B)
    for c in (0.0005, 0.00075, 0.0015):   # flat per side; tier 5bp is 0.0005, 3x tier-ish 0.0015
        split(tr, f"  same, cost {c*1e4:.1f}bp/side", A, B, c)
    mc = tr.mc.rank(pct=True)
    P("   diagnostics (not gated):")
    split(tr, "  marketcap top vs bottom tercile", mc > 2/3, mc <= 1/3)
    split(tr, "  pe 0-15 (value) vs pe>25", (tr.pe > 0) & (tr.pe <= 15), tr.pe > 25)
    return res, tr

lo, hi = pd.Timestamp("1999-01-04"), pd.Timestamp("2015-12-31")
tj = picks(lo, hi)
res, tj = report(tj, "JUDGE 1999-2015")
obs, t_, h, md, ex5, pct = res
bar = [("paired A-B >= +20bp", obs >= 2e-3), ("night-clustered t >= 2.5", t_ >= 2.5),
       ("halves both > 0", h[0] > 0 and h[1] > 0), ("raw median diff > 0", md > 0), ("ex-top-5 nights > 0", ex5 > 0), ("placebo >= 95th", pct >= 95)]
from scipy.stats import norm
sr = t_ / np.sqrt(tj.date.nunique())  # per-night SR-like; DSR via Bonferroni-style expected max of N trials
emax = norm.ppf(1 - 1 / N_PROG)  # crude: z needed under N independent trials
P(f"   DSR proxy: t {t_:.2f} vs expected-max z under N={N_PROG} nulls ~{emax:.2f} -> {'exceeds' if t_ > emax else 'DOES NOT exceed'}")
for n_, ok in bar: P(f"   [{'ok' if ok else 'NO'}] {n_}")
P(f"VERDICT: {'PASS' if all(ok for _, ok in bar) else 'FAIL'}"); P("")
tc = picks(pd.Timestamp("2016-01-04"), pd.Timestamp("2026-09-18"))
report(tc, "CONFIRM/REPORT 2016-26 (touched window; new conditioner)")
OUT.write_text("\n".join(L))
