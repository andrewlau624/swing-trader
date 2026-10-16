"""NDISC: when does the night leg lose? Discovery -> holdout conditioning search.

Pre-registered in research/drafts/round1_prose.md (N 1014 -> 1015). Exploratory search with a placebo scan.
DISCOVERY 2016-02..2022-12 (sub-halves 2016-19 / 2020-22), HOLDOUT A 2023-01..2026-09 (exact 15:40 picks),
HOLDOUT B 2003-2015 (Sharadar daily-close proxy via nx.collect_trades; only daily-computable features).
Candidates + combined rule are frozen from DISCOVERY and printed before any holdout number is computed.
"""
import glob
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
sys.path.insert(0, "research/sim")

COST = 2 * 7.5e-4
NIGHT_W = 0.65
OUT = "data/research/program/ndisc_out.txt"
B_CACHE = "data/research/program/ndisc_B_cache.parquet"
NPLACEBO = int(os.environ.get("NDISC_NPLACEBO", 500))
D_LO, D_HI, A_LO, A_HI = "2016-02-01", "2022-12-31", "2023-01-01", "2026-12-31"
SPLIT_HALF = "2020-01-01"          # discovery sub-halves 2016-19 / 2020-22
LINES = []


def log(s=""):
    print(s, flush=True)
    LINES.append(s)


# ---------------------------------------------------------------- market (A: SIP minutes)
def mkt_minute(sym):
    m = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob(f"data/research/night/m1/{sym}_20*.parquet")))
    t = pd.to_datetime(m.timestamp, utc=True).dt.tz_convert("America/New_York")
    m = m.assign(d=t.dt.tz_localize(None).dt.normalize(), hm=t.dt.strftime("%H:%M"))
    m = m[(m.hm >= "09:30") & (m.hm <= "15:59")]
    g = m.groupby("d")
    q = pd.DataFrame({"open": g.open.first(), "close": g.close.last()})
    q["p40"] = m[m.hm == "15:39"].set_index("d")["close"]                 # 15:40 print
    pre = m[m.hm <= "15:39"].groupby("d")
    q["hi"], q["lo"] = pre.high.max(), pre.low.min()
    return q


def mkt_feats(q, nm):
    """q: index sessions, cols p40 (15:40 proxy), close, hi, lo. Everything known at 15:40 of d."""
    pc = q.close.shift(1)
    f = pd.DataFrame(index=q.index)
    f[f"{nm}_d40"] = q.p40 / pc - 1
    f[f"{nm}_r5"] = q.p40 / q.close.shift(5) - 1
    f[f"{nm}_r20"] = q.p40 / q.close.shift(20) - 1
    for k in (20, 50, 200):
        f[f"{nm}_ma{k}"] = q.p40 / q.close.shift(1).rolling(k).mean() - 1
    f[f"{nm}_rng"] = (q.hi - q.lo) / pc
    return f


def vix_feats(sessions):
    def rd(n):
        v = pd.read_csv(f"data/research/program/cboe/{n}.csv")
        v["DATE"] = pd.to_datetime(v.DATE, format="%m/%d/%Y")
        return v.set_index("DATE").CLOSE
    v, v9 = rd("VIX"), rd("VIX9D")
    vs = v.reindex(v.index.union(sessions)).ffill().reindex(sessions)
    v9s = v9.reindex(v9.index.union(sessions)).ffill().reindex(sessions)
    v9s[sessions < v9.index.min()] = np.nan
    p = vs.shift(1)                                   # prior-day close
    f = pd.DataFrame(index=sessions)
    f["vix_lvl"] = p
    f["vix_d1"] = p - vs.shift(2)
    f["vix_d5"] = p - vs.shift(6)
    f["vix_pct252"] = p.rolling(252).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    f["vix9_ratio"] = v9s.shift(1) / p
    return f


