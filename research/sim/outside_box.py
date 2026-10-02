"""Round 30 (outside the box). Every part reads SELECT data only (cut at 2023-12-31 on load). Nothing
survived exploration, so nothing was registered and 2024-26 was never read (study_outside_box_round30.md).

    PYTHONPATH=. .venv/bin/python -m research.sim.outside_box explore | explore2 | explore3 [loc]

Output: data/research/program/outside_box_<part>_out.txt
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
NIGHT = ROOT / "data/research/night"
SEL_END = pd.Timestamp("2023-12-31")


def out(part):
    f = open(ROOT / f"data/research/program/outside_box_{part}_out.txt", "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def panel(end=SEL_END):
    P = pd.read_pickle(NIGHT / "panel.pkl")
    return {k: v.loc[:end] for k, v in P.items()}


def picks(end=SEL_END):
    T = pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl")
    T = T[(T.d >= "2021-01-01") & (T.d <= end) & T.ok].copy()
    T["x"] = T.ret_auc - T.groupby("d").ret_auc.transform("mean")      # within-night (what a tilt can earn)
    T["n"] = T.groupby("d").sym.transform("count")
    return T[T.n >= 2]


def tercile_look(log, T, col, lab):
    X = T.dropna(subset=[col]).copy()
    X["q"] = X.groupby("d")[col].rank(pct=True)
    X["t"] = pd.cut(X.q, [0, 1 / 3, 2 / 3, 1], labels=["lo", "mid", "hi"], include_lowest=True)
    for yrs in (("2021", "2022"), ("2023", "2023")):
        g = X[(X.d >= yrs[0]) & (X.d <= yrs[1] + "-12-31")].groupby("t", observed=True).x.agg(["mean", "count"])
        log(f"  {lab} {yrs[0]}-{yrs[1]} within-night bp by tercile: " + "  ".join(
            f"{k} {r['mean']*1e4:+.1f} (n {int(r['count'])})" for k, r in g.iterrows()))
    return X


# ---------------------------------------------------------------- #5 trade size, #10 exchange, #7 lockup
def look_pick_tilts(log):
    T = picks(); P = panel()
    V, N, C = P["volume"], P["trade_count"], P["close"]
    ats = (V.rolling(20, min_periods=10).sum() / N.rolling(20, min_periods=10).sum())
    ats_d = V / N
    dv = C * V
    pos = {d: i for i, d in enumerate(C.index)}
    def get(F, d, s):
        try:
            return float(F.at[d, s])
        except KeyError:
            return np.nan
    T["ats20"] = [np.log(get(ats, d, s) * get(C, d, s)) for d, s in zip(T.d, T.sym)]  # $ per trade
    T["ats0"] = [np.log(get(ats_d, d, s) * get(C, d, s)) for d, s in zip(T.d, T.sym)]
    log(f"#5 trade size: {T.ats20.notna().sum()}/{len(T)} picks have trade_count")
    tercile_look(log, T, "ats20", "#5 $/trade 20d")
    tercile_look(log, T, "ats0", "#5 $/trade today")
    meta = json.load(open(NIGHT / "asset_meta.json"))
    T["exch"] = [meta.get(s, {}).get("exchange", "?") for s in T.sym]
    for yrs in (("2021", "2022"), ("2023", "2023")):
        g = T[(T.d >= yrs[0]) & (T.d <= yrs[1] + "-12-31")].groupby("exch").x.agg(["mean", "count"])
        log(f"#10 exchange {yrs[0]}-{yrs[1]} within-night bp: " + "  ".join(
            f"{k} {r['mean']*1e4:+.1f} (n {int(r['count'])})" for k, r in g.iterrows()))
    # lockup: first session with volume in the panel (panel starts 2020-10-01: only names first seen after 2020-11)
    first = (V.fillna(0) > 0).idxmax()
    first = first[first > pd.Timestamp("2020-11-01")]
    T["age"] = [(pos[d] - pos[first[s]]) if s in first.index else np.nan for d, s in zip(T.d, T.sym)]
    T["cal_age"] = [((d - first[s]).days) if s in first.index else np.nan for d, s in zip(T.d, T.sym)]
    lk = T.cal_age.between(173, 190)
    log(f"#7 lockup window (first trade + 173..190 calendar days): {lk.sum()} picks; within-night "
        f"{T[lk].x.mean()*1e4:+.1f}bp (2021-22 {T[lk & (T.d < '2023')].x.mean()*1e4:+.1f}, 2023 {T[lk & (T.d >= '2023')].x.mean()*1e4:+.1f}); "
        f"other young (<400d) {T[(T.cal_age < 400) & ~lk].x.mean()*1e4:+.1f}bp n {((T.cal_age < 400) & ~lk).sum()}")
    T.to_pickle(ROOT / "data/research/program/outside_box_picks_sel.pkl")


# ---------------------------------------------------------------- #4 wash-sale day 31
def look_wash(log):
    P = panel(); C, V, O = P["close"], P["volume"], P["open"]
    dv = (C * V)
    r = C.pct_change(fill_method=None)
    adv = dv.rolling(20, min_periods=15).mean().shift(1)
    cal = C.index
    # event: a -15% day (or worse) on >= 3x dollar volume, liquid (adv >= $5M), price >= $3
    ev = (r <= -0.15) & (dv >= 3 * adv) & (adv >= 5e6) & (C.shift(1) >= 3)
    E = ev.stack(); E = E[E].index.tolist()
    log(f"#4 wash-sale events (<=-15% on >=3x $vol, adv>=$5M): {len(E)} in {cal[0].date()}..{cal[-1].date()}")
    rows = []
    cols = {s: j for j, s in enumerate(C.columns)}
    Cv, Ov = C.values, O.values
    spy = C["SPY"].values; spyo = O["SPY"].values
    for d, s in E:
        i = cal.get_loc(d); j = cols[s]
        tgt = d + pd.Timedelta(days=31)
        k = cal.searchsorted(tgt)                 # first session on/after day 31
        if k + 3 >= len(cal):
            continue
        for off in range(-6, 4):                  # sessions around day-31 session k
            a = k + off
            c0, c1 = Cv[a - 1, j], Cv[a, j]
            if np.isfinite(c0) and np.isfinite(c1) and c0 > 0:
                rows.append((d, s, off, c1 / c0 - 1 - (spy[a] / spy[a - 1] - 1),
                             Ov[a, j] / c0 - 1 - (spyo[a] / spy[a - 1] - 1)))
    X = pd.DataFrame(rows, columns=["d", "sym", "off", "ex", "exon"])
    X = X[X.ex.abs() < 0.5]
    g = X.groupby("off").agg(ex=("ex", "mean"), exon=("exon", "mean"), n=("ex", "count"))
    log("#4 excess vs SPY by session offset from the first session >= day 31 (0 = that session), bp: close-close | overnight")
    for off, rr in g.iterrows():
        log(f"   {off:+d}: {rr.ex*1e4:+6.1f} | {rr.exon*1e4:+6.1f}   n {int(rr.n)}")
    for lab, m in (("2020-22", X.d < "2023-01-01"), ("2023", X.d >= "2023-01-01")):
        y = X[m]
        log(f"   {lab}: day0 {y[y.off == 0].ex.mean()*1e4:+.1f}bp, days -2..0 {y[y.off.between(-2, 0)].ex.mean()*1e4:+.1f}, "
            f"days -6..-3 {y[y.off.between(-6, -3)].ex.mean()*1e4:+.1f}, days 1..3 {y[y.off.between(1, 3)].ex.mean()*1e4:+.1f}")
    # only events in Nov-Dec, when tax-loss motive is strongest, vs others
    nd = X.d.dt.month.isin([10, 11, 12])
    log(f"   Oct-Dec events day 0 {X[nd & (X.off == 0)].ex.mean()*1e4:+.1f}bp n {int((nd & (X.off == 0)).sum())}; "
        f"other months {X[~nd & (X.off == 0)].ex.mean()*1e4:+.1f}bp")


# ---------------------------------------------------------------- #6 the $5 cliff
def look_five(log):
    R = pd.read_parquet(NIGHT / "raw_close.parquet")
    R = R[R.date <= SEL_END]
    rc = R.pivot(index="date", columns="symbol", values="raw_close")
    ac = R.pivot(index="date", columns="symbol", values="adj_close")
    ao = R.pivot(index="date", columns="symbol", values="adj_open")
    P = panel(); spy = P["close"]["SPY"].reindex(ac.index); spyo = P["open"]["SPY"].reindex(ac.index)
    above20 = (rc.shift(1) >= 5).rolling(20).sum() == 20
    for lab, ev in (("cross below $5 after 20 sessions >= $5", above20 & (rc < 5) & (rc >= 4)),
                    ("cross above $5 after 20 sessions < $5", ((rc.shift(1) < 5).rolling(20).sum() == 20) & (rc >= 5) & (rc < 6))):
        E = ev.stack(); E = E[E].index
        rows = []
        idx = {d: i for i, d in enumerate(ac.index)}
        A, Ao, S, So = ac.values, ao.values, spy.values, spyo.values
        cols = {s: j for j, s in enumerate(ac.columns)}
        for d, s in E:
            i, j = idx[d], cols[s]
            if i + 10 >= len(ac):
                continue
            c0 = A[i, j]
            on = Ao[i + 1, j] / c0 - 1 - (So[i + 1] / S[i] - 1)
            r1 = A[i + 1, j] / c0 - 1 - (S[i + 1] / S[i] - 1)
            r5 = A[i + 5, j] / c0 - 1 - (S[i + 5] / S[i] - 1)
            r10 = A[i + 10, j] / c0 - 1 - (S[i + 10] / S[i] - 1)
            rows.append((d, s, on, r1, r5, r10))
        X = pd.DataFrame(rows, columns=["d", "sym", "on", "r1", "r5", "r10"]).dropna()
        X = X[X.r10.abs() < 1]
        log(f"#6 {lab}: n {len(X)}; excess vs SPY bp: overnight {X.on.mean()*1e4:+.1f}  1d {X.r1.mean()*1e4:+.1f}  "
            f"5d {X.r5.mean()*1e4:+.1f}  10d {X.r10.mean()*1e4:+.1f} (median 5d {X.r5.median()*1e4:+.1f})")
        for yl, m in (("2020-22", X.d < "2023"), ("2023", X.d >= "2023")):
            y = X[m]
            log(f"     {yl}: n {len(y)} overnight {y.on.mean()*1e4:+.1f} 1d {y.r1.mean()*1e4:+.1f} 5d {y.r5.mean()*1e4:+.1f} 10d {y.r10.mean()*1e4:+.1f}")
    # placebo threshold: same construction at $7 and $4
    for thr in (4.0, 7.0):
        ev = ((rc.shift(1) >= thr).rolling(20).sum() == 20) & (rc < thr) & (rc >= thr * 0.8)
        E = ev.stack(); E = E[E].index
        r5 = []
        idx = {d: i for i, d in enumerate(ac.index)}; cols = {s: j for j, s in enumerate(ac.columns)}
        A, S = ac.values, spy.values
        for d, s in E:
            i, j = idx[d], cols[s]
            if i + 5 < len(ac) and np.isfinite(A[i + 5, j]) and np.isfinite(A[i, j]):
                r5.append(A[i + 5, j] / A[i, j] - 1 - (S[i + 5] / S[i] - 1))
        r5 = np.array(r5); r5 = r5[np.abs(r5) < 1]
        log(f"#6 placebo cross below ${thr:.0f}: n {len(r5)} 5d excess {r5.mean()*1e4:+.1f}bp")


# ---------------------------------------------------------------- #1-3 anchored twins
CLASSES = [("FOX", "FOXA"), ("NWS", "NWSA"), ("BF.A", "BF.B"), ("UA", "UAA"), ("ZG", "Z"), ("FWONA", "FWONK"),
           ("BATRA", "BATRK"), ("HEI.A", "HEI"), ("LEN.B", "LEN"), ("PBR.A", "PBR"), ("GEF.B", "GEF"),
           ("RUSHB", "RUSHA"), ("MOG.B", "MOG.A"), ("LILA", "LILAK"), ("MKC.V", "MKC"), ("GOOG", "GOOGL"),
           ("BRK.A", "BRK.B"), ("CRD.B", "CRD.A"), ("HVT.A", "HVT"), ("BH.A", "BH"), ("KELYB", "KELYA")]
CLONES = [("IAU", "GLD"), ("GLDM", "GLD"), ("SGOL", "GLD"), ("BAR", "GLD"), ("AAAU", "GLD"), ("OUNZ", "GLD"),
          ("SPLG", "SPY"), ("IVV", "SPY"), ("VOO", "SPY"), ("QQQM", "QQQ"), ("SPTL", "TLT"), ("VGLT", "TLT"),
          ("SGOV", "BIL"), ("TBIL", "BIL"), ("XBIL", "BIL"), ("VTWO", "IWM"), ("SIVR", "SLV"), ("SCHB", "VTI"),
          ("ITOT", "VTI"), ("SCHX", "SPY"), ("BBUS", "SPY"), ("SPYG", "IVW"), ("SPYV", "IVE"), ("SPMD", "IJH"),
          ("SPSM", "IJR"), ("SCHA", "VB"), ("VUG", "SCHG"), ("ESGU", "SUSA"), ("IEMG", "VWO"), ("SCHE", "VWO"),
          ("IEFA", "VEA"), ("SCHF", "VEA"), ("BNDX", "IAGG"), ("AGG", "BND"), ("SCHZ", "BND"), ("SPAB", "BND"),
          ("VCIT", "IGIB"), ("SPIB", "IGIB"), ("SHY", "VGSH"), ("SCHO", "VGSH"), ("IEI", "VGIT"), ("SCHR", "VGIT"),
          ("BITB", "IBIT")]
LETFS = [("DRN", "XLRE", 3), ("CURE", "XLV", 3), ("NAIL", "ITB", 3), ("DFEN", "ITA", 3), ("RETL", "XRT", 3),
         ("UTSL", "XLU", 3), ("MIDU", "MDY", 3), ("TPOR", "IYT", 3), ("PILL", "XPH", 3), ("DUSL", "XLI", 3),
         ("WANT", "XLY", 3), ("HIBL", "SPHB", 3), ("DPST", "KRE", 3), ("ERX", "XLE", 2), ("UYG", "XLF", 2),
         ("ROM", "XLK", 2), ("UCC", "XLY", 2), ("UXI", "XLI", 2), ("RXL", "XLV", 2), ("UPW", "XLU", 2),
         ("URE", "XLRE", 2), ("SAA", "IJR", 2), ("MVV", "MDY", 2), ("UWM", "IWM", 2), ("QLD", "QQQ", 2),
         ("SSO", "SPY", 2), ("DDM", "DIA", 2), ("USD", "SMH", 2), ("UGE", "XLP", 2), ("UYM", "XLB", 2),
         ("BIB", "IBB", 2), ("TNA", "IWM", 3), ("SOXL", "SOXX", 3), ("TECL", "XLK", 3), ("FAS", "XLF", 3),
         ("LABU", "XBI", 3), ("UDOW", "DIA", 3), ("UPRO", "SPY", 3), ("TQQQ", "QQQ", 3), ("SPXL", "SPY", 3)]


def twin_rows(P, a, b, L=1.0, kind="class", look=60):
    """a = the thinner/cheap side we may buy, b = anchor. Residual of a's close vs its anchor; next-session reversion."""
    C, O, V = P["close"], P["open"], P["volume"]
    if a not in C or b not in C:
        return None
    ca, cb, oa, ob = C[a], C[b], O[a], O[b]
    dva = (ca * V[a]).rolling(20, min_periods=15).mean()
    if kind == "class":
        lr = np.log(ca / cb)
        z = (lr - lr.rolling(look, min_periods=40).mean().shift(1)) / lr.diff().rolling(look, min_periods=40).std().shift(1)
        dev = lr - lr.rolling(look, min_periods=40).mean().shift(1)
    else:
        res = ca.pct_change(fill_method=None) - L * cb.pct_change(fill_method=None)
        sd = res.rolling(look, min_periods=40).std().shift(1)
        z = res / sd; dev = res
    # next-session outcomes for buying a at today's close: a's overnight / close-close minus L x anchor's
    on = (oa.shift(-1) / ca - 1) - L * (ob.shift(-1) / cb - 1)
    cc = (ca.shift(-1) / ca - 1) - L * (cb.shift(-1) / cb - 1)
    raw_on = oa.shift(-1) / ca - 1
    raw_cc = ca.shift(-1) / ca - 1
    df = pd.DataFrame({"z": z, "dev": dev, "on": on, "cc": cc, "raw_on": raw_on, "raw_cc": raw_cc, "dva": dva})
    df["pair"] = f"{a}/{b}"; df["kind"] = kind
    return df.dropna()


