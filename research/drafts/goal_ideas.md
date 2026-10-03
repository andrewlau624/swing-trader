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
