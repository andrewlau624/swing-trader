"""Study EF runner (pre-registered in round1_prose.md, commit 30251ec). One look, no tuning.

    PYTHONPATH=. .venv/bin/python -m research.sim.etf_flow
"""
from __future__ import annotations
import numpy as np, pandas as pd
from . import book as B
from .etf_flow_data import load_nav, load_px

EQ = "XLB XLE XLF XLI XLK XLP XLU XLV XLY XLRE XLC XBI KRE XOP XRT XHB XME MDY DIA".split()
START, END = pd.Timestamp("2008-01-02"), pd.Timestamp("2026-09-30")


def build(tickers):
    P = {t: load_px(t) for t in tickers + ["SPY"]}
    idx = P["SPY"].index
    o = pd.DataFrame({t: P[t].open * P[t].adjclose / P[t].close for t in P}).reindex(idx)
    c = pd.DataFrame({t: P[t].close for t in P}).reindex(idx)
    adv = pd.DataFrame({t: (P[t].close * P[t].volume).rolling(20).mean().shift(1) for t in P}).reindex(idx)
    hi = pd.DataFrame({t: P[t].high for t in P}).reindex(idx)
    lo = pd.DataFrame({t: P[t].low for t in P}).reindex(idx)
    return o, c, adv, hi, lo


def flows(tickers, idx):
    f, prem, born = {}, {}, {}
    for t in tickers:
        n = load_nav(t).reindex(idx) if False else load_nav(t)
        so, nav = n.so, n.nav
        r = so / so.shift()
        split = ((r - 1).abs() > 0.4) & ((r * nav / nav.shift() - 1).abs() < 0.25)
        ff = (r - 1).where(~split)
        f[t] = ff.reindex(idx)
        prem[t] = None
        born[t] = so.first_valid_index()
    return pd.DataFrame(f), born


def cost(model, price, adv):
    return B.cost_bps(model, np.asarray(price, float), np.asarray(adv, float)) / 1e4


def nw_t(x, lag=4):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; n = len(x); m = x.mean(); e = x - m
    s = e @ e / n
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return m / np.sqrt(s / n)


def clus_t(x, g):
    d = pd.DataFrame({"x": x, "g": g}).dropna(); m = d.x.mean()
    u = (d.x - m).groupby(d.g).sum()
    return m / (np.sqrt((u ** 2).sum()) / len(d))


