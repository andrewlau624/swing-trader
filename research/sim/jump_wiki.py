"""Jump hunt Wikipedia ideas (H5, H6, H15, H16, C1): en.wikipedia user pageviews of a listed company's article.

Pageviews for UTC day D end at 20:00 ET and are published overnight: fd = D (traded at the next open). Tickers from
Wikidata (tickers as of today: a reused ticker can map an article to an older, unrelated listing; accepted noise).
Every rule was written before any outcome (jump_ideas.md).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_wiki h5|h6|h15|h16|c1
"""
from __future__ import annotations

import sys

import pandas as pd

from . import event_fetch as F
from .jump_common import ROOT, first_in, save, small_only
from .jump_data import OUT


def views() -> dict[str, pd.Series]:
    """ticker -> daily views (calendar days, 0-filled inside the article's life)."""
    W = pd.read_parquet(OUT / "wikidata_tickers.parquet")
    from urllib.parse import quote, unquote
    out = {}
    for t, g in W.groupby("title"):
        f = OUT / "wiki" / (quote(unquote(t), safe="")[:150] + ".parquet")
        if not f.exists():
            continue
        D = pd.read_parquet(f)
        if not len(D):
            continue
        s = pd.Series(D.views.to_numpy(), index=pd.to_datetime(D.date)).sort_index().asfreq("D", fill_value=0)
        for tk in g.ticker.unique():
            out[tk] = s
    return out


def _closes(syms) -> dict[str, pd.Series]:
    bars = F.raw_bars(sorted(syms))
    out = {}
    for s, b in bars.items():
        if b is not None and len(b):
            out[s] = pd.Series(b.close.to_numpy(), index=pd.to_datetime(b.index)).sort_index()
    return out


def _ret_ok(c: pd.Series | None, d: pd.Timestamp, n: int, lim: float) -> bool:
    if c is None:
        return False
    x = c[c.index <= d]
    return len(x) > n and abs(x.iat[-1] / x.iat[-1 - n] - 1) < lim and (d - x.index[-1]).days <= 4


def h5() -> pd.DataFrame:
    """Views >= 5x the trailing-60-day median (median >= 20), the last session's |return| < 5%."""
    V = views()
    C = _closes(V.keys())
    out = []
    for s, v in V.items():
        med = v.rolling(60, min_periods=60).median().shift(1)
        for d in v.index[(v >= 5 * med) & (med >= 20)]:
            if _ret_ok(C.get(s), d, 1, 0.05):
                out.append(dict(sym=s, fd=d))
    return first_in(pd.DataFrame(out), 30)


def h6() -> pd.DataFrame:
    """20-day mean views >= 2x the prior 120-day mean, each of the last 4 weekly means above the week before, the
    20-session return within +-10%; first in 60 days."""
    V = views()
    C = _closes(V.keys())
    out = []
    for s, v in V.items():
        m20, m120 = v.rolling(20).mean(), v.rolling(120).mean().shift(20)
        wk = v.rolling(7).mean()
        rising = (wk > wk.shift(7)) & (wk.shift(7) > wk.shift(14)) & (wk.shift(14) > wk.shift(21)) & (wk.shift(21) > wk.shift(28))
        for d in v.index[(m20 >= 2 * m120) & (m120 >= 10) & rising]:
            if _ret_ok(C.get(s), d, 20, 0.10):
                out.append(dict(sym=s, fd=d))
    return first_in(pd.DataFrame(out), 60)


def h15() -> pd.DataFrame:
    """Article born after 2016-07-01 (its first pageview row is after then): the first day with >= 50 views."""
    out = []
    for s, v in views().items():
        nz = v[v > 0]
        if not len(nz) or nz.index[0] < pd.Timestamp("2016-07-01"):
            continue
        hit = v[v >= 50]
        if len(hit):
            out.append(dict(sym=s, fd=hit.index[0]))
    return pd.DataFrame(out)


def h16() -> pd.DataFrame:
    """Saturday+Sunday views >= 5x the median of the prior 8 weekends (>= 40 views a weekend): bought Monday's open."""
    out = []
    for s, v in views().items():
        wk = v.resample("W-SUN").apply(lambda x: x[x.index.dayofweek >= 5].sum())
        med = wk.rolling(8, min_periods=8).median().shift(1)
        for d in wk.index[(wk >= 5 * med) & (med >= 40)]:
            out.append(dict(sym=s, fd=d))
    return first_in(pd.DataFrame(out), 30)


def c1() -> pd.DataFrame:
    """An H5 pageview spike within 10 days after an officer/director open-market buy (Form 4)."""
    from .jump_insider import buys
    H = h5()
    X = buys()
    X = X[X.insider & (X.usd >= 1e3)]
    ib = X.groupby("sym").fd.apply(lambda x: x.sort_values().to_numpy())
    keep = []
    for r in H.itertuples():
        a = ib.get(r.sym)
        keep.append(a is not None and ((a <= r.fd.to_datetime64()) & (a >= (r.fd - pd.Timedelta(days=10)).to_datetime64())).any())
    return H[keep]


if __name__ == "__main__":
    what = sys.argv[1]
    save(globals()[what](), what)
