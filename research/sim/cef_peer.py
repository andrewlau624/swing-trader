"""CEF-PEER (N 933): CEF-RV net of a SAME-CATEGORY equal-weight CEF peer index (incl. delisted).

    PYTHONPATH=. .venv/bin/python -m research.sim.cef_peer     # -> research/sim/cef_peer_out.txt

Pre-registration: round1_prose.md "Study CEF-PEER". The category regex below is frozen before the run.
"""
from __future__ import annotations

import pathlib
import re

import numpy as np
import pandas as pd

from research.sim.cef_alpha import CEF, COST, fmt, stats, window
from research.sim.cef_rv import STORE

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "research/sim/cef_peer_out.txt"
lines: list[str] = []

# Frozen, in order: the first match wins.
CATS = [
    ("muni", r"MUNICIPAL|MUNI\b|TAX[- ]?FREE|TAX[- ]?EXEMPT|TAX[- ]?ADVANTAGED|\b(CALIFORNIA|NEW YORK|NEW JERSEY|PENNSYLVANIA|"
             r"MASSACHUSETTS|MINNESOTA|OHIO|MICHIGAN|VIRGINIA|ARIZONA|MARYLAND|GEORGIA|FLORIDA|TEXAS|CONNECTICUT|MISSOURI|"
             r"NORTH CAROLINA)\b"),
    ("pref_conv", r"PREFERRED|CONVERTIBLE|CAPITAL SECURITIES"),
    ("sector", r"ENERGY|MLP|INFRASTRUCTURE|UTILIT|REAL ESTATE|REALTY|PROPERTY|GOLD|PRECIOUS|COMMODIT|NATURAL RESOURCE|"
               r"HEALTH|SCIENCE|TECHNOLOGY|BIOTECH|FINANCIAL|BANK|INSURANCE|MEDIA|PIPELINE|RESOURCES"),
    ("taxable_fi", r"FIXED INCOME|BOND|CREDIT|HIGH INCOME|HIGH YIELD|FLOATING|SENIOR|LOAN|MORTGAGE|DEBT|TREASUR|GOVERNMENT|"
                   r"MULTI[- ]?SECTOR|CORPORATE|MULTI[- ]?MARKET|INCOME SECURITIES|STRATEGIC INCOME|INCOME TRUST|"
                   r"INCOME OPPORTUNIT|LIMITED DURATION|INTERMEDIATE|TERM TRUST|INCOME SHARES"),
    ("intl", r"GLOBAL|INTERNATIONAL|WORLD|EMERGING|ASIA|CHINA|JAPAN|EUROPE|LATIN|INDIA|KOREA|TAIWAN|MEXICO|BRAZIL|RUSSIA|"
             r"GERMANY|SWISS|IRELAND|SINGAPORE|THAI|MALAYSIA|INDONESIA|CHILE|TURKEY|VIETNAM|AFRICA|CANADA|AUSTRALIA|PACIFIC|"
             r"GREATER|OVERSEAS|FOREIGN|ISRAEL|SPAIN|ITALY|FRANCE|UNITED KINGDOM|GREECE|AUSTRIA|PORTUGAL"),
]


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def category(name: str) -> str:
    n = (name or "").upper()
    for cat, rx in CATS:
        if re.search(rx, n):
            return cat
    return "equity"


def peers() -> tuple[dict[str, pd.Series], dict[str, str], pd.Series]:
    """Per-category EW CEF index levels (incl. delisted), ticker -> category, and the category count series."""
    from sharadar import tickers
    t = tickers()
    c = t[(t["table"] == "SFP") & (t["category"] == "CEF")][["ticker", "name", "firstpricedate", "lastpricedate"]].copy()
    c["cat"] = c["name"].map(category)
    cat_of = c.drop_duplicates("ticker").set_index("ticker")["cat"].to_dict()
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "closeadj"],
                        filters=[("ticker", "in", sorted(set(c["ticker"])))])
    f["date"] = pd.to_datetime(f["date"]).astype("datetime64[ns]")
    f = f.merge(c, on="ticker")
    f = f[(f["date"] >= pd.to_datetime(f["firstpricedate"])) & (f["date"] <= pd.to_datetime(f["lastpricedate"]))]
    f = f.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    f["r"] = f.groupby("ticker")["closeadj"].pct_change()
    f = f[f["r"].abs() <= 0.5]
    idx: dict[str, pd.Series] = {}
    for cat, g in f.groupby("cat"):
        ew = g.groupby("date")["r"].agg(["mean", "size"])
        idx[cat] = (1 + ew["mean"]).cumprod()
        say(f"  peer index {cat:10s}: {g['ticker'].nunique()} tickers, median names/day {int(ew['size'].median())}")
    mix = c.drop_duplicates("ticker")["cat"].value_counts(normalize=True)
    return idx, cat_of, mix


