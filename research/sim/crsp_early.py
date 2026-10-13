"""Study CRSP-EARLY (pre-reg research/drafts/round1_prose.md '## Study CRSP-EARLY', f2a854a; N1 = 942, N2 = 943).

N1: Study NX primary night rule (daily-bar form) reused via research.sim.nx.build_panel / collect_trades on CRSP daily bars.
N2: Study OVN-MOM rule (adapted from research/sim/ovn_mom.py to CRSP matrices).
Data: data/research/crsp/{dsf_9106_9712.parquet, dsf_tail.parquet, delist.parquet} (WRDS crsp.dsf + dsenames + dsedelist).
Run: .venv/bin/python -m research.sim.crsp_early [coverage|run]
"""
from __future__ import annotations
import sys, pathlib, numpy as np, pandas as pd
from research.sim import nx

D = pathlib.Path("data/research/crsp")
OUT = pathlib.Path("data/research/program/crsp_early_out.txt")
LOG = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)

def load():
    df = pd.concat([pd.read_parquet(D / "dsf_9106_9712.parquet"), pd.read_parquet(D / "dsf_tail.parquet")])
    df = df.drop_duplicates(["permno", "date"]).sort_values(["permno", "date"]).reset_index(drop=True)
    for c in ("openprc", "prc", "bidlo", "askhi", "vol", "cfacpr", "shrout", "ret"): df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    dl = pd.read_parquet(D / "delist.parquet")
    for c in ("dlret", "dlprc", "dlstcd"): dl[c] = pd.to_numeric(dl[c], errors="coerce").astype("float64")
    return df, dl

def coverage(df):
    """Reads no returns: share of eligible-looking common-stock days with OPENPRC present, by month."""
    P("== COVERAGE CHECK (no returns read)")
    d = df.copy()
    d["elig"] = d["prc"].abs().ge(5) & (d["prc"].abs() * d["vol"]).ge(0)   # price >= $5 only; volume unit not assumed here
    d["has_open"] = d["openprc"].notna() & (d["openprc"] > 0)
    g = d[d.elig].groupby(d.date.dt.to_period("M")).agg(n=("has_open", "size"), cov=("has_open", "mean"))
    for per, r in g.iterrows():
        P(f"  {per} eligible-days {int(r.n):7d} openprc-coverage {r['cov']:.3f}")
    ok = g[g["cov"] >= 0.90]
    # first month from which coverage stays >= 90% for the rest of the window
    start = None
    start = g.index[(g["cov"] >= 0.90).to_numpy()][0]      # registered: first month with coverage >= 90%
    stays = [per for per in g.index if (g.loc[per:, "cov"] >= 0.90).all()][0]
    P("  REGISTERED START (first month >= 90% openprc coverage):", start, " | (not used) first month that stays >= 90% through 1997-12:", stays)
    return start

def build(df, dl, start):
    df = df[df.date >= start.to_timestamp()].copy()
    df["raw"] = df["prc"].abs()
    df["neg_prc"] = df["prc"] < 0
    f = df["cfacpr"].where(df["cfacpr"] > 0)
    df["close"] = df["raw"] / f; df["closeunadj"] = df["raw"]
    df["open"] = np.where(df["openprc"] > 0, df["openprc"], np.nan) / f
    okhl = (df["bidlo"] > 0) & (df["askhi"] > 0)
    df["high"] = np.where(okhl, df["askhi"] / f, np.nan); df["low"] = np.where(okhl, df["bidlo"] / f, np.nan)
    df["volume"] = df["vol"] * f          # so close*volume = raw price * raw shares (nominal $ volume)
    df["ticker"] = df["permno"].astype(int).astype(str)
    df = df[df["close"].notna() & (df["close"] > 0)]
    return df

