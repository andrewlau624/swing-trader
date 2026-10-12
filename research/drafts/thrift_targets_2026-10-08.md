# Thrift conversion targets (DL-G27 made actionable), 2026-10-08

Research only. No account opened, no bank contacted. State of residence unknown: every list is filterable by state
(`data/research/thrift/thrift_all_screened.csv`, 155 mutual savings institutions, column `STALP`).

## 1. DL-G27 recheck (`data/research/program/goal_dl27_deals.csv`, n=18)
- Day-1 close vs $10: mean +19.0%, median +21.2%, hit 83%. Reproduces.
- **By era it is not stable**: 2019-22 (11 deals) median +28.9%, 11/11 positive; **2023-25 (7 deals) median +2.3%, mean +6.2%, 4/7 positive**, worst -9.2%.
  The headline +20% is a 2021-22 hot-IPO number. Plan on a low-single-digit to high-single-digit central case, not +20%.
- Standard conversions (14) median +27.4% vs four likely MHC second-steps (GBNY, NECB, BVFL, MBBC; classified from filer
  history, not checked in EDGAR here) median +1.4%. Minority-offering/second-step deals are a different, weaker trade; the
  money is in standard mutual-to-stock conversions. Sample is tiny and survivor-only, so this is a pattern, not an estimate.
- Frequency from EDGAR full-text search ("eligible account holders", S-1, `s1_conversions.csv`): 2022: 3, 2023: 7,
  2024: 8, 2025: 7 (incl. second steps), 2026 to Oct: 6. About 6-8 a year, of which ~4-6 standard.
- Priority/allocation (general structure of the plans, not verified against a specific prospectus here): tier 1 eligible
  account holders (balance on the eligibility record date, usually >= 12 months before the offering), tier 2 tax-qualified
  plans/ESOP, tier 3 supplemental eligible (later record date), tier 4 other members/voting depositors, then community
  (local residents first). If oversubscribed, plans normally fill each eligible holder up to a small floor (commonly 100
  shares or the amount ordered, whichever is less) and pro-rate the rest by deposit size. **A small depositor realistically
  gets about 100 shares (~$1,000), not $2,000.** Check each prospectus.
- Live now (useless to you, record dates passed): Hometown Financial Group (MA, S-1 2026-09-10), MFB Bancorp (IL,
  2026-09-14); Narragansett Bancorp (MA/RI, 2026-06-12) and Rhinebeck/Columbia second steps filed Mar 2026.

## 2. Candidate list (standard mutual conversions)
Source: FDIC BankFind API, `ACTIVE:1 AND MUTUAL:1`, 222 institutions (cached `fdic_mutual.csv`; field `MUTUAL`), Jun 2026 call
report. Screen: assets $100M-$3B, ROA > 0.1%, equity/assets >= 6% (155 pass). Score (max 6): size 150M-1.2B (+2, else +1),
ROA >= 0.4 (+1), equity/assets 8-22% (+1), >= 3 offices (+1), savings-type charter (+1); ties broken by closeness to $500M.
**This is a base-rate heuristic, not a prediction.** Annual conversion hazard is ~2-3% for any given mutual and I found no
public signal (board actions, charter-conversion filings) that moves it much. Excluded: names that already filed an S-1 in
2022-26 (list in `s1_conversions.csv`). Online-open column is a homepage keyword check (`y` = an open-account/apply-online
link seen, `n/s` = none seen, `?` = site fetch failed); **min deposit was not machine-readable on any site, so it is `?`
(commonly $25-$100 for a basic savings account; confirm on the bank page)**. Out-of-state acceptance is not determined for
any bank; do not assume it. Many mutuals restrict accounts to residents of their counties, and the community-offering
priority is local.

