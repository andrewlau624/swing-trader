"""Reddit round R6 (GLD overnight for idle night cash), R7 (COR1M gate on the night leg), R4 (leg co-movement).

    PYTHONPATH=. .venv/bin/python -m research.sim.reddit_books

Pre-registration: research/drafts/study_reddit_round.md (commit 96c777d). Reads program_books' cached
"T0L live today" book (per-leg daily contributions) and the macro_events legs for the 2016-20 holdout.
"""
from __future__ import annotations

import io
import pickle
import urllib.request

import numpy as np
import pandas as pd

from . import macro_events as ME

ROOT = ME.CACHE.parents[3] if False else None
PROG = ME.CACHE.parent
OUT = PROG / "reddit_books_out.txt"
ETF = ME.CACHE.parents[1] / "night/etf_daily.parquet"
BOOK = "T0L live today 1.0x cap.10 no conv"
PER = (("2016-20", "2016-02-01", "2020-12-31"), ("2021-23", "2021-01-01", "2023-12-31"),
       ("2024-26", "2024-01-01", "2026-12-31"))
GLD_RT = 4.0 / 1e4                                   # 2bp per side in the crosses


def nw_t(x, lag=5):
    x = pd.Series(x).dropna().values
    n = len(x)
    e = x - x.mean()
    s = (e @ e) / n
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return x.mean() / np.sqrt(s / n)


def sharpe(r):
    r = pd.Series(r).dropna()
    return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan


def cagr(r):
    r = pd.Series(r).dropna()
    return (1 + r).prod() ** (252 / len(r)) - 1 if len(r) else np.nan


def maxdd(r):
    e = (1 + pd.Series(r).fillna(0)).cumprod()
    return float((e / e.cummax() - 1).min())


def cor1m():
    u = "https://cdn.cboe.com/api/global/us_indices/daily_prices/COR1M_History.csv"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    df = pd.read_csv(io.BytesIO(urllib.request.urlopen(req, timeout=60).read()))
    df["DATE"] = pd.to_datetime(df.DATE)
    s = df.set_index("DATE").CLOSE.astype(float)
    df.to_csv(PROG / "cboe" / "COR1M.csv", index=False)
    return s