def look_twins(log):
    P = panel()
    allr = []
    for fam, lst in (("class", [(a, b, 1.0) for a, b in CLASSES]), ("clone", [(a, b, 1.0) for a, b in CLONES]),
                     ("letf", LETFS)):
        for a, b, L in lst:
            # for share classes, test both directions (either class can be the cheap one)
            sides = [(a, b), (b, a)] if fam == "class" else [(a, b)]
            for x, y in sides:
                d = twin_rows(P, x, y, L, "class" if fam == "class" else fam)
                if d is not None and len(d):
                    d["fam"] = fam
                    allr.append(d)
    X = pd.concat(allr)
    X = X[(X.on.abs() < 0.2) & (X.cc.abs() < 0.2)]
    X["yr"] = X.index.year
    log(f"#1-3 twins: {X.pair.nunique()} pair-sides, {len(X)} rows (2020-11..2023-12)")
    for fam in ("class", "clone", "letf"):
        Y = X[X.fam == fam]
        for thr in (1.5, 2.0, 3.0):
            s = Y[Y.z <= -thr]
            if not len(s):
                continue
            log(f"  {fam} z<=-{thr}: n {len(s)} pairs {s.pair.nunique()}; next overnight rel {s.on.mean()*1e4:+.1f}bp "
                f"(med {s.on.median()*1e4:+.1f}); next close rel {s.cc.mean()*1e4:+.1f}bp; raw long cc {s.raw_cc.mean()*1e4:+.1f}; "
                f"2020-22 / 2023 cc {s[s.yr <= 2022].cc.mean()*1e4:+.1f} / {s[s.yr == 2023].cc.mean()*1e4:+.1f}")
        # slope of next-day relative return on today's deviation (all days)
        b = np.polyfit(Y.dev.clip(-0.2, 0.2), Y.cc, 1)[0]
        log(f"  {fam}: slope of next close-close rel return on today's deviation: {b:+.3f} (−1 = full reversal)")
    Y = X[(X.fam != "letf") & (X.z <= -2)]
    by = Y.groupby("pair").agg(n=("cc", "count"), cc=("cc", "mean"), on=("on", "mean"), dva=("dva", "median"))
    by = by[by.n >= 5].sort_values("cc")
    log("  per pair (z<=-2, n>=5): pair n cc_bp on_bp ADV$M")
    for p, r in by.iterrows():
        log(f"    {p:12s} {int(r.n):4d} {r.cc*1e4:+7.1f} {r.on*1e4:+7.1f} {r.dva/1e6:8.1f}")
    X.to_pickle(ROOT / "data/research/program/outside_box_twins_sel.pkl")


