"""Round 31 ID3 insider-purchase shadow: parsing, filters, filing-day mapping, gate. No network."""
import datetime as dt

import numpy as np
import pandas as pd

from swingtrader.config import Config
from swingtrader.daily import insider_shadow as s


def _form4(code="P", ad="A", shares="1000", px="25.50", director="1", officer="0", doc="4", sym="ABC"):
    return f"""<SEC-DOCUMENT><XML><ownershipDocument><documentType>{doc}</documentType>
<issuer><issuerCik>1</issuerCik><issuerTradingSymbol>{sym}</issuerTradingSymbol></issuer>
<reportingOwner><reportingOwnerRelationship><isDirector>{director}</isDirector><isOfficer>{officer}</isOfficer>
</reportingOwnerRelationship></reportingOwner><nonDerivativeTable><nonDerivativeTransaction>
<transactionCoding><transactionCode>{code}</transactionCode></transactionCoding>
<transactionAmounts><transactionShares><value>{shares}</value></transactionShares>
<transactionPricePerShare><value>{px}</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>{ad}</value></transactionAcquiredDisposedCode></transactionAmounts>
</nonDerivativeTransaction></nonDerivativeTable></ownershipDocument></XML></SEC-DOCUMENT>"""


def test_parse_purchase_and_rejects():
    r = s.parse_form4(_form4())
    assert r == dict(sym="ABC", usd=25500.0, insider=True, issuer_cik=1)
    assert s.parse_form4(_form4(code="S")) is None              # a sale
    assert s.parse_form4(_form4(ad="D")) is None
    assert s.parse_form4(_form4(doc="5")) is None
    assert s.parse_form4(_form4(director="0", officer="0"))["insider"] is False
    assert s.parse_form4(_form4(sym="brk-b"))["sym"] == "BRK.B"
    assert s.parse_form4("no xml here") is None


def test_form4_paths_dedupes_owner_and_issuer_lines():
    idx = ("Form Type   Company Name   CIK   Date Filed   File Name\n"
           "4           ABC CORP       1     20261001     edgar/data/1/0001-26-000001.txt\n"
           "4           SMITH JOHN     2     20261001     edgar/data/1/0001-26-000001.txt\n"
           "4/A         ABC CORP       1     20261001     edgar/data/1/0001-26-000002.txt\n"
           "424B2       XYZ            3     20261001     edgar/data/3/0003-26-000009.txt\n")
    assert s.form4_paths(idx) == ["edgar/data/1/0001-26-000001.txt", "edgar/data/1/0001-26-000002.txt"]


def _bars(close, vol, n=25, end="2026-10-01"):
    idx = pd.bdate_range(end=end, periods=n)
    return pd.DataFrame({"close": close, "volume": vol, "open": close}, index=idx)


def test_plan_filters_adv_price_insider_and_size():
    bars = {"BIG": _bars(50.0, 1e6), "THIN": _bars(50.0, 1e5), "CHEAP": _bars(4.0, 1e8)}
    buys = [dict(sym="BIG", usd=6000, insider=True), dict(sym="BIG", usd=6000, insider=True),   # sums to $12k
            dict(sym="THIN", usd=5e4, insider=True), dict(sym="CHEAP", usd=5e4, insider=True),
            dict(sym="OWNER10", usd=5e5, insider=False)]
    rows = s.plan_rows(buys, bars, "2026-10-02")
    assert [r["sym"] for r in rows] == ["BIG"] and rows[0]["usd"] == 12000 and rows[0]["adv"] == 50_000_000


def test_plan_ignores_bars_on_or_after_the_session():
    b = _bars(50.0, 1e6, end="2026-10-02")
    b.loc[b.index[-1], "close"] = 1.0                            # today's bar must not be read
    assert s.plan_rows([dict(sym="X", usd=2e4, insider=True)], {"X": b}, "2026-10-02")[0]["prev_close"] == 50.0


