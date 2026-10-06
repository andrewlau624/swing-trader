"""Study SPIN-CHILD: spun-off child post-distribution drift.

Pre-registration: "Amendment — Study SPIN-CHILD" in research/drafts/round1_prose.md
(1 judged rule; program N 839 -> 840). One look.

Mechanism: parent shareholders receive child shares they did not choose; holders
that cannot hold the (usually smaller, off-index) child must sell into the
distribution. Forced sellers, known date D; absorbers are new buyers.

Data: the daily-price-history dataset at ~/data/sharadar (delisted-complete daily
bars 1997-12-31+; actions table with spinoff rows naming parent/child/ratio).

  .venv/bin/python research/sim/spin_child.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parent / "spin_child_out.txt"
EV_LO, EV_HI = pd.Timestamp("1998-01-01"), pd.Timestamp("2026-06-30")
HOLD = 60  # judged hold, sessions on child calendar
HOLD2 = 20  # reported secondary hold
COST_JUDGE = 0.001  # 10bp/side
COST_STRESS = 0.0025  # 25bp/side


def load_bars(tickers: set[str]) -> pd.DataFrame:
    cols = ["ticker", "date", "close", "closeunadj", "volume"]
    parts = []
    for name in ("stocks", "funds"):
        pf = pq.ParquetFile(STORE / f"{name}.parquet")
        filt = [[("ticker", "in", sorted(tickers))]]
        try:
            t = pd.read_parquet(STORE / f"{name}.parquet", columns=cols, filters=filt)
        except Exception:
            t = pd.DataFrame()
        if len(t):
            parts.append(t)
    b = pd.concat(parts, ignore_index=True)
    b["date"] = pd.to_datetime(b["date"])
    b = b.drop_duplicates(["ticker", "date"], keep="first")
    return b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def cluster_t(x: pd.Series, g: pd.Series) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = x.mean()
    df = pd.DataFrame({"x": x, "g": np.asarray(g)}).dropna()
    if len(df) < 2:
        return m, 0.0
    xd = df["x"].to_numpy() - m
    s = pd.Series(xd).groupby(df["g"].to_numpy()).sum().to_numpy()
    G = len(s)
    var = (G / max(G - 1, 1)) * float((s ** 2).sum()) / (n ** 2)
    se = float(np.sqrt(max(var, 0)))
    return m, (m / se if se > 0 else 0.0)


def main() -> None:
    a = pd.read_parquet(STORE / "actions.parquet")
    a["date"] = pd.to_datetime(a["date"])
    sp = a[(a.action == "spinoff") & (a.date >= EV_LO) & (a.date <= EV_HI)].copy()
    sp = sp.drop_duplicates(["contraticker", "date"], keep="first")
    sp = sp.rename(columns={"ticker": "parent", "contraticker": "child", "date": "D"})
    print(f"spinoff events: {len(sp)}")

    need = set(sp.child) | set(sp.parent) | {"SPY", "QQQ"}
    b = load_bars(need)
    px = {t: g.reset_index(drop=True) for t, g in b.groupby("ticker")}
    spy = px.get("SPY", px.get("QQQ"))
    spy_idx = {d: c for d, c in zip(spy.date, spy.close)} if spy is not None else {}

    rows = []
    for r in sp.itertuples():
        g = px.get(r.child)
        if g is None or len(g) < 5:
            rows.append((r.child, r.parent, r.D, "no_bars", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        dates = g.date.to_numpy()
        pos = int(np.searchsorted(dates, np.datetime64(r.D)))
        if pos >= len(g):
            rows.append((r.child, r.parent, r.D, "no_bar_on_D", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        entry_pos = -1
        for k in range(pos, min(pos + 6, len(g))):
            if (g.date.iloc[k] - r.D).days <= 7:
                entry_pos = k
                break
        if entry_pos < 0:
            rows.append((r.child, r.parent, r.D, "late_entry", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        late = entry_pos - pos
        if entry_pos + HOLD >= len(g):
            rows.append((r.child, r.parent, r.D, "short_history", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        en, ex = entry_pos, entry_pos + HOLD
        ex20 = entry_pos + HOLD2
        ret = g.close.iloc[ex] / g.close.iloc[en] - 1
        ret20 = g.close.iloc[ex20] / g.close.iloc[en] - 1 if ex20 < len(g) else np.nan
        en_d, ex_d = g.date.iloc[en], g.date.iloc[ex]
        sb = spy[(spy.date >= en_d) & (spy.date <= ex_d)] if spy is not None else None
        if sb is not None and len(sb) >= 2:
            bmk = sb.close.iloc[-1] / sb.close.iloc[0] - 1
        else:
            bmk = np.nan
        raw_en = g.closeunadj.iloc[en]
        dvol = float(raw_en * g.volume.iloc[en])
        rows.append((r.child, r.parent, r.D, "ok", en_d, ex_d, float(ret), float(ret20),
                     float(bmk), float(raw_en), dvol, late))
    tr = pd.DataFrame(rows, columns=["child", "parent", "D", "status", "en_d", "ex_d",
                                     "ret", "ret20", "spy", "raw_en", "dvol_en", "late"])
    ok = tr[tr.status == "ok"].copy()
    ok["abn"] = ok.ret - ok.spy
    ok["net"] = ok.abn - 2 * COST_JUDGE
    ok["net_stress"] = ok.abn - 2 * COST_STRESS
    ok["exit_m"] = ok.ex_d.dt.strftime("%Y-%m")
    ok["half"] = np.where(ok.D < "2012-01-01", "1998-2011", "2012-2026")

    L = [f"SPIN-CHILD one-look  (events={len(sp)}, traded={len(ok)}, {ok.D.min().date()}..{ok.D.max().date()})",
         f"dropped: {(tr.status.value_counts()).to_dict()}",
         f"late-entry count: {(ok.late > 0).sum()}"]
    m, t = cluster_t(ok.net, ok.exit_m)
    L.append(f"PRIMARY net abn 60d @10bp/side: mean={m*100:.3f}% t={t:.2f} (exit-month clustered) "
             f"median={ok.net.median()*100:.3f}% hit={(ok.net > 0).mean()*100:.1f}% n={len(ok)}")
    m2, t2 = cluster_t(ok.net_stress, ok.exit_m)
    L.append(f"stress @25bp/side: mean={m2*100:.3f}% t={t2:.2f}")
    mg, tg = cluster_t(ok.ret - 2 * COST_JUDGE, ok.exit_m)
    L.append(f"gross (no bench) net: mean={mg*100:.3f}% t={tg:.2f}")
    for h in ("1998-2011", "2012-2026"):
        s = ok[ok.half == h]
        mh, th = cluster_t(s.net, s.exit_m)
        L.append(f"half {h}: n={len(s)} mean={mh*100:.3f}% t={th:.2f} median={s.net.median()*100:.3f}%")
    x5 = ok.sort_values("net").iloc[5:]
    mx, tx = cluster_t(x5.net, x5.exit_m)
    L.append(f"ex-top-5: mean={mx*100:.3f}% t={tx:.2f}")
    # placebo: same children 252 sessions before
    pl = []
    for r in ok.itertuples():
        g = px.get(r.child)
        pos = int(np.searchsorted(g.date.to_numpy(), np.datetime64(r.en_d)))
        p0 = pos - 252
        if p0 < 1 or p0 + HOLD >= len(g):
            continue
        pr = g.close.iloc[p0 + HOLD] / g.close.iloc[p0] - 1
        sb = spy[(spy.date >= g.date.iloc[p0]) & (spy.date <= g.date.iloc[p0 + HOLD])]
        pb = sb.close.iloc[-1] / sb.close.iloc[0] - 1 if (sb is not None and len(sb) >= 2) else np.nan
        pl.append(pr - pb - 2 * COST_JUDGE)
    pl = pd.Series(pl)
    L.append(f"placebo (same child, -252 sess): n={len(pl)} mean={pl.mean()*100:.3f}% t={pl.mean()/pl.std()*np.sqrt(len(pl)):.2f}")
    # parent control
    pc = []
    for r in ok.itertuples():
        g = px.get(r.parent)
        if g is None:
            continue
        pos = int(np.searchsorted(g.date.to_numpy(), np.datetime64(r.en_d)))
        if pos + HOLD >= len(g):
            continue
        pr = g.close.iloc[pos + HOLD] / g.close.iloc[pos] - 1
        sb = spy[(spy.date >= g.date.iloc[pos]) & (spy.date <= g.date.iloc[pos + HOLD])]
        pb = sb.close.iloc[-1] / sb.close.iloc[0] - 1 if (sb is not None and len(sb) >= 2) else np.nan
        pc.append(pr - pb - 2 * COST_JUDGE)
    pc = pd.Series(pc)
    L.append(f"parent control (same window): n={len(pc)} mean={pc.mean()*100:.3f}% t={pc.mean()/pc.std()*np.sqrt(len(pc)):.2f}")
    # regimes
    ok["yr"] = ok.ex_d.dt.year
    for y, s in ok.groupby("yr"):
        L.append(f"year {y}: n={len(s)} mean_net={s.net.mean()*100:.2f}%")
    # liquid subset
    liq = ok[(ok.raw_en >= 2) & (ok.dvol_en >= 500_000)]
    ml, tl = cluster_t(liq.net, liq.exit_m)
    L.append(f"liquid subset (>=2$, >=500k dvol): n={len(liq)} mean={ml*100:.3f}% t={tl:.2f} median={liq.net.median()*100:.3f}%")
    L.append(f"entry dvol: median=${ok.dvol_en.median():,.0f} p10=${ok.dvol_en.quantile(.1):,.0f}")
    # portfolio simulation for dollars
    L.append("dollars/year (equal-weight active trades, 5% entry-dvol cap/trade, idle=0):")
    for A in (1_000, 3_000, 5_000, 10_000, 25_000):
        L.append(f"  ${A}: " + port_dollars(ok, A))
    verdict = "REJECTED" if (m <= 0 or t < 1) else ("VALIDATED" if (t >= 2 and (ok.groupby('half').net.mean() > 0).all()
                and ok.net.median() > 0 and mx > 0 and abs(pl.mean()) < abs(m) / 3) else "WEAK/PARTIAL")
    L.append("VERDICT: " + verdict)
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def port_dollars(ok: pd.DataFrame, A: float) -> str:
    tr = ok.sort_values("en_d").reset_index(drop=True)
    days = pd.date_range(tr.en_d.min(), tr.ex_d.max(), freq="D")
    eq = A
    peak, dd = A, 0.0
    # calendar: need daily child prices — approximate with linear accrue between en/ex
    rets = []
    for r in tr.itertuples():
        n = (r.ex_d - r.en_d).days
        rets.append((r.en_d, r.ex_d, (1 + r.net) ** (1 / max(n, 1)) - 1, min(0.05 * r.dvol_en, A)))
    rets.sort()
    # daily sim
    import datetime as dt
    cur = {i: v for i, v in enumerate([A] * 0)}
    # simpler: equal weight across active, capped
    eqs = []
    e = A
    for d in days:
        act = [x for x in rets if x[0] <= d <= x[1]]
        if not act:
            eqs.append(e)
            continue
        w = e / len(act)
        g = sum(min(w, cap) * dr for (_, _, dr, cap) in act)
        idle = e - sum(min(w, cap) for (_, _, _, cap) in act)
        e = idle + sum(min(w, cap) * (1 + dr) for (_, _, dr, cap) in act)
        eqs.append(e)
    eqs = pd.Series(eqs, index=days)
    yrs = (days[-1] - days[0]).days / 365.25
    tot = e / A - 1
    ann = (1 + tot) ** (1 / yrs) - 1 if yrs > 0 else 0
    dd = float((eqs / eqs.cummax() - 1).min())
    return f"total={tot*100:.1f}% ann={ann*100:.1f}% ${ann*A:,.0f}/yr maxDD={dd*100:.1f}%"


if __name__ == "__main__":
    main()
