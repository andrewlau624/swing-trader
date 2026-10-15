"""Diagnostic (no N): SPY-over-hold and beta adjustment of CEF-RV and the NAV-fall arm, 1999-2014 and 2016-26.
    PYTHONPATH=. .venv/bin/python research/sim/cef_beta_diag.py
"""
import numpy as np, pandas as pd
from research.sim.cef_oos import navtr26, LO, HI, COST
from research.sim.cef_rv import load_sfp
from research.sim.cef_txt import tercile_drop, spread_stats
for name, f in (("1999-2014", "data/research/cefconnect/cef_rv_trades_1999_2014.csv"), ("2016-2026", "data/research/cefconnect/cef_rv_trades.csv")):
    tr = pd.read_csv(f, parse_dates=["edate", "xdate"])
    tr = tr[tr.edate >= ("1999" if name[0] == "1" else "2016")]
    tr["edate"] = tr.edate.astype("datetime64[ns]"); tr["xdate"] = tr.xdate.astype("datetime64[ns]")
    lo, hi = (LO, HI) if name[0] == "1" else (pd.Timestamp("2015-01-01"), pd.Timestamp("2026-10-05"))
    fS = load_sfp(sorted(tr.ticker.unique()) + ["SPY"], lo, hi)
    spy = fS[fS.ticker == "SPY"].set_index("dt")["closeadj"]
    px = lambda d: spy.asof(d)
    tr["spy"] = [px(x) / px(e) - 1 for e, x in zip(tr.edate, tr.xdate)]
    nv = navtr26(fS)
    pan = pd.read_parquet("data/research/cefconnect/cef_panel.parquet")[["ticker","date","nav"]]
    pan["date"] = pan.date.astype("datetime64[ns]")
    m = pd.merge_asof(tr.sort_values("edate"), nv.sort_values("date"), left_on="edate", right_on="date", by="ticker", direction="backward", tolerance=pd.Timedelta(days=10)).dropna(subset=["navtr26"])
    m = m.merge(pan.rename(columns={"date":"edate","nav":"nav_in"}), on=["ticker","edate"], how="left").merge(pan.rename(columns={"date":"xdate","nav":"nav_out"}), on=["ticker","xdate"], how="left")
    m["navret"] = m.nav_out / m.nav_in - 1
    m = m.sort_values("edate").reset_index(drop=True)
    yr = m.edate.dt.year; wk = m.edate.dt.strftime("%G-%V").to_numpy()
    low = tercile_drop(m.navtr26, yr, "low")
    r = m.ret.to_numpy() - COST
    for lab, x in (("raw", r), ("minus SPY", r - m.spy.to_numpy()), ("minus beta*SPY", None)):
        if x is None:
            b = np.polyfit(m.spy, r, 1)[0]; x = r - b * m.spy.to_numpy(); lab = f"minus {b:.2f}*SPY"
        s = spread_stats(x, ~low, wk)
        print(f"{name} {lab:16s} LOW-rest {s['spread']*1e4:+.0f}bp t {s['t']:.2f}")
    print(f"{name} SPY over hold: LOW {m.spy[low].mean()*1e4:+.0f} rest {m.spy[~low].mean()*1e4:+.0f}; price-NAV over hold (no dist): LOW {m.navret[low].mean()*1e4:+.0f} rest {m.navret[~low].mean()*1e4:+.0f}")
    from research.sim.cef_txt import clus_t
    b = np.polyfit(m.spy, r, 1)[0]; a = r - b * m.spy.to_numpy()
    print(f"{name} ALL CEF-RV: net {r.mean()*1e4:+.0f} SPY/hold {m.spy.mean()*1e4:+.0f} beta {b:.2f} alpha {a.mean()*1e4:+.0f}bp t {clus_t(a, wk):.2f} median {np.median(a)*1e4:+.0f}")
