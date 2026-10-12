"""Study WIKI-ATTN (pre-reg research/drafts/round1_prose.md "Study WIKI-ATTN"). One look, frozen design."""
from __future__ import annotations
import pathlib, sys, numpy as np, pandas as pd, pyarrow.parquet as pq
sys.path.insert(0, ".")
from research.sim import wiki_fetch as wf

SH = pathlib.Path.home() / "data/sharadar"
OUT = pathlib.Path("data/research/program/wiki_attn_out.txt")
CATS = ["Domestic Common Stock", "Domestic Common Stock Primary Class", "Domestic Common Stock Secondary Class"]
import datetime as _dt
D0 = _dt.date(2015, 10, 1)
LO, HI = pd.Timestamp("2016-01-01"), pd.Timestamp("2026-09-30")
COST = 7.5  # bp per side
lines: list[str] = []
def P(*a):
    s = " ".join(str(x) for x in a); lines.append(s); print(s, flush=True)

def build_map():
    raw = pd.read_parquet(wf.D / "ticker_map_raw.parquet").drop_duplicates(["ticker", "article", "start", "end"])
    n_raw = raw.ticker.nunique()
    a = raw.groupby("ticker").article.nunique(); b = raw.groupby("article").ticker.nunique()
    m = raw[raw.ticker.map(a).eq(1) & raw.article.map(b).eq(1)]
    n_amb = n_raw - m.ticker.nunique()
    t = pd.read_parquet(SH / "tickers.parquet")
    t = t[(t.table == "SEP") & t.category.isin(CATS)][["permaticker", "ticker", "firstpricedate", "lastpricedate", "isdelisted"]]
    tc = t.groupby("ticker").permaticker.nunique()
    t1 = t[t.ticker.map(tc).eq(1)]
    j = m.merge(t1, on="ticker", how="inner")
    for c in ["firstpricedate", "lastpricedate"]: j[c] = pd.to_datetime(j[c])
    st = pd.to_datetime(j.start, utc=True, errors="coerce").dt.tz_localize(None)
    en = pd.to_datetime(j.end, utc=True, errors="coerce").dt.tz_localize(None)
    bad = (en.notna() & (en < j.firstpricedate)) | (st.notna() & (st > j.lastpricedate))
    n_bad = int(bad.sum()); j = j[~bad]
    j = j.drop_duplicates("ticker")
    info = dict(n_raw=n_raw, n_amb=n_amb, n_unique=m.ticker.nunique(), n_joined=len(j), n_reused_sharadar=int((tc > 1).sum()), n_interval_drop=n_bad)
    return j[["ticker", "article", "permaticker", "isdelisted", "firstpricedate", "lastpricedate"]].reset_index(drop=True), info

def load_px(tickers):
    tb = pq.read_table(SH / "stocks.parquet", columns=["ticker", "date", "open", "close", "volume", "closeunadj"],
                       filters=[("ticker", "in", list(tickers)), ("date", ">=", D0)]).to_pandas()
    tb["date"] = pd.to_datetime(tb.date)
    tb = tb.sort_values(["ticker", "date"]).reset_index(drop=True)
    tb["ropen"] = tb.open * tb.closeunadj / tb.close
    tb["rclose"] = tb.closeunadj
    tb["dv"] = tb.close * tb.volume
    return tb

def load_spy():
    tb = pq.read_table(SH / "funds.parquet", columns=["ticker", "date", "open", "close", "closeunadj"], filters=[("ticker", "=", "SPY"), ("date", ">=", D0)]).to_pandas()
    tb["date"] = pd.to_datetime(tb.date); tb = tb.sort_values("date").set_index("date")
    tb["ropen"] = tb.open * tb.closeunadj / tb.close
    return tb

def tclust(r, g):
    r = np.asarray(r, float); n = len(r)
    if n < 3: return np.nan
    e = r - r.mean(); s = pd.Series(e).groupby(np.asarray(g)).sum()
    se = np.sqrt((s ** 2).sum()) / n
    return r.mean() / se if se > 0 else np.nan

def stat(df, col):
    if len(df) == 0: return "n=0"
    r = df[col].values; t = tclust(r, df.s.values)
    top5 = np.sort(r)[:-5].mean() if len(r) > 5 else np.nan
    return f"n={len(r)} mean={r.mean():+.1f}bp median={np.median(r):+.1f} hit={np.mean(r>0):.0%} clt={t:+.2f} ex-top5={top5:+.1f}"

