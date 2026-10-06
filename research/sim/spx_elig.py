"""Study SPX-ELIG: S&P 500 GAAP-eligibility transition -> index-inclusion anticipation.

Pre-registration: "Amendment — Study SPX-ELIG" in research/drafts/round1_prose.md
(1 judged rule; program N 842 -> 843). One look.

Mechanism: a size-qualified non-member whose trailing-4Q GAAP earnings turn positive
(S&P's hard earnings gate) becomes an add candidate. S&P 500 index funds are the
named forced buyers at the add's effective-date close; we buy after the filing and
sell to them at that close (or give up after 126 sessions). Long-only.

Data: the daily-price-history dataset at ~/data/sharadar (SF1 ARQ, daily marketcap,
sp500 snapshots + added/removed, SEP/SFP bars delisted-complete).

  .venv/bin/python research/sim/spx_elig.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parent / "spx_elig_out.txt"
EV_LO, EV_HI = pd.Timestamp("2000-01-01"), pd.Timestamp("2026-03-31")
COST_JUDGE = 0.001
COST_STRESS = 0.0025
HOLD = 126
SPACING = 252
SIZE_PCT = 20
CATS = {"Domestic Common Stock", "Domestic Common Stock Primary Class"}


# exit-month clustered mean/t, as in merg_cash.py
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


def membership(sp: pd.DataFrame):
    """PIT S&P 500 membership: latest quarterly snapshot <= d, rolled forward by adds/removes."""
    snaps = sp[sp.action == "historical"]
    snap_sets = {d: set(g.ticker) for d, g in snaps.groupby("date")}
    snap_dates = np.array(sorted(snap_sets))
    chg = sp[sp.action.isin(["added", "removed"])].sort_values("date")

    def members(d: pd.Timestamp) -> set[str]:
        i = np.searchsorted(snap_dates, np.datetime64(d), side="right") - 1
        if i < 0:
            return set()
        s0 = pd.Timestamp(snap_dates[i])
        m = set(snap_sets[snap_dates[i]])
        for r in chg[(chg.date > s0) & (chg.date <= d)].itertuples():
            (m.add if r.action == "added" else m.discard)(r.ticker)
        return m
    return members


def events(f: pd.DataFrame, placebo: bool) -> pd.DataFrame:
    """Earnings-test transitions (primary) or long-eligible filings (placebo)."""
    out = []
    for t, g in f.groupby("ticker"):
        g = g.sort_values("calendardate").drop_duplicates("calendardate", keep="first")
        cd = g.calendardate.to_numpy()
        ni = g.netinccmn.to_numpy(dtype=float)
        n = len(g)
        ok = np.full(n, np.nan)
        for i in range(3, n):
            span = (cd[i] - cd[i - 3]) / np.timedelta64(1, "D")
            if span > 290 or not np.isfinite(ni[i - 3:i + 1]).all():
                continue
            ok[i] = float(ni[i - 3:i + 1].sum() > 0 and ni[i] > 0)
        g = g.assign(ok=ok)
        if placebo:
            hit = np.zeros(n, bool)
            for i in range(4, n):
                w = ok[i - 4:i + 1]
                hit[i] = np.isfinite(w).all() and (w == 1).all()
        else:
            prev = np.r_[np.nan, ok[:-1]]
            hit = (ok == 1) & (prev == 0)
        out.append(g.loc[hit, ["ticker", "date"]])
    e = pd.concat(out, ignore_index=True).rename(columns={"date": "E"})
    return e[(e.E >= EV_LO) & (e.E <= EV_HI)]


def main() -> None:
    tk = pd.read_parquet(STORE / "tickers.parquet",
                         columns=["table", "ticker", "category", "firstpricedate"])
    tk = tk[(tk.table == "SF1") & tk.category.isin(CATS)].drop_duplicates("ticker")
    first_px = dict(zip(tk.ticker, pd.to_datetime(tk.firstpricedate)))
    f = pd.read_parquet(STORE / "fundamentals.parquet",
                        columns=["ticker", "dimension", "calendardate", "date", "netinccmn"],
                        filters=[[("dimension", "==", "ARQ")]])
    f = f[f.ticker.isin(first_px)].copy()
    f["calendardate"] = pd.to_datetime(f.calendardate)
    f["date"] = pd.to_datetime(f.date)

    sp = pd.read_parquet(STORE / "sp500.parquet")
    sp["date"] = pd.to_datetime(sp.date)
    members = membership(sp)
    adds = {t: np.sort(g.date.to_numpy()) for t, g in sp[sp.action == "added"].groupby("ticker")}

    cols = ["ticker", "date", "close", "closeunadj", "volume"]
    spy = pd.read_parquet(STORE / "funds.parquet", columns=cols, filters=[[("ticker", "==", "SPY")]])
    spy["date"] = pd.to_datetime(spy.date)
    spy = spy.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    assert len(spy) > 5000, "benchmark load failed"
    cal = spy.date.to_numpy()
    spy_c = spy.set_index("date").close

    raw = {"primary": events(f, False), "placebo": events(f, True)}
    for k, e in raw.items():
        print(f"{k} raw events: {len(e)}", flush=True)

    # size proxy: marketcap on the session before E vs P20 of members that session
    all_e = pd.concat(raw.values())
    prev_sess = {E: pd.Timestamp(cal[np.searchsorted(cal, np.datetime64(E)) - 1])
                 for E in all_e.E.unique()}
    sess = sorted(set(prev_sess.values()))
    mc = pd.read_parquet(STORE / "daily.parquet", columns=["ticker", "date", "marketcap"],
                         filters=[[("date", "in", [d.date() for d in sess])]])
    mc["date"] = pd.to_datetime(mc.date)
    mc = mc.dropna(subset=["marketcap"]).drop_duplicates(["ticker", "date"])
    mc_by_d = {d: g.set_index("ticker").marketcap for d, g in mc.groupby("date")}
    p20 = {}
    for d in sess:
        s = mc_by_d.get(d)
        if s is None:
            continue
        m = s.reindex(list(members(d))).dropna()
        if len(m) > 400:
            p20[d] = float(np.percentile(m, SIZE_PCT))

    kept = {}
    for k, e in raw.items():
        rows = []
        for r in e.itertuples():
            d = prev_sess[r.E]
            s = mc_by_d.get(d)
            if d not in p20 or s is None or r.ticker not in s.index:
                continue
            if s[r.ticker] < p20[d] or first_px.get(r.ticker, r.E) > r.E - pd.Timedelta(days=365):
                continue
            if r.ticker in members(r.E):
                continue
            rows.append((r.ticker, r.E, float(s[r.ticker]), p20[d]))
        kept[k] = pd.DataFrame(rows, columns=["ticker", "E", "mcap", "p20"])
        print(f"{k} size/seasoning/non-member events: {len(kept[k])}", flush=True)

    need = sorted(set(kept["primary"].ticker) | set(kept["placebo"].ticker))
    b = pd.read_parquet(STORE / "stocks.parquet", columns=cols, filters=[[("ticker", "in", need)]])
    b["date"] = pd.to_datetime(b.date)
    b = b.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    px = {t: g.reset_index(drop=True) for t, g in b.groupby("ticker")}

    res = {}
    for k, e in kept.items():
        rows = []
        last_entry: dict[str, int] = {}
        for r in e.sort_values("E").itertuples():
            g = px.get(r.ticker)
            if g is None:
                continue
            d = g.date.to_numpy()
            i0 = np.searchsorted(d, np.datetime64(r.E), side="right")
            if i0 >= len(g) or (pd.Timestamp(d[i0]) - r.E).days > 10:
                continue
            ci = np.searchsorted(cal, d[i0])
            if r.ticker in last_entry and ci - last_entry[r.ticker] < SPACING:
                continue
            last_entry[r.ticker] = ci
            entry = pd.Timestamp(d[i0])
            cap_i = min(ci + HOLD, len(cal) - 1)
            cap_d = pd.Timestamp(cal[cap_i])
            how = "cap"
            exit_d = cap_d
            a = adds.get(r.ticker)
            if a is not None:
                nxt = a[(a > np.datetime64(entry)) & (a <= np.datetime64(cap_d))]
                if len(nxt):
                    exit_d, how = pd.Timestamp(nxt[0]), "added"
            i1 = np.searchsorted(d, np.datetime64(exit_d), side="right") - 1
            if i1 <= i0:
                continue
            if i1 == len(g) - 1 and pd.Timestamp(d[i1]) < exit_d and pd.Timestamp(d[i1]) < pd.Timestamp(cal[-1]) - pd.Timedelta(days=10):
                how = "delist"
            x_d = pd.Timestamp(d[i1])
            ret = g.close.iat[i1] / g.close.iat[i0] - 1
            sb = spy_c.asof(x_d) / spy_c.asof(entry) - 1
            rows.append(dict(ticker=r.ticker, E=r.E, entry=entry, exit=x_d, how=how,
                             hold=int(np.searchsorted(cal, np.datetime64(x_d)) - ci),
                             ret=ret, abn=ret - sb, mcap=r.mcap,
                             px=float(g.closeunadj.iat[i0])))
        t = pd.DataFrame(rows)
        t["exit_m"] = t.exit.dt.to_period("M").astype(str)
        t["net"] = t.abn - 2 * COST_JUDGE
        t["net_s"] = t.abn - 2 * COST_STRESS
        res[k] = t

    p, pl = res["primary"], res["placebo"]
    L = ["Study SPX-ELIG — S&P 500 GAAP-eligibility -> inclusion anticipation (N 842 -> 843)",
         f"events E {EV_LO.date()}..{EV_HI.date()}, size >= P{SIZE_PCT} of members, hold <= {HOLD}, "
         f"costs {COST_JUDGE*1e4:.0f}bp/side judged, {COST_STRESS*1e4:.0f}bp stress", ""]

    def block(name: str, t: pd.DataFrame) -> float:
        m, tt = cluster_t(t.net, t.exit_m)
        ms, ts = cluster_t(t.net_s, t.exit_m)
        mr, tr = cluster_t(t.ret - 2 * COST_JUDGE, t.exit_m)
        L.append(f"[{name}] n={len(t)} tickers={t.ticker.nunique()} hold median={t.hold.median():.0f} "
                 f"exits {t.how.value_counts().to_dict()}")
        L.append(f"  net abnormal (10bp/side): mean={m*100:.3f}% t={tt:.2f} median={t.net.median()*100:.3f}% "
                 f"hit={(t.net > 0).mean()*100:.1f}%")
        L.append(f"  stress 25bp/side: mean={ms*100:.3f}% t={ts:.2f};  raw net: mean={mr*100:.3f}% t={tr:.2f}")
        ex5 = t.drop(t.net.nlargest(5).index)
        L.append(f"  ex-top-5 mean={ex5.net.mean()*100:.3f}%")
        h1, h2 = t[t.E.dt.year <= 2012], t[t.E.dt.year >= 2013]
        a1, b1 = cluster_t(h1.net, h1.exit_m)
        a2, b2 = cluster_t(h2.net, h2.exit_m)
        L.append(f"  halves 2000-12: {a1*100:.3f}% t={b1:.2f} n={len(h1)} | 2013-26: {a2*100:.3f}% t={b2:.2f} n={len(h2)}")
        L.append(f"  add rate within hold: {(t.how == 'added').mean()*100:.1f}%  "
                 f"added mean={t[t.how=='added'].net.mean()*100:.2f}% / not-added mean={t[t.how!='added'].net.mean()*100:.2f}%")
        dl = t[t.how != "delist"]
        L.append(f"  ex-delist-during-hold: n={len(dl)} mean={dl.net.mean()*100:.3f}%")
        return m

    m_p = block("primary", p)
    m_pl = block("placebo", pl)
    L.append("")
    L.append("per-year primary (E year): " + ", ".join(
        f"{y}:{g.net.mean()*100:+.1f}%({len(g)})" for y, g in p.groupby(p.E.dt.year)))

    m, tt = cluster_t(p.net, p.exit_m)
    ms, _ = cluster_t(p.net_s, p.exit_m)
    h1, h2 = p[p.E.dt.year <= 2012], p[p.E.dt.year >= 2013]
    checks = [m > 0 and tt >= 2.0, h1.net.mean() > 0 and h2.net.mean() > 0, p.net.median() > 0,
              p.drop(p.net.nlargest(5).index).net.mean() > 0, m_pl < m_p / 3, ms > 0]
    names = ["t>=2", "both halves", "median", "ex-top-5", "placebo<1/3", "25bp stress"]
    L.append("checks: " + ", ".join(f"{n}={'PASS' if c else 'fail'}" for n, c in zip(names, checks)))
    verdict = "FAIL" if (m <= 0 or tt < 1) else ("PASS" if all(checks) else "WEAK")
    L.append(f"registered verdict: {verdict}")

    yrs = (EV_HI - EV_LO).days / 365.25
    per_yr = len(p) / yrs
    avg_hold = p.hold.mean()
    conc = per_yr * avg_hold / 252  # average simultaneous positions
    L.append("")
    L.append(f"economics: {per_yr:.1f} events/yr, mean hold {avg_hold:.0f} sessions, ~{conc:.1f} concurrent; "
             f"median entry price ${p.px.median():.0f}")
    for acct in (1_000, 3_000, 5_000, 10_000, 25_000):
        per_pos = acct / max(conc, 1.0)
        dollars = 0.5 * m * per_pos * per_yr
        L.append(f"  ${acct:>6,}: ~${dollars:,.0f}/yr abnormal at 50% capture (~{dollars/acct*100:.1f}%/yr); "
                 f"per-position ${per_pos:,.0f} vs median share ${p.px.median():.0f}")
    txt = "\n".join(L)
    print(txt)
    OUT.write_text(txt + "\n")
    p.to_csv(OUT.with_name("spx_elig_trades.csv"), index=False)


if __name__ == "__main__":
    main()
