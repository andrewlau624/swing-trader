"""Every email shares live/mail.py's look and puts the command to run in the action box. No network."""
import datetime as dt

from swingtrader.daily import roundup_watch, splitoff_watch, tender_watch
from swingtrader.daily.schwab_reminder import _body
from swingtrader.live import mail as M

MDT = dict(parent="MDT", recv="MMED", expires="2026-10-09", per100=107.53, cap=4.5939, url="https://sec.gov/x")


def _looks_right(html, *must):
    assert html.startswith("<div style='background:#eaeef2") and M.BAND in html     # the digest's card + band
    for m in must:
        assert m in html, m


def test_text_is_escaped():
    assert "&lt;b&gt;" in M.page("k", "<b>", blocks=[M.para("<b>")])


def test_tender_email_has_the_command():
    r = dict(ticker="UTMD", name="Utah Medical", floor=75.0, last_close=74.0, floor_gain=0.0135, kind="fixed",
             expires="2026-10-07", date="2026-10-01", path="edgar/data/1/x.txt")
    subj, html = tender_watch.offer_email(r)
    assert "UTMD" in subj and "act today" in subj
    _looks_right(html, "make tender-buy ID=UTMD-2026-10-01", "odd-lot certification")
    assert "REMINDER" in tender_watch.offer_email(r, reminder=True)[0]


def test_splitoff_emails_have_the_command():
    subj, html = splitoff_watch.entry_email(MDT, 0.042, 86.44, 19.60)
    _looks_right(html, "make splitoff-buy PARENT=MDT", "binding now", "4.5939")
    _, html = splitoff_watch.new_offer_email(dict(MDT, name="Medtronic plc -> MiniMed Group, Inc.", recv=None, odd_lot="Y"))
    _looks_right(html, "make splitoff-add ARGS=")


def test_roundup_email_auto_and_manual():
    r = dict(ticker="VIVK", ratio=15.0, trade_date="2026-10-05", buy_by="2026-10-02", last_close=0.3181,
             url="https://sec.gov/v", form="8-K")
    assert roundup_watch.build_email([r], [], [], auto=True) is None                    # auto, nothing done: no email
    subj, html = roundup_watch.build_email([r], [], [("bought", "live", "VIVK", "1 share")], auto=True)
    _looks_right(html, "Bought VIVK", "NOTHING TO DO")
    subj, html = roundup_watch.build_email([r], [], [], auto=False)
    _looks_right(html, "buy by 2026-10-02")


def test_schwab_reminder_has_the_command():
    _looks_right(_body("expires TOMORROW", dt.datetime(2026, 10, 9, 9, 0)), "make schwab-login")
