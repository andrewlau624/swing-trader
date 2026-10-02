"""Generic runner for "trade the session after a filing" studies (Study ID / Round 32 machinery), for runbook use.

You supply ONLY an events file: a parquet with columns `sym` (ticker, upper case) and `fd` (filing date, datetime;
the trade is the FIRST regular session after it: buy the opening cross, sell the closing cross). Everything else
(raw prices, ADV, the V7 book sleeve, both halves, NW t, sign-flip and event-shuffle placebos, maxDD, P(DD>50%), DSR,
the judge half, PASS/DEAD) is the registered insider_day.run evaluation.

    # 1) explore on the SELECT half only (no N, no verdict): counts, per-year mean, hit rate, t
    PYTHONPATH=. .venv/bin/python -m research.sim.event_runner explore EVENTS.parquet
    # 1b) RARE big-swing events (too few for statistics): every deal, hit rate, mean, worst; hold N sessions
    PYTHONPATH=. .venv/bin/python -m research.sim.event_runner deals EVENTS.parquet HOLD select   # explore
    PYTHONPATH=. .venv/bin/python -m research.sim.event_runner deals EVENTS.parquet HOLD judge    # once, registered
    # 2) after pre-registering: the full registered test (prints PASS/DEAD)
    PYTHONPATH=. .venv/bin/python -m research.sim.event_runner run EVENTS.parquet "LABEL" N_PROGRAM [ADV_MIN]

ADV_MIN defaults to 2e7 ($20M a day, ID3's liquidity floor).
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from . import event_fetch as F
from . import filing_day as FD
from . import insider_day as I
from .outside_box import NIGHT

ROOT = pathlib.Path(__file__).resolve().parents[2]
SELECT_END = pd.Timestamp("2023-12-31")
END = pd.Timestamp("2026-03-31")          # the insider/EDGAR caches end here; the judge half is 2024-01-01..END


def load(path: str) -> pd.DataFrame:
    X = pd.read_parquet(path)
    assert {"sym", "fd"} <= set(X.columns), "events file needs columns sym, fd"
    X = X.assign(sym=X.sym.astype(str).str.upper().str.strip(), fd=pd.to_datetime(X.fd)).dropna(subset=["sym", "fd"])
    return X.drop_duplicates(["sym", "fd"])


def explore(path: str, adv_min: float = 2e7) -> None:
    """Select half only (<= 2023-12-31): never looks at 2024+."""
    X = load(path)
    X = X[X.fd <= SELECT_END]
    T, _ = FD.trades(X, SELECT_END)
    T = T[T.adv >= adv_min].assign(d=lambda z: pd.to_datetime(z.d))
    print(f"SELECT HALF ONLY (<= {SELECT_END.date()}), ADV >= ${adv_min/1e6:.0f}M")
    if len(T) < 3:
        print(f"events {len(X)} -> trades {len(T)}: too few (prices start 2020-10; check sym/fd). "
              "EXPLORE GATE: FAILS -> stop, record as explored-dead")
        return
    net = T.ret - 5e-4                                     # 2.5bp per side
    t = net.mean() / (net.std() / np.sqrt(len(net))) if len(net) > 2 else float("nan")
    print(f"events {len(X)} -> trades {len(T)}  ({len(T) / max(T.d.dt.year.nunique(), 1):.0f} per year)")
    print(f"net per trade {net.mean()*1e4:+.1f}bp  median {net.median()*1e4:+.1f}bp  hit rate {(net > 0).mean():.0%}  t {t:+.2f}")
    print("by year: " + "  ".join(f"{y}: {v*1e4:+.1f}bp (n {n})" for (y, v), n in
                                  zip(net.groupby(T.d.dt.year).mean().items(), T.groupby(T.d.dt.year).size())))
    per_yr = len(T) / max(T.d.dt.year.nunique(), 1)
    hit = (net > 0).mean()
    if per_yr >= 100:
        track, gate = "FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2", net.mean() >= 10e-4 and hit >= 0.5 and t >= 2
    elif per_yr >= 24:
        track, gate = "SEMI-RARE (24-100/yr): net >= +50bp, hit >= 55%, t >= 2", net.mean() >= 50e-4 and hit >= 0.55 and t >= 2
    else:
        print(f"RARE (< 24/yr): use the deal report instead -> event_runner deals {path} HOLD select")
        return
    print(f"TRACK {track}: {'MEETS -> may pre-register' if gate else 'FAILS -> stop, record as explored-dead'}")


def hold_trades(X: pd.DataFrame, hold: int, end, adv_min: float) -> pd.DataFrame:
    """Buy the opening cross of the first session after fd, sell the closing cross `hold` sessions later
    (hold=1: same day). Raw Alpaca prices; ADV$ as of the session before entry; prior close >= $5."""
    P = pd.read_pickle(NIGHT / "panel.pkl")
    C, V = P["close"], P["volume"]
    adv = (C * V).rolling(20, min_periods=15).mean()
    cal = C.index
    syms = sorted(set(X.sym) & set(C.columns))
    bars = F.raw_bars(syms)
    rows = []
    for s, fd in zip(X.sym, X.fd):
        i = cal.searchsorted(fd + pd.Timedelta(days=1))
        j = i + hold - 1
        if i <= 0 or j >= len(cal) or cal[j] > end or s not in adv.columns:
            continue
        b = bars.get(s)
        if b is None or not len(b):
            continue
        b = b.copy(); b.index = pd.to_datetime(b.index)
        o, c, pc = b.open.get(cal[i], np.nan), b.close.get(cal[j], np.nan), b.close.get(cal[i - 1], np.nan)
        rows.append((cal[i], cal[j], s, o, c, pc, adv.at[cal[i - 1], s]))
    T = pd.DataFrame(rows, columns=["d", "exit", "sym", "o", "c", "pc", "adv"]).dropna()
    T = T[(T.pc >= 5) & (T.adv >= adv_min) & (T.o > 0)].drop_duplicates(["d", "sym"])
    T["ret"] = T.c / T.o - 1
    return T[T.ret.abs() < 0.9]


def deals(path: str, hold: int, half: str = "select", adv_min: float = 1e6) -> None:
    """Deal-by-deal report for RARE, BIG-SWING events (too few for statistics): every event, its P&L at 2.5bp/side,
    hit rate, mean, worst, per year. half=select (<= 2023) while exploring; half=judge (2024+) once, after
    pre-registering."""
    X = load(path)
    if half == "select":
        X, end = X[X.fd <= SELECT_END], SELECT_END
    else:
        X, end = X[X.fd > SELECT_END], END
    T = hold_trades(X, hold, end, adv_min)
    net = T.ret - 5e-4
    print(f"DEALS, {half.upper()} HALF, hold {hold} session(s), ADV >= ${adv_min/1e6:.0f}M: {len(T)} events "
          f"({len(T) / max(T.d.dt.year.nunique(), 1):.1f} per year)")
    if not len(T):
        print("no events -> stop"); return
    for r, n in zip(T.itertuples(), net):
        print(f"  {r.d.date()} {r.sym:6s} open {r.o:9.2f} -> close {r.exit.date()} {r.c:9.2f}  net {n*100:+7.2f}%")
    print(f"hit rate {(net > 0).mean():.0%}  mean {net.mean()*100:+.2f}%  median {net.median()*100:+.2f}%  "
          f"worst {net.min()*100:+.2f}%  best {net.max()*100:+.2f}%")
    print("by year: " + "  ".join(f"{y}: {v*100:+.2f}% (n {n})" for (y, v), n in
                                  zip(net.groupby(T.d.dt.year).mean().items(), T.groupby(T.d.dt.year).size())))
    if half == "select":
        ok = (net > 0).mean() >= 0.65 and net.mean() >= 0.03 and net.min() >= -0.15 and len(T) >= 6
        print(f"RARE GATE (>= 6 events, hit >= 65%, mean >= +3%, worst >= -15%): "
              f"{'MEETS -> may pre-register' if ok else 'FAILS -> stop, record as explored-dead'}")
    else:
        ok = (net > 0).mean() >= 0.60 and net.mean() > 0 and net.min() >= -0.20
        print(f"RARE VERDICT (judge half: hit >= 60%, mean > 0, worst >= -20%): {'PASS' if ok else 'DEAD'}")


def run(path: str, label: str, n_prog: int, adv_min: float = 2e7) -> None:
    X = load(path)
    T, cal = FD.trades(X, END)
    RO, RC = FD.raw_frames(T)
    safe = "".join(ch if ch.isalnum() else "_" for ch in label)[:40]
    f = open(ROOT / f"data/research/program/event_runner_{safe}_out.txt", "w")

    def log(*a):
        x = " ".join(str(i) for i in a); print(x, flush=True); f.write(x + "\n"); f.flush()
    log(f"######## {label}: {len(X)} events -> {len(T)} trades (ADV >= ${adv_min/1e6:.0f}M judged)")
    I.run(T, X, cal, RO, RC, {label: (adv_min, np.inf)}, log, END, n_prog, label, h2=("2024-01-01", str(END.date())))
    T.to_pickle(ROOT / f"data/research/program/event_runner_{safe}_trades.pkl")
    f.close()


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "explore":
        explore(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 2e7)
    elif cmd == "deals":
        deals(sys.argv[2], int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "select",
              float(sys.argv[5]) if len(sys.argv) > 5 else 1e6)
    elif cmd == "run":
        run(sys.argv[2], sys.argv[3], int(sys.argv[4]), float(sys.argv[5]) if len(sys.argv) > 5 else 2e7)
    else:
        raise SystemExit("usage: event_runner explore EVENTS.parquet [ADV_MIN] | "
                         "deals EVENTS.parquet HOLD [select|judge] [ADV_MIN] | run EVENTS.parquet LABEL N [ADV_MIN]")
