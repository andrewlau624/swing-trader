"""CRASH-D addendum: same frozen rules, signal and sleeve both on QQQ (pre-reg round1_prose.md 'CRASH-D addendum').
Run: PYTHONPATH=. .venv/bin/python research/sim/crash_d_qqq.py"""
import pathlib, warnings, numpy as np, pandas as pd
from sharadar import prices
warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[2]; OUT = ROOT / "data/research/program/crash_d_qqq_out.txt"
COST = 3e-4; L = []
def P(s=""): print(s); L.append(s)
df = prices(["QQQ", "PSQ"], "1999-01-01", "2026-10-10", adjust="total", source="funds"); df["date"] = pd.to_datetime(df["date"])
px = df.pivot(index="date", columns="ticker", values="closeadj").sort_index()
q = px["QQQ"].dropna(); idx = q.index; r = q.pct_change().fillna(0.0)
t = pd.read_csv(ROOT / "data/research/fred/DTB3.csv", parse_dates=["observation_date"]).set_index("observation_date")["DTB3"]
cash = (pd.to_numeric(t, errors="coerce").reindex(idx, method="ffill").ffill() / 100 - 0.001) / 252
syn = -r - 0.0095 / 252 + cash
psq = px["PSQ"].reindex(idx).pct_change(); inv = psq.where(psq.notna(), syn); ov = psq.dropna().index
P(f"QQQ {idx[0].date()}..{idx[-1].date()}; PSQ actual from {ov[0].date()}; overlap corr {np.corrcoef(syn[ov], psq[ov])[0,1]:.3f}, cum PSQ {(1+psq[ov]).prod()-1:+.3f} vs syn {(1+syn[ov]).prod()-1:+.3f}")
me = q.groupby([idx.year, idx.month]).tail(1).index; mm = q[me]; cm = (1 + cash).cumprod()[me]
r1 = mm.lt(mm.rolling(10).mean()).where(mm.rolling(10).mean().notna())
r3 = ((mm / mm.shift(12) - 1) < (cm / cm.shift(12) - 1)).where(mm.shift(12).notna())
mon = lambda s: s.astype(object).where(s.notna(), False).astype(bool).reindex(idx).ffill().astype(bool)
sma = q.rolling(200).mean(); cur = False; st = []
for tt in idx:
    s = sma[tt]
    if np.isfinite(s):
        if not cur and q[tt] < .99 * s: cur = True
        elif cur and q[tt] > 1.01 * s: cur = False
    st.append(cur)
RULES = {"R1 Faber10m": mon(r1), "R2 200d+-1%": pd.Series(st, index=idx), "R3 TSMOM12m": mon(r3)}
def sleeve(state):
    h = state.shift(2).fillna(False).astype(bool); x = pd.Series(np.where(h, inv, cash), index=idx)
    return x - h.astype(int).diff().abs().fillna(0).shift(-1).fillna(0) * COST, h
comp = lambda x, a, b: (1 + x[a:b]).prod() - 1
EP = (("2000-03-10..2002-10-09*", "2000-03-10", "2002-10-09"), ("2007-11..2009-03", "2007-10-31", "2009-03-09"),
      ("2020-02-19..03-23", "2020-02-19", "2020-03-23"), ("2021-11..2022-12", "2021-11-19", "2022-12-28"))
CRASH = {2000, 2001, 2002, 2008, 2020, 2022}; res = {k: sleeve(s) for k, s in RULES.items()}
P(f"\nQQQ buy&hold in 2000-03-10..2002-10-09: {100*comp(r,'2000-03-10','2002-10-09'):+.1f}%")
P(f"{'episode (sleeve excess vs T-bills, % of sleeve)':<48}" + "".join(f"{k:>14}" for k in RULES) + "   QQQ")
ep = {}
for lab, a, b in EP:
    row = f"{lab:<48}"
    for k in RULES:
        e = 100 * (comp(res[k][0], a, b) - comp(cash, a, b)); ep[(k, lab)] = e; row += f"{e:>13.1f}%"
    P(row + f"   {100*comp(r,a,b):+.1f}%")
P("\n== Non-crash years (1999-2026 minus crash set): mean sleeve excess %/yr ==")
nc = {}
for k in RULES:
    y = 100 * ((1 + res[k][0]).groupby(idx.year).prod() - (1 + cash).groupby(idx.year).prod())
    y = y[y.index >= 2000]  # 1999 is a partial/warm-up year (starts Mar, no signals)
    n_ = y[[i for i in y.index if i not in CRASH]]; nc[k] = n_.mean()
    P(f"{k}: mean {n_.mean():+.2f} (n {len(n_)}, median {n_.median():+.2f}, worst {n_.min():+.1f} in {n_.idxmin()}); all years 2000-2026 {y.mean():+.2f}")
    x, h = res[k]; g = (h != h.shift()).cumsum(); sp = np.array([100 * (comp(x, s.index[0], s.index[-1]) - comp(cash, s.index[0], s.index[-1])) for _, s in h[h].groupby(g[h])])
    P(f"      spells {len(sp)}, whipsaws {(sp<0).sum()}, off share {h.mean():.0%}")
P("\n== Gate: non-crash cost <= 2%/yr AND 2000-02 gain >= +30% ==")
for k in RULES:
    a = nc[k] >= -2.0; b = ep[(k, EP[0][0])] >= 30
    P(f"{k}: cost {-nc[k]:.2f}%/yr -> {'PASS' if a else 'FAIL'}; 2000-02 gain {ep[(k, EP[0][0])]:.1f}% -> {'PASS' if b else 'FAIL'}; VERDICT {'PASS' if a and b else 'KILL'}")
OUT.write_text("\n".join(L) + "\n")