def calendar_feats(sessions, fomc):
    s = pd.Series(sessions, index=sessions)
    nxt = s.shift(-1)
    c = pd.DataFrame(index=sessions)
    c["weekday"] = sessions.weekday.astype(float)
    c["preweekend_hol"] = ((nxt - s).dt.days > 1).astype(float).where(nxt.notna())
    ym = pd.Series(sessions.year * 100 + sessions.month, index=sessions)
    first = ym.groupby(ym).cumcount()
    last = ym.groupby(ym).cumcount(ascending=False)
    c["monthend_pm2"] = ((first < 2) | (last < 2)).astype(float)
    if fomc is None:
        c["fomc_eve"] = np.nan
    else:
        c["fomc_eve"] = nxt.isin(fomc).astype(float).where(nxt.notna())
    # OPEX week = Mon..Fri week containing the 3rd Friday
    mon = sessions - pd.to_timedelta(sessions.weekday, unit="D")
    fri3 = set()
    for m in pd.period_range(sessions.min(), sessions.max(), freq="M"):
        d = pd.date_range(m.start_time, m.end_time, freq="W-FRI")
        if len(d) >= 3:
            fri3.add(d[2] - pd.Timedelta(days=4))
    c["opex_week"] = [1.0 if x in fri3 else 0.0 for x in mon]
    return c


def night_market_table(sessions, qs, fomc):
    n = pd.concat([mkt_feats(qs[k], k) for k in ("QQQ", "SPY", "IWM")], axis=1)
    n["iwm_qqq_spread"] = n.IWM_d40 - n.QQQ_d40
    lr = np.log(qs["QQQ"].close).diff()
    n["rv20"] = lr.shift(1).rolling(20).std() * np.sqrt(252)
    return n.join(vix_feats(sessions)).join(calendar_feats(sessions, fomc))


# ---------------------------------------------------------------- picks
def letf_flags():
    t = pd.read_parquet("data/research/nx/cache_TICKERS.parquet")
    t = t[t.table.isin(["SEP", "SFP"])].copy()
    t["_p"] = (t.table != "SEP").astype(int)
    t = t.sort_values("_p", kind="mergesort").drop_duplicates("ticker").set_index("ticker")
    cat = t.category.fillna("").str.upper()
    etf = cat.str.startswith(("ETF", "ETN", "ETD", "ETMF"))
    name = t.name.fillna("").str.upper()
    rx = re.compile(r"\b[123](\.5)?X\b|-[123]X|ULTRA|BULL|BEAR|INVERSE|SHORT|LEVERAGED|DAILY")
    lev = etf & name.map(lambda s: bool(rx.search(s)))
    mp = json.load(open("swingtrader/daily/letf_map.json"))["map"]
    lev = lev | lev.index.isin(list(mp))
    return etf.astype(float), lev.astype(float)


def load_A_picks():
    a = pd.read_parquet("data/research/program/night_exact_pre2021.parquet").reset_index()
    a = a[a.date < "2020-11-05"][["date", "sym", "day_ret", "ibs", "adv", "ret"]].copy()
    b = pd.read_parquet("data/research/recent/night_replay.parquet")[
        ["date", "sym", "day_ret", "ibs", "adv", "ret", "p40", "vol20"]].copy()
    b["ret"] = b.ret / 1e4
    p = pd.concat([a, b], ignore_index=True)
    p["date"] = pd.to_datetime(p.date)
    p["gross"] = p.ret
    p["net"] = p.gross - COST
    return p.sort_values(["date", "sym"]).reset_index(drop=True)


def daily_pick_feats(p):
    """Gap, intraday path, vol20, 5d return, price from daily bars (pre2021 + current caches)."""
    out = []
    for sym, g in p.groupby("sym"):
        parts = []
        for d in ("bars_pre2021", "bars"):
            try:
                parts.append(pd.read_parquet(f"data/cache/{d}/{sym.replace('/', '.')}.parquet"))
            except Exception:
                pass
        if not parts:
            continue
        b = pd.concat(parts)
        b = b[~b.index.duplicated(keep="last")].sort_index()
        b.index = pd.DatetimeIndex(b.index).astype("datetime64[ns]")
        lr = np.log(b.close).diff()
        f = pd.DataFrame({"prevc": b.close.shift(1), "o": b.open,
                          "vol20_b": lr.shift(1).rolling(20).std() * np.sqrt(252),
                          "ret5": b.close.shift(1) / b.close.shift(6) - 1})
        x = g[["date"]].join(f, on="date")
        out.append(x.drop(columns="date"))
    q = p.join(pd.concat(out))
    q["gap"] = q.o / q.prevc - 1
    q["intra"] = (1 + q.day_ret) * q.prevc / q.o - 1
    q["price"] = q.p40.where(q.p40.notna(), q.prevc * (1 + q.day_ret))
    q["vol20"] = q.vol20_b                              # one definition across the whole period (daily bars)
    return q


