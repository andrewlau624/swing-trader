"""Study GAMMA-MKT (N 1008). Index (SPY) dealer-gamma exposure vs next-day vol and 5-day direction.
Pre-registration: research/drafts/round1_prose.md, section "Study GAMMA-MKT" (2026-10-16, one look).

Data: optionm.opprcdYYYY (per-contract EOD OI, gamma, contract_size) for SPY (secid 109820);
underlying close/high/low from optionm.secprdYYYY (secid 109820). SPY options in opprcd begin 2005.
WRDS read-only. Usage: .venv/bin/python -m research.sim.gamma_mkt   ->   data/research/program/gamma_mkt_out.txt
"""
import pathlib, time
import numpy as np
import pandas as pd
import wrds

SPY = 109820
OUT = pathlib.Path("data/research/program/gamma_mkt_out.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
YEARS = list(range(1996, 2026))
H1 = (1996, 2010)   # registered halves
H2 = (2011, 2025)
Z_WIN, Z_MIN = 252, 60      # trailing-window standardisation
LAGS_V, LAGS_M = 5, 5       # Newey-West truncation lag

_L = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    _L.append(s)

def nw_t(y, X, lags):
    """OLS beta and Newey-West (HAC, Bartlett) t for y = X @ beta. Last column is the tested slope."""
    y = np.asarray(y, float); X = np.asarray(X, float)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    n = len(y)
    if n < 25:
        return np.full(X.shape[1], np.nan), np.full(X.shape[1], np.nan)
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    Sm = u.T @ u
    for k in range(1, lags + 1):
        w = 1 - k / (lags + 1)
        g = u[k:].T @ u[:-k]
        Sm += w * (g + g.T)
    V = XtX_inv @ Sm @ XtX_inv
    se = np.sqrt(np.diag(V))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = beta / se
    return beta, t

def pull(db, y):
    """Per-year SPY option gamma aggregates and underlying prices. Returns (opt_df, px_df) or (None, None)."""
    try:
        opt = db.raw_sql(
            f"select date, cp_flag, sum(open_interest*gamma*contract_size) as raw_g, "
            f"sum(open_interest) as oi, count(*) as n_rows from optionm.opprcd{y} "
            f"where secid={SPY} and gamma is not null and cp_flag in ('C','P') "
            f"group by date, cp_flag order by date")
    except Exception as e:
        P(f"  opprcd{y}: query error {type(e).__name__}: {str(e)[:120]}")
        return None, None
    try:
        px = db.raw_sql(f"select date, close, high, low from optionm.secprd{y} where secid={SPY} order by date")
    except Exception as e:
        P(f"  secprd{y}: query error {type(e).__name__}: {str(e)[:120]}")
        px = None
    return opt, px

def main():
    t0 = time.time()
    U = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
    db = wrds.Connection(wrds_username=U)

    # confirm secid
    sec = db.raw_sql(f"select secid,ticker,index_flag,issue_type from optionm.securd where secid={SPY}")
    P("SPY secid row:", sec.to_dict("records"))

    opt_parts, px_parts, days_per_year = [], [], {}
    for y in YEARS:
        opt, px = pull(db, y)
        if opt is None or len(opt) == 0:
            days_per_year[y] = 0
            continue
        opt["year"] = y
        opt_parts.append(opt)
        if px is not None and len(px):
            px["year"] = y
            px_parts.append(px)
        days_per_year[y] = int(opt["date"].nunique())
    db.close()

    if not opt_parts:
        P("No SPY option rows retrieved - abort.")
        OUT.write_text("\n".join(_L) + "\n"); return

    opt = pd.concat(opt_parts, ignore_index=True)
    px = pd.concat(px_parts, ignore_index=True)
    opt["date"] = pd.to_datetime(opt["date"])
    px["date"] = pd.to_datetime(px["date"])
    for c in ["raw_g", "oi", "n_rows"]:
        opt[c] = pd.to_numeric(opt[c], errors="coerce").astype(float)
    for c in ["close", "high", "low"]:
        px[c] = pd.to_numeric(px[c], errors="coerce").astype(float)
    for c in ["year"]:
        opt[c] = opt[c].astype(int); px[c] = px[c].astype(int)

    cg = (opt[opt.cp_flag == "C"].set_index("date")["raw_g"].rename("CG"))
    pg = (opt[opt.cp_flag == "P"].set_index("date")["raw_g"].rename("PG"))
    oic = (opt[opt.cp_flag == "C"].set_index("date")["oi"].rename("oi_c"))
    oip = (opt[opt.cp_flag == "P"].set_index("date")["oi"].rename("oi_p"))
    df = pd.concat([cg, pg, oic, oip], axis=1).reset_index()
    df = df.merge(px[["date", "close", "high", "low"]], on="date", how="left").sort_values("date").reset_index(drop=True)
    df["year"] = df["date"].dt.year

    # ---- signal at close of day t (only day-t data) ----
    df["DG"] = df["PG"] - df["CG"]                       # net dealer gamma proxy (pre-signed)
    df["pcr_gamma"] = df["PG"] / df["CG"]                # raw put/call gamma ratio
    roll_med = df["DG"].rolling(Z_WIN, min_periods=Z_MIN).median()
    roll_mad = df["DG"].rolling(Z_WIN, min_periods=Z_MIN).apply(
        lambda v: np.median(np.abs(v - np.median(v))), raw=True)
    df["DG_z"] = (df["DG"] - roll_med) / roll_mad.replace(0, np.nan)

    spot = df["close"]
    df["dollar_gamma_1pct"] = df["DG"] * spot ** 2 * 0.01    # $ gamma per 1% SPY move

    # ---- returns (forward = strictly after t) ----
    lc = np.log(df["close"])
    df["ret_t"] = lc - lc.shift(1)
    df["fwd1_ret"] = lc.shift(-1) - lc
    df["abs_fwd1"] = df["fwd1_ret"].abs()
    df["range_next"] = (df["high"].shift(-1) - df["low"].shift(-1)) / df["close"].shift(-1)
    df["fwd5_ret"] = lc.shift(-5) - lc
    df["sign_t"] = np.sign(df["ret_t"])

    # ---- report header ----
    P("=" * 96)
    P("Study GAMMA-MKT - index dealer-gamma exposure vs next-day vol / 5-day direction  (SPY secid 109820)")
    P("=" * 96)
    P(f"run {time.strftime('%Y-%m-%d %H:%M')}  years requested 1996-2025")
    P("")
    P("Underlying price source: optionm.secprdYYYY secid=109820 (columns: low,high,close,volume,return,cfadj,open,cfret,shrout).")
    P("  secprd HAS SPY -> used its raw close/high/low. (crsp.dsf permno 84398 is the stated fallback; not needed.)")
    P("")
    P("SPY trading days with option rows (usable-gamma coverage) per year:")
    for y in YEARS:
        n = days_per_year.get(y, 0)
        if n or y >= 2004:
            P(f"  {y}: {n} days with SPY option rows")
    P("")
    P("NOTE: optionm.opprcd has NO SPY rows before 2005 (checked 1996-2004: 0 rows). SPY option coverage")
    P("      starts 2005-01-10, so the registered first half 1996-2010 is effectively 2005-2010.")
    P("")

    # usable-signal days per year (z exists, forward return exists)
    df["usable_V"] = df["DG_z"].notna() & df["abs_fwd1"].notna()
    df["usable_M"] = df["DG_z"].notna() & df["fwd5_ret"].notna() & df["sign_t"].ne(0)
    P("SPY trading days with a USABLE standardised DG signal (z computed AND forward return present):")
    P(f"  {'year':<6}{'usable_V':>10}{'usable_M':>10}{'median $gamma/1%':>20}")
    for y in sorted(df.year.unique()):
        d = df[df.year == y]
        P(f"  {y:<6}{int(d.usable_V.sum()):>10}{int(d.usable_M.sum()):>10}"
          f"{d.dollar_gamma_1pct.median():>20,.0f}")
    P("")
    P(f"DG raw: mean {df.DG.mean():,.0f}  median {df.DG.median():,.0f}  (1 USD gamma units; DG=PG-CG)")
    P(f"pcr_gamma (PG/CG): mean {df.pcr_gamma.mean():.3f}  median {df.pcr_gamma.median():.3f}")
    P("")

    # ---- regressions ----
    def reg(sub, dep, xcol, lags=LAGS_V):
        m = sub[["year", dep, xcol]].dropna()
        X = np.column_stack([np.ones(len(m)), m[xcol].values])
        beta, t = nw_t(m[dep].values, X, lags)
        return m, beta[1], t[1]

    def ex_top5(sub, dep, xcol, k=5, lags=LAGS_V):
        m = sub[["year", dep, xcol]].dropna()
        if len(m) <= k + 25:
            return np.nan, np.nan, 0
        keep = m.reindex(m[dep].abs().sort_values(ascending=False).index[k:])
        X = np.column_stack([np.ones(len(keep)), keep[xcol].values])
        beta, t = nw_t(keep[dep].values, X, lags)
        return beta[1], t[1], len(keep)

    halves = {"H1 1996-2010 (data 2005-2010)": (1996, 2010),
              "H2 2011-2025": (2011, 2025),
              "FULL 1996-2025": (1996, 2025)}

    # ================= ARM V =================
    P("=" * 96)
    P("ARM V (vol): |next-day SPY log return|  ~  DG_z        pre-signed slope: NEGATIVE (short gamma -> vol up)")
    P("=" * 96)
    P(f"  {'sample':<28}{'n':>7}{'slope(bp/1sd)':>16}{'NW t':>9}{'ex-top5 slope':>16}{'ex-top5 t':>11}")
    vres = {}
    for lbl, (a, b) in halves.items():
        sub = df[df.year.between(a, b)]
        m, b1, t1 = reg(sub, "abs_fwd1", "DG_z")
        eb, et, en = ex_top5(sub, "abs_fwd1", "DG_z")
        vres[lbl] = (len(m), b1, t1, eb, et)
        P(f"  {lbl:<28}{len(m):>7}{b1*1e4:>16.3f}{t1:>9.2f}{eb*1e4:>16.3f}{et:>11.2f}")
    P("")

    # intraday range variant
    P("Arm V variant: next-day intraday range (high-low)/close ~ DG_z   (pre-signed NEGATIVE)")
    P(f"  {'sample':<28}{'n':>7}{'slope':>16}{'NW t':>9}")
    for lbl, (a, b) in halves.items():
        sub = df[df.year.between(a, b)]
        m, b1, t1 = reg(sub, "range_next", "DG_z")
        P(f"  {lbl:<28}{len(m):>7}{b1:>16.5f}{t1:>9.2f}")
    P("")

    # deciles of |next-day ret|
    sub = df[df.usable_V].copy()
    sub["dec"] = pd.qcut(sub["DG_z"], 10, labels=False, duplicates="drop")
    P("Deciles of DG_z vs next-day realized vol (full sample):")
    P(f"  {'decile':>7}{'mean DG_z':>12}{'mean |ret| bp':>16}{'mean range':>14}{'n':>8}")
    for d, g in sub.groupby("dec"):
        P(f"  {int(d)+1:>7}{g.DG_z.mean():>12.2f}{g.abs_fwd1.mean()*1e4:>16.3f}{g.range_next.mean():>14.5f}{len(g):>8}")
    P("")

    # ================= ARM M =================
    P("=" * 96)
    P("ARM M (direction): 5-day fwd SPY return ~ DG_z * sign(ret_t)   pre-signed slope: POSITIVE (short gamma trends)")
    P("=" * 96)
    df["xm"] = df["DG_z"] * df["sign_t"]
    P(f"  {'sample':<28}{'n':>7}{'slope(bp/1sd)':>16}{'NW t':>9}{'ex-top5 slope':>16}{'ex-top5 t':>11}")
    mres = {}
    for lbl, (a, b) in halves.items():
        sub = df[df.year.between(a, b)]
        m, b1, t1 = reg(sub, "fwd5_ret", "xm")
        eb, et, en = ex_top5(sub, "fwd5_ret", "xm")
        mres[lbl] = (len(m), b1, t1, eb, et)
        P(f"  {lbl:<28}{len(m):>7}{b1*1e4:>16.3f}{t1:>9.2f}{eb*1e4:>16.3f}{et:>11.2f}")
    P("")
    P(" (The mechanism sentence 'short-gamma trends' implies the slope on DG_z*sign should be NEGATIVE:")
    P("  short gamma = negative DG; a trend means fwd5 keeps today's sign, which reverses the product's sign.")
    P("  The registered text says POSITIVE; the two disagree. Both readings of the same quantity are below.)")
    P("")
    P("Equivalent mechanism form: sign(ret_t)*fwd5 ~ DG_z (slope expected NEGATIVE if short-gamma trends):")
    df["ym"] = df["sign_t"] * df["fwd5_ret"]
    P(f"  {'sample':<28}{'n':>7}{'slope(bp/1sd)':>16}{'NW t':>9}")
    for lbl, (a, b) in halves.items():
        sub = df[df.year.between(a, b)]
        m, b1, t1 = reg(sub, "ym", "DG_z")
        P(f"  {lbl:<28}{len(m):>7}{b1*1e4:>16.3f}{t1:>9.2f}")
    P("")

    # deciles of signed fwd5
    subm = df[df.usable_M].copy()
    subm["dec"] = pd.qcut(subm["DG_z"], 10, labels=False, duplicates="drop")
    P("Deciles of DG_z vs sign(ret_t)*fwd5 (full sample):")
    P(f"  {'decile':>7}{'mean DG_z':>12}{'mean sign*fwd5 bp':>20}{'n':>8}")
    for d, g in subm.groupby("dec"):
        P(f"  {int(d)+1:>7}{g.DG_z.mean():>12.2f}{g.ym.mean()*1e4:>20.3f}{len(g):>8}")
    P("")

    # lag-1 robustness (EOD OI/gamma is published after the close; enter one day later)
    P("Robustness - signal known only after the close: use z_{t} vs return t+1..t+6 (one-day-lagged entry):")
    df["abs_fwd1_lag"] = (lc.shift(-2) - lc.shift(-1)).abs()
    df["fwd5_lag"] = lc.shift(-6) - lc.shift(-1)
    df["ym_lag"] = np.sign(lc.shift(-1) - lc) * df["fwd5_lag"]
    P(f"  {'sample':<28}{'n':>7}{'V slope':>12}{'V t':>8}{'M slope':>12}{'M t':>8}")
    for lbl, (a, b) in halves.items():
        sub = df[df.year.between(a, b)].copy()
        mv_, bv, tv = reg(sub, "abs_fwd1_lag", "DG_z")
        _, bm, tm = reg(sub, "ym_lag", "DG_z")
        P(f"  {lbl:<28}{len(mv_):>7}{bv*1e4:>12.3f}{tv:>8.2f}{bm*1e4:>12.3f}{tm:>8.2f}")
    P("")

    # ---- verdict ----
    P("=" * 96)
    P("VERDICT (pre-registered, literal)")
    P("=" * 96)
    def arm_pass(res, want_sign):
        ok = {}
        for lbl, (n, b1, t1, eb, et) in res.items():
            sign_ok = (b1 > 0) if want_sign > 0 else (b1 < 0)
            t_ok = abs(t1) >= 2 if np.isfinite(t1) else False
            cow_ok = (eb > 0) if want_sign > 0 else (eb < 0)
            ok[lbl] = sign_ok and t_ok and cow_ok
        return ok
    vpass = arm_pass(vres, -1)
    mpass = arm_pass(mres, +1)
    b1_lbl = "H1 1996-2010 (data 2005-2010)"; b2_lbl = "H2 2011-2025"
    P("Arm V (expect slope<0):")
    for lbl in halves: P(f"  {lbl:<28} sign_ok={('yes' if (vres[lbl][1]<0) else 'no'):>4}  |t|>=2={('yes' if abs(vres[lbl][2])>=2 else 'no'):>4}  ex-top5 sign_ok={('yes' if vres[lbl][3]<0 else 'no')}")
    P("Arm M (expect slope>0):")
    for lbl in halves: P(f"  {lbl:<28} sign_ok={('yes' if (mres[lbl][1]>0) else 'no'):>4}  |t|>=2={('yes' if abs(mres[lbl][2])>=2 else 'no'):>4}  ex-top5 sign_ok={('yes' if mres[lbl][3]>0 else 'no')}")
    both = (vpass[b1_lbl] and vpass[b2_lbl] and mpass[b1_lbl] and mpass[b2_lbl])
    P("")
    P(f"Overall (both arms, both halves, literal pre-signed rule): {'PASS' if both else 'KILL'}")
    P(f"Arm V alone: {'PASS' if vpass[b1_lbl] and vpass[b2_lbl] else 'KILL'}; "
      f"Arm M alone: {'PASS' if mpass[b1_lbl] and mpass[b2_lbl] else 'KILL'}")
    P("")
    P(f"[runtime {time.time()-t0:.0f}s]")

    OUT.write_text("\n".join(_L) + "\n")
    P(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
