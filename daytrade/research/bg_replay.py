"""Study Lab-BG: Lab-BC's closing-imbalance signals entered PASSIVELY (round1_prose.md Lab Round 31).
A limit at the 15:54:31 bid (long) / ask (short) rests until 15:55:00. It fills on an SIP trade through the limit,
or at the limit once the size displayed there at placement has traded (queue). If filled: exit market-on-close at
the official close. Reads: Alpaca SIP quotes and trades 15:54:31-15:55:00 (regular session), Lab-BB's signals file.

  python -m daytrade.research.bg_replay
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import random

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A
from . import az_replay as Z
from .bb_replay import OUT as BB
from .bc_replay import CUT

OUT = DATA / "research" / "bg"
TICK = 0.01


def fills():
    from alpaca.data.requests import StockQuotesRequest, StockTradesRequest
    data, _ = A._clients()
    sig = pd.read_parquet(BB / "signals.parquet")
    sig = sig[(sig.dev.abs() >= CUT) & sig.close.notna()]
    cal = {o.date(): cl for o, cl in pickle.loads((Z.OUT / "sessions.pkl").read_bytes())}
    rows = []
    for day, g in sig.groupby("day"):
        cl = cal[dt.date.fromisoformat(day)]
        t0 = (cl - dt.timedelta(minutes=5, seconds=29)).astimezone(dt.timezone.utc)
        t1 = (cl - dt.timedelta(minutes=5)).astimezone(dt.timezone.utc)
        syms = sorted(set(g.sym))
        q = data.get_stock_quotes(StockQuotesRequest(symbol_or_symbols=syms, start=t0, end=t0 + dt.timedelta(seconds=3),
                                                     feed="sip")).df
        tr = data.get_stock_trades(StockTradesRequest(symbol_or_symbols=syms, start=t0, end=t1, feed="sip")).df
        q = q.reset_index() if q is not None and len(q) else pd.DataFrame()
        tr = tr.reset_index() if tr is not None and len(tr) else pd.DataFrame()
        for r in g.itertuples(index=False):
            qs = q[(q.symbol == r.sym) & (q.bid_price > 0)] if len(q) else q
            if not len(qs):
                continue
            qq = qs.iloc[0]
            limit = float(qq.bid_price) if r.side > 0 else float(qq.ask_price)
            queue = float(qq.bid_size) if r.side > 0 else float(qq.ask_size)
            ts = tr[(tr.symbol == r.sym) & (tr.timestamp > qq.timestamp)].sort_values("timestamp") if len(tr) else tr
            filled = False
            for x in ts.itertuples(index=False):
                # a lit limit fills only if the market trades a full tick THROUGH it, or its queue at the limit is
                # used up by LIT prints. Off-exchange (TRF, exchange "D") prints are internalised retail flow at
                # sub-penny prices: they never touch a resting lit order and are ignored.
                if str(getattr(x, "exchange", "")) == "D":
                    continue
                through = x.price <= limit - TICK + 1e-9 if r.side > 0 else x.price >= limit + TICK - 1e-9
                at = abs(x.price - limit) < 1e-9
                if through:
                    filled = True; break
                if at:
                    queue -= float(x.size)
                    if queue < 0:
                        filled = True; break
            rows.append({"day": day, "sym": r.sym, "side": int(r.side), "limit": limit, "close": float(r.close),
                         "mid": (float(qq.bid_price) + float(qq.ask_price)) / 2, "filled": filled})
    x = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(OUT / "fills.parquet")
    return x


def run():
    x = fills()
    cal = pickle.loads((Z.OUT / "sessions.pkl").read_bytes())
    res = {}
    for label, part in (("H2 (judged)", x[x.day >= "2024-06-01"]), ("H1 (reference)", x[x.day < "2024-06-01"])):
        f = part[part.filled].copy()
        n_days = sum(1 for o, _ in cal if (Z.SPLIT <= o.date() <= Z.END) == label.startswith("H2") and Z.START <= o.date() <= Z.END)
        out = {"signals": len(part), "fill_rate": float(part.filled.mean()) if len(part) else None, "fills": len(f)}
        for mult, c in ((1, 0.5), (2, 1.0)):
            entry = f.limit * (1 + f.side * c / 1e4)
            ex = f.close * (1 - f.side * c / 1e4)
            f[f"net{mult}"] = f.side * (ex / entry - 1) * 1e4
        f["gross"] = f.side * (f.close / f.limit - 1) * 1e4
        f["mid_gross"] = f.side * (f.close / f.mid - 1) * 1e4
        f["net_bp"] = f.net1
        out["unfilled_mid_gross"] = float((part[~part.filled].side * (part[~part.filled].close / part[~part.filled].mid - 1) * 1e4).mean())
        out["filled_mid_gross"] = float(f.mid_gross.mean())
        out["gross_from_limit"] = float(f.gross.mean())
        out["1x"] = A.summary(f.assign(net_bp=f.net1).to_dict("records"), n_days)
        out["2x"] = A.summary(f.assign(net_bp=f.net2).to_dict("records"), n_days)
        xs = np.sort(f.net1.values)
        out["without_top20"] = float(xs[:-20].mean()) if len(xs) > 40 else None
        rng = random.Random(43)
        cost = (f.gross - f.net1).values
        means = [np.mean([(g if rng.random() < 0.5 else -g) - cc for g, cc in zip(f.gross.values, cost)]) for _ in range(1000)]
        out["placebo_pct"] = float(np.mean(np.array(means) < f.net1.mean()) * 100) if len(f) else None
        out["fills_per_day"] = len(f) / n_days
        res[label] = out
    h = res["H2 (judged)"]
    res["verdict"] = ("PASS (to paper)" if h["2x"]["mean_bp"] > 0 and h["1x"]["t_day"] >= 2 and (h["without_top20"] or -1) > 0
                      and h["placebo_pct"] >= 95 else "DEAD")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
