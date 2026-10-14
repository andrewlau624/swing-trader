"""Study UPG-DAY0 (round1_prose.md "## Study UPG-DAY0"): pre-open IBES upgrade, buy the official open, sell close (A) or scalp (B).
usage: upg_day0.py build | A ERA | B ERA | all          ERA in disc|judge ; output data/research/program/upg_day0_out.txt (appended per stage)
Pre-registered parameters untouched. Disclosed choices (most conservative reading):
 1. IBES rows: usfirm=1, ireccd numeric 1..5 (1=strong buy). Rows with null/00:00:00 anntims dropped (time unknown), counted.
    anntims treated as US Eastern (hour histogram printed; morning peak 06-07h, consistent with ET).
 2. Prior rating = same (ticker, estimid=broker) previous record in time order (own prior); upgrade = ireccd < prior; downgrade >.
    First-ever rating in the pulled window (from 2009-10) has no prior -> not an event. recddet holds the latest revised ireccd (point-in-time
    revisions not recoverable): disclosed limitation.
 3. Pre-open = ts in (16:00:00 strictly after, prior trading day, 09:00 d] with d the next trading day (weekend/holiday notes -> next trading day).
    Control (c) = same-type upgrades with ts in [09:30,16:00) on a trading day.
 4. Link ibcrsphist: ticker, sdate<=anndats<=edate, score<=2 (best score). Firm-days with both an upgrade and a downgrade pre-open are dropped from both sets.
 5. Universe at d-1: CRSP shrcd 10/11 (names.parquet), |prc(d-1)|>=5, 20d median $vol (d-20..d-1, >=15 obs) >= $50M. Event needs openprc>0 and prc!=0 at d
    (missing/zero dropped, counted). Close = |prc|. No dividend adjustment (ex-date drops hurt longs: conservative).
 6. A: ret = |prc|/openprc - 1, cost c per side -> net = ret - 2c. Gate net at 4bp/side. Ceiling = P(day has event) x mean net(4bp/side) x 50% x 250, 100% of account on event days.
 7. Control (b): for each event, non-event days (no upgrade or downgrade pre-open event, in the universe) of the same permno in the same era whose open gap
    (openprc/|prc(d-1)|-1) is in the same decile (deciles of all universe name-days in the era); mean of their open->close returns; events w/o control dropped (counted).
    t = day-clustered t of (event ret - its control mean).
 8. B: 100 random event-days (days with >=1 valid event) per era; all valid events that day traded. Entry open=openprc; TP: first lit trade (ex<>D, size>=100, scond in [@F ]*, tr_corr 00)
    strictly > open*1.005 in 09:30:01..15:55; stop: first NBBO quote with bid>0, ask>bid, bid<=open*0.995 in the same window -> exit at that bid (pays half-spread);
    TP return exactly +50bp (limit fill), tie TP/stop -> stop. Else close = |prc|. 2x = stop exit one extra half-spread. p = TP/(TP+SL) over decided trades,
    p* = (S+h)/(G+S+h) with S=G=50bp and h = mean stop slippage below -50bp (2x for the 2x test). Control (b) for B: each event gets one random matched control day
    (same permno, same gap decile, non-event; RandomState(seed)), same scalp.
 9. Gates (A, B): mean net(2x)>0 with day-clustered t>=2; median>0 (A) / p>p* (B); ex-top-5 >0; both halves (time-ordered halves of events) >0; n>=200; beats ctrl (b) t>=2; ceiling>=8pp (A)."""
import sys, time, re
sys.path.insert(0, "research/sim")
import numpy as np, pandas as pd
from pathlib import Path
from sect_lag import conn, tstat_clustered, LIT_OK, BAD
from iso_burst import link
D = Path("data/research/upg_day0"); OUT = Path("data/research/program/upg_day0_out.txt")
ERA = {"disc": ("2010-01-01", "2014-12-31", 990), "judge": ("2015-01-01", "2019-12-31", 991)}
G = S = 50e-4
LITSQL = "c.ex <> 'D' and c.size >= 100 and coalesce(c.tr_scond,'') ~ '^[@F ]*$'"

