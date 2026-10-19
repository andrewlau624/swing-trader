"""Study BK-EMERGE-GV runner (pre-registered 2026-10-17, N 1019 -> 1020). One run, no tuning.
Chapter 11 emergence equity: old permno dlstcd 574 -> new permno (same gvkey via CCM LU/LC) first trading <=36m later.
Entry close of 5th trading day of new permno, hold 120 trading days (dlret on delisting), excess vs CRSP EW size decile
(erdport1.decret of the permno's own decile on each day), 50bp/side cost, 2x column.
Usage: .venv/bin/python -m research.sim.bk_emerge ; cache data/research/bk_emerge/ ; out data/research/program/bk_emerge_out.txt
"""
import sys, pathlib, numpy as np, pandas as pd
from research.sim.borrow_xs import conn

D = pathlib.Path("data/research/bk_emerge"); D.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path("data/research/program/bk_emerge_out.txt")
LOG = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); LOG.append(s)

HOLD, ENTRY_DAY, COST = 120, 5, 0.005
nm = pd.read_pickle(D / "names.pkl"); dl = pd.read_pickle(D / "delist.pkl"); lk = pd.read_pickle(D / "link.pkl"); fd = pd.read_pickle(D / "firstdate.pkl")
dl["dlstdt"] = pd.to_datetime(dl.dlstdt); fd["d0"] = pd.to_datetime(fd.d0)
for c in ["namedt", "nameendt"]: nm[c] = pd.to_datetime(nm[c])
lk["lpermno"] = lk.lpermno.astype(int)
dlr = dl.dropna(subset=["dlstdt"]).set_index("permno")
lastname = nm.sort_values("namedt").groupby("permno").last()

def build(codes, how):
    old = dl[dl.dlstcd.isin(codes)][["permno", "dlstdt", "dlstcd"]]
    if how == "gvkey":
        L = lk[["gvkey", "lpermno"]].drop_duplicates()
        g = old.merge(L, left_on="permno", right_on="lpermno").drop(columns="lpermno")
        c = g.merge(L, on="gvkey").rename(columns={"lpermno": "new"})
    else:  # CUSIP-6 continuity (ncusip history of the old permno)
        n6 = nm.dropna(subset=["ncusip"]).assign(c6=lambda d: d.ncusip.str[:6])[["permno", "c6"]].drop_duplicates()
        g = old.merge(n6, on="permno")
        c = g.merge(n6.rename(columns={"permno": "new"}), on="c6")
        c["gvkey"] = c.c6
    c = c[c.new != c.permno].merge(fd[["permno", "d0"]].rename(columns={"permno": "new"}), on="new")
    c = c[(c.d0 > c.dlstdt) & (c.d0 <= c.dlstdt + pd.DateOffset(months=36))]
    c = c.sort_values("dlstdt").drop_duplicates("new")  # one event per new permno (earliest old delist)
    c["oldname"] = c.permno.map(lastname.comnam); c["newname"] = c.new.map(lastname.comnam)
    return c.reset_index(drop=True)

def load_panel(db, permnos):
    f = D / "panel.pkl"
    have = pd.read_pickle(f) if f.exists() else {}
    need = [p for p in permnos if p not in have]
    if need:
        ids = ",".join(str(int(p)) for p in need)
        a = db.raw_sql(f"select permno,date,ret,prc from crsp.dsf where permno in ({ids}) order by permno,date")
        b = db.raw_sql(f"select permno,date,capn,decret from crsp.erdport1 where permno in ({ids})")
        a["date"] = pd.to_datetime(a.date); b["date"] = pd.to_datetime(b.date)
        a = a.merge(b, on=["permno", "date"], how="left")
        a["prc"] = pd.to_numeric(a.prc, errors="coerce").abs()
        for c in ["ret", "capn", "decret"]: a[c] = pd.to_numeric(a[c], errors="coerce")
        for p, d in a.groupby("permno"): have[p] = d.reset_index(drop=True)
        for p in need: have.setdefault(p, pd.DataFrame(columns=a.columns))
        pd.to_pickle(have, f)
    return have

