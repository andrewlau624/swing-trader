"""Study REC-RECALL (round1_prose.md "### REC-RECALL (N 1061)"): pre-ex-date covering window in hard-to-borrow dividend payers.
Rule: buy the closing cross at E-5, sell the closing cross at E-1 (E = CRSP ex-date, distcd 12xx), in names whose option-implied
borrow fee (optionm.borrate, nearest-30d tenor, -99.99 dropped) as of E-6 is in the top decile of that month's cross-section.
Eligible: prev close (E-6) >= $5, $ADV20 (E-6) >= $5M. Period 2001-2024. Net = tier 5bp/side (10bp RT).
usage: PYTHONPATH=. .venv/bin/python -m research.sim.rec_recall pull [--part link|dsf|borrate]
       PYTHONPATH=. .venv/bin/python -m research.sim.rec_recall run
"""
from __future__ import annotations
import sys, time, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data/research/rec_recall"
OUT = ROOT / "data/research/program/rec_recall_out.txt"
U = "andrewlau624"
Y0, Y1 = 2001, 2024
COST_BP = 10.0  # tier 5bp/side
HOLD = 4        # sessions E-5 -> E-1
PLACEBO_SHIFT = 5  # E-10 -> E-6, fee as of E-11


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f: f.write(s + "\n")


# ----------------------------------------------------------------------------------------------------------------- pull
def connect():
    import wrds
    last = None
    for k in range(4):
        try:
            return wrds.Connection(wrds_username=U, wrds_connect_attempts=2)
        except BaseException as e:  # noqa: BLE001
            last = e; time.sleep(min(60, 5 * (k + 1)))
    raise RuntimeError(f"wrds connect failed: {last}")


def pull_link(db):
    f = D / "link.parquet"
    if f.exists(): return pd.read_parquet(f)
    t = db.raw_sql("select secid, sdate, edate, permno, score from wrdsapps_link_crsp_optionm.opcrsphist where score = 1")
    t.to_parquet(f, index=False); return t


def pull_dist(db):
    f = D / "dsedist.parquet"
    if f.exists(): return pd.read_parquet(f)
    t = db.raw_sql(f"""select permno, distcd, divamt, dclrdt, exdt, rcrddt, paydt from crsp.dsedist
                       where distcd between 1200 and 1299 and exdt between '{Y0}-01-01' and '{Y1}-12-31'""")
    t.to_parquet(f, index=False); return t


def pull_dsf_year(db, y):
    f = D / f"dsf_{y}.parquet"
    if f.exists(): return pd.read_parquet(f)
    # names ever linked to OptionMetrics (score 1); one calendar year, with the trailing Dec for the ADV20 / E-6 lookback
    sql = f"""select d.permno, d.date, d.prc, d.vol, d.ret, d.cfacpr from crsp.dsf d
              where d.date between '{y}-01-01' and '{y}-12-31'
                and exists (select 1 from wrdsapps_link_crsp_optionm.opcrsphist l where l.permno = d.permno and l.score = 1)"""
    t = db.raw_sql(sql)
    t.to_parquet(f, index=False); return t


def pull_borrate_year(db, y):
    f = D / f"borrate_{y}.parquet"
    if f.exists(): return pd.read_parquet(f)
    # daily, nearest-to-30-day expiration per (securityid, date), sentinel -99.99 dropped first (borrow_xs.py precedent)
    sql = f"""select distinct on (securityid, date) securityid, date, expirationdate, days, borrowrate
              from optionm.borrate{y} where borrowrate <> -99.99 and borrowrate is not null
              order by securityid, date, abs(days - 30), expirationdate"""
    t = db.raw_sql(sql)
    t.to_parquet(f, index=False); return t


