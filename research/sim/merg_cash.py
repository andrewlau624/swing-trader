"""Study MERG-CASH: cash-takeover target spread, long side.

Pre-registration: "Amendment — Study MERG-CASH" in research/drafts/round1_prose.md
(1 judged rule; program N 840 -> 841). One look.

Mechanism: after a cash-bid announcement the target trades below the cash price
(deal-break risk + time value + arb funding constraints). Small long-only buyer
absorbs the spread, holds to close/tender. No shorting, no borrow.

Data: the daily-price-history dataset at ~/data/sharadar — actions
`acquisitioncash` rows give target, close date C and cash price P (value);
events 8-K rows give announcement proxy F (latest item-11/51 filing in
[C-365d, C-1d]); SEP/SFP bars give prices (delisted-complete).

  .venv/bin/python research/sim/merg_cash.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parent / "merg_cash_out.txt"
EV_LO, EV_HI = pd.Timestamp("1998-01-01"), pd.Timestamp("2026-06-30")
COST_JUDGE = 0.001
COST_STRESS = 0.0025
HOLD_CAP = 126  # sessions cap if target outlives C (failed match -> exit C+30 sess)


def has_code(s: str, want: set[str]) -> bool:
    return any(c in want for c in str(s).split("|"))


def cluster_t(x: pd.Series, g: pd.Series) -> tuple[float, float]:
    df = pd.DataFrame({"x": np.asarray(x, dtype=float), "g": np.asarray(g)})
    df = df[np.isfinite(df["x"].to_numpy())]
    if len(df) < 2:
        return float("nan"), 0.0
    x = df["x"].to_numpy()
    n = len(x)
    m = float(np.mean(x))
    xd = x - m
    s = pd.Series(xd).groupby(df["g"].to_numpy()).sum().to_numpy()
    G = len(s)
    var = (G / max(G - 1, 1)) * float((s ** 2).sum()) / (n ** 2)
    se = float(np.sqrt(max(var, 0)))
    return m, (m / se if se > 0 else 0.0)


def main() -> None:
    a = pd.read_parquet(STORE / "actions.parquet")
    a["date"] = pd.to_datetime(a["date"])
    mc = a[(a.action == "acquisitioncash")].copy()
    mc["P"] = pd.to_numeric(mc.value, errors="coerce")
    mc = mc[(mc.date >= EV_LO) & (mc.date <= EV_HI) & (mc.P > 0)].copy()
    mc = mc.rename(columns={"ticker": "target", "contraticker": "acq", "date": "C"})
    print(f"cash deals w/ price: {len(mc)}", flush=True)

    ev = pd.read_parquet(STORE / "events.parquet", columns=["ticker", "date", "eventcodes"])
    ev["date"] = pd.to_datetime(ev.date)
    ev = ev[ev.eventcodes.apply(lambda s: has_code(s, {"11", "51"}))].copy()
    ev_by_t = {t: g.date.sort_values().reset_index(drop=True) for t, g in ev.groupby("ticker")}

    # break-proxy candidates (adversarial check): 11/51 filers with no completed
    # cash close nearby AND a termination (item-12) filing within 200d after.
    _close_by_t = {t: pd.to_datetime(g.C.sort_values().to_numpy())
                   for t, g in mc.groupby("target")}
    _ev12 = pd.read_parquet(STORE / "events.parquet", columns=["ticker", "date", "eventcodes"])
    _ev12["date"] = pd.to_datetime(_ev12.date)
    _d12_by_t = {t: g.date.sort_values().to_numpy()
                 for t, g in _ev12[_ev12.eventcodes.apply(lambda s: has_code(s, {"12"}))].groupby("ticker")}
    _break_tickers: set[str] = set()
    for _t, _g in ev.groupby("ticker"):
        for _F in _g.date.sort_values().to_numpy():
            _F = pd.Timestamp(_F)
            if _F < pd.Timestamp("2004-08-23"):
                continue
            _cs = _close_by_t.get(_t)
            if _cs is not None and ((_cs >= _F.to_datetime64()) &
                                    (_cs <= (_F + pd.Timedelta(days=400)).to_datetime64())).any():
                continue
            _d12 = _d12_by_t.get(_t)
            if _d12 is None or not ((_d12 > _F.to_datetime64()) &
                                    (_d12 <= (_F + pd.Timedelta(days=200)).to_datetime64())).any():
                continue
            _break_tickers.add(_t)
            break
    print(f"break-proxy tickers: {len(_break_tickers)}", flush=True)

    need = set(mc.target) | _break_tickers
    cols = ["ticker", "date", "close", "closeunadj", "volume"]
    parts = []
    for name in ("stocks", "funds"):
        t = pd.read_parquet(STORE / f"{name}.parquet", columns=cols,
                            filters=[[("ticker", "in", sorted(need))]])
        if len(t):
            parts.append(t)
    b = pd.concat(parts, ignore_index=True)
    b["date"] = pd.to_datetime(b["date"])
    b = b.drop_duplicates(["ticker", "date"], keep="first")
    b = b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    px = {t: g.reset_index(drop=True) for t, g in b.groupby("ticker")}

    # benchmark, loaded alone so a big-list read can never silently drop it
    spy = None
    for _name in ("funds", "stocks"):
        _s = pd.read_parquet(STORE / f"{_name}.parquet", columns=cols,
                             filters=[[("ticker", "in", ["SPY", "QQQ"])]])
        if len(_s):
            _s["date"] = pd.to_datetime(_s["date"])
            _s = _s.drop_duplicates(["ticker", "date"], keep="first")
            _s = _s.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
            spy = (_s[_s.ticker == "SPY"] if (_s.ticker == "SPY").any()
                   else _s[_s.ticker == "QQQ"]).reset_index(drop=True)
            break
    assert spy is not None and len(spy) > 1000, "benchmark load failed"

    rows = []
    nofil = 0
    for r in mc.itertuples():
        fl = ev_by_t.get(r.target)
        F = None
        if fl is not None:
            cand = fl[(fl >= r.C - pd.Timedelta(days=365)) & (fl < r.C)]
            if len(cand):
                F = cand.iloc[-1]
        if F is None:
            nofil += 1
            continue
        g = px.get(r.target)
        if g is None or len(g) < 2:
            rows.append((r.target, r.C, r.P, F, "no_bars", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        dates = g.date.to_numpy()
        epos = int(np.searchsorted(dates, np.datetime64(F + pd.Timedelta(days=1))))
        if epos >= len(g):
            rows.append((r.target, r.C, r.P, F, "no_entry_bar", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        en_px = float(g.closeunadj.iloc[epos])
        spread = r.P / en_px - 1
        if not (0 < spread <= 0.30):
            rows.append((r.target, r.C, r.P, F, "spread_filter", np.nan, np.nan, np.nan, np.nan, np.nan, spread))
            continue
        if en_px < 2:
            rows.append((r.target, r.C, r.P, F, "price_filter", np.nan, np.nan, np.nan, np.nan, np.nan, spread))
            continue
        dvol = float(en_px * g.volume.iloc[epos])
        if dvol < 250_000:
            rows.append((r.target, r.C, r.P, F, "liq_filter", np.nan, np.nan, np.nan, np.nan, np.nan, spread))
            continue
        cpos = int(np.searchsorted(dates, np.datetime64(r.C + pd.Timedelta(days=1)))) - 1
        failed = False
        if cpos >= len(g) or (cpos >= 0 and (g.date.iloc[cpos] - r.C).days > 30):
            xpos = min(epos + HOLD_CAP, len(g) - 1)
            failed = True
        else:
            xpos = max(cpos, epos)
            if (g.date.iloc[xpos] - g.date.iloc[epos]).days > 400:
                xpos = min(epos + HOLD_CAP, len(g) - 1)
                failed = True
        ret = float(g.close.iloc[xpos] / g.close.iloc[epos] - 1)
        en_d, ex_d = g.date.iloc[epos], g.date.iloc[xpos]
        sb = spy[(spy.date >= en_d) & (spy.date <= ex_d)]
        bmk = float(sb.close.iloc[-1] / sb.close.iloc[0] - 1) if len(sb) >= 2 else np.nan
        rows.append((r.target, r.C, r.P, F, "failed_match" if failed else "ok",
                     en_d, ex_d, ret, bmk, dvol, spread))
    tr = pd.DataFrame(rows, columns=["target", "C", "P", "F", "status", "en_d", "ex_d",
                                     "ret", "spy", "dvol_en", "spread"])
    print(f"no 11/51 filing in window: {nofil}", flush=True)
    ok = tr[tr.status == "ok"].copy()
    ok["net"] = ok.ret - 2 * COST_JUDGE
    ok["net_stress"] = ok.ret - 2 * COST_STRESS
    ok["abn"] = ok.ret - ok.spy
    ok["exit_m"] = ok.ex_d.dt.strftime("%Y-%m")
    ok["half"] = np.where(ok.C < "2012-01-01", "1998-2011", "2012-2026")

    L = [f"MERG-CASH one-look (deals={len(mc)}, traded={len(ok)})",
         f"status counts: {tr.status.value_counts().to_dict()}"]
    m, t = cluster_t(ok.net, ok.exit_m)
    L.append(f"PRIMARY net spread @10bp/side: mean={m*100:.3f}% t={t:.2f} (exit-month clustered) "
             f"median={ok.net.median()*100:.3f}% hit={(ok.net > 0).mean()*100:.1f}% n={len(ok)}")
    m2, t2 = cluster_t(ok.net_stress, ok.exit_m)
    L.append(f"stress @25bp/side: mean={m2*100:.3f}% t={t2:.2f}")
    ma, ta = cluster_t(ok.abn - 2 * COST_JUDGE, ok.exit_m)
    L.append(f"SPY-abnormal net: mean={ma*100:.3f}% t={ta:.2f} median={(ok.abn - 2 * COST_JUDGE).median()*100:.3f}%")
    for h in ("1998-2011", "2012-2026"):
        s = ok[ok.half == h]
        mh, th = cluster_t(s.net, s.exit_m)
        L.append(f"half {h}: n={len(s)} mean={mh*100:.3f}% t={th:.2f} median={s.net.median()*100:.3f}%")
    x5 = ok.sort_values("net").iloc[5:]
    mx, tx = cluster_t(x5.net, x5.exit_m)
    L.append(f"ex-top-5: mean={mx*100:.3f}% t={tx:.2f}")
    L.append(f"break-tail: share losing >10%: {(ok.net < -0.10).mean()*100:.2f}%  "
             f"share losing >25%: {(ok.net < -0.25).mean()*100:.2f}%")
    L.append(f"time-to-close: median={(ok.ex_d - ok.en_d).dt.days.median():.0f}d mean={(ok.ex_d - ok.en_d).dt.days.mean():.0f}d")
    L.append(f"entry spread: median={ok.spread.median()*100:.2f}% mean={ok.spread.mean()*100:.2f}%")
    pl = []
    for r in ok.itertuples():
        g = px.get(r.target)
        pos = int(np.searchsorted(g.date.to_numpy(), np.datetime64(r.en_d)))
        p0 = pos - 252
        if p0 < 1:
            continue
        hold = min(len(g) - 1, p0 + int((r.ex_d - r.en_d).days * 0.7 + 5))
        if hold <= p0:
            continue
        pl.append(float(g.close.iloc[hold] / g.close.iloc[p0] - 1) - 2 * COST_JUDGE)
    pl = pd.Series(pl)
    if len(pl):
        pg = pd.Series([str((ok.ex_d.iloc[i] if i < len(ok) else 0))[:7] for i in range(len(pl))])
        mp, tp = cluster_t(pl, pg)
        L.append(f"placebo (-252 sess, matched hold): n={len(pl)} mean={pl.mean()*100:.3f}% "
                 f"median={pl.median()*100:.3f}% t_plain={pl.mean()/pl.std()*np.sqrt(len(pl)):.2f} t_clus={tp:.2f}")
    ok["yr"] = ok.ex_d.dt.year
    for y, s in ok.groupby("yr"):
        L.append(f"year {y}: n={len(s)} mean_net={s.net.mean()*100:.2f}%")
    L.append(f"entry dvol: median=${ok.dvol_en.median():,.0f} p10=${ok.dvol_en.quantile(.1):,.0f}")
    L.append("dollars/year (illustrative: full reinvestment, 5%-dvol cap, idle=0):")
    for A in (1_000, 3_000, 5_000, 10_000, 25_000):
        L.append(f"  ${A}: " + cycle_dollars(ok, A))
    # --- adversarial check (post-hoc, can only weaken: completed-deal conditioning) ---
    L.append("ADVERSARIAL break proxy (terminated-agreement filings, no completed deal):")
    close_dates = mc.set_index("target")["C"]
    br = []
    for t2 in sorted(_break_tickers):
        g = px.get(t2)
        if g is None:
            continue
        fl = ev_by_t.get(t2)
        if fl is None:
            continue
        for F2 in fl.sort_values().to_numpy():
            F2 = pd.Timestamp(F2)
            if F2 < pd.Timestamp("2004-08-23"):
                continue
            if t2 in close_dates.index:
                _cs = close_dates.loc[t2]
                _cs = _cs if isinstance(_cs, pd.Series) else pd.Series([_cs])
                if ((pd.to_datetime(_cs) >= F2) & (pd.to_datetime(_cs) <= F2 + pd.Timedelta(days=400))).any():
                    continue
            _d12 = _d12_by_t.get(t2, np.array([]))
            if not ((_d12 > F2.to_datetime64()) & (_d12 <= (F2 + pd.Timedelta(days=200)).to_datetime64())).any():
                continue
            epos = int(np.searchsorted(g.date.to_numpy(), np.datetime64(F2 + pd.Timedelta(days=1))))
            if epos >= len(g):
                break
            en_px = float(g.closeunadj.iloc[epos])
            if en_px < 2 or float(en_px * g.volume.iloc[epos]) < 250_000:
                break
            xpos = int(np.searchsorted(g.date.to_numpy(), np.datetime64(F2 + pd.Timedelta(days=84)))) - 1
            xpos = min(max(xpos, epos), len(g) - 1)
            br.append(float(g.close.iloc[xpos] / g.close.iloc[epos] - 1))
            break  # one proxy per ticker (first)
    br = pd.Series(br)
    if len(br):
        L.append(f"  n={len(br)} mean={br.mean()*100:.2f}% median={br.median()*100:.2f}% "
                 f"share<-10%={(br < -0.10).mean()*100:.1f}% share<-25%={(br < -0.25).mean()*100:.1f}%")
        n_comp = int((ok.C >= "2004-08-23").sum())
        rate = len(br) / max(n_comp + len(br), 1)
        drag = rate * abs(br[br < 0].mean()) if (br < 0).any() else 0.0
        L.append(f"  completed(2004+, w/ filing)={n_comp} proxy-break-rate={rate*100:.1f}% "
                 f"implied live drag~= -{drag*100:.2f}%/trade vs primary +{m*100:.2f}%")
    else:
        L.append("  n=0 (no proxy breaks found)")
    conds = [m > 0 and t >= 2, bool(((ok.groupby("half").net.mean() > 0)).all()),
             bool(ok.net.median() > 0), mx > 0,
             bool(len(pl) and abs(pl.mean()) < abs(m) / 3)]
    verdict = "REJECTED" if (m <= 0 or t < 1) else ("VALIDATED" if all(conds) else "WEAK/PARTIAL")
    L.append("VERDICT: " + verdict)
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def cycle_dollars(ok: pd.DataFrame, A: float) -> str:
    tr = ok.sort_values("en_d")
    e = A
    rets = []
    for r in tr.itertuples():
        n = max((r.ex_d - r.en_d).days, 1)
        rets.append((r.en_d, r.ex_d, (1 + r.net) ** (1 / n) - 1, min(0.05 * r.dvol_en, A)))
    rets.sort()
    days = pd.date_range(tr.en_d.min(), tr.ex_d.max(), freq="D")
    eqs = []
    for d in days:
        act = [x for x in rets if x[0] <= d <= x[1]]
        if act:
            w = e / len(act)
            e = (e - sum(min(w, cap) for (_, _, _, cap) in act)) + \
                sum(min(w, cap) * (1 + dr) for (_, _, dr, cap) in act)
        eqs.append(e)
    eqs = pd.Series(eqs, index=days)
    yrs = (days[-1] - days[0]).days / 365.25
    ann = (e / A) ** (1 / yrs) - 1 if yrs > 0 else 0
    dd = float((eqs / eqs.cummax() - 1).min())
    return (f"total={(e/A-1)*100:.1f}% ann={ann*100:.1f}% ${ann*A:,.0f}/yr "
            f"maxDD={dd*100:.1f}%")


if __name__ == "__main__":
    main()
