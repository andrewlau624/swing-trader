"""Study BETA-HEDGE (N 1103-1105): hedge each leg with a short of its own measured beta in QQQ (SPY arm, PSQ Roth form).

Pre-registered in research/drafts/round1_prose.md ("Study BETA-HEDGE") before any hedged number was computed.
Reuses: ibs_oos._trades (exact live IBS rule on the 2016-20 ETF series), book.Sim/night_days (live night rule, tilt,
weekend scale, cost), weight_grid.load_night/returns20 (night candidates + Sharadar closes), book_decomp._ols (NW t).

Beta: OLS slope of close-to-close returns on the index over the 60 sessions before the entry (IBS: through the signal
close d, known before the d+1 open; night: through d-1, since the 15:40 decision precedes d's close). < 40 obs -> 1.0.
Windows: IBS open(d+1) -> open(d+2); night close(d) -> open(d+1). Daily bars are the regular-session OHLC (Alpaca SIP
research panel; Sharadar; Yahoo daily for the live window), so open/close are the official auction prints.

Run: PYTHONPATH=. python3 -m research.sim.beta_hedge
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import ibs_oos as IO
from . import weight_grid as W
from .book_decomp import _ols

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/beta_hedge_out.txt"
LIVE = ROOT / "data/research/beta_hedge"
SH = pathlib.Path.home() / "data/sharadar"
WIN, MINOBS, CLIP = 60, 40, 4.0
HC = {"QQQ": 1.0, "SPY": 1.0, "PSQ": 3.0, "SH": 3.0}      # hedge cost bp/side
MARGIN = 0.10
LINES: list[str] = []


def log(s: str = "") -> None:
    print(s, flush=True); LINES.append(s)


# ------------------------------------------------------------------ helpers
def roll_beta(R: pd.DataFrame, idx: pd.Series) -> pd.DataFrame:
    """beta_t(s) = cov/var over the WIN rows ending at t (inclusive), per column vs idx."""
    X = R.reindex(idx.index)
    m = X.notna() & idx.notna().values[:, None]
    x = X.where(m); y = pd.DataFrame(np.repeat(idx.values[:, None], X.shape[1], 1), index=X.index,
                                    columns=X.columns).where(m)
    n = m.rolling(WIN, min_periods=1).sum()
    sx, sy = x.rolling(WIN, min_periods=1).sum(), y.rolling(WIN, min_periods=1).sum()
    sxy, syy = (x * y).rolling(WIN, min_periods=1).sum(), (y * y).rolling(WIN, min_periods=1).sum()
    b = (sxy - sx * sy / n) / (syy - sy * sy / n)
    return b.where(n >= MINOBS).clip(-CLIP, CLIP)


def nw_t(x: pd.Series) -> float:
    y = np.asarray(x, float); y = y[np.isfinite(y)]
    b, t, _ = _ols(y, np.ones((len(y), 1)), 5)
    return float(t[0])


def reg(y: pd.Series, f: pd.Series) -> tuple[float, float, float, float]:
    df = pd.concat([y, f], axis=1).dropna()
    b, t, _ = _ols(df.iloc[:, 0].values, np.column_stack([np.ones(len(df)), df.iloc[:, 1].values]), 5)
    return b[0] * 252, t[0], b[1], t[1]


def st(r: pd.Series) -> dict:
    r = r.fillna(0.0)
    eq = (1 + r).cumprod(); yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if len(r) > 20 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    w21 = ((1 + r).rolling(21).apply(np.prod, raw=True) - 1).min()
    return dict(cagr=cagr, dd=dd, mar=cagr / abs(dd) if dd < 0 else np.nan, sh=sh, w21=w21,
                mean=r.mean() * 1e4, t=nw_t(r))


def fs(d: dict) -> str:
    return (f"CAGR {d['cagr']*100:6.1f}%  maxDD {d['dd']*100:6.1f}%  MAR {d['mar']:5.2f}  Sharpe {d['sh']:5.2f}  "
            f"worst21 {d['w21']*100:6.1f}%  mean {d['mean']:6.2f}bp/day NW t {d['t']:5.2f}")


def window(r: pd.Series, a: str, b: str) -> float:
    x = r.loc[a:b].fillna(0)
    return (1 + x).prod() - 1 if len(x) else np.nan


def lever(rh: pd.Series, inv: pd.Series, dd_target: float, hratio: float) -> tuple[float, pd.Series]:
    dd_h = st(rh)["dd"]
    L = min(abs(dd_target) / abs(dd_h), 2.0 / (1 + abs(hratio))) if dd_h < 0 else 1.0
    rl = L * rh - np.where(inv, max(L - 1, 0) * MARGIN / 252, 0.0)
    return L, pd.Series(rl, index=rh.index)


def report_leg(name: str, ru: pd.Series, h: dict, inv: pd.Series, f: pd.Series, judge: tuple, halves: list,
               cost_unit: dict) -> dict:
    """ru: unhedged daily leg return; h: arm -> (hedged return, avg hedge ratio on invested days);
    f: same-window QQQ return (for the alpha/beta regression); cost_unit: arm -> daily cost of 1x the registered costs."""
    a, b = judge
    log(f"\n=== {name}: judge {a}..{b}")
    out = {}
    u = st(ru.loc[a:b]); log(f"  unhedged        {fs(u)}")
    al, at, be, bt = reg(ru.loc[a:b], f.loc[a:b] * inv.loc[a:b])
    log(f"  unhedged regression on same-window QQQ (invested days): alpha {al*100:5.1f}%/yr NW t {at:4.2f}, "
        f"beta {be:4.2f} (t {bt:4.1f})")
    for arm, (rh, hr) in h.items():
        x = st(rh.loc[a:b])
        L, rl = lever(rh.loc[a:b], inv.loc[a:b], u["dd"], hr)
        lv = st(rl)
        g1, g2, g3 = x["t"] >= 2, (x["mar"] >= 1.3 * u["mar"]) if u["mar"] > 0 else x["mar"] > 0, lv["cagr"] >= u["cagr"]
        log(f"  hedged {arm:8s} {fs(x)}  (avg hedge ratio {hr:4.2f})")
        log(f"     levered L={L:4.2f} to unhedged maxDD: {fs(lv)}")
        log(f"     GATES G1 t>=2 {'PASS' if g1 else 'fail'} | G2 MAR>=1.3x {'PASS' if g2 else 'fail'} | "
            f"G3 levered CAGR>=unhedged {'PASS' if g3 else 'fail'}  => {'PASS' if g1 and g2 and g3 else 'FAIL'}")
        out[arm] = dict(u=u, h=x, L=L, lv=lv, gates=(g1, g2, g3))
    # beta vs alpha split of the raw leg
    bx = (ru - h["QQQ"][0]).loc[a:b]   # hedge P&L incl. its cost
    log(f"  share of raw leg mean explained by the QQQ beta position: {bx.mean()/ru.loc[a:b].mean()*100:5.0f}%")
    for lab, lo, hi in halves:
        log(f"  half {lab}: unhedged {st(ru.loc[lo:hi])['mean']:6.2f}bp t {st(ru.loc[lo:hi])['t']:4.2f} | "
            + " | ".join(f"{arm} {st(rh.loc[lo:hi])['mean']:6.2f}bp t {st(rh.loc[lo:hi])['t']:4.2f}"
                         for arm, (rh, _) in h.items()))
    for k in (2, 3):
        log(f"  cost x{k}: unhedged {st(ru.loc[a:b] - (k-1)*cost_unit['U'].loc[a:b])['mean']:6.2f}bp | "
            + " | ".join(f"{arm} {st(rh.loc[a:b] - (k-1)*cost_unit[arm].loc[a:b])['mean']:6.2f}bp "
                         f"t {st(rh.loc[a:b] - (k-1)*cost_unit[arm].loc[a:b])['t']:4.2f}" for arm, (rh, _) in h.items()))
    rhq = h["QQQ"][0].loc[a:b]
    top = rhq.nlargest(5).index
    log(f"  ex-top-5 days: unhedged {st(ru.loc[a:b].drop(ru.loc[a:b].nlargest(5).index))['mean']:6.2f}bp | "
        f"QQQ-hedged {st(rhq.drop(top))['mean']:6.2f}bp t {st(rhq.drop(top))['t']:4.2f}; "
        f"invested-day median: unhedged {ru.loc[a:b][inv.loc[a:b]].median()*1e4:5.1f}bp "
        f"hedged {rhq[inv.loc[a:b]].median()*1e4:5.1f}bp, hit {(rhq[inv.loc[a:b]]>0).mean()*100:3.0f}%")
    return out


def stress(name: str, ru: pd.Series, h: dict) -> None:
    for lab, a, b in (("2020-02-19..04-30", "2020-02-19", "2020-04-30"), ("2022", "2022-01-01", "2022-12-31"),
                      ("2018Q4", "2018-10-01", "2018-12-31")):
        if len(ru.loc[a:b]) < 10:
            continue
        log(f"  stress {name} {lab}: unhedged {window(ru, a, b)*100:6.1f}% (DD {st(ru.loc[a:b])['dd']*100:5.1f}%) | "
            + " | ".join(f"{arm} {window(rh, a, b)*100:6.1f}% (DD {st(rh.loc[a:b])['dd']*100:5.1f}%)"
                         for arm, (rh, _) in h.items()))


# ------------------------------------------------------------------ data
def sharadar_px(tickers: list[str]) -> dict:
    f = pd.read_parquet(SH / "funds.parquet", columns=["ticker", "date", "open", "close"],
                        filters=[("ticker", "in", tickers)])
    f["date"] = pd.to_datetime(f.date)
    return {k: f.pivot(index="date", columns="ticker", values=k).sort_index() for k in ("open", "close")}


def yahoo(sym: str) -> pd.DataFrame:
    p = LIVE / "yahoo" / f"{sym}.json"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=1767225600&period2=1794787200"
               f"&interval=1d")
        p.write_bytes(subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", url], capture_output=True).stdout)
    try:
        r = json.loads(p.read_text())["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        ix = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
        return pd.DataFrame({"open": q["open"], "close": q["close"]}, index=ix).dropna()
    except Exception:
        return pd.DataFrame(columns=["open", "close"])


# ------------------------------------------------------------------ IBS leg
def ibs_leg(P: dict, idxs: list[str], psq: dict) -> tuple:
    O, C = P["open"], P["close"]
    R = C.pct_change(fill_method=None)
    tr = IO._trades("ibs_lo")                                      # exact live rule (raw prices)
    days = C.index
    nxt = {d: (days[i + 1], days[i + 2]) for i, d in enumerate(days[:-2])}
    betas = {k: roll_beta(R[IO.EQ18], R[k]) for k in idxs}
    sess = days[(days >= "2017-01-01")]
    ru = pd.Series(0.0, index=sess); inv = pd.Series(False, index=sess)
    hr = {k: pd.Series(0.0, index=sess) for k in idxs}
    for d, g in tr.groupby(level=0):
        if d not in ru.index:
            continue
        ru[d] = g["ret"].mean() - 2 * 1e-4; inv[d] = True
        for k in idxs:
            hr[k][d] = np.nanmean([betas[k].at[d, s] if np.isfinite(betas[k].at[d, s]) else 1.0 for s in g["sym"]])
    f = {}
    for k in idxs:
        f[k] = pd.Series({d: O.at[nxt[d][1], k] / O.at[nxt[d][0], k] - 1 for d in sess if d in nxt})
    pf = pd.Series({d: psq["open"].at[nxt[d][1], "PSQ"] / psq["open"].at[nxt[d][0], "PSQ"] - 1
                    if nxt[d][0] in psq["open"].index and nxt[d][1] in psq["open"].index else np.nan
                    for d in sess if d in nxt})
    return ru, inv, hr, f, pf


# ------------------------------------------------------------------ night leg (backtest 2021-26)
def night_leg(s: B.Sim, Rn: pd.DataFrame, ixr: dict, idxs: list[str], psq: dict) -> tuple:
    sess = s.days
    ru = pd.Series(0.0, index=sess); inv = pd.Series(False, index=sess)
    hr = {k: pd.Series(0.0, index=sess) for k in idxs}; cu = pd.Series(0.0, index=sess)
    betas = {k: roll_beta(Rn, ixr[k]).shift(1) for k in idxs}        # through d-1
    miss = tot = 0
    for d in sess:
        nd = s.N.get(d)
        if nd is None:
            continue
        w = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        per = nd.frac * w * (0.5 if s._gap(d) > 1 else 1.0)
        v = per / nd.price * nd.close
        ru[d] = float((v * (nd.ret - 2 * 2.5e-4)).sum()); inv[d] = True
        cu[d] = float(v.sum() * 2 * 2.5e-4)
        for k in idxs:
            b = np.array([betas[k].at[d, x] if (x in betas[k].columns and d in betas[k].index
                                                 and np.isfinite(betas[k].at[d, x])) else np.nan for x in nd.syms])
            if k == "QQQ":
                miss += int(np.isnan(b).sum()); tot += len(b)
            hr[k][d] = float((v * np.where(np.isnan(b), 1.0, b)).sum())
    C, O = s.C, s.O
    f = {k: (O[k].shift(-1) / C[k] - 1).reindex(sess) for k in idxs}
    pon = (psq["open"]["PSQ"].shift(-1) / psq["close"]["PSQ"] - 1).reindex(sess)
    return ru, inv, hr, f, pon, cu, miss / max(tot, 1)


# ------------------------------------------------------------------ live night/IBS from fills
def live_legs() -> dict:
    f = pd.read_json(LIVE / "daily-fills-live.jsonl", lines=True)
    f["t"] = pd.to_datetime(f.filled_at, utc=True).dt.tz_convert("America/New_York")
    f["d"] = f.t.dt.normalize().dt.tz_localize(None)
    out = {}
    for leg in ("night", "ibs"):
        g = f[f.leg == leg].sort_values("t")
        rows = []
        for sym, gs in g.groupby("sym"):
            buys = gs[gs.side == "buy"]; sells = gs[gs.side == "sell"]
            for _, b in buys.iterrows():
                s = sells[sells.t > b.t]
                if len(s):
                    s = s.iloc[0]
                    rows.append((b.d, sym, b.qty * b.fill_px, b.qty * (s.fill_px - b.fill_px), s.d))
        out[leg] = pd.DataFrame(rows, columns=["d", "sym", "notional", "pnl", "exit_d"])
    return out


def main() -> None:
    idxs = ["QQQ", "SPY"]
    log("Study BETA-HEDGE (N 1103-1105) -- one look. Pre-reg: research/drafts/round1_prose.md")
    log("Excess-of-cash comparison: idle capital earns 0 in every arm. Costs: IBS 1bp/side, night 2.5bp/side, "
        "QQQ/SPY 1bp/side, PSQ 3bp/side.")
    P = D.etf()
    psq = sharadar_px(["PSQ", "SH", "QQQ"])

    # ---------------- IBS
    ru, inv, hr, f, pf = ibs_leg(P, idxs, psq)
    H = {}; CU = {"U": pd.Series(np.where(inv, 2e-4, 0.0), index=ru.index)}
    for k in idxs:
        H[k] = (ru - hr[k] * f[k].reindex(ru.index).fillna(0) - 2 * HC[k] / 1e4 * hr[k].abs(),
                hr[k][inv].mean())
        CU[k] = CU["U"] + 2 * HC[k] / 1e4 * hr[k].abs()
    # Roth form: no margin -> long a/(1+b) of the leg, PSQ b/(1+b)
    b = hr["QQQ"]
    roth = ((ru + b * (pf.reindex(ru.index).fillna(0) - 2 * HC["PSQ"] / 1e4)) / (1 + b.abs()))
    H["PSQ-Roth"] = (roth.where(inv, 0.0), (b / (1 + b.abs()))[inv].mean())
    CU["PSQ-Roth"] = (CU["U"] + 2 * HC["PSQ"] / 1e4 * b.abs()) / (1 + b.abs())
    log(f"\nIBS leg: {int(inv.sum())} signal days 2017-26, avg QQQ beta of picks {hr['QQQ'][inv].mean():.2f}, "
        f"SPY beta {hr['SPY'][inv].mean():.2f}")
    res_ibs = report_leg("IBS leg (N 1103 QQQ / N 1105 SPY)", ru, H, inv, f["QQQ"].reindex(ru.index), ("2017-01-01", "2020-12-31"),
                         [("2017-18", "2017", "2018"), ("2019-20", "2019", "2020")], CU)
    stress("IBS", ru, H)
    report_leg("IBS leg DESCRIPTIVE 2021-26", ru, H, inv, f["QQQ"].reindex(ru.index), ("2021-01-01", "2026-12-31"),
               [("2021-23", "2021", "2023"), ("2024-26", "2024", "2026")], CU)
    stress("IBS", ru, H)
    ibs = (ru, inv, H, CU)

    # ---------------- night backtest 2021-26
    x = W.load_night(); D.night_candidates = lambda raw=False: x
    Rn = W.returns20(x); D.returns20 = lambda: Rn
    s = B.Sim(noise_syms=())
    ixc = sharadar_px(["QQQ", "SPY"])
    ixr = {k: ixc["close"][k].pct_change(fill_method=None) for k in idxs}
    nru, ninv, nhr, nf, pon, ncu, miss = night_leg(s, Rn, ixr, idxs, psq)
    NH = {}; NCU = {"U": ncu}
    for k in idxs:
        NH[k] = (nru - nhr[k] * nf[k].fillna(0) - 2 * HC[k] / 1e4 * nhr[k].abs(), (nhr[k][ninv]).mean())
        NCU[k] = ncu + 2 * HC[k] / 1e4 * nhr[k].abs()
    nb = nhr["QQQ"]
    NH["PSQ-Roth"] = (((nru + nb * (pon.fillna(0) - 2 * HC["PSQ"] / 1e4)) / (1 + nb.abs())).where(ninv, 0.0),
                      (nb / (1 + nb.abs()))[ninv].mean())
    NCU["PSQ-Roth"] = (ncu + 2 * HC["PSQ"] / 1e4 * nb.abs()) / (1 + nb.abs())
    log(f"\nNight leg backtest: {int(ninv.sum())} nights, names without a 60d beta (-> 1.0): {miss*100:.1f}%, "
        f"avg position-weighted QQQ beta {nb[ninv].mean():.2f} (median {nb[ninv].median():.2f}), "
        f"SPY {nhr['SPY'][ninv].mean():.2f}")
    report_leg("Night leg DESCRIPTIVE 2021-26 backtest (N 1104 judge is live)", nru, NH, ninv, nf["QQQ"],
               ("2021-01-01", "2026-12-31"), [("2021-23", "2021", "2023"), ("2024-26", "2024", "2026")], NCU)
    stress("night", nru, NH)

    # ---------------- combined book 0.5/0.5, 2021-26 descriptive
    log("\n=== Combined book 0.5 IBS / 0.5 night (config.yaml weights), 2021-02..2026-09, fractional, descriptive")
    ix = nru.index
    bu = 0.5 * ibs[0].reindex(ix).fillna(0) + 0.5 * nru
    binv = ibs[1].reindex(ix).fillna(False) | ninv
    bh = {k: (0.5 * ibs[2][k][0].reindex(ix).fillna(0) + 0.5 * NH[k][0], 0.5 * (ibs[2][k][1] + NH[k][1]))
          for k in ("QQQ", "SPY", "PSQ-Roth")}
    bh["IBS-cash+night-QQQ"] = (0.5 * NH["QQQ"][0], 0.5 * NH["QQQ"][1])
    bh["IBS-unh+night-QQQ"] = (0.5 * ibs[0].reindex(ix).fillna(0) + 0.5 * NH["QQQ"][0], 0.5 * NH["QQQ"][1])
    bcu = {"U": 0.5 * ibs[3]["U"].reindex(ix).fillna(0) + 0.5 * NCU["U"]}
    for k in ("QQQ", "SPY", "PSQ-Roth"):
        bcu[k] = 0.5 * ibs[3][k].reindex(ix).fillna(0) + 0.5 * NCU[k]
    bcu["IBS-cash+night-QQQ"] = 0.5 * NCU["QQQ"]
    bcu["IBS-unh+night-QQQ"] = 0.5 * ibs[3]["U"].reindex(ix).fillna(0) + 0.5 * NCU["QQQ"]
    qf = (s.O["QQQ"].shift(-1) / s.C["QQQ"] - 1).reindex(ix)
    report_leg("Book", bu, bh, binv, qf, ("2021-01-01", "2026-12-31"),
               [("2021-23", "2021", "2023"), ("2024-26", "2024", "2026")], bcu)
    stress("book", bu, bh)

    # ---------------- live judge (night) + live IBS descriptive
    log("\n=== LIVE taxable fills (server logs/daily-fills-live.jsonl), per-session sleeve return on deployed capital")
    lv = live_legs()
    q = {k: yahoo(k) for k in ("QQQ", "SPY", "PSQ", "SH")}
    qd = q["QQQ"].index
    for leg in ("night", "ibs"):
        g = lv[leg]
        syms = sorted(g.sym.unique())
        Ry = pd.DataFrame({sy: yahoo(sy)["close"] for sy in syms}).sort_index().pct_change(fill_method=None)
        bq = roll_beta(Ry, q["QQQ"]["close"].pct_change(fill_method=None).reindex(Ry.index))
        rows = []
        for d, gd in g.groupby("d"):
            ex = gd.exit_d.iloc[0]
            if leg == "night":
                bb = bq.shift(1)
                fq = q["QQQ"].at[ex, "open"] / q["QQQ"].at[d, "close"] - 1 if ex in qd and d in qd else np.nan
                fs_ = q["SPY"].at[ex, "open"] / q["SPY"].at[d, "close"] - 1 if ex in qd and d in qd else np.nan
            else:
                bb = bq.shift(1)  # signal close = previous session
                fq = q["QQQ"].at[ex, "open"] / q["QQQ"].at[d, "open"] - 1 if ex in qd and d in qd else np.nan
                fs_ = q["SPY"].at[ex, "open"] / q["SPY"].at[d, "open"] - 1 if ex in qd and d in qd else np.nan
            bet = np.array([bb.at[d, sy] if d in bb.index and np.isfinite(bb.at[d, sy]) else 1.0 for sy in gd.sym])
            wn = gd.notional.values / gd.notional.sum()
            rows.append((d, gd.pnl.sum() / gd.notional.sum(), float((wn * bet).sum()), fq, fs_, len(gd),
                         int(np.sum([not (d in bb.index and np.isfinite(bb.at[d, sy])) for sy in gd.sym]))))
        L = pd.DataFrame(rows, columns=["d", "r", "beta", "qqq", "spy", "n", "nobeta"]).set_index("d")
        L["rh"] = L.r - L.beta * L.qqq - 2 * 1e-4 * L.beta.abs()
        sess = q["QQQ"].loc[L.index.min():"2026-11-05"].index
        ru_l, rh_l = L.r.reindex(sess).fillna(0), L.rh.reindex(sess).fillna(0)
        log(f"\n  {leg.upper()} live: {len(L)} sessions with trades of {len(sess)}, {int(L.n.sum())} round trips, "
            f"{int(L.nobeta.sum())} names without a 60d beta (-> 1.0); position beta mean {L.beta.mean():.2f} "
            f"median {L.beta.median():.2f}")
        u, hh = st(ru_l), st(rh_l)
        log(f"   unhedged        sum {L.r.sum()*100:6.2f}%  per-session mean {L.r.mean()*1e4:6.1f}bp t {nw_t(L.r):5.2f}  "
            f"maxDD {u['dd']*100:6.2f}%  worst day {L.r.min()*100:5.2f}%")
        log(f"   QQQ-hedged      sum {L.rh.sum()*100:6.2f}%  per-session mean {L.rh.mean()*1e4:6.1f}bp t {nw_t(L.rh):5.2f}  "
            f"maxDD {hh['dd']*100:6.2f}%  worst day {L.rh.min()*100:5.2f}%")
        if L.qqq.notna().sum() > 5:
            a_, at_, b_, bt_ = reg(L.r, L.qqq)
            log(f"   regression on same-window QQQ: beta {b_:5.2f} (t {bt_:4.1f}), corr {L.r.corr(L.qqq):5.2f}, "
                f"QQQ window sum {L.qqq.sum()*100:5.2f}%")
        if leg == "night":
            log(f"   G1 (t>=2) {'PASS' if nw_t(L.rh) >= 2 else 'fail'}; G2 MAR / G3 levered need a drawdown history: "
                f"{len(L)} sessions < 60 -> UNDERPOWERED by registration")

    # ---------------- money: whole-share hedge granularity at today's prices
    log("\n=== Money: hedge share granularity at current prices (Yahoo last close)")
    px = {k: float(q[k]["close"].iloc[-1]) for k in ("QQQ", "PSQ", "SH", "SPY")}
    log("  last close: " + "  ".join(f"{k} ${v:,.2f}" for k, v in px.items()))
    bi, bn = hr["QQQ"][inv], nb[ninv]
    for A in (2300, 10000, 25000, 100000):
        parts = []
        for lab, bs in (("IBS", bi), ("night", bn)):
            tgt = 0.5 * A * bs.abs()
            for k in ("QQQ", "PSQ", "SH"):
                sh_ = np.round(tgt / px[k])
                err = (np.abs(sh_ * px[k] - tgt) / tgt.where(tgt > 0)).median()
                zero = (sh_ == 0).mean()
                parts.append(f"{lab}/{k}: med err {err*100:4.0f}% zero {zero*100:3.0f}%")
        log(f"  ${A:>7,}: " + " | ".join(parts))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    sys.exit(main())
