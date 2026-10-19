"""Study CUST-MOM: customer-supplier momentum (Cohen-Frazzini 2008), long-only, judged post-publication 2005+
(pre-reg round1_prose.md "Study CUST-MOM"). Run: PYTHONPATH=. .venv/bin/python -m research.sim.cust_mom [pull]

Choices the registration left open (stated, not tuned):
 - Customer names are matched to CRSP historical names (stocknames, valid within +-1y of srcdate) first, then to
   Compustat current names (comp.names -> CCM -> permno). One customer name -> one permno or it is dropped.
 - CRSP msf ends 2024-12 on this subscription: the judge window is 2005-01..2024-12, halves 2005-15 / 2016-24.
 - Month-m customer return uses CRSP ret incl. delisting returns; a customer that equals its supplier is dropped.
"""
from __future__ import annotations
import re, sys, pathlib
import numpy as np, pandas as pd

C = pathlib.Path("data/research/wrds_cust"); C.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path("data/research/program/cust_mom_out.txt")
COST, SHOCK = 0.0030, 0.0090
SUF = r"\b(INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|LLC|PLC|HOLDINGS?|GROUP|THE|LP|NV|SA|AG|ADR|CL A|CL B|NEW|DEL)\b"
GENERIC = re.compile(r"NOT REPORTED|CUSTOMER|GOVERNMENT|DISTRIBUTOR|DEALER|RETAILER|WHOLESALER|OEM|MANUFACTURER|HOSPITAL|UTILIT|AGENC|DEPARTMENT|"
                     r"^\d|AFFILIATE|VARIOUS|OTHER|INDIVIDUAL|UNNAMED|MAJOR|LARGEST|SEGMENT|EXPORT|DOMESTIC|FOREIGN|MILITARY|NAVY|ARMY|AIR FORCE|DOD|US GOV")


