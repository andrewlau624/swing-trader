"""Round 23 BA: the LLM news judge is shadow-only, cached per (date, symbol), and never raises."""
import datetime as dt
import json
from types import SimpleNamespace

import pandas as pd

from swingtrader.daily import news_judge as nj

ET = "America/New_York"


class FakeClient:
    def __init__(self, verdict="liquidity", fail=False, refuse=False):
        self.calls = []
        self.verdict, self.fail, self.refuse = verdict, fail, refuse
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("api down")
        text = json.dumps({"verdict": self.verdict, "confidence": 0.8, "catalyst": "none", "reason": "flow"})
        return SimpleNamespace(stop_reason="refusal" if self.refuse else "end_turn", _request_id="req_1",
                               model=kw["model"], content=[SimpleNamespace(type="text", text=text)],
                               usage=SimpleNamespace(input_tokens=100, output_tokens=20))


def _picks():
    return pd.DataFrame({"day_ret": [-0.09, -0.15, -0.11], "price": [12.0, 30.0, 8.0]}, index=["AAA", "BBB", "CCC"])


def _run(tmp_path, client, max_calls=8, today="2026-10-01"):
    logs = []
    n = nj.run_shadow(_picks(), today, pd.Timestamp("2026-09-30 16:00", tz=ET),
                      pd.Timestamp("2026-10-01 15:40", tz=ET), tmp_path, logs.append,
                      model="claude-opus-5-5", effort="low", max_calls=max_calls, keys=("k", "s"),
                      client=client, fetch_news=lambda *a: [{"time": "t", "headline": "h", "summary": "s"}],
                      fetch_filings=lambda *a: [])
    return n, logs


def test_judges_deepest_first_caps_calls_and_caches(tmp_path):
    c = FakeClient()
    n, _ = _run(tmp_path, c, max_calls=2)
    assert n == 2
    recs = [json.loads(x) for x in (tmp_path / nj.LOG_NAME).read_text().splitlines()]
    assert [r["sym"] for r in recs] == ["BBB", "CCC"], "deepest drops first"
    assert recs[0]["verdict"] == "liquidity" and recs[0]["request_id"] == "req_1"
    n2, _ = _run(tmp_path, c, max_calls=8)
    assert n2 == 1 and len(c.calls) == 3, "a second book (or rerun) never re-judges a cached pick"


def test_request_uses_structured_output_and_fallback(tmp_path):
    c = FakeClient()
    _run(tmp_path, c, max_calls=1)
    kw = c.calls[0]
    assert kw["output_config"]["format"]["schema"] == nj.SCHEMA
    assert kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]


def test_api_failure_and_refusal_are_logged_not_raised(tmp_path):
    n, logs = _run(tmp_path, FakeClient(fail=True), max_calls=1)
    rec = json.loads((tmp_path / nj.LOG_NAME).read_text().splitlines()[0])
    assert n == 1 and rec["verdict"] is None and "api down" in rec["error"]
    n, _ = _run(tmp_path, FakeClient(refuse=True), max_calls=1, today="2026-10-02")
    rec = json.loads((tmp_path / nj.LOG_NAME).read_text().splitlines()[-1])
    assert rec["verdict"] is None and rec["error"] == "refusal"


def test_no_key_is_a_silent_no_op(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    logs = []
    n = nj.run_shadow(_picks(), "2026-10-01", pd.Timestamp("2026-09-30 16:00", tz=ET),
                      pd.Timestamp("2026-10-01 15:40", tz=ET), tmp_path, logs.append,
                      model="m", effort="low", max_calls=8, keys=("k", "s"))
    assert n == 0 and "no ANTHROPIC_API_KEY" in logs[0]
    assert not (tmp_path / nj.LOG_NAME).exists()
