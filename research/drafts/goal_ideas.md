# Goal hunt ideas (`prompt_strategy_goal.md`, session llm-trader-ec)

Every idea is written before any outcome is looked at. Each answers the five questions of `prompt_hidden_edges.md`
section 1 (who pays / why they accept / why no one with capacity takes it / what makes it repeat / which death it
dodges) plus **source**: which of the four sources of big return (section 0) it uses and why it is big at $2-25k.
Track tags T1-T5. Status lives in `goal_log.md`, not here.

## Round 1 (written 2026-10-02, before any outcome)

### G1 (T5) Contract-payoff stack on an index core, both accounts
SPY is the core in taxable (Roth: the live Roth book or SPY). On top, every per-holder contract payoff that already
PASSED here runs as an overlay funded by selling core for the hold (taxable may use Reg T margin for the 8-10 day B2
hold instead): B1 reverse-split round-ups (1 share per account), B2 split-off exchange offers (<= 99 parent shares,
across accounts), odd-lot issuer tenders (<= 99 shares), plus the EV2-big day trade (intraday only, no overnight
capital). One book, after tax, whole shares, both accounts, judged as CAGR vs SPY.
1. Who pays: issuers following their own charters (round-up clause, odd-lot priority) and parent companies paying a
   discount to clear a split-off; for EV2-big, opening-cross sellers.
2. Why: the terms are written to be fair to holders of record at scale; the per-holder discontinuity is a rounding
   cost to the issuer, accepted as administrative.
