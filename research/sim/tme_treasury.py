"""Study TME: Treasury month-end duration extension, one look on 2002-15 (pre-registered in round1_prose.md, N 813 -> 814,
commit 003e176).

    PYTHONPATH=. .venv/bin/python -m research.sim.tme_treasury fetch      # Yahoo daily bars TLT/IEF/SHY/^IRX (no returns)
    PYTHONPATH=. .venv/bin/python -m research.sim.tme_treasury validate   # Yahoo vs Alpaca SIP closes 2016-26 (prices only)
    PYTHONPATH=. .venv/bin/python -m research.sim.tme_treasury run        # the one look (refuses a second run)

Rule TME1: buy TLT at the close of session T-3, sell at the close of T (T = the month's last session). AR_m = R_w - 3 x mean
daily TLT return over the month's other sessions. Net = AR - 2 x 2bp. Output data/research/program/tme_out.txt.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import datetime as dt

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/tme"
OUT = ROOT / "data/research/program/tme_out.txt"
VALID = D / "validate_passed.json"
DONE = D / "run_done.json"
SYMS = ["TLT", "IEF", "SHY", "^IRX"]
J0, J1 = "2002-08-01", "2015-12-31"
SUB = [("2002-08", "2008-12"), ("2009-01", "2015-12")]
COST = 2.0  # bp per side


def fetch_px(t: str, start: str = "2002-07-01") -> pd.DataFrame:
    p1 = int(pd.Timestamp(start).timestamp()); p2 = int(pd.Timestamp.now().timestamp())
    u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={p2}"
         f"&interval=1d&events=div,split")
    r = json.loads(subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", u], capture_output=True, text=True,
                                  check=True).stdout)
    res = r["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    adj = res["indicators"]["adjclose"][0]["adjclose"] if "adjclose" in res["indicators"] else q["close"]
    df = pd.DataFrame({"close": q["close"], "adjclose": adj},
                      index=pd.to_datetime(res["timestamp"], unit="s", utc=True)
                      .tz_convert("America/New_York").tz_localize(None).normalize())
    df.index.name = "date"
    return df.dropna(subset=["close"])


def fname(t: str) -> pathlib.Path:
    return D / f"px_{t.replace('^', '')}.csv"


def load(t: str) -> pd.DataFrame:
    return pd.read_csv(fname(t), parse_dates=["date"]).set_index("date")


def fetch() -> None:
    D.mkdir(parents=True, exist_ok=True)
    for t in SYMS:
        df = fetch_px(t)
        df.to_csv(fname(t))
        print(f"{t}: {len(df)} rows {df.index[0].date()} .. {df.index[-1].date()}")


def validate() -> bool:
    """Prices only: Yahoo closes vs Alpaca SIP raw closes on 2016-26 (no window returns computed)."""
    a = pd.read_parquet(ROOT / "data/research/night/etf_daily.parquet")
    a["date"] = pd.to_datetime(a["timestamp"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    ok = True
    for t in ["TLT", "IEF", "SHY"]:
        y = load(t)
        s = a[a.symbol == t].set_index("date")["close"]
        j = pd.concat([y["close"], y["adjclose"], s], axis=1, keys=["y", "yadj", "a"]).dropna()
        if j.empty:
            print(f"{t}: no Alpaca overlap -> FAIL"); ok = False; continue
        # The Alpaca file is dividend-adjusted (raw/adjusted ratio drifts by the cumulative dividends), so the
        # like-for-like check is daily returns of Yahoo adjclose vs Alpaca's adjusted close.
        lvl = (j.y / j.a - 1) * 1e4
        print(f"{t}: Yahoo raw close / Alpaca close - 1: first {lvl.iloc[0]:+.0f}bp, last {lvl.iloc[-1]:+.0f}bp "
              f"(drift = Alpaca file is dividend-adjusted)")
        d = (j.yadj.pct_change() - j.a.pct_change()).dropna().abs() * 1e4
        med = float(d.median())
        good = med <= 2.0
        ok &= good
        print(f"   daily-return agreement, Yahoo adjclose vs Alpaca: overlap {len(d)} days, median |diff| {med:.2f}bp, "
              f"p95 {d.quantile(.95):.2f}bp, max {d.max():.1f}bp -> {'PASS' if good else 'FAIL'}")
        yy = load(t)
        jw = yy.loc[J0:J1]
        print(f"   judge-window rows {len(jw)} ({jw.index[0].date()} .. {jw.index[-1].date()}), "
              f"dup dates {int(yy.index.duplicated().sum())}, weekend rows {int((yy.index.dayofweek >= 5).sum())}")
    irx = load("^IRX").loc[J0:J1]
    print(f"^IRX: judge-window rows {len(irx)}")
    if ok:
        VALID.write_text(json.dumps({"ts": dt.datetime.now().isoformat(timespec="seconds")}))
    print("VALIDATE:", "PASSED" if ok else "FAILED -> DATA-LIMITED")
    return ok


def month_table(px: pd.Series, cash: pd.Series) -> pd.DataFrame:
    """One row per month: window return T-3 close -> T close, AR vs the month's other sessions, excess over cash."""
    r = px.pct_change().dropna()
    rows = []
    for m, g in r.groupby(r.index.to_period("M")):
        if len(g) < 8:
            continue
        w = g.iloc[-3:]                      # returns on T-2, T-1, T = close(T-3) -> close(T)
        rest = g.iloc[:-3]
        rw = float(np.prod(1 + w.values) - 1)
        cw = float(cash.reindex(w.index).ffill().fillna(0).sum())
        rows.append({"month": m, "rw": rw, "ar": rw - 3 * float(rest.mean()), "xcash": rw - cw,
                     "rest_mean": float(rest.mean()), "year": m.year, "mon": m.month})
    return pd.DataFrame(rows).set_index("month")