def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with open(OUT, "a") as f: f.write(s + "\n")

def build():
    rec = pd.read_parquet(D / "recddet.parquet"); n0 = len(rec)
    rec["ir"] = pd.to_numeric(rec.ireccd, errors="coerce"); rec = rec[rec.ir.between(1, 5)]
    rec["anndats"] = pd.to_datetime(rec.anndats)
    tnull = rec.anntims.isna() | (rec.anntims.astype(str) == "00:00:00")
    log(f"[build] recddet rows {n0}; valid ireccd {len(rec)}; anntims null/00:00:00 dropped {int(tnull.sum())}")
    rec = rec[~tnull].copy()
    rec["ts"] = rec.anndats + pd.to_timedelta(rec.anntims.astype(str))
    log("anntims hour histogram (rows, 2010-19):", rec.ts.dt.hour.value_counts().sort_index().to_dict())
    rec = rec.sort_values(["ticker", "estimid", "ts"]).drop_duplicates(["ticker", "estimid", "ts", "ir"])
    rec["prior"] = rec.groupby(["ticker", "estimid"]).ir.shift(1)
    rec = rec[rec.prior.notna() & (rec.ir != rec.prior)].copy(); rec["kind"] = np.where(rec.ir < rec.prior, "up", "dn")
    log(f"rating changes with a prior: up {int((rec.kind=='up').sum())} dn {int((rec.kind=='dn').sum())}")
    lk = pd.read_parquet(D / "link.parquet"); lk = lk[lk.score <= 2].copy(); lk["sdate"] = pd.to_datetime(lk.sdate); lk["edate"] = pd.to_datetime(lk.edate)
    m = rec.merge(lk[["ticker", "permno", "sdate", "edate", "score"]], on="ticker")
    m = m[(m.anndats >= m.sdate) & (m.anndats <= m.edate)].sort_values("score").drop_duplicates(["ticker", "estimid", "ts"])
    log(f"linked changes {len(m)} of {len(rec)}")
    f = pd.read_parquet(D / "dsf.parquet"); f["date"] = pd.to_datetime(f.date); f["permno"] = f.permno.astype("int64")
    for c in ("openprc", "prc", "vol", "ret"): f[c] = pd.to_numeric(f[c], errors="coerce").astype("float64")
    f = f.sort_values(["permno", "date"]).reset_index(drop=True)
    f["ap"] = f.prc.abs(); f["dv"] = f.ap * f.vol; g = f.groupby("permno")
    f["adv"] = g.dv.transform(lambda s: s.shift(1).rolling(20, min_periods=15).median()); f["pclose"] = g.ap.shift(1)
    nm = pd.read_parquet("data/research/late_flow/names.parquet"); nm["permno"] = nm.permno.astype("int64")
    days = np.array(sorted(f.date.unique())); tdays = pd.DatetimeIndex(days)
    # map ts -> d
    ts = m.ts.values.astype("datetime64[ns]")
    # session class
    day0 = m.ts.dt.normalize()
    pos = tdays.searchsorted(day0)      # first trading day >= calendar date
    isday = np.asarray((pos < len(tdays)) & (tdays[np.minimum(pos, len(tdays) - 1)] == day0.values))
    hh = m.ts.dt.hour + m.ts.dt.minute / 60
    d_idx = np.full(len(m), -1); cls = np.array(["x"] * len(m), dtype=object)
    for i in range(len(m)):
        p = pos[i]
        if isday[i] and 9.5 <= hh.iloc[i] < 16:
            cls[i] = "intra"; d_idx[i] = p
        elif isday[i] and hh.iloc[i] > 16:
            if p + 1 < len(tdays): cls[i] = "pre"; d_idx[i] = p + 1       # after 16:00 -> next trading day pre-open
        elif (not isday[i]) or hh.iloc[i] < 9:
            if p < len(tdays): cls[i] = "pre"; d_idx[i] = p                 # before 09:00 or non-trading day -> first trading day >= date
    m["cls"] = cls; m["d"] = [tdays[j] if j >= 0 else pd.NaT for j in d_idx]
    log("event timing classes:", m.cls.value_counts().to_dict(), "(x = 09:00-09:30 or unmapped, excluded)")
    m = m[m.cls.isin(["pre", "intra"]) & m.d.notna()]
    ev = m.groupby(["permno", "d", "cls"]).kind.agg(lambda s: "both" if s.nunique() > 1 else s.iloc[0]).reset_index()
    ev["n_brokers"] = m.groupby(["permno", "d", "cls"]).estimid.nunique().values
    log("firm-day events (all kinds):", ev.groupby(["cls", "kind"]).size().to_dict())
    ev = ev[ev.kind != "both"]
    # attach prices and universe
    f1 = f[["permno", "date", "openprc", "ap", "prc", "adv", "pclose"]].rename(columns={"date": "d"})
    f1["nxt_close"] = f.groupby("permno").ap.shift(-1).values
    e = ev.merge(f1, on=["permno", "d"], how="left")
    nn = nm[nm.shrcd.isin([10, 11])]
    ok = np.zeros(len(e), bool)
    ng = {p: g for p, g in nn.groupby("permno")}
    for i, (p, d) in enumerate(zip(e.permno.values, e.d.values)):
        g = ng.get(p)
        ok[i] = g is not None and bool(((g.namedt <= d) & (g.nameendt >= d)).any())
    e["common"] = ok
    e["uni"] = e.common & (e.pclose >= 5) & (e.adv >= 50e6)
    log(f"events before universe {len(e)}; in universe {int(e.uni.sum())}")
    u = e[e.uni].copy()
    bad = (~(u.openprc > 0)) | (~(u.ap > 0)); log(f"universe events with missing/zero openprc or prc dropped: {int(bad.sum())} of {len(u)} ({(bad.mean()*100):.1f}%)")
    u = u[~bad]; u["gap"] = u.openprc / u.pclose - 1; u["ret"] = u.ap / u.openprc - 1
    u.to_parquet(D / "events.parquet")
    # universe name-days (for control b and gap deciles)
    nd = f[(f.date >= "2010-01-01") & (f.pclose >= 5) & (f.adv >= 50e6) & (f.openprc > 0) & (f.ap > 0)].rename(columns={"date": "d"}).copy()
    nd["gap"] = nd.openprc / nd.pclose - 1; nd["ret"] = nd.ap / nd.openprc - 1
    nd = nd[nd.permno.isin(nn.permno)]
    nd.loc[:, ["permno", "d", "openprc", "ap", "adv", "pclose", "gap", "ret"]].to_parquet(D / "nameday.parquet")
    log(f"universe name-days {len(nd)}")
    # hand-check sample
    s = m[m.cls == "pre"].sample(10, random_state=7)
    log("10 sample pre-open events (hand check): ticker broker prior->new ts -> d")
    for r in s.itertuples(): log(f"  {r.ticker} {r.estimid} {int(r.prior)}->{int(r.ir)} {r.ts} -> {r.d:%Y-%m-%d}")

