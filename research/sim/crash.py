"""Addendum 18: does the book survive a crash, and what makes it survive?

    .venv/bin/python -m research.sim.crash

Night leg, two data sets, one code path (swingtrader.daily.signals):
  2020      daily bars (data/research/night/panel2020.pkl). The signal is
            computed from the CLOSE, which the live bot cannot see at 15:40;
            on the 2021-26 overlap that version runs +9bp/day above the
            honest one, so 2020 results are shown bias-corrected as well.
  2020-11+  the honest 15:50 candidates (night_trades.v2).
IBS and intraday legs come from the simulator back to 2016.

Candidate protections were fixed from the economics of the 2020-03-06
failure, not searched: five oil producers were one bet (theme dedupe), a
selloff two weeks deep was not "crowded" by today's count alone (stress
memory), and the loss landed over a weekend (gap exposure).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .validate import load_sim

COST = 10.0          # bps per side, both data sets (flat, for comparability)
EPISODES = {
    "2018 Q4 selloff": ("2018-10-01", "2018-12-24"),
    "COVID crash": ("2020-02-19", "2020-03-23"),
    "COVID rebound": ("2020-03-24", "2020-06-08"),
    "2022 bear": ("2022-01-03", "2022-10-12"),
    "Aug 2024 unwind": ("2024-07-16", "2024-08-05"),
    "Apr 2025 tariffs": ("2025-02-19", "2025-04-08"),
}


# ------------------------------------------------ night leg, per day
def days_2020(max_corr=0.9):
    """Close-signal night candidates from the 2020 daily panel, through the
    live picking functions. Returns {date: (rets, vol20, day_ret, n_raw, next_gap_days)}."""
    P = pd.read_pickle(D.DATA / "panel2020.pkl")
    O, H, L, C, V = (P[k] for k in ["open", "high", "low", "close", "volume"])
    R = C.pct_change(fill_method=None)
    adv = (C * V).rolling(20).mean().shift(1)
    vol20 = R.rolling(20).std().shift(1) * np.sqrt(252)
    nxt = O.shift(-1) / C - 1
    idx = C.index
    out = {}
    for i in range(21, len(idx) - 1):
        d = idx[i]
        rows = pd.DataFrame({"price": C.iloc[i], "prev_close": C.iloc[i - 1],
                             "high": H.iloc[i], "low": L.iloc[i]})
        ok = (adv.iloc[i] >= 1e7) & nxt.iloc[i].abs().le(1)
        picks = sg.loser_picks(rows[ok.reindex(rows.index, fill_value=False)].dropna(),
                               day_ret_max=-0.08, ibs_max=0.10, price_min=5, price_max=2000)
        if picks.empty:
            continue
        win = R.iloc[i - 20:i][picks.index]
        picks, _ = sg.dedupe_correlated(picks, {s: win[s].dropna().tolist() for s in picks.index},
                                        max_corr)
        out[d] = (nxt.iloc[i][picks.index].values, vol20.iloc[i][picks.index].values,
                  picks.day_ret.values, len(picks), (idx[i + 1] - d).days)
    return out


def days_honest(max_corr=0.9):
    N = B.night_days(max_corr=max_corr, vol_min=0.0)     # vol filter applied below, same as 2020
    idx = D.panel()["close"].index
    nxt = {d: (idx[idx > d][0] - d).days if (idx > d).any() else 1 for d in N}
    return {d: (n.ret, n.vol20, n.day_ret, n.n_raw, nxt[d]) for d, n in N.items()}


def night_series(days: dict, *, stress_memory=0, weekend=1.0, stress_scale=None,
                 spy_vol=None, tilt=True) -> pd.Series:
    """Daily night-leg return at unit weight (the leg's own capital).
    stress_memory: crowding counts max(today, mean of the last k days' signals)
    weekend:       exposure multiplier when the position is held > 1 calendar night
    stress_scale:  exposure multiplier while SPY's 20d realised vol > 30%/yr"""
    ds = sorted(days)
    hist = []
    out = {}
    for d in ds:
        ret, vol20, day_ret, n_raw, gap = days[d]
        n_eff = n_raw
        if stress_memory:
            prev = hist[-stress_memory:]
            n_eff = max(n_raw, np.mean(prev) if prev else 0)
        hist.append(n_raw)
        keep = np.nan_to_num(vol20) >= 0.6
        if not keep.any():
            out[d] = 0.0; continue
        r, v, dr = ret[keep], vol20[keep], day_ret[keep]
        per = min(1 / len(r), 0.10) * min(1.0, 30 / max(n_eff, 1))
        w = sg.night_tilt(v, dr) if tilt else np.ones(len(r))
        x = per * w
        if gap > 1:
            x = x * weekend
        if stress_scale is not None and spy_vol is not None and spy_vol.get(d, 0) > 0.30:
            x = x * stress_scale
        out[d] = float((x * (np.nan_to_num(r) - 2 * COST / 1e4)).sum())
    return pd.Series(out)


def episode_table(cols: dict) -> pd.DataFrame:
    rows = {}
    for k, (a, b) in EPISODES.items():
        rows[k] = {c: ((1 + s[a:b]).prod() - 1) * 100 if len(s[a:b]) else np.nan for c, s in cols.items()}
    return pd.DataFrame(rows).T.round(1)


def main():
    s = load_sim()
    spy = s.spy
    spy_vol = spy.rolling(20).std() * np.sqrt(252)
    bias = 9.1e-4                                          # per active day, measured on the overlap
    variants = {
        "live rules": dict(),
        "theme dedupe (corr 0.7)": dict(_corr=0.7),
        "stress memory 5d": dict(stress_memory=5),
        "weekend x0.5": dict(weekend=0.5),
        "SPY vol>30%: x0.5": dict(stress_scale=0.5),
        "all four": dict(_corr=0.7, stress_memory=5, weekend=0.5, stress_scale=0.5),
    }
    cache = {}
    res = {}
    for lab, kw in variants.items():
        kw = dict(kw); corr = kw.pop("_corr", 0.9)
        if corr not in cache:
            cache[corr] = (days_2020(corr), days_honest(corr))
        d20, dh = cache[corr]
        a = night_series(d20, spy_vol=spy_vol, **kw)
        a = a[a.index < "2020-11-05"]
        a = a - bias * (a != 0)                            # bias-correct the close-signal year
        b = night_series(dh, spy_vol=spy_vol, **kw)
        res[lab] = pd.concat([a, b]).sort_index()
    print("night leg alone, unit weight, % over each episode (2020 bias-corrected)")
    print(episode_table(res).to_string())
    print("\nnight leg, 2021-02 -> 2026-09 (honest data): the cost of each protection")
    for lab, r in res.items():
        x = r["2021-02-01":]
        c, sh, dd = B.stats(x)
        worst = x.nsmallest(1)
        print(f"  {lab:28s} CAGR {c*100:5.1f}%  Sharpe {sh:4.2f}  maxDD {dd*100:5.1f}%  "
              f"worst night {worst.iloc[0]*100:5.1f}% ({worst.index[0]:%Y-%m-%d})")
    pd.to_pickle(res, D.DATA / "night_crash_variants.pkl")


if __name__ == "__main__":
    main()
