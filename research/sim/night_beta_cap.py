"""Study NIGHT-BETA-CAP (N 1108-1110): cap the night leg's position beta to QQQ at 1.0, or drop picks with beta > 2.

Pre-registered in research/drafts/round1_prose.md ("Study NIGHT-BETA-CAP") before any capped return was computed.
Section 1 is the Step-1 diagnostic (why live position beta ~2.45 vs the "0.49" BETA-HEDGE printed for the backtest).
Reuses: book.Sim (live night rule, tilt, weekend scale), weight_grid.load_night/returns20, beta_hedge.roll_beta/st/fs/
sharadar_px/live_legs/yahoo. Beta: 60-session close-close OLS vs QQQ through d-1 (known at 15:40 on d), clip +-4, <40 obs -> 1.0.

Run: PYTHONPATH=. python3 -m research.sim.night_beta_cap
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import beta_hedge as BH
from . import book as B
from . import data as D
from . import weight_grid as W

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/night_beta_cap_out.txt"
CAP, DROP, NAME_MAX, COST, FIN = 1.0, 2.0, 0.10, 2.5e-4, 0.10
HALVES = [("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31")]
LINES: list[str] = []


def log(s: str = "") -> None:
    print(s, flush=True); LINES.append(s)


def picks_panel() -> tuple[pd.DataFrame, pd.Index]:
    x = W.load_night(); D.night_candidates = lambda raw=False: x
    Rn = W.returns20(x); D.returns20 = lambda: Rn
    s = B.Sim(noise_syms=())
    q = BH.sharadar_px(["QQQ"])["close"]["QQQ"].pct_change(fill_method=None)
    bet = BH.roll_beta(Rn, q).shift(1)
    kind = x.drop_duplicates("sym", keep="last").set_index("sym").kind
    rows = []
    for d in s.days:
        nd = s.N.get(d)
        if nd is None:
            continue
        w = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        v = nd.frac * w * (0.5 if s._gap(d) > 1 else 1.0) / nd.price * nd.close
        for sy, vi, r, px in zip(nd.syms, v, nd.ret, nd.price):
            b = bet.at[d, sy] if (sy in bet.columns and d in bet.index) else np.nan
            rows.append((d, sy, vi, r, b, kind.get(sy, "?"), px))
    P = pd.DataFrame(rows, columns=["d", "sym", "v", "ret", "beta", "kind", "px"])
    P["b"] = P.beta.fillna(1.0)
    return P, s.days


def arms(P: pd.DataFrame) -> pd.DataFrame:
    """Per-pick weights for each arm (account fraction)."""
    P = P.copy()
    B_ = P.groupby("d").apply(lambda z: (z.v * z.b).sum() / z.v.sum(), include_groups=False)
    P["B"] = P.d.map(B_)
    P["w_base"] = P.v
    P["w_cap"] = P.v * np.where(P.B > CAP, CAP / P.B, 1.0)
    keep = P.b <= DROP
    P["w_dcash"] = P.v.where(keep, 0.0)
    out = []
    for d, z in P.groupby("d"):
        k = z.b <= DROP
        w = z.v.where(k, 0.0)
        free = z.v.sum() - w.sum()
        for _ in range(10):                                  # pro-rata re-spread, each name <= NAME_MAX
            room = (NAME_MAX - w).clip(lower=0).where(k, 0.0)
            if free <= 1e-12 or room.sum() <= 1e-12:
                break
            add = np.minimum(free * w / w.sum(), room) if w.sum() > 0 else room * 0
            w = w + add; free -= add.sum()
        out.append(w)
    P["w_dresp"] = pd.concat(out).reindex(P.index).fillna(0.0)
    return P


def series(P: pd.DataFrame, days: pd.Index, col: str, cost_mult: float = 1.0) -> tuple[pd.Series, pd.Series]:
    r = P.assign(x=P[col] * (P.ret - cost_mult * 2 * COST)).groupby("d").x.sum()
    g = P.groupby("d")[col].sum()
    return r.reindex(days).fillna(0.0), g.reindex(days).fillna(0.0)


def lever(r: pd.Series, g: pd.Series, dd_target: float) -> tuple[float, pd.Series]:
    dd = BH.st(r)["dd"]
    L = min(abs(dd_target) / abs(dd), 2.0) if dd < 0 else 1.0
    return L, L * r - (L * g - 1).clip(lower=0) * FIN / 252


def main() -> None:
    log("Study NIGHT-BETA-CAP (N 1108-1110) -- one look. Pre-reg: research/drafts/round1_prose.md")
    P, days = picks_panel()
    days = days[days >= "2021-01-01"]
    P = P[P.d >= "2021-01-01"]

    # ---------------- Step 1 diagnostic
    log("\n=== STEP 1: live-vs-backtest beta gap (backtest = live night rule on night_trades.v2, 60d QQQ beta, clip 4)")
    g = P.groupby("d").apply(lambda z: pd.Series(dict(
        gross=z.v.sum(), acct=(z.v * z.b).sum(), pos=(z.v * z.b).sum() / z.v.sum(), n=len(z),
        letf=(z.v * (z.kind == "levETF")).sum() / z.v.sum())), include_groups=False)
    g["y"] = g.index.year
    t = g.groupby("y").agg(nights=("n", "size"), names=("n", "mean"), gross=("gross", "mean"), acct_beta=("acct", "mean"),
                           pos_beta_mean=("pos", "mean"), pos_beta_med=("pos", "median"), letf_notional=("letf", "mean"))
    log(t.round(2).to_string())
    log("  median beta by kind x year:\n" + P.assign(y=P.d.dt.year).pivot_table(index="y", columns="kind", values="beta",
                                                                               aggfunc="median").round(2).to_string())
    lv = BH.live_legs()["night"]
    qy = BH.yahoo("QQQ")
    Ry = pd.DataFrame({sy: BH.yahoo(sy)["close"] for sy in sorted(lv.sym.unique())}).sort_index().pct_change(fill_method=None)
    bq = BH.roll_beta(Ry, qy["close"].pct_change(fill_method=None).reindex(Ry.index)).shift(1)
    lv["b"] = [bq.at[d, sy] if d in bq.index and np.isfinite(bq.at[d, sy]) else 1.0 for d, sy in zip(lv.d, lv.sym)]
    kind = W.load_night().drop_duplicates("sym", keep="last").set_index("sym").kind
    lv["kind"] = lv.sym.map(kind).fillna("unknown(new)")
    tot = lv.notional.sum()
    log(f"  LIVE {lv.d.nunique()} sessions: notional share by kind "
        + ", ".join(f"{k} {v*100:.0f}%" for k, v in (lv.groupby("kind").notional.sum() / tot).items())
        + "; notional-weighted beta by kind "
        + ", ".join(f"{k} {np.average(z.b, weights=z.notional):.2f}" for k, z in lv.groupby("kind"))
        + f"; notional with beta>2 {(lv.notional * (lv.b > 2)).sum() / tot * 100:.0f}%, at clip 4 "
        f"{(lv.notional * (lv.b >= 3.99)).sum() / tot * 100:.0f}%")
    Pb = P[P.d >= "2025-10-01"]
    log(f"  backtest 2025-10..2026-09 for comparison: LETF notional {(Pb.v*(Pb.kind=='levETF')).sum()/Pb.v.sum()*100:.0f}%, "
        f"stock-pick weighted beta {np.average(Pb[Pb.kind=='stock'].b, weights=Pb[Pb.kind=='stock'].v):.2f}, "
        f"LETF weighted beta {np.average(Pb[Pb.kind=='levETF'].b, weights=Pb[Pb.kind=='levETF'].v):.2f}, "
        f"notional with beta>2 {(Pb.v*(Pb.b>2)).sum()/Pb.v.sum()*100:.0f}%")

    # ---------------- Step 2 arms
    A = arms(P)
    names = {"base": "uncapped", "cap": "CAP B<=1 (N1108)", "dresp": "DROP>2 respread (N1109)", "dcash": "DROP>2 cash (N1110)"}
    R = {k: series(A, days, f"w_{k}") for k in names}
    trig = (A.groupby("d").B.first() > CAP)
    log(f"\n=== STEP 2: arms, 2021-01..{days.max().date()} ({int((R['base'][1] > 0).sum())} invested nights); CAP binds on "
        f"{trig.mean()*100:.0f}% of nights (2021-23 {trig.loc[:'2023'].mean()*100:.0f}%, 2024-26 {trig.loc['2024':].mean()*100:.0f}%); "
        f"avg gross base {R['base'][1][R['base'][1]>0].mean():.2f} cap {R['cap'][1][R['base'][1]>0].mean():.2f} "
        f"dcash {R['dcash'][1][R['base'][1]>0].mean():.2f}")
    log("  full period:")
    for k, lab in names.items():
        log(f"   {lab:26s} {BH.fs(BH.st(R[k][0]))}")
    verdict = {}
    for lab_h, a, b in HALVES:
        u = BH.st(R["base"][0].loc[a:b])
        log(f"  half {lab_h}: uncapped {BH.fs(u)}")
        for k in ("cap", "dresp", "dcash"):
            x = BH.st(R[k][0].loc[a:b])
            g1 = x["mar"] >= 1.3 * u["mar"]; g2 = x["cagr"] >= 0.75 * u["cagr"]; g3 = x["w21"] > u["w21"]
            verdict.setdefault(k, []).append(g1 and g2 and g3)
            log(f"   {names[k]:26s} {BH.fs(x)}\n      G1 MAR>=1.3x {'PASS' if g1 else 'fail'} ({x['mar']/u['mar']:.2f}x) | "
                f"G2 CAGR>=0.75x {'PASS' if g2 else 'fail'} ({x['cagr']/u['cagr']:.2f}x) | G3 worst21 better "
                f"{'PASS' if g3 else 'fail'}")
    log("  VERDICT: " + " | ".join(f"{names[k]}: {'PASS-INSAMPLE' if all(v) else 'KILL'}" for k, v in verdict.items()))

    ub = BH.st(R["base"][0])
    log("\n  robustness (full period 2021-26):")
    for k in ("cap", "dresp", "dcash"):
        r, gr = R[k]
        L, rl = lever(r, gr, ub["dd"])
        d = r - R["base"][0]
        inv = R["base"][1] > 0
        ex = BH.st(r.drop(r.nlargest(5).index)); exb = BH.st(R["base"][0].drop(R["base"][0].nlargest(5).index))
        log(f"   {names[k]}: levered L={L:.2f} to uncapped maxDD -> {BH.fs(BH.st(rl))}")
        log(f"      daily diff vs uncapped {d.mean()*1e4:6.2f}bp NW t {BH.nw_t(d):5.2f}; cost x2 "
            f"{BH.st(series(A, days, f'w_{k}', 2)[0])['cagr']*100:5.1f}% (unc {BH.st(series(A, days, 'w_base', 2)[0])['cagr']*100:5.1f}%), "
            f"x3 {BH.st(series(A, days, f'w_{k}', 3)[0])['cagr']*100:5.1f}% (unc {BH.st(series(A, days, 'w_base', 3)[0])['cagr']*100:5.1f}%); "
            f"ex-top-5 CAGR {ex['cagr']*100:5.1f}% MAR {ex['mar']:.2f} (unc {exb['cagr']*100:5.1f}% / {exb['mar']:.2f}); "
            f"median invested night {r[inv].median()*1e4:5.1f}bp (unc {R['base'][0][inv].median()*1e4:5.1f}), "
            f"hit {(r[inv]>0).mean()*100:3.0f}% (unc {(R['base'][0][inv]>0).mean()*100:3.0f}%)")
    for lab, a, b in (("2022", "2022-01-01", "2022-12-31"), ("QQQ 2025-10-29..2026-03-30", "2025-10-29", "2026-03-30"),
                      ("2025-10-29..2026-09", "2025-10-29", "2026-12-31")):
        log(f"  window {lab}: " + " | ".join(
            f"{k} {BH.window(R[k][0], a, b)*100:6.1f}% (DD {BH.st(R[k][0].loc[a:b])['dd']*100:5.1f}%)" for k in names))

    # ---------------- live replay (descriptive)
    log("\n=== LIVE replay, per-session sleeve return on deployed notional (descriptive, 17 sessions)")
    rows = []
    for d, z in lv.groupby("d"):
        Bp = (z.notional * z.b).sum() / z.notional.sum()
        base = z.pnl.sum() / z.notional.sum()
        k = z.b <= DROP
        rows.append((d, Bp, base, base * min(1.0, CAP / Bp) if Bp > CAP else base,
                     z.pnl[k].sum() / z.notional[k].sum() if k.any() else 0.0, z.pnl[k].sum() / z.notional.sum()))
    Lr = pd.DataFrame(rows, columns=["d", "B", "base", "cap", "dresp", "dcash"]).set_index("d")
    log(f"  position beta mean {Lr.B.mean():.2f} median {Lr.B.median():.2f}; cap binds {(Lr.B > CAP).mean()*100:.0f}% of sessions")
    for k in ("base", "cap", "dresp", "dcash"):
        log(f"   {k:6s} sum {Lr[k].sum()*100:6.2f}%  mean {Lr[k].mean()*1e4:6.1f}bp  maxDD {BH.st(Lr[k])['dd']*100:6.2f}%  "
            f"worst {Lr[k].min()*100:5.2f}%")

    # ---------------- money: whole shares (floor), sleeve 0.5 of account, research (split-adjusted) prices
    log("\n=== Money: whole-share floor, night sleeve = 0.5 x account, split-adjusted research prices (raw LETF prices "
        "are often higher after reverse splits -> more rounding than shown)")
    for acct in (2300, 10000, 25000, 100000):
        parts = []
        for k in ("base", "cap", "dresp"):
            sh = np.floor(A[f"w_{k}"] * 0.5 * acct / A.px)
            wq = sh * A.px / (0.5 * acct)
            r = A.assign(x=wq * (A.ret - 2 * COST)).groupby("d").x.sum().reindex(days).fillna(0.0)
            stt = BH.st(r)
            zero = ((sh == 0) & (A[f"w_{k}"] > 0)).sum() / (A[f"w_{k}"] > 0).sum()
            parts.append(f"{k} {stt['cagr']*100:5.1f}%/DD {stt['dd']*100:5.1f}% MAR {stt['mar']:.2f} (0-share {zero*100:3.0f}%)")
        log(f"  ${acct:>7,}: " + " | ".join(parts))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    sys.exit(main())