# ---------------------------------------------------------------- #9 sympathy losers
def look_sympathy(log):
    """Peers (same 4-digit SIC, EDGAR cache) of a stock that fell <= -15% today, themselves down 3-8% (not in the night
    pool), liquid; next overnight / next close excess vs SPY, vs non-peer stocks with the same day return band."""
    import glob, pickle
    sic = {}
    for f in glob.glob(str(NIGHT / "edgar/*.pkl")):
        try:
            x = pickle.load(open(f, "rb"))
        except Exception:
            continue
        sic[pathlib.Path(f).stem] = x.get("sic")
    tk = json.load(open(NIGHT / "edgar/ticker_cik.json"))                 # ticker -> cik
    s2sic = {t.upper().replace("-", "."): str(sic[str(c).zfill(10)]) for t, c in tk.items()
             if sic.get(str(c).zfill(10))}
    log(f"#9 sympathy: SIC for {len(s2sic)} tickers")
    P = panel(); C, O, V = P["close"], P["open"], P["volume"]
    syms = [s for s in s2sic if s in C.columns]
    C, O, V = C[syms], O[syms], V[syms]
    r = C.pct_change(fill_method=None)
    adv = (C * V).rolling(20, min_periods=15).mean().shift(1)
    spy_on = (P["open"]["SPY"].shift(-1) / P["close"]["SPY"] - 1)
    on = (O.shift(-1) / C - 1).sub(spy_on, axis=0)
    groups = pd.Series(s2sic).reindex(syms)
    rows = []
    for d in r.index[25:-1]:
        rd = r.loc[d]; ad = adv.loc[d]
        crash = rd[(rd <= -0.15) & (ad >= 5e6)].index
        if not len(crash):
            continue
        hit = set(groups[crash].values)
        band = rd[(rd <= -0.03) & (rd > -0.08) & (ad >= 5e6) & (C.loc[d] >= 5)].index
        for s in band:
            v = on.at[d, s]
            if np.isfinite(v) and abs(v) < 0.3:
                rows.append((d, s, groups[s] in hit and s not in crash, v))
    X = pd.DataFrame(rows, columns=["d", "sym", "peer", "on"])
    for lab, m in (("2020-22", X.d < "2023"), ("2023", X.d >= "2023")):
        y = X[m]
        log(f"#9 {lab}: peers of a crash (down 3-8%) next overnight excess {y[y.peer].on.mean()*1e4:+.1f}bp n {int(y.peer.sum())} "
            f"vs non-peers same band {y[~y.peer].on.mean()*1e4:+.1f}bp n {int((~y.peer).sum())}")


