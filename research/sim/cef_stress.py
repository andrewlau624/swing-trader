"""CEF-STRESS (N 1071): do CEF-RV entries made in broad-market stress earn more excess per trade than normal entries?
Also: overlap of CRASH-C's blowout decile with CEF-RV (question 1, descriptive) and today's state (question 4).

Pre-registration: round1_prose.md "Study CEF-STRESS". Panel: Nasdaq Fund Network daily NAV 2007-04..now (cef_nasdaq_hist.py),
Friday rows, price = Sharadar SFP closeunadj (fallback Nasdaq close after the SFP end). Live funds only (survivorship stated).
Reuses cef_rv.build_trades/load_sfp (frozen CEF-RV rule), cef_alpha.universe/window (EW CEF incl. delisted), cef_txt.spread_stats.

    python3 research/sim/cef_stress.py     # -> data/research/program/cef_stress_out.txt
"""
from __future__ import annotations

import json
import pathlib
import sys
import types

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
STORE = pathlib.Path.home() / "data" / "sharadar"
if "sharadar" not in sys.modules:   # cef_alpha.universe imports sharadar.tickers (server package); read the parquet here
    sys.modules["sharadar"] = types.SimpleNamespace(tickers=lambda: pd.read_parquet(STORE / "tickers.parquet"))
from research.sim import cef_alpha  # noqa: E402
from research.sim.cef_rv import build_trades, load_sfp  # noqa: E402
from research.sim.cef_txt import spread_stats  # noqa: E402
from swingtrader.daily.cef_nav import hist  # noqa: E402

CEF = ROOT / "data/research/cefconnect"
OUT = ROOT / "data/research/program/cef_stress_out.txt"
COST = 0.005
DD_STRESS, WIDEN_STRESS = -0.10, -2.0          # frozen (pre-reg)
JUDGE = ("2008-01-01", "2015-12-31"); MID = "2012-01-01"
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); lines.append(s)


def weekly_panel() -> pd.DataFrame:
    d = pd.read_parquet(CEF / "nasdaq_daily.parquet")
    d = d[d.date.dt.weekday == 4]
    tk = sorted(d.ticker.unique())
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "closeunadj"], filters=[("ticker", "in", tk)])
    f["date"] = pd.to_datetime(f["date"]); f = f.drop_duplicates(["ticker", "date"])
    d = d.merge(f, on=["ticker", "date"], how="left")
    d["price"] = d.closeunadj.fillna(d.px_nasdaq)
    d["disc"] = d.price / d.nav - 1
    d.loc[(d.disc < -0.6) | (d.disc > 1.0), "disc"] = np.nan      # frozen data-error screen
    return d.dropna(subset=["disc"])[["ticker", "date", "disc", "nav", "price"]].sort_values(["ticker", "date"])


def check_vs_server(p: pd.DataFrame) -> None:
    s = json.loads((CEF / "panel_server.json").read_text())
    rows = [(t, pd.Timestamp(r[0]), r[1]) for t, v in s.items() for r in v]
    s = pd.DataFrame(rows, columns=["ticker", "date", "disc_s"])
    m = p.merge(s, on=["ticker", "date"])
    e = (m.disc - m.disc_s).abs()
    say(f"data check vs server panel (2023-08..2026-10): {len(m)} rows, median |diff| {e.median()*100:.2f}pt, "
        f">1pt {np.mean(e > .01):.1%}")