# ---------------------------------------------------------------- B (Sharadar daily proxy)
def build_B():
    if os.path.exists(B_CACHE):
        return pd.read_parquet(B_CACHE)
    from research.sim import nx
    P = nx.Paths()
    lo, hi = nx.JUDGE
    master = nx.load_master(P)
    act = nx.read_table(P, "ACTIONS")
    bars = nx.load_bars(P, pd.Timestamp("2002-01-01"), hi + pd.Timedelta(days=10))
    mk = {}
    for s in ("QQQ", "SPY", "IWM"):
        x = bars[bars.ticker == s].set_index("date")
        mk[s] = pd.DataFrame({"p40": x.close, "close": x.close, "hi": x.high.astype(float), "lo": x.low.astype(float)})
    pn = nx.build_panel(bars)
    col = nx.collect_trades(pn, master, act, "primary", lo, hi)
    tr = col["trades"].copy()
    i = tr.row.to_numpy()
    c, h, l, o, cp = pn["c"], pn["h"], pn["l"], pn["o"], pn["c_prev"]
    tr["ibs"] = (c[i] - l[i]) / (h[i] - l[i])
    tr["gap"] = o[i] / cp[i] - 1
    tr["intra"] = c[i] / o[i] - 1
    j = i - 6
    ok = (j >= pn["start"][i])
    tr["ret5"] = np.where(ok, cp[i] / c[np.maximum(j, 0)] - 1, np.nan)
    tr["price"] = tr.cu
    tr = tr.rename(columns={"ticker": "sym", "ret": "gross"})
    tr["net"] = tr.gross - COST
    tr = tr[["date", "sym", "day_ret", "ibs", "adv", "vol20", "gap", "intra", "ret5", "price", "gross", "net"]]
    sess = pd.DatetimeIndex(col["nights"])
    allsess = pd.DatetimeIndex(np.unique(pn["date"]))
    allsess = allsess[allsess <= hi]
    qs = {k: v.reindex(allsess) for k, v in mk.items()}
    nm = night_market_table(allsess, qs, None)
    nm.index.name = "date"
    nm = nm.reset_index()
    nm["_kind"], nm["nights"] = "mkt", nm.date.isin(sess)
    tr["_kind"], tr["nights"] = "trade", False
    z = pd.concat([tr, nm], ignore_index=True)
    z.to_parquet(B_CACHE)
    return z


# ---------------------------------------------------------------- features -> codes
NIGHT_CONT = ["QQQ_d40", "QQQ_r5", "QQQ_r20", "QQQ_ma20", "QQQ_ma50", "QQQ_ma200", "QQQ_rng",
              "SPY_d40", "SPY_r5", "SPY_r20", "SPY_ma20", "SPY_ma50", "SPY_ma200", "SPY_rng",
              "IWM_d40", "IWM_r5", "IWM_r20", "IWM_ma20", "IWM_ma50", "IWM_ma200", "IWM_rng",
              "iwm_qqq_spread", "vix_lvl", "vix_d1", "vix_d5", "vix_pct252", "vix9_ratio", "rv20",
              "b_npicks", "b_etf_share", "b_mean_dayret"]
NIGHT_CAT = ["weekday", "preweekend_hol", "monthend_pm2", "fomc_eve", "opex_week"]
PICK_CONT = ["day_ret", "ibs", "vol20", "adv", "price", "gap", "intra", "ret5"]
PICK_CAT = ["is_etf", "is_letf", "repeat"]


def add_breadth_and_repeat(p, sessions):
    g = p.groupby("date")
    p["b_npicks"] = g.sym.transform("size").astype(float)
    p["b_etf_share"] = g.is_etf.transform("mean")
    p["b_mean_dayret"] = g.day_ret.transform("mean")
    pos = pd.Series(np.arange(len(sessions)), index=sessions)
    sp = p.date.map(pos)
    prev = set(zip(p.sym, sp))
    p["repeat"] = [float((s, k - 1) in prev) for s, k in zip(p.sym, sp)]
    return p


