"""Study RB6040: month-end 60/40 rebalancing pressure as a SPY/IEF volatility-neutral relative-value trade
(pre-registered round1_prose.md, N 816 -> 817, commit e2c4aed). One look on 2002-08..2015-12.

    PYTHONPATH=. .venv/bin/python -m research.sim.rb6040 fetch      # Yahoo total-return daily bars (no returns computed)
    PYTHONPATH=. .venv/bin/python -m research.sim.rb6040 validate   # daily-return agreement vs Alpaca SIP 2016-26
    PYTHONPATH=. .venv/bin/python -m research.sim.rb6040 run        # the one look (refuses a second run)

Implementation note fixed before the look: IEF starts 2002-07-30, so the 60-session vol window uses the sessions
available when >= 20 (else the month is skipped); stated in the output.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

from .tme_treasury import fetch_px, nw_t, tstat

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/rb6040"
OUT = ROOT / "data/research/program/rb6040_out.txt"
VALID, DONE = D / "validate_passed.json", D / "run_done.json"
SYMS = ["SPY", "IEF", "TLT", "AGG", "IWM", "VTI"]
J0, J1 = pd.Period("2002-08", "M"), pd.Period("2015-12", "M")
SUB = [(J0, pd.Period("2008-12", "M")), (pd.Period("2009-01", "M"), J1)]
COST = {"SPY": 1.0, "IWM": 1.0, "VTI": 1.0, "IEF": 2.0, "TLT": 2.0, "AGG": 2.0}   # bp per side
AGG_SWITCH = pd.Timestamp("2021-01-14")


def load(t):
    return pd.read_csv(D / f"px_{t}.csv", parse_dates=["date"]).set_index("date")


def fetch():
    D.mkdir(parents=True, exist_ok=True)
    for t in SYMS:
        df = fetch_px(t, start="2002-01-01")
        df.to_csv(D / f"px_{t}.csv")
        print(f"{t}: {len(df)} rows {df.index[0].date()}..{df.index[-1].date()}")


def validate() -> bool:
    a = pd.read_parquet(ROOT / "data/research/night/etf_daily.parquet")
    a["date"] = pd.to_datetime(a["timestamp"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    ok = True
    for t in SYMS:
        y = load(t)["adjclose"]
        s = a[a.symbol == t].set_index("date")["close"]
        j = pd.concat([y, s], axis=1, keys=["y", "a"]).dropna()
        if len(j) < 100:
            print(f"{t}: Alpaca overlap {len(j)} days (not in the local file) -> checked only for shape")
            continue
        d = (j.y.pct_change() - j.a.pct_change()).dropna().abs() * 1e4
        good = d.median() <= 2.0
        ok &= bool(good)
        print(f"{t}: daily-return agreement {len(d)} days, median |diff| {d.median():.2f}bp p95 {d.quantile(.95):.2f}bp "
              f"-> {'PASS' if good else 'FAIL'}; weekend rows {int((y.index.dayofweek >= 5).sum())}")
    if ok:
        VALID.write_text(json.dumps({"ts": dt.datetime.now().isoformat(timespec="seconds")}))
    print("VALIDATE:", "PASSED" if ok else "FAILED -> DATA-LIMITED")
    return ok


def monthly(eq: str, bd: str, start_idx=None, rng=None, end_offset=0, length=3) -> pd.DataFrame:
    """One row per month. Default window: close(T-3) -> close(T) (end_offset = 0 means it ends on T; -1 ends on T-1,
    +2 ends on T+2 of the NEXT month's sessions). start_idx/rng: placebo (random start session in the month)."""
    pe, pb = load(eq)["adjclose"], load(bd)["adjclose"]
    ix = pe.index.intersection(pb.index)
    pe, pb = pe.loc[ix], pb.loc[ix]
    re, rb = pe.pct_change(), pb.pct_change()
    pos = pd.Series(np.arange(len(ix)), index=ix)
    rows = []
    for m, g in pos.groupby(ix.to_period("M")):
        if len(g) < 12:
            continue
        first, last = int(g.iloc[0]), int(g.iloc[-1])
        if rng is not None:
            k = int(rng.integers(first + 2, last - 5))          # window start session (decision close), sessions 3..T-6
        else:
            k = last - length + end_offset
        e = k + length
        if k - 1 < 1 or e >= len(ix) + 0 or e > len(ix) - 1:
            continue
        m0 = first - 1                                           # last close of the prior month
        if m0 < 0:
            continue
        Re, Rb = pe.iloc[k] / pe.iloc[m0] - 1, pb.iloc[k] / pb.iloc[m0] - 1
        w = 0.6 * (1 + Re) / (0.6 * (1 + Re) + 0.4 * (1 + Rb))
        s = w - 0.6
        hist = slice(max(1, k - 59), k + 1)
        if k + 1 - max(1, k - 59) < 20:
            continue
        h = float(re.iloc[hist].std() / rb.iloc[hist].std())
        win = slice(k + 1, e + 1)                                 # daily returns on sessions k+1..e
        wE, wB = float(np.prod(1 + re.iloc[win]) - 1), float(np.prod(1 + rb.iloc[win]) - 1)
        oth = [i for i in range(first, last + 1) if not (k + 1 <= i <= e)]
        aE = wE - length * float(re.iloc[oth].mean())
        aB = wB - length * float(rb.iloc[oth].mean())
        sg = -np.sign(s) if s != 0 else 0.0
        cost = 2 * (COST[eq] + COST[bd] * h) / 1e4
        rows.append({"month": m, "s": s, "h": h, "sg": sg, "raw": sg * (wE - h * wB), "ap": sg * (aE - h * aB),
                     "spread_ab": aE - h * aB, "legE": sg * aE, "legB": -sg * h * aB, "bond_unsigned": h * aB,
                     "aE": aE, "aB": aB, "cost": cost, "relgap": Re - Rb, "T": ix[last]})
    return pd.DataFrame(rows).set_index("month")


def dollar_volume(t: str) -> pd.Series:
    """Daily close x volume from the Yahoo chart API (capacity only; fetch_px keeps no volume)."""
    p1, p2 = int(pd.Timestamp("2002-01-01").timestamp()), int(pd.Timestamp.now().timestamp())
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={p2}&interval=1d"
    j = json.loads(subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", u], capture_output=True, text=True,
                                  check=True).stdout)["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    ix = pd.to_datetime(j["timestamp"], unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize()
    return (pd.Series(q["close"], index=ix) * pd.Series(q["volume"], index=ix)).dropna()


def stat(x) -> str:
    x = pd.Series(x).dropna()
    return f"n {len(x):3d} mean {x.mean() * 1e4:+6.1f}bp median {x.median() * 1e4:+6.1f} t {tstat(x):+5.2f} hit {100 * (x > 0).mean():3.0f}%"


def judge(df):
    return df.loc[(df.index >= J0) & (df.index <= J1)]


def minute_experiment(base: pd.DataFrame) -> list[str]:
    """2016-26 day-T split close(T-1)->15:00 vs 15:00->close(T), signed by the month's -sign(s). Report only."""
    from swingtrader.daily import marketdata as md
    L = []
    rows = []
    sp, ie = load("SPY")["close"], load("IEF")["close"]
    for m, r in base.loc[base.index >= pd.Period("2016-01", "M")].iterrows():
        T = r["T"]
        prev = sp.index[sp.index.get_loc(T) - 1]
        mm = md.rth_minutes(["SPY", "IEF"], T, until_hm=1500)
        if mm.empty or "SPY" not in mm.index or "IEF" not in mm.index:
            continue
        for sym, px in (("SPY", sp), ("IEF", ie)):
            p15 = float(mm.loc[sym, "close"])
            a = p15 / float(px.loc[prev]) - 1
            b = float(px.loc[T]) / p15 - 1
            sign = r["sg"] if sym == "SPY" else -r["sg"]           # predicted direction of each leg's pressure
            rows.append({"T": T, "sym": sym, "pre15": sign * a, "last": sign * b, "post": T >= AGG_SWITCH})
    X = pd.DataFrame(rows)
    if X.empty:
        return ["  natural experiment: no minute data"]
    L.append("  2021 natural experiment (day T, signed by predicted flow; pre = 2016-01..2020-12, post = 2021-02..2026-09):")
    for sym in ("IEF", "SPY"):
        for post in (False, True):
            x = X[(X.sym == sym) & (X.post == post)]
            if post:
                x = x[x["T"] >= pd.Timestamp("2021-02-01")]
            tot = x.pre15 + x["last"]
            share = x["last"].sum() / tot.sum() if tot.sum() != 0 else np.nan
            L.append(f"    {sym} {'post' if post else 'pre '}: n {len(x)}  close(T-1)->15:00 {x.pre15.mean() * 1e4:+.1f}bp "
                     f"(t {tstat(x.pre15):+.2f})  15:00->close {x['last'].mean() * 1e4:+.1f}bp (t {tstat(x['last']):+.2f})  "
                     f"last-hour share {share:+.2f}")
    return L


def run(force=False) -> str:
    if not VALID.exists():
        raise SystemExit("validate has not passed")
    if DONE.exists() and not force:
        raise SystemExit(f"already run ({DONE.read_text()}); one look only")
    L = []
    full = monthly("SPY", "IEF")
    J = judge(full)
    net, net2 = J.ap - J.cost, J.ap - 2 * J.cost
    L.append(f"Study RB6040 (one look) {dt.datetime.now():%Y-%m-%d %H:%M}  SPY/IEF vol-neutral, close(T-3)->close(T), "
             f"months {J.index[0]}..{J.index[-1]} (vol window >= 20 sessions; months skipped: "
             f"{len(pd.period_range(J0, J1, freq='M')) - len(J)})")
    L.append(f"h (IEF $ per $1 SPY) median {J.h.median():.2f}; cost per window median {J.cost.median() * 1e4:.1f}bp; "
             f"months with s>0 (sell SPY) {100 * (J.s > 0).mean():.0f}%")
    L.append(f"raw P gross        {stat(J.raw)}")
    L.append(f"AP gross           {stat(J.ap)}")
    L.append(f"AP net             {stat(net)}  NW3 t {nw_t(net.values):+.2f}")
    ex5 = net.drop(net.nlargest(5).index)
    L.append(f"AP net ex-best-5   {stat(ex5)}")
    L.append(f"AP net 2x cost     {stat(net2)}")
    subs = []
    for a, b in SUB:
        x = net.loc[(net.index >= a) & (net.index <= b)]
        subs.append(x.mean())
        L.append(f"  sub {a}..{b}: {stat(x)}")
    yr = net.groupby(net.index.year).mean()
    L.append("  per year: " + " ".join(f"{y} {v * 1e4:+.0f}" for y, v in yr.items()))
    L.append("  best 5: " + ", ".join(f"{p} {v * 1e4:+.0f}" for p, v in net.nlargest(5).items()) +
             " | worst 5: " + ", ".join(f"{p} {v * 1e4:+.0f}" for p, v in net.nsmallest(5).items()))
    # mechanism gates
    X = np.column_stack([np.ones(len(J)), J.s.values])
    beta, *_ = np.linalg.lstsq(X, J.spread_ab.values, rcond=None)
    res = J.spread_ab.values - X @ beta
    se = np.sqrt(res @ res / (len(J) - 2) * np.linalg.inv(X.T @ X)[1, 1])
    slope_t = beta[1] / se
    terc = pd.qcut(J.s.abs(), 3, labels=["low", "mid", "high"])
    tm = net.groupby(terc, observed=True).mean()
    L.append(f"M-dose: spread_ab on s slope {beta[1] * 1e4:+.1f}bp per unit s (s sd {J.s.std():.4f}; "
             f"= {beta[1] * J.s.std() * 1e4:+.1f}bp per 1 sd), t {slope_t:+.2f}")
    L.append("M-dir: AP net by |s| tercile: " + "  ".join(f"{k} {v * 1e4:+.1f}bp" for k, v in tm.items()))
    g = {"mean>0 & t>=2": net.mean() > 0 and tstat(net) >= 2, "median>0": net.median() > 0, "ex-best-5>0": ex5.mean() > 0,
         "both subperiods>0": all(v > 0 for v in subs), "years>=60%": (yr > 0).mean() >= 0.6, "2x cost>0": net2.mean() > 0}
    mg = {"M-dose slope<0 t<=-1.5": slope_t <= -1.5, "M-dir high>low": tm["high"] > tm["low"]}
    L.append("RETURN GATES: " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in g.items()))
    L.append("MECHANISM GATES: " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in mg.items()))

    # placebos
    rng = np.random.default_rng(20261004)
    pl = [judge(monthly("SPY", "IEF", rng=rng)).pipe(lambda d: (d.ap - d.cost).mean()) for _ in range(1000)]
    pct = float((np.array(pl) < net.mean()).mean() * 100)
    mid = judge(monthly("SPY", "IEF", end_offset=-9))
    L.append(f"\nPLACEBO random 3-session windows (1000 draws): real mean at the {pct:.1f}th pct "
             f"(placebo mean {np.mean(pl) * 1e4:+.1f}bp, 95th {np.percentile(pl, 95) * 1e4:+.1f}bp)")
    L.append(f"PLACEBO fixed mid-month (ends T-9): {stat(mid.ap - mid.cost)}")
    raw_only = net.mean() <= 0 < (J.raw - J.cost).mean()

    # label
    m, t = net.mean() * 1e4, tstat(net)
    later = full.loc[full.index >= pd.Period("2016-01", "M")]
    later_net = (later.ap - later.cost)
    if m <= 0 or t < 1:
        label = "KILL"
    elif pct < 90 or raw_only:
        label = "ARTIFACT"
    elif all(g.values()) and all(mg.values()):
        label = "VALIDATED" if later_net.mean() > 0 else "DECAYED"
    elif all(g.values()) or (all(mg.values()) and 1.5 <= t < 2):
        label = "RESEARCH" if later_net.mean() > 0 else "DECAYED"
    else:
        label = "INTERESTING"
    if label in ("RESEARCH", "VALIDATED") and m < 5:
        label = "INTERESTING (economics < +5bp net per window)"
    L.append(f"VERDICT: {label}   (mean net AP {m:+.1f}bp/window, t {t:.2f}; placebo pct {pct:.0f}; "
             f"2016-26 touched mean net {later_net.mean() * 1e4:+.1f}bp)")

    # reported diagnostics
    L.append("\nREPORTED (falsification only)")
    for lab, kw in (("T-2->T", dict(length=2)), ("T-4->T-1", dict(end_offset=-1)), ("T-1->T", dict(length=1)),
                    ("T->T+2 (reversal)", dict(end_offset=2, length=2)), ("T->T+5", dict(end_offset=5, length=5))):
        x = judge(monthly("SPY", "IEF", **kw))
        L.append(f"  window {lab:18s} {stat(x.ap - x.cost)}")
    L.append(f"  |Re-Rb| < 1%: {stat(net[J.relgap.abs() < 0.01])}   > 5%: {stat(net[J.relgap.abs() > 0.05])}")
    crisis = (net.index >= pd.Period("2008-09", "M")) & (net.index <= pd.Period("2009-03", "M"))
    L.append(f"  ex 2008-09..2009-03: {stat(net[~crisis])}")
    L.append(f"  ex 5 largest |P|: {stat(net.drop(net.abs().nlargest(5).index))}")
    L.append(f"  leg decomposition (gross abnormal): equity leg {stat(J.legE)} | bond leg {stat(J.legB)}")
    L.append(f"  unsigned bond leg h*AR_IEF (TME confound): {stat(J.bond_unsigned)}")
    from .tme_treasury import month_table
    irx = pd.Series(0.0, index=load("SPY").index)
    tme = month_table(load("TLT")["adjclose"].loc["2002-07-01":"2015-12-31"], irx)["ar"]
    c = pd.concat([net, tme], axis=1, keys=["rb", "tme"]).dropna()
    L.append(f"  corr(P net, TME AR) monthly {c.rb.corr(c.tme):+.2f} (n {len(c)})")
    for eq, bd in (("SPY", "TLT"), ("SPY", "AGG"), ("IWM", "IEF"), ("VTI", "IEF")):
        x = judge(monthly(eq, bd))
        L.append(f"  cross-section {eq}/{bd}: {stat(x.ap - x.cost)}")
    L.append(f"  2016-26 (touched, add. 34): {stat(later_net)}")
    L.extend(minute_experiment(full))
    # capacity
    vol = {t: dollar_volume(t) for t in ("SPY", "IEF")}
    for y in (2005, 2010, 2015, 2025):
        adv = {t: float(v.loc[str(y)].mean()) for t, v in vol.items()}
        hh = float(J.h.median())
        parts = []
        for n in (1e5, 1e6, 1e7, 1e8):
            parts.append(f"${n:,.0f}: SPY {n / (3 * adv['SPY']) * 100:.3f}% IEF {n * hh / (3 * adv['IEF']) * 100:.2f}%")
        L.append(f"  capacity {y} (ADV SPY ${adv['SPY'] / 1e9:.1f}B IEF ${adv['IEF'] / 1e6:.0f}M; % of 3-session volume): "
                 + "; ".join(parts))
    text = "\n".join(L)
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
