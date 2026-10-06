"""Forced-flow discovery scanner: daily-index parser, cap/floor flag and submissions mapping. No network."""
from swingtrader.daily import forced_flow_discovery as w

IDX = (
    "Description:           Daily Index of EDGAR Dissemination Feed by Form Type\n"
    "Form Type   Company Name                                                  CIK\n"
    "      Date Filed  File Name\n"
    "------------------------------------------------------------------------------\n"
    "1-SA             Alternative Ballistics Corp                                   1834868     20261002    edgar/data/1834868/0001493152-26-045604.txt\n"
    "25-NSE           Getty Images Holdings, Inc.                                   1898496     20261002    edgar/data/1898496/0000876661-26-000814.txt\n"
    "425              Armada Acquisition Corp. II                                   2044009     20261002    edgar/data/2044009/0001193125-26-411024.txt\n"
    "8-K              1606 CORP.                                                    1877461     20261002    edgar/data/1877461/0001477932-26-006027.txt\n"
    "8-K/A            Foo Corp                                                      1234        20261002    edgar/data/1234/0001234-26-000001.txt\n"
    "8-K12B           Bar Corp                                                      5678        20261002    edgar/data/5678/0005678-26-000002.txt\n"
    "S-4              ENDRA Life Sciences Inc.                                      1681682     20261002    edgar/data/1681682/0001193125-26-410883.txt\n"
    "SC 14D-9         Target Corp                                                    111         20261002    edgar/data/111/0000111-26-000003.txt\n"
    "SC 13E3/A        Parent Corp                                                    222         20261002    edgar/data/222/0000222-26-000004.txt\n"
)

FIXED_ODD = ("Offer to purchase up to 588,235 shares of its common stock, at a price of $34.00 per Share, net "
             "to the seller in cash. If more than 588,235 shares are tendered, the Company will purchase all "
             "shares tendered by holders of odd lots first, and then on a pro rata basis.")
PER_HOLDER = ("Each holder may tender up to 5,000 shares of common stock at a price of $20.00 per share, net to "
              "the seller in cash, subject to proration.")
PLAIN_8K = ("Item 2.01 Completion of Acquisition or Disposition of Assets. On October 1, 2026 the registrant "
            "completed its acquisition of Acme LLC for cash.")


def test_parse_idx_keeps_wanted_forms_and_amendments_only():
    rows = w.parse_idx(IDX)
    got = [(r["form"], r["path"]) for r in rows]
    assert [f for f, _ in got] == ["25-NSE", "425", "8-K", "8-K/A", "S-4", "SC 14D-9", "SC 13E3/A"]
    assert all("8-K12B" not in p and "1-SA" not in p for _, p in got)
    assert rows[2]["cik"] == "1877461" and rows[0]["company"] == "Getty Images Holdings, Inc."


def test_accession_of():
    assert w.accession_of("edgar/data/1877461/0001477932-26-006027.txt") == "0001477932-26-006027"
    assert w.accession_of("edgar/data/1/not-an-accession.txt") is None


def test_fixed_odd_lot_floor_is_a_candidate():
    f = w.flag(FIXED_ODD)
    assert f["floor"] == 34.0 and f["odd_lot"] == "Y" and "odd_lot" in f["capped"] and f["candidate"]


def test_per_holder_cap_with_fixed_floor_is_a_candidate():
    f = w.flag(PER_HOLDER)
    assert f["cap"] == 5000.0 and f["floor"] == 20.0 and f["candidate"]


def test_plain_8k_has_no_cap_or_floor():
    f = w.flag(PLAIN_8K)
    assert f["floor"] is None and f["cap"] is None and not f["candidate"] and f["capped"] == []


def test_submission_index_and_primary_url():
    sub = {"filings": {"recent": {"accessionNumber": ["0001-26-000001", "0002-26-000002"],
                                  "form": ["8-K", "25-NSE"], "items": ["2.01,9.01", ""],
                                  "primaryDocument": ["a.htm", "b.htm"],
                                  "filingDate": ["2026-10-02", "2026-10-02"]}}}
    idx = w.submission_index(sub)
    assert idx["0001-26-000001"]["items"] == "2.01,9.01" and idx["0002-26-000002"]["primary"] == "b.htm"
    assert (w.primary_url("1877461", "0001477932-26-006027", "doc.htm")
            == "https://www.sec.gov/Archives/edgar/data/1877461/000147793226006027/doc.htm")
