"""Study EDGAR-MICRO (round1_prose.md "## Study EDGAR-MICRO", N 1100-1102): the micro-cap sibling of EDGAR-SESS. In-session EDGAR
filings by listed names with prior close < $5 OR 20d ADV < $5M, traded from acceptance minute + L to the close / next open cross.
Reuses edgar_sess.py's submissions cache, universe, raw-price join, bar cache and minute helpers.
usage: PYTHONPATH=. python3 -m research.sim.edgar_micro events | bars | run
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from . import edgar_sess as es

D = es.ROOT / "data/research/edgar_micro"
EV = D / "events.parquet"
OUT = es.ROOT / "data/research/program/edgar_micro_out.txt"
ITEMS = {"T101": "1.01", "T201": "2.01", "T301": "3.01", "T502": "5.02", "T103": "1.03", "T701": "7.01", "T801": "8.01",
         "T202": "2.02", "T402": "4.02"}


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with OUT.open("a") as f:
        f.write(s + "\n")


def events() -> None:
    D.mkdir(parents=True, exist_ok=True)
    t = pd.read_parquet(es.SH / "tickers.parquet")
    t = t[(t.table == "SEP") & t.category.str.startswith("Domestic Common", na=False) & t.exchange.isin(["NASDAQ", "NYSE", "NYSEMKT"])]
    t = t[pd.to_datetime(t.lastpricedate) >= es.START].copy()
    t["cik"] = t.secfilings.str.extract(r"CIK=(\d+)")[0]
    u = t.dropna(subset=["cik"])
    rows = []
    for c in sorted(set(u.cik)):
        f = es.SUB / f"{c}.json"
        if not f.exists():
            continue
        j = json.loads(f.read_text())
        if not j:
            continue
        x = pd.DataFrame(j)
        x = x[x.form.isin(["8-K", "424B4", "424B5", "SC TO-I", "SC TO-T"])]
        x["acc"] = pd.to_datetime(x.acceptanceDateTime, utc=True, errors="coerce").dt.tz_convert(es.ET)
        x = x[(x.acc >= pd.Timestamp(es.START, tz=es.ET)) & (x.acc <= pd.Timestamp(es.END, tz=es.ET) + pd.Timedelta(hours=23))]
        hm = x.acc.dt.hour * 60 + x.acc.dt.minute
        x = x[(hm >= 9 * 60 + 35) & (hm < 15 * 60 + 30) & (x.acc.dt.weekday < 5)]
        for r in x.itertuples():
            if r.form == "8-K":
                its = set(str(r.items).split(","))
                ty = [k for k, v in ITEMS.items() if v in its]
            elif r.form.startswith("SC TO"):
                ty = ["TTO"]
            else:
                ty = ["T424"]
            for k in ty:
                rows.append((c, r.accessionNumber, k, r.acc))
    e = pd.DataFrame(rows, columns=["cik", "acc_no", "type", "acc"]).drop_duplicates(["cik", "acc_no", "type"])
    e["date"] = e.acc.dt.tz_localize(None).dt.normalize()
    tick = u.groupby("cik").ticker.apply(list).to_dict()
    allt = sorted(set(u.ticker))
    sep = pd.read_parquet(es.SH / "stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"],
                          filters=[("ticker", "in", allt), ("date", ">=", pd.Timestamp("2018-11-01").date())])
    sep["date"] = pd.to_datetime(sep.date)
    sep = sep.sort_values(["ticker", "date"])
    f = sep.closeunadj / sep.close  # SEP OHLC split-adjusted; minute bars raw -> raw prices
    for k in ("open", "high", "low"):
        sep[k] = sep[k] * f
    sep["close"] = sep.closeunadj
    sep["dv"] = sep.close * sep.volume / f
    g = sep.groupby("ticker")
    sep["adv"] = g.dv.transform(lambda s: s.rolling(20).mean().shift(1))
    sep["nxo"] = g.open.shift(-1)
    sep["pclose"] = g.close.shift(1)
    # Abdi-Ranaldo (2017) close-high-low spread estimator, 20d mean of prior days (in bp)
    eta = (np.log(sep.high) + np.log(sep.low)) / 2
    eta_n = (np.log(g.high.shift(-1)) + np.log(g.low.shift(-1))) / 2
    cl = np.log(sep.close)
    s2 = 4 * (cl - eta) * (cl - eta_n)
    sep["s2"] = s2
    sep["ar"] = 1e4 * np.sqrt(sep.groupby("ticker").s2.transform(lambda s: s.rolling(20, min_periods=10).mean().shift(2)).clip(lower=0))
    key = sep.set_index(["ticker", "date"])[["close", "adv", "nxo", "pclose", "open", "ar", "dv"]]
    out = []
    for r in e.itertuples():
        for tk in tick.get(r.cik, []):
            if (tk, r.date) in key.index:
                v = key.loc[(tk, r.date)]
                out.append((r.cik, r.acc_no, r.type, r.acc, r.date, tk, *v.values))
                break
    ev = pd.DataFrame(out, columns=["cik", "acc_no", "type", "acc", "date", "ticker", "close", "adv", "nxo", "pclose", "open", "ar", "dvday"])
    ev = ev[(ev.pclose < 5) | (ev.adv < 5e6)]
    ev = ev[(ev.pclose >= 0.5) & (ev.adv >= 1e5)]  # sub-$0.50 / < $100k ADV: no executable fill even at $2.3k
    ev["acc"] = ev.acc.astype(str)
    ev.to_parquet(EV)
    ev["yr"] = ev.date.dt.year
    log("EDGAR-MICRO events (in-session 09:35-15:30, listed, pclose<5 or ADV<5M, pclose>=0.5, ADV>=100k)")
    log(ev.groupby(["yr", "type"]).size().unstack(fill_value=0).to_string())
    log("per yr (2019-26 avg):", (ev.groupby("type").size() / 7.76).round(0).to_dict())
    log("median ADV $", ev.groupby("type").adv.median().round(-3).to_dict())
    log("median AR half-spread bp", (ev.groupby("type").ar.median() / 2).round(0).to_dict())


def bars() -> None:
    es.bars(EV)


# ---------------------------------------------------------------- analysis
FIX = {"T424": -1, "T301": -1, "T402": -1, "T103": -1, "TTO": 1}
RNG = np.random.default_rng(1100)


def _cost1(ar):
    return np.maximum(25.0, np.nan_to_num(ar, nan=50.0) / 2) + 5.0


def panel() -> pd.DataFrame:
    ev = pd.read_parquet(EV)
    ev["acc"] = pd.to_datetime(ev.acc)
    rows, cache = [], {}
    for r in ev.itertuples():
        k = (r.ticker, r.date)
        if k not in cache:
            cache[k] = es._load_bars(r.ticker, r.date)
        b = cache[k]
        if b is None or len(b) < 20:
            continue
        m = r.acc.hour * 60 + r.acc.minute - 570

        def at(mm):
            return dict(p0=es._px(b, mm - 1, "c"), pm30=es._px(b, mm - 30, "c"), c1=es._px(b, mm + 1, "c"),
                        **{f"e{L}": es._px(b, mm + L, "o") for L in (1, 2, 5)})
        rest = b[b.index >= m + 2]
        d = dict(type=r.type, ticker=r.ticker, date=r.date, m=m, adv=r.adv, ar=r.ar, close=r.close, nxo=r.nxo, cik=r.cik,
                 acc_no=r.acc_no, dvrest=float((rest.c * rest.v).sum()), **at(m))
        # placebo minutes: same symbol-day, >= 60 min from acceptance, inside 09:35-15:30
        cand = [x for x in range(5, 360) if abs(x - m) >= 60]
        if cand:
            for j, mm in enumerate(RNG.choice(cand, size=5)):
                d.update({f"pl{j}_{k2}": v for k2, v in at(int(mm)).items()})
        rows.append(d)
    p = pd.DataFrame(rows)
    p["cost"] = _cost1(p.ar)
    return p


def trades(p, rule, L=2, ex="EOD", pref=""):
    ent, p0 = p[f"{pref}e{L}"], p[f"{pref}p0"]
    pre = (ent / p0 - 1) * 1e4
    xp = p.close if ex == "EOD" else p.nxo
    post = (xp / ent - 1) * 1e4
    if rule == "CONT":
        sgn = np.sign(pre).where(pre.abs() >= 100, 0)
    elif rule == "REV":
        sgn = -np.sign(pre).where(pre.abs() >= 100, 0)
    else:
        sgn = p.type.map(FIX).fillna(0)
    g = sgn * post
    c = 2 * p.cost
    ok = (sgn != 0) & ent.notna() & xp.notna() & p0.notna()
    return pd.DataFrame({"gross": g[ok], "net": (g - c)[ok], "net2": (g - 2 * c)[ok], "date": p.date[ok], "type": p.type[ok],
                         "dvrest": p.dvrest[ok], "adv": p.adv[ok]})


def run() -> None:
    from .ibs_voltilt import dsr
    OUT.write_text("")
    p = panel()
    p = p.dropna(subset=["p0", "e2"])
    bad = ((p.p0 / p.close - 1).abs() > 0.5) | ((p.nxo / p.close - 1).abs() > 0.5)
    log(f"EDGAR-MICRO panel: dropped {int(bad.sum())} events with minute vs official price > 50% apart (ticker/split mismatch)")
    p = p[~bad].copy()
    small = p.type.map(p[p.date <= "2022-12-31"].type.value_counts()).fillna(0) < 30
    p.loc[small & ~p.type.isin(list(FIX)), "type"] = "OTHER"
    ch, ju = p[p.date <= "2022-12-31"], p[p.date > "2022-12-31"]
    log(f"{len(p)} events with bars (choose {len(ch)}, judge {len(ju)}); median one-way cost {p.cost.median():.0f}bp; "
        f"median rest-of-day $vol after m+2 ${p.dvrest.median():,.0f}")
    log(p.groupby([p.date.dt.year, "type"]).size().unstack(fill_value=0).to_string())
    tot = (p.close / p.p0 - 1) * 1e4
    a1, a2 = (p.c1 / p.p0 - 1) * 1e4, (p.e2 / p.p0 - 1) * 1e4
    pre30 = (p.p0 / p.pm30 - 1) * 1e4
    plpre = pd.concat([(p[f"pl{j}_p0"] / p[f"pl{j}_pm30"] - 1) * 1e4 for j in range(5)])
    pla2 = pd.concat([(p[f"pl{j}_e2"] / p[f"pl{j}_p0"] - 1) * 1e4 for j in range(5)])
    log("\nDiagnostics (all events, not gates):")
    log(f"  |m-1 -> m+2 open| median {a2.abs().median():.0f}bp (placebo minutes {pla2.abs().median():.0f}bp); share >= 100bp "
        f"{(a2.abs() >= 100).mean():.3f} (placebo {(pla2.abs() >= 100).mean():.3f})")
    log(f"  |m-30 -> m-1| median {pre30.abs().median():.0f}bp (placebo {plpre.abs().median():.0f}bp)")
    big = tot.abs() >= 200
    for ty, g in p[big].groupby("type"):
        i = g.index
        sh1 = (np.sign(tot[i]) * a1[i] / tot[i].abs()).median()
        sh2 = (np.sign(tot[i]) * a2[i] / tot[i].abs()).median()
        log(f"  {ty:5s} n {len(g):5d} |m-1->close|>=200bp: median share done by m+1 {sh1:+.2f}, m+2 open {sh2:+.2f}; "
            f"median |m-1->close| {tot[i].abs().median():.0f}bp; |m-1->m+2| {a2[i].abs().median():.0f}bp; |m-30->m-1| "
            f"{pre30[i].abs().median():.0f}bp")
    cells = []
    log("\nCHOOSE 2019-2022 (L=2), net of max(25, AR/2)+5bp per side:")
    for ty in sorted(p.type.unique()):
        for rule in ("CONT", "REV", "FIX"):
            if rule == "FIX" and ty not in FIX:
                continue
            for ex in ("EOD", "NXO"):
                d = es.summ(trades(ch[ch.type == ty], rule, 2, ex))
                sel = d.get("n", 0) >= 30 and d["net"] > 0 and d["t"] >= 2
                cells.append((ty, rule, ex, sel))
                log(f"  {ty:5s} {rule:4s} {ex}: {es.fmt(d)}{'  SELECTED' if sel else ''}")
    for rule in ("CONT", "REV"):
        for ex in ("EOD", "NXO"):
            log(f"  ALL   {rule:4s} {ex}: {es.fmt(es.summ(trades(ch, rule, 2, ex)))}  (descriptive, not a cell)")
    sel = [c for c in cells if c[3]]
    log(f"\nGrid {len(cells)} cells; selected {len(sel)}")
    if not sel:
        return
    log("\nJUDGE 2023-01..2026-10-05 (selected cells only, one look):")
    yrs = (pd.Timestamp(es.END) - pd.Timestamp("2023-01-01")).days / 365.25
    for ty, rule, ex, _ in sel:
        q = ju[ju.type == ty]
        t2 = trades(q, rule, 2, ex)
        d = es.summ(t2)
        d5 = es.summ(trades(q.dropna(subset=["e5"]), rule, 5, ex))
        d1 = es.summ(trades(q.dropna(subset=["e1"]), rule, 1, ex))
        h1, h2 = es.summ(t2[t2.date <= "2024-12-31"]), es.summ(t2[t2.date > "2024-12-31"])
        pl = []
        for k in range(200):
            j = k % 5
            sub = q.rename(columns={f"pl{j}_{c}": f"PL{c}" for c in ("p0", "e1", "e2", "e5")})
            tp = trades(sub.sample(frac=1, replace=True, random_state=k), rule, 2, ex, pref="PL")
            pl.append(tp.net.mean() if rule != "FIX" else np.nan)
        pl = np.array(pl)
        pv = np.nanmean(pl >= d.get("net", np.nan)) if rule != "FIX" else np.nan
        dd = dsr(t2.net.values, 1102) if len(t2) > 10 else np.nan
        log(f"  {ty} {rule} {ex}: {es.fmt(d)}")
        log(f"     L=1 {d1.get('net', np.nan):+.1f} | L=5 {d5.get('net', np.nan):+.1f} | 2023-24 {h1.get('net', np.nan):+.1f} (n "
            f"{h1.get('n', 0)}) | 2025-26 {h2.get('net', np.nan):+.1f} (n {h2.get('n', 0)}) | placebo mean {np.nanmean(pl):+.1f} "
            f"p {pv:.3f} | DSR {dd:.3f} | events/yr {len(t2) / yrs:.0f} | ceiling 50% capture "
            f"{len(t2) / yrs * d.get('net', 0) / 1e4 * 0.5 * 100:+.1f}pp | median 5% rest-of-day $vol ${0.05 * t2.dvrest.median():,.0f}")


def quotes() -> None:
    """Validate the AR spread proxy: Alpaca SIP NBBO half-spread in the 2 minutes after acceptance+1, 300 random events."""
    import re
    import requests
    from .auction_fetch import _env
    H = _env()
    ev = pd.read_parquet(EV).sample(300, random_state=1101)
    out = []
    for r in ev.itertuples():
        t0 = pd.Timestamp(r.acc).tz_convert("UTC") + pd.Timedelta(minutes=1)
        sym = re.sub(r"\d+$", "", r.ticker)
        try:
            q = requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/quotes", headers=H, timeout=30,
                             params=dict(start=t0.isoformat(), end=(t0 + pd.Timedelta(minutes=2)).isoformat(), feed="sip",
                                         limit=2000)).json().get("quotes") or []
        except Exception:
            continue
        x = pd.DataFrame(q)
        if x.empty:
            continue
        x = x[(x.bp > 0) & (x.ap > x.bp)]
        if x.empty:
            continue
        hs = ((x.ap - x.bp) / (x.ap + x.bp) * 1e4).median()
        out.append((r.type, r.adv, r.pclose, r.ar / 2, hs))
    o = pd.DataFrame(out, columns=["type", "adv", "px", "ar_half", "nbbo_half"])
    o.to_parquet(D / "quote_check.parquet")
    log(f"\nSpread check (n {len(o)} events, NBBO half-spread in minutes acc+1..+3): median {o.nbbo_half.median():.0f}bp, "
        f"p75 {o.nbbo_half.quantile(.75):.0f}bp; AR half median {o.ar_half.median():.0f}bp; registered one-way cost "
        f"median {np.median(_cost1(o.ar_half * 2)):.0f}bp; share of events NBBO half > registered one-way cost "
        f"{(o.nbbo_half > _cost1(o.ar_half * 2)).mean():.2f}")
    o["b"] = pd.cut(o.adv, [0, 5e5, 1e6, 2e6, 5e6, 1e12])
    log(o.groupby("b").agg(n=("nbbo_half", "size"), nbbo=("nbbo_half", "median"), ar=("ar_half", "median")).round(0).to_string())


if __name__ == "__main__":
    {"events": events, "bars": bars, "run": run, "quotes": quotes}[sys.argv[1]]()
