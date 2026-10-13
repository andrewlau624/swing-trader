"""Study MODERN-XS (pre-registration: "Study MODERN-XS" at the end of research/drafts/round1_prose.md, N 949 -> 977).

Monthly decile sorts on 14 never-judged stock characteristics, both directions (28 candidates).
Order (one-look): panel -> DISCOVERY 2021-01..2023-12 -> selection written to the output file ->
JUDGE 2024-01..2026-09 (<= 3 kept) -> descriptive 1998-2015 / per-year / liquidity buckets.

  PYTHONPATH=. .venv/bin/python research/sim/modern_xs.py
"""
from __future__ import annotations

import math
import pathlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import scipy.stats as SS

ROOT = pathlib.Path(__file__).resolve().parents[2]
ST = pathlib.Path.home() / "data" / "sharadar"
OUT = ROOT / "data" / "research" / "program" / "modern_xs_out.txt"
N_PROG = 977
COST = 0.0010
SHOCK = 0.0030
D_LO, D_HI = "2021-01", "2023-12"
J_LO, J_HI = "2024-01", "2026-09"
FEATS = ["lnmcap", "b2m", "ey", "sy", "evebitda_inv", "gprof", "roe", "accruals", "assetgr", "issuance",
         "leverage", "turnover", "dvtrend", "lndv"]
CANDS = [(f, s) for f in FEATS for s in (+1, -1)]  # +1 = top decile of feature, -1 = bottom decile
FUND_STALE = pd.Timedelta(days=450)

_lines: list[str] = []
_fh = None


def log(s=""):
    print(s, flush=True)
    _lines.append(s)
    _fh.write(s + "\n")
    _fh.flush()


# ------------------------------------------------------------------ panel
def build_panel():
    tk = pd.read_parquet(ST / "tickers.parquet", columns=["table", "ticker", "category", "sector", "isdelisted"])
    tk = tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")]
    tk = tk.drop_duplicates("ticker")
    tickers = sorted(tk.ticker.unique())
    sector = tk.set_index("ticker").sector.replace("", "Unknown").fillna("Unknown")
    t = pq.read_table(ST / "stocks.parquet", columns=["ticker", "date", "close", "closeadj", "closeunadj", "volume"],
                      filters=[("ticker", "in", tickers), ("date", ">=", pd.Timestamp("1997-12-01").date())]).to_pandas()
    t["date"] = pd.to_datetime(t["date"])
    t = t.dropna(subset=["closeadj", "closeunadj", "close"])
    dates = np.sort(t.date.drop_duplicates().values)
    names = np.array(sorted(t.ticker.unique()))
    di = np.searchsorted(dates, t.date.values)
    ti = np.searchsorted(names, t.ticker.values)
    shp = (len(dates), len(names))

    def mat(col):
        m = np.full(shp, np.nan, dtype=np.float32)
        m[di, ti] = t[col].values.astype(np.float32)
        return m

    adj, raw, cls, vol = mat("closeadj"), mat("closeunadj"), mat("close"), mat("volume")
    del t
    dv = cls * vol
    return tk, sector, dates, names, adj, raw, vol, dv, cls


def build_fund_long(uni, names_set):
    """Latest ART / ARQ fundamentals with datekey strictly < t (>= datekey + 1 session), stale cap 450d."""
    f = pq.read_table(ST / "fundamentals.parquet",
                      columns=["ticker", "dimension", "calendardate", "date", "assets", "equity", "gp", "netinc", "ncfo",
                               "debt", "sharesbas"],
                      filters=[("dimension", "in", ["ART", "ARQ"]), ("ticker", "in", sorted(names_set))]).to_pandas()
    for c in ("calendardate", "date"):
        f[c] = pd.to_datetime(f[c])
    f = f.rename(columns={"date": "datekey"}).sort_values(["ticker", "dimension", "calendardate", "datekey"])
    f = f.drop_duplicates(["ticker", "dimension", "calendardate"], keep="last")
    art = f[f.dimension == "ART"].copy()
    art["gprof"] = art.gp / art.assets
    art["roe"] = art.netinc / art.equity.where(art.equity > 0)
    art["accruals"] = (art.netinc - art.ncfo) / art.assets
    arq = f[f.dimension == "ARQ"].copy().sort_values(["ticker", "calendardate"])
    g = arq.groupby("ticker")
    gap = (arq.calendardate - g.calendardate.shift(4)).dt.days
    ok = gap.between(350, 380)
    arq["assetgr"] = np.where(ok, arq.assets / g.assets.shift(4) - 1, np.nan)
    arq["issuance"] = np.where(ok, arq.sharesbas / g.sharesbas.shift(4) - 1, np.nan)
    arq["leverage"] = arq.debt / arq.assets
    q = uni[["ticker", "t"]].sort_values("t")
    out = q.copy()
    for src, cols in ((art, ["gprof", "roe", "accruals"]), (arq, ["assetgr", "issuance", "leverage"])):
        s = src[["ticker", "datekey"] + cols].dropna(subset=["datekey"]).sort_values("datekey")
        m = pd.merge_asof(q, s, left_on="t", right_on="datekey", by="ticker", allow_exact_matches=False,
                          tolerance=FUND_STALE)
        for c in cols:
            out[c] = m[c].values
    return out


