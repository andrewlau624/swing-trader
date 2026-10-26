"""Study PREMKT-CROSS (round1_prose.md "## Amendment - Studies HALT-REOPEN ... PREMKT-CROSS", N 1047-1048): learned pre-market-tape
selection into the 09:30 cross, exit at the 16:00 cross (A) or the next open (B). Both legs are auctions (0bp); judged net 5bp.
usage: PYTHONPATH=. .venv/bin/python -m research.sim.premkt_cross build | run
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from .intra_any import FIT_END, JUDGE0, MID, DEV_END, SRC, _daily, clus_t, fit as _fit, shuffle_within, stats

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
ROWS = PROG / "premkt_rows.parquet"
OUT = PROG / "premkt_cross_out.txt"
ET = "America/New_York"
COST = 5.0
FEATS = ["pm_ret", "pm_ret_0830", "pm_range", "pm_usd", "pm_nbars", "pm_vwapdist", "pm_rv", "pm_last_mos", "pm_full_ret", "pm_full_usd",
         "pm_full_nbars", "spy_pm", "rel_spy", "dow", "ret1", "ret5", "ret20", "vol20", "ladv", "src"]


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with OUT.open("a") as f:
        f.write(s + "\n")


def _spy_pm() -> pd.DataFrame:
    """SPY 09:29 close / prior session's last regular-hours close - 1, per date."""
    fr = []
    for f in sorted((ROOT / "data/research/night/m1").glob("SPY_*.parquet")):
        x = pd.read_parquet(f, columns=["timestamp", "close"])
        t = pd.to_datetime(x.timestamp, utc=True).dt.tz_convert(ET)
        x["date"] = t.dt.normalize().dt.tz_localize(None)
        x["mos"] = (t.dt.hour * 60 + t.dt.minute) - 570
        fr.append(x[["date", "mos", "close"]])
    x = pd.concat(fr).sort_values(["date", "mos"])
    rth_last = x[(x.mos >= 0) & (x.mos < 390)].groupby("date").close.last()
    pm_last = x[x.mos < 0].groupby("date").close.last()
    d = pd.DataFrame({"pm": pm_last, "prev": rth_last.shift(1)}).dropna()
    return (d.pm / d.prev - 1).rename("spy_pm").reset_index()


def build() -> None:
    files = [(f, "volday") for f in sorted((ROOT / "data/research/volday").glob("m1_*.parquet"))]
    files += [(f, "inplay") for f in sorted((ROOT / "data/research/inplay").glob("m1_*.parquet"))]
    syms = set()
    for f, _ in files:
        syms |= set(pd.read_parquet(f, columns=["sym"]).sym.unique())
    daily = _daily(syms)
    spy = _spy_pm()
    out = []
    for f, src in files:
        m = pd.read_parquet(f, columns=["sym", "t", "o", "h", "l", "c", "v"])
        if m.empty:
            continue
        t = pd.to_datetime(m.t, utc=True).dt.tz_convert(ET)
        m["date"] = t.dt.normalize().dt.tz_localize(None)
        m["mos"] = (t.dt.hour * 60 + t.dt.minute) - 570
        m = m[(m.mos >= -330) & (m.mos < 390)].sort_values(["sym", "date", "mos"])
        key = ["sym", "date"]
        rth = m[m.mos >= 0]
        g = rth.groupby(key)
        base = pd.DataFrame({"open": g.o.first(), "last": g.c.last(), "n_rth": g.size(), "k0": g.mos.first()})
        pm = m[m.mos < 0]
        gp = pm.groupby(key)
        full = pd.DataFrame({"pm_first_c": gp.c.first(), "pm_full_usd": (pm.c * pm.v).groupby([pm.sym, pm.date]).sum(),
                             "pm_full_nbars": gp.size(), "pm_last_c": gp.c.last(), "pm_last_mos": gp.mos.last()})
        w = pm[pm.mos >= -60]                                  # 08:30-09:29 (both panels cover it)
        gw = w.groupby(key)
        win = pd.DataFrame({"w_first_c": gw.c.first(), "w_hi": gw.h.max(), "w_lo": gw.l.min(), "w_usd": (w.c * w.v).groupby([w.sym, w.date]).sum(),
                            "w_vol": gw.v.sum(), "pm_nbars": gw.size()})
        w2 = pm[pm.mos >= -30]
        r2 = w2.groupby(key).c.apply(lambda s: np.log(s).diff().std() if len(s) > 3 else np.nan).rename("pm_rv")
        x = base.join(full, how="left").join(win, how="left").join(r2, how="left").reset_index()
        x = x[(x.n_rth >= 300) & (x.k0 == 0)]
        x["src"] = SRC[src]
        x = x.merge(daily, on=["sym", "date"], how="left").merge(spy, on="date", how="left")
        with np.errstate(all="ignore"):
            x["pm_ret"] = x.pm_last_c / x.pc - 1
            x["pm_ret_0830"] = x.pm_last_c / x.w_first_c - 1
            x["pm_range"] = (x.w_hi - x.w_lo) / x.pc
            x["pm_usd"] = x.w_usd / np.exp(x.ladv)
            x["pm_vwapdist"] = x.pm_last_c / (x.w_usd / x.w_vol) - 1
            x["pm_full_ret"] = np.where(x.src == 0, x.pm_first_c / x.pc - 1, np.nan)
            x["pm_full_usd"] = np.where(x.src == 0, x.pm_full_usd / np.exp(x.ladv), np.nan)
            x["pm_full_nbars"] = np.where(x.src == 0, x.pm_full_nbars, np.nan)
            x["rel_spy"] = x.pm_ret - x.spy_pm
            x["dow"] = pd.DatetimeIndex(x.date).dayofweek
            x["yA"] = (x["last"] / x.open - 1) * 1e4
            x["yB"] = ((x["last"] / x.open) * x.nxt - 1) * 1e4
            x["gap"] = (x.open / x.pc - 1) * 1e4           # NOT a feature (the open is the entry); reported only
        out.append(x[["sym", "date", "src", "open", "gap", "yA", "yB"] + FEATS[:-1]])
        print(f"{f.name} {src}: {len(x)} name-days", flush=True)
    df = pd.concat(out, ignore_index=True)
    df.to_parquet(ROWS)
    print(f"rows {len(df):,} -> {ROWS}", flush=True)


