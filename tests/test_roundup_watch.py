"""Round 32 B1 reverse-split round-up watch: which sentences qualify. No network."""
import datetime as dt
import json
from types import SimpleNamespace

from swingtrader.daily import roundup_watch as w


def test_forward_round_up_sentence_qualifies():
    t = ("<p>No fractional shares will be issued in connection with the Reverse Stock Split, and any fractional shares "
         "resulting from the Reverse Stock Split will be rounded up to the nearest whole share.</p>")
    assert "rounded up" in w.round_up_sentence(t)


def test_cash_in_lieu_option_and_past_tense_do_not():
    cash = ("Stockholders who would otherwise be entitled to a fractional share as a result of the reverse split will "
            "receive a cash payment in lieu of such fractional share, or such fraction will be rounded up.")
    option = ("The Board may elect to issue fractions, or to entitle shareholders to receive, in lieu of any fractional "
              "share, the number of shares rounded up to the next whole number following the reverse split.")
    past = "Any fractional shares resulting from the Reverse Stock Split were rounded up to the nearest whole share."
    assert w.round_up_sentence(cash) is None
    assert w.round_up_sentence(option) is None
    assert w.round_up_sentence(past) is None


def test_unrelated_round_up_text_does_not_qualify():
    reit = ("that number of shares (rounded up to the nearest whole share) in excess of the ownership limit will be "
            "transferred to a charitable trust.")
    assert w.round_up_sentence(reit) is None


def test_participant_level_language_is_caught():
    t = "fractional shares will be rounded up to the nearest whole share at the participant level"
    assert w.PL.search(t)


def test_whole_share_in_lieu_wording_qualifies():
    t = ("If as a result of the reverse stock split a stockholder would otherwise hold a fractional share, the stockholder "
         "will receive one whole share in lieu of the issuance of any such fractional share.")
    assert w.round_up_sentence(t) is not None
    cash = ("Stockholders who would otherwise hold a fractional share as a result of the reverse stock split will receive "
            "cash in lieu of the fractional share.")
    assert w.round_up_sentence(cash) is None


# ---- 2026-10-26 audit: qualification false positives (negative regressions) and EDGAR discovery
AXNX = ("Rather, the number of Class A Ordinary Shares to be issued will, at our election, either be rounded up to the "
        "nearest whole number or we will pay a cash adjustment in respect of such final fraction in an amount equal to such "
        "fraction multiplied by the exercise price.")
GCTK = ("No fractional shares of Common Stock are to be issued upon the exercise of this Warrant, but rather the number of "
        "shares of Common Stock to be issued shall be rounded up to the nearest whole number.")
PPCB = ("Except for adjustments that may result from the treatment of fractional shares, which will be rounded up to the "
        "nearest whole number, each shareholder will beneficially hold the same percentage of Common Stock immediately "
        "following the Reverse Stock Split as such shareholder held immediately prior to the Reverse Stock Split.")


def test_cash_adjustment_and_warrant_clauses_do_not_qualify():
    assert w.round_up_sentence(AXNX) is None                     # "or we will pay a cash adjustment"
    assert w.round_up_sentence(GCTK) is None                     # a warrant's own fraction clause
    for cash in ("will be paid in cash", "will receive cash in lieu", "will receive a cash payment"):
        t = f"Fractional shares resulting from the reverse stock split will be rounded up, or holders {cash}."
        assert w.round_up_sentence(t) is None, cash
    conv = ("Any fractional share resulting from the conversion of the Notes after the reverse stock split will be "
            "rounded up to the nearest whole share.")
    assert w.round_up_sentence(conv) is None
    assert w.round_up_sentence(PPCB) is not None                 # a genuine split clause still qualifies


def test_effective_date_and_ratio_parse():
    today = dt.date(2026, 10, 26)
    t = ("The Company will effect a 1-for-25 reverse stock split. The reverse stock split will become effective at "
         "12:01 a.m. Eastern Time on November 3, 2026, and the shares will begin trading on a split-adjusted basis on "
         "November 3, 2026. The prior split was effective as of March 2, 2024.")
    assert w.effective_date(t, today) == dt.date(2026, 11, 3)    # earliest date on/after today, not the old one
    assert w.effective_date("effective as of October 21, 2026 only", today) == dt.date(2026, 10, 21)   # late, not unknown
    assert w.effective_date("effective as of March 2, 2024 only", today) is None       # > 30 days back: not this split
    assert w.effective_date("will become effective on July 13, 2027", today) is None   # > 60 days out: a proxy window
    assert w.effective_date("the split will be effective at such time as the board determines", today) is None
    assert w.split_ratio(t) == 25.0
    assert w.split_ratio("a one-for-twenty reverse stock split") == 20.0
    assert w.split_ratio("no ratio named") is None


