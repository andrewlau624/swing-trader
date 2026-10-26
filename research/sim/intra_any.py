"""Study INTRA-ANY (round1_prose.md "## Amendment - Study INTRA-ANY", N 1044-1045): a learned model that may fire at any 5-minute
check time on any name in the point-in-time volatile-liquid (volday) and in-play (inplay) minute panels, exit at the closing
auction (A) or the next open (B). Fit 2016-2021, judge 2022-01..2026-09 (one look).
usage: PYTHONPATH=. .venv/bin/python -m research.sim.intra_any build | run
"""
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
SH = Path.home() / "data/sharadar"
ROWS = PROG / "intra_any_rows.parquet"
OUT = PROG / "intra_any_out.txt"
KS = list(range(30, 361, 5))                # 10:00 .. 15:30 every 5 minutes
HOURLY = {30, 90, 150, 210, 270, 330}
FIT_END, JUDGE0, MID = "2021-12-31", "2022-01-01", "2024-01-01"
DEV_END = "2019-12-31"
COST = 5.0                                  # bp, entry (marketable order); exit at the auction = 0
MIN_BARS = 300
SRC = {"volday": 0, "inplay": 1}
FEATS = ["ropen", "rpc", "gap", "r5", "r15", "r30", "r60", "dhod", "dlod", "dvwap", "rng", "rv30", "rvday", "relvol",
         "v5share", "spy_ropen", "spy_r30", "rel_spy", "k", "dow", "ret1", "ret5", "ret20", "vol20", "ladv", "src"]


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with OUT.open("a") as f:
        f.write(s + "\n")


# ----------------------------------------------------------------------------- build
def _minutes(f: Path, src: str) -> pd.DataFrame:
    m = pd.read_parquet(f, columns=["sym", "t", "o", "h", "l", "c", "v"])
    if m.empty:
        return m
    t = pd.to_datetime(m.t, utc=True).dt.tz_convert("America/New_York")
    m["date"] = t.dt.normalize().dt.tz_localize(None)
    m["mos"] = (t.dt.hour * 60 + t.dt.minute) - 570
    m = m[(m.mos >= 0) & (m.mos < 390)].drop(columns="t")
    m["src"] = src
    return m


def _grid(m: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """name-days x 390 matrices (ffilled closes; missing opens = prior close; missing volume = 0)."""
    key = m.groupby(["src", "sym", "date"]).size()
    key = key[key >= MIN_BARS].reset_index(name="n")
    m = m.merge(key[["src", "sym", "date"]].assign(row=np.arange(len(key))), on=["src", "sym", "date"])
    nd = len(key)
    A = {}
    for col in "ohlcv":
        X = np.full((nd, 390), np.nan)
        X[m.row.to_numpy(), m.mos.to_numpy()] = m[col].to_numpy(float)
        A[col] = X
    C = pd.DataFrame(A["c"]).ffill(axis=1).bfill(axis=1).to_numpy()
    A["c"] = C
    for col in "ohl":
        X = A[col]
        X[np.isnan(X)] = C[np.isnan(X)]
        A[col] = X
    A["v"] = np.nan_to_num(A["v"])
    return key, A


def _spy() -> dict[pd.Timestamp, np.ndarray]:
    out = {}
    for f in sorted((ROOT / "data/research/night/m1").glob("SPY_*.parquet")):
        x = pd.read_parquet(f, columns=["timestamp", "close"])
        t = pd.to_datetime(x.timestamp, utc=True).dt.tz_convert("America/New_York")
        x["date"] = t.dt.normalize().dt.tz_localize(None)
        x["mos"] = (t.dt.hour * 60 + t.dt.minute) - 570
        x = x[(x.mos >= 0) & (x.mos < 390)]
        for d, g in x.groupby("date"):
            v = np.full(390, np.nan)
            v[g.mos.to_numpy()] = g.close.to_numpy(float)
            out[d] = pd.Series(v).ffill().bfill().to_numpy()
    return out


def _daily(syms: set[str]) -> pd.DataFrame:
    """Sharadar daily context keyed by Alpaca symbol (Sharadar suffix digits stripped) and date."""
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker"])
    tk = tk[tk.table == "SEP"].ticker.unique()
    want = [t for t in tk if re.sub(r"\d+$", "", t) in syms]
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "close", "closeunadj", "volume"],
                         filters=[("ticker", "in", want)])
    st["date"] = pd.to_datetime(st.date)
    st = st[st.date >= "2015-06-01"].sort_values(["ticker", "date"])
    g = st.groupby("ticker")
    st["pc"] = g.closeunadj.shift(1)
    r = g.close.pct_change()
    # context as of the PRIOR close (d-1): v1 used the same-day close here (lookahead; disclosed in round1_prose.md)
    st["ret1"] = g.close.pct_change().groupby(st.ticker).shift(1)
    st["ret5"] = g.close.pct_change(5).groupby(st.ticker).shift(1)
    st["ret20"] = g.close.pct_change(20).groupby(st.ticker).shift(1)
    st["vol20"] = r.groupby(st.ticker).transform(lambda x: x.shift(1).rolling(20, min_periods=15).std()) * np.sqrt(252)
    st["ladv"] = np.log((st.closeunadj * st.volume).groupby(st.ticker).transform(lambda x: x.shift(1).rolling(20, min_periods=15).median()))
    st["nxt"] = g.open.shift(-1) / st.close          # open(d+1) / close(d), split-adjusted series, same basis
    st["sym"] = st.ticker.str.replace(r"\d+$", "", regex=True)
    st = st.drop_duplicates(["sym", "date"], keep="last")
    return st[["sym", "date", "pc", "ret1", "ret5", "ret20", "vol20", "ladv", "nxt"]]


