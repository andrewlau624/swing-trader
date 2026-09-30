"""Study T: SEC offering filings on the shipped night picks.

    PYTHONPATH=. .venv/bin/python -m research.sim.night_filings fetch   # EDGAR -> cache
    PYTHONPATH=. .venv/bin/python -m research.sim.night_filings         # the study

Pre-registration: research/drafts/round1_prose.md, "Round 6" (commit ff5e7b9, stamped
before any Study T return or event count was computed).

Symbol -> CIK by EDGAR's entity index (exact ticker), kept only for entityType "operating"
with a periodic filing in the 400 days before the pick. Events are filings accepted in
(16:00 ET d-1, 15:40 ET d]: E1 424B*, E2 original S-1/S-3/F-1/F-3, E3 either.
"""
from __future__ import annotations

import json
import pathlib
import pickle
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from . import book as B

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/night/edgar"
OUT = ROOT / "data/research/program/night_filings_out.txt"
UA = {"User-Agent": "swing-trader research tool"}

PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))
FULL = ("2021-01-01", "2026-12-31")
PERIODIC = {"10-K", "10-Q", "20-F", "40-F", "6-K", "10-K/A", "10-Q/A"}
E2_FORMS = {"S-1", "S-3", "F-1", "F-3"}
SIZES = (2_300, 25_000, 100_000, 500_000)
N_PERM = 1000


def get(url: str, tries: int = 4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 ** k)
        except Exception:
            time.sleep(2 ** k)
    return None


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    syms = sorted({s for nd in N.values() for s in nd.syms})
    mp_f = CACHE / "ticker_cik.json"
    mp = json.loads(mp_f.read_text()) if mp_f.exists() else {}
    for i, s in enumerate(syms):
        if s in mp:
            continue
        q = s.replace(".", "-")
        r = get("https://efts.sec.gov/LATEST/search-index?keysTyped=" + urllib.parse.quote(q))
        cik = None
        for h in (r or {}).get("hits", {}).get("hits", []):
            tick = [t.strip().upper() for t in (h["_source"].get("tickers") or "").split(",")]
            if q.upper() in tick:
                cik = h["_id"]
                break
        mp[s] = cik
        if i % 100 == 0:
            print(f"map {i}/{len(syms)}", flush=True)
            mp_f.write_text(json.dumps(mp))
        time.sleep(0.12)
    mp_f.write_text(json.dumps(mp))
    ciks = sorted({c for c in mp.values() if c})
    print(f"mapped {sum(1 for c in mp.values() if c)}/{len(syms)} symbols, {len(ciks)} CIKs")
    for i, c in enumerate(ciks):
        f = CACHE / f"{int(c):010d}.pkl"
        if f.exists():
            continue
        j = get(f"https://data.sec.gov/submissions/CIK{int(c):010d}.json")
        time.sleep(0.12)
        if j is None:
            continue
        frames = [pd.DataFrame(j["filings"]["recent"])]
        for extra in j["filings"].get("files", []):
            if extra.get("filingTo", "9999") < "2019-06-01":
                continue
            x = get("https://data.sec.gov/submissions/" + extra["name"])
            time.sleep(0.12)
            if x is not None:
                frames.append(pd.DataFrame(x))
        fl = pd.concat(frames, ignore_index=True)[["form", "filingDate", "acceptanceDateTime"]]
        pickle.dump({"entityType": j.get("entityType"), "sic": j.get("sic"), "filings": fl},
                    open(f, "wb"))
        if i % 100 == 0:
            print(f"submissions {i}/{len(ciks)}", flush=True)
    print("fetch done")


