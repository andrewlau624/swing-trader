"""Study ATTN-OPEN: scheduled retail-attention events, first-night open pressure, official SIP crosses 2021-2026.

Pre-registration: "Amendment — Study ATTN-OPEN" in research/drafts/round1_prose.md (program N 847 -> 849).
Arms: D de-SPAC (first session under the operating company), T ticker change. Buy the closing cross on E-1 (old
symbol when the symbol changes), sell the opening cross on E. Raw minus SPY official overnight.

    PYTHONPATH=. .venv/bin/python -m research.sim.attn_open
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from exdiv_open import crosses, overnight  # noqa: E402
from lh_panel import Panel, cluster_t  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/exdiv"
OUT = pathlib.Path(__file__).resolve().parent / "attn_open_out.txt"


def main() -> None:
    lines: list[str] = []

    def log(s=""):
        print(s)
        lines.append(s)

    P = Panel.load()
    spy_on = overnight(crosses(json.load(open(D / "spy.json"))["SPY"]))
    rows = []
    for f in sorted(glob.glob(str(D / "attn" / "*.json"))):
        arm, t, d = pathlib.Path(f).stem.split("_")
        d = pd.Timestamp(d)
        v = json.load(open(f))
        new = crosses(v.get("new") or []) if v.get("new") else None
        if new is None or d not in new.index:
            continue
        old = crosses(v["old"]) if v.get("old") else pd.DataFrame(columns=["op", "os", "cp", "cs"], index=pd.DatetimeIndex([]))
        both = pd.concat([old[old.index < d], new[new.index >= d]])
        both = both[~both.index.duplicated(keep="last")].sort_index()
        prev = new[new.index < d]
        if len(prev):  # the new symbol already traded before E (vendor/tape mapping): use its own history
            both = new
        k = both.index.get_loc(d)
        if k < 1 or (both.index[k] - both.index[k - 1]).days > 5:
            continue
        c0 = both.cp.iloc[k - 1]
        g = P.row_at(t, d)
        if not (c0 >= 5) or g < 1 or P.dates[P.di[g]] != np.datetime64(d) or P.c[g - 1] * P.v[g - 1] < 1e6:
            continue
        r0 = both.op.iloc[k] / c0 - 1
        if abs(r0) > 1.0:  # symbol/ratio mismatch with the tape: data error, dropped
            continue
        r1 = both.op.iloc[k + 1] / both.cp.iloc[k] - 1 if k + 1 < len(both) else np.nan
        rows.append(dict(arm=arm, ticker=t, d=d, pnl=r0, pnl1=r1, d1=both.index[k + 1] if k + 1 < len(both) else pd.NaT,
                         ocs=both.os.iloc[k] * both.op.iloc[k], c0=c0, id_x=both.cp.iloc[k] / both.op.iloc[k] - 1))
    X = pd.DataFrame(rows)
    X["x"] = X.pnl - spy_on.reindex(X.d).to_numpy()
    X["x1"] = X.pnl1 - spy_on.reindex(X.d1).to_numpy()
    for arm, name in (("D", "de-SPAC"), ("T", "ticker change")):
        S = X[X.arm == arm].dropna(subset=["x"])
        log(f"ATTN-OPEN arm {arm} ({name}), official SIP crosses 2021-2026")
        if len(S) < 10:
            log(f"   n={len(S)} too few")
            continue
        g = S.d.dt.strftime("%Y-%m-%d")
        m, t = cluster_t(S.x, g)
        srt = np.sort(S.x.to_numpy())
        h1, h2 = S[S.d.dt.year <= 2023].x.mean(), S[S.d.dt.year >= 2024].x.mean()
        c5 = m - 0.001
        log(f"{arm}: n={len(S)} raw-SPY mean {m*1e4:+.1f}bp t {t:.2f} median {S.x.median()*1e4:+.1f}bp hit "
            f"{(S.x > 0).mean()*100:.0f}% ex-top5 {srt[:-5].mean()*1e4:+.1f}bp | halves 21-23 {h1*1e4:+.1f} 24-26 "
            f"{h2*1e4:+.1f} | 5bp/side {c5*1e4:+.1f}")
        checks = [m > 0 and t >= 2, h1 > 0 and h2 > 0, S.x.median() > 0, srt[:-5].mean() > 0, c5 > 0]
        verdict = "PASS" if all(checks) else ("FAIL" if (m <= 0 or t < 1) else "WEAK")
        log(f"   checks [t, halves, median, ex-top5, 5bp] = {checks} -> {verdict}")
        log(f"   T+1 night: mean {S.x1.mean()*1e4:+.1f}bp median {S.x1.median()*1e4:+.1f}bp | ex-day session "
            f"{S.id_x.mean()*1e4:+.1f}bp | open-cross $ median {S.ocs.median()/1e6:.2f}M p10 {S.ocs.quantile(.1)/1e3:.0f}k")
        log("   by year (n/mean/median bp): " + "; ".join(
            f"{y} {len(s)}/{s.x.mean()*1e4:+.0f}/{s.x.median()*1e4:+.0f}" for y, s in S.groupby(S.d.dt.year)))
    X.to_csv(D / "attn_open.csv", index=False)
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
