"""Study OVN-MOM (pre-reg research/drafts/round1_prose.md, 'Study OVN-MOM', N 938 -> 939).

Overnight-return momentum held overnight. Sharadar SEP: open/high/low/close/volume are SPLIT-adjusted,
closeunadj is raw; so open_{t+1}/close_t on the stored columns is split-invariant (raw ratio would give a
spurious -k:1 on split ex-dates). Raw close (>= $5) = closeunadj. $vol = stored close*volume (split-invariant).
Run: .venv/bin/python -m research.sim.ovn_mom
"""
from __future__ import annotations
import os, pathlib, numpy as np, pandas as pd, pyarrow.dataset as ds

D = os.path.expanduser("~/data/sharadar/")
OUT = pathlib.Path("data/research/program/ovn_mom_out.txt")
LOG = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)

# ---- universe master + load
tk = pd.read_parquet(D + "tickers.parquet", columns=["table", "ticker", "category"])
tk = tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")]
names = set(tk.ticker)
dset = ds.dataset(D + "stocks.parquet")
df = dset.to_table(columns=["ticker", "date", "open", "close", "volume", "closeunadj"],
                   filter=ds.field("ticker").isin(sorted(names))).to_pandas()
df["date"] = pd.to_datetime(df["date"])
P("rows", len(df), "tickers", df.ticker.nunique(), "dup(ticker,date)", int(df.duplicated(["ticker", "date"]).sum()))
df = df[(df.close > 0) & (df.open > 0)].drop_duplicates(["ticker", "date"])
dates = pd.DatetimeIndex(sorted(df.date.unique()))
cols = sorted(df.ticker.unique()); ci = {c: i for i, c in enumerate(cols)}
T, N = len(dates), len(cols)
di = dates.get_indexer(df.date); cj = df.ticker.map(ci).to_numpy()
def mat(v, dt=np.float32):
    m = np.full((T, N), np.nan, dt); m[di, cj] = v.to_numpy(dt); return m
O = mat(df.open); C = mat(df.close); RC = mat(df.closeunadj); DV = mat(df.close * df.volume, np.float64).astype(np.float32)
del df

# ---- action flags: night s-1 -> s is dropped when an action has ex-date at session s
act = pd.read_parquet(D + "actions.parquet", columns=["date", "action", "ticker", "value"])
act["date"] = pd.to_datetime(act["date"])
a = act[act.action.isin(["split", "dividend", "spinoff", "spinoffdividend", "adrratiosplit"]) & act.ticker.isin(ci)]
ai = dates.searchsorted(a.date.to_numpy()); ok = ai < T
AF = np.zeros((T, N), bool); AF[ai[ok], a.ticker[ok].map(ci).to_numpy()] = True

# ---- overnight returns R[s] = O[s]/C[s-1]-1 (night ending at s's open)
R = np.full((T, N), np.nan, np.float32); R[1:] = O[1:] / C[:-1] - 1
bigm = np.abs(R) > 0.5
nA = np.isfinite(R) & AF; nB = np.isfinite(R) & bigm & ~AF
Rv = R.copy(); Rv[AF | bigm] = np.nan                       # valid nights only

# ---- score: mean of last 252 valid nights ending with day t's open (R[t-251..t]); need >= 200
V = np.isfinite(Rv)
cs = np.cumsum(np.nan_to_num(Rv, nan=0.0).astype(np.float64), axis=0)
cn = np.cumsum(V, axis=0)
def lag(x, k):
    y = np.zeros_like(x); y[k:] = x[:-k]; return y
S = np.full((T, N), np.nan, np.float32)
n252 = cn - lag(cn, 252); s252 = cs - lag(cs, 252)
okS = (n252 >= 200) & (np.arange(T)[:, None] >= 251)
S[okS] = (s252[okS] / n252[okS]).astype(np.float32)
del cs, cn, n252, s252, okS

