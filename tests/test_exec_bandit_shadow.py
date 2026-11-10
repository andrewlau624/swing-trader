import datetime as dt
import json

from swingtrader.daily import exec_bandit_shadow as eb

Q = dict(bid=24.90, ask=25.10, mid=25.00, age_s=12)


def test_arms_rewards_vs_the_close_cross():
    r = eb.arms(Q, cross=25.05, low=24.80)               # traded through the bid: both passive arms fill
    assert r["cross"] == 0.0
    assert r["take"] == round((25.05 / 25.10 - 1) * 1e4, 1) < 0
    assert r["bid_then_cross"] == round((25.05 / 24.90 - 1) * 1e4, 1) > 0
    r = eb.arms(Q, cross=25.05, low=24.95)               # touched below the mid only
    assert r["bid_then_cross"] == 0.0 and r["mid_then_cross"] > 0
    r = eb.arms(Q, cross=25.05, low=24.90)               # touching the bid is not a fill (queue haircut)
    assert r["bid_then_cross"] == 0.0
    assert eb.arms(Q, cross=25.05, low=None)["mid_then_cross"] is None


def _write(p, rows):
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_run_scores_once_and_skips_unpublished_crosses(tmp_path):
    logs, state = tmp_path / "logs", tmp_path / "state"
    logs.mkdir()
    _write(logs / "pref-ex-live.jsonl", [
        dict(ts="2026-11-09T15:25:03", cmd="buy", sym="C-PRN", qty=4, quote=Q),
        dict(ts="2026-11-10T15:25:03", cmd="buy", sym="C-PRN", qty=4, quote=Q),       # cross not out yet
        dict(ts="2026-11-09T15:25:03", cmd="buy-skip", sym="X"),
        dict(ts="2026-11-09T15:25:03", cmd="buy", sym="OLD", qty=4)])                 # pre-quote-logging row
    _write(logs / "cef-rv-live.jsonl", [dict(ts="2026-11-09T09:05:01", cmd="buy", sym="GAB", qty=94,
                                             quote=dict(px=5.0, mid=5.0, ask=5.02))])
    X = {"C-PRN": {"2026-11-09": (None, None, 25.05, 900)}, "GAB": {"2026-11-09": (5.05, 4000, None, None)}}
    cr = lambda syms, s, e, H: {k: v for k, v in X.items() if k in syms}  # noqa: E731
    low = lambda sym, day, H: 24.8  # noqa: E731
    rows = eb.run(state, logs, log=lambda *_: None, today=dt.date(2026, 11, 10), crosses_fn=cr, low_fn=low, H={})
    assert [(r["strategy"], r["sym"]) for r in rows] == [("pref-ex", "C-PRN"), ("cef-rv", "GAB")]
    assert rows[1]["open_vs_prior_mid_bp"] == 100.0
    again = eb.run(state, logs, log=lambda *_: None, today=dt.date(2026, 11, 10), crosses_fn=cr, low_fn=low, H={})
    assert len(again) == 2                                                         # no double scoring
    assert "collecting (1/60)" in eb.line(again)


def test_gate_proposes_only_with_n_and_t():
    rows = [dict(strategy="pref-ex", day=f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}",
                 reward_bp=dict(cross=0.0, take=-20.0, bid_then_cross=5.0 + (i % 3), mid_then_cross=1.0)) for i in range(60)]
    s = eb.stats(rows)
    assert s["state"] == "PROPOSE bid_then_cross" and s["would_choose"] == "bid_then_cross"
    assert eb.stats(rows[:30])["state"].startswith("collecting")
    bad = [dict(r, reward_bp=dict(cross=0.0, take=-20.0, bid_then_cross=-1.0, mid_then_cross=0.0)) for r in rows * 2]
    assert eb.stats(bad)["state"] == "KILL (cross stays)" and eb.stats(bad)["would_choose"] == "cross"