def norm(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", str(s).upper().replace("&", " AND "))
    s = re.sub(SUF, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def pull():
    import wrds
    u = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3].strip()
    db = wrds.Connection(wrds_username=u)
    q = lambda s, f, dc=None: db.raw_sql(s, date_cols=dc).to_parquet(C / f)
    q("select gvkey, cnms, salecs, srcdate from compseg.wrds_seg_customer where ctype='COMPANY' and srcdate>='1979-01-01'", "cust.parquet", ["srcdate"])
    q("select gvkey, conm from comp.names", "compnames.parquet")
    q("select gvkey, lpermno as permno, linkdt, linkenddt, linktype, linkprim from crsp.ccmxpf_lnkhist where linktype in ('LU','LC') and linkprim in ('P','C')",
      "ccm.parquet", ["linkdt", "linkenddt"])
    q("select permno, namedt, nameenddt, comnam, shrcd, exchcd from crsp.stocknames", "stocknames.parquet", ["namedt", "nameenddt"])
    q("select permno, date, ret, prc, shrout, hsiccd from crsp.msf where date>='1980-01-01'", "msf.parquet", ["date"])
    q("select permno, dlstdt, dlret from crsp.msedelist where dlret is not null", "delist.parquet", ["dlstdt"])
    days = db.raw_sql("select distinct date from crsp.dsi where date>='1980-01-01' order by date", date_cols=["date"])["date"]
    first = days.groupby(days.dt.to_period("M")).min()
    parts = []
    for y in range(1980, 2025):
        ds = ",".join(f"'{d.date()}'" for d in first if d.year == y)
        parts.append(db.raw_sql(f"select permno, date, ret from crsp.dsf where date in ({ds})", date_cols=["date"]))
        print("day1", y, flush=True)
    pd.concat(parts).to_parquet(C / "day1.parquet")


def links():
    cu = pd.read_parquet(C / "cust.parquet")
    cu["n"] = cu["cnms"].map(norm)
    cu = cu[(cu["n"].str.len() >= 3) & ~cu["cnms"].str.upper().str.contains(GENERIC)]
    sn = pd.read_parquet(C / "stocknames.parquet")
    sn = sn[sn.shrcd.isin([10, 11])]
    sn["n"] = sn["comnam"].map(norm)
    ccm = pd.read_parquet(C / "ccm.parquet"); ccm["linkenddt"] = ccm["linkenddt"].fillna(pd.Timestamp("2099-12-31"))
    # supplier permno at srcdate
    s = cu.merge(ccm, on="gvkey")
    s = s[(s.linkdt <= s.srcdate) & (s.linkenddt >= s.srcdate)].rename(columns={"permno": "sp"})
    # customer via CRSP historical names (valid within +-1y)
    m = s.merge(sn[["n", "permno", "namedt", "nameenddt"]], on="n")
    m = m[(m.namedt <= m.srcdate + pd.Timedelta(days=365)) & (m.nameenddt >= m.srcdate - pd.Timedelta(days=365))]
    m = m.groupby(["gvkey", "srcdate", "cnms"]).filter(lambda g: g.permno.nunique() == 1)
    hit = m[["gvkey", "srcdate", "cnms", "salecs", "sp", "permno"]].drop_duplicates(["gvkey", "srcdate", "cnms"])
    # fallback: Compustat current names -> CCM
    rest = s.merge(hit[["gvkey", "srcdate", "cnms"]], how="left", indicator=True).query("_merge=='left_only'").drop(columns="_merge")
    cn = pd.read_parquet(C / "compnames.parquet"); cn["n"] = cn["conm"].map(norm)
    cn = cn.groupby("n").filter(lambda g: g.gvkey.nunique() == 1).merge(ccm, on="gvkey", suffixes=("", "_c"))
    f = rest.merge(cn[["n", "gvkey", "permno", "linkdt", "linkenddt"]].rename(columns={"gvkey": "cg", "linkdt": "cl0", "linkenddt": "cl1", "permno": "cp"}), on="n")
    f = f[(f.cl0 <= f.srcdate) & (f.cl1 >= f.srcdate)]
    f = f.groupby(["gvkey", "srcdate", "cnms"]).filter(lambda g: g.cp.nunique() == 1).rename(columns={"cp": "permno"})
    hit = pd.concat([hit, f[["gvkey", "srcdate", "cnms", "salecs", "sp", "permno"]].drop_duplicates(["gvkey", "srcdate", "cnms"])])
    hit = hit[hit.sp != hit.permno]
    stats = dict(cust_rows=len(cu), linked=len(hit), suppliers=hit.sp.nunique(), customers=hit.permno.nunique())
    return hit, stats


def returns():
    r = pd.read_parquet(C / "msf.parquet")
    r["m"] = r["date"].dt.to_period("M")
    d = pd.read_parquet(C / "delist.parquet"); d["m"] = d["dlstdt"].dt.to_period("M")
    r = r.merge(d[["permno", "m", "dlret"]], on=["permno", "m"], how="left")
    r["ret"] = (1 + r["ret"].fillna(0)) * (1 + r["dlret"].fillna(0)) - 1
    r.loc[r[["ret", "dlret"]].isna().all(1), "ret"] = np.nan
    sn = pd.read_parquet(C / "stocknames.parquet")
    ok = sn[sn.shrcd.isin([10, 11]) & sn.exchcd.isin([1, 2, 3])][["permno", "namedt", "nameenddt"]]
    r = r.merge(ok, on="permno")
    r = r[(r.date >= r.namedt) & (r.date <= r.nameenddt)].drop(columns=["namedt", "nameenddt"]).drop_duplicates(["permno", "m"])
    r["px"] = r["prc"].abs(); r["mcap"] = r["px"] * r["shrout"] / 1e3  # $M
    d1 = pd.read_parquet(C / "day1.parquet"); d1["m"] = d1["date"].dt.to_period("M")
    r = r.merge(d1[["permno", "m", "ret"]].rename(columns={"ret": "r1"}), on=["permno", "m"], how="left")
    r["rskip"] = (1 + r["ret"]) / (1 + r["r1"].fillna(0)) - 1
    r["sic2"] = (r["hsiccd"] // 100)
    return r


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "pull":
        pull(); return
    hit, st = links()
    r = returns()
    R = r.set_index(["permno", "m"])
    months = pd.period_range("1981-01", str(r.m.max()), freq="M")
    # active links per month: srcdate+6m .. srcdate+18m, latest srcdate per (supplier, customer) wins
    hit["a0"] = (hit.srcdate + pd.DateOffset(months=6)).dt.to_period("M")
    hit["a1"] = (hit.srcdate + pd.DateOffset(months=18)).dt.to_period("M")
    rows = []
    ret_m = r.pivot(index="m", columns="permno", values="ret")
    for m in months[:-1]:
        L = hit[(hit.a0 <= m) & (hit.a1 > m)].sort_values("srcdate").drop_duplicates(["sp", "permno"], keep="last")
        if not len(L) or m not in ret_m.index: continue
        cr = ret_m.loc[m].reindex(L.permno.values).values
        L = L.assign(cr=cr).dropna(subset=["cr"])
        L["w"] = L.salecs.fillna(0).clip(lower=0); L.loc[L.groupby("sp").w.transform("sum") <= 0, "w"] = 1
        g = L.groupby("sp").apply(lambda x: np.average(x.cr, weights=x.w), include_groups=False).rename("sig")
        cur = r[r.m == m].set_index("permno")
        elig = cur[(cur.px >= 5) & (cur.mcap >= 50)].index
        g = g[g.index.isin(elig)]
        if len(g) < 25: continue
        nxt = r[r.m == m + 1].set_index("permno")
        univ = nxt.loc[nxt.index.intersection(elig)]
        q = pd.qcut(g.rank(method="first"), 5, labels=False)
        fr = nxt["rskip"].reindex(g.index)
        top, bot = fr[q == 4].dropna(), fr[q == 0].dropna()
        if len(top) < 5: continue
        b1 = univ["rskip"].mean()
        sicm = univ.groupby("sic2")["rskip"].mean()
        ind = (top - nxt["sic2"].reindex(top.index).map(sicm)).mean()
        rows.append(dict(m=m + 1, n=len(top), n_sup=len(g), top=top.mean(), bot=bot.mean(), b1=b1, ind=ind))
    D = pd.DataFrame(rows).set_index("m")
    D["x1"] = D.top - D.b1 - COST; D["x2"] = D.ind - COST; D["ls"] = D.top - D.bot
    D.to_parquet(C / "cust_mom_monthly.parquet")

    def s(x, lab):
        x = x.dropna(); n = len(x); t = x.mean() / x.std(ddof=1) * np.sqrt(n)
        ex5 = x.sort_values().iloc[:-5].mean()
        return f"{lab:34s} n={n:<3} mean={x.mean()*1e2:+.2f}%/mo t={t:+.2f} med={x.median()*1e2:+.2f} hit={(x>0).mean()*100:.0f}% ex-top5={ex5*1e2:+.2f}"
    L = [f"CUST-MOM. links: {st}", f"months scored {len(D)} ({D.index.min()}..{D.index.max()}); mean Q5 names {D.n.mean():.0f} of {D.n_sup.mean():.0f} linked suppliers"]
    for nm, a, b in [("REPLICATION 1981-2004 (data check)", "1981-01", "2004-12"), ("JUDGE 2005-2024", "2005-01", "2024-12"),
                     ("  half 2005-15", "2005-01", "2015-12"), ("  half 2016-24", "2016-01", "2024-12")]:
        x = D.loc[pd.Period(a, "M"):pd.Period(b, "M")]
        L.append(nm)
        L.append("   " + s(x.x1, "Q5 - EW universe, net 30bp"))
        L.append("   " + s(x.x2, "Q5 - SIC2 peers, net 30bp"))
        L.append("   " + s(x.x1 - 2 * COST, "Q5 - EW universe, net 90bp (3x)"))
        L.append("   " + s(x.ls, "Q5 - Q1 gross (diagnostic)"))
        L.append("   " + s(x.top, "Q5 raw"))
    j = D.loc[pd.Period("2005-01", "M"):pd.Period("2024-12", "M")]
    h1, h2 = j.loc[:pd.Period("2015-12", "M")], j.loc[pd.Period("2016-01", "M"):]
    t1 = j.x1.mean() / j.x1.std() * np.sqrt(len(j)); t2 = j.x2.mean() / j.x2.std() * np.sqrt(len(j))
    ok = (j.x1.mean() > 0 and t1 >= 2 and j.x1.median() > 0 and j.x1.sort_values().iloc[:-5].mean() > 0 and h1.x1.mean() > 0 and h2.x1.mean() > 0
          and j.x2.mean() > 0 and t2 >= 2)
    L.append(f"VERDICT: {'PASS' if ok else 'KILL'} (gates: B1 mean>0,t>=2,median>0,ex-top5>0,both halves>0; B2 mean>0,t>=2)")
    L.append(f"by year Q5-EW net %/mo:\n" + (j.x1.groupby(j.index.year).mean() * 100).round(2).to_string())
    OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
