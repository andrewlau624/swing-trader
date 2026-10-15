"""Combo loop (2026-10-08 /loop): does signal A AND signal B beat the better of A, B alone?

Same panel/harness as winsig.py (buy open t+1, sell close t+5, excess vs EW universe, delisted included).
Gate frozen in research/drafts/window_signals_loop_2026-10-07.md "COMBO LOOP", per combo:
  combo net excess - max(net A, net B) >= +15bp, date-paired diff (combo vs better-single-not-combo) NW t >= 3,
  combo net NW t >= 3, combo net halves > 0, combo net median > 0, combo net ex-top-5-days > 0,
  improvement > 0 in both halves. 2016-01..2026-09 discovery; a pass gets one 2003-15 look.
Usage: python -m research.sim.combo C1 [--confirm]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.sim import winsig as w, winsig_fam as F

OUT = w.CACHE.parent / "program" / "combo_out.txt"
H = 5


def ibs(t):
    return (t.close - t.low) / (t.high - t.low).replace(0, np.nan)


def stats(t, m, lo, hi, cost, uni="liq"):
    sel = t[m & t[uni] & (t.date >= lo) & (t.date <= hi)]
    x = sel[f"x{H}"].dropna() - cost
    d = x.groupby(sel.loc[x.index, "date"]).mean()
    mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
    return dict(n=len(x), net=x.mean() * 1e4, med=x.median() * 1e4, t=w.nw_t(d, H),
                h=(d[d.index < mid].mean() * 1e4, d[d.index >= mid].mean() * 1e4),
                ex5=d.sort_values().iloc[:-5].mean() * 1e4 if len(d) > 10 else np.nan, d=d)


def paired(t, combo, rest, lo, hi, uni="liq"):
    """Per date: mean combo excess - mean excess of the better single's non-combo trades; NW t on dates with both."""
    def dm(m):
        s = t[m & t[uni] & (t.date >= lo) & (t.date <= hi)]
        return s.groupby("date")[f"x{H}"].mean()
    a, b = dm(combo), dm(rest)
    j = a.index.intersection(b.index)
    d = a[j] - b[j]
    mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
    return dict(n=len(d), mean=d.mean() * 1e4, t=w.nw_t(d, H),
                h=(d[d.index < mid].mean() * 1e4, d[d.index >= mid].mean() * 1e4))


def run(t, A, B, la, lb, lo, hi, cost, uni="liq"):
    A, B = A.fillna(False).astype(bool), B.fillna(False).astype(bool)
    C = A & B
    sa, sb, sc = (stats(t, m, lo, hi, cost, uni) for m in (A, B, C))
    best, bm, other = (sa, A, B) if sa["net"] >= sb["net"] else (sb, B, A)
    p = paired(t, C, bm & ~other, lo, hi, uni)
    imp = sc["net"] - best["net"]
    imp_h = (sc["h"][0] - best["h"][0], sc["h"][1] - best["h"][1])
    ok = (imp >= 15 and p["t"] >= 3 and sc["t"] >= 3 and min(sc["h"]) > 0 and sc["med"] > 0
          and sc["ex5"] > 0 and min(imp_h) > 0)
    f = lambda lab, s: (f"  {lab:34} n {s['n']:7} net {s['net']:+6.1f} med {s['med']:+6.1f} t {s['t']:+5.2f} "
                        f"halves {s['h'][0]:+6.1f}/{s['h'][1]:+6.1f} ex5 {s['ex5']:+6.1f}")
    lines = [f(la, sa), f(lb, sb), f("COMBO A&B", sc),
             f"  improvement vs better single {imp:+.1f}bp (halves {imp_h[0]:+.1f}/{imp_h[1]:+.1f}); "
             f"date-paired combo - better-single-only {p['mean']:+.1f}bp t {p['t']:+.2f} (n dates {p['n']}) "
             f"-> {'PASS' if ok else 'KILL'}"]
    return ok, "\n".join(lines)


