"""Study THR runner (pre-reg research/drafts/study_threshold_flow.md).

FTD-derived Reg SHO threshold episodes -> is there a predictable forced-buy window?

Run: PYTHONPATH=. .venv/bin/python -m research.sim.threshold_flow
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import data as D
from . import jump_ftd as JF

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/threshold_flow_out.txt"


def episodes() -> pd.DataFrame:
    F = JF.ftd()[["date", "sym", "frac", "qty"]].dropna(subset=["frac"])
    F = F[(F.frac >= 0.005) & (F.qty >= 10000)].sort_values(["sym", "date"])
    cal = np.array(sorted(F.date.unique()))
    ci = {d: i for i, d in enumerate(cal)}
    F = F.assign(ci=F.date.map(ci))
    rows = []
    for sym, g in F.groupby("sym"):
        v = g.ci.values
        br = np.r_[0, np.where(np.diff(v) != 1)[0] + 1, len(v)]
        for a, b in zip(br[:-1], br[1:]):
            if b - a >= 5:
                ls_i = v[a] + 4                          # 5th consecutive threshold day = list start
                dl_i = min(ls_i + 13, len(cal) - 1)
                rows.append((sym, cal[ls_i], cal[dl_i], b - a))
    return pd.DataFrame(rows, columns=["sym", "list_start", "deadline", "run"])


def main():
    ep = episodes()
    ep = ep[ep.list_start >= pd.Timestamp("2021-01-01")]          # panel window
    P = D.panel()
    O, C, V = P["open"], P["close"], P["volume"]
    days = C.index
    ret = C.pct_change(fill_method=None)
    mkt = ret.mean(axis=1)

    def td(d):  # first trading day >= d (by date)
        j = days.searchsorted(d)
        return j if j < len(days) else None

    recs = []
    for sym, ls, dl, run in ep.itertuples(index=False):
        if sym not in C.columns:
            continue
        e = td(ls + pd.Timedelta(days=1))
        if e is None:
            continue
        d0 = td(dl)
        if d0 is None or d0 <= e:
            continue
        px = C[sym]
        if not (np.isfinite(px.iloc[e]) and np.isfinite(O[sym].iloc[e]) and np.isfinite(px.iloc[d0])):
            continue
        entry = O[sym].iloc[e]
        if not np.isfinite(entry) or entry <= 0:
            continue
        r_dl = px.iloc[d0] / entry - 1
        r4 = px.iloc[min(e + 4, len(days) - 1)] / entry - 1
        r8 = px.iloc[min(e + 8, len(days) - 1)] / entry - 1
        m_dl = (1 + mkt.iloc[e:d0 + 1]).prod() - 1
        # volume footprint: mean daily $vol in window vs 20d ADV at entry
        adv = (C[sym] * V[sym]).rolling(20).mean().shift(1).iloc[e]
        win_v = (C[sym] * V[sym]).iloc[e:d0 + 1].mean()
        vrat = win_v / adv if adv and np.isfinite(adv) and adv > 0 else np.nan
        # last-3-sessions-into-deadline abnormal
        a3 = days[max(0, d0 - 3)]
        r_last3 = px.iloc[d0] / px.iloc[max(0, d0 - 3)] - 1
        m3 = (1 + mkt.iloc[max(0, d0 - 3):d0 + 1]).prod() - 1
        # overnight vs intraday over the window
        on = (O[sym].iloc[e:d0 + 1].values / C[sym].shift(1).iloc[e:d0 + 1].values - 1)
        idr = (C[sym].iloc[e:d0 + 1].values / O[sym].iloc[e:d0 + 1].values - 1)
        recs.append(dict(sym=sym, list_start=ls, entry=days[e], deadline=days[d0], run=run,
                         r_dl=r_dl, abn=r_dl - m_dl, r4=r4, r8=r8, vrat=vrat,
                         abn_last3=r_last3 - m3, on=np.nansum(on), idr=np.nansum(idr)))
    R = pd.DataFrame(recs)
    if R.empty:
        print("no episodes"); return
    b = 1e4
    lines = ["Study THR: Reg SHO threshold forced-buy window (FTD-derived, panel 2021-2026)",
             f"episodes={len(R)}  symbols={R.sym.nunique()}  (survivorship-limited panel)", ""]
    for lab, col in [("CAR to deadline", "abn"), ("3 sessions into deadline", "abn_last3")]:
        x = R[col].dropna().sort_values()
        if len(x) < 10:
            continue
        t = x.mean() / x.std() * np.sqrt(len(x))
        lines.append(f"{lab:26s}: n={len(x):4d} mean={x.mean()*b:6.1f}bp med={x.median()*b:6.1f} "
                     f"t={t:5.2f} hit={(x>0).mean()*100:3.0f}% ex5={x.iloc[:-5].mean()*b:6.1f}")
    for lab, col in [("entry->+4 raw", "r4"), ("entry->+8 raw", "r8")]:
        x = R[col].dropna()
        lines.append(f"{lab:26s}: n={len(x):4d} mean={x.mean()*b:6.1f}bp med={x.median()*b:6.1f}")
    lines.append(f"\nvolume footprint (window $vol / 20d ADV at entry): "
                 f"median={np.nanmedian(R['vrat']):.2f}x  mean={np.nanmean(R['vrat']):.2f}x")
    lines.append(f"window split: overnight mean={R['on'].mean()*b:.1f}bp  intraday mean={R['idr'].mean()*b:.1f}bp")
    # net after 50bp round trip
    net = R["abn"].dropna() - 50 / b
    lines.append(f"\nlong-only net of 50bp round trip: mean={net.mean()*b:.1f}bp "
                 f"hit={(net>0).mean()*100:.0f}% n={len(net)}")
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
