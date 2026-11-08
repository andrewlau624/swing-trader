"""INTL-GAP (N 1150): fade the open-cross residual of Asian single-country ETFs vs their (closed) home index.

Pre-registered in research/drafts/round1_prose.md (XASSET-TZ branch). Rule frozen there; one look.
Signal r = ETF gap ln(O_t/C_{t-1}) minus home index close-to-close ln(I_t/I_prev) (home close known before 09:30 ET).
Trade the official open cross -> close cross on day t, x = -sign(r), equal weight across eligible pairs.
Data: free Yahoo daily via vt_flow.yahoo_ohlc (cache redirected to data/research/intl_gap/).
Output data/research/program/intl_gap_out.txt.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vt_flow  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
vt_flow.CACHE = ROOT / "data/research/intl_gap"
vt_flow.CACHE.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data/research/program/intl_gap_out.txt"
PAIRS = {"EWJ": "^N225", "EWH": "^HSI", "EWY": "^KS11", "EWT": "^TWII", "EWA": "^AXJO"}
COST = 0.0003  # per side
J0, J1 = "2000-01-01", "2015-12-31"
L: list[str] = []


def home_index(sym: str) -> pd.DataFrame:
    """Yahoo daily for a foreign index dated in the EXCHANGE's local calendar.

    vt_flow.yahoo_ohlc converts timestamps to New York and normalises; Yahoo stamps Asian bars at the local open
    (09:00 JST = 19:00/20:00 ET the previous day), so that shifts every Asian bar back one date (Tohoku -6.4% shows
    on Sunday 2011-03-13) and the "home close dated t" becomes the close AFTER the US session t: lookahead.
    """
    import json, urllib.parse, urllib.request
    f = vt_flow.CACHE / f"local_{sym.replace('^', '')}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           f"?period1=0&period2={int(pd.Timestamp.now().timestamp())}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)["chart"]["result"][0]
    tz = res["meta"]["exchangeTimezoneName"]
    idx = (pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None)
           .astype("datetime64[ns]"))
    df = pd.DataFrame({"close": res["indicators"]["quote"][0]["close"]}, index=idx).dropna()
    df = df[~df.index.duplicated(keep="last")]
    df.to_parquet(f)
    return df


def P(s: str = "") -> None:
    print(s)
    L.append(s)


def nw_t(x: pd.Series, lags: int = 5) -> float:
    x = x.dropna().to_numpy(); n = len(x)
    if n < 20:
        return float("nan")
    e = x - x.mean(); v = e @ e / n
    for k in range(1, lags + 1):
        v += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / np.sqrt(v / n))


def legs() -> pd.DataFrame:
    spy = vt_flow.yahoo_ohlc("SPY")
    spy_oc = np.log(spy["close"] / spy["open"])
    rows, bug = [], []
    for etf, idx in PAIRS.items():
        e = vt_flow.yahoo_ohlc(etf); i = home_index(idx)
        e = e[e.index >= "1999-01-01"]; ic = i["close"]
        prev_us = e.index.to_series().shift(1)
        # dividend days: adjclose/close ratio changes -> drop (raw gap contains the ex-drop)
        ratio = (e["adjclose"] / e["close"]); exday = (ratio / ratio.shift(1) - 1).abs() > 1e-4
        g = np.log(e["open"] / e["close"].shift(1))
        oc = np.log(e["close"] / e["open"])
        ii = ic.index
        pos = ii.searchsorted(e.index)  # index of first Asian date >= t
        has_t = (pos < len(ii)) & (ii[np.minimum(pos, len(ii) - 1)] == e.index)
        prev_a = pd.Series(pd.NaT, index=e.index); f = pd.Series(np.nan, index=e.index)
        ok = has_t & (pos >= 1)
        prev_a[ok] = ii[pos[ok] - 1]
        f[ok] = np.log(ic.iloc[pos[ok]].to_numpy() / ic.iloc[pos[ok] - 1].to_numpy())
        same_prev = prev_a == prev_us
        stale = (e["open"] == e["close"].shift(1)) | (g.abs() > 0.15)
        bug.append((etf, int(stale.sum()), int(len(e))))
        d = pd.DataFrame({"etf": etf, "g": g, "f": f, "oc": oc, "spy_oc": spy_oc.reindex(e.index)})
        d = d[ok & same_prev & ~exday & ~stale & d["f"].abs().lt(0.15)].dropna()
        rows.append(d)
    for b in bug:
        P(f"data check {b[0]}: dropped O==C_prev or |gap|>15%: {b[1]} of {b[2]} days")
    df = pd.concat(rows).reset_index().rename(columns={"index": "date"})
    df["r"] = df["g"] - df["f"]
    df["x"] = -np.sign(df["r"])
    df["raw"] = df["x"] * df["oc"]
    df["hed"] = df["x"] * (df["oc"] - df["spy_oc"])
    return df


def book(df: pd.DataFrame, col: str, cost: float) -> pd.Series:
    c = 2 * cost if col == "raw" or col == "long" else 4 * cost  # hedged leg trades SPY too
    return df.groupby("date")[col].mean() - c


def report(name: str, s: pd.Series) -> dict:
    s = s.dropna(); top = s.sort_values(ascending=False)
    ex5 = s.drop(top.index[:5]).mean()
    rng = np.random.default_rng(0)
    return dict(name=name, n=len(s), mean=s.mean() * 1e4, t=nw_t(s), med=s.median() * 1e4, hit=(s > 0).mean(),
                ex5=ex5 * 1e4, ann=s.mean() * 252 * 100)


def fmt(d: dict) -> str:
    return (f"{d['name']:<34} n {d['n']:>5}  mean {d['mean']:+6.2f}bp  NW t {d['t']:+5.2f}  med {d['med']:+6.2f}  "
            f"hit {d['hit']:.2f}  ex-top5 {d['ex5']:+6.2f}  ann {d['ann']:+6.1f}%")


def placebo_p(df: pd.DataFrame, obs: float, k: int = 500) -> float:
    rng = np.random.default_rng(1); hits = 0
    for _ in range(k):
        sgn = rng.choice([-1.0, 1.0], size=len(df))
        m = (pd.Series(sgn * df["oc"].to_numpy(), index=df["date"]).groupby(level=0).mean() - 2 * COST).mean()
        hits += m >= obs
    return hits / k


def main() -> None:
    P("INTL-GAP (N 1150) fade open-cross residual vs home index, open->close, Asian ETFs; one look (home dates = exchange-local; the NY-dated first run was a lookahead artifact, see prose)")
    df = legs()
    df["long"] = np.where(df["r"] < 0, df["oc"], np.nan)
    P(f"legs {len(df)}  corr(r, oc) all {df['r'].corr(df['oc']):+.3f}")
    J = df[(df.date >= J0) & (df.date <= J1)]
    P(f"corr(r, oc) judge {J['r'].corr(J['oc']):+.3f}  corr(g, f) judge {J['g'].corr(J['f']):+.3f}")
    P("")
    P("JUDGE 2000-15 (3bp/side):")
    res = {}
    for col in ("raw", "hed", "long"):
        res[col] = report(f"judge {col}", book(J, col, COST)); P(fmt(res[col]))
    for k in (2, 3):
        P(fmt(report(f"judge raw cost x{k}", book(J, "raw", COST * k))))
    for a, b in (("2000-01-01", "2007-12-31"), ("2008-01-01", "2015-12-31"), ("2016-01-01", "2026-12-31")):
        S = df[(df.date >= a) & (df.date <= b)]
        P(fmt(report(f"raw {a[:4]}-{b[:4]}", book(S, "raw", COST))))
    for a, b, nm in (("2008-01-01", "2008-12-31", "2008"), ("2018-10-01", "2018-12-31", "2018Q4"),
                     ("2020-01-01", "2020-12-31", "2020"), ("2022-01-01", "2022-12-31", "2022")):
        S = df[(df.date >= a) & (df.date <= b)]
        P(fmt(report(f"stress {nm} raw", book(S, "raw", COST))))
    for etf in PAIRS:
        S = J[J.etf == etf]
        P(fmt(report(f"judge {etf} raw", book(S, "raw", COST))))
    jr = book(J, "raw", COST).mean()
    pp = placebo_p(J, jr)
    r = res["raw"]
    halves = [book(df[(df.date >= a) & (df.date <= b)], "raw", COST).mean() for a, b in
              (("2000-01-01", "2007-12-31"), ("2008-01-01", "2015-12-31"))]
    ceil10k = r["ann"] * 0.5
    gate = {"mean>0 & t>=2": r["mean"] > 0 and r["t"] >= 2, "halves>0": min(halves) > 0,
            "2x cost>0": book(J, "raw", 2 * COST).mean() > 0, "ex-top5>0": r["ex5"] > 0, "median>0": r["med"] > 0,
            "placebo p<.05": pp < 0.05, "ceiling>=8pp": ceil10k >= 8}
    P("")
    P(f"placebo p {pp:.3f}; $10k ceiling at 50% capture {ceil10k:+.1f}pp/yr (same % at $2.3k/$25k; 5 ETFs $15-80)")
    P("GATE " + "  ".join(f"{k}:{'T' if v else 'F'}" for k, v in gate.items()))
    P("VERDICT " + ("PASS" if all(gate.values()) else "KILL"))
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
