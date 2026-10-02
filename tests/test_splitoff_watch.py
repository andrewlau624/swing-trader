"""Round 32 B2 split-off exchange-offer watch: detection, term parsing, upper-limit valuation, entry window. No network."""
import datetime as dt
import json

import pytest

from swingtrader.daily import splitoff_watch as w

SC_TO = ("COMPANY CONFORMED NAME: Medtronic plc\n<p>The Schedule TO relates to the offer by Medtronic to exchange up to "
         "an aggregate of 225,361,295 newly issued shares of common stock of MiniMed Group, Inc., a Delaware corporation "
         "(&ldquo;MiniMed&rdquo;), for outstanding ordinary shares of Medtronic (the &ldquo;Exchange Offer&rdquo;).</p>")
CASH = ("COMPANY CONFORMED NAME: UTAH MEDICAL PRODUCTS INC\nOffer to purchase up to 300,000 shares at a price of $75.00 "
        "per share, net to the seller in cash. Odd lots will be accepted before proration.")
OPTIONS = ("COMPANY CONFORMED NAME: Acme Inc\nOffer to exchange eligible options to purchase shares of common stock of "
           "Acme, Inc. for restricted stock units (the Exchange Offer).")
PRESS = ("Medtronic shareholders will receive approximately $107.53 of MiniMed common stock for every $100 of Medtronic "
         "ordinary shares tendered, representing a 7% discount, subject to an upper limit of 4.5939 shares of MiniMed "
         "common stock per Medtronic ordinary share. The exchange offer is scheduled to expire at 12:00 midnight, New York "
         "City time, at the end of the day on October 9, 2026. Shareholders who own odd-lots and validly tender all of "
         "their shares will not be subject to proration.")


def test_detects_split_off_not_cash_or_option_exchanges():
    assert w.detect(SC_TO) == ("Medtronic plc", "MiniMed Group, Inc.")
    assert w.detect(CASH) is None
    assert w.detect(OPTIONS) is None


def test_press_release_terms():
    t = w.parse_terms(PRESS)
    assert t == {"per100": 107.53, "cap": 4.5939, "expires": "2026-10-09", "odd_lot": "Y"}


def test_upper_limit_caps_the_gain():
    r = dict(per100=107.53, cap=4.5939)
    assert w.implied_gain(r, 100.0, 25.0) == pytest.approx(0.0753)          # uncapped 4.30 < 4.59: full 7.53%
    assert w.implied_gain(r, 86.44, 19.60) == pytest.approx(4.5939 * 19.60 / 86.44 - 1)   # capped (2026-10-01 closes)
    assert w.implied_gain(r, 86.44, 19.60) < 0.05


def test_entry_window_and_open_offers(tmp_path):
    assert [w.in_window(n) for n in (6, 5, 3, 2)] == [False, True, True, False]
    w.add(tmp_path, "mdt", "mmed", "2026-10-09", 107.53, 4.5939)
    w.add(tmp_path, "OLD", "X", "2025-01-01", 107.0, 1.0)
    rows = [json.loads(x) for x in (tmp_path / w.LOG_NAME).read_text().splitlines()]
    live = w.open_offers(rows, dt.date(2026, 10, 2))
    assert [r["parent"] for r in live] == ["MDT"] and live[0]["recv"] == "MMED"