# ---------------------------------------------------------------- combos: return (panel kind, cost, A, B, labels)
def C1(t):
    """TTM squeeze release (>=5 bars in squeeze, any direction) AND IBS<0.2 on the release bar (stocks)."""
    m20, sd = F.sma(t, t.close, 20), F.std(t, t.close, 20)
    atr = F.sma(t, F.true_range(t), 20)
    sq = (2 * sd) < (1.5 * atr)
    fired = (w.lag(t, w.run_count(t, sq)) >= 5) & ~sq
    return fired, ibs(t) < 0.2, "A TTM squeeze release", "B IBS<0.2"


def C2(t):
    """TMO oversold cross-up AND a <= -8% total-return day in bars t-4..t (stocks)."""
    main, sig = F.tmo(t)
    a = (main > sig) & (w.lag(t, main) <= w.lag(t, sig)) & (main <= -10)
    r = t.closeadj / w.lag(t, t.closeadj) - 1
    b = F.rmax(t, (r <= -0.08).astype("float64"), 5) > 0
    return a, b, "A TMO oversold cross-up", "B -8% day in last 5"


def pre_ex(t, k0=2, k1=5):
    """True on bar t when the ticker has a Sharadar dividend ex-date on bars t+k0..t+k1."""
    a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker"])
    a = a[a.action == "dividend"]; a["date"] = pd.to_datetime(a.date)
    ex = pd.Series(t.set_index(["ticker", "date"]).index.isin(pd.MultiIndex.from_frame(a[["ticker", "date"]])), index=t.index)
    out = pd.Series(False, index=t.index)
    for k in range(k0, k1 + 1):
        out |= ex.groupby(t.ticker, sort=False).shift(-k).fillna(False).astype(bool)
    return out


def C3(t):
    """BB lower re-entry AND an ex-date on bars t+2..t+5 (prefs + baby bonds)."""
    return F.F5(t)["F5 BB lower re-entry after >=2 closes below"], pre_ex(t), "A BB lower re-entry", "B ex-date in t+2..t+5"


def C4(t):
    """Officer/director open-market buy filed on bars t-4..t AND 5-session total return <= -5% (stocks)."""
    i = pd.read_parquet(w.STORE / "insiders.parquet", columns=["ticker", "date", "formtype", "isdirector", "isofficer",
                                                               "transactioncode", "securityadcode", "transactionvalue",
                                                               "transactionshares", "transactionpricepershare"])
    ft = i.formtype.astype(str)
    i = i[(ft.str.startswith("4") | ft.str.startswith("RESTATED - 4")) & (i.transactioncode == "P")
          & (i.securityadcode == "NA") & ((i.isdirector == "Y") | (i.isofficer == "Y"))]
    usd = i.transactionvalue.astype(float).fillna(i.transactionshares.astype(float) * i.transactionpricepershare.astype(float))
    i = i[usd > 0]
    fd = pd.MultiIndex.from_arrays([i.ticker, pd.to_datetime(i.date)]).unique()
    # map each filing date onto the first trading bar >= filing date (filings on non-trading days)
    bars = t[["ticker", "date"]].astype({"date": "datetime64[ns]"})
    f = pd.DataFrame({"ticker": fd.get_level_values(0), "date": fd.get_level_values(1).astype("datetime64[ns]")}).sort_values("date")
    m = pd.merge_asof(f, bars.sort_values("date").rename(columns={"date": "bar"}), left_on="date", right_on="bar",
                      by="ticker", direction="forward", tolerance=pd.Timedelta("5D")).dropna()
    hit = pd.Series(t.set_index(["ticker", "date"]).index.isin(pd.MultiIndex.from_arrays([m.ticker, m.bar])), index=t.index)
    a = F.rmax(t, hit.astype("float64"), 5) > 0
    b = t.closeadj / w.lag(t, t.closeadj, 5) - 1 <= -0.05
    return a, b, "A insider buy filed t-4..t", "B 5d return <= -5%"


