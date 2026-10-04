"""Study TME-L forward shadow: window selection, sleeve arithmetic, margin headroom, digest reader."""
import json

import numpy as np
import pandas as pd

from research.sim import tme_shadow as t
from swingtrader.daily import testing


def test_window_is_close_t_minus_3_to_last_session():
    assert t.windows(pd.bdate_range("2026-10-01", "2026-10-31"))[0] == (pd.Timestamp("2026-10-27"), pd.Timestamp("2026-10-30"))


def test_sleeve_costs_and_financing():
    p = t.sleeve({"TLT": 0.01, "TMF": 0.03, "UBT": 0.02}, 4)
    assert abs(p["L1"] - (0.01 - 4e-4)) < 1e-12
    assert abs(p["L2"] - (0.02 - 8e-4 - 0.125 * 4 / 360)) < 1e-12   # 2x notional pays 2x cost
    assert abs(p["L3"] - (0.03 - 1e-3)) < 1e-12


def test_l2_headroom():
    assert abs(t.l2_headroom(np.array([1.0, 0.9])) - 0.175) < 1e-12


def test_digest_reader(tmp_path):
    (tmp_path / "tme-shadow.jsonl").write_text(json.dumps(
        {"T": "2026-10-30", "status": "scored", "pnl": {"L1": 0.003, "L2": 0.005, "L3": 0.008}}) + "\n")
    st = {r["name"]: r for r in testing.status(tmp_path, tmp_path)}
    r = st["TME-L: leveraged month-end Treasury sleeve"]
    assert r["n"] == 1 and "L3 +80.0bp" in r["line"]


def test_digest_reports_missing_prints_and_scored(tmp_path):
    (tmp_path / "tme-shadow.jsonl").write_text(
        json.dumps({"T": "2026-10-30", "status": "missing_prints", "missing": ["TMF"]}) + "\n")
    st = {r["name"]: r for r in testing.status(tmp_path, tmp_path)}
    assert "FAILED: 1 window(s) awaiting prints (2026-10-30)" in st["TME-L: leveraged month-end Treasury sleeve"]["line"]
    with (tmp_path / "tme-shadow.jsonl").open("a") as f:
        f.write(json.dumps({"T": "2026-10-30", "status": "scored", "pnl": {"L1": 0.003, "L2": 0.005, "L3": 0.008}}) + "\n")
    st = {r["name"]: r for r in testing.status(tmp_path, tmp_path)}
    assert "FAILED" not in st["TME-L: leveraged month-end Treasury sleeve"]["line"]


def test_forward_is_idempotent_and_retries_missing(tmp_path, monkeypatch):
    """A scored window is never logged twice; a missing-prints window is logged once and retried later."""
    cal = pd.bdate_range("2026-10-01", "2026-11-03")
    bars = {s: pd.DataFrame({"open": 100.0, "close": 100.0}, index=cal) for s in t.SYMS}
    monkeypatch.setattr(t, "LOG", tmp_path / "tme-shadow.jsonl")
    import swingtrader.daily.marketdata as md
    monkeypatch.setattr(md, "sip_daily", lambda syms, start, end=None: bars)
    monkeypatch.setattr(md, "cash_dividends", lambda syms, a, b: [])
    prints = {}
    monkeypatch.setattr(t, "_closing_prints", lambda syms, a, b: prints)
    t.forward(); t.forward()                                         # prints missing twice -> one missing row
    rows = [json.loads(x) for x in (tmp_path / "tme-shadow.jsonl").read_text().splitlines()]
    assert [r["status"] for r in rows] == ["missing_prints"]
    prints.update({(s, d): 100.0 for s in t.SYMS for d in (pd.Timestamp("2026-10-27"), pd.Timestamp("2026-10-30"))})
    t.forward(); t.forward()                                         # now scored once, never again
    rows = [json.loads(x) for x in (tmp_path / "tme-shadow.jsonl").read_text().splitlines()]
    assert [r["status"] for r in rows] == ["missing_prints", "scored"]
