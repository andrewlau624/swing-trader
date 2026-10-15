"""Study MFLW runner (pre-reg research/drafts/round1_prose.md N 865).

FINRA customer margin-debt monthly state -> next-month SPY. Deleveraging cascade family.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.mflw
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/mflw_out.txt"
B = 1e4


def margin() -> pd.Series:
    f = ROOT / "data/research/finra/margin.xlsx"
    d = pd.read_excel(f, sheet_name="Customer Margin Balances")
    d = d.rename(columns={d.columns[0]: "ym", d.columns[1]: "debit"})
    s = pd.Series(d["debit"].astype(float).values,
                  index=pd.to_datetime(d["ym"].astype(str) + "-01") + pd.offsets.MonthEnd(0),
                  name="debit").dropna().sort_index()
    return s


def spy_month() -> pd.Series:
    from sharadar import prices as SP
    p = SP(["SPY"], adjust="raw").reset_index()
    p["date"] = p["date"].astype("datetime64[ns]")
    c = p.set_index("date")["close"].astype(float)
    return c.resample("ME").last()


def main():
    m, spx = margin(), spy_month()
    idx = m.index.union(spx.index)
    D = pd.DataFrame({"debit": m.reindex(idx), "px": spx.reindex(idx)}, index=idx)
    D = D.dropna()
    D["m"] = np.log(D["debit"])
    D["d3"] = D["m"] - D["m"].shift(3)
    D["ma6"] = D["px"].rolling(6).mean()
    D["r1"] = D["px"].shift(-1) / D["px"] - 1
    D["cascade"] = (D["d3"] <= -0.10) & (D["px"] < D["ma6"])
    D["euphoria"] = (D["d3"] >= 0.10) & (D["px"] > D["ma6"])
    D = D.dropna(subset=["d3", "r1"])

    parts = ["Study MFLW: FINRA margin-debt monthly state -> next-month SPY",
             "CASCADE = d3(log debt, 3m) <= -10% AND SPY < 6m mean -> LONG next month (bounce after forced liquidation)",
             "EUPHORIA = d3 >= +10% AND SPY > 6m mean -> SHORT next month (leverage peak)",
             "net 1bp/side; shock 3bp; monthly t", ""]
    for nm, col, dr in (("cascade_long", "cascade", 1.0), ("euphoria_short", "euphoria", -1.0)):
        sub = D[D[col]].dropna(subset=["r1"]).copy()
        x = sub.copy()
        x["net"] = dr * x["r1"] - 2e-4
        t = x["net"].mean() / x["net"].std() * np.sqrt(len(x)) if x["net"].std() > 0 else np.nan
        k = len(x) // 2
        x = x.sort_index()
        ex5 = x.nsmallest(max(len(x) - 5, 1), "net")["net"].mean()
        parts.append(f"  {nm:14s} n={len(x):3d} freq={len(x)/len(D)*100:4.1f}% net={x['net'].mean()*B:6.2f}%/mo t={t:5.2f} "
                     f"med={x['net'].median()*B:6.2f} ex5={ex5*B:6.2f} halves={x['net'].iloc[:k].mean()*B:6.2f}/{x['net'].iloc[k:].mean()*B:6.2f} "
                     f"shock={(dr*x['r1']-6e-4).mean()*B:6.2f} hit={(x['net']>0).mean()*100:3.0f}%")
        parts.append("    events: " + " ".join(str(d.date())[:7] for d in x.index))
        # continuation mirror
        xm = sub.copy(); xm["net"] = -dr * xm["r1"] - 2e-4
        tm = xm["net"].mean() / xm["net"].std() * np.sqrt(len(xm)) if xm["net"].std() > 0 else np.nan
        parts.append(f"    mirror(continuation) net={xm['net'].mean()*B:6.2f}%/mo t={tm:5.2f}")
    # descriptive: worst drawdown windows
    parts.append("  largest 3m debt contractions (context):")
    for d, row in D.nsmallest(6, "d3")[["d3", "r1"]].iterrows():
        parts.append(f"    {d.date()}: d3={row['d3']*100:.1f}% next-month SPY={row['r1']*100:+.1f}%")
    text = "\n".join(parts) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
