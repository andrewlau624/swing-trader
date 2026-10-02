"""Goal hunt Study G8 (pre-registered in round1_prose.md, commit ff2c554): convertible pricing 8-Ks; buy the opening cross
of the first session after the filing date, sell the 5th session's closing cross; return minus SPY over the window.
G8a = size / 20d ADV$ >= 3; G8b = G8a without a capped call or a concurrent repurchase / share offering.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g8 build    # events (no prices after fd)
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g8 select   # 2021-23, one look
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g8 judge    # 2024-26 + holdout 2016-20, only if select passes

Output: data/research/program/goal_g8_out.txt
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g8_events.parquet"
QUERIES = ['"announces pricing" "convertible senior notes"', '"announces pricing" "convertible notes"',
           '"prices offering" "convertible senior notes"', '"pricing of" "convertible senior notes"',
           '"priced its" "convertible senior notes"', '"upsized" "convertible senior notes" "pricing"']
HOLD = 5
SEL, JDG, HO = ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-09-30"), ("2016-01-01", "2020-12-31")
AMT = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*(million|billion)\s+(?:aggregate\s+)?principal\s+amount", re.I)
PRICED = re.compile(r"(announc\w* (?:the )?pricing|prices? (?:its |an |the |upsized )?(?:private )?offering|pricing of|priced (?:its|an|the))"
                    r"[^.]{0,200}convertible", re.I)
CAPPED = re.compile(r"capped call", re.I)
CONC = re.compile(r"concurrent\w*[^.]{0,200}(repurchas|buy ?back|offering of (?:its )?(?:shares of )?(?:its )?common stock|delta)", re.I)


def out():
    f = open(PROG / "goal_g8_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def hits():
    H = []
    for q in QUERIES:
        H += F.fts_years(q, "8-K")
    H = list({r["id"]: r for r in H}.values())
    return H


def build():
    log = out()
    log(f"=== G8 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    H = hits()
    log(f"  fts hits {len(H)}")
    rows = []
    for j, h in enumerate(H):
        adsh, name = h["id"].split(":", 1)
        tk = F.ticker_of(h["names"][0]) if h["names"] else []
        if not tk:
            continue
        t = F.doc(h["ciks"][0], adsh, name)
        if not PRICED.search(t):
            continue
        m = AMT.search(t)
        if not m:
            continue
        amt = float(m.group(1).replace(",", "")) * (1e9 if m.group(2).lower() == "billion" else 1e6)
        rows.append(dict(sym=tk[0].replace("-", "."), fd=pd.Timestamp(h["date"]), amt=amt, capped=bool(CAPPED.search(t)),
                         conc=bool(CONC.search(t)), adsh=adsh))
        if j % 200 == 0:
            print(f"  docs {j}/{len(H)}", flush=True)
    E = pd.DataFrame(rows).sort_values(["sym", "fd"])
    keep, last = [], {}
    for r in E.itertuples():                              # first filing per issuer per 30 days
        if r.sym in last and (r.fd - last[r.sym]).days <= 30:
            continue
        last[r.sym] = r.fd
        keep.append(r.Index)
    E = E.loc[keep]
    bars = F.raw_bars(sorted(E.sym.unique()))
    out_rows = []
    for r in E.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            continue
        b = b.sort_index(); idx = pd.DatetimeIndex(b.index)
        i = idx.searchsorted(r.fd + pd.Timedelta(days=1))
        if i < 20 or i + HOLD - 1 >= len(idx) or (idx[i] - r.fd).days > 7:
            continue
        h20 = b.iloc[i - 20:i]
        adv = (h20.close * h20.volume).mean()
        out_rows.append(dict(sym=r.sym, fd=r.fd, d=idx[i], dx=idx[i + HOLD - 1], amt=r.amt, capped=r.capped, conc=r.conc,
                             pc=b.close.iloc[i - 1], adv=adv, o=b.open.iloc[i], c=b.close.iloc[i + HOLD - 1]))
    T = pd.DataFrame(out_rows)
    T = T[(T.pc >= 5) & (T.adv > 0)]
    T["ratio"] = T.amt / T.adv
    T.to_parquet(EVF)
    a = T[T.ratio >= 3]
    b = a[~a.capped & ~a.conc]
    log(f"  events with bars {len(T)}; G8a (size/ADV >= 3) {len(a)} by year {a.groupby(a.d.dt.year).size().to_dict()}")
    log(f"  G8b (no capped call / concurrent) {len(b)} by year {b.groupby(b.d.dt.year).size().to_dict()}")
    log(f"  share with capped call {T.capped.mean():.0%}, concurrent {T.conc.mean():.0%}")


def spy():
    from .goal_g2 import spy_adj
    s = spy_adj(); s.index = pd.DatetimeIndex(s.index)
    return s


def excess(V, S, cost):
    """Trade return open(d) -> close(dx) minus SPY close(d-1) -> close(dx) (SPY total return; the open isn't in the
    adjusted series, so SPY's day-d overnight is included: a small, unsigned difference), net of 2 sides."""
    s0 = S.reindex(V.d).values
    prev = np.array([S.loc[:d].iloc[-2] for d in V.d])
    sx = S.reindex(V.dx).values
    cb = B.cost_bps(cost, V.o.values, V.adv.values) / 1e4
    return (V.c.values / V.o.values - 1) - (sx / prev - 1) - 2 * cb


def variants(T):
    a = T[T.ratio >= 3]
    return {"G8a": a, "G8b": a[~a.capped & ~a.conc]}


def tstat(x):
    x = np.asarray(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def report(win, log):
    T = pd.read_parquet(EVF)
    S = spy()
    res = {}
    for k, V in variants(T).items():
        V = V[(V.d >= win[0]) & (V.d <= win[1])]
        for cost in ("tier", "tier_hi"):
            x = excess(V, S, cost) if len(V) else np.array([])
            res[(k, cost)] = (V, x)
            if len(x):
                yrs = pd.Series(x, index=V.d.dt.year.values).groupby(level=0).agg(["mean", "count"])
                log(f"  {k} {cost:8s} n {len(x)} mean {x.mean():+.2%} median {np.median(x):+.2%} hit {(x > 0).mean():.0%} t {tstat(x):+.2f} "
                    f"| by year " + " ".join(f"{y}:{m:+.1%}({n})" for y, (m, n) in yrs.iterrows()))
    return res


def select():
    log = out()
    log(f"\n=== G8 SELECT 2021-23 {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    res = report(SEL, log)
    for k in ("G8a", "G8b"):
        V, x = res[(k, "tier")]
        ok = len(x) >= 20 and x.mean() >= 0.01 and tstat(x) >= 2
        log(f"  {k}: select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": select}[sys.argv[1]]()
