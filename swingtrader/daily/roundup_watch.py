"""Reverse-split round-up watch (Round 32 B1, research/drafts/study_round32_events.md) — ALERT ONLY, never trades.

Some issuers round fractional post-split shares UP instead of paying cash in lieu. A holder of ONE pre-split share then
gets one post-split share, worth about N x the pre-split price. 2016-26: 344 reverse splits with a holder-level round-up
sentence (none saying the rounding is at the DTC participant level); buying 1 share at the last pre-split close made
a mean $4.36 (median $3.56) per account when the round-up was paid, on a median $0.25 of capital; if the broker pays
cash in lieu instead, the result is about $0 (mean −$0.02). ~75 deals a year. Unknown from history: whether Schwab
passes the extra share to a 1-share holder. The first deals are the live check.

With ROUNDUP_AUTO=1 in .env the bot also places the 1-share buys and sells itself (`roundup_orders.py`; caps and a
kill switch there). Run once a weekday before the open (`make roundup-watch`): Alpaca's corporate-action announcements list the reverse
splits with an ex-date in the next 14 days (ratio included). For each, the issuer's EDGAR filings of the last 180 days
are searched (full-text search by CIK) for a sentence about the split's fractional shares that rounds them up (no cash
alternative in it, not a warrant / conversion clause), and none may say the rounding is at the "participant level" /
"DTC participant" / "Cede". Each qualifying split is logged to state/roundup-watch.jsonl and emailed with its buy-by
session (the last session before the ex-date), and reminded on that day; after the ex-date it is scored from raw bars
(post-split close − pre-split close = the gain if rounded up).

Lead time (2026-10-26): Alpaca announces most splits 0-1 days before the ex-date, so a second DISCOVERY runs each
morning: EDGAR full-text search for 8-K / 6-K / DEF 14A filed in the last 7 days with "reverse stock split" and
"rounded up" (no CIK filter). A filing that passes the same sentence check and names an effective date is alerted as
UNCONFIRMED (Alpaca's ex-date is authoritative; the bot never buys an unconfirmed name) and is promoted to a normal
alert when Alpaca lists it. Nothing is dropped silently: every candidate seen writes a row with an `outcome`
(qualified / no-roundup / late-dropped / no-cik / unconfirmed / unconfirmed-expired / order-placed / no-order with
the broker's reason) so a missing order can be diagnosed from the file.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import requests

from .insider_shadow import _read, _sec_get
from .tender_watch import clean

LOG_NAME = "roundup-watch.jsonl"
QUERIES = ['"rounded up to the nearest whole share" "reverse stock split"',
           '"rounded up to the next whole share" "reverse stock split"',
           '"round up to the nearest whole share" "reverse stock split"',
           '"rounded up to the nearest whole number" "reverse stock split"',
           # index-beat R7-1 (2026-10-02): wordings the four phrases miss (~2.5 genuine deals/yr 2023-26)
           '"round up any fractional" "reverse stock split"',
           '"one whole share in lieu" "reverse stock split"',
           '"additional fraction of a share" "reverse stock split" "round up"']
PL = re.compile(r"participant level|DTC participant|at the participant|Cede ?& ?Co", re.I)
# a cash alternative in the same sentence ("... or we will pay a cash adjustment", AXNX 2026-10) = not a round-up
CASH = re.compile(r"cash (?:in lieu|payment|adjustment)|paid in cash|receive (?:a )?cash|or to entitle", re.I)
# warrant / convertible clauses round their own fractions up ("upon the exercise of this Warrant", GCTK 2026-10)
NOT_SPLIT = re.compile(r"\bwarrants?\b|\bexercis(?:e|ed|es|able)\b|\bconversion\b", re.I)
# EDGAR full-text discovery (lead time): forms, query and the effective-date / ratio wording parsed from the filing
DISCOVERY_FORMS = "8-K,6-K,DEF 14A"
DISCOVERY_QUERY = '"reverse stock split" "rounded up"'
DISCOVERY_DAYS = 7
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DATE = rf"((?:{_MONTHS})\s+\d{{1,2}},\s*\d{{4}}|\d{{1,2}}/\d{{1,2}}/\d{{4}})"
EFFECTIVE = re.compile(r"(?:effective (?:as of|on|at)|(?:will |shall |to )?become effective|(?:is|be|was) effective"
                       r"|split-adjusted basis (?:on|as of|at|beginning|commencing|when)|effective (?:date|time) (?:of|is|will be))"
                       r"[^.;]{0,120}?" + _DATE, re.I)
RATIO = re.compile(r"\b(?:1|one)[- ]for[- ](\d{1,3}|[a-z]+(?:[- ][a-z]+)?)\b", re.I)
_WORDS = dict(two=2, three=3, four=4, five=5, six=6, seven=7, eight=8, nine=9, ten=10, twelve=12, fifteen=15, twenty=20,
              twenty_five=25, thirty=30, forty=40, fifty=50, sixty=60, seventy=70, seventy_five=75, eighty=80, ninety=90,
              hundred=100, one_hundred=100, two_hundred=200, five_hundred=500)


def round_up_sentence(text: str) -> str | None:
    """A forward-looking sentence ("will/shall/would be rounded up") about the split's fractional shares, with no cash
    alternative in it and not about a warrant / conversion, else None. Past-tense sentences describe an earlier split
    (10-Q/10-K history)."""
    for sen in re.split(r"(?<=[.;])\s+", clean(text)):
        if (re.search(r"fraction", sen, re.I) and re.search(r"round(?:ed|ing)? up|(?:one )?whole share in lieu", sen, re.I)
                and re.search(r"split|whole (?:share|number)", sen, re.I) and re.search(r"\b(?:will|shall|would)\b", sen, re.I)
                and not CASH.search(sen) and not NOT_SPLIT.search(sen)):
            return sen.strip()[:400]
    return None


def _parse_date(s: str) -> dt.date | None:
    for fmt in ("%B %d, %Y", "%B %d,%Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(re.sub(r"\s+", " ", s), fmt).date()
        except ValueError:
            continue
    return None


def effective_date(text: str, today: dt.date, back: int = 30, ahead: int = 60) -> dt.date | None:
    """The split's effective / split-adjusted-trading date named in the filing: the earliest such date on or after
    `today` if any, else the latest one before it (so a late find is logged as late, not as unknown). Dates more than
    `back` days ago or `ahead` days out are not a split date (a proxy's "effective until July 13, 2027" window)."""
    found = {d for m in EFFECTIVE.finditer(text) if (d := _parse_date(m.group(1)))
             and -back <= (d - today).days <= ahead}
    ahead = sorted(d for d in found if d >= today)
    return ahead[0] if ahead else (max(found) if found else None)


def split_ratio(text: str) -> float | None:
    for m in RATIO.finditer(text):
        w = m.group(1).lower().replace("-", "_").replace(" ", "_")
        for cand in (w, w.split("_")[0]):
            n = int(cand) if cand.isdigit() else _WORDS.get(cand)
            if n and 2 <= n < 1000:
                return float(n)
    return None


def search(cik: int, start: dt.date, end: dt.date) -> list[dict]:
    """The issuer's filings in [start, end] that full-text search returns for round-up language."""
    hits = {}
    for q in QUERIES:
        u = (f"https://efts.sec.gov/LATEST/search-index?q={requests.utils.quote(q)}&ciks={int(cik):010d}"
             f"&dateRange=custom&startdt={start}&enddt={end}")
        j = _sec_get(u)
        try:
            for x in json.loads(j)["hits"]["hits"] if j else []:
                s = x["_source"]
                hits[x["_id"]] = dict(id=x["_id"], adsh=s["adsh"], form=s["form"], date=s["file_date"], cik=s["ciks"][0])
        except (ValueError, KeyError):
            continue
    return sorted(hits.values(), key=lambda h: h["date"], reverse=True)


def _hits(url: str) -> list[dict]:
    j = _sec_get(url)
    out = []
    try:
        for x in json.loads(j)["hits"]["hits"] if j else []:
            s = x["_source"]
            names = " ".join(s.get("display_names") or [])
            m = re.search(r"\(([A-Z][A-Z0-9.\-]*)(?:,[^)]*)?\)\s*\(CIK", names)
            out.append(dict(id=x["_id"], adsh=s["adsh"], form=s["form"], date=s["file_date"], cik=int(s["ciks"][0]),
                            ticker=m.group(1) if m else None))
    except (ValueError, KeyError, TypeError):
        return []
    return out


def discovery_url(today: dt.date, days: int = DISCOVERY_DAYS) -> str:
    return (f"https://efts.sec.gov/LATEST/search-index?q={requests.utils.quote(DISCOVERY_QUERY)}"
            f"&forms={requests.utils.quote(DISCOVERY_FORMS)}&dateRange=custom"
            f"&startdt={today - dt.timedelta(days=days)}&enddt={today}")


def filing_url(cik: int, hit: dict) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{hit['adsh'].replace('-', '')}/{hit['id'].split(':', 1)[1]}"


def edgar_upcoming(today: dt.date, skip: set[str] = frozenset(), days: int = DISCOVERY_DAYS, fetch=None) -> list[dict]:
    """EDGAR full-text discovery, no CIK filter: one candidate per filing (adsh) of the last `days` days whose text has a
    qualifying round-up sentence, with the effective date and ratio parsed from it (None when the filing names none).
    Filings in `skip` (already logged) are not fetched again. Filings with the search words but no qualifying sentence
    come back with sentence=None so the run can log them as no-roundup once."""
    fetch = fetch or _sec_get
    out, seen = [], set()
    for h in _hits(discovery_url(today, days)):
        if h["adsh"] in skip or h["adsh"] in seen:
            continue
        url = filing_url(h["cik"], h)
        t = clean(fetch(url) or "")
        if not t:
            continue
        sen = None if PL.search(t) else round_up_sentence(t)
        row = dict(ticker=h["ticker"], cik=h["cik"], adsh=h["adsh"], form=h["form"], filed=h["date"], url=url,
                   sentence=sen, source="edgar")
        if sen:
            e = effective_date(t, today)
            row.update(ex_date=str(e) if e else None, ratio=split_ratio(t))
            seen.add(h["adsh"])
        elif any(o["adsh"] == h["adsh"] for o in out):
            continue                                # another document of the same filing already recorded as no-roundup
        out.append(row)
    # a filing with several documents: keep the qualifying one, drop its no-roundup siblings
    good = {r["adsh"] for r in out if r["sentence"]}
    return [r for r in out if r["sentence"] or r["adsh"] not in good]


def upcoming(today: dt.date, days: int = 14) -> list[dict]:
    """Alpaca-announced reverse splits with an ex-date in [today, today + days]."""
    from alpaca.trading.enums import CorporateActionDateType, CorporateActionSubType, CorporateActionType
    from alpaca.trading.requests import GetCorporateAnnouncementsRequest
    from .marketdata import _clients
    _, tr = _clients()
    a = tr.get_corporate_announcements(GetCorporateAnnouncementsRequest(
        ca_types=[CorporateActionType.SPLIT], since=today, until=today + dt.timedelta(days=days),
        date_type=CorporateActionDateType.EX_DATE))
    out = []
    for x in a:
        if x.ca_sub_type == CorporateActionSubType.REVERSE_SPLIT and x.ex_date and x.old_rate and x.new_rate:
            n = float(x.old_rate) / float(x.new_rate)
            if 2 <= n < 1000:                       # >= 1000 is a going-private cash-out, not a round-up
                out.append(dict(ticker=(x.target_symbol or x.initiating_symbol or "").upper(), ex_date=str(x.ex_date),
                                ratio=round(n, 4)))
    return out


def qualify(cik: int, ex_date: str) -> dict | None:
    """The round-up sentence and its filing when the issuer rounds up at the holder level, else None."""
    ex = dt.date.fromisoformat(ex_date)
    found = None
    for h in search(cik, ex - dt.timedelta(days=180), ex):
        url = filing_url(cik, h)
        t = _sec_get(url) or ""
        if PL.search(clean(t)):
            return None                             # rounded at the broker level: a 1-share holder gets nothing
        sen = round_up_sentence(t)
        if sen and not found:
            found = dict(sentence=sen, url=url, form=h["form"], filed=h["date"])
    return found


def _raw_closes(sym: str, start: dt.date, end: dt.date):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    import pandas as pd
    from .marketdata import _clients, _sip_end, trade_date
    data, _ = _clients()
    df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=[sym], timeframe=TimeFrame.Day,
                                              start=pd.Timestamp(start, tz="UTC"),
                                              end=min(pd.Timestamp(end, tz="UTC"), _sip_end()),
                                              feed="sip", adjustment="raw")).df
    if df is None or df.empty:
        return None
    df = df.reset_index()
    df["date"] = trade_date(df["timestamp"])
    return df.set_index("date").close


