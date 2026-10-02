"""Jump hunt Reddit ideas (H1, H2, H3, H4, H13, V1, C4, C7, H18): ticker mentions in post titles (Arctic Shift).

Mentions: `$TICKER` cashtags, plus bare all-caps words of 3-5 letters that are exchange-listed stock symbols
(jump_common.stock_symbols, Alpaca incl. inactive) and not common words (STOP). Bare words are ignored in titles
that are mostly upper case. A post at UTC time t is public at t: fd = fd_of(t) (before 09:30 ET -> that day's open).

SMALL subs = pennystocks, smallstreetbets, RobinHoodPennyStocks, shortsqueeze. BIG = wallstreetbets.
Every rule below was written before any outcome (jump_ideas.md); thresholds are not tuned.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_reddit mentions
    PYTHONPATH=. .venv/bin/python -m research.sim.jump_reddit h1|h2|h3|h4|h13|v1
"""
from __future__ import annotations

import re
import sys

import pandas as pd

from .jump_common import ROOT, fd_of, first_in, save, small_only, stock_symbols
from .jump_data import OUT, load_reddit

SMALL = ["pennystocks", "smallstreetbets", "RobinHoodPennyStocks", "shortsqueeze"]
BIG = ["wallstreetbets"]
STOP = set("""THE AND FOR ARE BUT NOT YOU ALL ANY CAN HAD HER WAS ONE OUR OUT DAY GET HAS HIM HIS HOW MAN NEW NOW OLD SEE
TWO WAY WHO BOY DID ITS LET PUT SAY SHE TOO USE YOLO HOLD BUY SELL CALL CALLS PUTS PUT MOON GAIN GAINS LOSS LOSSES WSB
CEO CFO CTO IPO ETF SEC FDA USA USD EPS ATH ATL EOD EOW IMO IMHO LOL LMAO FYI TLDR WTF OMG WHY WHAT WHEN THIS THAT WITH
FROM HAVE WILL JUST LIKE YOUR THEY BEEN THAN THEM WERE SOME MORE MOST VERY INTO OVER ONLY ALSO BACK GOOD BEST NEXT
WEEK YEAR LONG SHORT HIGH LOW OPEN CLOSE FREE MAKE MADE TAKE BEAR BULL PUMP DUMP SQUEEZE STOCK STOCKS SHARE SHARES
MONEY CASH DEBT NEWS DATA INFO HELP NEED WANT KNOW THINK LOOK REAL TRUE FAKE BIG HUGE RUN RUNS UP DOWN TOP HOT NEXT
GME AMC DD OTC NYSE NASDAQ EST PST PM AM AH PR ER UK EU CEO API CPI GDP FED IRS LLC INC CORP LTD ATM SPAC SPY QQQ
DOW HODL APE APES TENDIES RIP FOMO NFT AI EV IT ON GO SO AM AN AT BE BY DO HE IF IN IS ME MY NO OF OK OR TO US WE
ELI EDIT UPDATE PART LAST FIRST TODAY WEEKLY DAILY MONDAY FRIDAY JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC
RED GREEN PLAY PLAYS TIME LIFE LOVE HATE FUCK SHIT WOW YES NOPE MEME ONE TWO TEN DUE PAY FUN ROI PDT ACT CAR CARS
OIL GAS GOLD TECH BANK BIO PHARMA CBD THC LET ANY OWN WIN WON LOST POST TERM WAR""".split())
CASH = re.compile(r"\$([A-Za-z]{1,5})\b")
BARE = re.compile(r"\b([A-Z]{3,5})\b")


def mentions() -> pd.DataFrame:
    f = OUT / "reddit_mentions.parquet"
    syms = stock_symbols()
    rows = []
    for sub in SMALL + BIG:
        try:
            R = load_reddit(sub)
        except ValueError:
            continue
        for t, title, flair in zip(R.created, R.title.astype(str), R.get("link_flair_text", pd.Series([None] * len(R)))):
            found = {m.upper() for m in CASH.findall(title)}
            letters = [c for c in title if c.isalpha()]
            if letters and sum(c.isupper() for c in letters) / len(letters) < 0.6:
                found |= {m for m in BARE.findall(title) if m not in STOP}
            for s in found & syms:
                rows.append((sub, t, s, "squeeze" in title.lower(),
                             bool(re.search(r"\bDD\b", title)) or (str(flair).upper() == "DD")))
        print(sub, len(rows), flush=True)
    M = pd.DataFrame(rows, columns=["sub", "t", "sym", "squeeze", "dd"])
    M["fd"] = fd_of(M.t)
    M.to_parquet(f)
    return M


def M() -> pd.DataFrame:
    return pd.read_parquet(OUT / "reddit_mentions.parquet")


