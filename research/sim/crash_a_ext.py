"""CRASH-A extension: same frozen rules on CRSP VW index 1926-1998 (pre-reg: round1_prose.md, 'CRASH-A extension').
Run: PYTHONPATH=. .venv/bin/python research/sim/crash_a_ext.py   (needs data/research/crash_a/{dsi,mcti}.parquet)"""
import pathlib, numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/crash_a"; OUT = ROOT / "data/research/program/crash_a_ext_out.txt"
COST = 3e-4; L = []
def P(s=""): print(s); L.append(s)
d = pd.read_parquet(D / "dsi.parquet").dropna(subset=["vwretd"]); d["date"] = pd.to_datetime(d["date"]); d = d.set_index("date")
idx = d.index; r = d["vwretd"].astype(float)
px = (1 + r).cumprod()
m = pd.read_parquet(D / "mcti.parquet").dropna(subset=["t30ret"]); m["caldt"] = pd.to_datetime(m["caldt"])
mr = m.set_index("caldt")["t30ret"].astype(float); mr.index = mr.index.to_period("M")
per = idx.to_period("M"); n = pd.Series(1, index=idx).groupby(per).transform("sum")
cash = pd.Series((1 + mr.reindex(per).values) ** (1 / n.values) - 1, index=idx).fillna(0.0) - 0.001 / 280
dt = pd.Series(idx, index=idx).diff().dt.days.fillna(1).values
syn = -r - 0.009 * dt / 365.25 + cash          # -1x daily rebalanced, synthetic
# signals
me = px.groupby([idx.year, idx.month]).tail(1).index; mm = px[me]
cm = (1 + cash).cumprod()[me]
r1 = (m_ := mm).lt(mm.rolling(10).mean()).where(mm.rolling(10).mean().notna())
r3 = ((mm / mm.shift(12) - 1) < (cm / cm.shift(12) - 1)).where(mm.shift(12).notna())
mon = lambda s: s.fillna(False).astype(bool).reindex(idx).ffill().fillna(False).astype(bool)
R1, R3 = mon(r1), mon(r3)
sma = px.rolling(200).mean(); cur = False; st = []
for t in idx:
    s = sma[t]
    if np.isfinite(s):
        if not cur and px[t] < .99 * s: cur = True
        elif cur and px[t] > 1.01 * s: cur = False
    st.append(cur)
R2 = pd.Series(st, index=idx)
RULES = {"R1 Faber10m": R1, "R2 200d+-1%": R2, "R3 TSMOM12m": R3}
def run(s, dd):
    h = s.shift(2).fillna(False).astype(bool)
    off = 0.5 * cash + 0.5 * syn if dd == "D1" else cash
    x = pd.Series(np.where(h, off, r), index=idx)
    sw = h.astype(int).diff().abs().fillna(0)
    return x - sw.shift(-1).fillna(0) * COST * (1.5 if dd == "D1" else 1.0), h
win = lambda x, a, b: (1 + x[a:b]).prod() - 1
yrs = lambda x: (x.index[-1] - x.index[0]).days / 365.25
def stats(x, lab):
    eq = (1 + x).cumprod(); y = yrs(x)
    return f"{lab:<24} CAGR {eq.iloc[-1]**(1/y)-1:+7.2%} maxDD {(eq/eq.cummax()-1).min():+7.2%}"
EP = (("W1 1929-09..1932-07", "1929-09-01", "1932-07-31"), ("W2 1937-03..1938-03", "1937-03-01", "1938-03-31"),
      ("W3 1973-01..1974-12", "1973-01-01", "1974-12-31"))
P(f"CRSP VW total return {idx[0].date()}..{idx[-1].date()}  days incl. pre-1952 Saturdays; 1-day-lag, 3bp cost")
res = {(k, dd): run(s, dd) for k, s in RULES.items() for dd in ("D1", "D2")}
P("\n== Full 1926-1950 ==")
a, b = "1926-01-01", "1950-12-31"
P(stats(r[a:b], "VW buy&hold"))
for (k, dd), (x, h) in res.items(): P(stats(x[a:b], f"{k} {dd}"))
P("\n== Windows: account return vs buy&hold, D1 / D2 (excess pp) ==")
gate = {}
for lab, a, b in EP:
    bh = win(r, a, b); P(f"{lab}: VW {bh:+.1%}")
    for k in RULES:
        e1 = win(res[(k, 'D1')][0], a, b); e2 = win(res[(k, 'D2')][0], a, b)
        P(f"   {k}: D1 {e1:+.1%} ({100*(e1-bh):+.1f}pp)  D2 {e2:+.1%} ({100*(e2-bh):+.1f}pp)  off share {res[(k,'D1')][1][a:b].mean():.0%}")
        gate.setdefault(k, {})[lab[:2]] = 100 * (e1 - bh)
