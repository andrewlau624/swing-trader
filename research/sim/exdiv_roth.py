"""Round 22: Study AZ — tax-exempt ex-dividend overnight capture on the Roth's idle overnight cash.

    PYTHONPATH=. .venv/bin/python -m research.sim.exdiv_roth

Pre-registration: research/drafts/round1_prose.md, "Round 22" (commit 4f11550, before any number).
Dividends: Alpaca /v1/corporate-actions (cash_dividend), cached in data/research/night/dividends.json.
Night-leg returns from the official crosses (Study AW). Costs per side.
"""
from __future__ import annotations

import json
import pathlib
import time

import numpy as np
import pandas as pd
import requests

from . import book as B
from . import data as D
from . import roth_cash as RC
from .auction_audit import with_rets
from .auction_fetch import _env
from .max_edge import nw_t, p_dd50
from .new_listings import etf_kind, load_meta
from .program_books import dsr
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/exdiv_roth_out.txt"
DIV = ROOT / "data/research/night/dividends.json"
N_TRIALS = 688
SIZES = (2300.0, 10000.0, 25000.0)


def universe():
    """night d -> top-500 non-ETF symbols by 20-session SIP dollar volume through d-1."""
    P = D.panel(); C, V = P["close"], P["volume"]
    meta = load_meta()
    ok = [s for s in C.columns if etf_kind(s, meta) is None and s in meta
          and meta[s].get("exchange") in ("NYSE", "NASDAQ", "ARCA", "AMEX", "BATS")]
    dv = (C[ok] * V[ok]).rolling(20, min_periods=15).mean().shift(1)
    top = {}
    for d in dv.index:
        x = dv.loc[d].dropna()
        if len(x):
            top[d] = set(x.nlargest(500).index)
    return top


def fetch_divs(syms):
    if DIV.exists():
        return json.load(open(DIV))
    H = _env(); out = []
    syms = sorted(syms)
    for i in range(0, len(syms), 50):
        for a, z in (("2020-10-01", "2022-12-31"), ("2023-01-01", "2024-12-31"), ("2025-01-01", "2026-09-30")):
            tok = None
            while True:
                q = {"symbols": ",".join(syms[i:i + 50]), "types": "cash_dividend", "start": a, "end": z, "limit": 1000}
                if tok:
                    q["page_token"] = tok
                r = requests.get("https://data.alpaca.markets/v1/corporate-actions", params=q, headers=H, timeout=30)
                r.raise_for_status(); j = r.json()
                out.extend(j.get("corporate_actions", {}).get("cash_dividends", []))
                tok = j.get("next_page_token")
                if not tok:
                    break
            time.sleep(0.3)
        print(f"divs {i}/{len(syms)}", flush=True)
    json.dump(out, open(DIV, "w"))
    return out


def events(top, divs, min_yield):
    """night d -> [(sym, total close->open return)] for names going ex on the next session."""
    P = D.panel(); O, C = P["open"], P["close"]
    raw = pd.read_parquet(D.RAW_CLOSE)[["symbol", "date", "raw_close"]]
    raw["date"] = pd.to_datetime(raw["date"])
    rawc = raw.set_index(["date", "symbol"]).raw_close.to_dict()
    cal = C.index; nxt = {a: b for a, b in zip(cal[:-1], cal[1:])}
    prv = {b: a for a, b in nxt.items()}
    ev = {}
    for x in divs:
        if x.get("special") or x.get("foreign"):
            continue
        e = pd.Timestamp(x["ex_date"])
        if e not in prv:
            continue
        d, s = prv[e], x["symbol"]
        if s not in top.get(d, ()) or s not in C.columns:
            continue
        rc = rawc.get((d, s), np.nan)
        if not np.isfinite(rc):
            rc = C.at[d, s]                                         # no raw row: adjusted (div-only factor ~1)
        if rc < 10 or x["rate"] / rc < min_yield:
            continue
        r = O.at[e, s] / C.at[d, s] - 1                              # dividend-inclusive (adjusted) overnight
        if np.isfinite(r) and abs(r) < 0.5:
            ev.setdefault(d, []).append((s, float(r), float(x["rate"] / rc), float(rc)))
    return ev


def replay(s, N, E, ev, cost, spy_on=None):
    """Roth cash book (RC.cash_day) + the ex-div sleeve on the idle overnight cash (fixed capital)."""
    out, prev_i = [], 0.0
    for d in s.days:
        pl, iused, nused = RC.cash_day(s, N, E, d, prev_i, 0.5, 0.5, 150.0, cost)
        idle = max(0.0, E - prev_i - nused)
        x = 0.0
        for sym, r, _, px in ev.get(d, []):
            per = min(idle / len(ev[d]), 0.25 * E)
            sh = np.floor(per / px)
            x += sh * px * (r - 2 * cost / 1e4)
        out.append((pl + x) / E)
        prev_i = iused
    return pd.Series(out, index=s.days)


