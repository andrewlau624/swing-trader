"""Reddit round R1: 8-K "bad-news" items (5.02 / 4.02 / 4.01 / 3.01) on the night picks -> DROP.

    PYTHONPATH=. .venv/bin/python -m research.sim.reddit_8k fetch   # EDGAR submissions with 8-K items -> cache
    PYTHONPATH=. .venv/bin/python -m research.sim.reddit_8k         # the study

Pre-registration: research/drafts/study_reddit_round.md (commit 96c777d, before any outcome).
Reuses Study T's ticker->CIK map, operating/periodic-filer filter, ETP exclusion and pass bar.
"""
from __future__ import annotations

import json
import pickle
import sys
import time

import numpy as np
import pandas as pd

from . import book as B
from .night_filings import CACHE as T_CACHE, PERIODIC, PER, FULL, N_PERM, clustered_t, get

ROOT = B.ROOT if hasattr(B, "ROOT") else T_CACHE.parents[3]
CACHE = T_CACHE.parent / "edgar_items"
OUT = T_CACHE.parents[1] / "program/reddit_8k_out.txt"
BAD = {"5.02", "4.02", "4.01", "3.01"}


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    mp = json.loads((T_CACHE / "ticker_cik.json").read_text())
    ciks = sorted({c for c in mp.values() if c})
    for i, c in enumerate(ciks):
        f = CACHE / f"{int(c):010d}.pkl"
        if f.exists():
            continue
        j = get(f"https://data.sec.gov/submissions/CIK{int(c):010d}.json")
        time.sleep(0.11)
        if j is None:
            continue
        frames = [pd.DataFrame(j["filings"]["recent"])]
        for extra in j["filings"].get("files", []):
            if extra.get("filingTo", "9999") < "2020-06-01":
                continue
            x = get("https://data.sec.gov/submissions/" + extra["name"])
            time.sleep(0.11)
            if x is not None:
                frames.append(pd.DataFrame(x))
        fl = pd.concat(frames, ignore_index=True)
        if "items" not in fl:
            fl["items"] = ""
        fl = fl[["form", "filingDate", "acceptanceDateTime", "items"]]
        pickle.dump({"entityType": j.get("entityType"), "sic": j.get("sic"), "filings": fl}, open(f, "wb"))
        if i % 100 == 0:
            print(f"submissions {i}/{len(ciks)}", flush=True)
    print("fetch done")


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Reddit R1: 8-K bad-news items on the night picks, started", pd.Timestamp.now(), "\n")
    N = B.night_days(raw_price=True, max_corr=0.7)
    mp = json.loads((T_CACHE / "ticker_cik.json").read_text())
    subs = {}
    for c in {c for c in mp.values() if c}:
        f = CACHE / f"{int(c):010d}.pkl"
        if f.exists():
            subs[c] = pickle.load(open(f, "rb"))
    log(f"CIKs with item data: {len(subs)} / {len({c for c in mp.values() if c})}")

    # Study T established acceptanceDateTime is ET labelled 'Z' (its timezone check); re-check here.
    acc = pd.concat([s["filings"] for s in subs.values()], ignore_index=True)
    acc = acc[acc.acceptanceDateTime.str.len() > 10]
    ts = pd.to_datetime(acc.acceptanceDateTime, utc=True)
    h_utc = ts.dt.tz_convert("America/New_York")
    h_raw = ts.dt.tz_localize(None).dt.tz_localize("America/New_York")
    bad_utc = ((h_utc.dt.hour.values >= 18) & (h_utc.dt.strftime("%Y-%m-%d").values == acc.filingDate.values)).mean()
    bad_raw = ((h_raw.dt.hour.values >= 18) & (h_raw.dt.strftime("%Y-%m-%d").values == acc.filingDate.values)).mean()
    et_is_raw = bad_raw < bad_utc
    log(f"acceptanceDateTime read as {'ET labelled Z' if et_is_raw else 'true UTC'} "
        f"(late same-day share raw {bad_raw:.2%} vs utc {bad_utc:.2%})\n")

    def to_et(s):
        t = pd.to_datetime(s, utc=True)
        return (t.dt.tz_localize(None).dt.tz_localize("America/New_York") if et_is_raw
                else t.dt.tz_convert("America/New_York"))

    ev, bad8k = {}, {}
    for c, s in subs.items():
        fl = s["filings"]
        fl = fl[fl.acceptanceDateTime.str.len() > 10].copy()
        fl["t"] = to_et(fl.acceptanceDateTime)
        ev[c] = fl
        k = fl[fl.form.isin(["8-K", "8-K/A"])]
        hit = [bool({x.strip() for x in str(v or "").split(",")} & BAD) for v in k["items"]]
        bad8k[c] = pd.DatetimeIndex(k.t[hit].sort_values())
    etp = {c for c, s in subs.items() if s.get("sic") == "6221"
           or (ev[c].form.str.startswith("424B") & (ev[c].t >= "2021-01-01")).sum() / 5.75 > 100}
    R = B.D.returns20()
    sess = R.index
    pos = {d: i for i, d in enumerate(sess)}

    rows = []
    for d, nd in N.items():
        d = pd.Timestamp(d)
        i = pos.get(d)
        if i is None or i < 6:
            continue
        hi = pd.Timestamp(f"{d.date()} 15:40", tz="America/New_York")
        lo1 = pd.Timestamp(f"{sess[i - 1].date()} 16:00", tz="America/New_York")
        lo5 = pd.Timestamp(f"{sess[i - 5].date()} 16:00", tz="America/New_York")
        for j, sym in enumerate(nd.syms):
            c = mp.get(sym)
            r = dict(d=d, sym=sym, ret=nd.ret[j], price=nd.price[j], adv=nd.adv[j], frac=nd.frac,
                     mapped=False, R1a=False, R1b=False)
            if c and c in ev and subs[c]["entityType"] == "operating" and c not in etp:
                fl = ev[c]
                per = fl[fl.form.isin(PERIODIC) & (fl.t < hi) & (fl.t >= hi - pd.Timedelta(days=400))]
                if len(per):
                    r["mapped"] = True
                    b = bad8k[c]
                    if len(b):
                        bt = b
                        r["R1a"] = bool(((bt > lo1) & (bt <= hi)).any())
                        r["R1b"] = bool(((bt > lo5) & (bt <= hi)).any())
            rows.append(r)
    T = pd.DataFrame(rows)
    log(f"picks {len(T)}; mapped {T.mapped.mean():.0%}")
    M = T[T.mapped]
    for e in ("R1a", "R1b"):
        log(f"  {e}: {M[e].sum()} tagged picks; by half "
            + ", ".join(f"{lab} {M[(M.d >= a) & (M.d <= b)][e].sum()}" for lab, a, b in PER))
    log("")

    alld = sess[(sess >= FULL[0]) & (sess <= FULL[1])]
    rng = np.random.default_rng(7)
    verdict = {}
    for cost in ("tier", "tier_hi"):
        T["net"] = T.ret - 2 * B.cost_bps(cost, T.price.values, T.adv.values) / 1e4
        g = T.groupby("d").net
        n_ = g.transform("size")
        T["exc"] = np.where(n_ >= 2, (T.net - (g.transform("sum") - T.net) / (n_ - 1).clip(1)), np.nan)
        M = T[T.mapped & (T.d >= FULL[0])].copy()
        log(f"## cost {cost}")
        for e in ("R1a", "R1b"):
            m = M[M[e] & M.exc.notna()]
            hv = []
            for lab, a, b in PER:
                h = m[(m.d >= a) & (m.d <= b)]
                hv.append((h.exc.mean() * 1e4, len(h), h.net.mean() * 1e4))
            t = clustered_t(m.exc.values, m.d.values)
            Mx = M[M.exc.notna()].reset_index(drop=True)
            lab_ = Mx[e].values
            grp = Mx.groupby("d").indices
            real = Mx.exc[lab_].mean()
            draws = np.empty(N_PERM)
            for k in range(N_PERM):
                perm = lab_.copy()
                for ix in grp.values():
                    if len(ix) > 1:
                        perm[ix] = perm[rng.permutation(ix)]
                draws[k] = Mx.exc[perm].mean() if perm.any() else np.nan
            pct = (draws < real).mean() * 100

            def book(wfun):
                w = wfun(np.minimum(T.frac.values, 0.10))
                inc = pd.Series(0.5 * w * T.net.values).groupby(T.d.values).sum()
                return inc.reindex(alld).fillna(0)
            isev = (T.mapped & T[e]).values
            diff = book(lambda w: np.where(isev, 0.0, w)) - book(lambda w: w)
            yr = [diff[a:b].sum() / (len(diff[a:b]) / 252) * 100 for _, a, b in PER]
            n_ev = int(M[e].sum())
            ok = (n_ev >= 100 and all(h[0] < 0 for h in hv) and t <= -2.0 and pct <= 2.5
                  and all(y > 0 for y in yr))
            verdict.setdefault(e, []).append(ok)
            log(f"  {e}: excess bp 2021-23 {hv[0][0]:+7.1f} (n {hv[0][1]:4d}, raw {hv[0][2]:+6.1f})"
                f"  2024-26 {hv[1][0]:+7.1f} (n {hv[1][1]:4d}, raw {hv[1][2]:+6.1f})  t {t:+5.2f}"
                f"  perm pct {pct:4.1f}  DROP pp/yr {yr[0]:+.3f} / {yr[1]:+.3f}  {'PASS' if ok else ''}")
        log("")
    log("## verdict (pass at tier AND tier_hi)")
    for k, v in verdict.items():
        log(f"  {k}: {'PASS' if all(v) else 'fail'}")
    T.to_pickle(OUT.parent / "reddit_8k_table.pkl")
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    fetch() if sys.argv[1:] == ["fetch"] else main()
