"""Adversarial diagnostics for CRSP-EARLY (N1 night leg, N2 OVN-MOM): closing-quote midpoint / ask execution, exchange & spread splits,
intraday follow-through, lagged-score placebo. Diagnostics only; reuses crsp_early.py builders, rules NOT retuned.
Run: .venv/bin/python -m research.sim.crsp_early_adv"""
from __future__ import annotations
import pathlib, numpy as np, pandas as pd
from research.sim import nx
from research.sim import crsp_early as ce

OUT = pathlib.Path("data/research/program/crsp_early_adv_out.txt"); LOG = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); LOG.append(s)
def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan
def rep(x, label):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 30: P(f"  {label}: n={len(x)} too few"); return
    P(f"  {label}: n={len(x)} mean {x.mean()*1e4:+.2f}bp t {tstat(x):.2f} median {np.median(x)*1e4:+.2f}bp hit {np.mean(x>0):.3f}")

def main():
    df, dl = ce.load()
    start = pd.Period("1992-11", "M")
    ba = pd.read_parquet(ce.D / "dsf_bidask.parquet")
    for c in ("bid", "ask"): ba[c] = pd.to_numeric(ba[c], errors="coerce").astype("float64")
    ba["ticker"] = ba.permno.astype(int).astype(str)
    b = ce.build(df, dl, start)
    exch = df[["permno", "date", "exchcd"]].copy(); exch["ticker"] = exch.permno.astype(int).astype(str)
    b = b.merge(ba[["ticker", "date", "bid", "ask"]], on=["ticker", "date"], how="left")
    b = b.merge(exch[["ticker", "date", "exchcd"]], on=["ticker", "date"], how="left", suffixes=("", "_x"))
    f = (b["closeunadj"] / b["close"])
    okq = (b.bid > 0) & (b.ask >= b.bid)
    b["mid"] = np.where(okq, (b.bid + b.ask) / 2 / f, np.nan); b["askadj"] = np.where(okq, b.ask / f, np.nan)
    b["hs"] = np.where(okq, (b.ask - b.bid) / (b.ask + b.bid), np.nan)    # relative half-spread
    b["dv"] = b.closeunadj * b.vol
    P("quote coverage (bid>0, ask>=bid) by year:", b.groupby(b.date.dt.year).apply(lambda g: round(float(np.mean(((g.bid > 0) & (g.ask >= g.bid)))), 3)).to_dict())
    P("median relative half-spread bp of $5+ names by year/exch(1 NYSE,2 AMEX,3 NASD):")
    q = b[(b.closeunadj >= 5) & okq]
    P(q.groupby([q.date.dt.year, q.exchcd]).hs.median().mul(1e4).round(0).unstack().to_string())
    P("share of close rows that are prc<0 (CRSP close already a bid/ask midpoint):", round(float(b.neg_prc.mean()), 4))

    last, dlt = ce.delist_tables(b, dl)
    bars = b[["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"]].sort_values(["ticker", "date"]).reset_index(drop=True)
    pn = nx.build_panel(bars)
    dates = pd.DatetimeIndex(pn["sessions"]); T = len(dates)
    cols = sorted(bars.ticker.unique()); ci = {c: i for i, c in enumerate(cols)}; Nn = len(cols)
    bb = b.sort_values(["ticker", "date"]).reset_index(drop=True)
    di = dates.get_indexer(pd.DatetimeIndex(bb.date)); cj = bb.ticker.map(ci).to_numpy()
    def mat(v, dt=np.float64):
        m_ = np.full((T, Nn), np.nan, dt); m_[di, cj] = np.asarray(v, dt); return m_
    O, C, MID, ASK, HS = mat(bb.open), mat(bb.close), mat(bb.mid), mat(bb.askadj), mat(bb.hs)
    RC, DV, EX = mat(bb.closeunadj), mat(bb.dv), mat(bb.exchcd)
    CF = RC / C
    # ---- same construction as crsp_early.py
    R = np.full((T, Nn), np.nan); R[1:] = O[1:] / C[:-1] - 1
    CFr = np.full((T, Nn), np.nan); CFr[1:] = CF[1:] / CF[:-1] - 1
    AF = np.isfinite(CFr) & (np.abs(CFr) > 1e-4); bigm = np.abs(R) > 0.5
    Rv = R.copy(); Rv[AF | bigm] = np.nan
    def score(Rm):
        V = np.isfinite(Rm); cs = np.cumsum(np.nan_to_num(Rm, nan=0.0), axis=0); cn = np.cumsum(V, axis=0)
        lag = lambda x, k: np.concatenate([np.zeros((k, x.shape[1]), x.dtype), x[:-k]])
        n252 = cn - lag(cn, 252); s252 = cs - lag(cs, 252)
        S = np.full((T, Nn), np.nan); ok = (n252 >= 200) & (np.arange(T)[:, None] >= 251); S[ok] = s252[ok] / n252[ok]; return S
    S = score(Rv)
    med = np.full((T, Nn), np.nan)
    for c0 in range(0, Nn, 1500):
        med[:, c0:c0 + 1500] = pd.DataFrame(DV[:, c0:c0 + 1500]).rolling(20, min_periods=15).median().to_numpy()
    medl = np.full((T, Nn), np.nan); medl[1:] = med[:-1]
    ELIG = (RC >= 5) & (medl >= 20e6) & np.isfinite(S)
    # next-night return matrices indexed at signal row t (night t -> t+1); only valid when Rv[t+1] valid (non-split)
    ok1 = np.zeros((T, Nn), bool); ok1[:-1] = np.isfinite(Rv[1:])
    def nxt(num_next, den_now):
        r = np.full((T, Nn), np.nan); r[:-1] = num_next[1:] / den_now[:-1] - 1; r[~ok1] = np.nan; return r
    r_tr = nxt(O, C); r_mid = nxt(O, MID); r_ask = nxt(O, ASK)
    r_id = np.full((T, Nn), np.nan); r_id[:-1] = C[1:] / O[1:] - 1; r_id[~ok1] = np.nan       # next day open->close
    r_cc = np.full((T, Nn), np.nan); r_cc[:-1] = C[1:] / C[:-1] - 1; r_cc[~ok1] = np.nan
    # benchmark (as registered): EW night return of top-500 $vol names, here computed on the SAME definition per variant
    def bm(rm):
        out = np.full(T, np.nan)
        for t in range(1, T - 1):
            e = np.flatnonzero(np.isfinite(medl[t]) & np.isfinite(Rv[t + 1]) & (RC[t] >= 5))
            if len(e) < 100: continue
            top = e[np.argsort(-medl[t, e], kind="stable")[:500]]
            x = rm[t, top]; x = x[np.isfinite(x)]
            if len(x) > 50: out[t] = x.mean()
        return out
    BMtr, BMmid, BMask = bm(r_tr), bm(r_mid), bm(r_ask)
    # intraday benchmark: EW open->close of the same top-500 set
    BMid = bm(r_id)
    qual = np.isfinite(MID) & np.isfinite(ASK)

    def decile_pick(Sx, lagk=0):
        """boolean top-decile matrix at row t using score row t-lagk (eligibility still at t)."""
        sel = np.zeros((T, Nn), bool)
        for t in range(252 + lagk, T - 1):
            e = np.flatnonzero(ELIG[t] & np.isfinite(Sx[t - lagk]))
            if len(e) < 100: continue
            s = Sx[t - lagk, e]; order = np.argsort(s, kind="stable"); rk = np.empty(len(e), int); rk[order] = np.arange(len(e))
            sel[t, e[(rk * 10 // len(e)) == 9]] = True
        return sel
    SEL = decile_pick(S)
    first = 252
    def nightly(rm, bmv, sel, extra=None):
        out = np.full(T, np.nan)
        for t in range(T - 1):
            m = sel[t] & np.isfinite(rm[t]) & (extra[t] if extra is not None else True)
            if m.sum() >= 3: out[t] = rm[t, m].mean() - bmv[t]
        return out
    P("\n=== BASELINE replicate (registered): top decile trade-close night minus BM")
    base = nightly(r_tr, BMtr, SEL); rep(base, "N2 base trade-close")
    P("\n=== (a) quote-based returns, restricted to picks with valid closing quote (apples to apples)")
    for nm, rm, bmv in (("trade close -> open", r_tr, BMtr), ("closing MID -> open", r_mid, BMmid), ("closing ASK -> open trade (buy at ask)", r_ask, BMask)):
        x = nightly(rm, bmv, SEL, qual); rep(x, nm)
    # executable lower bound: also sell at bid proxy = open*(1 - half spread at t)
    r_ask_lb = r_ask - HS * 1.0   # approx: sell at open minus same-name half spread (open trade assumed at mid)
    x = nightly(r_ask_lb, BMask, SEL, qual); rep(x, "ASK -> open minus half-spread (pessimistic bound)")
    P("  executable vs passive BM that also is taken at mid (BMmid):")
    x = nightly(r_ask, BMmid, SEL, qual); rep(x, "ASK->open minus BM(mid->open)")
    x = nightly(r_ask_lb, BMmid, SEL, qual); rep(x, "pessimistic bound minus BM(mid->open)")
    P("  mid-based SCORE (prior nights open_t/mid_{t-1}), mid-based returns:")
    Rm = np.full((T, Nn), np.nan); Rm[1:] = O[1:] / MID[:-1] - 1; Rm[AF | bigm] = np.nan
    Rm[np.abs(Rm) > 0.5] = np.nan
    SMID = score(Rm); selm = decile_pick(SMID)
    x = nightly(r_mid, BMmid, selm, qual); rep(x, "score(mid) pick, mid->open, minus BM(mid)")
    x = nightly(r_tr, BMtr, selm); rep(x, "score(mid) pick, trade close->open")
    P("  overlap of top deciles (trade-score vs mid-score):", round(float((SEL & selm).sum() / SEL.sum()), 3))
    P("  mean closing half-spread of top decile vs eligible: %.1fbp vs %.1fbp" % (np.nanmean(np.where(SEL, HS, np.nan)) * 1e4, np.nanmean(np.where(ELIG, HS, np.nan)) * 1e4))

    P("\n=== (b) splits (excess over BM(trade); night-clustered)")
    for nm, mk in (("NYSE", EX == 1), ("AMEX", EX == 2), ("Nasdaq", EX == 3)):
        x = nightly(r_tr, BMtr, SEL, mk); rep(x, f"{nm} picks, trade close->open")
        x = nightly(r_mid, BMmid, SEL, mk & qual); rep(x, f"{nm} picks, MID->open")
    hsq = np.nanmedian(HS[ELIG & np.isfinite(HS)])
    P("  median eligible rel half-spread bp:", round(hsq * 1e4, 1))
    for nm, mk in (("hs<=median", HS <= hsq), ("hs>median", HS > hsq)):
        x = nightly(r_tr, BMtr, SEL, mk & qual); rep(x, f"{nm} trade->open")
        x = nightly(r_mid, BMmid, SEL, mk & qual); rep(x, f"{nm} MID->open")
    for nm, mk in (("px 5-10", (RC >= 5) & (RC < 10)), ("px 10-25", (RC >= 10) & (RC < 25)), ("px 25+", RC >= 25)):
        x = nightly(r_tr, BMtr, SEL, mk); rep(x, f"{nm} trade->open")
    P("  NYSE & hs<=median:")
    x = nightly(r_tr, BMtr, SEL, (EX == 1) & (HS <= hsq) & qual); rep(x, "NYSE low-spread trade->open")
    x = nightly(r_ask, BMmid, SEL, (EX == 1) & qual); rep(x, "NYSE ASK->open minus BM(mid)")
    for y in (1993, 1994, 1995, 1996, 1997):
        mk = np.zeros(T, bool); mk[(dates.year == y)] = True
        xn = nightly(r_tr, BMtr, SEL, EX == 1)
        P(f"  year {y}: base {np.nanmean(base[mk])*1e4:+.2f}bp t {tstat(base[mk]):.2f}  NYSE-only {np.nanmean(xn[mk])*1e4:+.2f}bp t {tstat(xn[mk]):.2f}")

    P("\n=== (c) next-day intraday (open->close) and close-close of the top decile minus matching BM")
    x = nightly(r_id, BMid, SEL); rep(x, "open->close (day t+1)")
    BMcc = bm(r_cc); x = nightly(r_cc, BMcc, SEL); rep(x, "close->close (t -> t+1)")
    for nm, mk in (("NYSE", EX == 1), ("Nasdaq", EX == 3)):
        x = nightly(r_id, BMid, SEL, mk); rep(x, f"{nm} open->close")

    P("\n=== (d) placebos: lagged score (decile of score from k nights earlier), trade close->open, minus BM")
    for k in (126, 252, 504):
        if k + 252 >= T - 5: continue
        sel = decile_pick(S, lagk=k); x = nightly(r_tr, BMtr, sel); rep(x, f"score lagged {k} nights")
    P("  note: shuffling nights within stock leaves a 252-night mean unchanged by construction, so the lag test is the informative placebo.")
    # shuffled-stock placebo: permute score across names within night
    rng = np.random.default_rng(1); sh = np.zeros((T, Nn), bool)
    for t in range(252, T - 1):
        e = np.flatnonzero(ELIG[t]);
        if len(e) < 100: continue
        p = rng.permutation(len(e)); s = S[t, e][p]; order = np.argsort(s, kind="stable"); rk = np.empty(len(e), int); rk[order] = np.arange(len(e))
        sh[t, e[(rk * 10 // len(e)) == 9]] = True
    x = nightly(r_tr, BMtr, sh); rep(x, "random-decile placebo (names permuted within night)")
    # persistence of the lag: does the decile's own score persist across years?
    P("\n=== N1 night leg: closing midquote check")
    mt = pd.DataFrame({"ticker": last.index, "common": True, "exch": "NYSE", "sector": "", "lastpricedate": last["lastdate"].values}).set_index("ticker", drop=False)
    gone = mt.index.isin(dlt.index) & (mt["lastpricedate"] < pd.Timestamp("1997-12-30")); mt["delisted"] = gone; mt["fund"] = False
    val = [dict(ticker=tk, date=last.at[tk, "lastdate"], action="delisted", value=float(last.at[tk, "lastraw"] * (1.0 + dlt.at[tk, "ret_eff"]))) for tk in mt.index[gone]]
    act = pd.DataFrame(val)
    res = nx.collect_trades(pn, mt, act, "primary", pd.Timestamp(start.to_timestamp()), pd.Timestamp("1997-12-31"))
    tr = res["trades"]; tr = tr[~tr["ret"].isna()].copy()
    ti = dates.get_indexer(pd.DatetimeIndex(tr.date)); tj = tr.ticker.map(ci).to_numpy()
    tr["mid_ret"] = np.where(ti < T - 1, O[np.minimum(ti + 1, T - 1), tj] / MID[ti, tj] - 1, np.nan)
    tr["ask_ret"] = np.where(ti < T - 1, O[np.minimum(ti + 1, T - 1), tj] / ASK[ti, tj] - 1, np.nan)
    tr["trade_ret_chk"] = np.where(ti < T - 1, O[np.minimum(ti + 1, T - 1), tj] / C[ti, tj] - 1, np.nan)
    tr["close_vs_mid"] = C[ti, tj] / MID[ti, tj] - 1
    tr["negprc"] = [bool(b_) for b_ in b.set_index(["ticker", "date"]).neg_prc.reindex(pd.MultiIndex.from_arrays([tr.ticker, tr.date])).fillna(False)]
    tr["ex"] = EX[ti, tj]; tr["hs"] = HS[ti, tj]; tr["yr"] = pd.DatetimeIndex(tr.date).year
    P("  picks", len(tr), "with quote", int(tr.mid_ret.notna().sum()), "| close vs mid (bp) mean/median:", round(float(np.nanmean(tr.close_vs_mid))*1e4, 1), round(float(np.nanmedian(tr.close_vs_mid))*1e4, 1),
      "| share prc<0:", round(float(tr.negprc.mean()), 3))
    q1 = tr[tr.mid_ret.notna()]
    nights = res["nights"]
    def leg(col, d):
        w = pd.Series((d["per"] * d[col]).to_numpy()).groupby(d["date"].to_numpy()).sum().reindex(nights, fill_value=0.0); return w
    for col in ("ret", "mid_ret", "ask_ret"):
        w = leg(col, q1); P(f"  gross leg {col:8s}: mean {w.mean()*1e4:+.2f}bp/night t {nx.tstat(w):.2f} | median trade {np.median(q1[col])*1e4:+.1f}bp | trade mean {q1[col].mean()*1e4:+.1f}bp")
    for ex_ in (1, 2, 3):
        d = q1[q1.ex == ex_]
        if len(d) > 10: P(f"   exch {ex_}: n {len(d)} trade mean {d.ret.mean()*1e4:+.1f} mid mean {d.mid_ret.mean()*1e4:+.1f} ask mean {d.ask_ret.mean()*1e4:+.1f} bp")
    P("  by year (trade mean bp / mid mean bp / n):", {int(y): (round(g.ret.mean()*1e4), round(g.mid_ret.mean()*1e4), len(g)) for y, g in q1.groupby("yr")})
    wd = leg("ret", tr); top = wd.sort_values(ascending=False)
    P(f"  concentration: nights with trades {int((wd!=0).sum())}; top-10 nights sum {top.iloc[:10].sum()*1e4:.0f}bp of total {wd.sum()*1e4:.0f}bp; ex-top-10 mean {wd.drop(top.index[:10]).mean()*1e4:+.2f}bp t {nx.tstat(wd.drop(top.index[:10])):.2f}")
    for lab, a, z in (("1993-95", "1993-01-01", "1995-12-31"), ("1996-97", "1996-01-01", "1997-12-31")):
        s_ = wd[(wd.index >= a) & (wd.index <= z)]; P(f"  {lab}: mean {s_.mean()*1e4:+.2f}bp t {nx.tstat(s_):.2f} distinct trade nights {int((s_!=0).sum())}")
    wm = leg("mid_ret", q1); sm = wm[(wm.index >= "1993-01-01") & (wm.index <= "1995-12-31")]
    P(f"  mid-based 1993-95: mean {sm.mean()*1e4:+.2f}bp t {nx.tstat(sm):.2f}; 1996-97 {wm[wm.index >= '1996-01-01'].mean()*1e4:+.2f}bp")
    OUT.write_text("\n".join(LOG) + "\n")

if __name__ == "__main__":
    main()
