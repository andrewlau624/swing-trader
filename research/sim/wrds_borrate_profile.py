"""READ-ONLY profiling of WRDS OptionMetrics borrow-rate data (optionm.borrateYYYY / fwdprbrYYYY).

Answers, with real query output: coverage per year, the missing sentinel, reporting
frequency / key grain, breadth vs the tradable universe, the join path to ticker/cusip/permno,
and a sanity series on well-known hard-to-borrow names.

Usage:
    .venv/bin/python -m research.sim.wrds_borrate_profile
Writes: data/research/wrds_recon/borrate_profile.txt  (also prints to stdout)

Data is never modified. Any single query is bounded to one year (<= ~8M rows) or a
single securityid.
"""
import pathlib
import sys
import time
import wrds

OUT = pathlib.Path("data/research/wrds_recon/borrate_profile.txt")
YEARS = [1996, 2005, 2015, 2020, 2024, 2025]
SENT = -99.0


def connect():
    U = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
    last = None
    for k in range(12):
        try:
            return wrds.Connection(wrds_username=U)
        except BaseException as e:  # noqa: BLE001
            last = e
            time.sleep(min(30, 3 * (k + 1)))
    raise RuntimeError(f"wrds connect failed: {last}")


class Rep:
    def __init__(self):
        self.buf = []

    def w(self, s=""):
        self.buf.append(s)

    def title(self, s):
        self.w()
        self.w("=" * 78)
        self.w(s)
        self.w("=" * 78)

    def sub(self, s):
        self.w()
        self.w(f"-- {s}")

    def df(self, d, indent="  "):
        for line in d.to_string().splitlines():
            self.w(indent + line)

    def dump(self):
        txt = "\n".join(self.buf) + "\n"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(txt)
        sys.stdout.write(txt)
        return txt


