"""Jump runner: does an event pick stocks that JUMP (+20% or more) far more often than the same stocks normally do,
and does buying them make money after small-cap costs? The bar is fixed here so a "loop until found" session can't
loosen it (prompt_jump_hunt.md).

Events file: parquet with `sym`, `fd` (the date the signal is public, after the close or before the open of the next
session). Trade: buy the OPENING cross of the first session after fd; exit at the CLOSE `hold` sessions later
(rule "hold"), or earlier with a +20% limit sell (rule "tp20": filled at the limit, or at the open if the stock
opens above it). Returns use split-adjusted bars (no fake jumps from reverse splits); the price/ADV filters use raw
bars. Rule "trail" (the RIDE track): exit at the close once it is 15% below the best close since entry, else at
the hold's last close. Holds 1 / 5 / 20 / 60 sessions. Costs per side by 20-day ADV$ before entry: < $1M 75bp, < $5M 40bp, < $20M 15bp, else 5bp.
Universe: raw prior close >= $1, ADV$ >= $250k (a $230 slot can fill).

Matched base: for each event, the SAME stock on every other eligible session of the same half (excluding +-10
sessions around any of its events), same hold and rule. Jump = return >= +20% (before costs) at exit.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_runner explore EVENTS.parquet          # select half only
    PYTHONPATH=. .venv/bin/python -m research.sim.jump_runner judge EVENTS.parquet HOLD RULE   # once, registered
    PYTHONPATH=. .venv/bin/python -m research.sim.jump_runner confirm EVENTS.parquet HOLD RULE # once, only after a judge PASS
    # LLM-scored or other short-history events: set the halves explicitly (dates are the event fd)
    ... explore EVENTS.parquet --start 2025-12-01 --split 2026-04-01
    ... judge EVENTS.parquet HOLD RULE --start 2025-12-01 --split 2026-04-01 --confirm none   (confirm = forward shadow)

Three windows by event date: SELECT start..split (default 2016..2023), JUDGE split..confirm (2024-01..2025-06),
CONFIRM confirm..2026-09 (2025-07..2026-09), never looked at unless the judge half PASSES.

EXPLORE GATE (select half): >= 20 trades; jump rate >= 2x the matched base AND >= 5%; mean net > 0; mean net
without the 3 best trades > 0; median net > -3%; bootstrap P(mean net <= 0) < 10%.
JUDGE VERDICT (judge half, once): >= 15 trades; jump rate >= 1.5x base; mean net > 0; mean net without the 3 best
> 0; bootstrap P(mean net <= 0) < 10%. Prints PASS or DEAD.
CONFIRM VERDICT (confirm window, once, after a judge PASS): >= 10 trades; mean net > 0; mean net without the best
trade > 0; jump rate >= 1.2x base. Prints CONFIRMED or NOT CONFIRMED. FOUND = judge PASS + CONFIRMED.
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np
import pandas as pd

from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
SELECT_END = pd.Timestamp("2023-12-31")
DATA_START, DATA_END = pd.Timestamp("2016-01-01"), pd.Timestamp("2026-09-30")
HOLDS, RULES, JUMP, TP, TRAIL = (1, 5, 20, 60), ("hold", "tp20", "trail"), 0.20, 0.20, 0.15


def cost_side(adv: float) -> float:
    return 75e-4 if adv < 1e6 else 40e-4 if adv < 5e6 else 15e-4 if adv < 2e7 else 5e-4


def split_bars(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Alpaca SIP daily bars, split-adjusted (adjustment='split'), cached under data/research/events/bars/split."""
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import _clients, trade_date
    data, _ = _clients()
    out, need = {}, []
    for s in sorted(set(symbols)):
        f = F._cache("bars", "split", f"{s.replace('/', '_')}.parquet")
        (out.__setitem__(s, pd.read_parquet(f)) if f.exists() else need.append(s))
    for i in range(0, len(need), 50):
        chunk = need[i:i + 50]
        try:
            df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                                                      start=pd.Timestamp("2015-10-01", tz="UTC"),
                                                      end=pd.Timestamp(DATA_END, tz="UTC"), feed="sip",
                                                      adjustment="split")).df
        except Exception:
            df = None
        got = {}
        if df is not None and len(df):
            df = df.reset_index()
            df["date"] = trade_date(df["timestamp"])
            got = {s: g.set_index("date")[["open", "high", "low", "close", "volume"]] for s, g in df.groupby("symbol")}
        for s in chunk:
            g = got.get(s, pd.DataFrame(columns=["open", "high", "low", "close", "volume"]))
            g.to_parquet(F._cache("bars", "split", f"{s.replace('/', '_')}.parquet"))
            out[s] = g
        print(f"  split bars {i + len(chunk)}/{len(need)}", flush=True)
    return out


