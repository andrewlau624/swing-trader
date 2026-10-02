"""Goal hunt Study G2 (pre-registered in round1_prose.md, commit e6316e8): EV2-big (officer/director buys >= $500k at an
issuer with no code-P purchase filing in 730 days) as an intraday overlay on a 100% SPY core in taxable, judged on the
untouched 2016-20 holdout (2021 reported as a sixth year).

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g2 build   # events + counts only (no outcomes)
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g2 judge   # the one look

Output: data/research/program/goal_g2_out.txt
"""
from __future__ import annotations

import glob
import pathlib
import sys
import zipfile

import numpy as np
import pandas as pd

from . import book as B
from . import taxable_frontier as TF
from .event_fetch import raw_bars
from .ib_c1 import DIV, LT, irr
from .ib_c2 import ST_RATE
from .program_books import dsr

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
N_PROG = 772
HOLD = ("2016-01-01", "2020-12-31")
Y21 = ("2021-01-01", "2021-12-31")
BIG, FLOOR = 5e5, 1e4
COSTS = (("2.5bp", 2.5), ("tier_hi", "tier_hi"))


def out():
    f = open(PROG / "goal_g2_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def buys() -> pd.DataFrame:
    """Every Form 4 / 4-A accession with code-P acquisitions, 2014q1..2021q4: fd, sym, usd, shares, insider."""
    f = PROG / "goal_g2_buys.parquet"
    if f.exists():
        return pd.read_parquet(f)
    zs = sorted(glob.glob(str(ROOT / "data/research/jump/insider/201[4-9]q?_form345.zip"))) + \
        sorted(glob.glob(str(ROOT / "data/research/night/insider/202[01]q?_form345.zip")))
    assert len(zs) == 32, len(zs)
    rows = []
    for z in zs:
        Z = zipfile.ZipFile(z)
        rd = lambda n: pd.read_csv(Z.open(n), sep="\t", dtype=str, low_memory=False, on_bad_lines="skip")
        S = rd("SUBMISSION.tsv")[["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL", "DOCUMENT_TYPE"]]
        N = rd("NONDERIV_TRANS.tsv")[["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_ACQUIRED_DISP_CD", "TRANS_SHARES", "TRANS_PRICEPERSHARE"]]
        R = rd("REPORTINGOWNER.tsv")[["ACCESSION_NUMBER", "RPTOWNER_RELATIONSHIP"]]
        N = N[(N.TRANS_CODE == "P") & (N.TRANS_ACQUIRED_DISP_CD == "A")].copy()
        N["sh"] = pd.to_numeric(N.TRANS_SHARES, errors="coerce")
        N["usd"] = N.sh * pd.to_numeric(N.TRANS_PRICEPERSHARE, errors="coerce")
        g = N.groupby("ACCESSION_NUMBER")[["usd", "sh"]].sum().reset_index()
        rel = R.groupby("ACCESSION_NUMBER").RPTOWNER_RELATIONSHIP.agg(lambda x: " ".join(map(str, x))).rename("rel").reset_index()
        g = g.merge(S, on="ACCESSION_NUMBER").merge(rel, on="ACCESSION_NUMBER", how="left")
        rows.append(g[g.DOCUMENT_TYPE.isin(["4", "4/A"])])
        print(z.split("/")[-1], len(rows[-1]), flush=True)
    X = pd.concat(rows)
    X["fd"] = pd.to_datetime(X.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    X["sym"] = X.ISSUERTRADINGSYMBOL.str.upper().str.strip().str.replace("-", ".", regex=False)
    X["insider"] = X.rel.fillna("").str.contains("Director|Officer", case=False)
    X = X.dropna(subset=["fd", "usd", "sym"]).drop_duplicates("ACCESSION_NUMBER")
    X = X[["fd", "sym", "usd", "sh", "insider", "ACCESSION_NUMBER"]]
    X.to_parquet(f)
    return X


def candidates(X: pd.DataFrame) -> pd.DataFrame:
    """One row per (sym, fd) with officer/director code-P $ >= FLOOR: $ bought, $-weighted price, days since the
    issuer's previous code-P filing by anyone (NaN if none since 2014-01)."""
    I = X[X.insider & (X.usd > 0)].groupby(["sym", "fd"])[["usd", "sh"]].sum().reset_index()
    I = I[I.usd >= FLOOR]
    I["px"] = I.usd / I.sh
    allf = X[["sym", "fd"]].drop_duplicates().sort_values(["sym", "fd"])
    prev = {}
    for s, g in allf.groupby("sym"):
        d = g.fd.values
        prev[s] = d
    gap = []
    for s, fd in zip(I.sym, I.fd):
        d = prev[s]
        j = np.searchsorted(d, np.datetime64(fd)) - 1
        gap.append((fd - pd.Timestamp(d[j])).days if j >= 0 else np.nan)
    I["gap"] = gap
    I["first"] = I.gap.isna() | (I.gap > 730)
    return I[(I.fd >= "2016-01-02") & (I.fd <= "2021-12-31")]


def attach(I: pd.DataFrame, log):
    """Trade session, raw open/close, prior close, 20d ADV$ (to d-1), ticker-reuse guard."""
    bars = raw_bars(sorted(I.sym.unique()))
    rows, miss = [], 0
    for r in I.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            miss += 1
            continue
        b = b.sort_index()
        idx = pd.DatetimeIndex(b.index)
        i = idx.searchsorted(r.fd + pd.Timedelta(days=1))
        if i < 20 or i >= len(idx):
            miss += 1
            continue
        h = b.iloc[i - 20:i]
        rows.append(dict(sym=r.sym, fd=r.fd, d=idx[i], usd=r.usd, px=r.px, gap=r.gap, first=r.first,
                         o=b.open.iloc[i], c=b.close.iloc[i], pc=b.close.iloc[i - 1],
                         adv=(h.close * h.volume).mean(), stale=(idx[i] - r.fd).days))
    T = pd.DataFrame(rows)
    log(f"  candidates {len(I)}, no bars / short history {miss}, with bars {len(T)}")
    T = T[T.stale <= 7]                                  # the next session must exist within a week (else delisted/halted)
    g = (T.px / T.pc).between(0.67, 1.5)
    log(f"  ticker-reuse guard drops {int((~g).sum())}")
    T = T[g & (T.pc >= 5) & (T.adv >= 2e7) & (T.o > 0)].drop_duplicates(["d", "sym"])
    T["ret"] = T.c / T.o - 1
    T = T[T.ret.abs() < 0.5]
    return T


def variants(T):
    return {"G2 EV2-big": T[T["first"] & (T.usd >= BIG)],
            "EV2 all sizes (report)": T[T["first"]],
            "ID3 >= $500k (report)": T[T.usd >= BIG]}


def build():
    log = out()
    log(f"=== G2 build {pd.Timestamp.now():%Y-%m-%d %H:%M} (counts only) ===")
    X = buys()
    log(f"  accessions {len(X)}  {X.fd.min():%Y-%m-%d}..{X.fd.max():%Y-%m-%d}")
    I = candidates(X)
    T = attach(I, log)
    T.to_parquet(PROG / "goal_g2_events.parquet")
    for k, V in variants(T).items():
        h = V[(V.d >= HOLD[0]) & (V.d <= HOLD[1])]
        log(f"  {k:24s} holdout {len(h)} ({h.groupby(h.d.dt.year).size().to_dict()}), 2021 {int((V.d.dt.year == 2021).sum())}")


def spy_adj():
    f = PROG / "goal_spy_adj.parquet"
    if f.exists():
        return pd.read_parquet(f).close
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import _clients, trade_date
    data, _ = _clients()
    df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols="SPY", timeframe=TimeFrame.Day, start=pd.Timestamp("2015-10-01", tz="UTC"),
                                              end=pd.Timestamp("2026-09-30", tz="UTC"), feed="sip", adjustment="all")).df.reset_index()
    df["date"] = trade_date(df["timestamp"])
    s = df.set_index("date")[["close"]]
    s.to_parquet(f)
    return s.close


