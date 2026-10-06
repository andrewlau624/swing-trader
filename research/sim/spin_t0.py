"""Study SPIN-T0: spin-off parent ex-date night with the child's actual opening cross (official SIP 2021-2026).

Pre-registration: "Amendment — Study SPIN-T0" in research/drafts/round1_prose.md (N 850 -> 851).

    PYTHONPATH=. .venv/bin/python -m research.sim.spin_t0
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

from .auction_fetch import _env, fetch
from .exdiv_open import crosses, overnight
from .lh_panel import Panel, cluster_t

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/exdiv"
CACHE = D / "spin_t0.json"
OUT = pathlib.Path(__file__).resolve().parent / "spin_t0_out.txt"
STORE = pathlib.Path.home() / "data" / "sharadar"


def main() -> None:
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value", "contraticker"])
    a["date"] = pd.to_datetime(a["date"])
    sp = a[(a.action == "spinoff") & (a.date >= "2021-01-01") & a.ticker.str.fullmatch(r"[A-Z]{1,5}")
           & a.contraticker.str.fullmatch(r"[A-Z]{1,5}") & (a.value > 0)].drop_duplicates(["ticker", "date"])
    cache = json.load(open(CACHE)) if CACHE.exists() else {}
    H = _env()
    for r in sp.itertuples():
        k = f"{r.ticker}_{r.contraticker}_{r.date.date()}"
        if k in cache:
            continue
        s0, s1 = str((r.date - pd.Timedelta(days=7)).date()), str(r.date.date())
        try:
            cache[k] = fetch([r.ticker, r.contraticker], s0, s1, H)
        except Exception as e:  # noqa: BLE001
            cache[k] = {"_error": str(e)[:200]}
    json.dump(cache, open(CACHE, "w"))
    P = Panel.load()
    spy_on = overnight(crosses(json.load(open(D / "spy.json"))["SPY"]))
    rows = []
    for r in sp.itertuples():
        v = cache.get(f"{r.ticker}_{r.contraticker}_{r.date.date()}", {})
        if r.ticker not in v or r.contraticker not in v:
            continue
        p, c = crosses(v[r.ticker]), crosses(v[r.contraticker])
        if r.date not in p.index or r.date not in c.index:
            continue
        k = p.index.get_loc(r.date)
        if k < 1:
            continue
        g = P.row_at(r.ticker, r.date)
        pc = p.cp.iloc[k - 1]
        if g < 1 or pc < 5 or P.c[g - 1] * P.v[g - 1] < 1e6:
            continue
        pnl = (p.op.iloc[k] + r.value * c.op.loc[r.date]) / pc - 1
        if abs(pnl) > 0.5:
            continue
        rows.append(dict(t=r.ticker, ch=r.contraticker, d=r.date, pnl=pnl, cocs=c.os.loc[r.date] * c.op.loc[r.date]))
    X = pd.DataFrame(rows)
    X["x"] = X.pnl - spy_on.reindex(X.d).to_numpy()
    m, t = cluster_t(X.x, X.d.dt.strftime("%Y-%m-%d"))
    srt = np.sort(X.x.to_numpy())
    h1, h2 = X[X.d.dt.year <= 2023].x.mean(), X[X.d.dt.year >= 2024].x.mean()
    checks = [m > 0 and t >= 2, h1 > 0 and h2 > 0, X.x.median() > 0, srt[:-5].mean() > 0, m - 0.001 > 0]
    verdict = "PASS" if all(checks) else ("FAIL" if (m <= 0 or t < 1) else "WEAK")
    lines = [f"SPIN-T0 (official SIP crosses 2021-2026): n={len(X)} raw-SPY mean {m*1e4:+.1f}bp t {t:.2f} median "
             f"{X.x.median()*1e4:+.1f}bp hit {(X.x > 0).mean()*100:.0f}% ex-top5 {srt[:-5].mean()*1e4:+.1f}bp halves "
             f"{h1*1e4:+.1f} / {h2*1e4:+.1f} | child open-cross $ median {X.cocs.median()/1e6:.2f}M",
             f"   checks [t, halves, median, ex-top5, 5bp] = {checks} -> {verdict}",
             "   by year (n/mean/median bp): " + "; ".join(
                 f"{y} {len(s)}/{s.x.mean()*1e4:+.0f}/{s.x.median()*1e4:+.0f}" for y, s in X.groupby(X.d.dt.year))]
    print("\n".join(lines))
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
