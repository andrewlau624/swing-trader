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


# ---- $ amount vs market cap (D2, C5, R2-25, C3) ----------------------------------------------------------------------
AMT = re.compile(r"\$\s?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(Million|Mln|M|Billion|Bln|B)\b", re.I)


def _amount(text: str) -> float | None:
    m = AMT.search(text or "")
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    return v * (1e9 if m.group(2).lower().startswith("b") else 1e6)


def _mcap(E: pd.DataFrame) -> pd.DataFrame:
    """Attach shares (latest XBRL cover count within 400 days before fd) and mcap = shares x raw close on/before fd."""
    from .jump_common import shares_hist
    S = shares_hist()
    E = E.sort_values("fd")
    m = pd.merge_asof(E, S.sort_values("end"), left_on="fd", right_on="end", by="sym", direction="backward",
                      tolerance=pd.Timedelta(days=400))
    bars = F.raw_bars(sorted(m.sym.unique()))
    px = []
    for r in m.itertuples():
        b = bars.get(r.sym)
        c = b.close[pd.to_datetime(b.index) <= r.fd] if b is not None and len(b) else []
        px.append(float(c.iat[-1]) if len(c) else float("nan"))
    m["mcap"] = m.shares * np.array(px)
    return m


def d2() -> pd.DataFrame:
    """Contract/award/order headline (<= 2 tickers) with a $ amount >= 10% of market cap; next open gap < 3%."""
    L = news()
    X = L[(L.nsym <= 2) & L.headline.str.contains(r"contract|award|order|purchase agreement|supply agreement", case=False)
          & ~L.headline.str.contains(r"buyback|repurchase|offering|financing|loan|credit facility|notes|dividend", case=False)].copy()
    X["amt"] = X.headline.map(_amount)
    X = _mcap(X.dropna(subset=["amt"]))
    X = X[X.amt >= 0.10 * X.mcap]
    E = first_in(X[["sym", "fd"]], 30)
    return _gap_ok(E[E.fd >= "2016-01-01"], 0.03)


def c5() -> pd.DataFrame:
    """D2 events with fewer than 20M shares outstanding."""
    E = _mcap(d2())
    return E[E.shares < 20e6][["sym", "fd"]]


def r2_25() -> pd.DataFrame:
    """Buyback/repurchase authorization headline with a $ amount >= 15% of market cap; next open gap < 3%."""
    L = news()
    X = L[(L.nsym <= 2) & L.headline.str.contains(r"buyback|repurchase", case=False)].copy()
    X["amt"] = X.headline.map(_amount)
    X = _mcap(X.dropna(subset=["amt"]))
    X = X[X.amt >= 0.15 * X.mcap]
    E = first_in(X[["sym", "fd"]], 90)
    return _gap_ok(E[E.fd >= "2016-01-01"], 0.03)


def c3() -> pd.DataFrame:
    """H7 first coverage with fewer than 10M shares outstanding."""
    E = _mcap(h7())
    return E[E.shares < 10e6][["sym", "fd"]]


# ---- round 2 news ideas ----------------------------------------------------------------------------------------------
def r2_7() -> pd.DataFrame:
    """Strategic-alternatives review announced/explored (headline, <= 2 tickers); first per ticker in 365 days."""
    L = news()
    m = (L.nsym <= 2) & L.headline.str.contains(r"strategic alternatives|strategic review|explore (?:a )?sale|exploring (?:a )?sale",
                                               case=False) & ~L.headline.str.contains(r"conclude|complet|ends|terminat", case=False)
    return _first(L, m, 365, 0, 1e12)


def r2_19() -> pd.DataFrame:
    """Second upgrade within 10 days on a ticker (headline 'Upgrades <name> to ...'), ADV$ < $20M."""
    L = news()
    X = L[(L.nsym == 1) & L.headline.str.contains(r"\bUpgrades?\b", case=True)].sort_values("fd")
    X = X.drop_duplicates(["sym", "fd"])
    prev = X.groupby("sym").fd.shift(1)
    E = X[(X.fd - prev).dt.days.between(0, 10)][["sym", "fd"]]
    E = first_in(E, 60)
    return small_only(E[E.fd >= "2016-01-01"], 20e6)


DIV = re.compile(r"(?:Raises|Increases|Hikes|Boosts).*?Dividend.*?(?:from|From) \$?(\d*\.\d+|\d+)\s*(?:/Share|Per Share)?\s*(?:to|To) \$?(\d*\.\d+|\d+)")


