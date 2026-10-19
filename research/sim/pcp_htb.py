"""Study PCP-HTB runner (pre-registered 2026-10-17, N 1018 -> 1019). One run of the judged spec.
Usage: .venv/bin/python -m research.sim.pcp_htb [--pull] ; --pull only fetches caches.
Cache data/research/pcp_htb/ ; out data/research/program/pcp_htb_out.txt
"""
import sys, pathlib, time, numpy as np, pandas as pd
from research.sim.borrow_xs import conn

D = pathlib.Path("data/research/pcp_htb"); D.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path("data/research/program/pcp_htb_out.txt")
YEARS = list(range(2005, 2025))


def trading_days(db):
    f = D / "cal.parquet"
    if f.exists(): return pd.read_parquet(f)["date"]
    c = db.raw_sql("select distinct date from crsp.dsi order by date")
    c["date"] = pd.to_datetime(c["date"]); c.to_parquet(f, index=False)
    return c["date"]


def signal_dates(cal):
    """Wednesday close; if holiday, the next session. t1 = next session after t."""
    cal = pd.Series(cal).sort_values().reset_index(drop=True)
    out = []
    wed = pd.date_range(cal.min(), cal.max(), freq="W-WED")
    idx = cal.searchsorted(wed)  # first session >= Wednesday
    seen = set()
    for w, i in zip(wed, idx):
        if i + 1 >= len(cal): continue
        t = cal[i]
        if t.weekday() == 4 and w.weekday() == 2 and t != w and (t - w).days > 2: continue
        if t in seen: continue
        seen.add(t); out.append((t, cal[i + 1]))
    return pd.DataFrame(out, columns=["t", "t1"])


def pull_borrate(db, y, sd):
    f = D / f"htb_{y}.parquet"
    if f.exists(): return pd.read_parquet(f)
    ds = ",".join(f"'{d:%Y-%m-%d}'" for d in sd["t"] if d.year == y)
    sql = f"""select distinct on (securityid, date) securityid as secid, date, days, borrowrate
              from optionm.borrate{y} where date in ({ds}) and borrowrate >= 10
              order by securityid, date, abs(days-30)"""
    df = db.raw_sql(sql); df["date"] = pd.to_datetime(df["date"]); df.to_parquet(f, index=False); return df


def pull_opts(db, y, hb, sd):
    f = D / f"opt_{y}.parquet"
    if f.exists(): return pd.read_parquet(f)
    sdy = sd[sd["t"].dt.year == y]
    dl = sorted(set(sdy["t"]) | set(sdy["t1"]))
    parts = []
    secs = sorted(hb["secid"].astype(int).unique()) if len(hb) else []
    if not secs: pd.DataFrame().to_parquet(f); return pd.DataFrame()
    for i in range(0, len(secs), 150):
        ch = ",".join(map(str, secs[i:i + 150]))
        ds = ",".join(f"'{d:%Y-%m-%d}'" for d in dl)
        sql = f"""select secid, date, exdate, cp_flag, strike_price, best_bid, best_offer, volume, open_interest,
                         contract_size, cfadj, ss_flag, root, suffix
                  from optionm.opprcd{y} where secid in ({ch}) and date in ({ds})
                  and exdate - date between 18 and 75 and open_interest > 0 and best_offer > 0"""
        for k in range(5):
            try: parts.append(db.raw_sql(sql)); break
            except Exception as e:
                print("retry", str(e)[:80]); time.sleep(10)
        print(y, i, len(secs), flush=True)
    if not parts: return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]); df["exdate"] = pd.to_datetime(df["exdate"])
    df.to_parquet(f, index=False); return df


def pull_static(db):
    f = D / "static.pkl"
    if f.exists(): return pd.read_pickle(f)
    link = db.raw_sql("select secid, sdate, edate, permno from wrdsapps_link_crsp_optionm.opcrsphist where score = 1")
    link["sdate"] = pd.to_datetime(link["sdate"]); link["edate"] = pd.to_datetime(link["edate"])
    dist = db.raw_sql("select permno, exdt, distcd, divamt from crsp.dsedist where distcd between 1000 and 1999 and exdt is not null")
    dist["exdt"] = pd.to_datetime(dist["exdt"])
    dl = db.raw_sql("select permno, dlstdt, dlstcd from crsp.dsedelist")
    dl["dlstdt"] = pd.to_datetime(dl["dlstdt"])
    names = db.raw_sql("select distinct on (permno) permno, shrcd from crsp.dsenames order by permno, namedt desc")
    r = dict(link=link, dist=dist, dl=dl, names=names)
    pd.to_pickle(r, f); return r


