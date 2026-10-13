import json

from swingtrader.daily import cb_funding_log as W

PRODUCTS = [
    {"product_id": "BIP-20DEC30-CDE", "price": "81455", "volume_24h": "100",
     "future_product_details": {"funding_rate": "0.000012", "funding_time": "2026-10-13T00:00:00Z",
                                "funding_interval": "3600s", "open_interest": "166925"}},
    {"product_id": "ETP-20DEC30-CDE", "price": "2429",
     "future_product_details": {"perpetual_details": {"funding_rate": "-0.000009"}}},
    {"product_id": "BTC-PERP-INTX", "price": "1", "future_product_details": {"funding_rate": "0.001"}},   # non-US: skipped
    {"product_id": "BIT-31OCT26-CDE", "price": "1", "future_product_details": {}},                          # dated, no funding
]


def test_rows_keep_us_perps_only(tmp_path):
    n = W.run(tmp_path, now="2026-10-13T01:00:00Z", products=PRODUCTS)
    log = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert n == 2 and [r["sym"] for r in log] == ["BIP-20DEC30-CDE", "ETP-20DEC30-CDE"]
    assert log[0]["rate"] == 0.000012 and log[0]["oi"] == 166925.0 and log[1]["rate"] == -0.000009


def test_appends_and_summarizes(tmp_path):
    W.run(tmp_path, now="2026-10-13T01:00:00Z", products=PRODUCTS)
    W.run(tmp_path, now="2026-10-14T01:00:00Z", products=PRODUCTS)
    log = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    s = W.summary(log)
    assert s["days"] == 2 and s["rows"] == 4
    assert abs(s["ann"]["BIP"] - 0.000012 * 8760) < 1e-12
    assert "2/90 days" in W.line(log)
