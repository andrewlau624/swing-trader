"""Discovery loop method D: EDGAR-form enrichment around big 5-day moves.

Select window only (2020-10-01 .. 2022-06-30). For $1-100M ADV names, take the largest 5-day |move| events; for each,
count EDGAR form types filed in the 10 calendar days before the move's start, against a matched random base (same
issuer, random dates in the same window). Report the enrichment ratio with a binomial 95% CI. Forms over-represented
> 2x with >= 30 cases go forward to a single confirmation look (2022-07 .. 2023-12). K = number of form types scanned.

    PYTHONPATH=. .venv/bin/python -m research.sim.discovery_enrich
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
NIGHT = ROOT / "data/research/night"
SEL_END = pd.Timestamp("2022-06-30")
CONF_END = pd.Timestamp("2023-12-31")
H = {"User-Agent": "research discovery runbook contact@example.com"}


def name_to_cik() -> dict[str, str]:
    from . import event_fetch as F
    tk = F.company_tickers()                     # cik -> tickers
    out = {}
    for cik, ts in tk.items():
        for t in ts:
            out.setdefault(t, cik.zfill(10))
    return out


def submissions(cik: str) -> pd.DataFrame:
    f = NIGHT / f"discovery/sub/{cik}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists():
        j = json.load(open(f))
    else:
        try:
            j = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=H, timeout=30).json()
        except Exception:
            j = {}
        json.dump(j, open(f, "w"))
    r = (j.get("filings") or {}).get("recent")
    if not r:
        return pd.DataFrame(columns=["form", "date"])
    D = pd.DataFrame({"form": r["form"], "date": pd.to_datetime(r["filingDate"])})
    return D


def main():
    P = pd.read_pickle(NIGHT / "panel.pkl")
    C, V = P["close"], P["volume"]
    adv = (C * V).rolling(20, min_periods=15).mean()
    ret5 = C.pct_change(5)
    m = (adv >= 1e6) & (adv <= 1e8)
    r = ret5.where(m)
    d0 = pd.Timestamp("2020-10-01")
    win = r.loc[d0:SEL_END]
    c2c = name_to_cik()
    # events: top 5% |5-day move| per session when in the ADV band
    moves = []
    for d, row in win.iterrows():
        row = row.dropna()
        if row.empty:
            continue
        q = row.abs().quantile(0.90)
        for s, v in row[row.abs() >= q].items():
            moves.append((d, s, v))
    E = pd.DataFrame(moves, columns=["d", "sym", "ret"]).drop_duplicates(["d", "sym"])
    print(f"select-window big-move events: {len(E)} over {E.sym.nunique()} names", flush=True)

    # forms 10 calendar days before move start, per issuer
    subcache = {}
    formcount: dict[str, int] = {}
    cases = 0
    for s in E.sym.unique():
        cik = c2c.get(s)
        if not cik:
            continue
        subcache[s] = submissions(cik)
    rng = np.random.default_rng(7)
    forms_seen = set()
    ev = []
    for d, s, _ in zip(E.d, E.sym, E.ret):
        S = subcache.get(s)
        if S is None or S.empty:
            continue
        a, b = d - pd.Timedelta(days=10), d
        f = S[(S.date >= a) & (S.date < b)]
        if not len(f):
            continue
        cases += 1
        for form in set(f.form):
            forms_seen.add(form)
        ev.append((d, s, set(f.form)))
    # base: same issuer, random dates in the window without a big move
    base = []
    for s in E.sym.unique():
        S = subcache.get(s)
        if S is None or S.empty:
            continue
        for _ in range(4):
            dd = pd.Timestamp(d0) + pd.Timedelta(days=int(rng.integers(0, (SEL_END - d0).days)))
            f = S[(S.date >= dd - pd.Timedelta(days=10)) & (S.date < dd)]
            if len(f):
                base.append((s, set(f.form)))
    out = ROOT / "data/research/program/discovery_enrich_out.txt"
    lines = [f"method D enrichment, select {d0.date()}..{SEL_END.date()}, K(form types scanned)={len(forms_seen)}"]
    res = []
    for form in sorted(forms_seen):
        c = sum(form in fs for _, _, fs in ev)
        n = len(ev)
        b = sum(form in fs for _, fs in base)
        nb = len(base)
        if c < 5:
            continue
        pe = (c + 0.5) / (n + 1)
        pb = (b + 0.5) / (nb + 1)
        ratio = pe / pb
        se = np.sqrt(pe * (1 - pe) / n + pb * (1 - pb) / nb)
        lo, hi = ratio * np.exp(-1.96 * se / pe), ratio * np.exp(1.96 * se / pb)
        res.append((form, c, n, ratio, lo, hi))
    res.sort(key=lambda x: -x[3])
    for form, c, n, ratio, lo, hi in res:
        lines.append(f"  {form:14s} cases {c:5d}/{n}  ratio {ratio:5.2f}  95% CI [{lo:.2f},{hi:.2f}]")
    lines.append(f"cases {n if res else 0}; base {len(base)}")
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