def pull_px(db, permnos, y, dates):
    f = D / f"px_{y}.parquet"
    if f.exists(): return pd.read_parquet(f)
    ds = ",".join(f"'{d:%Y-%m-%d}'" for d in dates)
    pl = ",".join(map(str, permnos))
    df = db.raw_sql(f"select permno, date, prc, bid, ask, cfacpr from crsp.dsf where date in ({ds}) and permno in ({pl})")
    df["date"] = pd.to_datetime(df["date"]); df.to_parquet(f, index=False); return df


def pull_all():
    db = conn(); cal = trading_days(db); sd = signal_dates(cal)
    sd = sd[sd.t.dt.year.between(2005, 2024)]
    st = pull_static(db)
    for y in YEARS:
        hb = pull_borrate(db, y, sd)
        print(y, "borrate rows", len(hb), flush=True)
        pull_opts(db, y, hb, sd)
    return sd



# ---------------------------------------------------------------- analysis
RES = 2.60  # $ per contract-pair reserve (per contract; applied per contract = per 100 shares)


def dtb3():
    f = D / "dtb3.csv"
    if not f.exists():
        import urllib.request
        urllib.request.urlretrieve("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3", f)
    x = pd.read_csv(f); x.columns = ["date", "r"]; x["date"] = pd.to_datetime(x["date"])
    x["r"] = pd.to_numeric(x["r"], errors="coerce") / 100
    return x.set_index("date")["r"].ffill()