def tstat(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else float("nan")


def nw_t(x: np.ndarray, lags: int = 3) -> float:
    x = np.asarray(x, float); n = len(x); e = x - x.mean()
    v = e @ e / n
    for k in range(1, lags + 1):
        v += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / np.sqrt(v / n))


def bp(x: float) -> str:
    return f"{x * 1e4:+.1f}bp"


def run(force: bool = False) -> str:
    if not VALID.exists():
        raise SystemExit("validate has not passed")
    if DONE.exists() and not force:
        raise SystemExit(f"already run ({DONE.read_text()}); one look only")
    L = []
    irx = load("^IRX")["close"] / 100 / 252
    tabs = {t: month_table(load(t)["adjclose"].loc["2002-07-01":J1], irx) for t in ["TLT", "IEF", "SHY"]}
    T = tabs["TLT"].loc[pd.Period(J0[:7], "M"):]
    c = 2 * COST / 1e4
    net, net2 = T.ar - c, T.ar - 2 * c
    L.append(f"Study TME (one look) {dt.datetime.now():%Y-%m-%d %H:%M}  TLT close(T-3) -> close(T), months {T.index[0]}..{T.index[-1]}")
    L.append(f"n months {len(T)}")
    L.append(f"gross window R_w      mean {bp(T.rw.mean())}  median {bp(T.rw.median())}  t {tstat(T.rw):.2f}")
    L.append(f"excess over cash      mean {bp(T.xcash.mean())}  t {tstat(T.xcash):.2f}")
    L.append(f"AR gross              mean {bp(T.ar.mean())}  t {tstat(T.ar):.2f}")
    L.append(f"AR net (2bp/side)     mean {bp(net.mean())}  median {bp(net.median())}  t {tstat(net):.2f}  NW3 t {nw_t(net.values):.2f}  hit {100 * (net > 0).mean():.0f}%")
    ex5 = net.drop(net.nlargest(5).index)
    L.append(f"AR net ex-best-5      mean {bp(ex5.mean())}  t {tstat(ex5):.2f}")
    L.append(f"AR net at 2x cost     mean {bp(net2.mean())}  t {tstat(net2):.2f}")
    subs = []
    for a, b in SUB:
        s = net.loc[pd.Period(a, "M"):pd.Period(b, "M")]
        subs.append(s.mean())
        L.append(f"  sub {a}..{b}: n {len(s)}  mean {bp(s.mean())}  t {tstat(s):.2f}")
    yr = net.groupby(T.year).mean()
    L.append("  per year: " + "  ".join(f"{y} {v * 1e4:+.0f}" for y, v in yr.items()))
    ex08 = net.drop([p for p in net.index if p.year == 2008 and p.month >= 9])
    L.append(f"  ex Sep-Dec 2008: mean {bp(ex08.mean())}  t {tstat(ex08):.2f}")
    top = net.nlargest(5)
    L.append("  best 5 months: " + ", ".join(f"{p} {v * 1e4:+.0f}" for p, v in top.items()) +
             f"  (share of total {top.sum() / net.sum() * 100:.0f}%)" if net.sum() > 0 else "  best 5: total <= 0")

    # gates
    g = {"mean>0 & t>=2": net.mean() > 0 and tstat(net) >= 2,
         "median>0": net.median() > 0,
         "ex-best-5>0": ex5.mean() > 0,
         "both subperiods>0": all(s > 0 for s in subs),
         "years>=60% positive": (yr > 0).mean() >= 0.6,
         "2x cost>0": net2.mean() > 0}
    L.append("GATES: " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in g.items()))
    m, t = net.mean() * 1e4, tstat(net)
    failed = [k for k, v in g.items() if not v]
    if not failed:
        label = "VALIDATED" if m >= 25 else "PROMISING" if m >= 10 else "SMALL / NON-SCALABLE"
    elif failed == ["ex-best-5>0"]:
        label = "SMALL / NON-SCALABLE (carried by < 5 months)"
    elif m <= 0 or t < 1:
        label = "REJECTED"
    else:
        label = "REJECTED for adoption (WEAK: t in [1,2) or a robustness gate failed)"
    L.append(f"VERDICT: {label}   (mean net AR {m:+.1f}bp/month, t {t:.2f})")

    # identification (reported)
    L.append("\nIDENTIFICATION (reported, not gates)")
    for k in ["TLT", "IEF", "SHY"]:
        x = tabs[k].loc[pd.Period(J0[:7], "M"):]
        L.append(f"  (a) {k}: AR gross mean {bp(x.ar.mean())} t {tstat(x.ar):.2f}; excess over cash {bp(x.xcash.mean())}")
    px = load("TLT")["adjclose"].loc["2002-07-01":"2016-01-31"]
    r = px.pct_change().dropna()
    prof = {k: [] for k in range(-5, 3)}
    months = r.groupby(r.index.to_period("M"))
    idx = list(r.index)
    for mm, gg in months:
        if mm < pd.Period(J0[:7], "M") or mm > pd.Period("2015-12", "M") or len(gg) < 8:
            continue
        base = float(gg.iloc[:-3].mean())
        last = idx.index(gg.index[-1])
        for k in range(-5, 3):
            j = last + k
            if 0 <= j < len(idx):
                prof[k].append(float(r.iloc[j]) - base)
    L.append("  (b) abnormal daily return by session (T+0 = last session): " +
             "  ".join(f"T{k:+d} {np.mean(v) * 1e4:+.1f}bp(t {tstat(v):.1f})" for k, v in prof.items()))
    ref = T[T.mon.isin([2, 5, 8, 11])].ar - c
    oth = T[~T.mon.isin([2, 5, 8, 11])].ar - c
    L.append(f"  (c) refunding months net AR {bp(ref.mean())} (n {len(ref)}, t {tstat(ref):.2f}) vs others "
             f"{bp(oth.mean())} (n {len(oth)}, t {tstat(oth):.2f})")
    yr_tot = (1 + load("TLT")["adjclose"].loc[J0:J1].pct_change().dropna()).prod() - 1
    win_tot = (1 + T.rw).prod() - 1
    L.append(f"  (d) TLT total return over the judge {yr_tot * 100:.0f}%; compounded in the windows only {win_tot * 100:.0f}% "
             f"(windows = ~{3 * 12 / 252 * 100:.0f}% of sessions)")

    # economics
    xs_net = T.xcash - c
    L.append("\nECONOMICS (excess over cash, net 2bp/side; 12 round trips/yr, 3 sessions each)")
    L.append(f"  per window {bp(xs_net.mean())}; per year at 100% deployment {xs_net.mean() * 12 * 100:+.2f}%")
    for eq in (2300, 10000, 25000, 100000):
        for share, lab in ((0.6, "taxable idle 60%"), (1.0, "Roth 100%")):
            L.append(f"  ${eq:>7,} {lab:16s}: {xs_net.mean() * 12 * share * eq:+8.0f} $/yr")
    L.append("  capacity: TLT ADV ~$1B+ in the 2010s; account size never binds; the closing auction is the venue.")

    text = "\n".join(L)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text + "\n")
    h = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
    DONE.write_text(json.dumps({"ts": dt.datetime.now().isoformat(timespec="seconds"), "git": h, "verdict": label}))
    return text


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch":
        fetch()
    elif cmd == "validate":
        sys.exit(0 if validate() else 1)
    elif cmd == "run":
        print(run(force="--force" in sys.argv))
    else:
        raise SystemExit(__doc__)
