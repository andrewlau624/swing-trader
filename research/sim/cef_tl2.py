"""Study CEF-TL2 (N 863 -> 864): December tax-loss -> January reversion in CEFs.

Reopen of CEF-TL (killed on 142 survivor CEFs) with the Sharadar SFP CEF universe:
~1,891 CEF series 1997-2026 INCLUDING delisted. Same legs/rates (round1_prose.md amendment).

    PYTHONPATH=. .venv/bin/python -m research.sim.cef_tl2
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .lh_panel import Panel

OUT = pathlib.Path(__file__).resolve().parent / "cef_tl2_out.txt"
lines: list[str] = []


def log(s: str) -> None:
    lines.append(s)
    print(s)


def main() -> None:
    P = Panel.load()
    # CEF tickers
    t = pd.read_parquet("/Users/andrewlau/data/sharadar/tickers.parquet")
    t = t[(t.table == "SFP") & (t.category.str.contains("CEF", na=False))]
    ceft = list(t.ticker.astype(str))
    log(f"CEF series in panel: {len(ceft)}")
    # build per-year array of daily CEF total-return indices
    dayw = np.isin(P.tid, [P.tix[x] for x in ceft if x in P.tix]) & (P.src == 1)
    rows = np.flatnonzero(dayw)
    F = pd.DataFrame({"ticker": P.tickers[P.tid[rows]], "di": P.di[rows], "tr": P.tr[rows]})
    dates_with = sorted(set(F.di.tolist()))
    # pivot to wide per-date returns via groupby (tr ratio within ticker)
    k = F.sort_values(["ticker", "di"])
    k["r"] = k.groupby("ticker")["tr"].pct_change(fill_method=None)
    log(f"CEF bars {len(F)}, tickers in data {F.ticker.nunique()}")
    # universe daily mean return (equal weight, per date)
    # filter: raw close >= 3 at each date too -- do it on cu when needed via P
# monthly aggregation per year
    years = range(1999, 2026)
    res = []
    for y in years:
        # session indices for: prior dec-end, nov end, dec end, jan end of y+1
        def lim(y, m):
            y2, m2 = (y, m) if m <= 12 else (y + 1, m - 12)
            return int(np.searchsorted(P.dates, np.datetime64(f"{y2}-{m2:02d}-01")))
        d_base = lim(y, 1) - 1     # ~prior Dec 31 session (last session before Jan 1 of y)
        d_nov = lim(y, 12) - 1
        d_dec = lim(y, 13) - 1     # last December session (before Jan 1 next yr)
        d_jan = lim(y + 1, 2) - 2  # last January session
        if not (d_dec - d_nov > 3 and d_jan - d_dec > 3):
            continue
        sub = k[(k.di >= d_base) & (k.di <= d_jan)]
        # prices at boundaries via pivot-table on tr (first close at/after boundary)
# per-ticker: value at each of the four dates (last bar <= boundary)
        def at(d_: int):
            g = sub[sub.di <= d_]
            z = g.sort_values(["ticker", "di"]).groupby("ticker").tail(1)
            return z.set_index("ticker")["tr"]
        A_ = {lab: at(d) for lab, d in (("base", d_base), ("nov", d_nov), ("dec", d_dec), ("jan", d_jan))}
        prev = A_["base"].index
        keep = list(prev)
        if len(keep) < 50:
            continue
        c = pd.DataFrame({f"p_{lab}": A_[lab].reindex(keep) for lab in A_})
        c = c.replace([np.inf, -np.inf], np.nan).dropna(subset=["p_base", "p_nov", "p_dec", "p_jan"])
        c = c[(c.p_nov > 0.05) & (c.p_dec > 0.05) & (c.p_jan > 0.05) & (c.p_base > 0.05)]
        # px filter: raw price at nov via P
        pxs = []
        for tk in keep:
            s = P.rows(tk)
            j = np.searchsorted(P.di[s], d_nov)
            pxs.append(float(P.cu[s][min(j, s.stop - s.start - 1)]) if j <= s.stop - s.start else np.nan)
        c["px"] = pxs
        c = c[c.px.notna() & (c.px >= 3)]
        if len(c) < 30:
            log(f"{y}: universe {len(c)} (n small, still judged)")
        c["ytd"] = c.p_nov / c.p_base - 1
        c["dec"] = c.p_dec / c.p_nov - 1
        c["jan"] = c.p_jan / c.p_dec - 1
        c = c.dropna(subset=["ytd"])
        q1 = c.nsmallest(max(1, int(np.ceil(len(c) * 0.2))), "ytd")
        uni = c[["dec", "jan"]].mean()
        res.append(dict(year=y, n=len(q1), nu=len(c),
                        dec_q1=q1.dec.mean() - uni.dec, jan_q1=q1.jan.mean() - uni.jan,
                        dec_q1_raw=q1.dec.mean(), jan_q1_raw=q1.jan.mean(),
                        jan_spread=q1.jan.mean() - c.nlargest(1, "ytd").jan.mean()))
    R = pd.DataFrame(res)
    R["dec_net"] = R.dec_q1 - 0.003
    R["jan_net"] = R.jan_q1 - 0.003
    for col in ("dec_q1_raw", "dec_net", "jan_q1_raw", "jan_net"):
        m = R[col].mean()
        se = R[col].std(ddof=1) / np.sqrt(len(R)) if len(R) else np.nan
        srt = np.sort(R[col].to_numpy())
        log(f"{col}: mean {m*100:+.2f}% t {m/se if se==se else 0:.2f} years+ {(R[col]>0).mean()*100:.0f}% "
            f"median {np.median(R[col])*100:+.2f}% ex-best {srt[:-1].mean()*100:+.2f}%")
    log(f"\nyears 1999-2025 n {len(R)}, fills {R.n.sum()}; avg names/yr {R.n.mean():.0f} / universe {R.nu.mean():.0f}")
    for lo, hi in ((1999, 2016), (2016, 2026)):
        s = R[(R.year >= lo) & (R.year < hi)]
        se = s.jan_q1_raw.std(ddof=1) / np.sqrt(len(s)) if len(s) > 2 else np.nan
        log(f"  {lo}-{hi}: jan Q1-u gross mean {s.jan_q1_raw.mean()*100:+.2f}% t {s.jan_q1_raw.mean()/se if se==se else 0:.2f} "
            f"years+ {(s.jan_q1_raw>0).mean()*100:.0f}%")
    log(R[["year", "n", "nu", "dec_q1_raw", "jan_q1_raw"]].to_string(index=False))
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