def delist_tables(df, dl):
    last = df.groupby("ticker").agg(lastdate=("date", "max"), lastraw=("raw", "last"))
    dl = dl.copy(); dl["ticker"] = dl["permno"].astype(int).astype(str)
    dl = dl.sort_values("dlstdt").drop_duplicates("ticker", keep="last").set_index("ticker")
    ret = dl["dlret"].copy()
    miss = ret.isna()
    perf = dl["dlstcd"].between(500, 599)
    ret[miss & perf] = -0.30; ret[miss & ~perf] = 0.0       # Shumway, as registered
    dl["ret_eff"] = ret
    return last, dl

def main_run():
    df, dl = load()
    cov = coverage(df)
    if len(sys.argv) > 1 and sys.argv[1] == "coverage":
        OUT.write_text("\n".join(LOG) + "\n"); return
    start = cov
    P("\n== WINDOW: data start", start, "(warmup 252 nights for N2; N1 needs 20 pos)  end 1997-12-31 (night of 12-31 uses 1998-01-02 open)")
    b = build(df, dl, start)
    P("rows", len(b), "permnos", b.ticker.nunique(), "dup(permno,date)", int(b.duplicated(["ticker", "date"]).sum()))
    P("DATA CHECK: share of rows with prc<0 (bid/ask stand-in)", f"{b.neg_prc.mean():.4f}", " rows with missing/<=0 bidlo|askhi", f"{b.high.isna().mean():.4f}",
      " rows with missing openprc", f"{b.open.isna().mean():.4f}")
    P("DATA CHECK: median nominal $vol of $5+ names by year (volume unit sanity):")
    b["dv"] = b.raw * b.vol
    for y, g in b[b.raw >= 5].groupby(b.date.dt.year): P(f"   {y}: median $vol/day ${g.dv.median()/1e6:.2f}M  n={len(g)}")
    last, dlt = delist_tables(b, dl)
    P("delist table rows", len(dlt), " delisted permnos with a last bar <= 1997-12-30:", int((last.lastdate <= "1997-12-30").sum()))

    # ---- master + act for nx.collect_trades
    mt = pd.DataFrame({"ticker": last.index, "common": True, "exch": "NYSE", "sector": "",
                       "lastpricedate": last["lastdate"].values}).set_index("ticker", drop=False)
    gone = mt.index.isin(dlt.index) & (mt["lastpricedate"] < pd.Timestamp("1997-12-30"))
    mt["delisted"] = gone
    mt["fund"] = False
    val = []
    for tk in mt.index[gone]:
        val.append(dict(ticker=tk, date=last.at[tk, "lastdate"], action="delisted",
                        value=float(last.at[tk, "lastraw"] * (1.0 + dlt.at[tk, "ret_eff"]))))
    act = pd.DataFrame(val)
    # nx dprice: value > 0 and px/cu <= 5 ; value 0 (dlret -1) -> nx scores -100% via delist_nopx, which equals px=0: correct.
    bars = b[["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"]].sort_values(["ticker", "date"]).reset_index(drop=True)
    pn = nx.build_panel(bars)
    P("sessions in panel", len(pn["sessions"]), pd.Timestamp(pn["sessions"][0]).date(), pd.Timestamp(pn["sessions"][-1]).date())

    # ================= N1
    lo, hi = pd.Timestamp(start.to_timestamp()), pd.Timestamp("1997-12-31")
    res = nx.collect_trades(pn, mt, act, "primary", lo, hi)
    tr, nights = res["trades"], res["nights"]
    P(f"\n== N1 night leg: raw picks {len(tr)} on {tr.date.nunique() if len(tr) else 0} nights of {len(nights)}")
    nanret = tr["ret"].isna(); P("  picks with NaN ret (missing next openprc) dropped:", int(nanret.sum()))
    tr = tr[~nanret].copy()
    P("  kind counts:", tr["kind"].value_counts().to_dict())
    P("  picks with prc<0 at the pick close (bid/ask stand-in close):",
      int(b.set_index(["ticker", "date"]).neg_prc.reindex(pd.MultiIndex.from_arrays([tr.ticker, tr.date])).fillna(False).sum()))
    # $10M-bar count by year: eligible names (cu_prev>=5 & adv>=10M) per day, mean per year
    el = nx.eligible_mask(pn)
    ys = pd.Series(el, index=pd.DatetimeIndex(pn["date"])).groupby(level=0).sum()
    P("  eligible ($5, 20d ADV >= $10M nominal) names/day, mean by year:", ys.groupby(ys.index.year).mean().round(1).to_dict())
    # benchmark: same-night small-cap EW close->open = EW overnight of eligible names with ADV below the day's median ADV
    m = el & np.isfinite(pn["ovn"]) & (pn["date"] >= np.datetime64(lo))
    dfb = pd.DataFrame({"d": pn["date"][m], "adv": pn["adv"][m], "r": pn["ovn"][m]})
    dfb["small"] = dfb.adv < dfb.groupby("d").adv.transform("median")
    bench = dfb[dfb.small].groupby("d").r.mean(); bench.index = pd.DatetimeIndex(bench.index)
    halves = {"h1 start..1994-12": (lo, pd.Timestamp("1994-12-31")), "h2 1995-01..1997-12": (pd.Timestamp("1995-01-01"), hi)}

    def stats(trs, nts, model, label):
        d = nx.judge_stats(trs, nts, model, bench)
        L = d["L"]
        P(f"  [{model}] {label}: nights {d['n_nights']} trade-nights {d['n_trade_nights']} trades {d['n_trades']}")
        P(f"     leg mean {d['mean']*1e4:+.2f}bp/night (all nights) t {d['t']:.2f} ; mean on trade nights {d['mean_trade_nights']*1e4:+.2f}bp ; median trade {d['med_trade']*1e4:+.1f}bp "
          f"hit(net) {d['hit_net']:.3f} hit(gross) {d['hit_gross']:.3f} ; ex-best-5-nights {d['ex5']*1e4:+.2f}bp ; beta {d['beta']:.2f} resid {d['adj_mean']*1e4:+.2f}bp t {d['adj_t']:.2f}")
        return d
    out = {}
    for model in ("none", "tier", "tier_hi", "2x_tier_hi"):
        out[model] = stats(tr, nights, model, "1992-97 window") if model != "none" else None
    # gross (zero cost): cost_model needs a model name; compute gross directly
    wL = pd.Series(tr["per"].to_numpy() * tr["ret"].to_numpy()).groupby(tr["date"].to_numpy()).sum().reindex(nights, fill_value=0.0)
    gm, gt = float(wL.mean()), nx.tstat(wL)
    gmed = float(np.median(tr["ret"])); gex5 = float(wL.drop(wL.sort_values().index[-5:]).mean())
    gb = bench.reindex(wL.index); okb = gb.notna()
    gbeta = float(np.cov(wL[okb], gb[okb])[0, 1] / gb[okb].var()); gres = wL[okb] - gbeta * gb[okb]
    P(f"  [GROSS] leg mean {gm*1e4:+.2f}bp/night t {gt:.2f} ; median trade {gmed*1e4:+.1f}bp ; ex-best-5 nights {gex5*1e4:+.2f}bp ; hit {np.mean(tr['ret']>0):.3f} ; beta {gbeta:.2f} resid {gres.mean()*1e4:+.2f}bp t {nx.tstat(gres):.2f}")
    gh = {}
    for hn, (a, z) in halves.items():
        w = wL[(wL.index >= a) & (wL.index <= z)]; gh[hn] = float(w.mean())
        P(f"  [GROSS] {hn}: mean {w.mean()*1e4:+.2f}bp/night t {nx.tstat(w):.2f} nights {len(w)}")
    for model in ("tier", "tier_hi"):
        L = out[model]["L"]
        for hn, (a, z) in halves.items():
            w = L[(L.index >= a) & (L.index <= z)]
            P(f"  [{model}] {hn}: mean {w.mean()*1e4:+.2f}bp/night t {nx.tstat(w):.2f}")
    yr = tr.assign(y=tr.date.dt.year).groupby("y")[["ret"]].apply(lambda g: pd.Series(dict(n=len(g), gross_bp=g.ret.mean()*1e4, med_bp=g.ret.median()*1e4)))
    P("  by year (trade-level gross):"); P(yr.round(1).to_string())
    P("  top-5 gross trades (ret):", tr.nlargest(5, "ret")[["date", "ticker", "ret", "kind"]].assign(ret=lambda x: x.ret.round(3)).values.tolist())
    P("  worst-5 gross trades (ret):", tr.nsmallest(5, "ret")[["date", "ticker", "ret", "kind"]].assign(ret=lambda x: x.ret.round(3)).values.tolist())
    # split sanity: any pick whose next open/close ratio is extreme or whose cfacpr changes at the next bar
    P("  picks with |ret| > 40%:", int((tr.ret.abs() > 0.4).sum()))
    v1 = "FAIL" if (not gm > 0 or not gt >= 1) else ("PASS" if (gm > 0 and gt >= 2 and gmed > 0 and gex5 > 0 and all(v > 0 for v in gh.values())) else "WEAK")
    P("  GATE N1 (gross>0 & t>=2, median>0, ex-best-5>0, both halves>0):",
      f"mean>0&t>=2 {gm>0 and gt>=2} | median>0 {gmed>0} | ex5>0 {gex5>0} | halves>0 {all(v>0 for v in gh.values())}  => {v1}")
    P("  N1 VERDICT:", v1)
    nx_tr = tr

    # ================= N2 : OVN-MOM on CRSP matrices
    P("\n== N2 OVN-MOM")
    dates = pd.DatetimeIndex(pn["sessions"]); T = len(dates)
    cols = sorted(bars.ticker.unique()); ci = {c: i for i, c in enumerate(cols)}; Nn = len(cols)
    di = dates.get_indexer(pd.DatetimeIndex(bars.date)); cj = bars.ticker.map(ci).to_numpy()
    def mat(v, dt=np.float32):
        m_ = np.full((T, Nn), np.nan, dt); m_[di, cj] = np.asarray(v, dt); return m_
    O, C = mat(bars.open), mat(bars.close)
    RC, DV = mat(bars.closeunadj), mat(bars.closeunadj * bars.volume / bars.close * 1.0, np.float64).astype(np.float32)  # DV = raw$vol = raw px * raw shares
    DV = mat(b.set_index(["ticker", "date"]).dv.reindex(pd.MultiIndex.from_arrays([bars.ticker, bars.date])).to_numpy(), np.float64).astype(np.float32)
    CF = mat((bars.closeunadj / bars.close).to_numpy())
    # actions: split = factor (raw/adjusted) changes between consecutive bars (night dropped), plus |ret|>50%
    R = np.full((T, Nn), np.nan, np.float32); R[1:] = O[1:] / C[:-1] - 1
    CFr = np.full((T, Nn), np.nan, np.float32); CFr[1:] = CF[1:] / CF[:-1] - 1
    AF = np.isfinite(CFr) & (np.abs(CFr) > 1e-4)
    bigm = np.abs(R) > 0.5
    nA = np.isfinite(R) & AF; nB = np.isfinite(R) & bigm & ~AF
    Rv = R.copy(); Rv[AF | bigm] = np.nan
    V = np.isfinite(Rv)
    cs = np.cumsum(np.nan_to_num(Rv, nan=0.0).astype(np.float64), axis=0); cn = np.cumsum(V, axis=0)
    def lag(x, k):
        y = np.zeros_like(x); y[k:] = x[:-k]; return y
    n252 = cn - lag(cn, 252); s252 = cs - lag(cs, 252)
    S = np.full((T, Nn), np.nan, np.float32); okS = (n252 >= 200) & (np.arange(T)[:, None] >= 251)
    S[okS] = (s252[okS] / n252[okS]).astype(np.float32)
    med = np.full((T, Nn), np.nan, np.float32)
    for c0 in range(0, Nn, 1500):
        med[:, c0:c0 + 1500] = pd.DataFrame(DV[:, c0:c0 + 1500]).rolling(20, min_periods=15).median().to_numpy(np.float32)
    medl = np.full((T, Nn), np.nan, np.float32); medl[1:] = med[:-1]
    ELIG = (RC >= 5) & (medl >= 20e6) & np.isfinite(S)
    dayret = np.full((T, Nn), np.nan, np.float32); dayret[1:] = C[1:] / C[:-1] - 1
    # delisting nights: name's last bar is session t (< final session), delisted -> night t->t+1 return from dlret
    DR = np.full((T, Nn), np.nan, np.float32)
    lastidx = {tk: int(dates.get_loc(last.at[tk, "lastdate"])) for tk in cols}
    nde = 0
    for tk in dlt.index.intersection(cols):
        t_ = lastidx[tk]
        if t_ < T - 1 and last.at[tk, "lastdate"] < pd.Timestamp("1997-12-30"):
            DR[t_, ci[tk]] = (1 + dlt.at[tk, "ret_eff"]) * last.at[tk, "lastraw"] / RC[t_, ci[tk]] - 1; nde += 1
    P("delisting nights wired:", nde)
    # benchmark: EW close->open of the top-500 raw $vol names (20d median through t-1) in the eligible-price set, night t->t+1
    BM = np.full(T, np.nan)
    for t in range(1, T - 1):
        e = np.flatnonzero(np.isfinite(medl[t]) & np.isfinite(Rv[t + 1]) & (RC[t] >= 5))
        if len(e) < 100: continue
        top = e[np.argsort(-medl[t, e], kind="stable")[:500]]
        BM[t] = Rv[t + 1, top].mean()
    dec = np.full((T, 10), np.nan); top10 = np.full(T, np.nan); nper = np.zeros(T); advm = np.full(T, np.nan); ovl = np.zeros(T); dropn = np.zeros(T); dropB = np.zeros(T)
    top10arm = np.full(T, np.nan)
    for t in range(252, T - 1):
        e = np.flatnonzero(ELIG[t])
        if len(e) < 100: continue
        order = np.argsort(S[t, e], kind="stable"); rk = np.empty(len(e), int); rk[order] = np.arange(len(e))
        g = (rk * 10 // len(e))
        r = Rv[t + 1, e].copy()
        dr = DR[t, e]; useD = ~np.isfinite(r) & np.isfinite(dr); r[useD] = dr[useD]
        for k in range(10):
            x = r[g == k]; x = x[np.isfinite(x)]
            if len(x): dec[t, k] = x.mean()
        top = e[g == 9]
        nper[t] = len(top); advm[t] = np.median(medl[t, top]); ovl[t] = (dayret[t, top] <= -0.08).sum()
        dropn[t] = nA[t + 1, top].sum(); dropB[t] = nB[t + 1, top].sum()
        t10 = e[np.argsort(-S[t, e], kind="stable")[:10]]
        x10 = Rv[t + 1, t10]; d10 = DR[t, t10]; x10 = np.where(np.isfinite(x10), x10, d10); x10 = x10[np.isfinite(x10)]
        if len(x10): top10arm[t] = x10.mean()
    exc = dec[:, 9] - BM; gx = dec - BM[:, None]; exc10 = top10arm - BM
    idx = dates
    first = idx[np.isfinite(exc)][0]
    P("first valid N2 night (252 prior nights):", first.date(), "last", idx[np.isfinite(exc)][-1].date())

    def stat(x, label):
        x = x[np.isfinite(x)]
        if len(x) < 30: P(f"  {label}: n={len(x)} (too few)"); return None
        m_ = x.mean(); t_ = m_ / (x.std(ddof=1) / np.sqrt(len(x))); ex5 = np.sort(x)[:-5].mean()
        P(f"  {label}: n={len(x)} mean {m_*1e4:+.2f}bp t {t_:.2f} median {np.median(x)*1e4:+.2f}bp ex-top5-nights {ex5*1e4:+.2f}bp hit {np.mean(x>0):.3f}")
        return m_, t_, np.median(x), ex5
    mid = pd.Timestamp("1995-01-01")
    PERS = {"JUDGE first-valid..1997-12": (first, pd.Timestamp("1997-12-31")), "half A (first..1994-12)": (first, pd.Timestamp("1994-12-31")),
            "half B (1995-01..1997-12)": (pd.Timestamp("1995-01-01"), pd.Timestamp("1997-12-31"))}
    # N2 halves per registration: the same halves split as N1? Registered 'both halves' for N2 unspecified -> use the same 1994-12 / 1995-01 split (disclosed)
    r2 = {}
    for nm, (a, z) in PERS.items():
        mk = (idx >= a) & (idx <= z)
        P(f"\n== {nm}")
        for c in (0, 2, 5):
            r2[(nm, c)] = stat(exc[mk] - 2 * c * 1e-4, f"top decile minus BM, {c}bp/side")
        stat(exc10[mk] - 4e-4, "top-10 names minus BM, 2bp/side")
        P("  decile gross excess D1..D10 (bp):", " ".join(f"{np.nanmean(gx[mk][:, k])*1e4:+.1f}" for k in range(10)))
        vm = mk & (nper > 0)
        P(f"  names/night {nper[vm].mean():.1f}; median pick $ADV ${np.nanmedian(advm[vm])/1e6:.1f}M; overlap with -8% day losers {ovl[vm].sum()/nper[vm].sum():.2%}; "
          f"dropped(split) {dropn[vm].sum()/nper[vm].sum():.4%}; dropped(|ret|>50%) {dropB[vm].sum()/nper[vm].sum():.4%}")
    J = "JUDGE first-valid..1997-12"
    g0, g2 = r2[(J, 0)], r2[(J, 2)]; h1, h2 = r2[("half A (first..1994-12)", 0)], r2[("half B (1995-01..1997-12)", 0)]
    P("\n== N2 GATE (gross excess; net at 2bp/side vs +6.5bp economic bar reported)")
    chk = [("gross excess mean > 0", g0 and g0[0] > 0, g0 and f"{g0[0]*1e4:+.2f}"), ("night-clustered t >= 2", g0 and g0[1] >= 2, g0 and f"{g0[1]:.2f}"),
           ("median night > 0", g0 and g0[2] > 0, g0 and f"{g0[2]*1e4:+.2f}"), ("both halves > 0", h1 and h2 and h1[0] > 0 and h2[0] > 0, f"{h1 and h1[0]*1e4:+.2f} / {h2 and h2[0]*1e4:+.2f}")]
    for n_, ok_, v in chk: P(f"  {'PASS' if ok_ else 'FAIL'}  {n_}  [{v}]")
    P(f"  (reported) net @2bp/side {g2[0]*1e4:+.2f}bp vs +6.5bp bar: {'meets' if g2[0]*1e4 >= 6.5 else 'does not meet'}")
    P("  N2 VERDICT:", "PASS" if all(bool(c[1]) for c in chk) else "FAIL/WEAK (see gates)")
    P("\nDEVIATIONS (disclosed): daily-bar CRSP; dividends not added back on ex-nights (N1 nx adds Sharadar dividends, here none); N2 ex-action nights = nights where raw/adjusted price factor changes "
      "(splits/distributions in cfacpr), no dividend flags; N2 halves use the same 1994-12 split as N1; N1 benchmark = EW overnight of eligible names below the day's median ADV (small-cap proxy); "
      "picks with missing next openprc dropped (counted above); CRSP vol in shares (volume = vol*cfacpr so close*volume = nominal $).")
    OUT.write_text("\n".join(LOG) + "\n")

if __name__ == "__main__":
    main_run()