def cost_of(cost, V):
    return B.cost_bps(cost, V.o.values, V.adv.values) / 1e4


def weights(V, per, cap=1.0):
    k = V.groupby("d").sym.transform("count")
    return np.minimum(per, cap / k)


def account(spy_r, V, w, cbp, days, start, mo):
    """SPY core (total return, dividends taxed LT when paid) + whole-share intraday overlay; overlay P&L netted per
    calendar year at ST_RATE, paid on the first session >= Apr 15 (carry-forward, $3k deduction); SPY gain taxed LT at
    the end (ib_c2.c2_account rules). Returns (end value after tax, daily pre-tax returns, trade P&L list)."""
    ev = {d: g for d, g in V.assign(w=w, cb=cbp).groupby("d")}
    E, basis, gain, carry, due = start, start, 0.0, 0.0, None
    r_out, tr = [], []
    for i, d in enumerate(days):
        if i and i % 21 == 0:
            E += mo; basis += mo
        E0 = E
        pn = 0.0
        if d in ev:
            for t in ev[d].itertuples():
                q = np.floor(t.w * E0 / t.o)
                p = q * (t.c - t.o) - t.cb * q * (t.o + t.c)
                pn += p
                if q > 0:
                    tr.append((d, t.sym, p, p / E0))
        x = spy_r.get(d, 0.0)
        x = 0.0 if pd.isna(x) else x
        E = E * (1 + x) + pn
        basis += pn; gain += pn
        dv = E * DIV / 252
        E -= dv * LT; basis += dv * (1 - LT)
        if due is not None and d >= due[0]:
            E -= due[1]; basis -= due[1]; due = None
        if i + 1 < len(days) and days[i + 1].year != d.year:
            net = gain + carry
            if net >= 0:
                tax, carry = ST_RATE * net, 0.0
            else:
                ded = min(3000.0, -net); tax, carry = -ST_RATE * ded, net + ded
            cand = days[days >= pd.Timestamp(f"{d.year + 1}-04-15")]
            due = (cand[0] if len(cand) else days[-1], tax); gain = 0.0
        r_out.append(E / E0 - 1 if E0 else 0.0)
    net = gain + carry
    E -= (due[1] if due is not None else 0.0) + (ST_RATE * net if net > 0 else 0.0)
    basis -= (due[1] if due is not None else 0.0)
    endv = E - LT * max(0.0, E - basis)
    return endv, pd.Series(r_out, index=days), pd.DataFrame(tr, columns=["d", "sym", "pnl", "frac"])