def build():
    tk, sector, dates, names, adj, raw, vol, dv, cls = build_panel()
    dser = pd.Series(dates)
    ym = dser.dt.to_period("M")
    last_idx = dser.groupby(ym).apply(lambda s: s.index[-1]).values  # index of last session per month
    me = [(ym.iloc[i], i) for i in last_idx]
    # Actions: delisted for cause
    act = pd.read_parquet(ST / "actions.parquet", columns=["date", "action", "ticker"])
    act["date"] = pd.to_datetime(act["date"])
    cause = act[act.action.isin(["bankruptcyliquidation", "regulatorydelisting"])].groupby("ticker").date.max()
    nn = len(names)
    valid = ~np.isnan(adj)
    nlisted = np.cumsum(valid, axis=0)
    lastbar = np.where(valid.any(0), len(dates) - 1 - np.argmax(valid[::-1], axis=0), -1)
    cause_flag = np.zeros(nn, bool)
    cd = cause.reindex(names)
    for j in np.where(cd.notna().values)[0]:
        if lastbar[j] >= 0 and cd.iloc[j] >= dates[lastbar[j]] - np.timedelta64(10, "D"):
            cause_flag[j] = True
    # benchmark
    qq = pq.read_table(ST / "funds.parquet", columns=["ticker", "date", "closeadj"], filters=[("ticker", "=", "QQQ")]).to_pandas()
    qq["date"] = pd.to_datetime(qq.date)
    qqq = qq.set_index("date").closeadj.reindex(dates)
    # monthly rows
    rows = []
    for k in range(len(me) - 1):
        p, i = me[k]
        if i < 252:
            continue
        e1 = i + 1
        e2 = me[k + 1][1] + 1
        if e2 >= len(dates):
            continue
        wdv = dv[i - 62:i + 1]
        n_dv = np.sum(~np.isnan(wdv), 0)
        med63 = np.where(n_dv >= 50, np.nanmedian(np.where(np.isnan(wdv), np.nan, wdv), axis=0), np.nan)
        elig = (raw[i] >= 5) & (med63 >= 10e6) & (nlisted[i] >= 252) & valid[i]
        idx = np.where(elig & valid[e1])[0]  # must be buyable at e1
        if len(idx) < 200:
            continue
        med21 = np.nanmedian(dv[i - 20:i + 1][:, idx], axis=0)
        med252 = np.nanmedian(dv[i - 251:i + 1][:, idx], axis=0)
        mv63 = np.nanmean(vol[i - 62:i + 1][:, idx], axis=0)
        # holding return
        a1 = adj[e1, idx]
        seg = adj[e1:e2 + 1][:, idx]
        # last valid price within [e1, e2]
        vv = ~np.isnan(seg)
        lastrel = seg.shape[0] - 1 - np.argmax(vv[::-1], axis=0)
        a2 = seg[lastrel, np.arange(len(idx))]
        r = a2 / a1 - 1
        gone = lastbar[idx] < e2  # no bar at/after e2 => delisted in-window
        pen = gone & cause_flag[idx]
        r = np.where(pen, (1 + r) * 0.7 - 1, r)
        df = pd.DataFrame(dict(ticker=names[idx], t=dates[i], p=p, ret=r, med63=med63[idx],
                               med21=med21, med252=med252, mv63=mv63, close_t=cls[i, idx].astype(float)))
        qr = qqq.iloc[e2] / qqq.iloc[e1] - 1
        df["qqq"] = qr
        df["hold"] = pd.Period(dates[e1], "M")
        rows.append(df)
    uni = pd.concat(rows, ignore_index=True)
    # daily metrics at month-end
    dts = sorted(uni.t.unique())
    d = pq.read_table(ST / "daily.parquet", columns=["ticker", "date", "marketcap", "pb", "pe", "ps", "evebitda"],
                      filters=[("date", "in", [pd.Timestamp(x).date() for x in dts])]).to_pandas()
    d["t"] = pd.to_datetime(d.date)
    uni = uni.merge(d.drop(columns="date"), on=["ticker", "t"], how="left")
    uni["lnmcap"] = np.log(uni.marketcap.where(uni.marketcap > 0))
    uni["b2m"] = 1 / uni.pb.where(uni.pb != 0)
    uni["ey"] = 1 / uni.pe.where(uni.pe != 0)
    uni["sy"] = 1 / uni.ps.where(uni.ps != 0)
    uni["evebitda_inv"] = 1 / uni.evebitda.where(uni.evebitda != 0)
    uni["turnover"] = uni.mv63 / (uni.marketcap * 1e6 / uni.close_t)
    uni["dvtrend"] = uni.med21 / uni.med252
    uni["lndv"] = np.log(uni.med63)
    fl = build_fund_long(uni, set(uni.ticker))
    fl = fl.drop(columns=["t"]).reset_index(drop=True)
    # merge_asof output was sorted by t; realign via keys
    q = uni[["ticker", "t"]].sort_values("t")
    fl["ticker"] = q.ticker.values
    fl["t"] = q.t.values
    uni = uni.merge(fl, on=["ticker", "t"], how="left")
    uni["sector"] = uni.ticker.map(sector).fillna("Unknown")
    uni.loc[~np.isfinite(uni.turnover), "turnover"] = np.nan
    return uni