# data-driven W1 peak/trough
a, b = "1929-09-01", "1932-07-31"; pk = px[a:b].idxmax(); tr = px[pk:b].idxmin()
P(f"\nW1 data peak {pk.date()} trough {tr.date()}: VW {px[tr]/px[pk]-1:+.1%}")
P("\n== -1x leg path decay, 1929-09 peak -> 1932 trough ==")
dec = (1 + syn[pk:tr].iloc[1:]).prod() - 1; stat = -(px[tr] / px[pk] - 1) + (1 + cash[pk:tr].iloc[1:]).prod() - 1
P(f"   daily-rebalanced -1x (synth, fee, cash): {dec:+.1%}; static short from peak (-index return + cash): {stat:+.1%}; index {px[tr]/px[pk]-1:+.1%}")
pk2 = px["1932-06-01":"1932-12-31"]; P(f"   (-1x leg during the 1930-31 rallies is what the daily leg bleeds; static short suffers the same marks)")
P("\n== 1930-31 bear rallies: flips / whipsaws ==")
for k, s in RULES.items():
    h = s.shift(2).fillna(False).astype(bool)["1929-09-01":"1932-07-31"]; ch = h.astype(int).diff().fillna(0)
    ent = list(h.index[ch == 1]); ext = list(h.index[ch == -1]); lose = 0; rows = []
    for e in ent:
        nx = [t for t in ext if t > e]; t2 = nx[0] if nx else h.index[-1]; ret = px[t2] / px[e] - 1; lose += ret > 0
        rows.append(f"{e.date()}->{t2.date()} {ret:+.0%}")
    P(f"   {k}: first off {ent[0].date() if ent else None}, VW dd at entry {px[ent[0]]/px[pk]-1 if ent else 0:+.1%}; {len(ent)} risk-off spells, {lose} whipsaws (VW rose); " + "; ".join(rows))
rally = px["1930-01-01":"1930-04-30"]; P(f"   spring-1930 rally: VW low {rally.idxmin().date()} -> high {rally.idxmax().date()} {rally.max()/rally.min()-1:+.1%}")
P("\n== Dollars (D1/D2) for W1 and W3 ==")
for lab, a, b in (EP[0], EP[2]):
    bh = win(r, a, b)
    for k in RULES:
        row = f"{lab} {k}: "
        for dd in ("D1", "D2"):
            e = win(res[(k, dd)][0], a, b); row += f"{dd} {e:+.0%} (${2300*(1+e):,.0f}/${10000*(1+e):,.0f}/${25000*(1+e):,.0f})  "
        P(row)
    P(f"   VW buy&hold {bh:+.0%}: ${2300*(1+bh):,.0f}/${10000*(1+bh):,.0f}/${25000*(1+bh):,.0f}")
P("\n== Bleed in non-crash years 1926-1950 (excl 1929-32, 1937-38) ==")
mask = pd.Series(~idx.year.isin([1929, 1930, 1931, 1932, 1937, 1938]) & (idx.year <= 1950) & (idx.year >= 1926), index=idx)
cg = lambda x: (1 + x[mask]).prod() ** (365.25 / ((x[mask].index[-1] - x[mask].index[0]).days * mask.mean() if False else (mask.sum() / 300 * 365.25))) - 1
for k in RULES:
    for dd in ("D1", "D2"):
        P(f"   {k} {dd}: cost vs VW {100*(cg(r)-cg(res[(k,dd)][0])):+.2f}pp/yr (VW {cg(r):+.2%})")
P("\n== Gate (D1 >= +15pp in W1 and W3) ==")
for k in RULES:
    g = gate[k]; P(f"   {k}: W1 {g['W1']:+.1f} W2 {g['W2']:+.1f} W3 {g['W3']:+.1f} -> {'PASS' if g['W1']>=15 and g['W3']>=15 else 'KILL'}")
OUT.write_text("\n".join(L) + "\n")
