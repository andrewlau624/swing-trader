"""Study SHAR-SURV: survivorship audit of the 2021-26 stock-panel results.

Pre-registration: the "Amendment — Study SHAR-SURV" at the end of
research/drafts/round1_prose.md (diagnostic, no judged rule, N unchanged).

Runs the free daily-bar form of the live night leg (the close is the proxy for
the live 15:40 decision; the rule is the live `loser_picks` + corr dedupe +
`night_sizing`) on two panels over 2021-02-01..2026-09-18:

  (a) Sharadar delisted-complete common stocks (nx.universe_mask "primary",
      every name regardless of today's delisting flag)
  (b) the survivor-only analogue: the same panel restricted to names that are
      NOT delisted today (master isdelisted == "N")

and reports (a)-(b). A cross-check against the local Alpaca-cache survivor
panel (book.night_days) is reported only.

This reuses nx.build_panel / collect_trades / leg_series (do not edit nx.py).
Data: ~/data/sharadar/{stocks,actions}.parquet via the installed `sharadar`
loader store; the security master is `nx.load_master` over the NX cache.

  PYTHONPATH=. .venv/bin/python research/sim/shar_surv.py [--no-local]
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from research.sim import book
from research.sim import nx

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORES = pathlib.Path.home() / "data" / "sharadar"
LO, HI = pd.Timestamp("2021-02-01"), pd.Timestamp("2026-09-18")
LOAD_LO, LOAD_HI = pd.Timestamp("2020-11-01"), pd.Timestamp("2026-09-25")
BARS = ROOT / "data" / "research" / "nx" / "run_done.json"  # sentinel only (not read)
OUT = ROOT / "research" / "sim" / "shar_surv_out.txt"
MODELS = ("tier", "flat2.5")


# ------------------------------------------------------------------ data
def load_bars(lo=LOAD_LO, hi=LOAD_HI) -> pd.DataFrame:
    """Sharadar SEP bars (split-adjusted O/H/L/C + raw closeunadj), sorted (ticker, date).

    ~/data/sharadar/stocks.parquet is the same SEP table nx expects (close = split-adjusted,
    closeunadj = raw); the local SFP (funds) table is irrelevant to the primary common-stock
    universe, so only stocks is read. Date filters push down in pyarrow; rows ~10M."""
    t = pq.read_table(
        STORES / "stocks.parquet",
        columns=["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"],
        filters=[("date", ">=", lo), ("date", "<=", hi)],
    )
    b = t.to_pandas()
    b["date"] = pd.to_datetime(b["date"])
    b = b.dropna(subset=["close", "closeunadj"])
    b = b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    return b


def load_actions() -> pd.DataFrame:
    a = pd.read_parquet(STORES / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a["date"] = pd.to_datetime(a["date"])
    return a


def load_master() -> pd.DataFrame:
    """Full security master (common/exch/delisted flags) via nx.load_master on the NX cache."""
    return nx.load_master(nx.Paths())


def collect(pn, master, act, lo=LO, hi=HI) -> dict:
    return nx.collect_trades(pn, master, act, "primary", lo, hi)


# ------------------------------------------------------------------ stats
def panel_stats(tr: dict, model: str) -> dict:
    """Per-trade net /trade = ret - 2*cost/1e4, plus the published-style portfolio night."""
    T = tr["trades"]
    nights = tr["nights"]
    if T.empty:
        return dict(n=0)
    c = nx.cost_model(model, T["cu"].to_numpy(), T["adv"].to_numpy())
    net = T["ret"].to_numpy() - 2 * c / 1e4
    day = pd.Series(net).groupby(T["date"].to_numpy()).mean()
    L = pd.Series(T["per"].to_numpy() * net).groupby(T["date"].to_numpy()).sum().reindex(nights, fill_value=0.0)
    ex5 = np.mean(np.sort(net)[:-5]) if len(net) > 5 else np.nan
    ex5L = L.drop(L.sort_values().index[-5:]).mean() if len(L) > 5 else np.nan
    return dict(n=len(T), nights=int((L != 0).sum()),
                mean=float(net.mean()), med=float(np.median(net)), hit=float((net > 0).mean()),
                clus_t=float(nx.tstat(day)), ex5=float(ex5),
                leg=float(L.mean()), leg_t=float(nx.tstat(L)), ex5_leg=float(ex5L))


def by_year(tr: dict, model: str) -> dict:
    T = tr["trades"]
    if T.empty:
        return {}
    c = nx.cost_model(model, T["cu"].to_numpy(), T["adv"].to_numpy())
    net = T["ret"].to_numpy() - 2 * c / 1e4
    yr = pd.DatetimeIndex(T["date"]).year
    return {int(y): (float(g.mean()), int(len(g))) for y, g in pd.Series(net).groupby(yr)}


def delisted_decomp(pn, master, tr_a, lo=LO, hi=HI) -> dict:
    """Eligible primary names in window: total / now-delisted; pick share from now-delisted."""
    el = nx.eligible_mask(pn) & nx.universe_mask(pn, master, "primary")
    inwin = (pn["date"] >= np.datetime64(lo)) & (pn["date"] <= np.datetime64(hi))
    uniq = pd.Series(pn["tickers"][el & inwin]).drop_duplicates()
    dset = set(master.loc[master["delisted"], "ticker"])
    n_del = int(uniq.isin(dset).sum())
    mp = master.drop_duplicates("ticker").set_index("ticker")["lastpricedate"]
    lp = pd.to_datetime(mp.reindex(uniq[uniq.isin(dset)]), errors="coerce")
    n_del_win = int(((lp >= lo) & (lp <= hi)).sum())
    T = tr_a["trades"]
    kinds = T["kind"].value_counts().to_dict() if len(T) else {}
    if T.empty:
        return dict(n_uniq=len(uniq), n_del=n_del, n_del_win=n_del_win, pick_cnt=0.0, pick_w=0.0, kinds=kinds)
    isdel = T["ticker"].isin(dset).to_numpy()
    return dict(n_uniq=int(len(uniq)), n_del=n_del, n_del_win=n_del_win,
                pick_cnt=float(isdel.mean()), pick_w=float(T.loc[isdel, "per"].sum() / T["per"].sum()),
                kinds=kinds)


def local_survivor() -> dict:
    """Cross-check (reported only): the local Alpaca-cache survivor panel per-trade."""
    nd = book.night_days()
    out = {}
    for model in MODELS:
        rets = []
        for d, x in nd.items():
            c = book.cost_bps(model, x.close, x.adv)
            rets.append(x.ret - 2 * c / 1e4)
        if not rets:
            out[model] = dict(n=0)
            continue
        net = np.concatenate(rets)
        out[model] = dict(n=len(net), mean=float(net.mean()), med=float(np.median(net)),
                          hit=float((net > 0).mean()),
                          ex5=float(np.mean(np.sort(net)[:-5])) if len(net) > 5 else np.nan)
    gross = np.concatenate([x.ret for x in nd.values()]) if nd else np.array([])
    out["gross"] = dict(n=len(gross), mean=float(gross.mean()), med=float(np.median(gross))) if len(gross) else dict(n=0)
    return dict(days=len(nd), models=out)


# ------------------------------------------------------------------ report
def _bp(x):
    return f"{x * 1e4:8.2f}bp" if np.isfinite(x) else "     nan  "


def _row(tag, s):
    return (f"  {tag:<12} n {s['n']:>5}  nights {s['nights']:>4}  "
            f"mean/trade {_bp(s['mean'])}  clus t {s['clus_t']:6.2f}  "
            f"med {_bp(s['med'])}  hit {s['hit']:5.1%}  ex5 {_bp(s['ex5'])}  "
            f"leg/night {_bp(s['leg'])} (t {s['leg_t']:.2f}, ex5 {_bp(s['ex5_leg'])})")


def build_report(a, b, dec, loc, elapsed):
    L = []
    L.append("Study SHAR-SURV — survivorship audit of the 2021-26 night leg (daily-bar form)")
    L.append(f"window {LO.date()}..{HI.date()} (bars loaded {LOAD_LO.date()}..{LOAD_HI.date()})")
    L.append("rule: live loser_picks at the close (close proxy for 15:40), corr dedupe .7, "
             "night_sizing(crowd_n=30, max_name_pct=.10); buy close(d), sell open(d+1)")
    L.append(f"(a) Sharadar delisted-complete primary common stocks | "
             f"(b) same, restricted to isdelisted=='N'")
    L.append("")
    for model in MODELS:
        L.append(f"model {model} (per-side bps)")
        L.append(_row("(a) delist-complete", a[model]))
        L.append(_row("(b) survivor-only", b[model]))
        sa, sb = a[model], b[model]
        if sa["n"] and sb["n"]:
            d = sa["mean"] - sb["mean"]
            L.append(f"  (a)-(b) mean/trade {_bp(d)}  ({d / sb['mean']:.1%} of (b))  "
                     f"leg/night {_bp(sa['leg'] - sb['leg'])}  "
                     f"n_trades {sa['n'] - sb['n']}")
        L.append("")
    L.append("by year, mean net/trade (a) | (b)")
    ya, yb = by_year(a["src"], "tier"), by_year(b["src"], "tier")
    for y in sorted(set(ya) | set(yb)):
        ca, na = ya.get(y, (np.nan, 0))
        cb, nb = yb.get(y, (np.nan, 0))
        L.append(f"  {y}  (a) {_bp(ca)} n {na:>4}   (b) {_bp(cb)} n {nb:>4}")
    L.append("")
    L.append("eligible primary names 2021-26: "
             f"{dec['n_uniq']} total, {dec['n_del']} now delisted "
             f"({dec['n_del'] / max(dec['n_uniq'], 1):.1%}); "
             f"{dec.get('n_del_win', 0)} of those have a last price in the window")
    L.append("share of (a) picks from now-delisted names: "
             f"{dec['pick_cnt']:.1%} by count, {dec['pick_w']:.1%} by per-weight")
    kc = dec.get("kinds") or {}
    if kc:
        L.append("(a) outcome kinds: " + "  ".join(f"{k} {v}" for k, v in sorted(kc.items())))
    L.append("")
    if loc is not None:
        L.append(f"cross-check (reported only) local Alpaca-cache survivor panel: {loc['days']} nights")
        g = loc["models"].get("gross", {})
        if g.get("n"):
            L.append(f"  gross       n {g['n']:>5}  mean/trade {_bp(g['mean'])}  med {_bp(g['med'])}")
        for model in MODELS:
            s = loc["models"][model]
            if not s.get("n"):
                L.append(f"  {model}: no trades")
                continue
            L.append(f"  {model:<8} n {s['n']:>5}  mean/trade {_bp(s['mean'])}  "
                     f"med {_bp(s['med'])}  hit {s['hit']:5.1%}  ex5 {_bp(s['ex5'])}")
        L.append("  (local panel is unweighted per trade; (a)/(b) use per=frac*night_tilt*gap)")
    L.append("")
    L.append(f"elapsed {elapsed:.0f}s")
    return "\n".join(L)


# ------------------------------------------------------------------ main
def run(no_local=False) -> str:
    t0 = time.time()
    master = load_master()
    bars = load_bars()
    print(f"bars {bars.shape}  master {master.shape}", file=sys.stderr)
    pn = nx.build_panel(bars)
    del bars
    act = load_actions()

    tr_a = collect(pn, master, act)
    master_b = master[~master["delisted"]].copy()
    tr_b = collect(pn, master_b, act)

    a = {m: panel_stats(tr_a, m) for m in MODELS}
    b = {m: panel_stats(tr_b, m) for m in MODELS}
    a["src"], b["src"] = tr_a, tr_b
    dec = delisted_decomp(pn, master, tr_a)
    loc = None if no_local else local_survivor()
    return build_report(a, b, dec, loc, time.time() - t0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-local", action="store_true", help="skip the local Alpaca-cache cross-check")
    args = ap.parse_args(argv)
    txt = run(no_local=args.no_local)
    OUT.write_text(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