def look_twins2(log):
    """Second look: tradable sizes only (both sides 20d ADV >= $10M), vs each pair's own baseline (all days)."""
    X = pd.read_pickle(ROOT / "data/research/program/outside_box_twins_sel.pkl")
    P = panel(); C, V = P["close"], P["volume"]
    adv = (C * V).rolling(20, min_periods=15).mean()
    X["b"] = X.pair.str.split("/").str[1]
    X["adv_b"] = [adv.at[d, b] if b in adv else np.nan for d, b in zip(X.index, X.b)]
    Y = X[(X.dva >= 1e7) & (X.adv_b >= 1e7)].copy()
    base = Y.groupby("pair")[["on", "cc"]].transform("mean")
    Y["on_x"], Y["cc_x"] = Y.on - base.on, Y.cc - base.cc
    log(f"#1-3 liquid (both >= $10M ADV): {Y.pair.nunique()} pair-sides")
    for fam in ("class", "clone", "letf"):
        Z = Y[Y.fam == fam]
        for thr in (2.0, 3.0):
            s = Z[Z.z <= -thr]
            if not len(s):
                continue
            days = s.groupby(level=0).cc_x.mean()
            log(f"  {fam} z<=-{thr}: n {len(s)} ({len(days)} days, {s.pair.nunique()} pairs); vs pair baseline: next overnight "
                f"{s.on_x.mean()*1e4:+.1f}bp, next close {s.cc_x.mean()*1e4:+.1f}bp; by year cc "
                + " ".join(f"{y}:{v*1e4:+.1f}" for y, v in s.groupby(s.index.year).cc_x.mean().items())
                + f"; day-series t {days.mean()/days.std()*np.sqrt(len(days)):+.2f}")
        s = Z[Z.z >= 2.0]
        log(f"  {fam} z>=+2 (rich side, would be avoided): next close {s.cc_x.mean()*1e4:+.1f}bp n {len(s)}")


