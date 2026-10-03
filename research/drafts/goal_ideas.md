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

## Round 2, part 1 (written 2026-10-02 after the 10-judged paragraph, before any outcome): G11-G20
Aim (from `goal_log.md`): own-money / forced-flow mechanisms with (a) a window nobody here has looked at and (b) dollars
that scale past per-holder caps.

### G11 (T1) Insider buys >= $500k on 2006-15: the untouched decade
EV2-big and ID3 >= $500k, same rules as G2 and its report row, on Form 345 2006q1-2015q4. This window has never been looked
at for any insider rule here (the Jump hunt's J2 starts in 2016). Blocker: daily bars before 2016 (Alpaca SIP starts
2016). Step 1 is a data check: Tiingo free tier (raw close + adjClose, includes many delisted names) or Stooq. Register
before any 2006-15 price is touched.
1-4: as G2. 5. Death dodged: no clean judge half, G2's missing bar. Source: (1)+(2).
Big if the holdout repeats (+11pp/yr at 0.5x).

### G12 (T1) Act on the acceptance time, not the next open
Form 4s accepted during market hours (09:30-15:30 ET; EDGAR acceptance stamps in the header) can be bought the same day:
enter at the first 5-minute bar after acceptance + 5 min, exit at that session's closing cross. This is a different return
window (fd intraday) from G2's next-session open->close, so it is not a rerun.
1. Who pays: intraday sellers before screeners refresh. 2. Why: attention. 3. Capacity: minutes-scale, small names.
4. Repeat: acceptance datetime in every filing header. 5. Death dodged: GAP (earlier than the next-open reaction).
Source: (1). Big only if a meaningful share of >= $500k buys is filed intraday (count first).

### G13 (T3) Issuer buyback execution intensity from the 10-Q / 10-K repurchase table
Item 2 tables list shares the issuer actually repurchased each month. Issuers that bought >= 2% of shares outstanding in the
latest reported quarter keep buying (programs run for quarters). Buy the top decile by intensity / ADV at the filing,
hold 1 quarter, minus SPY.
1. Who pays: holders selling to a price-insensitive buyer. 2. Why: the issuer runs to a schedule (10b5-1 grids), not a price
view. 3. Capacity: a per-name flow the issuer sets; funds know buybacks but not the table-level intensity.
4. Repeat: every 10-Q / 10-K. 5. Death dodged: TEXTBOOK (buyback announcement drift), dodged by measuring EXECUTED shares
instead of authorizations. Jump J5 (authorization >= 15% of market cap) is a different event.
Source: (1). Big only in the top decile (2%+ a quarter).

### G14 (T2) Spin-offs: regular-way parent vs when-issued pieces
Before a spin, three lines trade: parent regular-way (with the distribution), parent ex-distribution when-issued and spinco
when-issued. The contract says regular-way = ex-dist + ratio x spinco. When regular-way trades below the sum, buy
regular-way the session before the ex-date, hold through the distribution, sell both pieces on the first regular-way
session.
1. Who pays: holders who sell the parent before the spin to avoid receiving an unwanted small cap (index funds, mandates).
2. Why: mandate; the spinco may not fit their index. 3. Capacity: small, needs WI quotes most retail tools don't show.
4. Repeat: Form 10 / 8-K distribution notices, ~20-40 a year. 5. Death dodged: "spin-off completions" (explored-dead) traded
after the spin; this trades the contractual sum-of-parts gap before it. Risk: WI history may not exist in SIP bars.
Source: (3). Count WI availability first.

### G15 (T2) Large special dividends with due bills
For specials >= 25% of the price, the ex-date is the day after the pay date. In the due-bill window, some vendors, brokers
and option adjustments treat the stock as already ex. Contract: a buyer in the window gets the dividend. Buy at the close
of the record date if the price is below the prior close minus 50% of the dividend; sell on the ex-date.
1. Who pays: holders and algos who think the stock already went ex. 2. Why: mechanics most people never see.
3. Capacity: rare events, small names. 4. Repeat: Nasdaq/NYSE dividend notices with "due bill". 5. Death dodged: GAP
(contractual). TOO RARE is the risk: ~10-20 a year. Source: (3).

