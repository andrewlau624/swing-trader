# Overnight loop ledger — 2026-10-16/17 night ("everything on" night, user directive)

Rolling loop: each cycle = 1 hunt class -> parallel subagents -> dedupe vs dead list -> cards ->
pivot decision for the next cycle. Session-bound (runs while this session is alive); resume by
reading this file. No N consumed (no tests run; only screens).

## Hunt queue (pivot list, updated each cycle)
1. EDGAR structural lump classes (SC 13E3 going-private cash-outs, TO-I odd-lot tranches,
   exchange-offer sweeteners in 425/S-4, N-14 fund reorg minority cash-outs, Form 25 with
   odd-lot buybacks)
2. Broker / exchange plumbing (Schwab/IBKR features, RPI routes, ACATS/welcome bonuses, DRIP,
   SYEP at scale, 24X retail designation, sub-penny changes)
3. Tax-law forced windows (QOF 180d, wash-sale timing, 83(b), year-end charitable, holding
   period flips; 2026-27 rule transition dates)
4. Non-US analogues + ADR wrappers (Abfindung squeeze-out ADR pass-through, UK/HK reductions,
   AU selective reductions, Brazil tag-along, Canadian arrangements/appraisal, Delaware 262)
5. Regulatory effective-date events 2025-2027 (23/5 Dec 6, sub-penny, margin transition)
6. New-panel random search (LUCK-B7) — BLOCKED until a panel: token-twin marks (TOK-GAP-FWD
   collector ~60 days to maturity), 0DTE/OPRA OI if purchased
7. CEF / interval-fund / closed-end-fund buyback and list mechanics (may feed the ALIVE CEF-RV
   sleeve rather than new edges)

## Cycle log
(nothing yet — cycle 1 below)

## Standing rules for the night
- Dead-list dedupe before ranking (CLAUDE.md section 2 + this file's queue).
- Half-capture ceiling math on every card.
- Never invent sources; mark UNVERIFIED.
- Anything that would need a code change on the LIVE book waits for morning + user OK.

## Cycle 1 (2026-10-16 ~22:30) — EDGAR lump classes + broker/tax plumbing

**1a verdicts:** odd-lot-priority issuer SELF-tenders (SC TO-I) = the only variant that changes
the retired class's arithmetic (verbatim clause verified: "all of the Shares of Odd Lot Holders
will be accepted for payment before any pro rata reduction", HPC 2025 ex-99.(a)(1)(A); Rule
14e-1(a) 20-business-day floor is law — NO faster/ Cheaper-pay variant legal). Premium-family
frequency thin (dutch auctions clear ~market; fixed-price >=3%-premium offers need a screen).
Proposed: add flags "SC TO-I odd-lot priority + fixed-price + premium>=3% + price>=$50" to
`forced_flow_discovery.py` (REGISTRY entry, ~10-session gate) — morning decision.
Ticking-fee deals: low ceiling, mostly arb-crowded. N-14 CEF→open-end: effect in the announcement
gap (untradeable). Cash-in-lieu: at market, dust. Evergreen BDC mini-tenders: issuer-side harvest,
account can't be the payee. REJECTED for the record: MFW premium (doesn't exist), appraisal for
small holders (fees exceed recovery), retail-priority in S-4/425 (EDGAR FTS = zero hits 2023-26).
**1b verdicts:** FUND-LADDER (ACATS/deposit bonus ladder across E*Trade/TastyTrade/Moomoo/Public
— VERIFIED live 10/16/26 with URLs; ~$400-1,200/yr at $25-75k funding pace; one-time per broker;
TastyTrade exact tiers unfetched). SWEEP-MMF (Schwab sweep -> SWVXX 3.71% 7-day; sweeps only the
non-book idle cash; delta needs the Schwab One Interest number). ROTH-INCOME (ETD in Roth saves
22-24% of the yield ~$65-85/yr per $10k; consistent with what we already do; REIT $199A-second).
ROTH-ANNUAL-MATCH (Robinhood Gold 3% on contributions $225/yr MAXIMUM, requires moving the whole
Roth off Schwab — REJECT, kills the live book). SYEP = **invite-only, ~$100k household minimum
(50/50 split)** — CONTRADICTION with my earlier advice; remove SYEP from the user todo list.
IEX/24X/NYSE retail programs: all gated by RMO broker certification; Schwab/Alpaca not confirmed;
kill (matches the CLAUDE.md RPI-RMO caveat).
**Corrections caught by the night:** SYEP not actionable today; LTCG-0% = planning-only no-trade.

**Morning actionables (for the user):** FUND-LADDER if multi-broker ops OK; SWVXX check (needs
the sweep rate); tastytrade tier fetch; Schwab transfer-in promo call question; C1 scan flag.

## Cycle 2 (launching) — non-US analogues + legal forced-sale money

## Cycle 2 (~23:20) — non-US ADR pass-through + legal forced-flow
- **BSBR→Santander Brasil: a LIVE NYSE exchange offer right now** (0.4056 SAN ADS per BSBR ADS,
  425 filed 2026-07-30; published premium +15% has been EATEN by SAN's rally; the current ratio
  value vs BSBR $5.58 is ~-3.5% => channel open, edge currently ~0). The British/German/Japan
  squeeze-out-to-ADR channels are verified-par MECHANISMS (Schering: €89.36 -> €98.98 RAISED
  published via SC 14D9/A; Shire/Takeda paid par to ADS holders verbatim; DOCOMO/NTT tendered
  ADSs) but ALL dormant for lack of in-scope lines today — free pilots to paper-track in the
  next event. Israel: filed offer language includes US holders; SG-styles blocked (OTC).