def clustered_t(x: np.ndarray, g: np.ndarray) -> float:
    x = np.asarray(x, float)
    if len(x) < 10:
        return float("nan")
    e = pd.Series(x - x.mean()).groupby(g).sum().values
    se = np.sqrt((e ** 2).sum()) / len(x)
    return x.mean() / se if se > 0 else float("nan")


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study T: SEC offering filings on the night picks, started", pd.Timestamp.now(), "\n")
    N = B.night_days(raw_price=True, max_corr=0.7)
    mp = json.loads((CACHE / "ticker_cik.json").read_text())
    subs = {}
    for c in {c for c in mp.values() if c}:
        f = CACHE / f"{int(c):010d}.pkl"
        if f.exists():
            subs[c] = pickle.load(open(f, "rb"))

    # ---- timezone check: EDGAR moves filings accepted after 17:30 ET to the next filingDate.
    acc_all = pd.concat([s["filings"] for s in subs.values()], ignore_index=True)
    acc_all = acc_all[acc_all.acceptanceDateTime.str.len() > 10]
    ts = pd.to_datetime(acc_all.acceptanceDateTime, utc=True)
    same = ts.dt.strftime("%Y-%m-%d").values == acc_all.filingDate.values
    for lab, hh in (("as UTC", ts.dt.tz_convert("America/New_York").dt.hour),
                    ("as ET-labelled-Z", ts.dt.hour)):
        late = (hh.values >= 18) & same
        log(f"timezone check, read {lab}: filings after 18:00 still on the same filingDate "
            f"{late.mean():.2%}")
    # decide: the reading under which late same-day filings are ~absent is the true one
    h_utc = ts.dt.tz_convert("America/New_York")
    h_raw = ts.dt.tz_localize(None).dt.tz_localize("America/New_York")
    bad_utc = ((h_utc.dt.hour.values >= 18) & (h_utc.dt.strftime("%Y-%m-%d").values
                                                == acc_all.filingDate.values)).mean()
    bad_raw = ((h_raw.dt.hour.values >= 18) & same).mean()
    et_is_raw = bad_raw < bad_utc
    log(f"-> acceptanceDateTime is {'ET labelled Z' if et_is_raw else 'true UTC'}\n")

    def to_et(s: pd.Series) -> pd.Series:
        t = pd.to_datetime(s, utc=True)
        return (t.dt.tz_localize(None).dt.tz_localize("America/New_York") if et_is_raw
                else t.dt.tz_convert("America/New_York"))

    ev = {}
    for c, s in subs.items():
        fl = s["filings"]
        fl = fl[fl.acceptanceDateTime.str.len() > 10].copy()
        fl["t"] = to_et(fl.acceptanceDateTime)
        ev[c] = fl

    # bug fix after the first run (pre-reg intent: ETPs excluded): ETN issuers (Bank of
    # Montreal files ~2,500 424B/yr for its structured notes, so FNGD/BULZ/BNKU matched
    # every night) and commodity pools (SIC 6221, e.g. KOLD) are "operating" entities.
    etp = {c for c, s in subs.items() if s.get("sic") == "6221"
           or (ev[c].form.str.startswith("424B") & (ev[c].t >= "2021-01-01")).sum() / 5.75 > 100}
    log(f"ETP issuers excluded (SIC 6221 or > 100 424B/yr): {len(etp)}\n")
    days = pd.DatetimeIndex(sorted(N))
    prv = {d: days[i - 1] for i, d in enumerate(days) if i > 0}
    # the previous SESSION, not the previous pick day: use the return-panel index
    R = B.D.returns20()
    sess = R.index
    prev_sess = {d: sess[i - 1] for i, d in enumerate(sess) if i > 0}

    rows = []
    for d, nd in N.items():
        d = pd.Timestamp(d)
        p = prev_sess.get(d, prv.get(d))
        lo = pd.Timestamp(f"{p.date()} 16:00", tz="America/New_York")
        hi = pd.Timestamp(f"{d.date()} 15:40", tz="America/New_York")
        for j, sym in enumerate(nd.syms):
            c = mp.get(sym)
            r = dict(d=d, sym=sym, ret=nd.ret[j], price=nd.price[j], adv=nd.adv[j],
                     frac=nd.frac, mapped=False, E1=False, E2=False)
            if c and c in ev and subs[c]["entityType"] == "operating" and c not in etp:
                fl = ev[c]
                per = fl[fl.form.isin(PERIODIC) & (fl.t < hi) & (fl.t >= hi - pd.Timedelta(days=400))]
                if len(per):
                    r["mapped"] = True
                    w = fl[(fl.t > lo) & (fl.t <= hi)]
                    r["E1"] = bool(w.form.str.startswith("424B").any())
                    r["E2"] = bool(w.form.isin(E2_FORMS).any())
            rows.append(r)
    T = pd.DataFrame(rows)
    T["E3"] = T.E1 | T.E2
    log(f"picks {len(T)}; mapped {T.mapped.mean():.0%} "
        f"({T.mapped.sum()}); by year: "
        + ", ".join(f"{y} {g.mapped.mean():.0%}" for y, g in T.groupby(T.d.dt.year)))
    M = T[T.mapped].copy()
    for e in ("E1", "E2", "E3"):
        log(f"  {e}: {M[e].sum()} event picks ({M[e].mean():.1%} of mapped); by half "
            + ", ".join(f"{lab} {M[(M.d >= a) & (M.d <= b)][e].sum()}" for lab, a, b in PER))
    log("  (no 2016-20 holdout: the V7 pool starts 2020-11)\n")

    alld = sess[(sess >= FULL[0]) & (sess <= FULL[1])]
    rng = np.random.default_rng(7)
    verdict = {}
    for cost in ("tier", "tier_hi"):
        T["net"] = T.ret - 2 * B.cost_bps(cost, T.price.values, T.adv.values) / 1e4
        # excess vs the other picks the same night (all picks, mapped or not, form the night)
        g = T.groupby("d").net
        n_ = g.transform("size")
        T["exc"] = np.where(n_ >= 2, (T.net - (g.transform("sum") - T.net) / (n_ - 1).clip(1)),
                            np.nan)
        M = T[T.mapped & (T.d >= FULL[0])].copy()
        log(f"## cost {cost}")
        log(f"  mapped picks mean net {M.net.mean() * 1e4:+.1f}bp; unmapped "
            f"{T[~T.mapped & (T.d >= FULL[0])].net.mean() * 1e4:+.1f}bp")
        for e in ("E1", "E2", "E3"):
            m = M[M[e] & M.exc.notna()]
            hv = []
            for lab, a, b in PER:
                h = m[(m.d >= a) & (m.d <= b)]
                hv.append((h.exc.mean() * 1e4, len(h), h.net.mean() * 1e4))
            t = clustered_t(m.exc.values, m.d.values)
            # within-night permutation of the label among mapped picks
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
            log(f"  {e}: excess bp 2021-23 {hv[0][0]:+7.1f} (n {hv[0][1]:4d}, raw {hv[0][2]:+6.1f})"
                f"  2024-26 {hv[1][0]:+7.1f} (n {hv[1][1]:4d}, raw {hv[1][2]:+6.1f})"
                f"  t {t:+5.2f}  perm pct {pct:4.1f}")
            # book: baseline vs rule
            def book(wfun):
                w = np.minimum(T.frac.values, 0.10)
                w = wfun(w)
                inc = pd.Series(0.5 * w * T.net.values).groupby(T.d.values).sum()
                return inc.reindex(alld).fillna(0)
            base = book(lambda w: w)
            isev = (T.mapped & T[e]).values
            rules = {"DROP": lambda w: np.where(isev, 0.0, w),
                     "DOUBLE": lambda w: np.where(isev, np.minimum(2 * w, 0.10), w)}
            for rname, f in rules.items():
                diff = book(f) - base
                yr = [diff[a:b].sum() / (len(diff[a:b]) / 252) * 100 for _, a, b in PER]
                sign = -1 if rname == "DROP" else 1
                n_ev = int((M[e]).sum())
                ok = (n_ev >= 100 and all(np.sign(h[0]) == sign for h in hv)
                      and sign * t >= 2.0
                      and (pct >= 97.5 if sign > 0 else pct <= 2.5)
                      and all(y > 0 for y in yr))
                verdict.setdefault(f"{e} {rname}", []).append(ok)
                log(f"      {rname:6s} book vs baseline pp/yr 2021-23 {yr[0]:+.3f}  "
                    f"2024-26 {yr[1]:+.3f}  {'PASS' if ok else ''}")
        log("")

    log("## capacity: event picks' order size as % of 20d ADV (night leg 0.5 of equity x frac)")
    E = T[T.mapped & T.E3 & (T.d >= FULL[0])]
    for sz in SIZES:
        pct_adv = 0.5 * sz * np.minimum(E.frac, 0.10) / E.adv * 100
        allp = T[T.d >= FULL[0]]
        pa = 0.5 * sz * np.minimum(allp.frac, 0.10) / allp.adv * 100
        log(f"  ${sz:>7,}: event picks median {np.nanmedian(pct_adv):.3f}% ADV "
            f"(p95 {np.nanpercentile(pct_adv, 95):.3f}%); all picks median "
            f"{np.nanmedian(pa):.3f}% (p95 {np.nanpercentile(pa, 95):.3f}%)")

    log("\n## verdict (pass at tier AND tier_hi)")
    for k, v in verdict.items():
        log(f"  {k:10s} {'PASS' if all(v) else 'fail'}")
    T.to_pickle(ROOT / "data/research/program/night_filings_table.pkl")
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    fetch() if sys.argv[1:] == ["fetch"] else main()
