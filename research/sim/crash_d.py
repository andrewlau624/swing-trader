"""Study CRASH-D: trend-gated 1x inverse sleeve vs T-bills (pre-reg round1_prose.md, N 1028).
Run: PYTHONPATH=. .venv/bin/python research/sim/crash_d.py   (needs data/research/crash_a/{dsi,mcti}.parquet)"""
from __future__ import annotations
import pathlib, numpy as np, pandas as pd
from sharadar import prices
ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/crash_a"; OUT = ROOT / "data/research/program/crash_d_out.txt"
COST = 3e-4; L = []
def P(s=""): print(s); L.append(s)
# ---- CRSP VW 1926-1997
d = pd.read_parquet(D / "dsi.parquet").dropna(subset=["vwretd"]); d["date"] = pd.to_datetime(d["date"]); d = d.set_index("date")
d = d[d.index < "1998-01-01"]; rc = d["vwretd"].astype(float)
m = pd.read_parquet(D / "mcti.parquet").dropna(subset=["t30ret"]); m["caldt"] = pd.to_datetime(m["caldt"])
mr = m.set_index("caldt")["t30ret"].astype(float); mr.index = mr.index.to_period("M")
per = rc.index.to_period("M"); n = pd.Series(1, index=rc.index).groupby(per).transform("sum")
cc = pd.Series((1 + mr.reindex(per).values) ** (1 / n.values) - 1, index=rc.index).fillna(0.0) - 0.001 / 280
dtc = pd.Series(rc.index, index=rc.index).diff().dt.days.fillna(1).values
sync = -rc - 0.009 * dtc / 365.25 + cc
# ---- SPY 1998+
df = prices(["SPY", "SH"], "1998-01-01", "2026-10-10", adjust="total", source="funds"); df["date"] = pd.to_datetime(df["date"])
px = df.pivot(index="date", columns="ticker", values="closeadj").sort_index()
spy = px["SPY"].dropna(); rs = spy.pct_change(); rs = rs[rs.index >= "1998-01-02"]
t = pd.read_csv(ROOT / "data/research/fred/DTB3.csv", parse_dates=["observation_date"]).set_index("observation_date")["DTB3"]
t = pd.to_numeric(t, errors="coerce").reindex(rs.index, method="ffill").ffill()
cs = (t / 100 - 0.001) / 252
syns = -rs - 0.009 / 252 + cs
sh = px["SH"].reindex(rs.index).pct_change(); invs = sh.where(sh.notna(), syns)
r = pd.concat([rc, rs]); cash = pd.concat([cc, cs]); inv = pd.concat([sync, invs]); idx = r.index
P(f"Spliced series {idx[0].date()}..{idx[-1].date()} n={len(idx)}; SH actual from {sh.dropna().index[0].date()}")
px_ = (1 + r).cumprod()
# ---- frozen CRASH-A signals
me = px_.groupby([idx.year, idx.month]).tail(1).index; mm = px_[me]
cm = (1 + cash).cumprod()[me]
r1 = mm.lt(mm.rolling(10).mean()).where(mm.rolling(10).mean().notna())
r3 = ((mm / mm.shift(12) - 1) < (cm / cm.shift(12) - 1)).where(mm.shift(12).notna())
mon = lambda s: s.fillna(False).astype(bool).reindex(idx).ffill().fillna(False).astype(bool)
sma = px_.rolling(200).mean(); cur = False; st = []
for tt in idx:
    s = sma[tt]
    if np.isfinite(s):
        if not cur and px_[tt] < .99 * s: cur = True
        elif cur and px_[tt] > 1.01 * s: cur = False
    st.append(cur)
RULES = {"R1 Faber10m": mon(r1), "R2 200d+-1%": pd.Series(st, index=idx), "R3 TSMOM12m": mon(r3)}
def sleeve(state):
    h = state.shift(2).fillna(False).astype(bool)
    x = pd.Series(np.where(h, inv, cash), index=idx)
    sw = h.astype(int).diff().abs().fillna(0)
    return x - sw.shift(-1).fillna(0) * COST, h          # 1x notional per switch
def comp(x, a, b): return (1 + x[a:b]).prod() - 1
EP = (("1929-09..1932-07", "1929-09-01", "1932-07-31", 1), ("1937-03..1938-03", "1937-03-01", "1938-03-31", 1),
      ("1973-01..1974-12", "1973-01-01", "1974-12-31", 0), ("2000-03..2002-10", "2000-03-24", "2002-10-09", 0),
      ("2007-10..2009-03", "2007-10-09", "2009-03-09", 1), ("2020-02..2020-03", "2020-02-19", "2020-03-23", 0),
      ("2022-01..2022-10", "2022-01-03", "2022-10-12", 0))
