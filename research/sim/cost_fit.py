"""A per-name night-leg cost model fitted on LIVE fills (NEXT.md addendum 16's "next research").

    PYTHONPATH=. .venv/bin/python -m research.sim.cost_fit                    # logs/ on this machine
    PYTHONPATH=. .venv/bin/python -m research.sim.cost_fit --logs DIR --tag -live [--prints prints.csv]
    PYTHONPATH=. .venv/bin/python -m research.sim.cost_fit --selftest DIR     # synthetic fixture

Inputs (written by swingtrader/daily/executor.py; they live on the SERVER, not the laptop):
  daily-fills<tag>.jsonl      {coid, sym, leg, side, qty, fill_px, ref_px, slippage_bps, route, filled_at}
                              one line per NEW fill; ref_px is the 15:40 decision price (buys)
                              or the last mark (sells) -- NOT the auction print
  daily-decisions<tag>.jsonl  {date, sym, price, day_ret, ibs, vol20, spread_bps, qty}
                              one line per night pick at 15:40, spread_bps = quoted (ask-bid)/mid
Cost is measured against the OFFICIAL auction print, as the lever gate does
(signals.night_exit_costs): sells vs the day's official open, buys vs the official close.
Prints come from --prints (csv: sym,date,open,close), else md.sip_daily (needs keys), else
the fill falls back to ref_px and is flagged (drift, not cost: excluded from the fit by default).

Model (per side, bps, + = worse than the print):
    bps = b0 + b1*log(price/20) + b2*log(adv/5e7) + b3*(half_spread/10bp) + b4*sell + b5*directed
  Bayesian linear regression. Prior: intercept ~ N(pooled measured mean, 5^2),
  slopes ~ N(0, 3^2) (bp per unit of a ~unit-scaled feature): with few fills the fit IS
  the pooled mean and every name gets the same cost; slopes appear only when the data
  insist. Fills on the same morning share the auction's conditions, so observations are
  down-weighted by 1/(1+(k_d-1)*rho) (k_d = fills that day, rho = intra-day correlation,
  method of moments, clipped to [0, 0.9]): the posterior reflects effective n, not raw n.
Outputs: CostFit.predict(price, adv, spread, side) -> (mean, lo95, hi95);
  cost_fn(fit, bound) -> f(price, adv) with book.cost_bps's (price, adv) arrays -> bps/side;
  register(fit) adds book.TIERS["live"] (mean, floored at 0) and ["live_hi"] (95% UB) so
  Params(night_cost="live") runs in the unmodified simulator.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = ["const", "log_px", "log_adv", "half_spread", "sell", "directed"]
PRIOR_SD = np.array([5.0, 3.0, 3.0, 3.0, 3.0, 3.0])
MEASURED_MEAN_BPS = -0.75      # addendum 29: buys -0.5, open sells -1.0 (26 round trips)
# representative names per book.TIERS bucket: (price, adv) for (<$10, $10-20, >$20 thin, rest)
BUCKETS = [(6.0, 2e7), (14.0, 3e7), (40.0, 2.5e7), (60.0, 2e8)]


# ---------------------------------------------------------------- loading
def _jsonl(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(rows)


def load_logs(log_dir: str | Path = "logs", tag: str = "-live") -> tuple[pd.DataFrame, pd.DataFrame]:
    d = Path(log_dir)
    return _jsonl(d / f"daily-fills{tag}.jsonl"), _jsonl(d / f"daily-decisions{tag}.jsonl")


def load_prints(path: str | Path | None, fills: pd.DataFrame) -> dict:
    """{(sym, 'YYYY-MM-DD'): (open, close)} from a csv, else SIP daily bars if keys exist."""
    out: dict = {}
    if path and Path(path).exists():
        p = pd.read_csv(path)
        for r in p.itertuples():
            out[(r.sym, str(r.date)[:10])] = (float(r.open), float(r.close))
        return out
    if fills.empty:
        return out
    try:                                        # the server path: same source as the lever gate
        from swingtrader.daily import marketdata as md
        days = sorted({str(x)[:10] for x in fills.filled_at})
        bars = md.sip_daily(sorted(set(fills.sym)), pd.Timestamp(days[0]) - pd.Timedelta(days=3), None)
        for sym, b in bars.items():
            for dd in b.index:
                out[(sym, str(dd.date()))] = (float(b.loc[dd, "open"]), float(b.loc[dd, "close"]))
    except Exception as exc:                    # no keys / offline: caller falls back to ref_px
        print(f"(no official prints: {type(exc).__name__}; costs vs ref_px are flagged, not fitted)")
    return out


def build_obs(fills: pd.DataFrame, decisions: pd.DataFrame, prints: dict,
              adv: dict | None = None) -> pd.DataFrame:
    """One row per night-leg fill: cost vs the official print and the ex-ante features."""
    if fills.empty:
        return pd.DataFrame(columns=["date", "sym", "side", "bps", "official"] + FEATURES)
    f = fills[fills.get("leg", pd.Series(dtype=str)) == "night"].copy()
    f["date"] = f["filled_at"].astype(str).str[:10]
    dec = decisions.copy() if not decisions.empty else pd.DataFrame(columns=["date", "sym", "price", "spread_bps"])
    if not dec.empty:
        dec["date"] = dec["date"].astype(str).str[:10]
    rows = []
    for r in f.itertuples():
        pr = prints.get((r.sym, r.date))
        side = r.side
        if pr is not None:
            ref = pr[0] if side == "sell" else pr[1]
            official = True
        else:
            ref = float(getattr(r, "ref_px", np.nan) or np.nan); official = False
        px = float(r.fill_px)
        bps = (px / ref - 1) * 1e4 * (1 if side == "buy" else -1) if ref and ref > 0 else np.nan
        # the 15:40 decision behind this fill: same day for a buy, the latest earlier one for a sell
        cand = dec[dec.sym == r.sym] if not dec.empty else dec
        cand = cand[cand.date <= r.date] if side == "buy" else cand[cand.date < r.date]
        drow = cand.iloc[-1] if len(cand) else None
        price = float(drow["price"]) if drow is not None else px
        spread = float(drow["spread_bps"]) if drow is not None and pd.notna(drow.get("spread_bps")) else np.nan
        a = np.nan
        if adv:
            a = adv.get(r.sym, np.nan)
        if drow is not None and "adv" in drow and pd.notna(drow.get("adv")):
            a = float(drow["adv"])
        route = str(getattr(r, "route", "") or "")
        directed = 1.0 if side == "buy" else float(route not in ("", "AUTO", "None"))
        rows.append(dict(date=r.date, sym=r.sym, side=side, bps=bps, official=official,
                         price=price, adv=a, spread=spread, directed=directed))
    o = pd.DataFrame(rows)
    return o


def design(price, adv, spread, sell, directed, spread_fill: float = 10.0) -> np.ndarray:
    price = np.asarray(price, float)
    n = len(price)
    adv = np.broadcast_to(np.asarray(adv, float), (n,)).astype(float)
    spread = np.broadcast_to(np.asarray(spread, float), (n,)).astype(float)
    la = np.where(np.isfinite(adv) & (adv > 0), np.log(np.where(adv > 0, adv, 1) / 5e7), 0.0)   # unknown ADV -> centre
    hs = np.where(np.isfinite(spread), spread / 2, spread_fill / 2) / 10.0
    return np.column_stack([np.ones(n), np.log(price / 20.0), la, hs,
                            np.broadcast_to(np.asarray(sell, float), (n,)),
                            np.broadcast_to(np.asarray(directed, float), (n,))])


# -------------------------------------------------------------------- fit
@dataclass
class CostFit:
    beta: np.ndarray
    cov: np.ndarray
    sigma: float
    rho: float
    n: int
    n_days: int
    n_eff: float
    pooled_mean: float
    pooled_ub95: float            # day-clustered one-sided 95% UB on the pooled mean
    spread_fill: float = 10.0     # median quoted spread (bp) used when a name has none (the sim)
    notes: list = field(default_factory=list)

    def predict(self, price, adv, spread=np.nan, side: str = "avg", directed: float = 1.0):
        """(mean, lo95, hi95) per-side bps for arrays of names. side: buy | sell | avg."""
        if side == "avg":
            mb, lb, hb = self.predict(price, adv, spread, "buy", 1.0)
            ms, ls, hs = self.predict(price, adv, spread, "sell", directed)
            X = (design(price, adv, spread, 0.0, 1.0, self.spread_fill)
                 + design(price, adv, spread, 1.0, directed, self.spread_fill)) / 2
        else:
            X = design(price, adv, spread, float(side == "sell"), 1.0 if side == "buy" else directed,
                       self.spread_fill)
        m = X @ self.beta
        se = np.sqrt(np.einsum("ij,jk,ik->i", X, self.cov, X))
        return m, m - 1.96 * se, m + 1.96 * se

    def ub(self, price, adv, spread=np.nan, side="avg", z: float = 1.645):
        X = design(price, adv, spread, 0.5 if side == "avg" else float(side == "sell"), 1.0, self.spread_fill)
        return X @ self.beta + z * np.sqrt(np.einsum("ij,jk,ik->i", X, self.cov, X))

    def summary(self) -> str:
        sd = np.sqrt(np.diag(self.cov))
        lines = [f"cost fit: n {self.n} fills on {self.n_days} days, effective n {self.n_eff:.1f}, "
                 f"sigma {self.sigma:.1f}bp, intra-day rho {self.rho:.2f}",
                 f"  pooled mean {self.pooled_mean:+.2f}bp/side, day-clustered 95% UB {self.pooled_ub95:+.2f}bp"]
        for k, b, s in zip(FEATURES, self.beta, sd):
            lines.append(f"  {k:12s} {b:+7.2f} +- {1.96*s:5.2f}  (prior sd {PRIOR_SD[FEATURES.index(k)]:.0f})")
        lines += [f"  note: {x}" for x in self.notes]
        return "\n".join(lines)


def icc(y: np.ndarray, g: np.ndarray) -> float:
    """Intra-day correlation by one-way ANOVA moments, clipped to [0, 0.9]."""
    df = pd.DataFrame({"y": y, "g": g})
    k = df.groupby("g").y.size()
    if len(k) < 3 or (k > 1).sum() < 2:
        return 0.0
    grand = df.y.mean()
    msb = (k * (df.groupby("g").y.mean() - grand) ** 2).sum() / (len(k) - 1)
    msw = ((df.y - df.groupby("g").y.transform("mean")) ** 2).sum() / max(1, len(df) - len(k))
    k0 = (len(df) - (k ** 2).sum() / len(df)) / (len(k) - 1)
    r = (msb - msw) / (msb + (k0 - 1) * msw) if (msb + (k0 - 1) * msw) > 0 else 0.0
    return float(np.clip(r, 0.0, 0.9))


def clustered_ub(y: np.ndarray, g: np.ndarray, z: float = 1.645) -> tuple[float, float]:
    """(mean, one-sided 95% UB) with the SE from day sums (CR0 with G/(G-1))."""
    y = np.asarray(y, float); m = y.mean()
    df = pd.DataFrame({"e": y - m, "g": g})
    s = df.groupby("g").e.sum().values
    G = len(s)
    if G < 2:
        return m, np.nan
    v = (s ** 2).sum() / len(y) ** 2 * G / (G - 1)
    return float(m), float(m + z * np.sqrt(v))


def fit(obs: pd.DataFrame, prior_mean: float = MEASURED_MEAN_BPS, official_only: bool = True,
        winsor_bps: float = 150.0) -> CostFit:
    o = obs.copy()
    notes = []
    if official_only and "official" in o:
        drop = int((~o.official.astype(bool)).sum())
        if drop:
            notes.append(f"{drop} fill(s) without an official print skipped (ref_px is drift, not cost)")
        o = o[o.official.astype(bool)]
    o = o[np.isfinite(pd.to_numeric(o.get("bps", pd.Series(dtype=float)), errors="coerce").astype(float))]
    spread_fill = float(np.nanmedian(o.spread)) if len(o) and np.isfinite(o.spread).any() else 10.0
    if len(o) < 3:
        notes.append("fewer than 3 fills: returning the prior (measured mean, wide bounds)")
        cov = np.diag(PRIOR_SD ** 2)
        b = np.r_[prior_mean, np.zeros(len(FEATURES) - 1)]
        return CostFit(b, cov, 40.0, 0.0, len(o), o.date.nunique() if len(o) else 0, float(len(o)),
                       prior_mean, prior_mean + 1.645 * 40.0 / np.sqrt(max(1, len(o))), spread_fill, notes)
    y = np.clip(o.bps.values.astype(float), -winsor_bps, winsor_bps)
    if (np.abs(o.bps.values) > winsor_bps).any():
        notes.append(f"{int((np.abs(o.bps.values) > winsor_bps).sum())} fill(s) winsorised at +-{winsor_bps:g}bp")
    g = o.date.values
    X = design(o.price.values, o.adv.values, o.spread.values, (o.side == "sell").values.astype(float),
               o.directed.values, spread_fill)
    rho = icc(y, g)
    k = pd.Series(g).map(pd.Series(g).value_counts()).values
    w = 1.0 / (1.0 + (k - 1) * rho)
    pm, pub = clustered_ub(y, g)
    # residual scale from the pooled model (robust: MAD, then sd, whichever larger)
    r0 = y - y.mean()
    sigma = float(max(np.std(r0, ddof=1), 1.4826 * np.median(np.abs(r0 - np.median(r0))), 1.0))
    m0 = np.r_[prior_mean, np.zeros(len(FEATURES) - 1)]
    P0 = np.diag(1.0 / PRIOR_SD ** 2)
    # constant features in this sample (e.g. every sell directed) are unidentified: the prior holds them
    A = P0 + (X.T * w) @ X / sigma ** 2
    cov = np.linalg.inv(A)
    beta = cov @ (P0 @ m0 + (X.T * w) @ y / sigma ** 2)
    if len(o) < 30:
        notes.append(f"only {len(o)} fills: slopes are ~the prior (0); treat as a pooled mean")
    return CostFit(beta, cov, sigma, rho, len(o), int(pd.Series(g).nunique()), float(w.sum()), pm, pub,
                   spread_fill, notes)


# ---------------------------------------------------- simulator adapters
def cost_fn(cf: CostFit, bound: str = "mean", floor: float | None = 0.0):
    """f(price, adv) -> per-side bps, the (price, adv) half of book.cost_bps's signature.
    bound: mean | ub (one-sided 95%) | hi (two-sided 97.5%)."""
    def f(price, adv):
        price = np.asarray(price, float)
        if bound == "mean":
            c = cf.predict(price, adv)[0]
        elif bound == "hi":
            c = cf.predict(price, adv)[2]
        else:
            c = cf.ub(price, adv)
        return np.maximum(c, floor) if floor is not None else c
    return f


def cost_bps(model, price, adv):
    """Drop-in for book.cost_bps: a CostFit (mean) or a callable is used directly,
    anything else goes to book.cost_bps."""
    from . import book as B
    if isinstance(model, CostFit):
        return cost_fn(model)(price, adv)
    if callable(model):
        return np.asarray(model(np.asarray(price, float), np.asarray(adv, float)), float)
    return B.cost_bps(model, price, adv)


def tiers(cf: CostFit, floor: float = 0.0) -> dict:
    """book.TIERS-shaped tuples, evaluated at one representative name per tier bucket."""
    p = np.array([b[0] for b in BUCKETS]); a = np.array([b[1] for b in BUCKETS])
    mean = np.maximum(cf.predict(p, a)[0], floor)
    ub = np.maximum(cf.ub(p, a), floor)
    return {"live": tuple(float(round(x, 2)) for x in mean), "live_hi": tuple(float(round(x, 2)) for x in ub)}


def register(cf: CostFit, floor: float = 0.0) -> dict:
    """Add "live" / "live_hi" to book.TIERS (in this process only; book.py is untouched)."""
    from . import book as B
    t = tiers(cf, floor)
    B.TIERS.update(t)
    return t


# ----------------------------------------------------------- self-test
TRUE_BETA = np.array([2.0, -3.0, -1.5, 4.0, 1.0, -2.0])


def make_fixture(out: str | Path, n_days: int = 80, per_day: float = 5.0, seed: int = 11,
                 beta: np.ndarray = TRUE_BETA, sigma: float = 20.0, rho: float = 0.2) -> Path:
    """Synthetic logs in the executor's exact schema, with known coefficients."""
    rng = np.random.default_rng(seed)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    fills, decs, prints = [], [], []
    days = pd.bdate_range("2026-01-05", periods=n_days + 1)
    for i in range(n_days):
        d, d1 = days[i].strftime("%Y-%m-%d"), days[i + 1].strftime("%Y-%m-%d")
        k = max(1, rng.poisson(per_day))
        shock = rng.normal(0, sigma * np.sqrt(rho))        # the morning's shared auction conditions
        for j in range(k):
            sym = f"S{i:03d}{j}"
            price = float(np.exp(rng.uniform(np.log(3), np.log(150))))
            adv = float(np.exp(rng.uniform(np.log(5e6), np.log(1e9))))
            spread = float(np.exp(rng.normal(np.log(12), 0.6)))
            route = rng.choice(["NASDAQ", "NYSE", "AUTO"], p=[0.45, 0.35, 0.2])
            decs.append({"date": d, "sym": sym, "price": price, "day_ret": -0.1, "ibs": 0.05,
                         "vol20": 0.9, "spread_bps": round(spread, 1), "qty": 3, "adv": adv})
            close_px, open_px = price * (1 + rng.normal(0, 0.002)), price * (1 + rng.normal(0.01, 0.03))
            prints.append({"sym": sym, "date": d, "open": price, "close": close_px})
            prints.append({"sym": sym, "date": d1, "open": open_px, "close": open_px})
            for side, ref, dte, dirf in (("buy", close_px, d, 1.0), ("sell", open_px, d1, float(route != "AUTO"))):
                x = design([price], [adv], [spread], float(side == "sell"), dirf)[0]
                e = x @ beta + (shock if side == "sell" else 0.0) + rng.normal(0, sigma * np.sqrt(1 - rho))
                px = ref * (1 + e / 1e4 * (1 if side == "buy" else -1))
                fills.append({"coid": f"dlv.{sym}.{side}", "sym": sym, "leg": "night", "side": side,
                              "qty": 3, "fill_px": px, "ref_px": price, "slippage_bps": 0.0,
                              "route": "" if side == "buy" else str(route), "filled_at": dte + "T09:30:02"})
    with open(out / "daily-fills-live.jsonl", "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in fills)
    with open(out / "daily-decisions-live.jsonl", "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in decs)
    pd.DataFrame(prints).drop_duplicates(["sym", "date"], keep="last").to_csv(out / "prints.csv", index=False)
    return out


def selftest(tmp: str | Path) -> bool:
    ok = True
    # 1. recovery: ~800 fills, every true coefficient inside its 95% interval
    d = make_fixture(Path(tmp) / "big", n_days=80)
    f, dec = load_logs(d)
    cf = fit(build_obs(f, dec, load_prints(d / "prints.csv", f)), prior_mean=0.0)
    sd = np.sqrt(np.diag(cf.cov))
    inside = np.abs(cf.beta - TRUE_BETA) <= 1.96 * sd
    print(cf.summary()); print("  true", TRUE_BETA, "inside 95%:", inside)
    ok &= bool(inside.sum() >= 5)          # 6 intervals at 95%: allow one miss
    ok &= 0.0 <= cf.rho <= 0.9
    # 2. graceful at live size: 26 fills on 4 days -> ~pooled mean, same cost for every name
    d2 = make_fixture(Path(tmp) / "small", n_days=4, per_day=6.5, seed=3,
                      beta=np.array([-0.75, 0, 0, 0, 0, 0]), sigma=39.0)
    f2, dec2 = load_logs(d2)
    obs2 = build_obs(f2, dec2, load_prints(d2 / "prints.csv", f2))
    cf2 = fit(obs2)
    print(cf2.summary())
    p = np.array([5.0, 50.0, 140.0]); m, lo, hi = cf2.predict(p, np.array([1e7, 1e8, 1e9]))
    print("  small-sample predictions", np.round(m, 2), "95%", np.round(lo, 1), np.round(hi, 1))
    ok &= bool(np.ptp(m) < 8.0 and (hi - lo).min() > 5.0)
    # 3. empty / missing logs -> prior, no crash; simulator adapters shape-compatible
    cf3 = fit(build_obs(pd.DataFrame(), pd.DataFrame(), {}))
    ok &= abs(cf3.beta[0] - MEASURED_MEAN_BPS) < 1e-9
    c = cost_bps(cf2, np.array([5.0, 25.0]), np.array([1e7, 1e8]))
    ok &= c.shape == (2,) and np.all(c >= 0)
    t = tiers(cf); ok &= len(t["live"]) == 4 and all(u >= m_ for u, m_ in zip(t["live_hi"], t["live"]))
    # 4. fills with no official print are flagged and excluded
    obs4 = build_obs(f2, dec2, {})
    ok &= (~obs4.official).all() and fit(obs4).n == 0
    print("SELFTEST", "PASS" if ok else "FAIL")
    return bool(ok)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--tag", default="-live")
    ap.add_argument("--prints", default=None)
    ap.add_argument("--selftest", default=None, help="directory for the synthetic fixture")
    a = ap.parse_args(argv)
    if a.selftest:
        raise SystemExit(0 if selftest(a.selftest) else 1)
    fills, dec = load_logs(a.logs, a.tag)
    if fills.empty:
        print(f"no {a.logs}/daily-fills{a.tag}.jsonl here (the logs live on the server). "
              f"Prior only: {MEASURED_MEAN_BPS:+.2f}bp/side.")
    obs = build_obs(fills, dec, load_prints(a.prints, fills))
    cf = fit(obs)
    print(cf.summary())
    print("book.TIERS-shaped:", tiers(cf))
    if len(obs):
        g = obs[obs.official.astype(bool)] if "official" in obs else obs
        for side in ("buy", "sell"):
            x = g[g.side == side]
            if len(x) >= 2:
                m, u = clustered_ub(x.bps.values, x.date.values)
                print(f"  {side:4s} n {len(x):3d}  mean {m:+.2f}bp  day-clustered 95% UB {u:+.2f}bp")


if __name__ == "__main__":
    main()