def main():
    t0 = time.time()
    fh = open(OUT, "w")

    def log(*a):
        z = " ".join(str(i) for i in a)
        print(z, flush=True); fh.write(z + "\n"); fh.flush()

    log("== Round 22: Study AZ (Roth ex-dividend overnight capture); started", pd.Timestamp.now(), "==")
    top = universe()
    divs = fetch_divs(set().union(*top.values()))
    log(f"dividend records {len(divs)}")
    s = load_sim(raw_price=True)
    N0 = B.night_days(raw_price=True, max_corr=0.7)
    Na = with_rets(N0, pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl"), "ret_auc")
    s.I = B.ibs_days()
    P = D.panel(); spy_on = (P["open"]["SPY"].shift(-1) / P["close"]["SPY"] - 1)
    rng = np.random.default_rng(21)
    verdict = {}
    for k, my in (("AZ1", 0.0025), ("AZ2", 0.005)):
        ev = events(top, divs, my)
        evs = [(d, *e) for d, v in ev.items() for e in v if d >= s.days[0]]
        E_ = pd.DataFrame(evs, columns=["d", "sym", "r", "yld", "px"])
        E_["ab"] = E_.r - E_.d.map(spy_on)
        log(f"\n######## {k} (yield >= {my:.2%}): events {len(E_)} ({len(E_)/5.6:.0f}/yr), nights {E_.d.nunique()}")
        for lab, a, z in (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31")):
            x = E_[(E_.d >= a) & (E_.d <= z)]
            pdr = 1 - (x.r.mean() - (x.d.map(spy_on)).mean()) / x.yld.mean()      # implied drop ratio vs SPY
            log(f"  {lab}: n {len(x)}  overnight total {x.r.mean()*1e4:+.1f}bp  minus SPY {x.ab.mean()*1e4:+.1f}bp "
                f"(t {x.ab.mean()/x.ab.std()*np.sqrt(len(x)):+.2f})  mean yield {x.yld.mean()*1e4:.0f}bp  implied drop ratio {pdr:.2f}")
        ok_all = []
        for cost in (2.5, "tier"):
            c = cost if cost == 2.5 else 5.0                       # large caps: tier = 5bp/side (price > $20, ADV > $50M)
            log(f"  [Roth cash, {cost}/side]")
            for E in SIZES:
                base = replay(s, Na, E, {}, c)
                r = replay(s, Na, E, ev, c)
                dlt = r - base
                half = [dlt[(dlt.index >= a) & (dlt.index <= z)].mean() * 25200 for _, a, z in
                        (("", "2021-01-01", "2023-12-31"), ("", "2024-01-01", "2026-12-31"))]
                t = nw_t(dlt.values)
                sims = np.array([(dlt.values * rng.choice([-1, 1], len(dlt))).mean() for _ in range(1000)])
                pct = float((sims < dlt.mean()).mean() * 100)
                sb, sr = B.stats(base), B.stats(r)
                ddd = (sr[2] - sb[2]) * 100
                pdd = p_dd50(r) if (E == 10000.0 and cost == 2.5) else None
                ok = half[0] > 0 and half[1] > 0 and t >= 2 and pct >= 95 and ddd >= -2 and (pdd is None or pdd <= 0.05)
                if cost == 2.5:
                    ok_all.append(ok)
                log(f"   ${E/1e3:5.1f}k base {sb[0]*100:5.1f}% -> {sr[0]*100:5.1f}%  inc {(sr[0]-sb[0])*100:+.2f}pp "
                    f"({half[0]:+.2f}/{half[1]:+.2f})  t {t:+.2f}  plac {pct:.0f}%  dDD {ddd:+.1f}"
                    + (f"  P(DD>50) {pdd:.1%}" if pdd is not None else "") + ("" if cost != 2.5 else f"  {'PASS' if ok else 'fail'}"))
        # matched placebo: same names, random non-ex nights 20-60 sessions away
        base = replay(s, Na, 10000.0, {}, 2.5)
        act = (replay(s, Na, 10000.0, ev, 2.5) - base).mean()
        cal = list(s.days); pos = {d: i for i, d in enumerate(cal)}
        Pc, Po = P["close"], P["open"]
        nxt = {a: b for a, b in zip(Pc.index[:-1], Pc.index[1:])}
        sims = []
        for _ in range(200):
            fake = {}
            for d, v in ev.items():
                if d not in pos:
                    continue
                for sym, _, yld, px in v:
                    j = pos[d] + int(rng.choice([-1, 1])) * int(rng.integers(20, 61))
                    if not 0 <= j < len(cal):
                        continue
                    dd = cal[j]; e = nxt.get(dd)
                    rr = Po.at[e, sym] / Pc.at[dd, sym] - 1 if e is not None else np.nan
                    if np.isfinite(rr) and abs(rr) < 0.5:
                        fake.setdefault(dd, []).append((sym, float(rr), yld, px))
            sims.append((replay(s, Na, 10000.0, fake, 2.5) - base).mean())
        pct = float((np.array(sims) < act).mean() * 100)
        q = dsr(replay(s, Na, 10000.0, ev, 2.5) - base, n_trials=N_TRIALS)
        log(f"  matched placebo (same names, random nights, 200): actual {act*25200:+.2f}pp/yr, pct {pct:.0f}%; DSR {q['dsr']:.3f}")
        ok_all.append(pct >= 95)
        verdict[k] = ok_all
    log("\n######## verdicts")
    for k, v in verdict.items():
        log(f"   {k}: {sum(v)}/{len(v)} checks pass -> {'SHADOW' if all(v) else 'DEAD'}")
    log(f"\ndone {time.time()-t0:.0f}s")
    fh.close()


if __name__ == "__main__":
    main()