def load(era):
    a, b, seed = ERA[era]; ev = pd.read_parquet(D / "events.parquet"); nd = pd.read_parquet(D / "nameday.parquet")
    ev = ev[(ev.d >= a) & (ev.d <= b)]; nd = nd[(nd.d >= a) & (nd.d <= b)].copy()
    return ev, nd, seed

def stats(x, col, label):
    x = x.dropna(subset=[col]).copy(); x['date'] = x['d']; n = len(x)
    if n == 0: log(f"  {label}: n=0"); return
    t = tstat_clustered(x, col); top5 = x[col].sort_values().iloc[:-5].mean() if n > 5 else np.nan
    xs = x.sort_values("d"); h = n // 2
    log(f"  {label}: n {n} mean {x[col].mean()*1e4:+.1f}bp median {x[col].median()*1e4:+.1f} hit {(x[col]>0).mean():.2f} t {t:.2f} ex-top5 {top5*1e4:+.1f} halves {xs[col].iloc[:h].mean()*1e4:+.1f}/{xs[col].iloc[h:].mean()*1e4:+.1f}")
    return dict(n=n, mean=x[col].mean(), median=x[col].median(), t=t, top5=top5, h1=xs[col].iloc[:h].mean(), h2=xs[col].iloc[h:].mean())

