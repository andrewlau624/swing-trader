"""EV2 post-judge diagnostics (NOT a new verdict; the registered PASS at N 760 stands as printed).
Every ID3 event (officer/director open-market purchase) is tagged with the days since the issuer's previous open-market
purchase filing by anyone; then: silence buckets, EV2 vs the rest of ID3, outliers, SPY-adjusted, size, cost break-even.

    PYTHONPATH=. .venv/bin/python -m research.sim.ev2_diagnostics
"""
import numpy as np
import pandas as pd

from research.sim import event_fetch as F
from research.sim import filing_day as FD
from research.sim.outside_box import insider_buys

END = pd.Timestamp("2026-03-31")
COST = 5e-4                                   # 2.5bp per side


def tstat(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std() / np.sqrt(len(x))) if len(x) > 2 else np.nan


def day_t(T, col="net"):
    """t on the equal-weight daily portfolio (events on the same day are not independent)."""
    return tstat(T.groupby("d")[col].mean())


def line(name, T, col="net"):
    if not len(T):
        return f"{name:34s} n 0"
    x = T[col]
    return (f"{name:34s} n {len(T):5d}  mean {x.mean()*1e4:+6.1f}bp  median {x.median()*1e4:+6.1f}  "
            f"hit {(x > 0).mean():.0%}  t {tstat(x):+.2f}  day-t {day_t(T, col):+.2f}")


def main():
    A = insider_buys().sort_values("fd")
    hist = A.groupby("sym").fd.apply(lambda s: np.sort(s.drop_duplicates().to_numpy()))
    X = A[A.insider].copy()
    gap, usd = [], []
    for s, d in zip(X.sym, X.fd):
        h = hist.get(s)
        prev = h[h < d.to_datetime64()] if h is not None else []
        gap.append((d - pd.Timestamp(prev.max())).days if len(prev) else np.nan)
    X["gap"] = gap
    X["censored"] = X.gap.isna()
    # one row per (sym, fd): keep the longest silence and the total $ bought that day
    X = X.groupby(["sym", "fd"]).agg(gap=("gap", "max"), censored=("censored", "all"), usd=("usd", "sum")).reset_index()
    X = X[X.fd >= "2022-01-01"]                               # silence of 2y is observable from here on
    T, _ = FD.trades(X[["sym", "fd"]], END)
    T = T[T.adv >= 2e7]
    # map trade back to its event: the event is the latest fd before d
    ev = X.sort_values("fd")
    T = T.sort_values("d")
    T = pd.merge_asof(T, ev.rename(columns={"fd": "fd_"}).sort_values("fd_")[["sym", "fd_", "gap", "censored", "usd"]],
                      left_on="d", right_on="fd_", by="sym", direction="backward", allow_exact_matches=False)
    first = T.censored | (T.gap >= 730)
    T["ev2"] = first
    spy = F.raw_bars(["SPY"])["SPY"]; spy.index = pd.to_datetime(spy.index)
    T["spy"] = T.d.map(spy.close / spy.open - 1)
    T["net"] = T.ret - COST
    T["xnet"] = T.ret - T.spy - COST
    T["half"] = np.where(T.d <= "2023-12-31", "select", "judge")
    T["year"] = T.d.dt.year

    print("== ID3 events 2022-01..2026-03, ADV >= $20M, open->close net of 2.5bp/side")
    for h in ["select", "judge", None]:
        S = T if h is None else T[T.half == h]
        print(f"-- {h or 'all'}")
        print(line("  EV2 (silence >= 730d or none)", S[S.ev2]))
        print(line("  rest of ID3", S[~S.ev2]))
        a, b = S[S.ev2].groupby("d").net.mean(), S[~S.ev2].groupby("d").net.mean()
        diff = (S[S.ev2].net.mean() - S[~S.ev2].net.mean())
        se = np.sqrt(S[S.ev2].net.var() / S.ev2.sum() + S[~S.ev2].net.var() / (~S.ev2).sum())
        print(f"  EV2 minus rest: {diff*1e4:+.1f}bp (Welch t {diff/se:+.2f})")

    print("\n== dose-response: days since the issuer's previous open-market purchase (all years)")
    bins = [0, 7, 30, 90, 180, 365, 730, 1e9]
    T["bucket"] = pd.cut(T.gap, bins, right=False, labels=["<7d", "7-30d", "30-90d", "90-180d", "180-365d", "1-2y", ">=2y"])
    for b, S in T.groupby("bucket", observed=True):
        print(line(f"  {b}", S), "| select", f"{S[S.half=='select'].net.mean()*1e4:+.1f}", "judge", f"{S[S.half=='judge'].net.mean()*1e4:+.1f}")
    print(line("  none since 2020-01 (censored)", T[T.censored]), "| select",
          f"{T[T.censored & (T.half=='select')].net.mean()*1e4:+.1f}", "judge", f"{T[T.censored & (T.half=='judge')].net.mean()*1e4:+.1f}")

    E = T[T.ev2]
    print("\n== EV2 robustness")
    print(line("  EV2 net", E))
    print(line("  EV2 net minus SPY open->close", E, "xnet"))
    print(line("  ID3-rest net minus SPY", T[~T.ev2], "xnet"))
    q = E.net.quantile([0.01, 0.99])
    print(line("  EV2 trimmed 1%/99%", E[(E.net > q.iloc[0]) & (E.net < q.iloc[1])]))
    print(line("  EV2 without its 10 best trades", E.drop(E.net.nlargest(10).index)))
    print(line("  EV2 without its best 20 days", E[~E.d.isin(E.groupby('d').net.mean().nlargest(20).index)]))
    print("  by year: " + "  ".join(f"{y} {v*1e4:+.1f} (n {n})" for (y, v), n in
                                    zip(E.groupby('year').net.mean().items(), E.groupby('year').size())))
    E = E.assign(advb=pd.qcut(E.adv, 3, labels=["low ADV", "mid ADV", "high ADV"]),
                 usdb=pd.qcut(E.usd, 3, labels=["small buy", "mid buy", "big buy"]),
                 gapday=(E.o / E.pc - 1))
    E["gapb"] = pd.cut(E.gapday, [-1, -0.01, 0.01, 1], labels=["gap down <-1%", "flat", "gap up >+1%"])
    for col in ["advb", "usdb", "gapb"]:
        for b, S in E.groupby(col, observed=True):
            print(line(f"  {b}", S), "| sel", f"{S[S.half=='select'].net.mean()*1e4:+.1f}", "jdg", f"{S[S.half=='judge'].net.mean()*1e4:+.1f}")
    g = E.ret.mean()
    print(f"\n  gross {g*1e4:+.1f}bp -> break-even cost {g/2*1e4:.1f}bp per side "
          f"(ID3 rest gross {T[~T.ev2].ret.mean()*1e4:+.1f}bp -> {T[~T.ev2].ret.mean()/2*1e4:.1f}bp/side)")
    print(f"  trades/yr {len(E)/((E.d.max()-E.d.min()).days/365.25):.0f}; days with an EV2 trade/yr "
          f"{E.d.nunique()/((E.d.max()-E.d.min()).days/365.25):.0f}; median ADV ${E.adv.median()/1e6:.0f}M; median price ${E.o.median():.0f}")
    T.to_pickle("data/research/program/ev2_diagnostics_trades.pkl")


if __name__ == "__main__":
    main()
