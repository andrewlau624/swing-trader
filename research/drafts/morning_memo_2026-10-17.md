# MORNING MEMO — overnight loop 2026-10-16/17 ("everything on" night)

Four cycles ran overnight (EDGAR lump classes, broker/tax plumbing, tax effective-date windows +
wildcard pass, live deal screen). Full cycle log: `research/drafts/loop_night_2026-10-17.md`.
Cards with verbatim quotes are in the cycle outputs on disk. Nothing was deployed during the
night except this memo (code changes need your OK per standing rule).

---

## 1. ACTION TODAY (ranked by $)

### 1a. BMEZ trigger tender — LIVE NOW, closes Wed Nov 18, 2026 5:00 pm ET
BlackRock Health Sciences Term Trust: discount-management program triggered at -11.05% avg
discount (9-month measurement period); fund will buy **up to 5% of its shares at 98% of NAV**
(NAV struck the day AFTER expiration; prorated if oversubscribed; payment ~5 business days
after expiration). Verified verbatim on the SC TO-C (sec.gov, CIK 1785971, acc
0001193125-26-410845, filed 2026-10-01).
- Numbers (measured at cycle time): BMEZ $16.29 vs NAV $18.22 (discount -10.59%) -> tender value
  ~$17.86 = **+9.6% if NAV flat**; +6.3% if NAV -5% by Nov 18; NAV risk is real (leveraged
  health-sciences book, ~37% effective leverage).
- Proration is the base-case cost: RGR's identical offer closed 10/15 oversubscribed 3x
  (realized ~+1% at the entry price); HERZ's 97.5%-of-NAV offer expired 10/15 too.
- **Decision for you:** a small BMEZ slot (~$500-1,000) bought today and tendered before Nov 18
  is a 1.2-month capital lock with a ~+3-10% expected range depending on NAV and proration.
  Sized small enough that proration/NAV risk is bounded. This is the same instrument family as
  the live CEF-RV sleeve — not a new strategy, a scheduled event inside an ALIVE family.
- **Program implication (needs your OK — code change):** extend `forced_flow_discovery.py` to
  flag BlackRock-style trigger tenders (query: "98% of the Fund's NAV" + "up to 5%" +
  measurement-period language) across the whole CEF universe — the class is recurring and
  schedulable from each fund's measurement-period ends (~19 funds in BlackRock's program alone,
  plus Herzfeld/others). This makes the lump recurring rather than one-off. REGISTRY entry in
  the same commit if approved.

### 1b. FUND-LADDER — broker bonuses verified live 10/16/26 (morning decisions)
- **tastytrade SWEETBONUS**: $25,000-99,999 net deposit = **$500** ($2,000 at $100k); window
  **ends 11/30/26**; first deposit by 11/30; NO trading requirement; IRAs NOT eligible
  (taxable only); ACATS-in counts. (T&C: stockbrokers.com + tastytrade.com/sweet-bonus/,
  fetched 10/16/26.)
- **Public 1% match, NO CAP** (ACATS + IRA transfers + IRA contributions), paid in 60 monthly
  drips over 5 years, "no retention period or clawback on payments you've already received"
  (help.public.com, updated 2026-10-13). The drip cannot be front-loaded.
- **Moomoo**: 3% match on first $20k ACAT ($600) — BUT paid as in-app cash coupons unlocked at
  90/180/270/360 days, each usable 6 months inside moomoo; withdrawal before unlock forfeits
  remaining installments; APY booster 8.1% on first $20k for 2 months (then 0.03%).
- **E*Trade RETIRE26 (IRAs eligible, NEW clients only)**: ~$150 at $5-20k, ~$300 at $20-100k,
  open by 10/31/26, 12-month hold. NOTE: opening a SECOND Roth at E*Trade for the $7.5k/yr
  contribution stream (not moving the Schwab Roth — the live book stays) could collect $50-150/yr
  from the new contributions. One extra account, one extra tax document; your call.