def make_edges(disc):
    """Quintile edges on DISCOVERY: night-level features from unique pick nights, pick-level from trades."""
    edges = {}
    nights = disc.drop_duplicates("date")
    for f, src in [(f, nights) for f in NIGHT_CONT] + [(f, disc) for f in PICK_CONT]:
        v = src[f].dropna()
        edges[f] = np.unique(np.quantile(v, [.2, .4, .6, .8])) if len(v) > 50 else None
    return edges


def code_matrix(df, edges):
    names, cols, kind = [], [], []
    for f in NIGHT_CONT + PICK_CONT:
        e = edges.get(f)
        if e is None or f not in df:
            continue
        x = df[f].to_numpy(float)
        names.append(f); cols.append(np.where(np.isfinite(x), np.digitize(x, e), -1))
        kind.append("night" if f in NIGHT_CONT else "pick")
    for f in NIGHT_CAT + PICK_CAT:
        if f not in df:
            continue
        x = df[f].to_numpy(float)
        names.append(f); cols.append(np.where(np.isfinite(x), np.nan_to_num(x).astype(int), -1))
        kind.append("night" if f in NIGHT_CAT else "pick")
    return names, np.column_stack(cols).astype(np.int16), kind


def bucket_label(f, k, edges):
    e = edges.get(f)
    if e is None:
        return f"{f}={k}"
    if k == 0:
        return f"{f} <{e[0]:.4g}"
    if k == len(e):
        return f"{f} >={e[-1]:.4g}"
    return f"{f} [{e[k-1]:.4g},{e[k]:.4g})"


def scan(net, did, half, C, nd):
    """Per (feature,bucket): [n, mean h0, mean h1, day-clustered t, share]."""
    n = len(net)
    F = C.shape[1]
    Kmax = max(int(C.max()) + 1, 2)
    res = np.full((F, Kmax, 5), np.nan)
    for f in range(F):
        c = C[:, f]
        v = c >= 0
        if not v.any():
            continue
        cc, nn, dd, hh = c[v].astype(np.int64), net[v], did[v], half[v]
        Kf = int(cc.max()) + 1
        key = cc * nd + dd
        cnt = np.bincount(key, minlength=Kf * nd).reshape(Kf, nd)
        sm = np.bincount(key, weights=nn, minlength=Kf * nd).reshape(Kf, nd)
        has = cnt > 0
        nds = has.sum(1)
        with np.errstate(divide="ignore", invalid="ignore"):
            m = np.where(has, sm / np.maximum(cnt, 1), 0.0)
            mu = m.sum(1) / nds
            sd = np.sqrt((np.where(has, m - mu[:, None], 0.0) ** 2).sum(1) / (nds - 1))
            t = mu / (sd / np.sqrt(nds))
            k2 = cc * 2 + hh
            c2 = np.bincount(k2, minlength=Kf * 2).reshape(Kf, 2)
            s2 = np.bincount(k2, weights=nn, minlength=Kf * 2).reshape(Kf, 2)
            h = s2 / c2
        res[f, :Kf, 0] = cnt.sum(1)
        res[f, :Kf, 1] = h[:, 0]
        res[f, :Kf, 2] = h[:, 1]
        res[f, :Kf, 3] = t
        res[f, :Kf, 4] = cnt.sum(1) / n
    return res


def is_cand(res):
    with np.errstate(invalid="ignore"):
        return (res[..., 1] < 0) & (res[..., 2] < 0) & (res[..., 3] <= -2.0) & (res[..., 4] >= 0.05)


# ---------------------------------------------------------------- stats
def series(df, w, cal):
    """Per-night: sum(w*net)/n_picks over all picks, 0 on nights without picks, on calendar cal."""
    x = pd.DataFrame({"d": df.date.to_numpy(), "v": (w * df.net).to_numpy()}).groupby("d").v.agg(["sum", "size"])
    return (x["sum"] / x["size"]).reindex(cal).fillna(0.0)


def stats(r):
    eq = (1 + r * NIGHT_W).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    return sh, dd, eq.iloc[-1] ** (252 / len(r)) - 1


