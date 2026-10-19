"""Studies SSR-NIGHT (N 1035) and PATTERN-NIGHT (N 1036); see round1_prose.md.

Builds pick-level features for SEL-NIGHT's kept picks (Sharadar common stocks 1999-2026), then:
  SSR-NIGHT: RD at the Rule 201 -10% trigger (post-2011 judge, pre-2011 placebo, adjacent cutoffs).
  PATTERN-NIGHT: HistGradientBoosting ranker, fit 1999-2015 -> judge 2016-26, walk-forward, shuffled-label placebo, leg replay.

Run:  PYTHONPATH=. .venv/bin/python research/sim/pattern_night.py
Out:  data/research/program/ssr_night_out.txt, data/research/program/pattern_night_out.txt
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data" / "research" / "program"
S = pathlib.Path.home() / "data" / "sharadar"
RULE201 = pd.Timestamp("2011-03-01")
SECTORS = ["Technology", "Healthcare", "Industrials", "Financial Services", "Consumer Cyclical",
           "Communication Services", "Real Estate", "Basic Materials", "Energy", "Consumer Defensive", "Utilities"]
FEATS = ["day_ret", "ibs", "vol20", "log_adv", "log_px", "low_ret", "high_ret", "gap", "ret5", "ret20", "ret63",
         "ret252", "dist_hi", "volratio", "prev_low_ret", "ssr", "repeat", "n_picks", "spy_ret", "dow"] + \
        [f"sec_{s[:6]}" for s in SECTORS]


def clus_t(x: np.ndarray) -> float:
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def build() -> pd.DataFrame:
    nm = pd.read_parquet(PROG / "sel_night_names_primary.parquet")
    nm["date"] = pd.to_datetime(nm["date"])
    if "rule" in nm.columns:
        nm = nm[nm["rule"] == "current"].drop(columns=["rule"]).reset_index(drop=True)
    tks = sorted(nm.ticker.unique())
    b = ds.dataset(S / "stocks.parquet").to_table(
        columns=["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"],
        filter=ds.field("ticker").isin(tks)).to_pandas()
    b["date"] = pd.to_datetime(b["date"])
    b = b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    f = b.closeunadj / b.close
    g = b.groupby("ticker", sort=False)
    pc_raw = g.closeunadj.shift(1)
    pc_adj = g.close.shift(1)
    b["low_ret"] = b.low * f / pc_raw - 1
    b["high_ret"] = b.high * f / pc_raw - 1
    b["gap"] = b.open * f / pc_raw - 1
    b["prev_low_ret"] = g.low_ret.shift(1)
    b["ibs"] = ((b.closeunadj - b.low * f) / ((b.high - b.low) * f)).where((b.high - b.low) > 0)
    for w in (5, 20, 63, 252):
        b[f"ret{w}"] = pc_adj / g.close.shift(w + 1) - 1
    b["dist_hi"] = pc_adj / g.close.transform(lambda s: s.shift(1).rolling(252, min_periods=120).max()) - 1
    b["volratio"] = b.volume / g.volume.transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    nm = nm.merge(b[["ticker", "date", "ibs", "low_ret", "high_ret", "gap", "prev_low_ret", "ret5", "ret20", "ret63",
                     "ret252", "dist_hi", "volratio"]], on=["ticker", "date"], how="left")
    # sector
    t = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "sector", "lastupdated"])
    t = t[t.table == "SEP"].sort_values("lastupdated").drop_duplicates("ticker", keep="last").set_index("ticker")
    nm["sector"] = nm.ticker.map(t.sector)
    for s in SECTORS:
        nm[f"sec_{s[:6]}"] = (nm.sector == s).astype(float)
    # SPY day return
    spy = ds.dataset(S / "funds.parquet").to_table(columns=["ticker", "date", "close"],
                                                   filter=ds.field("ticker") == "SPY").to_pandas()
    spy["date"] = pd.to_datetime(spy.date)
    spy = spy.sort_values("date")
    spy["spy_ret"] = spy.close.pct_change()
    nm = nm.merge(spy[["date", "spy_ret"]], on="date", how="left")
    nm["ssr"] = ((nm.low_ret <= -0.10) | (nm.prev_low_ret <= -0.10)).astype(float)
    nm["log_adv"] = np.log(nm.adv)
    nm["log_px"] = np.log(nm.price)
    nm["n_picks"] = nm.groupby("date").ticker.transform("size").astype(float)
    nm["dow"] = nm.date.dt.dayofweek.astype(float)
    # repeat: picked in the prior 5 sessions
    sess = np.sort(nm.date.unique())
    pos = {d: i for i, d in enumerate(sess)}
    nm["si"] = nm.date.map(pos)
    nm = nm.sort_values(["ticker", "si"])
    prev_si = nm.groupby("ticker").si.shift(1)
    nm["repeat"] = ((nm.si - prev_si) <= 5).astype(float)
    nm = nm.sort_values(["date", "ticker"]).reset_index(drop=True)
    nm["label"] = (nm.r - nm.groupby("date").r.transform("mean")).clip(-0.5, 0.5)
    return nm


def within_night_pairs(df: pd.DataFrame, a: pd.Series, b: pd.Series) -> np.ndarray:
    """Per-night mean r(a) - mean r(b) over nights with both groups present, bp."""
    out = []
    for d, g in df.groupby("date"):
        ia, ib = a.loc[g.index].to_numpy(bool), b.loc[g.index].to_numpy(bool)
        if ia.any() and ib.any():
            out.append((g.r[ia].mean() - g.r[ib].mean()) * 1e4)
    return np.array(out)


def ssr_study(nm: pd.DataFrame) -> str:
    L = ["SSR-NIGHT: Rule 201 trigger (-10% intraday low) as a night-pick selector; picks = SEL-NIGHT current rule 1999-2026",
         f"picks {len(nm)}; low_ret available {nm.low_ret.notna().mean():.1%}; SSR-on share post-2011 "
         f"{nm.loc[nm.date >= RULE201, 'ssr'].mean():.1%} (trigger today {(nm.loc[nm.date >= RULE201, 'low_ret'] <= -0.10).mean():.1%})", ""]
    d = nm.dropna(subset=["low_ret"])

    def rd(sub: pd.DataFrame, cut: float, label: str) -> tuple[str, float, float]:
        lo = sub.low_ret
        bins = {"b_above": (lo > cut) & (lo <= cut + 0.005), "b_below": (lo <= cut) & (lo > cut - 0.005),
                "b_above2": (lo > cut + 0.005) & (lo <= cut + 0.010), "b_below2": (lo <= cut - 0.005) & (lo > cut - 0.010)}
        D = within_night_pairs(sub, bins["b_below"], bins["b_above"])
        s_up = within_night_pairs(sub, bins["b_above"], bins["b_above2"])
        s_dn = within_night_pairs(sub, bins["b_below2"], bins["b_below"])
        pooled = (sub.r[bins["b_below"]].mean() - sub.r[bins["b_above"]].mean()) * 1e4
        trend = 0.5 * (s_up.mean() + s_dn.mean()) if len(s_up) and len(s_dn) else float("nan")
        did = D.mean() - trend
        yr = None
        line = (f"  {label}: cutoff {cut:+.0%}: n_below {int(bins['b_below'].sum())} n_above {int(bins['b_above'].sum())}; "
                f"within-night D {D.mean():+.1f}bp (n_nights {len(D)}, t {clus_t(D):.2f}, med {np.median(D) if len(D) else float('nan'):+.1f}); "
                f"pooled D {pooled:+.1f}; adjacent steps {s_up.mean() if len(s_up) else float('nan'):+.1f} / "
                f"{s_dn.mean() if len(s_dn) else float('nan'):+.1f}; diff-in-disc {did:+.1f}bp")
        return line, D.mean(), did

    post = d[d.date >= RULE201]
    pre = d[d.date < RULE201]
    L.append("== primary: RD at -10%, post-2011 judge ==")
    line, D_post, did_post = rd(post, -0.10, "post-2011")
    L.append(line)
    for lo_, hi_, lab in [("2011-03-01", "2018-12-31", "h1 2011-18"), ("2019-01-01", "2026-12-31", "h2 2019-26")]:
        L.append(rd(post[(post.date >= lo_) & (post.date <= hi_)], -0.10, lab)[0])
    # ex-top-5 nights on D
    Dn = within_night_pairs(post, (post.low_ret <= -0.10) & (post.low_ret > -0.105), (post.low_ret > -0.10) & (post.low_ret <= -0.095))
    if len(Dn) > 10:
        s = np.sort(Dn)
        L.append(f"  post-2011 D ex-top-5 nights {s[:-5].mean():+.1f}bp, ex-bottom-5 {s[5:].mean():+.1f}bp, hit {(Dn > 0).mean():.3f}")
    L.append("== placebo: pre-2011 (no rule) ==")
    L.append(rd(pre, -0.10, "pre-2011")[0])
    L.append("== placebo: adjacent cutoffs post-2011 ==")
    L.append(rd(post, -0.09, "post-2011")[0])
    L.append(rd(post, -0.11, "post-2011")[0])
    L.append("== secondary: SSR-on vs SSR-off within night, close day_ret in [-9.5%, -8%] ==")
    for lab, sub in [("post-2011", post), ("pre-2011", pre)]:
        band = sub[(sub.day_ret >= -0.095) & (sub.day_ret <= -0.08)]
        on = band.ssr == 1
        x = within_night_pairs(band, on, ~on)
        L.append(f"  {lab}: picks {len(band)} (SSR-on {on.mean():.1%}); on-minus-off {x.mean():+.1f}bp t {clus_t(x):.2f} "
                 f"med {np.median(x):+.1f} n_nights {len(x)}; pooled on {band.r[on].mean()*1e4:+.1f} off {band.r[~on].mean()*1e4:+.1f}")
    share = float(post.ssr.mean())
    L.append(f"== ceiling: diff-in-disc {did_post:+.1f}bp x SSR share {share:.0%} x redistributable half x w .65 x 250 = "
             f"{did_post * share * 0.5 * 0.65 * 250 / 1e4 * 100:+.2f}pp/yr (upper bound) ==")
    return "\n".join(L) + "\n"


def judge_block(df: pd.DataFrame, pred: np.ndarray, label: str) -> list[str]:
    d = df.assign(p=pred)
    rows = []
    for dt, g in d.groupby("date"):
        if len(g) < 4:
            continue
        o = np.argsort(g.p.to_numpy())
        r = g.r.to_numpy()
        half = len(g) // 2
        rows.append(dict(date=dt, tmb=(r[o[-half:]].mean() - r[o[:half]].mean()) * 1e4,
                         rho=pd.Series(r).corr(g.p.reset_index(drop=True), method="spearman")))
    t = pd.DataFrame(rows)
    x = t.tmb.to_numpy()
    s = np.sort(x)
    h1 = t[t.date < "2021-01-01"].tmb
    h2 = t[t.date >= "2021-01-01"].tmb
    dec = d.assign(q=d.groupby("date").p.rank(pct=True)).assign(q=lambda z: np.minimum((z.q * 5).astype(int), 4))
    decm = dec.groupby("q").r.mean() * 1e4
    return [f"  {label}: nights {len(t)}; top-half minus bottom-half {x.mean():+.1f}bp t {clus_t(x):.2f} med {np.median(x):+.1f} "
            f"hit {(x > 0).mean():.3f} h1 {h1.mean():+.1f} h2 {h2.mean():+.1f} ex-top-5 {s[:-5].mean():+.1f}; "
            f"Spearman {t.rho.mean():+.3f}; pred quintile means bp {decm.round(0).tolist()}"], x.mean()


def leg_replay(df: pd.DataFrame, pred: np.ndarray) -> str:
    d = df.assign(p=pred)
    base, alt = [], []
    for dt, g in d.groupby("date"):
        w = g.per.to_numpy(); r = g.r.to_numpy()
        z = (g.p - g.p.mean()).to_numpy()
        z = z / (z.std() if z.std() > 0 else 1)
        m = np.clip(1 + 0.25 * z, 0.25, 2); m = m / m.mean()
        base.append((w * r).sum()); alt.append((w * m * r).sum())
    b, a = np.array(base) * 1e4, np.array(alt) * 1e4
    return (f"  leg replay (tilt form, k .25): current {b.mean():+.2f} bp/night -> {a.mean():+.2f}; diff {(a - b).mean():+.2f} "
            f"t {clus_t(a - b):.2f} = {(a - b).mean() * 250 / 100 * 0.65:+.2f}pp/yr of equity at w .65")


def pattern_study(nm: pd.DataFrame) -> str:
    d = nm.dropna(subset=FEATS + ["label"]).copy()
    L = ["PATTERN-NIGHT: HistGradientBoosting ranker over all close-time features; picks = SEL-NIGHT current rule",
         f"rows {len(d)} of {len(nm)} (complete features); features {len(FEATS)}", ""]
    train = d[d.date <= "2015-12-31"]; test = d[d.date >= "2016-01-01"]
    L.append(f"fit 1999-2015 (n {len(train)}) -> judge 2016-2026 (n {len(test)})")
    X_tr, y_tr = train[FEATS].to_numpy(), train.label.to_numpy()
    X_te = test[FEATS].to_numpy()
    mdl = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200,
                                        l2_regularization=1.0, random_state=0).fit(X_tr, y_tr)
    pred = mdl.predict(X_te)
    line, real_tmb = judge_block(test, pred, "GBM judge 2016-26")
    L += line
    L.append(leg_replay(test, pred))
    line_tr, _ = judge_block(train, mdl.predict(X_tr), "GBM in-sample 1999-2015 (fit quality, not evidence)")
    L += line_tr
    # ridge anchor
    mu, sd = X_tr.mean(0), X_tr.std(0) + 1e-9
    rg = Ridge(alpha=10.0).fit((X_tr - mu) / sd, y_tr)
    L += judge_block(test, rg.predict((X_te - mu) / sd), "Ridge judge 2016-26")[0]
    # placebo: shuffled labels within night
    rng = np.random.default_rng(20261018)
    plc = []
    for i in range(20):
        ys = train.groupby("date").label.transform(lambda s: rng.permutation(s.to_numpy()))
        m2 = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200,
                                           l2_regularization=1.0, random_state=i).fit(X_tr, ys.to_numpy())
        plc.append(judge_block(test, m2.predict(X_te), "p")[1])
    plc = np.array(plc)
    L.append(f"  placebo (20 shuffled-label fits): top-minus-bottom mean {plc.mean():+.1f}bp sd {plc.std():.1f} 95th pct "
             f"{np.percentile(plc, 95):+.1f}; real {real_tmb:+.1f} -> beats 95th: {real_tmb > np.percentile(plc, 95)}")
    # permutation importance on the judge set (top-minus-bottom drop)
    imp = []
    base_pred = pred
    for j, f in enumerate(FEATS):
        Xp = X_te.copy(); Xp[:, j] = rng.permutation(Xp[:, j])
        imp.append((f, real_tmb - judge_block(test, mdl.predict(Xp), "i")[1]))
    imp.sort(key=lambda z: -z[1])
    L.append("  permutation importance (bp of top-minus-bottom lost): " + ", ".join(f"{f} {v:+.1f}" for f, v in imp[:8]))
    # walk-forward expanding by year
    L.append("== walk-forward (expanding fit, judge each year 2006-2026) ==")
    wf = []
    for y in range(2006, 2027):
        tr = d[d.date < f"{y}-01-01"]; te = d[(d.date >= f"{y}-01-01") & (d.date <= f"{y}-12-31")]
        if len(te) < 200:
            continue
        m3 = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200,
                                           l2_regularization=1.0, random_state=0).fit(tr[FEATS].to_numpy(), tr.label.to_numpy())
        wf.append(te.assign(p=m3.predict(te[FEATS].to_numpy())))
    wf = pd.concat(wf)
    L += judge_block(wf, wf.p.to_numpy(), "walk-forward 2006-26")[0]
    L.append(leg_replay(wf, wf.p.to_numpy()))
    byy = []
    for y, g in wf.groupby(wf.date.dt.year):
        byy.append(f"{y}:{judge_block(g, g.p.to_numpy(), 'y')[1]:+.0f}")
    L.append("  by year top-minus-bottom bp: " + " ".join(byy))
    return "\n".join(L) + "\n"


def main() -> int:
    nm = build()
    s = ssr_study(nm)
    (PROG / "ssr_night_out.txt").write_text(s)
    print(s)
    p = pattern_study(nm)
    (PROG / "pattern_night_out.txt").write_text(p)
    print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
