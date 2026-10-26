"""Study CHART-YOLO (round1_prose.md "## Amendment - Study CHART-YOLO", N 1049): textbook chart patterns detected by the public
`foduucom/stockmarket-pattern-detection-yolov8` model on rendered 100-day candlestick charts of liquid US stocks; forward returns at
the auctions and over 5 days vs SPY. Right-edge detections are the signal; earlier (stale) detections are the control.
usage: PYTHONPATH=. .venv/bin/python -m research.sim.chart_yolo probe | run
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data/research/chart_yolo"
SH = Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/chart_yolo_out.txt"
DET = D / "detections.parquet"
N_SAMPLE = 30_000
BARS = 100
EDGE = 0.85                          # a detection is a SIGNAL if its box right edge >= EDGE of the chart width
CONF = 0.25
BULL = {"W_Bottom", "Head and shoulders bottom"}
BEAR = {"M_Head", "Head and shoulders top"}
W, H, DPI = 640, 480, 100


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with OUT.open("a") as f:
        f.write(s + "\n")


def universe() -> pd.DataFrame:
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"])
    st = st[st.ticker.isin(ok)]
    st["date"] = pd.to_datetime(st.date)
    st = st[st.date >= "2015-06-01"].sort_values(["ticker", "date"]).reset_index(drop=True)
    g = st.groupby("ticker")
    st["pc"] = g.closeunadj.shift(1)
    st["adv"] = (st.closeunadj * st.volume).groupby(st.ticker).transform(lambda x: x.shift(1).rolling(20, min_periods=15).median())
    st["nbar"] = g.cumcount()
    st["o1"] = g.open.shift(-1)
    st["c1"] = g.close.shift(-1)
    st["c5"] = g.close.shift(-5)
    return st


def spy_ret() -> pd.DataFrame:
    s = pd.read_parquet(SH / "funds.parquet", columns=["ticker", "date", "open", "close"], filters=[("ticker", "==", "SPY")])
    s["date"] = pd.to_datetime(s.date)
    s = s.sort_values("date").reset_index(drop=True)
    s["s_l1"] = s.open.shift(-1) / s.close - 1
    s["s_l2"] = s.close.shift(-1) / s.open.shift(-1) - 1
    s["s_l5"] = s.close.shift(-5) / s.close - 1
    return s[["date", "s_l1", "s_l2", "s_l5"]]


def render(o, h, l, c, path: Path) -> None:
    """mplfinance-like daily candles: green up / red down, grey grid, right price axis."""
    fig, ax = plt.subplots(figsize=(W / DPI, H / DPI), dpi=DPI)
    x = np.arange(len(c))
    up = c >= o
    ax.vlines(x, l, h, color=np.where(up, "#26a69a", "#ef5350"), linewidth=1)
    ax.bar(x[up], (c - o)[up], bottom=o[up], color="#26a69a", width=0.7)
    ax.bar(x[~up], (o - c)[~up], bottom=c[~up], color="#ef5350", width=0.7)
    ax.set_facecolor("#e6e6e6")
    ax.grid(True, color="white", linewidth=0.8)
    ax.yaxis.tick_right()
    ax.set_xlim(-1, len(c))
    ax.tick_params(labelsize=6)
    ax.set_xticks(x[::20])
    fig.subplots_adjust(left=0.02, right=0.9, top=0.97, bottom=0.08)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def sample(st: pd.DataFrame, n: int, seed: int = 0) -> pd.DataFrame:
    el = st[(st.date >= "2016-01-01") & (st.date <= "2026-09-30") & (st.pc >= 5) & (st.adv >= 1e7) & (st.nbar >= BARS) & st.c5.notna()]
    return el.sample(n, random_state=seed)[["ticker", "date"]].reset_index(drop=True)


def detect(st: pd.DataFrame, picks: pd.DataFrame, model, img_dir: Path, keep_images: bool = False) -> pd.DataFrame:
    img_dir.mkdir(parents=True, exist_ok=True)
    by = {t: g.reset_index(drop=True) for t, g in st[st.ticker.isin(set(picks.ticker))].groupby("ticker")}
    rows = []
    for i, r in enumerate(picks.itertuples()):
        g = by[r.ticker]
        j = int(g.index[g.date == r.date][0])
        w = g.iloc[j - BARS + 1: j + 1]
        p = img_dir / f"{r.ticker}_{r.date.date()}.png"
        render(w.open.to_numpy(float), w.high.to_numpy(float), w.low.to_numpy(float), w.close.to_numpy(float), p)
        res = model.predict(str(p), conf=CONF, verbose=False, imgsz=640)[0]
        names = res.names
        n_det = 0
        for b in res.boxes:
            x1, y1, x2, y2 = b.xyxyn[0].tolist()
            rows.append(dict(ticker=r.ticker, date=r.date, cls=names[int(b.cls)], conf=float(b.conf), x1=x1, x2=x2, y1=y1, y2=y2))
            n_det += 1
        if n_det == 0:
            rows.append(dict(ticker=r.ticker, date=r.date, cls=None, conf=np.nan, x1=np.nan, x2=np.nan, y1=np.nan, y2=np.nan))
        if not keep_images:
            p.unlink()
        if i % 500 == 0:
            print(f"  {i}/{len(picks)} ({len(rows)} rows)", flush=True)
    return pd.DataFrame(rows)


def load_model():
    from ultralytics import YOLO
    return YOLO(str(D / "model/model.pt"))


def probe() -> None:
    st = universe()
    picks = sample(st, 60, seed=123)
    det = detect(st, picks, load_model(), D / "probe_images", keep_images=True)
    print(det.cls.value_counts(dropna=False).to_dict())
    print(f"charts with >= 1 detection: {det.dropna(subset=['cls']).groupby(['ticker','date']).ngroups}/60; right-edge: "
          f"{(det.x2 >= EDGE).sum()}")
    print(det.dropna(subset=["cls"]).head(12).to_string())


def clus_t(y, d):
    y = np.asarray(y, float)
    e = y - y.mean()
    s = pd.Series(e).groupby(np.asarray(d)).sum().to_numpy()
    se = np.sqrt((s * s).sum()) / len(y)
    return y.mean() / se if se > 0 else float("nan")


def stats(y, d) -> str:
    y = np.asarray(y, float)
    m = np.isfinite(y)
    y, d = y[m], np.asarray(d)[m]
    if len(y) < 3:
        return f"n {len(y)}"
    top = np.sort(y)[-5:].sum() if len(y) > 5 else 0.0
    return (f"n {len(y)} mean {y.mean():+.1f} med {np.median(y):+.1f} hit {np.mean(y > 0):.2f} t {clus_t(y, d):.2f} "
            f"ex-top5 {(y.sum() - top) / max(len(y) - 5, 1):+.1f}")


def run() -> None:
    if OUT.exists():
        OUT.unlink()
    st = universe()
    if DET.exists():
        det = pd.read_parquet(DET)
    else:
        parts = sorted(D.glob("detections_*.parquet"))
        if parts:
            det = pd.concat([pd.read_parquet(f) for f in parts], ignore_index=True)
        else:
            picks = sample(st, N_SAMPLE)
            det = detect(st, picks, load_model(), D / "images")
        det.to_parquet(DET)
    det["date"] = pd.to_datetime(det.date)
    lab = st[["ticker", "date", "close", "o1", "c1", "c5"]].merge(spy_ret(), on="date", how="left")
    lab["l1"] = (lab.o1 / lab.close - 1 - lab.s_l1) * 1e4
    lab["l2"] = (lab.c1 / lab.o1 - 1 - lab.s_l2) * 1e4
    lab["l5"] = (lab.c5 / lab.close - 1 - lab.s_l5) * 1e4
    x = det.merge(lab[["ticker", "date", "l1", "l2", "l5"]], on=["ticker", "date"], how="left")
    charts = x.groupby(["ticker", "date"]).ngroups
    hits = x.dropna(subset=["cls"])
    log(f"CHART-YOLO (N 1049): {charts:,} charts, {len(hits):,} detections on {hits.groupby(['ticker','date']).ngroups:,} charts; "
        f"classes {hits.cls.value_counts().to_dict()}; right-edge (x2 >= {EDGE}) {int((hits.x2 >= EDGE).sum())}")
    base = x.drop_duplicates(["ticker", "date"])
    log(f"universe baseline (all sampled charts, excess vs SPY): L1 {stats(base.l1, base.date)} | L2 {stats(base.l2, base.date)} | L5 {stats(base.l5, base.date)}")
    hits = hits.assign(edge=hits.x2 >= EDGE, side=np.where(hits.cls.isin(BULL), "BULL", np.where(hits.cls.isin(BEAR), "BEAR", "NONE")))
    # one row per chart x side (a chart with two bull boxes counts once)
    u = hits.sort_values("conf", ascending=False).drop_duplicates(["ticker", "date", "side", "edge"])
    res = {}
    for side in ("BULL", "BEAR", "NONE"):
        for edge in (True, False):
            s = u[(u.side == side) & (u.edge == edge)]
            tag = f"{side} {'RIGHT-EDGE' if edge else 'stale'}"
            log(f"\n{tag}: classes {s.cls.value_counts().to_dict()}")
            for L in ("l1", "l2", "l5"):
                log(f"  {L}: {stats(s[L], s.date)}")
            res[(side, edge)] = s
    for cls in sorted(hits.cls.unique()):
        s = u[(u.cls == cls) & u.edge]
        log(f"  by class right-edge {cls}: L5 {stats(s.l5, s.date)} | L2 {stats(s.l2, s.date)}")
    b, br = res[("BULL", True)], res[("BEAR", True)]
    for nm, m1, m2 in (("2016-20", b.date < "2021-01-01", br.date < "2021-01-01"), ("2021-26", b.date >= "2021-01-01", br.date >= "2021-01-01")):
        log(f"  {nm}: BULL L5 {stats(b[m1].l5, b[m1].date)} | BEAR L5 {stats(br[m2].l5, br[m2].date)}")
    log(f"  by conf tercile BULL right-edge L5: " + ", ".join(
        f"{q} {g.l5.mean():+.0f}/{len(g)}" for q, g in b.groupby(pd.qcut(b.conf, 3, labels=["lo", "mid", "hi"], duplicates="drop"))) if len(b) > 10 else "")
    bull5 = b.l5.to_numpy(float)
    bull5 = bull5[np.isfinite(bull5)]
    bear5 = br.l5.to_numpy(float)
    bear5 = bear5[np.isfinite(bear5)]
    stale = res[("BULL", False)].l5.to_numpy(float)
    stale = stale[np.isfinite(stale)]
    spread = bull5.mean() - bear5.mean() if len(bear5) else float("nan")
    t_spread = spread / np.sqrt(bull5.var() / max(len(bull5), 1) + bear5.var() / max(len(bear5), 1)) if len(bear5) > 2 else float("nan")
    net5 = bull5 - 10
    ok = dict(mean=net5.mean() >= 30 if len(net5) else False, t=clus_t(net5, b.date.to_numpy()[np.isfinite(b.l5)]) >= 2 if len(net5) > 2 else False,
              median=np.median(net5) > 0 if len(net5) else False,
              h1=b[b.date < "2021-01-01"].l5.mean() - 10 > 0 if (b.date < "2021-01-01").any() else False,
              h2=b[b.date >= "2021-01-01"].l5.mean() - 10 > 0 if (b.date >= "2021-01-01").any() else False,
              extop5=((net5.sum() - np.sort(net5)[-5:].sum()) / max(len(net5) - 5, 1) > 0) if len(net5) > 5 else False,
              spread=spread >= 40 and t_spread >= 2, stale=(bull5.mean() - stale.mean()) >= 20 if len(stale) else False)
    log(f"\nBULL - BEAR L5 spread {spread:+.1f}bp (t {t_spread:.2f}); BULL right-edge minus stale {bull5.mean() - stale.mean() if len(stale) else float('nan'):+.1f}; "
        f"L2 auction trade BULL {b.l2.mean():+.1f} (bar +10)")
    log(f"GATES {ok} -> {'PASS' if all(ok.values()) else 'KILL'}")
    log("Disclosed: charts rendered by matplotlib in the model's training style (not screen captures); conf 0.25 as published; one "
        "chart x side counted once (highest-conf box); labels are Sharadar daily bars (opens = daily open, not the cross print).")


def shard() -> None:
    """detect on picks[i::n] -> detections_i.parquet (parallel workers; `run` merges)."""
    i, n = int(sys.argv[2]), int(sys.argv[3])
    st = universe()
    picks = sample(st, N_SAMPLE).iloc[i::n].reset_index(drop=True)
    det = detect(st, picks, load_model(), D / f"images_{i}")
    det.to_parquet(D / f"detections_{i}.parquet")
    print(f"shard {i}/{n}: {len(picks)} charts, {len(det)} rows", flush=True)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"probe": probe, "run": run, "shard": shard}[cmd]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
