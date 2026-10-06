import json

from swingtrader.daily import pref_ex_shadow as W


def _hist(px=25.0, size=200, n=25):
    # 25 prior sessions with a closing cross of px x size ($5,000) each, plus the ex-date session
    days = {f"2026-09-{d:02d}": (px, 100, px, size) for d in range(1, n + 1)}
    return days


def test_score_adds_dividend_and_uses_prior_close_cross():
    p = _hist()
    p["2026-09-30"] = (24.90, 400, 24.80, 300)
    r = W.score(dict(sym="AAA.PRA", ex="2026-09-30", div=0.40), {"AAA.PRA": p})
    assert r["status"] == "scored" and r["d0"] == "2026-09-25"
    assert abs(r["co"] - ((24.90 + 0.40) / 25.0 - 1)) < 1e-12
    assert abs(r["cc"] - ((24.80 + 0.40) / 25.0 - 1)) < 1e-12
    assert r["eligible"] and abs(r["med_cross_usd"] - 5000.0) < 1e-9 and abs(r["yld"] - 0.016) < 1e-12


def test_score_waits_for_both_ex_crosses_and_flags_mismatch():
    p = _hist()
    p["2026-09-30"] = (24.9, 100, None, None)
    assert W.score(dict(sym="A.PRA", ex="2026-09-30", div=0.4), {"A.PRA": p}) is None
    p["2026-09-30"] = (10.0, 100, 10.0, 100)
    assert W.score(dict(sym="A.PRA", ex="2026-09-30", div=0.4), {"A.PRA": p})["status"] == "mismatch"


def test_execution_caps_order_at_part_of_median_cross_whole_shares():
    rows = [dict(sym="A.PRA", ex="2026-09-30", status="scored", eligible=True, med_cross_usd=5000.0, close_px=25.0,
                 close_usd=5000.0, open_usd=10000.0, exit_close_usd=5000.0, co=0.004, cc=0.003)]
    W.execution(rows, acct=10_000, part=0.05)
    r = rows[0]
    assert r["order_usd"] == 250.0                     # 5% x $5,000 = $250 = 10 shares
    assert abs(r["part_close"] - 0.05) < 1e-12 and abs(r["part_open"] - 0.025) < 1e-12
    imp = (0.05 / 0.01) ** 0.5 / 10
    assert abs(r["net_co"] - (0.004 - W.COST - imp * (W.HALF_SPR["close"] + W.HALF_SPR["open"]))) < 1e-12
    assert r["broker"] == "unverified"


def test_summary_counts_forward_nights_and_gate_line():
    rows = []
    for i in range(W.NEED):
        d = f"2026-12-{(i % 28) + 1:02d}" if i < 28 else f"2027-01-{(i % 28) + 1:02d}" if i < 56 else f"2027-02-0{i - 55}"
        rows.append(dict(sym=f"S{i}.PRA", ex=d, status="scored", eligible=True, co=0.006 + 0.0001 * (i % 3),
                         cc=0.004, net_co=0.003 + 0.0001 * (i % 3), net_cc=0.002, order_usd=200.0, part_close=0.04))
    rows.append(dict(sym="OLD.PRA", ex="2026-09-15", status="scored", eligible=True, co=0.01, cc=0.01, net_co=0.008,
                     net_cc=0.008, order_usd=100.0, part_close=0.02))
    rows.append(dict(sym="UP.PRA", ex="2027-03-01", status="upcoming"))
    s = W.summary(rows)
    assert s["forward"]["co"]["nights"] == W.NEED and s["backfill"]["co"]["n"] == 1
    assert s["upcoming"] == [("2027-03-01", "UP.PRA")]
    ln = W.line(rows)
    assert "PASS" in ln and "next: UP.PRA 2027-03-01" in ln
    json.dumps(rows)
