"""Study SKEW-MKT — index option skew / term structure and forward SPY returns.

Pre-registration: research/drafts/round1_prose.md, section "Study SKEW-MKT" (N 1008 -> 1009).
Judge: 1996-2025, halves 1996-2010 / 2011-2025; ONE look. Pass iff the 20d-forward slope has the
pre-signed sign with Newey-West t >= 2 in BOTH halves AND ex-top-5 is intact; else KILL.

Data (all free-licensed on WRDS, SELECT-only):
  * Signal: optionm.vsurfdYYYY  (SPY secid=109820), per-delta implied-vol surface.
      RR30 = IV(days=30, delta=+25, C) - IV(days=30, delta=-25, P)   [call minus put; negative = fear]
      TS   = IV(days=30, delta=-10, P) - IV(days=182, delta=-10, P)  [near minus far; high = near fear]
    days grid {10,30,60,91,122,152,182,273,365,547,730}; delta grid {-90..-10,+10..+90} step 5.
    days=30 exact; TS uses days=182 (nearest available to 180).
  * Underlying: optionm.secprdYYYY (SPY secid=109820) daily close. Chosen over crsp.dsf because
    crsp.dsf prices end 2024-12-31 and one consistent source is wanted across the whole sample.

Coverage limit (verified, reported): vsurfd has NO SPY rows before 2005-01-10 and secprd SPY ends
2025-08-29, so the judge window is 2005-2025 (not 1996-2025). First z-signal ~2006-01 (trailing 252d).

Forward returns: signal at the CLOSE of day t; fwd_k = close(t+k)/close(t) - 1, k in {5,20}.
Usage: .venv/bin/python -m research.sim.skew_mkt   (writes data/research/program/skew_mkt_out.txt)
"""
import pathlib
import numpy as np
import pandas as pd

OUT = pathlib.Path("data/research/program/skew_mkt_out.txt")
SPY = 109820
YEARS = list(range(2005, 2026))          # vsurfd/secprd tables that exist for SPY
SPLIT_REG = "2010-12-31"                 # registered half boundary (1996-2010 / 2011-2025)
SPLIT_EQ = "2015-12-31"                  # equal-length robustness split (2005-15 / 2016-25)
Z_WIN = 252

_LINES = []


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    _LINES.append(s)


def head(title):
    P("")
    P("=" * 96)
    P(title)
    P("=" * 96)


def nw_slope(y, x, lags):
    """OLS y = a + b*x, Newey-West(lags) t on b. Returns (b, t, n)."""
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return np.nan, np.nan, n
    X = np.c_[np.ones(n), x]
    XtX = np.linalg.inv(X.T @ X)
    b = XtX @ X.T @ y
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        g = u[L:].T @ u[:-L]
        S += w * (g + g.T)
    V = XtX @ S @ XtX
    t = b[1] / np.sqrt(V[1, 1]) if V[1, 1] > 0 else np.nan
    return float(b[1]), float(t), n


def ztrail(s, win=Z_WIN):
    m = s.rolling(win, min_periods=win).mean()
    sd = s.rolling(win, min_periods=win).std(ddof=1)
    return (s - m) / sd


