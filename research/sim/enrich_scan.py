"""Discovery C6 (method D): which EDGAR form types are over-represented in the 10 days before the biggest 5-day up
moves in $1-100M ADV names. Discover on 2020-10 .. 2022-06; candidates (ratio > 2, > 30 event cases) confirm once on
2022-07 .. 2023-12 (ratio > 2 and one-sided p < 0.05). Exploration only (<= 2023); K = form types scanned is logged."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from research.sim.event_fetch import company_tickers, full_index

DISC, CONF = ("2020-10-01", "2022-06-30"), ("2022-07-01", "2023-12-31")
MOVE, GAP, NCTRL, LOOK = 0.30, 10, 5, 10


def filings() -> pd.DataFrame:
    D = pd.concat([full_index(y, q) for y in (2020, 2021, 2022, 2023, 2024) for q in (1, 2, 3, 4)])
    D["date"] = pd.to_datetime(D.date)
    return D[["form", "cik", "date"]]


def events(rng) -> pd.DataFrame:
    P = pd.read_pickle("data/research/night/panel.pkl")
    C, V = P["close"].loc[:"2024-01-31"], P["volume"].loc[:"2024-01-31"]
    adv = (C * V).rolling(20).median()
    f5 = C.shift(-5) / C - 1
    ok = (adv >= 1e6) & (adv <= 1e8) & C.notna() & f5.notna()
    rows = []
    days = C.index
    for s in C.columns:
        m = ok[s].values
        if m.sum() < 60:
            continue
        r = f5[s].values
        idx = np.where(m)[0]
        last = -999
        for i in idx[r[idx] >= MOVE]:
            if i - last >= GAP:
                rows.append((s, days[i], 1)); last = i
        pool = idx
        if len(rows) and rows[-1][0] == s:
            k = sum(1 for x in rows if x[0] == s and x[2] == 1)
            for i in rng.choice(pool, size=min(len(pool), NCTRL * k), replace=False):
                rows.append((s, days[i], 0))
    return pd.DataFrame(rows, columns=["sym", "d", "ev"])


def scan(E: pd.DataFrame, F: pd.DataFrame, win) -> pd.DataFrame:
    E = E[(E.d >= win[0]) & (E.d <= win[1])].copy()
    tick = {t: c for c, ts in company_tickers().items() for t in ts}
    E["cik"] = E.sym.map(tick)
    E = E.dropna(subset=["cik"])
    F = F[F.cik.isin(set(E.cik))]
    G = {c: g for c, g in F.groupby("cik")}
    hits = []
    for k, e in enumerate(E.itertuples()):
        g = G.get(e.cik)
        if g is None:
            continue
        w = g[(g.date <= e.d) & (g.date > e.d - pd.Timedelta(days=int(LOOK * 1.45)))]  # ~10 sessions
        for f in set(w.form):
            hits.append((k, f))
    H = pd.DataFrame(hits, columns=["k", "form"])
    E = E.reset_index(drop=True)
    H["ev"] = E.ev.values[H.k.values]
    n1, n0 = int((E.ev == 1).sum()), int((E.ev == 0).sum())
    T = H.groupby(["form", "ev"]).size().unstack(fill_value=0).rename(columns={0: "c0", 1: "c1"})
    T["p1"], T["p0"] = T.c1 / n1, T.c0 / n0
    T["ratio"] = T.p1 / T.p0.replace(0, np.nan)
    # one-sided binomial-normal test of p1 > p0 (two proportions)
    pp = (T.c1 + T.c0) / (n1 + n0)
    z = (T.p1 - T.p0) / np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n0))
    T["p"] = 0.5 * np.vectorize(math.erfc)(z / math.sqrt(2))
    T.attrs.update(n1=n1, n0=n0)
    return T.sort_values("ratio", ascending=False)


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    F = filings()
    E = events(rng)
    A = scan(E, F, DISC)
    K = int(((A.c1 + A.c0) >= 5).sum())
    print(f"discover {DISC}: events {A.attrs['n1']}, controls {A.attrs['n0']}, K (form types with >= 5 cases) {K}")
    cand = A[(A.ratio > 2) & (A.c1 > 30)]
    print(cand.round(4).head(30).to_string())
    B = scan(E, F, CONF)
    print(f"\nconfirm {CONF}: events {B.attrs['n1']}, controls {B.attrs['n0']}")
    J = cand[["c1", "ratio"]].join(B[["c1", "c0", "ratio", "p"]], rsuffix="_conf")
    J["confirmed"] = (J.ratio_conf > 2) & (J.p < 0.05)
    print(J.round(4).to_string())
    A.to_csv("data/research/events/enrich_disc.csv"); B.to_csv("data/research/events/enrich_conf.csv")
