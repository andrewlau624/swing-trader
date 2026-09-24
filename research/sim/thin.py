"""Excluded night names: <= -8% losers the live filters drop for thin volume
(20d SIP $vol $5-10M, under night_adv_min) or price ($3-5, under night_price_min).

    .venv/bin/python -m research.sim.fetch_depth     # once (lm6 covers price >= 3, adv >= 5M)
    .venv/bin/python -m research.sim.thin

Question: does widening the universe to them improve V7 at tier AND tier_hi
costs in both halves? The tier model has no bucket for them (price < $10 is
one bucket, ADV only splits above $20), so costs for the NEW names are
overridden with a flat per-side figure (15 = no extra, 30, 50bp) and the
result is reported across that range. Everything else is the live pipeline:
IBS < 0.1 at 15:50, vol20 >= 60%, dedupe 0.7, crowding 30, tilt, weekend x0.5.
"""
from __future__ import annotations

import copy
import glob

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .depth import _rows_1550
from .validate import load_sim

CORR = 0.7
S2 = {"QQQ": 0.5, "SMH": 0.5}
V7 = dict(tilt="live", noise=S2, weekend_scale=0.5, conviction_w=0.5, noise_cap=1.0)
ADV_LIVE, PX_LIVE = 1e7, 5.0


def candidates() -> pd.DataFrame:
    """<= -8% and IBS < 0.1 at 15:50, prev close >= $3, 20d $vol >= $5M (the
    fetch universe), with the depth.candidates columns plus 15:59 minute volume."""
    pk = D.DATA / "thin_cands.pkl"
    if pk.exists():
        return pd.read_pickle(pk)
    P = D.panel(); C, V, O, L, H = P["close"], P["volume"], P["open"], P["low"], P["high"]
    C1 = C.shift(1); lr = np.log(C / C1)
    vol20 = lr.rolling(20).std() * np.sqrt(252)
    ret20 = C1 / C.shift(21) - 1
    adv = (C * V).rolling(20).mean().shift(1)
    on = O.shift(-1) / C - 1
    rows, v59 = [], {}
    for sub in ("lm1", "lm6"):
        for f in sorted(glob.glob(str(D.DATA / sub / "*.parquet"))):
            rows += _rows_1550(f, C, L, H)
            df = pd.read_parquet(f)
            if len(df):
                t = df.timestamp.dt.tz_convert("America/New_York")
                m = df[(t.dt.hour == 15) & (t.dt.minute == 59)]
                d = pd.Timestamp(f.split("/")[-1][:10])
                for s, vv, cc in zip(m.symbol, m.volume, m.close):
                    v59[(d, s)] = vv * cc
    x = pd.DataFrame(rows).drop_duplicates(["date", "sym"])
    get = lambda M: np.array([M.at[a, b] for a, b in zip(x.date, x.sym)], float)
    x["pc"] = get(C1)
    x["day50"] = x.p50 / x.pc - 1
    x["ibs50"] = (x.p50 - x.L50) / (x.H50 - x.L50).replace(0, np.nan)
    x = x[(x.day50 <= -0.08) & (x.ibs50 < 0.1)].copy()
    for k, M in (("ret", on), ("vol20", vol20), ("ret20", ret20), ("adv", adv), ("C", C), ("dvol", C * V)):
        x[k] = get(M)
    x["v59"] = [v59.get((a, b), np.nan) for a, b in zip(x.date, x.sym)]
    x = x[(x.adv >= 5e6) & (x.pc >= 3)]
    x = x[np.isfinite(x.ret) & (x.ret.abs() <= 1)]
    twin = x.groupby(["date", "day50", "ret"]).sym.transform("count")
    x = x[twin == 1].copy()
    x["new"] = (x.adv < ADV_LIVE) | (x.pc < PX_LIVE) | (x.p50 < PX_LIVE)
    x.to_pickle(pk)
    return x


def night_days(x: pd.DataFrame, adv_min: float, px_min: float) -> dict:
    """The live pipeline over the universe adv >= adv_min, price >= px_min."""
    R = D.returns20()
    idx = {d: i for i, d in enumerate(R.index)}
    x = x[(x.adv >= adv_min) & (x.pc >= px_min)]
    out = {}
    for d, g in x.groupby("date"):
        if d < B.START:
            continue
        rows = pd.DataFrame({"price": g.p50.values, "prev_close": g.pc.values,
                             "high": g.H50.values, "low": g.L50.values}, index=g.sym.values)
        keep = g.set_index("sym")
        picks = sg.loser_picks(rows, day_ret_max=-0.08, ibs_max=0.10, price_min=px_min, price_max=2000.0)
        if picks.empty:
            continue
        i = idx.get(pd.Timestamp(d))
        if i is not None:
            win = R.iloc[max(0, i - 20):i]
            cols = [s for s in picks.index if s in win.columns]
            picks, _ = sg.dedupe_correlated(picks, {s: win[s].dropna().tolist() for s in cols}, CORR)
        picks = picks.assign(vol20=keep.loc[picks.index, "vol20"].values)
        n_raw = len(picks)
        kept, frac = sg.night_sizing(picks, vol_min=0.60, crowd_n=30, max_name_pct=0.10)
        if kept.empty:
            continue
        k = keep.loc[kept.index]
        nd = B.NightDay(kept.index.values, kept.price.values, k.C.values, k.ret.values, k.adv.values,
                        k.vol20.values, k.ret20.values, kept.day_ret.values, frac, n_raw)
        nd.new = k.new.values
        out[pd.Timestamp(d)] = nd
    return out