3. Capacity: every overlay is capped per beneficial owner (1 share, 99 shares); a fund gets nothing.
4. Repeat: DEF 14A / 8-K split ratios with "rounded up" (~75/yr), SC TO-I split-off and odd-lot tender filings.
5. Death dodged: TOO RARE (a family of ~80 events/yr, not one), STACKING (overlays are contract payoffs with their own
   capital, not tilts on the same returns), HAIRCUT (the core is SPY, which can't be haircut; the overlay is contractual).
Source: (3) large contract payoffs. Big because a per-holder $ payoff is a huge % of a $2.3k account (B1 alone
~$640/yr = +28% at $2.3k). Shrinks in % as the account grows: the question is whether $10k still clears SPY+10pp.
Open risk: B1 depends on Schwab rounding a 1-share holder (VIVK settles ~10-07).

### G2 (T1) EV2-big as a sized standalone day book, with a true holdout
Officer/director open-market buy >= $500k at an issuer with no purchase in 2+ years, opening cross -> closing cross,
ADV >= $20M. Sized as a standalone book: up to 50% of equity per event, up to 2x intraday buying power when two land
on one day (taxable; the Roth trades it unlevered). The size cut was found on 2022-26 data, so 2024-26 is no longer a
judge half for it. **Fix:** extend the SEC Form 345 data sets back to 2014 (they exist from 2006) so 2016-21 is an
untouched holdout; register the rule before building the 2014-19 files.
1. Who pays: opening-cross sellers and market makers who price the session before screeners read the filing.
2. Why: a 1-day, attention-limited reaction; makers are paid for liquidity, not for reading Form 4s.
3. Capacity: one session in a $20M-ADV name; ~$250k per event before cross impact; funds can't size into 60 events/yr.
4. Repeat: Form 4 code P, every business day.
5. Death dodged: LOTTERY (EV2-big kept +35bp of +75bp without its best 5% days; R2), COST (+75bp vs ~5bp round trip),
   HALF-FLIP (tested on a period nobody here has looked at).
Source: (1) concentration + (2) intraday leverage. Big because ~60 events/yr x +50-75bp x 0.5-1.0x of equity is
+15-45%/yr gross before any compounding, with no overnight risk.

### G3 (T1) The whole ID3 family by buy size, dollar-weighted, on the same 2016-21 holdout
Every ID3 event (officer/director buy, ADV >= $20M), weight proportional to log($ bought) / cap, no 2-year-silence
filter. A dose-response across all sizes (<$100k +5, $100-500k +17, $500k-1M +23, >= $1M +35bp in 2022-26) is the
kind of shape that holds out of sample; a single cut isn't.
1-4: as G2. 5. Death dodged: STACKING / overfitting a cut (a monotone weight, not a threshold), REFIT (fixed weight).
Source: (1) concentration. More trades than G2 (~300/yr), smaller per trade; the t comes from breadth.

### G4 (T2) ADR terminations: the last ADR price vs the cash the depositary pays
When a depositary terminates an ADR program, it sells the underlying shares after a notice period and pays holders
cash (net of fees). US holders who can't hold the foreign line (mandates, retail apps) dump the ADR as it moves to OTC
or delists. Payoff = ratio x local price x FX - depositary fees - ADR price at entry.
1. Who pays: US funds and retail who must or will sell before the program ends.
2. Why: mandate (no OTC / no foreign line), broker restrictions on terminated ADRs.
3. Capacity: thin OTC ADRs, $5-50k a name; per-event dollars too small for a fund to staff.
4. Repeat: 8-K / 6-K and F-6 POS / Form 25 with "termination of the deposit agreement"; depositary notice pages.
5. Death dodged: GAP (we trade the contract value, not the reaction), TEXTBOOK (no paper on termination discounts).
Source: (3) contract payoff. Big only if the discount is >= 5% on a meaningful share of events. Kill early if the
count from documents is < 5/yr or the discount from terms is ~0.

### G5 (T2) Mandatory class collapses with a fixed ratio and a market gap
Dual-class unifications, tracking-stock retirements and share-class conversions where class B converts into class A
at a fixed ratio on a known date. Buy the class whose ratio-implied value exceeds its price; hold to conversion.
1. Who pays: holders of the thin class who sell to index funds or can't wait (index weight is on the liquid class).
2. Why: index and liquidity mandates; the thin class is excluded from indexes until conversion.
3. Capacity: thin class ADV often < $1M; a fund can't build a position.
4. Repeat: DEF 14A / 8-K "reclassification", "conversion of each share of Class B".
5. Death dodged: share-class twins at the close were dead (Round 30 #1) because no conversion date bound them; here the
   contract fixes the date and ratio.
Source: (3). Big only on discounts >= 5%; count first.

### G6 (T2) Issuer odd-lot buy-back / round-up programs with a per-holder premium
Some issuers (demutualised insurers, post-reorg companies, old utilities) run voluntary programs where holders of < 100
shares can sell at market plus a fixed premium or round up to 100 commission-free. A fixed $ premium on 1-99 shares is a
large % at the minimum size; across two accounts it repeats.
1. Who pays: the issuer, to cut per-holder admin cost (it pays the premium to shrink its holder count).
2. Why: transfer-agent and mailing costs per holder exceed the premium.
3. Capacity: per-holder cap by construction.
4. Repeat: 8-K / press releases "odd-lot sales program", "odd-lot buyback"; SC TO-I with "odd-lot" in the title.
5. Death dodged: TOO RARE is the risk: count first; overlaps odd-lot tenders (Round 31) only when it is a formal tender.
Source: (3) + (D) small-account superpower.

### G7 (T3) Autocallable barrier levels from 424B2: dealer hedging near knock-in
Bank 424B2 pricing supplements list the single-stock underlying, knock-in barrier (typically 50-70% of initial) and
observation dates. Investors are short a down-and-in put; dealers are long it and hedge by buying as the stock falls
toward the barrier (long gamma), then sell when it breaches (delta of the vanilla put replaces the barrier digital).
Trade only the top decile of outstanding barrier notional / ADV: buy the stock when it trades within 3% above a big
barrier cluster, exit at a breach or after 10 sessions.
1. Who pays: dealers' rule-bound hedge flow (they must stay delta-neutral to their book).
2. Why: hedging is mandated by risk limits; the flow is known only to whoever parses the supplements.
3. Capacity: documents read one at a time (thousands of 424B2s a month); single-name flows of $1-50M.
4. Repeat: 424B2 filings by GS, JPM, MS, BAC, CS/UBS, Barclays, Citi, every day.
5. Death dodged: TEXTBOOK (no paper parses retail note barriers at scale), GAP (no news event).
Source: (1) concentration in the top decile of flow. Direction risk: gamma sign may be wrong; the first look must test
both sides on select data only.

### G8 (T3) Convertible pricing-day hedge shorting, top decile by size / ADV
On the pricing day of a convertible issue, convert arbs short 30-60% of the delta, pushing the stock down 3-8%. Once
the hedge is set, the pressure stops. Buy at the close of the first session after pricing, sell 5 sessions later; only
issues with size / 20d ADV in the top decile (where the shorting is largest relative to normal flow).
1. Who pays: arbs, who must short at pricing regardless of price (their hedge, not a view).
2. Why: the arb's P&L is the convert's cheapness; paying a few % of impact on the hedge is part of the deal.
3. Capacity: a few days, mid caps; funds that do it are the arbs themselves.
4. Repeat: 8-K "pricing of convertible senior notes", 424B / press release, ~150-300 deals/yr.
5. Death dodged: GAP (we buy after the forced flow, betting it stops), FORCED SELLERS KEPT FALLING (Round 30) is the
   risk: that was retail forced selling with no end date; here the hedge size is fixed by the deal.
Source: (1) concentration. Big if top-decile deals rebound >= 3% in 5 days at ~30/yr.

### G9 (T3) S&P 400/600 replacement prediction when a member is acquired
When an S&P 400/600 member's acquisition closes, S&P names a replacement, often from the smaller index or a recent IPO,
with ~2-5 days' notice. Index funds must buy the replacement at the effective close. Predict the replacement before the
announcement from S&P eligibility (market cap band, float, profitability) when a merger's closing date is published
(8-K / DEFM14A "expected to close"); buy the 3 likeliest names the session before the expected close, sell at the
announcement or after 5 sessions.
1. Who pays: index funds (S&P 400/600 trackers: IJH, IJR, VB-adjacent funds) buying at the effective close.
2. Why: tracking mandate.
3. Capacity: only works on small replacements where flow / ADV is large; funds avoid prediction risk.
4. Repeat: every S&P 400/600 member acquisition (~40-60/yr).
5. Death dodged: GAP (S&P 500 adds after the announcement were dead; this is before it), TEXTBOOK (prediction of second-tier
   replacements isn't the published effect).
Source: (1). Risk: prediction hit rate too low; bound with the S&P press-release archive before any prices.

### G10 (T4) Long calls on EV2-big / B2 events instead of shares (Roth convexity)
For EV2-big day trades and split-off parents in the entry window, buy near-the-money calls at the quoted ask instead
of stock. Gives Roth leverage without margin (Roth allows long options) and caps the worst case.
1-4: as G2 / G1. 5. Death dodged: COST is the risk (option spreads in $20M-ADV names are 3-10% of premium); price at
the quoted bid/ask, never mid.
Source: (4) convex. Big only if the stock move (+75bp intraday / +7% over 8 days) clears the option spread and decay.
Likely killed by a bound: same-day calls need 0DTE/weekly liquidity few EV2 names have.
