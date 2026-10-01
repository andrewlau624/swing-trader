# Round 1 research — hypotheses and pre-registrations (2026-09-29)

Research standards per README ("Research standards") and RESULTS.md addenda 27-41.
This file contains ONLY hypothesis statements, mechanisms, variant lists and pass bars.
No 2024-26 or variant result has been computed at the time of the stamps below.

Baseline: corrected raw-price pool (`load_sim(raw_price=True)`, night pool corr 0.7).
Verified reproduction before anything else was computed: V7 1.0x cap .10 conv .5 at 3bp
= 50.2 / 44.1 / 47.2/2.06/-14 and tier_hi 34.4 / 24.3 / 29.4/1.41/-17 — matches addenda 30/39
to the decimal. Costs: 3bp flat ("measured"), tier, tier_hi via `book.cost_bps`.

## The candidate list this round (8, ranked by expected after-tax $/yr x P(survive))

| # | hypothesis | mechanism | data | why not in the dead list |
|---|---|---|---|---|
| 1 | Night-leg exit: hold past the opening auction when the open gaps down hard (≤ -5% / ≤ -8%), sell at a 09:35-10:00 minute close instead | For extreme overnight gaps the opening auction is mechanically overwhelmed (overnight order imbalance, share-count clearing); the forced-supply side keeps hitting it into the first half hour. Existing test (add. 10, 09:35 exit) was unconditional and mixed all gaps; conditional-on-gap-size is a different rule | `data/research/night/gm1` minute bars for the 1,474 eligible-gap sessions 2020-11..2026-09 (38.8 names/day, top-40 by abs gap >= 3%), joined to the raw night pool | the dead list has unconditional 09:35 exit (add. 10) and Friday/weekend entry patterns, but no gap-conditioned EXIT study |
| 2 | Earnings-reaction skip on the night leg (skip/size names whose -8% day was the earnings reaction) | information/liquidity asymmetry: earnings-reaction drops are informed flow that continues | would need point-in-time earnings dates | dead by prior: the point-in-time headline test (add. 12) measured exactly this as the "earnings" category: n 9.2%, mean +19.7bp vs +18.3 no-news, excess vs same night +0.6 bp (t ~0.4-0.6), no category after controlling for the night. The rule buys after the news is priced; "whether the selling overshot" is not measured by the headline. Not retested. |
| 3 | Always-full night deployment via cross-sectional ranking | none beyond volume | - | dead by prior: index filler (add. 16: 2024-26 only), multi-day losers M2/M3/M5 (add. 27 R2: slides are continuation), depth -6/-7% band (add. 21), tilt v2 (add. 23, OFF when tested) |
| 4 | Taxable-book V6 (SPY/QQQ oversold overnight on idle IBS money) on the RAW pool at tier/tier_hi | index-level liquidity provision at the close into weakness (already shadow) | ETF daily/minute bars | not a new rule: an on-raw restatement of the taxable side of add. 27/31's shadow variant, which add. 39 never restated for the taxable book (it restated the Roth A2 only). New money question: is the increment still positive at tier_hi on raw prices |
| 5 | Closing-auction imbalance (15:50) as a night-entry filter | imbalance-driven close-price displacement | not obtainable free historically | untestable: declared n/a |
| 6 | Noise-band rule on non-equity 24h markets via deep ETFs | hedging flows in 24h markets | ETF minutes (TLT/GLD/...) | dead by prior: bonds/gold/oil/SPY intraday diversification dead (add. 20), 24h/crypto variants dead (add. 3) |
| 7 | Second overnight leg on up-day extremes in ETFs | short the ETF at the close after an extreme up day | data exists | dead by prior: chase-the-up-day ~0-; long/short dead; S&P "post-effective reversal" dead (add. 34). No new mechanism named |
| 8 | Tax-lot / loss-harvest scheduling in the taxable book | wash-sale-aware timing | - | structurally void: every leg holds <= 1 session, so all realizations are ST within the year and there is no scheduling freedom; the wash guard (roth_first, add. 31/39) already manages the cross-account part |

Ranking rationale: #1 is the only hypothesis with (a) a forced/structural counterparty at the
opening auction, (b) data already on disk, (c) potential low correlation to existing legs (it
changes WHEN the same leg sells, not what it buys), (d) direct capacity. #4 is a cheap, honest
restatement decision-gating a shadow that the program already built. #2-#3, #6-#8 are judged
dead-by-prior with the citations above (each counted as a tested idea, zero variants run).

## Pre-registration — Study A: gap-conditioned night exit (stamped below)

**Hypothesis.** For night picks whose next session opens with a gap-down of <= G% from the
previous close, extending the exit from the opening auction to the minute-M close earns more
than the auction exit, net of costs, in both halves, because the auction print for such names
is a mechanically dominated venue (forced overnight clearance) and the residual supply keeps
arriving; the bounce completes later.

**Data / linkage (all decisions at live times, no lookahead).**
- Pick legs: raw-price night pool (s = validate.load_sim(raw_price=True), N = book.night_days
  (raw_price=True, max_corr=0.7)); each pick's entry price `nd.close`, the published auction
  return `nd.ret`, the decision price `nd.price`, adv and vol20 already known at 15:40+.
- Next-morning minute bars from `data/research/night/gm1` (SIP minute, eligibility C1 >= $3
  and ADV >= $5M, top-40 by abs gap per session). Exit decision = the MINUTE close (what a
  live market order at that minute would hit); the minute-0 open is the auction proxy.
- Rebase minute prices onto the daily-panel basis with scale = daily open / minute-0 open for
  that (session, name); assert the last minute close vs the daily close agrees within 0.5% (else
  drop the name-day and count it).
- Cost of the exit leg: `book.cost_bps` at tier / tier_hi on the raw exit price (raw factor =
  raw open / adjusted open of that session; from the raw_close.parquet, addendum 30).
- Whole shares are preserved by the book replay (as shipped).

**Variants (5 pre-registered; all judged with the same pass bar).**
- E1: gap <= -5%: sell at the 09:35 close (minute 5)
- E2: gap <= -5%: sell at the 09:45 close (minute 15)
- E3: gap <= -5%: sell at the 10:00 close (minute 30)
- E4: gap <= -8%: sell at the 10:00 close (minute 30)
- E5: gap <= -5%: half at the opening auction, half at the 10:00 close

Each variant is scored versus the shipped V7 book on the SAME simulated trade set, at tier and
tier_hi, with the per-trade diff and a book replay. A position not qualifying (no minute data,
gap above the threshold, or the minute price missing) keeps the shipped auction exit.

**Controls.**
- Placebo (200 draws): for each qualifying pick, a random OTHER eligible gap name from the same
  session with a same-signed gap of any magnitude >= 3%, same vol20 decile (deciles over the
  study's own pooled names), scored with the same variant's exit rule. The actual mean
  per-trade diff must beat the 95th percentile of the placebo diffs in BOTH halves.
- Periods: 2021-23 (fit) / 2024-26 (judge), and the reverse; the full span 2021-26 t (NW,
  5 lags) on the book-level daily increment; 2020 (part of the gm1 span) reported as an
  episode check with COVID 2020-02-19..03-23 behaviour, not a pass gate.

**Pass bar (all must hold, at tier_hi AND at tier, for "adopt"; else "dead" unless 1-3 of the
next list hold -> "shadow").**
1. mean per-trade diff (alt minus auction) net > 0 in 2021-23 AND 2024-26;
2. placebo percentile >= 95 in both halves;
3. book (V7 raw, corr .7) increment positive in both halves and 2016-20 holdout not negative;
4. Newey-West (5 lags) t >= 2.0 on the book increment 2021-26;
5. edge-halves and P(DD>50% in 5y, $3k+$1k/mo, after 35% tax) not worse than the base;
6. still positive with each leg's mean contribution halved (growth.eh-style stress);
7. wash-sale / account structure unchanged (exit timing does not affect the pick, the account
   split or the guard), so items 5-7 re-check via the book only.

**Variant count for deflation:** A: 5 pre-registered + any post-hoc shadow-only add-ons;
followed by Study B variants (2) + dead-by-prior ideas (5, zero variants). Baseline N = 559.

**Date stamp (output of `date`, before any variant number):** Tue Sep 29 01:33:38 PDT 2026
(correction to an earlier placeholder in the first save: 01:41:04 was written from the session's
earlier `date` output at 01:26:38; the authoritative stamp is this 01:33:38 reading, which precedes
every variant run below. Study B's line inherits the same stamp.)

## Pre-registration — Study B: taxable V6 on the raw pool

**Variants (2).**
- A1t: V6 (SPY/QQQ "either" trigger at 15:40, close auction -> next open) funded ONLY by the
  idle IBS half, on the V7 base book (1.0x, cap .10, conv .5), raw pool.
- A2t: same, funded from ALL idle overnight money (idle IBS half + night-leg unused), cap the
  overnight gross at 1.0x, whole shares, Roth F3-style FOMC overlap NOT added (F3's taxable
  filler stays separate; on overlap days F3 keeps priority, both pre-registered).

**Costs.** V6 leg: 1bp/side (tier) and 3bp/side (tier_hi) as in add. 27's taxable test; the
night leg at 3bp flat ("measured") / tier / tier_hi reading the raw pool.

**Pass bar (inherited, restated on the raw pool).** Both halves positive at 3bp and tier_hi;
2016-20 holdout not worse (Sharpe); placebo (same trigger count on random dates, 200 draws,
exposure-matched) >= 95th pct in both judged halves; NW t (5 lags) of the daily book increment
>= 2.0 over 2021-26; EH and 5y MC ($3k+$1k/mo, 35% tax) P(DD>30%) <= 15% and P(DD>50%) <= 5%
(taxable bound); skip if either half fails.

**Date stamp (output of `date`):** Tue Sep 29 01:33:38 PDT 2026 (same run as above; see correction note)

## Amendment — Study C: tilt-v2 raw restatement (pre-registered before any number)

`date`: Tue Sep 29 01:50:46 PDT 2026 (added before ANY of Study C's variant numbers were computed).

**Hypothesis.** `signals.night_tilt_v2` (addendum 23, built OFF, borderline on the adjusted
pool: +31bp per sd of yesterday's return, t 2.0/2.6 per half, fitted on 2021-23 only) restated
on the RAW night pool at tier and tier_hi. The raw pool removes the sub-$5 lookahead trades the
adjusted pool allowed (add. 30), so a pick-tilt fitted on 2021-23 could behave differently.
Winner-prev-day inside the same -8%/same-day/corr-0.7/price>=5 pool.

**Variants (2, pre-registered).**
- C1 V7 1.0x cap .10 conv .5 with tilt = night_tilt_v2 (k .25, the shipped default), RAW pool.
- C2 moderate as-built 1.0x cap .15 conv .5 with tilt = night_tilt_v2, RAW pool.
(Each also reported with the shipped v1 tilt as the direct baseline.)

**Controls.** Placebo: the same weights with the third input's ORDER shuffled within the day
(the second input kept), 200 draws, mean per-day book increment; both halves >= 95th pct.
Fit 2021-23 / judge 2024-26 and the reverse (weights are already frozen from 2021-23; the
fit/judge test applies to the ROBUSTNESS bar: both halves positive).

**Pass bar.** v2 beats v1 in BOTH halves at tier AND tier_hi on the same book; placebo
>= 95th pct in both halves; NW t (5 lags) >= 2.0 of the daily increment over 2021-26; the
2016-20 holdout (via the 2020 raw rebuild where the tilt's boosted inputs can be rebuilt)
not worse than the v1. Adopt requires ALL; the t/placement pattern add. 23 already showed
(+31bp per sd) means the realistic outcome is shadow at most — this run's job is the
RAW-pool restatement, and the verdict counts in our N. (counts as 2 variants)

## Amendment — Study D: MNQ (micro-futures) vs the QQQ noise leg, 1256 vs 35% ST tax (pre-register)

`date`: Tue Sep 29 02:04:34 PDT 2026 (the authoritative stamp; before any Study D number).

**Hypothesis.** The QQQ noise leg's edge carries to MNQ (add. 25, both halves, placebo,
stress) and 1256's 60% LT / 40% ST blended rate beats the all-short-term ETF leg after tax;
the blocker is contract size (one MNQ is ~82 x QQQ). Question: at which taxable equity does
moving the noise leg's QQQ half to MNQ add after-tax growth at $3k/$15k/$30k/$50k/$100k + $1k/mo,
and the risk (P(DD>50%) or a forced single-contract leverage over the bound)?

**Data.** MNQ stands in via QQQ minute bars (add. 25's stated PROXY: NQ ≈ 41 x QQQ, MNQ = $2 x
NQ, so notional ≈ 82 x QQQ; the Globex session, roll and basis are NOT modelled — the proxy
only sees the ETF's 09:30-16:00 session, so overnight gains/losses beyond the ETF's gap are not
in the series). QQQ/SMH noise leg uses the same live rule (swingtrader/daily/signals) at
0.5bp/side and 1.5bp stressed; MNQ busy per side = comm + ticks×tick value on the notional
(add. 25's tier $1.00 + 1 tick ≈ $0.50 = $1.50/side; tier_hi $1.50 + 2 x $0.50 = $2.50;
stress $1.50 + 3 ticks). The raw-price sim (load_sim(raw_price=True), corr 0.7) supplies the
book's other legs exactly as the last rounds did.

**Variants (4, pre-registered).**
- D1 V7 raw with noise = QQQ(0.5) + SMH(0.5), 3bp/tier/tier_hi night costs (base rows).
- D2 the same book with the QQQ half shifted to MNQ (asset = the MNQ leg's own return,
  futures costs per side, vol-target kept, same 0.02 target, cap 0.75-1.5 as the books run).
- D3 the MNQ leg with the Kelly x1.5 noise target (0.03) as the add. 40 shadow spec.
- D4 the whole-contract machine (futures.account_mc): contract granularity + margin at the
  REAL sizes ($15k/$30k/$50k/$100k) for D1 vs D2 and D3, after tax at the user's bracket
  (ST 35%, LT 20%, so 1256 blended = 0.26): Monte-Carlo medians, P(DD>50%), and "forced
  single-contract leverage" flags.

**Pass bar.** a) the MNQ leg's gross is not negative against QQQ at any cost model
(the swap only wins if futures costs per side < the ETF's at the same gross — a cost study,
not a new signal); b) the AFTER-TAX increment > +0.5pp at the sizes where a contract fits
the target (whole contracts); c) both halves positive and 2016-20 not worse; d) the
contract-granularity MC's forced-lev median: any equity where the forced single contract
exceeds 2x equity is OUT of range (not a candidate). Adopt only as a spec/gate, not as a
live switch at sizes where the contract does not fit.