def gates(name, r, dates, r2x, t, extra=None):
    """r: net per-obs returns; dates: timestamps; r2x: net at 2x cost; t: t-stat."""
    r = pd.Series(np.asarray(r, float), index=pd.DatetimeIndex(dates)).dropna()
    r2 = pd.Series(np.asarray(r2x, float), index=r.index) if len(np.asarray(r2x)) == len(r) else None
    yr = r.groupby(r.index.year).mean()
    top5 = r.sort_values(ascending=False).iloc[5:].mean()
    top1 = r.sort_values(ascending=False).iloc[max(1, int(len(r) * .01)):].mean()
    out = dict(n=len(r), mean_bp=r.mean() * 1e4, t=t, median_bp=r.median() * 1e4, ex5_bp=top5 * 1e4, ex1pct_bp=top1 * 1e4,
               hit=(r > 0).mean(), yrs_pos=(yr > 0).mean(), n_years=len(yr), mean2x_bp=(r2.mean() * 1e4 if r2 is not None else np.nan))
    print(f"[{name}] " + "  ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in out.items()))
    sub = {"2008-12": r["2008":"2012"], "2013-19": r["2013":"2019"], "2020-26": r["2020":]}
    print("   subperiods mean bp (n): " + ", ".join(f"{k} {v.mean()*1e4:.1f} ({len(v)})" for k, v in sub.items()))
    print("   by year bp: " + " ".join(f"{y}:{v*1e4:.0f}" for y, v in yr.items()))
    return out


def seg(o, a, b):  # open(a)->open(b) by row positions arrays
    return o


def H1(o, c, adv, f, stress=0):
    rows = o.index; pos = pd.Series(np.arange(len(rows)), index=rows)
    wk = pd.Series(rows.isocalendar().week.values + 100 * rows.isocalendar().year.values, index=rows)
    last = wk[wk != wk.shift(-1)].index
    F = f.rolling(20, min_periods=15).sum()
    res = []
    for t in last:
        if not (START <= t <= END): continue
        i = pos[t] + 1 + stress; j = i + 5
        if j >= len(rows): continue
        e = [x for x in EQ if x in F.columns and pd.notna(F.loc[t, x]) and pd.notna(o.iloc[i][x]) and pd.notna(o.iloc[j][x])
             and pd.notna(adv.iloc[i][x]) and (x not in ("XLRE", "XLC") or True)]
        e = [x for x in e if f[x].loc[:t].notna().sum() >= 60]
        if len(e) < 8: continue
        s = F.loc[t, e].sort_values(); low, high = list(s.index[:3]), list(s.index[-3:])
        ret = o.iloc[j][e] / o.iloc[i][e] - 1
        cst = pd.Series(cost("tier", o.iloc[i][e] * 1, adv.iloc[i][e]), index=e)
        bor = 0.01 * 5 / 252
        spy = o.iloc[j]["SPY"] / o.iloc[i]["SPY"] - 1
        def net(m):
            return (ret[low].mean() - ret[high].mean() - m * 2 * (cst[low].mean() + cst[high].mean()) - bor)
        res.append(dict(t=t, entry=rows[i], ls=net(1), ls2=net(2), roth=ret[low].mean() - 2 * cst[low].mean() - ret.mean(),
                        roth2=ret[low].mean() - 4 * cst[low].mean() - ret.mean(), lowraw=ret[low].mean() - 2 * cst[low].mean(),
                        lowspy=ret[low].mean() - 2 * cst[low].mean() - spy, gross=ret[low].mean() - ret[high].mean(),
                        low=low, high=high))
    return pd.DataFrame(res).set_index("entry")


def H2(o, c, adv, tick=("JNK", "SJNK"), stress=0, doubling=2.0):
    rows = o.index; pos = pd.Series(np.arange(len(rows)), index=rows)
    spy_w = {}
    ev = []
    for t in tick:
        n = load_nav(t); d = (c[t] / n.nav.reindex(rows) - 1)
        # beta on non-overlapping 5-session windows
        r5 = (o[t].shift(-5) / o[t] - 1).iloc[::5]; s5 = (o["SPY"].shift(-5) / o["SPY"] - 1).iloc[::5]
        z = pd.concat([r5, s5], axis=1).dropna(); z = z.loc[START:END]
        beta = np.cov(z.iloc[:, 0], z.iloc[:, 1])[0, 1] / z.iloc[:, 1].var()
        nxt_ok = -1
        for dt in rows[(rows >= START) & (rows <= END)]:
            if pd.isna(d.get(dt)) or d[dt] > -0.01: continue
            i = pos[dt] + 1 + stress; j = i + 5
            if j >= len(rows) or i <= nxt_ok: continue
            nxt_ok = pos[dt] + 5      # ignore signals within 5 sessions of the entry decision
            if pd.isna(o[t].iloc[i]) or pd.isna(o[t].iloc[j]): continue
            ret = o[t].iloc[j] / o[t].iloc[i] - 1; spy = o["SPY"].iloc[j] / o["SPY"].iloc[i] - 1
            cs = float(cost("tier", o[t].iloc[i], adv[t].iloc[i])) * doubling
            ev.append(dict(entry=rows[i], t=t, D=d[dt], raw=ret, ar=ret - beta * spy - 4 * cs, ar2=ret - beta * spy - 8 * cs,
                           rawnet=ret - 4 * cs, beta=beta, spy=spy))
    return pd.DataFrame(ev).set_index("entry").sort_index()


def H3(o, c, adv, f, hi, lo, stress=0, cmult=2.0, side=-1):
    rows = o.index; pos = pd.Series(np.arange(len(rows)), index=rows)
    ev = []
    for x in EQ:
        if x not in f.columns: continue
        fx = f[x]; cnt = fx.notna().cumsum()
        sel = fx[(fx * -side >= 0.03) & (fx.index >= START) & (fx.index <= END) & (cnt >= 60)].index if side == -1 else \
              fx[(fx >= 0.03) & (fx.index >= START) & (fx.index <= END) & (cnt >= 60)].index
        for t in sel:
            if t not in pos.index: continue
            i = pos[t] + 1 + stress; j = i + 1
            if j >= len(rows) or pd.isna(o[x].iloc[i]) or pd.isna(o[x].iloc[j]): continue
            ret = o[x].iloc[j] / o[x].iloc[i] - 1; spy = o["SPY"].iloc[j] / o["SPY"].iloc[i] - 1
            cs = float(cost("tier", o[x].iloc[i], adv[x].iloc[i]))
            ibs = (c[x].loc[t] - lo[x].loc[t]) / (hi[x].loc[t] - lo[x].loc[t] + 1e-12)
            # timing path: segments k=-3..5 around t
            path = {}
            for k in range(-3, 6):
                a, b = pos[t] + k, pos[t] + k + 1
                if 0 <= a and b < len(rows):
                    path[k] = (o[x].iloc[b] / o[x].iloc[a] - 1) - (o["SPY"].iloc[b] / o["SPY"].iloc[a] - 1)
            sgn = 1 if side == -1 else -1
            ev.append(dict(entry=rows[i], fund=x, f=fx[t], gross=sgn * (ret - spy), net=sgn * (ret - spy) - 2 * cs * cmult,
                           net1=sgn * (ret - spy) - 2 * cs, net2x=sgn * (ret - spy) - 4 * cs * cmult, ibs=ibs, path=path, t=t))
    return pd.DataFrame(ev).set_index("entry").sort_index()


def deciles(o, f, adv):
    """AR (open->open vs SPY) of segment k=0 (flow session) and k=1 (entry session) by f decile, all EQ fund-days."""
    rows = []
    for x in EQ:
        ar = (o[x].shift(-1) / o[x] - 1) - (o["SPY"].shift(-1) / o["SPY"] - 1)
        d = pd.DataFrame({"f": f[x], "k0": ar, "k1": ar.shift(-1), "k2": ar.shift(-2)}).loc[START:END].dropna()
        d = d[f[x].notna().cumsum().reindex(d.index) >= 60]
        rows.append(d)
    d = pd.concat(rows); d["dec"] = pd.qcut(d.f.rank(method="first"), 10, labels=False)
    return d.groupby("dec").agg(f_mean=("f", "mean"), k0_bp=("k0", lambda s: s.mean() * 1e4), k1_bp=("k1", lambda s: s.mean() * 1e4),
                                k2_bp=("k2", lambda s: s.mean() * 1e4), n=("f", "size"))


def main():
    tick = EQ + ["JNK", "SJNK"]
    o, c, adv, hi, lo = build(tick)
    f, born = flows(EQ, o.index)
    pd.set_option("display.width", 200)
    print("=== f deciles (all EQ fund-days 2008-26): AR vs SPY, open->open; k0 = session of row t, k1 = entry session (t+1), k2 = t+2")
    print(deciles(o, f, adv).round(2).to_string())
    print("\n=== H1")
    for st in (0, 1):
        h = H1(o, c, adv, f, st)
        print(f"-- entry at t+{1+st}: gross LS {h.gross.mean()*1e4:.1f}bp")
        g = gates(f"H1 LS st{st}", h.ls, h.index, h.ls2, nw_t(h.ls))
        gates(f"H1 Roth LOW-EW st{st}", h.roth, h.index, h.roth2, nw_t(h.roth))
        gates(f"H1 LOW-SPY st{st}", h.lowspy, h.index, h.lowspy, nw_t(h.lowspy))
    print("\n=== H2")
    for st in (0, 1):
        e = H2(o, c, adv, stress=st)
        print(f"-- entry at t+{1+st}: episodes {len(e)}  mean D {e.D.mean():.4f}  raw net {e.rawnet.mean()*1e4:.0f}bp  by fund:",
              e.groupby('t').ar.agg(['size', 'mean']).to_dict())
        if len(e) >= 3:
            gates(f"H2 st{st}", e.ar, e.index, e.ar2, clus_t(e.ar, e.index.to_period('W')))
            print(f"   ex 2 largest: {e.ar.sort_values(ascending=False).iloc[2:].mean()*1e4:.0f}bp; ex2008-09: {e.ar[(e.index.year>2009)|(e.index.year<2008)].mean()*1e4:.0f}bp; ex 2020-02..04: {e.ar[~((e.index>='2020-02-01')&(e.index<='2020-04-30'))].mean()*1e4:.0f}bp")
            print(e[["t", "D", "raw", "ar"]].round(4).to_string()) if len(e) <= 40 else None
    print("\n=== H3 (long after f<=-3%)")
    for st in (0, 1):
        e = H3(o, c, adv, f, hi, lo, stress=st)
        print(f"-- entry at t+{1+st}: n {len(e)} gross AR {e.gross.mean()*1e4:.1f}bp  net(tier) {e.net1.mean()*1e4:.1f}bp")
        gates(f"H3 st{st}", e.net, e.index, e.net2x, clus_t(e.net, e.index))
        if st == 0:
            print("   cum AR by segment k (k=0 is flow session t open->t+1 open; entry segment is k=1), bp mean:",
                  {k: round(np.nanmean([p.get(k, np.nan) for p in e.path]) * 1e4, 1) for k in range(-3, 6)})
            print("   share with IBS_t<0.2:", round((e.ibs < 0.2).mean(), 2), " by fund:", e.fund.value_counts().head(6).to_dict())
            print("   top-5 funds share:", e.fund.value_counts().head(5).sum() / len(e))
    e = H3(o, c, adv, f, hi, lo, side=+1)
    print(f"\n[H3 creation side, short, reported only] n {len(e)} net {e.net.mean()*1e4:.1f}bp gross {e.gross.mean()*1e4:.1f}bp")


if __name__ == "__main__":
    main()