def flows(days, start, mo, endv):
    t0 = days[0]
    f = [(0.0, -start)] + [((d - t0).days / 365.25, -mo) for i, d in enumerate(days) if i and i % 21 == 0]
    return f + [((days[-1] - t0).days / 365.25, endv)]


def maxdd(eq):
    return float((eq / eq.cummax() - 1).min())


def null_pool(days):
    """(session -> list of (sym, open, close)) for every cached raw-bar symbol with prior close >= $5 and 20d ADV$ >= $20M."""
    f = PROG / "goal_g2_pool.pkl"
    if f.exists():
        return pd.read_pickle(f)
    files = glob.glob(str(ROOT / "data/research/events/bars/raw/*.parquet"))
    O, C, DV = {}, {}, {}
    for j, p in enumerate(files):
        b = pd.read_parquet(p)
        if not len(b):
            continue
        b.index = pd.DatetimeIndex(b.index)
        b = b.loc["2015-11-01":"2021-12-31"]
        if len(b) < 25:
            continue
        s = pathlib.Path(p).stem
        O[s], C[s], DV[s] = b.open, b.close, b.close * b.volume
        if j % 5000 == 0:
            print(f"  pool {j}/{len(files)}", flush=True)
    O, C, DV = pd.DataFrame(O), pd.DataFrame(C), pd.DataFrame(DV)
    adv = DV.rolling(20, min_periods=15).mean().shift(1)
    pc = C.shift(1)
    ok = (adv >= 2e7) & (pc >= 5) & (O > 0) & ((C / O - 1).abs() < 0.5)
    P = {}
    for d in days:
        if d not in ok.index:
            continue
        m = ok.loc[d]
        cols = m.index[m.values]
        P[d] = (C.loc[d, cols] / O.loc[d, cols] - 1).values
    pd.to_pickle(P, f)
    return P


