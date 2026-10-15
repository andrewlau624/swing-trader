"""CEF-OOS + NAVFALL (N 890-891): the frozen CEF-RV rule on its untouched 1999-2014 window, and the NAV-fall filter.

    PYTHONPATH=. .venv/bin/python -m research.sim.cef_oos     # -> research/sim/cef_oos_out.txt

Pre-registration: round1_prose.md "Study CEF-OOS + NAVFALL".
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from research.sim.cef_rv import build_trades, load_nav, load_sfp
from research.sim.cef_txt import clus_t, spread_stats, tercile_drop

ROOT = pathlib.Path(__file__).resolve().parents[2]
CEF = ROOT / "data/research/cefconnect"
OUT = ROOT / "research/sim/cef_oos_out.txt"
LO, HI, LAST_ENTRY = pd.Timestamp("1999-01-01"), pd.Timestamp("2016-06-30"), pd.Timestamp("2014-12-31")
COST = 0.005
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def navtr26(fS: pd.DataFrame) -> pd.DataFrame:
    """Per panel week: raw 26-week NAV return and the distribution-inclusive, split-neutral version."""
    pan = pd.read_parquet(CEF / "cef_panel.parquet")[["ticker", "date", "nav"]].sort_values(["ticker", "date"])
    f = fS[["ticker", "dt", "closeadj", "closeunadj"]].copy()
    f["fac"] = f["closeadj"] / f["closeunadj"]
    pan["date"] = pan["date"].astype("datetime64[ns]")
    f["dt"] = f["dt"].astype("datetime64[ns]")
    pan = pd.merge_asof(pan.sort_values("date"), f[["ticker", "dt", "fac"]].sort_values("dt"),
                        left_on="date", right_on="dt", by="ticker", direction="backward",
                        tolerance=pd.Timedelta(days=10)).sort_values(["ticker", "date"])
    g = pan.groupby("ticker")
    pan["nav26"] = g["nav"].pct_change(26)
    pan["navtr26"] = (pan["nav"] / g["nav"].shift(26)) * (pan["fac"] / g["fac"].shift(26)) - 1
    return pan[["ticker", "date", "nav26", "navtr26"]]


def main() -> int:
    nav = load_nav()
    fS = load_sfp(sorted(nav["ticker"].unique()), LO, HI)
    tr = build_trades(nav[nav["date"] >= LO - pd.Timedelta(days=400)], fS)
    tr["edate"] = pd.to_datetime(tr["edate"]).astype("datetime64[ns]")
    tr = tr[(tr["edate"] >= LO) & (tr["edate"] <= LAST_ENTRY)].sort_values(["edate", "ticker"]).reset_index(drop=True)
    tr.to_csv(CEF / "cef_rv_trades_1999_2014.csv", index=False)
    r = tr["ret"].to_numpy(float) - COST
    wk = tr["edate"].dt.strftime("%G-%V").to_numpy()
    h0 = (tr["edate"] < "2007-01-01").to_numpy()
    yr = tr["edate"].dt.year
    ex5 = np.delete(r, np.argsort(-r)[:5]).mean()
    no0809 = ~yr.isin([2008, 2009]).to_numpy()
    say(f"ARM O (N 890) CEF-RV 1999-2014 entries: trades {len(tr)} funds {tr['ticker'].nunique()}")
    say(f"  mean net {r.mean()*1e4:+.1f}bp median {np.median(r)*1e4:+.1f} hit {(r>0).mean():.2f} t_wk {clus_t(r, wk):.2f}")
    say(f"  halves 1999-06 {r[h0].mean()*1e4:+.1f} (n {h0.sum()}) / 2007-14 {r[~h0].mean()*1e4:+.1f} (n {(~h0).sum()}); "
        f"ex-top-5 {ex5*1e4:+.1f}; ex-2008-09 {r[no0809].mean()*1e4:+.1f}; 2x/3x cost {(r.mean()-COST)*1e4:+.1f} / "
        f"{(r.mean()-2*COST)*1e4:+.1f}; mean hold {tr['hold_weeks'].mean():.1f}wk")
    say("  by entry year: " + " ".join(f"{y}:{v*1e4:+.0f}({n})" for y, (v, n) in
                                      pd.DataFrame(dict(y=yr, r=r)).groupby("y")["r"].agg(["mean", "size"]).iterrows()))
    gate_o = dict(n=len(tr) >= 300, t=clus_t(r, wk) >= 2, halves=r[h0].mean() > 0 and r[~h0].mean() > 0,
                  med=np.median(r) > 0, hit=(r > 0).mean() >= 0.55, ex5=ex5 > 0)
    say(f"  ARM O: {'PASS' if all(gate_o.values()) else 'KILL'}  " + " ".join(f"{k}={'Y' if v else 'n'}" for k, v in gate_o.items()))

    m = pd.merge_asof(tr.sort_values("edate"), navtr26(fS).sort_values("date"), left_on="edate", right_on="date",
                      by="ticker", direction="backward", tolerance=pd.Timedelta(days=10))
    m = m.sort_values(["edate", "ticker"]).reset_index(drop=True)
    ok = m["navtr26"].notna().to_numpy()
    m, r, wk, h0 = m[ok].reset_index(drop=True), r[ok], wk[ok], h0[ok]
    yr = m["edate"].dt.year
    say(f"\nARM F (N 891) NAV-fall: trades with navtr26 {ok.sum()} of {len(ok)}; corr(navtr26, nav26) "
        f"{np.corrcoef(m['navtr26'], m['nav26'])[0,1]:.2f}")
    res = {}
    for col in ("navtr26", "nav26"):
        low = tercile_drop(m[col], yr, "low")
        s = spread_stats(r, ~low, wk)          # mean(LOW) - mean(rest)
        hh = [spread_stats(r[k], ~low[k], wk[k])["spread"] for k in (h0, ~h0)]
        idx = np.argsort(-np.abs(r))[5:]
        e5 = r[idx][low[idx]].mean() - r[idx][~low[idx]].mean()
        k = ~yr.isin([2008, 2009]).to_numpy()
        x08 = r[k & low].mean() - r[k & ~low].mean()
        q = m["disc_in"].groupby(yr).rank(pct=True).to_numpy()
        dterc = [r[(q > a) & (q <= b) & low].mean() - r[(q > a) & (q <= b) & ~low].mean()
                 for a, b in ((0, 1/3), (1/3, 2/3), (2/3, 1.01))]
        res[col] = dict(s=s, hh=hh, e5=e5, x08=x08, dterc=dterc, low=low)
        say(f"  {col}: LOW n {low.sum()} mean {r[low].mean()*1e4:+.1f} vs rest {r[~low].mean()*1e4:+.1f}  "
            f"SPREAD {s['spread']*1e4:+.1f}bp t_wk {s['t']:.2f} med-diff {s['med']*1e4:+.1f} hit {s['hit_keep']:.2f}/"
            f"{s['hit_drop']:.2f}  halves {hh[0]*1e4:+.1f}/{hh[1]*1e4:+.1f}  ex-top5 {e5*1e4:+.1f}  ex-08/09 "
            f"{x08*1e4:+.1f}  by disc tercile (deep..shallow) " + "/".join(f"{v*1e4:+.0f}" for v in dterc))
    rng = np.random.default_rng(891)
    v = m["navtr26"]
    pl = []
    for _ in range(200):
        vs = v.groupby(yr).transform(lambda x: x.sample(frac=1, random_state=int(rng.integers(1e9))).to_numpy())
        lw = tercile_drop(vs, yr, "low")
        pl.append(r[lw].mean() - r[~lw].mean())
    f = res["navtr26"]
    pct = (np.array(pl) < f["s"]["spread"]).mean() * 100
    say(f"  PLACEBO navtr26: shuffled mean {np.mean(pl)*1e4:+.1f} p95 {np.percentile(pl, 95)*1e4:+.1f} -> real at {pct:.0f}th pct")
    gate_f = dict(spread=f["s"]["spread"] >= 0.015, t=f["s"]["t"] >= 2, halves=min(f["hh"]) > 0, med=f["s"]["med"] > 0,
                  ex5=f["e5"] > 0, placebo=pct >= 95, ex0809=f["x08"] > 0, disc=sum(x > 0 for x in f["dterc"]) >= 2)
    say(f"  ARM F: {'PASS' if all(gate_f.values()) else 'KILL'}  " + " ".join(f"{k}={'Y' if v else 'n'}" for k, v in gate_f.items()))
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