def pull(part="all"):
    D.mkdir(parents=True, exist_ok=True)
    db = connect()
    if part in ("all", "link"):
        t = pull_link(db); print("link rows", len(t), "permnos", t.permno.nunique(), "secids", t.secid.nunique(), flush=True)
        t = pull_dist(db); print("dsedist rows", len(t), "permnos", t.permno.nunique(), flush=True)
    for y in range(Y0 - 1, Y1 + 1):
        if part in ("all", "dsf"):
            t0 = time.time(); t = pull_dsf_year(db, y); print(f"dsf {y} rows {len(t):,} permnos {t.permno.nunique():,} {time.time()-t0:.0f}s", flush=True)
        if part in ("all", "borrate") and y >= Y0:
            t0 = time.time(); t = pull_borrate_year(db, y); print(f"borrate {y} rows {len(t):,} secids {t.securityid.nunique():,} {time.time()-t0:.0f}s", flush=True)


# ----------------------------------------------------------------------------------------------------------------- stats
def clus_t(x, g):
    """cluster-robust t of the mean (clusters g)."""
    x = np.asarray(x, float); g = np.asarray(g)
    m = np.isfinite(x); x, g = x[m], g[m]
    n = len(x)
    if n < 3: return float("nan")
    xb = x.mean()
    s = pd.Series(x - xb).groupby(g).sum()
    se = np.sqrt((s ** 2).sum()) / n
    return xb / se if se > 0 else float("nan")


def nstats(x, g):
    x = pd.Series(np.asarray(x, float)); g = np.asarray(g)
    m = x.notna().values; x, g = x[m], g[m]
    if len(x) == 0: return "n 0"
    srt = np.sort(x.values)[::-1]
    ex5 = (x.sum() - srt[:5].sum()) / max(len(x) - 5, 1) if len(x) > 5 else float("nan")
    return (f"n {len(x):5d} mean {x.mean():+7.1f} med {x.median():+7.1f} hit {np.mean(x > 0):.2f} "
            f"t {clus_t(x, g):+5.2f} ex-top5 {ex5:+7.1f} clusters {len(set(g))}")


def load_all():
    link = pd.read_parquet(D / "link.parquet")
    link["sdate"] = pd.to_datetime(link.sdate); link["edate"] = pd.to_datetime(link.edate)
    link["permno"] = link.permno.astype(int); link["secid"] = link.secid.astype(int)
    dist = pd.read_parquet(D / "dsedist.parquet")
    dist["exdt"] = pd.to_datetime(dist.exdt); dist["permno"] = dist.permno.astype(int)
    dsf = pd.concat([pd.read_parquet(D / f"dsf_{y}.parquet") for y in range(Y0 - 1, Y1 + 1)], ignore_index=True)
    dsf["date"] = pd.to_datetime(dsf.date); dsf["permno"] = dsf.permno.astype(int)
    for c in ("prc", "vol", "ret"): dsf[c] = pd.to_numeric(dsf[c], errors="coerce")
    br = pd.concat([pd.read_parquet(D / f"borrate_{y}.parquet").assign(yr=y) for y in range(Y0, Y1 + 1)], ignore_index=True)
    br["date"] = pd.to_datetime(br.date); br["securityid"] = br.securityid.astype(int)
    br["borrowrate"] = pd.to_numeric(br.borrowrate, errors="coerce")
    return link, dist, dsf, br