def look_trade_shares(log):
    T = pd.read_pickle(ROOT / "data/research/program/outside_box_picks_sel.pkl")
    T["sh_tr"] = T.ats20 - np.log(T.price)                    # log shares per trade (strip the price level)
    T["lp"] = np.log(T.price)
    log(f"#5 Spearman: log $/trade vs log price {T.ats20.corr(T.lp, method='spearman'):+.2f}; shares/trade vs price {T.sh_tr.corr(T.lp, method='spearman'):+.2f}")
    tercile_look(log, T, "sh_tr", "#5 shares/trade 20d")
    tercile_look(log, T, "lp", "#5 control: log price")


M1 = NIGHT / "twin_m1"


def m1_at(sym, years, hhmm):
    """Close of the minute bar starting at hh:mm ET, per session (select years only)."""
    fr = []
    for y in years:
        f = M1 / f"{sym}_{y}.parquet"
        if f.exists():
            x = pd.read_parquet(f)
            if len(x):
                fr.append(x)
    if not fr:
        return None
    x = pd.concat(fr)
    t = x.timestamp.dt.tz_convert("America/New_York")
    x = x[(t.dt.hour * 60 + t.dt.minute) <= hhmm]                 # last bar at or before hh:mm
    t = x.timestamp.dt.tz_convert("America/New_York")
    x = x.assign(d=t.dt.tz_localize(None).dt.normalize()).sort_values("timestamp")
    return x.groupby("d").close.last()