def test_filing_days_cover_holiday_filings():
    # Good Friday 2027-03-26: market closed, EDGAR open -> trades Monday 03-29 with Thursday's filings
    assert s.filing_days(dt.date(2027, 3, 25), dt.date(2027, 3, 29)) == [dt.date(2027, 3, 25), dt.date(2027, 3, 26)]
    assert s.filing_days(dt.date(2026, 10, 1), dt.date(2026, 10, 2)) == [dt.date(2026, 10, 1)]


def test_gate_rules():
    assert s.gate([])["n"] == 0
    rng = np.random.default_rng(0)
    mk = lambda mu: [dict(status="scored", date=f"d{i // 5}", ret_net=float(mu + rng.normal(0, 0.002))) for i in range(300)]
    assert s.gate(mk(0.0)[:100])["verdict"].startswith("shadowing")
    assert s.gate(mk(0.002))["verdict"].startswith("PASS")
    assert s.gate(mk(-0.001))["verdict"].startswith("KILL")


def test_config_key_defaults_to_shadow():
    assert Config.load().daily.insider_day == "shadow"


def test_digest_counts_round31_shadows(tmp_path):
    import json
    from swingtrader.daily import digest
    (tmp_path / "insider-day.jsonl").write_text(
        json.dumps(dict(date="2026-10-05", sym="A", status="scored", ret_net=0.002)) + "\n"
        + json.dumps(dict(date="2026-10-05", sym="B", status="scored", ret_net=0.0)) + "\n"
        + json.dumps(dict(date="2026-10-06", sym="C", status="planned")) + "\n")
    (tmp_path / "tender-watch.jsonl").write_text(json.dumps(dict(alert=True, floor=34.0, last_close=32.0)) + "\n"
                                                 + json.dumps(dict(alert=False, floor=10.0, last_close=9.0)) + "\n")
    acct = digest.Account("live", 2000.0, None, 0.0, [], [], [], [], [dict(date="2026-10-05", equity=2000.0)])
    w = {r["idea"][:10]: r for r in digest.round31_whatif(tmp_path, acct)}
    assert w["insider-da"]["n"] == 2 and abs(w["insider-da"]["usd"] - 0.45 * 2000 * 0.001) < 1e-9
    # $2,000 buys 62 shares at $32, not 99
    assert w["odd-lot te"]["n"] == 1 and w["odd-lot te"]["usd"] == 62 * 2.0
    assert "62 sh" in w["odd-lot te"]["idea"]
    g = {x["gate"]: x for x in digest.gates({}, tmp_path, tmp_path)}
    assert g["Insider-day (ID3) verdict"]["n"] == 2


# ------------------------------------------------------------ EV2 (Round 33): silence before the buy
def test_silence_days_finds_the_latest_earlier_purchase():
    fd = dt.date(2026, 10, 1)
    fl = [(dt.date(2026, 10, 1), "same-day"), (dt.date(2026, 9, 1), "sale"), (dt.date(2025, 1, 1), "buy-old"),
          (dt.date(2026, 3, 1), "buy")]
    seen = []
    buy = lambda u: seen.append(u) or u.startswith("buy")
    assert s.silence_days(fl, fd, buy) == (fd - dt.date(2026, 3, 1)).days
    assert seen == ["sale", "buy"]                         # newest first, same-day filing ignored, stops at a buy
    assert s.silence_days([(dt.date(2023, 1, 1), "buy")], fd, buy) is None     # beyond the 1,095-day cap
    assert s.silence_days([], fd, buy) is None


def test_ev2_flags_and_sub_gates():
    assert s.ev2_flags(dict(usd=1e6)) == (False, False)                       # logged before EV2 existed
    assert s.ev2_flags(dict(silence_days=None, usd=1e4)) == (True, False)
    assert s.ev2_flags(dict(silence_days=800, usd=6e5)) == (True, True)
    assert s.ev2_flags(dict(silence_days=100, usd=6e5)) == (False, False)
    rows = [dict(status="scored", date=f"d{i // 3}", ret_net=0.003 + (i % 3) * 1e-4, silence_days=None, usd=6e5)
            for i in range(60)]
    rows += [dict(status="scored", date=f"d{i}", ret_net=-0.001, silence_days=10, usd=1e4) for i in range(10)]
    g = s.gate(rows)
    assert g["ev2"]["n"] == 60 and g["ev2"]["verdict"].startswith("PASS") and g["ev2"]["rest_bp"] < 0
    assert g["ev2_big"]["n"] == 60
    assert s.gate(rows[:30])["ev2"]["verdict"].startswith("shadowing")