def build_panel(dsf):
    """per (permno,date): close, prevclose, adv20 (as of that date), 4-session fwd ret (close t -> close t+4), via CRSP ret."""
    dsf = dsf.sort_values(["permno", "date"]).reset_index(drop=True)
    dsf["close"] = dsf.prc.abs()
    dsf["dv"] = dsf.close * dsf.vol
    g = dsf.groupby("permno", sort=False)
    dsf["adv20"] = g["dv"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    lr = np.log1p(dsf.ret.fillna(0.0))
    lr[dsf.ret.isna()] = np.nan
    dsf["lr"] = lr
    cum = g["lr"].cumsum()
    dsf["cum"] = cum
    # fwd4 from close(t) to close(t+4): cum(t+4) - cum(t); requires contiguous rows (checked via session index below)
    dsf["cum4"] = g["cum"].shift(-HOLD)
    dsf["date4"] = g["date"].shift(-HOLD)
    dsf["fwd4"] = np.expm1(dsf.cum4 - dsf.cum)
    return dsf


def main_run():
    log(f"\nREC-RECALL (N 1061)  run {pd.Timestamp.today():%Y-%m-%d %H:%M}  period {Y0}-{Y1}  rule: buy close E-5, sell close E-1, "
        f"fee decile as of E-6 (monthly cross-section), elig prev close>=$5 & ADV20>=$5M, net {COST_BP:.0f}bp RT")
    link, dist, dsf, br = load_all()
    cal = np.array(sorted(dsf.date.unique()))
    cal_idx = pd.Series(np.arange(len(cal)), index=cal)
    log(f"calendar sessions {len(cal)} {pd.Timestamp(cal[0]):%Y-%m-%d}..{pd.Timestamp(cal[-1]):%Y-%m-%d}; dsf rows {len(dsf):,} permnos {dsf.permno.nunique():,}")

    # --- borrate: secid -> permno via link (score 1, date-ranged), fee in %/yr
    log("borrate raw: rate scale check (fraction/yr in table; printed as %/yr): median raw", f"{br.borrowrate.median():.4f}",
        "p90", f"{br.borrowrate.quantile(.9):.4f}")
    br["fee"] = br.borrowrate * 100.0
    cov = br.groupby("yr").agg(rows=("fee", "size"), secids=("securityid", "nunique"), medfee=("fee", "median"), p90=("fee", lambda s: s.quantile(.9)))
    log("borrate coverage by year (rows, secids, median fee %, p90 fee %):")
    for y, r in cov.iterrows(): log(f"  {y}: rows {int(r.rows):>9,} secids {int(r.secids):>5,} med {r.medfee:6.2f} p90 {r.p90:6.2f}")
    brl = br.merge(link[["secid", "permno", "sdate", "edate"]], left_on="securityid", right_on="secid", how="inner")
    brl = brl[(brl.date >= brl.sdate) & (brl.date <= brl.edate.fillna(pd.Timestamp("2100-01-01")))]
    brl = brl.drop_duplicates(["permno", "date"], keep="last")[["permno", "date", "fee", "days"]]
    log(f"borrate linked to permno: rows {len(brl):,} permnos {brl.permno.nunique():,} (unlinked secid-days dropped: {len(br)-len(brl):,})")

    # --- monthly cross-section breakpoints: each permno's last fee observation in the calendar month -> decile edges
    brl["ym"] = brl.date.dt.to_period("M")
    last_m = brl.sort_values("date").groupby(["permno", "ym"]).tail(1)
    edges = last_m.groupby("ym")["fee"].quantile([i / 10 for i in range(1, 10)]).unstack()
    edges.columns = [f"q{i}" for i in range(1, 10)]

    def decile_of(fee, ym):
        e = edges.reindex(ym).values  # (n, 9)
        f = np.asarray(fee, float)[:, None]
        return 1 + (f > e).sum(axis=1)

    # --- panel of eligible name-days with fee as of date (last available on or before, within 31 calendar days)
    pan = build_panel(dsf)
    pan = pan.merge(brl[["permno", "date", "fee"]], on=["permno", "date"], how="left")
    pan = pan.sort_values(["permno", "date"]).reset_index(drop=True)
    g = pan.groupby("permno", sort=False)
    pan["fee_asof"] = g["fee"].ffill()
    pan["fee_date"] = pan.date.where(pan.fee.notna())
    pan["fee_date"] = g["fee_date"].ffill()
    stale = (pan.date - pan.fee_date).dt.days
    pan.loc[stale > 31, "fee_asof"] = np.nan
    pan["ym"] = pan.date.dt.to_period("M")
    ok = pan.fee_asof.notna() & pan.ym.isin(edges.index)
    pan["dec"] = np.nan
    pan.loc[ok, "dec"] = decile_of(pan.loc[ok, "fee_asof"], pan.loc[ok, "ym"])
    pan["elig"] = (pan.close >= 5) & (pan.adv20 >= 5e6) & pan.dec.notna()
    # sign assert: D10 must carry the highest mean fee
    mf = pan[pan.elig].groupby("dec")["fee_asof"].mean()
    assert mf.idxmax() == 10 and mf.is_monotonic_increasing, f"decile labels inverted? {mf.to_dict()}"
    log("decile mean fee (%/yr, eligible name-days): " + " ".join(f"D{int(k)}={v:.1f}" for k, v in mf.items()))

    # universe 4-session returns per (decile, signal date d): next-session entry (d+1 close) -> d+5 close; keyed by signal date = E-6
    # entry close is session after signal date: fwd4 measured from close(d+1) to close(d+5)
    pan["sidx"] = cal_idx.reindex(pan.date).values
    pan["sidx_next"] = g["sidx"].shift(-1)
    pan["fwd4_next"] = g["fwd4"].shift(-1)            # close(d+1) -> close(d+5)
    pan["sidx_next4"] = g["sidx"].shift(-1 - HOLD)
    contig = (pan.sidx_next == pan.sidx + 1) & (pan.sidx_next4 == pan.sidx + 1 + HOLD)
    pan["u_ret"] = np.where(contig, pan.fwd4_next, np.nan)
    uni = pan[pan.elig & pan.u_ret.notna()]
    uni_dec = uni.groupby(["date", "dec"])["u_ret"].agg(["mean", "size"]).rename(columns={"mean": "bench_b", "size": "nb"})
    uni_dec_all = uni.groupby("dec")["u_ret"].agg(["mean", "median", "size"])
    log("unconditional 4-session return by fee decile (eligible universe, all name-days, bp, gross):")
    for k, r in uni_dec_all.iterrows(): log(f"  D{int(k):<2d} fee {mf[k]:5.1f}%  mean {r['mean']*1e4:+6.1f} med {r['median']*1e4:+6.1f} n {int(r['size']):,}")

    # --- events: ordinary cash dividends, E on calendar, in linked permnos
    ev = dist[(dist.distcd // 100 == 12)].copy()
    ev = ev.drop_duplicates(["permno", "exdt"])
    n_all = len(ev)
    ev = ev[ev.permno.isin(link.permno.unique())]
    n_linked = len(ev)
    ev = ev[ev.exdt.isin(cal_idx.index)]
    ev["eidx"] = cal_idx.reindex(ev.exdt).values.astype(int)
    log(f"events: 12xx ex-dates {Y0}-{Y1}: {n_all:,}; in OptionMetrics-linked permnos: {n_linked:,}; ex-date on calendar: {len(ev):,}")
    key = pan.set_index(["permno", "sidx"])

    def window(ev, shift):
        """signal at E-6-shift, entry close E-5-shift, exit close E-1-shift. returns frame with event return + benchmarks."""
        e = ev.copy()
        e["s_idx"] = e.eidx - 6 - shift
        e["in_idx"] = e.eidx - 5 - shift
        e = e[e.s_idx >= 0]
        sig = key.reindex(list(zip(e.permno, e.s_idx)))
        e["sig_date"] = sig.date.values; e["fee"] = sig.fee_asof.values; e["dec"] = sig.dec.values
        e["elig"] = sig.elig.values; e["close_sig"] = sig.close.values; e["adv20"] = sig.adv20.values
        e["ret"] = sig.u_ret.values
        e["in_date"] = cal[e.in_idx.clip(0, len(cal) - 1)]
        return e

    def analyse(e, label):
        log(f"\n== {label} ==")
        e = e[e.sig_date.notna()]
        n_rows = len(e); n_elig = int(e.elig.sum()); n_fee = int(e.fee.notna().sum())
        e = e[e.elig.astype(bool) & e.ret.notna()].copy()
        log(f"events with a panel row at signal date {n_rows:,}; with fee {n_fee:,}; eligible (px>=5, ADV20>=5M, fee) with full window {len(e):,}")
        # benchmark (a): same name, same year, non-event 4-session windows (windows overlapping [E-5,E-1] of any 12xx event excluded)
        e["year"] = e.exdt.dt.year
        bad = set()
        for p, i0 in zip(ev.permno.values, ev.eidx.values):
            for k in range(-5 - HOLD, 0): bad.add((p, i0 + k))   # start indices whose window [s, s+4] overlaps [E-5, E-1]
        pw = pan[pan.fwd4.notna() & pan.elig]
        pw = pw[~pd.MultiIndex.from_arrays([pw.permno, pw.sidx]).isin(bad)]
        pw = pw.assign(year=pw.date.dt.year)
        ba = pw.groupby(["permno", "year"])["fwd4"].mean().rename("bench_a")
        e = e.merge(ba, left_on=["permno", "year"], right_index=True, how="left")
        e = e.merge(uni_dec, left_on=["sig_date", "dec"], right_index=True, how="left")
        e["raw_bp"] = e.ret * 1e4
        e["xa_bp"] = (e.ret - e.bench_a) * 1e4 - COST_BP
        e["xb_bp"] = (e.ret - e.bench_b) * 1e4 - COST_BP
        e["net_bp"] = e.raw_bp - COST_BP
        g = e.in_date.values
        log("decile table (events; mean fee %; net raw; excess vs own-name non-event (a); excess vs same-decile universe (b); all net of 10bp):")
        for k in range(1, 11):
            s = e[e.dec == k]
            if len(s) == 0: log(f"  D{k:<2d} n 0"); continue
            log(f"  D{k:<2d} fee {s.fee.mean():5.1f}%  n {len(s):5d}  net {s.net_bp.mean():+6.1f}  xa {s.xa_bp.mean():+6.1f} (t {clus_t(s.xa_bp, s.in_date):+4.2f})"
                f"  xb {s.xb_bp.mean():+6.1f} (t {clus_t(s.xb_bp, s.in_date):+4.2f})  bench_b {s.bench_b.mean()*1e4:+6.1f}")
        d10 = e[e.dec == 10]
        for col, nm in (("net_bp", "D10 net raw"), ("xa_bp", "D10 excess (a) own-name"), ("xb_bp", "D10 excess (b) decile-universe")):
            log(f"  {nm:32s} ALL      {nstats(d10[col], d10.in_date)}")
            for h, (a, b) in (("2001-12", (2001, 2012)), ("2013-24", (2013, 2024))):
                s = d10[(d10.year >= a) & (d10.year <= b)]
                log(f"  {nm:32s} {h}  {nstats(s[col], s.in_date)}")
        m = lambda k, c: e[e.dec == k][c].mean()
        for c in ("xa_bp", "xb_bp"):
            log(f"  monotone {c}: D10 {m(10,c):+.1f} > D5 {m(5,c):+.1f} > D1 {m(1,c):+.1f} -> {m(10,c) > m(5,c) > m(1,c)}")
        log("  D10 events per year: " + " ".join(f"{y}:{n}" for y, n in d10.groupby("year").size().items()))
        return e, d10

    e_main, d10 = analyse(window(ev, 0), "MAIN: buy close E-5 -> sell close E-1, fee as of E-6")
    e_plc, d10p = analyse(window(ev, PLACEBO_SHIFT), "PLACEBO: buy close E-10 -> sell close E-6, fee as of E-11")

    # --- window specificity: same event, main window minus placebo window (paired), D10 only
    log("\n== paired main - placebo (same event, D10 at its own signal date in each) ==")
    pr = d10[["permno", "exdt", "net_bp", "xa_bp", "xb_bp", "in_date", "year"]].merge(
        d10p[["permno", "exdt", "net_bp", "xa_bp", "xb_bp"]], on=["permno", "exdt"], suffixes=("", "_p"))
    for c in ("net_bp", "xa_bp", "xb_bp"):
        d = pr[c] - pr[c + "_p"]
        log(f"  {c:7s} main-placebo  {nstats(d, pr.in_date)}")
    # --- concentration: distinct names, top contributors, by-year excess (a)
    log("\n== D10 concentration ==")
    log(f"  distinct permnos {d10.permno.nunique()}; events {len(d10)}; events/permno median {d10.groupby('permno').size().median():.0f}")
    top = d10.groupby("permno").agg(n=("xa_bp", "size"), sum_xa=("xa_bp", "sum"), mean_xa=("xa_bp", "mean"), fee=("fee", "mean")).sort_values("n", ascending=False).head(10)
    for p_, r in top.iterrows(): log(f"  permno {p_} n {int(r.n)} mean xa {r.mean_xa:+.1f} fee {r.fee:.1f}%")
    byy = d10.groupby("year").agg(n=("xa_bp", "size"), xa=("xa_bp", "mean"), xb=("xb_bp", "mean"), fee=("fee", "mean"))
    log("  D10 by year (n, xa, xb, mean fee %): " + " ".join(f"{y}:{int(r.n)}/{r.xa:+.0f}/{r.xb:+.0f}/{r.fee:.0f}" for y, r in byy.iterrows()))
    # ex-dividend-artifact check: fee at E-6 vs the same name's fee 30 sessions earlier (is the top-decile fee a pre-dividend spike?)
    lag = key.reindex(list(zip(d10.permno, d10.eidx - 36)))
    dlt = pd.to_numeric(d10.fee, errors="coerce").values.astype(float) - pd.to_numeric(lag.fee_asof, errors="coerce").values.astype(float)
    log(f"  D10 fee at E-6 minus fee at E-36 (same name): mean {np.nanmean(dlt):+.1f}pp med {np.nanmedian(dlt):+.1f}pp "
        f"share up {np.nanmean(dlt > 0):.2f} (n {np.isfinite(dlt).sum()})")

    # --- verdict vs registered bars (both benchmarks)
    log("\n== verdict vs registered bars (D10, net 10bp) ==")
    for col, nm in (("xa_bp", "excess (a) own-name"), ("xb_bp", "excess (b) decile-universe")):
        x = d10[col].dropna(); t = clus_t(x, d10.loc[x.index, "in_date"])
        h1 = d10[d10.year <= 2012][col].mean(); h2 = d10[d10.year >= 2013][col].mean()
        srt = np.sort(x.values)[::-1]; ex5 = (x.sum() - srt[:5].sum()) / (len(x) - 5)
        mono = e_main[e_main.dec == 10][col].mean() > e_main[e_main.dec == 5][col].mean() > e_main[e_main.dec == 1][col].mean()
        mean = x.mean()
        p = mean >= 40 and t >= 2 and x.median() > 0 and h1 > 0 and h2 > 0 and ex5 > 0 and mono
        w = (not p) and 20 <= mean < 40 and t >= 2
        v = "PASS" if p else ("WEAK" if w else "KILL")
        log(f"  {nm}: mean {mean:+.1f} t {t:+.2f} med {x.median():+.1f} h1 {h1:+.1f} h2 {h2:+.1f} ex5 {ex5:+.1f} mono {mono} -> {v}")
    log("Disclosed: daily CRSP closes stand in for the closing cross; CRSP ret (total return) compounds the 4 sessions; fee = last borrate on or "
        "before E-6 within 31 calendar days; deciles = each permno's last fee in the calendar month of E-6 (breakpoints refit monthly); "
        "benchmark (a) uses eligible non-event windows of the same name-year; t clustered by entry date (E-5).")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "pull":
        part = sys.argv[sys.argv.index("--part") + 1] if "--part" in sys.argv else "all"
        pull(part)
    else:
        main_run()