def r2_22() -> pd.DataFrame:
    """Dividend raised >= 50% (headline 'raises ... dividend ... from $a to $b', b >= 1.5a), ADV$ < $20M."""
    L = news()
    X = L[(L.nsym == 1) & L.headline.str.contains("Dividend", case=False)].copy()
    m = X.headline.str.extract(DIV)
    X = X[m[0].notna()].assign(a=m[0].dropna().astype(float), b=m[1].dropna().astype(float))
    X = X[(X.a > 0) & (X.b >= 1.5 * X.a)]
    return _first(X, X.index == X.index, 180, 0, 20e6)


def r2_14() -> pd.DataFrame:
    """Emergence from Chapter 11 (headline 'emerges/emerged from Chapter 11/bankruptcy'), first per ticker."""
    L = news()
    m = (L.nsym <= 2) & L.headline.str.contains(r"emerg\w* from (?:Chapter 11|bankruptcy)", case=False)
    return _first(L, m, 3650, 0, 1e12)


# ---- round 3 news ideas ----------------------------------------------------------------------------------------------
def r3_11() -> pd.DataFrame:
    """Small company adds/buys bitcoin (or crypto) for its treasury (headline), first per ticker in 365 days, ADV$ < $20M."""
    L = news()
    m = (L.nsym <= 2) & L.headline.str.contains(r"bitcoin|BTC|crypto", case=False) & \
        L.headline.str.contains(r"treasury|purchas|acquir|adds|buys|bought|reserve", case=False)
    return _first(L, m, 365, 0, 20e6)


SPEC = re.compile(r"Special (?:Cash )?Dividend of \$(\d*\.\d+|\d+)", re.I)


def r3_12() -> pd.DataFrame:
    """Special dividend >= 10% of the last close (headline amount), next open gap < 3%."""
    L = news()
    X = L[(L.nsym == 1) & L.headline.str.contains("Special", case=False)].copy()
    m = X.headline.str.extract(SPEC)
    X = X[m[0].notna()].assign(amt=m[0].dropna().astype(float))
    X = _mcap(X)                                        # attaches the raw close via mcap / shares
    px = X.mcap / X.shares
    X = X[X.amt >= 0.10 * px]
    E = first_in(X[["sym", "fd"]], 180)
    return _gap_ok(E, 0.03)


PT = re.compile(r"(?:Raises|Boosts|Lifts) .*?(?:PT|Price Target).*?(?:from|From) \$(\d*\.?\d+) (?:to|To) \$(\d*\.?\d+)")


def r3_14() -> pd.DataFrame:
    """A price target raised >= 50% in one note ('Raises PT from $a to $b', b >= 1.5a), ADV$ < $20M."""
    L = news()
    X = L[(L.nsym == 1)].copy()
    m = X.headline.str.extract(PT)
    X = X[m[0].notna()].assign(a=m[0].dropna().astype(float), b=m[1].dropna().astype(float))
    X = X[(X.a > 0) & (X.b >= 1.5 * X.a)]
    return _first(X, X.index == X.index, 60, 0, 20e6)


INIT = re.compile(r"Initiates Coverage .*?(?:Announces|With|,).*?\$(\d*\.?\d+)\s*(?:PT|Price Target)", re.I)


def r3_15() -> pd.DataFrame:
    """Initiation with a price target >= 2x the last close on a micro cap (ADV$ < $5M)."""
    L = news()
    X = L[(L.nsym <= 2) & L.headline.str.contains("Initiates Coverage", case=False)].copy()
    m = X.headline.str.extract(INIT)
    X = X[m[0].notna()].assign(pt=m[0].dropna().astype(float))
    X = _mcap(X)
    px = X.mcap / X.shares
    X = X[X.pt >= 2 * px]
    return _first(X, X.index == X.index, 365, 0, 5e6)


def r3_20() -> pd.DataFrame:
    """Coverage discontinued/suspended/terminated, then an officer/director buy within 60 days: fd = the buy."""
    from .jump_insider import buys
    L = news()
    D = L[(L.nsym <= 2) & L.headline.str.contains(r"(?:Discontinues|Suspends|Terminates|Drops) Coverage", case=False)]
    dd = D.groupby("sym").fd.apply(lambda x: x.sort_values().to_numpy())
    X = buys()
    X = X[X.insider & (X.usd >= 1e3)].dropna(subset=["sym"])
    out = []
    for r in X.itertuples():
        a = dd.get(r.sym)
        if a is not None and ((a <= r.fd.to_datetime64()) & (a >= (r.fd - pd.Timedelta(days=60)).to_datetime64())).any():
            out.append(dict(sym=r.sym, fd=r.fd))
    E = first_in(pd.DataFrame(out, columns=["sym", "fd"]), 60)
    return small_only(E[E.fd >= "2016-01-01"], 1e12)


if __name__ == "__main__":
    what = sys.argv[1]
    save(globals()[what](), what)