def _roll_std(R: np.ndarray, n: int) -> np.ndarray:
    """rolling std over the last n columns of R (NaN -> 0), per column."""
    R = np.nan_to_num(R)
    c1 = np.cumsum(R, axis=1)
    c2 = np.cumsum(R * R, axis=1)
    z = np.zeros((R.shape[0], 1))
    c1 = np.hstack([z, c1])
    c2 = np.hstack([z, c2])
    j = np.arange(R.shape[1]) + 1
    i = np.maximum(j - n, 0)
    cnt = (j - i).astype(float)
    s1 = c1[:, j] - c1[:, i]
    s2 = c2[:, j] - c2[:, i]
    var = s2 / cnt - (s1 / cnt) ** 2
    return np.sqrt(np.maximum(var, 0))


def build() -> None:
    files = [(f, "volday") for f in sorted((ROOT / "data/research/volday").glob("m1_*.parquet"))]
    files += [(f, "inplay") for f in sorted((ROOT / "data/research/inplay").glob("m1_*.parquet"))]
    syms = set()
    for f, _ in files:
        syms |= set(pd.read_parquet(f, columns=["sym"]).sym.unique())
    print(f"{len(files)} month files, {len(syms)} symbols", flush=True)
    daily = _daily(syms)
    spy = _spy()
    out = []
    for f, src in files:
        m = _minutes(f, src)
        if m.empty:
            continue
        key, A = _grid(m)
        if key.empty:
            continue
        O, H, L, C, V = A["o"], A["h"], A["l"], A["c"], A["v"]
        key = key.merge(daily, on=["sym", "date"], how="left")
        pc = key.pc.to_numpy()
        o0 = O[:, 0]
        last = C[:, 389]
        cumH = np.maximum.accumulate(H, axis=1)
        cumL = np.minimum.accumulate(L, axis=1)
        cumV = np.cumsum(V, axis=1)
        cumDV = np.cumsum(V * C, axis=1)
        R1 = np.diff(np.log(C), axis=1, prepend=np.log(C[:, :1]))
        rv30 = _roll_std(R1, 30)
        rvday = _roll_std(R1, 390)
        S = np.full((len(key), 390), np.nan)
        for i, d in enumerate(key.date):
            v = spy.get(d)
            if v is not None:
                S[i] = v
        adv = np.exp(key.ladv.to_numpy())
        for k in KS:
            c = C[:, k]
            e = O[:, k + 1]
            with np.errstate(all="ignore"):
                row = dict(
                    src=key.src.map(SRC).to_numpy(), sym=key.sym.to_numpy(), date=key.date.to_numpy(), k=k,
                    ropen=c / o0 - 1, rpc=c / pc - 1, gap=o0 / pc - 1,
                    r5=c / C[:, k - 5] - 1, r15=c / C[:, k - 15] - 1, r30=c / C[:, k - 30] - 1, r60=c / np.where(k >= 60, C[:, max(k - 60, 0)], o0) - 1,
                    dhod=c / cumH[:, k] - 1, dlod=c / cumL[:, k] - 1, dvwap=c / (cumDV[:, k] / np.where(cumV[:, k] > 0, cumV[:, k], np.nan)) - 1,
                    rng=(cumH[:, k] - cumL[:, k]) / pc, rv30=rv30[:, k], rvday=rvday[:, k],
                    relvol=cumDV[:, k] / adv / ((k + 1) / 390), v5share=V[:, k - 4:k + 1].sum(1) / np.where(cumV[:, k] > 0, cumV[:, k], np.nan),
                    spy_ropen=S[:, k] / S[:, 0] - 1, spy_r30=S[:, k] / S[:, k - 30] - 1,
                    dow=pd.DatetimeIndex(key.date).dayofweek.to_numpy(),
                    ret1=key.ret1.to_numpy(), ret5=key.ret5.to_numpy(), ret20=key.ret20.to_numpy(), vol20=key.vol20.to_numpy(), ladv=key.ladv.to_numpy(),
                    entry=e, yA=(last / e - 1) * 1e4,
                )
                row["rel_spy"] = row["ropen"] - row["spy_ropen"]
                row["yB"] = ((last / e) * key.nxt.to_numpy() - 1) * 1e4
            out.append(pd.DataFrame(row))
        print(f"{f.name} {src}: {len(key)} name-days", flush=True)
    df = pd.concat(out, ignore_index=True)
    for c in df.columns:
        if df[c].dtype == np.float64:
            df[c] = df[c].astype(np.float32)
    df.to_parquet(ROWS)
    print(f"rows {len(df):,} -> {ROWS}", flush=True)


