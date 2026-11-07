"""Study OIL-SHOCK (N 1110 -> 1112): does a crude-oil spike condition hurt the MR legs, and is it a reason to scale IBS down?
Pre-reg research/drafts/round1_prose.md ("Study OIL-SHOCK"). One look.
  P (N 1111, primary): FRED DCOILWTICO 20-obs return >= +20%.  S (N 1112, secondary): WTI at a 252-obs high.
Judge: IBS leg 1986-2020 = single-index proxy 1986-1998 (^GSPC close->close to 1993-01, SPY open->open after) + EQ18 live rule
1999-2016 Sharadar (shar_crash.ibs_daily) + ibs_oos series 2017-20. 2021-26 and the night leg are descriptive only.
Data: data/research/oil_shock/ (FRED csv, Yahoo chart json for ^GSPC/SPY with high/low; vt_flow.yahoo_ohlc keeps no H/L).
  PYTHONPATH=.:<sharadar-data> python3 -m research.sim.oil_shock"""
import json

import numpy as np
import pandas as pd

from research.sim import ibs_oos, nx
from research.sim import shar_crash as sc

DATA = sc.ROOT / "data/research/oil_shock"
OUT = sc.ROOT / "data/research/program/oil_shock_out.txt"
COST = 5e-4
RNG = np.random.default_rng(1111)
L = []


def P(s=""):
    print(s, flush=True); L.append(s)


def fred(sid):
    d = pd.read_csv(DATA / f"{sid}.csv")
    return pd.Series(pd.to_numeric(d[sid], errors="coerce").values, index=pd.to_datetime(d["observation_date"])).dropna()


