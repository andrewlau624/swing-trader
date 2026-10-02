"""Jump hunt news ideas from the Alpaca/Benzinga archive (jump_data.news): headline FACTS and COUNTS only (no
sentiment, no LLM judgment). A story is public at `created_at`: fd = fd_of(created_at).

Every rule was written before any outcome (jump_ideas.md). `python -m research.sim.jump_news <idea>` writes
data/research/program/events_jump_<idea>.parquet. Ideas: h7 h8 h9 h10 h11 h12 h14 h21 h22 s1 s2 s3 s4 s5 w2 w5
(+ the S variant `s1v`, `s2v`: fd 6 sessions before the scheduled date, registered with the primary rule).
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

from . import event_fetch as F
from .jump_common import ROOT, fd_of, first_in, save, small_only, stock_symbols
from .jump_data import OUT, load_news

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
DATE = re.compile(rf"\b({MONTHS})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?")
EARN = re.compile(r"\b(Q[1-4]|EPS|Earnings|Sales|Revenue|10-[QK]|Quarter|FY\d|Guidance|Dividend)\b", re.I)


def news() -> pd.DataFrame:
    """One row per (story, listed stock symbol), with fd. Cached."""
    f = OUT / "news_long.parquet"
    if f.exists():
        return pd.read_parquet(f)
    N = load_news()
    N = N[N.symbols.str.len() > 0]
    N["fd"] = fd_of(N.created_at)
    L = N.assign(sym=N.symbols.str.split(",")).explode("sym")
    L = L[L.sym.isin(stock_symbols())]
    L["nsym"] = L.symbols.str.count(",") + 1
    L = L[["id", "created_at", "fd", "sym", "nsym", "headline", "summary"]].reset_index(drop=True)
    if N.created_at.max() >= pd.Timestamp("2026-09-01", tz="UTC"):        # cache only the complete archive
        L.to_parquet(f)
    return L


def sessions() -> pd.DatetimeIndex:
    b = F.raw_bars(["SPY"])["SPY"]
    return pd.DatetimeIndex(pd.to_datetime(b.index)).sort_values()


def shift_sessions(d: pd.Timestamp, k: int, S: pd.DatetimeIndex) -> pd.Timestamp | None:
    """The session k sessions before (k > 0) the first session on/after d."""
    i = S.searchsorted(d)
    return S[i - k] if 0 <= i - k < len(S) and i < len(S) else None


def parse_date(text: str, ref: pd.Timestamp) -> pd.Timestamp | None:
    """First 'Month Day[, Year]' in text; a missing year is the next occurrence on/after the story date."""
    m = DATE.search(text or "")
    if not m:
        return None
    mon, day, yr = m.group(1)[:3], int(m.group(2)), m.group(3)
    try:
        d = pd.Timestamp(f"{mon} {day} {yr or ref.year}")
    except ValueError:
        return None
    if not yr and d < ref.normalize() - pd.Timedelta(days=2):
        d = d + pd.DateOffset(years=1)
    return d


def _gap_ok(E: pd.DataFrame, max_gap: float) -> pd.DataFrame:
    """Keep events whose trade open (first session after fd) gaps less than max_gap above the prior close (raw)."""
    bars = F.raw_bars(sorted(E.sym.unique()))
    keep = []
    for r in E.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            keep.append(False); continue
        idx = pd.to_datetime(b.index)
        i = idx.searchsorted(r.fd + pd.Timedelta(days=1))
        keep.append(0 < i < len(b) and b.open.iat[i] / b.close.iat[i - 1] - 1 < max_gap)
    return E[keep]


def _first(L: pd.DataFrame, mask, gap_days: int, start_days: int, max_adv: float) -> pd.DataFrame:
    E = first_in(L[mask][["sym", "fd"]], gap_days)
    E = E[E.fd >= pd.Timestamp("2016-01-01") + pd.Timedelta(days=start_days)]
    return small_only(E, max_adv)


# ---- H ideas -------------------------------------------------------------------------------------------------------
def h7() -> pd.DataFrame:
    """A ticker's first story in the archive (no story since 2016-01), fd >= 2018-01 (2 years of lookback), the stock
    trading >= 2 years before (first raw bar <= fd - 730d). No ADV cap beyond the runner's floor."""
    L = news()
    E = L.sort_values("fd").drop_duplicates("sym")[["sym", "fd"]]
    E = E[E.fd >= "2018-01-01"]
    bars = F.raw_bars(sorted(E.sym.unique()))
    ok = [len(bars.get(s, [])) and pd.to_datetime(bars[s].index).min() <= fd - pd.Timedelta(days=730)
          for s, fd in zip(E.sym, E.fd)]
    return E[np.array(ok, dtype=bool)]