def score(r: dict, today: dt.date) -> dict | None:
    """Gain if rounded up = first post-split raw close − last pre-split raw close (1 share)."""
    if not r.get("trade_date") or dt.date.fromisoformat(r["trade_date"]) >= today:
        return None
    import pandas as pd
    e = pd.Timestamp(r["trade_date"])
    c = _raw_closes(r["ticker"], (e - pd.Timedelta(days=10)).date(), (e + pd.Timedelta(days=5)).date())
    if c is None:
        return None
    c.index = pd.to_datetime(c.index)
    pre, post = c[c.index < e], c[c.index >= e]
    if not len(pre) or not len(post):
        return None
    ps, pe = float(pre.iloc[-1]), float(post.iloc[0])
    ok = r.get("ratio") is None or 0.33 <= pe / ps / r["ratio"] <= 3
    return dict(scored=str(today), ticker=r["ticker"], trade_date=r["trade_date"], pre_close=ps, post_close=pe,
                gain_if_rounded=round(pe - ps, 4), split_in_prices=ok)


def _unconfirmed_facts(unconfirmed: list[dict]) -> list[tuple[str, str]]:
    out = []
    for r in unconfirmed:
        n = r.get("ratio")
        out.append((f"{r['ticker'] or 'CIK ' + str(r['cik'])}" + (f" 1-for-{n:g}" if n else ""),
                    f"{r['form']} filed {r['filed']} names {r['ex_date']} as the effective date; Alpaca has not listed "
                    f"the split yet. If it is right, buy 1 share by the session before (the bot only buys once Alpaca "
                    f"confirms)."))
    return out


