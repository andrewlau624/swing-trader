"""Study EF data: SSGA navhist (NAV, shares outstanding) + daily OHLC. No returns/outcomes here.

    PYTHONPATH=. .venv/bin/python -m research.sim.etf_flow_data          # fetch + build + coverage
xlsx parsing needs openpyxl, which is not in the project venv: run `convert()` with any python that has it
(the build step falls back to the cached CSVs). Prices: Yahoo chart API (2007+; open adjusted by adjclose/close),
cross-checked against the Alpaca SIP panel (2016+) in `coverage()`.
"""
from __future__ import annotations
import json, subprocess
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "research" / "etf_flow"
URL = "https://www.ssga.com/us/en/intermediary/etfs/library-content/products/fund-data/etfs/us/navhist-us-en-{}.xlsx"
TICKERS = ("SPY MDY DIA XLB XLE XLF XLI XLK XLP XLU XLV XLY XLRE XLC XBI KRE XOP XRT XHB XME "
           "JNK SJNK SPSB SPIB SPLB BIL GLD").split()


def fetch_nav(t):
    subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "-o", str(D / f"{t.lower()}.xlsx"), URL.format(t.lower())], check=True)


def convert(t):                       # needs openpyxl
    x = pd.read_excel(D / f"{t.lower()}.xlsx", header=None, skiprows=4, usecols=[0, 1, 2, 3])
    x.columns = ["date", "nav", "so", "tna"]
    x["date"] = pd.to_datetime(x["date"], format="%d-%b-%Y", errors="coerce")
    for c in ("nav", "so", "tna"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["date"]).sort_values("date").drop_duplicates("date")
    x.to_csv(D / f"nav_{t}.csv", index=False)
    return x


def fetch_px(t, start="2007-01-01"):
    p1 = int(pd.Timestamp(start).timestamp()); p2 = int(pd.Timestamp.now().timestamp())
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={p2}&interval=1d&events=div,split"
    r = json.loads(subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", u], capture_output=True, text=True).stdout)
    res = r["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q["volume"],
                       "adjclose": res["indicators"]["adjclose"][0]["adjclose"]},
                      index=pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize())
    df.index.name = "date"
    df = df.dropna(subset=["close"])
    df.to_csv(D / f"px_{t}.csv")
    return df


def load_nav(t): return pd.read_csv(D / f"nav_{t}.csv", parse_dates=["date"]).set_index("date")
def load_px(t): return pd.read_csv(D / f"px_{t}.csv", parse_dates=["date"]).set_index("date")


def coverage():
    rows = []
    for t in TICKERS:
        try:
            n, p = load_nav(t), load_px(t)
        except FileNotFoundError:
            rows.append((t, "missing")); continue
        j = n.join(p, how="inner")
        rows.append((t, str(n.index.min().date()), str(n.index.max().date()), len(n), int(n.so.isna().sum()),
                     str(p.index.min().date()), len(j), int((n.so.diff().fillna(0) != 0).sum())))
    return pd.DataFrame(rows, columns=["t", "nav0", "nav1", "n_nav", "so_na", "px0", "n_join", "n_so_chg"][:len(rows[0])])


if __name__ == "__main__":
    import sys
    D.mkdir(parents=True, exist_ok=True)
    if "--fetch" in sys.argv:
        for t in TICKERS:
            fetch_nav(t); fetch_px(t)
    if "--convert" in sys.argv:
        for t in TICKERS: convert(t)
    print(coverage().to_string())