def main() -> int:
    say("CEF-PEER: CEF-RV net of same-category EW CEF peers (name-regex categories, delisted included)")
    idx, cat_of, mix = peers()
    say("  universe mix: " + " ".join(f"{k} {v:.0%}" for k, v in mix.items()))
    for name, fp, lo, mid in (("1999-2014", "cef_rv_trades_1999_2014.csv", "1999-01-01", "2007-01-01"),
                              ("2016-2026", "cef_rv_trades.csv", "2016-01-01", "2021-01-01")):
        tr = pd.read_csv(CEF / fp, parse_dates=["edate", "xdate"])
        tr = tr[tr["edate"] >= lo].sort_values("edate").reset_index(drop=True)
        tr["cat"] = tr["ticker"].map(cat_of)
        miss = tr["cat"].isna().sum()
        tr = tr.dropna(subset=["cat"]).reset_index(drop=True)
        a = tr["edate"].to_numpy("datetime64[ns]")
        b = tr["xdate"].to_numpy("datetime64[ns]")
        r = tr["ret"].to_numpy(float) - COST
        peer = np.full(len(tr), np.nan)
        for cat in tr["cat"].unique():
            m = (tr["cat"] == cat).to_numpy()
            peer[m] = window(idx[cat], a[m], b[m])
        # the EW-universe comparator of CEF-ALPHA, rebuilt from the same category indices (names-weighted is close enough
        # for the retention check; the registered N 892 number is quoted from cef_alpha_out.txt)
        allidx = None
        ok = np.isfinite(peer)
        r, peer, tr = r[ok], peer[ok], tr[ok].reset_index(drop=True)
        wk = tr["edate"].dt.strftime("%G-%V").to_numpy()
        h = (tr["edate"] < mid).to_numpy()
        say(f"\n== {name}: trades {len(r)} (no category {miss}, no comparator {int((~ok).sum())})")
        emix = tr["cat"].value_counts(normalize=True)
        say("  entry mix:    " + " ".join(f"{k} {v:.0%}" for k, v in emix.items()))
        say(f"  raw net        {fmt(stats(r, wk, h))}")
        say(f"  peer over hold {peer.mean()*1e4:+.1f}bp")
        sp = stats(r - peer, wk, h)
        say(f"  P  net - same-category peers ({'N 933' if name[0] == '2' else 'report'}): {fmt(sp)}")
        for cat in emix.index:
            m = (tr["cat"] == cat).to_numpy()
            if m.sum() >= 10:
                x = (r - peer)[m]
                say(f"     {cat:10s} n {m.sum():4d} excess {x.mean()*1e4:+.1f}bp median {np.median(x)*1e4:+.1f} hit {(x > 0).mean():.2f}")
        if name[0] == "2":
            ew_excess = 0.0125   # CEF-ALPHA N 892 (cef_alpha_out.txt): +125bp vs the EW CEF universe
            g = dict(mean=sp["mean"] >= 0.006, t=sp["t"] >= 2, med=sp["med"] > 0, halves=sp["h0"] > 0 and sp["h1"] > 0,
                     ex5=sp["ex5"] > 0, retain=sp["mean"] >= 0.5 * ew_excess)
            kill = sp["mean"] < 0.003 or sp["t"] < 1
            verdict = "PASS" if all(g.values()) else ("KILL" if kill else "WEAK")
            say(f"  GATE N 933: {verdict}  " + " ".join(f"{k}={'Y' if v else 'n'}" for k, v in g.items())
                + f"  (retained {sp['mean']/ew_excess:.0%} of the EW-universe excess)")
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