def test_splitoff_whatif_is_sized_by_what_each_account_can_buy(tmp_path):
    """MDT -> MMED 2026-10-02: a flat 99 shares showed +$371 on a $2.3k brokerage."""
    import json
    import pytest
    from swingtrader.daily import digest
    (tmp_path / "splitoff-watch.jsonl").write_text(json.dumps(dict(
        entry="2026-10-02", parent="MDT", parent_px=86.89, gain=0.0431, alert=True)) + "\n")
    acct = lambda name, eq: digest.Account(name, eq, None, 0.0, [], [], [], [], [dict(date="2026-10-02", equity=eq)])
    live = digest.round31_whatif(tmp_path, acct("live", 2263.09))
    roth = digest.round31_whatif(tmp_path, acct("roth", 1000.0), manual_only=True)
    big = digest.round31_whatif(tmp_path, acct("live", 25000.0))
    assert live[0]["usd"] == pytest.approx(26 * 86.89 * 0.0431) and "26 sh" in live[0]["idea"]
    assert roth[0]["usd"] == pytest.approx(11 * 86.89 * 0.0431) and len(roth) == 1
    assert big[0]["usd"] == pytest.approx(99 * 86.89 * 0.0431), "odd-lot priority caps at 99"
    assert digest.odd_lot_shares(50.0, 86.89) == 0


# ------------------------------------------------------------ Track M1: ID1 / ID2 / EV1 forward (never ID3)
def test_m1_plan_tags_id2_rows_and_id3_gate_ignores_them():
    bars = {"BIG": _bars(50.0, 1e6), "THIN": _bars(50.0, 1e5), "DUST": _bars(50.0, 1e4)}   # $50M / $5M / $0.5M
    buys = [dict(sym=k, usd=5e4, insider=True) for k in bars]
    rows = s.plan_rows(buys, bars, "2026-10-02", min_adv=s.MIN_ADV_ID1)
    assert [(r["sym"], r.get("id2", False)) for r in rows] == [("BIG", False), ("THIN", True)]
    assert [r["sym"] for r in s.plan_rows(buys, bars, "2026-10-02")] == ["BIG"]          # default unchanged
    sc = [dict(r, status="scored", ret_net=0.001, m1=True) for r in rows]
    assert s.gate(sc)["n"] == 1                                                          # ID3 counts BIG only
    g = s.m1_gate(sc)
    assert g["id1"]["n"] == 2 and g["id2"]["n"] == 1 and g["ev1"]["n"] == 0
    assert abs(g["id2"]["live_bp"] - (10 + 2 * (s.COST_BPS - s.LIVE_COST_BPS))) < 1e-9
    assert g["id1"]["verdict"].startswith("M1 reading")


def test_m1_ev1_needs_another_filing_in_the_previous_five_days():
    rows = [dict(sym="A"), dict(sym="B"), dict(sym="C"), dict(sym="D", id2=True)]
    buys = [dict(sym="A", insider=True, fd="2026-10-09"), dict(sym="B", insider=True, fd="2026-10-09"),
            dict(sym="B", insider=True, fd="2026-10-09"), dict(sym="C", insider=True, fd="2026-10-09"),
            dict(sym="D", insider=True, fd="2026-10-09")]
    recent = {"A": ["2026-10-05"], "C": ["2026-10-03"], "D": ["2026-10-08"]}    # A 4 days back; C 6 days back
    s.ev1_flags(rows, buys, recent)
    assert [r.get("ev1") for r in rows] == [True, False, False, None]          # same-day only: no; ID2 never EV1
    kept = s.remember_filings(recent, buys, dt.date(2026, 10, 9), keep_days=5)
    assert kept["C"] == ["2026-10-09"] and kept["A"] == ["2026-10-05", "2026-10-09"]   # 10-03 pruned