def fmt(label, r):
    sh, dd, yr = stats(r)
    return (f"  {label:<22} nights {len(r):5d} mean {r.mean()*1e4:+6.2f}bp Sharpe {sh:5.2f} maxDD {dd*100:6.1f}% "
            f"%/yr@0.65 {yr*100:+6.1f}"), sh, dd, yr


def clus_t(df, mask):
    x = df[np.asarray(mask)].groupby("date").net.mean()
    return x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 else np.nan


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    etf, lev = letf_flags()
    p = daily_pick_feats(load_A_picks())
    p["is_etf"] = p.sym.map(etf)
    p["is_letf"] = p.sym.map(lev)

    qs = {s: mkt_minute(s) for s in ("QQQ", "SPY", "IWM")}
    sess = qs["QQQ"].index
    sess = sess[sess <= p.date.max() + pd.Timedelta(days=5)]
    import event_calendar as EC
    fomc = pd.DatetimeIndex(EC.fomc_dates())
    nm = night_market_table(sess, {k: v.reindex(sess) for k, v in qs.items()}, fomc)
    p = add_breadth_and_repeat(p, sess).join(nm, on="date")
    p = p.sort_values(["date", "sym"]).reset_index(drop=True)
    cal_all = sess[sess <= p.date.max()]

    disc = p[(p.date >= D_LO) & (p.date <= D_HI)].reset_index(drop=True)
    hoA = p[(p.date >= A_LO) & (p.date <= A_HI)].reset_index(drop=True)
    log("NDISC: when does the night leg lose? (exploratory search; discovery -> holdout)")
    log(f"Net = gross - 15bp RT. Discovery {disc.date.min().date()}..{disc.date.max().date()} n {len(disc)} trades, "
        f"{disc.date.nunique()} nights; holdout A {hoA.date.min().date()}..{hoA.date.max().date()} n {len(hoA)}, "
        f"{hoA.date.nunique()} nights.")
    log(f"Discovery base: mean net {disc.net.mean()*1e4:+.1f}bp  median {disc.net.median()*1e4:+.1f}  "
        f"night-clustered t {clus_t(disc, np.ones(len(disc), bool)):.2f}")
    log("Feature coverage in A below 97% non-NaN: " + ", ".join(
        f"{f} {p[f].notna().mean():.2f}" for f in NIGHT_CONT + PICK_CONT + NIGHT_CAT + PICK_CAT if p[f].notna().mean() < 0.97))
    log("")

    edges = make_edges(disc)
    names, C, kind = code_matrix(disc, edges)
    dates = np.sort(disc.date.unique())
    did = np.searchsorted(dates, disc.date.to_numpy())
    half = (disc.date >= SPLIT_HALF).astype(int).to_numpy()
    net = disc.net.to_numpy()
    nd = len(dates)

    real = scan(net, did, half, C, nd)
    cand = is_cand(real)
    n_real = int(cand.sum())

    # placebo: date shuffle of outcome blocks vs ALL features (night-level vector moves with the night; pick-level
    # feature rows come from the shuffled night's block, tiled/truncated to the outcome night's pick count)
    rng = np.random.default_rng(20261016)
    starts = np.r_[0, np.flatnonzero(np.diff(did)) + 1]
    sizes = np.diff(np.r_[starts, len(did)])
    within = np.arange(len(did)) - starts[did]
    night_idx = np.array([k == "night" for k in kind])
    NCm = C[starts]
    pl = []
    for _ in range(NPLACEBO):
        s = rng.permutation(nd)[did]
        Cp = C.copy()
        Cp[:, night_idx] = NCm[s][:, night_idx]
        src = starts[s] + (within % sizes[s])
        Cp[:, ~night_idx] = C[src][:, ~night_idx]
        pl.append(int(is_cand(scan(net, did, half, Cp, nd)).sum()))
    pl = np.array(pl)
    log(f"Placebo calibration ({NPLACEBO} date-shuffles of outcomes vs all features; same edges and selection rule)")
    log(f"  buckets scanned {int((~np.isnan(real[..., 3])).sum())} across {C.shape[1]} features")
    log(f"  REAL candidates {n_real}; placebo candidates mean {pl.mean():.2f} median {np.median(pl):.0f} "
        f"p95 {np.percentile(pl, 95):.0f} max {pl.max()}; share of placebos >= real {np.mean(pl >= n_real):.3f}")
    informative = n_real > np.percentile(pl, 95)
    log(f"  scan informative (real > placebo p95): {'YES' if informative else 'NO'}")
    log("")

    cands = [(names[fi], k) for fi in range(C.shape[1]) for k in range(real.shape[1]) if cand[fi, k]]
    log("FROZEN CANDIDATES (discovery): bucket | n trades | share | mean net h1(2016-19) / h2(2020-22) | day-clustered t")
    if not cands:
        log("  (none)")
    for f, k in cands:
        r = real[names.index(f), k]
        log(f"  {bucket_label(f, k, edges):<40} n {int(r[0]):5d} share {r[4]*100:4.1f}% "
            f"h1 {r[1]*1e4:+7.1f} h2 {r[2]*1e4:+7.1f}bp t {r[3]:6.2f}")
    log("Combined rule (frozen): size x0.5 on a pick when exactly 1 candidate fires, x0 when >= 2 fire. Pure-skip: x0 when >= 1 fires.")
    log("")

    log("DESCRIPTIVE profile (discovery; most negative day-clustered t among buckets with share >= 5%, any sub-half sign)")
    order = sorted((real[fi, k, 3], fi, k) for fi in range(C.shape[1]) for k in range(real.shape[1])
                   if np.isfinite(real[fi, k, 3]) and real[fi, k, 4] >= 0.05)
    for lab, rows in (("most negative", order[:12]), ("most positive (contrast)", order[::-1][:4])):
        log(f"  [{lab}] discovery base mean net {disc.net.mean()*1e4:+.1f}bp")
        for t, fi, k in rows:
            r = real[fi, k]
            log(f"  {bucket_label(names[fi], k, edges):<40} n {int(r[0]):5d} share {r[4]*100:4.1f}% mean h1 {r[1]*1e4:+7.1f} "
                f"h2 {r[2]*1e4:+7.1f}bp t {t:6.2f}")
    log("")
    log("---- FREEZE COMPLETE; holdouts computed below ----")
    log("")

    def fire_matrix(df):
        n_, Cc, _ = code_matrix(df, edges)
        cols = {n: Cc[:, i] for i, n in enumerate(n_)}
        M, used = [], []
        for f, k in cands:
            if f not in cols or (cols[f] >= 0).mean() < 0.5:
                M.append(np.zeros(len(df), bool)); continue
            M.append(cols[f] == k); used.append((f, k))
        return (np.column_stack(M) if M else np.zeros((len(df), 0), bool)), used

    def evaluate(df, cal, tag):
        log(f"HOLDOUT {tag}: trades {len(df)}, nights with picks {df.date.nunique()}, calendar nights {len(cal)}")
        M, used = fire_matrix(df)
        nf = M.sum(1)
        ln, sh0, dd0, yr0 = fmt("BASE", series(df, np.ones(len(df)), cal))
        log(ln)
        fl = nf > 0
        res = {}
        for lab, w in (("RULE halve/skip>=2", np.where(nf == 0, 1.0, np.where(nf == 1, 0.5, 0.0))),
                       ("RULE pure-skip", np.where(nf == 0, 1.0, 0.0))):
            ln, sh, dd, yr = fmt(lab, series(df, w, cal))
            log(ln)
            ok = bool(fl.any() and df.net[fl].mean() < 0 and sh - sh0 >= 0.15 and dd > dd0 and yr >= yr0 - 0.02)
            res[lab] = ok
            log(f"    flagged trades n {int(fl.sum())} ({fl.mean()*100:.1f}%) mean net "
                f"{(df.net[fl].mean() if fl.any() else np.nan)*1e4:+.1f}bp t {clus_t(df, fl):.2f}; dSharpe {sh-sh0:+.2f} "
                f"maxDD {dd*100:.1f}% vs {dd0*100:.1f}% %/yr {yr*100:+.1f} vs {yr0*100:+.1f} -> {'PASS' if ok else 'FAIL'}")
        log("  per-candidate (flagged trades; solo-halve rule):")
        for ci, (f, k) in enumerate(cands):
            col = M[:, ci]
            if (f, k) not in used:
                log(f"    {bucket_label(f, k, edges):<40} NOT AVAILABLE in this holdout")
                continue
            if col.sum() == 0:
                log(f"    {bucket_label(f, k, edges):<40} flagged n 0")
                continue
            _, sh, dd, yr = fmt("x", series(df, np.where(col, 0.5, 1.0), cal))
            log(f"    {bucket_label(f, k, edges):<40} flagged n {int(col.sum()):4d} ({col.mean()*100:4.1f}%) mean net "
                f"{df.net[col].mean()*1e4:+7.1f}bp t {clus_t(df, col):5.2f} | rest {df.net[~col].mean()*1e4:+6.1f}bp "
                f"| solo dSharpe {sh-sh0:+.2f} dMaxDD {(dd-dd0)*100:+.1f}pp d%/yr {(yr-yr0)*100:+.1f}")
        log("")
        return res

    calA = pd.DatetimeIndex([d for d in cal_all if d >= pd.Timestamp(A_LO) and d <= hoA.date.max()])
    rA = evaluate(hoA, calA, "A (2023-01..2026-09, exact 15:40)")

    rB = None
    tb = None
    try:
        z = build_B()
        mb = z[z._kind == "mkt"].dropna(axis=1, how="all").copy()    # market columns only (fomc_eve is all-NaN -> re-added below)
        mb["fomc_eve"] = np.nan
        tb = z[z._kind == "trade"].drop(columns=["_kind", "nights"]).copy()
        tb = tb[[c for c in tb.columns if c not in mb.columns or c == "date"]]   # drop NaN market stubs from the concat
        calB = pd.DatetimeIndex(mb.loc[mb.nights, "date"])
        mb = mb.drop(columns=["_kind", "nights"]).set_index("date")
        tb = tb.sort_values(["date", "sym"]).reset_index(drop=True)
        tb["is_etf"], tb["is_letf"] = np.nan, np.nan
        tb = add_breadth_and_repeat(tb, pd.DatetimeIndex(mb.index))
        tb = tb.join(mb[[c for c in mb.columns if c not in tb.columns]], on="date")
        rB = evaluate(tb, calB, "B (2003-2015, Sharadar daily-close proxy; FOMC and ETF/LETF flags n/a)")
    except Exception as e:  # noqa
        import traceback
        log("HOLDOUT B: NOT RUN -- " + repr(e))
        log(traceback.format_exc()[-800:])

    log("DESCRIPTIVE ONLY (not a registered test, not a candidate): holdout net mean of the discovery top-12 negative buckets")
    for lab, d_ in (("A", hoA), ("B", tb)):
        if d_ is None:
            continue
        n_, Cc, _ = code_matrix(d_, edges)
        cols = {n: Cc[:, i] for i, n in enumerate(n_)}
        for t, fi, k in order[:12]:
            f = names[fi]
            m = (cols[f] == k) if f in cols else np.zeros(len(d_), bool)
            ok = f in cols and (cols[f] >= 0).mean() >= 0.5
            log(f"  {lab} {bucket_label(f, k, edges):<40} " + (f"n {int(m.sum()):5d} mean net {d_.net[m].mean()*1e4:+7.1f}bp "
                f"(rest {d_.net[~m].mean()*1e4:+6.1f}) t {clus_t(d_, m):5.2f}" if ok and m.sum() > 2 else "n/a"))
    log("")
    log("VERDICT (registered bars: flagged trades net-negative; Sharpe >= base+0.15; maxDD smaller; %/yr >= base-2pp)")
    log(f"  scan informative vs placebo p95: {'YES' if informative else 'NO'}")
    log(f"  holdout A: halve rule {'PASS' if rA['RULE halve/skip>=2'] else 'FAIL'}; pure-skip {'PASS' if rA['RULE pure-skip'] else 'FAIL'}")
    if rB is not None:
        log(f"  holdout B: halve rule {'PASS' if rB['RULE halve/skip>=2'] else 'FAIL'}; pure-skip {'PASS' if rB['RULE pure-skip'] else 'FAIL'}")
    else:
        log("  holdout B: NOT RUN")
    log(f"runtime {time.time()-t0:.0f}s")
    open(OUT, "w").write("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
