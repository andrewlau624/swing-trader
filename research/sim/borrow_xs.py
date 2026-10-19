"""Study BORROW-XS runner (pre-registered 2026-10-16, program N 1005 -> 1006).
Option-implied borrow-rate cross-section: decile LS (level and 3m change) + long-only D1 excess vs EW universe,
common shares ($5+), CRSP monthly incl. delisting returns, 1996-2025. One look, no tuning.
Usage: .venv/bin/python -m research.sim.borrow_xs [--years 1996 2025] [--nocache]
Cache: data/research/borrate/ ; output: data/research/program/borrow_xs_out.txt
"""
import sys, pathlib, numpy as np, pandas as pd, wrds

D = pathlib.Path("data/research/borrate"); D.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path("data/research/program/borrow_xs_out.txt")
U = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
YEARS = list(range(1996, 2026))


def conn():
    import time
    for k in range(40):
        try:
            return wrds.Connection(wrds_username=U, wrds_connect_attempts=2)
        except BaseException:
            time.sleep(min(60, 5 * (k + 1)))
    raise RuntimeError("wrds connect failed")


def pull_borrate_year(y, db, nocache=False):
    f = D / f"borrate_m_{y}.parquet"
    if f.exists() and not nocache:
        return pd.read_parquet(f)
    sql = f"""
    select distinct on (securityid, date_trunc('month', date))
           securityid, date_trunc('month', date)::date as ym, date as obsdt, borrowrate
    from optionm.borrate{y}
    where borrowrate > -99
    order by securityid, date_trunc('month', date), date desc, abs(days - 30)
    """
    df = db.raw_sql(sql)
    df.to_parquet(f, index=False)
    return df


def pull_all_borrate(db, years, nocache=False):
    parts = []
    for y in years:
        try:
            parts.append(pull_borrate_year(y, db, nocache))
        except Exception as e:
            print(f"  borrate {y} FAIL {str(e)[:80]}")
    return pd.concat(parts, ignore_index=True)


def pull_static(db, nocache=False):
    p = D / "static.parquet"
    if p.exists() and not nocache:
        return pd.read_pickle(p)
    link = db.raw_sql("select secid, sdate, edate, permno from wrdsapps_link_crsp_optionm.opcrsphist where score = 1")
    link["sdate"] = pd.to_datetime(link["sdate"]); link["edate"] = pd.to_datetime(link["edate"])
    msf = db.raw_sql("select permno, date as ym, ret, prc, shrout, hexcd from crsp.msf")
    msf["prc"] = pd.to_numeric(msf["prc"], errors="coerce"); msf["ym"] = pd.to_datetime(msf["ym"])
    names = db.raw_sql("select distinct on (permno) permno, shrcd from crsp.dsenames order by permno, namedt desc")
    dl = db.raw_sql("select permno, dlstdt, dlret from crsp.dsedelist where dlret is not null")
    dl["dlstdt"] = pd.to_datetime(dl["dlstdt"])
    dl["glm"] = (dl["dlstdt"] + pd.offsets.MonthBegin(1)).dt.to_period("M").dt.to_timestamp()
    out = {"link": link, "msf": msf, "names": names, "dl": dl}
    pd.to_pickle(out, p)
    return out


def qcut_decile(s):
    try:
        return pd.qcut(s, 10, labels=False, duplicates="drop") + 1
    except Exception:
        return pd.Series(np.nan, index=s.index)