- Legal: Delaware appraisal post-2019 = negative expected (BU dataset 2015-19: +13.2% GROSS but
  -5.3% UPLIFT on deal price + 2.6-4y holds); class-action claims ~$5-30/event; Fair Fund/CFTC
  need pre-reveal holdings; claims farms not retail. CLASS = empty at the bar. Honest.

## Cycle 3 (~00:30) — funding bonuses verified + tax windows + wildcard
- **Broker bonus table verified as of 10/16/26** (all with URLs): tastytrade SWEETBONUS
  $2.5k=$50 / $25k-99,999=$500 / $100k=$2,000, window ENDS 11/30/26, no IRAs (BRINGIOMATCH
  IRA-promo expired 8/31); Moomoo 3% match on first $20k ($600, but as in-app cash coupons —
  NOT withdrawable, unlocked at 90/180/270/360 days; APY booster 8.1% on first $20k for 2 mo;
  the $200 NVDA stock bonus is ACH-only, ACATS not eligible); Public 1% match NO CAP (incl.
  IRA contributions + transfers), paid 60 monthly drip, no clawbacks on paid installments;
  E*Trade OFFER26 taxable $20-99,999=$300 (OPEN BY 10/31/26, 12-mo hold) and RETIRE26 **IRAs
  eligible** new-clients-only; Schwab NerdWallet award dead for existing household. Morning
  decision: which tranches to route (needs multi-broker ops OK; bonuses are per-broker-per-person).
- Tax windows: 899 revenge-tax DEAD (never effective); Saver's Match (SECURE 2.0 Sec 103;
  first discipline 2027, paid 2028, $1,000/yr IF MAGI <= $35,500 single); AMT/OB3, QSBS
  graduated 50@3y/75@4y/100@5y (N/A unless startup stock); Roth catchup mandate only if wages
  >$150k; charitable floor (bunching passed). All planning-only EXCEPT Saver's Match (annual).
- **Voluntary-liquidation cash-out schedule class DISCOVERED by wildcard pass** (FREVS 8-K
  2026-09-30: "$3.20 per share... payable on October 29, 2026... record October 14" — quoted
  schedule published right in the 8-K) — NOT previously in any ledger; extend
  `forced_flow_discovery.py` with 'plan of liquidation' + record-date + payable-date flags.
  Also liquidating-trust OTC units (ResCap RESCU example just completed) planning-tier;
  ACA MLR rebate annual automatic; §6418 clean-energy credit discount (planning);
  T-Mobile Keep-And-Switch ($300-1,000/yr personal, non-market; page says restricted 7/9/26+
  to NEW accounts), AT&T mirrors.

## Bot-state audit (read-only) — none of the live modules blocked; cpc-ledger, crowd-hold,
gamma-state, cef-activist all ticking; forced-flow-discovery flags no live candidates in latest
rows (all candidate:false); daytrade/cef_rv modes off as registered.

## Cycle 4 (launching) — live screen: unconverged minority cash-out exchange offers

## Cycle 4 (~01:40) — LIVE deal screen (the night's main catch)
- **BMEZ trigger tender: LIVE NOW** (SC TO-C verified on sec.gov, filed 10/1/2026): BlackRock's
  discount-management program triggered at -11.05% avg discount (9-month Measurement Period);
  offer commenced Fri 10/16/2026, expires Wed 11/18/2026 5pm ET; up to 5% of shares at 98% of
  NAV struck the DAY AFTER expiration; prorated if oversubscribed; payment ~5 BD after.
  Numbers (agent-measured 10/16): BMEZ $16.29 vs NAV $18.22 (-10.59% discount) -> tender value
  ~$17.86 = +9.6% if NAV flat; +6.3% if NAV -5%; NAV is the real risk (37% effective leverage).
  RGR's same-class offer closed 10/15 oversubscribed 3x (proration ~38%, realized ~+1% at
  43.38 entry) = the honest base case for oversubscription.
  **This is a RECURRING scheduled class** (BlackRock program across ~19 funds; HERZ 97.5%-of-NAV
  tender just expired 10/15; next triggers predictable from each fund's measurement-period ends)
  — the CEF trigger-tender class feeds BOTH the ALIVE CEF-RV sleeve and the lump-shape.
- NEXA (Boliden VTO at 20d VWAP-linked price): +7.7% in-spread measured, but FLOATING with
  Boliden/SEK and closing Q1 2027 -> monitor, not trade.
- BWIN going-private $32.50 cash vs $31.91 = +1.85%, 13E3, mid-Nov/Dec close: thin, watch.
- BARK: GNK "evaluating" an $11.00 tender vs $7.73 = +42% IF it ever launches: watch only,
  explicit "NO TENDER OFFER HAS COMMENCED" in the filing.
- SNDL: follow-up needed (rate-limited mid-screen).
- Decoys verified with numbers: BSBR (converged to -3.4% spread), PCRX (+0.44% at announcement).

## Night complete — morning memo in research/drafts/morning_memo_2026-10-17.md
