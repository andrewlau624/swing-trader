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


def test_etd_rows_are_gated_separately_from_preferreds():
    assert W._cls("AAA.PRA") == "pref" and W._cls("SOJD") == "etd" and "SOJD" in W.ETD
    rows = [dict(sym="BOND", ex="2026-12-01", status="scored", eligible=True, co=0.005, cc=0.004, net_co=0.004,
                 net_cc=0.003, order_usd=200.0, part_close=0.04),
            dict(sym="P.PRA", ex="2026-12-02", status="scored", eligible=True, co=0.004, cc=0.003, net_co=0.003,
                 net_cc=0.002, order_usd=200.0, part_close=0.04)]
    assert W.summary(rows)["forward"]["co"]["n"] == 1 and W.summary(rows, "etd")["forward"]["co"]["n"] == 1
    assert "ETDX: forward 1 nights/1 events" in W.lines(rows)


def test_chain_prices_t10_close_and_compares_with_the_bench_over_both_windows():
    p = _hist()
    p["2026-09-26"] = (24.9, 100, 24.8, 300)             # ex-date E
    r = W.score(dict(sym="A.PRA", ex="2026-09-26", div=0.40), {"A.PRA": p})
    days = sorted(d for d in p if d < "2026-09-26")
    b = {d: (50.0, 1, 50.0, 1) for d in days}
    b["2026-09-26"] = (50.5, 1, 50.5, 1)
    c = W.chain(r, p, b, {W.BENCH: [("2026-09-20", 0.10)]})
    assert c["t10"] == days[-10] and abs(c["ch"] - ((24.8 + 0.40) / 25.0 - 1)) < 1e-12
    assert abs(c["ch_bench"] - ((50.5 + 0.10) / 50.0 - 1)) < 1e-12        # bench dividend inside T-10 -> E
    assert abs(c["cc_bench"] - (50.5 / 50.0 - 1)) < 1e-12                 # but not inside E-1 -> E
    assert abs(c["ch_x"] - (c["ch"] - c["ch_bench"])) < 1e-12 and abs(c["cc_x"] - (r["cc"] - c["cc_bench"])) < 1e-12
    assert W.chain(r, {d: p[d] for d in days[-5:]} | {"2026-09-26": p["2026-09-26"]}, b, {}) == {}


def test_stable_needs_three_priors_within_2pct_and_current_within_10pct():
    h = [("2026-01-01", 0.40), ("2026-04-01", 0.40), ("2026-07-01", 0.404)]
    assert W.stable(h, "2026-10-01", 0.40) is True
    assert W.stable(h, "2026-10-01", 0.30) is False
    assert W.stable(h[:2], "2026-10-01", 0.40) is None                     # too little history: unknown, not stable
    assert W.stable(h + [("2026-10-01", 0.40)], "2026-10-01", 0.40) is True  # the event itself is not a prior


def test_costs_sign_convention_buy_above_mid_and_sell_below_mid_are_positive():
    r = dict(sym="A.PRA", d0="d0", ex="E", t10="t", t10_px=25.05, close_px=25.0, exit_close_px=24.90)
    Q = {("A.PRA", "t"): (24.90, 25.10), ("A.PRA", "d0"): (24.90, 25.10), ("A.PRA", "E"): (24.80, 25.10)}
    c = W.costs(r, Q)
    assert abs(c["cost_buy_t10"] - (25.05 / 25.0 - 1)) < 1e-12 and abs(c["cost_buy_d0"]) < 1e-12
    assert abs(c["cost_sell_E"] - (1 - 24.90 / 24.95)) < 1e-12 and abs(c["hs_d0"] - 0.10 / 25.0) < 1e-12


def test_chain_verdict_waits_for_need_forward_nights_then_reads_pass_or_kill():
    def rows(n, ch, cc):
        return [dict(sym=f"A{k}.PRA", ex=f"2026-11-{k % 28 + 1:02d}" if k < 28 else f"2027-{k // 28:02d}-{k % 28 + 1:02d}",
                     status="scored", eligible=True, stable=True, ch_x=ch + 0.0001 * (k % 3), cc_x=cc,
                     cost_buy_t10=0.0002, cost_buy_d0=0.0002, cost_sell_E=0.0003) for k in range(n)]
    assert W.chain_verdict(rows(W.NEED - 1, 0.004, 0.001)) == ""
    assert "PASS" in W.chain_verdict(rows(W.NEED, 0.004, 0.001))
    assert "KILL" in W.chain_verdict(rows(W.NEED, 0.004, 0.006))          # no better than T-1
    assert "KILL" in W.chain_verdict(rows(W.NEED, 0.0005, 0.0))           # <= +5bp net
    backfill = [dict(r, ex="2026-09-15") for r in rows(W.NEED, 0.004, 0.001)]
    assert W.chain_verdict(backfill) == ""                                # backfill never gates


def test_roth_stack_alloc_caps_at_part_of_cross_and_night_first_leaves_less():
    import datetime
    snap = W.roth_snapshot({"cash": 600.0, "start_equity": 1000.0, "equity_log": [{"equity": 1000.0}],
                            "positions": {"SGOV": {"qty": 4, "avg_px": 100.0, "leg": "tbill"}}}, datetime.date(2026, 10, 9))
    assert snap["tbill_usd"] == 400.0 and snap["night_budget"] == 500.0
    night = [dict(sym="AAA", med_cross_usd=2000.0, close_px=25.0), dict(sym="BBB", med_cross_usd=1_000_000.0, close_px=25.0)]
    a = W.stack_alloc(night, snap)
    assert a["strict_pref"]["qty"] == {"AAA": 4, "BBB": 20}          # AAA capped at 5% x 2000 = $100; BBB gets the rest
    assert a["strict_night"]["avail"] == 100.0 and a["strict_night"]["qty"]["AAA"] == 2
    assert a["lenient_pref"]["avail"] == 1000.0
