import datetime as dt
import json
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from research.sim.cef_rights_fetch import classify, clean
from swingtrader.daily import cef_rights_shadow as W

ET = ZoneInfo("America/New_York")
HOLIDAYS = {"2025-11-27", "2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16"}

PROSPECTUS = (b"<html><body><p>Rights Offering for Common Shares</p><p>The Fund is issuing non-transferable "
              b"subscription rights to its common shareholders. The Fund's 2023 rights offering expired on March&nbsp;3, 2023. "
              b"The Rights will expire at 5:00 p.m., New York City time, on <b>December 12, 2025</b>, unless extended. "
              b"The subscription price per share will be 92.5% of the average closing price.</p></body></html>")


def sessions(start="2025-10-01", end="2026-03-31", half=("2025-11-28",), bad=()):
    out = []
    for d in pd.bdate_range(start, end):
        s = str(d.date())
        if s in HOLIDAYS:
            continue
        o = dt.datetime(d.year, d.month, d.day, 9, 30, tzinfo=ET)
        c = dt.datetime(d.year, d.month, d.day, 13 if s in half else (20 if s in bad else 16), 0, tzinfo=ET)
        out.append((o, c))
    return out


def test_classify_parses_the_offering_expiry_not_a_past_one():
    c = classify(clean(PROSPECTUS), pd.Timestamp("2025-11-10"))
    assert c["expiry"] == pd.Timestamp("2025-12-12")
    assert c["transferable"] is False and c["preferred"] is False
    assert classify(clean(b"<p>Annual report. Distribution rate 8%.</p>"), pd.Timestamp("2025-11-10")) is None


def test_window_on_the_regular_calendar():
    days = W.session_days(sessions())
    assert "2025-11-27" not in days and "2025-11-28" in days          # holiday dropped, half day kept
    w = W.window(days, "2025-12-12")
    assert w["E"] == "2025-12-12"
    assert days.index(w["E"]) - days.index(w["entry"]) == 10 and days.index(w["exit"]) - days.index(w["E"]) == 25
    assert w["entry"] == "2025-11-28"                                 # 10 sessions back across Thanksgiving
    assert w["pw_hi"] == days[days.index("2025-12-12") + 5]
    assert W.window(days, "2025-12-13")["E"] == "2025-12-15"          # Saturday expiry -> next session
    assert W.window(days, "2026-03-20") is None                        # calendar does not reach E+25


def test_session_days_rejects_a_non_regular_calendar():
    with pytest.raises(ValueError):
        W.session_days(sessions(bad=("2025-12-01",)))


def _fetch(url, path, limit=None):
    if url == W.TICKERS_URL:
        return json.dumps({"0": {"cik_str": 111, "ticker": "AAA"}, "1": {"cik_str": 222, "ticker": "BBB"},
                           "2": {"cik_str": 333, "ticker": "CCC"}}).encode()
    if "submissions" in url:
        cik = int(url.split("CIK")[1][:10])
        if cik != 111:
            return json.dumps({"filings": {"recent": {"accessionNumber": ["0000-1"], "filingDate": ["2010-01-01"],
                                                      "form": ["N-CSR"], "primaryDocument": ["x.htm"]}}}).encode()
        return json.dumps({"filings": {"recent": {
            "accessionNumber": ["0001-25-000001", "0001-25-000002", "0001-10-000003"],
            "filingDate": ["2025-11-10", "2025-11-12", "2010-01-01"],
            "form": ["497", "424B3", "N-2"], "primaryDocument": ["p.htm", "p2.htm", "n2.htm"]}}}).encode()
    return PROSPECTUS


def _crosses(syms, start, end, H):
    days = W.session_days(sessions())
    out = {}
    for s in syms:
        out[s] = {}
        for k, d in enumerate(days):
            px = 10.0 if s != "AAA" else (10.0 if d <= "2025-11-28" else 9.0)    # AAA falls 10% after entry, others flat
            out[s][d] = (px, 100, px, 100)
    return out


