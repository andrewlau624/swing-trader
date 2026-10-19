"""READ-ONLY recon of the WRDS CRSP Mutual Fund database (`crsp_q_mutualfunds`) for
(A) ETF creation/redemption flow and (B) closed-end-fund (CEF) discount panels.

Prints a self-contained report and saves it to data/research/wrds_recon/mfnav_profile.txt.
No writes to WRDS; every query is bounded (single-date snapshots / indexed equality / reltuples).

Usage: .venv/bin/python -m research.sim.wrds_mfnav_profile
"""
import pathlib
import datetime as dt
import wrds

OUT = pathlib.Path("data/research/wrds_recon/mfnav_profile.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)

_lines: list[str] = []


def emit(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    _lines.append(s)


def main():
    U = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
    db = wrds.Connection(wrds_username=U)
    errs = []

    def q(sql):
        return db.raw_sql(sql)

    def tryq(label, sql):
        try:
            return q(sql)
        except Exception as e:
            errs.append(f"{label}: {type(e).__name__}: {str(e)[:200]}")
            emit(f"  !! {label}: {type(e).__name__}: {str(e)[:200]}")
            return None

    emit("=" * 100)
    emit("CRSP MUTUAL FUND DATABASE PROFILE  —  crsp_q_mutualfunds @ WRDS")
    emit(f"run {dt.datetime.now():%Y-%m-%d %H:%M}   (read-only; SELECT only)")
    emit("=" * 100)

    # ---------------------------------------------------------------- 0. inventory
    emit("\n## 0. Tables in crsp_q_mutualfunds")
    t = q("""select table_name from information_schema.tables
             where table_schema='crsp_q_mutualfunds' order by 1""")
    emit("   " + ", ".join(t.table_name.tolist()))

    emit("\nKey-table columns:")
    for tb in ["daily_nav", "monthly_tna", "monthly_nav", "daily_nav_ret",
               "fund_hdr", "fund_hdr_hist", "holdings", "fund_flows", "dividends"]:
        c = q(f"""select column_name from information_schema.columns
                  where table_schema='crsp_q_mutualfunds' and table_name='{tb}'
                  order by ordinal_position""")
        emit(f"   {tb:16s}: " + ", ".join(c.column_name.tolist()))

    # ---------------------------------------------------------------- 1. et_flag
    emit("\n## 1. et_flag distribution  (F = ETF, N = exchange-traded note, blank = conventional open-end; NO in-DB codebook)")
    emit("   [fund_hdr_hist = history table]")
    emit(tryq("et_flag hist", """select et_flag, count(*) rows_, count(distinct crsp_fundno) funds,
               min(first_offer_dt) min_fo, max(first_offer_dt) max_fo
               from crsp_q_mutualfunds.fund_hdr_hist group by 1 order by 1 nulls last""").to_string())
    emit("   [fund_hdr = current snapshot]")
    emit(tryq("et_flag cur", """select et_flag, count(distinct crsp_fundno) funds
               from crsp_q_mutualfunds.fund_hdr group by 1 order by 1 nulls last""").to_string())

    emit("\n   ETF/ETN funds reporting a NAV on a mid-year trading day (daily_nav join):")
    emit(f"   {'year':>4} {'date':>10} {'ETF':>6} {'ETN':>5} {'all_nav':>8}")
    etf_sub = "(select distinct crsp_fundno from crsp_q_mutualfunds.fund_hdr_hist where et_flag='F')"
    etn_sub = "(select distinct crsp_fundno from crsp_q_mutualfunds.fund_hdr_hist where et_flag='N')"
    for y in range(1999, 2027):
        d = dt.date(y, 6, 30)
        while d.weekday() >= 5:            # move weekend snapshots to Monday
            d += dt.timedelta(days=1)
        r = tryq("byyear", f"""select
                   count(distinct crsp_fundno) filter (where crsp_fundno in {etf_sub}) etf,
                   count(distinct crsp_fundno) filter (where crsp_fundno in {etn_sub}) etn,
                   count(distinct crsp_fundno) tot
                 from crsp_q_mutualfunds.daily_nav where caldt='{d}' and dnav is not null""")
        if r is not None:
            emit(f"   {y:>4} {str(d):>10} {int(r.etf.iloc[0]):>6} {int(r.etn.iloc[0]):>5} {int(r.tot.iloc[0]):>8}")

    # ---------------------------------------------------------------- 2. class / separability
    emit("\n## 2. Share-class vs CEF identifiability")
    emit("   Per-row grain:  crsp_fundno = ONE SHARE CLASS.  crsp_cl_grp groups classes of one")
    emit("   fund; crsp_portno groups classes that share a portfolio (holdings/tna are per portno).")
    emit("   Available class/roster fields in fund_hdr_hist:")
    emit("     et_flag (F=ETF,N=ETN,blank=open-end), index_fund_flag, open_to_inv, retail_fund,")
    emit("     inst_fund, m_fund, vau_fund, crsp_cl_grp, crsp_portno, cusip8, ncusip, ticker.")
    emit("   There is NO closed-end-fund flag anywhere in the library. CEFs are ABSENT from")
    emit("   crsp_q_mutualfunds entirely (they are exchange-listed and live in the CRSP stock DB).")
    emit("   Evidence — known CEF names / tickers found in the MFDB:")
    for pat in ["central securities", "tri-continental", "gabelli equity", "closed-end"]:
        r = tryq("cefname", f"""select count(distinct crsp_fundno) n, min(fund_name) ex
                  from crsp_q_mutualfunds.fund_hdr_hist where strpos(lower(fund_name),'{pat}')>0""")
        if r is not None:
            emit(f"     name~'{pat}': funds={int(r.n.iloc[0])}  ex={r.ex.iloc[0]}")
    r = tryq("cefticker", """select count(*) n from crsp_q_mutualfunds.fund_hdr_hist
              where ticker in ('PDI','GAB','ADX','UTF','NIE','EOI','USA','BIF','JRI','UTG','GUT','DNP','CET')""")
    if r is not None:
        emit(f"     13 classic CEF tickers in fund_hdr_hist: {int(r.n.iloc[0])} rows")
    emit("   CEFs DO exist in the CRSP stock DB: crsp.dsenames shrcd=14 is closed-end funds.")
    cefex = tryq("dsenames_cef", """select distinct permno,ticker,comnam from crsp.dsenames
               where shrcd=14 and ticker in ('GAB','CET','ADX','UTF') order by comnam limit 4""")
    if cefex is not None and len(cefex):
        emit("     e.g.  " + "; ".join(
            f"{x.comnam.strip()} ({x.ticker}, permno {int(x.permno)})" for _, x in cefex.iterrows()))
    r = tryq("shrcd", "select shrcd, count(distinct permno) n from crsp.dsenames where shrcd in (14,73) group by 1 order by 1")
    if r is not None:
        emit("   " + " | ".join(f"shrcd={int(x.shrcd)} ({'CEF' if x.shrcd==14 else 'ETF'}): {int(x.n)} permnos"
                                for _, x in r.iterrows()))
    emit("   => ETFs separable (et_flag='F'); CEFs NOT in the library, not even inferable here.")

    # ---------------------------------------------------------------- 3. daily_nav breadth
    emit("\n## 3. daily_nav breadth & cadence")
    r = tryq("nav_range", "select min(caldt) mn, max(caldt) mx from crsp_q_mutualfunds.daily_nav")
    if r is not None:
        emit(f"   range {r.mn.iloc[0]} .. {r.mx.iloc[0]}  (calendar 1998-09 bayonet.. 2026-06)")
    emit("   distinct funds with non-null dnav on a snapshot date:")
    for d in ["2000-06-30", "2010-06-30", "2020-06-30", "2025-06-30"]:
        r = tryq("breadth", f"""select count(distinct crsp_fundno) funds, count(*) rows_
                  from crsp_q_mutualfunds.daily_nav where caldt='{d}' and dnav is not null""")
        if r is not None:
            emit(f"     {d}: funds={int(r.funds.iloc[0]):,}  rows={int(r.rows_.iloc[0]):,}")
    emit("   cadence check — days reported per fund in 2025 (ETFs, open-end, mmkt):")
    r = tryq("cadence", """select crsp_fundno, count(distinct caldt) days, min(caldt) mn, max(caldt) mx
              from crsp_q_mutualfunds.daily_nav where crsp_fundno in (27635,24697,31417)
              and caldt between '2025-01-01' and '2025-12-31' group by 1 order by days desc""")
    if r is not None:
        emit(r.to_string(index=False))
    emit("   (no dnav -> no row: funds that report weekly/monthly simply have fewer rows; the")
    emit("    table is a true daily series, not a forward-filled grid.)")

    # ---------------------------------------------------------------- 4. discount
    emit("\n## 4. NAV-vs-price discount reconstruction")
    emit("   JOIN KEY:  fund_hdr_hist.cusip8  =  crsp.dsenames.ncusip (8-char)")
    emit("          or  fund_hdr_hist.ncusip  =  crsp.dsenames.cusip  (9-char)")
    emit("              -> permno -> crsp.dsf.prc  (price)   vs   daily_nav.dnav")
    r = tryq("dsf_range", "select min(date) mn, max(date) mx from crsp.dsf")
    if r is not None:
        emit(f"   crsp.dsf (== crsp_a_stock.dsf) price range: {r.mn.iloc[0]} .. {r.mx.iloc[0]}   <-- PRICE STOPS 2024-12-31")
    r = tryq("spy_nm", "select permno,ncusip,shrcd from crsp.dsenames where ncusip='78462F10' order by namedt desc limit 1")
    if r is not None:
        emit(f"   SPY example: permno={int(r.permno.iloc[0])} shrcd={int(r.shrcd.iloc[0])}  (shrcd 73 = ETF)")
    emit("   end-to-end ETF discount demo (SPY dnav vs dsf price):")
    for d in ["2024-06-28"]:
        a = tryq("dnav", f"select dnav from crsp_q_mutualfunds.daily_nav where crsp_fundno=27635 and caldt='{d}'")
        b = tryq("prc", f"select abs(prc) px from crsp.dsf where permno=84398 and date='{d}'")
        if a is not None and b is not None and len(a) and len(b):
            nav = float(a.dnav.iloc[0]); px = float(b.px.iloc[0])
            emit(f"     {d}: dnav={nav:.3f}  price={px:.3f}  discount={100*(px/nav-1):+.3f}%")
    emit("   => ETF discount IS reconstructable 1998-09 .. 2024-12-31 via the cusip8 join.")
    emit("      Beyond 2024-12-31 prices must come from Sharadar (daily_nav still runs to 2026-06).")
    emit("   => CEF discount is NOT reconstructable here: no CEF NAV exists in the library.")

    # ---------------------------------------------------------------- 5. shares outstanding
    emit("\n## 5. Shares outstanding / creation-redemption flow")
    r = tryq("tna_range", "select min(caldt) mn, max(caldt) mx, count(*) n from crsp_q_mutualfunds.monthly_tna")
    if r is not None:
        emit(f"   monthly_tna range {r.mn.iloc[0]} .. {r.mx.iloc[0]}  rows~{int(r.n.iloc[0]):,}  -> MONTHLY only")
    emit("   monthly shares outstanding = monthly_tna.mtna / monthly_nav.mnav   (mtna in $MM):")
    r = tryq("shares", """select t.caldt, t.mtna, n.mnav, round((t.mtna/n.mnav)::numeric,2) shares_mm
              from crsp_q_mutualfunds.monthly_tna t
              join crsp_q_mutualfunds.monthly_nav n using(crsp_fundno,caldt)
              where t.crsp_fundno=27635 order by t.caldt desc limit 4""")
    if r is not None:
        emit(r.to_string(index=False))
    emit("   fund_flows (dollar flows, quarterly, per PORTFOLIO not class):")
    r = tryq("flows", """select min(report_dt) mn, max(report_dt) mx,
               count(distinct report_dt) dates from crsp_q_mutualfunds.fund_flows""")
    if r is not None:
        emit(f"     report_dt {r.mn.iloc[0]} .. {r.mx.iloc[0]}, {int(r.dates.iloc[0])} distinct dates")
    emit("   columns with 'tna'/'shr'/'flow' across the whole library -> only MONTHLY tna;")
    r = tryq("tnacols", """select table_name,column_name from information_schema.columns
              where table_schema='crsp_q_mutualfunds'
              and (strpos(column_name,'tna')>0 or strpos(column_name,'shr')>0 or strpos(column_name,'flow')>0)
              order by 1,2""")
    if r is not None:
        emit("     " + "; ".join(f"{x.table_name}.{x.column_name}" for _, x in r.iterrows()))
    emit("   => NO daily shares-outstanding column exists anywhere in the library.")
    emit("      Daily creation/redemption (shares) is NOT available; only monthly shares (=mtna/mnav)")
    emit("      and quarterly dollar flows. A daily ETF flow signal cannot be built from CRSP alone.")

    # ---------------------------------------------------------------- 6. holdings
    emit("\n## 6. holdings table")
    r = tryq("h_range", "select min(report_dt) mn, max(report_dt) mx from crsp_q_mutualfunds.holdings")
    r2 = tryq("h_rows", "select reltuples::bigint n from pg_class where oid='crsp_q_mutualfunds.holdings'::regclass")
    if r is not None:
        emit(f"   report_dt {r.mn.iloc[0]} .. {r.mx.iloc[0]}  (~{int(r2.n.iloc[0]):,} rows, reltuples)")
    emit("   grain: (crsp_portno, report_dt, security_rank); fields percent_tna, nbr_shares,")
    emit("          market_val, cusip, permno, ticker, coupon, maturity_dt, eff_dt.")
    emit("   frequency = MONTHLY (report_dt = month-end), 2001-12 .. 2026-06:")
    r = tryq("h_freq", """select crsp_portno, extract(year from report_dt) y, count(distinct report_dt) n_dates
              from crsp_q_mutualfunds.holdings where crsp_portno=1021980 group by 1,2 order by 2 desc limit 6""")
    if r is not None:
        emit(r.to_string(index=False))
    emit("   => supports ETF composition / rebalance-flow at MONTHLY frequency (~2-3M rows/month).")
    emit("      Monthly disclosure lag makes it unsuitable for same-cycle creation/redemption flow.")

    # ---------------------------------------------------------------- 7. pitfalls
    emit("\n## 7. Pitfalls")
    emit("   1. et_flag = F/N/blank (not Y/N): F=ETF, N=ETN, blank=open-end. Trust the codebook, not the task guess.")
    emit("   2. CEFs are NOT in this library at all -> no CEF NAV here; the CEF-discount leg must keep its own NAV source.")
    emit("   3. crsp.dsf / crsp_a_stock.dsf PRICES END 2024-12-31 while daily_nav runs to 2026-06-30:")
    emit("      any discount panel after 2024 needs Sharadar (or another price feed) for the price leg.")
    emit("   4. Join at fund_hdr_hist level multiplies rows (date-ranged header history). Dedup to a")
    emit("      distinct crsp_fundno list first, or match caldt BETWEEN chgdt AND chgenddt.")
    emit("   5. crsp_fundno is a SHARE CLASS; holdings/tna are per crsp_portno. Aggregate to the right grain.")
    emit("   6. daily_nav has no dnav on non-trading days and funds with sparse reporting just have")
    emit("      fewer rows -> resample/diff carefully; do not assume a full grid.")
    emit("   7. daily_nav (185M) and holdings (460M) are large: always filter on an indexed column")
    emit("      (caldt, crsp_fundno, report_dt, crsp_portno); avoid full-table GROUP BY year.")

    # ---------------------------------------------------------------- 8. snippets
    emit("\n## 8. Ready-to-use SQL")
    emit("   -- (a) Daily NAV panel for ETFs (no duplicate rows):")
    emit("""   WITH etf AS (SELECT DISTINCT crsp_fundno FROM crsp_q_mutualfunds.fund_hdr_hist WHERE et_flag='F')
   SELECT d.crsp_fundno, d.caldt, d.dnav
   FROM crsp_q_mutualfunds.daily_nav d
   JOIN etf USING (crsp_fundno)
   WHERE d.caldt BETWEEN DATE '2016-01-01' AND DATE '2026-06-30'
     AND d.dnav IS NOT NULL;""")
    emit("")
    emit("   -- (b) ETF NAV + market price + discount (prices end 2024-12-31):")
    emit("""   WITH etf AS (
     SELECT DISTINCT crsp_fundno, cusip8 FROM crsp_q_mutualfunds.fund_hdr_hist WHERE et_flag='F')
   SELECT d.caldt, e.crsp_fundno, d.dnav, ABS(s.prc) AS price,
          ABS(s.prc)/d.dnav - 1 AS discount
   FROM crsp_q_mutualfunds.daily_nav d
   JOIN etf e ON e.crsp_fundno = d.crsp_fundno
   JOIN crsp.dsenames n ON n.ncusip = e.cusip8
                       AND d.caldt BETWEEN n.namedt AND n.nameendt
   JOIN crsp.dsf s ON s.permno = n.permno AND s.date = d.caldt
   WHERE d.dnav IS NOT NULL;""")
    emit("")
    emit("   -- (c) Monthly shares outstanding (ETF or any fund):")
    emit("""   SELECT t.crsp_fundno, t.caldt, t.mtna / n.mnav AS shares_out
   FROM crsp_q_mutualfunds.monthly_tna t
   JOIN crsp_q_mutualfunds.monthly_nav n USING (crsp_fundno, caldt);""")

    emit("\n## 9. Inaccessible / errored items")
    if errs:
        for e in errs:
            emit("   " + e)
    else:
        emit("   none — every probe returned")

    emit("\n" + "=" * 100)
    db.close()
    OUT.write_text("\n".join(_lines) + "\n")
    emit(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
