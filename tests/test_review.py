"""Review script: cost signs and round-trip pairing. No network."""
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import review  # noqa: E402

ET = ZoneInfo("America/New_York")


def test_costs_and_round_trip(monkeypatch):
    bars = {"LOSER": pd.DataFrame({"open": [0.0, 10.20], "high": 0, "low": 0, "close": [10.00, 0.0], "volume": 1},
                                  index=[pd.Timestamp("2026-09-24"), pd.Timestamp("2026-09-25")])}
    monkeypatch.setattr(review.md, "sip_daily", lambda syms, *a, **k: bars)
    fills = pd.DataFrame([
        dict(book="live", sym="LOSER", leg="night", side="buy", qty=16, px=10.02,
             when=pd.Timestamp("2026-09-24 16:00:01", tz=ET), tif="cls"),
        dict(book="live", sym="LOSER", leg="night", side="sell", qty=16, px=10.15,
             when=pd.Timestamp("2026-09-25 09:30:02", tz=ET), tif="day")])
    f = review.auction_prices(fills)
    buy, sell = f.iloc[0], f.iloc[1]
    assert buy.cost_bps == pytest.approx(20.0), "paid 10.02 vs a 10.00 close auction: 20bp WORSE"
    assert sell.cost_bps == pytest.approx((1 - 10.15 / 10.20) * 1e4), "sold under the 10.20 open: worse, positive"
    rt = review.round_trips(f)
    assert len(rt) == 1
    r = rt.iloc[0]
    assert r.ret == pytest.approx(10.15 / 10.02 - 1)
    assert r.bt_ret == pytest.approx(10.20 / 10.00 - 1 - 15 / 1e4)
    assert r.pnl == pytest.approx(16 * (10.15 - 10.02))


def test_noise_hygiene_counts_clean_days():
    t = lambda s: pd.Timestamp(s, tz=ET)
    f = pd.DataFrame([
        dict(book="live", sym="QQQ", leg="noise", side="buy", qty=2, px=1.0, when=t("2026-09-24 10:01:05")),
        dict(book="live", sym="QQQ", leg="noise", side="sell", qty=2, px=1.0, when=t("2026-09-24 15:57:03")),
        dict(book="live", sym="SMH", leg="noise", side="buy", qty=1, px=1.0, when=t("2026-09-25 11:31:02"))])
    out = review.noise_hygiene(f)
    assert "2026-09-24: 2 fills, flat - clean" in out
    assert "NOT flat" in out and "1 clean day(s) of 2." in out


def test_healthcheck_ping_is_a_noop_without_a_url(monkeypatch):
    import daily
    monkeypatch.delenv("HEALTHCHECK_URL", raising=False)
    monkeypatch.setattr(daily, "__name__", "daily")
    daily.ping_healthcheck(0)       # must not raise or reach the network


def test_impact_inputs_use_only_bars_before_the_fill(monkeypatch):
    import numpy as np
    days = pd.bdate_range("2026-08-01", "2026-09-25")
    close = pd.Series(10 * np.exp(0.03 * np.sin(np.arange(len(days)))), index=days)
    b = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e6})
    b.loc[pd.Timestamp("2026-09-25"), "volume"] = 1e9          # the fill day: must be ignored
    monkeypatch.setattr(review.md, "sip_daily", lambda syms, *a, **k: {"X": b})
    f = pd.DataFrame([dict(book="live", sym="X", qty=100, px=10.0, day=pd.Timestamp("2026-09-25"))])
    r = review.impact_inputs(f).iloc[0]
    h = b[b.index < pd.Timestamp("2026-09-25")].tail(21)
    assert r.adv20 == pytest.approx((h.close * h.volume).iloc[-20:].mean())
    sig = np.log(h.close).diff().iloc[-20:].std()
    assert r.x_bps == pytest.approx(sig * 1e4 * np.sqrt(1000 / r.adv20))


def test_live_fills_reads_the_roth_account_and_labels_it(monkeypatch):
    import datetime as dt
    from types import SimpleNamespace
    import scripts.review as R
    import swingtrader.daily.brokers as BR
    seen = {}
    order = {"orderType": "MARKET_ON_CLOSE", "enteredTime": "2026-09-30T19:40:30+0000",
             "orderActivityCollection": [{"executionLegs": [{"quantity": 3, "price": 10.0,
                                                             "time": "2026-09-30T20:00:01+0000"}]}]}
    client = SimpleNamespace(get_orders_for_account=lambda h, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: [order]))

    class FakeAdapter:
        def __init__(self, client=None, account_env="SCHWAB_ACCOUNT_NUMBER", **k):
            seen["env"] = account_env; self.hash = "h"
        def _leg(self, o):
            return "ABC", "BUY", None
    monkeypatch.setattr(BR, "schwab_client", lambda: client)
    monkeypatch.setattr(BR, "SchwabAdapter", FakeAdapter)
    cfg = SimpleNamespace(daily=SimpleNamespace(ibs_symbols=["QQQ"], ibs_cash_symbol="SGOV",
                                                noise_symbol="QQQ", noise_alt_symbol="SMH"))
    f = R.live_fills(dt.date(2026, 9, 29), cfg, book="roth")
    assert seen["env"] == "SCHWAB_ROTH_ACCOUNT_NUMBER"
    assert list(f.book) == ["roth"] and list(f.leg) == ["night"] and f.tif.iloc[0] == "cls"