def test_edgar_discovery_parses_hits_and_keeps_one_row_per_filing(monkeypatch):
    today = dt.date(2026, 10, 26)
    hits = {"hits": {"hits": [
        {"_id": "0001-26-1:ex99.htm", "_source": {"adsh": "0001-26-1", "form": "6-K", "file_date": "2026-10-21",
                                                  "ciks": ["0001897532"], "display_names": ["Ping An  (PASW)  (CIK 0001897532)"]}},
        {"_id": "0001-26-1:main.htm", "_source": {"adsh": "0001-26-1", "form": "6-K", "file_date": "2026-10-21",
                                                  "ciks": ["0001897532"], "display_names": ["Ping An  (PASW)  (CIK 0001897532)"]}},
        {"_id": "0002-26-2:ex4.htm", "_source": {"adsh": "0002-26-2", "form": "8-K", "file_date": "2026-10-22",
                                                 "ciks": ["0001506983"], "display_names": ["Glucotrack  (GCTK, GCTKW)  (CIK 0001506983)"]}},
        {"_id": "0003-26-3:x.htm", "_source": {"adsh": "0003-26-3", "form": "8-K", "file_date": "2026-10-20",
                                               "ciks": ["0000000009"], "display_names": ["Old  (OLD)  (CIK 0000000009)"]}},
    ]}}
    texts = {"ex99.htm": "<p>Cover page only.</p>",
             "main.htm": ("<p>The Board approved a 1-for-10 reverse stock split effective on November 2, 2026. Any fractional "
                          "shares resulting from the reverse stock split will be rounded up to the nearest whole share.</p>"),
             "ex4.htm": GCTK,
             "x.htm": "Skipped: already logged"}
    monkeypatch.setattr(w, "_sec_get", lambda url: json.dumps(hits) if "search-index" in url else None)
    fetched = []
    def fetch(url):
        fetched.append(url)
        return texts[url.rsplit("/", 1)[1]]
    out = w.edgar_upcoming(today, skip={"0003-26-3"}, fetch=fetch)
    assert "x.htm" not in " ".join(fetched)                      # skipped filings are not fetched again
    by = {r["adsh"]: r for r in out}
    assert set(by) == {"0001-26-1", "0002-26-2"}                 # one row per filing
    p = by["0001-26-1"]
    assert p["ticker"] == "PASW" and p["cik"] == 1897532 and p["ex_date"] == "2026-11-02" and p["ratio"] == 10.0
    assert p["sentence"] and p["source"] == "edgar" and p["url"].endswith("/1897532/0001261/main.htm")
    g = by["0002-26-2"]
    assert g["ticker"] == "GCTK" and g["sentence"] is None       # the warrant clause: logged as no-roundup
    assert "efts.sec.gov" in w.discovery_url(today) and "startdt=2026-10-19" in w.discovery_url(today)


def _run_patched(monkeypatch, tmp_path, today, alpaca, edgar, order_mode="day", auto=False, manage=None):
    """run() with every network call faked; returns (new, rows on file, mails)."""
    import pandas as pd
    from swingtrader.daily import roundup_orders as ro
    mails = []
    monkeypatch.setattr(w, "upcoming", lambda t, days=14: alpaca)
    monkeypatch.setattr(w, "edgar_upcoming", lambda t, skip=frozenset(), days=7, fetch=None: [
        c for c in edgar if c["adsh"] not in skip])
    monkeypatch.setattr(w, "qualify", lambda cik, ex: dict(sentence="will be rounded up", url="u", form="8-K", filed="2026-10-20"))
    monkeypatch.setattr(w, "score", lambda r, t: None)
    monkeypatch.setattr("swingtrader.daily.news_judge._cik_map", lambda d: {"AAA": 1, "LATE": 2, "PASW": 1897532})
    monkeypatch.setattr("swingtrader.data.trading_days",
                        lambda s, e: pd.bdate_range(pd.Timestamp(s), pd.Timestamp(e)))
    monkeypatch.setattr("swingtrader.daily.marketdata.sip_daily",
                        lambda syms, start: {s: pd.DataFrame(dict(close=[0.5])) for s in syms})
    monkeypatch.setattr("swingtrader.live.notify.Notifier",
                        lambda d: SimpleNamespace(mail=lambda s, h: mails.append(s)))
    monkeypatch.setattr(ro, "enabled", lambda: auto)
    if manage is not None:
        monkeypatch.setattr(ro, "manage", manage)
    new = w.run(tmp_path, today, email=True, log=lambda *a: None, order_mode=order_mode)
    rows = [json.loads(l) for l in (tmp_path / w.LOG_NAME).read_text().splitlines()]
    return new, rows, mails


