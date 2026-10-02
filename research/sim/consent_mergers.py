"""Discovery DL3: written-consent all-cash mergers (DEFM14C). Registered in round1_prose.md (amendment "deal rule
DL3") before this ran."""
from __future__ import annotations

import collections
import html
import re

import pandas as pd

from research.sim.event_fetch import doc, fts_years, raw_bars


def deals() -> pd.DataFrame:
    R = [r for r in fts_years('"per share in cash" "written consent" "merger"', "DEFM14C", 2016, 2026) if r["form"] == "DEFM14C"]
    first = {}
    for r in sorted(R, key=lambda r: r["date"]):
        first.setdefault(r["ciks"][0], r)
    rows = []
    for r in first.values():
        t = html.unescape(doc(r["ciks"][0], r["adsh"], r["id"].split(":")[1]))
        px = collections.Counter(re.findall(r"\$(\d+(?:\.\d+)?) per share in cash", t)).most_common(1)
        sym = re.findall(r"under the symbols? “([A-Z][A-Z.]{0,5})”", t)
        stock_leg = bool(re.search(r"exchange ratio|stock consideration|at your election", t, re.I))
        rows.append(dict(date=r["date"], name=r["names"][0][:40], sym=sym[0] if sym else None,
                         X=float(px[0][0]) if px else None, stock_leg=stock_leg))
    return pd.DataFrame(rows)


def run(sizes=(2300, 10000, 25000)) -> pd.DataFrame:
    D = deals()
    out = []
    for _, d in D.iterrows():
        row = d.to_dict()
        if d.stock_leg or not isinstance(d.sym, str) or not d.X == d.X or not d.X:
            row["note"] = "excluded: stock leg" if d.stock_leg else "excluded: no symbol/price"
            out.append(row); continue
        b = raw_bars([d.sym])[d.sym]
        if not len(b):
            row["note"] = "no bars"; out.append(row); continue
        b.index = pd.to_datetime(b.index)
        aft = b.index[b.index > pd.Timestamp(d.date)]
        if not len(aft) or (aft[0] - pd.Timestamp(d.date)).days > 7:
            row["note"] = "no bar at entry"; out.append(row); continue
        i0 = b.index.get_loc(aft[0])
        entry = b.close.iloc[i0]
        last = len(b) - 1
        done = last - i0 <= 250 and b.index[-1] < pd.Timestamp("2026-09-20")
        if done:
            val, days = d.X, (b.index[-1] - aft[0]).days
        elif i0 + 250 <= last:
            val, days = b.close.iloc[i0 + 250], (b.index[i0 + 250] - aft[0]).days
        else:
            row["note"] = "open (< 250 sessions, still trading)"; out.append(row); continue
        row.update(entry=entry, done=done, value=val, ret=val / entry - 1, days=days)
        for s in sizes:
            row[f"usd{s}"] = int(0.10 * s // entry) * (val - entry)
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    D = run()
    D.to_csv("data/research/events/consent_merger_deals.csv", index=False)
    print(D.round(4).to_string())
    X = D.dropna(subset=["ret"])
    yrs = 10.7
    print(f"\nn {len(X)} ({len(X)/yrs:.1f}/yr) mean {X.ret.mean():.2%} median {X.ret.median():.2%} hit {(X.ret > 0).mean():.0%}"
          f" worst {X.ret.min():.2%}; mean days {X.days.mean():.0f}; mean annualised {(X.ret * 365 / X.days.clip(lower=1)).mean():.1%}")
    print("not completed:", int((~X.done.astype(bool)).sum()))
    for s in (2300, 10000, 25000):
        print(s, "$/yr", round(X[f"usd{s}"].sum() / yrs))
