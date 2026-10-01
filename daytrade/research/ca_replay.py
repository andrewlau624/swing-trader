"""Study Lab-CA: 3x daily-levered market with a 200-day trend exit (round1_prose.md Lab Round 49). French daily data;
2016-26 also with the real UPRO / SPY / BIL (Alpaca adjusted daily closes).

  python -m daytrade.research.ca_replay
"""
from __future__ import annotations

import io
import json
import math

import numpy as np
import pandas as pd

from .bt_replay import OUT as BT


def daily_ff():
    lines = (BT / "F-F_Research_Data_Factors_daily.csv").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(","))
    rows = [l for l in lines[start + 1:] if l.split(",")[0].strip().isdigit()]
    df = pd.read_csv(io.StringIO(lines[start] + "\n" + "\n".join(rows)))
    df = df.rename(columns={df.columns[0]: "d"})
    df["d"] = pd.to_datetime(df.d.astype(str).str.strip(), format="%Y%m%d")
    df = df.set_index("d").astype(float) / 100
    return pd.DataFrame({"mkt": df["Mkt-RF"] + df["RF"], "rf": df["RF"]})


def stats(r, per=252):
    eq = (1 + r).cumprod()
    ann = r.groupby(r.index.to_period("M")).apply(lambda x: (1 + x).prod() - 1)
    return {"cagr": float(eq.iloc[-1] ** (per / len(r)) - 1), "sharpe": float(r.mean() / r.std(ddof=1) * math.sqrt(per)),
            "max_dd": float((eq / eq.cummax() - 1).min()),
            "worst12": float(((1 + ann).rolling(12).apply(np.prod, raw=True) - 1).min())}


def sleeve(d, lev_ret, switch_cost):
    level = (1 + d.mkt).cumprod()
    on = (level > level.rolling(200).mean()).shift(1).fillna(False).astype(bool)
    sw = on.astype(int).diff().abs().fillna(0)
    return pd.Series(np.where(on, lev_ret, d.rf), index=d.index) - sw * switch_cost, on, sw


def run():
    d = daily_ff()
    fin = 0.005 / 252; exp = 0.0095 / 252
    r3 = 3 * d.mkt - 2 * (d.rf + fin) - exp
    P = (("judged", "1963-07-01", "2015-12-31"), ("h1", "1963-07-01", "1989-12-31"), ("h2", "1990-01-01", "2015-12-31"),
         ("ref 1927-63", "1927-01-01", "1963-06-30"), ("ref 2016-26 (sim)", "2016-01-01", "2026-08-31"))
    res = {}
    for tier, sc in (("1x", 0.0010), ("2x", 0.0020)):
        s, on, sw = sleeve(d, r3, sc)
        res[tier] = {}
        for n, a, b in P:
            m = (d.index >= a) & (d.index <= b)
            res[tier][n] = {"sleeve": stats(s[m]), "market": stats(d.mkt[m]), "levered_bh": stats(r3[m]),
                            "in_market": float(on[m].mean()), "switches_per_yr": float(sw[m].sum() / (m.sum() / 252))}
    # 2016-26 with the real ETFs (signal on SPY's own 200-day average)
    try:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        from swingtrader.daily.marketdata import trade_date
        from . import as_replay as A
        data, _ = A._clients()
        x = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=["UPRO", "SPY", "BIL"], timeframe=TimeFrame.Day,
                                                 start=pd.Timestamp("2015-01-01", tz="UTC"), end=pd.Timestamp("2026-09-30T23:00", tz="UTC"),
                                                 feed="sip", adjustment="all")).df.reset_index()
        x["date"] = trade_date(x["timestamp"])
        C = x.pivot_table(index="date", columns="symbol", values="close").sort_index()
        R = C.pct_change()
        on = (C.SPY > C.SPY.rolling(200).mean()).shift(1).fillna(False).astype(bool)
        sw = on.astype(int).diff().abs().fillna(0)
        real = pd.Series(np.where(on, R.UPRO, R.BIL), index=R.index) - sw * 0.0010
        m = R.index >= pd.Timestamp("2016-01-01")
        res["real 2016-26 (UPRO/SPY/BIL, 1x)"] = {"sleeve": stats(real[m].dropna()), "spy": stats(R.SPY[m].dropna()),
                                                  "upro_bh": stats(R.UPRO[m].dropna()), "switches_per_yr": float(sw[m].sum() / (m.sum() / 252))}
    except Exception as exc:
        res["real 2016-26"] = f"unavailable: {type(exc).__name__}"
    r2, r1 = res["2x"], res["1x"]
    ok = (r2["h1"]["sleeve"]["cagr"] >= r2["h1"]["market"]["cagr"] and r2["h2"]["sleeve"]["cagr"] >= r2["h2"]["market"]["cagr"]
          and r1["h1"]["sleeve"]["sharpe"] > r1["h1"]["market"]["sharpe"] and r1["h2"]["sleeve"]["sharpe"] > r1["h2"]["market"]["sharpe"]
          and r1["judged"]["sleeve"]["worst12"] > -0.50 and r1["judged"]["sleeve"]["max_dd"] > r1["judged"]["levered_bh"]["max_dd"])
    res["verdict"] = "PASS" if ok else "DEAD"
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