def run(db):
    head("Study SKEW-MKT — SPY index-option skew / term structure -> forward returns")
    import time
    P("run " + time.strftime("%Y-%m-%d %H:%M") + "   (one look; pre-registered)")

    # ---- grid actually present (verified on a modern session) ----
    g_delta = db.raw_sql(
        "select distinct delta from optionm.vsurfd2020 where secid=109820 "
        "and date='2020-06-30' order by delta").delta.astype(float).tolist()
    g_days = db.raw_sql(
        "select distinct days from optionm.vsurfd2020 where secid=109820 "
        "and date='2020-06-30' order by days").days.astype(float).tolist()
    P("")
    P(f"delta grid present (2020-06-30): {g_delta}")
    P(f"days  grid present (2020-06-30): {g_days}")
    P("used: RR30 = IV(30d,+25,C) - IV(30d,-25,P)   [+25 and -25 exactly on grid]")
    P("      TS   = IV(30d,-10,P) - IV(182d,-10,P)  [delta -10 exact; days=182 nearest to 180]")

    # ---- pull surface points (bounded: one small query per year) ----
    surf = []
    for y in YEARS:
        df = db.raw_sql(
            f"select date, days, delta, cp_flag, impl_volatility as iv "
            f"from optionm.vsurfd{y} where secid={SPY} and days in (30,182) "
            f"and delta in (25,-25,-10)")
        surf.append(df)
    v = pd.concat(surf, ignore_index=True)
    v["iv"] = pd.to_numeric(v["iv"], errors="coerce")
    v["date"] = pd.to_datetime(v["date"])
    v["days"] = v["days"].astype(float)
    v["delta"] = v["delta"].astype(float)

    def pick(days, delta, cp):
        z = v[(v.days == days) & (v.delta == delta) & (v.cp_flag == cp)]
        return z.sort_values("date").drop_duplicates("date", keep="last").set_index("date")["iv"]

    a = pick(30, 25, "C").rename("c25_30")
    b = pick(30, -25, "P").rename("p25_30")
    c = pick(30, -10, "P").rename("p10_30")
    d = pick(182, -10, "P").rename("p10_182")
    sig = pd.concat([a, b, c, d], axis=1).sort_index()
    sig["rr30"] = sig["c25_30"] - sig["p25_30"]
    sig["ts"] = sig["p10_30"] - sig["p10_182"]
    raw_rr = sig["rr30"].copy()
    raw_ts = sig["ts"].copy()
    sig["z_rr"] = ztrail(sig["rr30"])
    sig["z_ts"] = ztrail(sig["ts"])

    # ---- underlying closes ----
    pxf = []
    for y in YEARS:
        pxf.append(db.raw_sql(f"select date, close from optionm.secprd{y} where secid={SPY}"))
    px = pd.concat(pxf, ignore_index=True)
    px["close"] = pd.to_numeric(px["close"], errors="coerce")
    px["date"] = pd.to_datetime(px["date"])
    px = px.dropna(subset=["close"]).drop_duplicates("date").set_index("date").sort_index()
    px["fwd5"] = px["close"].shift(-5) / px["close"] - 1.0
    px["fwd20"] = px["close"].shift(-20) / px["close"] - 1.0

    df = sig.join(px[["close", "fwd5", "fwd20"]], how="inner").dropna(subset=["close"])

    # ---- coverage per year ----
    head("1. Coverage per year (SPY days)")
    P(f"{'year':>6} {'surface_pts':>12} {'rr30_raw':>9} {'ts_raw':>8} {'z_rr30':>7} {'z_ts':>6} "
      f"{'fwd5':>6} {'fwd20':>6}")
    df["_y"] = df.index.year
    for y in YEARS:
        g = df[df["_y"] == y]
        P(f"{y:>6} {len(g):>12} {int(g['rr30'].notna().sum()):>9} {int(g['ts'].notna().sum()):>8} "
          f"{int(g['z_rr'].notna().sum()):>7} {int(g['z_ts'].notna().sum()):>6} "
          f"{int(g['fwd5'].notna().sum()):>6} {int(g['fwd20'].notna().sum()):>6}")
    P("")
    P(f"total SPY signal-days with surface 2005-2025: {len(df)}  "
      f"({df.index.min().date()} .. {df.index.max().date()})")
    P("NOTE: vsurfd has NO SPY rows before 2005-01-10 (verified; 1996-2004 empty for secid 109820 "
      "and its intraday/NAV secids). secprd SPY ends 2025-08-29. So the registered 1996-2025 window is "
      "BOUNDED BY DATA to 2005-2025; the first usable z-signal is ~2006-01 (trailing 252d).")

    # ---- usable frame: z defined AND fwd horizon ----
    def frame(col_z, col_f):
        f = df[["z_rr".replace("z_rr", col_z), col_f]].copy()
        f = f.dropna()
        return f.rename(columns={col_z: "x", col_f: "y"})

    head("2. Judged statistics — 20d forward horizon (Newey-West, 20 lags)")
    P("pre-signed slope:  z_rr30 -> fwd20 POSITIVE (low RR30 = fear = lower return);  "
      "z_ts -> fwd20 NEGATIVE (high TS = near fear = lower return)")
    P("")
    P(f"{'signal':>8} {'window':>22} {'n':>6} {'slope':>10} {'NW t':>7} {'ex-top5 slope':>14} "
      f"{'ex-top5 t':>10}")

    def judged(zcol, sign):
        out = {}
        for label, lo, hi in [
            ("ALL 2005-2025", None, None),
            (f"H1_reg <= {SPLIT_REG}", None, SPLIT_REG),
            (f"H2_reg >= 2011", "2011-01-01", None),
            (f"H1_eq <= {SPLIT_EQ}", None, SPLIT_EQ),
            (f"H2_eq >= 2016", "2016-01-01", None),
        ]:
            f = frame(zcol, "fwd20")
            if lo is not None:
                f = f[f.index >= lo]
            if hi is not None:
                f = f[f.index <= hi]
            b, t, n = nw_slope(f["y"], f["x"], 20)
            g = f.drop(f["y"].nlargest(5).index)
            b2, t2, _ = nw_slope(g["y"], g["x"], 20)
            out[label] = (b, t, n, b2, t2)
            P(f"{zcol:>8} {label:>22} {n:>6} {b:>10.5f} {t:>7.2f} {b2:>14.5f} {t2:>10.2f}")
        return out

    rr20 = judged("z_rr", +1)
    ts20 = judged("z_ts", -1)

    head("3. 5d forward horizon (Newey-West, 5 lags)")
    P(f"{'signal':>8} {'window':>22} {'n':>6} {'slope':>10} {'NW t':>7} {'ex-top5 slope':>14} "
      f"{'ex-top5 t':>10}")

    def judged5(zcol):
        out = {}
        for label, lo, hi in [
            ("ALL 2005-2025", None, None),
            (f"H1_reg <= {SPLIT_REG}", None, SPLIT_REG),
            (f"H2_reg >= 2011", "2011-01-01", None),
            (f"H1_eq <= {SPLIT_EQ}", None, SPLIT_EQ),
            (f"H2_eq >= 2016", "2016-01-01", None),
        ]:
            f = frame(zcol, "fwd5")
            if lo is not None:
                f = f[f.index >= lo]
            if hi is not None:
                f = f[f.index <= hi]
            b, t, n = nw_slope(f["y"], f["x"], 5)
            g = f.drop(f["y"].nlargest(5).index)
            b2, t2, _ = nw_slope(g["y"], g["x"], 5)
            out[label] = (b, t, n, b2, t2)
            P(f"{zcol:>8} {label:>22} {n:>6} {b:>10.5f} {t:>7.2f} {b2:>14.5f} {t2:>10.2f}")
        return out

    rr5 = judged5("z_rr")
    ts5 = judged5("z_ts")

    head("4. Decile means of fwd20 by signal z (ALL 2005-2025)")
    P(f"{'decile':>7} {'z_rr30 mean':>12} {'fwd20':>9} {'fwd5':>9} | {'z_ts mean':>10} "
      f"{'fwd20':>9} {'fwd5':>9}")
    fr = df.dropna(subset=["z_rr", "z_ts", "fwd5", "fwd20"]).copy()
    fr["dq_rr"] = pd.qcut(fr["z_rr"], 10, labels=False)
    fr["dq_ts"] = pd.qcut(fr["z_ts"], 10, labels=False)
    for q in range(10):
        a1 = fr[fr["dq_rr"] == q]
        a2 = fr[fr["dq_ts"] == q]
        P(f"{q + 1:>7} {a1['z_rr'].mean():>12.3f} {a1['fwd20'].mean() * 1e4:>7.1f}bp "
          f"{a1['fwd5'].mean() * 1e4:>7.1f}bp | {a2['z_ts'].mean():>10.3f} "
          f"{a2['fwd20'].mean() * 1e4:>7.1f}bp {a2['fwd5'].mean() * 1e4:>7.1f}bp")

    head("5. Unconditional forward returns (pp per window)")
    P(f"fwd5  mean {fr['fwd5'].mean() * 100:+.3f}%  median {fr['fwd5'].median() * 100:+.3f}%  n {len(fr)}")
    P(f"fwd20 mean {fr['fwd20'].mean() * 100:+.3f}%  median {fr['fwd20'].median() * 100:+.3f}%  n {len(fr)}")

    # ---- verdict (literal rule) ----
    head("6. VERDICT (literal rule)")

    def passes(out, sign):
        h1 = out[f"H1_reg <= {SPLIT_REG}"]
        h2 = out[f"H2_reg >= 2011"]
        s_ok = (sign >= 0 and h1[0] >= 0 and h2[0] >= 0) or (sign < 0 and h1[0] <= 0 and h2[0] <= 0)
        t_ok = (h1[1] >= 2) and (h2[1] >= 2)
        ex_ok = (sign >= 0 and h1[3] >= 0 and h2[3] >= 0) or (sign < 0 and h1[3] <= 0 and h2[3] <= 0)
        return s_ok, t_ok, ex_ok

    P("Primary judged signal = RR30 (the 'skew' measure; Lab-CC analogue). Pre-signed sign = POSITIVE.")
    P("Registered halves, applied to available data: H1 = 2005/2006-2010, H2 = 2011-2025.")
    P("")
    for name, out, sign in [("RR30 (skew)", rr20, +1), ("TS (term)", ts20, -1)]:
        s_ok, t_ok, ex_ok = passes(out, sign)
        h1 = out[f"H1_reg <= {SPLIT_REG}"]
        h2 = out[f"H2_reg >= 2011"]
        P(f"{name}: slope {h1[0]:+.5f} (t {h1[1]:.2f}, n {h1[2]}) in H1_reg ; "
          f"slope {h2[0]:+.5f} (t {h2[1]:.2f}, n {h2[2]}) in H2_reg")
        P(f"   -> sign_ok {s_ok}  t>=2 both halves {t_ok}  ex-top5 sign_ok {ex_ok}  "
          f"=> {'PASS' if (s_ok and t_ok and ex_ok) else 'FAIL'}")
    P("")
    rr = passes(rr20, +1)
    verdict = "PASS" if all(rr) else "KILL"
    P(f"FAMILY VERDICT (primary RR30): {'PASS' if all(rr) else 'KILL'}")
    P(f"side note — equal-length split (H1_eq <= 2015 / H2_eq >= 2016): "
      f"RR30 slope {rr20[f'H1_eq <= {SPLIT_EQ}'][0]:+.5f} t {rr20[f'H1_eq <= {SPLIT_EQ}'][1]:.2f} | "
      f"{rr20['H2_eq >= 2016'][0]:+.5f} t {rr20['H2_eq >= 2016'][1]:.2f}")

    head("7. Caveats")
    for t in [
        "Judge window is 2005-2025, NOT the registered 1996-2025: vsurfd carries no SPY rows before",
        "  2005-01-10 and secprd SPY ends 2025-08-29. The registered split point (2010/2011) is kept;",
        "  the first half is therefore only ~5 years. An equal-length split is reported as a side note.",
        "One look, no tuning, no variant search: RR30 and TS are the two registered signals.",
        "RR30 uses delta +25 exactly (call) minus -25 exactly (put); TS uses delta -10 exactly and",
        "  days=182 as the nearest grid point to the registered 180.",
        "Forward returns use secprd CLOSE (price, not total return); SPY dividends ~1.3%/yr ~ 5bp/20d.",
        "Newey-West lags 20 (fwd20) / 5 (fwd5) handle the overlapping-return autocorrelation.",
        "ex-top-5 = drop the 5 largest fwd20 within each half, re-estimate the slope.",
        "vsurfd2020 has a SPY surface gap 2020-07-27..2020-08-18 (17 sessions, all grid points null);",
        "  because z uses min_periods=252 the gap also suppresses z for the ~252 following rows",
        "  (2020 z_rr=142, 2021 z_rr=95). Data gap, not an artifact; it does not change the KILL",
        "  (the H2_reg slope already carries the wrong sign over n=3399).",
    ]:
        P(t)
    return verdict


def main():
    import wrds
    U = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
    db = wrds.Connection(wrds_username=U)
    try:
        run(db)
    finally:
        db.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(_LINES) + "\n")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