### G16 (T3) Equal-weight ETF quarterly rebalance (RSP and the equal-weight sector ETFs)
RSP (~$60B+) resets to 1/500 at the March / June / September / December rebalance close. Required trade per name =
AUM x (1/500 - current weight), computable from prices alone. Buy the 10 names with the largest predicted buy / ADV 5
sessions before, sell at the rebalance close.
1. Who pays: RSP (mandate). 2. Why: tracking. 3. Capacity: the rebalance is 1-5% of ADV in large caps; a retail book fits.
4. Repeat: S&P 500 Equal Weight methodology. 5. Death dodged: the calendar is not the signal; the methodology's flow is.
Risk: TEXTBOOK and small flow vs ADV. Source: (1) concentration in the largest predicted buys.

### G17 (T3) SCHD / Dow Jones US Dividend 100 annual reconstitution: predict the adds
The index reconstitutes every March from public screens (10-year dividend history, cash flow / debt, ROE, yield, 5-year
dividend growth). SCHD (~$60B+) must buy the adds at the effective close; adds in mid caps can be 20-100% of a day's ADV.
Predict the adds from the published methodology BEFORE S&P's announcement, buy the predicted top-flow names, sell at the
effective close.
1. Who pays: SCHD and other trackers. 2. Why: mandate. 3. Capacity: one event a year, prediction needed, small names.
4. Repeat: methodology + SCHD holdings history (Schwab holdings files; Wayback for history). 5. Death dodged: GAP (before the
announcement). Risk: one event a year (TOO RARE unless it is ~20 names a year). Source: (1).

### G18 (T4) Pre-deal SPAC warrants as a convex basket
SPAC unit buyers (arbs) keep the trust-backed share and dump the warrant: forced, price-insensitive sellers of a free option
on a deal. Buy a basket of pre-announcement SPAC warrants priced < $0.50 and hold to the deal announcement (warrants
typically 2-5x on a deal) or the liquidation (−100%).
1. Who pays: arbs stripping warrants. 2. Why: their return is the trust yield, so the warrant is a by-product.
3. Capacity: tiny warrants. 4. Repeat: S-1 / 424B4 of every SPAC. 5. Death dodged: LOTTERY is the risk (warrants are
lottery tickets by construction), REGIME (2020-21 boom, 2022-23 bust). Source: (4) convex.
The likely death is REGIME: 2021-23 liquidations.

### G19 (T4) Warrants distributed in reorganizations and spins, bought below their option value
When emergence or a spin distributes warrants to holders who can't keep them (index funds, mandates), the warrants trade
below Black-Scholes value at a conservative IV for weeks. Buy those trading at < 60% of BS value (IV = the stock's 1-year
realized vol), hold 60 sessions or to fair value.
1. Who pays: forced holders dumping a distribution. 2. Why: mandate. 3. Capacity: thin warrant lines.
4. Repeat: 8-K / plan of reorganization "warrants will be distributed". 5. Death dodged: DL2 (issuer warrant offers) was a
different event; LOTTERY is controlled by the BS-value floor. Source: (4).

### G20 (T1) Insider conviction scaled by the insider, not by dollars
Same events as G11 (2006-15, the clean window), but rank by the buy as a share of the insider's prior holdings
(Form 345 SHRS_OWND_FOLWNG_TRANS) or of market cap, instead of a fixed $500k. A $500k buy is huge for a micro-cap
director and trivial for a large-cap CEO.
1-4: as G2. 5. Death dodged: STACKING / overfit, by registering one scaled measure only, on the clean window.
Source: (1). Needs G11's data step.

## Round 2, part 2 (written 2026-10-02, before any outcome): G21-G30
Tracks short of quota: T4, T5, then T1/T2. Every idea still answers the five questions; brief where it builds on an
earlier idea.

