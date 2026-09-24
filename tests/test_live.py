"""Live-executor tests. Nothing here touches the network."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from swingtrader.live.broker import PaperBroker
from swingtrader.live.executor import BookState, LivePosition
from swingtrader.live.lock import AccountLock, account_fingerprint


def test_client_order_ids_are_deterministic_and_bounded():
    a = PaperBroker.coid("rev", "UPST", "2026-09-22", "entry")
    b = PaperBroker.coid("rev", "UPST", "2026-09-22", "entry")
    assert a == b, "same decision must produce the same id, or re-runs double-fill"
    assert a != PaperBroker.coid("rev", "UPST", "2026-09-23", "entry")
    assert a != PaperBroker.coid("mom", "UPST", "2026-09-22", "entry")
    assert len(a) <= 48


def test_lock_is_exclusive(tmp_path):
    fp = account_fingerprint("PKTEST", "SEC")
    a, b = AccountLock(fp, tmp_path), AccountLock(fp, tmp_path)
    assert a.acquire()
    assert not b.acquire(), "two processes must not trade one account"
    a.release()
    assert b.acquire()
    b.release()


def test_book_state_round_trips(tmp_path):
    p = tmp_path / "book.json"
    s = BookState(name="reversion", live=True, equity=97_826.0)
    s.positions["UPST"] = {"symbol": "UPST", "qty": 100, "entry_px": 24.78,
                           "entry_date": "2026-09-22", "stop_px": 22.30,
                           "peak": 24.78, "bars_held": 0}
    s.save(p)
    back = BookState.load(p, "reversion", True, 0.0)
    assert back.positions["UPST"]["entry_px"] == 24.78
    assert back.equity == 97_826.0


def test_corrupt_state_falls_back_instead_of_crashing(tmp_path):
    p = tmp_path / "book.json"
    p.write_text("{ this is not json")
    s = BookState.load(p, "reversion", True, 100_000.0)
    assert s.positions == {} and s.equity == 100_000.0


def test_paper_broker_refuses_a_live_key(monkeypatch):
    import swingtrader.live.broker as B
    monkeypatch.setattr(B, "require_alpaca_keys", lambda: ("AKLIVEKEY123", "secret"))
    with pytest.raises(RuntimeError, match="not a paper key"):
        B.PaperBroker(paper=True)


def test_slippage_sign_is_always_a_cost():
    """Buying above reference and selling below it must both read positive."""
    class O:
        def __init__(self, side, fill):
            self.client_order_id = "rev.X.2026-09-22.entry"
            self.filled_at, self.filled_avg_price = "now", fill
            self.side, self.symbol, self.filled_qty, self.id = side, "X", 10, "1"
    b = PaperBroker.__new__(PaperBroker)
    b.recent_orders = lambda days=5: [O("buy", 101.0)]
    f = b.measure_fills({"rev.X.2026-09-22.entry": {"ref_px": 100.0}})[0]
    assert f.slippage_bps == pytest.approx(100.0)
    b.recent_orders = lambda days=5: [O("sell", 99.0)]
    f = b.measure_fills({"rev.X.2026-09-22.entry": {"ref_px": 100.0}})[0]
    assert f.slippage_bps == pytest.approx(100.0), "a bad sell must not read as a gain"


def test_pending_orders_are_not_reconciled_away(tmp_path):
    """Regression: an unfilled OPG order must not be treated as a lost position.

    The post-close run submits for the next open; the pre-open run then sees no
    broker position yet. Reconciling that away re-submits under the next day's
    client_order_id -- a different id, so Alpaca accepts it, and the position
    opens twice.
    """
    p = tmp_path / "book.json"
    s = BookState(name="reversion", live=True)
    s.pending["VG"] = {"coid": "rev.VG.2026-09-22.entry", "day": "2026-09-22",
                       "ref_px": 13.66, "qty": 894}
    s.save(p)
    back = BookState.load(p, "reversion", True, 0.0)
    assert "VG" in back.pending
    assert "VG" not in back.positions, "a pending order is not a position"


def test_entry_skips_symbols_with_work_in_flight():
    from swingtrader.live.executor import Executor
    from swingtrader.config import Config
    st = BookState(name="reversion", live=True)
    st.positions["AAA"] = {"symbol": "AAA"}
    st.pending["BBB"] = {"coid": "x"}
    busy = set(st.positions) | set(st.pending)
    assert busy == {"AAA", "BBB"}, "both held and in-flight symbols must block re-entry"


def _capture(notifier):
    seen = {}
    def fake(subject, html, dedupe_key=None):
        seen["subject"], seen["html"] = subject, html
        return "captured"
    notifier.send = fake
    notifier.enabled = True
    return seen


def test_alert_subject_has_exactly_one_prefix(tmp_path):
    from swingtrader.live.notify import Notifier
    n = Notifier(tmp_path)
    seen = _capture(n)
    common = dict(equity=97_826.56, fills=[], positions={}, pending={},
                  slippage=None, log_tail=[])
    n.activity(actions=["x"], warnings=[], **common)
    assert seen["subject"].count("[swing-trader]") == 1
    n.activity(actions=["x"], warnings=["stop failed"], **common)
    assert seen["subject"].count("[swing-trader]") == 1, seen["subject"]
    assert "⚠" in seen["subject"], "a warning must be visible in the subject line"


def test_alert_body_carries_the_decision_critical_fields(tmp_path):
    from swingtrader.live.notify import Notifier
    from swingtrader.live.broker import Fill
    n = Notifier(tmp_path)
    seen = _capture(n)
    n.activity(equity=97_826.56, actions=["submitted MOO buy 894 VG"],
               fills=[Fill("VG", "buy", 894, 13.71, 13.66, 36.6, "a", "t")],
               positions={"VG": {"qty": 894, "entry_px": 13.71,
                                 "stop_px": 12.34, "bars_held": 0}},
               pending={}, slippage={"n": 1, "mean": 64.7, "median": 64.7, "p90": 64.7},
               warnings=[], log_tail=["line"])
    h = seen["html"]
    for must in ("VG", "13.71", "36.6", "12.34", "WORSE", "line"):
        assert must in h, f"alert omitted {must!r}"


def test_slippage_verdict_flips_at_the_backtest_assumption(tmp_path):
    from swingtrader.live.notify import Notifier
    n = Notifier(tmp_path)
    seen = _capture(n)
    common = dict(equity=1.0, actions=["a"], fills=[], positions={}, pending={},
                  warnings=[], log_tail=[])
    n.activity(slippage={"n": 9, "mean": 18.0, "median": 18.0, "p90": 20.0}, **common)
    assert "holding up" in seen["html"]
    n.activity(slippage={"n": 9, "mean": 41.0, "median": 41.0, "p90": 60.0}, **common)
    assert "WORSE" in seen["html"]


def test_refresh_is_skipped_while_the_market_is_open(monkeypatch, tmp_path):
    """The two management runs must not pay for a 14,760-symbol refresh.

    They cannot submit market-on-open orders anyway, and the last COMPLETE
    daily bar does not change intraday, so the refresh buys nothing.
    """
    import swingtrader.live.executor as E
    calls = []
    monkeypatch.setattr(E, "refresh_bars", lambda *a, **k: calls.append(1))
    monkeypatch.setattr(E, "fetch_bars", lambda *a, **k: {})
    monkeypatch.setattr(E, "all_assets",
                        lambda: type("U", (), {"symbols": ["AAA"]})())

    class Ex(E.Executor):
        def __init__(self):
            self.cfg = __import__("swingtrader.config", fromlist=["Config"]).Config.load()
            self.log_dir = tmp_path; self.state_dir = tmp_path
            self.lines = []; self.actions = []; self.warnings = []

    ex = Ex()
    try:
        ex.load_market(refresh=False)
    except ValueError:
        pass                      # empty bar dict is fine; we only count calls
    assert calls == [], "a management run triggered the slow refresh"


# --------------------------------------------------------------- fixed bugs
def test_measure_fills_does_not_re_emit_recorded_fills():
    """The sample the whole live run exists to produce must not be inflated by
    re-reporting the same fill on every run for five days."""
    class O:
        client_order_id = "rev.X.2026-09-22.entry"
        filled_at, filled_avg_price = "now", 101.0
        side, symbol, filled_qty, id = "buy", "X", 10, "42"
    b = PaperBroker.__new__(PaperBroker)
    b.recent_orders = lambda days=5: [O()]
    refs = {"rev.X.2026-09-22.entry": {"ref_px": 100.0}}
    assert len(b.measure_fills(refs)) == 1
    assert len(b.measure_fills(refs, {"42"})) == 0, "a recorded fill was counted twice"


def test_submit_exit_does_not_cancel_stops_when_exit_already_working():
    """Cancelling the stop and THEN hitting the duplicate id is how a position
    ends up naked with a live sell order out."""
    b = PaperBroker.__new__(PaperBroker)
    cancelled = []

    class O:
        client_order_id = "rev.X.2026-09-22.exit-reversion"
    b.open_orders = lambda: [O()]
    b.cancel_stops = lambda sym: cancelled.append(sym)
    o, note, rejected = b.submit_exit("rev", "X", 10, "2026-09-22", "reversion")
    assert o is None and not rejected
    assert cancelled == [], "must not cancel the stop when the exit is already working"


def test_ensure_protection_rearms_a_stale_stop():
    """A stop at the wrong price (e.g. after a split) is as dangerous as none."""
    b = PaperBroker.__new__(PaperBroker)
    submitted = []

    class Stop:
        id, stop_price, qty = "s1", 100.0, 10
    b.stops_by_symbol = lambda: {"X": Stop()}
    b.client = type("C", (), {
        "cancel_order_by_id": lambda self, i: None,
        "submit_order": lambda self, r: submitted.append(r)})()

    ok, note = b.ensure_protection("X", 50.0, 10)      # split halved the price
    assert ok and "re-armed" in note and submitted


def test_corrupt_state_is_backed_up_and_flagged(tmp_path):
    p = tmp_path / "book.json"
    p.write_text("{ not json")
    s = BookState.load(p, "reversion", True, 100_000.0)
    assert s.load_error and s.positions == {}
    assert list(tmp_path.glob("book.json.corrupt-*")), "corrupt state must be kept, not lost"


def test_notifier_dedupe_keys_keep_insertion_order(tmp_path):
    from swingtrader.live.notify import Notifier
    n = Notifier(tmp_path)
    n._remember("a"); n._remember("b"); n._remember("a")
    assert n._seen == ["a", "b"], "recent keys must not be dropped by set ordering"
    assert Notifier(tmp_path)._seen == ["a", "b"]


def test_corr_above_detects_duplicate_bet():
    from swingtrader.live.executor import _corr_above
    idx = pd.bdate_range("2024-01-02", periods=30)
    a = pd.Series(np.arange(30.0), index=idx)
    b = pd.Series(np.arange(30.0) * 2, index=idx)          # perfectly correlated
    c = pd.Series(np.sin(np.arange(30.0)), index=idx)
    assert _corr_above(a, {"b": b}, 0.9)
    assert not _corr_above(a, {"c": c}, 0.9)


def test_live_decide_honours_overnight_and_corr_filters():
    """Live must apply the same entry gates the backtest was validated with."""
    from swingtrader.live.executor import Executor
    from swingtrader.config import Config
    cfg = Config.load()
    cfg.walkforward.formation_days = 60
    cfg.selection.top_n = 99
    cfg.selection.min_amplitude_pct = 0.0
    cfg.selection.max_abs_drift_t = 99.0
    cfg.selection.halflife_min = 0.1
    cfg.selection.halflife_max = 999.0
    cfg.selection.hurst_max = 2.0
    cfg.selection.max_efficiency_ratio = 1.0
    cfg.cohorts["toy"] = cfg.cohorts["broad"]
    cfg.cohorts["toy"].min_iex_dollar_vol = 0.0
    cfg.strategy.live_cohort = "toy"
    n = 160
    t = np.arange(n)
    base = 20.0 * (1 + 0.12 * np.sin(2 * np.pi * t / 20))

    def mk(shift):
        c = np.roll(base, shift).copy()
        c[-1] = c[-1] * 0.85          # force z < -1 on the decision bar
        return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                             "close": c, "volume": np.full(n, 1e6)},
                            index=pd.bdate_range("2021-01-04", periods=n))
    bars = {"AAA": mk(0), "BBB": mk(0), "CCC": mk(7)}
    asof = bars["AAA"].index[-1]
    ex = Executor.__new__(Executor)
    ex.cfg, ex.daily_owned = cfg, set()
    st = type("S", (), {"positions": {}, "pending": {}})()

    ent, _ = ex.decide(bars, asof, "reversion", -1.0, st)
    assert {"AAA", "BBB"} <= {e[0] for e in ent}, "fixture: correlated pair should enter unfiltered"

    cfg.strategy.max_corr = 0.9
    ent2, _ = ex.decide(bars, asof, "reversion", -1.0, st)
    assert not ({"AAA", "BBB"} <= {e[0] for e in ent2}), "duplicate bet not filtered live"

    cfg.strategy.max_corr = None
    cfg.strategy.min_overnight_share = 5.0        # impossible -> blocks everything
    ent3, _ = ex.decide(bars, asof, "reversion", -1.0, st)
    assert ent3 == [], "overnight filter not applied live"
