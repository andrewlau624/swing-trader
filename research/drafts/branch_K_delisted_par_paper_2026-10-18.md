# Branch K - $25-par paper forcibly delisted while the claim survives (2026-10-18)
Descriptive only. No backtest, no N, nothing registered. Scratch scripts: scratchpad k2..k9.py (Sharadar tickers/prices, WRDS FISD/TRACE).

## Verdict: CEILING-KILL + DATA-KILL (no pre-registration draft written)
The mechanism is real and documented (AmTrust, Charah), but (a) the dislocation is in the ANNOUNCEMENT gap, before the delisting, (b) there is no
post-delisting price history anywhere in hand (TRACE has none for these), (c) genuine non-bankrupt events are ~0.5-1/yr, (d) the bankrupt ones are a default lottery.

## Task 1 - event count (Sharadar tickers, FISD)
- Sharadar SEP/SFP delisted $25-paper: 1,138 (ETD 311, Domestic Preferred 716, ADR pref 66, CEF pref 42, Canadian pref 3), lastpricedate 2015-2026 (feature table: scratchpad k_feat.pkl). Sharadar has NO delisting reason.
- Filter "last close < 20 after a 60d high >= 22" (distress-type exit): 14 names, 2015-2026 (~1.2/yr): MHR-PD, AFFS/AFFT (AmTrust), LTSF/K/H/L (Ladenburg),
  HMLPF, FRCHL/FRCIL, FBYDP1, AQNU, FOSLL, TFSA. This filter misses issues delisted near par (e.g. AmTrust-style delist at 17-18 is caught; going-dark at 24 is not).
- Matched 246 ETD tickers to FISD by 9-digit CUSIP (fisd_mergedissue.complete_cusip); FISD `active_issue='Y'` / amount_outstanding>0 for only 33. FISD action_type E/B/IM
  (early redemption / bought / matured-type) explains most of the rest = acquired/redeemed, NOT events. Of the 33 still-outstanding after the Sharadar
  exit, sorted by cause (cause read from names/prices, then confirmed only where marked):
  - Voluntary delist/deregister, no bankruptcy (THE event): AmTrust AFFS/AFFT 2019-02 (confirmed, 8-K); Charah CHRB 2023-04 (confirmed, NYSE section 802.01B market-cap
    standard); possibly Argo Blockchain ARBKL 2025-12 (UK restructuring; UNVERIFIED), Fossil FOSLL 2025-11 (UNVERIFIED), Terra Income Fund 6 TFSA 2026-03 (UNVERIFIED), Falcon's Beyond pref (UNVERIFIED).
  - Bankruptcy / default (different class, lottery): iMedia IMBIL 2023 (FISD defaulted=Y, last 0.98), Office Properties Income Trust OPIRL 2025 (defaulted=Y, 3.90), QVC QVCCQ/QVCDQ 2026 (defaulted=Y, ~11), First Republic prefs 2023 (1.96-1.98), Magnum Hunter pref 2015 (1.76).
  - Acquired/ticker change, issue stayed (not events): Ladenburg LTS* (Advisor Group deal; March-2020 drop was COVID, UNVERIFIED), Qwest CTDD/CTBB (FISD action X), Algonquin AQNA/AQNU, Zions, Travel Centers, Cowen, Goldman GSF, others at ~25.
- So clean voluntary-delist events with a surviving claim: ~2 verified in 11 years, <= ~6 even if every UNVERIFIED name counts (~0.2-0.5/yr). Not 1-8/yr.