# ------------------------------------------------------------------ stats
def tstat(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return np.nan
    return x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))


def dsr(x, n_trials):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    sk = SS.skew(x)
    ku = SS.kurtosis(x, fisher=False)
    g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z)), sr, sr0


def picks(g, f, s):
    v = g[f].dropna()
    n = len(v)
    if n < 100:
        return g.iloc[0:0]
    k = max(1, int(n // 10))
    order = v.sort_values(ascending=(s < 0))
    return g.loc[order.index[:k]]


def monthly(uni, cands, lo, hi, keep_picks=False):
    """per-month strategy net return, EW universe, QQQ for each candidate within [lo, hi] hold months."""
    sel = uni[(uni.hold >= pd.Period(lo)) & (uni.hold <= pd.Period(hi))]
    res = {c: [] for c in cands}
    pk = {c: [] for c in cands}
    ew = {}
    for h, g in sel.groupby("hold"):
        ew[h] = (g.ret.mean(), g.qqq.iloc[0], len(g))
        for c in cands:
            p = picks(g, *c)
            if len(p) == 0:
                continue
            res[c].append((h, p.ret.mean(), len(p)))
            if keep_picks:
                pk[c].append(p.assign(hold=h))
    out = {}
    for c in cands:
        r = pd.DataFrame(res[c], columns=["hold", "gross", "n"]).set_index("hold")
        r["ew"] = [ew[h][0] for h in r.index]
        r["qqq"] = [ew[h][1] for h in r.index]
        r["univ_n"] = [ew[h][2] for h in r.index]
        r["net"] = r.gross - COST
        r["x_ew"] = r.net - r.ew
        r["x_q"] = r.net - r.qqq
        out[c] = r
    return (out, pk) if keep_picks else out


def cname(c):
    return f"{c[0]}{'+' if c[1] > 0 else '-'}"


def table(res, cands, title):
    log(title)
    log(f"{'cand':<17}{'n':>3} {'x_EW %/mo':>10}{'t_EW':>6} {'x_QQQ %/mo':>11}{'t_QQQ':>6} {'ann x_QQQ %':>12}{'net %/mo':>9}")
    rows = []
    for c in cands:
        r = res[c]
        rows.append((c, len(r), r.x_ew.mean() * 100, tstat(r.x_ew), r.x_q.mean() * 100, tstat(r.x_q),
                     r.x_q.mean() * 1200, r.net.mean() * 100))
    for x in rows:
        log(f"{cname(x[0]):<17}{x[1]:>3} {x[2]:>10.2f}{x[3]:>6.2f} {x[4]:>11.2f}{x[5]:>6.2f} {x[6]:>12.1f}{x[7]:>9.2f}")
    return rows


def main():
    global _fh
    OUT.parent.mkdir(parents=True, exist_ok=True)
    _fh = open(OUT, "w")
    log("== Study MODERN-XS (N 977): 14 features x 2 directions = 28 candidates, monthly EW top decile, 10bp RT, one-session lag")
    uni = build()
    um = uni.groupby("hold").size()
    log(f"Panel: {len(uni):,} stock-months, {um.index.min()}..{um.index.max()}; universe size per month: "
        f"median {int(um.median())}, min {um.min()} ({um.idxmin()}), max {um.max()} ({um.idxmax()}); "
        f"1998-2015 median {int(um[um.index <= pd.Period('2015-12')].median())}, 2021-23 median "
        f"{int(um[(um.index >= pd.Period('2021-01')) & (um.index <= pd.Period('2023-12'))].median())}, "
        f"2024-26 median {int(um[um.index >= pd.Period('2024-01')].median())}")
    log("Universe: Sharadar SEP, Domestic Common Stock (incl. primary/secondary class), delisted included; at month-end t raw "
        "close >= $5, 63d median $vol (split-adj close x volume) >= $10M, >= 252 listed sessions, and a bar at the entry session.")
    log("Data notes / deviations:")
    log("  - Entry = close of first session of t+1; exit = close of first session of t+2 (closeadj). Month label = month of entry.")
    log("  - Cost 10bp RT deducted from the strategy; EW universe and QQQ are gross benchmarks (conservative). Shock 30bp.")
    log("  - Delisting: no bar at exit => last close in window; -30% extra if a bankruptcyliquidation/regulatorydelisting action "
        "falls within 10 days of the last bar (my reading of 'delisted for cause'). Acquisitions/other: last close.")
    log("  - SF1: ART (gprof, ROE, accruals) and ARQ (asset growth/issuance yoy via the ARQ row 4 quarters back, leverage = debt/assets) "
        "from the latest row with datekey < t (strict), stale cap 450 days (my addition; registration silent). ROE needs equity > 0.")
    log("  - DAILY metrics (marketcap, pb, pe, ps, evebitda) read as of the month-end row; 1/x features: x == 0 -> NaN, negatives kept "
        "(earnings yield 'all signs as is'). Vendor DAILY is assumed point-in-time (not verifiable).")
    log("  - Turnover = 63d mean volume / (marketcap / raw close_t shares); split-adjusted volume vs raw price mismatch can distort "
        "turnover around recent splits (noted, not corrected).")
    log("  - Ticker symbol used as the key (reused symbols not separated). Top decile = floor(n_valid/10) names, min 100 valid names.")
    log("  - DSR is computed on MONTHLY excess-vs-QQQ returns (T=33), SR0 from sample-length null variance, N=977 (program_books.dsr form).")

    cands = CANDS
    # ---------------- DISCOVERY
    disc = monthly(uni, cands, D_LO, D_HI)
    log("")
    rows = table(disc, cands, f"== DISCOVERY {D_LO}..{D_HI} ({len(next(iter(disc.values())))} months), all 28 candidates")
    ranked = sorted(rows, key=lambda x: -(x[3] if not np.isnan(x[3]) else -99))
    log("Discovery top 5 by t of excess vs EW universe: " + "; ".join(f"{cname(x[0])} t={x[3]:.2f} vsQQQ {x[6]:+.1f}%/yr" for x in ranked[:5]))
    kept = [x[0] for x in ranked[:3] if x[3] >= 2]
    log("")
    log(f"== SELECTION (written before any {J_LO}..{J_HI} result is computed): "
        + (", ".join(cname(c) for c in kept) if kept else "NONE (no candidate has discovery t >= 2) -> KILL, no judge look"))
    # ---------------- JUDGE
    verdicts = {}
    jres = {}
    if kept:
        jres, jpk = monthly(uni, kept, J_LO, J_HI, keep_picks=True)
        log("")
        log(f"== JUDGE {J_LO}..{J_HI} ({len(next(iter(jres.values())))} months), kept only")
        for c in kept:
            r = jres[c]
            ann_q = r.x_q.mean() * 12
            t_ew = tstat(r.x_ew)
            med_q = r.x_q.median()
            top3 = r.x_q.drop(r.x_q.nlargest(3).index)
            shock = (r.x_q - (SHOCK - COST)).mean()
            ds, sr, sr0 = dsr(r.x_q.values, N_PROG)
            gates = [("ann net excess vs QQQ >= +16%/yr", ann_q >= 0.16, f"{ann_q * 100:+.1f}%"),
                     ("excess vs EW universe t >= 2", t_ew >= 2, f"t {t_ew:.2f} ({r.x_ew.mean() * 100:+.2f}%/mo)"),
                     ("median month vs QQQ > 0", med_q > 0, f"{med_q * 100:+.2f}%"),
                     ("ex-top-3 months mean vs QQQ > 0", top3.mean() > 0, f"{top3.mean() * 100:+.2f}%/mo"),
                     ("30bp shock mean vs QQQ > 0", shock > 0, f"{shock * 100:+.2f}%/mo"),
                     ("DSR > 0.95 @ N 977", ds > 0.95, f"DSR {ds:.3f} (SR/mo {sr:.2f}, SR0 {sr0:.2f})")]
            allp = all(g[1] for g in gates)
            weak = (t_ew >= 2) and not allp
            v = "PASS" if allp else ("WEAK" if weak else "KILL")
            verdicts[c] = v
            log(f"-- {cname(c)}: mean net {r.net.mean() * 100:.2f}%/mo, vs QQQ {r.x_q.mean() * 100:+.2f}%/mo (t {tstat(r.x_q):.2f}), "
                f"vs EW {r.x_ew.mean() * 100:+.2f}%/mo; hit vs QQQ {np.mean(r.x_q > 0) * 100:.0f}%; mean picks/mo {r.n.mean():.0f}")
            for nm, ok, val in gates:
                log(f"     {'PASS' if ok else 'FAIL'}  {nm}: {val}")
            log(f"   VERDICT {cname(c)}: {v}")
            # beta
            for lab, rr in (("judge", r), ("discovery", disc[c])):
                b = np.polyfit(rr.qqq.values, rr.net.values, 1)
                log(f"   beta to QQQ ({lab}): {b[0]:.2f}, alpha {b[1] * 1200:+.1f}%/yr")
            pk = pd.concat(jpk[c])
            sm = pk.sector.value_counts(normalize=True) * 100
            uj = uni[(uni.hold >= pd.Period(J_LO)) & (uni.hold <= pd.Period(J_HI))].sector.value_counts(normalize=True) * 100
            log("   sector mix of picks (judge) vs universe: " + ", ".join(f"{s} {sm[s]:.0f}/{uj.get(s, 0):.0f}" for s in sm.index[:6]))
            log(f"   median pick $ADV(63d) ${pk.med63.median() / 1e6:.0f}M vs universe ${uni[uni.hold >= pd.Period(J_LO)].med63.median() / 1e6:.0f}M")
        log("")
        log("OVERALL VERDICT: " + "; ".join(f"{cname(c)} {v}" for c, v in verdicts.items())
            + ("  -> PASS (forward-shadow candidate only)" if "PASS" in verdicts.values() else "  -> no PASS"))
    else:
        log("OVERALL VERDICT: KILL (no judge look)")
    # ---------------- DESCRIPTIVE
    log("")
    desc = monthly(uni, cands, "1998-01", "2015-12")
    table(desc, cands, "== DESCRIPTIVE 1998-2015 (not a gate), all 28 (months with valid feature coverage only)")
    # coverage: features available months
    cov = {f: int(uni[uni.hold <= pd.Period('2015-12')].groupby('hold')[f].apply(lambda s: s.notna().sum() >= 100).sum()) for f in FEATS}
    log("   months with >= 100 valid names in 1998-2015: " + ", ".join(f"{f} {n}" for f, n in cov.items()))
    if kept:
        log("")
        log("== PER-YEAR (kept features; net excess vs EW / vs QQQ, %/mo avg; all years)")
        allr = monthly(uni, kept, "1998-01", J_HI)
        for c in kept:
            r = allr[c]
            yr = r.groupby(r.index.year).agg(x_ew=("x_ew", "mean"), x_q=("x_q", "mean"), n=("x_ew", "size"))
            log(f"-- {cname(c)}: " + " ".join(f"{y}:{v.x_ew * 100:+.1f}/{v.x_q * 100:+.1f}" if not np.isnan(v.x_q) else f"{y}:{v.x_ew * 100:+.1f}/na"
                                             for y, v in yr.iterrows()))
        log("")
        log("== LIQUIDITY BUCKETS (kept features' picks, 2021-01..2026-09): mean pick return - EW universe, per bucket ($ADV 63d)")
        _, pk = monthly(uni, kept, D_LO, J_HI, keep_picks=True)
        ewm = uni.groupby("hold").ret.mean()
        bins = [10e6, 50e6, 500e6, np.inf]
        labs = ["$10-50M", "$50-500M", ">$500M"]
        for c in kept:
            p = pd.concat(pk[c])
            p["b"] = pd.cut(p.med63, bins, labels=labs, right=False)
            p["x"] = p.ret - p.hold.map(ewm) - COST
            g = p.groupby(["hold", "b"], observed=True).x.mean().reset_index()
            parts = []
            for b in labs:
                s = g[g.b == b].x
                parts.append(f"{b}: {s.mean() * 100:+.2f}%/mo (t {tstat(s):.1f}, {len(s)} mo, {int((p.b == b).sum())} picks)")
            log(f"-- {cname(c)}: " + "; ".join(parts))
    _fh.close()


if __name__ == "__main__":
    main()
