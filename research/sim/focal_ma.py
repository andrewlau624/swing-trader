"""Probe FOCAL-MA: do crossings of POPULAR moving-average lookbacks (50/100/200d) carry more follow-through than
crossings of adjacent non-focal lookbacks? Mechanism: trend followers / technical traders herd on focal rules, so a
focal cross triggers synchronized flow (continuation) that a non-focal cross of the same size does not.

Daily closes, Sharadar SFP (ETFs, ADV >= $20M) and SEP (common, price >= $10, ADV >= $50M), 2000-2026.
Signed forward return = sign(cross) x (ret over h days from the cross close - own trailing 250d mean daily ret x h).
Exploratory probe, no N.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).with_name("focal_ma_out.txt")
FOCAL = [50, 100, 200]
NON = [43, 57, 87, 113, 173, 227]
H = [1, 5, 20]


def bars(name: str, lo_adv: float, lo_px: float) -> pd.DataFrame:
    b = ds.dataset(STORE / f"{name}.parquet").to_table(
        columns=["ticker", "date", "close", "volume"],
        filter=ds.field("date") >= pd.Timestamp("1999-01-01").date()).to_pandas()
    if name == "stocks":
        t = ds.dataset(STORE / "tickers.parquet").to_table(columns=["table", "ticker", "category"]).to_pandas()
        ok = set(t.loc[(t.table == "SEP") & (t.category.fillna("") == "Domestic Common Stock"), "ticker"])
        b = b[b.ticker.isin(ok)]
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["ticker", "date"]).reset_index(drop=True)
    adv = (b.close * b.volume).groupby(b.ticker).transform(lambda s: s.rolling(20, min_periods=15).mean())
    keep = adv.groupby(b.ticker).transform("median") >= lo_adv
    return b[keep & (b.close >= lo_px)].reset_index(drop=True)


def events(b: pd.DataFrame) -> pd.DataFrame:
    g = b.groupby("ticker", sort=False).close
    r = g.pct_change()
    mu = r.groupby(b.ticker).transform(lambda s: s.shift(1).rolling(250, min_periods=200).mean())
    fwd = {h: g.shift(-h) / b.close - 1 - mu * h for h in H}
    out = []
    for n in FOCAL + NON:
        sma = g.transform(lambda s: s.rolling(n, min_periods=n).mean())
        above = (b.close > sma).astype(float).where(sma.notna())
        prev = above.groupby(b.ticker).shift(1)
        cross = (above != prev) & prev.notna() & above.notna()
        sgn = np.where(above == 1, 1.0, -1.0)
        e = pd.DataFrame({"date": b.date[cross], "n": n, "sgn": sgn[cross.values]})
        for h in H:
            e[f"f{h}"] = sgn[cross.values] * fwd[h][cross].values
        out.append(e)
    return pd.concat(out).dropna()


def clus(x: pd.Series, d: pd.Series) -> tuple[float, float]:
    m = x.groupby(d).mean()
    return x.mean(), m.mean() / m.std() * np.sqrt(len(m))


def main():
    lines = ["FOCAL-MA probe: signed forward excess return after an SMA cross (bp), date-clustered t", ""]
    for name, adv, px in [("funds", 2e7, 5), ("stocks", 5e7, 10)]:
        e = events(bars(name, adv, px))
        lines.append(f"== {name} ==")
        for era, x in [("2000-12", e[e.date < "2013"]), ("2013-26", e[e.date >= "2013"])]:
            for h in H:
                f = x[x.n.isin(FOCAL)]; nf = x[x.n.isin(NON)]
                mf, tf = clus(f[f"f{h}"], f.date); mn, tn = clus(nf[f"f{h}"], nf.date)
                per = " ".join(f"{n}:{x[x.n == n][f'f{h}'].mean()*1e4:+.0f}" for n in sorted(FOCAL + NON))
                lines.append(f"{era} h{h:2d}: focal {mf*1e4:+6.1f} (t {tf:+.2f}, n {len(f)}) non-focal {mn*1e4:+6.1f} "
                             f"(t {tn:+.2f}) diff {(mf-mn)*1e4:+6.1f} | {per}")
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