def letf_m1_table(P, years, hhmm, end=SEL_END):
    C, O, V = P["close"], P["open"], P["volume"]
    adv = (C * V).rolling(20, min_periods=15).mean()
    rows = []
    for a, b, L in LETFS:
        pa, pb = m1_at(a, years, hhmm), m1_at(b, years, hhmm)
        if pa is None or pb is None or a not in C or b not in C:
            continue
        ca, cb, oa, ob = C[a], C[b], O[a], O[b]
        res_close = ca.pct_change(fill_method=None) - L * cb.pct_change(fill_method=None)
        sd = res_close.rolling(60, min_periods=40).std().shift(1)
        df = pd.DataFrame({"pa": pa, "pb": pb}).reindex(C.index)
        res_dec = (df.pa / ca.shift(1) - 1) - L * (df.pb / cb.shift(1) - 1)           # known at hh:mm
        slip = (ca / df.pa - 1) - L * (cb / df.pb - 1)                                   # hh:mm -> cross
        on = (oa.shift(-1) / ca - 1) - L * (ob.shift(-1) / cb - 1)
        X = pd.DataFrame({"z": res_dec / sd, "res": res_dec, "slip": slip, "on": on,
                          "raw_on": oa.shift(-1) / ca - 1, "adv_a": adv[a].shift(1), "adv_b": adv[b].shift(1)})
        X["pair"] = f"{a}/{b}"
        rows.append(X.dropna())
    X = pd.concat(rows)
    X = X[(X.index <= end) & (X.on.abs() < 0.2)]
    X["base"] = X.groupby("pair").on.transform("mean")
    X["on_x"] = X.on - X.base
    return X


def look_twins_m1(log):
    P = panel()
    for hhmm, lab in ((15 * 60 + 45, "15:45"), (15 * 60 + 50, "15:50"), (15 * 60 + 55, "15:55"), (15 * 60 + 59, "15:59")):
        X = letf_m1_table(P, range(2020, 2024), hhmm)
        X = X[(X.adv_a >= 1e7) & (X.adv_b >= 1e7)]
        for thr in (2.0, 3.0):
            s = X[X.z <= -thr]
            days = s.groupby(level=0).on_x.mean()
            log(f"#1-3 L13 LETF decided at {lab}, z<=-{thr}: n {len(s)} ({len(days)} nights, {s.pair.nunique()} pairs); "
                f"cross -> next open vs pair baseline {s.on_x.mean()*1e4:+.1f}bp (raw long {s.raw_on.mean()*1e4:+.1f}); "
                f"decision->cross drift {s.slip.mean()*1e4:+.1f}bp; by year "
                + " ".join(f"{y}:{v*1e4:+.1f}" for y, v in s.groupby(s.index.year).on_x.mean().items())
                + f"; night-series t {days.mean()/days.std()*np.sqrt(len(days)):+.2f}")


def cross_prices(part):
    """{sym: (closing-cross Series, opening-cross Series)} from the twin auction cache (largest print per side)."""
    js = json.load(open(NIGHT / f"twin_auctions_{part}.json"))
    big = lambda l: max(l, key=lambda x: x.get("s", 0))["p"] if l else np.nan
    out = {}
    for sym, v in js.items():
        d = pd.to_datetime([x["d"] for x in v])
        out[sym] = (pd.Series([big(x.get("c", [])) for x in v], index=d), pd.Series([big(x.get("o", [])) for x in v], index=d))
    return out


def look_twins_cross(log):
    """L14: the 15:45 LETF signal with P&L on the official crosses (LETF leg) vs the panel's open/close."""
    P = panel(); X = letf_m1_table(P, range(2020, 2024), 15 * 60 + 45)
    X = X[(X.adv_a >= 1e7) & (X.adv_b >= 1e7)]
    A = cross_prices("sel")
    cal = P["close"].index; nxt = dict(zip(cal[:-1], cal[1:]))
    X["a"] = X.pair.str.split("/").str[0]
    ca = [A[a][0].get(d, np.nan) if a in A else np.nan for a, d in zip(X.a, X.index)]
    oa = [A[a][1].get(nxt.get(d), np.nan) if a in A and d in nxt else np.nan for a, d in zip(X.a, X.index)]
    X["raw_auc"] = np.array(oa) / np.array(ca) - 1
    X["has"] = np.isfinite(X.raw_auc)
    X["dif"] = X.raw_auc - X.raw_on
    X["base_auc"] = X.groupby("pair").raw_auc.transform("mean")
    for thr in (2.0, 3.0):
        s = X[(X.z <= -thr) & X.has]
        log(f"#1-3 L14 LETF 15:45 z<=-{thr}: cross prints cover {s.has.mean():.0%} of {int((X.z <= -thr).sum())}; raw long on crosses "
            f"{s.raw_auc.mean()*1e4:+.1f}bp vs panel {s.raw_on.mean()*1e4:+.1f}bp (|diff| median {s.dif.abs().median()*1e4:.1f}bp); "
            f"vs pair baseline on crosses {(s.raw_auc - s.base_auc).mean()*1e4:+.1f}bp")


