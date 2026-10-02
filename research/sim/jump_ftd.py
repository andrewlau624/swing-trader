"""Jump hunt FTD / short-interest ideas: R3-2 fails-to-deliver spike, R3-16 FTD collapse after a spike, R3-9 short
interest collapse.

SEC fails-to-deliver files (cnsfailsYYYYMM{a,b}.zip, settlement date / symbol / quantity), 2015-12..2026-09. SEC posts
each half-month file about two weeks after it ends: a file is treated as public 20 calendar days after its last
settlement date (fd). Shares outstanding from jump_common.shares_hist (XBRL cover counts, latest within 400 days).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_ftd fetch
    PYTHONPATH=. .venv/bin/python -m research.sim.jump_ftd r3_2|r3_16|r3_9
"""
from __future__ import annotations

import io
import sys
import time
import zipfile

import pandas as pd
import requests

from .jump_common import ROOT, first_in, save, shares_hist, small_only

D = ROOT / "data/research/jump/ftd"


def fetch():
    from swingtrader.daily.news_judge import sec_headers
    H = sec_headers()
    D.mkdir(parents=True, exist_ok=True)
    import re
    page = requests.get("https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data", headers=H, timeout=60).text
    links = {re.search(r"cnsfails(\d{6}[ab])\.zip", u).group(1): u for u in re.findall(r'href="([^"]+cnsfails\d{6}[ab]\.zip)"', page)}
    for key in sorted(links):
        if key < "201512a":
            continue
        f = D / f"{key}.parquet"
        if f.exists():
            continue
        r = requests.get("https://www.sec.gov" + links[key], headers=H, timeout=120)
        m, h = key[:6], key[6]
        time.sleep(0.3)
        if not r.ok:
            print(m, h, r.status_code, flush=True); continue
        z = zipfile.ZipFile(io.BytesIO(r.content))
        X = pd.read_csv(z.open(z.namelist()[0]), sep="|", dtype=str, encoding="latin1", on_bad_lines="skip")
        X.columns = [c.strip().lower() for c in X.columns]
        X = X.rename(columns={"settlement date": "date", "quantity (fails)": "qty"})
        X = X[pd.to_numeric(X.qty, errors="coerce").notna() & X.symbol.notna()]
        X = pd.DataFrame(dict(date=pd.to_datetime(X.date, format="%Y%m%d", errors="coerce"), sym=X.symbol.str.strip(),
                              cusip=X.cusip.str.strip().str.upper(), qty=pd.to_numeric(X.qty), file=f.stem)).dropna()
        X.to_parquet(f)
        print(m, h, len(X), flush=True)


def ftd() -> pd.DataFrame:
    X = pd.concat([pd.read_parquet(f) for f in sorted(D.glob("*.parquet"))], ignore_index=True)
    X["pub"] = X.groupby("file").date.transform("max") + pd.Timedelta(days=20)
    S = shares_hist().sort_values("end")
    X = pd.merge_asof(X.sort_values("date"), S, left_on="date", right_on="end", by="sym", direction="backward",
                      tolerance=pd.Timedelta(days=400))
    X["frac"] = X.qty / X.shares
    return X


def r3_2() -> pd.DataFrame:
    """Any settlement day with fails >= 0.5% of shares outstanding; fd = the file's public date; first in 60 days."""
    X = ftd()
    X = X[X.frac >= 0.005]
    E = X.groupby(["sym", "file"]).pub.first().reset_index().rename(columns={"pub": "fd"})
    E = first_in(E[["sym", "fd"]], 60)
    return small_only(E[E.fd >= "2016-01-01"], 20e6)


def r3_16() -> pd.DataFrame:
    """A file whose max fails fraction is < 0.05% right after a file with >= 0.5% (buy-ins done); fd = public date."""
    X = ftd()
    F = X.groupby(["sym", "file"]).agg(frac=("frac", "max"), pub=("pub", "first")).reset_index().sort_values(["sym", "pub"])
    F["prev"] = F.groupby("sym").frac.shift(1)
    E = F[(F.prev >= 0.005) & (F.frac < 0.0005)].rename(columns={"pub": "fd"})
    E = first_in(E[["sym", "fd"]], 60)
    return small_only(E[E.fd >= "2016-01-01"], 20e6)


def r3_9() -> pd.DataFrame:
    """FINRA short position down >= 50% from the previous report (both published; >= 100k shares before) with the raw
    close within +-10% of its level at the previous report's publication; fd = the new report's publication."""
    from . import event_fetch as F
    from .jump_reddit import si
    S = si().sort_values(["sym", "settle"])
    S["prev"], S["prev_pub"] = S.groupby("sym").short.shift(1), S.groupby("sym").pub.shift(1)
    X = S[(S.prev >= 1e5) & (S.short <= 0.5 * S.prev)]
    X = small_only(X.rename(columns={"pub": "fd"}), 20e6)
    bars = F.raw_bars(sorted(X.sym.unique()))
    keep = []
    for r in X.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            keep.append(False); continue
        c = pd.Series(b.close.to_numpy(), index=pd.to_datetime(b.index))
        a, z = c[c.index <= r.prev_pub], c[c.index <= r.fd]
        keep.append(len(a) > 0 and len(z) > 0 and abs(z.iat[-1] / a.iat[-1] - 1) <= 0.10)
    return first_in(X[keep][["sym", "fd"]], 60)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "fetch":
        fetch()
    else:
        save(globals()[what](), what)