def main():
    r = Rep()
    db = connect()
    q = db.raw_sql

    r.title("WRDS OptionMetrics borrow-rate profile (optionm.borrateYYYY / fwdprbrYYYY)")
    r.w(f"generated: {time.strftime('%Y-%m-%d %H:%M:%S')}  |  server: wrds  |  READ-ONLY")

    # ---------------------------------------------------------------- tables
    r.title("0. Tables present (each year is a separate table; there is NO bare borrate)")
    tobs = [t for t in db.list_tables(library="optionm") if t.startswith("borrate")]
    fobs = [t for t in db.list_tables(library="optionm") if t.startswith("fwdprbr")]
    r.w(f"borrate  tables: {len(tobs)}  {min(tobs)} .. {max(tobs)}")
    r.w(f"fwdprbr  tables: {len(fobs)}  {min(fobs)} .. {max(fobs)}")
    r.w("borrate cols : securityid, date, expirationdate, days, borrowrate")
    r.w("fwdprbr cols : securityid, date, expiration, amsettlement, forwardprice")
    r.w("secnmd  cols : secid, effect_date, cusip, ticker, class, issuer, issue, sic")
    r.w("link table   : wrdsapps_link_crsp_optionm.opcrsphist  (secid, sdate, edate, permno, score)")

    # ------------------------------------------------------------- 1 coverage
    r.title("1. Coverage per representative year")
    r.w("n=rows, nsec=distinct securityid, ndates=distinct date; sent=sentinel rows,")
    r.w("validsec=distinct securityid with borrowrate>-99.  Sentinel == missing.")
    rows = []
    for y in YEARS:
        d = q(
            f"""select count(*) n, count(distinct securityid) nsec, count(distinct date) ndates,
                       min(date) mn, max(date) mx,
                       sum(case when borrowrate <= {SENT} then 1 else 0 end) sent,
                       count(distinct case when borrowrate > {SENT} then securityid end) validsec
                from optionm.borrate{y}"""
        ).iloc[0]
        rows.append(dict(year=y, **d.to_dict()))
    import pandas as pd

    cov = pd.DataFrame(rows)
    cov["sent_frac"] = (cov.sent / cov.n).round(3)
    cov = cov[["year", "n", "nsec", "ndates", "mn", "mx", "sent", "sent_frac", "validsec"]]
    r.df(cov)
    r.w()
    r.w("NOTE: 2025 in this WRDS snapshot stops at the mx date above (partial year).")
    r.w("      fwdprbrYYYY shares securityid/date grain with borrateYYYY and adds")
    r.w("      forwardprice (same coverage):")
    fd = q("select count(*) n, count(distinct securityid) nsec, count(distinct date) ndates from optionm.fwdprbr2024").iloc[0]
    r.df(pd.DataFrame([fd.to_dict()]))

    # -------------------------------------------------------------- 2 sentinel
    r.title("2. Missing sentinel and the valid borrowrate distribution")
    r.w(f"Sentinel = borrowrate <= {SENT} (observed exact value: -99.99). Values are PERCENT per annum.")
    for y in (2020, 2024):
        d = q(
            f"""select min(borrowrate) mn,
                       percentile_cont(0.25) within group (order by borrowrate) p25,
                       percentile_cont(0.50) within group (order by borrowrate) p50,
                       percentile_cont(0.75) within group (order by borrowrate) p75,
                       percentile_cont(0.90) within group (order by borrowrate) p90,
                       percentile_cont(0.99) within group (order by borrowrate) p99,
                       max(borrowrate) mx
                from optionm.borrate{y} where borrowrate > {SENT}"""
        ).iloc[0]
        d = d.to_dict()
        r.sub(f"borrate{y} valid-only borrowrate (percent/yr)")
        r.df(pd.DataFrame([d]))
    r.w()
    r.w("Reading (2020): ~55% of rows are the -99.99 sentinel; valid rates are tiny for most")
    r.w("names (median ~0.02%/yr = easy-to-borrow) with a fat right tail (p99 ~1%, max ~20%).")

    # -------------------------------------------------------------- 3 frequency
    r.title("3. Reporting frequency / key grain")
    r.w("Key grain = (securityid, date, expirationdate) -- verified unique (no dup keys).")
    for y in (2015, 2020, 2024):
        d = q(f"select count(*) n, count(distinct (securityid,date,expirationdate)) d from optionm.borrate{y}").iloc[0]
        r.w(f"  borrate{y}: rows={int(d.n)}, distinct (securityid,date,expirationdate)={int(d.d)}  -> {'UNIQUE' if int(d.n)==int(d.d) else 'DUPLICATES'}")
        med = q(
            f"""select percentile_cont(0.5) within group (order by c) med_rows_per_sec,
                       min(c) mn, max(c) mx
                from (select securityid, count(*) c from optionm.borrate{y} group by securityid) t"""
        ).iloc[0]
        r.w(f"    median rows/securityid/year={float(med.med_rows_per_sec):.0f} (min {int(med.mn)}, max {int(med.mx)})")
    r.w()
    r.w("Within a securityid it is a DAILY grid (one row per listed option expiration each day).")
    r.w("Date spacing for 3 securityids picked with full-year 2024 coverage")
    r.w("(consecutive distinct dates in 2024):")
    picks = q(
        """select securityid from optionm.borrate2024 group by securityid
           having count(distinct date) >= 250 order by securityid limit 3"""
    ).securityid.tolist()
    for sid in picks:
        g = q(
            f"""select min(g) mn, percentile_cont(0.5) within group (order by g) med, max(g) mx, count(*) k
                from (select date - lag(date) over (order by date) g
                      from (select distinct date from optionm.borrate2024 where securityid={int(sid)}) t) u
                where g is not null"""
        ).iloc[0]
        r.w(f"    secid {int(sid)}: median gap {int(g.med)}d (min {int(g.mn)}, max {int(g.mx)}), {int(g.k)+1} dates")
    r.w("=> not tied to expirations; every trading day, one borrowrate per expiration on the chain.")
    r.w()
    r.w("fwdprbr adds an amsettlement flag (0=PM-settled, 1=AM-settled); key is unique on")
    r.w("(securityid, date, expiration, amsettlement):")
    d = q("select count(*) n, count(distinct (securityid,date,expiration,amsettlement)) d from optionm.fwdprbr2024").iloc[0]
    r.w(f"  fwdprbr2024 rows={int(d.n)} distinct key={int(d.d)}")

    # -------------------------------------------------------------- 4 breadth
    r.title("4. Breadth vs the tradable universe (2024)")
    n_all = q("select count(distinct securityid) c from optionm.borrate2024").iloc[0].c
    n_val = q(f"select count(distinct securityid) c from optionm.borrate2024 where borrowrate>{SENT}").iloc[0].c
    r.w(f"distinct securityid with a valid borrowrate in 2024: {int(n_val)} of {int(n_all)} optionable names")
    r.sub("CRSP security type (SHRCD) of those, via opcrsphist -> crsp.dsenames (2024-06-30 snapshot)")
    sd = q(
        f"""select n.shrcd, count(distinct o.secid) c
            from wrdsapps_link_crsp_optionm.opcrsphist o
            join crsp.dsenames n on n.permno=o.permno
                 and n.namedt <= '2024-06-30' and (n.nameendt is null or n.nameendt >= '2024-06-30')
            join optionm.borrate2024 b on b.securityid=o.secid and b.borrowrate>{SENT}
            where o.sdate <= '2024-06-30' and (o.edate is null or o.edate >= '2024-06-30')
            group by n.shrcd order by c desc"""
    )
    r.df(sd)
    tot = int(sd.c.sum())
    common = int(sd.loc[sd.shrcd.isin([11, 12]), "c"].sum())
    etf = int(sd.loc[sd.shrcd == 73, "c"].sum())
    r.w("  SHRCD legend (CRSP): 11/12 = ordinary common (US/foreign); 73 = ETFs;")
    r.w("  31 = ADRs/foreign ordinaries; 18/48 = REITs; 14 = preferred.")
    r.w(f"  of {tot} linkable names: ordinary common {common} ({100*common/tot:.0f}%), "
        f"ETFs {etf} ({100*etf/tot:.0f}%), ADRs/foreign {int(sd.loc[sd.shrcd==31,'c'].sum())}.")
    r.sub("Same idea by issuer name (latest secnmd row per secid, tokens via strpos)")
    nm = q(
        f"""with latest as (
              select distinct on (secid) secid, lower(issuer) iss from optionm.secnmd order by secid, effect_date desc)
            select count(distinct b.securityid) c from optionm.borrate2024 b
            join latest l on l.secid=b.securityid
            where b.borrowrate>{SENT}
              and (strpos(l.iss,'etf')>0 or strpos(l.iss,'ishares')>0 or strpos(l.iss,'spdr')>0
                   or strpos(l.iss,'proshares')>0 or strpos(l.iss,'vanguard')>0 or strpos(l.iss,'invesco')>0)"""
    ).iloc[0].c
    r.w(f"  distinct secids matching an ETF/issuer token: {int(nm)}")

    # -------------------------------------------------------------- 5 join path
    r.title("5. Join path: securityid -> cusip/ticker and -> CRSP permno")
    r.w("(a) securityid == optionm.secnmd.secid (100% of a year's secids match). secnmd is a")
    r.w("    slowly-changing dimension: SAME secid can appear on many effect_date rows, so a")
    r.w("    naive 'secnmd.effect_date <= borrate.date' join FANS OUT. Dedup to the single row")
    r.w("    active on the trade date with DISTINCT ON.")
    mm = q(
        f"""select (select count(distinct securityid) from optionm.borrate2024) secids,
                   (select count(*) from (select distinct b.securityid from optionm.borrate2024 b
                        join optionm.secnmd s on s.secid=b.securityid) x) matched"""
    ).iloc[0]
    r.w(f"    secnmd match: {int(mm.matched)}/{int(mm.secids)} secids in 2024 resolve to a secnmd row")
    r.sub("Point-in-time ticker/cusip (as-of active metadata), 3 example rows from 2021-01-11")
    ex = q(
        """select distinct on (b.securityid) b.securityid, s.ticker, s.cusip, s.issuer
           from optionm.borrate2021 b
           join optionm.secnmd s on s.secid=b.securityid and s.effect_date <= b.date
           where b.date='2021-01-11'
           order by b.securityid, s.effect_date desc
           limit 3"""
    )
    r.df(ex)
    r.w("(b) CRSP link: wrdsapps_link_crsp_optionm.opcrsphist (secid, sdate, edate, permno, score).")
    r.w("    Use range overlap: sdate <= date and (edate is null or edate >= date). ~71% of")
    r.w("    opcrsphist rows have a null edate (open-ended).")
    lk = q("select count(*) n, sum(case when edate is null then 1 else 0 end) ed_null, sum(case when permno is not null then 1 else 0 end) has_permno from wrdsapps_link_crsp_optionm.opcrsphist").iloc[0]
    r.df(pd.DataFrame([lk.to_dict()]))

    # -------------------------------------------------------------- 6 sanity
    r.title("6. Sanity series on well-known hard-to-borrow names")
    r.w("Borrow rate is PERCENT/yr; sentinel -99.99 replaced by NULL below. For each name we show")
    r.w("the ~30-day-tenor row per day (expiration nearest 30 calendar days), monthly sampled.")
    for tick in ("GME", "AMC"):
        sid_ = q(
            f"""select secid from optionm.secnmd where ticker='{tick}' and effect_date <= '2021-06-30'
                order by effect_date desc limit 1"""
        )
        if not len(sid_):
            r.sub(f"{tick}: no secid")
            continue
        sid = int(sid_.iloc[0].secid)
        r.sub(f"{tick}  (secid {sid}, 2021 monthly, tenor nearest 30d; NULL=sentinel)")
        d = q(
            f"""with daily as (
                  select distinct on (date) date, expirationdate, days,
                         case when borrowrate>{SENT} then borrowrate end as br
                  from optionm.borrate2021 where securityid={sid}
                  order by date, abs(days-30))
                select distinct on (date_trunc('month', date)) to_char(date,'YYYY-MM') mon, date, days, br
                from daily order by date_trunc('month', date), date"""
        )
        r.df(d)
        pk = q(f"select max(borrowrate) mx, percentile_cont(0.9) within group (order by borrowrate) p90 from optionm.borrate2021 where securityid={sid} and borrowrate>{SENT}").iloc[0]
        r.w(f"    {tick} 2021 valid-rate max={float(pk.mx):.2f}%/yr, p90={float(pk.p90):.3f}%/yr")
    r.w()
    r.w("CAVEAT: this implied rate does NOT reproduce the 100%+/yr street borrow fees reported")
    r.w("during the Jan-2021 meme squeeze (GME max here 2.8%, AMC 4.8%). Sector-level relative")
    r.w("ranking is usable; do not treat it as the actual equity-loan fee in extreme squeezes.")

    # -------------------------------------------------------------- pitfalls
    r.title("7. Pitfalls to carry into a pre-registered study")
    r.w("P1 GRAIN / DUPLICATE-KEY FAN-OUT: the fact key is (securityid, date, expirationdate). A")
    r.w("   study that wants one rate per stock-day must choose ONE expiration (a tenor bucket),")
    r.w("   otherwise the same stock-day appears ~4-6x. Joining secnmd without DISTINCT ON fans")
    r.w("   out further (up to ~13x) -- always resolve the as-of metadata row first.")
    r.w("P2 SENTINEL: missing is -99.99 (about 38-56% of rows/yr). It is NOT null; filter")
    r.w("   borrowrate > -99 BEFORE any mean/percentile or every stat is garbage (min looks like -99).")
    r.w("P3 UNITS + PARTIAL YEAR: rates are percent per annum (median ~0.02%/yr = easy-to-borrow,")
    r.w("   high single/double digits = hard-to-borrow). The current-latest table (2025) stops at")
    r.w("   the max date in section 1 -- do not treat it as a full year.")
    r.w("P4 fwdprbr has its own sentinel (-99.99 on forwardprice) with a DIFFERENT column name")
    r.w("   (expiration vs expirationdate); never left-join it to borrate without the amsettlement")
    r.w("   discriminator or a dup appears.")

    # -------------------------------------------------------------- snippet
    r.title("8. Ready-to-use loader: one year of valid borrow rates joined to tickers")
    r.w("Choose ONE expiration per stock-day (30-day tenor: expiration nearest to +30 days).")
    r.w("")
    r.w("""-- one borrow rate per stock-day: expiration nearest +30 calendar days (30d tenor)
with tenor as (
    select distinct on (securityid, date)
           securityid, date, expirationdate, days, borrowrate
    from optionm.borrate2024
    where borrowrate > -99
    order by securityid, date, abs(days - 30)),
meta as (   -- attach the secnmd row active on that date (dedup -> no fan-out)
    select distinct on (t.securityid, t.date)
           t.securityid, t.date, t.expirationdate, t.days, t.borrowrate,
           s.ticker, s.cusip
    from tenor t
    join optionm.secnmd s on s.secid = t.securityid and s.effect_date <= t.date
    order by t.securityid, t.date, s.effect_date desc)
select m.*, l.permno
from meta m
left join wrdsapps_link_crsp_optionm.opcrsphist l
     on l.secid = m.securityid
    and l.sdate <= m.date
    and (l.edate is null or l.edate >= m.date);""")
    r.w("")
    r.w("Minimal pure-borrow-rate pull (no metadata, fastest):")
    r.w("  select securityid, date, expirationdate, days, borrowrate")
    r.w("  from optionm.borrate2024 where borrowrate > -99;")

    # -------------------------------------------------------------- errors?
    r.title("9. Access notes")
    r.w("All queried tables were reachable read-only. wrdsapps_link_crsp_optionm contains only")
    r.w("one table: opcrsphist (secid<->permno crosswalk). There is no bare optionm.borrate.")

    db.close()
    r.dump()


if __name__ == "__main__":
    main()
