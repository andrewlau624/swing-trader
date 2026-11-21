"""PREF-SIB (N 1240, pre-registered in round1_prose.md "Amendment - EXP round 6", 2026-11-21): same-issuer
preferred / baby-bond sibling dislocation. J1 = Sharadar daily closes 2015-01..2020-12.

    PYTHONPATH=. python3 -m research.sim.exp_prefsib map     # issuer mapping + panel only (no returns)
    PYTHONPATH=. python3 -m research.sim.exp_prefsib         # J1 judge -> exp_prefsib_out.txt

Universe. Sharadar SEP 'Domestic/ADR/Canadian Preferred Stock' + SFP 'CEF Preferred' (group PREF) and SFP 'ETD'
(group ETD = exchange-traded debt / baby bonds). PREF and ETD of one issuer are never siblings of each other.

Issuer mapping (frozen before any return was read). Key = (group, normalised tickers.name), where normalisation
upper-cases, strips punctuation, a leading THE and trailing legal suffixes (INC, CORP, CO, LLC, LP, LTD, PLC, NV, SA,
AG, HOLDING(S)). Sharadar's `name` is the issuer of that security (current name, carried back on predecessor tickers),
so it is used instead of the ticker root (roots are reused: RPT-PD = RPT Realty vs RPT-PC = Rithm Property Trust) and
instead of `relatedtickers` (which chains in predecessors and merger partners, e.g. NSAM under DBRG). permaticker is
per security, not per issuer, so it cannot group. Separately-named vehicles stay separate (e.g. 'MORGAN STANLEY CAPITAL
TRUST VIII' trust preferreds vs 'MORGAN STANLEY' notes; 'ENTERGY ARKANSAS LLC' vs other Entergy subsidiaries): a
different legal issuer is a different credit / seniority. Sharadar has no security-level description (descriptions.parquet
is field metadata only), so seniority inside a group (senior vs subordinated notes, cumulative vs not) is NOT separable.

Signal at close T (series i, sibling set = other series of the same key that are live on T):
  live    = bar on T and on T-5 (calendar sessions), 20d median $vol (closeunadj x volume, through T-1) >= $100k
  tr5     = 5-session total return, closeunadj + cash dividends on their ex-dates (actions.parquet)
  res     = tr5_i - median(tr5_j, j live sibling); needs >= 1 live sibling
  z       = res / sd(res over sessions T-60..T-1, >= 40 valid); fire z <= -2
Exclusions: own ex-date in sessions T-1..T+6 (T-1..T+2 registered + any ex-date inside the hold), closeunadj(T) > 25.75.
Trade: buy close T+1, sell close T+6 (+ any dividend ex in (T+1, T+6]); no re-entry in a series while a position in it
is open (primary); all-signals reported as a sensitivity. 10bp/side, shock 2x.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import sys

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from .program_books import dsr

S = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).with_name("exp_prefsib_out.txt")
PREF_CAT = ["Domestic Preferred Stock", "ADR Preferred Stock", "Canadian Preferred Stock"]
SIDE = 10e-4
ADV, CAP, ZT, LB, MINP = 1e5, 25.75, 2.0, 60, 40
J1 = ("2015-01-01", "2020-12-31")
N_PROGRAM = 1241
SUF = r" (INC|CORP|CORPORATION|CO|COMPANY|LLC|LP|L P|LTD|PLC|NV|N V|SA|AG|HOLDINGS?)$"


def norm(s: str) -> str:
    s = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", str(s).upper())).strip()
    s = re.sub(r"^THE ", "", s)
    while (s2 := re.sub(SUF, "", s)) != s:
        s = s2
    return s


def universe() -> pd.DataFrame:
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "name", "category", "permaticker",
                                                             "firstpricedate", "lastpricedate", "isdelisted"]).to_pandas()
    u = t[((t.table == "SEP") & t.category.isin(PREF_CAT)) |
          ((t.table == "SFP") & t.category.isin(["ETD", "CEF Preferred"]))].copy()
    u["g"] = np.where(u.category == "ETD", "ETD", "PREF")
    u["key"] = u.g + "|" + u.name.map(norm)
    return u.reset_index(drop=True)


def bars(u: pd.DataFrame) -> pd.DataFrame:
    cols = ["ticker", "date", "closeunadj", "volume"]
    sep, sfp = u[u.table == "SEP"].ticker.tolist(), u[u.table == "SFP"].ticker.tolist()
    b = pd.concat([ds.dataset(S / "stocks.parquet").to_table(columns=cols, filter=ds.field("ticker").isin(sep)).to_pandas(),
                   ds.dataset(S / "funds.parquet").to_table(columns=cols, filter=ds.field("ticker").isin(sfp)).to_pandas()])
    b["date"] = pd.to_datetime(b.date)
    lim = u.set_index("ticker")[["firstpricedate", "lastpricedate"]].apply(pd.to_datetime)
    b = b.join(lim, on="ticker")
    b = b[(b.date >= b.firstpricedate) & (b.date <= b.lastpricedate) & (b.closeunadj > 0)]
    return b.drop(columns=["firstpricedate", "lastpricedate"]).drop_duplicates(["ticker", "date"])


def calendar() -> pd.DatetimeIndex:
    s = ds.dataset(S / "funds.parquet").to_table(columns=["date"], filter=ds.field("ticker") == "SPY").to_pandas()
    return pd.DatetimeIndex(sorted(pd.to_datetime(s.date).unique()))


def actions(tk: list[str]):
    a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker", "value"],
                                                   filter=ds.field("ticker").isin(tk)).to_pandas()
    a["date"] = pd.to_datetime(a.date)
    dv = a[a.action == "dividend"].groupby(["ticker", "date"]).value.sum()
    sp = set(a.loc[a.action == "split", "ticker"])
    return dv, sp


def panel(u, b, cal, dv):
    """Wide (session x ticker) matrices on the SPY calendar."""
    b = b[b.date.isin(cal)].copy()
    b["div"] = dv.reindex(pd.MultiIndex.from_arrays([b.ticker, b.date])).fillna(0.0).to_numpy()
    b = b.sort_values(["ticker", "date"])
    g = b.groupby("ticker", sort=False)
    b["r"] = (b.closeunadj + b["div"]) / g.closeunadj.shift(1) - 1
    b["adv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    W = {c: b.pivot(index="date", columns="ticker", values=c).reindex(cal) for c in ("closeunadj", "r", "adv", "div")}
    # cumulative TR index along each series' own bars, then 5-session TR needs bars at T and T-5
    idx = (1 + W["r"].fillna(0.0)).cumprod().where(W["closeunadj"].notna())
    W["tr5"] = idx / idx.shift(5) - 1
    ex = pd.DataFrame(False, index=cal, columns=W["closeunadj"].columns)
    ex[:] = W["div"].fillna(0).to_numpy() > 0
    W["ex"] = ex
    return W


def signals(u, W):
    key = u.set_index("ticker").key
    tk = [c for c in W["tr5"].columns if c in key.index]
    live = W["tr5"][tk].notna() & (W["adv"][tk] >= ADV)
    tr5 = W["tr5"][tk].where(live)
    Z = pd.DataFrame(np.nan, index=tr5.index, columns=tk)
    NS = pd.DataFrame(0, index=tr5.index, columns=tk)
    for k, cols in pd.Series(tk).groupby(key.reindex(tk).to_numpy()):
        cols = list(cols)
        if len(cols) < 2:
            continue
        m = tr5[cols].to_numpy()
        for j, c in enumerate(cols):
            oth = np.delete(m, j, axis=1)
            n = np.isfinite(oth).sum(1)
            with np.errstate(all="ignore"):
                med = np.where(n > 0, np.nanmedian(np.where(n[:, None] > 0, oth, 0.0), axis=1), np.nan)
            res = pd.Series(np.where(n > 0, m[:, j] - med, np.nan), index=tr5.index)
            sd = res.shift(1).rolling(LB, min_periods=MINP).std()
            Z[c] = res / sd
            NS[c] = n
    return Z, NS


def trades(Z, W, fire, label, overlap=False):
    """fire: boolean frame (session x ticker) of signal days T. Returns one row per trade."""
    cal = Z.index
    px, ex = W["closeunadj"][Z.columns].to_numpy(), W["ex"][Z.columns].to_numpy()
    dvm = W["div"][Z.columns].fillna(0).to_numpy()
    F = fire.to_numpy()
    rows = []
    n_ex = n_cap = n_miss = 0
    for j, c in enumerate(Z.columns):
        last_exit = -1
        for i in np.flatnonzero(F[:, j]):
            if i + 6 >= len(cal) or i < 1:
                continue
            if ex[i - 1:i + 7, j].any():
                n_ex += 1; continue
            if px[i, j] > CAP:
                n_cap += 1; continue
            if not np.isfinite(px[i + 1, j]):
                n_miss += 1; continue
            if not overlap and i + 1 <= last_exit:
                continue
            seg = px[i + 2:i + 7, j]
            ok = np.flatnonzero(np.isfinite(seg))
            if not len(ok):
                n_miss += 1; continue
            e = i + 2 + ok[-1]
            gross = (px[e, j] + dvm[i + 2:e + 1, j].sum()) / px[i + 1, j] - 1
            rows.append((c, cal[i], cal[i + 1], cal[e], gross, e != i + 6))
            last_exit = e
    t = pd.DataFrame(rows, columns=["t", "T", "d_in", "d_out", "gross", "short_exit"])
    t["net"] = t.gross - 2 * SIDE
    t["net2"] = t.gross - 4 * SIDE
    t.attrs.update(label=label, n_ex=n_ex, n_cap=n_cap, n_miss=n_miss)
    return t


def tday(x, col="net", by="T"):
    d = x.groupby(by)[col].mean()
    return d.mean() / d.std() * np.sqrt(len(d)) if len(d) > 2 else np.nan


def line(x, col="net"):
    if not len(x):
        return "n     0"
    wk = x.assign(w=x.d_in.dt.to_period("W")).groupby("w")[col].mean()
    tw = wk.mean() / wk.std() * np.sqrt(len(wk)) if len(wk) > 2 else np.nan
    return (f"n {len(x):5d} mean {x[col].mean()*1e4:+7.1f} med {x[col].median()*1e4:+7.1f} hit {(x[col]>0).mean():.2f} "
            f"t(day) {tday(x, col):+5.2f} t(week) {tw:+5.2f}")


def ex_top_issuers(x, key, k=5):
    s = x.assign(i=x.t.map(key)).groupby("i").net.sum().sort_values(ascending=False)
    keep = x[~x.t.map(key).isin(s.index[:k])]
    return keep.net.mean(), list(s.index[:k])


def sha():
    return hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()


def main_map():
    u = universe()
    b = bars(u)
    cal = calendar()
    dv, sp = actions(u.ticker.tolist())
    W = panel(u, b, cal, dv)
    key = u.set_index("ticker").key
    j1 = (W["closeunadj"].index >= J1[0]) & (W["closeunadj"].index <= J1[1])
    live = (W["tr5"].notna() & (W["adv"] >= ADV))[j1]
    lk = live.T.groupby(key.reindex(live.columns).to_numpy()).sum().T        # live series per key per day
    multi = (lk >= 2).any()
    print(f"universe {len(u)} securities, {u.key.nunique()} keys; J1 keys with >=2 live series on some day: {int(multi.sum())} "
          f"(PREF {int(multi[multi.index.str.startswith('PREF')].sum())}, ETD {int(multi[multi.index.str.startswith('ETD')].sum())})")
    print(f"securities with a split action: {len(sp)} ({sorted(sp)[:20]})")
    act = live.any()
    ku = u[u.ticker.isin(act[act].index)]
    roots = ku[ku.g == "PREF"].assign(r=lambda d: d.ticker.str.split("-").str[0]).groupby("r").key.nunique()
    print("PREF ticker roots mapped to >1 key among J1-live series:")
    print(ku[ku.g == "PREF"].assign(r=lambda d: d.ticker.str.split("-").str[0]).query("r in @roots[@roots>1].index")[
        ["ticker", "name", "key", "firstpricedate", "lastpricedate"]].sort_values("ticker").to_string())
    top = lk.max().sort_values(ascending=False)
    print("\nlargest J1 groups (max live series on one day):")
    for k in list(top.index[:15]) + [k for k in top.index if k.startswith("ETD")][:10]:
        tks = sorted(u.loc[u.key == k, "ticker"])
        print(f"  {k:55s} max-live {int(top[k]):2d}  {' '.join(tks)[:150]}")
    return u, top


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "map":
        main_map(); return
    L = [f"PREF-SIB (N 1240) J1 {J1[0]}..{J1[1]}   code sha256 {sha()}", ""]
    print(L[0], flush=True)
    u = universe()
    b = bars(u)
    cal = calendar()
    dv, sp = actions(u.ticker.tolist())
    W = panel(u, b, cal, dv)
    Z, NS = signals(u, W)
    key = u.set_index("ticker").key
    grp = u.set_index("ticker").g
    # split names: drop the series entirely (no split-safe TR here); none expected in prefs
    Z = Z.drop(columns=[c for c in Z.columns if c in sp])
    inj = (Z.index >= J1[0]) & (Z.index <= J1[1])
    zj = Z.where(pd.DataFrame(np.repeat(inj[:, None], Z.shape[1], 1), index=Z.index, columns=Z.columns))
    prim = trades(Z, W, zj <= -ZT, "z<=-2")
    allsig = trades(Z, W, zj <= -ZT, "all signals", overlap=True)
    mirror = trades(Z, W, zj >= ZT, "mirror z>=+2")
    J = pd.DataFrame(np.repeat(inj[:, None], Z.shape[1], 1), index=Z.index, columns=Z.columns)
    plac = trades(Z, W, (Z.shift(30) <= -ZT) & J, "placebo z(T-30)<=-2")
    p = prim
    L.append(f"universe {len(u)} securities / {u.key.nunique()} issuer keys; series with a valid z in J1: "
             f"{int(zj.notna().any().sum())} in {key.reindex(Z.columns[zj.notna().any()]).nunique()} keys")
    L.append(f"primary signals excluded: ex-date T-1..T+6 {p.attrs['n_ex']}, price>{CAP} {p.attrs['n_cap']}, "
             f"no T+1/exit bar {p.attrs['n_miss']}; short exits (series stopped before T+6) {int(p.short_exit.sum())}")
    L.append(f"issuers traded {p.t.map(key).nunique()}, series {p.t.nunique()}; PREF {int((p.t.map(grp)=='PREF').sum())} "
             f"/ ETD {int((p.t.map(grp)=='ETD').sum())} trades; trades/yr {len(p)/6:.0f}")
    L.append("")
    L.append("J1 primary (net = gross - 20bp RT):")
    L.append(f"  net    {line(p)}")
    L.append(f"  gross  {line(p, 'gross')}")
    L.append(f"  2x cost{line(p, 'net2')}")
    h1, h2 = p[p['T'].dt.year <= 2017], p[p['T'].dt.year >= 2018]
    L.append(f"  2015-17 {line(h1)}")
    L.append(f"  2018-20 {line(h2)}")
    xt, top5 = ex_top_issuers(p, key)
    L.append(f"  ex-top-5 issuers mean {xt*1e4:+.1f}bp  (dropped {top5})")
    for y, x in p.groupby(p['T'].dt.year):
        L.append(f"    {y} {line(x)}")
    L.append("")
    L.append("Controls / sensitivities (same exclusions, same trade):")
    for t in (mirror, plac, allsig):
        L.append(f"  {t.attrs['label']:22s} {line(t)}")
    m20 = (p['T'] >= "2020-03-01") & (p['T'] <= "2020-03-31")
    L.append(f"  March 2020 only        {line(p[m20])}")
    L.append(f"  ex-March 2020          {line(p[~m20])}")
    for gname in ("ETD", "PREF"):
        x = p[p.t.map(grp) == gname]
        L.append(f"  {gname}-only arm          {line(x)}")
    L.append(f"  by sibling count (1 / 2-3 / 4+):")
    nsib = pd.Series([NS.at[r.T, r.t] for r in p.itertuples()], index=p.index)
    for lab, msk in (("1", nsib == 1), ("2-3", nsib.between(2, 3)), ("4+", nsib >= 4)):
        L.append(f"    {lab:4s} {line(p[msk])}")
    day = p.groupby("T").net.mean()
    D = dsr(day, n_trials=N_PROGRAM)
    L.append(f"  DSR(N {N_PROGRAM}) on signal-day mean net: {D['dsr']:.3f}  (T {D['T']}, t {D['t']:+.2f}, skew {D['skew']:+.2f})")
    L.append("")
    gates = {
        "net >= +40bp": p.net.mean() >= 40e-4,
        "2x cost > 0": p.net2.mean() > 0,
        "median > 0": p.net.median() > 0,
        "t(day) >= 2.5": tday(p) >= 2.5,
        "both halves > 0": h1.net.mean() > 0 and h2.net.mean() > 0,
        "ex-top-5 issuers > 0": xt > 0,
        "mirror mean lower": mirror.net.mean() < p.net.mean(),
        "placebo mean lower": plac.net.mean() < p.net.mean(),
    }
    for k, v in gates.items():
        L.append(f"  gate {k:22s} {'PASS' if v else 'FAIL'}")
    verdict = "PASS -> J3" if all(gates.values()) else "KILL (J1 fails; J3 not run)"
    L.append(f"J1 verdict: {verdict}")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L[1:]))


if __name__ == "__main__":
    main()