- **Schwab**: no open-enrollment transfer promo for existing households (referral $1,000 tier
  needs $500k and a NEW client).
- Best single move if you are moving ~$25-75k anyway: split across Public (1% uncapped, no hold)
  + tastytrade ($500 at $25k, 30-day window) + Moomoo ($600 at $20k, coupon-locked; only if you
  accept the coupons) — ~$1,100-1,600 of same-dollar bonus at your funding scale.

### 1c. SWEEP-MMF — today, $0 effort
Schwab's sweep pays less than SWVXX (7-day 3.70% as of 10/14; Schwab's own cash page steers to
it). Move all NON-book idle Schwab cash to SWVXX; keep only the night/IBS working cash in sweep.
The exact Schwab One Interest rate for the $0-25k tier is login-gated (couldn't verify overnight);
check in-app. Worth ~$75-250/yr at your sizes.

### 1d. Watch list (no action, I monitor)
- **NEXA** (Boliden VTO at Boliden-20d-VWAP-linked price): +7.7% in-spread measured 10/16, but
  floating with Boliden/SEK; closing ~Q1 2027. Monitor weekly.
- **BWIN** going-private $32.50 cash vs $31.91 (+1.85%): thin; DEFM14C due mid-Nov.
- **BARK**: GNK "evaluating" an $11.00 tender vs $7.73 (+42% if it ever launches) — NO offer
  commenced (verbatim in filing). Watch only.
- **BSBR→SAN**: converged (-3.4% spread); skip (the template decoy).

## 2. CORRECTION from last night's earlier advice
**Schwab SYEP is NOT actionable today** — invite-only with a ~$100k household minimum (50/50
split, verified overnight). It was on yesterday's "easy toggles" list by mistake. Same for
IBKR's version at our size (~$20-80/yr). Cross both off; the retail-lending sleeve is a
>$100k-account item. Robinhood IRA match ($225/yr max, requires moving the whole Roth): REJECT
(kills the live book).

## 3. NEW LUMP CLASS discovered (the wildcard cycle)
**Voluntary-liquidation 8-K calendar class** (quote: FREVS 8-K 2026-09-30: "$3.20 per share,
payable on October 29, 2026... record October 14" — the distribution schedule is published in the
8-K itself). Also liquidating-trust OTC units (ResCap RESCU's final distribution 9/15/26) and
§6418 clean-energy credit discounts (planning). The FREVS-class fits the existing EDGAR scanner:
one more flag set ('plan of liquidation' + record/payable dates). Same morning-OK as 1a.

## 4. What ran/verified overnight (no user action)
- Broker bonus table: all 6 offers fetched with dates/URLs.
- Tax windows: §899 dead (never effective); Saver's Match = $1,000/yr from 2028 IF MAGI ≤ $35.5k
  (single) — planning note; QSBS graduated (N/A unless startup stock); Roth catch-up mandate
  (N/A-EMPLOYEE); AMT re-tightened (N/A under $500k AGI).
- Delaware appraisal: negative expected post-2019 (BU dataset: -5.3% average uplift vs deal
  price, 2.6-4yr holds) — confirmed dead for small accounts. Class-action claims: $5-30/event.
- Legal channels (German/UK/Japan squeeze-out to ADRs): mechanisms VERIFIED par-passing
  (Schering €98.98 raised compensation, Shire/Takeda paid par to ADS holders) but no in-scope
  US-listed lines exist today — dormant, paper-track.

## 5. Standing program state (unchanged overnight, all verified ticking on him)
- PREF-EX live (first entry: PSEC.PRA ex 10-21, sizes/reserves Monday 15:25).
- CEF-RV forward shadow (15/60 closed, NAVFALL + ACCEL arms now logging).
- Fill-cost ledger live (305 fills, +0.2bp mean). TOK-GAP collector accruing. 23/5 recorder
  arms Dec 6. Noise leg OFF (re-arm watch). SSR-LIFT short sleeve: still needs your "go."

## 6. Program N unchanged (no tests ran overnight; screens only). Loop ledger ready to resume.