def main() -> int:
    p = weekly_panel()
    say(f"Study CEF-STRESS (N 1071). panel {p.ticker.nunique()} funds, {p.date.min().date()}..{p.date.max().date()} (LIVE funds only)")
    check_vs_server(p)
    wk = p.pivot_table(index="date", columns="ticker", values="disc") * 100
    med = wk.median(axis=1); widen = med - med.rolling(52, min_periods=40).median()
    ew, spy = cef_alpha.universe()
    sdd = spy / spy.rolling(252, min_periods=200).max() - 1

    def at(series, dates):
        return series.reindex(pd.DatetimeIndex(dates), method="ffill").to_numpy()

    # ---- CEF-RV trades on the rebuilt panel (frozen rule) ----
    fS = load_sfp(sorted(p.ticker.unique()), lo=pd.Timestamp("2007-01-01"), hi=pd.Timestamp("2026-10-05"))
    tr = build_trades(p[["ticker", "date", "disc"]], fS)
    tr["edate"] = pd.to_datetime(tr.edate); tr["xdate"] = pd.to_datetime(tr.xdate)
    a, b = tr.edate.to_numpy("datetime64[ns]"), tr.xdate.to_numpy("datetime64[ns]")
    tr["ew"] = cef_alpha.window(ew, a, b); tr["spyr"] = cef_alpha.window(spy, a, b)
    tr = tr.dropna(subset=["ew"]).reset_index(drop=True)
    tr["net"] = tr.ret - COST; tr["exc"] = tr.net - tr.ew
    tr["dd"] = at(sdd, tr.edate); tr["widen"] = widen.reindex(pd.DatetimeIndex(tr.edate)).to_numpy()
    tr["s_dd"] = tr.dd <= DD_STRESS; tr["s_wd"] = tr.widen <= WIDEN_STRESS
    tr["stress"] = tr.s_dd | tr.s_wd
    tr["month"] = tr.edate.dt.strftime("%Y-%m")
    tr.to_csv(CEF / "cef_stress_trades.csv", index=False)

    def block(lab, t, cost_mult_stress=1):
        if t.stress.sum() < 5 or (~t.stress).sum() < 5:
            say(f"  {lab}: too few (stress {t.stress.sum()}, normal {(~t.stress).sum()})"); return None
        x = t.exc.to_numpy() - np.where(t.stress, (cost_mult_stress - 1) * 2 * COST, 0)
        s = spread_stats(x, ~t.stress.to_numpy(), t.month.to_numpy())
        xs = x[t.stress.to_numpy()]
        o = np.argsort(-xs)
        ex5 = np.delete(xs, o[:5]).mean() - x[~t.stress.to_numpy()].mean()
        say(f"  {lab}: stress n {s['n_keep']} ({t[t.stress].month.nunique()} months) exc {xs.mean()*1e4:+.0f}bp med {np.median(xs)*1e4:+.0f} "
            f"hit {s['hit_keep']:.0%} | normal n {s['n_drop']} exc {x[~t.stress.to_numpy()].mean()*1e4:+.0f}bp hit {s['hit_drop']:.0%} | "
            f"DIFF {s['spread']*1e4:+.0f}bp t_month {s['t']:.2f} med-diff {s['med']*1e4:+.0f} ex-top5 {ex5*1e4:+.0f} | raw net stress "
            f"{t[t.stress].net.mean()*1e4:+.0f} vs {t[~t.stress].net.mean()*1e4:+.0f}bp")
        return dict(diff=s["spread"], t=s["t"], med=s["med"], ex5=ex5)

    say("\n== Q2 CEF-STRESS: excess = CEF-RV net (50bp RT) - EW CEF universe incl. delisted over the same hold ==")
    J = tr[(tr.edate >= JUDGE[0]) & (tr.edate <= JUDGE[1])]
    say(f"JUDGE {JUDGE[0][:4]}-{JUDGE[1][:4]} (pre-CEF-RV-selection; 2008-14 was read in aggregate by CEF-OOS/SPY-dip control; 2015 untouched)")
    g = block("all judge", J)
    h1 = block("half 2008-11", J[J.edate < MID]); h2 = block("half 2012-15", J[J.edate >= MID])
    c2 = block("cost 2x on stress entries", J, 2); c3 = block("cost 3x on stress entries", J, 3)
    block("2015 only (untouched)", J[J.edate >= "2015-01-01"])
    block("ex-2008-09", J[(J.edate < "2008-01-01") | (J.edate >= "2010-01-01")])
    for comp in ("s_dd", "s_wd"):
        Jc = J.assign(stress=J[comp]); block(f"component {comp} only (report)", Jc)
    if g:
        ok = dict(diff=g["diff"] >= .01, t=g["t"] >= 2, med=g["med"] > 0, halves=bool(h1 and h2 and h1["diff"] > 0 and h2["diff"] > 0),
                  ex5=g["ex5"] > 0, cost3=bool(c3 and c3["diff"] > 0))
        say(f"GATE: {'PASS' if all(ok.values()) else 'KILL'} " + " ".join(f"{k}={'Y' if v else 'n'}" for k, v in ok.items()))
    say("\nREPORT (CEF-RV selection period, not judged):")
    block("2016-2026", tr[tr.edate >= "2016-01-01"])
    block("2016-2020", tr[(tr.edate >= "2016-01-01") & (tr.edate < "2021-01-01")])
    block("2021-2026", tr[tr.edate >= "2021-01-01"])
    for y, t in tr.assign(y=tr.edate.dt.year).groupby("y"):
        say(f"    {y}: n {len(t)} stress {t.stress.mean():.0%} exc stress {t[t.stress].exc.mean()*1e4:+.0f} normal {t[~t.stress].exc.mean()*1e4:+.0f}bp")
    turns = 52 / tr.hold_weeks.mean()
    share = tr.stress.mean(); yrs = (tr.edate.max() - tr.edate.min()).days / 365.25
    say(f"stress share of entries {share:.0%}; stress entries/yr {tr.stress.sum()/yrs:.0f}; mean hold {tr.hold_weeks.mean():.1f}wk ({turns:.1f} turns/yr)")

    # ---- Q1 overlap: CRASH-C trigger on the rebuilt panel ----
    say("\n== Q1 overlap: CRASH-C fires (SPY <= -20% from 252d high AND EW median disc <= 52w median - 3pt; 52w lockout) ==")
    z = wk - wk.rolling(52, min_periods=40).median()
    fires, last = [], None
    for d in wk.index:
        v = at(sdd, [d])[0]
        if last is not None and (d - last).days < 364: continue
        if np.isfinite(v) and v <= -0.20 and widen.get(d, np.nan) <= -3.0:
            fires.append(d); last = d
    for d in fires:
        zz = z.loc[d].dropna(); zz = zz[wk.loc[:d].notna().sum().reindex(zz.index) >= 52]
        sel = set(zz[zz <= zz.quantile(.10)].index)
        win = tr[(tr.edate > d - pd.Timedelta(weeks=8)) & (tr.edate <= d + pd.Timedelta(weeks=8))]
        held = tr[(tr.edate <= d) & (tr.xdate > d)]
        cov = len(sel & (set(win.ticker) | set(held.ticker))) / max(len(sel), 1)
        rv_in = win[win.edate <= d]
        say(f"  fire {d.date()}: decile {len(sel)} of {len(zz)}; {cov:.0%} of the decile is a CEF-RV position/entry within +-8w; "
            f"CEF-RV entries in the 8w up to the fire {len(rv_in)} ({rv_in.ticker.nunique()} funds, {rv_in.ticker.isin(sel).mean():.0%} in decile); "
            f"stress flag on those entries {rv_in.stress.mean():.0%}")
        # return comparison on the decile: CRASH-C tranche-0 hold vs the CEF-RV trade covering the fire
        pre = wk.loc[:d].tail(52).median()
        rr = []
        for t in sel:
            ftt = fS[fS.ticker == t].set_index("dt")["closeadj"]
            i0 = ftt.index.searchsorted(d, side="right")
            if i0 >= len(ftt): continue
            w = wk.loc[d:, t].dropna().iloc[1:]
            hit = w[(w >= pre[t]) | ((w.index - d).days > 260)]
            if hit.empty: continue
            i1 = ftt.index.searchsorted(hit.index[0], side="right")
            if i1 >= len(ftt): continue
            cc = ftt.iloc[i1] / ftt.iloc[i0] - 1
            rv = held[held.ticker == t]
            rv = rv if len(rv) else win[(win.ticker == t) & (win.edate > d)]
            rr.append((cc, rv.ret.iloc[0] if len(rv) else np.nan))
        rr = np.array(rr)
        if len(rr):
            ok = np.isfinite(rr[:, 1])
            say(f"    decile returns: CRASH-C tranche0 mean {rr[:,0].mean()*100:+.1f}%; matched CEF-RV trade mean {np.nanmean(rr[:,1])*100:+.1f}% "
                f"(n {ok.sum()} of {len(rr)}); corr {np.corrcoef(rr[ok,0], rr[ok,1])[0,1] if ok.sum() > 2 else float('nan'):.2f}")

    # ---- Q4: today ----
    say("\n== Q4 now (Nasdaq NAV daily to latest; SPY from Nasdaq) ==")
    d = pd.read_parquet(CEF / "nasdaq_daily.parquet")
    last = d.date.max(); today = d[d.date == last].dropna(subset=["px_nasdaq"])
    today = today.assign(disc=(today.px_nasdaq / today.nav - 1) * 100).set_index("ticker").disc
    hist52 = wk.loc[wk.index > last - pd.Timedelta(weeks=52)]
    q10, m52 = hist52.quantile(.10), hist52.median()
    h = hist("SPY", "etf", (last - pd.Timedelta(days=400)).date().isoformat())
    sp = pd.Series(h).sort_index(); sp.index = pd.to_datetime(sp.index)
    say(f"latest NAV day {last.date()}: funds {len(today)}; EW median disc {today.median():+.2f}% vs 52w median of weekly medians "
        f"{med[med.index > last - pd.Timedelta(weeks=52)].median():+.2f}% (widening {today.median() - med[med.index > last - pd.Timedelta(weeks=52)].median():+.2f}pt; "
        f"stress >= 2pt, CRASH-C >= 3pt)")
    say(f"SPY {sp.iloc[-1]:.2f} on {sp.index[-1].date()}, {(sp.iloc[-1]/sp.tail(252).max()-1)*100:+.1f}% from 252d high (stress <= -10%, CRASH-C <= -20%)")
    say("weekly EW median disc, last 8 weeks: " + ", ".join(f"{k.date()} {v:+.2f}" for k, v in med.tail(8).items()))
    zt = (today - m52.reindex(today.index)).dropna()
    sig = today[today <= q10.reindex(today.index)].dropna()
    say(f"funds at/below own 52w 10th pct today (CEF-RV-style signal on a daily print): {len(sig)} of {len(today)} "
        f"({len(sig)/len(today):.0%}; base rate ~10% by construction)")
    say("widest vs own 52w median (z, pts): " + ", ".join(f"{k} {v:+.1f} (disc {today[k]:+.1f})" for k, v in zt.sort_values().head(15).items()))
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