(Tax modelled per add. 32: ST 35% on the non-1256 net, LT 20%, so 1256 blended = 0.6×0.20 +
0.4×0.35 = 0.26; 1256 net losses carry forward but can ONLY offset 1256 gains (no ordinary
deduction except the $3k NLL election); ETF legs keep the T3 model. No wash-sale issue: MNQ
is not a security and shares no symbol with the taxable legs.)

**Variant count for deflation:** D1-D4 (4; D4 is one run at 4 equity sizes × 2 Leg options x 3
cost tiers = a sensitivity table, reported as ONE variant per book row; count 4). N goes to
568 + 4 = 572.

## Amendment — Study E: a GBM picker on the organic 15:40 features (pre-register)

`date`: Tue Sep 29 02:14:15 PDT 2026 (the authoritative stamp; before any Study E number).

**Hypothesis** (per the reply's proposal #1). A gradient-boosted model (sklearn
HistGradientBoostingRegressor) predicting the night pick's close→next-open net return,
trained ONLY on features computable at 15:50 from data already held, with purged/embargoed
walk-forward, produces named bump more than the shipped v1 tilt is able to capture, i.e. the
raw-pool book's 2024-26 grows with it in BOTH halves, placebo-beaten. Add. 23's 9-feature
linear tilt is not this test: it fit a monotone-in-quintiles linear form and its raw-pool
2024-26 verdict is negative (Study C).

**Data / features (all honest at 15:50, no lookahead).** From `data.night_candidates(raw=True)`
(the 20,501-candidate raw pool 2020-10..2026-09) joined to the big split-adjusted daily panels:
  f1  day_ret (the candidate's day move, the pool's -8% filter)
  f2  ibs_last = (p50 - L50) / max(H50 - L50, eps)   (the pool's ~0.1 gate)
  f3  gap = open / pc - 1   (the day open from the big panel)
  f4  pm_move = p50 / open - 1                    (the day's move by 15:50)
  f5  late = (p50 / (pc and the 15:30 bar...))     NOT available here: use (p50 - pc) share of day_ret
  f6  width = (H50 - L50) / p50                   (the late window's range)
  f7  p50 (log price)
  f8  vol20, f9 ret20 (20d momentum), f10 adv (log)
  f11 dopen/p50-1 = the day open's gap share of the day's move
Labels = ret (close→next open) net of 2 × book.cost_bps("tier on the RAW price") per side
(the raw pool's own convention). Missing amenities -> np.nan handled in-model.

**Variants (3, pre-registered).**
- E1 GBM: HistGradientBoostingRegressor (depth-3, lr 0.05, 300 trees, min_samples_leaf 200),
  inside-day-2021..-23 fit, 2024-26 judged; 30-calendar-day embargo between the fit's last
  pick and the judge's start. Reverse fit (2024-26 -> judge 2021-23) reported too.
- E2 GBM with ONLY the add. 23's 9-feature honest panel (the add. 23 linear model's own
  feature set), to separate "more model" from "more features".
- E3 linear ridge on the same big feature panel (the interaction-free reference).
All three produce per-name predicted edge; the book leg's tilt uses the SAME weight form as
the shipped tilt: w = clip(1 + k * pred/sd_pred, 0.25, 2), mean-normalized per day; the sizing
reuses the shipped night_sizing's frac and the whole-share/everything else unchanged.

**Controls.**
- Placebo: the same weights with the predictioN's VALUES shuffled WITHIN THE DAY (the
  model's structure destroyed), 200 draws; the actual daily book increment must beat the
  95th percentile in BOTH halves.
- Batching: fit 2021-23 vs the shipped v1 tilt AND the equal-weight base, both as book rows.
- The 2016-20 holdout is NOT computable from this pool (the honest 15:50 reconstruction
  starts 2020-10), so the verdict caps at SHADOW by construction (as in add. 23). This study
  counts; the PROGRAM's adopt bar unmodified (no holdout ⇒ no adopt).

**Pass bar.** 1) the book increment (E vs the shipped v1 tilt) > 0 in BOTH halves at tier AND
tier_hi on the raw pool; 2) placebo ≥ 95th pct in both halves; 3) NW t (5 lags) ≥ 2.0 over
2021-26; 4) edge-halves not worse and P(DD>50%) not worse than the shipped book; 5) still
positive with each leg's mean halved. Verdict: all → the best a NEW STUDY can be is SHADOW
(no holdout); 1-3 hold but a later bar fails → dead.

**Variant count for deflation:** 3 model variants × the book rows; N = 572 + 3 = 575.

## Amendment — Round 2: two more studies, pre-registered before any number

`date`: Tue Sep 29 02:32:51 PDT 2026 (the authoritative stamp, before any F/G number).

### Study F: IBS on non-equity ETFs (a different asset class, the same mechanics — NOT in the dead list)

