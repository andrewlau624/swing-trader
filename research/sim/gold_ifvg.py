"""GOLD-IFVG: Reddit "first 15m IFVG in the Asia session, gold, 1:1, BE at 0.68R" (pre-reg round1_prose.md, N 988)."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/gold/gcv_1m_2016_2025.parquet"
OUT = ROOT / "data/research/program/gold_ifvg_out.txt"
COST1, COST2 = 0.20, 0.40
BE_AT, MIN_RISK = 0.68, 0.5


def load_1m():
    if not CACHE.exists():
        import databento as db
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        c = db.Historical(os.environ["DATABENTO_API_KEY"])
        df = c.timeseries.get_range(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=["GC.v.0"], stype_in="continuous",
                                    start="2016-01-01", end="2026-01-01").to_df()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CACHE)
    df = pd.read_parquet(CACHE)
    df.index = df.index.tz_convert("America/New_York")
    return df[["open", "high", "low", "close", "instrument_id"]]


def session_key(ts):
    # Asia window 19:00-03:00 ET belongs to the session that starts at 19:00
    d = ts.normalize()
    return np.where(ts.hour >= 19, d, d - pd.Timedelta(days=1))


def trades(m1, stop_mode):
    m15 = m1.resample("15min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "instrument_id": "last"}).dropna()
    in_win = (m15.index.hour >= 19) | (m15.index.hour < 3)
    m15 = m15.assign(sess=session_key(m15.index), win=in_win)
    m1 = m1.assign(sess=session_key(m1.index))
    out = []
    m1_by = {k: g for k, g in m1.groupby("sess")}
    for sess, g in m15.groupby("sess"):
        w = g[g.win]
        if len(w) < 10 or w.instrument_id.nunique() > 1:
            continue
        h, l, c, idx = w.high.values, w.low.values, w.close.values, w.index
        fvgs = []
        hit = None
        for j in range(len(w)):
            for (i, kind, lo, hi) in fvgs:
                if j - i > 16 or j <= i:
                    continue
                if kind == "bull" and c[j] < lo:
                    hit = (i, j, "short")
                elif kind == "bear" and c[j] > hi:
                    hit = (i, j, "long")
                if hit:
                    break
            if hit:
                break
            if j >= 2:
                if h[j - 2] < l[j]:
                    fvgs.append((j, "bull", h[j - 2], l[j]))
                elif l[j - 2] > h[j]:
                    fvgs.append((j, "bear", h[j], l[j - 2]))
        if not hit:
            continue
        i, j, side = hit
        entry = c[j]
        if stop_mode == "S1":
            stop = l[i] if side == "short" else h[i]
        else:
            stop = h[i - 2:j + 1].max() if side == "short" else l[i - 2:j + 1].min()
        risk = (stop - entry) if side == "short" else (entry - stop)
        if risk < MIN_RISK:
            continue
        t0 = idx[j] + pd.Timedelta(minutes=15)
        end = (sess + pd.Timedelta(days=1)).replace(hour=12)
        path = m1_by.get(sess)
        if path is None:
            continue
        path = pd.concat([path, m1_by.get(sess + pd.Timedelta(days=1), path.iloc[:0])])
        path = path[(path.index >= t0) & (path.index < end)]
        if path.empty or path.instrument_id.nunique() > 1 or path.instrument_id.iloc[0] != w.instrument_id.iloc[-1]:
            continue
        out.append(dict(sess=sess, t=idx[j], side=side, entry=entry, risk=risk, **resolve(path, side, entry, risk)))
    return pd.DataFrame(out)


def resolve(path, side, entry, risk):
    sgn = 1 if side == "long" else -1
    stop_r, be = -1.0, False
    for hi, lo in zip(path.high.values, path.low.values):
        fav = ((hi - entry) if sgn > 0 else (entry - lo)) / risk
        adv = ((lo - entry) if sgn > 0 else (entry - hi)) / risk
        if adv <= stop_r:
            return dict(R=stop_r, res="be" if be else "loss")
        if fav >= 1.0:
            return dict(R=1.0, res="win")
        if not be and fav >= BE_AT:
            be, stop_r = True, 0.0
    r = sgn * (path.close.values[-1] - entry) / risk
    return dict(R=r, res="time")


def clus_t(x):
    x = np.asarray(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def placebo(df, path_fn, n=200, seed=7):
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n):
        flips = rng.integers(0, 2, len(df))
        means.append(np.mean([path_fn(r, f) for r, f in zip(df.itertuples(), flips)]))
    return np.array(means)


def report(df, label, lines, pl=None):
    if df.empty:
        lines.append(f"{label}: n 0")
        return
    net1 = df.R - COST1 / df.risk
    net2 = df.R - COST2 / df.risk
    yr = df.sess.dt.year
    h1, h2 = net1[yr <= 2020], net1[yr >= 2021]
    vc = df.res.value_counts(normalize=True).round(3).to_dict()
    lines.append(f"{label}: n {len(df)} ({len(df) / 10:.0f}/yr)  outcomes {vc}")
    lines.append(f"  win rate (TP/all) {(df.res == 'win').mean():.1%}; wins/(wins+losses) "
                 f"{(df.res == 'win').sum() / max(1, df.res.isin(['win', 'loss']).sum()):.1%}")
    lines.append(f"  gross R {df.R.mean():+.3f} | net1 {net1.mean():+.3f} t {clus_t(net1):.2f} | net2 {net2.mean():+.3f} | "
                 f"median risk {df.risk.median():.2f} $/oz")
    lines.append(f"  halves net1 2016-20 {h1.mean():+.3f} (n {len(h1)}) / 2021-25 {h2.mean():+.3f} (n {len(h2)})")
    lines.append("  by year net1: " + " ".join(f"{y}:{v:+.2f}" for y, v in net1.groupby(yr).mean().items()))
    lines.append(f"  long {df[df.side == 'long'].R.mean():+.3f} (n {(df.side == 'long').sum()}) / "
                 f"short {df[df.side == 'short'].R.mean():+.3f} (n {(df.side == 'short').sum()})")
    if pl is not None:
        lines.append(f"  placebo gross R mean {pl.mean():+.3f}, 95th pct {np.percentile(pl, 95):+.3f}; real {df.R.mean():+.3f} "
                     f"-> pct {(pl < df.R.mean()).mean():.0%}")


def main():
    m1 = load_1m()
    lines = [f"GOLD-IFVG (N 988). GC.v.0 1m {m1.index[0]} .. {m1.index[-1]}"]
    m1s = m1.assign(sess=session_key(m1.index))
    by = {k: g for k, g in m1s.groupby("sess")}
    for mode in ("S2", "S1"):
        df = trades(m1, mode)
        df["sess"] = pd.to_datetime(df.sess)

        def path_fn(r, flip):
            p = pd.concat([by[r.sess], by.get(r.sess + pd.Timedelta(days=1), by[r.sess].iloc[:0])])
            end = (r.sess + pd.Timedelta(days=1)).replace(hour=12)
            p = p[(p.index >= r.t + pd.Timedelta(minutes=15)) & (p.index < end)]
            return resolve(p, "long" if flip else "short", r.entry, r.risk)["R"]
        pl = placebo(df, path_fn, n=200) if mode == "S2" else None
        report(df, f"{mode} ({'PRIMARY' if mode == 'S2' else 'report'})", lines, pl)
        if mode == "S2":
            prim = df
    # ceiling: MGC 10 oz, risk 1% of account
    tpy = len(prim) / 10
    net = (prim.R - COST1 / prim.risk).mean()
    one = prim.risk.median() * 10
    for acct in (2300, 10_000, 25_000):
        k = int(acct * 0.01 // one)
        ok = one <= 0.02 * acct
        dollars = tpy * net * max(k, 1 if ok else 0) * one
        lines.append(f"ceiling ${acct:,}: one MGC risk ${one:.0f}, contracts {max(k, 1 if ok else 0)}, "
                     f"{'tradable' if ok else 'NOT tradable (1 MGC > 2% risk)'}; ~${dollars:,.0f}/yr = {dollars / acct * 100:+.1f}%/yr pre-tax")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
