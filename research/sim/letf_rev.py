"""Study LETF-REV (round1_prose.md "## Amendment - Study LETF-REV", N 1065): does the single-stock LETF close impact revert at the
next open? Pressure I = ss_letf.panel() (no redefinition). Rule A: day_ret <= -3% & I >= 0.05, buy close cross, sell next open cross,
net 10bp round trip. Rule B (read only): day_ret >= +3% & I >= 0.05. Tilt read: live night subset (dr <= -8%, IBS < 0.10) by I.
usage: PYTHONPATH=. .venv/bin/python -m research.sim.letf_rev"""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np, pandas as pd
from research.sim.ss_letf import panel, fund_map, START, END
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
SH = Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/letf_rev_out.txt"
H1_END = "2024-06-30"
COST = 10.0  # bp round trip (5/side)
BUCKETS = [(0.0, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 1.0)]


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with OUT.open("a") as f: f.write(s + "\n")


def clus_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else float("nan")


def nstats(s: pd.Series) -> str:
    """per-night series (already EW within the night), bp."""
    x = s.dropna().to_numpy(float)
    if len(x) < 3: return f"nights {len(x)}"
    top = np.sort(x)[-5:].sum()
    return (f"nights {len(x)} mean {x.mean():+.1f} med {np.median(x):+.1f} hit {np.mean(x > 0):.2f} t {clus_t(x):.2f} "
            f"ex-top5 {(x.sum() - top) / (len(x) - 5):+.1f}")


def nightly(sub: pd.DataFrame, col: str) -> pd.Series:
    return sub.groupby("date")[col].mean()


def build() -> pd.DataFrame:
    p = panel()
    f = fund_map()
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close"])
    st = st[st.ticker.isin(set(p.ticker))]; st["date"] = pd.to_datetime(st.date)
    st = st[st.date >= "2022-06-01"].sort_values(["ticker", "date"])
    g = st.groupby("ticker")
    st["nd"] = g.date.shift(-1); st["no"] = g.open.shift(-1)
    st["on"] = (st.no / st.close - 1) * 1e4
    st.loc[(st.nd - st.date).dt.days > 7, "on"] = np.nan      # next row must be within 7 calendar days
    st["ibs"] = (st.close - st.low) / (st.high - st.low).replace(0, np.nan)
    m = p.merge(st[["ticker", "date", "on", "ibs"]], on=["ticker", "date"], how="left")
    m["dr"] = m.closeunadj / m.pc - 1
    m = m[m.on.notna() & m.dr.notna()].copy()
    m["letf"] = m.ticker.isin(set(f.u))
    m["net"] = m.on - COST
    return m


def report(nm: str, sub: pd.DataFrame, bench: pd.DataFrame, plc: pd.DataFrame | None, gates: bool):
    """sub: treated name-days; bench: per-night benchmarks (letf, univ); plc: placebo name-days."""
    t = nightly(sub, "net").rename("t")
    d = pd.concat([t, bench], axis=1).dropna(subset=["t"])
    d["x_letf"] = d.t - d.letf_on; d["x_univ"] = d.t - d.univ_on
    log(f"\n=== {nm}: {len(sub):,} name-days ({sub.ticker.nunique()} names) on {len(t):,} nights; names/night median "
        f"{sub.groupby('date').size().median():.0f}, mean I {sub.I.mean():.3f}")
    log(f"  gross            {nstats(nightly(sub, 'on'))}")
    log(f"  net {COST:.0f}bp         {nstats(d.t)}")
    log(f"  x LETF-und EW    {nstats(d.x_letf)}")
    log(f"  x panel EW       {nstats(d.x_univ)}")
    log(f"  halves net:   H1 {nstats(d[d.index <= H1_END].t)} | H2 {nstats(d[d.index > H1_END].t)}")
    log(f"  halves x letf: H1 {nstats(d[d.index <= H1_END].x_letf)} | H2 {nstats(d[d.index > H1_END].x_letf)}")
    log("  by year net/x_letf/nights: " + ", ".join(f"{y} {g.t.mean():+.0f}/{g.x_letf.mean():+.0f}/{len(g)}"
                                                    for y, g in d.groupby(d.index.year)))
    pdiff = None
    if plc is not None:
        c = nightly(plc, "net").rename("c")
        dd = pd.concat([t, c], axis=1).dropna()
        pdiff = dd.t - dd.c
        log(f"  placebo (I==0, same cut): {len(plc):,} name-days, net {nstats(c)}")
        log(f"  paired night diff treated-placebo: {nstats(pdiff)}")
    top = sub.groupby("ticker").net.agg(["mean", "count"]); top["contrib"] = top["mean"] * top["count"]
    top = top.sort_values("contrib", ascending=False).head(10)
    log("  top-10 contributing names (net mean bp, n): " + ", ".join(f"{k} {r['mean']:+.0f}/{int(r['count'])}" for k, r in top.iterrows()))
    if gates:
        x = d.t.dropna().to_numpy(float)
        ok = dict(mean15=x.mean() >= 15, t2=clus_t(x) >= 2, median=np.median(x) > 0,
                  extop5=(x.sum() - np.sort(x)[-5:].sum()) / (len(x) - 5) > 0,
                  h1=d[d.index <= H1_END].t.mean() > 0, h2=d[d.index > H1_END].t.mean() > 0,
                  placebo=pdiff.mean() > 0)
        return ok, x.mean(), clus_t(x), pdiff.mean()
    return None


