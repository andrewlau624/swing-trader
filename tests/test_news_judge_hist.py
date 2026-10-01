"""Round 25 BC: the historical LLM test sees only what was public by 15:40 on the pick's day."""
import json
from types import SimpleNamespace

import pandas as pd

from research.sim import news_judge_hist as H


def test_window_is_previous_session_close_to_1540():
    a, b = H.window("2025-07-07")                  # a Monday: previous session is Thursday 07-03 (07-04 holiday)
    assert str(a) == "2025-07-03 16:00:00-04:00" and str(b) == "2025-07-07 15:40:00-04:00"


def test_filings_window_excludes_anything_after_1540(monkeypatch):
    monkeypatch.setattr(H.nj, "_cik_map", lambda d: {"ABC": 1})
    cache = {1: {"filings": {"recent": {
        "acceptanceDateTime": ["2025-07-07T13:00:00.000Z", "2025-07-07T20:30:00.000Z", "2025-07-01T12:00:00.000Z"],
        "form": ["8-K", "8-K", "10-Q"], "items": ["2.02", "1.01", ""], "primaryDocDescription": ["", "", ""]}}}}
    a, b = H.window("2025-07-07")
    got = H.filings_window("ABC", a, b, cache)
    assert [g["form"] + g["items"] for g in got] == ["8-K2.02"], "16:30 ET filing and the week-old 10-Q excluded"


def _probe_with(monkeypatch, answers):
    class C:
        provider = "opencode-go"
        def chat(self, payload):
            return {"model": "m", "choices": [{"message": {"content": json.dumps(answers)}}]}
    monkeypatch.setattr(H, "client_and_model", lambda: (C(), SimpleNamespace(news_judge_model="m")))
    return H.probe()


def test_probe_grades_open_answers_and_voids_on_a_hallucination(monkeypatch, capsys):
    real = {"2024-11": "Donald Trump", "2025-01": "DeepSeek", "2025-04": "Liberation Day", "2025-05": "Geneva"}
    ans = {str(i + 1): real.get(m, "unknown") for i, (m, _, _) in enumerate(H.PROBES)}
    assert _probe_with(monkeypatch, ans) == 0
    assert "starts 2025-08-01" in capsys.readouterr().out
    ans[str(len(H.PROBES))] = "Rivian"                 # a named answer to a fabricated event
    assert _probe_with(monkeypatch, ans) == 1
    assert "VOID" in capsys.readouterr().out


def test_probe_refuses_when_the_model_knows_the_latest_event(monkeypatch, capsys):
    ans = {str(i + 1): (" ".join(k) if m != "F" else "unknown") for i, (m, _, k) in enumerate(H.PROBES)}
    assert _probe_with(monkeypatch, ans) == 1
    assert "cutoff not placed" in capsys.readouterr().out
