"""WRDS OptionMetrics profiling (READ-ONLY). Answers whether two mechanisms are testable at $0:
  (A) signed dealer gamma / open-interest concentration on the UNDERLYING (needs per-contract OI + gamma)
  (B) volatility surface (skew / term structure) via optionm.vsurfdYYYY

Writes a self-contained report to data/research/wrds_recon/optionm_profile.txt.

Usage: .venv/bin/python -m research.sim.wrds_optionm_profile

Data notes learned while writing this:
  * opprcd/vsurfd are PER-YEAR tables (optionm.opprcd2020); there is no bare optionm.opprcd.
  * wrds.Connection.raw_sql does pyformat substitution, so a literal '%' in SQL breaks it.
    Use chr(37) for '%' (e.g. issue_type = chr(37), the ETF code) and never LIKE '%%x%%'.
  * Some optionm views (option, exchange, security_name) resolve to schema optionm_europe and raise
    InsufficientPrivilege; they are skipped.
Nothing is written except the report file. SELECT-only.
"""
import pathlib, time, traceback
import pandas as pd
import wrds

OUT = pathlib.Path("data/research/wrds_recon/optionm_profile.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)
COVER_YEARS = [1996, 2010, 2020, 2025]
MID_YEAR_DATE = {1996: "1996-06-28", 2010: "2010-06-30", 2020: "2020-06-30", 2025: "2025-06-30"}
SPY, QQQ, IWM, AAPL, IBM = 109820, 107899, 106445, 101594, 106276
SAMPLE_DATE = "2020-06-30"

_LINES = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    _LINES.append(s)

def head(title):
    P("")
    P("=" * 100)
    P(title)
    P("=" * 100)

def q(db, sql, label, limit=30, quiet=False):
    """Run one bounded query; never raise. Returns DataFrame or None."""
    if not quiet:
        P("")
        P("-- " + label)
        P("SQL: " + " ".join(sql.split()))
    t0 = time.time()
    try:
        df = db.raw_sql(sql)
    except Exception as e:
        P(f"ERROR after {time.time()-t0:.1f}s: {type(e).__name__}: {str(e)[:300]}")
        return None
    P(f"rows={len(df)}  ({time.time()-t0:.1f}s)")
    if len(df):
        with pd.option_context("display.max_columns", 60, "display.width", 240, "display.max_colwidth", 40):
            P(df.head(limit).to_string(index=False))
    return df


def main():
    U = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
    db = wrds.Connection(wrds_username=U)

    head("OptionMetrics profile  (WRDS, read-only)  " + time.strftime("%Y-%m-%d %H:%M"))

    # ---------------------------------------------------------------- 0. orientation
    head("0. Orientation: per-year tables, no bare opprcd")
    tbls = db.list_tables(library="optionm")
    P(f"optionm library: {len(tbls)} tables.")
    P("opprcd* years present: " + ", ".join(sorted(t for t in tbls if t.startswith("opprcd"))))
    P("vsurfd* years present: " + ", ".join(sorted(t for t in tbls if t.startswith("vsurfd"))))
    P("borrate* years present: " + ", ".join(sorted(t for t in tbls if t.startswith("borrate"))))
    P("reference tables: " + ", ".join(t for t in tbls if not any(c.isdigit() for c in t)))
    q(db, "select * from optionm.opprcd2020 limit 1", "opprcd column list (2020)")

    # ---------------------------------------------------------------- 1. coverage
    head("1. Coverage in opprcdYYYY (distinct secid / distinct date)")
    P("Full-year DISTINCT scans are 17-34s each; four years only. Everything else below is bounded to one date.")
    for y in COVER_YEARS:
        q(db, f"select count(distinct secid) as n_secid, count(distinct date) as n_dates, "
              f"min(date) as first_date, max(date) as last_date from optionm.opprcd{y}",
          f"opprcd{y} coverage")

    head("1b. Universe mix on one representative mid-year session (join to securd)")
    P("securd.issue_type: '0'=common/ordinary, chr(37)='%'=ETF, 'A'=index(NAV/intraday), 'F'=fund, etc.")
    P("securd.index_flag=1 mixes true indices AND index ETF NAV/intraday records -> NOT an ETF flag.")
    for y in COVER_YEARS:
        d = MID_YEAR_DATE[y]
        q(db, f"""with u as (select distinct secid from optionm.opprcd{y} where date='{d}')
select coalesce(s.issue_type,'(unmatched)') as issue_type, s.index_flag, count(*) as n_secid
from u left join optionm.securd s on s.secid=u.secid group by 1,2 order by n_secid desc""",
          f"opprcd{y} @ {d}: secids by issue_type / index_flag", limit=12)

    # ---------------------------------------------------------------- 2. OI completeness + gamma
    head("2. open_interest / gamma / delta completeness in opprcd (bounded to one date)")
    for d, tbl in [("2020-06-30", "optionm.opprcd2020"), ("2025-06-30", "optionm.opprcd2025")]:
        q(db, f"""select count(*) as n_rows,
 count(open_interest) as n_oi_notnull,
 sum((open_interest>0)::int) as n_oi_gt0,
 sum((open_interest=0)::int) as n_oi_zero,
 sum((open_interest is null)::int) as n_oi_null,
 sum((gamma  is not null)::int) as n_gamma_notnull,
 sum((delta  is not null)::int) as n_delta_notnull,
 sum((impl_volatility is not null)::int) as n_iv_notnull,
 count(distinct secid) as n_secid
 from {tbl} where date='{d}'""", f"completeness @ {d}")

    # ---------------------------------------------------------------- 3. signed-gamma ingredients
    head("3. Signed-gamma ingredients: OI x gamma split by cp_flag (one secid, one date)")
    P(f"Underlying secid {SPY} (SPY ETF). strike_price is in 1/1000 USD (235000 = $235).")
    P("Raw ingredients dealers need: OI and gamma (and delta for dollar-gamma / charm) per contract.")
    q(db, f"""select cp_flag, count(*) as n_contracts,
 sum(open_interest)                        as tot_oi,
 sum(open_interest*gamma)                  as oi_x_gamma,
 sum(open_interest*gamma*delta)            as oi_x_gamma_x_delta,
 sum(open_interest*gamma*contract_size)    as dollar_gamma_raw
 from optionm.opprcd2020
 where secid={SPY} and date='{SAMPLE_DATE}' and gamma is not null
 group by cp_flag order by cp_flag""",
      "SPY OI x gamma by cp_flag", limit=10)
    q(db, f"""select exdate, cp_flag, strike_price, open_interest, gamma, delta, contract_size
 from optionm.opprcd2020
 where secid={SPY} and date='{SAMPLE_DATE}' and gamma is not null and open_interest>0
 order by exdate, cp_flag, strike_price limit 15""",
      "SPY per-contract ingredients (strike-level sample)", limit=15)
    q(db, f"""select date, cp_flag, count(*) as n, sum((gamma is not null)::int) as n_gamma
 from optionm.opprcd2020 where secid={SPY} and date between '{SAMPLE_DATE}' and '{SAMPLE_DATE}'::date + 5
 group by date, cp_flag order by date, cp_flag limit 12""",
      "gamma population for SPY across a few sessions", limit=12)

    # ---------------------------------------------------------------- 4. ETF / index presence
    head("4. ETF / index presence (the program trades ETFs)")
    P("ETF = securd.issue_type = chr(37). A ticker can map to several secids (ETF vs index-NAV copies):")
    q(db, "select * from optionm.securd where secid in "
          f"({SPY},{QQQ},{IWM},{AAPL},{IBM},100155,115101,100473) order by ticker, secid",
      "securd rows for known tickers", limit=20)
    q(db, "select count(*) as n_etf_secids from optionm.securd where issue_type = chr(37)",
      "total ETF-designated secids in securd")
    for y in COVER_YEARS:
        d = MID_YEAR_DATE[y]
        q(db, f"""with u as (select distinct secid from optionm.opprcd{y} where date='{d}')
 select count(*) as n_etf_secid_present
 from u join optionm.securd s on s.secid=u.secid where s.issue_type = chr(37)""",
          f"ETFs present in opprcd{y} @ {d}", limit=5)

    # ---------------------------------------------------------------- 5. vsurf
    head("5. optionm.vsurfdYYYY: per-delta implied-vol surface (skew + term structure)")
    q(db, "select * from optionm.vsurfd2020 limit 3", "vsurfd column list (2020)")
    q(db, f"""select secid, date, days, cp_flag, delta, impl_volatility, impl_strike
 from optionm.vsurfd2020
 where secid={SPY} and date='{SAMPLE_DATE}' and days in (30,91,182) and impl_volatility is not null
 order by days, delta limit 40""",
      "SPY 30/91/182-day volatility surface (delta ladder) -> skew & term structure", limit=40)
    q(db, f"""select days, cp_flag,
 count(*) as n_points, min(delta) as min_delta, max(delta) as max_delta,
 min(impl_volatility) as min_iv, max(impl_volatility) as max_iv
 from optionm.vsurfd2020 where secid={SPY} and date='{SAMPLE_DATE}'
 group by days, cp_flag order by days, cp_flag limit 30""",
      "SPY surface shape by tenor", limit=30)

    # ---------------------------------------------------------------- 6. join path
    head("6. Join path: secid -> ticker (secnmd/securd) and secid -> permno (opcrsphist)")
    q(db, "select * from wrdsapps_link_crsp_optionm.opcrsphist limit 5",
      "opcrsphist column list (secid -> permno link)")
    q(db, "select count(*) as n_rows, count(distinct secid) as n_secid from wrdsapps_link_crsp_optionm.opcrsphist",
      "opcrsphist size")
    q(db, "select score, count(*) as n from wrdsapps_link_crsp_optionm.opcrsphist group by score order by n desc",
      "opcrsphist score distribution (1=best match)")
    q(db, """select l.secid, l.permno, l.score, n.ticker, n.shrcd, n.exchcd, n.comnam
 from wrdsapps_link_crsp_optionm.opcrsphist l
 left join crsp.dsenames n on n.permno=l.permno
 where l.secid in (109820,107899,106445,101594) and l.score=1
 order by l.secid limit 20""",
      "worked join: secid -> permno -> crsp.dsenames (shares/name). shrcd 73 = ETF, 11 = US common", limit=20)
    q(db, "select secid, ticker, cusip, class, issue, issuer from optionm.secnmd "
          "where secid in (109820,107899,106445) order by secid limit 20",
      "secnmd secid -> ticker/issuer (historical names)")

    # ---------------------------------------------------------------- 7. bonus table
    head("7. optionm.opvold (daily option volume / OI, one row per secid-date-cp_flag)")
    q(db, "select * from optionm.opvold limit 5", "opvold column list")

    # ---------------------------------------------------------------- deliverables
    head("8. READY-TO-USE SQL: per-secid-per-date OI / gamma aggregate (dealer-gamma ingredients)")
    P("""
-- One row per (secid, date): call/put OI, OI*gamma and OI*gamma*delta (the signed dealer-gamma inputs).
-- Bounded to a single session with the indexed `date =` predicate. strike/contract scaling is left raw;
-- multiply OI*gamma*contract_size*(spot^2)*0.01 for the conventional dollar-gamma per 1% move.
select secid,
       sum(case when cp_flag='C' then open_interest else 0 end)                    as oi_call,
       sum(case when cp_flag='P' then open_interest else 0 end)                    as oi_put,
       sum(case when cp_flag='C' then open_interest*gamma else 0 end)              as oi_gamma_call,
       sum(case when cp_flag='P' then open_interest*gamma else 0 end)              as oi_gamma_put,
       sum(open_interest*gamma*delta)                                              as oi_gamma_delta_net,
       sum(open_interest*gamma*contract_size)                                      as dollar_gamma_raw
from optionm.opprcd2020
where date = '2020-06-30'          -- keep an equality on the indexed date column
  and gamma is not null
  and cp_flag in ('C','P')
group by secid;

-- Per-strike/expiry detail for one name:
select exdate, cp_flag, strike_price/1000.0 as strike, sum(open_interest) as oi,
       sum(open_interest*gamma) as oi_gamma
from optionm.opprcd2020
where secid = 109820 and date = '2020-06-30' and gamma is not null
group by exdate, cp_flag, strike_price
order by exdate, cp_flag, strike_price;
""")

    head("9. Pitfalls / conventions")
    for t in [
        "opprcd/vsurfd are per-year tables (opprcd2020). There is NO bare optionm.opprcd.",
        "raw_sql does pyformat substitution: a literal '%' breaks it. Use chr(37) for '%'; never LIKE '%%x%%'.",
        "open_interest is ~100% populated (end-of-day, incl. non-traded contracts); gamma/delta/IV only on rows with a computed greek (~83% in 2020).",
        "strike_price is in 1/1000 USD (235000 = $235); contract_size = 100. Divide/bill accordingly.",
        "delta sign: calls positive, puts negative (put delta ladder runs -90..-10, calls +10..+90).",
        "ETF vs index: use securd.issue_type = chr(37) for the tradable ETF. index_flag=1 also covers index-NAV/intraday records (SPY has secid 100155 intraday, 115101 NAV, 109820 the ETF).",
        "A ticker maps to multiple secids over time; join links on secid, not ticker.",
        "opcrsphist holds >1 row for a few secids; filter score=1 (or dedupe) before joining to crsp.dsenames.",
        "opprcd is OptionMetrics-filtered (wide/stale quotes dropped) - fine for OI/gamma aggregates, not raw NBBO microstructure.",
        "For a year scan use `where date = '...'` (indexed) or a date range; count(distinct secid) over a full year is 17-34s, do not loop it over many years.",
        "Inaccessible: optionm.option / optionm.exchange / optionm.security_name -> InsufficientPrivilege (resolve to schema optionm_europe). cboe.* denied (prior recon).",
    ]:
        P(" - " + t)

    head("10. Verdict")
    P("""
(A) Signed dealer gamma / OI concentration on the UNDERLYING: TESTABLE. Per-contract open_interest is
    present and complete, gamma and delta are populated on ~83% of rows, and cp_flag splits calls/puts.
    All ingredients exist with no extra purchase (optionm.opprcdYYYY). Note this is OptionMetrics-filtered
    EOD data, not raw OPRA - adequate for OI/gamma aggregates.
(B) Volatility surface (skew, term structure): TESTABLE. optionm.vsurfdYYYY gives a per-delta (delta
    ladder -90..90) implied vol for fixed tenors (days), i.e. skew and term structure directly, 1996-2025.
ETF availability: yes - SPY secid 109820, QQQ 107897? (107899), IWM 106445, plus ~6,783 ETF secids
    (securd.issue_type = chr(37)); the live-traded ETFs are all present.
Join path: optionm.opprcdYYYY.secid -> optionm.securd.secid / optionm.secnmd.secid (ticker, index_flag,
    issue_type) and -> wrdsapps_link_crsp_optionm.opcrsphist.secid (permno, score) -> crsp.dsenames(permno)
    (shrcd, exchcd, comnam). Underlying prices also directly in optionm.secprd.
""".replace("107897? (107899)", "107899"))

    OUT.write_text("\n".join(_LINES) + "\n")
    P(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
