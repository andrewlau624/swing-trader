"""Study BORROW-XS2 runner (pre-registered 2026-10-16, program N 1006 -> 1007).
Is the BORROW-XS long-only low-fee tilt (D1-EW +22bp/mo net, t 3.58) alpha, or a size/low-vol beta?
Same panel/rule as borrow_xs.py (formation end of m, hold m+1, EW, common $5+, CRSP, 1996-2025).
Arm 1: size terciles (mktcap=|prc|*shrout); Arm 2: trailing-24m return-vol terciles (>=12 obs).
Within each tercile: decile by borrow rate -> long-only D1 - EW(within tercile) and LS D1-D10.
One look, no tuning. Reuses the BORROW-XS panel/cache.
Usage: .venv/bin/python -m research.sim.borrow_xs2 [--nocache]
Output: data/research/program/borrow_xs2_out.txt
"""
import sys, pathlib, numpy as np, pandas as pd
import research.sim.borrow_xs as BX

D = BX.D
OUT = pathlib.Path("data/research/program/borrow_xs2_out.txt")
YEARS = list(range(1996, 2026))


def qcut3(s):
    try:
        return pd.qcut(s, 3, labels=False, duplicates="drop") + 1
    except Exception:
        return pd.Series(np.nan, index=s.index)


def build_panel(db, years):
    br = BX.pull_all_borrate(db, years)
    st = BX.pull_static(db)

    br = br.merge(st["link"], left_on="securityid", right_on="secid", how="inner")
    br["ym"] = pd.to_datetime(br["ym"]); br["obsdt"] = pd.to_datetime(br["obsdt"])
    br = br[(br["sdate"] <= br["obsdt"]) & ((br["edate"].isna()) | (br["edate"] >= br["obsdt"]))]
    br = br[["permno", "ym", "borrowrate"]].drop_duplicates(["permno", "ym"])

    msf = st["msf"].copy()
    msf["ym"] = pd.to_datetime(msf["ym"]).dt.to_period("M").dt.to_timestamp()
    msf["ret"] = pd.to_numeric(msf["ret"], errors="coerce")
    msf = msf.merge(st["names"], on="permno", how="left")

    ret = msf[["permno", "ym", "ret"]].copy()
    dl = st["dl"][["permno", "glm", "dlret"]].rename(columns={"glm": "ym"})
    ret = pd.concat([ret, dl], ignore_index=True)
    ret = ret.dropna(subset=["ret"]).drop_duplicates(["permno", "ym"])

    vmsf = st["msf"].copy()
    vmsf["ym"] = pd.to_datetime(vmsf["ym"]).dt.to_period("M").dt.to_timestamp()
    vmsf["ret"] = pd.to_numeric(vmsf["ret"], errors="coerce")
    vmsf = vmsf.sort_values(["permno", "ym"])
    vmsf["vol24"] = vmsf.groupby("permno")["ret"].transform(
        lambda s: s.rolling(24, min_periods=12).std().shift(1))
    vol = vmsf[["permno", "ym", "vol24"]].dropna(subset=["vol24"])

    p = br.merge(msf[["permno", "ym", "prc", "shrout", "shrcd", "hexcd"]], on=["permno", "ym"], how="left")
    p = p[(p["prc"].abs() >= 5) & (p["shrcd"].isin([10, 11]))].copy()
    p = p.sort_values(["permno", "ym"])
    p["ym_next"] = p["ym"] + pd.offsets.MonthBegin(1)
    p = p.merge(ret.rename(columns={"ym": "ym_next", "ret": "ret_fwd"}), on=["permno", "ym_next"], how="left")
    p = p.dropna(subset=["ret_fwd"])
    p["mktcap"] = p["prc"].abs() * pd.to_numeric(p["shrout"], errors="coerce")
    p = p.merge(vol, on=["permno", "ym"], how="left")
    return p


def stats(series, name):
    s = pd.Series(series).dropna()
    n = len(s)
    if n == 0:
        return f"{name:30s} no obs"
    mean, sd = s.mean(), s.std(ddof=1)
    t = mean / (sd / np.sqrt(n)) if sd and sd > 0 else np.nan
    med = np.median(s)
    ex5 = s.sort_values().iloc[:-5].mean() if n > 5 else np.nan
    return (f"{name:30s} n={n:4d} mean={mean*1e4:8.2f}bp t={t:6.2f} "
            f"med={med*1e4:7.2f} ex5={ex5*1e4:8.2f}")


