"""IDX-LETF-REV (N 1208 arm A long, N 1209 arm B short): index/sector LETF close rebalance -> next-open reversal on the
UNDERLYING ETF. The `not tested: index LETFs` leaf of LETF-REV (N 1065).

Pre-registration: research/drafts/round1_prose.md "BRANCH LIST + PRE-REGISTRATION - IDX-LETF-REV" (2026-11-10).
Data: WRDS CRSP dsf, cached to data/research/idx_letf/. Usage: python research/sim/idx_letf_rev.py [--pull]
"""
import math
import pathlib
import sys

import numpy as np
import pandas as pd
import scipy.stats as SS

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data" / "research" / "idx_letf"
OUT = ROOT / "data" / "research" / "program" / "idx_letf_rev_out.txt"
N_PROGRAM = 1209
COST = 3e-4  # per side
LINES = []

# underlying -> {letf: leverage}; leverage from the fund name, changes over time not modelled (disclosed)
MAP = {
    "QQQ": {"QLD": 2, "QID": -2, "TQQQ": 3, "SQQQ": -3, "PSQ": -1},
    "SPY": {"SSO": 2, "SDS": -2, "UPRO": 3, "SPXU": -3, "SPXL": 3, "SPXS": -3, "SH": -1},
    "DIA": {"DDM": 2, "DXD": -2, "UDOW": 3, "SDOW": -3, "DOG": -1},
    "IWM": {"UWM": 2, "TWM": -2, "TNA": 3, "TZA": -3, "URTY": 3, "SRTY": -3, "RWM": -1},
    "XLF": {"UYG": 2, "SKF": -2, "FAS": 3, "FAZ": -3},
    "XLE": {"DIG": 2, "DUG": -2, "ERX": 3, "ERY": -3},
    "XLK": {"ROM": 2, "REW": -2, "TECL": 3, "TECS": -3},
    "SOXX": {"USD": 2, "SSG": -2, "SOXL": 3, "SOXS": -3},
    "XBI": {"LABU": 3, "LABD": -3},
    "IBB": {"BIB": 2, "BIS": -2},
    "GDX": {"NUGT": 3, "DUST": -3},
    "GDXJ": {"JNUG": 3, "JDST": -3},
    "IYR": {"URE": 2, "SRS": -2, "DRN": 3, "DRV": -3},
    "EEM": {"EET": 2, "EEV": -2, "EDC": 3, "EDZ": -3},
    "FXI": {"XPP": 2, "FXP": -2, "YINN": 3, "YANG": -3},
}
JUDGE = ("2009-01-01", "2019-12-31")
HALVES = [("2009-01-01", "2014-12-31"), ("2015-01-01", "2019-12-31")]
REPORT = [("2006-01-01", "2008-12-31"), ("2020-01-01", "2024-12-31")]
PLACEBO = ("1999-01-01", "2005-12-31")


def P(s=""):
    print(s)
    LINES.append(str(s))


def pull():
    import wrds
    nm = pd.read_parquet(D / "names.parquet")
    nm = nm[nm.shrcd == 73]
    tick = set(MAP) | {l for m in MAP.values() for l in m} | {"QQQQ"}
    nm = nm[nm.ticker.isin(tick)]
    perm = nm.groupby("permno").ticker.agg(lambda s: "QQQ" if "QQQQ" in set(s) or "QQQ" in set(s) else s.iloc[-1])
    perm.rename("tk").reset_index().to_parquet(D / "permmap.parquet")
    db = wrds.Connection(wrds_username="andrewlau624", wrds_connect_attempts=2)
    pl = ",".join(str(int(p)) for p in perm.index)
    dsf = db.raw_sql(f"""select permno, date, prc, openprc, shrout, vol, ret, retx, cfacpr from crsp.dsf
        where permno in ({pl}) and date between '1998-01-01' and '2024-12-31'""", date_cols=["date"])
    dsf.to_parquet(D / "dsf.parquet")
    print("pulled", len(perm), len(dsf), dsf.date.max())


def day_t(x, dates):
    df = pd.DataFrame({"x": np.asarray(x, float), "d": np.asarray(dates)}).dropna()
    m = df.x.mean()
    gs = df.groupby("d").x.apply(lambda s: (s - m).sum())
    se = math.sqrt((gs ** 2).sum()) / len(df)
    return m / se if se > 0 else float("nan")


def dsr(x, n_trials):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False)
    g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


