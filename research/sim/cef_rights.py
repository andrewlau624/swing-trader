"""CEF-RIGHTS (N 1084): post-issuance recovery after seasoned-CEF rights offerings. Pre-registration: round1_prose.md
"Forced-flow EDGAR families ... CEF-RIGHTS (N 1084)". One look.

    python3 research/sim/cef_rights.py      # needs data/research/cef_rights/events.csv (cef_rights_fetch.py)
    -> data/research/program/cef_rights_out.txt
"""
from __future__ import annotations

import pathlib
import sys
import types

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
STORE = pathlib.Path.home() / "data" / "sharadar"
if "sharadar" not in sys.modules:   # same shim as cef_stress.py: cef_alpha.universe imports sharadar.tickers
    sys.modules["sharadar"] = types.SimpleNamespace(tickers=lambda: pd.read_parquet(STORE / "tickers.parquet"),
                                                    prices=None, table=None, actions=None)  # dsr import only
from research.sim import cef_alpha  # noqa: E402
from research.sim.cef_txt import clus_t  # noqa: E402
from research.sim.hpool_sharadar import dsr  # noqa: E402

EV = ROOT / "data/research/cef_rights/events.csv"
OUT = ROOT / "data/research/program/cef_rights_out.txt"
N_PROGRAM = 1084
COST = 0.0020          # per side, judged
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def events() -> pd.DataFrame:
    e = pd.read_csv(EV, parse_dates=["filed", "expiry"])
    n0 = len(e)
    e = e[~e["preferred"].astype(bool)].dropna(subset=["expiry"])
    e = e[(e["expiry"] >= e["filed"]) & (e["expiry"] <= e["filed"] + pd.Timedelta(days=120))]
    e = e.sort_values("filed").drop_duplicates(["cik", "expiry"], keep="first")
    # several prospectuses (497 + 424B3 supplements) for one offering: keep one row per cik within 45 days of expiry
    e = e.sort_values(["cik", "expiry"])
    keep, last = [], {}
    for i, r in e.iterrows():
        p = last.get(r["cik"])
        if p is not None and abs((r["expiry"] - p).days) <= 45:
            continue
        last[r["cik"]] = r["expiry"]
        keep.append(i)
    e = e.loc[keep]
    say(f"events: {n0} candidate prospectuses -> {len(e)} offerings (cik, expiry) after preferred/expiry/dedupe filters")
    return e


def prices(tk: list[str]) -> pd.DataFrame:
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "high", "low", "close", "volume", "closeadj"],
                        filters=[("ticker", "in", tk)])
    f["date"] = pd.to_datetime(f["date"]).astype("datetime64[ns]")
    return f.sort_values(["ticker", "date"])


def cs_spread(h: np.ndarray, l: np.ndarray) -> float:
    """Corwin-Schultz (2012) 2-day high-low spread estimate, averaged, negatives set to 0."""
    k = 3 - 2 * np.sqrt(2)
    lh = np.log(h / l) ** 2
    beta = lh[1:] + lh[:-1]
    gamma = np.log(np.maximum(h[1:], h[:-1]) / np.minimum(l[1:], l[:-1])) ** 2
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    s = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    return float(np.nanmean(np.maximum(s, 0)))