CRASH = set(range(1929, 1933)) | {1937, 1938, 1973, 1974, 2000, 2001, 2002, 2008, 2020, 2022}
res = {k: sleeve(s) for k, s in RULES.items()}
P("\n== Per episode: sleeve excess over T-bills, % of sleeve capital (gate arms *) ==")
P(f"{'episode':<18}" + "".join(f"{k:>14}" for k in RULES) + "   index")
ep = {}
for lab, a, b, g in EP:
    row = f"{lab + ('*' if g else ''):<18}"
    for k in RULES:
        x = res[k][0]; e = 100 * (comp(x, a, b) - comp(cash, a, b)); ep[(k, lab)] = e; row += f"{e:>13.1f}%"
    P(row + f"   {100*comp(r,a,b):+.1f}%")
yr = {}
for k in RULES:
    x = res[k][0]; ye = (1 + x).groupby(idx.year).prod() - (1 + cash).groupby(idx.year).prod(); yr[k] = 100 * ye
P("\n== Non-crash calendar years: mean sleeve excess (%/yr of sleeve capital), cost = -mean ==")
nc_all = {}
for k in RULES:
    y = yr[k]; ncy = y[[i for i in y.index if i not in CRASH]]
    a98 = ncy[ncy.index >= 1998]; a26 = ncy[(ncy.index < 1998)]
    nc_all[k] = ncy.mean()
    P(f"{k}: 1926-2026 mean {ncy.mean():+.2f} (n {len(ncy)}, median {ncy.median():+.2f}, worst {ncy.min():+.1f} in {ncy.idxmin()}); "
      f"1926-1997 {a26.mean():+.2f}; 1998-2026 {a98.mean():+.2f} (n {len(a98)}, worst {a98.min():+.1f} in {a98.idxmin()})")
P("\n== Whipsaws (risk-off spells; whipsaw = sleeve excess < 0 over the spell) ==")
for k in RULES:
    x, h = res[k]; g = (h != h.shift()).cumsum(); sp = []
    for _, seg in h[h].groupby(g[h]):
        a, b = seg.index[0], seg.index[-1]; sp.append(100 * (comp(x, a, b) - comp(cash, a, b)))
    sp = np.array(sp); P(f"{k}: spells {len(sp)}, whipsaws {(sp<0).sum()}, mean spell {sp.mean():+.1f}%, median {np.median(sp):+.1f}%, best {sp.max():+.0f}%, worst {sp.min():+.0f}%, off share of days {h.mean():.0%}")
    P(f"      1998+: " + (lambda s2: f"spells {len(s2)}, whipsaws {(s2<0).sum()}")(np.array([100 * (comp(x, g2.index[0], g2.index[-1]) - comp(cash, g2.index[0], g2.index[-1])) for _, g2 in h[h & (idx >= '1998-01-01')].groupby(g[h & (idx >= '1998-01-01')])])))
P("\n== Dollars: 50%-of-account sleeve, $ effect vs leaving that half in T-bills ==")
for k in RULES:
    e1929 = ep[(k, "1929-09..1932-07")] / 100; avg = nc_all[k] / 100
    P(f"{k}: 1929-32 " + " / ".join(f"${0.5*c*e1929:+,.0f}" for c in (2300, 10000, 25000)) + f"  | avg non-crash yr " + " / ".join(f"${0.5*c*avg:+,.0f}" for c in (2300, 10000, 25000)))
P("   (columns: $2.3k / $10k / $25k account)")
P("\n== Gate: avg non-crash-yr excess >= -2.0%/yr (1926-2026) AND gain >= +30% in 1929-32, 1937-38, 2007-09 ==")
for k in RULES:
    arm_a = nc_all[k] >= -2.0; g = [ep[(k, lab)] for lab, _, _, f in EP if f]; arm_b = all(v >= 30 for v in g)
    P(f"{k}: (a) cost {-nc_all[k]:.2f}%/yr -> {'PASS' if arm_a else 'FAIL'}; (b) gains {[round(float(v),1) for v in g]} -> {'PASS' if arm_b else 'FAIL'}; VERDICT {'PASS' if arm_a and arm_b else 'KILL'}")
P("\n== All years (crash incl.): mean sleeve excess %/yr, 1926-2026 / 1998-2026 (net value of the insurance; not a gate) ==")
for k in RULES: P(f"{k}: {yr[k].mean():+.2f} / {yr[k][yr[k].index>=1998].mean():+.2f}")
P("\n== Payoff per unit of cost (1929-32 + 1937-38 + 2007-09 gain sum / non-crash cost per yr) ==")
for k in RULES:
    g = sum(ep[(k, lab)] for lab, _, _, f in EP if f); P(f"{k}: sum gain {g:.0f}%  cost {-nc_all[k]:.2f}%/yr  ratio {g/max(-nc_all[k],1e-9):.0f}")
OUT.write_text("\n".join(L) + "\n")
