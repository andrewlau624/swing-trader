import json

import pandas as pd

from swingtrader.daily import pick_cost_watch as W


def _fill(sym, side, px, at, leg="night"):
    return {"sym": sym, "leg": leg, "side": side, "qty": 2.0, "fill_px": px, "filled_at": at}


def test_trips_pair_buy_with_next_sell():
    f = [_fill("AAA", "buy", 8.0, "2026-10-01T20:00:01+0000"), _fill("BBB", "buy", 60.0, "2026-10-01T20:00:02+0000"),
         _fill("AAA", "sell", 8.2, "2026-10-02T13:30:01+0000"), _fill("QQQ", "buy", 500.0, "2026-10-02T14:00:00+0000", leg="noise")]
    t = W.trips(f, "taxable")
    assert [(x["sym"], x["buy_at"], x["sell_at"]) for x in t] == [("AAA", "2026-10-01", "2026-10-02")]


def test_score_and_buckets():
    r = W.score({"buy_px": 8.08, "sell_px": 8.18, "sym": "AAA"}, buy_close=8.0, sell_open=8.2)
    assert r["bucket"] == "$5-10"
    assert abs(r["buy_cost_bp"] - 100.0) < 1e-9 and abs(r["sell_cost_bp"] - (1 - 8.18 / 8.2) * 1e4) < 1e-9
    assert abs(r["bounce_bp"] - 250.0) < 1e-9
    assert W.bucket(75.0) == "$50+" and W.bucket(3.0) == "<$5"


def test_run_scores_and_is_idempotent(tmp_path):
    logs, state = tmp_path / "logs", tmp_path / "state"
    logs.mkdir(); state.mkdir()
    (logs / "daily-fills-live.jsonl").write_text("".join(json.dumps(x) + "\n" for x in [
        _fill("AAA", "buy", 8.0, "2026-10-01T20:00:01+0000"), _fill("AAA", "sell", 8.3, "2026-10-02T13:30:01+0000")]))
    bars = {"AAA": pd.DataFrame({"open": [7.9, 8.3], "close": [8.0, 8.4]}, index=pd.to_datetime(["2026-10-01", "2026-10-02"]))}
    s = W.run(state, logs, log=lambda *a: None, bars=bars)
    assert s["$5-10"]["n"] == 1 and abs(s["$5-10"]["cost_side_med"]) < 1e-9
    W.run(state, logs, log=lambda *a: None, bars=bars)
    assert len((state / W.LOG_NAME).read_text().splitlines()) == 1
