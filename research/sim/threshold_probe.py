"""PHASE 5 probe: Reg SHO threshold securities and the 13-day close-out (forced buying).

The jump hunt tested FTD *spikes* (R3-2) and *collapses* (R3-16) as return signals and
killed them. This is a different, untested mechanism: a security on the Reg SHO
threshold list (aggregate fails >= 0.5% of shares for 5 consecutive settlement days)
must have its fails closed out within 13 consecutive settlement days. That is a
mandated forced BUY by the failing broker, with a known deadline.

Test: from SEC FTD (cached 2015+, `jump_ftd.ftd`, frac = fails/shares from XBRL),
find threshold episodes (>=5 consecutive settlement days with frac >= 0.5%), then
measure the abnormal return from the episode's first day to the 13-settlement-day
deadline, and in the 3 days into the deadline. Abnormal = episode return minus the
equal-weight panel return over the same window.

Caveat: bars from `panel.pkl` (2020-10+) -> episodes 2021+ only; survivorship-limited.
A null here does not prove the mechanism false; it tests the tradable window.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.threshold_probe
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import data as D
from . import jump_ftd as JF

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/threshold_probe_out.txt"


def episodes() -> pd.DataFrame:
    F = JF.ftd()[["date", "sym", "frac", "file", "pub"]].dropna()
    cal = np.array(sorted(F.date.unique()))
    idx = {d: i for i, d in enumerate(cal)}
    X = F[F.frac >= 0.005].copy().sort_values(["sym", "date"])
    # publication date per (file): when the market could first know that settlement day
    pub_of = F.groupby("file").pub.first().to_dict()
    X["file"] = X["file"].astype(str)
    X["ci"] = X.date.map(idx)
    rows = []
    for sym, g in X.groupby("sym"):
        cis = g.ci.values
        files = g["file"].values
        breaks = np.r_[0, np.where(np.diff(cis) != 1)[0] + 1, len(cis)]
        for a, b in zip(breaks[:-1], breaks[1:]):
            if b - a >= 5:
                t0_ci = cis[a]
                dl_ci = min(t0_ci + 13, len(cal) - 1)
                # public only when the file containing the CONFIRMING (last) threshold day is out
                pub = pub_of.get(files[b - 1], F.pub.max())
                rows.append((sym, cal[t0_ci], cal[dl_ci], pub, b - a))
    return pd.DataFrame(rows, columns=["sym", "t0", "deadline", "pub", "run"])


def main():
    ep = episodes()
    ep = ep[ep.t0 >= pd.Timestamp("2021-01-01")]
    P = D.panel()
    C = P["close"]
    days = C.index
    # equal-weight panel return over a window (benchmark)
    ret = C.pct_change(fill_method=None)
    mkt = ret.mean(axis=1)          # per-day cross-sectional mean

    def td(d):  # first trading day >= d
        j = days.searchsorted(d)
        return days[j] if j < len(days) else None

    def fwd(mode):
        recs = []
        for sym, t0, dl, pub, run in ep[["sym", "t0", "deadline", "pub", "run"]].itertuples(index=False):
            if sym not in C.columns:
                continue
            if mode == "lookahead_to_deadline":
                a, b = td(t0), td(dl)
            else:  # honest: enter only when the file is public (pub is the entry date)
                j = days.searchsorted(pub)
                if j >= len(days):
                    continue
                a = days[j]
                k = {"pub_fwd5": 5, "pub_fwd10": 10, "pub_to_deadline": None}[mode]
                if k is None:
                    b = td(dl)
                else:
                    b = days[min(j + k, len(days) - 1)]
            if a is None or b is None or b <= a:
                continue
            px = C[sym].reindex([a, b]).dropna()
            if len(px) < 2:
                continue
            r = px.iloc[1] / px.iloc[0] - 1
            mb = (1 + mkt.loc[a:b]).prod() - 1
            recs.append((sym, a, b, r, r - mb, run))
        return pd.DataFrame(recs, columns=["sym", "a", "b", "ret", "abn", "run"])

    lines = ["Reg SHO threshold close-out probe (forced buy-in by settlement day 13)",
             f"episodes>=2021: {len(ep)}  symbols {ep.sym.nunique()}",
             "lookahead row uses the settlement date; honest rows enter at the FTD file's",
             "publication date (SEC posts each file ~20 days after its last settlement day).", ""]
    for mode, lab in [("lookahead_to_deadline", "LOOKAHEAD t0 -> deadline (not tradable)"),
                      ("pub_to_deadline", "pub -> deadline (deadline may already be past)"),
                      ("pub_fwd5", "publication + 5 sessions"),
                      ("pub_fwd10", "publication + 10 sessions")]:
        T = fwd(mode)
        T = T[T["ret"].abs() < 1.0]
        n = len(T)
        if n < 10:
            lines.append(f"{lab}: n={n} (too few)"); continue
        t = T["abn"].mean() / T["abn"].std() * np.sqrt(n)
        ex5 = T["abn"].sort_values().iloc[:-5].mean()
        lines.append(f"{lab}: n={n} raw={T['ret'].mean()*100:6.2f}% abn={T['abn'].mean()*100:6.2f}% "
                     f"med={T['abn'].median()*100:6.2f}% t={t:5.2f} hit={(T['abn']>0).mean()*100:3.0f}% "
                     f"ex5={ex5*100:6.2f}%")
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