def run_events(ev, panel):
    rows = []
    for r in ev.itertuples():
        d = panel[r.new]
        if len(d) < ENTRY_DAY: rows.append(dict(new=r.new, skip="no_bars")); continue
        e = d.iloc[ENTRY_DAY - 1]
        sh = lastname.shrcd.get(r.new)
        # shrcd as of entry date
        nn = nm[(nm.permno == r.new) & (nm.namedt <= e.date)].sort_values("namedt")
        shr = nn.shrcd.iloc[-1] if len(nn) else sh
        exch = nn.exchcd.iloc[-1] if len(nn) else np.nan
        base = dict(new=r.new, old=r.permno, oldname=r.oldname, newname=r.newname, dlstdt=r.dlstdt, first=r.d0,
                    entry=e.date, px=e.prc, shrcd=shr, exchcd=exch, dlstcd=r.dlstcd)
        if shr not in (10, 11): rows.append({**base, "skip": "shrcd"}); continue
        if not (e.prc >= 1): rows.append({**base, "skip": "px<1"}); continue
        w = d.iloc[ENTRY_DAY: ENTRY_DAY + HOLD]
        # delisting inside window: last bar of permno + dlret
        short = len(w) < HOLD
        ret = w.ret.fillna(0).values; dec = w.decret.fillna(0).values
        # missing decile at entry -> no benchmark
        cap = e.capn
        gross = np.prod(1 + ret) - 1; bm = np.prod(1 + dec) - 1
        dlret_used = np.nan; delisted = False
        if short and r.new in dlr.index:
            x = dlr.loc[r.new]
            x = x.iloc[-1] if isinstance(x, pd.DataFrame) else x
            if pd.notna(x.dlstdt) and x.dlstdt <= d.date.iloc[-1] + pd.Timedelta(days=10):
                delisted = True
                dlret_used = x.dlret if pd.notna(pd.to_numeric(x.dlret, errors="coerce")) else (-0.30 if 500 <= x.dlstcd < 600 else 0.0)
                gross = (1 + gross) * (1 + float(dlret_used)) - 1
        if short and not delisted and len(w) == 0:
            rows.append({**base, "skip": "no_window"}); continue
        rows.append({**base, "skip": "", "n_days": len(w), "delisted": delisted, "dlret": dlret_used, "cap_dec": cap,
                     "raw": gross, "bm": bm, "exc": gross - bm, "short_window": short and not delisted})
    return pd.DataFrame(rows)

def stats(x, label, scale_cost=1.0):
    z = x.copy(); z["net"] = z.exc - 2 * COST * scale_cost
    n = len(z)
    if n == 0: P(label, "n=0"); return {}
    h1 = z[z.entry < "2008-01-01"]; h2 = z[z.entry >= "2008-01-01"]
    t5 = z.sort_values("exc", ascending=False).iloc[5:]
    s = dict(n=n, years=(z.entry.max() - z.entry.min()).days / 365.25,
             mean_raw=z.raw.mean(), med_raw=z.raw.median(), mean_exc=z.exc.mean(), med_exc=z.exc.median(), hit_exc=(z.exc > 0).mean(),
             net=z.net.mean(), net2=(z.exc - 4 * COST).mean(), h1=h1.net.mean(), h1n=len(h1), h2=h2.net.mean(), h2n=len(h2),
             ex5=t5.net.mean(), worst=z.exc.min(), best=z.exc.max(), hit_raw=(z.raw > 0).mean())
    s["t"] = z.net.mean() / (z.net.std(ddof=1) / np.sqrt(n)) if n > 2 else np.nan
    P(f"{label}: n={n} mean_raw={s['mean_raw']:+.3f} med_raw={s['med_raw']:+.3f} mean_exc={s['mean_exc']:+.3f} med_exc={s['med_exc']:+.3f} hit_exc={s['hit_exc']:.2f} hit_raw={s['hit_raw']:.2f}")
    P(f"   net(50bp/side) mean={s['net']:+.3f} t={s['t']:.2f}; 2x cost mean={s['net2']:+.3f}; halves net 1990-2007 {s['h1']:+.3f} (n{s['h1n']}), 2008-2024 {s['h2']:+.3f} (n{s['h2n']}); ex-top-5 net={s['ex5']:+.3f}; worst={s['worst']:+.3f} best={s['best']:+.3f}")
    return s

