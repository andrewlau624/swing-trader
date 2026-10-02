"""Discovery DL1: DRIP optional cash purchases at a fixed 5% discount (UMH, MNR). Registered in round1_prose.md
(amendment "deal rule DL1") before this ran. $1,000 on each monthly Investment Date (the 15th, next trading day)
at P = max(0.95 x mean_4(mid), 0.95 x mid_ID), mid = (high+low)/2 on raw bars; sell at the close of ID+k."""
from __future__ import annotations

import pandas as pd

from research.sim.event_fetch import raw_bars

PLANS = {"UMH": ("2016-01-01", "2026-09-30"), "MNR": ("2016-01-01", "2022-02-27")}  # MNR -> ILPT closed 2022-02-28


def deals(sym: str, start: str, end: str, cash: float = 1000.0, ks=(1, 5, 10)) -> pd.DataFrame:
    b = raw_bars([sym], "2015-10-01", "2026-09-30")[sym].sort_index()
    b.index = pd.to_datetime(b.index)
    mid = (b.high + b.low) / 2
    rows = []
    for m in pd.date_range(start, end, freq="MS"):
        d15 = m + pd.Timedelta(days=14)
        later = b.index[b.index >= d15]
        if not len(later) or later[0] > pd.Timestamp(end):
            continue
        i = b.index.get_loc(later[0])
        if i < 3 or i + max(ks) >= len(b):
            continue
        p = max(0.95 * mid.iloc[i - 3:i + 1].mean(), 0.95 * mid.iloc[i])
        r = dict(sym=sym, id=b.index[i].date(), price=p, close_id=b.close.iloc[i])
        for k in ks:
            r[f"pnl{k}"] = cash / p * b.close.iloc[i + k] - cash
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    D = pd.concat([deals(s, a, z) for s, (a, z) in PLANS.items()])
    D["year"] = pd.to_datetime(D.id).dt.year
    print(D.groupby("sym").size().to_string())
    for k in (5, 1, 10):
        x = D[f"pnl{k}"]
        print(f"exit ID+{k}{' (registered)' if k == 5 else ' (info)'}: n {len(x)}, mean ${x.mean():.2f}, median ${x.median():.2f},"
              f" hit {(x > 0).mean():.0%}, worst ${x.min():.2f}, best ${x.max():.2f}")
    y = D.groupby(["year"])["pnl5"].agg(["count", "sum", "mean"]).round(2)
    print(y.to_string())
    print("years with sum > 0:", int((y["sum"] > 0).sum()), "of", len(y))
    u = D[D.sym == "UMH"]
    print("UMH only, ID+5: n", len(u), "mean", round(u.pnl5.mean(), 2), "hit", f"{(u.pnl5 > 0).mean():.0%}",
          "per yr (12 x mean)", round(12 * u.pnl5.mean(), 0))
    u5 = u[pd.to_datetime(u.id) < "2021-02-11"]
    print("UMH pre-2021 at the $5,000 cap (info): mean/month", round(5 * u5.pnl5.mean(), 2))
    print("effective discount vs ID close: mean", f"{(1 - D.price / D.close_id).mean():.2%}", "median",
          f"{(1 - D.price / D.close_id).median():.2%}")
    D.to_csv("data/research/events/drip_ocp_deals.csv", index=False)
    return D


if __name__ == "__main__":
    main()