def explore3():
    log = out("explore3" + ("_loc" if "loc" in sys.argv else ""))
    log("Round 30 exploration L13: LETF twins on a pre-auction decision (SELECT data only)")
    if "loc" not in sys.argv:
        look_twins_m1(log)
    look_twins_cross(log)
    look_twins_loc(log)


def explore2():
    log = out("explore2")
    log("Round 30 exploration, second looks (SELECT data only, cut at 2023-12-31)")
    for f in (look_twins2, look_trade_shares, look_sympathy):
        log(f"\n==== {f.__name__}")
        f(log)


def explore():
    log = out("explore")
    log("Round 30 exploration on SELECT data only (cut at 2023-12-31)")
    for f in (look_pick_tilts, look_wash, look_five, look_twins, look_sympathy):
        log(f"\n==== {f.__name__}")
        f(log)




# ---------------------------------------------------------------- Round 31: EDGAR filters on night picks (#8, #44, #45)
def edgar_events():
    """{cik10: DataFrame(form, t)} with t = acceptance time in ET (naive)."""
    import glob
    import pickle
    ev = {}
    for f in glob.glob(str(NIGHT / "edgar/0*.pkl")):
        x = pickle.load(open(f, "rb"))
        F = x["filings"]
        t = pd.to_datetime(F.acceptanceDateTime, utc=True, errors="coerce").dt.tz_convert("America/New_York").dt.tz_localize(None)
        ev[pathlib.Path(f).stem] = (pd.DataFrame({"form": F.form.values, "t": t.values}).dropna(), x.get("entityType"), x.get("sic"))
    return ev


FLAGS = {"NT": (("NT 10-K", "NT 10-Q", "NT 10-K/A", "NT 10-Q/A", "NT 20-F"), 60),
         "EFFECT": (("EFFECT",), 7),
         "144": (("144", "144/A"), 7)}


def flag_picks(T, ev, flags=FLAGS):
    tk = json.load(open(NIGHT / "edgar/ticker_cik.json"))
    out = {k: [] for k in flags}
    for d, sym in zip(T.d, T.sym):
        cik = tk.get(str(sym).upper().replace(".", "-")) or tk.get(str(sym).upper())
        e = ev.get(str(cik).zfill(10)) if cik else None
        cut = d + pd.Timedelta(hours=15, minutes=40)
        for k, (forms, days) in flags.items():
            if e is None:
                out[k].append(np.nan); continue
            F = e[0]
            m = F.form.isin(forms) & (F.t <= cut) & (F.t > cut - pd.Timedelta(days=days))
            out[k].append(float(m.any()))
    for k in flags:
        T[k] = out[k]
    return T


def explore4():
    log = out("explore4")
    log("Round 31 exploration (SELECT: night picks 2021-23): EDGAR flags on picks, within-night demeaned auction return")
    T = picks(); ev = edgar_events()
    T = flag_picks(T, ev)
    log(f"  mapped picks {T.NT.notna().mean():.0%} of {len(T)}")
    for k in FLAGS:
        for lab, (a, z) in (("2021-22", ("2021", "2022-12-31")), ("2023", ("2023", "2023-12-31"))):
            y = T[(T.d >= a) & (T.d <= z) & T[k].notna()]
            f = y[y[k] == 1]
            log(f"  {k} {lab}: flagged n {len(f)}  within-night {f.x.mean()*1e4:+.1f}bp (median {f.x.median()*1e4:+.1f})  vs unflagged {y[y[k] == 0].x.mean()*1e4:+.1f}bp")
    T.to_pickle(ROOT / "data/research/program/outside_box_picks_edgar_sel.pkl")




