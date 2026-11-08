"""Study VT-FLOW: modeled vol-target fund rebalancing flow -> next-day index return. Pre-reg round1_prose.md (N 1071 -> 1075).

Run: python3 -I research/sim/vt_flow.py   (free Yahoo daily data, cached in data/research/vtflow/)
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import research.sim.vts as vts  # noqa: E402  (repo Yahoo close helper)

CACHE = ROOT / "data/research/vtflow"
CACHE.mkdir(parents=True, exist_ok=True)
vts.CACHEDIR = CACHE
OUT = ROOT / "data/research/program/vt_flow_out.txt"
TARGET, CAP, B = 0.10, 1.5, 1e4
lines: list[str] = []


def P(s: str = "") -> None:
    print(s)
    lines.append(s)


def yahoo_ohlc(sym: str) -> pd.DataFrame:
    """Open/close/adjclose (vts.yahoo keeps close only)."""
    f = CACHE / f"ohlc_{sym.replace('^', '')}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           f"?period1=0&period2={int(pd.Timestamp.now().timestamp())}&interval=1d&events=div,split")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.load(r)
    res = j["chart"]["result"][0]
    # exchange-local dates: Yahoo stamps Asian/FX bars at the local open (the previous evening in New York), so a
    # New York date puts them one day early (lookahead; caught in intl_gap, 2026-11-07). US tickers are unchanged.
    tz = res.get("meta", {}).get("exchangeTimezoneName") or "America/New_York"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None)
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({"open": q["open"], "close": q["close"], "adjclose": res["indicators"]["adjclose"][0]["adjclose"]},
                      index=idx.astype("datetime64[ns]")).dropna()
    df = df[~df.index.duplicated(keep="last")]
    df.to_parquet(f)
    return df


def exposure(lr: pd.Series) -> pd.Series:
    rv = np.maximum(lr.rolling(21).std(), lr.rolling(63).std()) * np.sqrt(252)
    return np.minimum(CAP, TARGET / rv)


def flows(close: pd.Series) -> pd.DataFrame:
    lr = np.log(close).diff()
    E = exposure(lr)
    a1 = E.diff()
    # A2: windows ending t+1 with r_{t+1}=0 -> only the drop-outs act. sd over [t-19..t, 0] and [t-61..t, 0].
    def sd_with_zero(n):
        w = n - 1
        s1 = lr.rolling(w).sum()
        s2 = (lr ** 2).rolling(w).sum()
        mean = s1 / n
        return np.sqrt((s2 - n * mean ** 2) / (n - 1))
    rv_star = np.maximum(sd_with_zero(21), sd_with_zero(63)) * np.sqrt(252)
    a2 = np.minimum(CAP, TARGET / rv_star) - E
    return pd.DataFrame({"E": E, "A1": a1, "A2": a2, "lr": lr})


def signal(F: pd.Series, q: float) -> pd.Series:
    a = F.abs()
    thr = a.shift(1).rolling(252, min_periods=200).quantile(q)
    s = np.sign(F).where(a > thr, 0.0)
    return s.where(thr.notna(), 0.0)


def nw_t(x: np.ndarray, lag: int = 5) -> float:
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return float("nan")
    e = x - x.mean()
    v = e @ e / n
    for k in range(1, lag + 1):
        v += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return x.mean() / np.sqrt(v / n)


def stats(sig: pd.Series, ret: pd.Series, cost_rt: float, lo, hi) -> dict:
    """Signed next-day return on signal days. sig at t, ret = return t -> t+1 aligned at t."""
    d = pd.DataFrame({"s": sig, "r": ret}).dropna().loc[lo:hi]
    d = d[d.s != 0]
    g = d.s * d.r
    net = g - cost_rt
    o = np.sort(net.values)
    ex5 = net.drop(net.abs().nlargest(5).index).mean() if len(net) > 5 else np.nan
    yrs = max((pd.Timestamp(hi) - pd.Timestamp(lo)).days / 365.25, 1e-9) if hi else np.nan
    return dict(n=len(d), peryr=len(d) / yrs, gross=g.mean() * B, net=net.mean() * B, t=nw_t(net.values), med=net.median() * B,
                hit=(net > 0).mean(), ex5=ex5 * B, net2x=(g - 2 * cost_rt).mean() * B,
                long=(d.r[d.s > 0]).mean() * B, short=(-d.r[d.s < 0]).mean() * B, nl=int((d.s > 0).sum()), ns=int((d.s < 0).sum()),
                worst=o[0] * B if len(o) else np.nan)


def fmt(name: str, s: dict) -> str:
    return (f"{name:<34} n {s['n']:5d} ({s['peryr']:5.1f}/yr, L{s['nl']}/S{s['ns']}) gross {s['gross']:+6.1f} net {s['net']:+6.1f}bp "
            f"NW t {s['t']:+5.2f} med {s['med']:+6.1f} hit {s['hit']:.0%} ex5 {s['ex5']:+6.1f} 2x {s['net2x']:+6.1f} "
            f"long {s['long']:+6.1f} short {s['short']:+6.1f} worst {s['worst']:+6.0f}")


def main() -> None:
    gspc = vts.yahoo("^GSPC")
    sx = vts.yahoo("^STOXX50E")
    spy = yahoo_ohlc("SPY")
    P(f"VT-FLOW run {pd.Timestamp.now():%Y-%m-%d %H:%M}. ^GSPC {gspc.index[0].date()}..{gspc.index[-1].date()}, "
      f"^STOXX50E {sx.index[0].date()}..{sx.index[-1].date()}, SPY {spy.index[0].date()}..{spy.index[-1].date()}")
    fu = flows(gspc)
    fe = flows(sx)
    # SPY returns aligned at signal date t (return t -> t+1); SPY dates mapped onto ^GSPC dates
    adj = spy["adjclose"]
    r_cc = adj.pct_change().shift(-1)
    ratio = adj / spy["close"]
    r_co = (spy["open"].shift(-1) * ratio.shift(-1) / adj - 1)  # close t -> open t+1 (total-return adj)
    r_oc = (spy["close"].shift(-1) / spy["open"].shift(-1) - 1)
    g_cc = gspc.pct_change().shift(-1)
    s_cc = sx.pct_change().shift(-1)
    COST = 4e-4

    variants = {(a, q): signal(fu[a], q) for a in ("A1", "A2") for q in (0.80, 0.90)}
    P("\n== Variant choice on SPY 2010-2019 (signed close->close, net 4bp RT) ==")
    best, bt = None, -9
    for k, s in variants.items():
        st = stats(s, r_cc, COST, "2010-01-01", "2019-12-31")
        P(fmt(f"{k[0]} q{k[1]:.2f}", st))
        if st["t"] > bt:
            best, bt = k, st["t"]
    P(f"CHOSEN: {best}")
    a, q = best
    sig = variants[best]
    sig_e = signal(fe[a], q)

    P("\n== JUDGE (chosen variant only) ==")
    j1 = stats(sig, r_cc, COST, "2020-01-01", "2026-11-05")
    P(fmt("J1 SPY 2020-26 close->close", j1))
    for lo, hi in (("2020-01-01", "2022-12-31"), ("2023-01-01", "2026-11-05")):
        P(fmt(f"   half {lo[:4]}-{hi[:4]}", stats(sig, r_cc, COST, lo, hi)))
    P(fmt("   J1 close->open part", stats(sig, r_co, 0.0, "2020-01-01", "2026-11-05")))
    P(fmt("   J1 open->close part", stats(sig, r_oc, 0.0, "2020-01-01", "2026-11-05")))
    j2 = stats(sig_e, s_cc, 6e-4, "2010-01-01", "2026-11-05")
    P(fmt("J2 STOXX50E 2010-26 (own signal)", j2))
    for lo, hi in (("2010-01-01", "2019-12-31"), ("2020-01-01", "2026-11-05")):
        P(fmt(f"   STOXX {lo[:4]}-{hi[:4]}", stats(sig_e, s_cc, 6e-4, lo, hi)))
    p1 = stats(sig, g_cc, 0.0, "1950-01-01", "1999-12-31")
    P(fmt("P1 ^GSPC 1950-99 placebo (gross)", p1))
    for lo, hi in (("1950-01-01", "1974-12-31"), ("1975-01-01", "1999-12-31")):
        P(fmt(f"   GSPC {lo[:4]}-{hi[:4]}", stats(sig, g_cc, 0.0, lo, hi)))
    P(fmt("desc SPY 1993-2009", stats(sig, r_cc, COST, "1993-01-01", "2009-12-31")))
    P(fmt("desc ^GSPC 2000-2009", stats(sig, g_cc, 0.0, "2000-01-01", "2009-12-31")))

    # G5 regression with controls on J1
    d = pd.DataFrame({"y": r_cc, "s": sig, "r0": fu["lr"], "r5": fu["lr"].rolling(5).sum()}).dropna().loc["2020-01-01":"2026-11-05"]
    X = np.column_stack([np.ones(len(d)), d.s, d.r0, d.r5])
    beta, *_ = np.linalg.lstsq(X, d.y.values, rcond=None)
    e = d.y.values - X @ beta
    XtX = np.linalg.inv(X.T @ X)
    n = len(e)
    S = (X * e[:, None]).T @ (X * e[:, None]) / n
    for k in range(1, 6):
        G = (X[k:] * e[k:, None]).T @ (X[:-k] * e[:-k, None]) / n
        S += (1 - k / 6) * (G + G.T)
    se = np.sqrt(np.diag(n * XtX @ S @ XtX))
    P(f"\nG5 J1 OLS r(t+1) ~ signal + r_t + r_5d (NW5): signal coef {beta[1]*B:+.1f}bp t {beta[1]/se[1]:+.2f}; "
      f"r_t coef {beta[2]:+.3f} t {beta[2]/se[2]:+.2f}; r5 coef {beta[3]:+.3f} t {beta[3]/se[3]:+.2f}")

    # placebo: circular shifts of the signal series in J1
    sj = sig.loc["2020-01-01":"2026-11-05"]
    rj = r_cc.reindex(sj.index)
    rng = np.random.default_rng(7)
    obs = (sj * rj)[sj != 0].mean()
    ps = []
    for _ in range(500):
        k = int(rng.integers(20, len(sj) - 20))
        ss = pd.Series(np.roll(sj.values, k), index=sj.index)
        ps.append((ss * rj)[ss != 0].mean())
    P(f"Placebo J1: observed gross {obs*B:+.1f}bp; circular-shift rank {np.mean(np.array(ps) < obs):.1%} (500 shifts), "
      f"shift mean {np.mean(ps)*B:+.1f} sd {np.std(ps)*B:.1f}")

    # Gates
    g1 = j1["net"] >= 10 and j1["t"] >= 2.0
    g2 = j2["gross"] > 0 and j2["t"] >= 1.5
    g3 = p1["gross"] <= 0.5 * j1["gross"]
    hs = [stats(sig, r_cc, COST, lo, hi)["net"] for lo, hi in (("2020-01-01", "2022-12-31"), ("2023-01-01", "2026-11-05"))]
    g4 = j1["med"] > 0 and j1["ex5"] > 0 and j1["net2x"] > 0 and min(hs) > 0
    g5 = beta[1] / se[1] >= 1.5
    ceil_ls = j1["peryr"] * j1["net"] / B * 0.5 * 100
    ceil_l = j1["nl"] / (j1["n"] / j1["peryr"]) * (j1["long"] / B - COST) * 0.5 * 100 if j1["nl"] else 0.0
    g6 = ceil_ls >= 8
    P(f"\nGATES: G1 {g1} G2 {g2} G3 {g3} G4 {g4} G5 {g5} G6 {g6}")
    P(f"Ceiling J1 (50% capture, 100% of account): long+short {ceil_ls:+.1f}pp/yr; long-only (Roth) {ceil_l:+.1f}pp/yr. "
      f"Same % at $2.3k/$10k/$25k (3 SPY shares at $2.3k ~10% cash drag); $100k+ unconstrained.")
    verdict = "PASS" if all([g1, g2, g3, g4, g5, g6]) else ("PASS-SMALL" if all([g1, g2, g3, g4, g5]) else "KILL")
    P(f"VERDICT: {verdict}")

    # today
    P("\n== Today (descriptive) ==")
    t = fu.dropna().tail(3)
    for dt, row in t.iterrows():
        P(f"{dt.date()} ^GSPC r {np.expm1(row.lr):+.2%}  E {row.E:.3f}  A1 dE {row.A1:+.4f}  A2 roll-off dE {row.A2:+.4f}  "
          f"signal({a},q{q}) {sig.get(dt, np.nan):+.0f}")
    lr = fu["lr"]
    last = lr.index[-1]
    pos = len(lr) - 1
    P("Drop-out calendar (returns leaving the 21d / 63d windows over the next 10 sessions):")
    for h in range(1, 11):
        d21 = lr.iloc[pos + h - 21] if pos + h - 21 >= 0 else np.nan
        d63 = lr.iloc[pos + h - 63]
        P(f"  session +{h:2d}: drops 21d {lr.index[pos+h-21].date()} {np.expm1(d21):+.2%} | 63d {lr.index[pos+h-63].date()} {np.expm1(d63):+.2%}")
    rv21 = lr.tail(21).std() * np.sqrt(252)
    rv63 = lr.tail(63).std() * np.sqrt(252)
    P(f"As of {last.date()}: RV21 {rv21:.1%} RV63 {rv63:.1%} -> modeled exposure {min(CAP, TARGET/max(rv21, rv63)):.2f}x")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
