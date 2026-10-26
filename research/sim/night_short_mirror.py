"""Study NIGHT-SHORT (round1_prose.md "### NIGHT-SHORT (N 1062)"): the night leg's short mirror. day_ret >= +8% and IBS >= 0.90 at
the close, prev close >= $5, $ADV20 >= $10M, domestic common stock; short the closing cross, cover the next opening cross; net 5bp/side
+ 2bp borrow; excess vs the EW eligible-universe overnight. Judge 2003-15. usage: PYTHONPATH=. .venv/bin/python -m research.sim.night_short_mirror
--min-dr 0.20 runs Study NIGHT-SHORT-20 (N 1064): same pipeline, day_ret >= +20%, judged 2016-01-01..2026-09-30 (2003-15 = selection sample),
out night_short20_out.txt."""
from __future__ import annotations
import argparse, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
SH = Path.home() / "data/sharadar"
ARGS = argparse.ArgumentParser(); ARGS.add_argument("--min-dr", type=float, default=0.08); A = ARGS.parse_args()
MIN_DR = A.min_dr; IS20 = abs(MIN_DR - 0.20) < 1e-9
OUT = ROOT / ("data/research/program/night_short20_out.txt" if IS20 else "data/research/program/night_short_out.txt")
START, END = "2003-01-01", "2026-09-30"
COST = 10.0 + 2.0  # bp: 5bp/side + 2bp overnight borrow
if IS20:  # N 1064: judge 2016-26 (never inspected for this bin); 2003-15 is the selection sample
    JUDGE = ("2016-01-01", "2026-09-30"); SUBS = {"sub 2016-20": ("2016-01-01", "2020-12-31"), "sub 2021-26": ("2021-01-01", "2026-09-30")}
    PERIODS = {"JUDGE 2016-26": JUDGE, **SUBS, "SELECTION SAMPLE 2003-15 (not judged)": ("2003-01-01", "2015-12-31")}
    BAR_MEAN, BAR_HIT = 25.0, 0.55
else:
    JUDGE = ("2003-01-01", "2015-12-31"); SUBS = {"sub 2003-08": ("2003-01-01", "2008-12-31"), "sub 2009-15": ("2009-01-01", "2015-12-31")}
    PERIODS = {"JUDGE 2003-15": JUDGE, **SUBS, "touched 2016-20": ("2016-01-01", "2020-12-31"), "live-era 2021-26": ("2021-01-01", "2026-09-30")}
    BAR_MEAN, BAR_HIT = 15.0, 0.0


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with OUT.open("a") as f: f.write(s + "\n")


def clus_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else float("nan")


def extop5(x):
    x = np.sort(np.asarray(x, float)); return (x.sum() - x[-5:].sum()) / (len(x) - 5) if len(x) > 5 else float("nan")


def nstats(s: pd.Series) -> str:
    """per-night series (already EW within the night), bp."""
    x = s.dropna().to_numpy(float)
    if len(x) < 3: return f"n {len(x)}"
    return f"nights {len(x)} mean {x.mean():+.1f} med {np.median(x):+.1f} hit {np.mean(x > 0):.2f} t {clus_t(x):.2f} ex-top5 {extop5(x):+.1f}"


