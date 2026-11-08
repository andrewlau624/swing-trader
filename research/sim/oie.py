"""Study OIE (N 1140-1142): option-income ETF ex-date flow (pre-registered in research/drafts/round1_prose.md).

N 1140 OIE-CAP: close T-1 -> open T (+div). N 1141 OIE-POST: close T -> close T+3. N 1142 OIE-PRE: close T-4 -> close T-1.
Excess = pnl minus the fund's own mean return over same-shape windows in T-35..T-5 with no ex-date inside.
Data: Yahoo chart API (raw split-adjusted OHLC, dividend events). Cache data/research/oie/.

    python3 -I research/sim/oie.py
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import time
import urllib.request

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/oie"
OUT = ROOT / "data/research/program/oie_out.txt"
UA = {"User-Agent": "Mozilla/5.0 (research)"}
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?period1=946684800&period2=1793000000&interval=1d&events=div"
YM = ("TSLY OARK APLY NVDY AMZY FBY GOOY CONY NFLY DISO MSFO XOMO JPMO AMDY PYPY SQY MRNY AIYY YMAX YMAG ULTY MSTY SNOY "
      "BABO TSMY PLTY MARO CVNY HOOY SMCY LFGY GPTY QQQY IWMY JEPY XDTE QDTE RDTE SPYI QQQI").split()
OLD = "QYLD XYLD RYLD JEPI JEPQ".split()
MINY, COST = 0.003, 0.0005


def fetch(sym: str) -> pd.DataFrame | None:
    f = CACHE / f"{sym}.json"
    if not f.exists():
        for i in range(3):
            try:
                raw = urllib.request.urlopen(urllib.request.Request(URL.format(sym), headers=UA), timeout=30).read()
                f.write_bytes(raw)
                break
            except Exception:
                time.sleep(1 + i)
        else:
            return None
    r = json.loads(f.read_text())["chart"]["result"][0]
    off = r["meta"].get("gmtoffset", -14400)
    q = r["indicators"]["quote"][0]
    if "open" not in q or not r.get("timestamp"):
        return None
    d = pd.DataFrame({"open": q["open"], "close": q["close"], "vol": q["volume"]},
                     index=[dt.datetime.fromtimestamp(t + off, dt.UTC).date() for t in r["timestamp"]]).dropna()
    d = d[(d.open > 0) & (d.close > 0)]
    d["div"] = 0.0
    for v in (r.get("events", {}) or {}).get("dividends", {}).values():
        day = dt.datetime.fromtimestamp(v["date"] + off, dt.UTC).date()
        if day in d.index:
            d.loc[day, "div"] += v["amount"]
    return d


def events(sym: str, d: pd.DataFrame) -> list[dict]:
    o, c, dv = d.open.to_numpy(), d.close.to_numpy(), d["div"].to_numpy()
    isex = dv > 0
    ovn = np.r_[np.nan, o[1:] / c[:-1] - 1]          # close t-1 -> open t (no div)
    r3f = np.r_[c[3:] / c[:-3] - 1, [np.nan] * 3]     # close t -> close t+3
    rows = []
    for t in np.flatnonzero(isex):
        if t < 40 or t + 3 >= len(c):
            continue
        y = dv[t] / c[t - 1]
        if y < MINY or y > 0.25:
            continue
        exwin = lambda a, b: isex[a:b + 1].any()  # noqa: E731
        # placebo nights T-35..T-5 not ex nights
        pn = [ovn[k] for k in range(t - 35, t - 4) if not isex[k]]
        # 3-session windows close s -> close s+3, s in T-35..T-8, no ex-date in (s, s+3]
        p3 = [r3f[s] for s in range(t - 35, t - 7) if not exwin(s + 1, s + 3)]
        cap = (o[t] + dv[t]) / c[t - 1] - 1
        post = c[t + 3] / c[t] - 1 if not exwin(t + 1, t + 3) else np.nan
        pre = c[t - 1] / c[t - 4] - 1 if not exwin(t - 3, t - 1) else np.nan
        rows.append(dict(
            sym=sym, date=pd.Timestamp(d.index[t]), y=y, dollar=c[t - 1] * d.vol.iloc[t - 1],
            cap=cap, cap_x=cap - np.nanmean(pn) if pn else np.nan,
            post=post, post_x=post - np.nanmean(p3) if p3 else np.nan,
            pre=pre, pre_x=pre - np.nanmean(p3) if p3 else np.nan,
            exday=c[t] / o[t] - 1))
    return rows


def ct(x: pd.Series, g: pd.Series) -> tuple[float, float]:
    df = pd.DataFrame({"x": x.to_numpy(float), "g": g.to_numpy()}).dropna()
    n = len(df)
    if n < 5:
        return np.nan, 0.0
    m = df.x.mean()
    s = (df.x - m).groupby(df.g).sum().to_numpy()
    se = np.sqrt(len(s) / max(len(s) - 1, 1) * (s ** 2).sum() / n ** 2)
    return m, m / se if se > 0 else 0.0


def judge(ev: pd.DataFrame, col: str, mid: str, lines: list[str], tag: str, old: pd.DataFrame | None = None):
    e = ev.dropna(subset=[col])
    m, t = ct(e[col], e.date)
    a, b = e[e.date < mid][col].mean(), e[e.date >= mid][col].mean()
    med = e[col].median()
    ex5 = e[col].drop(e[col].nlargest(5).index).mean()
    hit = (e[col] > 0).mean()
    chk = {"t>=2": t >= 2 and m > 0, "halves": a > 0 and b > 0, "median": med > 0, "ex-top5": ex5 > 0, ">10bp": m > 0.001}
    if old is not None:
        mo, to = ct(old.dropna(subset=[col])[col], old.dropna(subset=[col]).date)
        chk["old-sign"] = mo > 0
        oldtxt = f" | 2014-22 set n {old[col].notna().sum()} {mo*1e4:+.1f}bp t {to:+.2f}"
    else:
        oldtxt = ""
    v = "PASS" if all(chk.values()) else ("FAIL" if (m <= 0 or t < 1) else "WEAK")
    lines.append(f"{tag}: n {len(e)} dates {e.date.nunique()} excess {m*1e4:+.1f}bp t {t:+.2f} median {med*1e4:+.1f}bp "
                 f"hit {hit:.0%} ex-top5 {ex5*1e4:+.1f}bp | halves {a*1e4:+.1f} / {b*1e4:+.1f}{oldtxt}")
    lines.append(f"   checks {chk} -> {v}")
    return v


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    got = []
    for s in YM + OLD:
        d = fetch(s)
        if d is None or len(d) < 60:
            continue
        got.append(s)
        rows += events(s, d)
    ev = pd.DataFrame(rows)
    L = [f"OIE (N 1140-1142), Yahoo daily, fetched {len(got)}/{len(YM + OLD)}: {' '.join(got)}",
         f"events y>={MINY:.1%}: {len(ev)}; by year: " + " ".join(f"{k}:{v}" for k, v in ev.date.dt.year.value_counts().sort_index().items())]
    prim = ev[(ev.date >= "2023-01-01") & (ev.date < "2026-11-01")]
    old = ev[ev.sym.isin(["QYLD", "XYLD", "RYLD", "JEPI"]) & (ev.date >= "2014-01-01") & (ev.date < "2023-01-01")]
    L.append(f"primary 2023-01..2026-10: n {len(prim)}, {prim.sym.nunique()} funds, distinct ex-dates {prim.date.nunique()}, "
             f"median yield {prim.y.median():.2%}, median prior-day $vol {prim.dollar.median()/1e6:.2f}M")
    for col, tag in (("cap_x", "N1140 OIE-CAP close T-1 -> open T +div, excess"), ("post_x", "N1141 OIE-POST close T -> close T+3, excess"),
                     ("pre_x", "N1142 OIE-PRE close T-4 -> close T-1, excess")):
        judge(prim, col, "2025-01-01", L, tag, old)
    L.append("reported, not judged:")
    for col in ("cap", "post", "pre", "exday"):
        L.append(f"   raw {col}: mean {prim[col].mean()*1e4:+.1f}bp median {prim[col].median()*1e4:+.1f}bp")
    for lo, hi in ((0.003, 0.01), (0.01, 0.02), (0.02, 0.05), (0.05, 0.25)):
        s = prim[(prim.y >= lo) & (prim.y < hi)]
        L.append(f"   yield {lo:.1%}-{hi:.1%}: n {len(s)} cap_x {s.cap_x.mean()*1e4:+.1f}bp (med {s.cap_x.median()*1e4:+.1f}) "
                 f"post_x {s.post_x.mean()*1e4:+.1f} pre_x {s.pre_x.mean()*1e4:+.1f}")
    for y, s in prim.groupby(prim.date.dt.year):
        L.append(f"   {y}: n {len(s)} cap_x {s.cap_x.mean()*1e4:+.1f} post_x {s.post_x.mean()*1e4:+.1f} pre_x {s.pre_x.mean()*1e4:+.1f}")
    # cost shock and capacity for cap rule: daily equal-weight across same-date events
    dly = prim.dropna(subset=["cap_x"]).groupby("date").cap_x.mean()
    L.append(f"   cap_x date-EW: {len(dly)} dates mean {dly.mean()*1e4:+.1f}bp; net of 5bp RT {(dly.mean()-COST)*1e4:+.1f}, "
             f"15bp RT shock {(dly.mean()-3*COST)*1e4:+.1f}; dates/yr ~{len(dly)/3.83:.0f}")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
