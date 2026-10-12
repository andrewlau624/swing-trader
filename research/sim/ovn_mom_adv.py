"""Adversarial checks on OVN-MOM (does not alter registered logic; reuses runner prefix by exec). Run: .venv/bin/python research/sim/ovn_mom_adv.py"""
import json, glob, pathlib, numpy as np, pandas as pd
src = open("research/sim/ovn_mom.py").read()
src = src.split("# ---- daily decile loop")[0]
g = {}; exec(compile(src, "ovn_mom_prefix", "exec"), g)
O, C, RC, Rv, S, ELIG, medl, dates, cols, T, SPYR, so, sc = [g[k] for k in "O C RC Rv S ELIG medl dates cols T SPYR so sc".split()]
LOG = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)
SPYo = SPYR                                  # night ending at s
SPYc = (sc / sc.shift(1) - 1).to_numpy()     # close-close day s (SFP close; may be div-adjusted)
SPYi = (sc / so - 1).to_numpy()              # intraday day s
Ri = np.full(O.shape, np.nan, np.float32); Ri = C / O - 1   # intraday of day s
Rcc = np.full(O.shape, np.nan, np.float32); Rcc[1:] = C[1:] / C[:-1] - 1
J0, J1 = np.searchsorted(dates, pd.Timestamp("1998-12-01")), np.searchsorted(dates, pd.Timestamp("2015-12-31"), side="right")
def tstat(x):
    x = x[np.isfinite(x)]; return len(x), x.mean() * 1e4, x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
def rep(label, ser, mask=None):
    x = np.asarray(ser, float)
    if mask is not None: x = np.where(mask, x, np.nan)
    if np.isfinite(x).sum() < 30: P(f"  {label}: n<30"); return
    n, m, t = tstat(x); P(f"  {label}: n={n} mean {m:+.2f}bp t {t:.2f} median {np.nanmedian(x)*1e4:+.2f}")