def main():
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")

    res = pickle.load(open(PROG / "program_books_res.pkl", "rb"))
    me = pickle.load(open(ME.CACHE, "rb"))
    night20, _, bil20, _, _ = me["legs"]
    e = pd.read_parquet(ETF)
    e["d"] = pd.to_datetime(e.timestamp).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    px = {s: g.set_index("d")[["open", "close"]] for s, g in e[e.symbol.isin(["GLD", "BIL"])].groupby("symbol")}
    gld_co = (px["GLD"].open.shift(-1) / px["GLD"].close - 1)          # bought at d's close, sold at d+1's open
    bil_d = px["BIL"].close.pct_change().shift(-1).fillna(0)            # cash earned over the same night (approx.)

    log("== Reddit round R6 / R7 / R4 on the T0L live-today book", pd.Timestamp.now(), "\n")
    verdict = {"R6": [], "R7": []}
    for cost in (3.0, "tier_hi"):
        df = res[("T", BOOK, cost)]["df"].copy()
        ho = res[("T", BOOK, "ho")]
        spare = float((1 - df.night_used.clip(0, 1)).mean())
        log(f"## cost {cost}   (2021-26 mean idle share of the night half {spare:.2f})")

        # ---------------- R6: idle night cash in GLD close->open
        idle = 0.5 * (1 - df.night_used.clip(0, 1))
        inc = idle * (gld_co.reindex(df.index).fillna(0) - GLD_RT - bil_d.reindex(df.index).fillna(0))
        ix_ho = ho.index
        inc_ho = 0.5 * spare * (gld_co.reindex(ix_ho).fillna(0) - GLD_RT - bil_d.reindex(ix_ho).fillna(0))
        r6 = df.r + inc
        both = pd.concat([inc_ho, inc]).sort_index()
        yr = [both[a:b].sum() / (len(both[a:b]) / 252) * 100 for _, a, b in PER]
        t6 = nw_t(both)
        dd0 = min(maxdd(ho), maxdd(df.r)); dd1 = min(maxdd(ho + inc_ho), maxdd(r6))
        ok6 = all(y > 0 for y in yr) and t6 >= 2.0 and (dd1 - dd0) > -0.02
        verdict["R6"].append(ok6)
        log(f"  R6 GLD overnight increment pp/yr: " + "  ".join(f"{l} {y:+.2f}" for (l, _, _), y in zip(PER, yr))
            + f"   NW t {t6:+.2f}   maxDD {dd0*100:.1f}% -> {dd1*100:.1f}%   {'PASS' if ok6 else 'fail'}")
        log(f"     GLD C->O raw mean bp/night: " + "  ".join(
            f"{l} {gld_co[a:b].mean()*1e4:+.2f}" for l, a, b in PER) + "   (O->C: " + "  ".join(
            f"{l} {(px['GLD'].close / px['GLD'].open - 1)[a:b].mean()*1e4:+.2f}" for l, a, b in PER) + ")")

        # ---------------- R7: COR1M z >= +1 at d-1 -> night leg x0.5
        c = cor1m() if cost == 3.0 else c
        z = ((c - c.rolling(252).mean()) / c.rolling(252).std()).shift(1)   # known at d's 15:40 (d-1 close)
        def gate(ix):
            return (z.reindex(ix).ffill() >= 1.0).astype(float)
        gt = gate(df.index)
        r7 = df.r - 0.5 * gt * (df.r_night - 0.5 * df.night_used.clip(0, 1) * bil_d.reindex(df.index).fillna(0))
        # holdout: only 2020 has a night leg (before 2020 the night half is in T-bills)
        n20 = pd.Series(night20).reindex(ix_ho)
        g20 = gate(ix_ho)
        b20 = pd.Series(bil20).reindex(ix_ho).fillna(0)
        r7ho = ho - 0.5 * g20 * 0.5 * (n20.fillna(b20) - b20)
        rows = []
        ok7 = True
        for (lab, a, b) in PER:
            if lab == "2016-20":
                s0, s1 = sharpe(ho["2020-01-02":b]), sharpe(r7ho["2020-01-02":b])
                lab = "2020 HO"
            else:
                s0, s1 = sharpe(df.r[a:b]), sharpe(r7[a:b])
            ok7 &= s1 > s0
            rows.append(f"{lab} Sharpe {s0:.2f} -> {s1:.2f}")
        c0, c1 = cagr(df.r["2021-01-01":]), cagr(r7["2021-01-01":])
        ok7 &= (c1 / c0 - 1) > -0.10
        verdict["R7"].append(ok7)
        log(f"  R7 COR1M gate (on {gt['2021-01-01':].mean():.0%} of 2021-26 days): " + "; ".join(rows)
            + f"; CAGR 2021-26 {c0*100:.1f}% -> {c1*100:.1f}%   {'PASS' if ok7 else 'fail'}")

        # ---------------- R4: leg co-movement (diagnostic)
        L = df[["r_night", "r_ibs", "r_noise"]]
        worst = df.r <= df.r.quantile(0.10)
        log("  R4 leg correlation, all days:\n" + L.corr().round(2).to_string())
        log("  R4 leg correlation, book's worst 10% days:\n" + L[worst].corr().round(2).to_string())
        sh = {k: (L[k] < 0)[worst].mean() for k in L}
        log("  share of the worst-10% days on which each leg lost: " + ", ".join(f"{k} {v:.0%}" for k, v in sh.items()))
        w50 = {k: set(L[k].nsmallest(50).index) for k in L}
        log(f"  worst-50-day overlap: night&ibs {len(w50['r_night'] & w50['r_ibs'])}, night&noise "
            f"{len(w50['r_night'] & w50['r_noise'])}, ibs&noise {len(w50['r_ibs'] & w50['r_noise'])}")
        contrib = L[worst].sum() / df.r[worst].sum()
        log("  share of the worst-10% days' loss by leg: " + ", ".join(f"{k} {v:.0%}" for k, v in contrib.items()) + "\n")

    log("## verdict (both costs)")
    for k, v in verdict.items():
        log(f"  {k}: {'PASS' if all(v) else 'fail'}")


if __name__ == "__main__":
    main()