def _ret(a: pd.DataFrame, i: int, hold: int, rule: str) -> float:
    """Gross return buying the open of row i, exiting by rule within `hold` rows (split-adjusted frame)."""
    o = a.open.iat[i]
    j = i + hold - 1
    if rule == "trail":                      # ride: exit at the close once it is 15% below the best close since entry
        peak = a.close.iat[i]
        for k in range(i, j + 1):
            peak = max(peak, a.close.iat[k])
            if a.close.iat[k] <= peak * (1 - TRAIL):
                return a.close.iat[k] / o - 1
        return a.close.iat[j] / o - 1
    if rule == "tp20":
        lim = o * (1 + TP)
        for k in range(i, j + 1):
            if k > i and a.open.iat[k] >= lim:
                return a.open.iat[k] / o - 1
            if a.high.iat[k] >= lim:
                return TP
    return a.close.iat[j] / o - 1


def _rets(a: pd.DataFrame, ii: np.ndarray, hold: int, rule: str) -> np.ndarray:
    """Vectorized _ret for many entry rows `ii` (same results; _ret stays the reference, tests compare them)."""
    ii = np.asarray(ii, dtype=int)
    if not len(ii):
        return np.zeros(0)
    O, Hh, C = a.open.to_numpy(float), a.high.to_numpy(float), a.close.to_numpy(float)
    w = ii[:, None] + np.arange(hold)[None, :]
    o = O[ii]
    if rule == "trail":
        Cw = C[w]
        peak = np.maximum.accumulate(Cw, axis=1)
        hit = Cw <= peak * (1 - TRAIL)
        f = np.where(hit.any(1), hit.argmax(1), hold - 1)
        return Cw[np.arange(len(ii)), f] / o - 1
    if rule == "tp20":
        lim = o * (1 + TP)
        Ow, Hw = O[w], Hh[w]
        co = Ow >= lim[:, None]
        co[:, 0] = False
        ch = Hw >= lim[:, None]
        any_ = co | ch
        f = any_.argmax(1)
        r = np.arange(len(ii))
        out = np.where(co[r, f], Ow[r, f] / o - 1, TP)
        return np.where(any_.any(1), out, C[ii + hold - 1] / o - 1)
    return C[ii + hold - 1] / o - 1


