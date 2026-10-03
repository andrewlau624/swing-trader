import json

import pandas as pd

from swingtrader.daily import stack_shadow as S


def _bars(closes):
    idx = pd.to_datetime(list(closes))
    return pd.DataFrame({"close": list(closes.values())}, index=idx)


def test_day_returns_skips_deposits():
    log = [{"date": "2026-10-01", "equity": 1000.5}, {"date": "2026-10-02", "equity": 1010.505},
           {"date": "2026-10-05", "equity": 2010.5}, {"date": "2026-10-06", "equity": 2030.605}]
    r = S.day_returns(log)
    assert abs(r["2026-10-02"] - 0.01) < 1e-9
    assert r["2026-10-05"] is None                    # +99%: a deposit, not a return
    assert abs(r["2026-10-06"] - 0.01) < 1e-9


def test_overlay_math():
    o = S.overlay(0.01, 0.02, 0.005, 0.015)
    assert abs(o["stack_taxable"] - (0.01 + 0.005 - S.DEBIT * S.MARGIN / 252)) < 1e-12
    assert abs(o["stack_roth"] - (2 / 3 * 0.02 + 1 / 3 * 0.015)) < 1e-12
    assert S.overlay(None, None, 0.0, 0.0) == {"stack_taxable": None, "stack_roth": None}


def test_run_logs_once_and_never_orders(tmp_path):
    for f, eq in (("book-daily-live.json", (2000.5, 2020.505, 2010.4)), ("book-daily-roth.json", (8500.5, 8585.505, 8500.5))):
        log = [{"date": d, "equity": e} for d, e in zip(("2026-10-01", "2026-10-02", "2026-10-05"), eq)]
        (tmp_path / f).write_text(json.dumps({"equity_log": log}))
    bars = {"SPY": _bars({"2026-10-01": 100.0, "2026-10-02": 101.0, "2026-10-05": 100.0}),
            "UPRO": _bars({"2026-10-01": 50.0, "2026-10-02": 51.5, "2026-10-05": 50.0})}
    s1 = S.run(tmp_path, bars=bars, log=lambda *a: None)
    rows = [json.loads(x) for x in (tmp_path / S.LOG_NAME).read_text().splitlines()]
    assert [r["date"] for r in rows] == ["2026-10-02", "2026-10-05"]
    assert abs(rows[0]["r_spy"] - 0.01) < 1e-12 and abs(rows[0]["stack_roth"] - (2 / 3 * 0.01 + 1 / 3 * 0.03)) < 1e-12
    S.run(tmp_path, bars=bars, log=lambda *a: None)                  # idempotent
    assert len((tmp_path / S.LOG_NAME).read_text().splitlines()) == 2
    assert s1["n"] == 2


def test_day_returns_skips_cap_placeholders():
    log = [{"date": "2026-09-23", "equity": 931.36}, {"date": "2026-09-24", "equity": 1000.0},
           {"date": "2026-09-25", "equity": 1000.0}, {"date": "2026-09-29", "equity": 2258.74},
           {"date": "2026-09-30", "equity": 2259.77}]
    r = S.day_returns(log)
    assert r["2026-09-24"] is None and r["2026-09-25"] is None and r["2026-09-29"] is None
    assert abs(r["2026-09-30"] - (2259.77 / 2258.74 - 1)) < 1e-12
