"""Study NIGHT-TAU (round1_prose.md, N 1036 -> 1037): the night leg's decision time.

Same data/code path as research/sim/recent_night.py (lm1 minute panels 15:30-16:00 for -8%-low candidates,
2020-11..2026-10). For each tau the frozen rule is evaluated on the minute state at tau; entry = daily close,
exit = next daily open; equal weight; leg proxy = min(1, 0.15 n) x mean r.

Run:  PYTHONPATH=. .venv/bin/python research/sim/night_tau.py
Out:  data/research/program/night_tau_out.txt, data/research/program/night_tau_picks.parquet
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pandas as pd

REPO = "/Users/andrewlau/Documents/Code/Projects/swing-trader"
sys.path.insert(0, REPO)
os.chdir(REPO)
sys.path.insert(0, f"{REPO}/data/research/night")

R = f"{REPO}/data/research/recent"
OUT = f"{REPO}/data/research/program/night_tau_out.txt"
TAUS = [1535, 1540, 1545, 1548, 1550, 1552, 1555, 1558, 1559, 1600]
SPLIT = pd.Timestamp("2023-07-01")
CAP = 0.15


def panel_from_parquet(src: str) -> dict:
    """panel() without its pickle cache (the cache was written by an older pandas and no longer loads)."""
    df = pd.concat([pd.read_parquet(f, columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
                    for f in sorted(glob.glob(f"{src}/sipd/*.parquet"))])
    df["date"] = pd.to_datetime(df.timestamp).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    return {f: df.pivot_table(index="date", columns="symbol", values=f, aggfunc="last").astype("float32")
            for f in ["open", "high", "low", "close", "volume"]}


def full_panel():
    P = panel_from_parquet(f"{REPO}/data/research/night")
    rec = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{R}/sipd/*.parquet"))])
    rec["date"] = pd.to_datetime(rec.timestamp).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    Q = {f: rec.pivot_table(index="date", columns="symbol", values=f, aggfunc="last").astype("float32")
         for f in ["open", "high", "low", "close", "volume"]}
    out = {}
    for f in Q:
        old = P[f]
        old = old[old.index < "2026-09-17"]
        out[f] = pd.concat([old, Q[f]]).sort_index()
    return out


def clus_t(x: np.ndarray) -> float:
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def build() -> pd.DataFrame:
    P = full_panel()
    O, H, L, C, V = [P[k] for k in ["open", "high", "low", "close", "volume"]]
    C1 = C.shift(1)
    adv = (C * V).rolling(20).mean().shift(1)
    vol20 = np.log(C / C1).rolling(20).std().shift(1) * np.sqrt(252)
    NO = O.shift(-1)
    files = sorted(glob.glob(f"{REPO}/data/research/night/lm1/*.parquet") + glob.glob(f"{R}/lm1/*.parquet"))
    rows = []
    for f in files:
        d = pd.Timestamp(os.path.basename(f)[:10])
        if d not in C.index:
            continue
        df = pd.read_parquet(f)
        if df.empty:
            continue
        t = pd.to_datetime(df.timestamp).dt.tz_convert("America/New_York")
        df["hm"] = t.dt.hour * 100 + t.dt.minute
        for s, g in df.groupby("symbol"):
            if s not in C.columns:
                continue
            pc, Ld, Hd, cl, no = C1.at[d, s], L.at[d, s], H.at[d, s], C.at[d, s], NO.at[d, s]
            if not (np.isfinite(pc) and np.isfinite(cl) and np.isfinite(no)):
                continue
            base = dict(date=d, sym=s, vol20=vol20.at[d, s], adv=adv.at[d, s], close=cl, nopen=no, pc=pc)
            g = g.sort_values("hm")
            for tau in TAUS:
                if tau == 1600:
                    p, Lt, Ht = cl, Ld, Hd
                else:
                    pre = g[g.hm <= tau]
                    post = g[g.hm > tau]
                    if pre.empty:
                        continue
                    p = pre.close.iloc[-1]
                    Lt = Ld if (len(post) == 0 or post.low.min() > Ld + 1e-9) else pre.low.min()
                    Ht = Hd if (len(post) == 0 or post.high.max() < Hd - 1e-9) else pre.high.max()
                Ht, Lt = max(Ht, p), min(Lt, p)
                ret = p / pc - 1
                ibs = (p - Lt) / (Ht - Lt) if Ht > Lt else np.nan
                rows.append(dict(base, tau=tau, p=p, day_ret=ret, ibs=ibs))
    x = pd.DataFrame(rows)
    x["sig"] = (x.day_ret <= -0.08) & (x.ibs < 0.10) & x.p.between(5, 2000) & (x.vol20 >= 0.6) & (x.adv >= 1e7)
    x["r"] = (x.nopen / x.close - 1) * 1e4
    x = x[x.r.abs() < 6000]
    return x


def main() -> int:
    x = build()
    x.to_parquet(f"{REPO}/data/research/program/night_tau_picks.parquet")
    sel = x[x.sig]
    L = [f"NIGHT-TAU: decision time of the night leg; lm1 minute panel {x.date.min().date()}..{x.date.max().date()}, "
         f"candidate name-days {x[x.tau == 1540].shape[0]}, sessions {x.date.nunique()}", ""]
    nights_all = np.sort(x.date.unique())
    # per-tau picks and per-night leg proxy
    legs = {}
    L.append("== per tau: picks, per-pick r (gross / net 7.5bp/side), leg proxy per night (min(1,.15n) x mean r, all sessions) ==")
    for tau in TAUS:
        s = sel[sel.tau == tau]
        by = s.groupby("date").r.agg(["mean", "size"])
        leg = pd.Series(0.0, index=nights_all)
        leg.loc[by.index] = np.minimum(1.0, CAP * by["size"]) * by["mean"]
        legs[tau] = leg
        dm = by["mean"]
        L.append(f"  tau {tau:4d}: picks {len(s):5d} nights {len(by):4d} mean {s.r.mean():+6.1f} med {s.r.median():+6.1f} "
                 f"net {s.r.mean() - 15:+6.1f} hit {(s.r > 0).mean():.3f} t(day) {clus_t(dm.to_numpy()):5.2f} | "
                 f"leg {leg.mean():+6.2f} bp/night (x250 {leg.mean() * 250 / 100:+5.2f}%/yr of leg)")
    L.append("")
    L.append("== paired leg delta vs 15:40 (per night, all sessions) ==")
    base = legs[1540]
    yr = pd.DatetimeIndex(nights_all).year
    for tau in TAUS:
        d = (legs[tau] - base).to_numpy()
        h1 = d[pd.DatetimeIndex(nights_all) < SPLIT]
        h2 = d[pd.DatetimeIndex(nights_all) >= SPLIT]
        s_ = np.sort(d)
        L.append(f"  tau {tau:4d}: delta {d.mean():+6.2f} bp/night t {clus_t(d):5.2f} med {np.median(d):+5.2f} "
                 f"h1 {h1.mean():+6.2f} h2 {h2.mean():+6.2f} ex-top-5 {s_[:-5].mean():+6.2f} ex-bottom-5 {s_[5:].mean():+6.2f} "
                 f"= {d.mean() * 250 / 100 * 0.65:+5.2f}pp/yr at w .65 | by year " +
                 " ".join(f"{y}:{d[yr == y].mean():+.1f}" for y in sorted(set(yr))))
    L.append("")
    L.append("== set change vs 15:40 (name-days) ==")
    s40 = set(zip(sel[sel.tau == 1540].date, sel[sel.tau == 1540].sym))
    for tau in TAUS:
        s = sel[sel.tau == tau]
        key = list(zip(s.date, s.sym))
        inb = np.array([k in s40 for k in key])
        st = x[(x.tau == 1540)]
        st_key = set(zip(st.date, st.sym))
        drop = [k for k in s40 if k not in set(key)]
        dr = sel[(sel.tau == 1540)].set_index(["date", "sym"]).r
        dropped_r = dr.loc[[k for k in drop if k in dr.index]].mean() if drop else float("nan")
        L.append(f"  tau {tau:4d}: common {int(inb.sum()):5d} (r {s.r[inb].mean():+6.1f})  added {int((~inb).sum()):5d} "
                 f"(r {s.r[~inb].mean() if (~inb).any() else float('nan'):+6.1f})  dropped-from-15:40 {len(drop):5d} (r {dropped_r:+6.1f})")
    L.append("")
    L.append("== deflation note: 9 taus vs 15:40; max-of-9 null t ~2.6 ==")
    txt = "\n".join(L) + "\n"
    open(OUT, "w").write(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