def yahoo(sym):
    j = json.load(open(DATA / f"y_{sym}.json"))["chart"]["result"][0]; q = j["indicators"]["quote"][0]
    idx = pd.to_datetime(j["timestamp"], unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")}, index=idx).dropna()
    return df[~df.index.duplicated(keep="last")]


def oil_states(idx):
    w = fred("DCOILWTICO"); w = w[w > 0]
    r20 = w / w.shift(20) - 1; hi = w >= w.rolling(252).max()
    asof = lambda s: s.reindex(s.index.union(idx)).ffill().reindex(idx)
    return (asof(r20) >= 0.20).fillna(False).to_numpy(), asof(hi.astype(float)).fillna(0).astype(bool).to_numpy()


def proxy_ibs():
    """Single-index IBS<0.2 proxy, net 2 x 5bp. ^GSPC: close d -> close d+1 (opens are stale); SPY: open d+1 -> open d+2."""
    g, s = yahoo("GSPC"), yahoo("SPY")
    def leg(df, oo):
        ibs = (df.close - df.low) / (df.high - df.low)
        ret = (df.open.shift(-2) / df.open.shift(-1) - 1) if oo else (df.close.shift(-1) / df.close - 1)
        return (ret - 2 * COST).where(ibs < 0.2, 0.0).fillna(0.0)
    a = leg(g, False); a = a[(a.index >= "1986-01-02") & (a.index < "1993-02-01")]
    b = leg(s, True); return pd.concat([a, b[b.index >= "1993-02-01"]])


def stats(r):
    r = r.fillna(0.0); eq = (1 + r).cumprod(); yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1; mdd = float((eq / eq.cummax() - 1).min())
    return cagr, mdd, (cagr / -mdd if mdd < 0 else np.nan)


def dd_window(r):
    eq = (1 + r.fillna(0)).cumprod(); dd = eq / eq.cummax() - 1; tr = dd.idxmin(); pk = eq.loc[:tr].idxmax(); return pk, tr


def tstat(x): x = np.asarray(x, float); return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 else np.nan


def episodes(on, gap=20):
    out, cur, last = [], None, -10**9
    for i in np.flatnonzero(on):
        if i - last > gap:
            if cur: out.append(cur)
            cur = [i, i]
        else: cur[1] = i
        last = i
    if cur: out.append(cur)
    return out


def placebo_p(x, on, n=1000):
    obs = x[on].mean(); n_ = len(x); sh = RNG.integers(252, n_ - 252, n)
    return float(np.mean([x[np.roll(on, k)].mean() <= obs for k in sh]))


# ------------------------------------------------------------------ series
prox = proxy_ibs()
etf = ibs_oos._trades("ibs_lo"); etf_d = (etf.ret - 2 * COST).groupby(level=0).mean()
etf_idx = ibs_oos.D.etf()["close"].index
o_start = etf_d.index.min()
from sharadar import prices as sh_prices
df = sh_prices(sc.EQ18, "1997-11-01", "2026-09-30", adjust="split", source="funds"); df = df[df.ticker.isin(sc.EQ18)].assign(date=lambda x: pd.to_datetime(x.date))
O, H, Lo, C = [df.pivot(index="date", columns="ticker", values=c).sort_index() for c in ("open", "high", "low", "close")]
sh_ibs = (sc.ibs_daily(O, H, Lo, C) - 2 * COST)
sh_idx = C.index[C.index >= "1999-01-04"]
sh_full = sh_ibs.reindex(sh_idx).fillna(0.0)
P(f"ibs_oos series starts {o_start.date()}; Sharadar EQ18 IBS used 1999-01-04..{(o_start - pd.Timedelta(days=1)).date()}")
eq18 = pd.concat([sh_full[sh_full.index < o_start], etf_d.reindex(etf_idx[etf_idx >= o_start]).fillna(0.0)])
judge = pd.concat([prox[prox.index < "1999-01-04"], eq18[eq18.index <= "2020-12-31"]])
report = pd.concat([etf_d.reindex(etf_idx[etf_idx >= "2021-01-01"]).fillna(0.0)])
vix = fred("VIXCLS")
P(f"overlap check 2017-20: corr(Sharadar EQ18 IBS, ibs_oos) = {sh_full.reindex(etf_d.index).fillna(0).loc[o_start:'2020'].corr(etf_d.loc[o_start:'2020']):.2f}")


def block(name, x, gate=False, cost_mult=1.0):
    x = x.copy(); idx = x.index; pon, son = oil_states(idx)
    vx = vix.reindex(vix.index.union(idx)).ffill().reindex(idx).to_numpy(); hv = vx > 25
    mid = pd.Timestamp("2003-01-01")
    P(f"== {name}: sessions {len(idx)} ({idx[0].date()}..{idx[-1].date()}), signal sessions {(x != 0).sum()}")
    res = {}
    for lab, on in (("P r20>=+20% (N1111)", pon), ("S 1y high (N1112)", son)):
        xv = x.to_numpy(); ep = episodes(on)
        sig = xv != 0
        on_m, off_m = xv[on].mean(), xv[~on].mean()
        P(f"  [{lab}] ON {on.sum()} sessions ({on.mean()*100:.1f}%), {len(ep)} episodes, ON signal trades {(on & sig).sum()} | "
          f"VIX>25 on {np.nanmean(hv[on])*100:.0f}% of ON vs {np.nanmean(hv[~on])*100:.0f}% of OFF; ON share of VIX>25 days {on[hv].mean()*100:.0f}%")
        P(f"    leg per session: ON {on_m*1e4:+6.2f}bp (t {tstat(xv[on]):+5.2f}) vs OFF {off_m*1e4:+6.2f}bp | per trade ON {xv[on & sig].mean()*1e4:+6.1f} "
          f"(median {np.median(xv[on & sig])*1e4:+6.1f}, hit {(xv[on & sig] > 0).mean()*100:.0f}%) vs OFF {xv[~on & sig].mean()*1e4:+6.1f} (median {np.median(xv[~on & sig])*1e4:+6.1f})")
        h1, h2 = on & (idx < mid), on & (idx >= mid)
        lv = on & ~hv & ~np.isnan(vx)
        P(f"    halves ON: <2003 {xv[h1].mean()*1e4 if h1.any() else np.nan:+6.2f}bp (n {h1.sum()}) / >=2003 {xv[h2].mean()*1e4 if h2.any() else np.nan:+6.2f}bp (n {h2.sum()}) | "
          f"ON & VIX<=25 {xv[lv].mean()*1e4 if lv.any() else np.nan:+6.2f}bp (n {lv.sum()}) ; ON & VIX>25 {xv[on & hv].mean()*1e4 if (on & hv).any() else np.nan:+6.2f}bp (n {(on & hv).sum()}) ; "
          f"OFF & VIX>25 {xv[~on & hv].mean()*1e4:+6.2f}bp")
        ons = xv[on & sig]; ex5 = np.sort(ons)[5:].mean() if len(ons) > 6 else np.nan
        P(f"    ex-worst-5 ON trades {ex5*1e4:+6.1f}bp/trade ; placebo (circular shift, 1000) P(shift ON mean <= obs) = {placebo_p(xv, on):.3f}")
        ep_m = []
        for a, b in ep:
            seg = xv[a:b + 1]; m = on[a:b + 1]
            ep_m.append((idx[a].date(), idx[b].date(), int(m.sum()), seg[m].sum()))
        P("    episodes (start..end, ON sessions, sum of leg return on ON sessions): " + "; ".join(f"{s}..{e} n{n} {v*100:+.2f}%" for s, e, n, v in ep_m))
        worst = int(np.argmin([v for *_, v in ep_m])) if ep_m else None
        if worst is not None:
            keep = on.copy(); a, b = ep[worst]; keep[a:b + 1] = False
            exw = xv[keep].mean() if keep.any() else np.nan
        else: exw = np.nan
        base = x; arm0 = x.where(~on, 0.0); arm5 = x.where(~on, 0.5 * x)
        (bc, bm, bmar), (c0, m0, mar0), (c5, m5, mar5) = stats(base), stats(arm0), stats(arm5)
        pk, tr = dd_window(base); w = (idx >= pk) & (idx <= tr)
        lr = np.log1p(xv); share = lr[w & on].sum() / lr[w].sum() if lr[w].sum() != 0 else np.nan
        P(f"    base CAGR {bc*100:5.2f}% maxDD {bm*100:6.1f}% MAR {bmar:4.2f} | x0 on ON: {c0*100:5.2f}% {m0*100:6.1f}% MAR {mar0:4.2f} | x0.5: {c5*100:5.2f}% {m5*100:6.1f}% MAR {mar5:4.2f} | "
              f"maxDD window {pk.date()}..{tr.date()}: ON sessions {int((w & on).sum())}/{int(w.sum())}, share of DD log-loss on ON {share*100:+.0f}%")
        if gate:
            sub = xv[on]; t1 = on_m < 0; pp = placebo_p(xv, on); g1 = t1 and pp <= 0.05
            g2 = (xv[h1].mean() < 0 if h1.any() else False) and (xv[h2].mean() < 0 if h2.any() else False)
            g3 = (m0 - bm >= 0.02) and (c0 >= bc - 0.002)
            g4 = lv.any() and xv[lv].mean() < 0
            g5 = exw < 0
            P(f"    GATES: G1 ON<0 & placebo<=.05 {g1} (p {pp:.3f}) | G2 both halves {g2} | G3 DD+2pp & CAGR {g3} | G4 VIX<=25 {g4} | G5 ex-worst-episode {g5} (ex-worst {exw*1e4:+.2f}bp)"
              f" => {'PASS' if all((g1, g2, g3, g4, g5)) else 'FAIL'}")
        res[lab] = on
    return pon, son


P("OIL-SHOCK (N 1110 -> 1112). Leg = IBS, per session, net 5bp/side, 0 on no-signal sessions.")
block("JUDGE IBS 1986-2020 (proxy 1986-98 + EQ18 1999-2020)", judge, gate=True)
P("--- cost shock 2x (extra 10bp per trade):")
block("JUDGE IBS 1986-2020, 2x cost", judge.where(judge == 0, judge - 2 * COST))
block("JUDGE sub: index proxy only 1986-1998", judge[judge.index < "1999-01-04"])
block("JUDGE sub: EQ18 1999-2020", judge[judge.index >= "1999-01-04"])
block("REPORT (touched) IBS ibs_oos 2021-26", report)
P("--- single-index proxy SPY open->open 1993-2026 (consistent across 2008/2022/2026; descriptive):")
block("SPY-IBS proxy 1993-2026", prox[prox.index >= "1993-02-01"])

P("--- night leg (DESCRIPTIVE only; 1999-2015 = NX window, judging reserved) and book 0.5/0.5:")
Pp = nx.Paths(); master = nx.load_master(Pp); act = nx.read_table(Pp, "ACTIONS"); sep = nx.read_table(Pp, "SEP"); sfp = nx.read_table(Pp, "SFP")
for lo, hi in (("1999-01-04", "2015-12-31"), ("2016-01-04", "2026-09-18")):
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    ngt, tr, _ = sc.night_daily(lo, hi, sep, sfp, master, act)
    idx = C.index[(C.index >= lo) & (C.index <= hi)]
    ngt = ngt.reindex(idx).fillna(0.0) - 2 * COST * tr.groupby("date").per.sum().reindex(idx).fillna(0.0)
    block(f"NIGHT {lo.year}-{hi.year} (descriptive)", ngt)
    ib = sh_full.reindex(idx).fillna(0.0) if hi.year < 2016 else eq18.reindex(idx).fillna(0.0)
    block(f"BOOK 0.5 IBS + 0.5 night {lo.year}-{hi.year} (descriptive)", 0.5 * ib + 0.5 * ngt)

OUT.write_text("\n".join(L) + "\n")
