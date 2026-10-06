"""Study SPLIT-NIGHT: post-split retail open pressure, nights T+0..T+4, judged on official SIP crosses 2021-2026.

Pre-registration: "Amendment — Study SPLIT-NIGHT" in research/drafts/round1_prose.md (program N 846 -> 847).
Rule: each night hold (closing cross D -> opening cross D+1) every common stock within nights T+0..T+4 of a
forward-split ex-date E (raw close(E-1) >= $5, $vol(E-1) >= $1M). P&L per name-night minus SPY official overnight.
Also reported (not judged): the T+0 night alone on common stocks (the EXDIV-OPEN arm B rule without funds).

    PYTHONPATH=. .venv/bin/python -m research.sim.split_night
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from exdiv_open import crosses, overnight  # noqa: E402
from lh_panel import Panel, cluster_t  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/exdiv"
OUT = pathlib.Path(__file__).resolve().parent / "split_night_out.txt"
STORE = pathlib.Path.home() / "data" / "sharadar"


def main(folder: str = "splitnight", spy_file: str = "spy.json", out: pathlib.Path = OUT,
         split_year: int = 2023) -> None:
    lines: list[str] = []

    def log(s=""):
        print(s)
        lines.append(s)

    P = Panel.load()
    spy_on = overnight(crosses(json.load(open(D / spy_file))["SPY"]))
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a["date"] = pd.to_datetime(a["date"])
    sp = a[(a.action == "split") & (a.value > 1)].drop_duplicates(["ticker", "date"])
    rows = []
    for f in sorted(glob.glob(str(D / folder / "*.json"))):
        t, d = pathlib.Path(f).stem.rsplit("_", 1)
        d = pd.Timestamp(d)
        v = json.load(open(f))
        if t not in v:
            continue
        g = P.row_at(t, d)
        if g < 1 or P.dates[P.di[g]] != np.datetime64(d) or P.src[g] != 0:
            continue  # stocks table only (common stock rule)
        if P.cu[g - 1] < 5 or P.c[g - 1] * P.v[g - 1] < 1e6:
            continue
        x = crosses(v[t])
        if d not in x.index:
            continue
        k = x.index.get_loc(d)
        ratio = float(sp[(sp.ticker == t) & (sp.date == d)].value.iloc[0])
        later = sp[(sp.ticker == t) & (sp.date > d)].date
        on = overnight(x)
        on.iloc[k] = x.op.iloc[k] * ratio / x.cp.iloc[k - 1] - 1
        if abs(on.iloc[k]) > 1.0:  # vendor split date/ratio disagrees with the tape (BRIA, MBC): data error, dropped
            continue
        for off in range(5):
            if k + off >= len(x) or (len(later) and x.index[k + off] >= later.min()):
                break
            rows.append(dict(ticker=t, E=d, off=off, d=x.index[k + off], pnl=on.iloc[k + off],
                             ocs=x.os.iloc[k + off] * x.op.iloc[k + off], ccs=x.cs.iloc[k + off - 1] * x.cp.iloc[k + off - 1]))
    X = pd.DataFrame(rows).dropna(subset=["pnl"])
    X["x"] = X.pnl - spy_on.reindex(X.d).to_numpy()
    X = X.dropna(subset=["x"])
    g = X.d.dt.strftime("%Y-%m-%d")
    m, t = cluster_t(X.x, g)
    srt_t = X.groupby("ticker").x.sum().sort_values()
    ex5 = X[~X.ticker.isin(srt_t.index[-5:])].x.mean()
    h1, h2 = X[X.d.dt.year <= split_year].x.mean(), X[X.d.dt.year > split_year].x.mean()
    c5 = X.x.mean() - 0.001
    post = X[X.off > 0].x.mean()
    log(f"SPLIT-NIGHT (official SIP crosses, {folder}), common stocks, nights T+0..T+4: {X.E.nunique()} events")
    log(f"name-nights {len(X)} (nights {g.nunique()}) raw-SPY mean {m*1e4:+.1f}bp t {t:.2f} median {X.x.median()*1e4:+.1f}bp "
        f"hit {(X.x > 0).mean()*100:.0f}% | ex-top-5 tickers {ex5*1e4:+.1f}bp | halves <= {split_year} {h1*1e4:+.1f} after "
        f"{h2*1e4:+.1f} | 5bp/side {c5*1e4:+.1f} | T+1..T+4 only {post*1e4:+.1f}bp")
    checks = [m > 0 and t >= 2, h1 > 0 and h2 > 0, X.x.median() > 0, ex5 > 0, c5 > 0, post > 0]
    verdict = "PASS" if all(checks) else ("FAIL" if (m <= 0 or t < 1) else "WEAK")
    log(f"   checks [t, halves, median, ex-top5, 5bp cost, T+1..4] = {checks} -> {verdict}")
    for off, s in X.groupby("off"):
        mm, tt = cluster_t(s.x, s.d.dt.strftime("%Y-%m-%d"))
        srt = np.sort(s.x.to_numpy())
        log(f"   T+{off}: n {len(s)} mean {mm*1e4:+.1f}bp t {tt:.2f} median {s.x.median()*1e4:+.1f} hit "
            f"{(s.x > 0).mean()*100:.0f}% ex-top5 {srt[:-5].mean()*1e4:+.1f} | open-cross $ median {s.ocs.median()/1e6:.2f}M "
            f"p10 {s.ocs.quantile(.1)/1e3:.0f}k")
    T0 = X[X.off == 0]
    log("   T+0 by year (n / mean / median bp): " + "; ".join(
        f"{y} {len(s)}/{s.x.mean()*1e4:+.0f}/{s.x.median()*1e4:+.0f}" for y, s in T0.groupby(T0.d.dt.year)))
    X.to_csv(D / f"{folder}.csv", index=False)
    out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