def A(era):
    ev, nd, seed = load(era); log(f"\n=== A {era} ===")
    up = ev[(ev.cls == "pre") & (ev.kind == "up") & ev.uni].copy(); dn = ev[(ev.cls == "pre") & (ev.kind == "dn")].copy(); it = ev[(ev.cls == "intra") & (ev.kind == "up")].copy()
    ndays = nd.d.nunique(); eds = up.d.nunique()
    log(f"trading days {ndays}; upgrade events {len(up)} on {eds} days ({len(up)/ndays:.2f}/day, {eds/ndays:.2f} of days with >=1)")
    log("open gap distribution (upgrades): " + str((up.gap.quantile([.05, .25, .5, .75, .95]) * 1e4).round(0).to_dict()) + f"; all name-days: {(nd.gap.quantile([.05,.25,.5,.75,.95])*1e4).round(0).to_dict()}")
    r = {}
    for c in (0, 2, 4):
        up[f"n{c}"] = up.ret - 2 * c * 1e-4
        r[c] = stats(up, f"n{c}", f"A upgrades net at {c}bp/side")
    log("  by $vol bucket (net 2bp/side):")
    for lo, hi in ((50e6, 200e6), (200e6, 1e9), (1e9, 1e15)):
        stats(up[(up.adv >= lo) & (up.adv < hi)], "n2", f"   adv [{lo/1e6:.0f}M,{min(hi,1e12)/1e6:.0f}M)")
    log("  by gap sign (net 2bp/side):")
    stats(up[up.gap > 0], "n2", "   gap>0"); stats(up[up.gap <= 0], "n2", "   gap<=0")
    # control b
    q = np.quantile(nd.gap, np.linspace(0, 1, 11)); q[0] = -9; q[-1] = 9
    nd["dec"] = np.digitize(nd.gap, q[1:-1]); up["dec"] = np.digitize(up.gap, q[1:-1])
    evkeys = set(zip(ev.permno, ev.d)) ; 
    nd["isev"] = [k in evkeys for k in zip(nd.permno, nd.d)]
    ctl = nd[~nd.isev].groupby(["permno", "dec"]).ret.mean().rename("ctl").reset_index()
    up = up.merge(ctl, on=["permno", "dec"], how="left"); nc = int(up.ctl.isna().sum()); upc = up.dropna(subset=["ctl"]).copy()
    upc["diff"] = upc.ret - upc.ctl
    log(f"  control (b) same-firm non-event days, same gap decile: events w/o control dropped {nc}")
    stats(upc, "ret", "   events (matched subset) gross"); stats(upc, "ctl", "   control (b) gross"); rb = stats(upc, "diff", "   event minus control (b)")
    # control a, c
    if len(dn):
        dn = dn.dropna(subset=["ret"]); dn["short"] = -dn.ret; stats(dn[dn.uni], "short", "  control (a) downgrades, SHORT open->close gross (sign check)"); stats(dn[dn.uni], "ret", "  control (a) downgrades, long gross")
    it = it[it.uni]; it["drift"] = it.nxt_close / it.ap - 1
    stats(it, "ret", "  control (c) intraday upgrades: event-day open->close gross (includes pre-announcement part)"); stats(it, "drift", "  control (c) close(d)->close(d+1) drift gross")
    # gate
    x = up.n4; n4 = r[4]; ceil = (eds / ndays) * n4["mean"] * 0.5 * 250 * 100
    ok = dict(mean4=n4["mean"] > 0, t=n4["t"] >= 2, median=up.n4.median() > 0, top5=n4["top5"] > 0, halves=(n4["h1"] > 0 and n4["h2"] > 0), n=len(up) >= 200,
              ctl=(rb is not None and rb["t"] >= 2), ceiling=ceil >= 8)
    log(f"  GATE (net 4bp/side): {ok}; ceiling at $10k = {ceil:+.2f}pp/yr")
    return r[2]["mean"], up, nd, ok

