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
alternative in it), and none may say the rounding is at the "participant level" / "DTC participant" / "Cede". Each
qualifying split is logged to state/roundup-watch.jsonl and emailed with its buy-by session (the last session before
the ex-date), and reminded on that day; after the ex-date it is scored from raw bars (post-split close − pre-split
close = the gain if rounded up).
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
           '"rounded up to the nearest whole number" "reverse stock split"']
PL = re.compile(r"participant level|DTC participant|at the participant|Cede ?& ?Co", re.I)
CASH = re.compile(r"cash (?:in lieu|payment)|paid in cash|receive (?:a )?cash|or to entitle", re.I)


def round_up_sentence(text: str) -> str | None:
    """A forward-looking sentence ("will/shall/would be rounded up") about the split's fractional shares, with no cash
    alternative in it, else None. Past-tense sentences describe an earlier split (10-Q/10-K history)."""
    for sen in re.split(r"(?<=[.;])\s+", clean(text)):
        if (re.search(r"fraction", sen, re.I) and re.search(r"round(?:ed|ing)? up", sen, re.I)
                and re.search(r"split|whole (?:share|number)", sen, re.I) and re.search(r"\b(?:will|shall|would)\b", sen, re.I)
                and not CASH.search(sen)):
            return sen.strip()[:400]
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
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{h['adsh'].replace('-', '')}/{h['id'].split(':', 1)[1]}"
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
    from .marketdata import _clients, trade_date
    data, _ = _clients()
    df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=[sym], timeframe=TimeFrame.Day,
                                              start=pd.Timestamp(start, tz="UTC"), end=pd.Timestamp(end, tz="UTC"),
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


def build_email(new: list[dict], due: list[dict], events: list, auto: bool) -> tuple[str, str] | None:
    """(subject, html) for this run, or None. Auto: what the bot did. Manual: what to buy and by when."""
    from ..live import mail as M
    rows = {r["ticker"]: r for r in new + due}
    split_facts = []
    for r in rows.values():
        n = r.get("ratio")
        val = f", ~${(n - 1) * r['last_close']:.2f} if rounded up" if n and r.get("last_close") else ""
        split_facts.append((f"{r['ticker']} 1-for-{n:g}", f"buy by {r['buy_by']}, splits {r['trade_date']}{val}"))
    if auto:
        if not events:
            return None
        verb = {"bought": "Bought", "sold": "Sold", "cash": "Cash in lieu"}
        acts = [(f"{verb[k]} {sym} · {'Brokerage' if a == 'live' else 'Roth'}", d) for k, a, sym, d in events]
        kinds = {k for k, *_ in events}
        title = ("Bought 1 share for the round-up" if kinds == {"bought"} else "Round-up update")
        blocks = [M.action("Nothing to do", title, lines=[
                      "The bot buys 1 share per account before each qualifying reverse split and sells the post-split "
                      "share once Schwab credits it. These are the orders it placed this morning."], tone="info"),
                  M.facts(acts, "This morning")]
        if split_facts:
            blocks.append(M.facts(split_facts, "Splits"))
        blocks.append(M.fine("If Schwab rounds up, each account ends with 1 post-split share worth about N x the price "
                             "paid; if it pays cash in lieu instead, the loss is about the price of 1 share. After 2 "
                             "cash-in-lieu outcomes with none rounded, an account stops buying (you get an email). "
                             "Switch off: remove ROUNDUP_AUTO=1 from the server's .env."))
        return (f"Round-up: {', '.join(sorted({e[2] for e in events}))} - {', '.join(sorted(kinds))}",
                M.page("Reverse-split round-up", title, f"{len(events)} order(s)", blocks))
    if not rows:
        return None
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
                         "After 2-3 of those, stop."], "Then"),
                M.fine("Risk per deal: the price of 1 share (median $0.25). Turn on automatic buying with ROUNDUP_AUTO=1 "
                       "in the server's .env.")] + [M.link(r["url"], f"{r['ticker']}: the round-up clause ({r.get('form')})")
                                                   for r in rows.values()]))


def run(state_dir: Path, today: dt.date | None = None, email: bool = True, log=print) -> list[dict]:
    from ..data import trading_days
    from ..live.notify import Notifier
    from . import marketdata as md
    from .news_judge import _cik_map
    path = Path(state_dir) / LOG_NAME
    rows = _read(path)
    alerted = {(r["ticker"], r["trade_date"]): r for r in rows if r.get("alert")}
    checked = {(r["ticker"], r["ex_date"]) for r in rows if r.get("checked")}
    today = today or dt.date.today()
    cik = _cik_map(Path(state_dir))
    new, misses = [], []
    for u in upcoming(today):
        key = (u["ticker"], u["ex_date"])
        if key in alerted or key in checked or u["ticker"] not in cik:
            continue
        q = qualify(cik[u["ticker"]], u["ex_date"])
        if not q:
            misses.append(dict(checked=str(today), **u))
            continue
        sess = [d.date() for d in trading_days(today - dt.timedelta(days=7), dt.date.fromisoformat(u["ex_date"]))]
        buy_by = max(d for d in sess if d < dt.date.fromisoformat(u["ex_date"]))
        if buy_by < today:
            continue
        b = md.sip_daily([u["ticker"]], today - dt.timedelta(days=10)).get(u["ticker"])
        r = dict(date=str(today), ticker=u["ticker"], trade_date=u["ex_date"], buy_by=str(buy_by), ratio=u["ratio"],
                 last_close=float(b.close.iloc[-1]) if b is not None and len(b) else None, alert=True, **q)
        new.append(r)
        log(f"[roundup] {r['ticker']} 1-for-{r['ratio']:g} ex {r['trade_date']} buy by {r['buy_by']}: {q['sentence'][:90]}")
    done = {(r["ticker"], r["trade_date"]) for r in rows if r.get("scored")}
    scored = [s for k, r in alerted.items() if k not in done and (s := score(r, today))]
    for s in scored:
        log(f"[roundup] scored {s['ticker']} {s['trade_date']}: gain if rounded ${s['gain_if_rounded']:+.2f}")
    with path.open("a") as f:
        for r in new + misses + scored:
            f.write(json.dumps(r) + "\n")
    due = [r for r in alerted.values() if r.get("buy_by") == str(today)]
    from . import roundup_orders as ro
    events: list = []
    note = Notifier(Path(state_dir)) if email else None
    if ro.enabled():                       # automatic 1-share buys/sells (user-approved 2026-10-02); ROUNDUP_AUTO=1
        ro.manage(state_dir, list(alerted.values()) + new, today, events=events,   # prices: each account's Schwab ask
                  notify=(lambda s, h: note.mail(s, h)) if note else None, log=log)
    msg = build_email(new, due, events, ro.enabled())
    if note and msg:
        note.mail(*msg)
    log(f"[roundup] {len(new)} new round-up splits ({len(misses)} upcoming splits without a holder-level round-up), "
        f"{len(due)} due today, {len(scored)} scored")
    return new


if __name__ == "__main__":
    import sys
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    run(Path(__file__).resolve().parents[2] / "state", dt.date.fromisoformat(a[0]) if a else None,
        email="--no-email" not in sys.argv)