### G21 (T5) The whole small-account book in one number
A report, not a new edge: index-beat's FOUND stack (taxable SPY 1.0x + legs on margin; Roth 1/3 UPRO + 2/3 Roth book),
plus the G1 contract stack (B1 both accounts, B2 + tenders in the better account), plus G2 / `id3_big` as a forward add-on.
After tax, both accounts, at $2.3k / $10k / $25k, with deposits. Each part sized by its own risk; correlation on bad days
from R4. Answers "how far over the index is everything we have, if the forward tests pass".
Source: (5) combine. Death dodged: STACKING (contract payoffs and index beta don't share returns).

### G22 (T5) Put the per-holder contract payoffs in the Roth
B2 split-offs and odd-lot tenders cap at 99 shares ACROSS accounts, so the account that holds them is a free choice. In
the Roth, their short-term gains are untaxed: at $10k taxable that is ~35% of ~$1,000/yr = ~$350/yr (+3.5pp). Constraint:
the Roth must have the cash for 99 parent shares (~$5-15k) for ~8-10 days, i.e. pull the Roth book's cash out for the
hold. Model the Roth book's lost days vs the tax saved.
1. Who pays: the IRS's 35% ST rate is avoided. 2-4: as B2 / tenders. 5. Death dodged: TAX (by construction).
Source: (5).

### G23 (T5/T1) The insider day sleeve in the Roth's idle daytime cash
The Roth night book sells at the opening cross and buys at the closing cross, so the Roth's cash sits idle 09:30-15:59.
An open->close insider trade (ID3 / `id3_big`, when the forward gate passes) fits in that window with no margin, which
the Roth can't use for an overlay on an index core anyway. Tax-free, and it uses capital that earns nothing intraday.
1-4: as ID3. 5. Death dodged: WHOLE SHARES (Roth $8.5k+ buys whole shares in $20M+ ADV names), TAX.
Source: (1)+(5). Depends on the forward gate.

### G24 (T4) Deep-ITM SPY LEAPs instead of UPRO for the Roth's levered beta
Index-beat's FOUND stack puts 1/3 of the Roth in UPRO (3x daily). UPRO pays ~0.9% expense, swap financing and daily-reset
drag (~L(L-1)/2 x var = ~3 x var a year, ~8-10% in a 17%-vol year). A 0.8-delta 12-18-month SPY call gives ~2.5-4x
exposure per dollar with financing at the implied rate, no reset drag, and a capped loss. The Roth allows long options.
1. Who pays: nobody is mispricing. It's an instrument-cost comparison, valid only if the option bid/ask (SPY LEAPs: a few
cents on $100+) beats UPRO's drag. 3. Capacity: unlimited. 4. Repeat: listed SPY LEAPs. 5. Death dodged: the "leap book"
(addendum 24, shadow) was a leap *strategy*; this is a cheaper wrapper for exposure already chosen.
Source: (2)+(4). Data: SPY option history before 2024 isn't free; bound with a conservative IV and the quoted spread.

### G25 (T4/T2) Listed CVRs that index funds receive and must dump
When an acquirer pays partly in contingent value rights (pays $X if an FDA approval or sales milestone happens by a date),
index funds holding the target receive CVRs they can't hold or price, and sell them in the first weeks. The payoff is
written in the CVR agreement; the milestone odds can be bounded from public data (FDA base rates by phase, sales guidance).
1. Who pays: mandate sellers (index funds, ETFs). 2. Why: no mandate to hold an unlisted / odd instrument. 3. Capacity:
thin, small. 4. Repeat: 8-K / S-4 "contingent value right" with a listing (Nasdaq: the -RT, -CVR symbols). 5. Death dodged:
LOTTERY (binary payoff) is the risk; only buy below expected value at the base rate. Count first: listed CVRs ~2-5/yr.
Source: (4) convex + (3) contract.

### G26 (T4) Index puts to buy back drawdown room for the levered overlay
G2b (1.0x per event) cleared +16-21pp on the holdout, but its max DD was 33-34% against the 35% bar. A rolling 3-month 10%-OTM
SPY put on the core costs ~1.5-3%/yr and cuts crash-month DD. If it lets the overlay run at 1.0x with DD <= 30%, the trade
is ~2pp of insurance for ~+5-10pp of overlay. Convexity as a risk budget, not as the return source.
5. Death dodged: REGIME DIAL (no de-risking by signal), TAX (puts on SPY are equity options, short-term). Source: (4) + (2).
Depends on G2-F passing forward.