def test_run_logs_upcoming_then_scores_and_never_orders(tmp_path, monkeypatch):
    from swingtrader.daily import brokers
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("order path touched"))  # noqa: E731
    monkeypatch.setattr(brokers, "make_adapter", boom)
    monkeypatch.setattr(brokers.SchwabAdapter, "submit", boom)
    monkeypatch.setattr(brokers.AlpacaAdapter, "submit", boom)
    kw = dict(syms=["AAA", "BBB", "CCC"], fetch=_fetch, sessions_fn=lambda a, b: sessions(), crosses_fn=_crosses,
              divs_fn=lambda *a: {}, borrow_fn=lambda s: dict(alpaca_shortable=True, alpaca_etb=False, schwab_shortable=None,
                                                             schwab_htb=True, schwab_htb_rate=12.0, schwab_htb_qty=None),
              log=lambda *a: None, workers=1)
    W.run(tmp_path, tmp_path, today=dt.date(2025, 11, 20), **kw)
    ev = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert len(ev) == 1                                                  # 497 + 424B3 supplement = one offering
    e = ev[0]
    assert (e["sym"], e["expiry"], e["entry"], e["status"], e["late"]) == ("AAA", "2025-12-12", "2025-11-28", "upcoming", False)
    assert e["borrow"][0]["date"] == "2025-11-20"
    W.run(tmp_path, tmp_path, today=dt.date(2026, 2, 1), **kw)
    e = json.loads((tmp_path / W.LOG_NAME).read_text().splitlines()[0])
    assert e["status"] == "scored"
    ew = (10 + 10 + 9) / 30 - 1                                          # EW includes the fund itself
    assert e["short_x"] == pytest.approx(-(-0.10 - ew), abs=1e-6)
    assert e["borrow_ok"] is True and e["borrow_rate"] == pytest.approx(0.12)
    assert e["net"] == pytest.approx(e["short_x"] - 0.004 - 0.12 * 35 / 252, abs=1e-6)
    assert W.summary([e])["n"] == 1


def test_hygiene_flags_cef_rv_trades_inside_the_pricing_window():
    e = dict(sym="AAA", cik=111, E="2025-12-12", pw_lo="2025-11-28", pw_hi="2025-12-19")
    rv = [dict(sym="AAA", signal="2025-11-21", entry="2025-12-01", exit=None, status="open"),
          dict(sym="AAA", signal="2025-06-06", entry="2025-06-09", exit="2025-11-03", status="closed", x_oo=0.01),
          dict(sym="AAA", signal="2025-10-03", entry="2025-10-06", exit="2025-12-29", status="closed", x_oo=-0.03),
          dict(sym="BBB", signal="2025-11-21", entry="2025-12-01", exit=None)]
    h = W.hygiene([e], rv, {"AAA": {"entry_date": "2025-12-01"}})
    assert [(r["src"], r.get("rel")) for r in h] == [("shadow", "entered_in_window"), ("shadow", "held_through"), ("live", "held_live")]
    assert "flagged OO excess -300bp vs unflagged +100bp" in W.hygiene_line(h, rv)


def test_merge_announces_from_497ad_and_takes_the_final_prospectus_expiry():
    ad = dict(cik=111, filed="2026-07-17", form="497AD", acc="a1", expiry="2026-07-28", transferable=True, final=False)
    fin = dict(cik=111, filed="2026-07-29", form="424B2", acc="a2", expiry="2026-08-03", transferable=False, final=True)
    ev = W.merge([], [ad], {111: ["AAA"]}, dt.date(2026, 7, 17))
    ev = W.merge(ev, [fin], {111: ["AAA"]}, dt.date(2026, 7, 29))
    assert len(ev) == 1
    e = ev[0]
    assert (e["announced"], e["expiry"], e["form"], e["final"], e["first_seen"]) == ("2026-07-17", "2026-08-03", "424B2", True,
                                                                                     "2026-07-17")
    assert e["alt_expiries"] == ["2026-07-28"]


def test_module_has_no_order_path():
    src = (W.__file__ and open(W.__file__).read())
    for bad in (".submit(", "make_adapter", "place_order", "executor"):
        assert bad not in src