# per-night top-decile picks
picks = {}
for t in range(252, T - 1):
    e = np.flatnonzero(ELIG[t])
    if len(e) < 100: continue
    o = np.argsort(S[t, e], kind="stable"); rk = np.empty(len(e), int); rk[o] = np.arange(len(e))
    picks[t] = (e, rk * 10 // len(e))
def night_series(fn):
    out = np.full(T, np.nan)
    for t, (e, gq) in picks.items(): out[t] = fn(t, e, gq)
    return out
def mean_fin(x):
    x = x[np.isfinite(x)]; return x.mean() if len(x) else np.nan
base = night_series(lambda t, e, gq: mean_fin(Rv[t + 1, e[gq == 9]]))
spyn = np.r_[SPYo[1:], np.nan]
exc = base - spyn
tt = pd.Series(range(T), index=dates)
cost = 4e-4
P("== BASELINE top-decile overnight minus SPY (judge 1998-12..2015-12), gross")
rep("judge", exc[J0:J1]); rep("judge net 2bp/side", exc[J0:J1] - cost)
P("== 1a decimalization split (net 2bp/side)")
dc = np.searchsorted(dates, pd.Timestamp("2001-05-01"))
rep("1998-12..2001-04", exc[J0:dc] - cost); rep("2001-05..2015-12", exc[dc:J1] - cost)
rep("2001-05..2006", exc[dc:np.searchsorted(dates, pd.Timestamp("2007-01-01"))] - cost)
rep("2007..2015", exc[np.searchsorted(dates, pd.Timestamp("2007-01-01")):J1] - cost)
P("== 1b price / ADV terciles within top decile (gross excess vs SPY; within-night terciles)")
for nm, M in (("raw price", RC), ("20d $ADV(t-1)", medl)):
    for q in range(3):
        def f(t, e, gq, q=q, M=M):
            top = e[gq == 9]; v = M[t, top]; ok = np.isfinite(v); top = top[ok]; v = v[ok]
            if len(top) < 9: return np.nan
            r = np.argsort(np.argsort(v)) * 3 // len(v); return mean_fin(Rv[t + 1, top[r == q]])
        s = night_series(f) - spyn
        rep(f"{nm} tercile {q} (0=low)", s[J0:J1])
P("   by absolute price (top decile picks pooled): <10, 10-25, >=25  [pooled mean minus mean SPY same nights]")
for lo, hi in ((5, 10), (10, 25), (25, 1e9)):
    vals = []; sp = []
    for t, (e, gq) in picks.items():
        if not (J0 <= t < J1): continue
        top = e[gq == 9]; m = (RC[t, top] >= lo) & (RC[t, top] < hi); r = Rv[t + 1, top[m]]; r = r[np.isfinite(r)]
        if len(r): vals.append(r.mean()); sp.append(spyn[t])
    v = np.array(vals) - np.array(sp); P(f"  px[{lo},{hi}): nights {len(v)} mean {v.mean()*1e4:+.2f}bp t {v.mean()/(v.std(ddof=1)/np.sqrt(len(v))):.2f}")
P("== 1c / 2 intraday & close-close of the same picks (night t -> t+1), gross vs SPY")
oi = night_series(lambda t, e, gq: mean_fin(Ri[t + 1, e[gq == 9]])) - np.r_[SPYi[1:], np.nan]
cc = night_series(lambda t, e, gq: mean_fin(Rcc[t + 1, e[gq == 9]])) - np.r_[SPYc[1:], np.nan]
oi_t = night_series(lambda t, e, gq: mean_fin(Ri[t, e[gq == 9]])) - SPYi
rep("next-day intraday (open->close t+1) excess", oi[J0:J1]); rep("next-day close-to-close excess", cc[J0:J1])
rep("same-day (day t) intraday excess [pick formation day]", oi_t[J0:J1])
rep("close-to-close 2016-26", cc[np.searchsorted(dates, pd.Timestamp("2016-01-01")):])
rep("intraday 2016-26", oi[np.searchsorted(dates, pd.Timestamp("2016-01-01")):])
P("   skip-a-night: rank on S[t-1] (nights through t-1 open), hold night t->t+1 (stale-score persistence)")
sk = np.full(T, np.nan)
for t in range(253, T - 1):
    if (t - 1) not in picks: continue
    e, gq = picks[t - 1]; top = e[gq == 9]
    top = top[ELIG[t, top]]
    sk[t] = mean_fin(Rv[t + 1, top])
rep("skip-1 gross excess", (sk - spyn)[J0:J1])
P("   score from nights ending t-1 (exclude the latest night's own bounce), same-day-ranked: lag-1 score vs original")
S1 = np.full(S.shape, np.nan, np.float32); S1[1:] = S[:-1]
sk2 = np.full(T, np.nan)
for t in range(253, T - 1):
    e = np.flatnonzero(ELIG[t] & np.isfinite(S1[t])); 
    if len(e) < 100: continue
    o = np.argsort(S1[t, e], kind="stable"); rk = np.empty(len(e), int); rk[o] = np.arange(len(e)); sk2[t] = mean_fin(Rv[t + 1, e[rk * 10 // len(e) == 9]])
rep("lag-1 score re-ranked gross excess", (sk2 - spyn)[J0:J1])
P("== 4 per-year net (2bp/side) excess, top decile")
yr = dates.year.to_numpy()
for y in range(1999, 2027):
    m = (yr == y); x = (exc - cost)[m]; 
    if np.isfinite(x).sum() > 30: P(f"  {y}: n={int(np.isfinite(x).sum())} net {np.nanmean(x)*1e4:+.2f}bp  gross {np.nanmean(exc[m])*1e4:+.2f}bp")
P("   share of 2016-26 top-decile picks with 20d median $vol < $50M / <$100M; 1% of ADV as auction$ proxy < $20M is all picks (median pick ADV below)")
a = []; 
for t, (e, gq) in picks.items():
    if t >= np.searchsorted(dates, pd.Timestamp("2016-01-01")): a.append(medl[t, e[gq == 9]])
a = np.concatenate(a); a = a[np.isfinite(a)]
P(f"  picks {len(a)}: ADV<50M {np.mean(a<50e6):.3f}  <100M {np.mean(a<100e6):.3f}  median {np.median(a)/1e6:.1f}M; 1%-ADV proxy median ${np.median(a)*0.01/1e6:.2f}M (below $20M for {np.mean(a*0.01<20e6):.3f})")
P("== 3 official prints vs Sharadar (2021-26 top-decile pick-nights)")
auc = {}
for f in sorted(glob.glob("data/research/night/auctions/*.json")) + sorted(glob.glob("data/research/night/auction_hist/*.json")):
    for sym, L in json.load(open(f)).items():
        for r in L:
            op = [x["p"] for x in (r.get("o") or []) if x["c"] == "O"]
            cl = [x for x in (r.get("c") or []) if x["c"] in ("6", "M")]
            cp = cl[0]["p"] if cl else None; cs = max(cl, key=lambda x: x["s"]) if cl else None
            k = (sym, r["d"]); old = auc.get(k, {})
            auc[k] = {"o": op[0] if op else old.get("o"), "c": cs["p"] if cs else old.get("c"), "cs": cs["s"] * cs["p"] if cs else old.get("cs")}
P(f"  auction keys {len(auc)}")
ci = g["ci"]; rows = []
t21 = np.searchsorted(dates, pd.Timestamp("2020-11-01"))
for t, (e, gq) in picks.items():
    if t < t21 or t + 1 >= T: continue
    for j in e[gq == 9]:
        sym = cols[j]; d0 = str(dates[t].date()); d1 = str(dates[t + 1].date())
        a0 = auc.get((sym, d0)); a1 = auc.get((sym, d1))
        if a0 and a1 and a0.get("c") and a1.get("o") and np.isfinite(O[t + 1, j]):
            f0 = RC[t, j] / C[t, j]; f1 = RC[t + 1, j] / C[t + 1, j]   # adj->raw factors
            rows.append((sym, d0, C[t, j] * f0, a0["c"], O[t + 1, j] * f1, a1["o"], a0["cs"], Rv[t + 1, j]))
P(f"  matchable top-decile pick-nights: {len(rows)}")
if rows:
    df = pd.DataFrame(rows, columns="sym d0 shC offC shO offO csd r".split())
    smp = df.sample(min(200, len(df)), random_state=1)
    dc_ = (smp.shC / smp.offC - 1).abs() * 1e4; do_ = (smp.shO / smp.offO - 1).abs() * 1e4
    P(f"  sample {len(smp)}: median |close diff| {dc_.median():.2f}bp (p90 {dc_.quantile(.9):.1f}); median |open diff| {do_.median():.2f}bp (p90 {do_.quantile(.9):.1f})")
    on_off = (smp.offO / smp.offC - 1); on_sh = (smp.shO / smp.shC - 1)
    P(f"  overnight on official crosses mean {on_off.mean()*1e4:+.1f}bp vs Sharadar {on_sh.mean()*1e4:+.1f}bp (sample, raw, ex-dividend nights may bias)")
    P(f"  close-auction $ (largest closing print) median ${df.csd.median()/1e6:.2f}M; share < $20M {np.mean(df.csd<20e6):.3f}; share <$1M {np.mean(df.csd<1e6):.3f}")
if rows:
    P("== 3b full matched set, per-night top-decile EW overnight on OFFICIAL crosses vs Sharadar, same picks (excl. ex-action nights), minus SPY, gross/net2")
    df["nd"] = pd.to_datetime(df.d0); df["on_off"] = df.offO / df.offC - 1; df["on_sh"] = df.shO / df.shC - 1
    df = df[np.isfinite(df.r)]
    gb = df.groupby("nd")[["on_off", "on_sh"]].mean(); gb["spy"] = [spyn[np.searchsorted(dates, d)] for d in gb.index]
    gb = gb[(gb.on_off.abs() < .2)]
    for c in ("on_off", "on_sh"):
        x = (gb[c] - gb.spy).to_numpy(); n, m, t_ = tstat(x); P(f"  {c}: nights {n} gross {m:+.2f}bp t {t_:.2f} net(2bp/side) {m-4:+.2f}bp median {np.median(x)*1e4:+.2f}")
    P(f"  per-pick median |open diff| full set {np.median((df.shO/df.offO-1).abs())*1e4:.2f}bp, share >20bp {np.mean((df.shO/df.offO-1).abs()>.002):.3f}")
pathlib.Path("data/research/program/ovn_mom_adv_out.txt").write_text("\n".join(LOG) + "\n")
