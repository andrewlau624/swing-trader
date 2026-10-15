"""Study PAIR-CLASS (N 857 -> 858): same-issuer dual-class differential, long-only, 20d z <= -2, 3-session exit.

Panel and rule frozen in round1_prose.md. Panel printed before any signal; no pair added after results.

    PYTHONPATH=. .venv/bin/python -m research.sim.pair_class
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .lh_panel import Panel

OUT = pathlib.Path(__file__).resolve().parent / "pair_class_out.txt"
lines: list[str] = []


def log(s: str) -> None:
    lines.append(s)
    print(s)


def main() -> None:
    P = Panel.load()
    spy = P.series("SPY").set_index("date")["tr"]
    t = pd.read_parquet("/Users/andrewlau/data/sharadar/tickers.parquet")
    t = t[t.table == "SEP"]
    t = t[t.category.str.match("Domestic Common Stock (Primary|Secondary) Class$", na=False)].copy()
    t["k"] = t.name.str.replace(r"[^A-Za-z0-9 ]", "", regex=True).str.strip().str.lower()
    m = (t[t.category.str.contains("Primary")][["ticker", "k"]]
         .merge(t[t.category.str.contains("Secondary")][["ticker", "k"]], on="k", suffixes=("_a", "_b"))
         .drop_duplicates(["ticker_a", "ticker_b"]))
    kept = []
    log("== PANEL (frozen: same-name primary/secondary common pairs, listed, >=300 joint days) ==")
    for r in m.itertuples(index=False):
        a, b = P.series(r.ticker_a), P.series(r.ticker_b)
        d = a.merge(b[["date", "cu", "v"]], on="date", suffixes=("", "_b"))
        if len(d) < 300:
            continue
        d = d[["date", "cu", "v", "cu_b", "v_b"]]
        va, vb = (d.cu * d.v).rolling(20).median(), (d.cu_b * d.v_b).rolling(20).median()
        if va.median() < 20e6 or vb.median() < 20e6:
            log(f"  drop-thin {r.ticker_a}/{r.ticker_b}")
            continue
        log(f"pair {r.ticker_a}/{r.ticker_b}: {len(d)} joint days {d.date.min().date()}-{d.date.max().date()} "
            f"(20d med $vol {va.median()/1e6:.0f}/{vb.median()/1e6:.0f} M)")
        kept.append((r.ticker_a, r.ticker_b, d))

    def run(col_signal_shift: int = 0, tag: str = "LIVE") -> pd.DataFrame:
        tr = []
        for a, b, d in kept:
            S = np.log(d.cu.to_numpy() / d.cu_b.to_numpy())
            ser = pd.Series(S)
            mu, sd = ser.rolling(20).mean(), ser.rolling(20).std()
            z = ((ser - mu.shift(col_signal_shift)) / sd.shift(col_signal_shift))
            sig = (z <= -2).to_numpy()
            n = len(d)
            i = 0
            while i < n - 3:
                if not sig[i]:
                    i += 1
                    continue
                i0 = i + col_signal_shift
                if i0 + 3 >= n:
                    break
                px0 = d.cu[i0]
                rraw = d.cu[i0 + 3] / px0 - 1
                da, db_ = d.date[i0], d.date[i0 + 3]
                s = spy.reindex([da, db_])
                rs = float(s.iloc[1] / s.iloc[0] - 1) if s.notna().all() else np.nan
                tr.append(dict(pair=a, d=str(da.date()), abn=rraw - rs))
                i += 4  # non-overlapping entries
        return pd.DataFrame(tr)

    E = run()
    PC = run(col_signal_shift=30)
    log(f"\n== SIGNAL EVENTS: {len(E)} fills over {len(E.pair.unique()) if len(E) else 0} pairs ==")
    for co, lab in ((0.0025, "25bp round"), (0.005, "50bp round")):
        y = E.assign(net=E.abn - co, yr=E.d.str[:4]).groupby("yr")["net"].mean().rename("net").to_frame()
        if not len(y):
            continue
        se = y.net.std(ddof=1) / np.sqrt(len(y)) if len(y) > 2 else np.nan
        log(f"[{lab}] years {len(y)}: mean {y.net.mean()*100:+.2f}% t {y.net.mean()/se if se==se else 0:.2f} "
            f"years+ {(y.net>0).mean()*100:.0f}% best {y.net.max()*100:+.1f} worst {y.net.min()*100:+.1f}")
    y = PC.assign(net=PC.abn - 0.0025, yr=PC.d.str[:4]).groupby("yr")["net"].mean().rename("net").to_frame()
    se = y.net.std(ddof=1) / np.sqrt(len(y)) if len(y) > 2 else np.nan
    log(f"[placebo shifted-30] years {len(y)}: mean {y.net.mean()*100:+.2f}% t {y.net.mean()/se if se==se else 0:.2f} "
        f"years+ {(y.net>0).mean()*100:.0f}%")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
