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
