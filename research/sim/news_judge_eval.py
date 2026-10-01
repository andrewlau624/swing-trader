"""Round 23, Study BA: forward test of the LLM news judge (pre-registered; run on the server's log).

    PYTHONPATH=. .venv/bin/python -m research.sim.news_judge_eval [path/to/news-judge.jsonl]
    (make news-eval)

Each judged night pick (date d, symbol) is scored on the OFFICIAL crosses (Alpaca /v2/stocks/auctions:
close cross d -> open cross of the next session; Study AW), net of 2 x 2.5bp. Reported: net by verdict
(and by confidence), then BA1 = weight 0.25 on picks judged fundamental with confidence >= 0.7 (the
freed cash idles), as a daily increment vs equal weight among that night's judged picks: both halves
of the judged sample (split at the median date), NW t, sign-flip placebo and a within-night shuffle of
the flags (1,000 draws). The verdict is read ONCE, at >= 300 judged picks with a verdict
(round1_prose.md, Round 23); before that this prints progress only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MIN_N = 300
COST = 2.5e-4


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 20:
        return float("nan")
    mu = x.mean(); e = x - mu; n = len(x)
    s = (e * e).sum() / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return mu / np.sqrt(s / n) if s > 0 else float("nan")


def crosses(T: pd.DataFrame) -> pd.DataFrame:
    from research.sim.auction_fetch import _env, fetch
    H = _env(); out = []
    for d, g in T.groupby("date"):
        end = (pd.Timestamp(d) + pd.Timedelta(days=5)).date()
        rows = fetch(sorted(g.sym), str(d), str(min(end, pd.Timestamp.now().date() - pd.Timedelta(days=1))), H)
        for s in g.sym:
            v = sorted(rows.get(s, []), key=lambda x: x["d"])
            c = [x for x in v if x["d"] == d]
            o = [x for x in v if x["d"] > d and x.get("o")]
            cp = max(c[0]["c"], key=lambda q: q.get("s", 0))["p"] if c and c[0].get("c") else np.nan
            op = max(o[0]["o"], key=lambda q: q.get("s", 0))["p"] if o else np.nan
            out.append((d, s, op / cp - 1 if cp and np.isfinite(cp) else np.nan))
    return pd.DataFrame(out, columns=["date", "sym", "ret"])


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else ROOT / "state" / "news-judge.jsonl"
    T = pd.DataFrame([json.loads(x) for x in path.read_text().splitlines() if x.strip()])
    T = T[T.verdict.notna()].drop_duplicates(["date", "sym"])
    print(f"judged picks with a verdict: {len(T)} / {MIN_N} needed; verdicts {T.verdict.value_counts().to_dict()}")
    if T.empty:
        return 0
    T = T.merge(crosses(T), on=["date", "sym"], how="left")
    T = T[T.ret.notna() & (T.ret.abs() < 1)]
    T["net"] = T.ret - 2 * COST
    for v, g in T.groupby("verdict"):
        print(f"  {v:12s} n {len(g):4d}  net {g.net.mean()*1e4:+7.1f}bp  (t {g.net.mean()/g.net.std()*np.sqrt(len(g)):+.2f})")
    hi = T[T.confidence >= 0.7]
    for v, g in hi.groupby("verdict"):
        print(f"  {v:12s} conf>=0.7 n {len(g):4d}  net {g.net.mean()*1e4:+7.1f}bp")
    if len(T) < MIN_N:
        print(f"\nBA1 not judged yet: {len(T)} of {MIN_N} scored picks (the verdict is read once, at {MIN_N}).")
        return 0
    T["flag"] = (T.verdict == "fundamental") & (T.confidence >= 0.7)

    def inc(df):
        w = np.where(df.flag, 0.25, 1.0)
        return (df.assign(x=(w - 1) * df.net).groupby("date").apply(lambda g: g.x.sum() / len(g)))

    d = inc(T)
    mid = sorted(d.index)[len(d) // 2]
    h = [d[d.index < mid].mean() * 1e4, d[d.index >= mid].mean() * 1e4]
    t = nw_t(d.values)
    rng = np.random.default_rng(23)
    flip = np.array([(d.values * rng.choice([-1, 1], len(d))).mean() for _ in range(1000)])
    shuf = []
    for _ in range(1000):
        S = T.copy(); S["flag"] = S.groupby("date").flag.transform(lambda f: rng.permutation(f.values))
        shuf.append(inc(S).mean())
    p1 = (flip < d.mean()).mean() * 100; p2 = (np.array(shuf) < d.mean()).mean() * 100
    ok = h[0] > 0 and h[1] > 0 and t >= 2 and p1 >= 95 and p2 >= 95
    print(f"\nBA1 (fundamental conf>=0.7 at x0.25): flagged {T.flag.mean():.0%} of picks; increment per night "
          f"{d.mean()*1e4:+.2f}bp (halves {h[0]:+.2f} / {h[1]:+.2f}), NW t {t:+.2f}, sign-flip {p1:.0f}%, "
          f"shuffle {p2:.0f}% -> {'PASS (SHADOW -> spec a switch)' if ok else 'DEAD'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
