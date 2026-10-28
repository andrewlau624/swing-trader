"""U6: IBS on auction-traded crypto ETFs (IBIT/ETHA/FBTC), 2024+.

Pre-registration: docs/research/hypothesis-space.md U6 (Tier B; below the +8pp
stand-alone gate, run as a zero-cost universe extension of the live IBS leg).
Rule, exactly the live IBS timing: IBS < 0.2 on day d's bar, buy the opening
cross d+1, sell the opening cross d+2 (re-evaluated every morning).
Judge: 2024-26 net return vs the live 18-ETF IBS leg's same-day mean. Kill if
the excess is <= 0. Data: Sharadar SFP daily bars (open == the official opening
print, SPLIT-CROSS 2016-20) + the cached 18-ETF panel used by the simulator.

    PYTHONPATH=. .venv/bin/python -m research.sim.u6_crypto_ibs
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import data as D
from .book import EQ18, ibs_days

ROOT = pathlib.Path(__file__).resolve().parents[2]
SH = pathlib.Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/u6_crypto_ibs_out.txt"
CRYPTO = ["IBIT", "ETHA", "FBTC"]
START = "2024-01-11"
IBS_MAX = 0.2
COSTS = (0.0, 2.0, 7.5)                  # bps/side; live measured ~0


def load_crypto() -> dict[str, pd.DataFrame]:
    cols = ["ticker", "date", "open", "high", "low", "close", "volume"]
    f = pd.read_parquet(SH / "funds.parquet", columns=cols,
                        filters=[("ticker", "in", CRYPTO)])
    f["date"] = pd.to_datetime(f.date)
    out = {}
    for k in ("open", "high", "low", "close"):
        out[k] = f.pivot(index="date", columns="ticker", values=k).sort_index()
    return out


def ibs(high, low, close):
    rng = high - low
    return np.where(rng > 0, (close - low) / rng, np.nan)


def leg_days(O, H, L, C, symbols, top_k=3):
    """The live IBS decision loop on a custom panel (book.ibs_days with a universe)."""
    days = C.index
    out, mom_cache = {}, {}
    for j in range(260, len(days) - 2):
        d, today = days[j], days[j + 1]
        m = today.to_period("M")
        if m not in mom_cache:
            mom_cache[m] = sg.momentum_top(C[symbols][C.index < today], today, top_k)
        last = {s: {"high": H.at[d, s], "low": L.at[d, s], "close": C.at[d, s]} for s in mom_cache[m]}
        tg = sg.ibs_targets(last, IBS_MAX)
        legs = [(s, O.at[days[j + 1], s], O.at[days[j + 2], s] / O.at[days[j + 1], s] - 1)
                for s in tg if np.isfinite(O.at[days[j + 1], s]) and np.isfinite(O.at[days[j + 2], s])]
        if legs:
            out[d] = legs
    return out


def cluster_t(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def stats(x: pd.Series, cost_bp: float = 0.0) -> str:
    x = (x - 2 * cost_bp / 1e4).dropna()
    if not len(x):
        return "n 0"
    ex5 = (x.sum() - np.sort(x.values)[-5:].sum()) / (len(x) - 5) if len(x) > 5 else np.nan
    return (f"n {len(x)} mean {x.mean()*1e4:+.1f}bp med {x.median()*1e4:+.1f} hit {(x > 0).mean():.2f} "
            f"t {cluster_t(x):+.2f} ex-top5 {ex5*1e4:+.1f}bp")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fh = open(OUT, "w")

    def log(*a):
        s = " ".join(str(i) for i in a)
        print(s, flush=True); fh.write(s + "\n"); fh.flush()

    K = load_crypto()
    live = ibs_days()                                   # day d -> [(sym, o1, ret)]
    days = K["close"].index
    trade_rows = []
    for s in CRYPTO:
        O, H, L, C = K["open"][s], K["high"][s], K["low"][s], K["close"][s]
        v = pd.Series(ibs(H.values, L.values, C.values), index=days)
        for d in v.index:
            if d < pd.Timestamp(START) or not np.isfinite(v.loc[d]) or v.loc[d] >= IBS_MAX:
                continue
            i = days.get_loc(d)
            if i + 2 >= len(days):
                continue
            o1, o2 = O.iloc[i + 1], O.iloc[i + 2]
            if np.isfinite(o1) and np.isfinite(o2) and o1 > 0:
                trade_rows.append(dict(date=d, sym=s, ibs=float(v.loc[d]), ret=float(o2 / o1 - 1)))
    T = pd.DataFrame(trade_rows)
    T["live"] = T.date.map(lambda d: np.mean([r for _, _, r in live[d]]) if d in live else np.nan)
    T["excess"] = T.ret - T.live
    log(f"U6 crypto-ETF IBS (N 1067): {len(T)} trades, {T.date.nunique()} signal days, "
        f"{T.date.min().date()}..{T.date.max().date()}; IBS<{IBS_MAX} frequency "
        + ", ".join(f"{s} {len(T[T.sym == s])}" for s in CRYPTO))
    for s in CRYPTO:
        x = T[T.sym == s]
        log(f"  {s}: {stats(x.ret, 0.0)}")
    log(f"  pooled, 0bp/side:       {stats(T.ret, 0.0)}")
    log(f"  pooled, 2bp/side:       {stats(T.ret, 2.0)}")
    log(f"  pooled, 7.5bp/side:     {stats(T.ret, 7.5)}")
    log(f"  vs live 18-ETF leg same day, 0bp: {stats(T.excess, 0.0)}")
    log(f"  vs live 18-ETF leg same day, 2bp: {stats(T.excess, 2.0)}")
    for lab, m in (("2024", T.date.dt.year == 2024), ("2025-26", T.date.dt.year >= 2025)):
        log(f"  {lab}: {stats(T[m].excess, 0.0)}")
    log("  by year excess: " + ", ".join(f"{y} {g.excess.mean()*1e4:+.0f}bp (n {len(g)})" for y, g in T.groupby(T.date.dt.year)))
    if len(T) > 5:
        log("  ex-best-5 excess: " + stats(T.drop(T.excess.nlargest(5).index).excess, 0.0))

    # universe extension: 18 ETFs + crypto ETFs, same live rule and momentum rank
    P = D.etf()
    idx = P["close"].index.union(days)
    O = pd.DataFrame(index=idx).join(P["open"]).join(K["open"]).ffill()
    H = pd.DataFrame(index=idx).join(P["high"]).join(K["high"]).ffill()
    L = pd.DataFrame(index=idx).join(P["low"]).join(K["low"]).ffill()
    C = pd.DataFrame(index=idx).join(P["close"]).join(K["close"]).ffill()
    syms21 = EQ18 + CRYPTO
    ext = leg_days(O, H, L, C, syms21)
    rows = []
    for d in sorted(set(live) & set(ext)):
        if d < pd.Timestamp(START):
            continue
        lr = np.mean([r for _, _, r in live[d]])
        er = np.mean([r for _, _, r in ext[d]])
        n_crypto = sum(1 for s, _, _ in ext[d] if s in CRYPTO)
        rows.append(dict(date=d, live=lr, ext=er, diff=er - lr, n_crypto=n_crypto, n=len(ext[d])))
    E = pd.DataFrame(rows)
    log(f"\nuniverse extension (18 -> 21, same top-3 momentum + IBS<{IBS_MAX}): {len(E)} sessions, "
        f"crypto picked on {int((E.n_crypto > 0).sum())} ({(E.n_crypto > 0).mean():.0%}), "
        f"mean {E.n_crypto.mean():.2f} crypto names/night")
    log(f"  leg mean/day live {E.live.mean()*1e4:+.1f}bp vs extended {E.ext.mean()*1e4:+.1f}bp; "
        f"diff {E['diff'].mean()*1e4:+.1f}bp (t {cluster_t(E['diff']):+.2f}, median {E['diff'].median()*1e4:+.1f})")
    log(f"  on crypto-picked days: live {E[E.n_crypto > 0].live.mean()*1e4:+.1f} vs ext "
        f"{E[E.n_crypto > 0].ext.mean()*1e4:+.1f}bp (n {int((E.n_crypto > 0).sum())})")
    log(f"\nVERDICT: {'PASS-SMALL' if T.excess.mean() > 0 and E['diff'].mean() > 0 else 'KILL'} "
        f"(kill rule: excess vs the leg's same-day picks <= 0)")
    fh.close()


if __name__ == "__main__":
    main()