def fit(tr, y, seed=0):
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200,
                                         l2_regularization=1.0, random_state=seed).fit(tr[FEATS].to_numpy(np.float32), y)


def judge(df: pd.DataFrame, lab: str, name: str) -> None:
    tr, te = df[df.date <= FIT_END], df[df.date >= JUDGE0]
    log(f"\n=== {name}: label {lab}; fit {len(tr):,} name-days to {FIT_END}, judge {len(te):,} {JUDGE0}..{te.date.max().date()}")
    dtr, dte = df[df.date <= DEV_END], df[(df.date > DEV_END) & (df.date <= FIT_END)]
    m0 = fit(dtr, dtr[lab].to_numpy())
    p0 = m0.predict(dte[FEATS].to_numpy(np.float32))
    thr0 = np.quantile(m0.predict(dtr[FEATS].to_numpy(np.float32)), 0.9)
    log(f"dev (fit 2016-19 -> 2020-21, informational): selected gross {stats(dte[lab][p0 >= thr0], dte.date[p0 >= thr0])}; corr {np.corrcoef(p0, dte[lab])[0,1]:+.3f}")
    m = fit(tr, tr[lab].to_numpy())
    thr = float(np.quantile(m.predict(tr[FEATS].to_numpy(np.float32)), 0.9))
    p = m.predict(te[FEATS].to_numpy(np.float32))
    y = te[lab].to_numpy(float)
    log(f"threshold {thr:+.1f}bp; judge share selected {np.mean(p >= thr):.3f}; corr(pred, y) {np.corrcoef(p, y)[0,1]:+.4f}, corr(pred, |y|) {np.corrcoef(p, np.abs(y))[0,1]:+.4f}")
    dec = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False).to_numpy()
    log("prediction deciles (gross mean / median / hit / mean|y| / mean gap at the open):")
    for q in range(10):
        s = y[dec == q]
        log(f"  D{q+1}: {s.mean():+6.1f} / {np.median(s):+6.1f} / {np.mean(s > 0):.3f} / {np.abs(s).mean():6.1f} / {te.gap.to_numpy()[dec == q].mean():+6.0f}   pred {p[dec == q].mean():+.1f}")
    log(f"all name-days gross: mean {y.mean():+.1f} hit {np.mean(y > 0):.3f}")
    sel = p >= thr
    s = te[sel]
    net = s[lab].to_numpy(float) - COST
    d = s.date.to_numpy()
    log(f"SELECTED (pred >= fit p90): gross {stats(s[lab], d)}")
    log(f"  net {COST:.0f}bp: {stats(net, d)} | unconditional {y.mean():+.1f} -> excess {s[lab].mean() - y.mean():+.1f}")
    for nm, msk in (("2022-23", s.date < MID), ("2024-26", s.date >= MID)):
        log(f"  {nm}: net {stats(net[msk.to_numpy()], d[msk.to_numpy()])}")
    log("  by year (net mean / n): " + ", ".join(f"{yy} {g.mean() - COST:+.0f}/{len(g)}" for yy, g in s.groupby(s.date.dt.year)[lab]))
    log(f"  by src: " + ", ".join(f"{k} {g.mean() - COST:+.0f}/{len(g)}" for k, g in s.groupby('src')[lab]))
    bot = te[p <= np.quantile(p, 0.1)]
    log(f"  bottom decile (informational short): gross {stats(-bot[lab], bot.date)}")
    rng = np.random.default_rng(7)
    pl = []
    for k in range(3):
        mp = fit(tr, shuffle_within(tr, lab, rng), seed=k + 1)
        thp = float(np.quantile(mp.predict(tr[FEATS].to_numpy(np.float32)), 0.9))
        pp = mp.predict(te[FEATS].to_numpy(np.float32))
        pl.append(te[lab][pp >= thp].mean() - COST)
    log(f"  placebo selected net (3 refits): {', '.join(f'{v:+.1f}' for v in pl)} vs real {net.mean():+.1f}")
    Xs = te[FEATS].to_numpy(np.float32)
    b0 = np.mean((m.predict(Xs) - y) ** 2)
    r2 = np.random.default_rng(1)
    imp = {}
    for j, fn in enumerate(FEATS):
        Xp = Xs.copy()
        Xp[:, j] = r2.permutation(Xp[:, j])
        imp[fn] = np.mean((m.predict(Xp) - y) ** 2) - b0
    log("  permutation importance (dMSE, top 8): " + ", ".join(f"{k} {v:.1f}" for k, v in sorted(imp.items(), key=lambda kv: -kv[1])[:8]))
    ok = dict(mean=net.mean() >= 10, t=clus_t(net, d) >= 2, median=np.median(net) > 0,
              h1=net[(s.date < MID).to_numpy()].mean() > 0, h2=net[(s.date >= MID).to_numpy()].mean() > 0,
              extop5=(net.sum() - np.sort(net)[-5:].sum()) / max(len(net) - 5, 1) > 0,
              excess=(s[lab].mean() - y.mean()) >= 10, placebo=all(v < net.mean() for v in pl))
    log(f"  GATES {ok} -> {'PASS' if all(ok.values()) else 'KILL'}")