def h8() -> pd.DataFrame:
    """>= 4 stories in 5 days after <= 3 in the prior 90 days, |5-session return to fd| < 10%, ADV$ < $20M."""
    L = news().drop_duplicates(["id", "sym"])
    C = L.groupby(["sym", "fd"]).size().rename("n").reset_index()
    out = []
    for s, g in C.groupby("sym"):
        ser = g.set_index("fd").n.asfreq("D", fill_value=0)
        r5, r90 = ser.rolling(5).sum(), ser.rolling(90).sum().shift(5)
        for d in ser.index[(r5 >= 4) & (r90 <= 3)]:
            out.append(dict(sym=s, fd=d))
    E = first_in(pd.DataFrame(out), 30)
    E = E[E.fd >= "2016-04-01"]
    bars = F.raw_bars(sorted(E.sym.unique()))
    keep = []
    for r in E.itertuples():
        b = bars.get(r.sym)
        if b is None or len(b) < 7:
            keep.append(False); continue
        c = b.close[pd.to_datetime(b.index) <= r.fd]
        keep.append(len(c) >= 6 and abs(c.iat[-1] / c.iat[-6] - 1) < 0.10)
    return small_only(E[keep], 20e6)


def h9() -> pd.DataFrame:
    """First 'why is X trading higher / soaring / up' explainer for a ticker in 365 days (single-ticker story)."""
    L = news()
    m = (L.nsym == 1) & L.headline.str.contains(
        r"^Why .*(Trading Higher|Shares Are (Up|Higher|Soaring|Spiking|Surging)|Is (Soaring|Spiking|Surging|Rallying|Up)|Stock Is (Up|Higher|Soaring|Surging))",
        case=False, regex=True)
    return _first(L, m, 365, 365, 1e12)


def h10() -> pd.DataFrame:
    """First 'Initiates Coverage' on a ticker in 730 days, 20-day ADV$ < $5M."""
    L = news()
    m = L.headline.str.contains(r"Initiates Coverage", case=False) & (L.nsym <= 2)
    return _first(L, m, 730, 730, 5e6)


OPT = re.compile(r"^Option Alert:\s*([A-Z.]+)\s.*?\bCalls\b.*?:\s*([\d,]+)\s*@\s*(ASK|ABOVE ASK|A\.A\.|ABOVE)\b.*?([\d,.]+[kK]?)\s+traded vs\s+([\d,.]+[kK]?)\s+OI", re.I)


def _num(s: str) -> float:
    s = s.replace(",", "").lower()
    return float(s[:-1]) * 1e3 if s.endswith("k") else float(s)


def h11() -> pd.DataFrame:
    """Benzinga 'Option Alert' on CALLS bought at/above the ask with volume above open interest (opening), ADV$ < $50M,
    first per ticker in 10 days."""
    L = news()
    X = L[L.headline.str.startswith("Option Alert")].copy()
    m = X.headline.str.extract(OPT)
    X = X[m[0].notna()].assign(vol=m[3].dropna().map(_num), oi=m[4].dropna().map(_num))
    X = X[X.vol > X.oi]
    return _first(X, X.index == X.index, 10, 0, 50e6)


def h12() -> pd.DataFrame:
    """First headline with 'short squeeze' naming the ticker (<= 2 tickers on the story) in 365 days."""
    L = news()
    m = L.headline.str.contains(r"short[- ]squeeze|squeeze", case=False) & (L.nsym <= 2)
    return _first(L, m, 365, 365, 1e12)


def h14() -> pd.DataFrame:
    """PR blitz: >= 4 single-ticker stories in 10 days after <= 6 in the prior 180 days; ADV$ < $5M."""
    L = news()
    L = L[L.nsym == 1]
    C = L.groupby(["sym", "fd"]).size().rename("n").reset_index()
    out = []
    for s, g in C.groupby("sym"):
        ser = g.set_index("fd").n.asfreq("D", fill_value=0)
        r10, r180 = ser.rolling(10).sum(), ser.rolling(180).sum().shift(10)
        for d in ser.index[(r10 >= 4) & (r180 <= 6)]:
            out.append(dict(sym=s, fd=d))
    E = first_in(pd.DataFrame(out), 60)
    E = E[E.fd >= "2016-07-01"]
    return small_only(E, 5e6)


def h21() -> pd.DataFrame:
    """First story in >= 180 days whose headline is not an earnings/filing item."""
    L = news()
    L2 = L.sort_values("fd")
    prev = L2.groupby("sym").fd.shift(1)
    m = ((L2.fd - prev).dt.days >= 180) & ~L2.headline.str.contains(EARN)
    E = L2[m][["sym", "fd"]]
    return small_only(E[E.fd >= "2016-07-01"], 1e12)


BIGS = r"\b(NVIDIA|Nvidia|Microsoft|Amazon|AWS|Google|Alphabet|Apple|OpenAI|Tesla|Meta|Facebook)\b"


def h22() -> pd.DataFrame:
    """Single-ticker headline naming a big company + partner/collaborat/agreement/selected, ADV$ < $10M, next open
    gaps < 10%."""
    L = news()
    m = (L.nsym == 1) & L.headline.str.contains(BIGS) & L.headline.str.contains(
        r"partner|collaborat|agreement|selected|select|integrat|join", case=False)
    E = _first(L, m, 30, 0, 10e6)
    return _gap_ok(E, 0.10)


