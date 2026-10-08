import pandas as pd
from swingtrader.daybook import shadow


def _fake(days):
    return lambda sym, day, lookback, source: {pd.Timestamp(d): {} for d in days if pd.Timestamp(d) <= day}


def test_forward_defaults_to_last_complete_session(monkeypatch, tmp_path):
    monkeypatch.setattr(shadow, "LEDGER", tmp_path / "l.jsonl")
    monkeypatch.setattr(shadow, "sessions_for", _fake(["2026-10-06", "2026-10-07"]))
    seen = []
    monkeypatch.setattr(shadow, "replay_day", lambda d, source: seen.append(d) or [])
    shadow.forward(None, "alpaca")
    assert seen == [pd.Timestamp("2026-10-07")]


def test_forward_skips_day_without_session(monkeypatch, tmp_path):
    monkeypatch.setattr(shadow, "LEDGER", tmp_path / "l.jsonl")
    monkeypatch.setattr(shadow, "sessions_for", _fake(["2026-10-07"]))
    monkeypatch.setattr(shadow, "replay_day", lambda d, source: [{"kind": "daily", "date": "x", "config": "A"}])
    assert shadow.forward(pd.Timestamp("2026-10-08"), "alpaca") == []
    assert not (tmp_path / "l.jsonl").exists()
