"""Round 31 odd-lot tender watch: term extraction, odd-lot clause, alert rule. No network."""
import numpy as np

from swingtrader.daily import tender_watch as w

FIXED = ("Offer to purchase up to 588,235 shares of its common stock, par value $1.00 per share, at a price of $34.00 "
         "per Share, net to the seller in cash. If more than 588,235 shares are properly tendered, the Company will "
         "purchase all shares tendered by holders of &ldquo;odd lots&rdquo; first, and then on a pro rata basis.")
DUTCH = ("at a price not greater than $40.00 nor less than $36.00 per share. Odd lots will be accepted for "
         "purchase before proration.")
NAV_PRORATED = ("at a price equal to 98% of net asset value per share. The Fund will purchase duly tendered Shares on a "
                "pro rata basis (odd-lot tenders for Stockholders who own fewer than 100 shares are still subject to pro ration).")


def test_fixed_price_with_priority():
    t = w.terms("<p>" + FIXED + "</p>")
    assert t["fixed"] == 34.0 and t["floor"] == 34.0 and t["odd_lot"] == "Y" and not t["nav"]


def test_dutch_floor_is_low_end():
    t = w.terms(DUTCH)
    assert (t["lo"], t["hi"], t["floor"]) == (36.0, 40.0, 36.0) and t["odd_lot"] == "Y"


def test_nav_offer_without_priority_never_alerts():
    t = w.terms(NAV_PRORATED)
    assert t["nav"] and t["odd_lot"] == "N"
    assert not w.candidate(t, 9.0)["alert"]


def test_par_value_is_not_a_price():
    t = w.terms("its common stock, par value $0.01 per share (the Shares), and its warrants at a price of $0.50 per share")
    assert np.isnan(t["fixed"])


def test_alert_rule():
    t = w.terms(FIXED)
    assert w.candidate(t, 32.30) == dict(floor_gain=round(34 / 32.3 - 1, 4), alert=True)
    assert not w.candidate(t, 34.0)["alert"]          # floor not >= +1% over the market
    assert not w.candidate(t, None)["alert"]


def test_idx_and_header():
    idx = ("SC TO-I      ABC CORP   1   20261001   edgar/data/1/0001-26-000001.txt\n"
           "SC TO-I/A    ABC CORP   1   20261001   edgar/data/1/0001-26-000002.txt\n"
           "SC TO-T      XYZ        3   20261001   edgar/data/3/0003-26-000003.txt\n")
    assert w.idx_paths(idx) == ["edgar/data/1/0001-26-000001.txt"]
    hdr = ("FILED BY:\n COMPANY DATA:\n COMPANY CONFORMED NAME: ABC CORP\n CENTRAL INDEX KEY: 0000000001\n"
           "SUBJECT COMPANY:\n COMPANY DATA:\n COMPANY CONFORMED NAME: ABC CORP\n CENTRAL INDEX KEY: 0000000001\n")
    assert w.header_company(hdr) == ("1", "ABC CORP")


def test_expiry_kind_and_instructions():
    import datetime as dt
    t = w.terms(FIXED + " The offer will expire at 5:00 p.m., New York City time, on Friday, October 30, 2026, unless extended.")
    assert t["expires"] == "2026-10-30" and t["kind"] == "fixed"
    r = dict(ticker="ABC", name="ABC CORP", last_close=32.3, path="edgar/data/1/x.txt",
             **t, **w.candidate(t, 32.3))
    txt = w.instructions(r)
    for must in ("99 or FEWER", "Tender ALL", "ODD LOT", "2026-10-30", "LIMIT", "conditional"):
        assert must in txt
    assert w.reminders([r], dt.date(2026, 10, 28)) == [r]
    assert w.reminders([r], dt.date(2026, 10, 20)) == []
    d = w.terms(DUTCH)
    assert d["kind"] == "dutch"
