"""Study BDC-RV (N 1130 primary, N 1131 price-only control), pre-registered in round1_prose.md 2026-11-07.

Frozen CEF-RV band rule applied to listed BDCs (a wrapper the rule never saw):
weekly disc = close / PIT NAV - 1 (NAV = Sharadar SF1 ARQ bvps, known at its filing `date`);
enter when disc <= own trailing-52w 10th pct (>= 26 obs), exit when disc >= own trailing-52w median or 26 weeks;
fills at the close of the first session after the signal week-end. Excess vs EW BDC universe (incl. delisted).

Universe: CIKs in SEC XBRL frames NetAssetValuePerShare AND InvestmentOwnedAtCost (2012Q4+) mapped to Sharadar SEP common,
non-BDCs dropped by name, plus a hand list of delisted / renamed BDCs the frames miss (survivorship patch).

  python3 research/sim/bdc_rv.py   -> data/research/program/bdc_rv_out.txt, data/research/bdc_rv/trades.csv
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lh_panel import Panel, cluster_t  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data" / "research" / "bdc_rv"
OUT = ROOT / "data" / "research" / "program" / "bdc_rv_out.txt"
DROP = set("AFCG AIOS CCTSF CCTSU EARN EFC EZGO IXDP MFIN MI MKZR NEWT NXDT PHYT.U PHYTF SILO SUIG WT".split())
ADD = "ABDC ACAS ACSF ALD1 FULL GARS HCAP MCGC MVC OCSI OHAI PCAP1 SUNS1 TURN XRDC PFX".split()
COST, SHOCK, MAXW, NAV_AGE = 0.005, 0.015, 26, 200
lines: list[str] = []


def log(s: str = "") -> None:
    print(s)
    lines.append(s)


def universe() -> list[str]:
    u = pd.read_csv(D / "universe_raw.csv")
    return sorted((set(u.ticker) - DROP) | set(ADD))


def nav_table(tick: list[str]) -> pd.DataFrame:
    f = pd.read_parquet(pathlib.Path.home() / "data/sharadar/fundamentals.parquet",
                        columns=["ticker", "dimension", "date", "reportperiod", "bvps"],
                        filters=[("dimension", "==", "ARQ"), ("ticker", "in", tick)])
    f = f.dropna(subset=["bvps"])
    f = f[f.bvps > 0]
    f["date"] = pd.to_datetime(f["date"])
    return f.sort_values(["ticker", "date"])


def main() -> None:
    P = Panel.load()
    tick = [t for t in universe() if t in P.tix]
    F = nav_table(tick)
    log(f"BDC-RV universe {len(tick)} tickers in panel; with NAV rows {F.ticker.nunique()}")
    dates = pd.DatetimeIndex(P.dates)
    wk = pd.Series(dates, index=dates).groupby(dates.to_period("W-FRI")).max()
    fri = pd.DatetimeIndex(wk.values)
    fri = fri[fri >= "2004-01-01"]
    # weekly matrices
    tr = {}
    disc = {}
    for t in tick:
        s = P.series(t).set_index("date")
        if len(s) < 60:
            continue
        s = s[s.c > 0]
        trw = s.tr.reindex(fri)
        cw = s.c.reindex(fri)  # split-adjusted close
        n = F[F.ticker == t][["date", "reportperiod", "bvps"]].copy()
        if n.empty:
            continue
        # as-reported bvps is in share units valid at its reportperiod: put it in today's adjusted units
        sf = (s.cu / s.c).replace([np.inf, -np.inf], np.nan).dropna()
        rp = pd.to_datetime(n.reportperiod).values
        k = np.searchsorted(sf.index.values, rp, side="right") - 1
        n["f"] = np.where(k >= 0, sf.values[np.clip(k, 0, None)], np.nan)
        n["nav"] = n.bvps / n.f
        nv = pd.merge_asof(pd.DataFrame({"d": fri}), n.rename(columns={"date": "nd"})[["nd", "nav"]],
                           left_on="d", right_on="nd")
        nv.index = fri
        ok = (nv.d - nv.nd).dt.days <= NAV_AGE
        disc[t] = (cw / nv.nav - 1).where(ok)
        tr[t] = trw
    TR = pd.DataFrame(tr)
    DS = pd.DataFrame(disc)
    PX = TR.copy()  # control uses total-return price level
    log(f"funds with discount series {DS.notna().any().sum()}; weeks {len(fri)} {fri[0].date()}..{fri[-1].date()}")
    # daily fills: close of the first session after the signal Friday
    dpos = np.searchsorted(P.dates, fri.values, side="right")  # index of next session
    nxt = pd.Series([P.dates[i] if i < len(P.dates) else pd.NaT for i in dpos], index=fri)

    def tr_at(t, d):
        r = P.row_at(t, d)
        return np.nan if r < 0 else P.tr[r], (None if r < 0 else P.dates[P.di[r]])

    def last_tr(t):
        s = P.rows(t)
        return P.tr[s.stop - 1], P.dates[P.di[s.stop - 1]]

    def run(X: pd.DataFrame, label: str) -> pd.DataFrame:
        trades = []
        for t in X.columns:
            x = X[t]
            open_e = None
            for k in range(len(fri)):
                v = x.iloc[k]
                if np.isnan(v):
                    continue
                hist = x.iloc[max(0, k - 52):k].dropna()
                if open_e is None:
                    if len(hist) >= 26 and v <= np.percentile(hist, 10):
                        open_e = k
                else:
                    if (len(hist) >= 26 and v >= np.median(hist)) or k - open_e >= MAXW:
                        trades.append((t, open_e, k))
                        open_e = None
            if open_e is not None:
                trades.append((t, open_e, None))
        rows = []
        for t, e, xk in trades:
            ed = nxt.iloc[e]
            if pd.isna(ed):
                continue
            a, ead = tr_at(t, ed)
            if np.isnan(a) or ead is None or (pd.Timestamp(ead) - ed).days > 10:
                continue
            if xk is None or pd.isna(nxt.iloc[xk]):
                b, xd = last_tr(t)
                status = "open/last"
            else:
                b, xd = tr_at(t, nxt.iloc[xk])
                status = "closed"
                if np.isnan(b):
                    b, xd = last_tr(t)
                    status = "delisted"
            if xd is None or pd.Timestamp(xd) <= pd.Timestamp(ead):
                continue
            # EW BDC benchmark: all universe names with bars on both dates
            ra = []
            for u in X.columns:
                i, j = P.row_at(u, ead), P.row_at(u, xd)
                if i < 0 or j < 0 or P.dates[P.di[i]] != ead:
                    continue
                if P.dates[P.di[j]] != xd:
                    # delisted inside the window: hold to its last bar (cash after)
                    s = P.rows(u)
                    j = s.stop - 1
                    if P.dates[P.di[j]] < ead or j < i:
                        continue
                ra.append(P.tr[j] / P.tr[i] - 1)
            raw = b / a - 1
            rows.append(dict(arm=label, ticker=t, entry=pd.Timestamp(ead), exit=pd.Timestamp(xd), status=status,
                             disc=X[t].iloc[e] if label == "N1130" else np.nan, raw=raw, ew=np.mean(ra), n_ew=len(ra)))
        df = pd.DataFrame(rows)
        df["net"] = df.raw - COST
        df["exc"] = df.net - df.ew
        df["exc3"] = df.raw - SHOCK - df.ew
        return df

    def report(df: pd.DataFrame, label: str) -> None:
        wkid = df.entry.dt.to_period("W").astype(str)
        m, t_ = cluster_t(df.exc.values * 1e4, wkid.values)
        log(f"\n== {label}: n {len(df)} funds {df.ticker.nunique()} {df.entry.min().date()}..{df.entry.max().date()}")
        log(f"raw net mean {df.net.mean()*1e4:+.0f}bp median {df.net.median()*1e4:+.0f} | EW mean {df.ew.mean()*1e4:+.0f}")
        log(f"EXCESS mean {df.exc.mean()*1e4:+.1f}bp t(wk-clust) {t_:.2f} median {df.exc.median()*1e4:+.1f} "
            f"hit {(df.exc > 0).mean():.0%} | 3x cost {df.exc3.mean()*1e4:+.1f}bp")
        hold = (df.exit - df.entry).dt.days
        log(f"hold days mean {hold.mean():.0f} median {hold.median():.0f}; status {df.status.value_counts().to_dict()}")
        for a, b in (("2004", "2008-12-31"), ("2009", "2017-12-31"), ("2018", "2026-12-31"), ("2013", "2026-12-31")):
            s = df[(df.entry >= a) & (df.entry <= b)]
            if len(s) > 2:
                mm, tt = cluster_t(s.exc.values * 1e4, s.entry.dt.to_period("W").astype(str).values)
                log(f"  {a}..{b[:4]}: n {len(s)} exc {s.exc.mean()*1e4:+.1f} t {tt:.2f} med {s.exc.median()*1e4:+.1f}")
        j = df[df.entry >= "2009"]
        top = j.groupby("ticker").exc.sum().nlargest(5).index
        log(f"  2009+ ex-top-5 funds {j[~j.ticker.isin(top)].exc.mean()*1e4:+.1f}bp (dropped {list(top)})")
        topd = j.groupby(j.entry.dt.to_period('W')).exc.sum().nlargest(5).index
        log(f"  2009+ ex-top-5 entry weeks {j[~j.entry.dt.to_period('W').isin(topd)].exc.mean()*1e4:+.1f}bp")
        y = j.groupby(j.entry.dt.year).exc.agg(["count", "mean"])
        log("  by year exc(bp): " + " ".join(f"{k}:{int(r['count'])}/{r['mean']*1e4:+.0f}" for k, r in y.iterrows()))
        tpy = len(j) / max(1, (j.entry.max() - j.entry.min()).days / 365.25)
        log(f"  trades/yr {tpy:.1f}; mean concurrency {(hold[df.entry >= '2009'].sum() / 365.25) / max(1, (j.entry.max() - j.entry.min()).days / 365.25):.1f}")

    a = run(DS, "N1130")
    a.to_csv(D / "trades.csv", index=False)
    report(a, "N 1130 BDC-RV (NAV discount bands)")
    c = run(PX, "N1131")
    report(c, "N 1131 control (price-level bands, no NAV)")
    j1, j2 = a[a.entry >= "2009"], c[c.entry >= "2009"]
    log(f"\nNAV anchor: 1130 exc - 1131 exc (2009+) = {(j1.exc.mean() - j2.exc.mean())*1e4:+.1f}bp")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
