"""Keep the live account switches out of the tests.

The server's .env holds the real-money switches (DAILY_LIVE, DAILY_ROTH, ROTH_LIMITED_MARGIN,
DAILY_*_CAPITAL, DAILY_INTRADAY_MULT, ...), and Config.load() / get_env() read .env into
os.environ. Tests that assert default behaviour then see the server's settings and fail there
while passing on a laptop. Every test starts with no DAILY_* / ROTH_* variable, from the real
environment or from .env (nor ANTHROPIC_*, so no test can spend API money); a test that needs one sets
it with monkeypatch.setenv.
"""
from __future__ import annotations

import os

import pytest

import swingtrader.config as C

SWITCH_PREFIXES = ("DAILY_", "ROTH_", "ANTHROPIC_", "OPENCODE_", "SEC_")    # no test may call an LLM API


@pytest.fixture(autouse=True)
def _no_live_switches(monkeypatch):
    for k in [k for k in os.environ if k.startswith(SWITCH_PREFIXES)]:
        monkeypatch.delenv(k)
    real = C.load_dotenv

    def load_dotenv(path=None):
        before = set(os.environ)
        real(path)
        if path is None:                       # the real .env: drop the switches it just added
            for k in set(os.environ) - before:
                if k.startswith(SWITCH_PREFIXES):
                    os.environ.pop(k, None)

    monkeypatch.setattr(C, "load_dotenv", load_dotenv)
