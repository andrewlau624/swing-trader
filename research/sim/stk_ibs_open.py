"""Study STK-IBS-OPEN (round1_prose.md "### STK-IBS-OPEN (N 1063)"): the ETF IBS leg's open-to-open form on liquid single stocks.
Rule: day d in top-500 by $ADV20 (domestic common, prev close >= $5), IBS < 0.2, day_ret > -4%; buy open(d+1) cross, sell open(d+2)
cross; EW per signal day; net = gross - 10bp; excess vs EW top-500 universe open(d+1)->open(d+2). Judge 2003-15.
usage: PYTHONPATH=. .venv/bin/python -m research.sim.stk_ibs_open"""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
SH = Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/stk_ibs_open_out.txt"
START, END = "2003-01-01", "2026-09-30"
COST_BP = 10.0  # tier 5bp/side
PERIODS = [("2003-08", "2003-01-01", "2008-12-31"), ("2009-15", "2009-01-01", "2015-12-31"), ("JUDGE 2003-15", "2003-01-01", "2015-12-31"),
           ("2016-20", "2016-01-01", "2020-12-31"), ("2021-26", "2021-01-01", "2026-09-30"), ("2016-26", "2016-01-01", "2026-09-30")]


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with OUT.open("a") as f: f.write(s + "\n")


def clus_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else float("nan")


def extop5(x):
    x = np.sort(np.asarray(x, float)); return (x.sum() - x[-5:].sum()) / (len(x) - 5) if len(x) > 5 else float("nan")


def dstats(net: pd.Series, exc: pd.Series | None = None) -> str:
    """per-signal-day series (already EW within the day)."""
    x = net.dropna().to_numpy(float)
    if len(x) < 3: return f"days {len(x)}"
    s = f"days {len(x)} net {x.mean():+.1f} med {np.median(x):+.1f} hit {np.mean(x > 0):.2f} t {clus_t(x):.2f} ex-top5 {extop5(x):+.1f}"
    if exc is not None:
        e = exc.dropna().to_numpy(float)
        s += f" | excess {e.mean():+.1f} med {np.median(e):+.1f} t {clus_t(e):.2f}"
    return s


def load_stocks() -> pd.DataFrame:
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"],
                         filters=[("date", ">=", pd.Timestamp("2002-10-01"))])
    st = st[st.ticker.isin(ok)]; st["date"] = pd.to_datetime(st.date)
    st = st.sort_values(["ticker", "date"]).reset_index(drop=True)
    g = st.groupby("ticker", sort=False)
    st["pc"] = g.close.shift(1); st["pcu"] = g.closeunadj.shift(1)
    dv = (st.closeunadj * st.volume).groupby(st.ticker).shift(1)
    # flat rolling median (fast) is exact where the 20-row window stays inside the ticker; the first 15-19 rows of each
    # ticker (min_periods=15 but window straddles the boundary) are recomputed per ticker on that small subset
    adv = dv.rolling(20, min_periods=15).median()
    same20 = st.ticker.eq(st.ticker.shift(19)); cc = g.cumcount()
    adv[~same20] = np.nan
    edge = (cc >= 15) & (cc <= 19)
    if edge.any():
        head = dv[cc <= 19]
        adv_head = head.groupby(st.ticker[cc <= 19]).rolling(20, min_periods=15).median().reset_index(level=0, drop=True)
        adv[edge] = adv_head[edge[cc <= 19]]
    st["adv"] = adv
    st["dr"] = st.close / st.pc - 1
    st["ibs"] = (st.close - st.low) / (st.high - st.low).replace(0, np.nan)
    o1, o2 = g.open.shift(-1), g.open.shift(-2)
    d1, d2 = g.date.shift(-1), g.date.shift(-2)
    st["ret"] = (o2 / o1 - 1) * 1e4                    # open d+1 -> open d+2, bp
    # require the next two rows to be the next two sessions for this name (no >7 calendar-day hole; rules out stale/halted series)
    st["ok_fwd"] = st.ret.notna() & ((d2 - st.date).dt.days <= 7)
    st = st[(st.date >= START) & (st.date <= END) & st.ok_fwd & (st.pcu >= 5) & st.adv.notna() & (st.pc > 0)]
    st["rk"] = st.groupby("date").adv.rank(ascending=False, method="first")
    return st[st.rk <= 500].copy()


def load_etf(sym: str) -> pd.DataFrame:
    f = pd.read_parquet(SH / "funds.parquet", columns=["ticker", "date", "open", "high", "low", "close"], filters=[("ticker", "==", sym)])
    f["date"] = pd.to_datetime(f.date); f = f.sort_values("date").reset_index(drop=True)
    f["ibs"] = (f.close - f.low) / (f.high - f.low).replace(0, np.nan)
    f["dr"] = f.close / f.close.shift(1) - 1
    f["ret"] = (f.open.shift(-2) / f.open.shift(-1) - 1) * 1e4
    return f[(f.date >= START) & (f.date <= END)].set_index("date")