def main():
    j, info = build_map()
    P("# WIKI-ATTN study output (pre-reg round1_prose.md 'Study WIKI-ATTN'). Single look.")
    P(f"## Map coverage: Wikidata ticker rows -> {info['n_raw']} tickers; ambiguous dropped {info['n_amb']}; unique 1:1 {info['n_unique']};")
    P(f"   joined to Sharadar SEP domestic common {info['n_joined']} (Sharadar tickers reused by >1 permaticker, excluded: {info['n_reused_sharadar']}; dropped on Wikidata start/end vs price-span mismatch: {info['n_interval_drop']}).")
    px = load_px(j.ticker)
    # universe filter on every day: raw close>=5, 20d median $vol (ending s-1) >= 10M
    px["adv"] = px.groupby("ticker").dv.transform(lambda x: x.shift(1).rolling(20, min_periods=15).median())
    px["univ"] = (px.rclose >= 5) & (px.adv >= 10e6)
    cand = px[(px.date >= LO) & px.univ].ticker.unique()
    j = j[j.ticker.isin(cand)].reset_index(drop=True)
    P(f"   tickers passing the universe filter at least once 2016+: {len(j)}")
    uy = px[(px.date >= LO) & px.univ].groupby([px.date.dt.year]).ticker.nunique()
    P("   tickers in universe (>=1 day) per year: " + " ".join(f"{y}:{n}" for y, n in uy.items()))
    views = wf.fetch_views(sorted(j.article.unique()))
    views = views[views.article.isin(j.article)]
    P(f"   articles with pageviews data: {views.article.nunique()} of {len(j)}")
    v = views.merge(j[["ticker", "article"]], on="article")
    # per-ticker daily series on calendar days, zero-fill
    cal = pd.date_range("2015-07-01", "2026-09-30")
    V = v.pivot_table(index="date", columns="ticker", values="views", aggfunc="sum").reindex(cal).fillna(0.0)
    base = V.shift(1).rolling(30, min_periods=30).median()
    spike = (V / base.where(base > 0) >= 3) & (base >= 100)
    spike = spike.loc[LO - pd.Timedelta(days=5):]
    ev = spike.stack(); ev = ev[ev].reset_index(); ev.columns = ["d", "ticker", "f"]
    # session index per ticker
    spy = load_spy()
    sess = spy.index[spy.index >= "2015-10-01"]
    pos = pd.Series(np.arange(len(sess)), index=sess)
    # s = first trading session >= d+1 calendar
    idx = sess.searchsorted(ev.d + pd.Timedelta(days=1))
    ev = ev[idx < len(sess)].copy(); idx = idx[idx < len(sess)]
    ev["si"] = idx; ev["s"] = sess[idx]
    ev = ev.drop_duplicates(["ticker", "si"]).sort_values(["ticker", "si"])
    keep = []; last = {}
    for tk, si in zip(ev.ticker, ev.si):  # re-arm only after 10 sessions per name
        if tk in last and si - last[tk] <= 10: keep.append(False); continue
        last[tk] = si; keep.append(True)
    ev = ev[keep].reset_index(drop=True)
    n_spike_all = len(ev)
    act = pd.read_parquet(SH / "actions.parquet", columns=["date", "action", "ticker"])
    act = act[act.action.isin(["split"])]; act["date"] = pd.to_datetime(act.date)
    splits = set(zip(act.ticker, act.date))
    pxi = px.set_index(["ticker", "date"]).sort_index()
    spy_o = spy.ropen; spy_c = spy.closeunadj

    def returns(e, shift=0):
        out = []
        for tk, si in zip(e.ticker, e.si + shift):
            if si + 6 >= len(sess) or si < 1: continue
            s0, s1, s5, sm = sess[si], sess[si + 1], sess[si + 6], sess[si - 1]
            try:
                rs0 = pxi.loc[(tk, s0)]; rs1 = pxi.loc[(tk, s1)]; rs5 = pxi.loc[(tk, s5)]
            except KeyError: continue
            if not (rs0.rclose >= 5 and rs0.adv >= 10e6): continue
            sp = any((tk, d) in splits for d in sess[si + 1:si + 7])
            sp_night = (tk, s1) in splits
            night = rs1.ropen / rs0.rclose - 1; nspy = spy_o[s1] / spy_c[s0] - 1
            drift = rs5.ropen / rs1.ropen - 1; dspy = spy_o[s5] / spy_o[s1] - 1
            try: pc = pxi.loc[(tk, sm)].close; ret_d = rs0.close / pc - 1
            except KeyError: ret_d = np.nan
            out.append(dict(ticker=tk, si=si, s=s0, night=(night - nspy) * 1e4 if not (sp_night or abs(night) > .5) else np.nan,
                            drift=(drift - dspy) * 1e4 if not (sp or abs(drift) > .5) else np.nan, retd=ret_d))
        return pd.DataFrame(out)

    R = returns(ev)
    R = R[(R.s >= LO) & (R.s <= HI)].copy()
    n_guard = int(R.night.isna().sum()); n_guard_d = int(R.drift.isna().sum())
    R["night_net"] = R.night - 2 * COST; R["night_2x"] = R.night - 4 * COST
    R["drift_net"] = R.drift - 2 * COST; R["drift_2x"] = R.drift - 4 * COST
    R["yr"] = R.s.dt.year
    P(f"## Events (spike >=3x median(30d), median>=100, universe on session, 10-session re-arm): {len(R)} (pre-universe spikes {n_spike_all}); split/|ret|>50% guard NaN: night {n_guard}, drift {n_guard_d}")
    P("   events per year: " + " ".join(f"{y}:{n}" for y, n in R.groupby('yr').size().items()))
    Rn = R.dropna(subset=["night"]); Rd = R.dropna(subset=["drift"])
    halves = lambda d: (d[d.s < "2021-01-01"], d[d.s >= "2021-01-01"])
    P("## PRIMARY night (close s -> open s+1, minus SPY, bp)")
    P("  gross:", stat(Rn, "night")); P("  net 7.5/side:", stat(Rn, "night_net")); P("  net 2x cost:", stat(Rn, "night_2x"))
    h1, h2 = halves(Rn)
    P("  half 2016-20 net:", stat(h1, "night_net")); P("  half 2021-26 net:", stat(h2, "night_net"))
    P("## SECONDARY drift (open s+1 -> open s+6, minus SPY, bp)")
    P("  gross:", stat(Rd, "drift")); P("  net 7.5/side:", stat(Rd, "drift_net")); P("  net 2x cost:", stat(Rd, "drift_2x"))
    d1, d2 = halves(Rd)
    P("  half 2016-20 net:", stat(d1, "drift_net")); P("  half 2021-26 net:", stat(d2, "drift_net"))
    # placebo: spike dates shifted +60 sessions, same names
    Rp = returns(ev, shift=60)
    Rp = Rp[(Rp.s >= LO) & (Rp.s <= HI)].dropna(subset=["night"]).copy(); Rp["night_net"] = Rp.night - 2 * COST
    P("## Placebo (same names, spike sessions +60): ", stat(Rp, "night_net"), "| gross mean %+.1f" % Rp.night.mean())
    # overlap with -8% losers
    lo = Rn[Rn.retd <= -0.08]; nl = Rn[~(Rn.retd <= -0.08)]
    P(f"## Overlap with night-leg-style picks (close/prev_close <= -8% on session s): {len(lo)} of {len(Rn)} events ({len(lo)/max(len(Rn),1):.1%})")
    P("  overlap net:", stat(lo, "night_net")); P("  non-overlap net:", stat(nl, "night_net"))
    # gate
    m = Rn.night_net.mean(); t = tclust(Rn.night_net.values, Rn.s.values); med = Rn.night_net.median()
    ex5 = np.sort(Rn.night_net.values)[:-5].mean()
    g = [("net mean >= +15bp", m >= 15, f"{m:+.1f}"), ("day-clustered t >= 2.5", t >= 2.5, f"{t:+.2f}"), ("median > 0", med > 0, f"{med:+.1f}"),
         ("both halves > 0", h1.night_net.mean() > 0 and h2.night_net.mean() > 0, f"{h1.night_net.mean():+.1f}/{h2.night_net.mean():+.1f}"),
         ("ex-top-5 > 0", ex5 > 0, f"{ex5:+.1f}"), ("placebo mean (net) <= 1/3 of real", Rp.night_net.mean() <= m / 3 if m > 0 else False, f"{Rp.night_net.mean():+.1f} vs {m/3:+.1f}")]
    P("## GATE (PRIMARY)")
    for n, ok, val in g: P(f"  {'PASS' if ok else 'FAIL'}  {n}  [{val}]")
    P("## VERDICT: " + ("PASS" if all(x[1] for x in g) else "KILL (gate failed: " + "; ".join(x[0] for x in g if not x[1]) + ")"))
    P("## Deviations / notes")
    P("  - Wikidata gives current + some past tickers (start/end qualifiers on ~37%/10% of rows); where absent, current-ticker survivorship accepted; tickers reused by >1 Sharadar permaticker excluded.")
    P("  - Exchanges queried: NYSE, Nasdaq, NYSE American (Wikidata Q846626), NYSE Arca (none returned); domestic common only after Sharadar join.")
    P("  - d+1 = first trading session >= calendar d+1 (weekend spikes map to Monday). 20d ADV uses sessions ending s-1 (no same-day volume). Raw open = open*closeunadj/close.")
    P("  - Dropped a night if an ex-split date is the sell open, or |night ret| > 50%; drift if any split in the window. SPY raw open/close from SFP (dividends ignored).")
    P("  - Missing pageview days zero-filled (API omits zero days). 404 articles excluded. Placebo applies universe filter at shifted session.")
    OUT.write_text("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
