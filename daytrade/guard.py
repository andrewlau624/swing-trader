"""Account guard: the lab trades only its own brokerage account.

The lab's Schwab account is named by SCHWAB_DAYTRADE_ACCOUNT_NUMBER. The engine refuses to start
(paper or live) if it is unset, or if it could be the live book's account (SCHWAB_ACCOUNT_NUMBER),
the Roth (SCHWAB_ROTH_ACCOUNT_NUMBER) or the leap book (SCHWAB_LEAP_ACCOUNT_NUMBER). Last-4 values
are allowed (that is what `make schwab-login` shows), so a suffix match counts as the same account.
Paper trading uses its own Alpaca paper keys (ALPACA_DAYTRADE_API_KEY), never the live book's.
"""
from __future__ import annotations

from .settings import env as _env

LAB_ENV = "SCHWAB_DAYTRADE_ACCOUNT_NUMBER"
OTHER_ENVS = ("SCHWAB_ACCOUNT_NUMBER", "SCHWAB_ROTH_ACCOUNT_NUMBER", "SCHWAB_LEAP_ACCOUNT_NUMBER")
PAPER_KEY_ENV, PAPER_SECRET_ENV = "ALPACA_DAYTRADE_API_KEY", "ALPACA_DAYTRADE_SECRET_KEY"
OTHER_KEY_ENVS = ("ALPACA_API_KEY", "ALPACA_LIVE_API_KEY")


class AccountGuardError(RuntimeError):
    pass


def _digits(s: str | None) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _same(a: str, b: str) -> bool:
    return bool(a and b) and (a == b or a.endswith(b) or b.endswith(a))


def check_lab_account(env=_env) -> str:
    """Digits of the lab account, or raise. `env` is injectable for tests."""
    lab = _digits(env(LAB_ENV))
    if not lab:
        raise AccountGuardError(f"{LAB_ENV} is not set: the lab needs its own brokerage account")
    if len(lab) < 4:
        raise AccountGuardError(f"{LAB_ENV} needs at least the last 4 digits")
    for name in OTHER_ENVS:
        other = _digits(env(name))
        if _same(lab, other):
            raise AccountGuardError(f"{LAB_ENV} ...{lab[-4:]} is the same account as {name}: refusing")
    return lab


def check_resolved(lab_full: str, linked: dict[str, str]) -> None:
    """After Schwab resolves the lab account to a full number, it must differ from every other
    book's resolved number. linked = {env name: full account number}."""
    for name, num in linked.items():
        if _same(_digits(lab_full), _digits(num)):
            raise AccountGuardError(f"lab account resolves to the same account as {name}: refusing")


def check_paper_keys(env=_env) -> tuple[str, str]:
    k, s = env(PAPER_KEY_ENV), env(PAPER_SECRET_ENV)
    if not (k and s):
        raise AccountGuardError(f"{PAPER_KEY_ENV} / {PAPER_SECRET_ENV} are not set: the lab needs its "
                                "own Alpaca paper account (a second paper account, not the live book's)")
    for name in OTHER_KEY_ENVS:
        if env(name) and env(name) == k:
            raise AccountGuardError(f"{PAPER_KEY_ENV} is the same key as {name}: refusing")
    return k, s


def check_mode(mode: str, env=_env) -> None:
    """Replay needs no account. Paper and live both need the lab account set and distinct."""
    if mode == "replay":
        return
    check_lab_account(env)
    if mode == "paper":
        check_paper_keys(env)