def buckets(nm: str, sub_all: pd.DataFrame, bench: pd.DataFrame):
    log(f"\n--- I buckets, {nm} (per-night EW, net {COST:.0f}bp; x LETF-und EW) ---")
    means, nets = [], []
    for lo, hi in BUCKETS:
        s = sub_all[(sub_all.I >= lo) & (sub_all.I < hi)]
        if len(s) == 0:
            log(f"  I [{lo:.2f},{hi:.2f}) mean I   n/a  : empty"); means.append(np.nan); nets.append(np.nan); continue
        t = nightly(s, "net"); x = (t - bench.letf_on).dropna()
        means.append(s.I.mean()); nets.append(t.mean())
        log(f"  I [{lo:.2f},{hi:.2f}) mean I {s.I.mean():.3f}: {len(s):6,} name-days | net {nstats(t)} | x letf mean {x.mean():+.1f} t {clus_t(x):.2f}")
    mi = [v for v in means if np.isfinite(v)]
    assert all(b > a for a, b in zip(mi, mi[1:])), f"mean I not increasing across labels: {means}"
    return nets


def main():
    if OUT.exists(): OUT.unlink()
    m = build()
    log(f"LETF-REV (N 1065): panel {len(m):,} name-days, {m.ticker.nunique():,} names, {m.date.nunique():,} nights "
        f"{m.date.min().date()}..{m.date.max().date()} (ss_letf.panel: px>=5, udv20>=100M, common stock); "
        f"LETF-underlying names (fund_map) {m.letf.sum():,} name-days / {m[m.letf].ticker.nunique()} names; "
        f"I>0 {int((m.I > 0).sum()):,} name-days; I>=0.05 {int((m.I >= 0.05).sum()):,}")
    log(f"overnight = adjusted open(d+1)/close(d)-1 from stocks.parquet, next row within 7 calendar days; net = gross - {COST:.0f}bp; "
        f"I from ss_letf.panel() unchanged; IBS from adjusted high/low/close")
    bench = pd.concat([nightly(m[m.letf], "on").rename("letf_on"), nightly(m, "on").rename("univ_on")], axis=1)
    log(f"benchmarks (gross, per night): LETF-underlying EW {nstats(bench.letf_on)} | panel EW {nstats(bench.univ_on)}")
    log(f"  LETF-underlying names/night median {m[m.letf].groupby('date').size().median():.0f}; panel names/night median {m.groupby('date').size().median():.0f}")

    down = m[m.dr <= -0.03]; up = m[m.dr >= 0.03]
    A = down[down.I >= 0.05]; A_pl = down[down.I == 0]
    ok, mu, tt, pd_ = report("RULE A: day_ret <= -3% & I >= 0.05, long close -> next open", A, bench, A_pl, gates=True)
    netsA = buckets("RULE A cut (day_ret <= -3%)", down, bench)
    aI = [v for v in netsA if np.isfinite(v)]
    mono = all(b >= a for a, b in zip(aI, aI[1:]))
    ok["mono_I"] = mono
    verdict = "PASS" if all(ok.values()) else ("WEAK" if (8 <= mu < 15 and tt >= 2 and pd_ > 0) else "KILL")
    log(f"\nGATES RULE A {ok} | net {mu:+.1f}bp t {tt:.2f} placebo diff {pd_:+.1f} -> {verdict}")
    if verdict == "KILL":
        log("KILL: the LETF close impact does not revert at the next open by more than the round trip in the names with it.")

    B = up[up.I >= 0.05]; B_pl = up[up.I == 0]
    report("RULE B (read only): day_ret >= +3% & I >= 0.05, overnight long return", B, bench, B_pl, gates=False)
    buckets("RULE B cut (day_ret >= +3%)", up, bench)

    log("\n=== TILT READ: live night subset day_ret <= -8% & IBS < 0.10 ===")
    nt = m[(m.dr <= -0.08) & (m.ibs < 0.10)]
    for lab, s in [("all", nt), ("I >= 0.05", nt[nt.I >= 0.05]), ("0 < I < 0.05", nt[(nt.I > 0) & (nt.I < 0.05)]), ("I == 0", nt[nt.I == 0])]:
        if len(s) == 0: log(f"  {lab:12s}: empty"); continue
        t = nightly(s, "net")
        log(f"  {lab:12s}: {len(s):5,} name-days ({s.ticker.nunique()} names) | net {nstats(t)} | gross name-day mean {s.on.mean():+.1f} med {s.on.median():+.1f}")
    hi, lo = nt[nt.I >= 0.05], nt[nt.I == 0]
    dd = pd.concat([nightly(hi, "net").rename("t"), nightly(lo, "net").rename("c")], axis=1).dropna()
    log(f"  paired nights (both present) I>=0.05 minus I==0: {nstats(dd.t - dd.c)}")

    hi_n = nightly(hi, "net"); hx = (hi_n - bench.letf_on).dropna()
    log(f"  I>=0.05 subset x LETF-und EW: {nstats(hx)}; by year net/nights: " + ", ".join(f"{y} {g.mean():+.0f}/{len(g)}" for y, g in hi_n.groupby(hi_n.index.year)))
    tp = hi.groupby("ticker").net.agg(["mean", "count"]); tp["contrib"] = tp["mean"] * tp["count"]
    log("  I>=0.05 subset top names (net mean bp, n): " + ", ".join(f"{k} {r['mean']:+.0f}/{int(r['count'])}" for k, r in tp.sort_values("contrib", ascending=False).head(10).iterrows()))
    ex = hi[~hi.ticker.isin(tp.sort_values("contrib", ascending=False).head(3).index)]
    log(f"  I>=0.05 subset ex-top-3 names: {len(ex)} name-days | net {nstats(nightly(ex, 'net'))}")
    log("\n=== VOLUNTEERED: Rule A by day_ret depth and by I, gross name-day means ===")
    for lo_, hi_ in [(-1, -0.08), (-0.08, -0.05), (-0.05, -0.03)]:
        for il, ih in [(0.05, 1), (0, 1e-9)]:
            s = m[(m.dr > lo_) & (m.dr <= hi_) & (m.I >= il) & (m.I < ih)]
            if len(s) < 10: continue
            t = nightly(s, "net")
            log(f"  dr ({lo_:+.2f},{hi_:+.2f}] I {'>=0.05' if il else '==0  '}: {len(s):6,} nd | net {nstats(t)}")
    log("Disclosed: daily opens as the open cross, daily closes as the close cross (Sharadar adjusted); per-night EW; t = per-night "
        "(nights are the cluster); placebo diff = paired nights where both treated and placebo exist.")


if __name__ == "__main__":
    main()
