"""Study BH - Asymmetric Bottom Hunter (pre-registered in round1_prose.md, N 818 -> 819).

    PYTHONPATH=. .venv/bin/python -m research.sim.bottom_hunter > data/research/program/bottom_hunter_out.txt

Question: does extreme price depression carry a favorable forward ASYMMETRY (bounded downside, large right
tail) that survives realistic costs on a survivorship-aware universe, and does conviction sizing harvest it?
One judged primary (sleeve excess vs same-day vol-decile placebo, 2021-26); everything else pre-specified
report-only. See the registration for frozen definitions and gates.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.universe import valid_symbol

from . import book as B

ROOT = Path(__file__).resolve().parents[2]
NIGHT = ROOT / "data" / "research" / "night"
PROG = ROOT / "data" / "research" / "program"
DELIST_RET = -0.30
ETF_RE = None  # set in _etf_re()

CACHE_PRE = PROG / "bh_panel_pre2021.pkl"


def _etf_re():
    global ETF_RE
    if ETF_RE is None:
        import re
        from .theme_explosion import ETF_RE as R
        ETF_RE = R
    return ETF_RE


def stock_cols(cols) -> np.ndarray:
    """True for tradable stocks (not ETFs/ETNs/funds/trusts) per asset_meta name + ticker regex."""
    meta = json.load(open(NIGHT / "asset_meta.json"))
    rx = _etf_re()
    out = []
    for s in cols:
        nm = (meta.get(s) or {}).get("name") or ""
        out.append(bool(valid_symbol(s)) and not rx.search(nm.upper()))
    return np.asarray(out, dtype=bool)


# ------------------------------------------------------------------ panels
def load_primary() -> dict:
    """panel.pkl: SIP daily, 2020-10..2026-09, survivorship-aware (incl. inactive)."""
    P = pd.read_pickle(NIGHT / "panel.pkl")
    return {k: P[k].astype(np.float32) for k in ("open", "high", "low", "close", "volume")}


def load_pre2021() -> dict | None:
    """2016-01..2020-12 from per-symbol bars_pre2021 cache. Survivorship-limited (today's symbols only),
    so REPORT-ONLY. Cached to program/bh_panel_pre2021.pkl."""
    if CACHE_PRE.exists():
        return pd.read_pickle(CACHE_PRE)
    try:
        import glob
        o, c, v = {}, {}, {}
        files = glob.glob(str(ROOT / "data/cache/bars_pre2021/*.parquet"))
        t0 = time.time()
        for i, f in enumerate(files):
            s = Path(f).stem
            try:
                d = pd.read_parquet(f)
            except Exception:
                continue
            if len(d) < 30:
                continue
            o[s] = d["open"].astype(np.float32)
            c[s] = d["close"].astype(np.float32)
            v[s] = d["volume"].astype(np.float32)
            if i % 3000 == 0:
                print(f"  pre2021 load {i}/{len(files)} ({time.time()-t0:.0f}s)", flush=True)
        O = pd.DataFrame(o).sort_index()
        C = pd.DataFrame(c).reindex(columns=O.columns)
        V = pd.DataFrame(v).reindex(columns=O.columns)
        d = {"open": O, "close": C, "volume": V}
        pd.to_pickle(d, CACHE_PRE)
        return d
    except Exception as e:  # noqa: BLE001
        print(f"pre2021 load failed: {e}", flush=True)
        return None


# ------------------------------------------------------------- core features
def features(P: dict) -> dict:
    C, O, L, V = P["close"], P["open"], P["low"], P["volume"]
    R = C.pct_change(fill_method=None)
    adv = (C * V).rolling(20, min_periods=15).median()
    nbars = C.notna().cumsum()
    ma20 = C.rolling(20, min_periods=15).mean()
    ma50 = C.rolling(50, min_periods=30).mean()
    ma200 = C.rolling(200, min_periods=100).mean()
    hi252 = C.rolling(252, min_periods=120).max()
    lo252 = C.rolling(252, min_periods=120).min()
    dd252 = C / hi252 - 1
    dd_all = C / C.expanding(min_periods=60).max() - 1
    # trailing-2y close percentile (rank of today's close within the last 504 sessions)
    pct2y = C.rolling(504, min_periods=200).rank(pct=True)
    # z of log price vs 200d trend
    lc = np.log(C.where(C > 0))
    z200 = (lc - lc.rolling(200, min_periods=100).mean()) / lc.rolling(200, min_periods=100).std()
    vol20 = R.rolling(20, min_periods=15).std() * np.sqrt(252)
    return dict(C=C, O=O, L=L, V=V, R=R, adv=adv, nbars=nbars, ma20=ma20, ma50=ma50, ma200=ma200,
                hi252=hi252, lo252=lo252, dd252=dd252, dd_all=dd_all, pct2y=pct2y, z200=z200, vol20=vol20)


def eligible(F: dict, cols_mask: np.ndarray, min_price=1.0, min_adv=1e6, min_hist=252) -> pd.DataFrame:
    return (F["C"] >= min_price) & (F["adv"] >= min_adv) & (F["nbars"] >= min_hist) & cols_mask[None, :]


def forward_arrays(F: dict, C: pd.DataFrame, O: pd.DataFrame, L: pd.DataFrame) -> dict:
    """fwd[H] = C[t+H]/O[t+1]-1 (enter next open, exit close t+H); min_fwd[H] = min(L[t+1..t+H])/O[t+1]-1."""
    out = {}
    for H in (21, 63, 126, 252):
        fwd = C.shift(-H) / O.shift(-1) - 1
        mn = L.rolling(H, min_periods=H).min().shift(-H) / O.shift(-1) - 1
        out[H] = (fwd.astype(np.float32), mn.astype(np.float32))
    # reached the prior 252d high within the next 252 sessions
    out["recover"] = (C.rolling(252, min_periods=252).max().shift(-252) >= F["hi252"]).astype(np.float32)
    return out


def cells(cond: pd.DataFrame, arr: pd.DataFrame) -> np.ndarray:
    x = arr.values[cond.values]
    return x[np.isfinite(x)]


def excess_cells(cond: pd.DataFrame, arr: pd.DataFrame, dm: pd.Series):
    fr = arr.values
    d = dm.reindex(cond.index).values[:, None]
    m = cond.values & np.isfinite(fr) & np.isfinite(d)
    return fr[m], (fr - d)[m]


def dist(x: np.ndarray) -> str:
    if len(x) < 20:
        return f"n={len(x)} (too few)"
    p = np.nanpercentile(x, [5, 25, 50, 75, 95])
    return (f"n {len(x):>6d}  mean {np.nanmean(x)*100:+5.1f}  med {p[2]*100:+5.1f}  "
            f"q25 {p[1]*100:+5.1f} q75 {p[3]*100:+5.1f}  P(+) {np.nanmean(x>0)*100:4.0f}%  "
            f"P(+25) {np.nanmean(x>.25)*100:4.1f}%  P(+50) {np.nanmean(x>.5)*100:4.1f}%  "
            f"P(+100) {np.nanmean(x>1.)*100:4.1f}%  P(+200) {np.nanmean(x>2.)*100:4.1f}%  "
            f"P(+500) {np.nanmean(x>5.)*100:4.1f}%  P(-20) {np.nanmean(x<-.2)*100:4.1f}%  "
            f"P(-50) {np.nanmean(x<-.5)*100:4.1f}%")


# --------------------------------------------------------------- sleeve sim
def build_lists(S: pd.DataFrame, F: dict, elig: pd.DataFrame, size_rank: pd.DataFrame) -> dict:
    """day index -> column indices of signal names, ranked by score (desc)."""
    dates = S.index
    cols = np.arange(S.shape[1])
    out = {}
    sv = S.values
    ev = elig.values
    rv = size_rank.values
    for i in range(S.shape[0]):
        m = sv[i] & ev[i]
        if not m.any():
            continue
        cand = cols[m]
        order = cand[np.argsort(-rv[i][cand], kind="stable")]
        out[i] = order.tolist()[:12]
    return out


def _tier_cost(px, adv, model="tier_hi"):
    t = B.TIERS[model]
    if px < 10:
        bp = t[0]
    elif px < 20:
        bp = t[1]
    elif adv < 5e7:
        bp = t[2]
    else:
        bp = t[3]
    return bp / 1e4


def run_sleeve(F: dict, lists: dict, delist_day: dict, *, slots=10, size_mode="equal",
               maxhold=126, trail=0.25, ma_exit=True, cost=None, bil=None,
               cap=0.10, cost_model="tier_hi") -> tuple[pd.Series, pd.DataFrame]:
    """cost: flat per-side bps override; else per-name tier_hi. Entry next open, exit open, 25% trail/MA50/maxhold."""
    C, O, ma50 = F["C"].values, F["O"].values, F["ma50"].values
    AV = F["adv"].values
    score = lists.pop("_score", None)
    dates = F["C"].index
    T, N = C.shape
    dcol = {c: i for i, c in enumerate(F["C"].columns)}
    delist_i = {dcol[s]: d for s, d in delist_day.items() if s in dcol}
    cash = 1.0
    pos = {}   # col -> dict(q, peak, entry, i_in)
    eq = np.ones(T)
    trades = []
    pending_exit = {}   # col -> exit day index

    def cst(i, c):
        return cost if cost is not None else _tier_cost(O[i, c], AV[i, c], cost_model)

    for i in range(T):
        for c in [c for c, j in pending_exit.items() if j == i]:
            p = pos.pop(c)
            px = O[i, c]
            if np.isfinite(px):
                c0 = cst(i, c)
                cash += p["q"] * px * (1 - c0)
                trades.append(dict(i_in=p["i_in"], i_out=i, c=c, ret=px / p["entry"] - 1))
            pending_exit.pop(c, None)
        for c, j in list(delist_i.items()):
            if j == i and c in pos:
                p = pos.pop(c)
                cash += p["q"] * C[i, c] * (1 + DELIST_RET)
                trades.append(dict(i_in=p["i_in"], i_out=i, c=c, ret=-1.0 + (1 + DELIST_RET)))
                pending_exit.pop(c, None)
        if i in lists and len(pos) < slots:
            cand = lists[i]
            room = slots - len(pos)
            new = []
            for c in cand:
                if c in pos or c in pending_exit or not np.isfinite(O[i, c]) or O[i, c] <= 0:
                    continue
                new.append(c)
                if len(new) >= room:
                    break
            if new:
                eq_now = cash + sum(p["q"] * C[i, c] for c, p in pos.items())
                base = eq_now / slots
                if size_mode == "conviction" and score is not None:
                    sc = np.array([max(score[i, c], 1e-6) for c in new])
                    w = base * sc / sc.mean()
                    w = np.minimum(w, sc / sc.max() * 2 * base)
                else:
                    w = np.full(len(new), base)
                for c, wi in zip(new, w):
                    amt = min(wi, cap * eq_now, cash)
                    if amt <= 1e-9:
                        continue
                    c0 = cst(i, c)
                    q = amt * (1 - c0) / O[i, c]
                    cash -= amt
                    pos[c] = dict(q=q, peak=C[i, c], entry=O[i, c], i_in=i)
                    trades.append(dict(i_in=i, i_out=-1, c=c, ret=np.nan))
        eq[i] = cash + sum(p["q"] * C[i, c] for c, p in pos.items())
        if bil is not None:
            cash *= (1 + bil.iloc[i])
        for c, p in list(pos.items()):
            px = C[i, c]
            if not np.isfinite(px):
                continue
            p["peak"] = max(p["peak"], px)
            if (px <= (1 - trail) * p["peak"]) or (ma_exit and np.isfinite(ma50[i, c]) and px < ma50[i, c]) \
               or (i - p["i_in"] >= maxhold):
                pending_exit.setdefault(c, i + 1)
    r = pd.Series(eq, index=dates).pct_change().fillna(0.0)
    return r, pd.DataFrame(trades)


# ------------------------------------------------------------------- main
def main():
    t0 = time.time()
    print("=" * 100)
    print("Study BH - Asymmetric Bottom Hunter  (N 818 -> 819; one judged primary)")
    print("=" * 100, flush=True)

    P = load_primary()
    F = features(P)
    mask = stock_cols(F["C"].columns)
    lastv = F["C"].notna()[::-1].idxmax()
    ndel = int((lastv < F["C"].index[-11]).sum())
    print(f"primary panel {F['C'].index[0].date()} -> {F['C'].index[-1].date()}, {F['C'].shape[1]} symbols, "
          f"{int(mask.sum())} stocks; delisted in panel: {ndel}", flush=True)

    elig = eligible(F, mask)
    per = elig.sum(axis=1)
    print("eligible names/day by year: " + ", ".join(f"{y}:{int(per[str(y)].mean())}" for y in range(2020, 2027)), flush=True)

    fwd = forward_arrays(F, F["C"], F["O"], F["L"])
    daymean = {H: fwd[H][0].where(elig).mean(axis=1) for H in (21, 63, 126, 252)}

    # ---- R1: forward distribution by DD252 bucket (excess over same-day eligible-universe mean) ----
    print("\n" + "-" * 100)
    print("R1. Forward return by DD252 bucket, entered next open; excess over same-day eligible mean")
    print("-" * 100)
    buckets = [("DD -30..-50", (F["dd252"] <= -0.30) & (F["dd252"] > -0.50)),
               ("DD -50..-70", (F["dd252"] <= -0.50) & (F["dd252"] > -0.70)),
               ("DD -70..-85", (F["dd252"] <= -0.70) & (F["dd252"] > -0.85)),
               ("DD <=-85", F["dd252"] <= -0.85),
               ("DD <=-70 (EXTREME)", F["dd252"] <= -0.70)]
    for lab, cond in buckets:
        cond = cond & elig
        print(f"\n {lab}:")
        for H in (21, 63, 126, 252):
            x, ex = excess_cells(cond, fwd[H][0], daymean[H])
            print(f"   H={H:>3d} raw  {dist(x)}")
            print(f"         excess {dist(ex)}")

    print("\n Reached prior 252d high within 252 sessions (recovery rate), DD<=-70:")
    rec = F["C"].rolling(252, min_periods=252).max().shift(-252) >= F["hi252"]
    for lab, cond in (("all eligible", elig), ("DD<=-70", elig & (F["dd252"] <= -0.70)),
                      ("DD<=-85", elig & (F["dd252"] <= -0.85))):
        x = rec.values[cond.values]
        x = x[np.isfinite(x)]
        print(f"   {lab:12s} P(recover<=252d) {np.nanmean(x)*100:4.1f}%  n {len(x)}")

    # ---- R2: falling knife ----
    print("\n" + "-" * 100)
    print("R2. Falling knife: additional drawdown after the signal (min low over next H / entry open - 1)")
    print("-" * 100)
    for lab, cond in (("eligible (base)", elig), ("DD<=-70", elig & (F["dd252"] <= -0.70))):
        print(f" {lab}:")
        for H in (21, 63, 126, 252):
            x = cells(cond, fwd[H][1])
            print(f"   H={H:>3d} {dist(x)}  P(-30) {np.nanmean(x<-.3)*100:4.1f}%  P(-50) {np.nanmean(x<-.5)*100:4.1f}%")

    # ---- R3: survival filters ----
    print("\n" + "-" * 100)
    print("R3. Survival filters at the extreme-low signal (DD<=-70), forward 126d excess vs same-day eligible mean")
    print("-" * 100)
    base = elig & (F["dd252"] <= -0.70)
    buys = None
    bp = NIGHT / "insider" / "buys.parquet"
    if bp.exists():
        buys = pd.read_parquet(bp)
        buys["fd"] = pd.to_datetime(buys.fd)
        buys = buys[buys.get("insider", True).astype(bool)]
    insider_hit = None
    if buys is not None:
        sset = set(F["C"].columns)
        buys = buys[buys.sym.isin(sset)]
        by = {s: np.sort(g.fd.values.astype("datetime64[ns]")) for s, g in buys.groupby("sym")}
        dates_np = F["C"].index.values.astype("datetime64[ns]")
        cols = list(F["C"].columns)
        hit = np.zeros((len(dates_np), len(cols)), dtype=bool)
        window = np.timedelta64(60, "D")
        for s, arr in by.items():
            j = np.searchsorted(arr, dates_np, side="right")
            prev = np.where(j > 0, arr[np.clip(j - 1, 0, len(arr) - 1)], np.datetime64("NaT", "ns"))
            ok = (j > 0) & ((dates_np - prev) <= window)
            hit[ok, cols.index(s)] = True
        insider_hit = pd.DataFrame(hit, index=F["C"].index, columns=F["C"].columns)
        print(f" (Form 4 buys loaded: {len(buys)} rows, {buys.sym.nunique()} symbols)")
    filters = {
        "base DD<=-70": base,
        "price >= $10": base & (F["C"] >= 10),
        "price $1-3 (broken)": base & (F["C"] < 3),
        "ADV >= $10M": base & (F["adv"] >= 1e7),
        "close > MA20 (stabilizing)": base & (F["C"] > F["ma20"]),
        "not new 252d low (>1.05x lo)": base & (F["C"] > 1.05 * F["lo252"]),
        "insider buy <=60d": (base & insider_hit) if insider_hit is not None else None,
    }
    for lab, cond in filters.items():
        if cond is None:
            print(f"   {lab:34s} (no insider data)")
            continue
        x, ex = excess_cells(cond, fwd[126][0], daymean[126])
        print(f"   {lab:34s} raw {dist(x)}")
        print(f"   {'':34s} excess {dist(ex)}")

    # placebo per filter: same-day same-vol-decile random eligible names, 20 seeds
    print("\n   placebo (same day, same vol20 decile, eligible, 20 seeds): 126d excess mean +/- sd")
    dec = F["vol20"].where(elig).rank(axis=1, pct=True).values
    pools = {}
    for lab, cond in filters.items():
        if cond is None:
            continue
        cv = cond.values
        fr = fwd[126][0].values
        dm = daymean[126].values
        exs = []
        rng = np.random.default_rng(0)
        idx = np.arange(F["C"].shape[0])
        for seed in range(20):
            vals = []
            for i in np.where(cv.any(axis=1))[0]:
                cand = np.where(cv[i])[0]
                dpt = dec[i]
                pool_i = pools.setdefault(i, None)
                for c in cand:
                    if not np.isfinite(fr[i, c]) or not np.isfinite(dm[i]):
                        continue
                    key = (i, round(dpt[c], 2))
                    pool = pools.get(key)
                    if pool is None:
                        pool = np.where(elig.values[i] & (np.abs(dec[i] - dpt[c]) < 0.06))[0]
                        pools[key] = pool
                    if len(pool) == 0:
                        continue
                    cc = pool[rng.integers(len(pool))]
                    vals.append(fr[i, cc] - dm[i])
            exs.append(np.nanmean(vals))
        exs = np.array(exs)
        print(f"   {lab:34s} placebo excess {exs.mean()*100:+.2f}bp (sd {exs.std()*100:.2f})  n_sig/d {cv.sum()/max(cv.any(axis=1).sum(),1):.1f}")

    # ---- R5: theme / sector capitulation ----
    print("\n" + "-" * 100)
    print("R5. Theme/sector capitulation: buy after own DD252<=-20% (report -30%), hold 126, exit next open")
    print("-" * 100)

    def sym_bars(s):
        parts = []
        for c in ("bars_pre2021", "bars"):
            f = ROOT / "data/cache" / c / f"{s}.parquet"
            if f.exists():
                parts.append(pd.read_parquet(f))
        if not parts:
            return None
        d = pd.concat(parts).sort_index()
        d = d[~d.index.duplicated()]
        d.index = pd.to_datetime(d.index)
        return d

    themes = {
        "quantum ETF QTUM": ["QTUM"],
        "quantum basket": ["RGTI", "IONQ", "QBTS", "QUBT", "ARQQ"],
        "robotics (BOTZ,ROBO)": ["BOTZ", "ROBO"],
        "semis (SMH,SOXX)": ["SMH", "SOXX"],
        "space (ARKX,ARKQ)": ["ARKX", "ARKQ"],
        "clean/nuclear (ICLN,TAN,URA,NLR)": ["ICLN", "TAN", "URA", "NLR"],
        "biotech (XBI,IBB)": ["XBI", "IBB"],
        "energy (XLE,XOP)": ["XLE", "XOP"],
        "lithium (LIT)": ["LIT"],
        "ark (ARKK)": ["ARKK"],
        "broad tech (QQQ)": ["QQQ"],
        "SMH": ["SMH"],
    }
    spy = sym_bars("SPY")
    spy_ret = spy["close"].pct_change(fill_method=None) if spy is not None else None
    for lab, members in themes.items():
        rows = []
        for s in members:
            d = sym_bars(s)
            if d is None or len(d) < 300:
                continue
            c = d["close"]
            hi = c.rolling(252, min_periods=120).max()
            dd = c / hi - 1
            op = d["open"]
            for thr in (-0.20, -0.30):
                sig = (dd <= thr) & (dd.shift(1) > thr)   # crossing into the band
                idc = np.where(sig.fillna(False).values)[0]
                rets = []
                for i in idc:
                    j = i + 1
                    k = min(i + 127, len(c) - 1)
                    if j >= len(c) or k <= j or not np.isfinite(op.iloc[j]) or not np.isfinite(c.iloc[k]):
                        continue
                    r = c.iloc[k] / op.iloc[j] - 1
                    sr = (spy_ret.iloc[i + 1:k + 1].sum() if spy_ret is not None and k < len(spy_ret) else np.nan)
                    rets.append((r, r - sr))
                if rets:
                    a = np.array(rets)
                    rows.append((s, thr, len(a), np.mean(a[:, 0]) * 100, np.mean(a[:, 1]) * 100))
        for s, thr, n, m, e in rows:
            print(f"   {lab:32s} {s:6s} thr{thr:+.2f} n {n:>3d}  mean {m:+6.1f}%  excess-spy {e:+6.1f}%")

    # ---- R6 / PRIMARY: conviction sleeve vs placebo ----
    print("\n" + "-" * 100)
    print("R6. Sleeve: DD<=-70, close>=$3, 10 slots, conviction sizing, 25% trail / MA50 / 126d exit, tier_hi")
    print("-" * 100)
    sig = elig & (F["dd252"] <= -0.70) & (F["C"] >= 3)
    score = (np.minimum(2.0, np.maximum(0.5, 1 + (F["dd252"].abs() - 0.70) / 0.30))
             * np.where(F["C"] > F["ma20"], 1.0, 0.75))
    last = F["C"].notna()[::-1].idxmax()
    end = F["C"].index[-11]
    delist_day = {s: d for s, d in last.items() if d < end}
    base_lists = build_lists(sig, F, elig, score)
    base_lists["_score"] = score.values

    def bil_series():
        try:
            e = pd.read_parquet(NIGHT / "etf_daily.parquet")
            e["d"] = pd.to_datetime(e.timestamp).dt.tz_localize(None).dt.normalize()
            b = e[e.symbol == "BIL"].set_index("d")["close"]
            return (b.pct_change(fill_method=None).reindex(F["C"].index).fillna(0.0))
        except Exception:
            return None

    BIL = bil_series()
    res = {}
    variants = {
        "equal": (sig, "equal", None),
        "conviction": (sig, "conviction", None),
        "conv+MA20 confirm": (sig & (F["C"] > F["ma20"]), "conviction", None),
        "conv flat 25bp": (sig, "conviction", 25e-4),
    }
    for mode, (sg_, smode, costv) in variants.items():
        L2 = build_lists(sg_, F, elig, score)
        L2["_score"] = score.values
        r, tr = run_sleeve(F, L2, delist_day, size_mode=smode, cost=costv,
                           cost_model="tier_hi", bil=BIL)
        res[mode] = (r, tr)
        c, sh, dd = B.stats(r)
        print(f"   {mode:20s} {F['C'].index[0].date()}..{F['C'].index[-1].date()}  "
              f"CAGR {c*100:5.1f}%  Sharpe {sh:4.2f}  maxDD {dd*100:5.1f}%  trades {len(tr)}")
        tt = tr[tr.ret.notna()]
        if len(tt):
            g = tt.groupby("c").ret.agg(["count", "mean"]).sort_values("count", ascending=False).head(6)
            g.index = [F["C"].columns[c] for c in g.index]
            print(f"      top symbols by trade count: " +
                  ", ".join(f"{s}({int(n)}x,{m*100:+.0f}%)" for s, n, m in zip(g.index, g["count"], g["mean"])))
            top = tt.nlargest(5, "ret")
            print("      best 5 trades: " + ", ".join(f"{F['C'].columns[c]}({v*100:+.0f}%)" for c, v in zip(top.c, top.ret)))
            rb = r.drop(r.nlargest(5).index)
            c2, sh2, dd2 = B.stats(rb)
            print(f"      ex-best-5-DAYS CAGR {c2*100:5.1f}%  Sharpe {sh2:4.2f}")

    # placebo: random eligible same-vol-decile names, same exits/sizing, 30 seeds
    dec = F["vol20"].where(elig).rank(axis=1, pct=True).values
    bucket = np.clip((np.nan_to_num(dec) * 10).astype(int), 0, 9)
    elig_v = elig.values
    pool_by_day = []
    for i in range(F["C"].shape[0]):
        pool_by_day.append([np.where(elig_v[i] & (bucket[i] == b))[0] for b in range(10)])
    plac = []
    for seed in range(30):
        rng2 = np.random.default_rng(1000 + seed)
        L3 = {}
        for i, cand in base_lists.items():
            if i == "_score":
                continue
            pools = pool_by_day[i]
            new = []
            for c in cand:
                pool = pools[bucket[i, c]]
                new.append(int(pool[rng2.integers(len(pool))]) if len(pool) else c)
            L3[i] = new
        L3["_score"] = score.values
        rr, _ = run_sleeve(F, L3, delist_day, size_mode="conviction", cost=None, cost_model="tier_hi", bil=BIL)
        plac.append(rr)
    Pmat = pd.concat(plac, axis=1)
    print(f"   placebo (30 seeds) CAGR {np.mean([B.stats(x)[0] for x in plac])*100:5.1f}%  "
          f"Sharpe {np.mean([B.stats(x)[1] for x in plac]):4.2f}  maxDD {np.mean([B.stats(x)[2] for x in plac])*100:5.1f}%")

    # judged primary on 2021-10.. (signals need 252d) to end: excess daily vs placebo mean
    prim = None
    for mode in ("equal", "conviction"):
        r = res[mode][0]
        pl_mean = Pmat.mean(axis=1).reindex(r.index).fillna(0.0)
        d = (r - pl_mean)
        d = d["2021-10-01":]
        if mode == "conviction":
            prim = d
        t = (d.mean() / (d.std() / np.sqrt(len(d)))) if d.std() > 0 else np.nan
        c, sh, dd = B.stats(r["2021-10-01":])
        pc, psh, pdd = B.stats(pl_mean["2021-10-01":])
        print(f"   {mode:11s} 2021-10+  sleeve CAGR {c*100:5.1f}% Sharpe {sh:4.2f} DD {dd*100:5.1f}% | "
              f"placebo CAGR {pc*100:5.1f}% Sharpe {psh:4.2f} | excess mean {d.mean()*1e4:+.1f}bp/day t {t:.2f}")

    if prim is not None:
        d = prim
        best5 = d.nlargest(5).sum()
        ex5 = d.drop(d.nlargest(5).index)
        print(f"   PRIMARY excess: mean {d.mean()*1e4:+.1f}bp/day, t {d.mean()/(d.std()/np.sqrt(len(d))):.2f}, "
              f"ex-best-5 mean {ex5.mean()*1e4:+.1f}bp")
        yr = d.groupby(d.index.year).sum()
        print("   excess by year (bp): " + ", ".join(f"{y}:{v*1e4:+.0f}" for y, v in yr.items()))
        # edge haircut: halve sleeve's daily excess
        half = pl_mean + d * 0.5
        c, sh, dd = B.stats(half["2021-10-01":])
        print(f"   50% edge haircut: CAGR {c*100:5.1f}% Sharpe {sh:4.2f} maxDD {dd*100:5.1f}%")

    # dollars
    print("\n   Dollars at capital levels (conviction sleeve, 2021-10..end, no compounding across sizes):")
    r = res["conviction"][0]["2021-10-01":]
    yrs = len(r) / 252
    cagr = (1 + r).prod() ** (1 / yrs) - 1
    for cap0 in (2500, 10000, 25000, 100000, 500000, 1000000):
        print(f"     ${cap0:>9,}: ~{cap0*cagr:>10,.0f}/yr (CAGR {cagr*100:.1f}%)")

    # ---- pre-2021 extension (report only) ----
    print("\n" + "-" * 100)
    print("EXT. 2016-2020 extension (bars_pre2021, survivorship-limited today's symbols) -- REPORT ONLY")
    print("-" * 100)
    Pre = load_pre2021() if not os.environ.get("BH_SKIP_PRE") else None
    if Pre is not None:
        try:
            Fp = features({**Pre, "high": Pre["close"], "low": Pre["close"]})
            maskp = stock_cols(Fp["C"].columns)
            eligp = eligible(Fp, maskp)
            fwdp = forward_arrays(Fp, Fp["C"], Fp["O"], Fp["L"])
            dmp = fwdp[126][0].where(eligp).mean(axis=1)
            cp = eligp & (Fp["dd252"] <= -0.70) & (Fp["C"] >= 3)
            x, ex = excess_cells(cp, fwdp[126][0], dmp)
            print(f" 2016-20 DD<=-70 126d raw  {dist(x)}")
            print(f"           excess {dist(ex)}")
            print(f"  signal-days {int(cp.values.sum())}, symbols {int(cp.any(axis=0).sum())}")
        except Exception as e:  # noqa: BLE001
            print(f"  extension failed: {e}")
    print(f"\ndone in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