# ---- eligibility on day t: raw close_t >= 5; 20d median $vol through t-1 >= 20M (t-1: avoid same-day volume)
med = np.full((T, N), np.nan, np.float32)
for c0 in range(0, N, 1500):
    med[:, c0:c0 + 1500] = pd.DataFrame(DV[:, c0:c0 + 1500]).rolling(20, min_periods=15).median().to_numpy(np.float32)
medl = np.full((T, N), np.nan, np.float32); medl[1:] = med[:-1]
ELIG = (RC >= 5) & (medl >= 20e6) & np.isfinite(S)
dayret = np.full((T, N), np.nan, np.float32); dayret[1:] = C[1:] / C[:-1] - 1      # close_t/prev_close-1

# ---- SPY overnight (SFP), dividend ex-night add-back
sp = pd.read_parquet(D + "funds.parquet", columns=["ticker", "date", "open", "close"], filters=[("ticker", "==", "SPY")])
sp["date"] = pd.to_datetime(sp["date"]); sp = sp.set_index("date").sort_index()
sd = act[(act.ticker == "SPY") & (act.action == "dividend")].set_index("date")["value"]
so = sp.open.reindex(dates); sc = sp.close.reindex(dates)
divadd = pd.Series(0.0, index=dates)
for d, v in sd.items():
    j = dates.searchsorted(d)
    if j < T: divadd.iloc[j] += v
SPYR = ((so + divadd) / sc.shift(1) - 1).to_numpy()   # R-style: night ending at s