def main():
    if OUT.exists(): OUT.unlink()
    log(f"STK-IBS-OPEN (N 1063) run {pd.Timestamp.now():%Y-%m-%d %H:%M}; Sharadar SEP {START}..{END}; prices: Sharadar daily open as the "
        f"opening cross for ALL periods (official 2021-26 open crosses on disk cover only night-leg picks [drop <= -8%], disjoint from this rule)")
    st = load_stocks()
    univ = st.groupby("date").ret.mean().rename("univ")
    sig = st[(st.ibs < 0.2) & (st.dr > -0.04)]
    day = sig.groupby("date").agg(gross=("ret", "mean"), n=("ret", "size")).join(univ)
    day["net"] = day.gross - COST_BP; day["exc"] = day.gross - day.univ
    log(f"universe: {len(st):,} name-days on {st.date.nunique():,} sessions (top-500 by $ADV20, prev close>=$5, domestic common); "
        f"500th-rank $ADV20 median by year: " + ", ".join(f"{y} ${v/1e6:.0f}M" for y, v in st[st.rk == 500].groupby(st[st.rk == 500].date.dt.year).adv.median().items()))
    log(f"signals: {len(sig):,} name-days (IBS<0.2 & day_ret>-4%) on {len(day):,} signal days ({len(day)/st.date.nunique():.0%} of sessions); "
        f"names/day mean {day.n.mean():.1f} median {day.n.median():.0f}; IBS<0.2 total {int((st.ibs < 0.2).sum()):,} of which day_ret<=-4% excluded "
        f"{int(((st.ibs < 0.2) & (st.dr <= -0.04)).sum()):,}")
    log("\n=== per-period (per signal day, EW within day, bp; net = gross - 10bp; excess = gross - EW top-500 same open->open)")
    for nm, a, b in PERIODS:
        d = day[(day.index >= a) & (day.index <= b)]
        log(f"  {nm:14s} {dstats(d.net, d.exc)} | gross {d.gross.mean():+.1f} univ {d.univ.mean():+.1f}")
    log("\n=== per-year: year  sigdays  names/day  gross  net  excess  median(net)  hit  t(net)")
    for y, d in day.groupby(day.index.year):
        log(f"  {y}  {len(d):4d}  {d.n.mean():6.1f}  {d.gross.mean():+7.1f}  {d.net.mean():+7.1f}  {d.exc.mean():+7.1f}  {d.net.median():+7.1f}  {np.mean(d.net > 0):.2f}  {clus_t(d.net):+5.2f}")
    # gates
    J = day[day.index <= "2015-12-31"]; T = day[day.index >= "2016-01-01"]
    h1 = J[J.index <= "2008-12-31"]; h2 = J[J.index > "2008-12-31"]
    ok = dict(net10=J.net.mean() >= 10, t2=clus_t(J.net) >= 2, median=J.net.median() > 0, extop5=extop5(J.net) > 0,
              h1=h1.net.mean() > 0, h2=h2.net.mean() > 0, fwd_same_sign=np.sign(T.net.mean()) == np.sign(J.net.mean()))
    kill = (J.net.mean() < 8) or (clus_t(J.net) < 2)
    log(f"\nGATES (judge 2003-15, net): {ok} -> {'PASS' if all(ok.values()) else ('KILL' if kill else 'FAIL (neither PASS nor KILL bar)')}")
    log(f"  judge net {J.net.mean():+.2f}bp t {clus_t(J.net):.2f}; 2016-26 net {T.net.mean():+.2f}bp t {clus_t(T.net):.2f}")
    # diagnostics (reads only)
    log("\n=== diagnostics: ETF-leg-style IBS<0.2 on SPY / QQQ, same open(d+1)->open(d+2), net = gross - 10bp, per own-signal day")
    etf = {s: load_etf(s) for s in ("SPY", "QQQ")}
    for s, f in etf.items():
        e = f[(f.ibs < 0.2) & f.ret.notna()]
        for nm, a, b in PERIODS:
            d = e[(e.index >= a) & (e.index <= b)]
            log(f"  {s} {nm:14s} {dstats(d.ret - COST_BP)} | all-days {s} mean {f[(f.index >= a) & (f.index <= b)].ret.mean():+.1f}")
    spy = etf["SPY"]
    day["spy_ibs"] = spy.ibs.reindex(day.index); day["spy_low"] = day.spy_ibs < 0.2
    log("\n=== split of stock signal days by SPY's own IBS<0.2 that day (net, excess)")
    for nm, a, b in PERIODS:
        d = day[(day.index >= a) & (day.index <= b)]
        for lab, m in (("SPY IBS<0.2 ", d.spy_low), ("SPY IBS>=0.2", ~d.spy_low & d.spy_ibs.notna())):
            x = d[m]
            log(f"  {nm:14s} {lab} {dstats(x.net, x.exc)} | names/day {x.n.mean() if len(x) else float('nan'):.1f}")
    # volunteered: name-level, not day-level, and the gross distribution
    for nm, a, b in [("JUDGE 2003-15", "2003-01-01", "2015-12-31"), ("2016-26", "2016-01-01", "2026-09-30")]:
        s = sig[(sig.date >= a) & (sig.date <= b)]
        log(f"\nname-level {nm}: n {len(s):,} gross mean {s.ret.mean():+.1f} med {s.ret.median():+.1f} hit {np.mean(s.ret > 0):.2f} "
            f"sd {s.ret.std():.0f}; by IBS bucket <0.1 {s[s.ibs < 0.1].ret.mean():+.1f} (n {int((s.ibs < 0.1).sum()):,}) 0.1-0.2 {s[s.ibs >= 0.1].ret.mean():+.1f}; "
            f"by day_ret: >0 {s[s.dr > 0].ret.mean():+.1f} (n {int((s.dr > 0).sum()):,}) -2..0 {s[(s.dr <= 0) & (s.dr > -0.02)].ret.mean():+.1f} "
            f"-4..-2 {s[s.dr <= -0.02].ret.mean():+.1f} (n {int((s.dr <= -0.02).sum()):,})")
    log("Disclosed: Sharadar daily open as both crosses; ADV20 = rolling 20d median of closeunadj*volume shifted 1; top-500 ranked within date "
        "after the $5 / domestic-common filter; a signal needs the next two rows to be within 7 calendar days; t = per-signal-day (days are the cluster).")


if __name__ == "__main__":
    main()
