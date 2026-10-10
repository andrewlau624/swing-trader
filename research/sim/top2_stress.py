"""TOP2-STRESS (registered research/drafts/round1_prose.md 2026-10-10; descriptive): nightly (TOP2 - base) diff, both eras.
Needs data/research/robust/night_live_trades.parquet (built by research.sim.top2_size). Pandas/numpy only.
  PYTHONPATH=. .venv/bin/python -m research.sim.top2_stress
base = equal-weight mean net return (5bp/side) of all nx live-rule picks that night; TOP2 = the 2 deepest day_ret picks; nights with picks only
(same convention as catmom_depth). Seeds fixed."""
import pathlib
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/robust"; OUT = ROOT / "data/research/program/top2_stress_out.txt"
COST = 5e-4
ERAS = {"1999-2015": ("1999-01-04", "2015-12-31"), "2016-26": ("2016-01-04", "2026-09-18")}
L = []
def P(s=""): print(s, flush=True); L.append(s)
def tt(x): return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
def f(x): return f"{x*1e4:+7.2f}"

tr = pd.read_parquet(D / "night_live_trades.parquet"); tr["r"] = tr.ret - 2 * COST
rk = tr.groupby("date").day_ret.rank(method="first")
base = tr.groupby("date").r.mean(); top = tr[rk <= 2].groupby("date").r.mean().reindex(base.index)
diff = top - base
rng = np.random.default_rng(20261010)
CRASH = [(2000, 2002), (2008, 2009), (2020, 2020)]
for era, (lo, hi) in ERAS.items():
    d = diff[(diff.index >= lo) & (diff.index <= hi)]; b = base.reindex(d.index); t2 = top.reindex(d.index)
    P(f"== {era}: {len(d)} pick-nights; base {f(b.mean())}bp, TOP2 {f(t2.mean())}bp, diff {f(d.mean())}bp, night-clustered t {tt(d):+.2f}")
    x = d.to_numpy(); n = len(x); B = 20; nb = int(np.ceil(n / B)); means = np.empty(2000)
    for i in range(2000):
        st = rng.integers(0, n - B + 1, nb); means[i] = np.concatenate([x[s:s + B] for s in st])[:n].mean()
    P(f"  20-night block bootstrap (2000 draws): diff mean {f(means.mean())}, 95% CI [{f(np.percentile(means,2.5))}, {f(np.percentile(means,97.5))}], share draws<=0 {100*(means<=0).mean():.1f}%")
    yr = d.index.year; ex = d[~pd.Series(yr, index=d.index).apply(lambda y: any(a <= y <= c for a, c in CRASH))]
    P(f"  ex-crash years (2000-02, 2008-09, 2020): n {len(ex)}, diff {f(ex.mean())}bp, t {tt(ex):+.2f}" if len(ex) > 2 else "  ex-crash: no nights in era")
    e10 = d.drop(d.abs().nlargest(10).index); P(f"  ex-top-10 |diff| nights: n {len(e10)}, diff {f(e10.mean())}bp, t {tt(e10):+.2f}; the 10 largest contribute {f(d.mean()-e10.mean()*len(e10)/len(d))}bp of the mean")
    P("  per year: year  nights   base    top2    diff   t")
    for y, g in d.groupby(d.index.year):
        P(f"    {y}  {len(g):5d} {f(b[g.index].mean())} {f(t2[g.index].mean())} {f(g.mean())} {tt(g):+5.2f}")
    P()
OUT.write_text("\n".join(L))