# ---- daily decile loop. Night t = close_t -> open_{t+1}  => uses Rv[t+1], SPY SPYR[t+1]
dec = np.full((T, 10), np.nan); nper = np.zeros(T); advm = np.full(T, np.nan); ovl = np.zeros(T); dropn = np.zeros(T); dropB = np.zeros(T)
topn = np.zeros(T)
for t in range(252, T - 1):
    e = np.flatnonzero(ELIG[t])
    if len(e) < 100: continue
    order = np.argsort(S[t, e], kind="stable"); rk = np.empty(len(e), int); rk[order] = np.arange(len(e))
    g = (rk * 10 // len(e))
    r = Rv[t + 1, e]
    for k in range(10):
        x = r[g == k]; x = x[np.isfinite(x)]
        if len(x): dec[t, k] = x.mean()
    top = e[g == 9]
    nper[t] = len(top); topn[t] = np.isfinite(Rv[t + 1, top]).sum()
    advm[t] = np.median(medl[t, top]); ovl[t] = (dayret[t, top] <= -0.08).sum()
    dropn[t] = nA[t + 1, top].sum(); dropB[t] = nB[t + 1, top].sum()
spy_n = SPYR[1:].tolist() + [np.nan]; spy_n = np.array(spy_n)
exc = dec[:, 9] - spy_n; gx = dec - spy_n[:, None]
idx = dates

def nw_t(x, L=5):
    x = x[np.isfinite(x)]; n = len(x); m = x.mean(); u = x - m
    v = u @ u / n
    for l in range(1, L + 1): v += 2 * (1 - l / (L + 1)) * (u[l:] @ u[:-l]) / n
    return m / np.sqrt(v / n)

def stat(x, label):
    x = x[np.isfinite(x)]
    if len(x) < 30: P(f"  {label}: n={len(x)} (too few)"); return None
    m = x.mean(); t = m / (x.std(ddof=1) / np.sqrt(len(x)))
    ex5 = np.sort(x)[:-5].mean() if len(x) > 10 else np.nan
    P(f"  {label}: n={len(x)} mean {m*1e4:+.2f}bp t {t:.2f} NWt5 {nw_t(x):.2f} median {np.median(x)*1e4:+.2f}bp ex-top5-nights {ex5*1e4:+.2f}bp hit {np.mean(x>0):.3f}")
    return m, t, np.median(x), ex5

PER = {"JUDGE 1998-2015": ("1998-01-01", "2015-12-31"), "half 1998-2006": ("1998-01-01", "2006-12-31"),
       "half 2007-2015": ("2007-01-01", "2015-12-31"), "desc 2016-20": ("2016-01-01", "2020-12-31"),
       "desc 2021-26": ("2021-01-01", "2026-12-31"), "desc 2016-26": ("2016-01-01", "2026-12-31")}
sel = lambda lo, hi: (idx >= lo) & (idx <= hi)
P("first valid night", idx[np.isfinite(exc)][0].date(), "last", idx[np.isfinite(exc)][-1].date())
res = {}
for nm, (lo, hi) in PER.items():
    m = sel(lo, hi)
    P(f"\n== {nm}")
    for c in (0, 2, 5, 7.5):
        net = exc[m] - 2 * c * 1e-4
        res[(nm, c)] = stat(net, f"top-decile minus SPY, {c}bp/side (net {2*c}bp RT)")
    P("  decile gross excess vs SPY (bp/night) D1..D10:", " ".join(f"{np.nanmean(gx[m][:, k])*1e4:+.1f}" for k in range(10)))
    P("  D10-D1 gross spread:", f"{(np.nanmean(gx[m][:,9])-np.nanmean(gx[m][:,0]))*1e4:+.2f}bp; bottom decile excess {np.nanmean(gx[m][:,0])*1e4:+.2f}bp")
    vm = m & (nper > 0)
    P(f"  names/night (top decile) mean {nper[vm].mean():.1f}; median $ADV of picks (median of nightly median) ${np.nanmedian(advm[vm])/1e6:.1f}M")
    P(f"  overlap w/ day-ret<=-8% names: {ovl[vm].mean():.3f}/night ({ovl[vm].sum()/nper[vm].sum():.4%} of picks; nights with any {np.mean(ovl[vm]>0):.3f})")
    P(f"  dropped (action) share of top-decile pick-nights {dropn[vm].sum()/nper[vm].sum():.4%}; (|ret|>50% no action) {dropB[vm].sum()/nper[vm].sum():.4%}")

J = "JUDGE 1998-2015"
g1 = res[(J, 2)]; h1 = res[("half 1998-2006", 2)]; h2 = res[("half 2007-2015", 2)]; g5 = res[(J, 5)]; d = res[("desc 2016-26", 2)]
P("\n== GATE (net excess at 2bp/side unless noted)")
chk = [("net >= +6.5bp/night @2bp/side", g1 and g1[0] * 1e4 >= 6.5, g1 and f"{g1[0]*1e4:+.2f}"),
       ("day-clustered t >= 3", g1 and g1[1] >= 3, g1 and f"{g1[1]:.2f}"),
       ("both halves > 0", h1 and h2 and h1[0] > 0 and h2[0] > 0, f"{h1 and h1[0]*1e4:+.2f} / {h2 and h2[0]*1e4:+.2f}"),
       ("median night > 0", g1 and g1[2] > 0, g1 and f"{g1[2]*1e4:+.2f}"),
       ("ex-top-5 nights > 0", g1 and g1[3] > 0, g1 and f"{g1[3]*1e4:+.2f}"),
       ("> 0 at 5bp/side", g5 and g5[0] > 0, g5 and f"{g5[0]*1e4:+.2f}"),
       ("2016-26 descriptive > 0 @2bp/side", d and d[0] > 0, d and f"{d[0]*1e4:+.2f}")]
for n_, ok_, v in chk: P(f"  {'PASS' if ok_ else 'FAIL'}  {n_}  [{v}]")
P("VERDICT:", "PASS" if all(bool(c[1]) for c in chk) else "KILL (any gate fails)")
P("\nDEVIATIONS: (1) $vol median uses sessions through t-1 (avoid same-day volume); (2) SPY ex-div nights add back the dividend to SPY's open; "
  "(3) delisted names: no synthetic delisting return (night after last bar is missing, not -100%); (4) judge starts when 200 valid nights exist (~Dec 1998-Jan 1999), "
  "since data begins 1997-12-31; (5) nights with ex-date action or |ret|>50% are NaN in both score history and trade; action = split/dividend/spinoff/spinoffdividend/adrratiosplit.")
OUT.write_text("\n".join(LOG) + "\n")
