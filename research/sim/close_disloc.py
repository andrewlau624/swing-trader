"""Study CLOSE-DISLOC: passive limit-on-close buys that fill only on downward closing-cross dislocations.

Pre-registration: "Amendment — Study CLOSE-DISLOC" in research/drafts/round1_prose.md (program N 852 -> 853).

    PYTHONPATH=. .venv/bin/python -m research.sim.close_disloc
"""
from __future__ import annotations

import glob
import json
import pathlib
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .exdiv_open import crosses
from .lh_panel import cluster_t

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/close_disloc"
OUT = pathlib.Path(__file__).resolve().parent / "close_disloc_out.txt"
ET = ZoneInfo("America/New_York")


def preclose() -> pd.DataFrame:
    """(date, sym) -> price of the last 1-minute bar at or before 15:55 ET."""
    rows = []
    for f in sorted(glob.glob(str(D / "m_*.json"))):
        d = pathlib.Path(f).stem[2:]
        for sym, bars in json.load(open(f)).items():
            best = None
            for b in bars:
                t = pd.Timestamp(b["t"]).tz_convert(ET)
                if (t.hour, t.minute) <= (15, 55):
                    best = b["c"]
            if best:
                rows.append((pd.Timestamp(d), sym, best))
    return pd.DataFrame(rows, columns=["d", "sym", "p"])


def main() -> None:
    lines: list[str] = []

    def log(s=""):
        print(s)
        lines.append(s)

    A = {s: crosses(v) for s, v in json.load(open(D / "auctions.json")).items()}
    spy = A["SPY"]
    spy_on = (spy.op.shift(-1) / spy.cp - 1)  # indexed by the close date
    pc = preclose()
    rows = []
    for r in pc.itertuples():
        x = A.get(r.sym)
        if x is None or r.d not in x.index:
            continue
        k = x.index.get_loc(r.d)
        if k + 1 >= len(x):
            continue
        c, o = x.cp.iloc[k], x.op.iloc[k + 1]
        if not (c and o) or (x.index[k + 1] - r.d).days > 5:
            continue
        rows.append(dict(d=r.d, sym=r.sym, p=r.p, c=c, dev=c / r.p - 1, on=o / c - 1,
                         sess=(x.cp.iloc[k + 1] / o - 1), cs=(x.cs.iloc[k] or 0) * c))
    X = pd.DataFrame(rows)
    X["x"] = X.on - spy_on.reindex(X.d).to_numpy()
    X = X.dropna(subset=["x"])
    X = X[X.dev.abs() < 0.3]  # print errors
    log(f"CLOSE-DISLOC: {X.sym.nunique()} names, {X.d.nunique()} sessions, {len(X)} name-days; "
        f"cross vs 15:55 dev sd {X.dev.std()*1e4:.0f}bp")
    ctl = X[X.dev.abs() <= 0.002]
    log(f"   control (|dev| <= 0.2%): n {len(ctl)} overnight raw-SPY mean {ctl.x.mean()*1e4:+.1f}bp median {ctl.x.median()*1e4:+.1f}")
    for k in (0.005, 0.01, 0.02):
        F = X[X.dev <= -k]
        if len(F) < 10:
            log(f"k={k:.3f}: n={len(F)} too few")
            continue
        g = F.d.dt.strftime("%Y-%m-%d")
        m, t = cluster_t(F.x, g)
        srt = np.sort(F.x.to_numpy())
        h1 = F[F.d < "2025-07-01"].x.mean()
        h2 = F[F.d >= "2025-07-01"].x.mean()
        log(f"k={k:.3f}: fills {len(F)} ({len(F)/X.d.nunique():.2f}/session) overnight raw-SPY mean {m*1e4:+.1f}bp t {t:.2f} "
            f"median {F.x.median()*1e4:+.1f} hit {(F.x > 0).mean()*100:.0f}% ex-top5 {srt[:-5].mean()*1e4:+.1f} halves "
            f"{h1*1e4:+.1f} / {h2*1e4:+.1f} | next session {F.sess.mean()*1e4:+.1f}bp | cross $ median {F.cs.median()/1e6:.2f}M")
        if k == 0.01:
            checks = [m > 0 and t >= 2, h1 > 0 and h2 > 0, F.x.median() > 0, srt[:-5].mean() > 0, m > 0.001]
            verdict = "PASS" if all(checks) else ("FAIL" if (m <= 0 or t < 1) else "WEAK")
            log(f"   JUDGED k=1%: checks [t, halves, median, ex-top5, >10bp] = {checks} -> {verdict}")
    U = X[X.dev >= 0.01]
    log(f"   mirror (cross >= +1% above 15:55): n {len(U)} overnight raw-SPY mean {U.x.mean()*1e4:+.1f} median {U.x.median()*1e4:+.1f}")
    X.to_csv(D / "close_disloc.csv", index=False)
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