Checked first against the dead list: the intraday diversification row (add. 20/26a) killed
the *intraday* noise rule on TLT/GLD/IWM/XLE/USO/EEM/SPY, and add. 34's "SPY−TLT MTD" as an
IBS *sizing* dial is a "watch" (not a test of IBS itself on those instruments). The phase-1
swing study noted IBS holds on defensive/bond/commodity ETFs (12.7% CAGR, line 615) but was
never judged at the daily book's live 09:15 timing and the whole-share account. Testing the
IBS rule (last bar's IBS < 0.2, open -> open, momentum top_k among the candidate universe)
on a non-equity universe:

- Universe (fixed): TLT, IEF, IEI, TLO, GLD, SLV, IAUF, USO, UUP, HYG, LQD, EMB, KIE, XLP, XLU,
  DBC, EZU, FXE, EWZ, EWJ, EEM, EFA, VGK — every liquid non-3x-ETF in etf_daily 2016+, plus
  3x pairs on the pool. Momentum top-3 of 12 rolling 12-1 windows, whole shares, 1bp/side
  (tier) and 3bp (tier_hi).
- Variants (3): F1 the non-equity ETFs as an ADDITIONAL 12-ETF IBS pool (3 top picks),
  F2 the non-equity IBS leg REMOVING the equity IBS picks that share the day (dedupe),
  F3 non-equity IBS as a book-level substitute for the equity IBS half.
- Pass bar: the increment vs V7 (raw pool, corr .7) positive in 2021-23 AND 2024-26 at
  3bp AND tier_hi; placebo (random-day same-count) ≥ 95 pct in both halves; NW t ≥ 2; holdout
  2016-20 not worse; no look-ahead (12-1 momentum, IBS on the last full bar only).

### Study G: the "LLM idea" — a local semantic classifier on add. 12's news corpus

Data: `night_news.pkl` (17,552 point-in-time headline rows, `heads` text, the keyword
labels, the next-day returns). Add. 12's keyword parser got every category ≈ 0 excess
except "dilution"'s sign against intuition (t 1.6, n 1.4%). THE TEST: does an LLM's semantic
classification of the same headlines produce categories, the keyword machine's, that split
the next-open P&L (the meaning-level "is this a forced-flow story vs a real informational
shock")?

- I (the session's LLM) label a stratified sample of 400 headline rows while blind to the
  keyword class and the returns: label ∈ {"B1 dilution/whatever-share", "B2 drop-in-night-hop",
  "C macro-day", "D risk-warning", "E FDA/trial-claustrophobia", "F mere-news"}; classify
  ("the news STATED something material about the name" vs "it described the market flow").
- Sample power: at 40bp/trade sd and a target 15bp effect at 80% power, 400 rows per class
  ≈ ± 50bp confidence interval; the test CAN flag big effects only; note explicitly that a
  <30bp/trade effect is undetectable in-sample and the honest report is "power-limited".
- The rule: the LLM's classes' P&L comparison stays; the "dilution trades bounce shifted
  their mean" pf add. 12's table row must be regenerated by the LLM's groups to test.
- Verdict gating: at power limits the honest verdict is "report" (not adopt/dead), and the
  add. 12 conclusion remains the default: prospective at ~$0 edge.

Both studies' variant counts add to the program's N: F 3 + LLM 1 labelled sample (report,
0 rule variants) ⇒ N = 575 + 3 = **578**.

## Amendment — Round 3: Study H, F2's tie-break resolved + a smaller defensive sleeve (pre-register)

`date`: Tue Sep 29 09:52:46 PDT 2026 (the authoritative stamp; no Study H number below the stamp). Round 3's question, following round 2's finding: the F2 (the equity-18 + the 10
non-equity) IBS pool's +2.7..+5.5pp/yr depends on `sg.momentum_top`'s tie-break, which
today is the listing frame's own order. To test a version whose tie-break is deterministic
and ORDER-independent (the kind a live config could ship):

- H1 F2 with an alphabetical pool order (deterministic; the implementation sorts the pool
  before momentum_top; nothing else changes) at 3bp/tier/tier_hi — the pass bar identical
  to F2: both halves positive, placebo-200 >= 95 in both halves, NW t >= 2, the 2016-20
  holdout not worse, EH and the 5y MC draws not worse.
- H2 SMALLER: the equity-18 + a 4-sleeve of the non-equity (the pool = 22 with the non-
  equity sleeve at a 0.25 share of the leg: this tests whether the result needs a 24-pool
  or a smaller budget). Same pass bar.
- H3 the corr-dedupe variant: the same 24-pool with the momentum top-3's within-pool
  dedupe (drop a tie whose 20-day Pearson r > 0.9 with a higher-ranked pick, a live
  signal-mechanic already in the code base). Same pass bar.
- If H1 passes ALL its bars (both halves >=, placebo >= 95 both halves, NW t >= 2, holdout
  not worse, EH not worse) with the SAME value as F2's last review (+2-5pp/yr at tier),
  the verdict is STILL SHADOW (no 2020 rebuild, no 2016-20 minute holdout for the non-
  equity minute data): its own SHADOW-LOG spec carries over from study F's draft.
Variant count: H 3. N = 578 + 3 = 581.

## Amendment — Round 4: Study R, the Roth at $1,000 vs $3,000 sizing (pre-register)

`date`: Tue Sep 29 10:28:42 PDT 2026 (the authoritative stamp; no Study R number existed when this was written).

Question: at the Roth's real $1,000, how much of the daily book's backtest edge survives
whole-share rounding and the per-name cap? Schwab has no fractional API: night CLS buys are
`floor(per * w / price)` shares (`executor` night sizing), IBS/SGOV DAY buys go by notional but
SchwabAdapter floors `notional / ref_px` and refuses 0 shares. Live real-money also has the
1-share probe (`night_probe_max_usd` 150: a pick that rounds to 0 shares and costs <= $150
buys 1 share, while book cash lasts).

Roth book as modelled (limited-margin IRA, per the code): night 0.5 + IBS 0.5 = 1.0x, NO
intraday leg, NO conviction, NO borrowing (cash floor 0), tilt v1 (k 0.25), max_corr 0.7,
weekend x0.5, name cap 0.10 of the leg, raw prices, idle IBS half in T-bills (BIL proxy,
whole shares in the whole-share variants), no deposits. Not modelled: the roth_first wash
guard (look-alike swaps / blocked names) — it can only remove picks, so it biases toward
the Roth looking better than it is; flagged, not fixed.

Variants (the program's N counts each configuration):
- R1-R4 whole shares + probe (live rules) at $1k / $2k / $3k / $5k.
- R5-R8 fractional (the sim's `whole=False`) at the same four sizes (the "full edge" reference).
- R9 $1k whole + probe with the night name cap 0.15 (the moderate10 cap).
- R10 $1k whole, probe OFF (what the probe is worth).
Each at tier and tier_hi costs (costs are a stress, not extra variants). N = 581 + 10 = **591**.

Metrics, 2021-23 / 2024-26 / full:
- PRIMARY, fixed capital (the book is reset to its size each day; P&L withdrawn): CAGR,
  Sharpe, maxDD of the daily return on that fixed capital. This isolates account size.
- the gap G(size) = CAGR(whole+probe) - CAGR(fractional) at the same size, pp/yr, and the
  annualised tracking error of the daily return difference.
- night picks skipped (0 shares after probe) as % of picks; night leg notional deployed as
  % of the leg budget; probe share of night trades.
- SECONDARY, compounding from the start size, no deposits (the account as it would grow).
- MC: 21-day block bootstrap of the fixed-capital daily returns (2021-02..2026-09), 4000
  paths x 1260 days (5y), the SAME block draws for every variant (paired), compounding
  from the start size: p10 / median / p90 terminal, P(DD > 30%), and the paired median of
  (terminal whole / terminal fractional).

Decision rule (fixed before any number):
- G($1k) at tier, full period, >= -2.0pp/yr (i.e. rounding costs <= 2pp/yr) -> NO ACTION:
  the Roth runs fine at $1k.
- G($1k) < -2.0pp/yr -> sizing matters. Recommend topping up DAILY_ROTH capital to the
  smallest tested size with G >= -2.0pp/yr at tier (within contribution limits), and report
  G at tier_hi. The MC paired ratio must agree in sign, else "report" only.
- R9 (cap 0.15 at $1k) is only a candidate if it improves $1k whole+probe CAGR by >= 1pp in
  BOTH halves at tier AND tier_hi with maxDD no more than 3pp worse; even then SHADOW/report
  (moderate10 already exists as a profile; this is not a new rule).
- R10 is descriptive (no decision).
- Sanity: $3k fractional with the Roth settings must be within 0.5pp/yr of the same
  replay run through the unmodified `B.Sim.day_pnl` (whole=False, noise off, conviction 0);
  if not, the study is void.


## Amendment — Round 4b: Study P (probe off), stamped Tue Sep 29 10:34:59 PDT 2026

Written before any Study P number. R10 found the 1-share night probe (`night_probe_max_usd`
150) hurts at $1k (post-hoc). The probe's purpose (measure open-sell cost on
expensive names) is served: live open sells ~0bp over 34 exits. Study P tests it at the
sizes the live books actually run.

- Variants (2): whole shares with probe $150 vs whole shares, no probe; sizes $1k, $2k,
  $2,259 (brokerage today), $3k, $5k (sizes are one test, not separate variants).
  Same model as Study R (`roth_sizing.day`, 1x, name cap 0.10, raw prices, capital reset daily).
- Costs: tier and tier_hi. Periods 2021-23, 2024-26, full.
- **Decision rule:** switch the probe OFF (`daily.night_probe_max_usd: null`) if no-probe is
  >= probe in CAGR in BOTH halves at BOTH cost tiers at $2k, $2,259 and $3k, and its maxDD
  is not worse by more than 3pp at any of them. Otherwise keep it.
- N: +2 -> 593.


## Amendment — Round 5: Study S, short the night picks after the open (pre-register)

`date`: Tue Sep 29 19:47:04 PDT 2026 (the authoritative stamp; no Study S return, in any period, was computed
when this was written).

Motivation (existing numbers, not new): exitt.py shows the shipped night pick's return
falls from +20.1bp net at the auction to -21.5bp net by 10:30, i.e. the picks drift DOWN
after the open. Hypothesis: shorting the same picks after the long is sold earns that
post-open drift (the overnight/intraday "tug of war" reversal). Taxable brokerage only
(the IRA cannot short).

Sample: shipped night picks, `B.night_days(raw_price=True, max_corr=0.7)` (the V7 pool),
next session d+1 with am1 minute bars (SIP 09:30-10:31, adjustment all). Basis check: the
minute-0 open must match the daily-panel open of d+1 within 0.5%, else not scored (a skip).
Periods 2021-23 / 2024-26 / full (2020-11..12 is in no half).

Tradability filters (fixed now, applied to every variant and to the placebo):
- SEC Rule 201: a name whose day-d LOW is <= -10% vs close d-1 (daily panel) is SSR on
  d+1: a market/auction short is not accepted -> untradable, scores 0 (not dropped: it
  stays in the book denominator as idle money). Reported: the SSR share of picks.
- Borrow: no data. Not modelled in the mean; the book increment is reported at 100% / 60% /
  30% locate rates (a random, seeded fraction of the tradable names shorted). Intraday
  shorts closed the same day pay no borrow fee (Schwab), so fee = 0.

Variants (8; N = 593 + 8 = **601**):
- Entry A = the official open of d+1 (auction; idealised: Schwab will not take a sell-short
  in the same auction as the long's sell). Entry B = the close of minute 09:30 (the first
  minute bar, i.e. after the auction fill is known) — the executable version.
- Cover at the close of the last minute before 09:45 / 10:00 / 10:30, or at the d+1 CLOSE
  (daily panel; the close auction).
- S1-S4 = A x {09:45, 10:00, 10:30, close}; S5-S8 = B x the same four.
Short return per name: r = 1 - P_cover / P_entry.

Costs per side (tier table `B.TIERS`, by raw price / ADV, as the night leg):
- auction entry or close-auction cover: the tier cost.
- continuous-session entry (09:31) or cover (09:45/10:00/10:30): tier + 5bp (tier) and
  tier_hi + 15bp (tier_hi stress) — small caps' quoted spread, not the auction.
Net per-trade = r - entry cost - cover cost.

Book increment (the short leg reuses the capital the night leg frees at the open, so it
is an add-on inside the day, at the night leg's own size): per day
inc = 0.5 * sum_i min(frac, 0.10) * net_i over the picks (untilted; SSR / unscored = 0).

Placebo (200 draws): each scored pick replaced by a random NON-pick name from the same
d+1 am1 file, same vol20-decile, that passes the same SSR/basis filters; the pass is the
mean per-trade net of the variant >= the 95th percentile of the placebo means.

Pass bar (every one required, at BOTH tier and tier_hi, 100% locate):
(1) mean net per trade > 0 in BOTH halves; (2) placebo >= 95th pct in BOTH halves;
(3) book increment positive in both halves and NW t (5 lags) >= 2.0 over 2021-26;
(4) still positive in both halves at 30% locate (scale check only).
Verdict: a variant passing everything -> SHADOW only (borrow / locates / SSR at the auction
are untested by any data we have; a live shadow must log Schwab's locate answer per pick
before any money). An A-only pass (auction entry) with B failing -> "report": not
executable. Otherwise DEAD, and the "Do NOT redo" list gains "short the night picks
after the open".


## Amendment — Round 6: Study T, SEC offering filings on the night picks (pre-register)

`date`: Tue Sep 29 19:56:41 PDT 2026 (the authoritative stamp; no Study T return, split or count of event
picks, in any period, was computed when this was written).

Motivation: addendum 12's headline parser tagged "dilution / offering" on only 1.4% of
night trades, and that bucket bounced MOST (+72bp, excess +38bp, t 1.6): against the
intuition that new supply keeps selling. Headlines are a thin, noisy proxy. SEC EDGAR
filings are the primary record, with point-in-time acceptance timestamps. THE TEST: does
an offering-type filing by the issuer, accepted between the previous close and the
15:40 decision, split the night pick's next-open P&L? Two-sided: add. 12 favours
"bounces more" (discount-recovery toward the offering price); the naive prior is
"bounces less" (supply overhang).

Sample: shipped night picks, `B.night_days(raw_price=True, max_corr=0.7)` (V7 pool, as
Study S). Per-trade net = ret - 2 x cost_bps(tier | tier_hi). Halves 2021-23 / 2024-26;
2016-20 is a holdout reported only if the pool covers it.

Mapping (fixed now; applied the same to every pick): symbol -> CIK by EDGAR's entity
index (exact ticker match). A pick is MAPPED only if that CIK's `entityType` is
"operating" (ETF/ETP trusts file 424B3 continuously; excluded) AND it has a periodic
filing (10-K, 10-Q, 20-F, 40-F, 6-K) accepted within 400 days before d (guards against
reused tickers). Unmapped picks leave both groups; the mapped share is reported by year
(delisted names are likely under-mapped: a survivorship caveat stated with the result).

Events (acceptance time in (16:00 ET on d-1, 15:40 ET on d], timezone of EDGAR's
acceptanceDateTime verified against filingDate before use):
- E1: a 424B prospectus (424B1-424B8): an offering priced or a resale registered.
- E2: an original registration S-1, S-3, F-1 or F-3 (no /A amendments).
- E3: E1 or E2.

Statistic: excess_i = net_i - the mean net of the OTHER picks the same night (nights with
>= 2 picks). t = mean excess of event picks / SE clustered by night. Placebo: event labels
permuted among mapped picks within each night, 1000 draws; percentile of the real mean.

Variants (6; N = 601 + 6 = **607**): {E1, E2, E3} x {DROP the event picks (weight 0),
DOUBLE them (weight min(2 frac, 0.10))}. Book increment per day
inc = 0.5 * sum_i w_i * net_i (as Study S), rule minus baseline, pp/yr.

Pass bar (all, at BOTH tier and tier_hi): (1) event n >= 100 over 2021-26 (else
"power-limited: report"); (2) excess has the rule's sign in BOTH halves (negative for
DROP, positive for DOUBLE); (3) t in the rule's direction >= 2.0 over 2021-26;
(4) placebo >= 97.5th pct in that direction; (5) book increment vs baseline > 0 in both
halves. A 2016-20 sign flip downgrades a pass to "watch".
Verdict: pass -> SHADOW only (the live bot logs the flag per pick for >= 100 event
picks; no money). Otherwise DEAD and the do-not-redo list gains "SEC offering filings
as a night-leg filter". Dollars are reported at $2.3k / $25k / $100k / $500k, with the
event picks' order size as % of ADV at each (CLAUDE.md: balances are temporary).


## Amendment — Round 7: Study U, where the night leg's edge lives (pre-register)

`date`: Tue Sep 29 20:34:25 PDT 2026 (stamped after Study T's side observation, mapped −10.6bp vs unmapped
+14.6bp at tier, and before any return by the classes below was computed).

Classes of each V7 night pick 2021-26 (Study T's EDGAR cache and mapping):
- ETP: the ticker maps to a CIK whose entityType is not "operating", or to an ETP issuer
  (SIC 6221, or > 100 424B/yr: ETNs). KNOWABLE at d (a 15:40 lookup) -> rule-eligible.
- OPER-LIVE: operating CIK with a periodic filing accepted on/after 2026-03-01.
- OPER-GONE: operating CIK whose last periodic filing is before 2026-03-01 (stopped
  filing: delisted/acquired/went dark). LOOKAHEAD: report only.
- UNMAPPED: no CIK by today's ticker index (mostly renamed/delisted). LOOKAHEAD: report only.

Report (0 variants): count, mean net per trade (tier, tier_hi) and share of the leg's total
net P&L by class and half; for OPER-GONE the median sessions from d to the last filing.

Rules (2 variants; N = 607 + 2 = **609**), book increment as Study T (0.5 x w x net):
- U1: drop ETP picks. U2: ETP picks only (drop every non-ETP pick).
Pass (all, at tier AND tier_hi): rule minus baseline > 0 in both halves; NW t (5 lags) of
the daily increment >= 2.0 over 2021-26; placebo: drop the same number of picks at random
within each night (200 draws), rule >= 95th pct. Verdict: pass -> SHADOW; else DEAD.


## Amendment — Round 8: Study W, leveraged ETFs inside the night leg (pre-register)

`date`: Tue Sep 29 20:38:42 PDT 2026. Known before writing (Study U diagnostic, w-weighted GROSS): the
EDGAR-"unmapped" bucket (mostly LETFs) +19.5 / +44.9bp 2021-23 / 2024-26 vs US operating
stocks +21.8 / +16.7. No return by the classifier below, and no vol-normalised number, has
been computed.

Why raw bp is not the test: a 3x fund returns ~3x per trade, so higher gross bp can be
leverage (risk per dollar), not edge. The test is RISK-ADJUSTED.

Classifier (point-in-time, fixed now): LETF = `new_listings.etf_kind(sym) == "lev"` AND a
leverage factor parsed from the name: "<n>X"/"-<n>X" -> n (sign negative with BEAR / SHORT /
INVERSE / "-"), ULTRAPRO -> 3, ULTRA -> 2, ULTRASHORT -> -2, ULTRAPRO SHORT -> -3; |L| >= 1.5
or L = -1 (plain inverse). Option-income / YieldMax / anything unparsed is NOT LETF. Ticker
reuse guard: d must fall inside the ticker's LAST listing segment (`cache_new_listings_seg`,
add. 36), else not LETF. Subclass: single-stock LETF (name names one company: "LONG <X>",
"<X> DAILY", T-REX/TRADR/GRANITESHARES/DEFIANCE issuers) vs index/sector LETF.

Primary per-trade test (report + gate): z = ret / vol20 (the pick's own 20d daily sd).
LETF z vs non-LETF picks in the SAME vol20 decile and half (pooled deciles), difference and
t clustered by night, per half. Mechanism check (report only): mean z by L(L-1) group
{2: 2x & -1x, 6: 3x & -2x, 12: -3x}; the rebalance story predicts z rising with L(L-1).

Rules (2 variants; N = 609 + 2 = **611**), book increment inc = 0.5 x w x net, V7 picks 2021-26:
- W1: drop LETF picks.
- W2: LETF picks at 2 x weight with a 0.20 name cap for index/sector LETFs (single-stock
  LETFs stay at 0.10: their underlying is one company).
Pass (all, at tier AND tier_hi): (1) z difference has the rule's sign in both halves
(negative for W1, positive for W2) with t (2021-26) >= 2.0 in that direction; (2) rule minus
baseline > 0 pp/yr in both halves; (3) NW t (5 lags) of the daily increment >= 2.0;
(4) placebo, 200 draws: the same operation applied to the same number of random non-LETF
picks of the same vol decile in the same night (or the nearest night when absent), rule >=
95th pct; (5) the book's max drawdown under the rule not worse than baseline by > 2pp.
Verdict: pass -> SHADOW; else DEAD. Capacity reported at $25k/$100k/$500k (% of ADV).


## Amendment — Round 9: Study V, night-leg capacity at the auctions (report; 0 variants, N stays 611)

`date`: Tue Sep 29 20:40:54 PDT 2026 (no impact-adjusted number computed yet).
Picks: V7 2021-26 with a 16:00 bar on d (lm1: closing cross + that minute) and a 09:30 bar on
d+1 (am1: opening cross + that minute); bar volumes OVERSTATE the auctions, so every capacity
number here is a best case. Order at equity E: Q = 0.5 x E x w (book weights). Participation
p = Q / bar dollar volume, each side. Impact per side = Y x sigma_daily x sqrt(p), Y in {0.5, 1}
(square-root law; auctions assumed no deeper than continuous trading). Live cost 1bp/side.
Report at E = $2.3k, 25k, 100k, 250k, 500k, 1M, 2.5M, 5M: weighted net bp/trade, night-leg
pp/yr, $/yr, share of picks with p > 10% / 25% of either bar; the E where the net edge halves and
where it reaches 0. Also the "sell the open over the first N minutes" alternative is NOT tested here.


## Amendment — Round 10: Study X, an impact-optimal per-name cap for the night leg (pre-register)

`date`: Tue Sep 29 20:47:57 PDT 2026 (no capped number computed). Follows Study V (the leg's income collapses with size).
Rule: each night order q_i <= q*_i = ADV_i x (g / (3 x Y_rule x sigma_i))^2, sigma_i = vol20_i/sqrt(252),
g = 22bp (the weighted gross 24.6 minus live 1bp/side, rounded down). q* maximises
q (g - 3 Y sigma sqrt(q/ADV)) under the square-root law summed over both auctions (each side
Y sigma sqrt(q/ADV); the 3 is 2 sides x the 3/2 from the derivative). Money a cap frees stays
in cash (no reallocation in this study).
Variants (3; N = 611 + 3 = **614**): Y_rule in {1, 2, 4}.
Judged under Study V's four truth models (A/B x Y 0.5/1), E in {$25k, 100k, 250k, 500k, 1M, 5M}.
Adopt the variant that (1) is inert (changes no order) at $2.3k, (2) never has lower night-leg
$/yr than the uncapped leg at any (E, truth model), (3) has non-negative $/yr at every E under A/Y 1
and B/Y 0.5; among passers, the highest minimum $/yr at $1M across the four truths.
Adoption = ship in the live config (it is inert today), NOT a claim of new edge.


## Amendment — Round 11: the 23/5 regime check (pre-register; monitoring, 0 variants, N stays 614)

`date`: Wed Sep 30 02:03:15 PDT 2026. Nasdaq and NYSE Arca plan 23/5 trading from Sun 2026-12-06 21:00 ET (SEC-approved,
still conditional on data-system readiness). The 09:30 opening and 16:00 closing auctions and the
official close are unchanged; a 21:00-04:00 overnight session is added (no auctions, no market
orders). The night leg's close -> open trade is unchanged mechanically, but overnight price
discovery may move into that session and thin the 09:30 auction. No post-launch data exists.

Launch = the first regular session on/after the actual go-live date (expected Mon 2026-12-07).
Tests, run once ~60 sessions of post-launch SIP data exist (about March 2027), V7 raw pool:
1. Night-leg gross close->open per trade (book weights), post-launch vs 2024-26: difference and
   t (clustered by night). FLAG if post < 0.5 x 2024-26 AND t <= -2.0.
2. Opening-auction depth: median 09:30 SIP minute $ volume / ADV20 of the picks, post vs the
   Study V baseline (1.6%). FLAG if it falls below 1.0% (capacity model: Y rises ~sqrt(1.6/x)).
3. Live: make review sections 4/8 on post-launch live night trades (the same-trade gap and the
   impact fit) and the pre-registered kill rules, unchanged.
Action: any FLAG -> the night leg goes to SHADOW (daily.night_weight 0 with the shadow log) pending
a pre-registered study of the new regime; no FLAG -> nothing changes. The canaries in code
(signals.regular_clock / clock_drift / bar_semantics_issues / official_open) only warn; they never
change sizing.


## Amendment — Round 12: Study Y, the whole book's rate at $25k-$5M, after tax, vs an index (report; 0 variants, N stays 614)

`date`: Wed Sep 30 13:39:38 PDT 2026 (no Study Y number, at any size or in any period, was computed when this
was written). Motivation: long-horizon planning needs the book's return AT SIZE. Studies V/X and
scale_legs_diag.txt give each leg's impact alone; nothing combines them into the book's rate, pre- and
after-tax, beside the thing the surplus would otherwise go to (a held index fund). The planning tables
used a 10%/yr placeholder above $250k; this study replaces it with a measured number.

Legs (raw pool, V7 live-today settings: 1.0x, IBS 0.5 + night 0.5, no conviction, weekend 0.5),
2021-26 and halves 2021-23 / 2024-26 (`night_filings.PER`), at CONSTANT equity E (the rate at that
size, deposit-free), fractional shares (whole-share rounding is a small-account effect, reported at
$2.3k only), E in {$2.3k, 25k, 100k, 250k, 500k, 1M, 2.5M, 5M}:
- Night: Study X's per-trade table (w = min(frac, 0.10), q = 0.5 E w) with the Y_rule 4 cap
  (`signals.night_impact_cap`, g 22bp; the live plan from ~$25k). Net = ret - 2 x 1bp - impact under
  the truth model. Money the cap frees earns BIL that day.
- IBS: Sim's IBS trades; Q = 0.5 E / (names that day); impact per side Y sd sqrt(Q/ADV), 2 sides, with
  ADV and daily sd from scale_legs_diag.txt (last-12-month values, applied to the whole history).
- Noise: `book.noise_days`, Q = E x min(lev, cap) x share, impact per side Y sd sqrt(Q/ADV) times the
  day's `trades` (the same count the shipped cost charges per side).
- Idle: BIL, as Sim.

Truth models (fixed now): OPT = night A/Y .5 + ETF Y .5; CENTRAL = night A/Y 1 + ETF Y 1;
PESS = night B/Y .5 + ETF Y 1. A cost stress repeats CENTRAL with the night leg at `cost_bps(tier)`
in place of 1bp/side.

Books: B1 = as shipped (noise QQQ .5 + SMH .5, cap 1.5, all short-term). B2 = the scale plan
(scale_plan.md): noise QQQ-only (SMH retired), traded as MNQ, so the noise leg is taxed 60/40; its
returns use the QQQ series (futures proxy; MNQ impact taken as QQQ's, conservative). B3 = Roth:
B2's legs, noise cap 1.5 underlying (3x ETFs, as roth.py), no tax.

Tax (constant equity, so yearly $ gain = E x sum of the year's daily returns; losses carried
forward): MODERATE bracket ST 32% / LT 24%; TOP bracket ST 54% / LT 37% (fed 37/20 + CA 13.3 + NIIT 3.8).
The 60/40 rate = 0.6 LT + 0.4 ST.
Index: SPY over the same 2021-26 window, bought and held: pre-tax CAGR, and its after-tax equivalent
over H = 20 years with tax only at sale, ((1+g)^H (1-LT) + LT)^(1/H) - 1, per bracket.

Report, per E and truth: pre-tax %/yr (full, halves), after-tax %/yr (both brackets), and the index's
after-tax equivalent. Pre-registered readings (the only conclusions to be drawn):
1. The planning rate above $250k = B2 CENTRAL after-tax (MODERATE) at $500k and $1M (taxable), and
   B3 CENTRAL at $500k and $1M (Roth). These replace the 10% placeholder.
2. Taxable crossover E* = the smallest E on the grid at which B2 CENTRAL after-tax (MODERATE) falls
   below the index's after-tax equivalent (MODERATE); if at PESS it falls below at a smaller E, report
   both. Past E*, surplus taxable money goes to the index unless a later study finds a liquid edge.
3. Roth crossover likewise with B3 CENTRAL vs SPY pre-tax.
A reading that depends on 2024-26 alone (2021-23 below the index at that E while the full span is
above) is stated as such. All numbers replay the fitting period; they are upper bounds on the edge.


## Amendment — Round 13: the untested "use the day" ideas — Studies Z, AA, AB, AC, AD (pre-register; 5 variants, N 614 -> 619)

`date`: Wed Sep 30 14:24:20 PDT 2026 (no number from any of these five studies, at any size or in any period,
was computed when this was written; only data availability/date ranges were checked). Motivation: the user asked
for strategies that use the regular session / daytime capital beyond the live legs. Idle daytime cash earns
nothing (sweep and T-bill ETFs accrue on overnight balances), so the candidates are new daytime signals or new
instruments. Common: halves 2021-23 / 2024-26 (`night_filings.PER`); holdout 2016-20 wherever the data reach;
book = Study Y B2/B3 legs (scale_book.py) at constant equity; sizes $2.3k / 25k / 100k / 500k (+ $1M, 5M where
capacity matters); NW t = Newey-West, 5 lags, on daily increments; DSR reported against N = 619.

### Study Z — SPX put-writing as a taxable overlay (3 variants: Z1 PUT, Z2 WPUT, Z3 CNDR)
Data: Cboe daily index levels (cdn.cboe.com, `<SYM>_History.csv`, saved to data/research/program/cboe/): PUT
(monthly ATM SPX put, collateralized), WPUT (weekly ATM put), CNDR (monthly iron condor). The indices include
their T-bill collateral, so the overlay return is the EXCESS x = index daily return − BIL daily return (as
`Sim.bil`, aligned to the same day). Costs, not in the indices: per short/long option leg per roll, 2bp of
notional (tier) / 5bp (tier_hi), charged on roll days (PUT, CNDR: monthly third-Friday roll, CNDR 4 legs;
WPUT: weekly Friday roll); roll days = the index's roll calendar approximated by 3rd Fridays / Fridays.
Overlay: notional k = 0.5 x E of the (net) excess return added to the book's daily return (taxable B2 at
CENTRAL, Study Y), taxed 60/40 (§1256) with the noise leg's futures bucket. Margin check (report): SPX short
put Reg T ~20% of notional -> 0.1 E, inside the book's unused overnight buying power (book is 1.0x of a 2x
account). Pass (SHADOW), each variant, at tier_hi: (1) standalone net excess > 0 in 2016-20, 2021-23 AND
2024-26; (2) the book increment > 0 in both halves; (3) NW t of the increment, 2021-26, >= 2.0; (4) the
combined book's max drawdown not worse than B2's by > 3pp, and the overlay's worst 21-day loss 2007-26
(incl. 2008, 2020-03) <= 15% of E at k 0.5 (report the episode). Else DEAD. Report only (no variant): the
Roth version as a cash-secured sleeve (the Roth's cash is used by the legs, so it is a sleeve, not an overlay)
= PUT vs SPY as the destination for Roth money past the book's capacity ($2.5M, Study Y): CAGR, Sharpe, max
DD 2007-26 and 2016-26. Capacity: SPX options, no binding size on the grid (stated, not modelled).

### Study AA — box-spread financing of the overnight debit (report; 0 variants)
Sim (raw pool, V7 live-today) at lever_weight 0.65 (night 0.65 + IBS 0.65, i.e. 1.3x overnight) and at 1.0 each
(2.0x, the MAX profile). Overnight debit as `Sim.day_pnl`. Financing: Schwab margin at 12% (Sim default),
sensitivity 10% / 8% (large-balance tiers); box = BIL's trailing yield + 0.30%/yr. Report $/yr saved and pp/yr
at each size, both halves. Practical floor: XSP boxes ($10k face at 100-wide) -> from a ~$10k debit. Taxable
only; Roth cannot borrow. No change to live code (lever_weight is null today).

### Study AB — fade QQQ inside the noise band when the noise leg is flat (2 variants: θ 0.5, 1.0)
Same decision grid as the live noise leg (10:00..15:30 every 30 min, `sg.noise_*`, 14-day sigma). At a decision
where the noise rule's position AFTER its own decision is 0 and lb <= p <= ub: if |p / vwap − 1| >= θ x
sigma[m], open f = −sign(p − vwap). Exit at the next decision if p has crossed VWAP, or if the noise rule enters
(the fade closes first; the noise leg then trades as live), else at 15:59 close. One fade position at a time;
re-entry allowed. Size = the noise leg's vol-target lev capped at 1.5 x its budget share (QQQ 1.0), so it uses
buying power the noise leg is not using at that moment. Costs 0.5bp/side (Sim) and 1.0bp/side (stress).
Increment = E x lev x fade net return, added to B2. Pass (SHADOW), each θ, at 1.0bp/side: (1) increment > 0 in
2016-20, 2021-23 AND 2024-26; (2) NW t (2016-26) >= 2.0; (3) placebo, 200 draws: same entry times and exits,
random direction, rule >= 95th pct of the placebo mean; (4) the book's max DD not worse by > 2pp. Else DEAD.
Capacity: QQQ impact as Study Y ETF Y 1 x trades.

### Study AC — closing-auction imbalance (feasibility; 0 variants)
No historical Nasdaq NOII / NYSE imbalance feed is on hand, and neither Schwab nor Alpaca serves imbalance
messages live. Report only: sources and price (Nasdaq TotalView-ITCH / Databento, NYSE Imbalances), whether
Alpaca's auctions endpoint gives anything usable (auction prints only, not imbalances), and what a test would
need. No proxy signal is tested (a 15:50 price move is not an imbalance; last-half-hour momentum is dead, add. 27).

### Study AD — the noise leg as an intraday overlay on a held index (report; 0 variants; Study Y's "next")
Taxable account holds SPY 1.0x overnight, bought once (tax at sale, Study Y's H = 20 after-tax equivalent),
plus the QQQ noise leg on daytime buying power (vol target, cap 1.5; intraday gross <= 2.5x, inside Schwab's
~4x Intraday Margin Buying Power, add. 40), with Study Y's ETF impact (CENTRAL Y 1; OPT Y 0.5). Two tax cases:
noise as QQQ (short-term, taxed yearly) and as MNQ (60/40). Report at each size, 2016-26 and halves, both
brackets: after-tax %/yr of (a) SPY held, (b) SPY + noise overlay, (c) Study Y B2. Readings (the only
conclusions): 1. the sizes where (b) > (a) and where (b) > (c) after tax (MOD); 2. the size where the overlay's
after-tax increment over SPY halves (noise impact). A reading that holds in 2024-26 alone is stated as such.


## Amendment — Round 14: the taxable "index + noise overlay" switch (pre-register a decision rule; 0 variants, N stays 619)

`date`: Wed Sep 30 14:46:11 PDT 2026. Follows Round 13 AD plus a feasibility sensitivity run after it (scratch, reported in
study_z_ad_day_ideas.md "Round 14 addendum"): live `executor._gate` caps the noise leg at mult − overnight weight, so with
the index held at 1.0x on a standard (mult 2) margin account the cap is **1.0**, not AD's 1.5. At cap 1.0 the overlay
still beats B2 after tax (MOD) at every size in 2021-26, but with SPY at a 10%/yr long-run rate instead of 2021-26's
15.3% it is a loss at $25k (15.2 vs 15.9), a tie at $100k (14.9 vs 14.5) and a win from $500k (14.1 vs 12.5).

Decision rule (taxable account only; the Roth keeps the full book):
- **Trigger: taxable equity >= $100k** (not $25k: below that the gain depends on the index beating ~10%/yr), AND all of:
  (1) the noise leg has not fired a KILL_* rule and has >= 60 live sessions; (2) `make review` realised noise fills
  <= 1.5bp/side all-in; (3) the user re-confirms the drawdown up front: index-sized, −17% in 2021-26 and −31% in
  2020 on this replay, vs the book's −10%.
- **Switch:** the taxable night + IBS budget goes to one S&P 500 fund held 1.0x (a low-fee one, e.g. VOO/SPLG, bought
  once and not traded); the QQQ noise leg runs on daytime buying power at the live cap (1.0 at mult 2; 1.5 only if
  add. 40's `intraday_mult` is built and its gate passes); MNQ replaces QQQ past ~$160k (scale_plan.md). Nothing is
  realised by the switch (the night/IBS positions are overnight only).
- **Wash sales:** the held fund is never sold at a loss while the Roth's IBS leg trades SPY; a harvest, if ever, swaps
  to a different-index fund (VTI-style), the G4s look-alike rule.
- **No revert rule for the index:** if the noise leg is killed, the account is simply the held index (the fallback
  Study Y already recommends past $250k). Revisit the trigger at the ~March 2027 program review with live noise data.
Not built: build `daily.taxable_mode: book | index_overlay` (default book) when taxable equity nears $100k.


## Amendment — Round 15: Study AE, the anatomy of the biggest intraday swings and a held-out test of what predicts their direction (pre-register; <= 5 variants, N 619 -> <= 624)

`date`: Wed Sep 30 15:25:19 PDT 2026 (no swing-study number computed; only data coverage was checked: SIP daily panel
2020-10..2026-09, 13.9k symbols; broad-universe minute bars do not exist, so the study is open -> close).
Ask (user): study the biggest intraday swings and look for a common pattern that says "this will bounce".
Guard: patterns read off the largest moves select on the outcome; the same precursors (gap, volume, news)
precede big up AND big down days. So: describe on both halves, SELECT only on 2021-23, JUDGE only on 2024-26.

Universe, day d: every panel symbol with 21 prior bars, dollar ADV20 (d−1) >= $20M, price >= $5 (raw close
where raw_close.parquet has it, else the panel close; ADV >= $20M keeps out most reverse-split pennies).
σ = sd of daily log close returns d−21..d−1. Outcome z = ln(C_d / O_d) / σ (open auction -> close).
Features known at 09:30: gap_z = ln(O_d / C_{d−1}) / σ; r1_z (d−1 close/close); ibs1 (d−1); r5_z (5-day, /σ√5);
range1_z = ln(H/L)_{d−1} / σ; rvol1 = V_{d−1} / mean V over d−20..d−1; hi20 = C_{d−1} / max H over 20d;
vol20 (annualised); log ADV20; spy_gap_z (SPY's own gap / SPY σ).

Part 1 (report): big swing = |z| >= 3 (also the day's top 10 by |z|). For big-up and big-down separately,
per half: the share of events in each feature's top and bottom cross-sectional decile (lift = share / 10%),
and per feature decile P(|z| >= 3) (magnitude) next to mean z (direction). Reading: which features predict
size, and whether any predicts sign.

Part 2 (select on 2021-23 only): per feature, per-day cross-sectional deciles; mean open -> close return of
each extreme decile minus the universe mean that day, day-clustered t. Select up to 3 features whose extreme
decile has |t| >= 3.0 in 2021-23 (largest |t| first), each with its sign (long the decile if its excess is
positive, short if negative). Variants (all equal-weight, up to 10 names/day = the most extreme values of the
decile, enter at the open auction, exit at the close auction):
- AE1..AE3: one rule per selected feature.
- AE4: combined score = sum of the selected features' signed decile ranks; top 10 in the favoured direction.
- AE5: AE4 with a stop at 0.5σ against and a target at 1.0σ in favour (daily high/low; if both are touched the
  stop is assumed first); otherwise the close.
Shorts: skip a name whose open is <= −10% vs the prior close (SSR); assume borrow at ADV >= $20M (stated).
Costs per side by `book.cost_bps` on raw price/ADV: tier and tier_hi. If no feature reaches |t| 3 in 2021-23,
Part 2 adds no variant and says so.
Pass (SHADOW), each variant, on 2024-26: (1) mean net/trade > 0 at tier_hi; (2) day-clustered t >= 2.0 at
tier; (3) placebo, 200 draws: same days, same count, random universe names from the same vol20 quintile,
same direction and exit, rule >= 95th pct; (4) 2021-23 net > 0 at tier_hi. Else DEAD. Capacity: $ per name
at E = $25k / 100k / 500k (0.5 E over 10 names) as % of the opening auction (1.6% of ADV, Study V).


## Amendment — Round 16, Study AF: size the conviction trade by predicted magnitude (pre-register; 4 variants, N 619 -> 623)

`date`: Wed Sep 30 15:40:34 PDT 2026. Brief: research/drafts/prompt_conviction_research.md idea #2. No AF number computed; only data coverage
was checked (QQQ/TQQQ/SMH minutes 2016-01-04..2026-09-21; Cboe VIX, VIX9D daily; cached intraday_bp_res.pkl book
series B1 V7 / B3 moderate10c, M2 base, 2021-02..2026-09).
Idea: the conviction trade (book.breakout_days, TQQQ, first breakout >= 0.341σ) profits from the SIZE of the day's move;
Study AE found size (not sign) predictable at the open. Stated prior against: the trade is sized in fixed notional, so a
high-magnitude day already carries more dollar risk; if EV per trade scales with magnitude m and variance with m², the
Kelly weight is flat-to-falling in m, and sizing UP on m buys return with drawdown, not Sharpe. AF4 tests that rival.

Predicted magnitude m̂_d (known at 09:30, regular-hours data only: QQQ RTH minutes give O_d = minute-0 open, C = minute-389
close, H/L/V = RTH minute max/min/sum; VIX = Cboe official close of d−1):
- σ20 = sd of ln(C_t/C_{t−1}) over the 20 sessions to d−1; |gap_z| = |ln(O_d/C_{d−1})|/σ20; range1_z = ln(H/L)_{d−1}/σ20;
  rvol1 = V_{d−1} / mean V over d−20..d−1; vix = VIX_{d−1}/100.
- m̂ = OLS fit of |ln(C_d/O_d)| on [1, |gap_z|, range1_z, rvol1, vix], QQQ, every session 2016-02..2023-12; coefficients frozen.
- Tercile cut points of m̂ (and of VIX_{d−1} for AF3) over all 2016-23 sessions, frozen; applied unchanged to 2024-26.
Variants: conviction weight = 0.5 x multiplier by tercile (low / mid / high):
- AF1 m̂ 0.5 / 1.0 / 1.5;  AF2 m̂ 0 / 1.0 / 2.0 (skip the calm third, double the loud third);
- AF3 VIX_{d−1} only, 0.5 / 1.0 / 1.5 (no fitted model);  AF4 m̂ inverse, 1.5 / 1.0 / 0.5 (risk-parity rival).
Margin (live `executor._gate` reserves conv x 0.75 at the open): the day's noise cap = growth.cfg(1.0, w_conv(d), mult)
['noise_cap'], so a larger conviction allowance shrinks the QQQ/SMH noise leg that day whether or not a breakout comes;
this cost is in every variant. Primary mult 2 (the research baseline); mult 4 (add. 40, shadow) reported as a sensitivity.
Book: variant daily return = cached base (B3 moderate10c, and B1 V7 reported) + Δconviction + Δnoise, additive in daily
return (each leg is E x weight x leg return). EH series = base EH + Δ − ½ mean(Δ).
Costs: stressed = tier_hi (conviction 3bp/side = 2x measured 1.5bp; noise 1.5bp/fill, > 2x measured). Also shipped costs.
Reported (not variants): m̂'s R² for QQQ |open->close| and for the trade's |gross| in 2016-23 and 2024-26; conviction EV /
win rate / mean |gross| / trade count per m̂ tercile, each half; capacity: TQQQ notional / TQQQ $ volume in the entry
minute at E = .3k, k, k, k (median, 95th pct, max multiplier); $/yr of the increment at those sizes
(pre-tax; taxable after 35% ST tax).
Pass (SHADOW), each variant vs the shipped 0.5 flat, at the stressed cost:
1. increment > 0 in 2016-23 AND in 2024-26 (also shown 2016-20 / 2021-23 / 2024-26);
2. Newey-West t (5 lags) of the daily increment, 2016-26, >= 2.0;
3. placebo: the variant's multipliers permuted across sessions (1,000 draws, same multiplier mix), actual mean increment
   >= 95th pct;
4. book (B3, tier_hi, 2021-26) max DD not worse by > 2pp; 5. 5y MC (mc_tax, EH, after tax, $3k+$1k/mo) P(DD>50%) <= 5%.
DSR of the increment reported at N = 623. All five pass -> SHADOW (config switch spec, default off). Else DEAD.


## Amendment — Round 16, Study AG: confidence and confirmation signals at the breakout minute (pre-register; <= 6 variants, N 623 -> <= 629)

`date`: Wed Sep 30 15:43:37 PDT 2026. Brief idea #1. AF (above) was computed and is dead; nothing below was computed. Data coverage checked:
no NQ futures data and no minute bars for NDX-100 members exist in the repo (only 11 ETFs), so "breadth" and "NQ leads
QQQ" are UNTESTABLE and are reported as such (not counted). ETF minutes exist for QQQ, TQQQ, SMH, SPY, IWM.
Trades: the conviction trade list (conviction_af.conv_trades; 785 trades 2016-26). Every feature uses data up to the close
of the breakout decision minute m0 (or d−1 daily closes), regular-hours minutes only.
Confirmations (each split into terciles with cut points frozen on the 2016-23 trades, unless categorical):
- C1 strength (distance past the band / σ; already >= 0.341). Also REPORTED: EV by strength quintile over ALL first
  breakouts incl. those below 0.341 (2016-23 quintile cuts), both halves.
- C2 cross-ETF agreement: how many of SMH, SPY, IWM are outside their OWN noise band in the trade's direction at m0
  (same live band functions): categories 0 / 1 / 2-3.
- C3 relative volume: QQQ volume over minutes m0−29..m0 / mean of the same window over the prior 14 sessions.
- C4 VIX(d−1) level; C5 VIX9D/VIX(d−1) (term structure; Cboe closes).
- C6 time of day: m0 = 10:00 / 10:30-11:30 / 12:00 or later.
Selection (2016-23 only): net EV per trade (1.5bp/side) must be monotone across the 3 buckets, in either direction. For each
confirmation that is, the variant AG_k DROPS the worst end bucket (no trade that day; the conviction allowance was reserved
at the open, so the noise leg is unchanged). Confirmations that are not monotone add no variant (N counts only those run).
Reported for every confirmation regardless: EV / win / n per bucket in 2016-20, 2021-23, 2024-26.
Pass (SHADOW), each variant, increment vs the shipped trade at the stressed cost (3bp/side):
1. increment > 0 in 2016-23 (in-sample, expected) AND 2024-26 (the judgement); 2021-23 and 2024-26 shown separately;
2. NW t (5 lags) of the daily increment 2016-26 >= 2.0;
3. placebo: drop the same number of trades at random from the same years (1,000 draws); actual >= 95th pct;
4. B3 moderate10c book (tier_hi) max DD not worse by > 2pp; 5. mc_tax P(DD>50%) <= 5%. DSR at the new N.
If two or more pass bars 1-3, a combined AG_all (drop a trade in any variant's worst bucket) is reported, not counted.
Money at $2.3k / $25k / $100k / $500k (tier_hi, mult 2).


## Amendment — Round 16, Study AH: stops, targets, scale-outs and a pullback entry for the conviction trade (pre-register; 6 variants, N 624 -> 630)

`date`: Wed Sep 30 15:45:43 PDT 2026. Brief idea #3. AF and AG are computed (dead); nothing below was computed.
Stated prior: fixed targets and trailing exits lost on every earlier leg (add. 3, 13 and NEXT.md dead list) because they
cut the winners a ~39%-win trend trade lives on. Expect targets to lose and stops to be ~neutral (the band/VWAP exit is
already a stop, checked every 30 min).
Base: the shipped trade (conviction_af.conv_trades; entry at the breakout decision minute m0 close e, direction s, band σ
= sig[m0] of TQQQ, a fraction of the open). Unit u = sig[m0] x e. Stops/targets are resting orders checked on every
TQQQ minute from m0+1 (regular-hours minute high/low), IN ADDITION to the shipped band/VWAP exit at decision minutes and
15:57. Stop fill = the stop price, or the minute's open if it gapped through (worse); target fill = the target price; if a
minute touches both, the stop is assumed first.
- AH1 stop 1.0u;  AH2 stop 2.0u;  AH3 target 2.0u;  AH4 target 4.0u;
- AH5 half off at a 2.0u target, the rest on the shipped exit;
- AH6 pullback entry: after a qualifying breakout at m0, a limit at the band edge (ub[m0] long / lb[m0] short) valid for 30
  minutes; filled if a minute's low (long) / high (short) touches it, else no trade today; then the shipped exits from the
  next decision minute.
Costs: stressed 3bp/side (2x measured TQQQ), also 1.5bp; a half exit pays the side cost on each half.
Pass (SHADOW), each variant vs the shipped exit, increment = 0.5 x (variant − base) net per trade day:
1. > 0 in 2016-23 AND 2024-26 (2016-20 / 2021-23 / 2024-26 shown); 2. NW t (5 lags) 2016-26 >= 2.0;
3. placebo: random sign on each trade day's increment (1,000 draws), actual mean >= 95th pct;
4. B3 moderate10c (tier_hi) max DD not worse by > 2pp; 5. mc_tax P(DD>50%) <= 5%. DSR at N 630.
Also reported: win rate, mean win / mean loss, share of base P&L from trades that the variant cuts, worst trade.


## Amendment — Round 16, Study AI: how much daytime capital the conviction trade can take (pre-register; 4 variants, N 630 -> 634)

`date`: Wed Sep 30 15:47:32 PDT 2026. Brief idea #7. AF/AG/AH are computed (dead; AH1's 1u stop is NOT carried in here). Nothing below computed.
Margin facts (add. 40): TQQQ/SQQQ carry 75% maintenance, so TQQQ notional is capped at equity/0.75 = 1.33x even with
Schwab's intraday buying power; weight 2.0 is only reachable with futures (MNQ ≈ 6x QQQ-equivalent), and is reported as
that reference. Day's noise cap = growth.cfg(1.0, w, mult)['noise_cap'] (the allowance is reserved at the open).
Reference rows (not variants): w 0 (conviction off: the value of "turning it on" = 0.5 vs 0) at mult 2 and 4.
Variants vs the shipped w 0.5 at the same mult:
- AI1 w 0.75, mult 2;  AI2 w 1.0, mult 2 (noise cap -> 0);  AI3 w 1.0, mult 4 (Schwab intraday, add. 40 shadow);
- AI4 w 2.0 via MNQ (futures margin, noise cap left at the w-0.5 value; MNQ costs taken as the TQQQ stressed 3bp/side
  equivalent — conservative for futures).
Costs stressed tier_hi (conviction 3bp/side, noise 1.5bp/fill); also shipped costs.
Pass (SHADOW) as Round 16: increment > 0 in 2016-23 and 2024-26; NW t >= 2.0; placebo = random sign on the EXTRA
exposure's daily return (1,000 draws) >= 95th pct; B3 moderate10c (tier_hi) max DD not worse by > 2pp; mc_tax P(DD>50%)
<= 5% (also P(DD>30%) reported). Also reported: worst single conviction trade as % of equity; capacity (TQQQ entry-minute
share, 2024-26) at $2.3k / $25k / $100k / $500k; $/yr at those sizes (pre-tax and after 35%); DSR at N 634.


## Amendment — Round 16, Study AJ: the conviction trade in MNQ instead of TQQQ (pre-register; 3 variants, N 634 -> 637)

`date`: Wed Sep 30 15:49:28 PDT 2026. Brief idea #6; motivated by AI (computed): TQQQ's 75% maintenance takes the noise leg's margin. Nothing
below computed. 0DTE options are NOT tested: no options price history in the repo (priced separately in the writeup).
Signal and entry/exit minutes exactly as shipped (conv_trades on TQQQ). MNQ return = 3 x QQQ's move over the same minutes
(QQQ regular-hours minute closes as the NQ proxy, futures.py convention: NQ ≈ 41 x QQQ, MNQ = $2 x NQ; no roll/basis),
so weight w means the same exposure as w in TQQQ. Margin: futures margin taken as 10% of MNQ notional (conservative vs
~5% exchange intraday), i.e. 0.30 of equity per unit w reserved at the open: noise cap = growth.cfg(1.0, w, mult, r3=0.30).
Costs per side: shipped 0.5bp (1 tick ≈ 0.1bp + commissions), stressed 1.0bp. Taxable account only (Section 1256 60/40
in mc_tax via r1256; no wash sales vs the Roth's TQQQ/SQQQ); the Roth cannot trade futures in a limited-margin IRA.
Variants vs the shipped w 0.5 in TQQQ, mult 2 (mult 4 shown):
- AJ1 w 0.5 MNQ;  AJ2 w 0.75 MNQ;  AJ3 w 1.0 MNQ.
Pass (SHADOW) as Round 16: increment > 0 in 2016-23 and 2024-26 at the stressed costs; NW t >= 2.0; placebo = random sign
on the daily increment (1,000 draws) >= 95th pct; B3 max DD not worse by > 2pp; mc_tax P(DD>50%) <= 5%. DSR at N 637.
Reported: TQQQ vs 3x QQQ gross on the same trades (tracking); whole-contract minimum equity per w (one MNQ ≈ 82 x QQQ
price); $/yr at $2.3k / $25k / $100k / $500k with whole contracts (0 below the minimum), pre- and after-tax (60/40 vs
35% ST); capacity: contracts vs typical MNQ minute volume (stated, not measured: no futures volume data).


## Amendment — Round 16, Study AK: more rare setups (second breakouts; SMH/SPY/IWM fill-in days) + a latency report (pre-register; 5 variants, N 637 -> 642)

`date`: Wed Sep 30 15:52:59 PDT 2026. Brief ideas #5 and #4 (report part). AF-AJ are computed; nothing below computed.
Stated priors: SOXL conviction was dead as a split/extra book (conv2, NEXT.md); the noise rule fails on SPY after costs and
on IWM entirely (add. 6). Expect SPY/IWM to add ~0 or less; SMH uncertain; second breakouts after a failed first are a
reversal bet in disguise (expect ~0).
All trades use the shipped rule and live band functions, regular-hours minutes, weight 0.5, at most ONE conviction trade
per day across all instruments (the allowance reserved at the open is unchanged, so the noise leg is unchanged).
- AK1 second breakout: on a day whose strong first TQQQ trade exited on the band/VWAP before 15:00, take the next
  noise-band breakout of TQQQ (either direction, strength >= 0.341) at a later decision minute; shipped exits.
- AK2 SMH / AK3 SPY / AK4 IWM fill-in: on days with NO TQQQ conviction trade, the ETF's own first breakout if its strength
  >= that ETF's 2016-23 median first-breakout strength (frozen); traded as 1.5 x E notional of the 1x ETF (= 0.5 in a 3x
  ETF; same 25% x 3 maintenance), return = 3 x the ETF's move; shipped exits on the ETF's own band/VWAP.
- AK5 all three fill-ins, first breakout in time across SMH/SPY/IWM (ties: SMH, SPY, IWM).
Costs: TQQQ 1.5 / 3bp per side (shipped / stressed); 1x ETFs 0.5 / 1bp per side on 3x notional (= 1.5 / 3bp per unit weight).
Pass (SHADOW) as Round 16 (both of 2016-23 and 2024-26 > 0 at stressed cost; NW t >= 2; placebo = random sign on each added
trade's return, 1,000 draws, >= 95th pct; B3 max DD not worse by > 2pp; mc_tax P(DD>50%) <= 5%; DSR at N 642). Also:
correlation of each ETF's trade returns with the TQQQ trade on days both would fire (>= 0.7 = the same bet, reported).
Latency REPORT (idea #4, no variant): the shipped trade with entry AND exits filled 1 and 2 minutes after the decision
minute (the close of minute m+1 / m+2), EV per trade and $/yr by half. Sub-minute delays (5/15/60 s) need tick data the
repo does not have; the Schwab L1 recorder is NOT built this session (it would run on the live server: user's call).


## Amendment — Round 17: more %/yr on a small account ($2-25k) — Studies AL-AO (pre-register; N 642 -> 665)

`date`: Wed Sep 30 18:57:16 PDT 2026. Brief: research/drafts/prompt_small_account_profit.md. Program N = 642 at the end of
Round 16. **Nothing below is computed.** All studies use `load_sim(raw_price=True)` (add. 30), the night pool corr 0.7,
regular-hours only. Costs are the repo convention: 3bp flat = the measured planning level (live buys median -2.5bp, open
sells median 0bp, add. 29), `tier` = planning, and `tier_hi` = the **stressed** level the pass bar is scored on (add. 39).
Select 2016-23 (2021-23 where the night pool is the subject) and judge 2024-26; report both halves. Pass bar (SHADOW):
increment > 0 in both halves at the stressed cost; Newey-West t >= 2.0; placebo >= 95th pct; book max DD not worse by
> 2pp; mc_tax P(DD>50%) <= 5%. DSR is reported at the new N. Dead-list items are not retested.

### Study AL — the idle Roth: what the limited-margin delay costs, and the best cash-IRA book (delay report + 7 variants)

Motivation: the Roth has never traded; `executor.py:165` returns before any phase unless `.env` has
`ROTH_LIMITED_MARGIN=yes`. The question is what waiting costs, and whether a book that needs no limited margin clears the
bar so the Roth can start now.

**Mechanism (checked before running, add. 31/38).** In a plain cash IRA (no limited margin, no borrowing, no shorting):
- the IBS leg buys at open d+1 (settles d+2) and sells at open d+2 (= the funding sale's T+1 settlement date) -> GFV-safe;
- the night leg buys at the 16:00 close d (settles d+1) and sells at the open d+1 (= the settlement date) -> GFV-safe;
- the **3x-ETF intraday leg** (buy ~10:01, sell ~15:57 same day, funded by the morning's unsettled sale) is the only leg
  that needs limited margin. So the cash-IRA book = IBS + night, no intraday leg.
Two readings of same-day reuse are tested: *lenient* (allowed, as add. 38 Q4) and *strict* (each overnight dollar works
every other night = both legs at half weight, roth.py's "a-strict").

**A. Cost of the delay (report).** Run at $1k and $3k start + $7,500/yr ($625 every 21 sessions), 2021-02..2026-09:
M3 (live executor rule: SGOV held at 15:40, greedy skip), M2L (pro-rata on the 15:40 cash), cash-IRA AL1, BIL, SPY.
Report CAGR/Sharpe/maxDD (both halves + full), and the delay cost as $/month = (book - BIL CAGR) x equity / 12 at $1k,
$3k and at $25k-equivalent, plus a start-6/12/24-months-earlier end-$ comparison (the compounding value of starting now
instead of waiting for approval). The Roth's contributions are **savings, not alpha**: at $2k the deposits dominate the
dollars, and the report says so.

**B. Cash-IRA book (variants, pass bar in the brief, baseline BIL, reference M3).**
- AL1 IBS 0.5 + night 0.5, **no intraday leg** (lenient settlement). The live weights.
- AL2 IBS 0.5 + night 0.5 strict (both legs 0.25/0.25).
- AL3 IBS only, weight 1.0, lenient.
- AL4 night only, weight 1.0, lenient.
- AL5 alternating sessions: IBS 0.5 on even sessions, night 0.5 on odd sessions (each dollar employed every other night).
- AL6 AL1 with the live whole-share + night 1-share probe ($150) constraint (the as-traded book).
- AL7 AL1 with F3 off by construction (a Roth F3 is dead for wash, add. 39) and the A2 V6 leg **not** included (V6 is
  itself shadow; out of scope).
Reported: CAGR/Sharpe/maxDD per half + full at 3bp/tier/tier_hi, NW t of the daily difference vs BIL (2021-26), placebo =
sign-randomised position returns (1,000 draws) >= 95th pct, max DD vs M3, mc_tax $3k+$1k P(DD>30/50%), $/yr at
$2.3k/$10k/$25k. If AL1 (or better) clears, spec the switch (default off, kill rule, tests, `make test`).

### Study AM — limit orders at the bid/ask for the night leg (pre-register; 6 variants, N -> 656)

Motivation: add. 13 bounds the prize at ~+2pp CAGR ("earning the bid instead of paying the ask"), worth more at small size
where thin names cost nothing in impact. The repo has **no quotes/order-book data**: only SIP trade prints. The model is
therefore built from the trade path, with a per-name tick floor, and its bounds are stated.

**Data / linkage.** Night picks (raw pool, corr 0.7). Entry reference `p50` = the 15:50 price (the live decision price);
`C` = the official close (= p50 x (1+close_move)); `ret` = close -> next open. The 15:50-16:00 minute trade bars come from
`data/research/night/lm1` (+ `lm6`), the next-morning 09:30-10:31 bars from `data/research/night/am1`; bars are rebased onto
the daily basis (scale = daily close / 16:00 bar close) and a name-day with no bar keeps the shipped exit (counted). The
per-side cost on any continuous-session fill = `book.cost_bps(<model>+tick)` on the raw fill price.

- AM1/AM2/AM3 **close limit buy** at L = p50 x (1 - b), b in {5, 10, 20} bp. Fill rule: a resting limit fills at L if the
  15:50-15:59 trade low <= L (continuous), else fills at the official close if close <= L (the closing cross clears at or
  below the limit), else the name is **skipped** (capital redeployed pro-rata to the filled names, as night_sizing does).
- AM4 **sweep-to-the-low limit**: L = the 15:50-15:59 minute low (best case; upper bound on earning the bid).
- AM5 **limit-on-open sell** at H = C (sell only at/above the prior close); unfilled -> sell at the 09:45 minute close.
- AM6 **sell at the open + 1 tick**: after the open, rest a limit sell at the open + one tick; fill if the 09:30-09:59 high
  reaches it, else sell at the 09:59 close (earn the sell-side spread).
Measured and reported for each: fill rate; adverse selection = mean net per filled trade minus mean net of the same names
unfilled; book increment per half at the stressed cost; NW t; placebo (random sign on each changed pick's return, 1,000
draws) >= 95th pct; $/yr at $2.3k/$10k/$25k. Pass bar as above; the buy and sell sides are judged separately (a side
passes on its own; AM1 is the control that must reproduce the shipped book).

### Study AN — night-leg pick quality where small size helps (pre-register; 5 variants, N -> 661)

Motivation: Study U's diagnostic (+41bp foreign ADRs vs +17bp US operating) and Study T's side note (mapped operating
filers -11bp vs unmapped +15bp). Study U's EDGAR classifier mislabels: "UNMAPPED" = leveraged ETFs, "ETP" = foreign ADRs
(add. 30/36/Study W). This study builds a **proper** classifier and pre-registers tilts/filters.

**Classifier** (per pick, point-in-time; EDGAR cache `data/research/night/edgar`, forms accepted within the 400 days before
the pick; LETF from `new_listings.etf_kind`):
- `FOREIGN` any 20-F/40-F or 6-K filing (foreign private issuer / ADR);
- `US_OPER` entityType operating, not ETP, has 10-K/10-Q, no foreign form;
- `LETF` `etf_kind == "lev"`; `ETP` entityType != operating or SIC 6221 or >100 424B/yr; else `OTHER`.
- AN1 drop US_OPER picks (Study T's finding, as a filter).
- AN2 keep only FOREIGN picks (Study U's bucket); report the trade-count cut.
- AN3 FOREIGN picks at 2x weight (cap 0.20).
- AN4 drop LETF picks (control; Study W says the LETF gross is leverage, not edge).
- AN5 drop US_OPER and 2x-weight FOREIGN (combined).
Method as Study U/W: per-pick w = min(frac, 0.10), book increment = 0.5 x w x net vs the unmodified pool; NW t (day-
clustered), within-night placebo drawing the same number of picks at random (1,000 draws); $/yr at $2.3k/$10k/$25k; capacity
= the added/filtered names' ADV vs the leg's $ size (where the tilt breaks). Pass bar as above.

### Study AO — whole-share drag at $2.3k (pre-register; 5 variants, N -> 666)

Motivation: at $2.3k the IBS leg's per-ETF budget is ~$383 (3 picks) and the night cap is $115/name; whole-share rounding
throws away fills. Study R's method (whole vs fractional, by size). Baseline: the live Roth/taxable whole+probe book.

- AO1 baseline: whole + night 1-share probe ($150), the shipped as-traded book; fractional is the upper bound.
- AO2 **fewer, larger IBS picks**: IBS top_k in {2, 1} instead of 3 (rebuilt `ibs_days`) -> the per-pick budget rises.
- AO3 **cheaper look-alike per ETF**: size each IBS pick at the look-alike's share price but the same index return
  (QQQ->QQQM, IWM->VTWO, SMH->SOXX, XLK->VGT, XLF->VFH, XLE->VDE, XLV->VHT, XLI->VIS, XLY->VCR, XLP->VDC, XLU->VPU,
  XLB->VAW, MDY->IJH, EEM->IEMG, EFA->IEFA; prices from `panel.pkl`, 2020-10 onward). **SPLG has no research data**: the
  SPY and DIA legs are left at the original price and the SPY->SPLG gain is estimated separately as SPY_price/8.5
  (labelled a sensitivity, not a result).
- AO4 **IBS probe**: buy 1 share when the per-ETF budget is below one share and the price <= $150 (as the night leg does).
- AO5 AO3 + AO4.
Reported at $2.3k / $10k / $25k: whole+probe minus fractional (pp/yr) per half, skipped-fill rate, and each variant's
increment in pp/yr and $/yr; paired 5y MC (P(DD>30/50%)). PASS (adopt) only if a variant raises the $2.3k CAGR by >= 2.0pp
in both halves at the stressed cost (Study R's decision bar), else report/dead.


## Amendment — Round 17b, Study AP: the IBS leg's selection — cross-sectional rank and always-deployed (pre-register; 5 variants, N 664 -> 669)

`date`: Wed Sep 30 22:11:14 PDT 2026. Follow-on to Study AL: the IBS leg is the book's best %/yr
lever at small size (17.9%/yr at tier_hi, nearly cost-insensitive) and the cash-IRA Roth runs it
alone. NEXT.md's untested list names "cross-sectional ranking instead of a binary z-threshold
(always deployed)". Nothing below computed. Baseline = the shipped IBS leg (`book.ibs_days`:
monthly top-3 momentum ETFs, buy at open d+1 those with IBS < 0.2, equal weight, hold while IBS <
0.2). The whole leg return is the pick's open d+1 -> open d+2 move, so selection changes the trades.

Variants (each swaps `s.I`):
- AP1 rank-1 (threshold): of the top-3, hold ONLY the lowest-IBS name, and only if IBS < 0.2.
- AP2 rank-1 (always): the lowest-IBS name of the top-3 every session (no threshold).
- AP3 all-18 rank-1 (always): the single lowest-IBS name of the 18 EQ18 ETFs each session, no
  momentum filter and no threshold.
- AP4 rank-2 (threshold): the two lowest-IBS names with IBS < 0.2, equal weight (the shipped leg
  with the least-oversold of three dropped when all three pass).
- AP5 stricter gate: shipped selection with `ibs_max` 0.1 instead of 0.2.

Judged on the V7 book (night .5 + IBS .5 + QQQ/SMH noise cap .75, live tilt, weekend x.5, no
conviction) at fixed capital $2.3k / $10k / $25k, whole shares + $150 probe, tier and tier_hi. Pass
bar (SHADOW): increment > 0 in both halves at the stressed cost; NW t >= 2.0; placebo = random sign
on the IBS leg's daily contribution (1,000 draws) >= 95th pct; book max DD not worse by > 2pp;
mc_tax P(DD>50%) <= 5%. Also reported for the IBS-only cash-IRA book (Study AL). DSR at N 669.


## Amendment — Round 17c, Study AQ: the night leg's cost crossover (pre-register; report, 0 variants, N stays 669)

`date`: Wed Sep 30 22:14:00 PDT 2026. Triggered by Study AL: at the repo's `tier_hi` (15-50bp
round trip) the night leg is negative (-3.4%/yr), but the brief's cost instruction is the MEASURED
costs (buys ~-2.5bp, sells ~0bp) "stressed at 2x" (~5bp round trip), and add. 29 measured buys
-0.5bp / sells -1.0bp. tier_hi is 5-10x measured, not 2x. Nothing below computed.

Report: for the cash-IRA Roth book at fixed capital $3k, sweep the flat night round-trip cost over
{0, 2.5, 5, 7.5, 10, 15, 20}bp for IBS .5 + night .5 (AL1), IBS-only (AL3) and night-only (AL4);
report full CAGR and the crossover where IBS-only overtakes. Then re-evaluate AL1 at the brief's
stress (5bp): stats, both halves, NW t vs BIL, sign-flip placebo, mc_tax P(DD30/50), and $/yr at
$2.3k/$10k/$25k. Same for the taxable V7 book (B.Sim.replay) at the same costs. No new variant; a
sensitivity on registered variants. If IBS+night beats IBS-only at <= 5bp in both halves, the
cash-IRA spec becomes IBS .5 + night .5 (not IBS-only) with the cost level named as the gate.


## Amendment — Round 18: two ideas from a quant Discord (MemLabs server) — Studies AS, AT (pre-register; 6 variants, N 669 -> 675)

`date`: Wed Sep 30 23:54:33 PDT 2026. Source: chat logs the user pasted. Most ideas there are already
in NEXT.md's do-not-redo table (order-book / auction imbalance: data; decay monitors / CUSUM de-risk:
add. 37; regime & 200dma gates; inverse-vol name sizing; ML/XGBoost: Study E; parameter
sensitivity / DSR). Two are concrete and untested here. Nothing below computed.

### Study AS — allocate the overnight budget between legs by trailing metrics ("softmax of metrics")
MemLabs: "pass your metrics as a vector into the softmax function and that gives a weight
allocation"; sxssion: allocate by vol or expectancy. The shipped book splits the overnight budget
IBS .5 / night .5, fixed. Each variant keeps night_w + ibs_w = 1.0 (no added leverage, cash-IRA
compatible), clips each weight to [0.2, 0.8], and leaves the noise leg unchanged. Signals use each
leg's per-unit daily return (fractional $100k replay, IBS unit includes its idle BIL), lagged 2
sessions (an IBS signal on d-2 is realised at open d; nothing later is known at d's decisions).
- AS1 softmax of trailing 63-session annualised Sharpe, temperature 1.
- AS2 inverse trailing 63-session vol (risk parity between the two legs).
- AS3 softmax of trailing 252-session annualised Sharpe, temperature 1.
Books: V7 (night .5 + IBS .5 + QQQ/SMH noise cap .75, live tilt, weekend x.5, no conviction) and
IBS+night with noise off (the cash-IRA mix, approximated in B.Sim: no GFV timing), fixed capital
$2.3k / $10k / $25k, whole shares. Night cost: 5bp flat round trip (the brief's measured x2, Study
AQ) and tier_hi as the stress. Window 2021-02..2026-09 (the honest night pool); no 2016-20 holdout,
so the verdict caps at SHADOW.

### Study AT — vol-contraction and trend-slope conditioning for the IBS (mean-reversion) leg
Whiskey: filter "false mean-reversion signals" when short-term vol is regressing toward the
medium-term regime (20-bar vs 100-bar), and/or take MR trades only when a regression slope agrees.
Per IBS pick s on signal day d (d's close; known before the d+1 open buy):
VR = stdev of s's log close returns over the last 10 sessions / over the last 60 sessions.
- AT1 skip the pick if VR < 0.8 (vol contracting).
- AT2 skip the pick if VR > 1.25 (vol expanding) — the opposite sign, registered so a one-sided
  look can't pass by choosing the sign after the fact.
- AT3 skip the pick unless the OLS slope of s's log close over the last 50 sessions is > 0.
Skipped picks leave their slice of the IBS half in BIL (the shipped idle rule).
Holdout: the IBS leg alone exists 2016-01..2020-12; report per-trade mean gross (open->open, 1bp
side) of kept vs skipped picks in 2016-20, 2021-23, 2024-26. Books as Study AS, night 5bp and tier_hi.

### Pass bar (both studies, SHADOW at most)
At the stressed cost (tier_hi) and at 5bp: book increment > 0 in both halves (2021-23, 2024-26) at
every size; NW t (5 lags) of the daily increment >= 2.0; sign-flip placebo of the daily increment
>= 95th pct (1,000 draws); max DD not worse by > 2pp. AT also needs the kept-minus-skipped per-trade
gap to have the passing sign in 2016-20. DSR reported at N 675. A variant that fails any clause is
DEAD.

## Amendment — Round 18: the day-trading lab's first two strategies, Studies AS and AT (pre-register; 2 variants, N 669 -> 671)

`date`: Thu Oct 1 00:14 PDT 2026. Brief: `research/drafts/prompt_daytrade_lab.md`. The lab is a separate package
(`daytrade/`), account and state; nothing here touches the live book. Nothing below computed. The full rules,
costs and drop conditions are in the plans, which are part of this registration:
`daytrade/plans/gap_vwap_reclaim.md` and `daytrade/plans/open_imbalance.md`.

### Study AS — gap + premarket volume, pullback to VWAP, reclaim entry (1 variant, N -> 670)
- Selection at the official open: common stocks, prev close $5-1,000, 20d ADV >= $5M, gap >= +4.0% (09:30 SIP
  minute open / prev close), premarket SIP volume 04:00-09:29 >= 250k shares, top 5 by premarket volume.
- Entry: a bar ending >= 09:36 touches session VWAP (low <= VWAP, VWAP > prev close); a later bar closes above
  VWAP and the previous bar's high, by 11:30; market buy. Stop pullback low - $0.01 (skip if R < 0.2% or > 5%);
  target +2R; flat by 15:55; one entry per name per day; long only. Same bar stop+target = stop.
- Costs 10bp/side (1x), 20bp/side (2x). Latency 1s = next minute open; 0s / 60s reported.
- Data SIP minutes 2022-01-03 .. 2026-09-30; halves split at 2024-06-01.
- Pass (to paper): mean net/trade > 0 at 2x in both halves, day-clustered t >= 2.0 at 1x, and >= 95th pct of a
  random-entry placebo (same symbol-days, random minute 09:36-11:30, same % stop and 2R, 1,000 draws).
  Otherwise dead; no re-tuning of X, Y, cutoff, R or target.
- Prior: dead (AE, AB, AK, add. 41). It is the brief's "popular pattern" and the engine's first plug-in.

### Study AT — opening L1 quote imbalance + signed trade flow, ETFs (1 variant, N -> 671)
- QQQ, SPY, TQQQ, IWM, SMH; window 09:30:00-09:34:59 of the lab's own L1 recording. QI = mean per-second
  (bid_sz - ask_sz)/(bid_sz + ask_sz); FLOW = signed last-trade volume share (quote rule, tick rule at the mid).
  Long if QI >= +0.20 and FLOW >= +0.10; short if <= -0.20 and <= -0.10 (margin only). Enter 09:35 + 1s, exit
  10:05:00, stop at the window's low/high -/+ $0.01.
- Costs: recorded spread + 0.5bp/side (1x); 2x the half-spread + 0.5bp (2x).
- First look after 40 unflagged recorded sessions, run once; halves = first/last 20 sessions. Pass as AS
  (2x both halves, t >= 2 at 1x, sign-flip placebo >= 95th pct). Counted in N now so the look cannot be
  re-tuned.

## Note — reconciliation of two parallel "Round 18" registrations (merge of 2026-10-01)

Two sessions registered a "Round 18" from N 669 without seeing each other: the Discord ideas (Studies
AS/AT above them in this file's history, 6 variants, N 669 -> 675) and the day-trading lab (Studies AS/AT,
2 variants, below). The letters collide; from here the lab's are cited as **Lab-AS / Lab-AT**. Both sets
count: the program N before Round 19 is 669 + 6 + 2 = **677**, and Round 19's 5 variants make **682**
(Round 19's files say 675 -> 680; read +2). AU3's DSR at N 682 is reported in study_au_tow.md.


## Amendment — Round 19: max edge from outside sources — Studies AU, AV, AW (pre-register; 5 variants, N 675 -> 680)

`date`: Thu Oct  1 2026 (stamped by the commit). Brief: `research/drafts/prompt_max_edge.md`. Candidate
list (44 rows, sources, decay, counterparty, dead-list check): `research/drafts/max_edge_candidates.md`,
committed in the same commit as this amendment, before any number below was computed.

Common to AU and AV. `load_sim(raw_price=True)`, night pool `night_days(raw_price=True, max_corr=0.7)`.
Two books: **V7** (night .5 + IBS .5, QQQ/SMH noise .5/.5 cap .75, live tilt, weekend x.5, no
conviction) and **Roth cash** (IBS .5 + night .5, noise off, live tilt, weekend x.5). Fixed capital
$2.3k / $10k / $25k, whole shares. Costs: night **2.5bp per side** (the brief's 2x of measured; the
judged cost) and `tier_hi` (reported, not judged); IBS 1bp/side. Halves 2021-23 (select) / 2024-26
(judge). **Pass bar (SHADOW)**, at 2.5bp/side, in BOTH books at ALL three sizes: increment > 0 in
both halves; Newey-West t (5 lags) of the daily increment >= 2.0; sign-flip placebo (1,000 draws) >=
95th pct; book maxDD not worse by > 2pp; 5y P(maxDD > 50%) <= 5% (stationary block bootstrap of the
variant's daily book returns, 21-day blocks, 1,000 paths, at $10k). DSR reported at N 680.

### Study AU — night picks tilted by trailing overnight-return persistence (3 variants)
Sources: Aboody et al. JFQA 2018; Akbas-Boehmer-Jiang-Koch JFE 2022; CXO "overnight momentum".
Mechanism: names with persistent retail demand at the open are bid up again at the next open, which
is where the night leg sells. Different from add. 7 (overnight momentum as a standalone strategy):
a weight inside picks that already pay the cost. Features from the SIP daily panel (raw ratios, so
split-neutral), all known at 15:50 on d:
- ON20 = mean of open_t / close_{t-1} - 1 over t = d-19..d (20 gaps, including d's own open);
- TOW = count of t in d-20..d-1 with open_t/close_{t-1} > 1 and close_t/open_t < 1 (tug of war).
z = (feature - mean) / sd with mean and sd fixed from the 2021-23 night picks (select half only).
- AU1: weight = live tilt x clip(1 + 0.25 z(ON20), 0.25, 2), renormalised to the live tilt's mean that night.
- AU2: drop picks with ON20 < 0 (their slice stays in cash; no redeployment).
- AU3: weight = live tilt x clip(1 + 0.25 z(TOW), 0.25, 2), renormalised as AU1.
Extra placebo for AU1/AU3: the feature shuffled across picks within the same night (200 draws), V7
$10k 2.5bp: the actual increment must beat the 95th pct. Picks with no panel history keep z = 0.
Also reported: per-pick net by feature tercile per half (monotone or not).

### Study AV — the IBS leg's exit: hold until a state exit (2 variants)
Sources: Pagonidis (NAAIM 2014) IBS > 0.5 / 0.8 exits; idousse/mean-reversion-strategy (clean,
costed) exit close > yesterday's high. Shipped: entry when IBS_d < 0.2 on the month's top-3, held
open d+1 -> open d+2 and re-held while IBS < 0.2. Variants change only the exit; an entered name is
held (open -> open, re-evaluated each close) until the condition, a 5-session cap, or the name
leaving the month's top-3; legs are equal-weighted across held names as shipped.
- AV1: sell at the next open after the first close with IBS > 0.5.
- AV2: sell at the next open after the first close above the prior session's high.
Also judged: the 2016-20 holdout of the unit IBS leg (open->open, -2bp) must not be negative for a
variant to pass (the book sim starts 2021).

### Study AW — audit: night-leg returns on the official auction prints (report, 0 variants)
Source: Quantpedia 2025 (OHLC open = first trade, not the cross; GDX overnight 30%/yr vs 8.6%).
For every night pick 2021-26 (raw pool, corr .7), fetch Alpaca `/v2/stocks/auctions` (SIP): the
official closing cross on d and opening cross on d+1 (the largest-size print of each list). Compute
ret_auc = open_cross(d+1) / close_cross(d) - 1 vs the pool's ret (close -> next open from the vendor
daily bars). Prints are unadjusted: a pick whose |ret_auc - ret| > 20% is treated as a corporate
action and keeps ret. Report: coverage; mean and median (ret_auc - ret) in bp per half and by price
tier; the night-leg and both books' %/yr and $/yr at $2.3k / $10k / $25k with ret_auc substituted
where available. Decision rule: if the per-trade mean differs by more than 3bp in either half, every
night-leg level in NEXT.md is restated on auction prints. No variant, no N.

## Amendment — Round 20: auction-share tilts on the night leg — Study AX (pre-register; 2 variants, N 682 -> 684) + AU3 robustness reports

`date`: Thu Oct 1 2026 (stamped by the commit). Follow-on to Round 19 (candidate list rows #22/#40: the closing
auction is the one mechanism with a named payer that was untested for lack of data). Alpaca's
`/v2/stocks/auctions` (free, SIP) gives the SIZE of every opening and closing cross, so a trailing auction-share
measure is computable before 15:50 without imbalance data. Nothing below computed; the per-symbol auction
history is fetched after this commit.

Features per night pick on d, from the 20 completed sessions before d (sessions with a missing cross or zero
SIP daily volume skipped; < 15 valid -> unknown, z = 0):
- CSH20 = mean of closing-cross shares / SIP daily volume (Bogousslavsky & Muravyev, JFM 2023: auction prints
  deviate from the mid with passive/index flow and ~85% reverts by the next morning; names whose close is
  dominated by the cross carry more temporary close pressure -> a larger overnight bounce). Payer: passive
  and index flow at the close.
- OSH20 = mean of opening-cross shares / SIP daily volume (Berkman, Koch, Tuttle & Zhang, JFQA 2012: attention
  buyers concentrate at the open and pay too much; a heavier opening cross = more of that demand where the
  night leg sells). Payer: retail/attention buyers at the open.
z constants fixed from the 2021-23 picks. Weights as AU3: live v1 tilt x clip(1 + 0.25 z, 0.25, 2), renormalised.
- AX1: CSH20 tilt (predicted sign +).
- AX2: OSH20 tilt (predicted sign +).

Judged as Round 19 (V7 and Roth cash books, $2.3k / $10k / $25k, whole shares, 2.5bp/side judged, tier_hi
reported; increment > 0 both halves, NW t >= 2, sign-flip placebo >= 95th, within-night feature-shuffle placebo
(200, V7 $10k) >= 95th, dDD >= -2pp, P(DD>50%) <= 5%), with one change: **every night return from the official
crosses** (Study AW's standing rule). Also reported: per-pick net by 2021-23 terciles per half; Spearman corr
with TOW, vol20, depth, log price, log ADV; DSR at N 684.

Reports (0 variants, no N):
- R1 AU3 with TOW computed from the crosses (open cross_t vs close cross_{t-1}; close cross_t vs open cross_t)
  instead of vendor bars: same weights rule; does the tilt survive on official prices for its INPUT too?
- R2 AU3 under the `moderate` profile's 15% name cap applied after the tilt, and AU3 on top of tilt v2 (both
  flagged in study_au_tow.md as needing a check before combination).


## Amendment — Round 21: FINRA daily short-sale volume on the night picks — Study AY (pre-register; 2 variants, N 684 -> 686)

`date`: Thu Oct 1 2026 (stamped by the commit). Data: FINRA Reg SHO daily short-sale volume, consolidated
off-exchange (CNMS) files, public CDN, 2020-10..2026-09 (`research/sim/finra_short_fetch.py`). Not on the
do-not-redo list (Study S shorted the picks; the SSR flag was not run). Nothing below computed.

Feature per night pick on d: SVR5 = sum(ShortVolume) / sum(TotalVolume) over the 5 sessions d-5..d-1 (the
file for t is published after t's close, so d itself is excluded); >= 3 sessions with TotalVolume > 0, else
unknown (z = 0). z constants fixed from the 2021-23 picks; weights as AU3 (live v1 x clip(1 + 0.25 z, 0.25, 2),
renormalised).

The sign is genuinely ambiguous, so BOTH are registered and counted:
- AY1: tilt toward HIGH SVR5. Reading: off-exchange "short" volume is mostly wholesalers/market makers
  shorting to fill retail BUY orders, so a high ratio = a retail buying clientele (the AU3 mechanism: demand at
  the next open, where the leg sells). Payer: retail buyers at the open.
- AY2: tilt toward LOW SVR5. Reading: Diether-Lee-Werner (RFS 2009), Boehmer-Jones-Zhang (JF 2008): heavy short
  selling is informed and predicts lower returns, so high-SVR drops are information and bounce less. Payer: the
  liquidity demanders on the low-SVR picks.
Judged exactly as Round 20 (auction returns, V7 and Roth cash, $2.3k / $10k / $25k, 2.5bp/side judged, tier_hi
reported, both halves, NW t >= 2, sign-flip and feature-shuffle placebos >= 95th, dDD, P(DD>50%)), DSR at N 686.
Also reported: tercile nets per half; Spearman with TOW, vol20, depth, log price, log ADV. AY1 and AY2 are
mirror images; at most one can pass.


## Amendment — Round 22: tax-exempt ex-dividend overnight capture in the Roth — Study AZ (pre-register; 2 variants, N 686 -> 688)

`date`: Thu Oct 1 2026 (stamped by the commit). Brief topic: "tax placement between the accounts". Sources:
Elton & Gruber (1970) and the clientele literature (the ex-day drop < the dividend because taxable holders
value dividends less; a tax-exempt holder captures the gap); against it: Ruan & Ma (JFR 2012, ETF drops = the
dividend, so ETFs excluded), Bali & Hite (JFE 1998, tick discreteness), Frank & Jagannathan (1998). A forum-grade
2026 blog (mega-caps, overnight drop ~0.63 x dividend, no market adjustment) gets no credit. Payer: taxable
holders who sell before the ex-date (or will not buy cum-dividend) and short-horizon arbitrage costs. Not on the
do-not-redo list. Nothing below computed; dividend data (Alpaca /v1/corporate-actions, cash_dividend, free) is
fetched after this commit.

Universe on night d: common stocks (not ETFs) in the top 500 by 20-session SIP dollar volume through d-1, raw
price >= $10, with a regular (non-special) cash dividend whose ex-date is the NEXT session (declared in advance).
Trade (Roth cash book only; taxable excluded: a one-night dividend is non-qualified): the Roth's idle overnight
cash at 15:50 (equity - IBS held tonight - night leg used) buys these names equally, whole shares, <= 25% of equity
per name, MOC d -> MOO d+1. Return = the dividend-inclusive (adjusted) close -> open move from the SIP panel.
- AZ1: dividend yield (rate / raw close d) >= 0.25%.
- AZ2: dividend yield >= 0.50%.
Judged on the Roth cash IBS+night book (auction night returns, 2.5bp/side on the night leg AND the sleeve; tier
reported) at $2.3k / $10k / $25k: increment > 0 in both halves (2021-23 / 2024-26), NW t >= 2, sign-flip placebo
>= 95th, dDD >= -2pp, P(DD>50%) <= 5%, AND a matched placebo >= 95th pct: the same rule fed the same names on
random non-ex nights (each event moved to a random session of the same name 20-60 sessions away; 200 draws, Roth
$10k), which separates the dividend gap from ordinary overnight drift (the index filler died on drift, add. 16).
Also reported: per-event overnight return minus SPY's, the implied drop ratio per half, events/yr, idle share.
DSR at N 688.


## Amendment — Round 23: LLM news judge on the night picks, FORWARD test only — Study BA (pre-register; 1 variant, N 688 -> 689)

`date`: Thu Oct 1 2026 (stamped by the commit), BEFORE any verdict exists (the logger ships in the same commit).
Mechanism: the night leg is paid for absorbing selling that carries no information (liquidity); a drop on new
information about value (fundamental) drifts instead (Savor JFE 2012; Chan 2003; Da-Liu-Schaumburg 2014).
Headline CATEGORIES were dead (add. 12) and offering filings are a shadow (Study T); this asks a reader of the
actual news and filings the direct question. Why forward only: an LLM knows how events before its training
cutoff turned out, so any historical backtest is contaminated; every verdict is made at 15:40 on the day.

Logger: `swingtrader/daily/news_judge.py`, after the 15:40 orders (shadow; never changes an order), at most 8
new picks a night (deepest drops first), one verdict per (date, symbol) shared by all books, model
`claude-opus-5-5`, effort low, inputs = Alpaca/Benzinga news since the previous close + SEC filings accepted
since the previous close. Output: verdict in {fundamental, liquidity, unclear} + confidence.

Variant (the only one; counted now so the look cannot be re-tuned):
- BA1: weight 0.25 on picks judged fundamental with confidence >= 0.7 (freed cash idles), vs equal weight among
  that night's judged picks.
Scoring (`research/sim/news_judge_eval.py`, `make news-eval`): official crosses (close cross d -> next open cross,
Study AW), net of 2 x 2.5bp. Read ONCE at >= 300 judged picks with a verdict. PASS (-> SHADOW, spec a switch)
only if: the daily increment > 0 in both halves of the judged sample (split at the median date), NW t >= 2,
sign-flip placebo >= 95th and within-night flag-shuffle placebo >= 95th. Also reported: net by verdict and by
confidence. Model, prompt, effort and the 0.7 / 0.25 constants are frozen; changing any of them restarts the
count from zero as a new registration.


## Amendment — Round 24: 15:40 quote imbalance on the night picks, FORWARD test only — Study BB (pre-register; 1 variant, N 689 -> 690)

`date`: Thu Oct 1 2026 (stamped by the commit), before any snapshot exists (the logging ships in the same commit).
The free part of the closing-imbalance idea (AC, parked: no paid feed): the Schwab quote the night leg already
pulls at 15:40 carries bid/ask sizes. QI = (bid_size - ask_size) / (bid_size + ask_size). Mechanism (order-book
imbalance literature, e.g. Cont-Kukanov-Stoikov 2014; the lab's Lab-AT): a sell-heavy touch into the close marks
remaining selling pressure that the close auction absorbs and the next open reverses; a buy-heavy touch says the
pressure is already gone. Predicted sign: ambiguous in level, so ONE pre-committed direction is tested: buy-heavy
up-weighted (pressure exhausted, the bounce has started; the add. 23 "late selling" null argues against the
opposite). No historical L1 exists, so forward only.
- BB1: weight clip(1 + 0.5 QI, 0.5, 1.5), renormalised within the night.
Scored by `research/sim/quote_imbalance_eval.py` (`make qi-eval`) on the official crosses, 2 x 2.5bp, one row per
(date, symbol); read once at >= 300 picks with a snapshot; bars as Study BA (both halves, NW t >= 2, sign-flip
and within-night shuffle >= 95th).


## Amendment — Round 23b: Study BA's model changed BEFORE any verdict exists (N unchanged, 690)

`date`: Thu Oct 1 2026 (stamped by the commit). The user prefers OpenCode Go's DeepSeek Flash. No verdict has been
logged in production yet (the logger shipped hours ago and has not run a 15:40 session), so this replaces Round
23's frozen model rather than restarting a count. Frozen from here: provider `opencode-go`
(https://opencode.ai/zen/go/v1/chat/completions, OpenAI-compatible JSON mode), model `deepseek-v4-flash`,
temperature 0, the same system prompt + a JSON-keys line, at most **20** new picks a night (the cheaper model lets
the judge cover every pick instead of the 8 deepest). Every record logs the model that actually served it (a public
issue reports this ID may serve DeepSeek V3.2, knowledge cutoff 2025-05; immaterial to a forward test, but logged).
Variant BA1, scoring and bars unchanged. Changing provider/model/prompt again restarts the count.


## Amendment — Round 25: the LLM news judge on PAST night picks after the model's cutoff — Study BC (pre-register; 1 variant, N 690 -> 691)

`date`: Thu Oct 1 2026 (stamped by the commit), before the probe or any historical verdict is run.
Same judge as Study BA (Round 23b: OpenCode Go `deepseek-v4-flash`, temperature 0, same prompt; the date is never
in the prompt). Script: `research/sim/news_judge_hist.py`; picks: the shipped night pool (raw, corr .7)
2025-01-02..2026-09-18, 4,071 rows, `research/sim/news_judge_hist_picks.csv`.

Contamination rule (fixed now): `probe` asks 9 dated true/false questions about public events (2024-11..2025-10)
and 3 fabricated controls. If any control is answered true, the probe is void and BC does not run. Otherwise the
window starts on the first day of the THIRD month after the latest month answered true (two full months of
margin) and ends 2026-09-18. If the latest known month is 2025-10 (the last probe), the model's cutoff is not
placed by the probe and BC does not run (a later probe would be a new registration).

Inputs point-in-time per pick: news published from the previous session's 16:00 ET to 15:40 ET on d, SEC filings
accepted in the same window. Variant BC1 = BA1 (weight 0.25 on picks judged fundamental with confidence >= 0.7,
freed cash idles). Scored by `research/sim/news_judge_eval.py` on the official crosses (close cross d -> next
open cross), 2 x 2.5bp; PASS only if: >= 300 scored picks, daily increment > 0 in both halves of the window (split
at the median date), NW t >= 2, sign-flip and within-night flag-shuffle placebos >= 95th. A PASS here plus a PASS
of BA (forward) would be needed to spec a live switch; BC alone moves BA's prior, not the book.


## Amendment — Round 25b: Study BC's cutoff probe, re-specified before any historical verdict is scored (N unchanged, 691)

`date`: Thu Oct 1 2026 (stamped by the commit). The v1 probe (true / false / unknown) returned "unknown" to all 12
statements, including the 2024 US election: its instruction rewarded abstaining, so it measured caution, not
knowledge, and placed no cutoff. Per Round 25, BC did not start. Verdicts the user began collecting from
2025-08-01 are kept (each verdict depends only on that day's inputs, not on the window), but NONE is scored until
the v2 probe sets the window; picks before the v2 start are excluded from scoring, and if the v2 start is earlier
than 2025-08-01 the missing months are judged first.
v2 probe (fixed now): 8 open questions with keyword-graded answers (2024-11 .. 2025-10) + 2 fabricated controls
("which streaming company did Apple acquire in March 2025", "which company replaced Tesla in the S&P 500 in 2025").
A control answered with anything but unknown / none / a denial voids the probe (BC does not run). Window start = the
first day of the third month after the latest correctly answered month; if the 2025-10 question is answered, the
cutoff is not placed and BC does not run. One v2 probe call; its printout is copied into the BC writeup.