# new-name cost override: cost_bps(model=(tier_name, ext_bps)) -> tier, with
# the new names (price < $5 or ADV < $10M) at max(tier, ext_bps)
_cost = B.cost_bps


def _cost_ext(model, price, adv):
    if isinstance(model, tuple):
        base, ext = model
        c = _cost(base, price, adv)
        new = (np.asarray(adv, float) < ADV_LIVE) | (np.asarray(price, float) < PX_LIVE)
        return np.where(new, np.maximum(c, ext), c)
    return _cost(model, price, adv)


B.cost_bps = _cost_ext


def row(df, lab):
    r = df.r
    parts = [B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)]
    body = "  ".join(f"{c*100:5.1f}/{s:4.2f}/{d*100:4.0f}" for c, s, d in parts)
    return f"{lab:40s} {body}   use {df.night_used.mean()*100:4.0f}%  end ${df.E.iloc[-1]:>9,.0f}"


def main():
    x = candidates()
    x = x[x.date >= B.START]
    g = x[x.vol20 >= 0.60]
    print(f"candidates {len(x):,} (<= -8%, IBS<0.1, 15:50), {int(x.new.sum()):,} excluded by live filters; "
          f"after vol20 >= 60%: {len(g):,} / {int(g.new.sum()):,}")
    grp = {"traded (adv>=10M, px>=5)": ~g.new,
           "adv 5-10M, px>=5": (g.adv < ADV_LIVE) & (g.pc >= PX_LIVE),
           "px 3-5, adv>=10M": (g.adv >= ADV_LIVE) & (g.pc < PX_LIVE),
           "px 3-5 and adv 5-10M": (g.adv < ADV_LIVE) & (g.pc < PX_LIVE)}
    print("\ngross close->open bp (t), per half; net at 15/30/50bp/side (full)")
    for lab, m in grp.items():
        h = g[m]; line = f"  {lab:26s} n {len(h):5,}"
        for lo, hi in (("2021", "2023"), ("2024", "2026")):
            q = h[(h.date >= lo) & (h.date <= hi + "-12-31")].ret
            line += f" | {lo[2:]}-{hi[2:]} {q.mean()*1e4:+6.1f} (t {q.mean()/q.std()*np.sqrt(len(q)) if len(q) > 1 else 0:+.1f})"
        med = h.ret.median() * 1e4
        line += " | net " + "/".join(f"{(h.ret.mean()*1e4 - 2*c):+.0f}" for c in (15, 30, 50))
        line += f" | median {med:+.0f}"
        print(line)

    # capacity: position $ vs the 15:59 minute $ volume and the day's $ volume, new names only
    h = g[g.new & np.isfinite(g.v59)]
    print("\ncapacity, new names (median / p90 share):")
    for E in (10_000, 50_000):
        pos = E * 0.5 * 0.10 * 2.0          # max tilt weight 2 -> 20% of the leg
        print(f"  ${E:,} book, ${pos:,.0f}/name max: of the 15:59 minute $vol "
              f"{np.nanmedian(pos / h.v59):.1%} / {np.nanpercentile(pos / h.v59, 90):.1%};  "
              f"of the day's $vol {np.median(pos / h.dvol):.2%} / {np.percentile(pos / h.dvol, 90):.2%}")

    s = load_sim()
    base_N = night_days(x, ADV_LIVE, PX_LIVE)
    variants = {"V7 (adv>=10M, px>=5)": (ADV_LIVE, PX_LIVE),
                "+ adv 5-10M": (5e6, PX_LIVE),
                "+ px 3-5": (ADV_LIVE, 3.0),
                "+ both": (5e6, 3.0)}
    Ns = {k: (base_N if v == (ADV_LIVE, PX_LIVE) else night_days(x, *v)) for k, v in variants.items()}
    for cost in ("tier", "tier_hi"):
        for ext in (15, 30, 50):
            print(f"\n=== {cost}, new names at max(tier, {ext}bp)/side   2021-23 / 2024-26 / full ===")
            for lab, N in Ns.items():
                sim = copy.copy(s); sim.N = N
                df = sim.replay(B.Params(night_cost=(cost, ext), **V7))
                print(row(df, lab))
            if ext == 15:
                sim = copy.copy(s)
                print(row(sim.replay(B.Params(night_cost=cost, **V7)), "  (V7 on the sim's own night data)"))


if __name__ == "__main__":
    main()