def tercile_arm(p, tcol, labels, tag, out_lines, cells):
    sub = p.dropna(subset=["borrowrate", "ret_fwd", tcol]).copy()
    sub["dec"] = sub.groupby(["ym", tcol])["borrowrate"].transform(BX.qcut_decile)
    out_lines.append(f"\n== Arm {tag} (terciles by {tcol}: 1={labels[1]}, 2={labels[2]}, 3={labels[3]}) ==")
    for t in [1, 2, 3]:
        s = sub[sub[tcol] == t]
        if len(s) == 0:
            out_lines.append(f"-- {labels[t]} tercile: no obs")
            continue
        g = s.dropna(subset=["dec"]).groupby(["ym", "dec"])["ret_fwd"].mean().unstack()
        uni = s.groupby("ym")["ret_fwd"].mean()
        bc = (s[s["dec"] == 10].groupby("ym")["borrowrate"].mean() / 100.0 / 12.0)
        out_lines.append(f"-- {labels[t]} tercile (n_months={uni.shape[0]}, names={s['permno'].nunique()})")
        lo_g = (g[1] - uni).dropna() if 1 in g.columns else pd.Series(dtype=float)
        lo_n = lo_g - 0.0010
        for lo, hi, per in [(1996, 2025, "1996-2025"), (2016, 2025, "2016-2025")]:
            m = (lo_n.index.year >= lo) & (lo_n.index.year <= hi)
            if m.sum() > 6:
                out_lines.append(stats(lo_g[m], f"  long-1x gross {per}"))
                out_lines.append(stats(lo_n[m], f"  long-1x net10 {per}"))
                ss = lo_n[m].dropna()
                cells[(tag, t, per)] = (ss.mean(), ss.mean() / (ss.std(ddof=1) / np.sqrt(len(ss))) if len(ss) > 1 and ss.std(ddof=1) > 0 else np.nan)
        if 1 in g.columns and 10 in g.columns:
            ls = (g[1] - g[10]).dropna()
            bc2 = bc.reindex(ls.index).fillna(0)
            net = ls - (0.0020 + bc2)
            for lo, hi, per in [(1996, 2025, "1996-2025"), (2016, 2025, "2016-2025")]:
                m = (net.index.year >= lo) & (net.index.year <= hi)
                if m.sum() > 6:
                    out_lines.append(stats(ls[m], f"  LS gross {per}"))
                    out_lines.append(stats(net[m], f"  LS net20 {per}") + f"  brcost={bc2[m].mean()*1e4:.1f}bp/mo")


def run(out_lines):
    db = BX.conn()
    p = build_panel(db, YEARS)
    out_lines.append(f"BORROW-XS2  run {pd.Timestamp.today().date()}  years 1996-2025  "
                     f"panel rows={len(p):,} names={p['permno'].nunique():,} "
                     f"vol-eligible rows={p['vol24'].notna().sum():,}")
    cells = {}
    p["size_terc"] = p.groupby("ym")["mktcap"].transform(qcut3)
    p["vol_terc"] = p.groupby("ym")["vol24"].transform(qcut3)
    tercile_arm(p, "size_terc", {1: "SMALL", 2: "MID", 3: "LARGE"}, "SIZE", out_lines, cells)
    tercile_arm(p, "vol_terc", {1: "LOW", 2: "MID", 3: "HIGH"}, "VOL", out_lines, cells)

    out_lines.append("\n== PRE-REGISTERED DECISION (long-only D1 - EW(within tercile) net of 10bp) ==")
    for per in ["1996-2025", "2016-2025"]:
        out_lines.append(f"  period {per}:")
        for tag, tnames in [("SIZE", {1: "SMALL", 2: "MID", 3: "LARGE"}),
                            ("VOL", {1: "LOW", 2: "MID", 3: "HIGH"})]:
            row = []
            for t in [1, 2, 3]:
                mv = cells.get((tag, t, per))
                if mv is None:
                    row.append(f"{tnames[t]}=NA")
                else:
                    mean, tt = mv
                    ok = (mean > 0) and (tt >= 2)
                    row.append(f"{tnames[t]}: mean={mean*1e4:.1f}bp t={tt:.2f} {'PASS' if ok else 'no'}")
            out_lines.append(f"    {tag}: " + " | ".join(row))
    sz_ok = all(cells.get(("SIZE", t, "1996-2025")) is not None
                and cells[("SIZE", t, "1996-2025")][0] > 0 and cells[("SIZE", t, "1996-2025")][1] >= 2
                for t in [2, 3])
    vol_ok = all(cells.get(("VOL", t, "1996-2025")) is not None
                 and cells[("VOL", t, "1996-2025")][0] > 0 and cells[("VOL", t, "1996-2025")][1] >= 2
                 for t in [1, 2])
    verdict = "PASS" if (sz_ok and vol_ok) else "KILL"
    out_lines.append(f"\n  VERDICT (FULL 1996-2025, literal rule): {verdict}")
    out_lines.append(f"    size (MID,LARGE) pass = {sz_ok} ; vol (LOW,MID) pass = {vol_ok}")
    out_lines.append(f"    -> {'the tilt is NOT merely size/vol beta.' if verdict == 'PASS' else 'the tilt survives only in the small and/or high-vol tercile: BORROW-XS is size/vol beta.'}")
    out_lines.append("\n(terciles refit each month; deciles refit within each tercile-month; D1=low fee, D10=high fee; "
                     "long-only net = -10bp; LS net = 20bp RT + actual borrow on D10; t = month-clustered)")
    return "\n".join(out_lines)


if __name__ == "__main__":
    lines = []
    txt = run(lines)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(txt + "\n")
    print(txt)