# ----------------------------------------------------------------------------- run
def clus_t(y: np.ndarray, d: np.ndarray) -> float:
    y = np.asarray(y, float)
    n = len(y)
    if n < 3:
        return float("nan")
    e = y - y.mean()
    s = pd.Series(e).groupby(d).sum().to_numpy()
    se = np.sqrt((s * s).sum()) / n
    return y.mean() / se if se > 0 else float("nan")


def stats(y: np.ndarray, d: np.ndarray) -> str:
    y = np.asarray(y, float)
    if len(y) == 0:
        return "n 0"
    top = np.sort(y)[-5:].sum() if len(y) > 5 else 0.0
    return (f"n {len(y):,} mean {y.mean():+.1f} med {np.median(y):+.1f} hit {np.mean(y > 0):.2f} t {clus_t(y, d):.2f} "
            f"ex-top5 {(y.sum() - top) / max(len(y) - 5, 1):+.1f}")


def first_trigger(te: pd.DataFrame, pred: np.ndarray, thr: float, ks: set | None = None) -> pd.DataFrame:
    x = te[["src", "sym", "date", "k", "yA", "yB"]].copy()
    x["pred"] = pred
    if ks is not None:
        x = x[x.k.isin(ks)]
    x = x[x.pred >= thr].sort_values(["src", "sym", "date", "k"])
    return x.drop_duplicates(["src", "sym", "date"], keep="first")


def fit(tr: pd.DataFrame, y: np.ndarray, seed: int = 0):
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=500,
                                         l2_regularization=1.0, random_state=seed).fit(tr[FEATS].to_numpy(np.float32), y)