### G27 (T2) Mutual savings bank conversions: subscribe as a depositor
When a mutual savings bank converts to stock form, eligible depositors (account open before the eligibility record date,
often 12-18 months earlier) get priority subscription at $10/share. The price comes from a regulated pro-forma appraisal
that is conservative by design. First-day and first-month returns of standard and second-step conversions have been
positive on average.
1. Who pays: the mutual's other members and the regulator's appraisal rule (OCC / FDIC / Fed). 2. Why: regulation sets the
price conservatively to protect depositors. 3. Capacity: per-person subscription caps ($X per depositor), so funds can't take
it, and it needs a deposit account opened 1+ year early. 4. Repeat: S-1 / Form AC "plan of conversion", "subscription
offering", ~5-15 a year. 5. Death dodged: DL7 retail IPO access (cold IPOs, retail filled only in bad deals) is the risk.
Here eligibility is guaranteed by being a depositor, not by an allocation. Manual: opening bank accounts early
(> 5 min, once per bank). Source: (3)+(D).

### G28 (T1) Lever B2 split-offs with Reg T margin at small sizes
At $2.3k, B2 fills only ~20 of the 99 allowed parent shares. 2x overnight margin for the ~8-10 day hold doubles the
position to ~40-50 shares: ~+$180/yr -> ~+$360/yr at $2.3k (+16pp pre-tax) for ~$10 of margin interest. Worst historical
event −8.8% x 2 = −17.6% of the position's equity share.
1-4: as B2 (contract payoff with odd-lot priority). 5. Death dodged: TOO RARE (unchanged, ~1.4/yr); it only scales the
dollars of a payoff that already passed. Taxable only (Roth: no margin). Source: (2) leverage on a contract payoff.

### G29 (T4) Long-dated calls on split-off parents to hold through the exchange? KILLED at writing
The odd-lot priority requires tendering SHARES; a call holder can't tender. Written down only so it isn't re-proposed.

### G30 (T3) Transfer agents selling aggregated fractional shares after reverse splits
After a cash-in-lieu reverse split, the transfer agent aggregates every holder's fractions and SELLS them in the market
over the following days: a forced, price-insensitive seller. In heavy-retail micro caps (many small holders), the aggregate
can be a meaningful share of ADV. Buy once the sale window ends (the 8-K or the agent's notice often gives it, else d+5),
hold 5 sessions, minus the stock's usual post-split drift.
1. Who pays: the agent (it must sell; it reports the average price). 2. Why: the split terms require cash in lieu.
3. Capacity: micro caps, a few days. 4. Repeat: 8-K Item 5.03 / press releases "in lieu of fractional shares ... aggregated
and sold". 5. Death dodged: B1 (the same splits, holder-level round-ups) is a different mechanism. The known post-reverse-split
DRIFT (night picks with a recent reverse split were borderline) is the risk: measure vs matched reverse-split names that
round up (no agent sale) as the control. Source: (1) concentration in forced flow.

## Round 2, part 3 (written 2026-10-02 after the 20-judged paragraph, before any outcome): G31-G36
Aim: breadth (>= 50 events a year) from broad free data, payoffs that scale with capital. Only six were written: the
remaining T1/T4 slots would have been filler (T1's clean ideas are blocked on pre-2016 bars, G11/G20; T4 keeps dying on
option costs). The shortfall is deliberate.

### G31 (T3) Follow-on offerings: the underwriter's stabilizing bid as a floor
Overnight-priced follow-ons (424B4/424B7, "bought deals") are priced at a discount to the last close. Under Reg M Rule 104
the syndicate may post a stabilizing bid at or below the offer price and holds a greenshoe to cover. The stock tends to
open near the offer price. Buy at the open of the day after pricing when it opens within 1% of the offer price, sell at
the close of day 3, stop at offer −3% (stabilization abandoned).
1. Who pays: the selling holder (PE sponsor, insider), who accepts a discount for size. 2. Why: size and certainty.
3. Capacity: retail gets no allocation, but the aftermarket floor is open to anyone. 4. Repeat: 424B4/424B7 + 8-K pricing
press releases, several hundred a year. 5. Death dodged: GAP (we don't buy the reaction; we buy at the contractual
stabilization level). Study T (offering filings as a night-pick tilt) was a different trade.
Source: (1) breadth. Big only if the floor is real (median >= +1% by day 3 with a small left tail).

### G32 (T3) At-the-market program exhaustion: the issuer stops selling
Issuers with ATM programs (424B5 "at the market offering") sell into the market daily until the program is used up; the
10-Q states how much was sold vs authorized. When a filing shows >= 90% of the program sold and no new ATM supplement
has been filed, the steady seller is gone. Buy the session after that filing, hold 20 sessions, vs a matched control of
ATM issuers with < 50% sold.
1. Who pays: the issuer, a price-insensitive scheduled seller while the program runs. 2. Why: raising capital, not timing.
3. Capacity: small caps (biotech, REITs, miners). 4. Repeat: 424B5 + 10-Q ATM disclosures, hundreds of programs a year.
5. Death dodged: forced sellers kept falling (Round 30) because those had no end date; an ATM has a cap.
Source: (1) breadth. Risk: issuers usually file a new ATM right away (count first).

### G33 (T5) Tax-loss harvest the taxable SPY core against the legs' short-term gains
In index-beat's stack, the taxable account holds SPY 1.0x and the legs realize short-term gains taxed at 35%. When SPY is
>= 5% below the core's basis, sell it and buy IVV/VOO (a different fund on a different index provider's product; the IRS
hasn't ruled them substantially identical, and the practice is widespread), realizing a short-term capital loss that
offsets the legs' gains. Swap back after 31 days. Tax alpha scales with the core.
1. Who pays: the tax code's capital-loss offset rules. 2-4: mechanical, every drawdown >= 5%. 5. Death dodged: TAX (it
uses tax rules, not a signal), REGIME (it just harvests in drawdowns). Source: (5). Risk: the "substantially identical"
judgment is the user's (and their tax adviser's), not research.