def scalp_day(db, d, rows):
    """rows: DataFrame(permno, openprc, ap) -> dict permno -> (kind, ret1, ret2, hs, t)."""
    sym = link(db, d, list(rows.permno))
    rows = rows[rows.permno.isin(sym)]
    if not len(rows): return {}
    vals = ",".join("('%s','%s',%d,%.6f,%.6f)" % (sym[int(r.permno)][0].replace("'", "''"), sym[int(r.permno)][1].replace("'", "''"), int(r.permno), r.openprc * (1 + G), r.openprc * (1 - S)) for r in rows.itertuples())
    roots = ",".join("'%s'" % r.replace("'", "''") for r in sorted({sym[int(p)][0] for p in rows.permno}))
    ds = d.strftime("%Y%m%d"); y = ds[:4]
    tp = db.raw_sql(f"""with u(root,sfx,pid,up,dn) as (values {vals})
      select u.pid, min(c.time_m)::text t from taqm_{y}.ctm_{ds} c join u on u.root=c.sym_root and u.sfx=coalesce(c.sym_suffix,'')
      where c.sym_root in ({roots}) and c.time_m >= '09:30:01' and c.time_m <= '15:55:00' and c.tr_corr='00' and c.price > u.up and {LITSQL} group by 1""")
    st = db.raw_sql(f"""with u(root,sfx,pid,up,dn) as (values {vals})
      select distinct on (u.pid) u.pid, n.time_m::text t, n.best_bid bb, n.best_ask ba from taqm_{y}.complete_nbbo_{ds} n join u on u.root=n.sym_root and u.sfx=coalesce(n.sym_suffix,'')
      where n.sym_root in ({roots}) and n.time_m >= '09:30:01' and n.time_m <= '15:55:00' and n.best_bid>0 and n.best_ask>n.best_bid and n.best_bid <= u.dn order by u.pid, n.time_m""")
    # first lit trade near the cross, for sanity: skipped (cross vs CRSP openprc checked via TP/stop rates)
    sec = lambda s: pd.to_timedelta(s).total_seconds()
    tpt = {int(r.pid): sec(r.t) for r in tp.itertuples()}; stt = {int(r.pid): (sec(r.t), float(r.bb), float(r.ba)) for r in st.itertuples()}
    out = {}
    for r in rows.itertuples():
        p = int(r.permno); a = tpt.get(p, np.inf); b = stt.get(p, (np.inf, 0, 0))
        ret_to = r.ap / r.openprc - 1
        if a < b[0]: out[p] = ("TP", G, G, 0.0, a)
        elif b[0] < np.inf:
            hs = (b[2] - b[1]) / 2; out[p] = ("SL", b[1] / r.openprc - 1, (b[1] - hs) / r.openprc - 1, hs / r.openprc, b[0])
        else: out[p] = ("TO", ret_to, ret_to, 0.0, np.nan)
    return out