def _start(X: pd.DataFrame, days: int) -> pd.DataFrame:
    """Drop events inside the first `days` of each sub's archive (no lookback to call them 'first')."""
    return X[X.fd >= pd.Timestamp("2016-01-01") + pd.Timedelta(days=days)]


def h1() -> pd.DataFrame:
    """First mention in the small subs after >= 365 days of silence, confirmed by a 2nd post within 3 days."""
    X = M()[lambda d: d["sub"].isin(SMALL)].sort_values(["sym", "t"])
    prev = X.groupby("sym").t.shift(1)
    nxt = X.groupby("sym").t.shift(-1)
    first = X[(prev.isna() | ((X.t - prev).dt.days >= 365)) & ((nxt - X.t).dt.days <= 3)]
    nx = X.groupby("sym").fd.shift(-1)
    E = pd.DataFrame(dict(sym=first.sym, fd=nx.loc[first.index]))
    return small_only(_start(E, 365), 20e6)


def _daily(subs) -> pd.DataFrame:
    X = M()[lambda d: d["sub"].isin(subs)]
    return X.groupby(["sym", "fd"]).size().rename("n").reset_index()


def h2() -> pd.DataFrame:
    """Daily posts >= 3 and >= 5x the trailing-30-calendar-day daily mean, with the session's |return| < 5%."""
    from . import event_fetch as F
    C = _daily(SMALL)
    out = []
    bars = F.raw_bars(sorted(C.sym.unique()))
    for s, g in C.groupby("sym"):
        ser = g.set_index("fd").n.asfreq("D", fill_value=0)
        base = ser.rolling(30).mean().shift(1)
        hit = ser[(ser >= 3) & (ser >= 5 * base.clip(lower=1 / 30))]
        b = bars.get(s)
        if b is None or not len(b) or not len(hit):
            continue
        b = b.copy(); b.index = pd.to_datetime(b.index)
        r = (b.close / b.close.shift(1) - 1)
        for d in hit.index:
            rd = r[r.index <= d]
            if len(rd) and abs(rd.iat[-1]) < 0.05 and (d - rd.index[-1]).days <= 4:
                out.append(dict(sym=s, fd=d))
    E = first_in(pd.DataFrame(out), 30)
    return small_only(_start(E, 30), 20e6)


def h3() -> pd.DataFrame:
    """First shortsqueeze-sub post with DD in the title or flair naming a ticker (none in the prior 180 days)."""
    X = M()[lambda d: (d["sub"] == "shortsqueeze") & d.dd]
    return small_only(_start(first_in(X[["sym", "fd"]], 180), 180), 20e6)


def h4() -> pd.DataFrame:
    """First WSB post naming a small cap (ADV$ < $20M) in 365 days."""
    X = M()[lambda d: d["sub"].isin(BIG)]
    return small_only(_start(first_in(X[["sym", "fd"]], 365), 365), 20e6)


def h13() -> pd.DataFrame:
    """First mention in one small sub, then within 10 days a first mention in a different sub (small or WSB):
    bought at the second sub's post."""
    X = M().sort_values("t")
    X = X.drop_duplicates(["sym", "sub", "fd"])
    out = []
    for s, g in X.groupby("sym"):
        g = g.reset_index(drop=True)
        last_any = None
        for i, r in g.iterrows():
            if last_any is not None and (r.t - last_any).days < 180:
                last_any = r.t
                continue
            # r is a first mention after 180 days of silence anywhere: look for another sub within 10 days
            later = g[(g.t > r.t) & (g.t <= r.t + pd.Timedelta(days=10)) & (g["sub"] != r["sub"])]
            if r["sub"] in SMALL and len(later):
                out.append(dict(sym=s, fd=later.fd.iat[0]))
            last_any = r.t
    return small_only(_start(pd.DataFrame(out), 180), 20e6)


def v1() -> pd.DataFrame:
    """>= 3 small-sub posts within 5 days naming a ticker with no WSB post in the prior 90 days; buy at the 3rd post."""
    X = M().sort_values("t")
    S, W = X[X["sub"].isin(SMALL)], X[X["sub"].isin(BIG)]
    wl = W.groupby("sym").t.apply(lambda x: x.sort_values().to_numpy())
    out = []
    for s, g in S.groupby("sym"):
        t = g.t.to_numpy()
        fd = g.fd.to_numpy()
        for i in range(2, len(t)):
            if (t[i] - t[i - 2]) <= pd.Timedelta(days=5).to_timedelta64():
                w = wl.get(s)
                if w is None or not ((w < t[i]) & (w >= t[i] - pd.Timedelta(days=90).to_timedelta64())).any():
                    out.append(dict(sym=s, fd=pd.Timestamp(fd[i])))
    E = first_in(pd.DataFrame(out), 60)
    return small_only(_start(E, 90), 20e6)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "mentions":
        mentions()
    else:
        save(globals()[what](), what)