def run() -> None:
    if OUT.exists():
        OUT.unlink()
    df = pd.read_parquet(ROWS)
    df["date"] = pd.to_datetime(df.date)
    n0 = len(df)
    df = df[np.isfinite(df.yA) & np.isfinite(df.ladv) & np.isfinite(df.pm_ret)]
    log(f"PREMKT-CROSS (N 1047-1048): name-days {n0:,} -> {len(df):,} with a pre-market print and context; {df.date.min().date()}..{df.date.max().date()}; "
        f"src {df.src.value_counts().to_dict()}")
    log(f"unconditional: open->close {df.yA.mean():+.1f}bp (hit {np.mean(df.yA > 0):.3f}), open->next open {df.yB.mean():+.1f}; "
        f"gap at the open median {df.gap.abs().median():.0f}bp abs; pm_ret vs gap corr {np.corrcoef(df.pm_ret, df.gap)[0,1]:.2f}")
    judge(df, "yA", "A: 09:30 cross -> 16:00 cross (N 1047)")
    judge(df[np.isfinite(df.yB)], "yB", "B: 09:30 cross -> next open (N 1048)")
    log("\nDisclosed: entry = first RTH bar open (== official open cross 2016-20); exit = last 1-min close; the open/gap is never a feature; "
        "inplay rows carry only the 08:25-09:29 pre-market (full-session pre-market features NaN).")


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"build": build, "run": run}[cmd]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
