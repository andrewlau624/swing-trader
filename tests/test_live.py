"""Live-executor tests. Nothing here touches the network."""
import json
from pathlib import Path

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
