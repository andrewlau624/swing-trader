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


import pytest


@pytest.mark.parametrize("provider,var", [("opencode-go", "OPENCODE_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY")])
def test_no_key_is_a_silent_no_op(tmp_path, monkeypatch, provider, var):
    logs = []
    n = nj.run_shadow(_picks(), "2026-10-01", pd.Timestamp("2026-09-30 16:00", tz=ET),
                      pd.Timestamp("2026-10-01 15:40", tz=ET), tmp_path, logs.append,
                      model="m", effort="low", max_calls=8, keys=("k", "s"), provider=provider)
    assert n == 0 and f"no {var}" in logs[0]
    assert not (tmp_path / nj.LOG_NAME).exists()


class FakeOpenCode:
    provider = "opencode-go"

    def __init__(self, content):
        self.content, self.payloads = content, []

    def chat(self, payload):
        self.payloads.append(payload)
        return {"id": "chatcmpl-1", "model": "deepseek-v4-flash", "usage": {"prompt_tokens": 90, "completion_tokens": 30},
                "choices": [{"message": {"content": self.content}}]}


def test_opencode_path_parses_json_mode_and_logs_the_served_model(tmp_path):
    c = FakeOpenCode('```json\n{"verdict": "fundamental", "confidence": 1.4, "catalyst": "guidance cut", "reason": "8-K"}\n```')
    _run(tmp_path, c, max_calls=1)
    rec = json.loads((tmp_path / nj.LOG_NAME).read_text().splitlines()[0])
    assert rec["verdict"] == "fundamental" and rec["confidence"] == 1.0, "fenced JSON parsed, confidence clipped"
    assert rec["provider"] == "opencode-go" and rec["served_by"] == "deepseek-v4-flash" and rec["tokens_in"] == 90
    p = c.payloads[0]
    assert p["response_format"] == {"type": "json_object"} and p["temperature"] == 0
    assert p["messages"][0]["role"] == "system" and "JSON object" in p["messages"][0]["content"]


def test_opencode_invalid_verdict_is_logged_as_an_error(tmp_path):
    _run(tmp_path, FakeOpenCode('{"verdict": "maybe", "confidence": 0.5, "catalyst": "", "reason": ""}'), max_calls=1)
    rec = json.loads((tmp_path / nj.LOG_NAME).read_text().splitlines()[0])
    assert rec["verdict"] is None and "bad verdict" in rec["error"]


def test_default_provider_is_opencode_deepseek_flash():
    from swingtrader.config import Config
    d = Config.load().daily
    assert (d.news_judge_provider, d.news_judge_model) == ("opencode-go", "deepseek-v4-flash")


def test_sec_contact_comes_from_the_resend_address(monkeypatch):
    for v in ("SEC_USER_AGENT", "NOTIFY_EMAIL"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr("swingtrader.config.load_dotenv", lambda path=None: None)
    with pytest.raises(RuntimeError, match="NOTIFY_EMAIL"):
        nj.sec_headers()
    monkeypatch.setenv("NOTIFY_EMAIL", "jane@example.com")
    assert nj.sec_headers() == {"User-Agent": "swing-trader personal research jane@example.com"}
    monkeypatch.setenv("SEC_USER_AGENT", "Jane Doe jane@work.com")
    assert nj.sec_headers() == {"User-Agent": "Jane Doe jane@work.com"}, "explicit override wins"


def test_opencode_client_retries_without_json_mode_on_400_and_shows_errors(monkeypatch):
    calls = []

    seen = []

    def post(url, json=None, timeout=None, headers=None):
        calls.append(json); seen.append(headers)
        if "response_format" in json:
            return SimpleNamespace(status_code=400, text='{"error":"response_format not supported"}')
        if json["model"] == "bad":
            return SimpleNamespace(status_code=400, text='{"error":"unknown model bad"}')
        return SimpleNamespace(status_code=200, text="", json=lambda: {"ok": 1})

    monkeypatch.setattr(nj.requests, "post", post)
    c = nj.OpenCodeClient("k")
    assert c.chat({"model": "m", "response_format": {"type": "json_object"}}) == {"ok": 1}
    assert "response_format" not in calls[-1] and "not supported" in c.json_mode_rejected
    with pytest.raises(RuntimeError, match="unknown model bad"):
        c.chat({"model": "bad"})
    h = seen[0]
    assert h["x-opencode-session"].startswith("news-judge-") and h["User-Agent"] == nj.USER_AGENT
    assert h["Authorization"] == "Bearer k"