def build_candidates():
    db = conn(); cal = trading_days(db); sd = signal_dates(cal); sd = sd[sd.t.dt.year.between(2005, 2024)]
    st = pull_static(db); link = st["link"]; dist = st["dist"]; dl = st["dl"]
    rf = dtb3()
    rows = []; stats = dict(htb_namedates=0, nolink=0, noopt=0, noexp=0, nostrike=0, divexcl=0, signal=0, confirmed=0, delist=0)
    comp = []
    for y in YEARS:
        hb = pd.read_parquet(D / f"htb_{y}.parquet")
        if not len(hb): continue
        o = pd.read_parquet(D / f"opt_{y}.parquet")
        sdy = sd[sd.t.dt.year == y]
        t1map = dict(zip(sdy.t, sdy.t1))
        # link
        lk = hb.merge(link, on="secid")
        lk = lk[(lk.date >= lk.sdate) & (lk.date <= lk.edate)].drop_duplicates(["secid", "date"])
        stats["htb_namedates"] += len(hb); stats["nolink"] += len(hb) - len(lk)
        pxd = sorted(set(sdy.t) | set(sdy.t1))
        px = pull_px(db, sorted(lk.permno.astype(int).unique()), y, pxd)
        px["prc"] = px["prc"].abs()
        px["ask"] = pd.to_numeric(px["ask"], errors="coerce"); px["bid"] = pd.to_numeric(px["bid"], errors="coerce")
        px.loc[~(px.ask > 0), "ask"] = np.nan; px.loc[~(px.bid > 0), "bid"] = np.nan
        px["ask_u"] = px["ask"].fillna(px["prc"] * 1.005)
        px = px.set_index(["permno", "date"])
        o = o[(o.contract_size == 100) & (o.cfadj == 1) & (o.ss_flag.astype(str) == "0")
              & (o.suffix.isna() | (o.suffix == "")) & (o.open_interest > 0)].copy()
        for cc in ("strike_price", "best_bid", "best_offer", "open_interest"): o[cc] = o[cc].astype("float64")
        o["K"] = o.strike_price / 1000.0
        og = {k: g for k, g in o.groupby(["secid", "date"])}
        for r in lk.itertuples():
            permno = int(r.permno); t = r.date; t1 = t1map.get(t)
            if t1 is None or (permno, t) not in px.index or (permno, t1) not in px.index: stats["noopt"] += 1; continue
            S = px.loc[(permno, t), "prc"]; A = px.loc[(permno, t), "ask_u"]
            if pd.isna(S) or pd.isna(A): stats["noopt"] += 1; continue
            g = og.get((r.secid, t))
            if g is None: stats["noopt"] += 1; continue
            g = g.assign(dte=(g.exdate - t).dt.days)
            g = g[(g.dte >= 21) & (g.dte <= 70)]
            if g.empty: stats["noexp"] += 1; continue
            exps = g.groupby("exdate").dte.first()
            ex = (exps - 45).abs().idxmin()
            exd = pd.Timestamp(ex)
            # dividend exclusion: ordinary cash ex-date in (t1, expiry]
            dv = dist[(dist.permno == permno) & (dist.exdt > t) & (dist.exdt <= exd)]
            if len(dv): stats["divexcl"] += 1; continue
            ge = g[g.exdate == ex]
            c = ge[ge.cp_flag == "C"].drop_duplicates("K").set_index("K"); p = ge[ge.cp_flag == "P"].drop_duplicates("K").set_index("K")
            ks = c.index.intersection(p.index)
            ks = [k for k in ks if abs(k / S - 1) <= 0.15 and c.loc[k, "best_bid"] > 0 and p.loc[k, "best_offer"] > 0]
            if not ks: stats["nostrike"] += 1; continue
            dte = (exd - t).days; rft = rf.get(t, rf.asof(t))
            best = None; worst = 9
            for k in ks:
                cost = A + p.loc[k, "best_offer"] - c.loc[k, "best_bid"] + RES / 100
                y_ = (k - cost) / cost * 365 / dte; e = y_ - rft
                worst = min(worst, e)
                if best is None or e > best[0]: best = (e, k, cost)
            # sanity pair: mid implied vs borrowrate at ATM
            katm = min(ks, key=lambda k: abs(k - S))
            mid = S + (p.loc[katm, "best_bid"] + p.loc[katm, "best_offer"]) / 2 - (c.loc[katm, "best_bid"] + c.loc[katm, "best_offer"]) / 2
            comp.append(dict(secid=r.secid, t=t, bor=r.borrowrate / 100, best_e=best[0], worst_e=worst, impl=(katm - mid) / mid * 365 / dte - rft))
            if best[0] < 0.10: continue
            stats["signal"] += 1
            k = best[1]
            # next session confirmation
            g1 = og.get((r.secid, t1))
            if g1 is None: continue
            c1 = g1[(g1.cp_flag == "C") & (g1.exdate == ex) & (abs(g1.K - k) < 1e-9)]
            p1 = g1[(g1.cp_flag == "P") & (g1.exdate == ex) & (abs(g1.K - k) < 1e-9)]
            if c1.empty or p1.empty: continue
            c1 = c1.iloc[0]; p1 = p1.iloc[0]
            if not (c1.best_bid > 0 and p1.best_offer > 0): continue
            A1 = px.loc[(permno, t1), "ask_u"]
            if pd.isna(A1): continue
            B1 = px.loc[(permno, t1), "bid"]; dte1 = (exd - t1).days
            if dte1 <= 0: continue
            cost1 = A1 + p1.best_offer - c1.best_bid + RES / 100
            rf1 = rf.get(t1, rf.asof(t1)); e1 = (k - cost1) / cost1 * 365 / dte1 - rf1
            if e1 < 0.10: continue
            stats["confirmed"] += 1
            hs_s = (A1 - B1) / 2 if pd.notna(B1) else 0.0025 * A1
            shock = hs_s + (c1.best_offer - c1.best_bid) / 2 + (p1.best_offer - p1.best_bid) / 2
            d = dl[(dl.permno == permno) & (dl.dlstdt > t1) & (dl.dlstdt <= exd)]
            if len(d): stats["delist"] += 1
            rows.append(dict(secid=r.secid, permno=permno, t=t, t1=t1, exd=exd, K=k, S1=px.loc[(permno, t1), "prc"], A1=A1,
                             P1=p1.best_offer, C1=c1.best_bid, cost=cost1, dte=dte1, e_t=best[0], e_t1=e1, rf=rf1,
                             oi=int(min(c1.open_interest, p1.open_interest)), shock=shock, borrow=r.borrowrate / 100,
                             delisted=len(d) > 0))
        print(y, len(rows), flush=True)
    return pd.DataFrame(rows), stats, pd.DataFrame(comp), rf