def shuffle_within(df: pd.DataFrame, col: str, rng: np.random.Generator) -> np.ndarray:
    """shuffle labels among the rows of the same date (keeps the day's distribution; kills any name/time information)."""
    y = df[col].to_numpy(np.float64).copy()
    order = np.argsort(df.date.to_numpy(), kind="stable")
    ys = y[order]
    ds = df.date.to_numpy()[order]
    b = np.flatnonzero(np.r_[True, ds[1:] != ds[:-1], True])
    for a, z in zip(b[:-1], b[1:]):
        ys[a:z] = rng.permutation(ys[a:z])
    out = np.empty_like(y)
    out[order] = ys
    return out


def judge(df: pd.DataFrame, lab: str, name: str) -> None:
    tr = df[df.date <= FIT_END]
    te = df[df.date >= JUDGE0]
    log(f"\n=== {name}: label {lab}; fit {len(tr):,} rows to {FIT_END}, judge {len(te):,} rows {JUDGE0}..{te.date.max().date()} "
        f"({te.groupby(['src','sym','date']).ngroups:,} name-days)")
    # development read (not judged)
    dv_tr, dv_te = df[df.date <= DEV_END], df[(df.date > DEV_END) & (df.date <= FIT_END)]
    m0 = fit(dv_tr, dv_tr[lab].to_numpy())
    p0 = m0.predict(dv_te[FEATS].to_numpy(np.float32))
    thr0 = np.quantile(m0.predict(dv_tr[FEATS].to_numpy(np.float32)), 0.9)
    ft0 = first_trigger(dv_te, p0, thr0)
    log(f"dev (fit 2016-19 -> 2020-21, informational): first-trigger gross {stats(ft0[lab], ft0.date)}; "
        f"corr(pred,y) {np.corrcoef(p0, dv_te[lab])[0,1]:+.3f}")
    # the judged model
    m = fit(tr, tr[lab].to_numpy())
    ptr = m.predict(tr[FEATS].to_numpy(np.float32))
    thr = float(np.quantile(ptr, 0.9))
    p = m.predict(te[FEATS].to_numpy(np.float32))
    y = te[lab].to_numpy(float)
    log(f"threshold (fit p90 of predictions) {thr:+.1f}bp; judge pred mean {p.mean():+.1f}, share >= thr {np.mean(p >= thr):.3f}")
    log(f"direction vs volatility: corr(pred, y) {np.corrcoef(p, y)[0,1]:+.4f}, corr(pred, |y|) {np.corrcoef(p, np.abs(y))[0,1]:+.4f}")
    dec = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False).to_numpy()
    log("per-row prediction deciles (gross bp mean / median / hit / mean|y|):")
    for q in range(10):
        s = y[dec == q]
        log(f"  D{q+1}: {s.mean():+6.1f} / {np.median(s):+6.1f} / {np.mean(s > 0):.3f} / {np.abs(s).mean():6.1f}   pred {p[dec == q].mean():+.1f}")
    log(f"all rows gross: mean {y.mean():+.1f} hit {np.mean(y > 0):.3f}")
    # executable: first trigger per name-day
    ft = first_trigger(te, p, thr)
    net = ft[lab].to_numpy(float) - COST
    d = ft.date.to_numpy()
    ybar_k = te.groupby("k")[lab].mean()
    base = ybar_k.reindex(ft.k).to_numpy().mean() if len(ft) else float("nan")
    log(f"FIRST-TRIGGER (>= thr), hold to exit: gross {stats(ft[lab], d)}")
    log(f"  net {COST:.0f}bp: {stats(net, d)} | net 10bp mean {net.mean() - 5:+.1f} | time-matched unconditional {base:+.1f} -> excess {ft[lab].mean() - base:+.1f}")
    for nm, msk in (("2022-23", ft.date < MID), ("2024-26", ft.date >= MID)):
        log(f"  {nm}: net {stats(net[msk.to_numpy()], d[msk.to_numpy()])}")
    log(f"  by year (net mean / n): " + ", ".join(f"{yy} {g.mean() - COST:+.0f}/{len(g)}" for yy, g in ft.groupby(ft.date.dt.year)[lab]))
    log(f"  mean trigger time {ft.k.mean() / 60 + 9.5:.2f}h; triggers by src: {ft.src.value_counts().to_dict()}")
    fh = first_trigger(te, p, thr, HOURLY)
    log(f"  hourly grid only: net {stats(fh[lab].to_numpy(float) - COST, fh.date.to_numpy())}")
    # placebo: within-day shuffled labels, refit, same procedure
    rng = np.random.default_rng(7)
    pl = []
    for s in range(3):
        ys = shuffle_within(tr, lab, rng)
        mp = fit(tr, ys, seed=s + 1)
        thp = float(np.quantile(mp.predict(tr[FEATS].to_numpy(np.float32)), 0.9))
        fp = first_trigger(te, mp.predict(te[FEATS].to_numpy(np.float32)), thp)
        pl.append(fp[lab].mean() - COST if len(fp) else float("nan"))
    log(f"  placebo first-trigger net (3 refits): {', '.join(f'{v:+.1f}' for v in pl)} vs real {net.mean():+.1f}")
    # importance (permutation on a judge subsample, MSE-based)
    sub = te.sample(min(200_000, len(te)), random_state=0)
    Xs = sub[FEATS].to_numpy(np.float32)
    ysub = sub[lab].to_numpy(float)
    b0 = np.mean((m.predict(Xs) - ysub) ** 2)
    imp = {}
    r2 = np.random.default_rng(1)
    for j, fn in enumerate(FEATS):
        Xp = Xs.copy()
        Xp[:, j] = r2.permutation(Xp[:, j])
        imp[fn] = np.mean((m.predict(Xp) - ysub) ** 2) - b0
    top = sorted(imp.items(), key=lambda kv: -kv[1])[:10]
    log("  permutation importance (dMSE, top 10): " + ", ".join(f"{k} {v:.1f}" for k, v in top))
    # gates
    ok = dict(mean=net.mean() >= 10, t=clus_t(net, d) >= 2, median=np.median(net) > 0,
              h1=net[(ft.date < MID).to_numpy()].mean() > 0 if (ft.date < MID).any() else False,
              h2=net[(ft.date >= MID).to_numpy()].mean() > 0 if (ft.date >= MID).any() else False,
              extop5=(net.sum() - np.sort(net)[-5:].sum()) / max(len(net) - 5, 1) > 0,
              excess=(ft[lab].mean() - base) >= 10, placebo=all(v < net.mean() for v in pl))
    log(f"  GATES {ok} -> {'PASS' if all(ok.values()) else 'KILL'}")


