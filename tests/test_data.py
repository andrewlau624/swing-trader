"""Data-cache and universe-cache fixes."""
import datetime as dt

import pandas as pd

from swingtrader.data import _covers
from swingtrader.universe import _cache_fresh


def test_empty_cache_marker_counts_as_covered():
    """An empty frame with range metadata is a real answer (dead ticker), not a
    miss; treating it as a miss re-requests every delisted symbol every run."""
    e = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    e.attrs["req_start"] = "2021-01-01"
    e.attrs["req_end"] = "2026-09-18"
    assert _covers(e, pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-18"))
    assert not _covers(e, pd.Timestamp("2020-01-01"), pd.Timestamp("2026-09-18")), \
        "a marker built for a narrower range must not count as covering"
    assert not _covers(None, pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-18"))
    bare = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    assert not _covers(bare, pd.Timestamp("2021-01-01"), pd.Timestamp("2026-09-18")), \
        "a frame with no metadata is not usable"


def test_assets_cache_ttl():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat()
    assert _cache_fresh({"fetched_at": now}, 7)
    assert not _cache_fresh({"fetched_at": old}, 7)
    assert not _cache_fresh({}, 7), "an undated legacy cache must be refreshed once"


def test_universe_rejects_a_sliver_cache_and_fetch(tmp_path, monkeypatch):
    """2026-10-23: a broken asset fetch left ~40 names and the night leg scanned them for two weeks."""
    import datetime as dt, json, pytest
    from swingtrader import universe as U
    monkeypatch.setattr(U, "CACHE", tmp_path)
    (tmp_path / "assets.json").write_text(json.dumps({
        "symbols": ["AAA"] * 40, "n_active": 40, "n_inactive": 0,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat()}))
    calls = []
    def fetch():
        calls.append(1)
        raise RuntimeError("only 40 active names on major exchanges")
    monkeypatch.setattr(U, "_fetch_assets", fetch)
    info = U.all_assets()
    assert calls, "a fresh but sliver cache must be refetched, not trusted"
    assert info.n_active == 40          # fetch failed: falls back to the cache, and the executor warns