def judge():
    log = out()
    log(f"\n=== G2 JUDGE {pd.Timestamp.now():%Y-%m-%d %H:%M} (the one look; N {N_PROG}) ===")
    T = pd.read_parquet(PROG / "goal_g2_events.parquet")
    spy = spy_adj()
    spy.index = pd.DatetimeIndex(spy.index)
    spy_r = spy.pct_change()
    for k, V0 in variants(T).items():
        for wl, (a, b) in (("holdout 2016-20", HOLD), ("2021 (untouched)", Y21)):
            V = V0[(V0.d >= a) & (V0.d <= b)].copy()
            days = spy_r.loc[a:b].index
            log(f"\n-- {k} | {wl}: {len(V)} trades ({len(V) / max(1e-9, (days[-1] - days[0]).days / 365.25):.0f}/yr)")
            if not len(V):
                continue
            for cl, cost in COSTS:
                net = V.ret - 2 * cost_of(cost, V)
                yrs = net.groupby(V.d.dt.year).agg(["mean", "count"])
                log(f"   {cl:8s} per trade net {net.mean() * 1e4:+.1f}bp median {net.median() * 1e4:+.1f} hit {(net > 0).mean():.0%} "
                    f"| by year " + " ".join(f"{y}:{m * 1e4:+.0f}({n})" for y, (m, n) in yrs.iterrows()))
            if not k.startswith("G2"):
                continue
            net = V.ret - 2 * cost_of(2.5, V)
            for per, lab in ((0.5, "G2a 0.5x/event"), (1.0, "G2b 1.0x/event")):
                w = weights(V, per)
                dayp = (w * net).groupby(V.d).sum().reindex(days).fillna(0.0)
                ex5d = dayp.drop(dayp[dayp != 0].nlargest(max(1, int(round(0.05 * (dayp != 0).sum())))).index).sum()
                ex5t = (w * net).sort_values().iloc[:-5].sum()
                log(f"   {lab}: overlay sum {dayp.sum():+.3f} NW t {TF.nw_t(dayp):+.2f} | ex best 5% days {ex5d:+.3f} | ex best 5 trades "
                    f"{ex5t:+.3f} | years>0 {(dayp.groupby(dayp.index.year).sum() > 0).sum()}/{dayp.index.year.nunique()} "
                    f"| DSR N {N_PROG}: overlay {dsr(dayp, N_PROG)['dsr']:.3f}, SPY+overlay {dsr(spy_r.reindex(days).fillna(0) + dayp, N_PROG)['dsr']:.3f}")
                if per == 0.5 and wl.startswith("holdout"):
                    P = null_pool(days)
                    rng = np.random.default_rng(7)
                    cnt = V.groupby("d").size()
                    real = (net * weights(V, 0.5)).sum()
                    sims = []
                    for _ in range(1000):
                        s = 0.0
                        for d, n in cnt.items():
                            pool = P.get(d)
                            if pool is None or not len(pool):
                                continue
                            x = rng.choice(pool, size=min(n, len(pool)), replace=False) - 2 * 2.5e-4
                            s += (x * min(0.5, 1.0 / n)).sum()
                        sims.append(s)
                    log(f"   random-pick null: real {real:+.3f} vs null mean {np.mean(sims):+.3f}, pct {(np.array(sims) < real).mean():.1%}")
                for cl, cost in COSTS:
                    cb = cost_of(cost, V)
                    for start in (2300.0, 10000.0):
                        for mo in (1000.0, 0.0):
                            e1, r1, tr = account(spy_r, V, w.values, cb, days, start, mo)
                            e0, r0, _ = account(spy_r, V.iloc[:0], np.zeros(0), np.zeros(0), days, start, mo)
                            i1, i0 = irr(flows(days, start, mo, e1)), irr(flows(days, start, mo, e0))
                            eq = (1 + r1).cumprod()
                            mret = r1.groupby(r1.index.to_period("M")).apply(lambda x: (1 + x).prod() - 1)
                            wt = tr.loc[tr.frac.idxmin()] if len(tr) else None
                            log(f"     {cl:8s} ${start:>6,.0f} +${mo:,.0f}/mo: after-tax IRR {i1:6.1%} vs SPY {i0:6.1%} ({(i1 - i0) * 100:+5.1f}pp) "
                                f"| maxDD {maxdd(eq):.1%} | worst month {mret.min():+.1%} ({mret.idxmin()}) | worst trade "
                                + (f"{wt.sym} {wt.d:%Y-%m-%d} {wt.frac:+.1%} of equity" if wt is not None else "-")
                                + f" | trades filled {len(tr)}")


if __name__ == "__main__":
    {"build": build, "judge": judge}[sys.argv[1]]()
