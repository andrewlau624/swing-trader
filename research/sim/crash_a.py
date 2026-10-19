"""Study CRASH-A: trend-rule regime exit + inverse-ETF defensive book on SPY. Pre-reg: round1_prose.md (N 1024).
Run: PYTHONPATH=. .venv/bin/python research/sim/crash_a.py
"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd
from sharadar import prices

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "research" / "program" / "crash_a_out.txt"
COST = 3e-4
EPIS = (("2000-03..2002-10", "2000-03-24", "2002-10-09"), ("2007-10..2009-03", "2007-10-09", "2009-03-09"),
        ("2020-02..2020-03", "2020-02-19", "2020-03-23"), ("2022-01..2022-10", "2022-01-03", "2022-10-12"))
CRASH_YEARS = {2000, 2001, 2002, 2008, 2020, 2022}
lines = []
def P(s=""):
    print(s); lines.append(s)

df = prices(["SPY", "SH", "IEF"], "1998-01-01", "2026-10-10", adjust="total", source="funds")
df["date"] = pd.to_datetime(df["date"])
px = df.pivot(index="date", columns="ticker", values="closeadj").sort_index()
spy = px["SPY"].dropna(); idx = spy.index
r = spy.pct_change().fillna(0.0)
c = pd.read_csv(ROOT / "data/research/fred/DTB3.csv", parse_dates=["observation_date"]).set_index("observation_date")["DTB3"]
c = pd.to_numeric(c, errors="coerce").reindex(idx, method="ffill").ffill()
cash = (c / 100 - 0.001) / 252
syn = -r - 0.009 / 252 + cash
sh = px["SH"].reindex(idx).pct_change()
inv = sh.where(sh.notna(), syn)
ov = sh.dropna().index
P(f"SH actual from {ov[0].date()}; synthetic before. Overlap check ({len(ov)} days): daily corr(syn,SH)={np.corrcoef(syn[ov], sh[ov])[0,1]:.4f}, "
  f"cum SH {(1+sh[ov]).prod()-1:+.3f} vs synthetic {(1+syn[ov]).prod()-1:+.3f}")
ief = px["IEF"].reindex(idx).pct_change()

# ---- signals (state True = risk-off, known at close t)
me = spy.groupby([spy.index.year, spy.index.month]).tail(1).index
m = spy[me]
r1m = (m < m.rolling(10).mean())
cm = (1 + cash).cumprod()[me]
r3m = (m / m.shift(12) - 1) < (cm / cm.shift(12) - 1)
def monthly_state(s):
    s = s.where(s.notna(), False).astype(bool)
    return s.reindex(idx).ffill().fillna(False).astype(bool)
R1 = monthly_state(r1m.where(m.rolling(10).mean().notna()))
R3 = monthly_state(r3m.where(m.shift(12).notna()))
sma = spy.rolling(200).mean(); st = []; cur = False
for t in idx:
    s = sma[t]
    if np.isfinite(s):
        if not cur and spy[t] < 0.99 * s: cur = True
        elif cur and spy[t] > 1.01 * s: cur = False
    st.append(cur)
R2 = pd.Series(st, index=idx)
RULES = {"R1 Faber10m": R1, "R2 200d+-1%": R2, "R3 TSMOM12m": R3}

def run(state, d):
    held = state.shift(2).fillna(False)  # signal close t, trade close t+1, earn from t+2
    off = (cash * 0.5 + inv * 0.5) if d == "D1" else cash
    ret = pd.Series(np.where(held, off, r), index=idx)
    sw = held.astype(int).diff().abs().fillna(0)
    ret = ret - sw.shift(-1).fillna(0) * COST * (1.5 if d == "D1" else 1.0)  # cost on the trade day (close d-1)
    return ret, held

def stats(x, lab):
    x = x.dropna(); eq = (1 + x).cumprod(); yrs = len(x) / 252
    dd = (eq / eq.cummax() - 1).min(); ex = x - cash.reindex(x.index)
    return f"{lab:<28} CAGR {eq.iloc[-1]**(1/yrs)-1:+7.2%} maxDD {dd:+7.2%} Sharpe {ex.mean()/ex.std()*np.sqrt(252):5.2f}"
def win(x, a, b): return (1 + x[a:b]).prod() - 1
def cagr_years(x, mask):
    y = x[mask]; return (1 + y).prod() ** (252 / len(y)) - 1

bh = r
sixty = pd.Series(np.nan, index=idx); s0 = ief.first_valid_index()
mo = idx.to_series().groupby([idx.year, idx.month]).transform("first") == idx.to_series()
w = 0.6; v = []  # monthly rebalance 60/40
wt = 0.6; eq = 1.0; pr = []
for t in idx:
    if t < s0: pr.append(np.nan); continue
    if mo[t]: wt = 0.6
    rt = wt * r[t] + (1 - wt) * ief[t]; pr.append(rt)
    wt = wt * (1 + r[t]) / (1 + rt)
sixty = pd.Series(pr, index=idx)

P(f"CRASH-A  data {idx[0].date()}..{idx[-1].date()}  (signal close t, trade close t+1, cost {COST*1e4:.0f}bp/notional)")
P("\n== Full period 1998-2026 ==")
P(stats(bh, "SPY buy&hold"))
P(stats(sixty, "60/40 (2002-08+) [alone]"))
P(stats(bh[s0:], "SPY (2002-08+) [compare]"))
res = {}
for d in ("D1", "D2"):
    for k, s in RULES.items():
        x, h = run(s, d); res[(k, d)] = (x, h)
        P(stats(x, f"{k} {d}"))
P("\n== Per crash episode (SPY peak->trough), account return vs SPY ==")
gate_a = {}
for lab, a, b in EPIS:
    P(f"{lab}: SPY {win(bh,a,b):+.1%}")
    for d in ("D1", "D2"):
        for k in RULES:
            x, h = res[(k, d)]; e = win(x, a, b)
            P(f"   {k} {d}: {e:+.1%}  excess {100*(e-win(bh,a,b)):+.1f}pp  (off at peak? {bool(h[a:b].iloc[0])}; off share {h[a:b].mean():.0%})")
            if d == "D1": gate_a.setdefault(k, []).append(100 * (e - win(bh, a, b)))
nc = pd.Series(~idx.year.isin(CRASH_YEARS), index=idx)
P("\n== Non-crash years (all but 2000-02, 2008, 2020, 2022): CAGR cost vs SPY (pp/yr) ==")
P(f"SPY non-crash CAGR {cagr_years(bh, nc):+.2%}")
gate_b = {}
for d in ("D1", "D2"):
    for k in RULES:
        x, h = res[(k, d)]; cst = 100 * (cagr_years(bh, nc) - cagr_years(x, nc)); gate_b[(k, d)] = cst
        ann = [(1 + bh[str(y)]).prod() - (1 + x[str(y)]).prod() for y in sorted(set(idx.year)) if y not in CRASH_YEARS]
        P(f"   {k} {d}: rule CAGR {cagr_years(x, nc):+.2%}  cost {cst:+.2f}pp/yr   worst year {100*max(ann):+.1f}pp  mean yearly gap {100*np.mean(ann):+.2f}pp")
P("\n== Whipsaws / flips ==")
for k, s in RULES.items():
    h = s.shift(2).fillna(False); ch = h.astype(int).diff().fillna(0)
    ent = list(h.index[ch == 1]); ext = list(h.index[ch == -1])
    lose = 0
    for e in ent:  # risk-off spell lost if SPY rose over spell
        nx = [t for t in ext if t > e]; t2 = nx[0] if nx else idx[-1]
        if spy[t2] > spy[e]: lose += 1
    P(f"   {k}: {len(ent)} risk-off spells in {len(idx)/252:.1f}y; {lose} where SPY ROSE during the spell (whipsaw); mean spell {np.mean([ (min([t for t in ext if t>e] or [idx[-1]])-e).days for e in ent]):.0f} cal days")
P("\n== 2020 speed: first held risk-off date after the 2020-02-19 peak, SPY drawdown at the flip, and drawdown at trough ==")
pk = spy["2020-02-19"]
for k, s in RULES.items():
    h = s.shift(2).fillna(False)["2020-02-19":"2020-06-30"]
    on = h[h]; 
    if len(on):
        t = on.index[0]; P(f"   {k}: held off from {t.date()}  SPY dd at flip {spy[t]/pk-1:+.1%} (trough {spy['2020-03-23']/pk-1:+.1%}); re-risk {h[h.index>t][~h[h.index>t]].index[:1].astype(str).tolist()}")
    else: P(f"   {k}: never flipped in 2020 window")
P("\n== Dollars: each episode, account value from $2.3k/$10k/$25k (D1, 100% of account in rule) ==")
for lab, a, b in EPIS:
    row = f"{lab} SPY {win(bh,a,b):+.0%}: "
    for k in RULES:
        e = win(res[(k, 'D1')][0], a, b); row += f"{k.split()[0]} {e:+.0%} (${2300*(1+e):,.0f}/${10000*(1+e):,.0f}/${25000*(1+e):,.0f})  "
    P(row)
med = {k: np.median(v) for k, v in gate_a.items()}
P("\nStylised -35% SPY crash: B&H $2.3k->$1,495; rule = -35% + median episode excess (pp): " +
  "; ".join(f"{k.split()[0]} {med[k]:+.1f}pp -> ${2300*(0.65+med[k]/100):,.0f} (10k ${10000*(0.65+med[k]/100):,.0f}, 25k ${25000*(0.65+med[k]/100):,.0f})" for k in RULES))
P("\n== Gate (D1) ==")
for k in RULES:
    a = gate_a[k]; ok_a = all(v >= 15 for v in a); ok_b = gate_b[(k, 'D1')] <= 3
    P(f"   {k}: (a) episode excess pp {[round(v,1) for v in a]} -> {'PASS' if ok_a else 'FAIL'}; (b) bleed {gate_b[(k,'D1')]:+.2f}pp/yr -> {'PASS' if ok_b else 'FAIL'}; VERDICT {'PASS' if ok_a and ok_b else 'KILL'}")
OUT.write_text("\n".join(lines) + "\n")
