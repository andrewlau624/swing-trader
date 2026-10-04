# Mechanism-first seasonality: can a calendar-forced flow add material alpha to the book? (2026-10-04)

Method: economic-ceiling gate first (no coding unless a candidate can plausibly add >= ~5pp/yr to the book after costs at
50% capture of the published/hypothesised effect). Inputs: the repo's prior tests (file refs below) plus the literature.
No new variant was run, so program N is unchanged (~818). Account-level contribution assumes the sleeve uses capital the
book leaves idle (the book is ~63% idle by equity-hours at $2.3k), i.e. it stacks rather than competes.

Ceiling arithmetic used throughout: account pp/yr = (net return per event on deployed capital) x (events/yr) x (share of
equity deployed per event). Example: +1% net per event x 12 events x 50% deployed = +6pp.

## A. Ranked candidates
| # | candidate (mechanism) | payer / why no arbitrage | direction | events/yr | gross / net per event (50% capture) | capacity | independence from book | est. book contribution | confidence | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Tax-loss selling -> January reversal** in YTD losers (small/illiquid): taxable holders must realise losses by Dec 31; demand returns in January (Grinblatt-Moskowitz 2004; Starks-Yong-Zheng 2006 for CEFs) | taxable retail/advisers on a hard legal deadline; arbitrage limited by small-cap illiquidity and year-end balance-sheet limits | long late-Dec, exit mid-Jan | 1 (one ~10-15 session window) | ~2-4% gross post-2000 in small losers -> ~1-2% at 50% -> ~0.3-1.5% after 40-100bp small-cap round trip | $10k-50k per name at 1% ADV; fine to $100k+ | high (December only; IBS holds liquid ETFs) | **+0.2 to +1.5pp/yr** (even at 100% of equity deployed for the window) | medium on sign, low on size; DS5's year-end night sizing reversed in 2019-20 (study_ds_round29.md:21-43) | **DEPRIORITIZE** (highest untested upside, still below the gate) |
| 2 | CEF December tax-loss arm | same, CEF holders | long | 1 | +1-3%/month in the paper -> ~0.5-1.5% net | small (thin funds) | high | +0.2-1pp | low (10 Decembers) | DEPRIORITIZE |
| 3 | **OPEX / dealer gamma** -> underlying pinning or hedging momentum | short-gamma dealers hedge mechanically (Baltussen-Da-Lammers-Martens 2021) | gate on the noise leg (continue/fade last 30 min) | ~250 days (as a gate) | literature implies +0-2pp/yr as a noise-leg gate | large (SPY/QQQ) | moderate (it modulates the noise leg) | **+0 to +2pp** | low. OPEX calendar dead (add. 35, RESULTS.md:3413-3520: noise OPEX Fri -1.6bp t -0.5; book effect < 0.3pp); OI pinning killed (24 events, max-OI strike 43% hit vs 55% placebo); 0DTE era shows no change in the noise leg | DEPRIORITIZE (signed gamma stays a paid data target; the purchase case is weak at < 5pp) |
| 4 | **Index reconstitution** (S&P adds/deletes, Russell, quarterly rebalances) | index funds forced to trade at the effective close | buy adds / sell deletes into implementation | S&P ~20 changes; Russell 1-2 recons | S&P: the move is in the announcement gap (+48 / +271 / +517bp by period), tradable windows flip sign (RESULTS.md:3225-3236); Greenwood-Sammon: index effect disappearing | large | high | **~0 (S&P, measured); Russell untestable for single names (no point-in-time membership)** | high that S&P is dead | **KILL** (S&P); Russell Dec-2026 recon = forward shadow only (shadow_russell_recon.md), no backtest possible |
| 5 | Quarter-end / year-end institutional flows other than TME | pensions, balanced funds, window dressing, GSIB year-end balance sheets | various | 4-12 | pension rebalance: +0.15pp/yr as IBS sizing (add. 34 Q4, t 1.94); RB6040 = artefact (69% benchmark bias; executable +26.9bp, t 1.16; 2016-26 t 0.08); window dressing = DS5 quarter-end half, outliers only; GSIB/repo year-end effects live in money markets, not retail-tradable | large | high | **< +0.5pp** | high (several kills) | **KILL** (TME stays frozen and untouched; no distinct quarter-end mechanism found with a tradable instrument) |
| 6 | Seasonal volatility (implied vs realised by calendar window) | vol sellers/buyers with calendar habits | sell/buy vol in windows | 4-12 | needs options or VIX ETPs: generic options search closed (12 variants dead at executable prices), SVXY contango gate dead (NEXT.md:1159), regime gates dead (NEXT.md:1063); pre-holiday sessions "watch" +14-31bp x ~9 days/yr (add. 27) | - | - | **+0.5 to +1.4pp** (pre-holiday only, at 50% capture) | low | DEPRIORITIZE |
| 7 | Earnings-season structure (IV run-up/crush, clustering, index vs constituent vol) | event-vol buyers | sell event vol / dispersion | ~4 seasons | T3/T5/T5L dead at far-side fills (mid +3.3% of risk vs ~3.7% round-trip spread on liquid names, judge 2016-22 -3.4%/trade); dispersion needs multi-leg options (spread-dominated at retail); DS1 earnings-announcement premium +0-6bp gross (NEXT.md:206) | - | - | **~0** | high | **KILL** |
| 8 | Generic calendar anomalies (Monday, Halloween, January, turn-of-month, day-of-week) | no forced payer | - | - | add. 27 dead; Lab-BJ calendar-month -69bp/month | - | - | 0 | high | KILL (out of scope by the brief) |

