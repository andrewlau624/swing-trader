"""Study DELIST-31: delisting-notice (8-K item 31) drift.

Pre-registration: "Amendment — Study DELIST-31" in research/drafts/round1_prose.md
(1 judged rule; program N 841 -> 842). One look.

Question (Priority 2): after listing-compliance failure becomes public, do forced
sellers overshoot (long bounce) or is the return a database illusion on names
sliding to zero? Directional expectation: REJECT.

  .venv/bin/python research/sim/delist31.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parent / "delist31_out.txt"
EV_LO, EV_HI = pd.Timestamp("2004-08-23"), pd.Timestamp("2026-06-30")
HOLD = 60
COST_JUDGE = 0.001
COST_STRESS = 0.0025


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
    ev = pd.read_parquet(STORE / "events.parquet", columns=["ticker", "date", "eventcodes"])
    ev["date"] = pd.to_datetime(ev.date)
    f31 = ev[ev.eventcodes.apply(lambda s: has_code(s, {"31"}))].copy()
    f31 = f31[(f31.date >= EV_LO) & (f31.date <= EV_HI)].sort_values(["ticker", "date"])
    # episodes: first 31 after >= 252 sessions (~1yr) without one; use 365d proxy
    eps = []
    for t, g in f31.groupby("ticker"):
        ds = g.date.sort_values().to_numpy()
        last = np.datetime64("1990-01-01")
        for d in ds:
            if (d - last).astype("timedelta64[D]").astype(int) >= 365:
                eps.append((t, pd.Timestamp(d)))
            last = d
    eps = pd.DataFrame(eps, columns=["ticker", "F"])
    print(f"episodes: {len(eps)} tickers: {eps.ticker.nunique()}", flush=True)

    need = set(eps.ticker)
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

    _s = pd.read_parquet(STORE / "funds.parquet", columns=cols, filters=[[("ticker", "in", ["SPY"])]])
    _s["date"] = pd.to_datetime(_s["date"])
    spy = _s.drop_duplicates(["ticker", "date"]).sort_values("date").reset_index(drop=True)
    assert len(spy) > 1000

    rows = []
    for r in eps.itertuples():
        g = px.get(r.ticker)
        if g is None or len(g) < 2:
            rows.append((r.ticker, r.F, "no_bars", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        dates = g.date.to_numpy()
        epos = int(np.searchsorted(dates, np.datetime64(r.F + pd.Timedelta(days=1))))
        if epos >= len(g):
            rows.append((r.ticker, r.F, "no_entry_bar", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        en_px = float(g.closeunadj.iloc[epos])
        dvol = float(en_px * g.volume.iloc[epos])
        if en_px < 1 or dvol < 100_000:
            rows.append((r.ticker, r.F, "filter", np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
            continue
        xpos = min(epos + HOLD, len(g) - 1)
        delisted_hold = xpos < epos + HOLD
        ret = float(g.close.iloc[xpos] / g.close.iloc[epos] - 1)
        en_d, ex_d = g.date.iloc[epos], g.date.iloc[xpos]
        sb = spy[(spy.date >= en_d) & (spy.date <= ex_d)]
        bmk = float(sb.close.iloc[-1] / sb.close.iloc[0] - 1) if len(sb) >= 2 else np.nan
        rows.append((r.ticker, r.F, "delisted_hold" if delisted_hold else "ok",
                     en_d, ex_d, ret, bmk, dvol, en_px))
    tr = pd.DataFrame(rows, columns=["ticker", "F", "status", "en_d", "ex_d",
                                     "ret", "spy", "dvol_en", "raw_en"])
    print(tr.status.value_counts().to_dict(), flush=True)
    ok = tr[tr.status.isin(["ok", "delisted_hold"])].copy()
    ok["abn"] = ok.ret - ok.spy
    ok["net"] = ok.abn - 2 * COST_JUDGE
    ok["net_stress"] = ok.abn - 2 * COST_STRESS
    ok["exit_m"] = ok.ex_d.dt.strftime("%Y-%m")
    ok["half"] = np.where(ok.F < "2016-01-01", "2004-2015", "2016-2026")

    L = [f"DELIST-31 one-look (episodes={len(eps)}, traded={len(ok)})"]
    m, t = cluster_t(ok.net, ok.exit_m)
    L.append(f"PRIMARY net abn 60d @10bp/side: mean={m*100:.3f}% t={t:.2f} (exit-month clustered) "
             f"median={ok.net.median()*100:.3f}% hit={(ok.net > 0).mean()*100:.1f}% n={len(ok)}")
    m2, t2 = cluster_t(ok.net_stress, ok.exit_m)
    L.append(f"stress @25bp/side: mean={m2*100:.3f}% t={t2:.2f}")
    for h in ("2004-2015", "2016-2026"):
        s = ok[ok.half == h]
        mh, th = cluster_t(s.net, s.exit_m)
        L.append(f"half {h}: n={len(s)} mean={mh*100:.3f}% t={th:.2f} median={s.net.median()*100:.3f}%")
    x5 = ok.sort_values("net").iloc[5:]
    mx, tx = cluster_t(x5.net, x5.exit_m)
    L.append(f"ex-top-5: mean={mx*100:.3f}% t={tx:.2f}")
    nd = int((ok.status == "delisted_hold").sum())
    oo = ok[ok.status == "ok"]
    mo, to = cluster_t(oo.net, oo.exit_m)
    L.append(f"delist-during-hold: {nd}/{len(ok)} ({nd/max(len(ok),1)*100:.1f}%); ex-delist mean={mo*100:.3f}% t={to:.2f}")
    pl = []
    for r in ok.itertuples():
        g = px.get(r.ticker)
        pos = int(np.searchsorted(g.date.to_numpy(), np.datetime64(r.en_d)))
        p0 = pos - 252
        if p0 < 1 or p0 + HOLD >= len(g):
            continue
        pr = float(g.close.iloc[p0 + HOLD] / g.close.iloc[p0] - 1)
        sb = spy[(spy.date >= g.date.iloc[p0]) & (spy.date <= g.date.iloc[p0 + HOLD])]
        pb = float(sb.close.iloc[-1] / sb.close.iloc[0] - 1) if len(sb) >= 2 else np.nan
        if np.isfinite(pb):
            pl.append(pr - pb - 2 * COST_JUDGE)
    pl = pd.Series(pl)
    if len(pl):
        mp, tp = cluster_t(pl, pd.Series(["p"] * len(pl)))
        L.append(f"placebo (-252 sess): n={len(pl)} mean={pl.mean()*100:.3f}% median={pl.median()*100:.3f}%")
    ok["yr"] = ok.ex_d.dt.year
    for y, s in ok.groupby("yr"):
        L.append(f"year {y}: n={len(s)} mean_net={s.net.mean()*100:.2f}%")
    L.append(f"entry dvol: median=${ok.dvol_en.median():,.0f} p10=${ok.dvol_en.quantile(.1):,.0f}")
    conds = [bool(np.isfinite(m)) and m > 0 and t >= 2,
             bool(((ok.groupby("half").net.mean() > 0)).all()),
             bool(ok.net.median() > 0), bool(np.isfinite(mx)) and mx > 0,
             bool(len(pl) and abs(pl.mean()) < abs(m) / 3)]
    verdict = "REJECTED" if (not np.isfinite(m) or m <= 0 or t < 1) else ("VALIDATED" if all(conds) else "WEAK/PARTIAL")
    L.append("VERDICT: " + verdict)
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
