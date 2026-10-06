"""Long-history panel helpers for the overnight golden-egg loop (2026-10-06).

Compact cache of every Sharadar SEP (stocks) + SFP (funds) daily bar, 1997-12-31+, delisted
included, so event studies can run over ~28 years without re-reading 1.3GB of parquet.

Prices: open/high/low/close are split-adjusted (as stored); `fac` = closeadj/close is the
dividend factor, so total return between two bars = (px_b * fac_b) / (px_a * fac_a).
Raw (unadjusted) close = closeunadj. Bars end at the last trade: a delisted name's horizon
return is truncated to its last bar (no delisting return exists in the source).

  from lh_panel import Panel; P = Panel.load()
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

STORE = pathlib.Path.home() / "data" / "sharadar"
CACHE = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "lh_panel.npz"


def _build() -> None:
    frames = []
    for name in ("stocks", "funds"):
        t = pd.read_parquet(STORE / f"{name}.parquet",
                            columns=["ticker", "date", "open", "high", "low", "close", "closeadj",
                                     "closeunadj", "volume"])
        t["src"] = 0 if name == "stocks" else 1
        frames.append(t)
    b = pd.concat(frames, ignore_index=True)
    b = b.drop_duplicates(["ticker", "date"], keep="first")
    b["date"] = pd.to_datetime(b["date"])
    b = b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    tick = b["ticker"].astype("category")
    dates = np.sort(b["date"].unique())
    di = np.searchsorted(dates, b["date"].to_numpy())
    fac = (b["closeadj"] / b["close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, tickers=np.array(tick.cat.categories, dtype=object), tid=tick.cat.codes.to_numpy(np.int32),
             dates=dates, di=di.astype(np.int32),
             o=b["open"].to_numpy(np.float32), h=b["high"].to_numpy(np.float32),
             l=b["low"].to_numpy(np.float32), c=b["close"].to_numpy(np.float32),
             fac=fac.to_numpy(np.float32), cu=b["closeunadj"].to_numpy(np.float32),
             v=b["volume"].to_numpy(np.float32), src=b["src"].to_numpy(np.int8))


class Panel:
    """Long-format arrays sorted by (ticker, date). start[t]..end[t] is ticker t's row block."""

    @classmethod
    def load(cls) -> "Panel":
        if not CACHE.exists():
            _build()
        z = np.load(CACHE, allow_pickle=True)
        p = cls()
        for k in z.files:
            setattr(p, k, z[k])
        p.tix = {t: i for i, t in enumerate(p.tickers)}
        bounds = np.flatnonzero(np.diff(p.tid)) + 1
        p.start = np.r_[0, bounds]
        p.end = np.r_[bounds, len(p.tid)]
        p.tr = p.c.astype(np.float64) * p.fac  # total-return price level (close)
        p.tro = p.o.astype(np.float64) * p.fac  # total-return price level (open)
        return p

    def rows(self, ticker: str) -> slice:
        i = self.tix.get(ticker)
        return slice(0, 0) if i is None else slice(self.start[i], self.end[i])

    def series(self, ticker: str) -> pd.DataFrame:
        s = self.rows(ticker)
        return pd.DataFrame({"date": self.dates[self.di[s]], "o": self.o[s], "c": self.c[s], "tr": self.tr[s],
                             "tro": self.tro[s], "cu": self.cu[s], "v": self.v[s]})

    def row_at(self, ticker: str, date, side: str = "left") -> int:
        """Global row of the first bar on/after `date` (side='left') for ticker; -1 if none."""
        s = self.rows(ticker)
        if s.stop == s.start:
            return -1
        d = np.searchsorted(self.dates, np.datetime64(pd.Timestamp(date)))
        k = np.searchsorted(self.di[s], d, side=side)
        return -1 if k >= s.stop - s.start else s.start + k


def cluster_t(x, g) -> tuple[float, float]:
    """Mean and t clustered on g (e.g. event month)."""
    df = pd.DataFrame({"x": np.asarray(x, float), "g": np.asarray(g)}).dropna()
    n = len(df)
    if n < 3:
        return (df.x.mean() if n else np.nan), 0.0
    m = df.x.mean()
    s = (df.x - m).groupby(df.g).sum().to_numpy()
    G = len(s)
    se = np.sqrt((G / max(G - 1, 1)) * (s ** 2).sum() / n ** 2)
    return m, (m / se if se > 0 else 0.0)


def event_returns(P: Panel, ev: pd.DataFrame, horizons=(5, 20, 60, 120, 250), entry: str = "close",
                  bench: str = "SPY", lag: int = 0) -> pd.DataFrame:
    """ev: columns ticker, date (event day D). Entry at close of D+lag (entry='close') or open of D+1+lag
    ('open'). Returns total-return raw and bench-abnormal to the close h sessions after the entry bar
    (truncated at the name's last bar; `trunc` flags it)."""
    b = P.series(bench).set_index("date")["tr"]
    out = []
    for r in ev.itertuples(index=False):
        g = P.row_at(r.ticker, r.date)
        if g < 0:
            continue
        s = P.rows(r.ticker)
        e = g + lag + (1 if entry == "open" else 0)
        if e >= s.stop:
            continue
        p0 = P.tro[e] if entry == "open" else P.tr[e]
        d0 = P.dates[P.di[e]]
        rec = {"ticker": r.ticker, "date": pd.Timestamp(r.date), "d0": d0, "px0": float(P.cu[e]),
               "dv0": float(P.c[e] * P.v[e])}
        if entry == "open":
            d0b = b.index[b.index.searchsorted(d0) - 1] if b.index.searchsorted(d0) > 0 else d0
            b0 = b.get(d0b, np.nan)  # bench close before the open entry (approximation)
        else:
            b0 = b.get(d0, np.nan)
        for h in horizons:
            k = min(e + h, s.stop - 1)
            dk = P.dates[P.di[k]]
            raw = P.tr[k] / p0 - 1 if p0 > 0 else np.nan
            bk = b.asof(dk)
            rec[f"r{h}"] = raw
            rec[f"a{h}"] = raw - (bk / b0 - 1)
            rec[f"t{h}"] = (e + h) >= s.stop
        out.append(rec)
    return pd.DataFrame(out)


def summarize(df: pd.DataFrame, h: int, cost: float = 0.0, label: str = "") -> str:
    a = df[f"a{h}"] - 2 * cost
    m, t = cluster_t(a, df["date"].dt.to_period("M"))
    srt = np.sort(a.dropna().to_numpy())
    ex5 = srt[:-5].mean() if len(srt) > 10 else np.nan
    return (f"{label} h{h} n={a.notna().sum()} abn mean {m*100:+.2f}% t {t:.2f} med {np.nanmedian(a)*100:+.2f}% "
            f"hit {(a > 0).mean()*100:.0f}% ex-top5 {ex5*100:+.2f}% raw {df[f'r{h}'].mean()*100:+.2f}% "
            f"trunc {df[f't{h}'].mean()*100:.0f}%")