# ---------------------------------------------------------------- DS14: insider open-market purchases (SEC Form 345 data sets)
def insider_buys():
    """One row per Form 4 with open-market purchases (code P, acquired): filing date, issuer symbol, $ bought, n owners
    that are officers/directors. Point in time: usable from the session AFTER the filing date."""
    import glob
    import zipfile
    f = NIGHT / "insider/buys.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows = []
    for z in sorted(glob.glob(str(NIGHT / "insider/*_form345.zip"))):
        Z = zipfile.ZipFile(z)
        rd = lambda n: pd.read_csv(Z.open(n), sep="\t", dtype=str, low_memory=False, on_bad_lines="skip")
        S = rd("SUBMISSION.tsv")[["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL", "DOCUMENT_TYPE"]]
        N = rd("NONDERIV_TRANS.tsv")[["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_ACQUIRED_DISP_CD", "TRANS_SHARES", "TRANS_PRICEPERSHARE"]]
        R = rd("REPORTINGOWNER.tsv")[["ACCESSION_NUMBER", "RPTOWNER_RELATIONSHIP"]]
        N = N[(N.TRANS_CODE == "P") & (N.TRANS_ACQUIRED_DISP_CD == "A")].copy()
        N["usd"] = pd.to_numeric(N.TRANS_SHARES, errors="coerce") * pd.to_numeric(N.TRANS_PRICEPERSHARE, errors="coerce")
        g = N.groupby("ACCESSION_NUMBER").usd.sum().rename("usd").reset_index()
        rel = R.groupby("ACCESSION_NUMBER").RPTOWNER_RELATIONSHIP.agg(lambda x: " ".join(map(str, x))).rename("rel").reset_index()
        g = g.merge(S, on="ACCESSION_NUMBER").merge(rel, on="ACCESSION_NUMBER", how="left")
        rows.append(g[g.DOCUMENT_TYPE.isin(["4", "4/A"])])
    X = pd.concat(rows)
    X["fd"] = pd.to_datetime(X.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    X["sym"] = X.ISSUERTRADINGSYMBOL.str.upper().str.strip().str.replace("-", ".", regex=False)
    X["insider"] = X.rel.fillna("").str.contains("Director|Officer", case=False)
    X = X.dropna(subset=["fd", "usd"])[["fd", "sym", "usd", "insider", "ACCESSION_NUMBER"]]
    X.to_parquet(f)
    return X


def explore5():
    log = out("explore5")
    log("DS14 exploration (SELECT data only): insider open-market purchases")
    X = insider_buys()
    X = X[(X.fd <= SEL_END) & X.insider & (X.usd >= 1e4)]
    log(f"  officer/director purchase filings >= $10k, 2020-23: {len(X)}; issuers {X.sym.nunique()}")
    # (a) night picks: issuer had such a purchase filed in the 30 days before d (filing date < d)
    T = picks()
    by = X.groupby("sym").fd.apply(lambda s: np.sort(s.values))
    def recent(d, s, days):
        a = by.get(s)
        if a is None:
            return 0.0
        return float(((a < np.datetime64(d)) & (a >= np.datetime64(d - pd.Timedelta(days=days)))).any())
    for days in (30, 90):
        T[f"ib{days}"] = [recent(d, s, days) for d, s in zip(T.d, T.sym)]
        for lab, (a, z) in (("2021-22", ("2021", "2022-12-31")), ("2023", ("2023", "2023-12-31"))):
            y = T[(T.d >= a) & (T.d <= z)]; f = y[y[f"ib{days}"] == 1]
            log(f"  night picks with an insider buy in the prior {days}d, {lab}: n {len(f)} within-night {f.x.mean()*1e4:+.1f}bp "
                f"(median {f.x.median()*1e4:+.1f}) vs others {y[y[f'ib{days}'] == 0].x.mean()*1e4:+.1f}")
    # (b) event: buy at the open of the session after the filing date, hold 1/5/20 sessions; excess vs SPY
    P = panel(); C, O, V = P["close"], P["open"], P["volume"]
    adv = (C * V).rolling(20, min_periods=15).mean()
    cal = C.index; cols = {s: j for j, s in enumerate(C.columns)}
    Cv, Ov, Av = C.values, O.values, adv.values; sp = cols["SPY"]
    E = X.groupby(["sym", "fd"]).usd.sum().reset_index()
    rows = []
    for s, fd, usd in zip(E.sym, E.fd, E.usd):
        j = cols.get(s)
        if j is None:
            continue
        i = cal.searchsorted(fd + pd.Timedelta(days=1))            # first session after the filing date
        if i + 20 >= len(cal) or i < 1:
            continue
        o = Ov[i, j]; a = Av[i - 1, j]; pc = Cv[i - 1, j]
        if not (np.isfinite(o) and np.isfinite(a) and o >= 5):
            continue
        r = [Cv[i + h - 1, j] / o - 1 - (Cv[i + h - 1, sp] / Ov[i, sp] - 1) for h in (1, 5, 20)]
        rows.append((cal[i], s, usd, a, Cv[i - 1, j] / Cv[max(i - 21, 0), j] - 1, *r))
    Y = pd.DataFrame(rows, columns=["d", "sym", "usd", "adv", "ret20", "x1", "x5", "x20"])
    Y = Y[Y.x20.abs() < 1]
    for lab, m in (("all", Y.adv > 0), ("ADV $1-20M", Y.adv.between(1e6, 2e7)), ("ADV >= $20M", Y.adv >= 2e7),
                   ("after a 20d drop <= -15%", Y.ret20 <= -0.15), ("buy >= $100k", Y.usd >= 1e5)):
        y = Y[m]
        log(f"  event [{lab}]: n {len(y)}; excess vs SPY 1d {y.x1.mean()*1e4:+.1f}  5d {y.x5.mean()*1e4:+.1f}  20d {y.x20.mean()*1e4:+.1f}bp "
            f"(median 20d {y.x20.median()*1e4:+.1f}); by year 20d " + " ".join(f"{k}:{v*1e4:+.0f}" for k, v in y.groupby(y.d.dt.year).x20.mean().items()))
    Y.to_pickle(ROOT / "data/research/program/outside_box_insider_sel.pkl")


if __name__ == "__main__":
    {"explore": explore, "explore2": explore2, "explore3": explore3, "explore4": explore4, "explore5": explore5}[sys.argv[1]]()