| # | Institution | State | Assets $M | ROA | Eq/Assets | Offices | Online open | Min dep | Website |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Ambler Savings Bank | PA | 502 | 0.6% | 12% | 7 | n/s | ? | https://www.amblersav.com |
| 2 | Hancock County Savings Bank, F.S.B. | WV | 508 | 1.0% | 18% | 3 | y | ? | https://www.hcsbank.com |
| 3 | First Federal Savings Bank of Lincolnton | NC | 486 | 0.5% | 17% | 4 | n/s | ? | https://www.ffsb-nc.com |
| 4 | Seamen's Bank | MA | 478 | 0.6% | 12% | 5 | y | ? | https://seamensbank.com |
| 5 | Cross County Savings Bank | NY | 525 | 0.5% | 13% | 6 | n/s | ? | https://www.crosscounty.com |
| 6 | Essex Bank | CT | 537 | 1.1% | 14% | 8 | y | ? | https://www.essex.bank |
| 7 | United Savings Bank | PA | 461 | 0.8% | 18% | 6 | ? | ? | https://www.unitedsavingsbank.com |
| 8 | Eureka Savings Bank | IL | 436 | 0.9% | 21% | 5 | y | ? | https://www.eurekasavings.com |
| 9 | Home Bank SB | IN | 433 | 0.6% | 9% | 6 | y | ? | https://www.homebanksb.com |
| 10 | First Federal Savings Bank | IL | 422 | 0.4% | 11% | 11 | y | ? | https://ffsbweb.com |
| 11 | First Federal Bank & Trust | WY | 621 | 0.7% | 11% | 3 | n/s | ? | https://www.efirstfederal.bank |
| 12 | Evergreen Federal Bank | OR | 622 | 0.8% | 13% | 6 | y | ? | https://www.evergreenfederal.bank |
| 13 | Big Horn Federal Savings Bank | WY | 400 | 0.9% | 11% | 6 | n/s | ? | https://www.bighornfederal.com |
| 14 | Volunteer Federal Savings Bank | TN | 397 | 0.9% | 10% | 6 | y | ? | https://www.volfed.com |
| 15 | Mt. McKinley Bank | AK | 635 | 0.7% | 17% | 5 | y | ? | https://www.mtmckinleybank.com |
| 16 | San Luis Valley Federal Bank | CO | 390 | 1.1% | 17% | 3 | y | ? | https://www.slvfed.bank |
| 17 | BankGloucester | MA | 387 | 0.4% | 8% | 3 | n/s | ? | https://bankgloucester.com |
| 18 | Phoenixville Federal Bank and Trust | PA | 648 | 0.8% | 12% | 7 | y | ? | https://www.phoenixfed.com |
| 19 | The Milford Bank | CT | 652 | 0.7% | 9% | 6 | n/s | ? | https://www.milfordbank.com |
| 20 | First Federal Savings and Loan Association | MS | 381 | 0.4% | 9% | 6 | y | ? | https://www.firstwithus.com |
| 21 | The North Country Savings Bank | NY | 373 | 1.3% | 14% | 8 | y | ? | https://northcountrysavings.bank |
| 22 | First Shore Federal Savings and Loan Association | MD | 367 | 0.8% | 17% | 7 | n/s | ? | https://www.firstshorefederal.com |
| 23 | Artisans' Bank | DE | 718 | 0.5% | 9% | 13 | y | ? | https://www.artisansbank.com |
| 24 | Greenville Savings Bank | PA | 343 | 0.7% | 13% | 3 | n/s | ? | https://www.greenvillesavings.com |
| 25 | Franklin Bank | NJ | 334 | 0.7% | 9% | 8 | y | ? | https://www.franklinbnk.com |
| 26 | Citizens Savings Bank | LA | 329 | 1.3% | 14% | 5 | n/s | ? | https://www.citizenssb.com |
| 27 | Altoona First Savings Bank | PA | 329 | 0.9% | 14% | 5 | y | ? | https://www.altoonabank.com |
| 28 | Savers Co-operative Bank | MA | 783 | 0.7% | 10% | 7 | y | ? | https://www.saversbank.com |
| 29 | The Brattleboro Savings and Loan Association | VT | 296 | 0.8% | 10% | 5 | n/s | ? | https://www.brattbank.com |
| 30 | First Federal Savings and Loan Association | OH | 294 | 0.5% | 14% | 6 | y | ? | https://www.firstfedohio.com |
| 31 | Skowhegan Savings Bank | ME | 855 | 1.6% | 14% | 13 | y | ? | https://www.skowhegan.com |
| 32 | Community Partners Savings Bank | IL | 288 | 0.7% | 10% | 6 | y | ? | https://www.communitypartnerssb.com |