# ---- S ideas (scheduled run-ups) -----------------------------------------------------------------------------------
def _sched(L: pd.DataFrame, mask, k: int, min_lead: int) -> pd.DataFrame:
    """Events with a scheduled date parsed from headline (else summary). fd = k sessions before the date if the story
    was public by then (k = 0: fd = the story's own fd, kept only if the date is >= min_lead sessions later)."""
    S = sessions()
    out = []
    for r in L[mask].itertuples():
        d = parse_date(r.headline, r.created_at.tz_convert(None)) or parse_date(r.summary, r.created_at.tz_convert(None))
        if d is None or d <= r.fd:
            continue
        i_d, i_f = S.searchsorted(d), S.searchsorted(r.fd + pd.Timedelta(days=1))
        if k == 0:
            if i_d - i_f >= min_lead:
                out.append(dict(sym=r.sym, fd=r.fd))
        else:
            f = shift_sessions(d, k + 1, S)            # fd k+1 sessions before d -> buy k sessions before, hold k
            if f is not None and f >= r.fd:
                out.append(dict(sym=r.sym, fd=f))
    E = pd.DataFrame(out, columns=["sym", "fd"]).drop_duplicates()
    return first_in(E, 20) if len(E) else E


def _s1_mask(L):
    return (L.nsym == 1) & L.headline.str.contains(r"\bto (?:Present|Participate|Ring)\b.*\b(?:Conference|Summit|Forum|Symposium|Expo|CES|GTC)\b", case=False)


def s1() -> pd.DataFrame:
    """Conference presentation announced; bought at the announcement if the conference is >= 7 sessions later."""
    return small_only(_sched(news(), _s1_mask(news()), 0, 7), 20e6)


def s1v() -> pd.DataFrame:
    """Variant: fd 6 sessions before the conference date (hold5 = the last week), story public by then."""
    return small_only(_sched(news(), _s1_mask(news()), 5, 0), 20e6)


def _s2_mask(L):
    return L.headline.str.contains(r"PDUFA", case=False) | L.summary.str.contains(r"PDUFA", case=False)


def s2() -> pd.DataFrame:
    """PDUFA date in the story; fd = 21 sessions before it (hold20 exits the session before), story public by then."""
    L = news()
    return small_only(_sched(L, _s2_mask(L) & (L.nsym <= 2), 20, 0), 1e12)


def s2v() -> pd.DataFrame:
    L = news()
    return small_only(_sched(L, _s2_mask(L) & (L.nsym <= 2), 5, 0), 1e12)


def s3() -> pd.DataFrame:
    """Investor / analyst / capital-markets day announced with a date >= 7 sessions later."""
    L = news()
    m = (L.nsym == 1) & L.headline.str.contains(r"(Investor|Analyst|Capital Markets|R&D) Day", case=False) & \
        L.headline.str.contains(r"Host|Hold|Announce|Schedul|to ", case=False)
    return small_only(_sched(L, m, 0, 7), 20e6)


def s4() -> pd.DataFrame:
    """Micro/small biotech announces it will present data / an abstract at a medical meeting (bought at the story)."""
    L = news()
    m = (L.nsym == 1) & L.headline.str.contains(r"(Present|Presentation|Abstract|Poster|Oral).*(Data|Results)|(Data|Results).*(Present|Abstract|Poster|Oral)", case=False) & \
        L.headline.str.contains(r"\bto\b|Accepted|Will|Announces", case=False) & \
        L.headline.str.contains(r"ASCO|ASH|AACR|ESMO|ADA|AAN|EASL|AASLD|ASGCT|ACR|ATS|ERS|SABCS|ESC|AHA|Congress|Meeting|Conference", case=False)
    return _first(L, m, 30, 0, 20e6)


def s5() -> pd.DataFrame:
    """Forward stock split announced (not reverse): 'N-for-1' / 'N-for-M' with N > M, bought at the story."""
    L = news()
    X = L[L.headline.str.contains(r"Stock Split|Share Split", case=False) & ~L.headline.str.contains("Reverse", case=False)]
    m = X.headline.str.extract(r"(\d+)[- ]for[- ](\d+)", flags=re.I)
    X = X[m[0].notna() & (m[0].astype(float) > m[1].astype(float))]
    return _first(X, X.index == X.index, 180, 0, 1e12)


# ---- W ideas -------------------------------------------------------------------------------------------------------
def w2() -> pd.DataFrame:
    """First story naming AI / artificial intelligence in the headline for a ticker in 730 days; ADV$ < $20M."""
    L = news()
    m = (L.nsym <= 2) & L.headline.str.contains(r"\bAI\b|Artificial Intelligence|A\.I\.", case=True)
    return _first(L, m, 730, 730, 20e6)


def w5() -> pd.DataFrame:
    """First headline calling the ticker a 'meme' stock (<= 3 tickers) in 365 days."""
    L = news()
    m = (L.nsym <= 3) & L.headline.str.contains(r"\bmeme", case=False)
    return _first(L, m, 365, 0, 1e12)


if __name__ == "__main__":
    what = sys.argv[1]
    save(globals()[what](), what)
