"""Jump hunt: rebuild a registered news-based event file on a longer archive and check that its select-half events are
the ones that were registered (sha256 prefix of the (sym, fd) CSV sorted by (fd, sym), fd <= 2023-12-31).

The news rules use only information up to fd (plus the trade's opening print), so adding later months must not change
any earlier event. A mismatch means the rule changed: the judge must not run.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_rebuild r2_25 ee4fb4de291419c5 [s5 8490e20097b8a31f ...]
"""
from __future__ import annotations

import functools
import hashlib
import sys

import pandas as pd

from . import jump_news as J
from .jump_common import save


def sel_hash(X: pd.DataFrame, upto: str = "2023-12-31") -> tuple[str, int]:
    S = X[["sym", "fd"]].drop_duplicates()
    S = S[S.fd <= upto].sort_values(["fd", "sym"])
    return hashlib.sha256(S.to_csv(index=False).encode()).hexdigest()[:16], len(S)


if __name__ == "__main__":
    J.news = functools.lru_cache(maxsize=1)(J.news)
    args = sys.argv[1:]
    for name, pin in zip(args[::2], args[1::2]):
        E = getattr(J, name)()
        h, n = sel_hash(E.assign(fd=pd.to_datetime(E.fd)))
        ok = h == pin
        print(f"{name}: select-half hash {h} ({n} events) vs registered {pin}: {'MATCH' if ok else 'MISMATCH - do not judge'}")
        if ok:
            save(E, name)