## Task 2 - what happened next
- AmTrust (verified): 2019-01-18 board approves delisting 6 pref series + two 2055 sub notes (8-K https://www.sec.gov/Archives/edgar/data/1365555/000136555519000007/form8knysedelistinganddire.htm);
  Form 25 filed 01-28, effective ~02-07; securities "remain outstanding obligations". Plaintiffs allege the prefs fell almost 40% the next trading day (Martinek v. AmTrust; allegation, not a result).
  Sharadar AFFS closes: 14.46 (01-29) -> 18.10 (02-06) -> 17.55 (02-07, last print), i.e. most of the drop and a +20% partial rebound happened ON the exchange, before the last print. Last-250d range 14.08-24.99.
  After 02-07: OTC (OTCMarkets/Quantum list AFFS/AFFT as OTC; OTC Markets page lists AFFT on Expert Market, ~7yrs stale). Callable at par from 2020-06-18 / 2020-09-16. Outcome (called? paid through?) NOT FOUND: no redemption notice in two searches; FISD still shows amount_outstanding 150,000/135,000 (FISD flag, not proof). Coupon continuation UNVERIFIED.
  Entry at the last exchange print (17.55) vs par 25 would be -30% price with a 7.25% coupon (~10.3% current yield quoted by a Seeking Alpha piece in 2019, opened as search snippet only); that is a yield story, not a forced-selling snap-back, and tail risk is the sub-note/insurer credit (A- rated claim in same snippet).
- Charah (verified): NYSE suspended CHRA and CHRB 2023-04-03 (market cap < $15M, ICE release https://ir.theice.com/press/news-details/2023/NYSE-to-Suspend-Trading-Immediately-in-Charah-Solutions-Inc.-CHRA-and-Commence-Delisting-Proceedings/default.aspx); OTC Pink from 04-04.
  Sharadar CHRB: 13.56 (03-17) -> 9.40 (03-31) -> 10.03 (04-03, last); max-250d 23.85. $135M notes due 2026-08-31 8.5%. Merger agreement signed 2023-04-16 (SER Capital); 100.5% change-of-control call was available but whether used UNVERIFIED. Search snippet says a 2026-08-31 press release reports refinancing the 8.50% notes, i.e. they appear to have stayed outstanding to maturity (UNVERIFIED, single snippet). If true, a buyer at ~10 earned par = +150% plus coupons; but the entry price on OTC is unobserved and the move from 24 to 10 happened pre-delisting.
- TRACE (WRDS trace.trace_enhanced, non-commission filter) for 14 CUSIPs (AFFS, AFFT, CHRB, IMBIL, OPIRL, ARBKL, FOSLL, LTS*, QVC*, TFSA): ONLY new-issue week prints (2015-2021 offering dates), ZERO post-delisting prints. Exchange-listed $25 retail paper reports to TRACE only around primary distribution; post-delisting OTC trades are not in the file. => per-event OTC price path cannot be built from anything in hand. (query: scratchpad k8.py; output k_trace.pkl)
- Median dislocation: not measurable. n=2 verified; both show the large move before the last exchange print.

## Task 3 - access (all UNVERIFIED unless noted)
- Schwab's OTC page (https://www.schwab.com/stocks/understand-stocks/otc-markets, search snippet) says Expert/Grey securities "are not quoted by broker-dealers". It does not state whether they are buyable; sell-only/closing-only practice, IRA eligibility, and whether a Pink baby bond (CHRB) is buyable in the Roth were NOT sourced. Expert Market (AFFT) is the tier most likely closed to retail buying.
- Preferreds/baby bonds also have no clean Schwab symbol resolution (CUSIP needed, per CLAUDE.md 2026-10-10). Spreads on OTC Pink paper: no data; expect >> exchange quotes.

## Constrained seller: who is it, actually?
- PFF/PGX/PFFD-type ETFs hold only exchange-listed index members, so they must sell on delisting; but I could not verify holdings of AFFS/AFFT/CHRB in them (no PIT holdings, same as PREF-INDEX) and baby-bond-heavy ETFs (e.g. income ETFs) are not documented here. The seller exists in principle; its footprint is unobservable.
- Retail platforms: restriction to sell-only is a plausible force (UNVERIFIED).
- Both verified cases show the forced move was already priced between announcement and the last exchange day; no "OTC overshoot" can be shown without OTC prices.

## Cards
### K1 Voluntary-delist baby bond with surviving claim - KILL
- Mechanism: listing removal forces ETF/institutional/platform sellers; claim unchanged. Evidence: AmTrust 8-K, Charah NYSE release; Sharadar paths above.
- Frequency: ~0.2-1/yr. Payoff: AmTrust entry 17.55 -> par 25 (+42%) IF called/paid (UNVERIFIED); Charah ~10 -> 25 (+150%) IF paid (UNVERIFIED). Downside: insurer/sub-note and microcap credit (CHRB market cap < $15M; 2023 notes were priced at 10 for a reason), illiquid, wide OTC spread, possibly closed to purchase.
- Ceiling at $10k: 0.5/yr x ~+40% x 10-20% of account (OTC paper, thin) x 50% capture = +0.1-0.2pp/yr (even 1/yr x 100% = +2pp). $2.3k and $25k: same percent. Far below +8pp.
- Data: Sharadar+FISD give the event list but no post-delisting prices; TRACE has none; would need OTC Markets/FINRA OTC history (paid) or manual quotes. Capital lock: months to years (CHRB 3.3 yrs to maturity, AFFS callable only from 2020).
- Verdict: ceiling-kill; plus data-kill (no way to measure the dislocation) and access-unknown. Not registered.

### K2 Bankrupt/defaulted $25 paper (IMBIL, OPIRL, QVC, FRC) - DROP
- Default lottery (recovery on unsecured $25 paper, e.g. FRC prefs wiped to ~2, OPIRL 3.9, QVC ~11); same class as post-bankruptcy equity/DELIST-31 (NEXT.md:1252, 3,156 episodes net abn -2.72%, median -3.02%). No par anchor.

### Dropped
- Common-stock delisting/25-NSE: I22 (NEXT.md:300), DELIST-31 (NEXT.md:1252). $25 fallen-angel selling: branch D (~0.1pp). Merger/redemption delistings: not events (FISD action E/B/IM = 214 of 246 matched).

## Pre-registration draft
Not written: gate not met (no large measured median dislocation; n=2 verified; no post-delisting prices). Reopen only with an OTC price history source for ETD/pref CUSIPs plus a verified Schwab/Roth purchase path for Pink/Expert paper.
