"""U5: fire-sale decile, 2-4 quarter holds (the untested holding-period field of F-SALE2 N 1060).

Pre-registration: docs/research/hypothesis-space.md U5 (Tier B: +3-4pp as a Roth
sleeve, below the +8pp gate). Data: data/research/fsale2/pressure_*.parquet,
the same CRSP-MF flow panel F-SALE2 built. Signal = quarter q's pressure, known
after q's close; entry = close q; hold h = 2, 3, 4 quarters. Judge the bottom
decile (most fire-sold) vs the quarter's EW eligible universe.

Kill: next-4-quarter excess <= 0, or carried by < 5 names/quarters.
    PYTHONPATH=. .venv/bin/python -m research.sim.u5_firesale_hold
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import f_sale as F
from .f_sale2 import build

ROOT = pathlib.Path(__file__).resolve().parents[2]
SH = pathlib.Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/u5_firesale_hold_out.txt"
HORIZONS = (1, 2, 3, 4)


def quarter_prices(tickers: list[str]) -> pd.DataFrame:
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "closeadj"],
                         filters=[("ticker", "in", sorted(set(tickers)))])
    st["date"] = pd.to_datetime(st.date)
    st["q"] = st.date.dt.to_period("Q")
    return st.sort_values("date").groupby(["ticker", "q"]).closeadj.last().unstack("q")


def nw_t(x: pd.Series, lag: int) -> float:
    x = x.dropna().to_numpy(float)
    n = len(x)
    if n <= lag + 2:
        return float("nan")
    e = x - x.mean()
    s = (e * e).sum() / n
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * (e[k:] * e[:-k]).sum() / n
    return float(x.mean() / np.sqrt(s / n))


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fh = open(OUT, "w")

    def log(*a):
        s = " ".join(str(i) for i in a)
        print(s, flush=True); fh.write(s + "\n"); fh.flush()

    pr = build()
    pr["q"] = pd.PeriodIndex(pr.q, freq="Q")
    pr["advusd"] = pr.advsh * pr.pxu
    el = pr[(pr.pxu >= 5) & (pr.advusd >= 1e7) & ((pr.sell_p > 0) | (pr.buy_p > 0))].copy()
    el = el.dropna(subset=["ret_next"])
    el["dec"] = el.groupby("q").pressure.transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    P = quarter_prices(el.ticker.unique().tolist())
    log(f"U5 FIRE-SALE-HOLD (N 1068): {len(el):,} eligible stock-quarters, {el.q.nunique()} quarters "
        f"{el.q.min()}..{el.q.max()}; prices {P.shape[1]} quarters")

    qs = sorted(el.q.unique())
    univ = {q: el[el.q == q] for q in qs}
    rows = []
    for q in qs:
        if q not in P.columns:
            continue
        px_q = P[q]
        for h in HORIZONS:
            fq = q + h
            if fq not in P.columns:
                continue
            fwd = (P[fq] / px_q - 1).rename("fwd")
            g = univ[q].merge(fwd, left_on="ticker", right_index=True, how="inner")
            if len(g) < 50:
                continue
            ew = g.fwd.mean()
            d1 = g[g.dec == 0]
            d10 = g[g.dec == 9]
            rows.append(dict(q=q, h=h, ew=ew, d1=d1.fwd.mean(), d10=d10.fwd.mean(), n=len(g),
                             n1=len(d1), med1=d1.fwd.median(), x=d1.fwd.mean() - ew,
                             x10=d10.fwd.mean() - ew, press_ret_q=d1.ret_q.mean() - g.ret_q.mean()))
    R = pd.DataFrame(rows)
    log("\ncalendar-time bottom-decile (D1 = most fire-sold) forward excess vs EW, by horizon:")
    for h in HORIZONS:
        s = R[R.h == h].set_index("q")
        if s.empty:
            continue
        x = s.x * 1e4
        ann = x.mean() * 4
        top = np.sort(x.values)[-5:].sum()
        ex5 = (x.sum() - top) / (len(x) - 5) if len(x) > 5 else np.nan
        h1 = x[s.index.year <= 2017]; h2 = x[s.index.year >= 2018]
        log(f"  h={h}q: quarters {len(x)} ann {ann:+.1f}%/yr mean {x.mean():+.0f}bp med {x.median():+.0f} "
            f"hit {(x > 0).mean():.2f} t {F.clus_t(x):.2f} NW t {nw_t(x, h):+.2f} ex-top5 {ex5:+.0f} | "
            f"2009-17 {h1.mean():+.0f} (t {F.clus_t(h1):+.2f}) 2018-26 {h2.mean():+.0f} (t {F.clus_t(h2):+.2f})")
        log(f"        median stock excess {s.med1.sub(s.ew).mul(1e4).mean():+.0f}bp; "
            f"avg names/quarter {s.n1.mean():.0f}; event-quarter D1 excess {s.press_ret_q.mul(1e4).mean():+.0f}bp")
    log("\nD10 (inflow-bought) forward excess:")
    for h in HORIZONS:
        s = R[R.h == h].set_index("q")
        if not s.empty:
            log(f"  h={h}q: mean {(s.x10 * 1e4).mean():+.0f}bp t {F.clus_t(s.x10 * 1e4):+.2f}")

    s4 = R[R.h == 4].set_index("q")
    x4 = s4.x * 1e4
    ok = dict(excess=x4.mean() > 0, t=abs(nw_t(x4, 4)) >= 2, median=x4.median() > 0,
              halves=(x4[s4.index.year <= 2017].mean() > 0) and (x4[s4.index.year >= 2018].mean() > 0),
              ex_top5=((x4.sum() - np.sort(x4.values)[-5:].sum()) / (len(x4) - 5) > 0),
              mechanism=s4.press_ret_q.mean() < 0)
    log(f"\nGATES h=4q {ok} -> {'PASS' if all(ok.values()) else 'KILL'}")
    log("Disclosed: overlapping quarterly cohorts (NW lag 4); close-to-close quarterly prices; no delisting return; "
        "same eligibility screen as F-SALE2; bottom decile equal-weight.")
    fh.close()


if __name__ == "__main__":
    main()