No candidate clears the ~5pp gate. The best untested one (tax-loss reversal) tops out near ~1.5pp/yr because it is a
single short window per year: even a large per-event edge cannot compound into a material annual contribution.

## B. Deep dive: tax-loss selling -> January reversal (highest upside, still below the gate)
1. **Mechanism.** US taxable investors realise capital losses before Dec 31 (the deadline is statutory; wash-sale rules
   stop immediate repurchase for 30 days). Selling concentrates in YTD losers that are small and illiquid, where
   liquidity providers demand a price concession at year-end (balance-sheet window, holiday staffing). The pressure
   lifts in January; prices recover. Persistence: the tax code and the calendar do not change; the counterparties
   (year-end harvesters) are not price-sensitive by design.
2. **Exact hypothesis.** Stocks with the worst YTD return at the 7th-last session of December, conditional on small size
   and a sell-volume footprint, earn positive abnormal returns from the last-December close to the 10th January session,
   and the effect is larger where tax-motivated selling is larger (bigger YTD loss, more taxable/retail ownership, higher
   December volume vs its own history).
3. **Data.** Alpaca SIP daily bars 2016+ including inactive/delisted symbols (verified, CLAUDE.md part 2), IWM/SPY for
   market drift. Free. Ownership proxies are DATA-LIMITED (no free 13F-level retail share).
4. **Cheapest decisive test.** One event per year x 10 years (Dec 2016 - Jan 2026), ~50 names per year: one script, a
   few hours. Low statistical power is the binding limit, not cost.
5. **Pre-registered definition (would be written to round1_prose.md before any return is loaded).** Universe: common
   stocks, raw close >= $3, 20-day $ADV >= $1M at formation (executable), excluding ETFs/funds. Formation: close of the
   7th-last December session; rank by YTD return; take the worst 50 with YTD <= -30% and December volume >= 1.0x their
   prior-6-month daily mean. Trade: buy the close of the 5th-last December session (after most harvesting, before the
   turn), sell the close of the 10th January session; equal weight. Benchmark: IWM over the same window (no overlap with
   signal construction: YTD and volume use data before formation). Costs: Corwin-Schultz spread per name, floor 25bp per
   side; 2x shock. Placebo: the same rule run on a matched non-December window (formation in mid-June).
   Split: design nothing; judge all 10 events 2016-2025 once; report each year.
6. **Economic ceiling.** At 50% capture: ~+1-2% net per event on deployed capital, 1 event/yr. At 100% of equity
   deployed for the window: **+1-2pp/yr at $2.3k, $10k, $25k and $100k** (capacity is not binding below ~$1M with 50
   names at 1% of ADV). At the realistic 50% (only idle cash): +0.5-1pp/yr. This is the ceiling if the effect is real.
7. **Execution.** Close-auction entry and exit (MOC), whole shares (fine at $2.3k for 50 names only if ~$45 each: whole-
   share rounding on $3-20 names is OK, above that it is not; at $2.3k use the worst 15). Taxable account: the buys
   are short-term; Roth preferable.
8. **Kill criteria.** Mean net abnormal < +1% per event, or fewer than 7 of 10 years positive, or ex-best-1-year mean
   <= 0, or the June placebo does as well, or the effect is not monotone in YTD loss.
9. **Promotion criteria.** All kill criteria cleared AND the incremental book contribution >= +1pp/yr with no increase
   in max drawdown. Even then it is a small December sleeve (forward shadow first), not a material improvement.
   Recommendation: do not spend weeks on it; at most the one-shot test above, and only if a December sleeve is wanted.

## C. Conclusion
**No.** None of the six mechanism-first seasonal families has enough economic potential to materially improve the bot.
Measured candidates are dead (OPEX calendar, OI pinning, S&P reconstitution, quarter-end rebalancing beyond TME,
earnings-season options). The untested ones with a clean mechanism (tax-loss reversal, CEF December, pre-holiday, signed
dealer gamma as a noise gate) top out at roughly **+0.5 to +2pp/yr each** after costs at 50% capture, because seasonal
flows are by nature a few windows per year, or a gate on a leg that is already cost-bound. Plausible incremental CAGR
from all of them together: **~+1-3pp/yr, with low confidence**, nowhere near a path to a 30%+ forward book. TME (frozen,
+4%/yr on deployed capital) remains the only validated calendar mechanism in the program.
Implication for the 30% goal: the gap is not a missing calendar effect. Getting from a realistic ~8-15% to 30% needs
either (a) a much larger per-unit edge (not found in any forced-flow or seasonal search so far) or (b) more of the
edges that already validate (IBS) at higher, honestly-costed utilisation or leverage; that is an existing-book sizing
question, outside this brief. This memo does not recommend another broad seasonal search.