def trades(X: pd.DataFrame, lo, hi, holds=HOLDS, rules=RULES, base=True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Event trades with fd in [lo, hi] and their same-stock base, for every hold x rule."""
    X = X[(X.fd >= lo) & (X.fd <= hi)]
    syms = sorted(X.sym.unique())
    raw, adj = F.raw_bars(syms), split_bars(syms)
    ev_rows, base_rows = [], []
    H = max(holds)
    for s, g in X.groupby("sym"):
        r, a = raw.get(s), adj.get(s)
        if r is None or a is None or len(a) < 30:
            continue
        r, a = r.copy(), a.copy()
        r.index, a.index = pd.to_datetime(r.index), pd.to_datetime(a.index)
        a = a[~a.index.duplicated()].sort_index()
        r = r.reindex(a.index)
        advs = (r.close * r.volume).rolling(20, min_periods=15).mean().shift(1)
        pc = r.close.shift(1)
        n = len(a)
        idx = a.index
        ev_i = sorted({int(idx.searchsorted(fd + pd.Timedelta(days=1))) for fd in g.fd})
        ok = lambda i: 0 < i and i + H - 1 < n and np.isfinite(advs.iat[i]) and pc.iat[i] >= 1 and advs.iat[i] >= 2.5e5 \
            and a.open.iat[i] > 0 and idx[i] <= DATA_END
        ev_ok = [i for i in ev_i if ok(i) and idx[i + H - 1] <= hi]   # the whole window inside the half: no peeking
        if ev_ok:
            E = pd.DataFrame(dict(sym=s, d=idx[ev_ok], adv=advs.to_numpy()[ev_ok], price=pc.to_numpy()[ev_ok]))
            for h in holds:
                for ru in rules:
                    E[f"{ru}{h}"] = _rets(a, np.array(ev_ok), h, ru)
            ev_rows += E.to_dict("records")
        if not base:
            continue
        near = set()
        for i in ev_i:
            near.update(range(i - 10, i + 11))
        span = [i for i in range(1, n) if lo <= idx[i] and i + H - 1 < n and idx[i + H - 1] <= hi and i not in near and ok(i)]
        bi = np.array(span[::3], dtype=int)                           # every 3rd session: plenty, and faster
        if len(bi):
            Bf = pd.DataFrame(dict(sym=s, d=idx[bi], adv=advs.to_numpy()[bi]))
            for h in holds:
                for ru in rules:
                    Bf[f"{ru}{h}"] = _rets(a, bi, h, ru)
            base_rows.append(Bf)
    return pd.DataFrame(ev_rows), (pd.concat(base_rows, ignore_index=True) if base_rows else pd.DataFrame())


def _boot_p(x: np.ndarray, B: int = 4000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (B, len(x)))].mean(1)
    return float((m <= 0).mean())


def evaluate(T: pd.DataFrame, Bse: pd.DataFrame, col: str) -> dict:
    c = T.adv.map(cost_side) * 2
    net = (T[col] - c).to_numpy()
    jump = (T[col] >= JUMP).to_numpy()
    bj = Bse.groupby("sym")[col].apply(lambda x: (x >= JUMP).mean()) if len(Bse) else pd.Series(dtype=float)
    base_rate = float(T.sym.map(bj).dropna().mean()) if len(bj) else float("nan")
    srt = np.sort(net)
    bm = Bse.groupby("sym")[col].mean() if len(Bse) else pd.Series(dtype=float)
    base_mean = float(T.sym.map(bm).dropna().mean()) if len(bm) else float("nan")
    excess = float(T[col].mean() - base_mean) if base_mean == base_mean else float("nan")
    return dict(base_mean=base_mean, excess=excess, n=len(T), per_yr=len(T) / max(T.d.dt.year.nunique(), 1), jump=float(jump.mean()), base=base_rate,
                lift=float(jump.mean() / base_rate) if base_rate and base_rate > 0 else float("inf"),
                mean=float(net.mean()), median=float(np.median(net)), ex3=float(srt[:-3].mean()) if len(net) > 3 else float("nan"),
                worst=float(net.min()), best=float(net.max()), hit=float((net > 0).mean()), p0=_boot_p(net))


def _line(col, e):
    return (f"{col:7s} n {e['n']:4d} ({e['per_yr']:.0f}/yr)  jump {e['jump']:5.1%} vs base {e['base']:5.1%} "
            f"(x{e['lift']:.1f})  mean net {e['mean']:+6.1%}  ex-top3 {e['ex3']:+6.1%}  median {e['median']:+6.1%}  "
            f"vs stock's usual {e['excess']:+6.1%}  hit {e['hit']:.0%}  worst {e['worst']:+.0%}  best {e['best']:+.0%}  "
            f"P(mean<=0) {e['p0']:.2f}")


def explore_gate(e: dict) -> bool:
    return (e["n"] >= 20 and e["jump"] >= 0.05 and e["lift"] >= 2 and e["mean"] > 0 and e["ex3"] > 0
            and e["median"] > -0.03 and e["p0"] < 0.10)


def judge_gate(e: dict) -> bool:
    return e["n"] >= 15 and e["lift"] >= 1.5 and e["mean"] > 0 and e["ex3"] > 0 and e["p0"] < 0.10


def confirm_gate(e: dict, T: pd.DataFrame, col: str, track: str = "jump") -> bool:
    net = np.sort((T[col] - T.adv.map(cost_side) * 2).to_numpy())
    edge = e["lift"] >= 1.2 if track == "jump" else e["excess"] > 0
    return e["n"] >= 10 and e["mean"] > 0 and net[:-1].mean() > 0 and edge


# RIDE track: enter before / while a stock is hot and keep a chunk of the run. Judged on money, not jump counts:
# mean net >= +3% a trade AND >= +2% better than the same stock's usual return over the same hold and exit rule.
def ride_explore_gate(e: dict) -> bool:
    return (e["n"] >= 20 and e["mean"] >= 0.03 and e["excess"] >= 0.02 and e["ex3"] > 0
            and e["median"] > -0.05 and e["p0"] < 0.10)


def ride_judge_gate(e: dict) -> bool:
    return e["n"] >= 15 and e["mean"] > 0 and e["excess"] > 0 and e["ex3"] > 0 and e["p0"] < 0.10


def load(path: str) -> pd.DataFrame:
    X = pd.read_parquet(path)
    X = X.assign(sym=X.sym.astype(str).str.upper().str.strip(), fd=pd.to_datetime(X.fd)).dropna(subset=["sym", "fd"])
    return X.drop_duplicates(["sym", "fd"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["explore", "judge", "confirm"])
    ap.add_argument("events")
    ap.add_argument("hold", nargs="?", type=int)
    ap.add_argument("rule", nargs="?", choices=RULES)
    ap.add_argument("--start", default=str(DATA_START.date()))
    ap.add_argument("--split", default=str((SELECT_END + pd.Timedelta(days=1)).date()))
    ap.add_argument("--confirm", default="2025-07-01", help="confirm window start, or 'none' (forward shadow instead)")
    ap.add_argument("--track", choices=["jump", "ride"], default="jump", help="the registered track (judge/confirm)")
    a = ap.parse_args(argv)
    X = load(a.events)
    start, split = pd.Timestamp(a.start), pd.Timestamp(a.split)
    conf = None if a.confirm == "none" else pd.Timestamp(a.confirm)
    jend = (conf - pd.Timedelta(days=1)) if conf is not None else DATA_END
    if a.cmd == "explore":
        T, B = trades(X, start, split - pd.Timedelta(days=1))
        print(f"SELECT HALF ONLY: events {start.date()}..{(split - pd.Timedelta(days=1)).date()} "
              f"({len(X[(X.fd >= start) & (X.fd < split)])} events -> {len(T)} trades)")
        if len(T) < 3:
            print("too few trades -> EXPLORE GATE FAILS"); return
        for h in HOLDS:
            for ru in RULES:
                e = evaluate(T, B, f"{ru}{h}")
                print(_line(f"{ru}{h}", e), "| jump", "MEETS" if explore_gate(e) else "fails",
                      "| ride", "MEETS" if ride_explore_gate(e) else "fails")
        print("Pick ONE (track, rule, hold) that MEETS (shortest hold if several) and pre-register it before judging.")
    elif a.cmd == "judge":
        assert a.hold in HOLDS and a.rule, "judge needs HOLD (1/5/20/60) and RULE (hold/tp20/trail)"
        T, B = trades(X, split, jend, holds=(a.hold,), rules=(a.rule,))
        col = f"{a.rule}{a.hold}"
        print(f"JUDGE HALF: events {split.date()}..{jend.date()} -> {len(T)} trades")
        if not len(T):
            print("JUMP VERDICT: DEAD (no trades)"); return
        e = evaluate(T, B, col)
        print(_line(col, e))
        ok = judge_gate(e) if a.track == "jump" else ride_judge_gate(e)
        bar = "jump >= 1.5x base" if a.track == "jump" else "beats the stock's usual return"
        print(f"{a.track.upper()} VERDICT (>= 15 trades, {bar}, mean > 0, ex-top3 > 0, P(mean<=0) < 0.10): "
              f"{'PASS' if ok else 'DEAD'}")
        T.to_pickle(ROOT / f"data/research/program/jump_{pathlib.Path(a.events).stem}_{col}_judge.pkl")
    else:
        assert a.hold in HOLDS and a.rule and conf is not None, "confirm needs HOLD, RULE and a confirm window"
        T, B = trades(X, conf, DATA_END, holds=(a.hold,), rules=(a.rule,))
        col = f"{a.rule}{a.hold}"
        print(f"CONFIRM WINDOW: events {conf.date()}..{DATA_END.date()} -> {len(T)} trades")
        if not len(T):
            print("CONFIRM VERDICT: NOT CONFIRMED (no trades)"); return
        e = evaluate(T, B, col)
        print(_line(col, e))
        bar = "jump >= 1.2x base" if a.track == "jump" else "beats the stock's usual return"
        print(f"CONFIRM VERDICT (>= 10 trades, mean > 0, mean without the best > 0, {bar}): "
              f"{'CONFIRMED' if confirm_gate(e, T, col, a.track) else 'NOT CONFIRMED'}")
        T.to_pickle(ROOT / f"data/research/program/jump_{pathlib.Path(a.events).stem}_{col}_confirm.pkl")


if __name__ == "__main__":
    main()
