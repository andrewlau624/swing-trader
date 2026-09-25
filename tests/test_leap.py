"""Leap book (RESULTS.md addendum 24): shadow only, off by default."""
import datetime as dt
import json

import numpy as np

from swingtrader.config import Config
from swingtrader.leap import shadow, signals as sg


def _day(n=390, base=30.0):
    h = np.full(n, base + 0.1); l = np.full(n, base - 0.1); o = np.full(n, base)
    return o, h, l


def test_leap_is_off_and_shadow_by_default():
    c = Config.load().leap
    assert c.enabled is False and c.mode == "shadow"
    assert (c.symbol, c.inverse_symbol, c.orb_minutes, c.ibs_max) == ("SOXL", "SOXS", 15, 0.2)


def test_shadow_module_has_no_order_path():
    src = open(shadow.__file__).read()
    for word in ("submit", "place_order", "Broker", "Adapter", "requests.post"):
        assert word not in src


def test_orb_first_break_up_and_down():
    o, h, l = _day()
    h[40] = 31.0                                  # breaks the 15-min high first
    l[60] = 29.0
    assert sg.orb_break(h, l, 15) == (1, 40, 30.1, 29.9)
    o, h, l = _day()
    l[20] = 29.5
    h[50] = 31.0
    assert sg.orb_break(h, l, 15) == (-1, 20, 29.9, 30.1)


def test_orb_same_minute_both_ways_counts_as_down_and_late_breaks_are_ignored():
    o, h, l = _day()
    h[30] = 31.0; l[30] = 29.0
    assert sg.orb_break(h, l, 15)[0] == -1       # the research rule: ties go to the inverse side
    o, h, l = _day()
    h[388] = 31.0                                 # after 15:57: no trade
    assert sg.orb_break(h, l, 15) is None
    assert sg.orb_break(h[:15], l[:15], 15) is None


def test_orb_fill_and_stop():
    assert sg.orb_fill(1, 30.1, 30.05) == 30.1 and sg.orb_fill(1, 30.1, 30.3) == 30.3
    assert sg.orb_fill(-1, 29.9, 29.7) == 29.7
    assert sg.orb_stopped(1, 29.9, 30.2, 29.9) and not sg.orb_stopped(1, 29.9, 30.2, 29.95)
    assert sg.orb_stopped(-1, 30.1, 30.1, 29.8)


def test_ibs_entry():
    assert sg.ibs_entry(10.0, 9.0, 9.1, 0.2)
    assert not sg.ibs_entry(10.0, 9.0, 9.5, 0.2)
    assert not sg.ibs_entry(10.0, 10.0, 10.0, 0.2)


def test_shadow_decide_and_log(tmp_path):
    o, h, l = _day()
    h[40] = 31.0
    d = shadow.decide(Config.load(), dict(open=o, high=h, low=l, close=o),
                      dict(high=10.0, low=9.0, close=9.05), dt.date(2026, 9, 25))
    assert [x["rule"] for x in d] == ["orb", "ibs"]
    assert d[0]["buy"] == "SOXL" and d[0]["entry"] == 30.1 and d[0]["stop"] == 29.9
    p = tmp_path / "leap.jsonl"
    shadow.log(d, p)
    assert [json.loads(x)["rule"] for x in p.read_text().splitlines()] == ["orb", "ibs"]
    l2 = l.copy(); l2[20] = 29.0
    d = shadow.decide(Config.load(), dict(open=o, high=_day()[1], low=l2, close=o), None, dt.date(2026, 9, 25))
    assert d[0]["buy"] == "SOXS" and d[0]["side"] == -1


def test_futures_contracts_never_force_leverage():
    # MNQ at NQ 30,000 = $60,000 notional per contract
    assert sg.futures_contracts(1_000, 30_000, "MNQ", 1.0) == 0      # would be 60x
    assert sg.futures_contracts(25_000, 30_000, "MNQ", 1.0) == 0     # 2.4x > 1x target
    assert sg.futures_contracts(50_000, 30_000, "MNQ", 1.5) == 1
    assert sg.futures_contracts(100_000, 30_000, "MNQ", 5.0) == 3    # capped at 2x
    assert sg.futures_contracts(50_000, 7_700, "MES", 2.0) == 2      # $38.5k each
    assert sg.futures_contracts(50_000, float("nan"), "MES", 1.0) == 0
