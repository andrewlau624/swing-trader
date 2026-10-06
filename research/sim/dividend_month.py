"""Study DM - dividend-month clientele premium (Hartzmark-Solomon 2013).

    PYTHONPATH=. .venv/bin/python -m research.sim.dividend_month

Pre-registered: research/drafts/study_dm.md (N 834 -> 835). One look; research only.
Longs = stocks with >=1 regular (non-special, non-foreign) ex-date in month M; benchmark =
all other liquid stocks. Equal-weight forward return over M (last close of M vs last close of
M-1). Secondary: event window close T-5 .. close T+5 vs SPY, T = ex-date.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/dividend_month_out.txt"
PANEL = ROOT / "data/research/night/panel.pkl"
DIVS = ROOT / "data/research/night/dividends.json"

MIN_PRICE = 5.0
MIN_ADV = 5_000_000.0
ADV_WIN = 20
GATE_BP = 15.0
COSTS = {"gross": 0.0, "net@5bp": 10.0, "net@15bp": 30.0, "net@3x(45bp)": 90.0}

LINES: list[str] = []


def say(s=""):
    print(s)
    LINES.append(s)


def tstat(x):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 2:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def fmt(bp):
    return f"{bp:+.1f}" if np.isfinite(bp) else "n/a"


def load_regular_divs():
    rows = json.load(open(DIVS))
    df = pd.DataFrame(rows)
    df = df[(~df.special.astype(bool)) & (~df.foreign.astype(bool))]
    df["ex_date"] = pd.to_datetime(df["ex_date"])
    return df[["symbol", "ex_date", "rate"]].dropna()


def main():
    P = pd.read_pickle(PANEL)
    close = P["close"].sort_index()
    volume = P["volume"].sort_index()
    idx = close.index
    dv = close * volume
    spy = close["SPY"] if "SPY" in close.columns else None

    divs = load_regular_divs()
    divs = divs[divs.symbol.isin(close.columns)]
    divs["ym"] = divs.ex_date.dt.to_period("M")
    payer_by_ym = divs.groupby("ym").symbol.apply(lambda s: set(s.unique())).to_dict()

    # consecutive calendar-month pairs present in the panel
    ym_period = pd.Series(idx).dt.to_period("M")
    months = list(dict.fromkeys(ym_period.tolist()))
    pairs = [(months[i - 1], months[i]) for i in range(1, len(months))]

    rows = []
    for prev_m, m in pairs:
        sess_prev = idx[ym_period == prev_m]
        sess_last = idx[ym_period == m]
        m_prev, m_last = sess_prev[-1], sess_last[-1]
        pos = idx.get_loc(m_prev)
        if pos < ADV_WIN - 1:
            continue
        c_prev = close.iloc[pos]
        adv = dv.iloc[pos - ADV_WIN + 1:pos + 1].mean()
        uni = c_prev.notna() & (c_prev >= MIN_PRICE) & adv.notna() & (adv >= MIN_ADV)
        r = close.loc[m_last] / c_prev - 1.0
        ok = uni & r.notna() & np.isfinite(r)
        payers = payer_by_ym.get(m, set())
        is_pay = ok.index.isin(payers)
        long_m = ok & is_pay
        bench_m = ok & ~is_pay
        if long_m.sum() < 1 or bench_m.sum() < 1:
            continue
        ml, mb = float(r[long_m].mean()), float(r[bench_m].mean())
        rows.append(dict(month=str(m), n_long=int(long_m.sum()), n_bench=int(bench_m.sum()),
                         mean_long=ml, mean_bench=mb, dm=ml - mb))
    M = pd.DataFrame(rows)
    M["year"] = M.month.str[:4].astype(int)

    say("STUDY DM - dividend-month clientele premium (Hartzmark-Solomon 2013; research only, one look)")
    say(f"panel {PANEL.relative_to(ROOT)}  close {close.shape[0]} sessions x {close.shape[1]} symbols  "
        f"{idx.min().date()}..{idx.max().date()}  (SIP adjustment='all' = total-return closes)")
    say(f"divs {DIVS.relative_to(ROOT)}  regular ex-dates in-window: {len(divs)}  "
        f"{divs.ex_date.min().date()}..{divs.ex_date.max().date()}")
    say(f"rule: regular ex-date in M; long vs non-payer benchmark; uni = close ${MIN_PRICE:.0f} "
        f"+ 20d ADV >= ${MIN_ADV/1e6:.0f}M before M; equal-weight close(M-1)->close(M)")
    say(f"DM months: {len(M)}  {M.month.iloc[0]}..{M.month.iloc[-1]}  "
        f"avg longs {M.n_long.mean():.0f}  avg bench {M.n_bench.mean():.0f}")
    say()

    dm = M.dm.values * 1e4  # bp
    mean_bp = float(np.nanmean(dm))
    med_bp = float(np.nanmedian(dm))
    hit = float(np.mean(dm > 0))
    t_all = tstat(dm)
    ex5 = float(np.mean(np.sort(dm)[:-5])) if len(dm) > 5 else float("nan")

    say("== Monthly long-minus-benchmark (bp/month) ==")
    say(f"  months n={len(M)}  mean {fmt(mean_bp)}  median {fmt(med_bp)}  hit {hit*100:.0f}%  "
        f"month-clustered t {t_all:+.2f}  ex-top-5 {fmt(ex5)}")
    for k, c in COSTS.items():
        say(f"  {k:<14} {fmt(mean_bp - c)}")
    say()

    half = len(M) // 2
    h1, h2 = M.iloc[:half], M.iloc[half:]
    say("== Half / yearly (mean DM bp, months, sign) ==")
    say(f"  half1 {h1.month.iloc[0]}..{h1.month.iloc[-1]}: mean {fmt(h1.dm.mean()*1e4)} "
        f"median {fmt(h1.dm.median()*1e4)} hit {(h1.dm>0).mean()*100:.0f}% n={len(h1)}")
    say(f"  half2 {h2.month.iloc[0]}..{h2.month.iloc[-1]}: mean {fmt(h2.dm.mean()*1e4)} "
        f"median {fmt(h2.dm.median()*1e4)} hit {(h2.dm>0).mean()*100:.0f}% n={len(h2)}")
    for y, g in M.groupby("year"):
        say(f"  {y}: mean {fmt(g.dm.mean()*1e4)} median {fmt(g.dm.median()*1e4)} "
            f"hit {(g.dm>0).mean()*100:.0f}% n={len(g)}")
    say()

    # event-time: close T-5 -> close T+5 vs SPY
    ev = []
    if spy is not None:
        pos_of = {d: i for i, d in enumerate(idx)}
        for sym, t in zip(divs.symbol.values, divs.ex_date.values):
            if t not in pos_of or sym not in close.columns:
                continue
            p = pos_of[t]
            if p < 5 or p + 5 >= len(idx):
                continue
            s0, s1 = close[sym].iloc[p - 5], close[sym].iloc[p + 5]
            m0, m1 = spy.iloc[p - 5], spy.iloc[p + 5]
            if not (np.isfinite(s0) and np.isfinite(s1) and np.isfinite(m0) and np.isfinite(m1)):
                continue
            if s0 <= 0 or m0 <= 0:
                continue
            ev.append(dict(date=idx[p], sym=sym, abn=(s1 / s0 - 1.0) - (m1 / m0 - 1.0)))
    E = pd.DataFrame(ev)
    say("== Event-time: payer close(T-5)->close(T+5) minus SPY, T = regular ex-date ==")
    if E.empty:
        say("  no events with a full window")
        ev_mean = float("nan")
        ev_t = float("nan")
    else:
        ev_mean = float(E.abn.mean() * 1e4)
        ev_t = tstat(E.groupby("date").abn.mean().values * 1e4)
        say(f"  events n={len(E)}  mean {fmt(ev_mean)}  median {fmt(E.abn.median()*1e4)}  "
            f"hit {(E.abn>0).mean()*100:.0f}%  date-clustered t {ev_t:+.2f}  "
            f"ex-top-5 {fmt(np.mean(np.sort(E.abn.values*1e4)[:-5]))}")
    say()

    # verdict
    sign_h = (h1.dm.mean() > 0) and (h2.dm.mean() > 0)
    net5 = mean_bp - COSTS["net@5bp"]
    ok = (net5 >= GATE_BP) and (t_all >= 2) and (med_bp > 0) and sign_h and (ev_mean > 0)
    say("== GATE / KILL RULE ==")
    say(f"  1 net@5bp >= {GATE_BP:.0f}bp : {fmt(net5)}  {'PASS' if net5 >= GATE_BP else 'FAIL'}")
    say(f"  2 month-clustered t >= 2 : {t_all:+.2f}  {'PASS' if t_all >= 2 else 'FAIL'}")
    say(f"  3 median > 0 : {fmt(med_bp)}  {'PASS' if med_bp > 0 else 'FAIL'}")
    say(f"  4 sign both halves : {'PASS' if sign_h else 'FAIL'}")
    say(f"  5 event-time mean > 0 : {fmt(ev_mean)}  {'PASS' if ev_mean > 0 else 'FAIL'}")
    say(f"  VERDICT: {'PASS' if ok else 'KILL'}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