## 3. Existing MHCs with public minority (second-step candidates), from 10-K full-text search, 2026
Second steps give depositors of the MHC bank subscription rights, but the trade is weaker (above) and the existing
minority holders are the pre-positioned alternative (buy the minority stock at its market price; exchange ratio set at the
second step). Not verified by me beyond the 10-K hit. Tickers: GCBC (NY, MHC majority), PBFS (NY), BSBK (NJ), KFFB (KY),
SNNF (NY, S-1 filed 2025-06), RBKB (NY, S-1 2026-03), LSBK (done 2025), PBHC (Pathfinder, NY), AFBI (GA), MBBC (done).
TFSL (OH, $17B MHC) and CFSB, OFED, WAKE exist from my memory but were not in the search hits: unverified. Check `mhc_10k.csv`.

## 4. Expected value
Inputs: hazard h = 2.5%/yr per mutual (6 standard conversions / ~220); account must exist before the eligibility record date
(about 1+ year before the offering), so an account opened today starts to count for offerings from ~late 2027. Fill ~$1,000
(100 shares; $2,000 only if undersubscribed). Return on $1,000 per deal: central +8% (era-weighted, 2023-25 median +2%),
bear +2%, bull +20%. Cost: rate gap g = 1.5pp on the parked deposit (thrift savings vs a money fund), plus a small opening
balance of $100-250 per account. Each deal also needs $1,000 free cash at the offering.
Formula (steady state, after the ~1.5 yr lag): EV/yr = N x h x fill x return - N x d x g.

| capital | accounts N (d = $200) | deals/yr (N x h) | EV/yr bear / central / bull | cost/yr | net central, % of capital |
|---|---|---|---|---|---|
| $2.3k | 4 (parks $800; leaves $1k+ for a fill) | 0.10 | $2 / $8 / $20 | $12 | about -0.2%: ~0 (no real EV) |
| $10k | 15 ($3k parked) | 0.38 | $8 / $30 / $75 | $45 | about -0.1% to +0.5%: marginal |
| $25k | 40 ($8k parked) | 1.0 | $20 / $80 / $200 | $120 | about 0%: marginal; +1% bull |

At the DL-G27 era numbers (+20% on $2,000, 2.6 deals/yr) the yield was ~+35% at $2.3k, but that assumed the user is
already eligible at ~2.6 deals/yr; **a portfolio of N accounts gets N x 2.5% deals, so a handful of accounts yields ~0.1-0.4
deals a year.** To reach 2-3 eligible deals a year you need ~60-100 accounts, which breaks on minimum deposits, state
residency rules, and time. The edge is real per deal (about $80-$200) but the access cost dominates at $2.3k.
Per conversion at $1,000: central +$80, bull +$200, bear +$20 (before the opening-balance tie-up).

## 5. Caveats
- Per-deal numbers are 18 survivor deals dominated by 2021-22; the 2023-25 half is near zero.
- Concentrated-state prior: converters cluster in MA, NJ, LA, OH, IL, NY, PA. If you live in one, you have a local
  community-offering priority and many more branches to deposit in (order the table by state).
- One account per person (or per "associated" group) per bank; multiple ownership types at one bank may not add
  priority and plans cap per-person and per-family purchases (often $300k-$500k, irrelevant here).
- IRA purchases in conversions usually need the bank's own IRA or an IRA self-directed broker; not checked.
- FDIC `MUTUAL` flag can lag a completed conversion: confirm the bank is still mutual before opening.
- Taxable gain unless held in a Roth-eligible vehicle; short-term gains if flipped at the open.