### G34 (T2) Listed preferreds below par after a change-of-control merger
Many REIT, bank and utility preferreds must be redeemed at $25 + accrued dividends on a change of control (or convert at a
formula). After a merger announcement, thin retail-held preferreds can trade below $25 + accrued even though the contract
pays par at closing. Buy when price <= par + accrued − 1.5%, hold to redemption.
1. Who pays: inattentive preferred holders who sell. 2. Why: they don't read change-of-control clauses. 3. Capacity: thin
$25 issues, $10-50k per name. 4. Repeat: merger 8-Ks of issuers with listed preferreds + the preferred's prospectus
(424B5) "change of control" redemption clause, ~10-20 deals a year. 5. Death dodged: GAP (contract, not reaction); B3
merger arb was dead because the common spread was T-bill-like; preferred holders are a different, thinner crowd.
Source: (3).

### G35 (T2) Exchange-traded $25 notes with a 101% change-of-control put
The same mechanism for baby bonds: many $25-par notes carry a holder put at 101% on a change of control with a rating
downgrade. If a deal triggers it and the note trades below 101% of par + accrued, the payoff is contractual (the put window
opens after closing).
1-5: as G34. Count first (FTS 8-K "change of control repurchase event" + "notes"). Source: (3).

### G36 (T3) RSU vest-date selling by employees, detected from Form 4 code F clusters
Large-cap tech employees' RSUs vest on fixed dates; a cluster of officer Form 4 code F (tax withholding) filings marks a
company vest date, and rank-and-file employees sell on and after those dates (indifferent sellers taking cash). Buy the
company 2 sessions after a code-F cluster (>= 5 officers within 2 days), hold 5 sessions, vs SPY.
1. Who pays: employees selling vested shares. 2. Why: diversification and taxes, price-insensitive. 3. Capacity: large
caps (big capacity, so it's probably arbitraged; the sign could be tiny). 4. Repeat: Form 345 code F, quarterly per
issuer, thousands of events a year. 5. Death dodged: the calendar isn't the signal; the filing cluster is.
Source: (1) breadth. Expected small; kill early if select mean < 2 round trips.

## Round 3, part 1 (written 2026-10-02 after the after-30 paragraph, before any outcome): G41-G46
Aim: own-money signals with breadth and windows nobody here has computed; small names where flow / ADV is large.

### G41 (T1) Small concentrated 13F managers' new "best ideas" in small caps
A first-time 13F position that is >= 5% of a fund's reported portfolio, at a fund with < $500M of 13F assets and < 40
positions, in a stock with market cap < $2B. Buy at the 13F filing (45-day lag), hold 60 sessions, vs a size-matched ETF (IWM).
1. Who pays: sellers in thin names who don't track small-fund conviction. 2. Why: attention. 3. Capacity: the funds
themselves can't add more without moving the price, and a 45-day-old signal is useless to fast money. 4. Repeat: 13F-HR
quarterly (jump cache 2013-26). 5. Death dodged: TEXTBOOK (Cohen-Polk-Silli "best ideas", large funds, 2010) is the risk;
the small-fund / small-cap corner is less crowded. Source: (1).

### G42 (T1) Officer/director buys >= $500k in THIN names, 5-session hold
ID2 (all sizes, ADV $1-20M, next session) was dead, but the >= $500k cut was never computed in thin names in any period.
A $500k buy in a $5M-ADV name is ~10% of a day's volume: a far stronger signal than in a large cap, and diffusion is slower.
Buy the opening cross of the session after the filing, hold 5 sessions, tier costs (thin-name tiers), vs IWM.
1-4: as ID3. 5. Death dodged: COST (thin-name tiers charged on both sides; a 5-day hold amortizes them), the J2 overlap
(J2 required a 30% fall first). Source: (1). Big because thin-name signals are larger per trade.

### G43 (T1) Insider buys scaled by market cap: $ bought >= 0.5% of market cap
Scale-free conviction: an insider buying 0.5%+ of the company in one filing (XBRL shares history in the jump cache x raw
price = market cap at the filing). Any ADV >= $2M, next-session open -> close and 5-day hold. Breaks the tie between "big $"
and "big relative to the company".
1-4: as ID3. 5. Death dodged: overfitting a $ threshold (a relative measure is set by the mechanism: the insider's stake
in the company's float). Source: (1).

### G44 (T3) OTC -> Nasdaq/NYSE uplistings: mandate buyers arrive
When an OTC company uplists, funds barred from OTC names can buy for the first time; index eligibility (Russell) follows at
the next reconstitution. Buy at the 5th listed session's close (after the first-days noise), hold 60 sessions, vs IWM.
1. Who pays: nobody forced; the mandate change adds buyers. 2-3: small names, slow institutional entry. 4. Repeat: Form
8-A12B / exchange approval notices for issuers with prior OTC bars, ~50-100 a year. 5. Death dodged: GAP (we skip the first
days); the known risk is uplist-and-dilute (offerings right after the uplisting). Source: (1) small names.

### G45 (T3/T2) Activist 13D on a closed-end fund -> tender or discount narrowing
When a known CEF activist (Saba, Karpus, Bulldog, City of London ...) files a 13D on a CEF, boards often concede tender offers
at 98-99% of NAV or liquidations within months (contract payoffs). Buy the CEF the session after the 13D, hold 120 sessions or
until a tender is announced, vs a CEF index ETF (CEFS / PCEF).
1. Who pays: the fund board / the remaining holders, via the concession. 2. Why: proxy-fight costs. 3. Capacity: small CEFs,
thin. 4. Repeat: SC 13D on N-2 filers (EDGAR FTS), ~20-60 a year. 5. Death dodged: A1 (13D originals on operating companies,
next session) is dead; this is CEFs, where the activist's demand is a NAV payoff, not a story. Source: (3)+(1).

### G46 (T3) A large 13F holder's completed full exit in a small cap
When a 13F shows a fund holding >= 5% of a small cap's shares has gone to zero, the selling is already over (13F reports
45 days after quarter end). The forced or voluntary seller is gone; the price pressure it left should reverse. Buy at that
13F filing, hold 60 sessions, vs IWM.
1. Who pays: the liquidating fund (redemptions, closure). 2. Why: forced. 3. Capacity: small caps, slow. 4. Repeat: 13F
quarterly. 5. Death dodged: "forced sellers kept falling" (Round 30) bought DURING forced selling; this buys after it is
reported complete. Source: (1).

## Round 3, part 2 (written 2026-10-02, after G45 passed its study bars): G47-G49, aimed at G45's lesson
G45 worked because a specialist activist with a NAV-linked exit (tender at NAV, liquidation, open-ending) bought into a
discounted vehicle. Look for the same shape elsewhere.

### G47 (T3) Specialist small-bank activists (Stilwell, PL Capital, Driver, Basswood): 13D on a small bank
Small banks trade below book; specialist activists push for a sale, a buyback or a second-step conversion: a book-value-linked
exit like G45's NAV exit. First 13D by one of these activists on a bank/thrift; buy the next open, hold 120 sessions, vs KRE.
1. Who pays: the bank's board/acquirer (control premium). 2. Why: proxy pressure. 3. Capacity: micro-cap banks. 4. Repeat:
SC 13D by named filers (FTS). 5. Death dodged: A1 (all 13D originals next session) was dead; this is named specialists with a
book-value exit and a 120-session hold. Source: (1)+(3).

### G48 (T2) Closed-end fund mergers at NAV: buy the target trading at the wider discount
In a CEF reorganization (N-14), target shares convert into acquirer shares at the NAV ratio. If the target trades at a bigger
discount than the acquirer, buying the target captures (target discount − acquirer discount) at closing. Contractual, ~3-6
months.
1. Who pays: target holders selling at the wider discount. 2. Why: inattention; thin funds. 3. Capacity: thin. 4. Repeat: N-14 /
DEF 14A "Agreement and Plan of Reorganization", ~10-20 a year. 5. Death dodged: DL5/DL6 (term CEFs, ETF closures) traded the
discount closing on its own; here the NAV-for-NAV exchange is in the contract. Source: (3). Blocker: needs NAV at entry (fund
NAV history isn't in Alpaca); the N-14 text states NAVs at a date, which may be enough.

### G49 (T2) CEFs announcing open-ending, conversion to an ETF, or liquidation
After the announcement, the discount usually shrinks but not to zero: the last 1-3% is paid at conversion/liquidation months
later. Buy the session after the announcement, hold to conversion; payoff = the NAV at conversion (contract) minus the price.
1. Who pays: holders who sell after the announcement rather than wait. 2. Why: time preference, rotation. 3. Capacity: per
fund small. 4. Repeat: 8-K / N-CSR "convert to an open-end", "liquidat", "reorganize into an ETF", ~5-15 a year (more since the
2023-25 Saba campaigns). 5. Death dodged: DL5 term CEFs (no event, a year out) dead; this is a dated conversion at NAV.
Source: (3). Often the tail of G45 events: count overlap.

## Round 3, part 3 (written 2026-10-02, from the closest mechanism, G45): G50-G51
The same NAV-exit mechanism with more events per fund: escalation points of an activist campaign, not just the first 13D.

### G50 (T3) The activist's stake in a CEF crosses 15%
In a CEF, an activist past ~15% can usually force a tender or win a proxy vote (most CEF votes are decided by a plurality
of a low turnout). Event: the first 13D or 13D/A by the six G45 activists whose cover page shows >= 15.0% of the class, after
filings below 15%. Buy the next open, hold 60 sessions, vs PCEF.
1-4: as G45 (SC 13D/A cover-page "percent of class"). 5. Death dodged: STACKING on G45 (same funds, later dates); the
crossing is a separate, later event. Report the overlap with open G45 windows. Source: (3)+(1).

### G51 (T3) The activist files proxy materials against a CEF
Event: the first PREC14A / DEFC14A / DFAN14A filed by the six activists naming a fund (a proxy contest, the escalation before
a concession). Buy the next open, hold 60 sessions, vs PCEF.
1-4: as G45 (EDGAR FTS on proxy forms). 5. Death dodged: as G50. Source: (3).

## Round 4 (written 2026-10-02, from the closest mechanism, G45): G53
### G53 (T3) Any OTHER filer's first 13D on a closed-end fund
G45 used six named activists. Does the effect generalize to every other 13D filer on a listed fund (wealth managers,
smaller activists, funds of funds crossing 5%)? If yes, the event count roughly doubles and the book-level gap closes;
if no, G45 is specific to the activists who can force a NAV exit (the mechanism claim).
1. Who pays: as G45. 3. Capacity: as G45. 4. Repeat: SC 13D in the EDGAR quarterly form index, subject = a fund-like
company with a ticker. 5. Death dodged: STACKING / overlap with G45, by excluding the six activists. Source: (3)+(1).

### G54 (T1/T3) Officers/directors of a closed-end fund buying the fund with their own money
The two families that worked here, combined: own-money insider buying (ID3/EV2) and a discounted fund with a NAV anchor (G45).
A fund insider buying at a discount is buying NAV at a discount, and knows the board's plans (tenders, mergers, open-ending).
Event: officer/director code-P Form 4 at a fund-like issuer (the G45 regex on the issuer name), first per fund in 90 days.
Buy the next open, hold 60, vs PCEF. 5. Death dodged: ID2 thin-name (dead) was operating companies at next-session holds;
here the anchor is NAV. Source: (1)+(3).