def ceiling(z, years):
    P("ceiling table (whole shares, 5 equal slots = account/5 each, 50% capture of events, net of 50bp/side):")
    for cap in (2300, 10000, 25000):
        slot = cap / 5; pnl = 0; skipped = 0
        for r in z.itertuples():
            k = int(slot // r.px)
            if k < 1: skipped += 1; continue
            pnl += k * r.px * (r.exc + r.bm - 2 * COST)   # raw return net of cost (account is long, not hedged)
        pct = 0.5 * pnl / cap / years * 100
        pnl_exc = sum(int(slot // r.px) * r.px * (r.exc - 2 * COST) for r in z.itertuples() if slot // r.px >= 1)
        P(f"  ${cap:>6}: raw net {pct:+.2f} %/yr of account (events/yr {len(z)/years:.1f}, unaffordable {skipped}); excess-only {0.5*pnl_exc/cap/years*100:+.2f} %/yr")

def main():
    db = conn()
    S = {}
    reg = build([574], "gvkey")
    P("== Event set A (REGISTERED): dlstcd 574, gvkey continuity via CCM LU/LC, new permno first trading within 36m")
    P("candidates", len(reg), "by dlstcd:", reg.dlstcd.value_counts().to_dict())
    alt = build(list(range(550, 586)), "gvkey")
    P("== Fallback set B: dlstcd 550-585 gvkey", len(alt), "by dlstcd:", alt.dlstcd.value_counts().to_dict())
    cus = build([574], "cusip6")
    P("== Set C (report only): dlstcd 574, CUSIP-6 continuity", len(cus), " not in A:", len(set(cus.new) - set(reg.new)))
    allp = sorted(set(reg.new) | set(alt.new) | set(cus.new))
    panel = load_panel(db, allp)
    res = {}
    for k, ev in (("A", reg), ("B", alt), ("C", cus)):
        r = run_events(ev, panel); res[k] = r
        P(f"\n--- set {k}: skip reasons", r.skip.replace("", "OK").value_counts().to_dict())
    A = res["A"]; Aok = A[(A.skip == "") & (A.entry >= "1990-01-01") & (A.entry <= "2024-12-31")].dropna(subset=["exc"])
    P("\nA candidates by entry year:", Aok.entry.dt.year.value_counts().sort_index().to_dict())
    P("A by dlstcd of old:", A.dlstcd.value_counts().to_dict(), " (all 574 by construction)")
    P("A listing venue (exchcd at entry):", Aok.exchcd.value_counts(dropna=False).to_dict(), " (1=NYSE 2=AMEX 3=NASDAQ)")
    P("A missing decile benchmark at entry:", int(Aok.cap_dec.isna().sum()), " short windows(not delisted):", int(Aok.short_window.sum()), " delisted in hold:", int(Aok.delisted.sum()))
    P("\n== JUDGED SPEC: set A ==")
    s = stats(Aok, "A judged")
    # primary gate set: A if n>=100 else registered fallback B
    g = {}
    judged = Aok; jl = "A"
    if len(Aok) < 100:
        B = res["B"]; Bok = B[(B.skip == "") & (B.entry >= "1990-01-01") & (B.entry <= "2024-12-31")].dropna(subset=["exc"])
        P(f"\nA n={len(Aok)} < 100 -> registered fallback (550-585 gvkey) evaluated as the gate set: n={len(Bok)}")
        sB = stats(Bok, "B fallback")
        if len(Bok) >= 100: judged, s, jl = Bok, sB, "B"
    C = res["C"]; Cok = C[(C.skip == "") & (C.entry >= "1990-01-01") & (C.entry <= "2024-12-31")].dropna(subset=["exc"])
    P(""); stats(Cok, "C cusip6 (report only)")
    U = pd.concat([Aok, Cok]).drop_duplicates("new"); stats(U, "A union C (report only)")
    gates = {
        "n>=100": len(judged) >= 100,
        "median excess >= +4% per 120d (gross of cost)": s["med_exc"] >= 0.04,
        "mean excess > 0 net": s["net"] > 0,
        "halves both > 0 (net)": s["h1"] > 0 and s["h2"] > 0,
        "ex-top-5 mean > 0 (net)": s["ex5"] > 0,
        "2x cost mean > 0": s["net2"] > 0}
    P(f"\n== GATE (judged set {jl}) ==")
    for k, v in gates.items(): P(f"  {'PASS' if v else 'FAIL'}  {k}")
    P("VERDICT:", "PASS" if all(gates.values()) else "KILL")
    ceiling(judged, max(s["years"], 1))
    P("\n== PER-EVENT LIST (judged set; exc/raw/bm are 120d, before cost) ==")
    cols = ["oldname", "dlstdt", "newname", "entry", "px", "exchcd", "n_days", "delisted", "raw", "bm", "exc"]
    P(judged[cols].sort_values("entry").to_string(float_format=lambda v: f"{v:+.3f}" if abs(v) < 50 else f"{v:.2f}"))
    P("\n== Skipped in A (shrcd/px filters etc.) ==")
    P(A[A.skip != ""][["oldname", "newname", "first", "skip", "shrcd", "px"]].to_string())
    P("\n== Set C-only events (not in A) ==")
    P(Cok[~Cok.new.isin(Aok.new)][["oldname", "newname", "entry", "exc"]].to_string())
    OUT.write_text("\n".join(LOG))

if __name__ == "__main__":
    main()
