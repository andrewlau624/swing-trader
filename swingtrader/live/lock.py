"""Single-writer lock per Alpaca account.

Ported from llm-trader, which added it after two live loops on one account
cancelled each other's stops and left a position unprotected overnight. For a
swing strategy that holds through the night that is the worst available failure,
so this guards every run.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path


def account_fingerprint(api_key: str, secret_key: str = "") -> str:
    """Same account -> same fingerprint on any host, without storing the key."""
    return hashlib.sha256(f"{api_key}:{secret_key}".encode()).hexdigest()[:12]


class AccountLock:
    """flock-based. The kernel releases it on crash, so a hung process cannot
    wedge the account permanently."""

    def __init__(self, fingerprint: str, state_dir: Path):
        state_dir.mkdir(parents=True, exist_ok=True)
        self.path = state_dir / f"lock-{fingerprint}"
        self._fh = None

    def acquire(self) -> bool:
        import fcntl
        self._fh = open(self.path, "w")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._fh.close()
            self._fh = None
            return False
        self._fh.write(str(os.getpid()))
        self._fh.flush()
        return True

    def release(self) -> None:
        if self._fh is None:
            return
        import fcntl
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(
                f"another run holds {self.path}; refusing to trade the same "
                "account from two processes")
        return self

    def __exit__(self, *exc):
        self.release()