def run(years, out_lines):
    db = conn()
    br = pull_all_borrate(db, years)
    st = pull_static(db)
    br = br.merge(st["link"], left_on="securityid", right_on="secid", how="inner")
    br["ym"] = pd.to_datetime(br["ym"]); br["obsdt"] = pd.to_datetime(br["obsdt"])
    br = br[(br["sdate"] <= br["obsdt"]) & ((br["edate"].isna()) | (br["edate"] >= br["obsdt"]))]
    br = br[["permno", "ym", "borrowrate"]].drop_duplicates(["permno", "ym"])

    msf = st["msf"].copy()
    msf["ym"] = pd.to_datetime(msf["ym"]).dt.to_period("M").dt.to_timestamp()
    msf = msf.merge(st["names"], on="permno", how="left")
    ret = msf[["permno", "ym", "ret"]].copy()
    dl = st["dl"][["permno", "glm", "dlret"]].rename(columns={"glm": "ym"})
    ret = pd.concat([ret, dl], ignore_index=True)
    ret = ret.dropna(subset=["ret"]).drop_duplicates(["permno", "ym"])

    p = br.merge(msf[["permno", "ym", "prc", "shrcd", "hexcd"]], on=["permno", "ym"], how="left")
    p = p[(p["prc"].abs() >= 5) & (p["shrcd"].isin([10, 11]))].copy()
    p = p.sort_values(["permno", "ym"])
    p["br_chg3"] = p["borrowrate"] - p.groupby("permno")["borrowrate"].shift(3)
    p["ym_next"] = p["ym"] + pd.offsets.MonthBegin(1)
    p = p.merge(ret.rename(columns={"ym": "ym_next", "ret": "ret_fwd"}), on=["permno", "ym_next"], how="left")
    p = p.dropna(subset=["ret_fwd"])

    def stats(series, name):
        s = series.dropna()
        n = len(s)
        if n == 0:
            return f"{name:26s} no obs"
        mean, sd = s.mean(), s.std(ddof=1)
        t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
        med = np.median(s)
        ex5 = s.sort_values().iloc[:-5].mean() if n > 5 else np.nan
        return (f"{name:26s} n={n:4d} gross={mean*1e4:8.2f}bp t={t:6.2f} med={med*1e4:7.2f} "
                f"ex5={ex5*1e4:8.2f}")

    lines = []
    lines.append(f"BORROW-XS  run {pd.Timestamp.today().date()}  years {years[0]}-{years[-1]}  "
                 f"panel rows={len(p):,} names={p['permno'].nunique():,}")
    for arm, col in [("A_level", "borrowrate"), ("B_chg3", "br_chg3")]:
        sub = p.dropna(subset=[col]).copy()
        sub["dec"] = sub.groupby("ym")[col].transform(qcut_decile)
        g = sub.dropna(subset=["dec"]).groupby(["ym", "dec"])["ret_fwd"].mean().unstack()
        uni = sub.groupby("ym")["ret_fwd"].mean()
        if 1 in g.columns and 10 in g.columns:
            ls = (g[1] - g[10]).dropna()
            brcost = sub[sub["dec"] == 10].groupby("ym")["borrowrate"].mean() / 100.0 / 12.0
            brcost = brcost.reindex(ls.index).fillna(0)
            net = ls - (0.0020 + brcost)
            lines.append(f"\n== Arm {arm} ({col}) ==")
            for lo, hi, tag in [(1996, 2007, "1996-2007"), (2008, 2015, "2008-2015"),
                                (2016, 2025, "2016-2025"), (years[0], years[-1], "FULL")]:
                m = (ls.index.year >= lo) & (ls.index.year <= hi)
                if m.sum() > 6:
                    lines.append(stats(ls[m], f"LS gross {tag}"))
                    lines.append(stats(net[m], f"LS net   {tag}") + f"  brcost={brcost[m].mean()*1e4:.1f}bp/mo")
            lo_only = (g[1] - uni).dropna()
            lines.append(stats(lo_only, "longonly D1-EW gross"))
            lines.append(stats(lo_only - 0.0010, "longonly D1-EW net"))
            prof = g.mean()
            lines.append("decile profile bp/mo: " + " ".join(f"D{d}={prof[d]*1e4:.0f}" for d in sorted(prof.index) if d in prof))
            if 1 in g.columns and 5 in g.columns:
                lines.append(stats((g[1] - g[5]).dropna(), "D1-D5 (mid)"))
                lines.append(stats((g[5] - g[10]).dropna(), "D5-D10 (mid)"))
    lines.append("\n(deciles refit each month; D1=low fee, D10=high fee; net = 20bp RT + actual borrow on D10; "
                 "t = month-clustered)")
    out_lines.extend(lines)
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    nocache = "--nocache" in args
    ys = YEARS
    if "--years" in args:
        i = args.index("--years"); ys = list(range(int(args[i + 1]), int(args[i + 2]) + 1))
    lines = []
    txt = run(ys, lines)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(txt + "\n")
    print(txt)