def simulate(ent, rf, cap, shock=False, start="2005-01-01", end="2024-12-31"):
    """Cash account; returns (equity series by date, trades df). Positions marked on linear accrual."""
    days = pd.bdate_range(start, end)
    r = rf.reindex(days, method="ffill").fillna(0).values / 365 * 1.0
    ent = ent.sort_values(["t1", "e_t1"], ascending=[True, False])
    cash = cap; open_ = []; eq = []; trades = []; held = set(); util = []
    byd = {d: g for d, g in ent.groupby("t1")}
    for i, d in enumerate(days):
        # expiries
        keep = []
        for pz in open_:
            if pz["exd"] <= d:
                cash += pz["payoff"]; held.discard(pz["permno"]); trades.append({**pz, "pnl": pz["payoff"] - pz["outlay"]})
            else: keep.append(pz)
        open_ = keep
        if d in byd:
            for e in byd[d].itertuples():
                if e.permno in held: continue
                cps = e.cost + (e.shock if shock else 0)
                per = cps * 100  # reserve already in cost (per share, RES/100)
                n = int(min(10, cash // per, 0.05 * e.oi))
                if n < 1: continue
                out = n * per; cash -= out; held.add(e.permno)
                open_.append(dict(permno=e.permno, secid=e.secid, t1=d, exd=e.exd, outlay=out, payoff=n * 100 * e.K, n=n, dte=e.dte, ann=(e.K / cps - 1) * 365 / e.dte))
        mark = sum(pz["outlay"] + (pz["payoff"] - pz["outlay"]) * min(1, (d - pz["t1"]).days / max(1, (pz["exd"] - pz["t1"]).days)) for pz in open_)
        eq.append(cash + mark); util.append(mark / (cash + mark))
        cash *= 1 + r[i]
    return pd.Series(eq, index=days), pd.DataFrame(trades), pd.Series(util, index=days)


def period_excess(eq, rf, a, b):
    e = eq[a:b]
    if len(e) < 2: return np.nan, np.nan, np.nan
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    g = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    r = rf.reindex(e.index, method="ffill").fillna(0) / 365
    b_ = (1 + r).prod() ** (1 / yrs) - 1
    return g, b_, g - b_


def main():
    ent, stats, comp, rf = build_candidates()
    comp.to_parquet(D / "comp.parquet")
    if not len(ent):
        c = comp.dropna(); L = ["Study PCP-HTB output (one run)", f"funnel: {stats}", "confirmed entries: 0 (no strike shows excess >= 10%/yr at t: signal=0)"]
        L.append(f"candidate name-dates with valid conversion quotes: {len(c)}")
        L.append(f"best-strike excess yield per candidate (conversion = buy stock@ask + buy put@offer - sell call@bid, K locked): median {c.best_e.median():.1%} p90 {c.best_e.quantile(.9):.1%} max {c.best_e.max():.1%}; share >= 10%: {(c.best_e>=.10).mean():.1%}")
        L.append(f"DIAGNOSTIC (unjudged) worst-strike excess: median {c.worst_e.median():.1%}")
        L.append(f"mid-implied (r+b) vs OptionMetrics borrowrate at ATM: n={len(c)} pearson={c.bor.corr(c.impl):.3f} spearman={c.bor.corr(c.impl, method='spearman'):.3f}")
        cw = c[(c.impl.abs() < 0.5)]; L.append(f"  winsorized |impl|<50%: n={len(cw)} pearson={cw.bor.corr(cw.impl):.3f} spearman={cw.bor.corr(cw.impl, method='spearman'):.3f}; median impl excess {cw.impl.median():.1%}")
        L.append("per-year candidates: " + str(c.groupby(c.t.dt.year).size().to_dict()))
        L.append("GATE: (1) $10k excess>=8pp False (0.00pp, no trades) (2) False (3) >=100 entries/yr False (0/yr) (4) n/a (5) n/a (6) False (no trades)")
        L.append("VERDICT: KILL"); OUT.write_text("\n".join(L)); print("\n".join(L)); return
    ent.to_parquet(D / "entries.parquet")
    L = []; P = L.append
    P("Study PCP-HTB output (one run)"); P(f"funnel: {stats}")
    P(f"confirmed entries: {len(ent)}")
    if len(ent):
        P("per-year confirmed entries: " + str(ent.groupby(ent.t1.dt.year).size().to_dict()))
        P(f"unique names {ent.secid.nunique()}")
    sig = stats["signal"]; P(f"survival t->t+1: {stats['confirmed']}/{sig} = {stats['confirmed']/max(sig,1):.2%}")
    P(f"dividend exclusions (name-dates): {stats['divexcl']}; delisted before expiry among confirmed: {stats['delist']}")
    if len(comp) > 3:
        c = comp.dropna(); P(f"mid-implied (r+b) vs OptionMetrics borrowrate, ATM: n={len(c)} corr={c.bor.corr(c.impl):.3f} spearman={c.bor.corr(c.impl, method='spearman'):.3f}")
    if len(ent):
        P(f"entry excess yield (t+1): median {ent.e_t1.median():.1%} p90 {ent.e_t1.quantile(.9):.1%} max {ent.e_t1.max():.1%}")
    res = {}
    for cap in (2300, 10000, 25000, 100000):
        eq, tr, ut = simulate(ent, rf, cap); res[cap] = (eq, tr, ut)
        P(f"\n== ${cap}  ==")
        for nm, a, b in (("2005-2015", "2005-01-01", "2015-12-31"), ("2016-2024 (judge)", "2016-01-01", "2024-12-31"), ("2016-20", "2016-01-01", "2020-12-31"), ("2021-24", "2021-01-01", "2024-12-31")):
            g, b_, x = period_excess(eq, rf, a, b); P(f"  {nm}: ret {g:.2%}/yr  tbill {b_:.2%}  excess {x*100:.2f}pp")
        P(f"  mean utilization 2016-24 {ut['2016':'2024'].mean():.1%}; trades {len(tr)}")
    eq, tr, ut = res[10000]
    P("\nper-year $10k excess (pp over T-bill):")
    for y in YEARS:
        g, b_, x = period_excess(eq, rf, f"{y}-01-01", f"{y}-12-31"); P(f"  {y}: ret {g:.2%} excess {x*100:.2f}pp  util {ut[str(y)].mean():.1%}")
    if len(tr):
        tr["name_pnl"] = tr.pnl; top = tr.groupby("secid").pnl.sum().sort_values(ascending=False)
        P("\ntop names by $10k pnl: " + str(top.head(10).round(1).to_dict()))
        eqs, _, _ = simulate(ent, rf, 10000, shock=True)
        P("2x spread shock $10k: 2016-24 excess %.2fpp ; 2005-15 %.2fpp" % (period_excess(eqs, rf, "2016-01-01", "2024-12-31")[2] * 100, period_excess(eqs, rf, "2005-01-01", "2015-12-31")[2] * 100))
        ex5 = ent[~ent.secid.isin(top.head(5).index)]
        eq5, _, _ = simulate(ex5, rf, 10000)
        P("ex-top-5 names $10k: 2016-24 excess %.2fpp" % (period_excess(eq5, rf, "2016-01-01", "2024-12-31")[2] * 100))
        P("\ntop 20 entries by e_t1:"); P(ent.sort_values("e_t1", ascending=False).head(20)[["secid", "t1", "exd", "K", "S1", "A1", "P1", "C1", "cost", "dte", "e_t", "e_t1", "borrow", "oi", "delisted"]].to_string())
        P("\nexample trades (4 prices):"); P(ent.sample(min(5, len(ent)), random_state=0)[["secid", "t1", "exd", "K", "A1", "P1", "C1", "cost", "dte", "e_t1"]].to_string())
    # gate
    ex10 = lambda a, b: period_excess(res[10000][0], rf, a, b)[2] * 100
    g1 = ex10("2016-01-01", "2024-12-31") >= 8; g2 = ex10("2016-01-01", "2020-12-31") > 0 and ex10("2021-01-01", "2024-12-31") > 0
    n16 = ent[ent.t1.dt.year.between(2016, 2024)]
    ppy = len(n16) / 9 if len(n16) else 0
    g3 = ppy >= 100
    g4 = len(tr) and period_excess(eqs, rf, "2016-01-01", "2024-12-31")[2] > 0
    g5 = len(tr) and period_excess(eq5, rf, "2016-01-01", "2024-12-31")[2] > 0
    g6 = ex10("2005-01-01", "2015-12-31") > 0
    P(f"\nGATE: (1) 10k excess>=8pp {g1} ({ex10('2016-01-01','2024-12-31'):.2f}pp) (2) halves>0 {g2} (3) >=100 entries/yr {g3} ({ppy:.1f}/yr 2016-24) (4) 2x shock>0 {bool(g4)} (5) ex-top5>0 {bool(g5)} (6) 2005-15>0 {g6}")
    rest = g2 and g3 and g4 and g5 and g6
    P("VERDICT: " + ("PASS" if g1 and rest else "SMALL" if (not g1 and rest) else "KILL"))
    OUT.write_text("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    if "--pull" in sys.argv: pull_all()
    else: main()
