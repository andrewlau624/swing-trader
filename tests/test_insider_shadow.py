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
    assert r == dict(sym="ABC", usd=25500.0, insider=True)
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
    assert w["odd-lot te"]["n"] == 1 and w["odd-lot te"]["usd"] == 99 * 2.0
    g = {x["gate"]: x for x in digest.gates({}, tmp_path, tmp_path)}
    assert g["Insider-day (ID3) verdict"]["n"] == 2
