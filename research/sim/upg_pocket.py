"""Study UPG-POCKET (round1_prose.md "## Study UPG-POCKET", N 987): UPG-DAY0 arm A restricted to the post-hoc pocket gap <= 0,
judged once on untouched 2020-24. Reuses upg_day0.build / stats helpers; only the data dir, window and gate are new.
usage: upg_pocket.py fetch | build | judge"""
import sys, time
sys.path.insert(0, "research/sim")
import numpy as np, pandas as pd
from pathlib import Path
import upg_day0 as U
from sect_lag import conn, tstat_clustered
D = Path("data/research/upg_pocket"); OUT = Path("data/research/program/upg_pocket_out.txt")
U.D = D; U.OUT = OUT          # build()/log()/stats() write to the pocket dir/out
A_, B_ = "2020-01-01", "2024-12-31"
log = U.log; stats = U.stats

def fetch():
    D.mkdir(parents=True, exist_ok=True)
    old = Path("data/research/upg_day0")
    db = conn()
    parts = []
    for a, b in (("2019-10-01", "2020-12-31"), ("2021-01-01", "2022-12-31"), ("2023-01-01", "2024-12-31")):
        parts.append(db.raw_sql("select ticker,cusip,estimid,amaskcd,analyst,ireccd,anndats,anntims,actdats,revdats from ibes.recddet "
                                f"where anndats between '{a}' and '{b}'"))
        log(f"[fetch] recddet {a}..{b}: {len(parts[-1])}")
    rec = pd.concat([pd.read_parquet(old / "recddet.parquet")] + parts, ignore_index=True)
    rec["anntims"] = rec.anntims.astype(str).where(rec.anntims.notna(), None)
    rec.to_parquet(D / "recddet.parquet"); log(f"[fetch] recddet total {len(rec)}")
    pd.read_parquet(old / "link.parquet").to_parquet(D / "link.parquet")
    ds = []
    for a, b in (("2019-09-01", "2020-12-31"), ("2021-01-01", "2022-12-31"), ("2023-01-01", "2024-12-31")):
        ds.append(db.raw_sql(f"select permno,date,openprc,prc,vol,ret from crsp.dsf where date between '{a}' and '{b}'"))
        log(f"[fetch] dsf {a}..{b}: {len(ds[-1])}")
    pd.concat(ds, ignore_index=True).to_parquet(D / "dsf.parquet"); db.close()

def judge():
    ev = pd.read_parquet(D / "events.parquet"); nd = pd.read_parquet(D / "nameday.parquet")
    ev = ev[(ev.d >= A_) & (ev.d <= B_)]; nd = nd[(nd.d >= A_) & (nd.d <= B_)].copy()
    up = ev[(ev.cls == "pre") & (ev.kind == "up") & ev.uni].copy()
    log(f"\n=== UPG-POCKET judge {A_}..{B_} ===  trading days {nd.d.nunique()}; all pre-open upgrades in universe {len(up)}")
    for c in (0, 2, 4): up[f"n{c}"] = up.ret - 2 * c * 1e-4
    log("ALL upgrades (UPG-DAY0 arm A on 2020-24, context):")
    for c in (0, 2, 4): stats(up, f"n{c}", f"  all net {c}bp/side")
    P = up[up.gap <= 0].copy(); Q = up[up.gap > 0]
    log("PRIMARY gap<=0:")
    r = {c: stats(P, f"n{c}", f"  P1 net {c}bp/side") for c in (0, 2, 4)}
    stats(Q, "n2", "  complement gap>0 net 2bp/side")
    P["yr"] = P.d.dt.year
    log("  P1 by year (net 2bp/side):")
    for y, g in P.groupby("yr"): stats(g, "n2", f"   {y}")
    h1 = P[P.d < "2023-01-01"]; h2 = P[P.d >= "2023-01-01"]
    s1 = stats(h1, "n2", "  half 2020-22 net 2bp"); s2 = stats(h2, "n2", "  half 2023-24 net 2bp")
    # control: unconditional name-days with gap<=0 in the same universe
    c0 = nd[nd.gap <= 0].copy(); c0["n2"] = c0.ret - 4e-4
    log(f"  control all universe name-days gap<=0: n {len(c0)} mean net2 {c0.n2.mean()*1e4:+.1f}bp; event minus control {(P.n2.mean()-c0.n2.mean())*1e4:+.1f}bp")
    ed = nd.groupby("d").n2.mean() if "n2" in nd else None
    cdm = c0.groupby("d").n2.mean(); dd = P.groupby("d").n2.mean().to_frame("e").join(cdm.rename("c"), how="left").dropna()
    dd["x"] = dd.e - dd.c; dd["date"] = dd.index; dd["d"] = dd.index
    log(f"  day-level event minus control: n days {len(dd)} mean {dd.x.mean()*1e4:+.1f}bp t {tstat_clustered(dd.reset_index(drop=True), 'x'):.2f}")
    # overlap / concentration
    nday = P.groupby("d").size()
    log(f"  P1 events {len(P)} on {P.d.nunique()} days ({P.d.nunique()/nd.d.nunique():.2f} of days); max/day {nday.max()}; share of days with >=2: {(nday>=2).mean():.2f}")
    log(f"  gap<=0 share of all upgrades {len(P)/len(up):.2f}; median gap {P.gap.median()*1e4:+.0f}bp; median adv ${P.adv.median()/1e6:.0f}M")
    log("SECONDARY adv>=1e9 (report only):")
    S = up[up.adv >= 1e9]; stats(S, "n2", "  P2 net 2bp/side"); stats(S, "n4", "  P2 net 4bp/side")
    stats(S[S.gap <= 0], "n2", "  P2 & gap<=0 net 2bp/side")
    # gate
    m2, m4 = r[2], r[4]
    items = {"n>=200": m2["n"] >= 200, "mean2>0": m2["mean"] > 0, "t>=2": m2["t"] >= 2, "median>0": m2["median"] > 0,
             "ex-top5>0": m2["top5"] > 0, "halves>0": s1["mean"] > 0 and s2["mean"] > 0, "mean4>0": m4["mean"] > 0}
    log("GATE: " + "; ".join(f"{k} {'ok' if v else 'FAIL'}" for k, v in items.items()))
    dpy = P.d.nunique() / 5
    log("CEILING (days with event/yr %.0f x net2 %.1fbp x share 1.0 x 50%% capture x 0.65 tax):" % (dpy, m2["mean"] * 1e4))
    for cap in (2300, 10000, 25000):
        # whole-share haircut: one share granularity of median price
        px = P.openprc.median(); haircut = 1 - (px / 2) / cap if cap < 20 * px else 1.0
        pp = dpy * m2["mean"] * 1.0 * 0.5 * 0.65 * 100 * (haircut if cap == 2300 else 1.0)
        log(f"  ${cap}: {pp:+.1f}pp/yr after tax (median open px ${px:.0f}; $2.3k whole-share haircut {haircut:.2f})")
    k = sum(items.values())
    verdict = "PASS" if all(items.values()) else ("WEAK" if (not items["t>=2"]) and all(v for kk, v in items.items() if kk != "t>=2") else "KILL")
    log(f"VERDICT (frozen gate, {k}/{len(items)}): {verdict}; DSR at N 987 n/a unless PASS")

if __name__ == "__main__":
    st = sys.argv[1]
    if st == "fetch": fetch()
    elif st == "build": U.build()
    elif st == "judge": judge()
