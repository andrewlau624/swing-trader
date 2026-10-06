import json
from types import SimpleNamespace

import pandas as pd

from swingtrader.daily import size_shadow as S
from swingtrader.leap import shadow as L

CFG = SimpleNamespace(night_weight=0.5, night_max_name_pct=0.15, night_weekend_scale=0.5,
                      night_impact_edge_bps=22.0, noise_target_vol=0.02, noise_max_lev=3.5)


def _bars(rows):
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close"]).set_index("date")


def test_night_at_whole_shares_and_impact():
    picks = [{"sym": "A", "adv20": 1e7, "vol20": 1.0}, {"sym": "B", "adv20": 1e7, "vol20": 1.0}]
    bars = {"A": (10.0, 10.5), "B": (20.0, 19.0)}
    r = S.night_at(picks, bars, 2000.0, weight=0.5, max_name_pct=0.15, gap=1.0)
    # per name = 2000 x 0.5 x min(1/2, .15) = 150: A 15 sh ($150), B 7 sh ($140)
    assert r["deployed"] == 290.0 and r["n"] == 2
    assert abs(r["gross"] - (150 * 0.05 + 140 * -0.05)) < 1e-9
    big = S.night_at(picks, bars, 1e7, weight=0.5, max_name_pct=0.15, gap=1.0)
    assert big["net"] < big["gross"] and big["capped"] == 2        # $750k orders in $10M-ADV names


def test_noise_day_and_mnq_rounding():
    f = [{"side": "buy", "qty": 2, "fill_px": 100.0, "filled_at": "1"},
         {"side": "sell", "qty": 2, "fill_px": 101.0, "filled_at": "2"}]
    r, px = S.noise_day(f)
    assert abs(r - 0.01) < 1e-12 and px == 100.0
    assert S.noise_day(f[:1]) is None                                 # not flat: skip
    small = S.noise_at(0.01, 750.0, 1.0, 30_000, 3.5)                 # 1 MNQ = 2 x 750 x 41 ~ $61.5k
    assert small["contracts"] == 0                                    # lev 1.0 x 30k < one contract
    big = S.noise_at(0.01, 750.0, 1.0, 250_000, 3.5)
    assert big["contracts"] == 4 and abs(big["ideal"] - 2500.0) < 1e-9


def test_run_idempotent(tmp_path):
    state, logs = tmp_path / "state", tmp_path / "logs"
    state.mkdir(); logs.mkdir()
    (state / "book-daily-live.json").write_text(json.dumps({"equity_log": [{"date": "2026-10-05", "equity": 2300.0}]}))
    (logs / "daily-decisions-live.jsonl").write_text(json.dumps(
        {"date": "2026-10-05", "sym": "A", "adv20": 5e7, "vol20": 0.9, "price": 10.0}) + "\n")
    d = [pd.Timestamp("2026-10-05"), pd.Timestamp("2026-10-06")]
    bars = {"A": _bars([(d[0], 11, 11, 9.9, 10.0), (d[1], 10.3, 10.5, 10.1, 10.2)])}
    S.run(state, logs, bars=bars, cfg=CFG, log=lambda *a: None)
    S.run(state, logs, bars=bars, cfg=CFG, log=lambda *a: None)
    rows = [json.loads(x) for x in (state / S.LOG_NAME).read_text().splitlines()]
    assert len(rows) == 1 and set(rows[0]["night"]) == {"live", "30000", "100000", "250000"}
    assert rows[0]["night"]["100000"]["deployed"] == 7500.0          # 100k x .5 x .15 at $10


def test_leap_forward(tmp_path):
    cfg = SimpleNamespace(leap=SimpleNamespace(symbol="SOXL", ibs_max=0.2))
    d = pd.bdate_range("2026-10-01", periods=4)
    bars = {"SOXL": _bars([(d[0], 30, 31, 29, 29.1),       # IBS 0.05 -> buy d1 open, sell d2 open
                           (d[1], 29.5, 30, 29, 29.8), (d[2], 30.1, 31, 30, 30.5), (d[3], 30.6, 31, 30, 30.9)])}
    p = tmp_path / "leap.jsonl"
    L.forward(cfg, p, bars=bars, log_fn=lambda *a: None)
    L.forward(cfg, p, bars=bars, log_fn=lambda *a: None)
    rows = [json.loads(x) for x in p.read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["date"] == "2026-10-01" and abs(rows[0]["r_bp"] - (30.1 / 29.5 - 1) * 1e4) < 0.1