def build():
    pm = pd.read_parquet(D / "permmap.parquet").set_index("permno").tk
    df = pd.read_parquet(D / "dsf.parquet")
    df["tk"] = df.permno.map(pm)
    df = df.sort_values(["tk", "date"]).reset_index(drop=True)  # explicit order (never trust on-disk order)
    df["prc"] = df.prc.abs()
    for c in ("openprc", "shrout", "vol", "ret", "retx", "cfacpr"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    g = df.groupby("tk")
    # close(t) -> open(t+1), split-adjusted, plus the t+1 ex-dividend cash (ret - retx) received by the holder at close t
    nxt_open = g.openprc.shift(-1)
    nxt_cf = g.cfacpr.shift(-1)
    nxt_div = (g.ret.shift(-1) - g.retx.shift(-1)).fillna(0.0)
    df["on"] = (nxt_open / nxt_cf) / (df.prc / df.cfacpr) - 1 + nxt_div
    df.loc[(df.openprc.isna()) | (nxt_open <= 0), "on"] = np.nan
    df["nxt_date"] = g.date.shift(-1)
    df["aum_lag"] = g.prc.shift(1) * g.shrout.shift(1) * 1000.0
    df["dvol"] = df.prc * df.vol
    df["adv20"] = g.dvol.transform(lambda s: s.rolling(20, min_periods=15).mean().shift(1))
    return df


def panel(df):
    rows = []
    lev = {l: (u, L) for u, m in MAP.items() for l, L in m.items()}
    let = df[df.tk.isin(lev)].copy()
    let["und"] = let.tk.map(lambda t: lev[t][0])
    let["k"] = let.tk.map(lambda t: lev[t][1] * (lev[t][1] - 1))
    let["kaum"] = let.k * let.aum_lag
    kaum = let.groupby(["und", "date"]).kaum.sum(min_count=1).rename("kaum")
    und = df[df.tk.isin(MAP)].set_index(["tk", "date"])
    und.index.names = ["und", "date"]
    u = und.join(kaum, how="left").reset_index()
    u["kaum"] = u.kaum.fillna(0.0)
    u["r"] = u.retx
    u["I"] = u.kaum * u.r / u.adv20
    u["R"] = u.kaum / u.adv20
    u = u.sort_values(["und", "date"]).reset_index(drop=True)
    gg = u.groupby("und")
    # PIT thresholds over the prior 252 sessions (>= 120 obs)
    u["absI"] = u.I.abs().where(u.kaum > 0)
    u["thrI"] = gg.absI.transform(lambda s: s.rolling(252, min_periods=120).quantile(0.9).shift(1))
    u["absr"] = u.r.abs()
    u["thrr"] = gg.absr.transform(lambda s: s.rolling(252, min_periods=120).quantile(0.9).shift(1))
    u["on_mu"] = gg.on.transform(lambda s: s.rolling(252, min_periods=120).mean().shift(1))
    u["ex"] = u.on - u.on_mu
    u["evI"] = (u.absI >= u.thrI) & (u.kaum > 0) & u.ex.notna()
    u["evr"] = (u.absr >= u.thrr) & u.ex.notna()
    return u


def daily(ev, sign):
    """Equal-weight event-day portfolio; sign +1 long after down (I<0), -1 short after up (I>0). Returns gross excess."""
    x = ev.assign(p=sign * ev.ex, praw=sign * ev.on)
    return x.groupby("date").agg(p=("p", "mean"), praw=("praw", "mean"), n=("p", "size"))


def stats(name, pday, cost_rt):
    x = (pday.p - cost_rt)
    if len(x) < 5:
        P(f"  {name:44s} days {len(x)}")
        return None
    s = x.sort_values()
    yrs = (x.index.max() - x.index.min()).days / 365.25 or 1
    P(f"  {name:44s} days {len(x):4d} ({len(x)/yrs:5.1f}/yr) mean {x.mean()*1e4:+6.1f}bp med {x.median()*1e4:+6.1f} "
      f"hit {100*(x>0).mean():4.1f}% t {x.mean()/x.std(ddof=1)*math.sqrt(len(x)):+5.2f} ex-top5 {s.iloc[:-5].mean()*1e4:+6.1f} "
      f"book {x.sum()/yrs*100:+5.1f}%/yr")
    return x


def sl(d, a, b):
    return d[(d.index >= a) & (d.index <= b)] if isinstance(d.index, pd.DatetimeIndex) else d[(d.date >= a) & (d.date <= b)]


def run():
    df = build()
    u = panel(df)
    P("IDX-LETF-REV (N 1208 long / 1209 short), CRSP dsf 1998-2024, 15 underlyings; pre-reg round1_prose 2026-11-10")
    P(f"cost {COST*1e4:.0f}bp/side; returns = close->open excess vs the ETF's own prior-252 mean close->open (PIT)")
    cov = u[u.kaum > 0].groupby("und").date.min()
    P("LETF coverage start: " + ", ".join(f"{k} {v.date()}" for k, v in cov.sort_values().items()))
    med_R = u[(u.date >= JUDGE[0]) & (u.date <= JUDGE[1]) & (u.kaum > 0)].groupby("und").R.median()
    P("median LETF k*AUM / underlying ADV in judge (I per 1.00 = 100% day move): " +
      ", ".join(f"{k} {v:.2f}" for k, v in med_R.sort_values(ascending=False).items()))
    res = {}
    for arm, sign, cond, nid in (("A long (I<0)", 1, lambda e: e.I < 0, 1208), ("B short (I>0)", -1, lambda e: e.I > 0, 1209)):
        P()
        P(f"=== Arm {arm}, N {nid}")
        ev = u[u.evI & cond(u)]
        pd_all = daily(ev, sign)
        J = sl(pd_all, *JUDGE)
        P(" judge 2009-19:")
        xj = stats("net 1x cost (6bp RT)", J, 2 * COST)
        stats("gross", J, 0.0)
        stats("net 2x cost", J, 4 * COST)
        stats("net 3x cost", J, 6 * COST)
        if xj is not None:
            P(f"  raw (not excess) net mean {(J.praw - 2*COST).mean()*1e4:+.1f}bp; day-clustered t on event level "
              f"{day_t(sign*sl(ev, *JUDGE).ex.values - 2*COST, sl(ev, *JUDGE).date.values):+.2f}; "
              f"events {len(sl(ev, *JUDGE))}; DSR@{N_PROGRAM} {dsr(xj.values, N_PROGRAM):.3f}")
        for a, b in HALVES:
            stats(f"half {a[:4]}-{b[:4]} net", sl(pd_all, a, b), 2 * COST)
        for a, b in REPORT:
            stats(f"report {a[:4]}-{b[:4]} net (not judged)", sl(pd_all, a, b), 2 * COST)
        P("  per underlying (judge, event-level net excess):")
        ej = sl(ev, *JUDGE)
        for k, s in ej.groupby("und"):
            v = sign * s.ex - 2 * COST
            P(f"    {k:5s} n {len(v):4d} mean {v.mean()*1e4:+6.1f} med {v.median()*1e4:+6.1f}")
        # rung-1 baselines
        P(" baselines (judge, net 1x):")
        allday = u[u.ex.notna() & (u.kaum > 0)]
        stats("every day, same ETFs, unconditional (sign)", sl(daily(allday, sign), *JUDGE), 2 * COST)
        evr = u[u.evr & (u.r < 0 if sign > 0 else u.r > 0)]
        stats("top-decile |r| days, no LETF input", sl(daily(evr, sign), *JUDGE), 2 * COST)
        # dose: top-decile |r| events split by R above/below the median R of those events
        e2 = sl(evr[evr.kaum > 0], *JUDGE).copy()
        m = e2.R.median()
        hi = sign * e2[e2.R > m].ex
        lo = sign * e2[e2.R <= m].ex
        tt = SS.ttest_ind(hi, lo, equal_var=False)
        P(f"  DOSE (|r| top-decile events, R > vs <= median {m:.2f}): high {hi.mean()*1e4:+.1f}bp n {len(hi)} | low "
          f"{lo.mean()*1e4:+.1f}bp n {len(lo)} | diff {(hi.mean()-lo.mean())*1e4:+.1f} t {tt.statistic:+.2f}")
        # placebo: |r| rule pre-LETF on the same ETFs
        pl = sl(daily(evr, sign), *PLACEBO)
        xp = stats("PLACEBO |r| top-decile 1999-2005 (pre-LETF)", pl, 2 * COST)
        res[arm] = (xj, hi.mean() - lo.mean(), tt.statistic, xp)
    P()
    P("VERDICT inputs per the pre-registered kill rule: see lines above (judge mean >= +10bp, t >= 2, median > 0, halves > 0,")
    P("ex-top-5 > 0, dose diff > 0 with t >= 1.5, judge >= placebo + 50% of effect, DSR >= 0.95, book >= 16pp/yr).")
    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    if "--pull" in sys.argv:
        pull()
    run()
