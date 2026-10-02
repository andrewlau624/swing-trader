"""Round 32 B4 (rules: round1_prose.md Round 32 amendment, cf5d8cf): going-private odd-lot cash-outs, deal by deal.

Holders of fewer than `ratio_threshold` pre-split shares are cashed out at a fixed price. Entry: the close of the first
session after the first public filing; buy min(threshold − 1, what the account affords) shares. Exit: the cash price
if the split took effect within 365 days (paid ~10 sessions after it), else the close 365 days after entry.
Terms: research/data/b4_deals.csv (read from the filings by an agent; no prices).

    PYTHONPATH=. .venv/bin/python -m research.sim.cashout
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
SIZES = (2300, 10000, 25000)


def main():
    D = pd.read_csv(ROOT / "research/data/b4_deals.csv")
    L = D[(D.kind == "oddlot_cashout") & D.ticker.fillna("").str.match(r"(NASDAQ|NYSE)")].copy()
    rows = []
    for r in L.itertuples():
        sym = r.ticker.split(":")[1]
        b = F.raw_bars([sym]).get(sym)
        t0 = pd.Timestamp(r.first_public_date)
        thr = int(str(r.ratio_threshold).split("-")[0])
        if b is None or not len(b):
            rows.append(dict(sym=sym, status="no bars")); continue
        c = b.close.copy(); c.index = pd.to_datetime(c.index); c = c.sort_index()
        post = c[c.index > t0]
        ent_d, ent = post.index[0], float(post.iloc[0])
        pre_close = float(c[c.index < t0].iloc[-1]) if len(c[c.index < t0]) else np.nan
        eff = pd.Timestamp(r.effective_date) if isinstance(r.effective_date, str) else None
        if eff is not None and (eff - ent_d).days <= 365 and r.outcome == "completed":
            ex, ex_d, st = float(r.cash_price), eff + pd.Timedelta(days=14), "cashed out"
        else:
            later = c[c.index <= ent_d + pd.Timedelta(days=365)]
            ex, ex_d, st = float(later.iloc[-1]), later.index[-1], "not completed in 365d"
        g = ex / ent - 1
        d = dict(sym=sym, announced=t0.date(), pre_close=pre_close, entry_d=ent_d.date(), entry=ent, cash=r.cash_price,
                 threshold=thr, status=st, exit=ex, gain=g, days=(ex_d - ent_d).days)
        for E in SIZES:
            sh = min(thr - 1, int(E // ent))
            d[f"usd_{E}"] = sh * (ex - ent)
        rows.append(d)
    X = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    yrs = 10.0
    lines = [f"B4 going-private odd-lot cash-outs, exchange-listed: {len(X)} (of {(D.kind == 'oddlot_cashout').sum()} odd-lot cash-outs; the rest OTC or unlisted)",
             X.round(4).to_string(),
             f"\nentry -> exit: mean {X.gain.mean():+.2%} median {X.gain.median():+.2%} worst {X.gain.min():+.2%} > 0 {(X.gain > 0).mean():.0%}; "
             f"median hold {X.days.median():.0f} days"]
    for E in SIZES:
        lines.append(f"${E/1e3:.1f}k: mean ${X[f'usd_{E}'].mean():,.0f}/deal, worst ${X[f'usd_{E}'].min():,.0f}; ~{len(X)/yrs:.1f}/yr -> ~${X[f'usd_{E}'].sum()/yrs:,.0f}/yr")
    out = "\n".join(lines)
    (ROOT / "data/research/program/cashout_out.txt").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
