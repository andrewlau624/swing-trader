"""CEF-ALPHA (N 892-893): CEF-RV net of an equal-weight CEF universe (incl. delisted) and of fixed-beta SPY.

    PYTHONPATH=. .venv/bin/python -m research.sim.cef_alpha     # -> research/sim/cef_alpha_out.txt

Pre-registration: round1_prose.md "Study CEF-ALPHA".
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from research.sim.cef_rv import STORE
from research.sim.cef_txt import clus_t

ROOT = pathlib.Path(__file__).resolve().parents[2]
CEF = ROOT / "data/research/cefconnect"
OUT = ROOT / "research/sim/cef_alpha_out.txt"
COST = 0.005
BETA_OTHER = {"1999-2014": 0.76, "2016-2026": 0.53}
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def universe() -> tuple[pd.Series, pd.Series]:
    """Daily EW CEF index level (incl. delisted) and SPY closeadj, indexed by date."""
    from sharadar import tickers
    t = tickers()
    c = t[(t["table"] == "SFP") & (t["category"] == "CEF")][["ticker", "firstpricedate", "lastpricedate"]]
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "closeadj"],
                        filters=[("ticker", "in", sorted(set(c["ticker"]) | {"SPY"}))])
    f["date"] = pd.to_datetime(f["date"]).astype("datetime64[ns]")
    spy = f[f["ticker"] == "SPY"].set_index("date")["closeadj"].sort_index()
    f = f.merge(c, on="ticker")   # a ticker can carry several CEF lives; keep rows inside one of them
    f = f[(f["date"] >= pd.to_datetime(f["firstpricedate"])) & (f["date"] <= pd.to_datetime(f["lastpricedate"]))]
    f = f.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    f["r"] = f.groupby("ticker")["closeadj"].pct_change()
    f = f[f["r"].abs() <= 0.5]
    ew = f.groupby("date")["r"].agg(["mean", "size"])
    say(f"EW CEF universe: {f['ticker'].nunique()} tickers, {ew.index.min().date()}..{ew.index.max().date()}, "
        f"median names/day {int(ew['size'].median())}")
    return (1 + ew["mean"]).cumprod(), spy


def window(idx: pd.Series, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Return of a level series from the first date > a to the first date > b."""
    d = idx.index.to_numpy()
    ia, ib = np.searchsorted(d, a, side="right"), np.searchsorted(d, b, side="right")
    ok = (ia < len(d)) & (ib < len(d))
    v = idx.to_numpy()
    out = np.full(len(a), np.nan)
    out[ok] = v[ib[ok]] / v[ia[ok]] - 1
    return out


def stats(x: np.ndarray, wk: np.ndarray, h: np.ndarray) -> dict:
    e5 = np.delete(x, np.argsort(-x)[:5]).mean()
    return dict(mean=x.mean(), t=clus_t(x, wk), med=np.median(x), h0=x[h].mean(), h1=x[~h].mean(), ex5=e5,
                hit=(x > 0).mean())


def fmt(s: dict) -> str:
    return (f"mean {s['mean']*1e4:+.1f}bp t_wk {s['t']:.2f} median {s['med']*1e4:+.1f} hit {s['hit']:.2f} "
            f"halves {s['h0']*1e4:+.1f}/{s['h1']*1e4:+.1f} ex-top5 {s['ex5']*1e4:+.1f}")


def main() -> int:
    ew, spy = universe()
    spy26 = spy.pct_change(126)
    for name, fp, lo, mid in (("1999-2014", "cef_rv_trades_1999_2014.csv", "1999-01-01", "2007-01-01"),
                              ("2016-2026", "cef_rv_trades.csv", "2016-01-01", "2021-01-01")):
        tr = pd.read_csv(CEF / fp, parse_dates=["edate", "xdate"])
        tr = tr[tr["edate"] >= lo].sort_values("edate").reset_index(drop=True)
        a = tr["edate"].to_numpy("datetime64[ns]")
        b = tr["xdate"].to_numpy("datetime64[ns]")
        r = tr["ret"].to_numpy(float) - COST
        ixb, ixs = window(ew, a, b), window(spy, a, b)
        ok = np.isfinite(ixb) & np.isfinite(ixs)
        r, ixb, ixs, tr = r[ok], ixb[ok], ixs[ok], tr[ok].reset_index(drop=True)
        wk = tr["edate"].dt.strftime("%G-%V").to_numpy()
        h = (tr["edate"] < mid).to_numpy()
        beta = BETA_OTHER[name]
        say(f"\n== {name}: trades {len(r)} (dropped {int((~ok).sum())} without comparator)")
        say(f"  raw net        {fmt(stats(r, wk, h))}")
        say(f"  EW-CEF over hold {ixb.mean()*1e4:+.1f}bp; SPY over hold {ixs.mean()*1e4:+.1f}bp")
        sb, sa = stats(r - ixb, wk, h), stats(r - beta * ixs, wk, h)
        say(f"  B  net - EW CEF ({'N 892' if name[0] == '2' else 'report'}): {fmt(sb)}")
        say(f"  A  net - {beta:.2f}*SPY ({'N 893' if name[0] == '2' else 'report'}): {fmt(sa)}")
        # SPY-dip control: share of entries in SPY's bottom trailing-5y tercile of 26-week return
        s26 = spy26.reindex(pd.DatetimeIndex(a[ok]), method="ffill").to_numpy()
        thr = spy26.rolling(1260, min_periods=500).quantile(1 / 3).reindex(pd.DatetimeIndex(a[ok]), method="ffill").to_numpy()
        dip = s26 <= thr
        say(f"  SPY-dip control: {dip.mean():.0%} of entries on SPY bottom-tercile dates; SPY over hold dip "
            f"{ixs[dip].mean()*1e4:+.0f} vs other {ixs[~dip].mean()*1e4:+.0f}bp; CEF-RV excess vs EW CEF dip "
            f"{(r - ixb)[dip].mean()*1e4:+.0f} vs other {(r - ixb)[~dip].mean()*1e4:+.0f}bp")
        if name[0] == "2":
            g = dict(mean=lambda s: s["mean"] >= 0.01, t=lambda s: s["t"] >= 2, med=lambda s: s["med"] > 0,
                     halves=lambda s: s["h0"] > 0 and s["h1"] > 0, ex5=lambda s: s["ex5"] > 0)
            for lab, s in (("N 892 (B, EW CEF)", sb), ("N 893 (A, fixed-beta SPY)", sa)):
                ch = {k: f(s) for k, f in g.items()}
                say(f"  GATE {lab}: {'PASS' if all(ch.values()) else 'KILL'}  " +
                    " ".join(f"{k}={'Y' if v else 'n'}" for k, v in ch.items()))
            turns = 52 / tr["hold_weeks"].mean()
            for acct, slots in ((2300, 2), (10000, 10), (25000, 25)):
                say(f"  economics ${acct:,}: {slots} x $1k slots, excess vs EW CEF ~{sb['mean']*turns*100:+.1f}pp/yr "
                    f"on deployed capital ({turns:.1f} turns/yr) before capacity limits")
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
