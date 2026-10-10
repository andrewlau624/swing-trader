import json

from swingtrader.daily import exdate_open_shadow as W

SPY = {"2026-10-06": (500.0, 501.0, 1e6), "2026-10-07": (502.0, 503.0, 1e6)}


def test_split_scores_close_to_open_with_ratio():
    X = {"AAA": {"2026-10-06": (98.0, 100.0, 1000), "2026-10-07": (51.0, 50.0, 900)}, "SPY": SPY}
    r = W.score(dict(kind="split", sym="AAA", ex="2026-10-07", ratio=2.0), X, SPY)
    assert r["status"] == "scored" and r["d0"] == "2026-10-06"
    assert abs(r["pnl"] - 0.02) < 1e-12
    assert abs(r["x"] - (0.02 - (502.0 / 501.0 - 1))) < 1e-12
    assert r["eligible"] and abs(r["close_dollars"] - 100000.0) < 1e-9


def test_spin_adds_child_open_and_waits_for_prints():
    X = {"PAR": {"2026-10-06": (40.0, 40.0, 10), "2026-10-07": (36.0, 35.0, 10)},
         "KID": {"2026-10-07": (9.0, 8.0, 5)}, "SPY": SPY}
    ev = dict(kind="spin", sym="PAR", child="KID", ex="2026-10-07", ratio=0.5)
    r = W.score(ev, X, SPY)
    assert abs(r["pnl"] - ((36.0 + 0.5 * 9.0) / 40.0 - 1)) < 1e-12
    assert W.score(dict(ev, ex="2026-10-08"), X, SPY) is None


def test_mismatch_and_summary_counts_forward_stock_only():
    X = {"BAD": {"2026-10-06": (10.0, 10.0, 1), "2026-10-07": (10.0, 10.0, 1)}, "SPY": SPY}
    assert W.score(dict(kind="split", sym="BAD", ex="2026-10-07", ratio=10.0), X, SPY)["status"] == "mismatch"
    rows = [dict(kind="split", sym="A", ex="2026-10-07", status="scored", eligible=True, fund=False, x=0.01),
            dict(kind="split", sym="B", ex="2026-10-07", status="scored", eligible=True, fund=True, x=0.5),
            dict(kind="split", sym="C", ex="2026-09-01", status="scored", eligible=True, fund=False, x=-0.01),
            dict(kind="spin", sym="D", ex="2026-10-20", status="upcoming")]
    s = W.summary(rows)
    assert s["forward"]["n"] == 1 and abs(s["forward"]["mean_bp"] - 100.0) < 1e-9
    assert s["backfill"]["n"] == 1 and s["upcoming"] == [("2026-10-20", "spin", "D")]
    assert "next: spin D 2026-10-20" in W.line(rows)
    json.dumps(rows)


def test_split_cross_filter_bucket_is_reported_not_gated():
    rows = [dict(kind="split", sym="A", ex="2026-10-07", status="scored", eligible=True, fund=False, x=0.01, ratio=2.0, close_dollars=5e6),
            dict(kind="split", sym="B", ex="2026-10-07", status="scored", eligible=True, fund=False, x=-0.02, ratio=4.0, close_dollars=5e6),
            dict(kind="split", sym="C", ex="2026-10-07", status="scored", eligible=True, fund=False, x=-0.03, ratio=1.5, close_dollars=2e5),
            dict(kind="spin", sym="D", ex="2026-10-07", status="scored", eligible=True, fund=False, x=0.05, ratio=0.1, close_dollars=9e6)]
    s = W.summary(rows)
    assert s["forward"]["n"] == 4, "the registered arm still counts every eligible stock event"
    assert s["forward_filter"]["n"] == 1 and abs(s["forward_filter"]["mean_bp"] - 100.0) < 1e-9
    assert "forward liquid<=2:1 splits n 1 mean +100 median +100 (reported)" in W.line(rows)