def test_run_logs_every_outcome_and_promotes_edgar_finds(monkeypatch, tmp_path):
    today = dt.date(2026, 10, 26)
    edgar = [dict(ticker="PASW", cik=1897532, adsh="0001-26-1", form="6-K", filed="2026-10-21", url="u1",
                  sentence="will be rounded up", source="edgar", ex_date="2026-11-02", ratio=10.0),
             dict(ticker="META", cik=1, adsh="0009-26-9", form="8-K", filed="2026-10-21", url="u9", sentence=None,
                  source="edgar")]
    alpaca = [dict(ticker="AAA", ex_date="2026-10-28", ratio=5.0),     # buy-by 10-27 >= today: alert
              dict(ticker="LATE", ex_date="2026-10-26", ratio=5.0),    # ex today: buy-by passed -> late-dropped
              dict(ticker="NOCIK", ex_date="2026-10-30", ratio=5.0)]
    new, rows, mails = _run_patched(monkeypatch, tmp_path, today, alpaca, edgar)
    oc = {(r["ticker"], r["outcome"]) for r in rows}
    assert ("AAA", "qualified") in oc and ("LATE", "late-dropped") in oc and ("NOCIK", "no-cik") in oc
    assert ("PASW", "unconfirmed") in oc and ("META", "no-roundup") in oc
    late = next(r for r in rows if r["ticker"] == "LATE")
    assert late["checked"] == "2026-10-26" and late["buy_by"] == "2026-10-23" and late["sentence"]
    unc = next(r for r in rows if r["ticker"] == "PASW")
    assert unc["unconfirmed"] and unc["ex_date"] == "2026-11-02" and not unc.get("alert")
    assert [r["ticker"] for r in new] == ["AAA"]
    assert len(mails) == 1 and "AAA" in mails[0]
    # next morning: nothing is re-fetched or re-alerted; Alpaca now lists PASW -> promoted to a normal alert
    alpaca.append(dict(ticker="PASW", ex_date="2026-11-02", ratio=10.0))
    new2, rows2, mails2 = _run_patched(monkeypatch, tmp_path, dt.date(2026, 10, 27), alpaca, edgar)
    assert [r["ticker"] for r in new2] == ["PASW"] and new2[0]["promoted_from"] == "0001-26-1"
    assert sum(r.get("outcome") == "unconfirmed" for r in rows2) == 1
    assert sum(r["ticker"] == "LATE" for r in rows2) == 1               # checked once, never re-run
    # the ledger reader still sees only the real alerts
    from swingtrader.daily import cpc_ledger as L
    assert sorted(e["security"] for e in L.from_roundup(rows2)) == ["AAA", "PASW"]


def test_run_emails_unconfirmed_alone_and_writes_order_outcomes(monkeypatch, tmp_path):
    today = dt.date(2026, 10, 26)
    edgar = [dict(ticker="PASW", cik=1897532, adsh="0001-26-1", form="6-K", filed="2026-10-21", url="u1",
                  sentence="will be rounded up", source="edgar", ex_date="2026-11-02", ratio=10.0)]
    seen = {}
    def manage(state_dir, alerts, t, **kw):
        seen.update(kw)
        kw["outcomes"].append(dict(ticker="AAA", trade_date="2026-10-28", account="live", outcome="no-order",
                                   reason="no usable quote (None) - retry next run"))
        return {}
    alpaca = [dict(ticker="AAA", ex_date="2026-10-28", ratio=5.0)]
    new, rows, mails = _run_patched(monkeypatch, tmp_path, today, alpaca, edgar, order_mode="gtc", auto=True, manage=manage)
    assert seen["mode"] == "gtc"
    o = next(r for r in rows if r.get("outcome") == "no-order")
    assert o["account"] == "live" and o["reason"].startswith("no usable quote") and o["date"] == "2026-10-26"
    assert len(mails) == 1 and "unconfirmed" in mails[0] and "PASW" in mails[0]   # auto mode, no orders: still mailed
    # an unconfirmed candidate whose parsed date passes without Alpaca -> expired, once
    _, rows3, _ = _run_patched(monkeypatch, tmp_path, dt.date(2026, 11, 3), [], edgar, auto=False)
    assert sum(r.get("outcome") == "unconfirmed-expired" for r in rows3) == 1
    _, rows4, _ = _run_patched(monkeypatch, tmp_path, dt.date(2026, 11, 4), [], edgar, auto=False)
    assert sum(r.get("outcome") == "unconfirmed-expired" for r in rows4) == 1