def main() -> int:
    e = events()
    t = pd.read_parquet(STORE / "tickers.parquet")
    c = t[(t["table"] == "SFP") & (t["category"] == "CEF")][["ticker", "firstpricedate", "lastpricedate"]]
    tk = sorted(set("|".join(e["tickers"]).split("|")))
    px = prices(tk)
    g = {k: v.reset_index(drop=True) for k, v in px.groupby("ticker")}
    ew, _spy = cef_alpha.universe()
    ewd, ewv = ew.index.to_numpy(), ew.to_numpy()

    def ewret(d0, d1):
        i0, i1 = np.searchsorted(ewd, d0), np.searchsorted(ewd, d1)
        if i0 >= len(ewd) or i1 >= len(ewd) or ewd[i0] != d0 or ewd[i1] != d1:
            return np.nan
        return ewv[i1] / ewv[i0] - 1

    rows = []
    for r in e.itertuples(index=False):
        live = c[c["ticker"].isin(r.tickers.split("|"))
                 & (pd.to_datetime(c["firstpricedate"]) <= r.expiry) & (pd.to_datetime(c["lastpricedate"]) >= r.expiry)]
        if live.empty or live["ticker"].iloc[0] not in g:
            rows.append(dict(cik=r.cik, expiry=r.expiry, status="no-price"))
            continue
        p = g[live["ticker"].iloc[0]]
        d = p["date"].to_numpy()
        i = int(np.searchsorted(d, np.datetime64(r.expiry)))
        if i + 25 >= len(d) or i < 140:
            rows.append(dict(cik=r.cik, expiry=r.expiry, ticker=live["ticker"].iloc[0], status="short-history"))
            continue
        ca = p["closeadj"].to_numpy()

        def win(a, b):
            raw = ca[b] / ca[a] - 1
            return raw, raw - ewret(d[a], d[b])

        jf = int(np.searchsorted(d, np.datetime64(r.filed)))
        rr, xx = win(i + 5, i + 25)
        pr, px_ = win(i + 5 - 126, i + 25 - 126)
        sr_, sx = win(jf, i) if jf < i else (np.nan, np.nan)
        s10r, s10x = win(i - 10, i)
        ir, ix = win(i, i + 5)
        dv = (p["close"].to_numpy()[i - 20:i + 5] * p["volume"].to_numpy()[i - 20:i + 5]).mean()
        cs = cs_spread(p["high"].to_numpy()[i - 15:i + 6], p["low"].to_numpy()[i - 15:i + 6])
        rows.append(dict(cik=r.cik, ticker=live["ticker"].iloc[0], expiry=r.expiry, entry=d[i + 5], exit=d[i + 25],
                         status="ok", raw=rr, x=xx, plac=px_, sub_filed=sx, sub10=s10x, iss=ix, dollar_vol=dv, cs=cs,
                         transferable=r.transferable))
    T = pd.DataFrame(rows)
    say("status:", T["status"].value_counts().to_dict())
    T = T[(T["status"] == "ok") & T["x"].notna()].copy()
    T = T[(T["expiry"] >= "2001-01-01") & (T["expiry"] <= "2026-09-01")].sort_values("entry").reset_index(drop=True)
    T.to_csv(ROOT / "data/research/cef_rights/trades.csv", index=False)
    yrs = (T["expiry"].max() - T["expiry"].min()).days / 365.25
    say(f"judged events {len(T)}, {T['expiry'].min().date()}..{T['expiry'].max().date()}, {len(T)/yrs:.1f}/yr, "
        f"transferable {T['transferable'].mean():.0%}, tickers {T['ticker'].nunique()}")
    say("per-year counts:", T.groupby(T["expiry"].dt.year).size().to_dict())

    mon = T["entry"].dt.to_period("M").astype(str).to_numpy()
    h0 = (T["expiry"] < "2014-01-01").to_numpy()

    def block(name, x):
        x = np.asarray(x, float)
        ok = ~np.isnan(x)
        x, m, hh = x[ok], mon[ok], h0[ok]
        e5 = np.delete(x, np.argsort(-x)[:5]).mean()
        say(f"  {name:34s} n {len(x):3d} mean {x.mean()*1e4:+7.1f}bp t_mon {clus_t(x, m):+.2f} median {np.median(x)*1e4:+7.1f} "
            f"hit {(x > 0).mean():.2f} halves {x[hh].mean()*1e4:+.1f}/{x[~hh].mean()*1e4:+.1f} ex-top5 {e5*1e4:+.1f}")
        return x

    say("\nPRIMARY: buy close(E+5) -> sell close(E+25), excess vs EW CEF universe")
    net = T["x"].to_numpy() - 2 * COST
    block("gross excess", T["x"])
    xn = block("net excess @20bp/side (JUDGED)", net)
    block("net excess @40bp/side (2x)", T["x"] - 0.008)
    block("net excess @60bp/side (3x)", T["x"] - 0.012)
    block("net excess @ CS spread (full RT)", T["x"] - T["cs"])
    block("raw (not excess) net @20bp", T["raw"] - 2 * COST)
    pl = block("placebo E-126 (gross excess)", T["plac"])
    say("\nMECHANISM (reported):")
    block("subscription close(filed)->close(E)", T["sub_filed"])
    block("pre-expiry close(E-10)->close(E)", T["sub10"])
    block("issuance close(E)->close(E+5)", T["iss"])
    for tf, gg in T.groupby("transferable"):
        say(f"  transferable={tf}: n {len(gg)} net {np.mean(gg['x'] - 2*COST)*1e4:+.1f}bp median {np.median(gg['x'] - 2*COST)*1e4:+.1f}")
    say("  per-year net mean (bp):", {int(k): round(v * 1e4) for k, v in
                                       pd.Series(net, index=T['expiry'].dt.year).groupby(level=0).mean().items()})
    say(f"  CS spread median {T['cs'].median()*1e4:.0f}bp; $vol/day median ${T['dollar_vol'].median()/1e6:.2f}M, "
        f"p10 ${T['dollar_vol'].quantile(.1)/1e6:.2f}M")

    # concurrency-aware ceiling: equal split among overlapping open events, capped at 100% of capital
    ent, ex = T["entry"].to_numpy(), T["exit"].to_numpy()
    conc = np.array([max(1, int(((ent <= ent[k]) & (ex > ent[k])).sum())) for k in range(len(T))])
    w = 1.0 / conc
    ann_x = (w * net).sum() / yrs
    ann_raw = (w * (T["raw"].to_numpy() - 2 * COST)).sum() / yrs
    say(f"\nCEILING: mean concurrency {conc.mean():.2f}; %/yr of account (equal split, net 20bp/side): excess {ann_x*100:+.2f}pp, "
        f"raw {ann_raw*100:+.2f}pp; at 50% capture excess {ann_x*50:+.2f}pp ($2.3k/$10k/$25k identical: whole-share and "
        f"$vol cap non-binding at median ${T['dollar_vol'].median()/1e6:.2f}M/day; $100k: 10% of 20d $vol caps "
        f"{(T['dollar_vol']*2 < 1e5).mean():.0%} of events)")

    # gates
    d, srr, sr0 = dsr(xn, N_PROGRAM)
    t_p = clus_t(xn, mon)
    t_pl = clus_t(pl[~np.isnan(pl)], mon[~np.isnan(T["plac"].to_numpy())])
    g = {
        "1 mean>0 t>=2": xn.mean() > 0 and t_p >= 2,
        "2 halves>0": xn[h0].mean() > 0 and xn[~h0].mean() > 0,
        "3 median>0": np.median(xn) > 0,
        "4 ex-top5>0": np.delete(xn, np.argsort(-xn)[:5]).mean() > 0,
        "5 placebo |t|<1.5 & <1/3": abs(t_pl) < 1.5 and abs(np.nanmean(pl)) < abs(xn.mean()) / 3,
        "6 2x cost>0": (T["x"] - 0.008).mean() > 0,
        "7 ceiling>=8pp@50%": ann_x * 50 >= 8,
    }
    say("\nGATES:", {k: bool(v) for k, v in g.items()}, f"DSR {d:.3f} (SR/obs {srr:.3f} vs SR0 {sr0:.3f})")
    verdict = "PASS" if all(g.values()) else ("KILL" if xn.mean() <= 0 or t_p < 1 else "WEAK")
    say("VERDICT:", verdict)
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
