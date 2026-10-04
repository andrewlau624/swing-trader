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
