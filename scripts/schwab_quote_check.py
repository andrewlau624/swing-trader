"""Compare Schwab real-time quotes with Alpaca (IEX) for liquid names. Run it
during market hours; it changes nothing.

  python scripts/schwab_quote_check.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from swingtrader.daily import marketdata as md

SYMS = "SPY QQQ AAPL MSFT NVDA TSLA AMD SMH XLE XBI RGTI SOUN PLTR COIN MARA SGOV".split()


def main():
    s = md.schwab_rows(SYMS, max_age_min=1e9)
    a = md.live_rows(SYMS, max_age_min=1e9)
    print(f"Schwab returned {len(s)}/{len(SYMS)} symbols, Alpaca {len(a)}/{len(SYMS)}\n")
    if s.empty:
        print("Schwab gave no usable quotes. Before 09:30 ET that is expected: its day")
        print("high/low stay 0 until the regular session opens. Run this during market hours.")
        return
    df = s.join(a, lsuffix="_schwab", rsuffix="_alpaca", how="outer")
    for c in ("price", "high", "low"):
        df[f"{c}_diff_bp"] = (df[f"{c}_schwab"] / df[f"{c}_alpaca"] - 1) * 1e4
    pd.set_option("display.width", 200)
    print(df[["price_schwab", "price_alpaca", "price_diff_bp", "high_schwab", "high_alpaca",
              "low_schwab", "low_alpaca", "trade_age_min_schwab"]].round(3).to_string())
    print("\nExpect: prices within a few bp; Schwab high >= Alpaca high and low <= Alpaca low")
    print("(IEX sees only its own trades, so its range is narrower). A Schwab range far wider")
    print("than the stock's regular session would mean extended-hours prints are included.")


if __name__ == "__main__":
    main()