def build_email(new: list[dict], due: list[dict], events: list, auto: bool,
                unconfirmed: list[dict] = ()) -> tuple[str, str] | None:
    """(subject, html) for this run, or None. Auto: what the bot did. Manual: what to buy and by when. `unconfirmed`:
    EDGAR-only finds (effective date parsed from the filing, no Alpaca listing yet), listed in both modes."""
    from ..live import mail as M
    rows = {r["ticker"]: r for r in new + due}
    split_facts = []
    for r in rows.values():
        n = r.get("ratio")
        val = f", ~${(n - 1) * r['last_close']:.2f} if rounded up" if n and r.get("last_close") else ""
        split_facts.append((f"{r['ticker']} 1-for-{n:g}", f"buy by {r['buy_by']}, splits {r['trade_date']}{val}"))
    unc = _unconfirmed_facts(list(unconfirmed))
    unc_block = [M.facts(unc, "Unconfirmed (EDGAR filing only, not yet on Alpaca)")] if unc else []
    unc_links = [M.link(r["url"], f"{r['ticker']}: the filing ({r.get('form')})") for r in unconfirmed if r.get("url")]
    if auto:
        if not events and not unc:
            return None
        verb = {"bought": "Bought", "sold": "Sold", "cash": "Cash in lieu"}
        acts = [(f"{verb[k]} {sym} · {'Brokerage' if a == 'live' else 'Roth'}", d) for k, a, sym, d in events]
        kinds = {k for k, *_ in events}
        title = ("Bought 1 share for the round-up" if kinds == {"bought"} else
                 "Round-up update" if events else "Unconfirmed round-up candidates (EDGAR)")
        blocks = [M.action("Nothing to do" if events else "Check", title, lines=[
                      "The bot buys 1 share per account before each qualifying reverse split and sells the post-split "
                      "share once Schwab credits it. These are the orders it placed this morning." if events else
                      "EDGAR names these splits before Alpaca lists them. The bot buys only once Alpaca confirms the "
                      "ex-date; to be early, buy 1 share per account yourself by the session before the filing's date."],
                      tone="info")]
        if acts:
            blocks.append(M.facts(acts, "This morning"))
        if split_facts:
            blocks.append(M.facts(split_facts, "Splits"))
        blocks += unc_block
        blocks.append(M.fine("If Schwab rounds up, each account ends with 1 post-split share worth about N x the price "
                             "paid; if it pays cash in lieu instead, the loss is about the price of 1 share. After 2 "
                             "cash-in-lieu outcomes with none rounded, an account stops buying (you get an email). "
                             "Switch off: remove ROUNDUP_AUTO=1 from the server's .env."))
        blocks += unc_links
        subj = (f"Round-up: {', '.join(sorted({e[2] for e in events}))} - {', '.join(sorted(kinds))}" if events else
                f"Round-up (unconfirmed): {', '.join(str(r['ticker']) for r in unconfirmed)} filed a round-up split")
        return (subj, M.page("Reverse-split round-up", title, f"{len(events)} order(s)" if events else
                             f"{len(unc)} unconfirmed", blocks))
    if not rows and not unc:
        return None
    if not rows:
        return (f"Round-up (unconfirmed): {', '.join(str(r['ticker']) for r in unconfirmed)} filed a round-up split",
                M.page("Reverse-split round-up", "Unconfirmed round-up candidates (EDGAR)", f"{len(unc)} filings", [
                    M.action("Check", "EDGAR names these splits before Alpaca lists them", lines=[
                        "Buy 1 share per account by the session before the filing's effective date if you want to be "
                        "early; the watch re-checks Alpaca every morning and alerts again once it confirms."])]
                    + unc_block + unc_links))
    first = min(r["buy_by"] for r in rows.values())
    return (f"Round-up: buy 1 share of {', '.join(rows)} in each account by {first}",
            M.page("Reverse-split round-up", f"Buy 1 share of {', '.join(rows)} in each account", f"by the close of {first}", [
                M.action("Act by the buy-by date", "Buy exactly 1 share per account (Brokerage and Roth)", lines=[
                    "Market order or a limit a cent above the ask, on or before the last session before the split. "
                    "Hold it through the split."]),
                M.facts(split_facts, "Splits"),
                M.steps(["Buy 1 share in each account by the date above.",
                         "A day to a few weeks after the split the position should show 1 post-split share (worth about "
                         "N x what you paid). Sell it whenever you like.",
                         "If it shows 0 shares and a few cents of cash, Schwab paid cash in lieu: you lost about nothing. "
                         "After 2-3 of those, stop."], "Then")] + unc_block + [
                M.fine("Risk per deal: the price of 1 share (median $0.25). Turn on automatic buying with ROUNDUP_AUTO=1 "
                       "in the server's .env.")] + [M.link(r["url"], f"{r['ticker']}: the round-up clause ({r.get('form')})")
                                                   for r in rows.values()] + unc_links))


