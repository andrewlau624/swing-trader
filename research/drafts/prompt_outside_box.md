# Research prompt: think outside the box — find edges nobody sells in a course (Round 30+)

You are working in the `swing-trader` repo (research data on the Mac at `data/research/night/`). The bot already
harvests three well-known effects (overnight reversal of big losers, IBS mean reversion in ETFs, intraday trend in
QQQ/SMH). Seven hundred and fifty tested variants of *familiar* ideas have mostly died. The last round tested
earnings drift, short interest, seasonality and finer intraday grids: textbook ideas, all dead.

**This round is different. Do not test common strategies.** Your job is to find mechanisms that are specific,
structural, a little strange, and that a $2-25k account can exploit because it is small, fast to adapt and not
bound by the rules that bind funds.

## Banned (do not propose, even reworded)
Technical indicators and their combinations (RSI, MACD, moving-average crosses, Bollinger, ATR breakouts), momentum
and reversal factor variants, earnings drift, analyst revisions, short interest, news/sentiment scores, calendar
seasonality (day-of-week, turn-of-month, holidays, January, quarter-ends), VIX/regime gates, pairs trading, ML on
price features, and anything already in NEXT.md's do-not-redo table or in RESULTS.md (grep before proposing).

## Start from a forced trader, not a pattern
Every candidate must begin by naming **who is forced or constrained to trade at a bad price, and why they can't
stop.** Edges that last come from rules, mandates, plumbing, taxes, deadlines and attention limits, not from chart
shapes. For each idea write the one sentence: "<who> must <trade what, when> because <rule/constraint>, and a
small, flexible account can take the other side by <how>."

Mine these for forced traders (each is a prompt, not a strategy):
- **Mechanical rebalancers with known schedules**: leveraged/inverse ETPs (daily), target-date and balanced funds
  (monthly/quarterly), covered-call and buffer ETFs (roll dates), index reconstitutions of small indexes nobody
  watches (sector, thematic, equal-weight, dividend indexes), ETF creation/redemption in illiquid ETFs.
- **Rule-bound holders**: funds that must sell on a downgrade, delisting, index deletion, a price below $1/$5,
  a spin-off they can't hold, a reverse split, a dividend cut; insurers and pensions with rating or price floors.
- **Settlement, tax and calendar plumbing** that isn't seasonality: wash-sale windows (31 days after big loser
  sell-offs), T+1 settlement and good-faith rules for cash accounts, option expiry pinning in the single
  stocks the night leg buys, short-sale-restriction (SSR) days, LULD bands, closing-auction mechanics per exchange.
- **Attention and interface limits**: what retail apps show (top movers, 52-week lists), what happens when a stock
  enters or leaves a widely watched list, renamed or reticker'd symbols, first days after an uplisting from OTC.
- **Products with broken arbitrage**: closed-end fund discounts, ETF premiums/discounts on thinly traded ETFs,
  ADRs vs home shares across time zones, share classes of the same company (GOOG/GOOGL-type, BRK), SPACs near
  their trust value, preferreds near call dates.

## Generate ideas with these methods (use at least three, say which produced each idea)
1. **Invert a constraint**: list what the bot is *forbidden* to do (short in the Roth, margin in the Roth,
   trade outside regular hours, fractional auction orders) and ask who profits from that same constraint binding
   on other people.
2. **Steal from another field**: inventory management, insurance pricing, queueing, auction theory, sports
   betting closing-line value, ecology (predator/prey on liquidity), epidemiology (how a sell-off spreads across
   related names). Write how the analogy maps to a tradable rule.
3. **Small-size advantage**: what is uneconomic below $1M of capacity, too odd-lot, too illiquid, too
   operationally fiddly, or too small for a fund's compliance to bother? Those places stay unarbitraged.
4. **Look at the bot's own logs as data**: its fills, skips, whole-share rejects, the 15:40 shadow lines, the LLM
   news-judge verdicts, the quote-imbalance snapshots. What does the bot see that no paper studies?
5. **Second-order effects of the bot's own legs**: when the night leg's picks bounce, who loses, and what do they
   do next morning? When the IBS leg fires across sector ETFs at once, what does that say about the next week?
6. **Weird data**: anything public, free and rarely used: EDGAR form types beyond 8-K (NT 10-K late filings,
   S-8, 13D/G amendments, Form 144 intent-to-sell), exchange notices (symbol changes, delisting notices, SSR lists,
   halt codes), FINRA/SEC daily files, ETF holdings files, Cboe/Nasdaq auction statistics, Treasury auction
   calendars, the lab's L1 recordings (`data/daytrade/...`).

## Process (creative first, rigorous second)
1. **Diverge (no tests)**: write `research/drafts/outside_box_ideas.md` with **≥ 40 raw ideas**, each with the
   forced-trader sentence, the generation method, the data it needs (free / cached / paid) and a 1-5 novelty score
   (5 = you can't find it in a paper, blog or forum after a real search; say what you searched).
2. **Kill fast**: for each, the dead-list check (NEXT + RESULTS), "is it just a renamed common strategy?" and
   "does it fit whole shares at $2-25k?". Keep the survivors.
3. **Explore cheaply on the SELECT data only** (2016-23, or 2021-23 for the night pool): quick looks to see whether
   the mechanism exists at all. Never touch 2024-26 while exploring. Log every look you take (it counts toward
   honesty, even when it doesn't count toward N).
4. **Converge**: rank survivors by (expected %/yr at $2.3k-$25k) × (novelty) × (P(survives the judge half)) ×
   (independence from the current legs; same-bet rule corr ≥ 0.7). Commit the list, then pre-register the top
   3-5 (≤ 3 variants each) in `round1_prose.md` with the current N (last amendment; shared with the lab), and only
   then run each once on the judge half.

## The bar, unchanged (it is why the survivors can be trusted)
Night returns from the official crosses (`auction_audit.with_rets`); raw prices; 2.5bp/side judged, tier_hi
reported; increment > 0 in both halves; NW t ≥ 2; a sign-flip placebo AND a placebo that shuffles the feature
itself (catch exposure changes posing as selection); maxDD not worse by > 2pp; P(DD>50%) ≤ 5%; DSR reported.
LLM-judged ideas: forward only. Paid data: price it and ask the user (and tell the lab session) before spending.
Nothing goes live: a pass becomes a default-off switch with shadow logging, a kill rule, tests and a digest gate.
SEC/EDGAR: `swingtrader.daily.news_judge.sec_headers()` builds the required contact User-Agent from
`NOTIFY_EMAIL` (or `SEC_USER_AGENT`) in `.env`; if neither is set on this machine, ask the user rather than
inventing one.

## Deliverables
- `outside_box_ideas.md` (≥ 40 ideas, methods, novelty, kills) committed before any test.
- One pre-registered study per tested idea, a writeup, and a NEXT.md entry (dead ones in the do-not-redo table).
- A closing table: idea | the forced trader | verdict | %/yr and $/yr at $2.3k / $10k / $25k | capacity | what
  live evidence would change it. And a short section: **the three most surprising things you learned**, even
  from dead ideas.
- Commit and push after each study; merge (never rebase) `origin/main` first, since the lab session pushes too.
