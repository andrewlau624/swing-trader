"""Study MINPATH-NIGHT (N 1042): the 15:30-15:40 minute path as a within-night ranker of the night pool.
Run: PYTHONPATH=. .venv/bin/python research/sim/minpath_night.py"""
from __future__ import annotations
import glob
import os
import pathlib
import time

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from research.sim.seq_night import GBM, fit_gbm, judge_night, night_replays, nw_t, shuffle_within  # noqa: F401

REPO = pathlib.Path(__file__).resolve().parents[2]
PROG = REPO / "data" / "research" / "program"
LM1 = [REPO / "data" / "research" / "night" / "lm1", REPO / "data" / "research" / "recent" / "lm1"]
SPLIT = pd.Timestamp("2023-07-01")
FEATS = ["r_win", "drawup", "min_since_low", "new_low", "win_range", "vwap_dist", "down_share", "r_last1", "r_last5",
         "volwin_rel", "vol_accel", "n_bars", "day_ret", "ibs", "vol20", "log_adv"]


def build() -> pd.DataFrame:
    pk = pd.read_parquet(PROG / "night_tau_picks.parquet")
    pk = pk[(pk.tau == 1540) & pk.sig].copy()
    pk["date"] = pd.to_datetime(pk.date)
    want = {d: set(g.sym) for d, g in pk.groupby("date")}
    files = sorted(f for d in LM1 for f in glob.glob(str(d / "*.parquet")))
    rows = []
    t0 = time.time()
    for f in files:
        d = pd.Timestamp(os.path.basename(f)[:10])
        if d not in want:
            continue
        df = pd.read_parquet(f)
        df = df[df.symbol.isin(want[d])]
        if df.empty:
            continue
        t = pd.to_datetime(df.timestamp).dt.tz_convert("America/New_York")
        df["hm"] = t.dt.hour * 100 + t.dt.minute
        df = df[(df.hm >= 1530) & (df.hm <= 1540)].sort_values("hm")
        for s, g in df.groupby("symbol"):
            if len(g) < 3:
                continue
            c, lo, hi, v, o = g.close.to_numpy(), g.low.to_numpy(), g.high.to_numpy(), g.volume.to_numpy(), g.open.to_numpy()
            p40 = c[-1]
            usd = c * v
            i_lo = int(np.argmin(lo))
            dusd = usd.sum()
            first5, last5 = usd[: max(1, len(usd) // 2)].sum(), usd[-max(1, len(usd) // 2):].sum()
            rows.append(dict(date=d, sym=s, n_bars=len(g), r_win=p40 / o[0] - 1, drawup=p40 / lo.min() - 1,
                             min_since_low=int(1540 - g.hm.iloc[i_lo]), new_low=float(lo[-1] <= lo.min() + 1e-9),
                             win_range=(hi.max() - lo.min()) / p40, vwap_dist=p40 / (dusd / v.sum()) - 1 if v.sum() > 0 else np.nan,
                             down_share=float(np.mean(np.diff(c) < 0)), r_last1=c[-1] / c[-2] - 1,
                             r_last5=c[-1] / c[max(0, len(c) - 6)] - 1, dusd=dusd,
                             vol_accel=last5 / first5 if first5 > 0 else np.nan))
    x = pd.DataFrame(rows).merge(pk[["date", "sym", "day_ret", "ibs", "vol20", "adv", "r"]], on=["date", "sym"], how="inner")
    x["volwin_rel"] = x.dusd / (x.adv / 39.0)
    x["log_adv"] = np.log(x.adv)
    x = x.rename(columns={"sym": "ticker"}).sort_values(["date", "ticker"]).reset_index(drop=True)
    x["r"] = x.r / 1e4                                   # night_tau stores bp; judge helpers expect fractions
    x["label"] = (x.r - x.groupby("date").r.transform("mean")).clip(-0.5, 0.5)
    n = x.groupby("date").ticker.transform("size")
    x["per"] = np.minimum(1.0, 0.15 * n) / n            # equal weight under the live per-name cap
    print(f"built {len(x):,} pick-rows from {x.date.nunique()} nights in {time.time()-t0:.0f}s", flush=True)
    return x


def main() -> int:
    d = build().dropna(subset=FEATS + ["label"])
    d.to_parquet(PROG / "minpath_night_rows.parquet", index=False)
    train, test = d[d.date < SPLIT], d[d.date >= SPLIT]
    L = [f"MINPATH-NIGHT (N 1042): 15:30-15:40 minute-path ranker on the 15:40 night picks; rows {len(d):,}, features {len(FEATS)}",
         f"fit 2020-11..2023-06 (n {len(train):,}) -> judge 2023-07..2026-10 (n {len(test):,})", ""]
    X_tr, y_tr, X_te = train[FEATS].to_numpy(np.float32), train.label.to_numpy(), test[FEATS].to_numpy(np.float32)
    mdl = fit_gbm(X_tr, y_tr)
    pred = mdl.predict(X_te)
    line, real = judge_night(test, pred, "GBM judge 2023-07..2026-10"); L += line
    L += night_replays(test, pred)
    L += judge_night(train, mdl.predict(X_tr), "GBM in-sample (fit quality only)")[0]
    mu, sd = X_tr.mean(0), X_tr.std(0) + 1e-9
    rg = Ridge(alpha=10.0).fit((X_tr - mu) / sd, y_tr)
    rp = rg.predict((X_te - mu) / sd)
    L += judge_night(test, rp, "Ridge judge")[0]
    L += night_replays(test, rp)
    L.append("  Ridge coefficients (std units): " + ", ".join(f"{f} {c:+.4f}" for f, c in sorted(zip(FEATS, rg.coef_), key=lambda z: -abs(z[1]))[:8]))
    rng = np.random.default_rng(20261019)
    plc = np.array([judge_night(test, fit_gbm(X_tr, shuffle_within(train, "label", rng), seed=i).predict(X_te), "p")[1] for i in range(20)])
    L.append(f"  placebo (20 shuffled-label fits): mean {plc.mean():+.1f}bp sd {plc.std():.1f} 95th {np.percentile(plc, 95):+.1f}; real {real:+.1f} -> beats 95th: {real > np.percentile(plc, 95)}")
    imp = []
    for j, f in enumerate(FEATS):
        Xp = X_te.copy(); Xp[:, j] = rng.permutation(Xp[:, j])
        imp.append((f, real - judge_night(test, mdl.predict(Xp), "i")[1]))
    imp.sort(key=lambda z: -z[1])
    L.append("  permutation importance (bp lost): " + ", ".join(f"{f} {v:+.1f}" for f, v in imp[:10]))
    # single-feature reads (mechanism): within-night top-half minus bottom-half by each raw feature
    L.append("== single features, judge window: top-half minus bottom-half by the raw feature (bp, t) ==")
    for f in FEATS:
        ln, v = judge_night(test, test[f].to_numpy(float), f)
        L.append(f"  {f:14s} {v:+6.1f}  {ln[0].split('t ')[1].split(' ')[0]}")
    txt = "\n".join(L) + "\n"
    (PROG / "minpath_night_out.txt").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