def run(state_dir: Path, today: dt.date | None = None, email: bool = True, log=print,
        order_mode: str | None = None) -> list[dict]:
    """One morning. Rows appended to state/roundup-watch.jsonl this run, each with an `outcome`:
      qualified      the alert row (alert=True, buy_by, trade_date, sentence, url; promoted_from=adsh when an EDGAR
                     unconfirmed row preceded it)
      qualified-known  a discovery filing for a split Alpaca already lists (the Alpaca path owns the alert)
      no-roundup     an upcoming split (Alpaca, `checked`) or a discovery filing (`source` edgar, `adsh`) with no
                     holder-level round-up sentence
      late-dropped   qualified, but the buy-by session had passed when first seen (`checked` so it is not re-run)
      no-cik         Alpaca symbol not in SEC's ticker file
      unconfirmed    EDGAR-only find: sentence + effective date parsed from the filing, Alpaca has not listed it
                     (`unconfirmed`=True, ex_date=parsed date or None, emailed only when the date is on/after today)
      unconfirmed-expired  the parsed date passed with no Alpaca listing
      order-placed / no-order   one row per account per deal from roundup_orders.manage (`account`, `reason`,
                     `order_id`, `limit`); no-order carries the exact reason (no usable quote, cap, broker error)
    `order_mode`: roundup_orders mode ("day" = the current DAY limit at the ask; "gtc" = GTC at or below the last
    close); None reads config.yaml daily.roundup_order_mode."""
    from ..data import trading_days
    from ..live.notify import Notifier
    from . import marketdata as md
    from .news_judge import _cik_map
    path = Path(state_dir) / LOG_NAME
    rows = _read(path)
    alerted = {(r["ticker"], r["trade_date"]): r for r in rows if r.get("alert")}
    checked = {(r["ticker"], r["ex_date"]) for r in rows if r.get("checked")}
    seen_adsh = {r["adsh"] for r in rows if r.get("adsh") and r.get("source") == "edgar"}
    closed = {r.get("promoted_from") or r.get("adsh") for r in rows
              if r.get("promoted_from") or r.get("outcome") == "unconfirmed-expired"}
    unconf = {r["adsh"]: r for r in rows if r.get("outcome") == "unconfirmed" and r["adsh"] not in closed}
    today = today or dt.date.today()
    cik = _cik_map(Path(state_dir))
    new, misses, out = [], [], []
    if order_mode is None:
        from ..config import Config
        order_mode = getattr(Config.load().daily, "roundup_order_mode", "day")
    # 1. Alpaca (authoritative ex-date)
    alp = upcoming(today)
    alp_tickers = {u["ticker"] for u in alp}
    for u in alp:
        key = (u["ticker"], u["ex_date"])
        if key in alerted or key in checked:
            continue
        if u["ticker"] not in cik:
            r = dict(checked=str(today), outcome="no-cik", **u)
            misses.append(r); log(f"[roundup] {u['ticker']} ex {u['ex_date']}: not in SEC's ticker file, skipped")
            continue
        q = qualify(cik[u["ticker"]], u["ex_date"])
        if not q:
            misses.append(dict(checked=str(today), outcome="no-roundup", **u))
            continue
        sess = [d.date() for d in trading_days(today - dt.timedelta(days=7), dt.date.fromisoformat(u["ex_date"]))]
        buy_by = max(d for d in sess if d < dt.date.fromisoformat(u["ex_date"]))
        if buy_by < today:
            r = dict(checked=str(today), outcome="late-dropped", buy_by=str(buy_by), **u, **q)
            misses.append(r)
            log(f"[roundup] {u['ticker']} 1-for-{u['ratio']:g} ex {u['ex_date']} qualified but buy-by {buy_by} has "
                f"passed (first seen {today}): LATE, no alert")
            continue
        b = md.sip_daily([u["ticker"]], today - dt.timedelta(days=10)).get(u["ticker"])
        r = dict(date=str(today), ticker=u["ticker"], trade_date=u["ex_date"], buy_by=str(buy_by), ratio=u["ratio"],
                 last_close=float(b.close.iloc[-1]) if b is not None and len(b) else None, alert=True, outcome="qualified",
                 **q)
        prev = [x for x in unconf.values() if x.get("ticker") == u["ticker"] or x.get("cik") == cik[u["ticker"]]]
        if prev:
            r["promoted_from"] = prev[0]["adsh"]
            log(f"[roundup] {u['ticker']} confirmed by Alpaca (EDGAR unconfirmed since {prev[0]['date']})")
        new.append(r)
        log(f"[roundup] {r['ticker']} 1-for-{r['ratio']:g} ex {r['trade_date']} buy by {r['buy_by']}: {q['sentence'][:90]}")
    # 2. EDGAR full-text discovery (lead time): unconfirmed until Alpaca lists the split
    new_unconf = []
    try:
        found = edgar_upcoming(today, skip=seen_adsh)
    except Exception as exc:                        # never let discovery break the Alpaca path
        log(f"[roundup] EDGAR discovery failed: {str(exc)[:120]}"); found = []
    for c in found:
        r = dict(date=str(today), **c)
        if not c["sentence"]:
            r["outcome"] = "no-roundup"
        elif c["ticker"] in alp_tickers or any(k[0] == c["ticker"] and k[1] >= str(today - dt.timedelta(days=30))
                                               for k in alerted):
            r["outcome"] = "qualified-known"        # Alpaca lists it (or alerted it in the last 30 days): the Alpaca path owns it
        elif c["ex_date"] and c["ex_date"] < str(today):
            r["outcome"] = "late-dropped"
            log(f"[roundup] EDGAR {c['ticker']} {c['form']} {c['filed']}: round-up split effective {c['ex_date']} "
                f"already passed, LATE")
        else:
            r.update(outcome="unconfirmed", unconfirmed=True)
            unconf[c["adsh"]] = r
            if c["ex_date"]:
                new_unconf.append(r)
            log(f"[roundup] EDGAR {c['ticker']} {c['form']} {c['filed']}: round-up split, effective "
                f"{c['ex_date'] or 'date not stated'} (UNCONFIRMED by Alpaca): {c['sentence'][:80]}")
        out.append(r)
    for a, r in list(unconf.items()):               # re-check: parsed date passed, Alpaca never listed it
        if r.get("ex_date") and r["ex_date"] < str(today) and r.get("ticker") not in alp_tickers \
                and not any(x.get("promoted_from") == a for x in new):
            out.append(dict(date=str(today), ticker=r.get("ticker"), cik=r.get("cik"), adsh=a, ex_date=r["ex_date"],
                            source="edgar", outcome="unconfirmed-expired"))
            log(f"[roundup] EDGAR {r.get('ticker')}: effective {r['ex_date']} passed without an Alpaca listing")
    done = {(r["ticker"], r["trade_date"]) for r in rows if r.get("scored")}
    scored = [s for k, r in alerted.items() if k not in done and (s := score(r, today))]
    for s in scored:
        log(f"[roundup] scored {s['ticker']} {s['trade_date']}: gain if rounded ${s['gain_if_rounded']:+.2f}")
    due = [r for r in alerted.values() if r.get("buy_by") == str(today)]
    from . import roundup_orders as ro
    events: list = []
    outcomes: list = []
    note = Notifier(Path(state_dir)) if email else None
    with path.open("a") as f:
        for r in new + misses + scored + out:
            f.write(json.dumps(r) + "\n")
    if ro.enabled():                       # automatic 1-share buys/sells (user-approved 2026-10-02); ROUNDUP_AUTO=1
        try:
            ro.manage(state_dir, list(alerted.values()) + new, today, events=events,   # prices: each account's Schwab ask
                      notify=(lambda s, h: note.mail(s, h)) if note else None, log=log, outcomes=outcomes,
                      mode=order_mode)
        finally:                           # the order outcomes are on file even when manage() raises
            with path.open("a") as f:
                for o in outcomes:
                    f.write(json.dumps(dict(date=str(today), **o)) + "\n")
    msg = build_email(new, due, events, ro.enabled(), unconfirmed=new_unconf)
    if note and msg:
        note.mail(*msg)
    log(f"[roundup] {len(new)} new round-up splits ({len(misses)} upcoming splits without a holder-level round-up or late), "
        f"{len(new_unconf)} unconfirmed from EDGAR, {len(due)} due today, {len(scored)} scored, "
        f"{sum(o['outcome'] == 'no-order' for o in outcomes)} no-order")
    return new


if __name__ == "__main__":
    import sys
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    run(Path(__file__).resolve().parents[2] / "state", dt.date.fromisoformat(a[0]) if a else None,
        email="--no-email" not in sys.argv)