def main():
    if OUT.exists(): OUT.unlink()
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"],
                         filters=[("date", ">=", pd.Timestamp("2002-10-01").date())])
    st = st[st.ticker.isin(ok)]; st["date"] = pd.to_datetime(st.date)
    st = st.sort_values(["ticker", "date"]).reset_index(drop=True)
    g = st.groupby("ticker")
    st["pc"] = g.close.shift(1); st["pcu"] = g.closeunadj.shift(1)
    dv = (st.closeunadj * st.volume).groupby(st.ticker).shift(1)
    st["adv"] = dv.groupby(st.ticker).rolling(20, min_periods=15).median().reset_index(level=0, drop=True)
    st["dr"] = st.close / st.pc - 1
    st["ibs"] = (st.close - st.low) / (st.high - st.low).replace(0, np.nan)
    st["on"] = (g.open.shift(-1) / st.close - 1) * 1e4           # close d -> open d+1, bp
    st["on"] = st.on.replace([np.inf, -np.inf], np.nan)
    st = st[(st.date >= START) & (st.date <= END) & (st.pcu >= 5) & (st.adv >= 1e7) & st.on.notna() & (st.close > 0)]
    pick = (st.dr >= MIN_DR) & (st.ibs >= 0.90)
    univ = st.groupby("date").on.mean().rename("univ")                 # EW eligible universe overnight (incl. the picks)
    univ_x = st[~pick].groupby("date").on.mean().rename("univ_xpick")   # extra: universe ex the picks (not the registered bar)
    P = st[pick]
    nights = P.groupby("date").agg(on=("on", "mean"), names=("on", "size"), ibs=("ibs", "mean"), dr=("dr", "mean"), adv=("adv", "median"))
    d = pd.concat([nights, univ, univ_x], axis=1).dropna(subset=["on"])
    d["raw"] = -d.on - COST                        # short net, bp/night
    d["exc"] = -(d.on - d.univ) - COST              # short excess vs EW universe, net (registered bar)
    d["xs2"] = -(d.on - d.univ_xpick) - COST       # extra: vs universe ex-picks
    log(f"{'NIGHT-SHORT-20 (N 1064)' if IS20 else 'NIGHT-SHORT (N 1062)'}: rule dr>={MIN_DR:+.0%} & IBS>=0.90, prev close>=$5, $ADV20>=$10M, domestic common; short close cross -> cover open cross; "
        f"net = gross - {COST:.0f}bp. {len(P):,} name-nights on {len(d):,} nights {d.index.min().date()}..{d.index.max().date()}; "
        f"universe {len(st):,} name-days, {st.ticker.nunique():,} tickers; names/night median {d.names.median():.0f} mean {d.names.mean():.1f}")
    log(f"PASS bar (registration): applies to EXCESS vs EW eligible-universe overnight, net ('exc' below), judged {JUDGE[0][:4]}-{JUDGE[1][2:4]}: "
        f"mean >= +{BAR_MEAN:.0f}bp, t >= 2, median > 0, ex-top-5 > 0, both subperiods ({', '.join(SUBS)}) > 0" + (f", hit >= {BAR_HIT}." if IS20 else "."))
    for nm, (a, b) in PERIODS.items():
        s = d[(d.index >= a) & (d.index <= b)]
        if len(s) == 0: log(f"\n== {nm}: no nights"); continue
        log(f"\n== {nm}: {len(s):,} nights, {int(s.names.sum()):,} name-nights")
        log(f"  raw short net          : {nstats(s.raw)}")
        log(f"  EXCESS short net (bar) : {nstats(s.exc)}")
        log(f"  excess vs univ ex-picks: {nstats(s.xs2)}")
        log(f"  decomposition (long overnight, gross bp): picks {s.on.mean():+.1f} (med {s.on.median():+.1f}) vs universe {s.univ.mean():+.1f} "
            f"(ex-picks {s.univ_xpick.mean():+.1f}) -> picks minus universe {(s.on - s.univ).mean():+.1f}")
    J = d[(d.index >= JUDGE[0]) & (d.index <= JUDGE[1])]; x = J.exc.dropna()
    ok_ = {f"mean{BAR_MEAN:.0f}": bool(round(x.mean(), 2) >= BAR_MEAN), "t2": bool(round(clus_t(x), 2) >= 2), "median": bool(x.median() > 0),
           "extop5": bool(extop5(x) > 0)}
    for nm, (a, b) in SUBS.items(): ok_[nm.replace("sub ", "sub")] = bool(d[(d.index >= a) & (d.index <= b)].exc.mean() > 0)
    if IS20: ok_["hit55"] = bool(np.mean(x > 0) >= BAR_HIT)
    log(f"\nGATES ({JUDGE[0][:4]}-{JUDGE[1][2:4]}, excess short net): {ok_} -> {'PASS' if all(ok_.values()) else 'KILL'}")
    log(f"  for reference, the same gates on the RAW short net: mean {J.raw.mean():+.1f} t {clus_t(J.raw):.2f} med {J.raw.median():+.1f} ex-top5 {extop5(J.raw):+.1f}")
    log("\nper-year: year nights names mean_raw_short_net mean_excess_short_net median_excess hit_excess | picks_on univ_on (gross long bp)")
    for y, s in d.groupby(d.index.year):
        log(f"  {y} {len(s):4d} {int(s.names.sum()):6d} {s.raw.mean():+7.1f} {s.exc.mean():+7.1f} {s.exc.median():+7.1f} {np.mean(s.exc > 0):.2f} | {s.on.mean():+7.1f} {s.univ.mean():+6.1f}")
    # volunteered: by size tercile of ADV (name-level, 2003-15) and by names/night
    PJ = P[(P.date >= JUDGE[0]) & (P.date <= JUDGE[1])].merge(univ, left_on="date", right_index=True)
    PJ["xs_name"] = -(PJ.on - PJ.univ) - COST
    PJ["adv_bin"] = pd.cut(PJ.adv, [0, 2.5e7, 1e8, 5e8, np.inf], labels=["10-25M", "25-100M", "100-500M", ">500M"])
    JL = f"{JUDGE[0][:4]}-{JUDGE[1][2:4]}"
    log(f"\nvolunteered, {JL} name-level (EW per night within bin), short excess net by $ADV20 bin:")
    for b, s in PJ.groupby("adv_bin"):
        n = s.groupby("date").xs_name.mean()
        log(f"  {b:>9}: {len(s):6,} name-nights, {nstats(n)}")
    PJ["dr_bin"] = pd.cut(PJ.dr, [0.20, 0.30, 0.50, np.inf], labels=["20-30%", "30-50%", ">50%"], right=False) if IS20 else \
        pd.cut(PJ.dr, [0.08, 0.12, 0.20, np.inf], labels=["8-12%", "12-20%", ">20%"], right=False)
    log(f"volunteered, {JL} by day-return bin (short excess net, EW per night):")
    for b, s in PJ.groupby("dr_bin"):
        n = s.groupby("date").xs_name.mean()
        log(f"  {b:>7}: {len(s):6,} name-nights, {nstats(n)}")
    log(f"volunteered, {JL} by names/night (short excess net):")
    for b, s in J.groupby(pd.cut(J.names, [0, 2, 5, 10, np.inf], labels=["1-2", "3-5", "6-10", ">10"])):
        log(f"  {b:>5}: {nstats(s.exc)}")
    log("Disclosed: daily opens as the open cross, daily closes as the close cross; adjusted open/close for the overnight; EW per night; "
        "t = per-night (nights are the cluster); universe = all name-days passing px/ADV gates (includes the picks).")


if __name__ == "__main__":
    main()
