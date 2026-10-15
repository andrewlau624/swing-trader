"""RESURRECTION RES-1 / Study TL-JAN (N 853 -> 854): tax-loss selling -> January reversal.

Delisted-complete Sharadar panel (research/sim/lh_panel.py), formation years 1998-2025 = 28 events.
Design frozen in round1_prose.md (amendment TL-JAN) from seasonal_memo_2026-10-04.md B.5: common stocks,
raw close >= $3 and 20d $ADV >= $1M at formation; YTD <= -30%; December daily mean $vol >= 1.0x the
Jun-Nov daily mean; worst 50 by YTD; buy the close of the 5th-last December session, sell the close of the
10th January session; equal weight; benchmark IWM (same window, SFP). Costs 25bp/side floor + 2x shock.
June placebo with the matched calendar (formation 7th-last June session, exit 10th July session).

    PYTHONPATH=. .venv/bin/python -m research.sim.tl_jan
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .lh_panel import Panel

OUT = pathlib.Path(__file__).resolve().parent / "tl_jan_out.txt"
lines: list[str] = []


def log(s: str) -> None:
    lines.append(s)
    print(s)


def _m(dates: np.ndarray, y: int, m: int) -> int:
    """First date index >= month m of year y (m=12 rolls into January of y+1)."""
    y2, m2 = (y, m) if m <= 12 else (y + 1, m - 12)
    return int(np.searchsorted(dates, np.datetime64(f"{y2}-{m2:02d}-01")))


def _frame(P: Panel, di_lo: int, di_hi: int, stocks_only: bool = True) -> pd.DataFrame:
    mask = (P.di >= di_lo) & (P.di < di_hi) & (P.src == 0 if stocks_only else True)
    rows = np.flatnonzero(mask)
    return pd.DataFrame({"tid": P.tid[rows], "di": P.di[rows], "tr": P.tr[rows], "cu": P.cu[rows],
                         "usd": P.cu[rows] * P.v[rows]}).set_index("tid")


def _snapshot(f: pd.DataFrame, di: int) -> pd.DataFrame:
    x = f[f.di == di]
    return x.groupby(level=0).agg(tr=("tr", "first"), px=("cu", "first"))


def _picks(f: pd.DataFrame, base: int, form: int, dec_lo: int, dec_hi: int, PRIOR: tuple[int, int],
           min_ytd: float, n: int) -> pd.DataFrame:
    """20d $ADV filter ranked picks at formation, with the footprint ratio."""
    f1 = f[f.di <= form]
    adv = f1.groupby(level=0)["usd"].tail(20).groupby(level=0).mean()
    dec_m = f[(f.di >= dec_lo) & (f.di <= dec_hi)].groupby(level=0)["usd"].mean()
    prio_m = f[(f.di >= PRIOR[0]) & (f.di < PRIOR[1])].groupby(level=0)["usd"].mean()
    snap = _snapshot(f, base)
    sf = _snapshot(f, form)
    have = snap.index.to_numpy()
    d = pd.DataFrame({"ytd": sf.tr.reindex(have) / snap.tr.reindex(have) - 1.0,
                      "adv": adv.reindex(have).to_numpy(),
                      "px": sf.px.reindex(have).to_numpy(),
                      "dec": dec_m.reindex(have).to_numpy() / prio_m.reindex(have).to_numpy()})
    d = d[(d.px >= 3) & (d.adv >= 1e6)]
    return d[(d.ytd <= min_ytd) & (d.dec >= 1.0)].nsmallest(n, "ytd")


def _trade(P: Panel, tidv: int, entry: int, exit_: int) -> tuple[float, bool, float] | None:
    t = str(P.tickers[tidv])
    s = P.rows(t)
    k_e = int(np.searchsorted(P.di[s], entry))
    if k_e >= s.stop - s.start or P.di[s][k_e] != entry:
        return None
    k_x = int(np.searchsorted(P.di[s], exit_, side="right") - 1)
    k_x = max(k_x, k_e)
    trunc = k_x >= s.stop - s.start - 1
    k_x = min(k_x, s.stop - s.start - 1)
    raw = P.tr[s.start + k_x] / P.tr[s.start + k_e] - 1
    return raw, trunc, float(P.cu[s.start + k_e])


def _bench(iw: pd.Series, dates: np.ndarray, d0: int, d1: int) -> float:
    ben = iw.reindex([pd.Timestamp(dates[d0]), pd.Timestamp(dates[d1])])
    return float(ben.iloc[1] / ben.iloc[0] - 1) if ben.notna().all() else float("nan")


def main() -> None:
    P = Panel.load()
    dates = P.dates
    iw = P.series("IWM").set_index("date")["tr"]
    evs: list[dict] = []
    DIMS = 50
    for y in range(1998, 2026):
        dec0, dec1 = _m(dates, y, 12), _m(dates, y, 13)
        j0, j1 = _m(dates, y + 1, 1), _m(dates, y + 1, 2)
        if dec1 - dec0 < 15:
            continue
        base = dec0 - 1                # prior-year end (last Nov session)
        form, entry = dec1 - 7, dec1 - 5
        exit_ = j0 + 9                 # 10th January session
        if exit_ >= j1:
            exit_ = j1 - 1
        if base >= dec0 or exit_ <= entry:
            continue
        PRIOR = (_m(dates, y, 6), dec1)
        f = _frame(P, PRIOR[0], j1)
        picks = _picks(f, base, form, dec0, form, PRIOR, -0.30, DIMS)
        b = _bench(iw, dates, entry, exit_)
        for tidv in picks.index.to_numpy():
            r = _trade(P, tidv, entry, exit_)
            if r is None:
                continue
            raw, trunc, px = r
            evs.append(dict(year=y, ytd=float(picks.loc[tidv, "ytd"]), raw=raw, bret=b,
                            trunc=trunc, px=px, adv=float(picks.loc[tidv, "adv"])))
        log(f"{y}: picked {len(picks)} (med ytd {picks.ytd.median():.2f}, med px ${picks.px.median():.1f}, "
            f"med adv ${(picks.adv.median()/1e6 if len(picks) else 0):.1f}M)" if len(picks) else f"{y}: no picks")
    E = pd.DataFrame(evs)
    if E.empty:
        log("no events")
        OUT.write_text("\n".join(lines) + "\n")
        return
    E["net"] = E.raw - E.bret - 0.005
    E["net2"] = E.raw - E.bret - 0.01
    for col, lab in (("net", "cost 25bp/side"), ("net2", "cost 2x 50bp/side")):
        yv = E.groupby("year")[col].mean().dropna()
        se = yv.std(ddof=1) / np.sqrt(len(yv)) if len(yv) > 2 else float("nan")
        srt = np.sort(yv.to_numpy())
        log(f"[{lab}] years {int(yv.index.min())}-{int(yv.index.max())} n {len(yv)}, fills {len(E)}, "
            f"trunc {E.trunc.mean()*100:.0f}%")
        log(f"  mean/yr {yv.mean()*100:+.2f}% t(yr) {yv.mean()/se if se==se else 0:.2f} "
            f"median-yr {np.median(yv)*100:+.2f}%  years+ {(yv>0).mean()*100:.0f}%  "
            f"ex-best-yr {srt[:-1].mean()*100:+.2f}%  worst-yr {srt[0]*100:+.1f}%")
    yv = E.groupby("year")["net"].mean().dropna()
    for lo, hi in ((1998, 2016), (2016, 2026)):
        sl = yv[(yv.index >= lo) & (yv.index < hi)]
        se = sl.std(ddof=1) / np.sqrt(len(sl)) if len(sl) > 2 else float("nan")
        log(f"  {lo}-{hi-1}: n {len(sl)} mean {sl.mean()*100:+.2f}% t {sl.mean()/se if se==se else 0:.2f} "
            f"years+ {(sl>0).mean()*100:.0f}%")
    log(f"  years: { {int(k): round(v*100, 1) for k, v in yv.items()} }")
    # monotone in YTD loss (pooled within-year terciles of the picks)
    E["tc"] = E.groupby("year")["ytd"].transform(lambda z: pd.qcut(z.rank(ascending=False), q=3, labels=False))
    btc = E.groupby("tc").apply(lambda g: g.raw.mean() - g.bret.mean(), include_groups=False)
    log(f"  YTD-loss tercile mean return (gross, in tercile order worst->least): "
        f"{ [round(x*100, 2) for x in btc] }")
    # June placebo: formation = 7th-last June session, entry 5th-last, exit = 10th July session
    pl = []
    for y in range(1998, 2026):
        jun0, jul0, aug0 = _m(dates, y, 6), _m(dates, y, 7), _m(dates, y, 8)
        if jul0 - jun0 < 15:
            continue
        base_p = jun0 - 1
        form_p, entry_p = jul0 - 7, jul0 - 5
        exit_p = aug0 + 9
        if exit_p >= aug0:
            exit_p = aug0 - 1
        PRIOR = (_m(dates, y, 1), jun0)
        f = _frame(P, PRIOR[0], aug0)
        picks = _picks(f, base_p, form_p, jun0, form_p, PRIOR, -0.30, DIMS)
        b = _bench(iw, dates, entry_p, exit_p)
        for tidv in picks.index.to_numpy():
            r = _trade(P, tidv, entry_p, exit_p)
            if r is None:
                continue
            pl.append(dict(year=y, raw=r[0], bret=b, trunc=r[1]))
    PL = pd.DataFrame(pl)
    ply = (PL.raw - PL.bret - 0.005).groupby(PL.year).mean().dropna()
    se = ply.std(ddof=1) / np.sqrt(len(ply)) if len(ply) > 2 else float("nan")
    log(f"  [placebo June]: n years {len(ply)}, fills {len(PL)}, mean/yr {ply.mean()*100:+.2f}% "
        f"t {ply.mean()/se if se==se else 0:.2f} years+ {(ply>0).mean()*100:.0f}% "
        f"median-yr {np.median(ply)*100:+.2f}%")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