def run() -> None:
    if OUT.exists():
        OUT.unlink()
    df = pd.read_parquet(ROWS)
    df["date"] = pd.to_datetime(df.date)
    n0 = len(df)
    df = df[np.isfinite(df.yA) & np.isfinite(df.entry) & (df.entry > 0) & np.isfinite(df.ladv)]
    log(f"INTRA-ANY (N 1044-1045), rows {n0:,} -> {len(df):,} with labels/context; {df.date.min().date()}..{df.date.max().date()}; "
        f"name-days {df.groupby(['src','sym','date']).ngroups:,}; src counts {df.src.value_counts().to_dict()}")
    log(f"label A (to last 1-min close) all rows mean {df.yA.mean():+.1f}bp; label B (to next open) mean {df.yB.mean():+.1f}bp")
    judge(df, "yA", "A: entry at any 5-min check -> closing auction (N 1044)")
    dB = df[np.isfinite(df.yB)]
    judge(dB, "yB", "B: entry at any 5-min check -> next open (N 1045)")
    log("\nDisclosed choices: GBM params as SEQ-NIGHT but min_samples_leaf 500 (larger panel); threshold = fit-period p90 of predictions; "
        "exit proxy = last 1-min close (not the cross print); entry = open of bar k+1; inplay files contain only scanner name-days.")


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"build": build, "run": run}[cmd]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
