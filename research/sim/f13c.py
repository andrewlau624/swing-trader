"""Study F13F-CAP (N 854 -> 856): forced trim of concentrated fund holdings after a share-count shrink.

Design frozen in round1_prose.md (two judged arms). No variant tuning after the first return line.

    PYTHONPATH=. .venv/bin/python -m research.sim.f13c
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .lh_panel import Panel

OUT = pathlib.Path(__file__).resolve().parent / "f13c_out.txt"
lines: list[str] = []


def log(s: str) -> None:
    lines.append(s)
    print(s)


DEADLINE = {3: "05-15", 6: "08-14", 9: "11-14", 12: "02-15"}
NEXTYR = {3: 0, 6: 0, 9: 0, 12: 1}
PREV_Q = {3: (1, 12, 31), 6: (0, 3, 31), 9: (0, 6, 30), 12: (0, 9, 30)}   # (years_back, month, day)
DL_Y = {3: 0, 6: 0, 9: 0, 12: 1}
HOLD = 63


def _after(dates: np.ndarray, ds: str) -> int:
    k = int(np.searchsorted(dates, np.datetime64(ds)))
    kk = k + 1 if k < len(dates) and pd.Timestamp(dates[k]).strftime("%Y-%m-%d") == ds else k
    return min(kk, len(dates) - 1)   # first session strictly after the deadline date


def _q_prev(q: str) -> str:
    mm = int(q[5:7])
    yy, mm2, dd = PREV_Q[mm]
    return f"{int(q[:4]) - yy}-{mm2:02d}-{dd:02d}"


def _deadline(q: str) -> str:
    mm = int(q[5:7])
    y = int(q[:4]) + DL_Y[mm]
    return f"{y}-{DEADLINE[mm]}"


def _trade(P: Panel, ticker: str, j: int, hold: int = HOLD):
    rows = P.rows(ticker)
    s = rows.start
    n = np.searchsorted(P.di[s:rows.stop], j, side="left")
    if n >= rows.stop - s or P.di[s:rows.stop][n] != j:
        return None
    n_stop = rows.stop - s - 1
    k = min(n + hold, n_stop)
    trunc = (n + hold) > (rows.stop - s - 1)
    raw = float(P.tr[s + k] / P.tr[s + n] - 1)
    return raw, trunc, float(P.cu[s + n])


def arm(P: Panel, spy: pd.Series, dates: np.ndarray, ev: pd.DataFrame, flip: int, cost_side: float,
        hold: int = HOLD) -> pd.DataFrame:
    out = []
    for r in ev.itertuples(index=False):
        j = _after(dates, _deadline(r.date))
        d0 = pd.Timestamp(dates[j])
        t = _trade(P, str(r.ticker), j)
        if t is None:
            continue
        raw, trunc, px = t
        if px < 3.0:
            continue
        dx = pd.Timestamp(dates[min(j + hold, len(dates) - 1)])
        sp = spy.reindex([d0, dx])
        b = float(sp.iloc[1] / sp.iloc[0] - 1) if sp.notna().all() else np.nan
        out.append({"ticker": str(r.ticker), "d": str(r.date), "entry": d0, "dx": dx,
                    "raw": raw, "bret": b, "trunc": trunc, "px": px})
    D = pd.DataFrame(out)
    if not D.empty:
        for c in ("net", "net2"):
            D[c] = flip * (D.raw - D.bret) - (cost_side * (1 if c == "net" else 2)) * 2
    return D


def stats(D: pd.DataFrame, tag: str) -> None:
    if D.empty:
        log(f"{tag}: no events")
        return
    log(f"== {tag} == events {len(D)}, names {D.ticker.nunique()}")
    for col in ("net", "net2"):
        yv = D.groupby("entry")[col].mean().dropna()
        m = yv.mean()
        se = yv.std(ddof=1) / np.sqrt(len(yv)) if len(yv) > 2 else np.nan
        srt = np.sort(yv.to_numpy())
        log(f"  [{col}] days {len(yv)}: mean/day {m*100:+.2f}%  t {m/se if se==se else 0:.2f}  "
            f"med-day {np.nanmedian(yv)*100:+.2f}%  days+ {(yv>0).mean()*100:.0f}%  ex-top5 {srt[:-5].mean()*100:+.2f}%")
    g = D.groupby("entry")["net"].mean()
    log(f"  halves: {g[g.index < '2020-01-01'].mean()*100:+.2f}% / {g[g.index >= '2020-01-01'].mean()*100:+.2f}%")
    nmean = D.groupby("ticker")["net"].mean().sort_values()
    keep = nmean.index[:-5]
    dd = D[D.ticker.isin(keep)]
    log(f"  name-level med {nmean.median()*100:+.2f}%  ex-top5-names {dd.net.mean()*100:+.2f}%  "
        f"trunc {D.trunc.mean()*100:.0f}%  med px ${D.px.median():.1f}")


def main() -> None:
    P = Panel.load()
    dates = P.dates
    spy = P.series("SPY").set_index("date")["tr"]
    A = pd.read_parquet("data/research/f13f/agg.parquet")
    A["date"] = pd.to_datetime(A["date"]).dt.strftime("%Y-%m-%d")
    A = A.sort_values(["ticker", "date"])
    A["dsh"] = A.groupby("ticker")["sh6"].pct_change(fill_method=None)
    press = A[(A.mxp >= 0.095) & (A.dsh <= -0.05)][["ticker", "date"]]
    plc = A[(A.mxp < 0.05) & (A.dsh <= -0.05)][["ticker", "date"]]
    press2 = A[(A.mfpx >= 0.095) & (A.dsh <= -0.05)][["ticker", "date"]]
    prev_pdata = press.copy()
    prev_pdata["date"] = prev_pdata["date"].map(_q_prev)
    low = A[A.mxp <= 0.07]
    freed = prev_pdata.merge(low, on=["ticker", "date"])[["ticker", "date"]]
    log(f"press events {len(press)} ({press.ticker.nunique()} names), freed {len(freed)}, "
        f"placebo {len(plc)} ({plc.ticker.nunique()} names); press2 {len(press2)}")
    stats(arm(P, spy, dates, plc, +1, 0.005), "PLACEBO (long)")
    stats(arm(P, spy, dates, press, -1, 0.005), "F13C-TRIM (short, 50bp/side; unborrow excluded)")
    stats(arm(P, spy, dates, freed, +1, 0.005), "F13C-FREED (long, 50bp/side)")
    stats(arm(P, spy, dates, press2, -1, 0.005), "F13C-TRIM2 (short, participant-typed)")
    prev2 = press2.copy(); prev2["date"] = prev2["date"].map(_q_prev)
    freed2 = prev2.merge(low, on=["ticker", "date"])[["ticker", "date"]]
    stats(arm(P, spy, dates, freed2, +1, 0.005), "F13C-FREED2 (long, participant-typed)")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