def C5(t):
    """5-session total return <= -5% AND 5-bar mean volume <= 0.8 x the prior 20 bars' mean (stocks)."""
    v = t.volume.astype("float64")
    v5, v20 = F.sma(t, v, 5), w.lag(t, F.sma(t, v, 20), 5)
    a = t.closeadj / w.lag(t, t.closeadj, 5) - 1 <= -0.05
    return a, v5 <= 0.8 * v20, "A 5d return <= -5%", "B 5d volume <= 0.8x prior 20d"


def C6(t):
    """5-session total return <= -5% AND P/B in the bottom quintile of the day's liquid universe (pb > 0)."""
    d = pd.read_parquet(w.STORE / "daily.parquet", columns=["ticker", "date", "pb"])
    d["date"] = pd.to_datetime(d.date)
    pb = t[["ticker", "date"]].merge(d, on=["ticker", "date"], how="left").pb.to_numpy()
    pb = pd.Series(pb, index=t.index).where(lambda s: s > 0)
    q = pb.where(t.liq).groupby(t.date).rank(pct=True)
    a = t.closeadj / w.lag(t, t.closeadj, 5) - 1 <= -0.05
    return a, q <= 0.2, "A 5d return <= -5%", "B P/B bottom quintile"


def C7(t):
    """IBS < 0.2 AND bar t is one of the last 2 trading days of the month (ETFs)."""
    days = pd.Series(np.sort(t.date.unique()))
    ym = days.dt.to_period("M")
    last2 = set(days[ym != ym.shift(-1)]) | set(days[ym != ym.shift(-2)])
    return ibs(t) < 0.2, t.date.isin(last2), "A IBS<0.2", "B last 2 days of month"


def event_window(t, code: str, k: int = 5):
    """True on bar t when a Sharadar EVENTS row containing `code` is dated on bars t-k+1..t (first bar >= event date)."""
    e = pd.read_parquet(w.STORE / "events.parquet")
    e = e[e.eventcodes.astype(str).str.split("|").apply(lambda c: code in c)]
    f = pd.DataFrame({"ticker": e.ticker, "date": pd.to_datetime(e.date).astype("datetime64[ns]")}).sort_values("date")
    bars = t[["ticker", "date"]].astype({"date": "datetime64[ns]"}).sort_values("date").rename(columns={"date": "bar"})
    m = pd.merge_asof(f, bars, left_on="date", right_on="bar", by="ticker", direction="forward",
                      tolerance=pd.Timedelta("5D")).dropna()
    hit = pd.Series(t.set_index(["ticker", "date"]).index.isin(pd.MultiIndex.from_arrays([m.ticker, m.bar])), index=t.index)
    return F.rmax(t, hit.astype("float64"), k) > 0


def C8(t):
    """Earnings 8-K (item 2.02) on bars t-4..t AND 5-session total return <= -5% (stocks)."""
    b = t.closeadj / w.lag(t, t.closeadj, 5) - 1 <= -0.05
    return event_window(t, "22"), b, "A earnings 8-K in t-4..t", "B 5d return <= -5%"


COMBOS = {"C8": ("stock", 10e-4, C8), "C7": ("etf", 10e-4, C7), "C6": ("stock", 10e-4, C6), "C5": ("stock", 10e-4, C5), "C4": ("stock", 10e-4, C4), "C3": ("pref", 8e-4, C3), "C1": ("stock", 10e-4, C1), "C2": ("stock", 10e-4, C2)}


def main(argv):
    name = argv[0]
    kind, cost, fn = COMBOS[name]
    t = w.add_bench(w.load_panel(kind=kind))
    A, B, la, lb = fn(t)
    ok, txt = run(t, A, B, la, lb, *w.DISC, cost)
    txt = f"{name} [2016-26 discovery, cost {cost*1e4:.0f}bp RT]\n{txt}"
    if ok and "--confirm" in argv:
        _, t2 = run(t, A, B, la, lb, *w.CONF, cost)
        txt += f"\n{name} [CONFIRM 2003-15, one look]\n{t2}"
    print(txt)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as fh:
        fh.write(f"# {name} {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")


if __name__ == "__main__":
    main(sys.argv[1:])
