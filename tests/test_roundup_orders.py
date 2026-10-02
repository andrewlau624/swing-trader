"""Round 32 B1 automatic round-up buys: buy once per account before the ex-date, sell only once the post-split share
shows (>= 2 days after), cash-in-lieu after 21 days, kill switch after 2 cash outcomes. Fake broker, no network."""
import datetime as dt
from types import SimpleNamespace

from swingtrader.daily import roundup_orders as ro

ALERT = dict(ticker="VIVK", trade_date="2026-10-05", buy_by="2026-10-02", ratio=15.0, last_close=0.3181)


class Fake:
    def __init__(self, held=None):
        self.held = held or {}

    def positions(self):
        return {s: SimpleNamespace(qty=q, current_price=1.0) for s, q in self.held.items()}


def run(tmp, day, ads, alerts=(ALERT,)):
    calls = []
    st = ro.manage(tmp, list(alerts), dt.date.fromisoformat(day), adapters=ads, prices={"VIVK": 0.2983},
                   placer=lambda ad, sym, side, lim=None: calls.append((sym, side, lim)) or "id", log=lambda *a: None)
    return st, calls


def test_buys_one_share_per_account_once(tmp_path):
    ads = {"live": Fake(), "roth": Fake()}
    st, calls = run(tmp_path, "2026-10-02", ads)
    assert [(c[0], c[1]) for c in calls] == [("VIVK", "buy"), ("VIVK", "buy")]
    assert calls[0][2] == 0.3043                          # ask + 2%, 4 decimals under $1 (Schwab rejects far limits)
    _, again = run(tmp_path, "2026-10-02", ads)
    assert again == []                                    # never twice


def test_no_buy_after_buy_by_or_if_already_held(tmp_path):
    _, calls = run(tmp_path, "2026-10-05", {"live": Fake()})
    assert calls == []
    other = tmp_path / "other"
    other.mkdir()
    _, calls = run(other, "2026-10-02", {"live": Fake({"VIVK": 3})})
    assert calls == []


def test_sell_only_after_split_settles_then_cash_and_kill(tmp_path):
    live = Fake()
    run(tmp_path, "2026-10-02", {"live": live})
    live.held = {"VIVK": 1}
    st, calls = run(tmp_path, "2026-10-05", {"live": live})          # ex-date: decide nothing
    assert calls == [] and st["VIVK-2026-10-05"]["live"]["status"] == "waiting"
    st, calls = run(tmp_path, "2026-10-07", {"live": live})
    assert calls == [("VIVK", "sell", None)] and st["VIVK-2026-10-05"]["live"]["status"] == "sold"
    # two later deals paid in cash -> the account is not killed because one was rounded
    for t, ex in (("AAA", "2026-11-02"), ("BBB", "2026-11-09")):
        a = dict(ALERT, ticker=t, trade_date=ex, buy_by="2026-10-30")
        ro.manage(tmp_path, [a], dt.date(2026, 10, 30), adapters={"live": Fake()}, prices={t: 0.5},
                  placer=lambda *k, **kw: "id", log=lambda *k: None)
    st, _ = run(tmp_path, "2026-12-15", {"live": Fake()}, alerts=())
    assert st["AAA-2026-11-02"]["live"]["status"] == "cash" and not ro.killed(st, "live")


def test_kill_switch_after_two_cash_and_no_rounded():
    st = {"A-1": {"roth": {"status": "cash"}}, "B-2": {"roth": {"status": "cash"}}, "C-3": {"live": {"status": "sold"}}}
    assert ro.killed(st, "roth") and not ro.killed(st, "live")
