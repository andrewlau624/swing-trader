"""PREF-EX execution economics on official SIP crosses 2021-26 (rows from pref_cross.py).

Two executable forms (Schwab has MARKET_ON_CLOSE but no market-on-open; directed open routes are refused by the API):
  CO: buy T-1 closing cross, sell T opening cross (+div)   -- needs an open-auction fill
  CC: buy T-1 closing cross, sell T closing cross (+div)   -- MOC on both legs
Capacity: our order per leg <= p x that leg's auction $ (p = 1/2/5/10/20%). Two size bases: the event's own cross $
(contemporaneous, optimistic) and an ex-ante estimate = median(cross $ / 20d median daily $vol) x the name's 20d $vol.
Execution: flat degradation 0-25bp round trip, asymmetric (close vs open leg), and a spread-linked impact model
(per leg: half the median quoted spread x sqrt(p / 1%) x 1/10, capped at the half spread).
Accounts $1k..$25k: each ex-night the account is split equally across that night's events, each capped by capacity,
whole shares at the T-1 close price. Roth: no margin, no leverage.

    PYTHONPATH=. .venv/bin/python -m research.sim.pref_exec
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/pref"
OUT = pathlib.Path(__file__).resolve().parent / "pref_exec_out.txt"
S = pathlib.Path.home() / "data" / "sharadar"
HALF_SPR = {"close": 0.00192, "open": 0.00441}   # median quoted spread / 2 at 15:59 and 09:30 (pref_quotes.py, n 296)
PARTS = [0.01, 0.02, 0.05, 0.10, 0.20]
ACCTS = [1e3, 3e3, 5e3, 1e4, 2.5e4]


def load() -> pd.DataFrame:
    df = pd.read_parquet(D / "cross_rows.parquet")
    ev = pd.read_parquet(D / "events.parquet")[["ticker", "date", "pc", "div"]].rename(columns={"ticker": "t", "date": "d"})
    df = df.merge(ev, on=["t", "d"], how="left")
    t = ds.dataset(S / "tickers.parquet").to_table(
        columns=["table", "ticker", "siccode", "firstpricedate"]).to_pandas()
    t = t[t.table == "SEP"].drop_duplicates("ticker")
    df = df.merge(t.rename(columns={"ticker": "t"})[["t", "siccode", "firstpricedate"]], on="t", how="left")
    df["age_y"] = (df.d - pd.to_datetime(df.firstpricedate)).dt.days / 365.25
    # ex-ante auction size: typical cross $ as a fraction of 20d median daily $vol, applied to the name's own $vol
    kc, ko = (df.close_usd / df.dv).median(), (df.open_usd / df.dv).median()
    df["cap_close_ea"], df["cap_open_ea"] = kc * df.dv, ko * df.dv
    df.attrs["k"] = (kc, ko)
    return df


def stat(x: pd.Series, d: pd.Series) -> str:
    day = x.groupby(d).mean()
    t = day.mean() / day.std() * np.sqrt(len(day)) if len(day) > 2 else np.nan
    return f"mean {x.mean()*1e4:+6.1f} med {x.median()*1e4:+6.1f} hit {(x > 0).mean():.2f} t {t:+5.1f} n {len(x)}"


def account(df: pd.DataFrame, col: str, acct: float, p: float, cost_close: float, cost_open: float,
            exante: bool, impact: bool) -> tuple[float, float, float]:
    """(gross $/yr, %/yr, mean share of the account deployed on ex-nights) for one account size."""
    yrs = (df.d.max() - df.d.min()).days / 365.25
    exit_cap = "open" if col == "co" else "close"
    pnl, used = 0.0, []
    for _, g in df.groupby("d"):
        cin = (g.cap_close_ea if exante else g.close_usd).values * p
        cout = (g.cap_open_ea if exante else g.open_usd).values * p if exit_cap == "open" else cin
        cap = np.minimum(cin, cout)
        alloc, rem = np.zeros(len(g)), acct
        for k, i in enumerate(np.argsort(cap)):
            a = min(cap[i], rem / (len(g) - k))
            alloc[i] = np.floor(a / g.pc.values[i]) * g.pc.values[i]   # whole shares
            rem -= alloc[i]
        r = g[col].values - cost_close - (cost_open if col == "co" else cost_close)
        if impact:
            sp = np.sqrt(p / 0.01) / 10
            r = r - min(sp, 1) * HALF_SPR["close"] - min(sp, 1) * HALF_SPR[exit_cap]
        pnl += (alloc * r).sum()
        used.append(alloc.sum() / acct)
    return pnl / yrs, pnl / yrs / acct, float(np.mean(used))


def main():
    df = load()
    kc, ko = df.attrs["k"]
    L = [f"PREF-EX execution economics, official crosses {df.d.min().date()}..{df.d.max().date()}: {len(df)} events, "
         f"{df.d.nunique()} ex-nights ({df.d.nunique() / ((df.d.max()-df.d.min()).days/365.25):.0f}/yr)",
         f"auction $: close median ${df.close_usd.median():,.0f}, open median ${df.open_usd.median():,.0f}; "
         f"ex-ante size = {kc:.3f} (close) / {ko:.3f} (open) x 20d median daily $vol", ""]

    L.append("== 1. Per-event edge after flat round-trip degradation (bp) ==")
    for col in ["co", "cc"]:
        for c in [0, 5, 10, 15, 20, 25]:
            L.append(f"{col.upper()} -{c:2d}bp: " + stat(df[col] - c / 1e4, df.d))
        L.append("")
    L.append("== 2. Asymmetric degradation (close leg / open leg, bp) for CO ==")
    for cc_, oo in [(0, 10), (0, 20), (0, 30), (0, 44), (5, 20), (10, 30), (19, 44)]:
        L.append(f"close {cc_:2d} / open {oo:2d}: " + stat(df.co - (cc_ + oo) / 1e4, df.d))
    L.append("  (19/44 = paying the full median half-spread on both legs = no auction at all)")
    L.append("")

    L.append("== 3. Capacity per ex-night ($ deployable, all events that night) ==")
    for p in PARTS:
        for exante, tag in [(False, "event cross $"), (True, "ex-ante $")]:
            cin = (df.cap_close_ea if exante else df.close_usd) * p
            cout_o = (df.cap_open_ea if exante else df.open_usd) * p
            co_cap = np.minimum(cin, cout_o).groupby(df.d).sum()
            cc_cap = cin.groupby(df.d).sum()
            L.append(f"p {p:4.0%} {tag:13s}: per-event median CO ${np.minimum(cin, cout_o).median():7,.0f} | per night CO "
                     f"median ${co_cap.median():8,.0f} p25 ${co_cap.quantile(.25):7,.0f} | CC median ${cc_cap.median():8,.0f}")
    L.append("")

    L.append("== 4. Account economics (Roth, whole shares, ex-ante capacity) ==")
    hdr = "form p     cost       " + " ".join(f"{'$'+format(int(a),','):>16s}" for a in ACCTS)
    L.append(hdr)
    for col in ["co", "cc"]:
        for p in PARTS:
            for lab, cc_, oo, imp in [("0bp", 0, 0, False), ("10bp", 0.0005, 0.0005, False),
                                      ("20bp", 0.001, 0.001, False), ("impact", 0, 0, True)]:
                cells = []
                for a in ACCTS:
                    dol, pct, use = account(df, col, a, p, cc_, oo, True, imp)
                    cells.append(f"${dol:6,.0f} {pct*100:5.1f}% {use*100:3.0f}%")
                L.append(f"{col.upper()}  {p:4.0%} {lab:6s} " + " ".join(f"{c:>16s}" for c in cells))
        L.append("")
    L.append("  cell = gross $/yr, %/yr of the account, mean share deployed on ex-nights")
    L.append("")

    L.append("== 5. Event partitions (economically motivated; descriptive, CO and CC) ==")
    df["sic"] = pd.to_numeric(df.siccode, errors="coerce")
    parts = {
        "yield/payment": pd.qcut(df.yld, 3, labels=["low", "mid", "high"]),
        "price vs $25 par": pd.cut(df.pc, [0, 20, 24, 25.5, 100], labels=["<20 (deep disc)", "20-24", "24-25.5", ">25.5"]),
        "auction liquidity (20d $vol)": pd.qcut(df.dv, 3, labels=["thin", "mid", "liquid"]),
        "issuer type": df.sic.map(lambda s: "REIT" if s == 6798 else "bank/credit" if 6020 <= s <= 6199
                                  else "insurance" if 6300 <= s <= 6411 else "utility" if 4900 <= s <= 4999 else "other"),
        "years since first price": pd.cut(df.age_y, [-1, 1, 3, 100], labels=["<1y", "1-3y", ">3y"]),
        "dividend $ per share": pd.qcut(df["div"], 3, labels=["small", "mid", "large"]),
    }
    for name, grp in parts.items():
        L.append(f"-- {name}")
        for k, x in df.groupby(grp, observed=True):
            L.append(f"   {str(k):18s} CO {stat(x.co, x.d)} | CC mean {x.cc.mean()*1e4:+6.1f} med {x.cc.median()*1e4:+6.1f}")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