def B(era, up, nd, a_ok):
    a, b, seed = ERA[era]; log(f"\n=== B {era} (100 random event-days, seed {seed}) ===")
    days = sorted(up.d.unique()); rs = np.random.RandomState(seed)
    pick = sorted(rs.choice(len(days), size=min(100, len(days)), replace=False)); sel = [days[i] for i in pick]
    evs = up[up.d.isin(sel)].copy()
    # control day per event
    ndn = nd[~nd.isev]; grp = {k: g for k, g in ndn.groupby(["permno", "dec"])}
    crow = []
    for r in evs.itertuples():
        g = grp.get((r.permno, r.dec))
        if g is None or not len(g): continue
        rr = np.random.RandomState((seed * 7919 + int(r.permno) * 31 + r.d.toordinal()) % (2**31 - 1)); c = g.iloc[rr.randint(len(g))]
        crow.append(dict(permno=int(r.permno), d=c.d, openprc=c.openprc, ap=c.ap, evd=r.d))
    cdf = pd.DataFrame(crow)
    db = conn(); res = []
    t0 = time.time()
    for kind, df in (("event", evs), ("control", cdf)):
        for d, g in df.groupby("d"):
            try: o = scalp_day(db, pd.Timestamp(d), g[["permno", "openprc", "ap"]])
            except Exception as e:
                log(f"  ERR {kind} {d:%Y-%m-%d}: {e!r}")
                try: db.close()
                except Exception as e2: log(f"  close failed: {e2!r}")
                db = conn(); continue
            for p, (k, r1, r2, hs, tt) in o.items(): res.append(dict(kind=kind, d=pd.Timestamp(d), permno=p, out=k, r1=r1, r2=r2, hs=hs))
        log(f"  {kind} pulled {time.time()-t0:.0f}s")
    db.close()
    R = pd.DataFrame(res); R.to_parquet(D / f"scalp_{era}.parquet")
    for kind in ("event", "control"):
        x = R[R.kind == kind].copy()
        if not len(x): log(f"  {kind}: no rows"); continue
        tp_, sl_, to_ = (x.out == "TP").sum(), (x.out == "SL").sum(), (x.out == "TO").sum()
        h = x[x.out == "SL"].apply(lambda r: max(-(r.r1 + S), 0), axis=1).mean() if sl_ else 0.0
        hsm = x[x.out == "SL"].hs.mean() if sl_ else 0.0
        p = tp_ / max(1, tp_ + sl_); ps1 = (S + h) / (G + S + h); ps2 = (S + 2 * h) / (G + S + 2 * h)
        log(f"  {kind}: n {len(x)} TP {tp_} SL {sl_} TO {to_}; p(TP/(TP+SL)) {p:.3f}; p* 1x {ps1:.3f} 2x {ps2:.3f}; mean stop slippage past -50bp {h*1e4:.1f}bp, mean stop half-spread {hsm*1e4:.1f}bp")
        x["d"] = x.d; stats(x, "r1", f"   {kind} net 1x"); stats(x, "r2", f"   {kind} net 2x")
    if (R.kind == "control").any():
        e = R[R.kind == "event"].copy(); c = R[R.kind == "control"].copy()
        log(f"  control (b) scalp mean net1x {c.r1.mean()*1e4:+.1f}bp vs event {e.r1.mean()*1e4:+.1f}bp (n ctl {len(c)})")
        # event minus its own control: events map to the control rows by permno (+ order); use event-day clustered diff of means per event day
        m = e.merge(pd.DataFrame(crow).rename(columns={"d": "cd", "evd": "d"})[["permno", "d", "cd"]], on=["permno", "d"], how="left")
        cc = c.rename(columns={"d": "cd", "r2": "c2", "r1": "c1"})[["permno", "cd", "c1", "c2"]].drop_duplicates(["permno", "cd"])
        m = m.merge(cc, on=["permno", "cd"], how="inner"); m["diff"] = m.r2 - m.c2
        stats(m, "diff", "   event minus control (b), 2x"); 
    return R

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stage = sys.argv[1]
    if stage == "build": build(); return
    if stage == "disc":
        m2, up, nd, ok = A("disc")
        log(f"\nEARLY KILL CHECK: discovery A mean net at 2bp/side = {m2*1e4:+.2f}bp -> {'KILL, judge era unopened' if m2 < 0 else 'continue'}")
        if m2 < 0: return
        B("disc", up, nd, ok); return
    if stage == "judge":
        m2, up, nd, ok = A("judge"); R = B("judge", up, nd, ok)

if __name__ == "__main__": main()
