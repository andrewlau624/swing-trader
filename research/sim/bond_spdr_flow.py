"""Study BSPD runner — bond-SPDR premium/discount and creation-flow reversion.

Pre-registered: research/drafts/study_bspd.md (N 834 -> 835). One look, no tuning.

    PYTHONPATH=. .venv/bin/python -m research.sim.bond_spdr_flow

Premium uses RAW px.close / NAV (never adjclose). Costs fixed per-side c in {2bp,5bp};
a two-leg spread round trip = 4c. Report net at 1x/2x/3x.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from .etf_flow_data import load_nav, load_px

UNIV = ["JNK", "SJNK", "SPSB", "SPIB", "SPLB"]
HDRS = ["JNK", "SJNK", "SPSB", "SPIB", "SPLB"]
OUT = "data/research/program/bond_spdr_out.txt"

_lines: list[str] = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    _lines.append(s)


def nw_t(x, lag=4):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; n = len(x)
    if n < 3:
        return np.nan
    m = x.mean(); e = x - m; s = e @ e / n
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return m / np.sqrt(s / n) if s > 0 else np.nan


def clus_t(x, g):
    d = pd.DataFrame({"x": np.asarray(x, float), "g": np.asarray(g)}).dropna()
    if len(d) < 2:
        return np.nan
    m = d.x.mean()
    u = (d.x - m).groupby(d.g).sum()
    denom = np.sqrt((u ** 2).sum()) / len(d)
    return m / denom if denom > 0 else np.nan


def stats(name, r, dates):
    r = pd.Series(np.asarray(r, float), index=pd.DatetimeIndex(dates)).dropna()
    if len(r) == 0:
        log(f"[{name}] n=0"); return None
    g = pd.DatetimeIndex(r.index).normalize()
    d = dict(n=len(r), mean_bp=r.mean() * 1e4, median_bp=r.median() * 1e4,
             hit=(r > 0).mean(), t=clus_t(r.values, g), nwt=nw_t(r.values),
             ex5_bp=r.sort_values(ascending=False).iloc[5:].mean() * 1e4 if len(r) > 5 else np.nan)
    log(f"[{name}] n={d['n']} mean={d['mean_bp']:.2f}bp median={d['median_bp']:.2f}bp "
        f"hit={d['hit']:.2%} clus_t={d['t']:.2f} nw_t={d['nwt']:.2f} ex5={d['ex5_bp']:.2f}bp")
    yr = r.groupby(r.index.year).mean() * 1e4
    log("   by year bp: " + " ".join(f"{y}:{v:.0f}" for y, v in yr.items()))
    # sub-periods
    subs = {"2008-2015": r[(r.index.year >= 2008) & (r.index.year <= 2015)],
            "2016-2020": r[(r.index.year >= 2016) & (r.index.year <= 2020)],
            "2021-2026": r[r.index.year >= 2021]}
    log("   subperiods mean bp (n): " + ", ".join(
        f"{k} {v.mean()*1e4:.1f} ({len(v)})" for k, v in subs.items()))
    # both halves split at pooled median date
    med = r.index.to_series().median()
    h1, h2 = r[r.index <= med], r[r.index > med]
    log(f"   halves @{med.date()}: H1_mean={h1.mean()*1e4:.1f}bp (n={len(h1)}) "
        f"H2_mean={h2.mean()*1e4:.1f}bp (n={len(h2)}) sign_same={(h1.mean()>0)==(h2.mean()>0)}")
    d.update(h1_bp=h1.mean() * 1e4, h2_bp=h2.mean() * 1e4,
             same_sign=bool((h1.mean() > 0) == (h2.mean() > 0)),
             subs={k: (v.mean() * 1e4, len(v)) for k, v in subs.items()})
    return d


def build():
    px = {t: load_px(t) for t in UNIV}
    idx = sorted(set().union(*[px[t].index for t in UNIV]))
    idx = pd.DatetimeIndex(idx)
    o = pd.DataFrame({t: px[t].open.reindex(idx) for t in UNIV})
    c = pd.DataFrame({t: px[t].close.reindex(idx) for t in UNIV})
    nav = {}
    for t in UNIV:
        n = load_nav(t)
        nav[t] = n
    nav_eff = pd.DataFrame({t: nav[t].nav.reindex(idx, method="ffill") for t in UNIV})
    prem = c / nav_eff - 1.0
    # flow on nav index, split-filtered, reindexed without carry
    flow = {}
    for t in UNIV:
        n = nav[t]; so, nv = n.so, n.nav
        r = so / so.shift()
        split = ((r - 1).abs() > 0.4) & ((r * nv / nv.shift() - 1).abs() < 0.25)
        flow[t] = ((r - 1).where(~split)).reindex(idx)
    flow = pd.DataFrame(flow)
    return idx, o, c, prem, flow, nav, px


def _rets(o, entry, exit_, funds):
    a = o.iloc[entry][funds]; b = o.iloc[exit_][funds]
    return (b / a - 1.0), a


def h1_trades(idx, o, prem, h, min_funds=3):
    n = len(idx); trades = []
    last_exit = -1
    for i in range(n):
        row = prem.iloc[i].dropna()
        if len(row) < min_funds:
            continue
        s = row.sort_values()
        bot, top = s.index[0], s.index[-1]
        entry = i + 1; ex = i + 1 + h
        if ex >= n or entry <= last_exit:
            continue
        funds = list(prem.iloc[i].dropna().index)
        ropen = o.iloc[entry]
        if not all(pd.notna(ropen[f]) and pd.notna(o.iloc[ex][f]) for f in funds):
            continue
        if not (pd.notna(o.iloc[entry][bot]) and pd.notna(o.iloc[ex][bot])):
            continue
        rets = (o.iloc[ex][funds] / o.iloc[entry][funds] - 1.0).dropna()
        uni = rets.mean()
        if bot not in rets.index or top not in rets.index:
            continue
        trades.append(dict(t=idx[i], entry=idx[entry], r_mkt=rets[bot] - uni,
                           r_top=rets[bot] - rets[top], r_long=rets[bot], nfund=len(funds)))
        last_exit = ex
    return pd.DataFrame(trades)


def h2_trades(idx, o, flow, min_funds=3, h=1):
    n = len(idx); trades = []; last_exit = -1
    for i in range(n):
        row = flow.iloc[i].dropna()
        if len(row) < min_funds:
            continue
        top = row.sort_values().index[-1]
        entry = i + 1; ex = i + 1 + h
        if ex >= n or entry <= last_exit:
            continue
        funds = list(flow.iloc[i].dropna().index)
        if not all(pd.notna(o.iloc[entry][f]) and pd.notna(o.iloc[ex][f]) for f in funds):
            continue
        rets = (o.iloc[ex][funds] / o.iloc[entry][funds] - 1.0).dropna()
        uni = rets.mean()
        if top not in rets.index:
            continue
        trades.append(dict(t=idx[i], entry=idx[entry], r_mkt=rets[top] - uni, r_long=rets[top],
                           flow=row[top], nfund=len(funds)))
        last_exit = ex
    return pd.DataFrame(trades)


def report_spread(name, tr, c_bp_scen=(2, 4, 6)):
    if len(tr) == 0:
        log(f"[{name}] no trades"); return None
    log(f"\n=== {name}  (n trades {len(tr)}, non-overlapping)")
    res = {}
    for label, gross in (("mkt-adj", tr.r_mkt), ("vs-top", tr.r_top) if "r_top" in tr else (None, None)):
        if label is None:
            continue
        for mult, c in zip((1, 2, 3), c_bp_scen):
            net = gross - 4 * c / 1e4  # two-leg spread, round trip 4c
            d = stats(f"{name} {label} net_{mult}x(c={c}bp)", net, tr.entry)
            res[(label, mult)] = (d, gross.mean() * 1e4)
        log(f"   {label}: gross={gross.mean()*1e4:.2f}bp")
    # long-only reference at 1x
    stats(f"{name} long-only net_1x(c=2bp)", tr.r_long - 2 * 2 / 1e4, tr.entry)
    return res


def verdict(name, d):
    if d is None:
        log(f"VERDICT {name}: NO TRADES -> KILL (events < 30)"); return
    ok = (d["mean_bp"] >= 8.0) and (d["t"] >= 2) and (d["median_bp"] > 0) and d["same_sign"] and d["n"] >= 30
    log(f"VERDICT {name}: {'PASS' if ok else 'KILL'}  "
        f"(net1x={d['mean_bp']:.2f}bp {'>=' if d['mean_bp']>=8 else '<'} 8bp gate; "
        f"clus_t={d['t']:.2f}; median={d['median_bp']:.2f}; same_sign={d['same_sign']}; n={d['n']})")


def main():
    idx, o, c, prem, flow, nav, px = build()
    log("Study BSPD: bond-SPDR premium/discount + creation-flow reversion")
    log(f"universe: {' '.join(UNIV)}")
    for t in HDRS:
        j = nav[t].join(px[t], how="inner")
        log(f"  {t}: nav {nav[t].index.min().date()}..{nav[t].index.max().date()} "
            f"n_nav={len(nav[t])} px {px[t].index.min().date()}..{px[t].index.max().date()} "
            f"n_px={len(px[t])} so_changes={int((nav[t].so.diff().fillna(0)!=0).sum())}")
    log(f"pooled price index {idx.min().date()}..{idx.max().date()} rows={len(idx)}")
    log(f"premium obs: {prem.notna().sum().to_dict()}")
    log(f"flow obs: {flow.notna().sum().to_dict()}")

    log("\n### H1 discount reversion (long most-discounted)")
    for h in (1, 5):
        tr = h1_trades(idx, o, prem, h)
        d = report_spread(f"H1 h={h}", tr)
        if d:
            verdict(f"H1 h={h} mkt-adj net_1x", d[("mkt-adj", 1)][0])
            verdict(f"H1 h={h} vs-top net_1x", d[("vs-top", 1)][0])

    log("\n### H2 creation flow (long top-quintile creation, 1-day hold)")
    tr = h2_trades(idx, o, flow, h=1)
    if len(tr):
        log(f"flow signal mean {tr.flow.mean():.4f} median {tr.flow.median():.4f}")
    d = report_spread("H2", tr)
    if d:
        verdict("H2 mkt-adj net_1x", d[("mkt-adj", 1)][0])

    log("\n### H2 by direction (descriptive)")
    for label, side in (("creation-top", 1), ("redemption-bottom", -1)):
        tr = h2_trades(idx, o, flow * side, h=1)
        if len(tr):
            stats(f"H2 {label} long-only", tr.r_long - 2 * 2 / 1e4, tr.entry)

    with open(OUT, "w") as f:
        f.write("\n".join(_lines) + "\n")
    log(f"\nwritten {OUT}")


if __name__ == "__main__":
    import os
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    main()
