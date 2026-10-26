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

### Lab Round 18 results (2026-10-01)
- **Lab-AS: DEAD.** 1x/1s: −18.9bp/trade (n 3,308, t −3.2); 2x: H1 −28.8, H2 −41.5; placebo 59th pct; gross
  −1.7bp. Fails every bar. study_as_gap_vwap.md. N 670.
- **Lab-AT: not yet looked at** (needs 40 unflagged recorded sessions). N 671 counted at registration.


## Amendment — Lab Round 19, Study Lab-AU: 5-minute opening-range breakout on Stocks in Play (pre-register; 2 variants, N 671 -> 673)

`date`: Thu Oct 1 01:05 PDT 2026. Source: Zarattini, Barbon & Aziz (2024), SSRN 4729284 (Sharpe 2.81 in 2016-23,
commission-only costs, no held-out period). Full rules: `daytrade/plans/orb_in_play.md` (part of this
registration). Nothing below computed; no data fetched.
- Universe: common stock, 09:30 open > $5, 14d avg volume >= 1M, ATR14 > $0.50 (prior sessions). RVOL = 09:30-09:34
  SIP volume / its 14-session average (>= 10 obs); RVOL >= 1, top 20. Direction = the 5-minute candle; stop entry at
  the OR high/low from 09:35; stop 10% ATR14; flat 15:55; no target.
- Lab-AU1 long+short (the paper); Lab-AU2 long only.
- Costs 5bp/side (1x), 10bp/side (2x). SIP minutes 2022-01-03 .. 2026-09-30, halves split 2024-06-01 (H2 is
  out-of-sample for the paper).
- Pass (per variant): 2x net > 0 in both halves; day-clustered t >= 2.0 at 1x; >= 95th pct of a coin-flip-direction
  placebo (1,000 draws). Otherwise dead; nothing re-tuned.


## Amendment — Lab Round 20, Study Lab-AV: Study Lab-AT's opening imbalance on historical SIP ticks (pre-register; 1 variant, N 673 -> 674)

`date`: Thu Oct 1 03:20 PDT 2026. Why: Alpaca's free plan serves historical SIP NBBO quotes and trades (verified
back to 2018), so AT's idea need not wait 40 recorded sessions. Nothing below computed; no tick data fetched.
- Rules: exactly `daytrade/plans/open_imbalance.md` and the lab's `OpenImbalance` strategy code (QI >= +0.20 and
  FLOW >= +0.10 long; mirror short; window 09:30:00-09:34:59; enter 09:35 + 1s; exit 10:05:00; stop at the window
  low/high -/+ $0.01). SIP NBBO replaces Schwab L1 (quote sizes in shares; NBBO, not one venue).
- Symbols: **QQQ and SPY only** (the two cheapest instruments; the data budget, fixed before looking).
- Data: SIP quotes (sampled to the last quote of each second, which is all the strategy reads) and every SIP trade in
  the window; SIP quotes 09:35:00-09:35:05 and 10:05:00-10:05:05 for the fills; SIP minute bars 09:35-10:06 for the stop.
- 2022-01-03 .. 2026-09-30, halves split 2024-06-01. Costs: fills at the NBBO + 0.5bp/side (1x); + 1.0bp/side plus
  the half-spread again (2x). Stops on minute bars at 1bp/side (1x) / 2bp (2x).
- Pass: 2x net > 0 in both halves, day-clustered t >= 2.0 at 1x, sign-flip placebo (random direction on the same
  trades, gross mid-to-mid return minus the same cost) >= 95th pct. Otherwise dead; thresholds not re-tuned.
- Pre-check done: RESULTS.md and NEXT.md have no opening-imbalance study (only closing-auction imbalance, AC/add. 35).


## Amendment — Lab Round 21, Study Lab-AW: VWAP trend on QQQ / TQQQ (Zarattini & Aziz 2023) (pre-register; 2 variants, N 674 -> 676)

`date`: Thu Oct 1 03:35 PDT 2026. Source SSRN 4631351 (QQQ 2018-23 Sharpe 2.1, commissions only). Full rules:
`daytrade/plans/vwap_trend.md`. Nothing computed; no data fetched. RESULTS.md/NEXT.md grep: no VWAP-trend study.
- QQQ 1-min close vs session VWAP from 09:31; long above, short below; reverse at the next minute's open on a cross;
  flat 15:55; 2% catastrophe stop. Lab-AW1 QQQ, Lab-AW2 TQQQ on QQQ's signal.
- Costs: QQQ 0.5/1.0bp per side, TQQQ 1.5/3.0bp per side (1x/2x). SIP minutes 2022-01-03 .. 2026-09-30, halves
  at 2024-06-01. Unit = day.
- Pass: 2x day-mean > 0 both halves; day t >= 2.0 at 1x; >= 95th pct of a segment-direction placebo. Report the
  correlation with the noise leg.


## Amendment — Lab Round 22, Study Lab-AX: late-day continuation of +25% movers, long only (pre-register; 1 variant, N 676 -> 677)

`date`: Thu Oct 1 ~03:30 PDT 2026 (the commit time is the stamp). Plan: `daytrade/plans/late_mover.md`. Nothing computed; no data fetched.
- Motivation: the RESULTS.md intraday-setups table's "stocks down >= 25% by 15:00 keep falling into the close (~-1.5% gross, both halves), untradable (Rule 201,
  HTB)". The long mirror has never been tested (grep RESULTS.md/NEXT.md).
- Rules: common stock, prev close >= $5; at 15:00 (14:59 bar close) day change >= +25% and 09:30-15:00 $ volume
  >= $10M; buy at the next minute's open; sell at 15:55; 10% catastrophe stop; long only.
- Costs 20/40bp per side (1x/2x). SIP minutes 2022-01-03 .. 2026-09-30, halves at 2024-06-01.
- Pass: 2x > 0 both halves; day-clustered t >= 2 at 1x; >= 95th pct of a random-earlier-hour placebo on the same
  stock-days. Diagnostic: the losers' mirror gross.


## Note — reconciliation of the lab's Rounds 19-22 with the main Rounds 19-25 (merge of 2026-10-01, later)
The lab registered Rounds 19-22 (Lab-AU 2, Lab-AV 1, Lab-AW 2, Lab-AX 1 = 6 variants) in parallel with the main
program's Rounds 19-25. The lab's commits were not on origin when those rounds were numbered: its pushes had
been rejected and the errors hidden. The lab's files carry their own local N (671 -> 677); read them as **+6 on
top of the main count**. The program N after both is **691 + 6 = 697**. Lab-AS and Lab-AT were already counted
in 691 (see the Round 18 reconciliation note above).


## Amendment — Lab Round 23, Study Lab-AY: trading LULD halt reopenings in big movers (pre-register; 2 variants, program N 697 -> 699)

`date`: Thu Oct 1 ~04:15 PDT 2026 (the commit time is the stamp). Plan (part of this registration):
`daytrade/plans/halt_resume.md`. The minute data is Lab-AX's (already fetched for other reasons); NO halt statistic
has been computed. Grep of RESULTS.md / NEXT.md / this file: no halt-trading study.
- Halt inferred from minute bars: >= 5 minutes without a bar between 09:45 and 15:00, the last bar >= +5% / <= -5%
  vs 5 bars earlier, active in >= 8 of the 10 prior minutes. Market order during the halt, filled at the first
  post-gap bar's open (the reopening auction); hold 30 minutes; 10% stop; flat 15:55; one per name per day.
- Lab-AY1 = buy after a halt UP; Lab-AY2 = buy after a halt DOWN. Costs 20/40bp per side. Halves at 2024-06-01.
- Pass per variant: 2x > 0 both halves; day-clustered t >= 2 at 1x; >= 95th pct of a random-minute placebo on the
  same stock-days.


## Amendment — Round 26: closing-auction imbalance on the night picks — Study BD (pre-register; 2 variants, program N 699 -> 701)

`date`: Thu Oct 1 2026 (stamped by the commit), before any imbalance record is downloaded. The parked Round 13 AC
idea (the one untested mechanism with a named payer), now testable: the user supplied a Databento key. Source:
Bogousslavsky & Muravyev (JFM 2023): passive/index flow pushes the closing cross off the mid and ~85% reverts by
the next morning; the published imbalance is the ex-ante measure of that pressure. Payer: close sellers (passive,
forced, risk-reducing) who demand liquidity in the auction.

Data: Databento `imbalance` schema, closing-auction messages, for each night pick's listing exchange (NYSE ->
XNYS.PILLAR, Nasdaq -> XNAS.ITCH, Arca -> ARCX.PILLAR, NYSE American -> XASE.PILLAR; Cboe BZX listings, ~4% of
picks, have no feed here and keep z = 0), 15:50:00-15:52:00 ET on the pick day, 2021-26. Timing: the FIRST
closing-imbalance message at or after 15:50:00 and before 15:52:00 is the signal (what a live order could see:
NYSE accepts a buy MOC that offsets a sell imbalance after 15:50; Nasdaq takes MOC until 15:55).
Feature: SIR = signed imbalance shares / 20-day ADV in shares (positive = SELL imbalance), ADV shares = the pool's
dollar ADV / the 15:50 price. z constants from the 2021-23 picks.
- BD1: weight = live v1 tilt x clip(1 + 0.25 z(SIR), 0.25, 2), renormalised (more weight on heavier selling).
- BD2: drop picks with a BUY imbalance in the first message (the close is being bid up: little pressure left to revert).
Judged exactly as Round 20 (night returns from the official crosses; V7 and Roth cash books; $2.3k / $10k / $25k;
2.5bp/side judged, tier_hi reported; increment > 0 in both halves; NW t >= 2; sign-flip and within-night
feature-shuffle placebos >= 95th; dDD >= -2pp; P(DD>50%) <= 5%). Also: coverage by exchange, terciles per half,
Spearman with TOW / vol20 / depth. DSR at N 701. A pass is SHADOW only: live use needs a paid live imbalance feed
(Massive $49/mo, NYSE-listed only; Databento live for Nasdaq), priced in the writeup.

## Amendment — Lab Round 24, Study Lab-AZ: Nasdaq closing-cross convergence from the NOII (pre-register; 2 variants, program N 701 -> 703, after main Round 26 BD)

`date`: Thu Oct 1 ~04:30 PDT 2026 (the commit time is the stamp). Plan (part of this registration):
`daytrade/plans/close_cross.md`. Data: Databento XNAS.ITCH imbalance (user's key; ~$52 of the free credit). Nothing
downloaded beyond a 70-second QQQ field sample.
- Universe: top 100 Nasdaq-listed common stocks by Nov-Dec 2021 dollar volume + QQQ, TQQQ (fixed file).
- At close - 5:30 (15:54:30): the latest closing NOII, dev = near / ref - 1. Long if dev >= +10bp and side B; short if
  dev <= -10bp and side A. Enter at the SIP NBBO 1s later; exit market-on-close at the official close.
- Lab-AZ1 long+short; Lab-AZ2 long only. Costs NBBO+0.5bp / close 0.5bp (1x); NBBO+1bp+half-spread / close 1bp (2x).
- Halves at 2024-06-01. Pass: 2x > 0 both halves; day-clustered t >= 2 at 1x; >= 95th pct of a random-side placebo.
- Shared Databento credit: this pull (~$52) plus main Round 26 BD (night picks, 2-minute windows) stay inside the
  $125 free credit; each study prices its pull with `metadata.get_cost` first and stops above its estimate.


## Amendment — Round 27: the IBS leg's entry vs the 09:28 indicative opening gap — Study BE (pre-register; 2 variants, program N 703 -> 705)

`date`: Thu Oct 1 2026 (stamped by the commit), before any opening-imbalance record is downloaded. The IBS leg buys
the month's top-3 ETFs at the next open after a close with IBS < 0.2; its return is open d+1 -> open d+2 (the
overnight bounce d -> d+1 is NOT captured: that is V6). Mechanism: when the ETF is already indicated well above the
prior close before the open, the oversold bounce has been paid out overnight and buy-side pressure sets a high open
price, leaving less for the hold (short-term reversal decays within a day: Pagonidis 2014; overnight/intraday split:
Lou-Polk-Skouras 2019). Payer of the shipped leg: short-horizon sellers; this asks whether the edge is gone on
gap-up entries.
Signal (knowable before the 09:30 market order): the opening auction's indicative price in the last opening
imbalance message at or before 09:28:59 ET (Databento `imbalance`, auction_type 'O'; ARCX.PILLAR for the 16 Arca
ETFs, XNAS.ITCH for QQQ/SMH; ind_match_price, else cont_book_clr_price, else ref_price), divided by the prior
session's official closing cross (Alpaca auctions, raw, cached for the IBS audit) minus 1 = GAPI.
- BE1: skip the entry (that slice idles in BIL) when GAPI >= +0.5%.
- BE2: skip when GAPI >= +1.0%.
Data from 2018-05 (the feed's start): judged on 2018-05..2023 (select) and 2024-26 (judge) halves on the unit IBS
leg, and the books 2021-26 as Round 20 (V7 and Roth cash; $2.3k / $10k / $25k; 2.5bp/side judged, tier_hi
reported; increment > 0 in both halves; NW t >= 2; sign-flip placebo and a within-day shuffle of the skip flags
>= 95th; dDD >= -2pp). Also reported: per-entry open->open net by GAPI tercile per period. DSR at N 705.


## Amendment — Lab Round 25, Study Lab-BA: short the reopening after a halt (pre-register; 3 variants, program N 705 -> 708)

`date`: Thu Oct 1 2026 (the commit time is the stamp). Motivated by Lab-AY (longs lose ~130bp/30 min after a halt
either way); no short-side statistic computed. Plan (part of this registration): `daytrade/plans/halt_short.md`.
- Lab-AY's detection, universe, 30-minute hold, flat 15:55; entry SELL SHORT at the reopening; 10% stop above the fill.
- Lab-BA1 halt up, all names; Lab-BA2 halt up, names Alpaca flags easy_to_borrow+shortable today (disclosed look-ahead
  proxy for a locate); Lab-BA3 halt down when the reopening print > 0.9 x previous close (no SSR today).
- Costs 20/40bp per side. Pass: 2x > 0 both halves; day-clustered t >= 2 at 1x; >= 95th pct of a random-30-minute-
  short placebo; mean without the 20 best trades > 0 at 1x.


## Amendment — Lab Round 24 result: Study Lab-AZ UNTESTABLE as registered (0 trades)
Nasdaq's NOII publishes the near/far indicative prices only from 15:55. The 15:50-15:55 early messages have
cont_book_clr_price = 0, so the 15:54:30 rule never fires (0 signals in 1,190 sessions). This is a registration
error (MISTAKES.md), not a result. Lab-AZ's 2 variants stay counted in N.

## Amendment — Lab Round 26, Study Lab-BB: early closing-imbalance size as a 15:54 signal (pre-register; 2 variants, program N 708 -> 710)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Plan (part of this registration): `daytrade/plans/close_imbalance.md`.
Data: Lab-AZ's NOII files (already paid). No return computed.
- r = signed imbalance / paired shares from the latest closing message at 15:54:30. Long the top 5 with r > 0; short
  the bottom 5 with r < 0. Enter at the NBBO 1s later; exit market-on-close at the official close.
- Lab-BB1 long+short; Lab-BB2 long only. Costs as Lab-AZ.
- Pass: 2x > 0 both halves; day-clustered t >= 2 at 1x; >= 95th pct of a random-side placebo; mean without the top 20 > 0.


## Amendment — Lab Round 26 result: Study Lab-BB DEAD; Lab Round 27, Study Lab-BC pre-registered on the H2 holdout (1 variant, program N 710 -> 711)
`date`: Thu Oct 1 2026 (the commit time is the stamp).
- **Lab-BB result (DEAD, both).** The imbalance side predicts the close: placebo 100th pct, gross +3.4bp (long +4.1)
  from the 15:54:31 mid to the official close. But the mean entry spread is 7.5bp, so net −1.3bp (t −4.0), negative
  in both halves; long-only −0.7bp. Without the top 20 −1.6bp. study_lab_bb_close_imbalance.md.
- **Lab-BC (designed on H1 only, judged on H2 only).** In H1 (2022-01 .. 2024-05) Lab-BB1's gross rises
  monotonically with |r| = |imbalance / paired|: by quartile −1.9 / +2.6 / +3.6 / **+7.0bp**; the top quartile nets
  +2.1bp at 1x. Spread quartiles matter less. Rule: Lab-BB1 (long the top 5 with r > 0, short the bottom 5 with
  r < 0), taking ONLY names with |r| >= **1.6742** (the H1 75th percentile of |r| among Lab-BB1 trades). Entry, exit
  and costs as Lab-BB.
- **Judged ONLY on 2024-06-03 .. 2026-09-30 (H2), which the rule never saw.** Pass: H2 net > 0 at 2x; day-clustered t
  >= 2 at 1x on H2; >= 95th pct of a random-side placebo on H2; H2 mean without the top 20 > 0. H1 is reported for
  reference only (in-sample).


## Amendment — Lab Round 28, Study Lab-BD: QQQ's early closing imbalance, every day, H2 holdout (1 variant, program N 711 -> 712)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Designed on H1 only.
- In H1, QQQ (median spread 0.31bp) moves from the 15:54:31 mid to the official close: by quintile of r = signed
  imbalance / paired at 15:54:30, −2.4 / +1.9 / +1.8 / +4.1bp (TQQQ noisy, spread 2.7bp: excluded).
- Rule: QQQ only. Long if r >= **0.2585** (the H1 80th pct); short if r <= **-0.2824** (the H1 20th pct). Enter at the
  NBBO at 15:54:31 (Lab-AZ's timing); exit market-on-close (official close). The same stated flat-by-15:55 exception
  (the 16:00 cross).
- Costs: 1x = NBBO + 0.5bp in, 0.5bp out; 2x = NBBO + 1bp + half-spread again in, 1bp out.
- **Judged on H2 only (2024-06-03 .. 2026-09-30):** H2 net > 0 at 2x; t >= 2 at 1x (days are the unit: one trade a day
  at most); >= 95th pct of a random-side placebo; without the top 20 > 0. Long and short legs are reported separately.


## Amendment — Lab Round 29, Study Lab-BE: buy (short) in the Nasdaq opening cross after a big sell (buy) imbalance, exit 10:00 (pre-register; 2 variants, program N 712 -> 714)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Plan (part of this registration):
`daytrade/plans/open_cross_reversal.md`. A priori rule; only the field availability was checked (4 days).
- 09:28:00 latest opening message; d = near / ref - 1. Long the 5 most negative d with a sell imbalance; short the 5
  most positive d with a buy imbalance. Enter in the opening cross (official open); exit 10:00 at the NBBO.
- Lab-BE1 long+short; Lab-BE2 long only. Costs 0.5/1bp at the cross; NBBO + 0.5bp (1x) / + half-spread + 1bp (2x) at exit.
- Pass: 2x > 0 both halves; day-clustered t >= 2 at 1x; >= 95th pct of a random-side placebo; mean without the top 20 > 0.
- Databento: ~$6 (09:27-09:28 window); with Lab-AZ's $64.88 and main BD/BE, inside the $125 credit.


## Amendment — Lab Round 29 result: Study Lab-BE UNTESTABLE as registered (0 signals; near price 0 before 09:28:00)
Nasdaq's opening NOII carries near/far only from 09:28:00. The registered window ended at 09:28:00, so 0 signals.
$27.13 spent (MISTAKES.md). Lab-BE's 2 variants stay counted.

## Amendment — Lab Round 30, Study Lab-BF: Lab-BE's rule at 09:28:30 on a 30-name universe (pre-register; 2 variants, program N 714 -> 716)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Plan: `daytrade/plans/open_cross_reversal.md` (Lab-BF section).
- Universe: the first 28 names of Lab-AZ's list (top by Nov-Dec 2021 dollar volume) + QQQ + TQQQ. Budget: Databento
  bills ~$0.00022 per symbol-day; 30 names x 1,190 days ~ $8. Combined spend ~$116 of $125.
- Decision 09:28:30: each name's latest opening message at or before 09:28:30 with a near price > 0.
  d = near / ref - 1. Long the 2 most negative d with side A; short the 2 most positive d with side B.
- Enter in the opening cross (official open); exit 10:00 at the NBBO. Costs and pass bar as Lab-BE (2x > 0 both
  halves; t >= 2 at 1x; placebo >= 95th; without the top 20 > 0). Lab-BF1 long+short; Lab-BF2 long only.
- Gate in code: before the full pull, assert that >= 50% of 09:28:00-09:28:30 messages have near > 0 on 5 sample days.


## Amendment — Lab Round 31, Study Lab-BG: Lab-BC's closing-imbalance signal with PASSIVE entry (pre-register; 1 variant, program N 716 -> 717)
`date`: Thu Oct 1 2026 (the commit time is the stamp).
- **Disclosure:** H2's gross for Lab-BC (+6.3bp mid -> close) is already known. What is NOT known is the outcome
  conditional on a passive fill, which is what this tests (adverse selection).
- Signals: Lab-BC's (Lab-BB1 names with |r| >= 1.6742; long r > 0, short r < 0), decided at 15:54:30.
- Entry: a limit order at the 15:54:31 NBBO **bid** for a long (ask for a short), resting until 15:55:00 (Nasdaq's MOC
  cutoff), then cancelled. Filled iff an SIP trade prints at or below the bid (long) / at or above the ask (short)
  after 15:54:31 and before 15:55:00. Conservative: a print AT the limit counts only once the displayed size at the
  limit at placement has traded (queue); a print through the limit fills at once. If filled, a market-on-close order is
  sent (before 15:55) and the exit is the official close.
- Costs: 1x 0.5bp in + 0.5bp out; 2x 1bp in + 1bp out (the fill is AT the limit, no spread paid).
- Judged on H2 (2024-06-03 .. 2026-09-30): net per FILLED trade > 0 at 2x; day-clustered t >= 2 at 1x; without the top
  20 > 0; and a placebo: random side on the same filled trades (sign-flip of mid -> close) >= 95th pct. Fill rate and
  $/day (fills x edge) reported; H1 for reference.


## Amendment — Round 28: night picks that LULD-halted that day — Study BF (pre-register; 2 variants, program N 717 -> 719)

`date`: Thu Oct 1 2026 (stamped by the commit), before any minute bar is downloaded. Source: the lab's halt studies
(study_lab_ay_halts.md, study_lab_ba_halt_short.md): in big-mover stock-days 2022-26, after an inferred LULD halt
the stock slides ~−130bp over the next 30 minutes whichever way the halt went (t −4..−5). Mechanism for the night
leg: a halt marks a violent, information-driven move (or forced liquidation that is not over); such drops drift
rather than revert (Savor 2012), unlike the liquidity-driven drops the night leg is paid to absorb. Payer of the
shipped leg: liquidity demanders; this asks whether halted picks are a different, worse population. Against: news
categories (add. 12) and depth/vol features (add. 23) are dead, and halts correlate with depth and vol20.

Halt flag (the lab's rule, fixed now): from Alpaca SIP 1-minute bars of the pick day, 09:30-15:49 ET, a run of >= 5
consecutive minutes with no bar (no trades) that starts within 2 minutes after a 5-minute window whose close moved
>= 5% (either direction) from its start. Reported separately: halts whose triggering move was down. A pick with no
minute data keeps flag = False (counted).
- BF1: drop picks with any halt that day (their slice idles).
- BF2: halted picks at half weight (live v1 tilt x 0.5, not renormalised).
Judged exactly as Round 20 (official-cross night returns; V7 and Roth cash; $2.3k / $10k / $25k; 2.5bp/side judged,
tier_hi reported; increment > 0 both halves; NW t >= 2; sign-flip and within-night flag-shuffle placebos >= 95th;
dDD >= -2pp; P(DD>50%) <= 5%). Also: halt share by half, per-pick net halted vs not (and down-halts), Spearman of
the flag with depth / vol20 / TOW. DSR at N 719.


## Amendment — Lab Round 32, Study Lab-BH: announcement-return drift proxy (up gap >= 5% on >= 3x volume), long at the next open, hold 20 / 5 sessions (pre-register; 2 variants, program N 719 -> 721)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Plan (part of this registration): `daytrade/plans/event_drift.md`.
RESULTS.md/NEXT.md grep: earnings appears only as a news filter on the overnight leg; multi-day drift is untested.
- Common stock, prev close >= $5, ADV20 >= $20M; day 0: open/prev close - 1 >= +5% and volume >= 3x ADV20 shares.
  Buy day 1's opening cross; sell at day H's official close (BH1 H=20, BH2 H=5). Long only. Adjusted prices for returns.
- Costs 10/20bp per side. Excess over SPY on the same window. Month-clustered t. Random-date placebo on the same stocks.
- Pass: 2x excess > 0 both halves; t >= 2 (1x excess); placebo >= 95th; without the top 20 > 0.


## Amendment — Lab Round 32 result: Study Lab-BH DEAD (long), the drift is a REVERSAL; Lab Round 33, Study Lab-BI pre-registered on 2017-2021 (2 variants, program N 721 -> 723)
`date`: Thu Oct 1 2026 (the commit time is the stamp).
- **Lab-BH result.** Up gap >= 5% on >= 3x volume, buy the next open:
  - 20-day excess over SPY −185bp at 1x (t −3.1, placebo 0th pct), negative EVERY year 2022-26 (−71..−300bp),
    median −194bp;
  - 5-day −85bp.
  - DEAD as a long. study_lab_bh_event_drift.md.
- **Lab-BI (the short side), judged ONLY on 2017-01-03 .. 2021-12-31.** That window has not been fetched or looked at
  by anyone in this program for this question.
  - Same events (common stock, prev close >= $5, ADV20 >= $20M, gap >= +5%, volume >= 3x ADV20 shares).
  - SHORT at day 1's opening cross, cover at day 20's official close.
  - Hedged with an equal-notional SPY long over the same window, so the P&L is the excess.
  - Costs: 1x = 10bp/side on the stock + 0.5bp/side on SPY + borrow 0.5%/yr; 2x = 20bp/side + 1bp/side + 1%/yr.
  - Lab-BI1: all events. Lab-BI2: only names Alpaca flags easy_to_borrow+shortable today. This is a disclosed
    look-ahead proxy; delisted names have no flag and are excluded from BI2.
  - Halves: 2017-2019 / 2020-2021.
  - Pass, per variant: hedged net > 0 at 2x in both halves; month-clustered t >= 2 at 1x; >= 95th pct of a placebo
    (the same stocks on random non-event dates, same short+hedge, 1,000 draws); mean without the 20 best events > 0.
  - Shorts need a margin account (no Roth, no cash account under $2k): stated for any $ figures.


## Amendment — Lab Round 34, Study Lab-BJ: calendar-month return seasonality, top 20 of the 500 most traded stocks (pre-register; 1 variant, program N 723 -> 724)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Plan (part of this registration): `daytrade/plans/seasonality.md`.
Heston & Sadka (2008); Keloharju, Linnainmaa & Nyberg (2016). grep: untested here.
- Monthly adjusted SIP bars 2016-01 .. 2026-09. Universe: price >= $5, top 500 by trailing-12-month dollar volume.
  Signal = mean same-calendar-month return over the prior 5 years (>= 3 obs). Long the top 20, equal weight, close to
  close, rebalanced monthly. Excess vs the equal-weight universe.
- Test 2021-01 .. 2026-09; halves at 2024-01. Costs 10/20bp per side, full turnover.
- Pass: 2x excess > 0 both halves; t >= 2; >= 95th pct of a random-20 placebo; without the 5 best months > 0.


## Amendment — Lab Round 35, Study Lab-BK: short both legs of a 3x LETF pair (volatility drag), weekly rebalanced (pre-register; 2 variants, program N 724 -> 726)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Plan (part of this registration): `daytrade/plans/letf_decay.md`.
grep: untested here.
- Lab-BK1 TQQQ+SQQQ; Lab-BK2 UPRO+SPXU. Short 0.5E each, rebalance at each week's last close (MOC). Adjusted SIP daily,
  2016-01 .. 2026-09. No short rebate.
- Costs 1x: 5bp/side + borrow 2%/4% (bull/bear); 2x: 10bp/side + 5%/10%.
- Pass: 2x weekly net > 0 both halves (2016-20 / 2021-26); t >= 2; without the best 5 weeks > 0; max DD (1x) > -40%.
  Reference: QQQ+PSQ shorted the same way.


## Amendment — Lab Round 36, Study Lab-BL: distance-method stock pairs (Gatev, Goetzmann & Rouwenhorst 2006) on the 100 most-traded stocks (pre-register; 1 variant, program N 726 -> 727)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Prior: weak (Do & Faff 2010: the returns decayed after 2002).
grep: ETF pairs dead (add. 27 R4); stock pairs untested.
- Every 6 months from 2017-01: formation = the previous 12 months. Universe = common stock, price >= $5, the top 100 by
  formation-period dollar volume (adjusted SIP daily, 2016-01 .. 2026-09). Normalise each price path to 1 at the
  formation start; pick the 20 pairs with the smallest sum of squared differences.
- Trading = the next 6 months, daily closes: open when the normalised spread diverges by > 2 formation SDs (long the
  low leg, short the high leg, $1 each); close at the next crossing or the period's end. Re-open allowed.
- Each pair gets 1/20 of capital (committed-capital returns). Costs: 1x 10bp per side per leg (4 legs per round trip),
  2x 20bp.
- Halves 2017-2021 / 2022-2026-09. Pass: 2x monthly net > 0 both halves; t >= 2 (monthly); without the best 3 months
  > 0; >= 95th pct of a placebo (20 random pairs from the same universe, same rules, 200 draws).


## Amendment — Lab Round 37, Study Lab-BM: post-split drift after FORWARD-split ex-dates (pre-register; 1 variant, program N 727 -> 728)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Source: Ikenberry, Rankine & Stice (1996); Desai & Jain (1997)
(positive drift after splits). grep: untested here. Alpaca's corporate-announcement history is unusable before 2024,
so ex-dates are inferred from raw SIP daily bars.
- Event: a common stock whose raw open on day 0 / raw close on day -1 is within ±6% of 1/k for k in {2, 3, 4, 5, 10,
  20} (a k-for-1 forward split; reverse splits excluded). Raw post-split day-0 open >= $5; 20-day ADV (pre-split $)
  >= $5M. Raw SIP daily 2016-10 .. 2026-09 (Lab-BI's and Lab-AU's caches).
- Buy at day 0's official close (market-on-close); sell at day 60's official close. Return on raw prices after day
  0, adjusted by any further detected split in the window. Excess vs SPY (adjusted) on the same window.
- Costs 10/20bp per side. Halves: event years 2017-2021 / 2022-2026.
- Pass: 2x excess > 0 both halves; month-clustered t >= 2 (1x); >= 95th pct of a random-date placebo (same stocks, 60
  days, 1,000 draws); without the best 10 events > 0 (fewer events than the other studies).


## Amendment — Lab Round 38, Study Lab-BN: short-volatility (SVXY, −0.5x VIX futures) only in VIX term-structure contango, else T-bills (pre-register; 1 variant, program N 728 -> 729)
`date`: Thu Oct 1 2026 (the commit time is the stamp). grep: no SVXY / contango / VRP study here. Source: the volatility
risk premium (Carr & Wu 2009; Simon & Campasano 2014, the VIX futures basis).
- Signal: Cboe VIX close / VIX3M close on day t (cdn.cboe.com History CSVs) < 1 = contango.
- Position from day t+1's opening cross to day t+2's opening cross: SVXY if contango, else BIL. A switch trades at the
  opening cross (directed MOO-style order). Adjusted Alpaca SIP daily opens. 2018-03-01 .. 2026-09-30 (SVXY is −0.5x
  from 2018-02-28). Halves: 2018-03..2021-12 / 2022-01..2026-09.
- Costs: 1x 5bp/side per switch; 2x 10bp.
- Pass: monthly excess over BIL (net) > 0 at 2x in both halves; t >= 2 (monthly); max drawdown at 1x better than −50%;
  >= 95th pct of a placebo (random in/out days with the same in-market share, shuffled in 21-day blocks, 1,000 draws);
  without the best 5 months > 0. Reported beside SVXY buy-and-hold and SPY; Roth-compatible (long ETFs only).


## Amendment — Lab Round 39, Studies Lab-BO / Lab-BP / Lab-BQ: three monthly cross-sectional anomalies on the 500 most-traded stocks (pre-register; 3 variants, program N 729 -> 732)
`date`: Thu Oct 1 2026 (the commit time is the stamp). The frame is Lab-BJ's (`daytrade/research/bj_replay.py`: monthly
adjusted SIP bars for returns, raw closes for the $5 filter, top 500 by trailing-12-month dollar volume, long the top
20 equal weight at month m-1's close to month m's close, excess vs the equal-weight universe, full-turnover costs
10/20bp per side). Test months 2017-01 .. 2026-09; halves 2017-01..2021-12 / 2022-01..2026-09.
grep: 52w-high only as a swing filter, a night tilt and SPY timing (dead); low-vol and 1-month reversal untested.
- **Lab-BO 52-week-high momentum** (George & Hwang 2004): score = month m-1 close / max of the closes of months
  m-12..m-1; long the 20 highest (nearest the high).
- **Lab-BP low volatility** (Ang et al. 2006; Frazzini & Pedersen 2014): score = −std of monthly returns over months
  m-12..m-1 (>= 10 obs); long the 20 lowest-vol. Also report the Sharpe of the long portfolio vs the universe.
- **Lab-BQ 1-month reversal** (Jegadeesh 1990): score = −return of month m-1; long the 20 biggest losers.
- Pass, each: 2x excess > 0 both halves; t >= 2 (monthly); >= 95th pct of a random-20 placebo; without the best 5 months
  > 0. For Lab-BP the Sharpe of the long book must also beat the universe's in both halves.


## Amendment — Lab Round 39 result: Lab-BO / BP / BQ all DEAD (study_lab_bo_bp_bq_cross_section.md). Lab Round 40, Study Lab-BR: 12-1 momentum in the same frame (pre-register; 1 variant, program N 732 -> 733)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Jegadeesh & Titman (1993). grep: NEXT "Momentum sleeve at 25%:
promising, unvalidated"; theme/breakout/top-1% momentum dead (add. 28); the IBS leg uses ETF momentum. The plain
cross-sectional stock version is untested.
- Score = close of month m-2 / close of month m-13 - 1 (skip the last month); long the top 20 of the 500, equal weight,
  monthly. Lab-BJ's frame, costs and test months (2017-01 .. 2026-09; halves 2017-21 / 2022-26).
- Pass: 2x excess > 0 both halves; t >= 2; >= 95th pct of the random-20 placebo; without the best 5 months > 0.


## Amendment — Lab Round 41, Study Lab-BS: sector-ETF momentum rotation (Moskowitz & Grinblatt 1999) (pre-register; 1 variant, program N 733 -> 734)
`date`: Thu Oct 1 2026 (the commit time is the stamp). grep: no sector rotation / industry momentum study (the IBS leg
uses ETF momentum only to choose mean-reversion entries).
- Universe (fixed): the 11 Select Sector SPDRs XLB XLC XLE XLF XLI XLK XLP XLRE XLU XLV XLY (XLC from 2018-07, XLRE from
  2015-10; a fund joins once it has 13 months). Monthly adjusted SIP bars 2015-11 .. 2026-09.
- Score = 12-1 momentum (close m-2 / close m-13 - 1). Hold the top 3, equal weight, month-end close to month-end close.
- Benchmark: equal-weight all available sector SPDRs (excess), and SPY reported.
- Test 2017-01 .. 2026-09; halves 2017-21 / 2022-26. Costs 5/10bp per side, full turnover.
- Pass: 2x excess > 0 both halves; t >= 2 (monthly); >= 95th pct of a random-3 placebo; without the best 5 months > 0.


## Amendment — Lab Round 42, Study Lab-BT: long-only top-decile momentum vs the market on 1963-2015 (Kenneth French library) (pre-register; 1 variant, program N 734 -> 735)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Purpose: Lab-BR (12-1 momentum, top 20 of 500, 2017-26) failed only
on t (1.5) with ~10 years of Alpaca history. This tests the same long-only idea on the decades this program has never
used, survivorship-free.
- Data: Ken French "10 Portfolios Formed on Prior (12-2) Return", value-weighted monthly (CRSP), and the FF factors
  (market = Mkt-RF + RF). Downloaded 2026-10-01 (CRSP 202608); no return looked at before this registration.
- Book: hold the value-weighted TOP decile (Hi PRIOR) each month. Excess = Hi PRIOR - market.
- Judged on 1963-07 .. 2015-12 (the modern CRSP era, before this program's data). Halves 1963-07..1989-12 /
  1990-01..2015-12.
- Costs (full monthly turnover, conservative): 1x 20bp/month; 2x 40bp/month.
- Pass: 2x excess > 0 in BOTH halves; t >= 2 (monthly, judged period); the mean without the best 5 months > 0.
- Reported, not judged: 1927-1963 and 2016-2026-08, the worst 12-month excess (momentum crashes, e.g. 2009), CAGR vs
  market.
- If it passes: build a monthly momentum sleeve (Lab-BR's rule) in the lab as a PAPER SHADOW only. Its own live gate
  stays the lab's $500 gate; nothing in the live book changes.


## Amendment — Lab Round 43, Study Lab-BU: volatility-scaled top-decile momentum (Barroso & Santa-Clara 2015), 1963-2015 (pre-register; 1 variant, program N 735 -> 736)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Follows Lab-BT (PASS, crash-prone). Same French data and periods.
- Each month m: realised vol = std of the top decile's EXCESS returns over months m-6..m-1, annualised. Weight w =
  min(1, 12% / vol) in the top decile; 1 - w in the market. Excess = w x (Hi PRIOR - market) - cost x w.
- Costs as Lab-BT (20 / 40bp per month on the momentum weight).
- Judged on 1963-07 .. 2015-12, halves as Lab-BT. Pass (a risk fix, so risk-adjusted bars):
  - (a) the Sharpe of the scaled excess beats the unscaled excess's in BOTH halves;
  - (b) the worst 12-month excess is better than unscaled's;
  - (c) 2x excess > 0 both halves;
  - (d) t >= 2.
- Reported: 1927-63 and 2016-26-08, the worst-12-month windows.


## Amendment — Lab Round 44, Study Lab-BV: long-only long-term reversal, the bottom 60-13-month decile vs the market, 1963-2015 (pre-register; 1 variant, program N 736 -> 737)
`date`: Thu Oct 1 2026 (the commit time is the stamp). De Bondt & Thaler (1985). grep: untested here.
- Data: Ken French "10 Portfolios Formed on Prior (60-13) Return", value-weighted monthly (downloaded 2026-10-01, CRSP
  202608; no return looked at). Hold the LOW decile (Lo PRIOR); excess vs the market.
- Judged 1963-07 .. 2015-12, halves as Lab-BT. Costs: this decile's turnover is low; to be conservative, 1x 10bp/month,
  2x 20bp/month.
- Pass: 2x excess > 0 both halves; t >= 2; without the best 5 months > 0; worst 12-month excess reported.
- Reported: 1927-63, 2016-26-08, by decade.


## Amendment — Lab Round 45, Study Lab-BW: industry momentum on French's 49 industries, 1963-2015 (pre-register; 1 variant, program N 737 -> 738)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Moskowitz & Grinblatt (1999). Lab-BS (11 sector SPDRs, 2017-26)
was dead; this asks whether the premium itself is durable.
- Data: "49 Industry Portfolios", value-weighted monthly (CRSP 202608; no return looked at). An industry with a missing
  month (-99.99) is excluded that month.
- Score = 12-1 momentum of each industry's cumulative return (months m-12..m-2). Hold the top 5, equal weight;
  excess vs the market.
- Judged 1963-07 .. 2015-12, halves as Lab-BT. Costs: 1x 10bp/month, 2x 20bp/month.
- Pass: 2x excess > 0 both halves; t >= 2; without the best 5 months > 0. Reported: 1927-63, 2016-26, by decade.


## Amendment — Lab Round 46, Study Lab-BX: industry-ETF momentum (the implementable Lab-BW), 2017-2026 (pre-register; 1 variant, program N 738 -> 739)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Lab-BW passed on French's 49 industries (1963-2015) and was
weaker after 2010. This tests the version a $2-25k account or the Roth can hold.
- Fixed list, one liquid US industry ETF per industry, chosen before looking: XBI (biotech), XHB (homebuilders),
  XRT (retail), KRE (regional banks), KIE (insurance), XME (metals/mining), XOP (oil & gas E&P), OIH (oil services),
  SMH (semiconductors), IGV (software), ITA (aerospace/defense), IYT (transports), XPH (pharma), IHI (medical
  devices), XHS (health services), GDX (gold miners), IYR (real estate), IYZ (telecom), JETS (airlines), TAN (solar).
- Monthly adjusted SIP bars. Score = 12-1 momentum. Hold the top 5, equal weight, month-end close to month-end close.
  The first full signal is 2017-02 (SIP history starts 2016-01).
- Excess vs SPY (the implementable alternative). Equal-weight list also reported.
- Costs: 1x 10bp/month, 2x 20bp/month (full turnover).
- Halves 2017-02..2021-12 / 2022-01..2026-09.
- Pass: 2x excess vs SPY > 0 both halves; t >= 2; >= 95th pct of a random-5 placebo; without the best 5 months > 0.
- Either way, a PAPER SHADOW of this rule is built (forward evidence for Lab-BW's durable premium). A live test would
  need its own registration, the $500 gate and the user's approval.


## Amendment — Lab Round 47, Study Lab-BY: top-decile momentum with a market-trend crash filter (Faber 10-month SMA), 1963-2015 (pre-register; 1 variant, program N 739 -> 740)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Faber (2007); Daniel & Moskowitz (2016) on momentum crashes
after bear markets. Builds on Lab-BT (PASS, crash-prone) and Lab-BU (vol scaling; dead by bar). grep: no trend-filtered
momentum here (TSMOM cross-asset dead, add. 26b, is a different book).
- French data (CRSP 202608). Market index level = cumulative (Mkt-RF + RF). At the end of month m-1: if the market
  level > its 10-month average (months m-10..m-1), hold the value-weighted top momentum decile (Hi PRIOR) in month m;
  otherwise hold T-bills (RF). Cost: 20bp/month while in momentum (1x), 40bp (2x), plus 10bp per switch.
- Judged as a WHOLE SLEEVE vs the market (buy and hold) on 1963-07 .. 2015-12, halves as Lab-BT. Pass:
  - (a) CAGR at 2x costs >= the market's in BOTH halves;
  - (b) Sharpe > the market's in both halves;
  - (c) max drawdown better than the market's over the judged period;
  - (d) the worst 12-month return better than −30%.
- Reported: 1927-63 and 2016-26 (the recent, already-seen era), time in market, switches per year.


## Amendment — Lab Round 48, Study Lab-BZ: industry momentum (Lab-BW's top 5 of 49) with Lab-BY's trend filter, 1963-2015 (pre-register; 1 variant, program N 740 -> 741)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Combines the two best long-history findings: Lab-BW (industry
momentum, positive every decade) and Lab-BY's market filter (10-month SMA, else T-bills). Same costs and switch cost as
Lab-BY (on industry momentum: 10/20bp per month while in, + 10bp per switch). Whole-sleeve bars as Lab-BY:
- (a) 2x CAGR >= the market's in both halves;
- (b) Sharpe > the market's in both halves;
- (c) max DD better than the market's;
- (d) worst 12m better than −30%.
Reported: 1927-63, 2016-26.


## Amendment — Lab Round 49, Study Lab-CA: 3x daily-levered market with a 200-day trend exit ("Leverage for the Long Run", Gayed & Bilello 2016), 1963-2015 (pre-register; 1 variant, program N 741 -> 742)
`date`: Thu Oct 1 2026 (the commit time is the stamp). grep: the 200dma appears only as a gate on the swing book
("buys Sharpe for return"); a levered index with a trend exit is untested.
- Data: French DAILY factors (CRSP 202608). Market = Mkt-RF + RF.
- Levered fund (simulated, daily rebalanced like UPRO): r3 = 3 x market - 2 x (RF + 0.5%/yr financing spread) -
  0.95%/yr expense, applied daily.
- Rule: at day t's close, if the market index level > its 200-day average, hold the levered fund on day t+1, else
  T-bills (RF). Switch cost 10bp (1x) / 20bp (2x).
- Judged as a whole sleeve vs the market (buy and hold) on 1963-07-01 .. 2015-12-31, halves 1963-89 / 1990-2015.
- Pass:
  - (a) CAGR at 2x >= the market's in BOTH halves;
  - (b) Sharpe > the market's in both halves;
  - (c) the worst 12-month return better than −50%;
  - (d) max drawdown reported, and must be better than buy-and-hold 3x without the filter.
- Reported: 1927-63, and 2016-26 both simulated and with the real UPRO / SPY (Alpaca, adjusted daily).
- Small-account notes: it trades ~5-10 times a year, needs no margin (the leverage is inside the ETF) and works in a
  cash account and the Roth. The live book's IBS/conviction legs already hold 3x ETFs: a wash-sale check is needed
  before any taxable use.


## Amendment — Lab Round 50, Studies Lab-CB / Lab-CC: Cboe sentiment as a predictor of 20-day market returns (pre-register; 2 variants, program N 742 -> 744)
`date`: Thu Oct 1 2026 (the commit time is the stamp). Predictive tests, not timing overlays: a pass would be an input
for SIZING the live book's legs (main program's call), not a market-timing book (timing the index already lost on
return: the 200dma gate, Lab-BN, Lab-BY/BZ in 2016-26). Data: Cboe CSVs (cdn.cboe.com, downloaded 2026-10-01; no
return looked at) and the French daily market (CRSP 202608).
- **Lab-CB put/call contrarian.** Equity put/call ratio (equitypc.csv, 2006-11 .. 2019-10). Signal day t: the 10-day
  mean P/C, z-scored against its trailing 252-day mean/sd; HIGH = z >= +1 (fear). Hypothesis: HIGH -> higher forward
  20-day market return (t+1..t+20).
- **Lab-CC SKEW.** Cboe SKEW (1990 .. 2026-09). Signal: SKEW z-scored against its trailing 252 days; HIGH = z >= +1.
  Hypothesis: HIGH -> LOWER forward 20-day return.
- Test: forward 20-day return on signal days minus on all other days, Newey-West t (20 lags), in each half (CB:
  2006-11..2012-12 / 2013-01..2019-10; CC: 1990-2007 / 2008-2026-08). Pass: the hypothesised sign in BOTH halves AND
  NW |t| >= 2 over the whole sample. Overlapping windows are handled by the NW lags.


## Amendment — Lab Round 51, Study Lab-CD: volatility-managed market exposure (Moreira & Muir 2017), French daily 1963-2015 (pre-register; 1 variant, program N 744 -> 745)
`date`: Thu Oct 1 2026 (the commit time is the stamp). grep: portfolio vol targeting of the LIVE BOOK is dead (add. 9);
a vol-managed index sleeve is untested. Critique noted: Cederburg, O'Doherty, Wang & Yan (2020) find out-of-sample
gains weak.
- Monthly: weight w_m = c / RV_{m-1}, where RV is the realised variance of daily market returns in month m-1, capped
  at 2.0 (a 2x ETF's reach), floor 0. **c is fixed from 1927-1962 data** (the value making the mean weight 1 there), so
  nothing is fitted on the judged period.
- Return: w x market + (1 - w) x RF for w <= 1; for w > 1 the extra (w - 1) is financed at RF + 0.5%/yr, plus a
  0.9%/yr fee on the levered part. Turnover cost |dw| x 5bp (1x) / 10bp (2x).
- Judged on 1963-07 .. 2015-12 (halves 1963-89 / 1990-2015) vs the market. Pass:
  - (a) Sharpe > the market's in BOTH halves;
  - (b) CAGR at 2x costs >= the market's in BOTH halves;
  - (c) max DD better than the market's;
  - (d) the mean weight in the judged period between 0.6 and 1.6 (a sanity bound on c).
- Reported: 2016-26 simulated, and real SPY / SSO / BIL with the same weights.


## Amendment — Round 29 (deep search), Studies DS1 / DS2-3 / DS4 / DS5 (pre-register; 7 variants, program N 745 -> 752)
`date`: Fri Oct 2 2026 (the commit time is the stamp). Brief: `prompt_deep_search.md`; ranked list of 23 candidates
with the dead-list check: `deep_search_candidates.md` (committed with this amendment, before any number). Common to all:
night returns from the official crosses (`auction_audit.with_rets`, `ret_auc`); raw prices for any price filter; judged
at 2.5bp/side, tier_hi reported; book = V7 live today (`growth.cfg(1.0, 0, 2.48)`, `growth.V7`) at fixed $2.3k / $10k /
$25k unless stated; halves 2021-23 / 2024-26; NW t with 5 lags; sign-flip placebo 1,000 draws; DSR reported at N 752.

### DS1 — earnings-announcement premium as an overnight sleeve (3 variants)
Source: Frazzini-Lamont 2007; Barber-De George-Lehavy-Trueman 2013; Savor-Wilson 2016; Lou-Polk-Skouras 2019 (it
accrues overnight). Who pays: a premium for announcement risk and attention-driven buyers at the post-news open.
Not the same as add. 12 (earnings headlines on night picks).
- Events: every symbol on the Nasdaq earnings calendar (`api.nasdaq.com/api/calendar/earnings?date=d`, free) for
  announcement date d, 2020-10 .. 2026-09. History has no before-open/after-close time, so every window spans both
  candidate nights. Excluded: symbols not in the SIP panel, ETFs/ETPs, |window return| > 50% (data/corporate action).
- Liquidity from the panel, through d−1 only: ADV$ = 20-day mean of close × volume (split-invariant; no price filter).
- **E1** liquid (ADV$ >= $20M), hold close d−1 -> open d+1 (one round trip, 2 sides).
- **E2** thin (ADV$ $2M-$20M), same window.
- **E3** liquid, the two overnights only (close d−1 -> open d, close d -> open d+1; 4 sides; day d in cash).
- Unit: per-event return minus SPY's return over the same window, net of 2.5bp/side × sides. Series for t: by entry
  date (d−1), the equal-weight mean of that day's events.
- Pass (each variant): (a) mean net excess > 0 in both halves; (b) NW t >= 2 on the entry-date series; (c) sign-flip
  placebo >= 95th pct; (d) **feature placebo**: the same events moved to a random non-announcement date of the same
  stock in the same calendar year (>= 10 sessions from any announcement), 200 draws; the real mean must beat >= 95%;
  (e) for a variant passing (a)-(d), confirmed on Alpaca official crosses (opening cross at d+1 / d, closing cross at
  d−1 / d): mean net excess > 0 in both halves; (f) as a sleeve on the Roth cash book's idle night cash and on V7's,
  book maxDD not worse by > 2pp and 5y P(DD>50%) <= 5%. Reported: 2019-10 .. 2020-09 (panel2020) where the calendar
  covers it, tier_hi, correlation with the night / IBS / noise legs, by-year means.

### DS2 / DS3 — the noise leg's decision grid (2 variants)
Same rule, bands, sizing and 0.5bp/side noise cost (1.0bp reported); only the decision slots change.
- **G1 (DS2)**: decisions every 15 minutes from 10:00 to 15:45 (live: every 30 from 10:00 to 15:30).
- **G2 (DS3)**: the live 30-minute grid, but no new or reversed position at 12:00 / 12:30 / 13:00 / 13:30 (exits to
  flat allowed there).
- Pass: (a) V7 book increment > 0 in both halves at all three sizes; (b) the noise leg's unit return (QQQ/SMH 50/50)
  increment > 0 in the 2016-20 holdout; (c) NW t >= 2 on the daily book increment ($10k); (d) sign-flip placebo
  >= 95th; (e) G2 only: >= 95th pct of 100 placebos that block 4 random slots of the 12; (f) maxDD not worse by > 2pp,
  5y P(DD>50%) <= 5% at $10k.

### DS4 — night picks tilted by FINRA days-to-cover (1 variant)
Source: Boehmer-Huszar-Jordan 2010 (heavily shorted stocks reverse); covering into the next open. Who pays: short
sellers covering. Not AY (daily off-exchange short VOLUME). Data: FINRA consolidated short interest (free API), the
latest settlement whose publication is known by d: settlement date + 10 business days <= d. Feature x = log(1 + DTC).
- **Q1**: weights = live tilt × clip(1 + 0.25 z, 0.25, 2), renormalised to the live tilt's mean; z = (x − mu) / sd with
  mu/sd from 2021-23 picks; missing DTC -> z = 0 (AU3's exact construction). Hypothesis: high DTC bounces more.
- Pass: (a) increment > 0 in both halves at all three sizes; (b) NW t >= 2 ($10k); (c) sign-flip >= 95th; (d) feature
  shuffle within each night (200 draws) >= 95th; (e) dDD >= −2pp; (f) P(DD>50%) <= 5%. Reported: tier_hi, DTC
  coverage of picks, corr of DTC with vol20 / price / TOW.

### DS5 — night leg ×1.5 on tax-loss / window-dressing nights (1 variant)
Source: Grinblatt-Moskowitz 2004 (December tax-loss selling of losers); Ng-Wang 2004 (quarter-end selling of small
losers). Who pays: sellers dumping losers into the close for tax or reporting reasons.
- **S1**: the night leg's per-name size ×1.5 on entries made in the last 10 sessions of December and the last 3
  sessions of March / June / September (calendar known in advance; ~19 nights a year). Overnight debit charged at 12%.
- Pass: (a) increment > 0 in both halves at all three sizes; (b) NW t >= 2 ($10k); (c) sign-flip >= 95th;
  (d) **matched placebo**: ×1.5 on the same number of random nights per calendar year, 200 draws, the real increment
  must beat >= 95%; (e) dDD >= −2pp; (f) P(DD>50%) <= 5%. Low power expected (~110 nights): reported as such.

Anything that passes becomes a default-off switch with shadow logging, a kill rule, tests and a digest gate; nothing
goes live without the user.

## Amendment — Round 31 (EDGAR unblocked), Study ID: the session after an insider purchase filing (pre-register; 3 variants, program N 752 -> 755)
`date`: Fri Oct 2 2026 (the commit time is the stamp). Context: Round 30 (`study_outside_box_round30.md`) found
nothing; the user added an SEC contact, which unblocked DS14 and the parked EDGAR ideas. Exploration looks on select
data only (2020-23) are logged in `outside_box_explore_log.md` (L16-L20): NT filers, Form 144 and insider-buy
night tilts / 20-day drift were dead; EFFECT notices on night picks were outlier-driven (ex-top-5 0bp, like DS5) and
are **not** registered; SPAC trust (#13) was closed without a test (only ~8% of equity is idle for a month).
2021-23 has been seen for this signal (L19-L20: +20bp, t 3.4), so **2024-26 is the judge** (rule (g)).

**Mechanism.** An officer's or director's open-market purchase is public in a Form 4 by the next business day.
Attention-limited buyers (screeners, alert apps, newsletters) arrive during the following session, after the open,
so the stock drifts up from the opening cross to the closing cross. Not DS14's 20-day drift (dead in L19), not
Lab-BH (announcement gaps, 5-20 days).

- Events: SEC Form 3/4/5 data sets (quarterly, `insider_buys()`), document type 4 or 4/A with >= 1 non-derivative
  code-P acquisition; a reporting owner who is a Director or Officer; total P dollars in the filing >= $10,000;
  grouped by (symbol, filing date). Trade session = the first session strictly after the filing date (the filing is
  public before that session's open). Data end: 2026-03-31 (the last published set), so 2024-26 = 2024-01 .. 2026-03.
- Filters known before the open: 20-day ADV$ through the prior session >= $1M; raw prior close >= $5 (Alpaca raw daily
  bars, never adjusted prices).
- Trade: buy in the opening cross, sell in the closing cross of the same session. Unit = raw open -> close return (SIP
  daily open/close; a random 500-event judge-half sample is checked against Alpaca official crosses and reported).
- **ID1** all events; **ID2** ADV$ $1M-$20M; **ID3** ADV$ >= $20M.
- Sleeve in V7 (taxable margin account; daytime only, no overnight debit): a fixed 0.45 x equity of daytime buying
  power (fits beside the IBS half and the noise cap at the live 2.48 multiplier), split equally across the session's
  events, at most 10% of equity and 1% of ADV$ per name, whole shares on the raw open. Night, IBS, noise unchanged.
  Not for the Roth (cash account: same-day proceeds would fund the night buy unsettled).
- Costs: 2.5bp/side judged; tier_hi (`book.cost_bps` on raw price and ADV) reported.
- Pass (each variant): (a) book increment > 0 in 2021-23 and 2024-26 at $2.3k / $10k / $25k; (b) NW t >= 2 on the
  daily increment ($10k, full window); (c) sign-flip >= 95th; (d) feature placebo: every event moved to a random
  session of the same stock in the same calendar year with no purchase filing within 10 sessions, 200 draws, real
  beats >= 95%; (e) maxDD not worse by > 2pp; (f) 5y P(DD>50%) <= 5%; (g) the judge half alone: event-level mean net
  of 2.5bp/side > 0 with NW t >= 2 on the 2024-26 daily sleeve return. Reported: DSR at N 755, tier_hi, by year,
  correlation with the noise leg, the 2020 pre-window.

Anything that passes becomes a default-off switch with shadow logging, a kill rule, tests and a digest gate; nothing
goes live without the user.

## Amendment — Round 32 (event and structural edges): family A Studies A1 / A2 (pre-register; 2 variants, program N 755 -> 757) and family B deal-selection rules B1-B4 (no N)
`date`: Fri Oct 2 2026 (the commit time is the stamp). Candidates: `event_edge_candidates.md` (e67e794, 36 ideas,
before any number). No return of any of these events has been looked at, on any window.

### Family A: the session after a filing, ID3's frame (2 variants)
Mechanism as ID3: a filing public by the evening of day d draws attention-limited buyers during the next session, so
the stock drifts up from the opening cross to the closing cross. Who pays: the filer's information (an activist about
to push, an owner near control), bought late by screeners and alert readers.
- **A1 — Schedule 13D (activist) original filings.** Forms `SC 13D` and `SCHEDULE 13D` (EDGAR's form name from
  2024-12), not amendments, from EDGAR's quarterly full index 2020-07 .. 2026-09; subject company from each filing's
  header (`SUBJECT COMPANY`), mapped CIK -> ticker by EDGAR's `company_tickers.json` (current map: names that changed
  ticker or delisted are missed; reported as coverage). Grouped by (symbol, filing date).
- **A2 — 10%-owner open-market purchases.** SEC Form 3/4/5 data sets, document type 4 or 4/A, >= 1 non-derivative
  code-P acquisition, the reporting owners include a 10% owner and **none** is a director or officer (so A2 does not
  overlap ID's events), total P dollars >= $10,000; grouped by (symbol, filing date). Data end 2026-03-31.
- Common to both, exactly ID's construction (`research/sim/insider_day.py`): trade session = the first session
  strictly after the filing date; filters known before the open: 20-day ADV$ through the prior session >= $1M, raw
  prior close >= $5; buy the opening cross, sell the closing cross; unit = raw open -> close; |ret| < 50% (bad prints).
  Sleeve: 0.45 x equity in V7, equal split across the session's events, <= 10% of equity and <= 1% of ADV$ per name,
  whole shares on the raw open. Costs 2.5bp/side judged; tier_hi reported.
- Pass (each variant), ID's bar: (a) book increment > 0 in 2021-23 and 2024-26 at $2.3k / $10k / $25k; (b) NW t >= 2
  ($10k, full window); (c) sign-flip >= 95th; (d) feature placebo (same stock, same year, no event within 10
  sessions, 200 draws) >= 95%; (e) dDD >= −2pp; (f) 5y P(DD>50%) <= 5%; (g) 2024-26 alone: event-level mean net > 0
  and NW t >= 2 on the daily sleeve. Reported: DSR at N 757, tier_hi, by year, overlap with ID3 sessions, corr with
  the noise leg. A pass becomes a default-off shadow beside ID3, with a kill rule and a digest gate.

### Family B: deal-selection rules, written before any outcome (no N: contractual payoffs, judged deal by deal)
Every deal the rule selects is listed with its P&L at whole-share size; nothing is dropped after looking. "Pass" =
positive in aggregate, the worst deal's loss small and explained, the rule mechanical enough to alert on.
- **B1 — reverse-split round-up.** Universe: every Alpaca `reverse_splits` corporate action with ex-date E in
  2016-01 .. 2026-09, ratio N = old_rate / new_rate with 2 <= N < 1000 (>= 1000 belongs to B4), Alpaca SIP raw daily
  bars on S (the last session before E) and on E. Qualifies when the issuer filed, between E − 90 days and S,
  accepted before 15:30 ET on S, an EDGAR document (any form) that EDGAR full-text search returns for "reverse stock
  split" with a round-up clause ("rounded up to the nearest whole share" / "round up ... whole share") and **no** such
  document in the window says the rounding is at the participant / DTC level ("participant level", "DTC participant",
  "Cede"). Issuer match: the ticker in the hit's display name equals the Alpaca symbol (else CIK -> ticker map).
  Trade: buy 1 share at the raw close of S. Payoff per account: rounded up -> 1 post-split share, valued at the raw
  close of E and of E+5 sessions (shares can arrive late); not rounded (cash in lieu) -> P_E / N. Reported: P&L of
  every deal both ways, the break-even rounding probability, worst deal, deals/yr, $/yr per account and for two
  accounts (taxable + Roth). Unknowable from history: whether Schwab passes a round-up to a 1-share holder; that is
  the live check.
- **B2 — split-off exchange offers with odd-lot priority.** Every SC TO-I 2016-26 that EDGAR full-text search returns
  for "exchange offer" and "odd lot" in which an issuer offers shares of **another** company for its own shares, and
  whose text grants odd-lot priority (Round 31's regex). Entry: buy 99 parent shares at the close 5 sessions before
  expiry (Round 31's entry B). Payoff: the final exchange ratio (from the final-results filing; capped by the upper
  limit) × the subsidiary's close on the first session after expiry, minus the entry cost; if odd lots are prorated
  after all, the unaccepted shares are sold at the parent's close on that session.
- **B3 — cash tender offers by acquirers.** Every original SC TO-T 2016-01 .. 2026-03 that EDGAR full-text search
  returns for "net to the seller in cash", whose subject company has Alpaca bars and whose cover/offer text states a
  fixed cash price per share (CVRs valued at 0). Entry: close of the first session after the filing date. Exit:
  if the target's bars end within 250 sessions of entry, the last raw close (completion at the final, possibly raised,
  price); otherwise the deal failed: the close 5 sessions after the first close < 0.85 × offer, else session 250.
  Reported by pre-offer 20-day ADV$ (< $5M "small", $5-50M, > $50M), with holding days and the annualised return;
  12%/yr financing shown.
- **B4 — going-private odd-lot cash-outs.** Every SC 13E3 2016-26 that EDGAR full-text search returns for "reverse
  stock split" with "cashed out" / "cash payment" / "in lieu of fractional", listed (Alpaca bars on the filing date),
  with a fixed cash price per pre-split share for holders below the ratio. Entry: buy (ratio − 1) shares or fewer at
  the close of the first session after the first SC 13E3. Exit: the cash price if an Alpaca reverse split with
  old_rate >= the ratio follows within 365 days (paid ~10 sessions after E), else the close 365 days later.

## Amendment — Round 33 (event runbook, smaller-model session), Study EV1: cluster insider buys, next session open -> close (pre-register; 1 variant, program N 757 -> 758)

`date`: Fri Oct 2 2026 (the commit time is the stamp). Runbook: research/drafts/prompt_event_runbook.md.
Event: officer/director open-market purchases from `insider_buys()` (SEC Form 345 sets), `X[X.insider]`; per symbol,
chain filings whose consecutive filing dates are <= 5 days apart (distinct accessions) and emit one event at the
**completion date** of each chain of 2+ filings (known only once the cluster is visible), events file
data/research/program/events_cluster.parquet (snippet C, rule above). Trade: buy the opening cross of the first
session after the completion date, sell the closing cross the same session; ADV >= $20M; raw prior close >= $5;
|ret| < 50%. Track: FREQUENT. Who pays: at the cross, market makers and early sellers; the later-session buyers are
attention-limited screeners/newsletters reading "multiple insiders bought" lists. Why it persists: a cluster of two
or more distinct officer/director buys is harder to fake than a single buy and attention diffuses slowly, so the
open-to-close drift repeats; too small/manual/rare for funds to size into.
Select-half result (2021-23):
```
events 9787 -> trades 780  (195 per year)
net per trade +27.7bp  median +12.3bp  hit rate 53%  t +2.42
by year: 2020: -42.0bp (n 29)  2021: +21.2bp (n 198)  2022: +22.7bp (n 284)  2023: +45.2bp (n 269)
TRACK FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2: MEETS -> may pre-register
```
Judge: FREQUENT -> `event_runner run` (the registered Study ID bar, PASS/DEAD as printed).

## Amendment — Round 33 (overnight runbook loop), Study EV2: first insider purchase in 2+ years, next session open -> close (pre-register; 1 variant, program N 758 -> 759; renumbered below to 760)

`date`: Fri Oct 2 2026 (the commit time is the stamp), before any 2024-26 number. Runbook: research/drafts/prompt_event_runbook.md.
Event: officer/director open-market purchase filings from `insider_buys()` (`X[X.insider]`) at an issuer whose previous
open-market purchase filing by any reporting owner is >= 730 days earlier (no purchase in the data, which starts
2020-01-01, counts as none since 2020-01-01); events file data/research/program/events_firstbuy.parquet (snippet C,
built by research/sim/events_firstbuy_build.py; 3,011 events 2022-01..2026-03). Trade: buy the opening cross of the
first session after the filing date, sell the closing cross the same session; ADV >= $20M. Track: FREQUENT.
Who pays: opening-cross sellers and market makers; later-session buyers are attention-limited screeners reading
"first insider buy in years". Why it persists: a buy that breaks a 2-year silence is a rare, costly signal noticed
slowly; too small/manual for funds. Subset of ID3's events (not independent of the ID3 pass).
Select-half result (2022-23):
```
events 1449 -> trades 318  (159 per year)
net per trade +41.8bp  median +20.0bp  hit rate 53%  t +2.44
by year: 2022: +61.7bp (n 182)  2023: +15.0bp (n 136)
TRACK FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2: MEETS -> may pre-register
```
Judge: FREQUENT -> `event_runner run` (the registered Study ID bar, PASS/DEAD as printed).

**EV2 renumbering (before the judge, same night):** another session explored a variant of this idea on the select
half minutes earlier (commit d4a0401: it also counted every issuer's first buy in 2020-21 as "first in 2 years",
which a 2-year lookback cannot observe since the data start 2020-01; select t +1.66, FAILS, not registered). EV2 is
therefore the second construction of the same idea. Both count: **program N 758 -> 760**; the judge runs with N 760.

## Amendment — Discovery loop (session llm-trader-c5), deal rule DL1: DRIP optional cash purchases at a fixed discount (no N; registered before any outcome)

Source reading (2026-10-02): FTS for discounted OCP language in S-3D/S-3/S-3ASR/424B 2016-26 found ~90 issuers; almost
all say "a discount of 0-5% **at our discretion**, may vary each month" (Chatham, Hannon Armstrong, ONEOK, NNN, INDB,
Old National ...). Their monthly discounts are not in any filing, so they cannot be simulated. York Water's 5% is on
reinvested dividends only (OCP at 100%); TDS's 5% is dividends only. **Fixed OCP discounts written into the plan:
UMH Properties (UMH) and Monmouth REIT (MNR, acquired 2022)**, both "95% of market", $500 minimum. UMH's FY2025 10-K
confirms the plan is live ($5.8M of OCPs in 2025; $1,000 monthly cap since 2021-02-11, $5,000 before). Street-name
holders may join the OCP by certifying they are shareholders (UMH plan Q4).

**Payoff formula (UMH plan Q15-16, MNR the same template):** Investment Date (ID) = the 15th of each month (the
dividend payment date in dividend months, also ~15th), next NYSE trading day if closed. Price
P = max(0.95 x mean over the 4 sessions ending on ID of (high+low)/2, 0.95 x (high+low)/2 on ID), Alpaca SIP raw bars.
Shares = cash / P (fractional, as the plan credits).

**Deal rule (fixed now):** every month 2016-01 .. 2026-09 in which the plan was in force (UMH all months; MNR through
its last full month before the ILPT merger), invest **$1,000** (the current cap) at P. Exit at the **official close of
the 5th session after ID** (DRS transfer to Schwab, then sell in the closing auction). P&L = shares x close(ID+5) − $1,000.
No dividends added (an ex-date inside the hold makes it conservative). No fees (Schwab $0; DRS transfer $0).
Reported: months/yr, hit rate, mean/median/worst per month, by year, $/yr for one person (the cap is per participant,
so $/yr is the same at $2.3k / $10k / $25k; %/yr = $/yr over the balance), plus info-only lines for exit at ID+1 and
ID+10 and for UMH's $5,000 pre-2021 cap. **Verdict: PAYS if mean P&L per month > 0 with hit rate >= 60% and the
yearly sum > 0 in at least 2/3 of years; otherwise DEAD.** No change to the rule after the list is computed.

## Amendment — Discovery loop (session llm-trader-c5), deal rule DL2: issuer offers for its own listed warrants (no N; registered before any outcome)

Source reading (2026-10-02): FTS SC TO-I 2019-26 for "offer to exchange"/"offer to purchase" + "warrants" + "consent
solicitation"/"warrant amendment". Read Vivid Seats 2022 (0.240 Class A shares per public warrant), Payoneer 2024
($0.78 cash per warrant; warrants last $0.40) and AvePoint 2024 ($2.50 cash; last $1.87). The issuer pays a fixed
consideration per tendered warrant and asks for a consent that lets it force the rest at a lower ratio; the offer
usually needs that consent to close.

**Deal set (fixed now):** every SC TO-I 2019-01 .. 2026-09 by an issuer for its own exchange-listed warrants with a
fixed consideration per warrant (r shares, or $c cash, or both), terms parsed from the original offer text (ratio/cash,
warrant symbol); a deal is dropped only if no warrant bars exist on Alpaca for the entry date.

**Payoff (same template as Round 31's odd-lot study):** let L = the date of the last SC TO-I/A of the offer (the
results/expiry amendment). **Entry = warrant close 5 sessions before L** (or the first session after the original
SC TO-I if that is later). **Completed** if the warrant has no Alpaca bar more than 10 sessions after L (the amendment
retired them); then value = c + r x (stock close 2 sessions after L). **Not completed** (warrants still trading):
value = warrant close 2 sessions after L. Return = value / entry − 1. Whole warrants; at $2.3k/$10k/$25k the stake is
min(10% of equity, 5% of the warrant's 20-session median dollar volume before entry). No fees (Schwab $0 voluntary
reorg). Reported: deals/yr, hit, mean/median/worst return, $/yr at the three sizes, completed vs not, share vs cash.
**Verdict: PAYS if the median return > +1%, the mean > 0 and hit >= 70%; otherwise DEAD.** No rule change after the list.

## Amendment — Discovery loop (session llm-trader-c5), deal rule DL3: written-consent cash mergers (DEFM14C) (no N; registered before any outcome)

Source reading (2026-10-02): DEFM14C information statements ("per share in cash" + "written consent" + "merger"),
2016-26: 57 issuers. Read Datto 2022 ($35.50, NYSE "MSP"), Ocean Bio-Chem 2022 ($13.08, controller consent), Sterling
Check 2024 (cash OR 0.979 FA shares, prorated). The vote is already won; the merger can't close until 20 calendar
days after mailing (Rule 14c-2), and the open conditions are HSR / regulatory approvals and financing.

**Deal set (fixed now):** first DEFM14C per issuer 2016-01 .. 2026-09 whose text (a) names a single cash price
"$X per share in cash" (the most frequent such figure) and (b) has no stock leg (no "exchange ratio", "stock
consideration" or "at your election"); ticker parsed from "under the symbol “…”"; dropped if no Alpaca bars at entry.
**Entry:** the official close of the first session after the DEFM14C filing date. **Completed** if the stock's last
Alpaca bar is within 250 sessions of entry: value = X (cash at closing). **Otherwise:** value = the close 250 sessions
after entry. Return = value / entry − 1; days held = entry to last bar (or 250 sessions). Stake 10% of equity (whole
shares). Reported: deals/yr, hit, mean/median/worst return, mean annualised, $/yr at $2.3k/$10k/$25k.
**Verdict: PAYS if median return > +1%, mean > 0 and hit >= 80%; otherwise DEAD.** No rule change afterwards.

## Amendment — Discovery loop (session llm-trader-c5), deal rule DL4: liquidations trading below the proxy's low estimate (no N; registered before any outcome)

Source reading (2026-10-02): DEF 14A 2016-26 with "plan of dissolution" + "liquidating distributions" + "per share" +
"estimate": 76 issuers (most are SPACs or failed biotechs). Read Actua 2018 ($0.80-2.07 after a $14.89 special
dividend), Merrimack 2024 ($14.68-15.30), Third Harmonic 2025 ($5.13-5.33). The board estimates total
distributions per share as a range; stockholders vote; then cash goes out in one or more distributions (often an
initial one within weeks of approval, a final one after the wind-down, sometimes through a liquidating trust).

**Deal set (fixed now):** first DEF 14A per issuer 2016-01 .. 2026-06 with an estimate range parsed from
"between/from $A and/to $B ... per share" near the plan; SPACs excluded (blank-check trust redemptions, not
estimates); exchange-listed with Alpaca bars on the entry date. **Entry:** the official close of the first session
after the DEF 14A filing date, **only if entry < A** (the low estimate); others are listed, not traded.
**Payoff:** the total cash actually distributed per share after entry (special/liquidating dividends and
liquidating-trust payments from the issuer's 8-Ks and press releases, cross-checked with Alpaca corporate actions),
plus the last close if the stock still trades on 2026-09-30, plus any cash-merger price if the plan was replaced by a
sale. If the plan was voted down or abandoned and the stock kept trading: the close 250 sessions after entry.
Return = payoff / entry − 1; days = entry to the last payment. Stake 10% of equity (whole shares).
**Verdict: PAYS if median return > +3%, mean > 0 and hit >= 70% on the traded deals; otherwise DEAD.** No rule change.

## Amendment — Discovery loop (session llm-trader-c5), deal rule DL5: dated-term closed-end funds in their final year (no N; registered before any outcome)

Source reading (2026-10-02): EDGAR company names with "Term Trust / Target Term / <year> Term" (N-CSR, N-2, 497,
N-8F filers) and the funds' N-CSR text "will terminate on or about <date>". The charter sets a termination date on
which the fund liquidates and pays NAV in cash (target-term funds also aim to return the original NAV); a board/vote
can extend or convert the fund (the failure mode). A discount to NAV must close by that date.

**Deal set (fixed now):** every exchange-listed CEF with a dated term whose scheduled termination date (from its own
N-CSR/N-2 sentence; the name's year if no sentence) falls in 2017-01 .. 2025-12, with Alpaca bars 250 sessions before
it. **Entry:** the close 250 sessions before the scheduled termination date. **Exit:** the fund's last close on or
before the scheduled date (+30 calendar days grace) if it liquidated (bars end within 60 days after the date);
otherwise (extended / converted) the close on the scheduled date. Fund return = exit / entry − 1 + cash
distributions with ex-dates in (entry, exit] / entry (Alpaca corporate actions). Benchmark over the same window: the
total return of a matched ETF (Alpaca all-adjusted closes): munis MUB, high yield HYG, loans BKLN, EM debt EMB,
preferreds PFF, convertibles CWB, mortgages MBB, investment-grade corporates LQD. **Excess = fund − benchmark.**
Stake 10% of equity, whole shares. **Verdict: PAYS if median excess > +2%, mean excess > 0 and excess > 0 in >= 70%
of funds; otherwise DEAD.** No rule change afterwards.

## Amendment — Discovery loop (session llm-trader-c5), deal rule DL6: closing ETFs bought in their last week (no N; registered before any outcome)

Source reading (2026-10-02): ETF closures are announced in a 497 supplement that fixes the last trading day and the
liquidation (cash at NAV a few days later). Alpaca records the liquidation proceeds as a `cash_mergers` corporate
action for many of them (probe: BEDZ $36.54; IZRL, CTRU have none). Holders who sell in the last days may give a
discount to the cash that remaining holders receive.

**Deal set (fixed now):** every Alpaca `cash_mergers` record 2016-01 .. 2026-09 whose symbol's Alpaca asset name
contains "ETF", with raw bars. **Entry:** the close 5 sessions before the symbol's last bar (the announced last
trading day). **Payoff:** the cash_mergers rate (liquidation proceeds) + cash dividends with ex-dates in
(entry, last bar]. Return = payoff / entry − 1. Stake min(10% of equity, 5% of the 20-session median dollar volume
before entry), whole shares. Reported: deals/yr, hit, mean/median/worst, $/yr at $2.3k/$10k/$25k, and the same with
entry at the last close (info). **Verdict: PAYS if median > +0.5%, mean > 0 and hit >= 70%; otherwise DEAD.**
Records where the rate is < 20% or > 500% of the entry close are listed as data errors and dropped. No rule change.

## Amendment — Discovery loop (session llm-trader-c5), deal rule DL7: IPO allocations through retail IPO-access platforms, a bound (no N; registered before any outcome)

Mechanism (method F, queueing): underwriters place a slice of each IPO with retail platforms (Robinhood IPO Access,
SoFi, Public) at the offer price; Robinhood may restrict IPO access for accounts that sell within 30 days. Allocation
sizes are not public and fall in hot deals (Rock 1986 winner's curse), so only a bound is possible.

**Deal set (fixed now):** every 424B4 2019-01 .. 2026-06 with "initial public offering price of $X per share"
(X parsed), an exchange ticker in the filer name, not a SPAC/unit/blank check/closed-end fund/ADS-only, X >= $4, with
Alpaca bars starting within 5 sessions after the 424B4. **Payoff:** buy at X, sell at the close of the 30th session
(the platforms' flipping window); info line: sell at the first close. **Fill models:** (opt) every deal filled in
full; (pess) filled only when the first-session open <= 1.10 X (cold deals, where retail gets shares), zero otherwise.
Stake $500 per deal (a typical retail IPO-access request; capped by the platforms). Reported: deals/yr, mean/median/
hit of the 30-session return under each model, $/yr. **Verdict on the pessimistic model: PAYS if its median > 0 and
mean > 0 with hit >= 55%; otherwise DEAD.** No rule change afterwards.

## Amendment — Index beat (session llm-trader-ee), deal rule DL-IB1: the reverse-split round-up in more accounts (no N; registered before any outcome)

`date`: Fri Oct 2 2026, before any number below is computed. Prompt: research/drafts/prompt_index_beat.md, idea A1.
Rule: B1 (Round 32) unchanged — for every reverse split whose issuer's filings say fractional post-split shares "will be
rounded up" (never "participant level"), hold ONE pre-split share at the last pre-split close and sell the post-split
share once it shows — run in each of K brokerage accounts the user owns (K-2 extra Schwab individual accounts beyond
the taxable and the Roth; the Trader API sees every account under one login). Payoff per account and deal = (1 share's
post-split value at the first post-split close) - (pre-split price) if rounded up, about -$0.02 if cash in lieu.
Who pays: the issuer's other holders (a few dollars of dilution per round-up), because the issuer wants to keep small
holders and avoid a cash-in-lieu process. Why a small account: the payoff is a fixed ~$4 per account per deal, so it is
~1%/yr per account at $25k but ~14%/yr at $2.3k; capacity is 1 share per account.
Measured (B1's deal file, roundup_deals.csv, no new outcome window): per account and year, deals 2023-26, $ if rounded
and if cash; the share of round-up filings that switched to "participant level" by year (the issuer-adaptation trend);
$/yr for K = 2 (today), 3, 5, at $2.3k / $10k / $25k as % of the taxable balance.
PAYS if: mean $/deal > $0 if rounded (B1: yes) AND >= $150/yr per extra account in 2024-26 AND the participant-level
share is not rising so fast that 2026's qualifying deals are < half of 2024's. Conditional on Schwab paying round-ups to
a 1-share holder, which history cannot show: the first live deal (VIVK, ex 2026-10-05, check ~10-07) decides it, and
this rule is NOT a FOUND until 2 live deals have been rounded in an account.

## Amendment — Jump hunt, Study J1: first profitable quarter after >= 6 losing quarters (pre-register; track RIDE, cell hold60, 1 look, program N 760 -> 761)

Session llm-trader-51, `prompt_jump_hunt.md`, idea D6 (`research/drafts/jump_ideas.md`). Registered 2026-10-02 before
any 2024+ outcome of this rule was computed.

- **Event** (`research/sim/jump_d6.py`, file `data/research/program/events_jump_d6.parquet`, sha256 prefix
  718a23ae3cfa6c97, 726 events 2016-2026): a company's first ORIGINALLY reported positive quarterly NetIncomeLoss (XBRL
  companyfacts, ~90-day duration, 10-Q/10-K, earliest `filed` per quarter end) after >= 6 consecutive negative
  reported quarters; fd = that filing's date; 20-day ADV$ < $20M (raw bars); ticker via EDGAR tickers or exact
  name match to Alpaca assets incl. inactive.
- **Trade** (`jump_runner`, fixed): buy the open of the first session after fd, hold 60 sessions (rule `hold`), ADV-tiered
  small-cap costs. Track RIDE.
- **Select-half look (2016-2023, the only look):** `hold60 n 299 (37/yr) jump 25.8% vs base 20.5% (x1.3) mean net
  +7.3% ex-top3 +4.5% median -0.6% vs stock's usual +7.2% hit 49% worst -84% best +409% P(mean<=0) 0.00 | ride MEETS`.
  No other cell met (tp2060 mean +2.9%, hold20 +2.3%).
- **Judge (once):** `PYTHONPATH=. .venv/bin/python -m research.sim.jump_runner judge data/research/program/events_jump_d6.parquet 60 hold --track ride`
  on events 2024-01-01..2025-06-30. PASS = the runner's RIDE judge gate (>= 15 trades, mean net > 0, beats the stock's
  usual return, ex-top3 > 0, bootstrap P(mean <= 0) < 0.10). If PASS: `confirm` once, same arguments, window
  2025-07-01..2026-09 (CONFIRMED = >= 10 trades, mean > 0, mean without the best > 0, beats the stock's usual).
- **Who is on the other side, and why it might persist:** holders and screens that exclude loss-makers (positive-EPS
  screens, P/E sorts, index rules needing positive GAAP earnings, quant value/quality factors) only start to own a
  small company after its first profit; the milestone is in a 10-Q table, not a headline, so the new demand arrives
  over weeks, not at the open.
- **Known weaknesses, stated before judging:** (1) survivorship in the select half: only 63-70% of 2016-18 events
  map to a ticker (vs ~90% in 2024-25), likely missing delisted firms, so the select mean may be flattered; (2) regime:
  select-year means +21/+14/-1/-8/+42/-5/-5/+14% (2016..2023), i.e. 60-day small-cap timing; median by year positive
  in 4 of 8; (3) TEXTBOOK-adjacent (post-earnings drift family). The judge half is the test of all three. k = 1 judged
  idea in this hunt so far.

## Amendment — Index beat (session llm-trader-ee), deal rule DL-IB2: reverse splits with a round-lot top-up (no N; registered before any outcome)

`date`: Fri Oct 2 2026, before any event is counted or priced. Source of the idea: round-4 contractual-payoff sweep
(index_beat_log.md), example AREB 1-for-20 (Feb 2026 8-K: "no current owner of 100 or more shares will be reduced to
less than 100"). Rule: for a reverse split whose issuer's filings (8-K, DEF 14A, PRE/DEF 14C, 424B) in the 90 days before
the ex-date say holders of 100+ (a round lot) will not fall below 100 shares, hold exactly 100 pre-split shares at the
last pre-split close (S) in each account and sell the post-split position at the first close on/after ex + 2 sessions
(E2). Payoff per account = 100 x P_E2 - 100 x P_S if topped up, = (100/N) x P_E2 - 100 x P_S if not (the split alone).
Filters: price at S <= $3 (capital <= $300), no "participant level" / "Cede" restriction on the top-up sentence.
Measured: events per year 2016-26, payoff if topped up and if not, worst, capital; break-even probability of the top-up
being paid. PAYS if: >= 3 events/yr in 2024-26, mean if topped up >= +$100/account/event, and break-even probability
<= 25%. Like DL-IB1 it is conditional on the broker allocating the top-up to a beneficial account: not FOUND before a
live event has been topped up in an account.

## Amendment — Jump hunt, Study J2: insider buy after a 30% fall (pre-register; track JUMP, cell tp205, 1 look, program N 761 -> 762)

Session llm-trader-51, `prompt_jump_hunt.md`, idea R2-5 (`jump_ideas.md`, round 2). Registered 2026-10-02 before any
2024+ outcome of this rule was computed.

- **Event** (`research/sim/jump_insider.py r2_5`, file `data/research/program/events_jump_r2_5.parquet`, sha256 prefix
  33ba9bed7bfdcdf7, 4,370 events 2016-2026): an officer/director open-market purchase (Form 4 code P, >= $1k; SEC
  insider data sets 2014-2026; first per stock in 30 days) filed on fd while the stock's raw close is >= 30% below its
  close 60 sessions earlier.
- **Trade** (`jump_runner`, fixed): buy the open of the first session after fd; sell at a +20% limit within 5 sessions,
  else at the 5th close (rule `tp20`, hold 5). Track JUMP. Chosen by the runner's rule "shortest hold if several":
  tp205 (JUMP) and hold20 / tp2020 / hold60 / tp2060 (RIDE) all met.
- **Select-half look (2016-2023, the only look):** `tp205 n 2379 (297/yr) jump 15.1% vs base 5.8% (x2.6) mean net +0.5%
  ex-top3 +0.5% median +0.3% vs stock's usual +1.2% hit 51% worst -74% best +38% P(mean<=0) 0.02 | jump MEETS`.
- **Judge (once):** `PYTHONPATH=. .venv/bin/python -m research.sim.jump_runner judge data/research/program/events_jump_r2_5.parquet 5 tp20 --track jump`
  (events 2024-01-01..2025-06-30; PASS = >= 15 trades, jump >= 1.5x base, mean > 0, ex-top3 > 0, P < 0.10). If PASS:
  `confirm` once with the same arguments (2025-07..2026-09; CONFIRMED = >= 10 trades, mean > 0, mean without the best >
  0, jump >= 1.2x base).
- **Other side / why it might persist:** holders who sell a small cap after a 30% fall (tax, risk limits, retail
  capitulation) vs. the insiders who buy it; small caps after a crash bounce more often than they normally jump.
- **Known weakness, stated before judging:** a select-only control — the same stocks on dates with a >= 30% 60-session
  fall and NO officer/director buy within -30..+5 days (4,753 trades) — did as well: tp205 mean +0.93% (insider
  +0.61% on the same code path), hold20 +4.8% (insider +3.7%); jump rate 12.1% vs 15.1%. So the insider adds little
  or nothing over the fall itself: this is mostly a fallen-small-cap reversal (PRICE PROXY), strongest at market
  bottoms (2020 hold20 +10%; 2018 tp205 -2.1%). A judge PASS would be a reversal effect, not an insider effect.
  k = 2 judged ideas in this hunt.

## Amendment — Jump hunt, Studies J3 and J4: an 8-K saying the board engaged a financial advisor / signed confidentiality agreements to evaluate "strategic alternatives" (pre-register; J3 track RIDE cell hold20, J4 track JUMP cell hold20, 1 look each, program N 762 -> 764)

Session llm-trader-51, `prompt_jump_hunt.md`, round-4 ideas R4-5 and R4-6 (`jump_ideas.md`). Registered 2026-10-02
before any 2024+ outcome of either rule was computed. Builder `research/sim/jump_edgar.py` (`_r4`): EDGAR full-text
search, forms 8-K, half-years 2015-2026; event = a company's first matching 8-K in 365 days, fd = the 8-K file date;
20-day ADV$ < $20M; ticker via jump_common.resolve. Trade: buy the next open, `jump_runner` costs.

- **J3 (R4-5)**: query `"strategic alternatives" "financial advisor"` -> `events_jump_r4_5.parquet` (sha256 prefix
  cb47310a3a35bec9, 519 events). Select look: `hold20 n 155 (19/yr) jump 14.2% vs base 8.8% (x1.6) mean net +3.5%
  ex-top3 +1.1% median -0.5% vs stock's usual +4.4% hit 47% worst -55% best +149% P(mean<=0) 0.04 | ride MEETS`
  (also trail20 +3.9%, hold60 +7.3%, trail60 +7.4%; shortest hold = 20, hold20 chosen over trail20 as the plain rule).
  Judge: `jump_runner judge data/research/program/events_jump_r4_5.parquet 20 hold --track ride`.
- **J4 (R4-6)**: query `"confidentiality agreements" "strategic alternatives"` -> `events_jump_r4_6.parquet` (sha256
  prefix 38492bb6e5c769cc, 92 events). Select look: `hold20 n 24 (3/yr) jump 20.8% vs base 8.0% (x2.6) mean net
  +6.0% ex-top3 +1.7% median +3.5% vs stock's usual +6.9% hit 62% worst -30% best +41% P(mean<=0) 0.04 | jump MEETS
  | ride MEETS`; registered on JUMP (the idea's track). Judge: `... judge data/research/program/events_jump_r4_6.parquet 20 hold --track jump`.
- Judge window 2024-01-01..2025-06-30, once each; on PASS, `confirm` once with the same arguments (2025-07..2026-09).
- **Standing-rule control (select only, before registering):** same-day control (`jump_control.py`: up to 400 of the
  idea's own stocks bought on the same entry mornings without an event): J3 event minus control **+4.4%** (median
  +0.0%, 51% above, bootstrap P 0.004); J4 **+4.9%** (median +1.8%, 59% above, P 0.057). Year means J3:
  +10/+4/-5/-4/+6/+7/+6/+2% (2016..2023).
- **Who is on the other side:** holders who read "strategic alternatives" as distress (many such companies are
  struggling) and don't read the 8-K line that a bank was hired or that bidders signed NDAs; a sale process ends in a
  premium for some of them within weeks. The edge is a right tail (median difference ~0), so ex-top-3 is the risk.
- **Known weaknesses:** J4 is small (24 select trades; the judge half may have < 15 trades -> DEAD by count); J3 and J4
  overlap (some events in both). k = 4 judged ideas in this hunt after these two.

## Amendment — Jump hunt, Study J5: buyback authorization >= 15% of market cap, bought only if the next open gaps < 3% (pre-register; track JUMP, cell tp205, 1 look, program N 764 -> 765)

Session llm-trader-51, `prompt_jump_hunt.md`, round-2 idea R2-25 (`jump_ideas.md`). Registered 2026-10-02 before any
2024+ outcome of this rule was computed.

- **Event** (`research/sim/jump_news.py r2_25`): an Alpaca/Benzinga story (<= 2 tickers) whose headline contains
  "buyback" or "repurchase" and a $ amount (`AMT` regex: $N million/billion) >= 15% of market cap (XBRL dei cover-page
  shares, latest within 400 days before fd, x the raw close on/before fd: `jump_news._mcap`); first per ticker in 90
  days; fd = fd_of(story time); kept only if the trade's opening print is < 3% above the prior raw close (`_gap_ok`:
  in practice a limit-on-open order at prior close x 1.03).
- **Event file:** select-half events (fd <= 2023-12-31) sha256 prefix **ee4fb4de291419c5** over the CSV of (sym, fd)
  sorted by (fd, sym), 214 events; built from the news archive through 2024-01. The judge/confirm file is the SAME
  builder re-run on the complete archive (2016-01..2026-09) when the download finishes; the judge runs only if that
  file's select-half subset hashes to ee4fb4de291419c5 (same rule, same select events).
- **Trade** (`jump_runner`, fixed): buy the open of the first session after fd; sell at +20% limit within 5 sessions,
  else at the 5th close (`tp20`, hold 5). Track JUMP (shortest hold that met; RIDE also met at tp2060).
- **Select-half look (2016-2023, the only look):** `tp205 n 162 (20/yr) jump 6.2% vs base 2.4% (x2.6) mean net +2.1%
  ex-top3 +1.8% median +1.7% vs stock's usual +2.3% hit 63% worst -25% best +26% P(mean<=0) 0.00 | jump MEETS`.
- **Standing-rule control (select only):** same-day control (`jump_control.py`, 21,402 trades): event minus control
  **+1.9%** a trade (median +1.4%, 59% above, bootstrap P 0.001). Year means +4.9/+1.0/+2.2/+1.5/+0.5/+3.5/+2.1/+0.6%
  (2016..2023), medians positive in 7 of 8.
- **Judge (once):** `PYTHONPATH=. .venv/bin/python -m research.sim.jump_runner judge data/research/program/events_jump_r2_25.parquet 5 tp20 --track jump`
  (2024-01-01..2025-06-30; PASS = >= 15 trades, jump >= 1.5x base, mean > 0, ex-top3 > 0, P < 0.10). If PASS:
  `confirm` once with the same arguments (2025-07..2026-09).
- **Other side / why it might persist:** opening-auction sellers who read "buyback" as boilerplate (most authorizations
  are small or never executed) and don't scale the dollar amount by the company's size; when the authorization is
  15%+ of a small company, the company itself is a large, price-insensitive, informed buyer over the next weeks.
  TEXTBOOK-adjacent (buyback-announcement drift, Ikenberry et al.), dodged by the relative size and the un-gapped
  entry; a 3% gap filter keeps us out of names the market already repriced.
- **Known weaknesses:** 20 events a year; the $ amount is parsed from headlines (no LLM), so missed/garbled amounts
  shrink the sample; some events may be issuer tender offers (price converges to the tender range). k = 5.

## Amendment — Jump hunt, Study J6: forward stock split announced, bought at the next open (pre-register; track JUMP, cell trail20, 1 look, program N 765 -> 766)

Session llm-trader-51, `prompt_jump_hunt.md`, round-1 idea S5 (`jump_ideas.md`; death-dodge of Lab-BM, which tested
the window AFTER the ex-date). Registered 2026-10-02 before any 2024+ outcome of this rule was computed.

- **Event** (`research/sim/jump_news.py s5`): an Alpaca/Benzinga story whose headline says "Stock Split" / "Share
  Split", not "Reverse", with an "N-for-M" ratio where N > M; first per ticker in 180 days; fd = fd_of(story time). No
  ADV cap (the runner's $1 / $250k floors apply).
- **Event file:** select-half events (fd <= 2023-12-31) sha256 prefix and count **8490e20097b8a31f 92** over the CSV of (sym, fd)
  sorted by (fd, sym); built from the archive through 2024-01. The judge file is the same builder on the complete
  archive; the judge runs only if its select-half subset hashes the same.
- **Trade** (`jump_runner`, fixed): buy the next open; exit at the close once it is 15% below the best close since
  entry, else at the 20th close (`trail`, hold 20). Track JUMP (the only cell that met).
- **Select-half look (the only look):** `trail20 n 78 (10/yr) jump 9.0% vs base 4.1% (x2.2) mean net +2.2% ex-top3 +0.8%
  median +2.6% vs stock's usual +1.0% hit 62% worst -22% best +48% P(mean<=0) 0.06 | jump MEETS`.
- **Standing-rule control (select only):** same-day control 4,650 trades: event minus control **+2.0%** (median +1.5%,
  58% above, bootstrap P 0.054). Year means -4.7/+6.4/+0.7/-3.0/+2.6/+5.6/-0.1/-2.4% (2016..2023).
- **Judge (once):** `PYTHONPATH=. .venv/bin/python -m research.sim.jump_runner judge data/research/program/events_jump_s5.parquet 20 trail --track jump`;
  on PASS, `confirm` once with the same arguments.
- **Other side:** holders who sell into the announcement pop while retail and option buyers keep buying "cheaper
  shares" into the ex-date (2020-24 split wave: AAPL, TSLA, NVDA, AVGO, CMG, WMT). TEXTBOOK-adjacent (Ikenberry,
  Rankine & Stice 1996 post-announcement drift); REGIME risk: year means swing -5..+6%. k = 6.

## Amendment — Jump hunt, Studies J7 and J8: two upgrades in 10 days on a small cap (JUMP tp205) / initiation with a target >= 2x the price on a micro cap (RIDE hold60) (pre-register; 1 look each, program N 766 -> 768)

Session llm-trader-51, `prompt_jump_hunt.md`, ideas R2-19 and R3-15 (`jump_ideas.md`). Registered 2026-10-02 before
any 2024+ outcome of either rule was computed. Builders in `research/sim/jump_news.py` (Alpaca/Benzinga headlines;
fd = fd_of(story time)); event files built from the archive through 2024-01; select-half (fd <= 2023-12-31) subsets
pinned by sha256 prefix of the (sym, fd) CSV sorted by (fd, sym); each judge runs on the same builder re-run on the
complete archive, only if its select-half subset hashes the same. Trades by `jump_runner` (fixed costs, windows, gates).

- **J7 (R2-19, `r2_19`)**: single-ticker headline matching "Upgrade(s)" whose previous upgrade headline on the same
  ticker was 0-10 days earlier; first per ticker in 60 days; 20-day ADV$ < $20M. Select pin **0715cbe8f4bb7105** (310
  events). Look: `tp205 n 277 (35/yr) jump 8.3% vs base 3.1% (x2.6) mean net +0.7% ex-top3 +0.5% median -0.1% vs
  stock's usual +1.1% hit 49% worst -31% best +20% P(mean<=0) 0.09 | jump MEETS` (shortest hold; RIDE also met at
  hold60 +5.9% and trail60). Control: event minus same-day control **+1.0%** (median +0.4%, 52% above, P 0.021); year
  means +1.9/+0.2/+1.7/+0.1/-0.4/+1.0/+0.1/-0.5%. Judge: `jump_runner judge data/research/program/events_jump_r2_19.parquet 5 tp20 --track jump`.
- **J8 (R3-15, `r3_15`)**: "Initiates Coverage" headline (<= 2 tickers) with a price target >= 2x the raw close on/before
  fd; first per ticker in 365 days; ADV$ < $5M. Select pin **95c3dafbbf6fdeb6** (230 events). Look: `hold60 n 140
  (18/yr) jump 27.9% vs base 21.1% (x1.3) mean net +6.1% ex-top3 +2.7% median +1.0% vs stock's usual +6.0% hit 52%
  worst -85% best +170% P(mean<=0) 0.05 | ride MEETS` (only hold60 / tp2060 met; hold60 is the shorter... equal
  holds, hold60 = the plain rule). Control: **+5.0%** (median -1.4%, 46% above, P 0.079): a right tail. Events fall
  to 1-2 a year after 2020 (the headline format with a target appears less), so the judge half may have < 15 trades.
  Judge: `jump_runner judge data/research/program/events_jump_r3_15.parquet 60 hold --track ride`.
- On a PASS: `confirm` once with the same arguments. **Other side:** analysts (semi-informed) whose clients act over
  weeks, vs. holders who ignore notes on tiny names. TEXTBOOK-adjacent (recommendation drift); REGIME risk.
  k = 8 after these (J1-J8).

## Amendment — Goal hunt, Study G2: EV2-big as a SPY-core intraday overlay, judged on an untouched 2016-20 holdout (pre-register; program N 768 -> 772)

Session llm-trader-ec, `prompt_strategy_goal.md`, idea G2 (`goal_ideas.md`, track T1). Registered 2026-10-02 before any
2014-2021 Form 345 file was downloaded and before any outcome on 2016-21 was computed. **Why a holdout replaces the judge
half:** the >= $500k size cut was found on 2022-26 data (`study_ev2_first_insider_buy.md` diagnostics), so 2024-26 can't
judge it. Insider data here starts 2020-01 (EV2 events 2022+); 2016-20 has never been looked at for any insider rule.

- **Data:** SEC insider-transactions data sets 2014q1..2021q4 (`/files/structureddata/data/insider-transactions-data-sets/`),
  parsed exactly as `outside_box.insider_buys()` (Form 4 / 4-A, code P, acquired; $ = shares x price; officer/director by
  RPTOWNER_RELATIONSHIP). Bars: Alpaca SIP daily raw (`event_fetch.raw_bars`), session-labelled.
- **Event (EV2-big):** a filing date fd with officer/director code-P purchases at issuer `sym`, summed over that (sym, fd)
  **>= $500,000**, where no code-P purchase filing by anyone at that issuer has a filing date in the 730 days before fd.
  Trade session d = first regular session after fd. Filters known before the open: prior raw close >= $5; 20-session
  mean raw close x volume >= $20M; **ticker-reuse guard:** the dollar-weighted Form 4 price is within 0.67-1.5x the raw
  close of the session before d (else dropped; count reported). |open->close| >= 50% dropped (as ID3).
- **Trade:** buy the 09:30 opening cross (raw open), sell the 16:00 closing cross (raw close) of d. Costs per side:
  2.5bp (primary) and `tier_hi` (reported). Whole shares at the stated equity.
- **Book (taxable, the account that has intraday margin):** 100% SPY held (dividend-adjusted), plus the overlay:
  - **G2a (primary):** each event gets 0.5x equity; on a day with k events each gets min(0.5, 1.0/k) (overlay gross <= 1.0x,
    total intraday gross <= 2.0x Reg T).
  - **G2b:** 1.0x per event, overlay gross <= 1.0x... (k events: min(1.0, 1.0/k)): the concentrated version.
  - Margin interest: none (intraday only). Tax: `taxable_frontier.after_tax` short-term on the overlay, SPY unrealised.
  - $2.3k and $10k start, +$1k/month (the frontier default) and a no-deposit run; whole shares on the overlay.
- **Reported, not judged (counted in N):** EV2 all sizes (no $ floor) and ID3 >= $500k (no silence filter) on the same
  holdout, same G2a sizing, to show whether the size cut or the silence filter carries it.
- **Pass (all on 2016-01-01..2020-12-31):** (1) per-trade net mean > 0 at 2.5bp and at tier_hi; (2) overlay daily P&L NW t
  >= 2; (3) lottery test: overlay total > 0 without its best 5% of event days AND without its best 5 trades; (4) random-pick
  null: 1,000 draws of the same count of (session, sym) from names with ADV >= $20M and price >= $5 on each event's
  session, holdout total at >= the 95th percentile; (5) each of the 5 years' overlay sum > 0 in >= 4 of 5; (6) **Goal
  FOUND bar:** G2a CAGR after tax >= SPY + 10pp/yr at $2.3k AND $10k (whole shares), max DD <= 35%, worst month and worst
  single event named; >= 100 trades in the holdout. 2021 (also untouched for EV2-big) is reported as a sixth year; 2022-26
  is printed as in-sample context only. DSR reported at N 772.
- **Expected count (written before download):** unknown; EV2 had ~159 trades/yr in 2022-23 at ADV >= $20M before any $
  floor, and the >= $500k buckets are ~15-25% of those, so ~25-40/yr -> 125-200 in 2016-20. If < 100, the FOUND bar (6) fails
  by count and the verdict is at most NEAR.
- **Causality:** every input dated <= fd (filing date) or <= the session before d (ADV, prior close, ticker guard).
  `tests/test_causality.py` style check: truncating bars after d-1 leaves the event list unchanged.
- Runner: `research/sim/goal_g2.py` (to be written after this commit). k = 1 when judged.

## Amendment — Goal hunt, G2-F: the one NEAR follow-up for Study G2 (forward only; no new N)

G2 judged NEAR (`study_goal_g2.md`): every registered 2016-20 holdout bar passed for G2a at 2.5bp (+68.7bp/trade, NW t 3.48,
lottery test passed, null 100th pct, +11.3pp/yr after tax vs SPY at $2.3k and $10k), but 2021 (untouched) was −10bp/trade
and the size cut's 2024-26 judge half is contaminated. Follow-up, registered before any forward outcome: when the live
ID3 shadow's "EV2 x buy >= $500k" gate (testing.py, `make forward-status`) reaches 60 scored trades, PASS iff mean net
per trade at the measured live cost >= +30bp AND NW t >= 1.5 AND the G2a book on those trades (SPY core, 0.5x/event,
cap 1.0x) beats SPY by >= +10pp/yr after tax at $2.3k and $10k; otherwise DEAD (EV2-big folds back into ID3). No interim
decisions. Same rule as G2; no new variant, so N stays 772.

## Amendment — Goal hunt, Study G8: convertible pricing-day hedge shorting, buy after the hedge is set (pre-register; program N 772 -> 774)

Session llm-trader-ec, `prompt_strategy_goal.md`, idea G8 (`goal_ideas.md`, track T3). Registered 2026-10-02 before any
event list was built and before any price around a convertible pricing was looked at.

- **Events:** 8-K (incl. exhibits) whose text says the issuer "announces pricing" / "prices" / "pricing of" an offering of
  "convertible senior notes" or "convertible notes" (EDGAR full-text search, 2016-01..2026-09; queries listed in
  `research/sim/goal_g8.py`). One event per issuer per 30 days (first filing). Parsed from the press release only:
  ticker, principal ($ million, the base amount, not the option), whether it mentions a **capped call** or a **concurrent
  repurchase / delta / share offering** (regex, no LLM). Filing date = fd.
- **Filters known at entry:** prior raw close >= $5; size / (20-session mean raw close x volume, to the session before fd)
  **>= 3** (the arbs' short is large vs normal flow).
- **Trade:** buy the opening cross of the first session after fd (the press release lands after the close of the pricing
  day or pre-market; the short-sale pressure is on the launch/pricing session), sell the closing cross of the 5th session
  (hold 5). Return measured **minus SPY over the same window** (hedged excess; the book shorts nothing, the excess is what it
  adds over the SPY it displaces). Costs `tier` and `tier_hi` per side (2 sides).
  - **G8a:** all events passing the filters.
  - **G8b:** only those with **no** capped call and **no** concurrent repurchase/share offering (pure hedge shorting).
- **Halves:** select 2021-23 first (one look). Proceed to the judge (2024-26) only if a variant has, on select: n >= 20,
  mean net excess >= +1.0% per trade at tier, t >= 2 (trade-level). Holdout 2016-20 is run with the judge and must not be
  negative. Lottery test (ex best 5 trades, ex best 5% of event days) on the judge half. Random-event null on the judge
  half: same count of (fd, sym) from names passing the same price/ADV filters, >= 95th pct.
- **Goal bar if it gets that far:** an overlay at 0.25x equity per event funded from the SPY core, after tax, >= SPY +
  10pp at $2.3k and $10k; expected ~10-30 events/yr, so this is likely an add-on (>= +5pp) at best.
- **Why it might not work (written now):** modern deals often come with capped calls (dealers BUY stock at pricing) or
  concurrent repurchases, which offset the arbs' short; the recovery may already be in the pricing-day close. TEXTBOOK risk
  (Choi et al. 2010; de Jong et al. 2011 document the hedging pressure). k = 4 when judged.

## Amendment — Goal hunt, Study G12: insider buys >= $500k filed during market hours, bought the same session (pre-register; program N 774 -> 775)

Session llm-trader-ec, `prompt_strategy_goal.md`, idea G12 (`goal_ideas.md`, track T1). Registered 2026-10-02. Before
this, only filing timestamps (a 300-filing sample, 2016-21: 7% pre-market, 13% accepted 09:30-15:30, 1% 15:30-16:00,
79% after 16:00) were looked at. The same events' NEXT-session open->close was seen (G2 report row, EV2 diagnostics); this
window, from acceptance to the same session's close, has never been computed on any period.

- **Events:** Form 4 / 4-A accessions with officer/director code-P purchases >= $500k (summed per accession), parsed as in
  `goal_g2.buys()` from Form 345 2016q1..latest. Acceptance datetime from the EDGAR header (`event_fetch.hdr`, ET). Keep
  accessions accepted on a regular session day between 09:30 and 15:20 ET. One event per (sym, day): the earliest
  acceptance. Filters at entry: prior raw close >= $5, 20d ADV$ >= $20M (to the prior session).
- **Trade:** buy at the open of the first 1-minute SIP bar starting >= acceptance + 5 minutes (raw); sell at the session's
  closing cross (raw daily close). Costs: `tier_hi` per side + **5bp extra on entry** (an intraday marketable order, not a
  cross). One variant only.
- **Halves:** select 2021-23 (one look) -> proceed only if n >= 40, mean net >= +30bp, trade-level t >= 2. Then judge
  2024-26 (mean > 0, daily NW t >= 2, lottery test ex best 5% days and ex best 5 trades > 0, random-entry null: same
  minute-of-day entries in random ADV >= $20M names that day, >= 95th pct) and holdout 2016-20 (mean >= 0).
- **Goal bar (add-on):** as a 0.5x-per-event intraday overlay on a SPY core, after tax, >= +5pp/yr at $2.3k and $10k on
  the judge half. Expected ~40-50 events a year.
- Runner `research/sim/goal_g12.py`. k = 11 when judged.

## Deal rule DL-G27 (Goal hunt, no N): mutual savings bank conversions bought at $10 in the subscription offering

Session llm-trader-ec, idea G27 (`goal_ideas.md`). Registered 2026-10-02 before any post-IPO price of these deals was looked at.
- **Events:** S-1 filings 2016-01..2026-09 containing "plan of conversion", "subscription offering" and "eligible account
  holders" (EDGAR FTS), one per issuer. Standard conversions and second-step conversions; ticker from the FTS display name
  or the issuer's later filings; offering price $10.00 (the norm; any other stated price is used as-is).
- **Payoff (as an eligible depositor, order filled):** buy at the offering price; sell (a) at the close of the first
  trading day, (b) at the 20th session's close. Raw Alpaca SIP bars. No commission (subscription), sell-side cost tier.
- **PAYS if** on (a): median > 0, hit >= 60%, worst case survivable (no single deal below −30%); and >= 5 deals/yr. Report
  both exits, by year; worst deal named. Dollars: $2,000 per deal per account holder (assume full fill; note that
  oversubscribed deals prorate above minimums).
- **Logistics (written now; this decides whether it can be used):** eligibility requires a deposit account at the mutual
  BEFORE the eligibility record date (typically 1-2 years before the offering), and many mutuals restrict account opening
  or the community offering to state / county residents. Even if it PAYS, it can be used only for mutuals that open
  accounts to non-residents online; the manual setup is > 5 minutes per bank (one-time).

## Amendment — Goal hunt, Study G13: issuers that actually repurchased >= 2% of their shares last quarter (pre-register; program N 775 -> 776)

Session llm-trader-ec, idea G13 (`goal_ideas.md`, track T3). Registered 2026-10-02 before any repurchase data was joined to
prices. Seen before registering: only the SEC XBRL frames API's coverage count (140-210 filers per quarter for the 3-month
frames), no returns.

- **Data:** SEC XBRL companyfacts (data.sec.gov/api/xbrl/companyfacts) for every CIK in company_tickers.json. Shares
  repurchased in a fiscal quarter = `us-gaap:StockRepurchasedDuringPeriodShares`, else `TreasuryStockSharesAcquired`,
  using facts whose duration is 80-100 days (a reported quarter). Denominator = `dei:EntityCommonStockSharesOutstanding`,
  the latest value filed on or before that filing. `filed` = the fact's filing date (point in time).
- **Event:** intensity = repurchased / outstanding **>= 2.0%** in one quarter; first filing of that fact (10-Q or 10-K).
- **Trade:** buy the opening cross of the first session after `filed`, hold 63 sessions, sell at that close. Return minus
  SPY (total return, same window). Filters at entry: prior raw close >= $5, 20d ADV$ >= $5M. Costs tier per side.
- **Portfolio for the test:** calendar-time, equal weight across open positions, monthly excess returns vs SPY.
- **Halves:** select = events filed 2021-23 (one look). Proceed only if monthly excess mean >= +0.5% and NW t >= 2. Then
  judge (2024-26: mean > 0, NW t >= 2, lottery test ex best 5% of months and ex best 5 trades, random-filer null: same
  count of 10-Q filers per month, >= 95th pct) and holdout (2016-20: mean >= 0).
- **Goal bar:** as a taxable sleeve replacing SPY, after tax, >= SPY + 10pp at $2.3k and $10k (whole shares; ~1 position
  per $500 at $2.3k), or as an add-on >= +5pp.
- **Why it might fail (written now):** TEXTBOOK. Actual-repurchase predictability is published (Stephens & Weisbach 1998;
  Ben-Rephael, Oded & Wohl 2014) and may have decayed. One variant. k = 25 when judged.

## Amendment — Pick quality (session llm-trader-ee), Study PQ1: leveraged / inverse ETFs in the night pool (pre-register; 2 variants, program N 776 -> 778)

`date`: Fri Oct 2 2026, before any PQ1 book or 2024+ outcome is computed. Prompt: research/drafts/prompt_pick_quality.md.
Why: single-stock and index leveraged/inverse ETFs went from 3% of night picks (2021) to 24% (2026) (counts only); their
-8% day is often a mechanical 2x of the underlying's move, not an overreaction, and they duplicate the underlying's pick.
Only 2021-23 outcomes were seen (LETF +20.6bp vs stocks +17.5bp, n 208 / 3,857). Classifier: research/sim/pq1.py `classify`
(Alpaca asset name has a leverage word AND a fund/issuer word; underlying = the ticker after Long/Short/Inverse/Bull/Bear).
Variants: PQ1a EXCLUDE every LETF pick (it also leaves the raw signal count); PQ1b DEDUPE: drop an LETF pick when its
underlying, or an earlier-listed LETF on the same underlying, is also a pick that night. Sizing otherwise as live
(frac = min(1/n, 0.10) x min(1, 30/n_raw)). Book: V7 1.0x raw pool, Sim.replay, fixed $10k (and $2.3k whole shares),
tier and tier_hi. Halves: select 2021-02..2023-12, judge 2024-01..2026-09. No 2016-20 holdout (the raw pool starts 2020-11).
PASS (prompt_pick_quality.md): judge-half increment > 0 at tier AND tier_hi, NW t >= 2 (daily increment, judge half),
placebo >= 95th pct (50 draws dropping the same number of random picks per night, tier), select half not worse than -0.5pp.
Because LETFs were rare in 2021-23 the select half can only show "not worse"; the judge half carries the test. DSR at N 778
reported.

## Amendment — Goal hunt, Study G31: follow-on offerings bought at the stabilization floor (pre-register; program N 778 -> 779)

Session llm-trader-ec, idea G31 (`goal_ideas.md`, track T3). Registered 2026-10-02 before any event list or price was built.
Seen before registering: FTS hit counts only (~190-270 a year).

- **Events:** 8-K filings (incl. exhibits) matching "announces pricing" + "public offering" + "common stock" + "per share",
  2016-01..2026-09. Offer price parsed from the press release (first "$X.XX per share" after "priced"/"pricing"). Drop IPOs
  (the ticker has < 20 prior sessions of bars) and anything not common stock. One event per issuer per 30 days.
- **Entry session:** if the EDGAR acceptance time is before 09:30 ET, the filing date's session; else the next session.
- **Condition and trade:** if the entry session's raw open is within ±1% of the offer price, buy at the open. Exit: the close
  of the first session (entry day included) whose close is < 0.97 x offer price, else the 3rd session's close. Costs: tier
  per side. Primary = conditional trades; reported (counted in N 779, not a variant) = all events bought at the open
  regardless of the condition.
- **Halves:** select 2021-23 (one look) -> proceed only if n >= 40, mean net >= +0.75%, t >= 2. Then judge 2024-26 (mean > 0,
  daily NW t >= 2, lottery test ex best 5 trades and ex best 5% of days, random-date null on the same issuers) and holdout
  2016-20 (mean >= 0).
- **Goal bar:** an overlay at 0.25x per event (taxable, funded from the SPY core), after tax, >= +5pp/yr at $2.3k and $10k.
- Runner `research/sim/goal_g31.py`. k = 28 when judged.

## Amendment — Goal hunt, Study G36: RSU vest-date selling marked by officer code-F clusters (pre-register; program N 779 -> 780)

Session llm-trader-ec, idea G36 (`goal_ideas.md`, track T3). Registered 2026-10-02 before any code-F event was built.
- **Events:** Form 345 data sets 2014q1..latest (`data/research/jump/insider/` + `night/insider/`): Form 4 transactions with
  TRANS_CODE F (tax withholding on vesting). A **cluster** = >= 5 distinct reporting owners with code F at one issuer whose
  filing dates span <= 2 calendar days. Cluster date = the last filing date. One cluster per issuer per 20 sessions.
- **Trade:** buy the opening cross of the 2nd session after the cluster date (the vest-day selling is over; Form 4s are due
  within 2 business days), sell the 5th session's close. Return minus SPY over the same window. Filters: prior raw close
  >= $5, 20d ADV$ >= $50M. Costs tier per side.
- **Halves:** select 2021-23 (one look), with the t-stat computed on DATE-level means (vest dates cluster across issuers).
  Proceed only if mean net excess >= +0.30% per trade and date-level t >= 2. Then judge 2024-26 and holdout 2016-20 as in G31.
- **Goal bar:** an add-on at 0.25x per event (taxable), after tax, >= +5pp/yr at $2.3k and $10k. Expected: large caps, so
  most likely small; that's why the bar is two round trips.
- Runner `research/sim/goal_g36.py`. k = 31 when judged.

## Amendment — Goal hunt, Studies G42 and G43: big insider buys in thin names / relative to market cap, 5-session hold (pre-register; program N 780 -> 782)

Session llm-trader-ec, ideas G42 / G43 (`goal_ideas.md`, track T1). Registered 2026-10-02 before any outcome of either rule.
Never computed here before: the >= $500k cut in names with ADV < $20M (ID2 was all sizes, next session), and any
market-cap-relative insider rule.

- **Events:** officer/director code-P Form 4 accessions 2016-26 (`goal_g12.buys()`), summed per (sym, filing date).
  Trade session d = first regular session after the filing date. Prior raw close >= $5.
  - **G42:** $ bought >= $500,000 and 20d ADV$ in [$1M, $20M) (to d−1).
  - **G43:** $ bought >= 0.5% of market cap (raw close at d−1 x the latest XBRL cover-page shares with end <= the filing
    date, `jump_common.shares_hist()`), 20d ADV$ >= $2M.
- **Trade (primary, both):** buy d's opening cross, sell the 5th session's closing cross (hold 5); reported: d open -> d close.
  Return minus SPY (total return) over the same window. Costs `tier` per side (thin names pay the higher tiers).
- **Halves:** select 2021-23 (one look each). Proceed only if n >= 40, mean net excess >= +1.0% (hold 5), date-level t >= 2.
  Then judge 2024-26 (mean > 0, t >= 2, lottery test ex best 5 trades and ex best 5% of dates, random same-ADV-bucket null
  >= 95th pct) and holdout 2016-20 (mean >= 0).
- **Goal bar:** an overlay at 0.25x equity per event funded from the SPY core (taxable), after tax, >= +5pp/yr at $2.3k and
  $10k (add-on), or >= SPY + 10pp as part of the G2 book.
- Runner `research/sim/goal_g42.py`. k = 32-33 when judged.

## Amendment — Goal hunt, Study G45: activist 13D on a closed-end fund, buy the fund (pre-register; program N 782 -> 783)

Session llm-trader-ec, idea G45 (`goal_ideas.md`, track T3/T2). Registered 2026-10-02 before any price around these filings
was looked at. Seen: FTS counts only (Saba SC 13D: 42 filings / 14 funds in 2017, 105 / 23 in 2020, 354 / 58 in 2023; Karpus
193 in 2016-26; the form is "SCHEDULE 13D" from 2025).
- **Events:** the FIRST SC 13D / SCHEDULE 13D (not amendments) filed by Saba Capital, Karpus, Bulldog Investors, City of
  London Investment, 1607 Capital or Almitas on a subject company that is a registered closed-end fund (the subject has
  N-2/N-CSR filings or "Fund"/"Trust" in its name and trades on an exchange), 2016-01..2026-09; subject ticker from the FTS
  display names. One event per (fund, activist).
- **Trade:** buy the opening cross of the session after the filing date, hold 60 sessions, sell at that close. Return
  (dividend-adjusted, Alpaca adjustment "all") minus PCEF (dividend-adjusted) over the same window. Costs `tier` per side.
- **Halves:** select 2021-23 (one look) -> proceed only if n >= 30, mean net excess >= +2.0% per trade, date-level t >= 2.
  Then judge 2024-26 (mean > 0, t >= 2, lottery test ex best 5 trades) and holdout 2016-20 (mean >= 0).
- **Goal bar:** an add-on sleeve (a few % of equity per fund, 60-session holds; Roth-friendly, since CEF distributions are
  income), after tax where it applies, >= +5pp/yr at $2.3k and $10k.
- Runner `research/sim/goal_g45.py`. k = 34 when judged.

## Amendment — Goal hunt, G45-F: the one NEAR follow-up for Study G45 (forward only; no new N)
G45 passed every registered study bar (select +2.55% t 2.48; judge +3.57% t 2.67, ex-best-5 +1.25%; holdout +2.01%) but missed
the Goal add-on bar (+3.4pp/yr vs SPY long-only, ~+3.9pp hedged after tax; `study_goal_g45.md`). Follow-up, registered before
any forward outcome: a log-only watcher records every new first 13D by the same six activists on a listed closed-end fund and
scores it at 60 sessions (dividend-adjusted, vs PCEF). After 30 forward events: PASS iff mean excess vs PCEF >= +1.5% AND the
hedged sleeve (long fund / short PCEF, 12.5% of equity per position, taxable, after tax) >= +5pp/yr on those events; else DEAD.
No interim decisions; no re-run of history with new sizing. N stays 783.

## Amendment — Goal hunt, Study G47: specialist small-bank activist 13Ds, buy the bank (pre-register; program N 783 -> 784)

Session llm-trader-ec, idea G47 (`goal_ideas.md`, track T3). Registered 2026-10-02 before any price around these filings.
Seen: FTS counts only (2016-26: PL Capital 68, Driver Management 127, Basswood 46 SC 13D filings; Stilwell rate-limited).
- **Events:** the FIRST SC 13D / SCHEDULE 13D (not amendments) by Stilwell, PL Capital, Driver Management, Basswood,
  Bulldog-free list as written) on a listed subject (any non-fund subject with a ticker), 2016-01..2026-09; one per
  (subject, activist). Subject ticker from the FTS display names.
- **Trade:** buy the next session's opening cross, hold 120 sessions, sell at that close. Dividend-adjusted return minus KRE
  (dividend-adjusted). Costs tier per side. Prior raw close >= $5 is NOT required (small banks), ADV$ >= $200k (20d).
- **Halves:** select 2021-23 (one look): proceed iff n >= 20, mean net excess >= +3.0%, date-level t >= 2; then judge 2024-26
  (mean > 0, t >= 2, ex best 5 trades > 0) and holdout 2016-20 (mean >= 0).
- **Goal bar:** sleeve at 12.5%/position from the SPY core, after tax, >= +5pp/yr vs SPY at $2.3k and $10k (add-on).
- Runner `research/sim/goal_g47.py` (reuses goal_g45's adjusted-bar fetch). k = 38 when judged.

## Amendment — Goal hunt, Studies G50 / G51: escalation points of CEF activist campaigns (pre-register; program N 784 -> 786)

Session llm-trader-ec, ideas G50 / G51 (`goal_ideas.md`). Registered 2026-10-02 before any outcome of either rule. Same six
activists, benchmark (PCEF, dividend-adjusted), costs, hold (60 sessions) and halves as Study G45; only the event changes.
- **G50:** the first SC 13D or 13D/A (SCHEDULE 13D[/A]) by the activist on a fund whose cover page states >= 15.0% "percent of
  class" (regex on the first 8,000 characters), where every earlier filing by that activist on that fund (in the data) states
  < 15.0%. One event per (fund, activist).
- **G51:** the first PREC14A / DEFC14A / DFAN14A by the activist naming a fund-like subject with a ticker. One per (fund, activist).
- **Halves:** select 2021-23 (one look each). Proceed iff n >= 20, mean net excess >= +2.0%, date-level t >= 2; then judge 2024-26
  (mean > 0, t >= 2, ex best 5 > 0) and holdout 2016-20 (mean >= 0). Overlap with G45's open windows reported.
- **Goal bar:** combined with G45 in one sleeve (12.5%/position from the SPY core), after tax, >= +5pp/yr vs SPY at $2.3k and
  $10k. Runner `research/sim/goal_g50.py`. k = 41-42 when judged.

## Amendment — Goal hunt, Study G53: first 13D on a closed-end fund by any filer OTHER than G45's six activists (pre-register; program N 786 -> 787)

Session llm-trader-ec, idea G53. Registered 2026-10-02 before any outcome. Events from the EDGAR quarterly form index
(2016Q1-2026Q3): every SC 13D / SCHEDULE 13D path; subject = the index entry whose CIK maps to a ticker
(company_tickers.json) and whose name matches the G45 fund regex; filer = the other entry. Exclude filers matching the six
activists (Saba, Karpus, Bulldog, City of London, 1607, Almitas). First filing per (subject, filer). Trade, benchmark,
costs, hold (60), halves and gates exactly as G45 (select n >= 30, mean >= +2.0%, date-level t >= 2). Runner
`research/sim/goal_g53.py`. k = 43 when judged.

## Amendment — Goal hunt, Study G54: closed-end fund insiders buying their own fund (pre-register; program N 787 -> 788)
Session llm-trader-ec, idea G54. Registered 2026-10-03 before any outcome. Events: officer/director code-P Form 4 accessions
(`goal_g12.buys()`, 2016-26, $ >= $10k summed per (issuer, filing date)) whose issuer symbol's name (EDGAR company_tickers /
FTS display) matches the G45 fund regex AND that symbol has an adjusted Alpaca bar history; first event per fund per 90 days.
Trade/benchmark/costs/hold/halves/gates exactly as G45 (60 sessions vs PCEF, select n >= 30, mean >= +2.0%, date-level t >= 2;
judge mean > 0, t >= 2, ex-best-5 > 0; holdout >= 0). Runner `research/sim/goal_g54.py`. k = 44 when judged.

## Amendment — Goal L, Studies L1 / L2: concentration and leverage on the proven legs only (pre-register; program N 788 -> 791)
Registered 2026-10-04 before any outcome of these variants. Prior work cited, not redone: add. 22/29 (leverage profiles,
growth peaks at L ~ 3 under edge-halves), add. 24 D (night top-1 at 100%: dead, Kelly), add. 32 (after-tax frontier knee =
moderate 1.3x), add. 39 (raw pool), index-beat stack (taxable SPY 1.0x + legs on margin). New here: only the two legs with
holdout evidence (IBS ETF leg 2016-20; night leg 2020 raw rebuild), no noise/conviction legs, at the user's balances, with a
$2,000 margin floor, a drawdown stop and a 3-year ruin bootstrap. Three judged variants (N +3):
- **B0 control**: ibs 0.5 / night 0.5 (live today, 1.0x overnight, no margin).
- **L1 concentration**: one budget of 1.0x. On a Sim day where only one leg has a signal, that leg gets 1.0 of equity;
  both fire -> 0.5 / 0.5; neither -> cash (SGOV). No margin. (Top-1-name concentration is add. 24 D, dead; not re-run.)
- **L2a 1.5x / L2b 2.0x**, taxable only (Roth stays 1.0x): both legs scaled to 0.75/0.75 and 1.0/1.0 of equity. Capped at
  half-Kelly: f* = mu/sigma^2 of the 1.0x book's daily returns on the 2016-20 holdout; if 0.5 f* < L, run at 0.5 f*.
  Margin only while equity >= $2,000 (below it: B0). **Hard stop: equity 15% below its running peak -> B0 until a new
  peak.** Margin interest 12.5%/yr on the overnight debit (Schwab base-rate tier for < $25k; not in SCHWAB.md; ~12-13%).
Costs: night tier_hi (2020 rebuild: flat 10bp/side + its 9.1bp bias charge), IBS 3bp/side. Tax: 30% short-term on each
year's net gain, losses carried forward, paid from the account on Dec 31. Shipped simulator `load_sim(raw_price=True)`,
whole shares, $2.3k / $10k / $25k lumps, no deposits (time-weighted). Judge = 2016-20 holdout returns book (night leg 2020
only, bills before; L1 judged on 2020 only, the one holdout year with both legs). 2021-26 is descriptive.
Pass (each variant vs B0): holdout after-tax, after-interest CAGR >= B0 + 2pp/yr; holdout maxDD <= 30% and COVID
(2020-02-19..03-23) loss <= 25%; 3-yr 21-day block bootstrap of 2016-26 under edge-halves P(equity < 50% of start) <= 5%;
2021-23 and 2024-26 after-tax CAGR >= B0 at $10k. Also reported, not gates: worst month, P(equity < $2,000) in 3 yrs,
implied max leverage. Pass = SHADOW at most (live night edge unproven: 34 trades at 09-29; re-arm rule ~100 trades).
Options overlay: no option-chain history in the repo (NEXT.md, Study AR): not testable. Runner `research/sim/goal_l.py`.

## Amendment — Contest hunt, Studies T1 / T2: QQQ 0DTE options on the noise-leg signal (pre-register; program N 791 -> 795)
Session contest hunt (`prompt_contest_hunt.md`), registered 2026-10-04 before any option price was loaded. First options
study in the program (no prior option result exists; Goal L noted "not testable" for lack of chains). Data: Databento
OPRA.PILLAR cbbo-1m (consolidated NBBO, 1-min), only the contracts each rule needs (cost cap $5 of the shared credit);
QQQ signal from the SIP minute matrix (`intra.load('QQQ')`, regular hours 09:30-16:00 by trade date, data to 2026-09-21).
Signal: the noise rule exactly as `research/daily-strategies/noise.py` (lookback 14, step 30, first 30, VWAP stop,
long and short), decisions at the close of minutes 30, 60, ..., 360 (10:00..15:30 ET). Option = QQQ expiring that day.
Fills: decision at minute m, fill on the NBBO record of minute m+1; buy at the ask, sell at the bid, $0.65/contract/leg.
Forced exit 15:50 (minute 380) at the bid (long legs) / ask (short legs); a missing bid counts as 0. Whole contracts.
Sizing: max loss per trade (premium paid, or width - credit) <= 5% of equity; a trade whose one contract exceeds it is
skipped (logged). One position at a time. Four judged variants (N +4):
- **T1a long ATM**: noise long -> buy the call at the first strike >= price; noise short -> the put at the first strike
  <= price; exit when the noise rule exits (or flips: exit, then re-enter the new side) or at 15:50.
- **T1b debit vertical**: as T1a but buy ATM / sell the strike $2 further OTM (call or put spread).
- **T1c long OTM**: as T1a with the strike nearest 0.5% OTM.
- **T2a short iron condor inside the noise area**: at 10:00 (minute 30) if the noise rule is flat, sell the call at the
  first strike >= the day's upper band at minute 389 and the put at the first strike <= the lower band at minute 389,
  buy wings $1 further out; hold to 15:50 (no stop); skipped on days the rule is already in a position at 10:00.
Splits: select 2023-01-03..2024-12-31, untouched judge 2025-01-02..2026-09-21. Costs as above; tax 30% short-term on each
year's net gain (taxable); margin interest none (defined-risk, premium paid in cash).
Pass (each variant): judge mean net P&L per trade > 0 with day-block bootstrap P(mean <= 0) <= 5%; select mean > 0; judge
sum ex best 5 trades > 0; 3-month (63-session) 5-day block bootstrap of the judge period at 5% risk: P(equity -30% within
3 months) <= 10% at $2.3k. Reported per variant: CAGR pre/after tax, 3-month return median / p10 / p90 at $2.3k / $10k /
$25k, maxDD, worst day, win rate (a win rate >= 90% is treated as a bug until audited), skipped-trade share at $2.3k.
Pick among passers: highest judge median 3-month return at $2.3k. Pass = build + live at the smallest size (contest
prompt); no pass = the best is shipped only if labelled unproven. T3 (pre-earnings straddle) is registered separately
if its data can be had. Runner `research/sim/contest_options.py`.

## Amendment — Study H-POOL: the insider-buy next-session open -> close effect as ONE pooled rule, judged on the untouched 2006-15 decade (pre-register; 1 judged rule, program N 795 -> 796)
`date`: Sun Oct 4 02:25 PDT 2026, written before any 2006-15 Form 345 file was downloaded and before any price for a
2006-15 session was loaded. Not committed by the registering session (the file mtime and the session log are the stamp).
**Why.** A program-wide meta-analysis (this session) found select-half strength predicts judge-half results (rank corr
~0.6; judge keeps ~0.61x of select) and the median judge window detects only ~29bp/trade at t 2. The insider-buy
next-session intraday family was cut into underpowered pieces: ID1 (select +20.2bp t 3.4, judge +17.2 t 1.18), ID2
(+27.6 / +14.4), EV1 (+27.7 t 2.42 / +27.3 t 1.85, DEAD on bar g), EV2 (shadow; EV2-big NEAR on 2016-20 via G2). H-POOL
says these are one edge; it is judged once, on a window none of them saw.
**Window touched so far (checked, not assumed):** ID/ID1-3, EV1, EV2, L16-L20 explore: 2020-01..2026-03. G2 (EV2-big,
EV2 all sizes, ID3 >= $500k): 2016-21. J2 (insider after a 30% fall, 5-day jump target): 2016-23 events; its 2014-15
parse was lookback only (`jump_insider.py` filters fd >= 2016). G2's 2014-15 parse was lookback only (fd >= 2016-01-02).
**No insider rule here has computed any outcome on a 2006-15 session.** 2006-15 is therefore the window; 2016-19 is
NOT used (G2 saw its larger-buy, ADV >= $20M part). Published work on the same decade exists (e.g. Cohen-Malloy-Pomorski
2012), so "untouched" means untouched by this program, not by the world.
- **Data.** SEC insider-transactions data sets 2006q1..2015q4 (`insider-transactions-data-sets/YYYYqN_form345.zip`;
  2006q1 is the first published set; parsed exactly as `goal_g2.buys()`, keeping ISSUERCIK). Bars: Alpaca SIP starts
  2016, so **Yahoo Finance chart API daily bars** (regular-session OHLCV, timestamps at the 09:30 ET open -> labelled by
  trade date with `marketdata.trade_date`; split-adjusted, un-adjusted to raw with Yahoo's split events, so price
  filters and the ticker guard use raw prices; open->close and ADV$ are split-invariant). Yahoo open/close are the
  consolidated daily open/close, a proxy for the official 09:30 / 16:00 crosses (no 2006-15 minute or auction data
  exists in the repo). Yahoo has no delisted tickers: **survivor-only** coverage is a known bias, reported, not fixed.
- **Ticker map.** Per (CIK, fd): try the Form 4's ISSUERTRADINGSYMBOL, then the CIK's current ticker (SEC
  company_tickers.json); keep the first series that passes the ticker-reuse guard (dollar-weighted Form 4 price within
  0.67-1.5x the raw close of the session before d, as G2). Count of events lost at each step reported.
- **Event (the union, written once).** Officer/director (RPTOWNER_RELATIONSHIP contains Director|Officer) Form 4 / 4-A
  code-P acquisitions, summed per (issuer, filing date fd). Eligible if ANY of:
  (a) ID1: summed $ >= $10,000 and 20-session mean raw close x volume (to the session before d) >= $1M;
  (b) EV1 (causal form): ADV$ >= $20M and another officer/director purchase filing at the issuer has fd' in [fd-5d, fd)
      (every EV1 chain completion date satisfies this; it is the "cluster is visible" day);
  (c) EV2: ADV$ >= $20M and no code-P filing by anyone at the issuer in the 730 days before fd (evaluable only for
      fd >= 2008-01-01, two years after the data start; before that only (a)/(b) apply).
  Common filters known before the open: raw prior close >= $5; the next session d must be within 7 days of fd; volume
  on d > 0; |open->close| >= 50% dropped (as ID/G2). Trade session d = the first regular session strictly after fd
  (sessions = the exchange calendar; the data sets give a filing date, not acceptance time, so d+0 trading is not
  possible). **One trade per (symbol, d)** (several eligible fd mapping to one d count once).
- **Trade.** Buy the opening cross of d, sell the closing cross of d. Unit = raw open -> close, gross; net = gross - 2 x
  per-side cost. Costs: `book.cost_bps("tier", raw open, ADV$)` (judged) and `"tier_hi"` (stress); 2.5bp/side flat
  (ID/EV comparability) printed.
- **Pass bar (all on 2006-01..2015-12 trade sessions, at `tier`):** (1) mean net > 0 with t >= 2.0, standard error
  clustered by trade date; (2) mean net > 0 in 2006-10 AND in 2011-15; (3) n >= 500 trades. **PASS** = 1-3; PASS is
  "robust" if 1-2 also hold at tier_hi. **FAIL** otherwise. One look, no variant search after it.
- **Data-adequacy gates (checked before the bar; a failure = INCONCLUSIVE (data), not FAIL):** (i) Yahoo vs Alpaca
  raw bars on 2016-19 for up to 300 of the window's mapped symbols, all common sessions: mean(Yahoo - Alpaca)
  open->close within +-5bp and corr >= 0.95; (ii) >= 40% of (a)-eligible-by-$ (issuer, fd) groups get a series that
  passes the guard. Both reported whatever the verdict.
- **Reported, not judged:** n, gross/net mean, median, hit rate, ex-top-1% mean, by-year mean and sign, ID1-only /
  EV1-only / EV2-only subsets (context only, no new N), $-impact as a cash sleeve using idle daytime cash (0.63 x
  equity, split equally over the session's trades, <= 10% equity and <= 1% ADV$ per name, whole shares at the raw open)
  at $2.3k / $10k / $25k (+ one $100k capacity line), %/yr and $/yr at tier and tier_hi.
- **Causality.** Every input is dated <= fd (filings) or <= the session before d (ADV, prior close, guard, cluster and
  silence look-backs), except the inherited same-session |ret| >= 50% and volume > 0 drops (counts reported).
Runner `research/sim/hpool.py` (`build` = events and data gates only; `judge` = the one look).
**H-POOL build result (2026-10-04 ~03:00 PDT; `hpool build`, no outcome computed): INCONCLUSIVE (data); judge NOT run.**
Gate (i) OK: Yahoo vs Alpaca open->close 2016-19, 293 symbols / 293,582 name-days, mean(Y-A) +0.20bp, corr 0.986.
Gate (ii) FAIL: 37.3% of the 90,673 >= $10k officer/director (issuer, fd) groups map to a Yahoo series passing the guard
(27% in 2006 rising to 49% in 2015; 79,813 of 133,626 groups have no Yahoo series = delisted names). Survivor-only bars
miss most of the decade's issuers, so the one look is withheld: 2006-15 stays untouched for every insider rule.
Re-runnable as registered (`hpool judge`, N 796 already counted) once a delisted-inclusive daily source covers >= 40%.

## Amendment — Contest hunt, Study T4: overnight short QQQ 1DTE condor / fly (pre-register; program N 795 -> 798)
Registered 2026-10-04 after T1/T2 were judged (dead) and before any T4 option price was loaded. Mechanism: option returns
are negative overnight and positive intraday (Muravyev & Ni, JFE 2020, "Why do option returns change sign from day to
night?"); sellers of overnight option exposure are paid. Instrument: QQQ options expiring the NEXT trading session (1DTE;
Friday -> Monday). At 15:50 (minute 380) raw close price P (adjusted matrix x raw factor): sell, fill on the NBBO record of
minute 381, close at 09:35 next session (record of minute 5 after 09:30), far side both times, $0.65/contract/leg.
Whole contracts, max loss (width - credit + fees) <= 5% of equity. Every trading day with a next session. Three variants:
- **T4a**: short call at the first strike >= P x 1.005, short put at the first strike <= P x 0.995, wings $1 further out.
- **T4b**: as T4a at 1.0% OTM.
- **T4c iron fly**: short call and put at the strike nearest P, wings $2 further out.
Splits, gates and reporting exactly as T1/T2 (select 2023-01-03..2024-12-31, judge 2025-01-02..2026-09-18; pass = judge mean
> 0 with day-block bootstrap P <= 5%, select > 0, judge ex-best-5 > 0, P(-30% in 3 months) <= 10% at $2.3k). Runner
`research/sim/contest_options.py` (`fetch4` / `run4`).

## Amendment — Contest hunt, Study T3: pre-earnings long straddle (pre-register; program N 798 -> 800)
Registered 2026-10-04 before any T3 option price was loaded. Mechanism: option sellers under-price the uncertainty ahead of
scheduled earnings, so straddles bought a few days before the announcement and sold before it earn +3.34% on average
(Gao, Xing & Zhang, JFQA 2018, 1996-2013; strongest in small names). Events: Nasdaq earnings calendar report date t
(api.nasdaq.com, scheduled date, known weeks ahead), 2023-01..2026-09, market cap >= $2B (the calendar's figure; may be
as-of today, a mild universe look-ahead, noted). Strike = listed strike nearest the raw close of session t-4 (Alpaca raw
daily bars; strictly before entry). Expiry = the earliest listed expiry >= t (first Friday >= t, else the third Friday of
that month). Buy the call + put on the 15:51 NBBO of session t-3 at the ask; sell on the 15:51 NBBO of session t-1 at the
bid (before any report on t, before or after the open). $0.65/contract/leg. Max loss = premium paid + fees <= 5% of equity,
whole contracts, skip otherwise; several events on one day are taken in market-cap order while budget allows (each 5%).
Two variants: **T3a** market cap >= $2B; **T3b** $2B-$10B. Splits by t: select 2023-01..2024-12, judge 2025-01..2026-09.
Gates and reporting exactly as T1/T2. Runner `research/sim/contest_straddle.py`.

## Amendment — Methodology track M1: forward test of the pooled-posterior decision rule (pre-register; no new N)
Registered 2026-10-04, before any forward outcome exists. Source: the meta-holdout of the evaluation process (session
scratchpad `meta/meta_report.md`, ledger of 654 rows / 178 clusters). Its finding: the "NW t >= 2 in both halves" gate
loses 27-62% of ideas with true select-clock t >= 2. The judge keeps what shrinkage predicts (delta ~1.1, shrink 0.63),
so a select t of 2 is expected to give a judge t of ~1.2. Live night-leg cost against the official auction prints is
-0.66bp/side (95% UB +0.09bp, 78 fills), not tier_hi's 7.5-25bp.
**Proposed rule (what M1 tests):** decide on the pooled two-half posterior, with P(mu > 0) >= 0.9 and net edge above the
hurdle at live cost; forward shadow is the third stage; predictions are registered first. Nothing here changes a live
order or a size. M1 judges no new variant, so program N stays at 800 (after T3).

**Model.** Ideas use the t-space normal-normal model A1: mu ~ N(0.36, 1.91^2), s 1.46, judge = 1.10·r·mu + noise,
r = sqrt(n_judge / n_select). The ideas' mu is pooled from both halves. The forward prediction is 0.63 x the pooled
select+judge net per trade at live cost. Live cost is 0bp/side (the mean is floored at 0); the pooled UB +0.09bp/side
is used for scoring. Forward n is reported two ways, both from the judge half's SE (mean / t, on n_judge units):
- n80 = n_j (2.487 SE sqrt(n_j) / pred)^2, which gives 80% power against zero at one-sided 5%;
- the gate count, set near the 24-month count, and P(forward mean > 0 | real at prediction) at that count.
Numbers come from `research/sim/m1_numbers.py` (`PYTHONPATH=. .venv/bin/python -m research.sim.m1_numbers`). Inputs are published select and judge means, t and trade counts only;
no outcome was re-read.

| idea (killed on) | select / judge (bp, t, n) | pooled P(mu>0) | predicted forward | n80 (time) | gate n (time) | P(fwd>0 \| real) |
|---|---|---|---|---|---|---|
| ID1 every officer/director buy, ADV$ >= $1M (judge t 1.18) | +20.2 t3.40 n8934 / +17.2 t1.18 n6076 | 0.981 | **+14.6bp/trade** | 37,400 (13.8 y) | 5,400 (24 mo) | 0.83 |
| ID2 ADV$ $1-20M (judge t 0.86) | +27.6 t2.60 n4699 / +14.4 t0.86 n2982 | 0.944 | **+15.6bp/trade** | 21,200 (16 y) | 2,650 (24 mo) | 0.81 |
| EV1 cluster: another O/D buy filing in [fd-5d, fd), ADV$ >= $20M (judge t 1.85) | +27.7 t2.42 n780 / +27.3 t1.85 n635 | 0.972 | **+20.5bp/trade** | 2,040 (7.2 y) | 560 (24 mo) | 0.90 |
| N2 night leg on CPI/NFP exit mornings vs other nights (leg t 0.74) | +18.7 t2.44 ~70 / +9.0 t0.74 ~64 | 0.924 | **+8.8bp of equity / release night** | 750 (31 y) | 48 (24 mo) | 0.74 |

All four clear the hurdle at live cost. Using the per-name live_hi tier (5-8bp/side), the insider ideas stay positive:
ID1 +7.3, ID2 +8.9, EV1 +16.6bp. N2 is a same-cost comparison of nights; its x1.5 increment must also cover about
2.4bp per release night of margin interest on the extra 0.5x.

**Dropped (cannot be computed forward from data the live system gets, or the kill was not only t / cost):**
- **J2** (insider buy after a 30% fall): killed by its registered control. Falls with no insider buy did as well, and
  the judge mean (+0.5%) was below the stock's usual +1.4%. That is a failed mechanism, not a power failure.
- **MNQ-ORB**: the 2016-20 window lost -8.6% CAGR, which is a third-window failure. One contract also needs ~$29k,
  outside the $2-25k priority.
- **Lab-BD** (QQQ early closing imbalance): needs the Nasdaq NOII paired/imbalance shares at 15:54:30. The live system
  gets only L1 bid/ask sizes at 15:40. Entry is at the NBBO, not in an auction, so the live auction cost does not apply.
- **J1 / J5**: killed as lottery-tail (ex-top-3 judge negative), not on t.

**Cost kills re-scored at the live tier.** `cost_fit.register` fits on the 78 taxable fills: TIERS['live'] = (0.33, 0,
0, 0) and live_hi = (7.81, 4.68, 5.36, 7.96) bp/side. The raw-price pool is used; the published 3bp and tier_hi figures
reproduce exactly. Cells are the increment vs V7 in pp/yr (NW t of the daily difference), 2021-23 / 2024-26:

| kill | 3bp | tier_hi | **live** | live_hi |
|---|---|---|---|---|
| night name cap .15 | +4.4 (2.32) / +7.5 (2.98) | +1.3 (0.67) / +3.6 (1.46) | **+5.2 (2.74) / +8.3 (3.29)** | +3.5 (1.86) / +6.4 (2.53) |
| gated 1.3x overnight, cap .10 | +2.3 (1.17) / +7.1 (2.81) | -0.9 (-0.47) / +2.7 (1.06) | **+3.2 (1.65) / +8.1 (3.21)** | +1.3 (0.69) / +5.8 (2.30) |
| moderate (1.3x + cap .15) | +8.0 (2.08) / +16.7 (3.22) | +0.5 (0.13) / +7.1 (1.38) | **+10.2 (2.64) / +18.8 (3.63)** | +5.9 (1.53) / +14.0 (2.71) |
| night top-3 (bp/trade, t) | — | +1.3 (0.1) / +35.1 (1.6) | **+26.9 (1.8) / +61.2 (2.7)** | +14.3 (0.9) / +48.6 (2.2) |

- At live cost, every cost kill is positive in both halves. The cap .15 change passes t >= 2 in both halves even at
  live_hi.
- Top-3 keeps maxDD -55 to -62%, which is the separate Kelly objection.
- The open question for these four is cost, not edge. Their forward test is the cost measurement already running:
  "Night auction cost by price bucket" at 100 $5-10 trips, plus `cost_fit` refits. No new shadow is added.
- **Pre-registered reading:**
  - If the refit pooled 95% UB stays <= +2.5bp/side at 100 trips, the cap .15 and moderate kills are overturned, to be
    proposed to the user. 1.3x and top-3 stay subject to their drawdown limits.
  - If the UB exceeds tier_hi's 7.5bp for the < $10 names, the kills stand.

**Implementation (log-only, weekly digest "Being tested").**
- ID1, ID2 and EV1 run inside the existing ID3 shadow (`swingtrader/daily/insider_shadow.py`). Rows with ADV$ $1-20M
  carry `id2` and are never counted by the ID3 gate, its EV2 weights or the digest. Rows logged since M1 began carry
  `m1`.
- EV1 uses the issuer's earlier officer/director purchase filing dates, kept in `state/insider-filings.json` and
  pruned to 14 days.
- `m1_gate()` reports n, the mean at 2.5bp/side and at the live +0.09bp/side, and the day-clustered t.
- N2 uses `events.n2_score` on the live taxable book's own night round trips, from 2026-10-05.
- CPI/NFP dates are taken from BLS through 2026-12. The registry line warns when the calendar runs out, so the 2027
  schedule must be appended.
- REGISTRY entries: "M1 ID1/ID2/EV1/N2".

**Decision rule (primary, as proposed).**
- Each shadow's forward mean at live cost is read once, at its gate count or on **2028-10-04**, whichever comes first.
- **Validated** if >= 80% of the shadows show a positive forward mean (with 4 shadows, 4/4).
- **Refuted** if about 50% do (2/4 or fewer).
- 3/4 is inconclusive.
- Interim look on 2027-10-04: report only, no decision.

**Calibration, stated before the data.**
- Under "real at prediction", the expected positive share is 0.82 (mean of the last column).
- Under "zero" it is 0.50.
- With only 4 shadows, P(4/4) is about 0.45 if they are real and about 0.06 if they are zero. ID1 contains ID2 and
  ID3, so the shadows are not independent. A miss of the primary rule is therefore weak evidence against the method.
- **Secondary test (registered now):** Stouffer Z = sum(forward mean_i / SE_i) / 2.
  - The expectation is 1.88 if real at prediction and 0 if zero.
  - **Validated if Z >= 1.645; refuted if Z <= 0.5.**
- ID3 / EV2 (already shadowed, ID3 passed its gate) and the meta's other predictions are not part of M1's count.

**Stop.**
- All four M1 shadows stop on 2028-10-04, or at their gate count if that comes first.
- Their REGISTRY entries are removed in the commit that reads them.
- No idea switches on from M1 alone. A validated method changes the gate for **future** studies; each M1 idea would
  still need its own proposal.

## Amendment — Contest hunt, Studies T5 / T6 / T7: three more option families (pre-register; program N 800 -> 803)
Registered 2026-10-04 before any T5-T7 option price was loaded (T1/T2/T4 judged dead; T3 data loading, unseen).
Shared: Databento OPRA cbbo-1m, far-side fills, $0.65/contract/leg, whole contracts, max loss <= 5% of equity, splits
select 2023-01..2024-12 / judge 2025-01..2026-09, gates and reporting as T1/T2. Strikes from raw prices only.
- **T5 short earnings iron fly through the announcement** (the other side of GXZ's negative through-event straddle;
  retail lottery demand, IV crush). Events as T3 (Nasdaq calendar, market cap >= $2B). ATM = listed strike nearest the
  raw close of t-2; wings = strikes nearest raw close x 1.10 and x 0.90 (same candidate grid as T3); expiry = earliest
  Friday / third Friday >= t+1. Sell the fly on the 15:51 NBBO of t-1, buy back on the 15:51 NBBO of t+1 (covers before-
  open and after-close reports). Max loss = wider wing - credit + fees.
- **T6 QQQ 0DTE long straddle, intraday** (Muravyev & Ni 2020: option returns positive intraday). Every session: buy the
  call + put at the strike nearest the raw QQQ price at 09:45 (decision minute 15, NBBO record of minute 16, ask), sell
  on the 15:51 record at the bid.
- **T7 EV2-big insider buy -> long call**. Events = G2 EV2-big (officer/director code-P >= $500k, no code-P filing at the
  issuer for 730 days; `goal_g12.buys()`), traded the session after the filing date as G2. Buy the call at the strike
  nearest the raw prior close, expiry = earliest Friday / third Friday >= trade day + 5 calendar days, on the 09:35 NBBO
  (record of minute 5) at the ask; sell on the 15:51 NBBO at the bid. Few events (~30-50/yr): reported with its n.
Runners `research/sim/contest_straddle.py` (T5, T7) and `research/sim/contest_options.py` (T6).

## Amendment — Study IN: the insider-buy gap captured from the filing time (pre-register; 2 judged variants, program N 799 -> 801)
Registered 2026-10-04 ~03:40 PDT, before any IN outcome (no auction, extended-hours or quote price for these events has
been loaded; only EDGAR headers). **N bookkeeping:** T4's header says 795 -> 798, but H-POOL (registered just before it)
had already counted 795 -> 796, so the reconciled count is 799; IN adds 2 -> **801**.
Claim being attacked (context note `disc/info_sources.md`, from the cached EV2/ID3 trade file, raw, not SPY-adjusted):
the prior close -> next open of the session after an officer/director buy filing averages +76bp (ID3), +113bp (EV2),
+198bp (EV2 >= $500k); the book trades only the next open -> close (+18bp). **Prior coverage:** G12 (N 775) tested
buys >= $500k accepted 09:30-15:20, bought at the first minute after acceptance + 5 min, sold at the SAME session's close
(select 2021-23 n 128, +32.6bp net, median -5bp, t 1.75: dead on select). No close -> open (or after-hours -> open)
insider window has been computed in any study; L19 (night tilt on 30/90-day insider names) is a different event.
- **Events.** Form 345 data sets 2016q1..2026q1 (`goal_g12.buys()`), document 4 or 4/A, >= 1 non-derivative code-P
  acquisition, reporting owner Director or Officer, P dollars in the accession >= $10k (ID3's definition). EDGAR
  ACCEPTANCE-DATETIME from the filing header (`event_fetch.hdr`, ET). **Public time = acceptance + 1 min** (EDGAR
  disseminates on acceptance, 06:00-22:00; Rogers, Skinner & Zechman 2017 put the public-website lag behind the PDS feed
  at seconds); the entry rule adds 2 more minutes, and a +15 min lag is reported. One event per (symbol, acceptance
  date): the earliest acceptance that day; $ size and "first buy" flags use only that first accession (known at the
  public time). Filters through the PRIOR session (Alpaca raw daily bars; used only for ADV and prior close, not for any
  return): 20d ADV$ >= $20M (ID3), prior raw close >= $5. Half-day sessions (SPY's closing-cross print before 14:00 ET)
  are dropped and counted.
- **IN1 (rule-compliant).** Public time on a regular session in [09:30, 15:50) ET -> buy that session's official
  closing cross, sell the next session's official opening cross. Cross price = the largest-size print in Alpaca's SIP
  auction record for that trade date (the repo's max-by-size rule, `auction_share.load_hist` / `outside_box.cross_prices`),
  keeping only prints whose ET timestamp falls on that trade date (a vendor day can start the evening before).
- **IN2 (research only; deploying it needs a user exception to the sessions rule).** Public time in [16:00, 20:00) ET on
  a session day -> entry on the first SIP 1-minute extended-hours bar starting >= public + 2 min and < public + 32 min
  (no bar in that window = no trade, counted); entry price = max(bar high, bar close x (1 + half-spread)); exit at the next
  official opening cross. **Spread model:** half-spread = median over the SIP NBBO quotes inside the entry minute of
  (ask - bid) / 2 / mid (bid > 0, ask > bid, spread < 10% of mid); when no valid quote exists, the median half-spread of
  quoted IN2 entries in the same price bucket (<$10, $10-20, >=$20) x ADV bucket (<$50M, >=$50M); floored at half a
  cent. The quote is an input cost, not an outcome.
- **Costs and adjustment.** `book.cost_bps("tier", raw price, ADV$)` per side on both legs (tier_hi reported); IN2 pays the
  spread model on top. **Judged unit = SPY-adjusted net**: trade net minus SPY's return over the same window (IN1: SPY
  close cross -> next open cross; IN2: SPY's last extended-hours minute close at or before the entry minute -> next open
  cross). Raw net is reported.
- **Halves.** Select 2022-01..2023-12, judge 2024-01..2026-03 (data end). **The judge window is heavily reused in this
  program** (ID, EV1/EV2, G-series, H-POOL context); its p-values are optimistic. 2016-21 is reported as an extra
  out-of-sample period (EDGAR headers and Alpaca SIP auctions/minutes cover it), not a gate.
- **Pass bar (each variant separately, all in the judge half):** SPY-adjusted net mean >= +25bp/trade; median > 0;
  t >= 2 on the equal-weight daily series (date-clustered); mean > 0 after dropping the top 1% of trades; plus select
  half mean > 0. PASS = all hold; else DEAD. EV2-only and >= $500k-only subsets are reported, never judged (a subset
  result needs its own registration).
- **Artifact checks (reported whatever the verdict):** (a) acceptance vs FILING_DATE by acceptance hour (do 17:30-22:00
  filings carry the next business day's date; is any FILING_DATE earlier than the acceptance date); (b) for IN2, the move
  from the closing cross to the entry price and from the close to the last pre-public print, i.e. how much of the claimed
  close -> open happened before a public trader could act; (c) share of IN2 events with no extended-hours trade within
  30 min of public + 2 min; entry-bar $ volume vs the order at $2.3k / $10k / $25k; (d) % of P&L from the top 1% / 5% of
  trades, by-year signs; (e) every selection field (size, first-buy, ADV, price) dated <= the public time.
- **Sizing (reported):** events/yr; shared nights and daily correlation with the night leg (`B.night_days(raw_price=True,
  max_corr=0.7)`) and with ID3's next-session open -> close on the same events; %/yr as a sleeve on idle overnight cash
  (0.5 x equity per night split equally over that night's events, <= 0.25 x equity per name, whole shares at the entry
  price, IN2 order <= 20% of the entry bar's $ volume) at $2.3k / $10k / $25k, one $100k capacity line. The Roth can
  hold IN1 overnight longs without margin; IN2 needs extended-hours limit orders (broker-dependent).
Runner `research/sim/insider_night.py` (`events`, `fetch`, `run`; one look).

## Amendment — Study T5L: the earnings iron fly on liquid large caps, executable prices, untouched 2016-22 (pre-register; program N 805 -> 806)
Registered 2026-10-04 before any pre-2023 option price or earnings date was loaded. (N: 803 after T5-T7 plus Study IN's two
judged variants, which another session registered as "799 -> 801" in parallel: the true count before this is 805.)
Question: does T5's mid-to-mid +20% of risk (2023-26, `study_contest_t5.md`) survive executable prices, large-cap liquidity
and a period never looked at? One judged variant, no tuning:
- Events: Nasdaq earnings calendar report date t, 2016-02-01..2022-12-31 (judge, never inspected). 2023-26 is the
  selection period (already seen) and is reported only. The calendar's market cap is as-of today (look-ahead): NOT used.
- Liquidity, ex ante: 20-session mean raw close x volume (Alpaca SIP raw daily bars, sessions t-21..t-2) >= $1B/day and
  raw close of t-2 >= $20.
- Structure exactly T5: short ATM call + put (strike nearest raw close of t-2), long wings at the strikes nearest x1.10 /
  x0.90, earliest Friday / third Friday >= t+1. Sell on the 15:51 NBBO of t-1, buy back on the 15:51 NBBO of t+1.
- Executable fills only: every leg at the far side (sell at bid, buy at ask), both ends; $0.65/contract/leg. A short leg
  with no bid at entry = no trade; a missing long-wing bid at exit = 0; no ask on a short leg at exit = unpriced (counted).
- Entry spread gate (observable at entry, executable): trade only if the entry half-spread cost (mid credit - far-side
  credit) <= 10% of the far-side max loss (wider wing - far-side credit).
Pass (all): judge mean return on risk > 0 with event-date block bootstrap P(mean <= 0) <= 5%; judge median > 0; judge
ex-best-5 > 0; positive in >= 5 of the 7 judge years; still > 0 with every exit half-spread doubled (2x spread shock);
>= 300 judge trades. Reported: by year (2020, 2022 stress), mid-to-mid vs executable, win rate, worst trade, 3-month return
distribution at 5% risk per trade at $2.3k / $10k / $25k, the 2023-26 selection-period numbers. Kill = any gate fails.
Runner `research/sim/contest_t5l.py`.

## Amendment — Study NX: the exact live night leg judged on survivorship-free pre-2016 data (pre-register; 1 primary rule + 2 conditional size-up rules, program N 806 -> 809)

Stamped 2026-10-04, before any pre-2016 night-leg outcome has been computed by this program and before the dataset
is chosen. Why now: the night leg is the book's least-verified leg (CLAUDE.md "Research philosophy"); every proposed
size-up (D3 losing-night x2, M1 "moderate" 1.3x + cap .15) depends on it; it has never been judged on data it was not
chosen on. **2016-20 is NOT untouched**: `night_oos_pre2021.py` (survivor-only Alpaca universe) and this session's D3
proxy both read 2016-20 night outcomes on 2026-10-04. It is reported, never judged. The judge window is pre-2016.

**Data requirements (the purchase must meet all, or the study is INCONCLUSIVE, not FAIL).** Daily unadjusted OHLCV
plus split/dividend factors; delisted securities with history through the last trading day and a delisting price or
return; a permanent security id across ticker changes and reuse; security type (common stock vs ETF/ETN/ADR/CEF/
unit/warrant/preferred); an exchange trading calendar. Coverage gate (checked before any outcome): per-year count of
securities passing the eligibility filter within +/-15% of an independent count (e.g. CRSP/NYSE-published listings or
the vendor's own active+delisted totals), and >= 20% of eligible-name-years ending in a delisting over the window.

**Rule (frozen = the live rule as of config.yaml 2026-10-04; daily-bar form, the close stands in for the 15:40 price).**
Eligible on day t from bars before t: prior close >= $5, 20-day mean (unadjusted close x volume) >= $10M nominal.
Pick: close_t / close_{t-1} - 1 <= -8%, IBS_t = (close-low)/(high-low) < 0.10, close in [$5, $2000], 20-day realized
vol (log closes, x sqrt 252) >= 0.60. Crowd: n_raw (before the vol filter) > 30 -> exposure x 30/n_raw. Dedupe: walk
most-beaten first, drop a name whose 20-day returns correlate > 0.7 with a kept one. Weights: signals.night_tilt v1
(k 0.25, frozen NIGHT_TILT constants), per-name cap 10%, weekend/holiday x0.5 (signals.gap_scale). Outcome: next
session open / close_t - 1 on unadjusted prices adjusted only for a split/distribution effective at that open; a name
with no next open (halt/delist) is scored at its delisting price/return, or -100% if the vendor has none.
Universe: PRIMARY = common stock (incl. ADRs) on NYSE/Nasdaq/AMEX; SECONDARY (reported) = all listed incl. ETF/ETN.

**Windows.** Judge: 2003-01-02 .. 2015-12-31 (post-decimalization). Subperiods judged: 2003-07, 2008-09, 2010-15.
Reported only: 1998-2002 if available (pre-decimal spreads), 2016-20 (touched).

**Costs.** Primary: book.TIERS "tier" (5-15bp/side; consolidated open/close are not the auction prints, and pre-2016
spreads were wider). Stress: tier_hi and 2x tier_hi. The live-measured ~0bp is NOT used for the judge.

**Pass bar (primary).** Leg-level, equity-weighted per night, net at tier: mean > 0 with night-clustered t >= 2 over
2003-15; positive in >= 2 of the 3 subperiods; per-trade median > 0; mean still > 0 without its best 5 nights; still
> 0 after subtracting beta x same-night IWM (or Russell 2000 proxy) close->open, beta fitted on the window. FAIL: mean
net <= 0 at tier, or t < 1. Anything else: WEAK (not adopted for sizing; IBS remains the only OOS-verified leg).
Reported, not gated: tier_hi and 2x shock, hit rate, ADV-bucket and year trend (capacity), edge by VIX/vol regime
(mechanism: liquidity-provision premium should rise with stress), sector-adjusted residual.

**Secondary (judged ONLY if the primary passes; rules frozen as stated by D3 and M1 on 2026-10-04).**
NX-S1 losing-night: if yesterday's equal-weight night picks lost <= -2% net, size tonight's leg x2 within equity.
NX-S2 moderate: night 1.3x with name cap .15. Pass: book-level increment > 0 at tier in 2003-15 and in 2 of 3
subperiods, and max drawdown no worse than 1.5x the base leg's. Neither may be live-sized before both the primary and
its own bar pass. No parameter in this amendment may be tuned on the judge window; a second look is a new study.

## Amendment — Study TL: Reg SHO threshold-list forced buy-in, the 13-day clock (pre-register; program N 809 -> 810)
Registered 2026-10-04 before any price, volume or return of a threshold-list stock was loaded (only the free daily
lists and their episode counts exist at registration). One judged rule plus a pre-registered identification contrast.
Mechanism: Rule 203(b)(3) forces a participant with a fail persisting 13 consecutive settlement days in a threshold
security to close it out by PURCHASE (due by the start of list day 14). The question is whether that forced demand is
visible early enough to capture, distinct from generic distress / squeeze behaviour.
Data: Nasdaq daily threshold files (nasdaqthYYYYMMDD.txt) and the NYSE-family JSON (NYSE/Arca/American/National/Chicago),
`research/sim/threshold_lists.py`. A list dated D is public before D's open. Episode = run of consecutive sessions a
symbol is on any list; list day k = k-th session of the run. Funds/ETPs excluded by name (FUND_WORDS in that file).
Prices: Alpaca SIP daily bars 2016+ (split+dividend-adjusted for returns, RAW for the price filter).
- **Primary rule TL1**: every episode still on the list on list day 10 (known at day 10's open). Filters at entry, fixed:
  raw close of day 9 >= $1; 20-session mean $ volume before list day 1 >= $250k; Alpaca bars exist. Buy at the OPEN of
  list day 10, sell at the CLOSE of list day 13 (fixed horizon; removal from the list before day 13 does not change the
  exit: removal is not known in advance). Abnormal return AR = stock return - IWM return over the same open->close window.
- **Identification contrast TL1-ID** (forced timing vs generic distress): same episodes, same-length placebo window
  open(day 6) -> close(day 9). Forced-buy timing predicts AR[10-13] - AR[6-9] > 0.
- Costs: round trip = the Corwin-Schultz high-low spread estimate (mean over the 20 sessions before list day 1), floor
  10bp; plus a 2x cost shock.
Judge = ALL entries 2016-01-04..2026-09-30 (the one look; no design period, the rule is fixed a priori). Gates (all):
n >= 150 entries; mean net AR > 0 with entry-week-clustered t >= 2; median net AR > 0; mean > 0 ex the 5 largest and ex the
top 1% of trades; TL1-ID mean > 0 with clustered t >= 2; positive in >= 60% of calendar years; mean > 0 at 2x costs.
Reported, not gates: AR and abnormal volume (volume / pre-episode 20d mean) by list day 1..16, split overnight
(close->open) vs intraday (open->close); by price, $ADV and episode-length buckets; episodes reaching day 13 vs removed
earlier (descriptive only: conditions on the future); re-entries; per-year; FINRA short interest context 2020+ where
available; capital per trade at 1% / 5% of $ADV, entries per year, P(entering) (share of day-10 episodes passing filters),
top-5 share of P&L, worst trade; feasibility at $2k / $25k / $250k+. Market cap: not available free (DATA-LIMITED; $ADV
used instead). Note: Rule 204 (2008+) forces most fails closed by T+4/T+6, so the day-13 clock may bind rarely; a null
here is informative about that.
Classification: VALIDATED (all gates + economically meaningful capacity), PROMISING (TL1 and TL1-ID pass, economics
unclear), SMALL/NON-SCALABLE (passes but capacity trivial), REJECTED (TL1 or TL1-ID fails), DATA-LIMITED (n < 150).
Runner `research/sim/threshold_tl.py` (`bars`, `run`).

## Amendment — Study EF: ETF share-creation/redemption flow (pre-register; program N 810 -> 813)
Registered 2026-10-04 before any flow-conditioned return was computed. Bar: observable flow -> forced/intermediated
transaction -> predictable price effect -> EXECUTABLE trade; else reject. ETF flows are NOT assumed to be alpha. Three
judged rules. SPDR sector ETF prices were heavily used by the IBS leg; flow-conditioned returns are untouched.
Data (built, no outcomes read): `research/sim/etf_flow_data.py`, files in `data/research/etf_flow/`. SSGA navhist
(date, NAV, shares outstanding SO, total net assets) for 27 SPDR funds: SPY DIA XLB XLE XLF XLI XLK XLP XLU XLV XLY XBI
KRE XOP XRT XHB XME from 2006-06 (SPY, DIA, sectors 2003-12, but SO is blank before 2006-05-31); MDY SO from 2011-01;
XLRE 2015-10; XLC 2018-06; JNK 2007-12; SJNK 2012-03; SPSB 2009-12; SPIB 2009-02; SPLB 2009-03; BIL 2007-05; GLD (grantor
trust, no in-kind basket mechanics like the 1940-Act funds; excluded from the judged rules). ~252 rows/yr, through 2026-10-01
(the SPY file lacked 2026-10-02 on 2026-10-04 while GLD had it: SSGA publication lag is >= 1 session and unknown
historically). Prices: Yahoo chart API 2007+ (split-adjusted OHLC, adjclose), agrees with the Alpaca SIP panel 2016+ on
open/close ratios (median 0.1-0.5bp, p95 1.6-6.7bp; SPY XLK XBI MDY GLD). Pre-2016 opens are the first consolidated print
(auction proxy only); this is a data-quality caveat on the 2008-15 half, not a gate.
**Date convention of SO (internal evidence only; no external source).** corr(dSO_t/SO, premium_{t+k}), premium =
close/NAV-1: the peak is at k = -1 in 2024-26 (SPY 0.19, JNK 0.37, GLD 0.20 at k -1/0) i.e. the row dated t shows shares
created/redeemed on orders from the prior session close (T+1 settlement), and the pre-2024 eras are too weak (<= 0.1) to
date. So the flow occurred at or before the close of t-1, and row t is published after t's close with an unknown lag.
Conservative rule used everywhere: row t is actionable at the OPEN of t+1 (stated baseline, NOT proven; a 2026-10-04
snapshot suggests SPY's lag can exceed one session); every rule is also run with entry at the open of t+2 as a timing
stress, and a rule that passes only at t+1 can be at most PROMISING (timing unproven).
**Flow measure.** f_t = (SO_t - SO_{t-1}) * NAV_t / (SO_{t-1} * NAV_{t-1}) = SO_t/SO_{t-1} - 1 (fraction of shares), with
share-split days (|SO ratio - 1| > 0.4 and the NAV ratio ~ 1/SO ratio) set to NaN. Daily NaN/zero rows are kept.
Universe EQ = XLB XLE XLF XLI XLK XLP XLU XLV XLY (+XLRE from 60 sessions after launch, +XLC likewise) XBI KRE XOP XRT
XHB XME MDY DIA (no SPY: SPY is the benchmark). Returns: adjclose-adjusted open->open. Costs: book.cost_bps tier per side
at each open (ETF price, prior-20d ADV), stress = 2x tier; shorts add 1%/yr borrow. Judge window 2008-01-02 .. 2026-09-30
(one look); subperiods 2008-12, 2013-19, 2020-26 reported. No parameter is tuned; thresholds are round numbers.
- **H1 (Brown-Davies-Ringgenberg 2021): net creations predict underperformance.** Friday t (last session of the week):
  F = sum of f over the trailing 20 rows (ETFs with >= 15 non-NaN rows). Rank EQ; LOW = 3 lowest F (net redemptions),
  HIGH = 3 highest. Enter at the open of the next session after t (Monday), hold to
  the next Monday's open (5 sessions), equal weight, full round trip each week. Primary statistic = LS spread
  EW(LOW) - EW(HIGH) net of cost on both legs + borrow (taxable). Roth long-only version = EW(LOW) - EW(EQ) (excess over the
  equal-weight universe; not itself investable without the benchmark, so the Roth leg is tested as LOW minus EW(EQ) AND must
  beat zero in raw excess over SPY). Gates: n >= 400 weeks; LS mean > 0, Newey-West(4) t >= 2, median weekly > 0, mean > 0 ex
  5 largest weeks, positive in >= 60% of calendar years, mean > 0 at 2x cost; plus Roth LOW-EW(EQ) mean > 0 with t >= 2.
  Entry-at-t+2 stress reported.
- **H2: high-yield bond ETF discount at the close.** Universe JNK, SJNK. D_t = close_t / NAV_t - 1, t's NAV is the SSGA row.
  Signal: D_t <= -1.0%. Entry at the open of t+1 (known from the evening NAV), exit at the open of t+6 (5 sessions). First
  signal of an episode only (signals within 5 sessions of an entry ignored). The NAV can be stale (bonds priced at 4pm bid
  vs a real-time ETF price) so the test is the ETF return, not NAV convergence: AR = ETF return - beta * SPY return over the
  window, beta fitted by OLS on all non-overlapping 5-session windows of the fund. Roth-compatible (long only). Costs tier
  per side (doubled for a 1%+ discount day) plus 2x shock. Gates: >= 15 episodes (fewer: DATA-LIMITED); mean net AR > 0 with
  episode-clustered t >= 2; median > 0; mean > 0 ex 2 largest episodes; positive in >= 60% of years with an episode; mean > 0 at
  2x cost; not carried by one episode window (2008-09 or 2020-03 alone). Reported: raw return, mean D, JNK vs SJNK, t+2 entry.
- **H3: large redemption day, next-day reversal.** An EQ fund-day with f_t <= -3.0% (APs buy the ETF and sell the basket at
  the close; price pressure expected to revert). Enter at the open of t+1, exit at the open of t+2 (1 session), long only.
  AR = ETF open->open return - SPY open->open return. Costs: 2 x tier per side (one-day hold). Gates: >= 150 events; mean
  net AR > 0, date-clustered t >= 2; median > 0; mean > 0 ex 5 largest and ex top 1%; positive in >= 60% of years; mean > 0
  at 2x cost. Creation side (f >= +3%, short) reported only.
Reported, not gates: mean AR by f decile (all rules' fund-days) and cumulative AR by day from t-3 to t+5 (timing: whether the
effect is before t+1's open, i.e. untradable); capacity and turnover; overlap with IBS (share of H3/H1 entries with IBS_t < 0.2
on the signal fund); P&L at $2.3k / $10k / $25k with whole shares; DSR across N.
Classification: VALIDATED (all gates, t+2 stress mean > 0, economically meaningful), PROMISING (gates pass but t+2 stress
fails or Roth leg fails), SMALL (passes, <= 1% of NAV/yr effect or capacity trivial), REJECTED (mean net <= 0 or t < 1),
DATA-LIMITED (episodes/events below the n gate). A pass is log-only shadow proposal only; no live trading.
Runner `research/sim/etf_flow.py`.

## Amendment — Study TME: Treasury month-end duration extension, one definitive look on 2002-15 (pre-register; 1 judged rule, program N 813 -> 814)

Registered 2026-10-04 before any 2002-15 TLT/IEF/SHY price was loaded by this program. Touched, never judged: 2016-26
(the market-map probe read TLT last-3 vs mid-month 2016-26: +42.6bp/month, t 3.46). Study TAC (auction concession,
2016-26) is a different, killed premise; this study does not use auction dates in its rule.

**Mechanism.** The Bloomberg/Barclays US Treasury index (the benchmark for most core bond money) is rebalanced at month-end:
bonds issued during the month enter and bonds falling under one year to maturity leave, so the index's duration jumps on
the last business day. Benchmarked managers (pensions, insurers, bond funds) buy duration into the last sessions of the
month to stay matched; dealers who warehouse the demand are paid through a predictable price rise (Hartley & Schwarz,
"Predictable end-of-month Treasury returns"). Counterparty: dealers/arbitrageurs who provide the duration; the effect
persists because benchmark tracking error is costlier to the managers than the concession. Capacity: the Treasury market;
TLT/IEF ADV is $1B+ (2010s), so the account's size never binds.

**Data.** Yahoo chart API daily bars with dividends (research/sim/etf_flow_data.fetch_px pattern), TLT, IEF, SHY
(inception 2002-07-30), and ^IRX (13-week T-bill yield) for cash. Validation before outcomes: on 2016-26 the Yahoo
closes must match Alpaca SIP closes (median |diff| <= 2bp); else DATA-LIMITED. Trading calendar = TLT's own dates.

**Rule TME1 (judged).** Each calendar month m with a full window: let T = the last trading session of m. Buy TLT at the
close of session T-3, sell at the close of session T (3 sessions held; closing auction both sides; long-only, works in
the Roth and the taxable account). Window return R_w uses dividend-adjusted closes.
Primary statistic: abnormal window return AR_m = R_w - 3 x mean daily TLT return over the OTHER sessions of month m
(removes the month's own drift/term premium). Net = AR_m - 2 x 2bp (2bp/side, TLT; 2x shock = 4bp/side).

**Judge window.** Months 2002-08 .. 2015-12 (~161 months). Subperiods: 2002-08 .. 2008-12 and 2009-01 .. 2015-12.

**Gates (all, for PASS).** mean net AR > 0 with t >= 2 (months are non-overlapping; Newey-West 3 lags reported);
median net AR > 0; mean net AR > 0 excluding the 5 best months; positive mean in both subperiods; positive in >= 60% of
calendar years; mean > 0 at the 2x cost shock.
**Economic threshold (decides the label).** Incremental account return = 12 x mean net R_w-excess-over-cash x the share
of the account deployable for 3 sessions (taxable: idle cash, ~60%; Roth: up to 100%).
VALIDATED = all gates and mean net AR >= +25bp/month (>= ~3%/yr at 100% deployment).
PROMISING = all gates, +10 to +25bp/month. SMALL / NON-SCALABLE = gates pass but < +10bp/month, or the effect is carried
by < 5 months. REJECTED = mean net AR <= 0 or t < 1, or either subperiod negative with t < 1 overall... otherwise
(t in [1, 2) or a failed robustness gate) = REJECTED for adoption, reported as WEAK. DATA-LIMITED = validation fails.

**Identification (reported, not gates; registered so they cannot be chosen after).**
(a) Duration monotonicity: the same AR for IEF and SHY; duration demand predicts TLT > IEF > SHY ~ 0.
(b) Day profile: mean abnormal daily return for sessions T-5 .. T+2; the mechanism predicts concentration on T-2 .. T
and no reversal required before T (a reversal on T+1/T+2 is reported, not traded).
(c) Refunding months (Feb/May/Aug/Nov, larger index extension) vs other months.
(d) Excess over cash (R_w - T-bill) as the money number, and the share of the year's TLT return earned in the windows.
(e) Ex-2008: mean without Sep-Dec 2008. (f) Per-year table.
Capacity, turnover (12 round trips/yr), and $ economics at $2.3k / $10k / $25k / $100k reported.
One look; nothing tuned on 2002-15. Runner `research/sim/tme_treasury.py`.

## Amendment — Study TME-L: leveraged month-end Treasury sleeve, forward shadow (pre-register; 2 rules L2 / L3, program N 814 -> 816)

Registered 2026-10-04 before any leveraged-instrument window return was computed. The base rule TME1 (VALIDATED,
`study_tme.md`) is FROZEN: same windows (close of T-3 -> close of T, T = last session of the month), no change to
entry/exit day, instrument family or costs after this stamp. Question: does leverage raise TME's useful account-level
dollar contribution enough to justify its added tail and implementation risk? Forward shadow only; no orders.

**Rules.** Sleeve capital C = the account's idle cash at the T-3 close, capped at 50% of equity (taxable) / 100% (Roth).
- **L1 (reference, not judged):** TLT, notional 1.0 x C.
- **L2 (2x):** taxable: TLT notional 2.0 x C on Reg T margin (overnight 2x is the Reg T maximum; equity >= $2,000).
  Financing = Schwab margin rate, assumed 12.5%/yr on the debit (1.0 x C), actual/360 over the CALENDAR days held.
  Roth variant (report-only, no margin): UBT (ProShares Ultra 20+ Yr) notional 1.0 x C.
- **L3 (3x):** TMF (Direxion Daily 20+ Yr Treasury Bull 3X), notional 1.0 x C (3x TLT exposure, no margin; Roth and
  taxable). Report-only alternative: TLT 3x is not allowed overnight under Reg T; not modelled.
Entry/exit: official closing-auction prints (primary exchange's largest-size print rule the repo uses) of T-3 and T;
whole shares; the residual cash earns nothing. No intra-window stop (positions are held through overnight gaps; gap
risk is controlled by sizing and the kill rules). Distributions: total return (ex-dates inside a window credited); TLT
ex-dates fall at month start, TMF/UBT quarterly, reported.
Costs per side: TLT 2bp, TMF 5bp, UBT 15bp; stress 2x. Margin rate stress: 14%.

**Measured each window (logged):** sleeve $ P&L and % of C and of account equity; instrument window return vs
k x TLT window return (tracking error, k = 2 or 3) split into: daily-reset path effect, fund fees/swap financing
drag, closing-print slippage; financing $; margin used (debit / equity) and Reg T maintenance headroom at each close;
worst overnight move and worst single session inside the window; 3-session window loss.
Running: monthly P&L, worst month, max drawdown of the sleeve, volatility, downside deviation, % of windows lost.

**Historical implementation measurement (one run, reported, NOT a gate, not evidence of edge).** Over the TME windows
2009-05..2026-09 (TMF from 2009-04, UBT from 2010-01; Yahoo total-return closes, the TME data path): tracking error of
TMF/UBT vs 3x/2x TLT per window, implementation drag, worst 3-session loss, worst overnight move, worst window in
2013 taper / 2020-03 / 2022. This window overlaps the TME judge (2009-15) and the 2016-26 probe: it measures the
instrument, not the edge.

**Kill (forward, either rule, checked at each window close):** sleeve max drawdown > 30% of peak sleeve capital; any
single window loss > 15% of C; for L2, any close with maintenance headroom < 10% of equity; for L3, median tracking
error |TMF - 3 x TLT| > 50bp per window after 12 windows. Kill = stop that rule's shadow and record it; no re-tune.

**Success (evaluated once, at 24 forward windows = the Oct-2028 month-end, interim report-only at 12):**
(1) the frozen L1 TLT window keeps mean net > 0 (edge persists forward); (2) the leveraged rule's mean net $ P&L per
window >= 1.6 x L1's (L2) / >= 2.2 x L1's (L3), i.e. implementation keeps >= 80% / >= 73% of the theoretical multiple;
(3) worst window loss <= 10% of C and sleeve max DD <= 25%; (4) leveraged sleeve P&L ratio to downside deviation
not worse than L1's by more than 20%. PASS = all four -> eligible for a user sizing decision (not automatic).
Otherwise FAIL; if (1) fails, TME itself is flagged for review (forward decay), not re-tuned.
Leverage ratio is fixed at 2 and 3; never optimized on forward data. Runner `research/sim/tme_shadow.py`; digest via
testing.py REGISTRY "TME-L".

## Amendment — Study RB6040: month-end 60/40 rebalancing pressure as a stock/bond relative-value trade, one look on 2002-15 (pre-register; 1 judged rule, program N 816 -> 817)

Registered 2026-10-04 before any 2002-15 month-end SPY/IEF window return was computed. NEW hypothesis, validated
independently of TME (TME is frozen; its bond-demand effect is a confound to measure, not part of this rule). Prior
touched work: add. 34 Q4 M3 (2016-26, SPY-only, MTD SPY-TLT with +/-3% thresholds) and the 2025 paper
(Harvey-Mazzoleni-Melone, NBER w33554). No IBS or any book sizing anywhere in this study.

**Mechanism.** Balanced funds / pensions holding ~60% equity / 40% bonds drift when stocks and bonds diverge within the
month; calendar rebalancers restore weights near month-end: if equities outperformed month-to-date they SELL equities
and BUY bonds (and vice versa). The flow is non-informational, so the price pressure should partially reverse after
month-end. Bond benchmark (Bloomberg US Aggregate) priced at ~15:00 ET until 2021-01-14, 16:00 after.

**Signal (known at entry).** At the close of session T-3 (T = the month's last session), with month-start = last close of
the prior month: Re, Rb = SPY and IEF total returns month-start -> close(T-3);
w = 0.6(1+Re) / (0.6(1+Re) + 0.4(1+Rb)); s = w - 0.6 (positive = equity overweight -> rebalancers sell SPY, buy IEF).
**Trade (primary, every month, direction = -sign(s)):** at the close of T-3, short $1 SPY and long $h IEF if s > 0
(reverse if s < 0); exit both at the close of T. h = sd(SPY daily ret) / sd(IEF daily ret) over the 60 sessions ending
T-3 (volatility-neutral; both legs required). P&L per $1 of the SPY leg:
P = -sign(s) x [(R_SPY - h R_IEF)] over close(T-3) -> close(T), total returns (dividend-adjusted closes).
Primary statistic AP (abnormal): each leg's window return minus 3 x its mean daily return over the month's other
sessions (as TME). Costs per side: SPY 1bp, IEF 2bp, both legs, each side: cost = 2 x (1 + 2h) bp per window; 2x shock.
Instruments fixed: SPY / IEF primary. Data: Yahoo total-return daily (TME path), validated vs Alpaca 2016-26 returns.
**Judge:** months 2002-08 .. 2015-12 (~161). Subperiods 2002-08..2008-12 / 2009-01..2015-12.

**Return gates (all):** mean net AP > 0 and t >= 2 (NW3 reported); median > 0; ex-best-5 > 0; both subperiods > 0;
>= 60% of years positive; > 0 at 2x costs.
**Mechanism gates (judged on 2002-15):** M-dose: OLS of the signed-free spread (R_SPY - h R_IEF, abnormal) on s has a
NEGATIVE slope with t <= -1.5; M-dir: mean P in the top |s| tercile > mean P in the bottom tercile.
**Labels.** VALIDATED = all return gates + both mechanism gates. RESEARCH = return gates pass, one mechanism gate fails,
or all mechanism gates pass with return t in [1.5, 2). INTERESTING = mean net > 0, t >= 1, mechanism directionally
right, economics small (< +5bp net per window per $1 SPY leg) or a robustness gate fails. ARTIFACT = the placebo test
below puts the real mean at < 90th pct, or the effect exists only in raw (not abnormal) returns. DECAYED = passes on
2002-15 but the reported 2016-26 mean net <= 0. KILL = mean net <= 0 or t < 1.

**Reported, not gates (falsification only; never used to change the rule):**
- Placebos: (i) 1,000 draws of one random 3-session window per month from sessions 3..(T-6), signal computed the same
  way at the window start -> percentile of the real mean; (ii) fixed mid-month window (sessions 9-11 -> 12).
- Alternative month-end definitions: T-2 -> T, T-4 -> T-1, T-1 -> T, T -> T+2 (reversal), T -> T+5.
- |s| terciles; months with |Re - Rb| < 1% vs > 5%; ex 2008-09..2009-03; ex the 5 largest |P|.
- Leg decomposition: -sign(s) R_SPY abnormal and +sign(s) h R_IEF abnormal separately (equity-leg effect = new
  mechanism; bond-leg-only effect = overlaps TME). Monthly correlation of P with TME's AR; the unsigned average bond-leg
  return (TME confound).
- Cross-section (same rule): SPY/TLT, SPY/AGG (2003-10+), IWM/IEF, VTI/IEF.
- 2016-26 (touched: add. 34) reported for decay, not judged.
- **2021 natural experiment (mechanism, report-only; Alpaca SIP minutes 2016-01..2026-09):** on day T, split the signed
  spread and each signed leg into close(T-1) -> 15:00 and 15:00 -> close(T). Prediction if the Agg-benchmarked flow
  drives it: the share of the bond-leg signed move in 15:00 -> 16:00 rises after 2021-01-14 (pre 2016-01..2020-12 vs
  post 2021-02..2026-09). The equity leg (S&P priced at 16:00 throughout) is the control: its timing should not shift.
- Capacity: IEF/SPY $ADV from the data by year; spread notional at $100k / $1M / $10M / $100M as % of 3-session volume
  of each leg.
Relationship labels if it passes: A independent (equity leg carries it, low corr with TME), B TME extension (bond leg
carries it, unsigned bond strength), C overlapping (corr with TME AR > 0.5). Runner `research/sim/rb6040.py`; one look.

## Amendment — Study CPC: census of ALL per-holder-capped contract payoffs 2016-2026, as ONE opportunity (pre-register; 1 judged total, program N 817 -> 818)

Registered 2026-10-04 before any new aggregate was computed. Prior (NOT an input): study_goal_g1.md says +20.5pp after tax at
$2.3k, +8.8pp at $10k (2024-26 judge half, SPY-core baseline, B1 ~$370/yr/account). This study re-derives the total from the
per-deal tables, with costs, whole shares, capital allocation and overlap, on 2016-2026 as one block (no judge/holdout split;
the halves 2016-20 and 2021-26 are reported). Nothing is fitted; every rule below is an already-existing deal rule. Runner
`research/sim/cpc.py`, report `research/drafts/study_cpc.md`. Selection-bias caveat, stated up front: these families were
chosen BECAUSE they paid on this same history (B1/B2/odd-lot tenders were registered and judged on it; DL-G27 and DL1 were
kept for paying). The census therefore overstates the forward value of the survivors; it is a ceiling check, not a fresh test.

**Event universe and per-deal sources (frozen).**
- B1 reverse-split round-ups: `data/research/program/roundup_deals.csv`, status `ok` (the repo's "rounded up", never
  "participant level") with ratio_chk in [0.33, 3] (344 deals). One post-split share per account. Buy 1 share at the raw
  close of S (+ half-spread h), sell at the raw close of E+5 sessions (- h). PRIMARY scenario "rounded" (value = pe5);
  SENSITIVITY "cash in lieu" (every deal pays `cash` = P_E/N - ps; Schwab's treatment is unverified until VIVK ~2026-10-07),
  plus E-close exit, plus the break-even P(round). Live 3/day and $25 caps not applied; days with > 3 deals are counted.
- B2 split-off exchange offers with odd-lot priority: `splitoff_deals.csv` (14 offers 2016-25; none failed or cancelled; the
  live MDT/MMED offer is not complete and is excluded). <= 99 parent shares, buy at the close 5 sessions before expiry
  (+h), received shares valued and sold at the first close after expiry (value * (1 - h)), upper limit already in `value`.
- Issuer tender offers (fixed price or Dutch) with odd-lot priority: `data/research/night/tender/oddlot_trades_rule.csv`
  (EDGAR FTS "odd lot" SC TO-I, 2016-26). PRIMARY set = kind cash_fixed/cash_dutch, oddp = Y, entry B, floor_gain >= +1% (the
  tender_watch rule; decidable at entry from the offer's own floor and the market close; 14 deals). Entry at the close (+h), tender
  <= 99 shares, odd lots accepted in full, paid `final` (Dutch: the floor/low end, the conservative reading used in
  study_oddlot_tenders.md), exit date = entry + `days`. Reported variant: ALL cash odd-lot-priority deals with no floor filter.
  Failed or terminated offers would be valued at the market close (none in the set; the table carries the text).
- CEF tender offers (`kind = nav`, 55 offers; 54 of 55 give odd lots NO priority): scored pro-rata, p = `prorate`/100 else 25%
  (stated conservative), residual shares at the first close 5 sessions after expiry (+/- h). Marked CAPITAL-PROPORTIONAL, not
  per-holder capped, and EXCLUDED from the total (it belongs with the book's capacity-limited families); reported on its own.
- Rights offerings: capital-proportional (a holder's rights scale with shares held), no per-deal table exists, earlier
  discovery rounds (I4/I39) found text unidentifiable and payoff ~0. Marked as an UNSCORED GAP, counted $0, excluded.
- Thrift/mutual conversions (DL-G27): `goal_dl27_deals.csv` (18 deals with bars, ~2.6/yr), $2,000 order at $10, exit at the
  first-day close (column d1), tier cost via h. Requires a depositor account opened 1-2 years before the record date, so
  EXCLUDED from the primary total and reported separately as "pre-positioning required" (two scenarios: eligible for every
  listed deal; eligible for 2 deals/yr, the median-by-year deals).
- DRIP/DSPP optional-cash discount: only issuers with a documented non-zero discount actually granted over the window:
  UMH (95% of price, $1,000/month cap, 2016-26) and MNR (same terms, to 2022-02). `drip_ocp_deals.csv`, P&L exit ID+5 (as
  registered in DL1) less an exit half-spread h; capital $1,000 locked ID-5 calendar days to ID+14 (cash to the agent,
  DRS transfer). Taxable only (plan accounts are personal registrations). Other DSPP issuers (CLDT, HASI, OKE, NNN, ONB) have
  no filed history of the discount: forward-only, not counted.
- Eligibility: everything is decided from public information before the entry date. No proration or outcome is used to
  select events, except that the B1 "rounded" label and the B2/tender deal lists were themselves built from filings (offer
  text) available before entry.

**Costs.** Buy at ask, sell at bid, via a frozen half-spread h(P) per side (daily bars only, no 2016 quotes): P < $1:
max(0.005/P, 0.01) capped at 4%; $1-5: 1.0%; $5-20: 0.30%; $20-100: 0.15%; >= $100: 0.07%. $0 commissions, $0 voluntary
reorganization fee (Schwab 2026 guide), whole shares only. Tender/exchange proceeds from the issuer carry no exit spread.

**Accounts and sizes.** Taxable $2.3k / $10k / $25k, cash only (no margin). Roth separately: B1 ONLY. Legal/eligibility basis
(stated, not re-verified in the documents): odd-lot priority in an issuer tender or exchange offer is conditioned on the
holder owning beneficially fewer than 100 shares in total (the offers' own odd-lot certification; SEC Rule 13e-4(f)(3)
requires the issuer to accept odd lots first but defines the class by beneficial ownership), and the repo's tender_buy.py /
splitoff_buy.py already refuse to buy if the owner holds >= 100 in total. A Roth IRA is beneficially owned by the same
person, so Roth shares count toward the same 99. B1's round-up is a broker allocation per account and carries no such
aggregation in the filings' text, so the Roth takes B1. DRIP plan accounts are personal registrations, not IRA. Report-only
variant: the 99-share families placed in a Roth of $8.5k instead of the taxable account (the G21/G22 venue idea).

**Capital allocation and overlap.** All events pooled and processed in entry-date order (ties: B2, tender, DRIP, B1). Each
takes units = min(its cap, floor(free capital / unit cost)) (B1: 1 share; B2/tender: <= 99 shares; DRIP: <= $1,000 continuous;
thrift: $2,000 whole shares); capital frees the session after exit. Concurrent events compete; unfilled events earn $0.
Idle capital earns T-bills: frozen annual 3-month yields 2016-26 = 0.3, 0.9, 1.9, 2.1, 0.4, 0.05, 2.0, 5.1, 5.0, 4.2,
3.7 % (approximate averages, typed here before running). Excess = deal P&L minus T-bill interest on the deployed capital
over its hold (PRIMARY); minus SPY's return over the same hold (SECONDARY, raw SPY bars). Maximum simultaneous capital
and the days-in-deal share are reported.

**Taxes.** Taxable: 35% short-term on each calendar year's net deal gain (losses net within the year, no carryover,
conservative); Roth 0. Years by exit date.

**Aggregation.** Dollars and % of starting capital (constant $2.3k / $10k / $25k, no compounding) per calendar year
2016-2026 (2026 = YTD to 09-30, 0.75 yr); mean = total / 10.75 yr; 2016-20 vs 2021-26; ex-best-5 (the five events with
the largest P&L at that size removed, taxes recomputed); median calendar year. Reported per family in $/yr, events/yr, capital
per event, maximum simultaneous capital, per-account capacity, monthly-P&L correlation with the live book (T0L
`program_books_res_rawpool.pkl`: 'ho' 2016-02..2020-12 daily returns plus tier_hi 'r' 2021-26, monthly sums, over overlapping
months), operational burden (manual steps/yr, automated today), and accounts needed for the total to reach $1k/$5k/$10k a year
(B1 is the only family that scales per account; the rest are per beneficial owner; legitimacy and tax notes, no recommendation
to proliferate accounts).

**Pass (one judged total, the PRIMARY scenario = B1 "rounded", taxable $10k, after-tax excess over T-bills):** mean >= +8pp/yr
AND >= 60% of the 11 calendar years positive AND ex-best-5 mean >= +5pp. Labels on the mean: PASS (all three), NEAR (mean in
[+5, +8), or mean >= +8 with another gate failing), FAIL (mean < +5). The same label is reported for B1 "cash in lieu" and for
$2.3k / $25k, but only the $10k rounded line is the judged one. If B1 is cash in lieu, B1 contributes ~$0 and the rest must
stand alone.

## Amendment — Study TL WITHDRAWN before any outcome (2026-10-04)
Study TL (N 809 -> 810, 27f401c) is withdrawn unrun: no price, volume or return of a threshold-list stock was loaded by
it. Reason: Study THR (another session, `study_threshold_flow.md`, `threshold_flow.py`) already judged the same mechanism
on 1,516 FTD-derived threshold episodes 2021-26: CAR to the 13-day deadline -959bp (t -6.4), the 3 sessions into the
deadline are the worst (-274bp), no volume footprint (0.54x ADV), long-only net -1009bp; CLAUDE.md: "do not re-run
threshold/FTD-buy tests". Running TL would re-test the same idea with other data. TL's registration still counts in N.

## Amendment — Study BH "Asymmetric Bottom Hunter" (pre-register; 1 judged total, program N 818 -> 819)

Registered 2026-10-04 before any drawdown-conditioned forward return was read. Motivation (user): is there a systematic
edge in making relatively large allocations to a name the market prices as nearly dead, when survival is more likely
than the market implies — i.e. bounded downside + large right tail? Prior (NOT an input to the rule, all in `NEXT.md`'s
dead table): long-term reversal 1963-2015 dead (t 1.76, 2016-26 -22bp at 2x); IBS/close-at-low "falling knife" dead;
night 2/3/5-day losers dead; sub-$5 crossers keep falling; going-concern/listing-compliance relief dead; first-profitable-
quarter-after-6-losses lottery-dead; theme-explosion (incl. quantum, add. 28) dead. The open, un-run question is whether
*extreme price depression itself* carries forward asymmetry and whether conviction sizing harvests it.

**Question.** Not "will it go up" but "is the forward return distribution at this price unusually asymmetric, and is it
tradable net of costs on a survivorship-aware universe?" Price-only: the repo has no point-in-time fundamentals panel
(gross margin, debt detail, cash burn, dilution series, guidance, analyst revisions do not exist); XBRL companyfacts,
FINRA short interest (2020-06+) and Form 4 buys (2020-03+) exist for report-only survival proxies. This limitation is
part of the answer, not hidden.

**Data (frozen).** PRIMARY `data/research/night/panel.pkl`, SIP daily OHLCV, split/div adjusted, 2020-10-01..2026-09-21,
13,933 symbols incl. inactive (survivorship-aware, NOT delisted-complete). Extension (REPORT ONLY, never judged):
`data/cache/bars_pre2021/*.parquet`, 2016-01..2020-12, which exist only for today's symbol list (survivorship-limited).
Universe: `asset_meta.json` name excludes ETFs/ETNs/funds/trusts (`theme_explosion.stock_mask`); ticker matches
`swingtrader.universe.valid_symbol`; eligible on a day = close >= $1, 20d median ADV$ >= $1M, >= 252 sessions of history.
Delisting while held: `swingtrader.backtest.DELIST_RET` (-30%) on the last bar. Costs: `book.TIERS` per side by price/ADV
(primary `tier_hi`; `tier` and x2 `tier_hi` sensitivity). Entry = next session's open after the signal close (no same-bar
lookahead); exit evaluated at closes, executed at the next open.

**Signal (frozen, ONE definition; alternatives report-only).** `DD252 = close / rolling_max(close, 252) - 1`.
EXTREME LOW = `DD252 <= -0.70` AND close >= $3 (a $1-3 name is treated as broken, not cheap). Report-only alternative
definitions: `DD_ALL <= -0.70` (expanding max), trailing-2y close percentile <= 2%, z of log price vs 200d <= -2, and
distance from 52w high <= -70%.

**Rule (frozen).** Sleeve, $1 of equity at start, 10 slots. At each close, rank eligible extreme-low names by
`score = min(2.0, max(0.5, 1 + (|DD252|-0.70)/0.30)) * (1.0 if close > MA20 else 0.75)`, take the top free slots by
score (ties by ADV$). Sizing: slot weight = score / mean(score of filled slots) x (equity/10), hard-capped at 10% of
sleeve equity per name; idle cash earns BIL. Exit = first of (a) close <= 0.75 x highest close since entry, (b) close <
MA50, (c) 126 sessions held -> next open; delist at -30%.

**Judged PRIMARY (one look, 2021-26):** the sleeve's mean daily return MINUS the same-day, same-20d-vol-decile random
placebo (50 seeds, identical exits/sizing/costs, `theme_explosion.placebo`), net of tier_hi costs. PASS = mean excess
> 0 AND day-clustered t >= 2 AND ex-best-5 excess > 0 AND the 2016-20 extension excess > 0. NEAR = passes 2 of 4;
FAIL = mean <= 0 or ex-best-5 <= 0. Label on the primary only.

**Report-only (pre-specified, never used to change the primary).** (R1) forward-return distributions by DD bucket and
horizon 21/63/126/252: median, mean, P(+25/50/100/200/500%), P(-20/30/50%), in excess of that day's eligible-universe
mean. (R2) falling-knife: additional drawdown after the signal; share of signals that are within 5% of the forward
252-session low. (R3) survival filters, each vs the same-day eligible mean: price>= $10, ADV >= $10M, close > MA20,
close > 1.05 x 252d low, an insider buy in the prior 60 days. (R4) entry timing: immediate open vs wait-for-close>MA20
vs 5-session staged. (R5) theme/sector capitulation using per-symbol bars (survivorship/hindsight flagged): ETFs QTUM
(quantum), BOTZ/ROBO (robotics), SMH/SOXX (semis), ARKX/ARKQ (space), ICLN/TAN/URA/NLR (clean/nuclear), XBI (biotech),
XLE/XOP (energy), LIT, ARKK, and the quantum basket RGTI/IONQ/QBTS/QUBT/ARQQ — each bought after its own DD252 <= -20%
or <= -30%, hold 126, vs SPY; quantum's rank among themes. (R6) Spearman of the score vs forward 126d return, decile
monotonicity, and equal-weight vs conviction sizing, with dollars at $2.5k/$10k/$25k/$100k/$1M. Runner
`research/sim/bottom_hunter.py`; output `data/research/program/bottom_hunter_out.txt`; one look. If the primary FAILs,
the verdict is KILL/WATCHLIST and no live capital.

## Amendment — Study XB "existing-book optimization: IBS x TME portfolio allocation" (pre-register; 1 judged total, program N 819 -> 820)

Registered 2026-10-04, before any capital-allocation simulation number was read. Motivation (user): the alpha hunt is
at diminishing returns; the remaining lever is whether the ALREADY-VALIDATED legs can be allocated better. Prior
(NOT inputs): every IBS conditional/sizing/universe/exit variant is dead (`NEXT.md` dead table — AP1-AP3, AV1,
vol-target, IBS>200d SMA, leverage Goal L, gap exits, xasset/24-ETF universes all below the +2pp bar); V6
close->open is SHADOW/borderline; no IBS x TME allocation study exists (only the monthly corr -0.09,
`study_rb6040.md:29`). This study opens exactly one question, the open one: **does capital allocation between the
free IBS overlay and the TME-K (Kalman hedge-only Treasury month-end) overlay beat 100%-to-IBS after tax and at size?**
It does NOT touch the production IBS rule, TME's rule, or the backtest periods.

**Frozen inputs.**
- IBS H: monthly top-3 of the 18-ETF universe (`config.yaml:94`) by 12-1 momentum, hold while IBS<0.2; the ALREADY-TESTED
  close(T)->open(T+1) "V6" variant is taken as the primary IBS stream (SHADOW elsewhere); entry next open (no lookahead).
  Daily leg returns from `data/cache/bars/*.parquet` (split/div adj), 2016-01..2026-09.
- IBS G: the same rule with the live open(T+1)->open(T+2) implementation, report-only baseline.
- TME-A: TLT close(T-3)->close(T), no hedge (the validated form).
- TME-K: long TLT + short beta x IEF, beta(t) = trailing-252d OLS beta of TLT/IEF daily returns (lagged), rebalanced
  monthly; residual AR = R_(LT-SH) - 3 x mean daily residual over the month's other sessions; 2bp/side both legs.
  This is the only NEW construction; it is an overlayment of the validated mechanism, not a new mechanism.
- Cash: BIL from `data/research/night/etf_daily.parquet`; TLT/IEF/SHY/^IRX from `data/research/tme/px_*.csv`
  (Yahoo, div-adj; TLT interest roll not modelled -> conservative), 2002-08..2026-09.

**Allocation rule (frozen, no tuned parameter).** Each overlay runs at FULL sleeve notional on its own window; because the
windows do not overlap (IBS = first 1-2 sessions of the month, TME-K = the last 3), the deployed overlays are disjoint.
At any session, the free sleeve dollars are split equally across the overlays then ACTIVE (IBS legs are size 1/3 of the
sleeve each, so an active IBS day uses its share; TME-K uses its share on an active month-end day). Idle sleeve dollars
earn BIL. No leverage, no notional > sleeve. This is "equal allocation when everything overlaps", the simplest rule; no
vol/correlation weighting (those are report-only variants).

**Tax (frozen).** Taxable account: 35% short-term on the year's net overlay gain (losses net within the year, no
carryover); Roth: 0%. Reported both. $2.3k static sleeve (no compounding), 2016-2026; 2026 = YTD to 09-30.

**Judged PRIMARY (one look, 2016-09..2026-09 taxable):** (combined sleeve after-tax/yr) - (IBS-H-only after-tax/yr),
where combined = 50/50 sleeve dollars to IBS-H and TME-K and the whole sleeve is the unit (reported for 100%-IBS-H cash
leakage too). PASS = incremental >= +2.0pp of the sleeve /yr AND positive in both 2016-20 and 2021-26 AND ex-best-5
months still > 0. NEAR = 1.0..2.0pp or one gate fails; FAIL < +1.0pp. The +2.0pp bar is the repo's standing adoption
bar for an IBS change.

**Report-only (pre-specified).** (R1) correlation of the two overlay monthly returns. (R2) allocation variants: 100/0,
70/30, 50/50, 30/70, 0/100; a correlation-aware rule; TME-K hedged vs TME-A unhedged. (R3) maxDD and a bootstrap 5th-pct
of annual dollars, at $2.3k/$10k/$25k/$100k/$1M. (R4) TME-K alone vs TLT-alone (does the hedge help per unit of risk?).
(R5) 50% edge haircut; ex-best-5 months. Runner `research/sim/xb_alloc.py`; output
`data/research/program/xb_alloc_out.txt`; one look. If the primary FAILs, the verdict is KILL for allocation and the
book stays 100% to IBS (TME-K remains a standalone small, capital-light overlay).

## Amendment — Study CC: RGTI \$14-\$16 level bounce, concentration/leverage (pre-register; 1 judged primary, program N 820 -> 821)

Registered 2026-10-05, before any band-conditioned return was read (only RGTI's date range, schema and a
raw==adjusted check were inspected; raw/adj ratio 1.0000 -> no splits/dividends). Motivating hypothesis (user):
"RGTI around \$14-\$16 has historically produced a strong next-day bounce." This opens the Conviction
Concentration / Leverage branch: does an instrument-specific price-state give a conditional next-day
distribution strong enough to justify concentration or moderate leverage? NOT a claim of truth.

Frozen rule: RGTI only; signal = raw close d in [14.00,16.00]; liquidity floor 20d median \$vol >= \$5M; entry
open(d+1); exit close(d+1), max hold 1 session; costs book.cost_bps tier and tier_hi both sides; every band day
counted (overlap allowed), with a report-only "fresh cross" subset. Unlevered size = 100% of sleeve.

Judged PRIMARY (one look, 1,268 sessions): conditional net mean (tier) minus unconditional net mean (all liquid
days, same costs). PASS = conditional net mean >= +50bp AND > unconditional AND positive in 2021-23 and 2024-26
AND ex-best-5 > 0 AND still > 0 at tier_hi. PROMISING = net > 0 with one gate missed. REJECTED = net <= 0, or
not positive in both halves, or ex-best-5 <= 0. Untouched judge is weak by construction (band is hindsight-chosen
by the user; RGTI trades ~\$16 now): report-only chronological split + placebo, no clean OOS, no forward shadow
unless the primary is PROMISING.

Report-only (pre-specified): equal-width band placebo [8,10]..[20,22]; per-year and half returns; random-entry
placebo 2,000 draws; SPY/QQQ beta and alpha on the same window; net mean by 20d-vol tercile and by day-d return
bucket; overnight-gap distribution; leverage 1x-4x (financing 8%/yr, Reg T, ruin). Earnings is DATA-LIMITED
(no PIT calendar). Search expansion classes (oversold levels, DD->reversal, gap-down recovery, vol-shock reversal,
post-event) are pre-specified but NOT run unless the primary survives. Runner `research/sim/conviction.py`;
output `data/research/program/conviction_out.txt`; one look. If the primary FAILs, the branch stops: no expansion,
no leverage study, no deployment.

Prior overlap (NOT inputs): Goal L1/L2 concentration/leverage on IBS+night is dead on holdout (`NEXT.md`, N 789-791);
BH bottom-hunter and theme-explosion already cover drawdown/level hunting on the survivorship-aware panel. This study
is a *different* object (single-name price-state conditional distribution), registered as one idea. No deployment.

## Amendment — Study CLE: small-account IBS leverage (margin vs 3x-ETF financing) (pre-register; 1 judged primary, program N 821 -> 822)

Registered 2026-10-05, before any leveraged account return was read (only Goal L's published 1.5x post-hoc row and the
xasset premium scan were known, both cited as priors). Changed objective (user): small-account capital efficiency at
$2.3k/$10k/$25k, not institutional capacity. Does moderate leverage on the validated IBS leg raise $/yr per account
dollar without unacceptable drawdown/liquidation?

Freezes: IBS leg only (shipped `book.ibs_days()`, night OFF), net 3bp/side, idle cash in BIL; exposure 1x..3x; two
financing routes — retail margin 12.5%/yr on the borrowed fraction (Reg T, $2,000 floor) and a partial allocation to
the ACTUAL 3x ETF tracking each selected name (financing embedded, non-callable) with the rest in BIL; tax 30%
year-end; windows 2016-20 (untouched, judge) and 2021-26. Motivation: Goal L charged retail margin on ALL leverage and
found it loses; a 3x ETF finances at institutional swap rates (~5.5%) and cannot be called, which Goal L never modelled.

Judged PRIMARY (one look): largest LETF-allocated arm with maxDD <= 25% in BOTH windows and bootstrap P(DD>50%) <= 5%,
vs the 1x IBS sleeve. CONVICTION if edge >= +3pp and controlled downside; PROMISING if edge > 0; else REJECTED.
RESULT: 1.5x LETF allocation, +6.5pp OOS (9.6% -> 16.1%), maxDD -22.1% / -24.9%, P(DD>50%) 0%; 2x+ too fragile
(-29% to -49%). VERDICT: **PROMISING**, not conviction (Sharpe ~flat; the gain is financing + non-callability).
Runner `research/sim/cle.py`; output `data/research/program/cle_out.txt`. No deployment.

## Amendment — Study TME-L2: capital efficiency of TME via leveraged Treasury ETFs (pre-register; 1 judged question, program N 822 -> 823)

Registered 2026-10-05, before any leveraged TME account number was read (TME judge and tme_l_hist instrument history are
priors, cited). User question: does modest leveraged Treasury-ETF exposure make TME a materially better small-account
generator ($/yr per $1,000 of account capital), without unacceptable DD or ETF drag? Frozen TME1 signal (close(T-3) ->
close(T), 12/yr). Arms: A TLT 1x; B TLT 1.25x synthetic margin; C UBT 2x; D TMF 3x; E 0.5 TLT + 0.5 TMF. Costs TLT 2bp,
TMF 5bp, UBT 15bp/side; margin 12.5%; idle cash at ^IRX; whole-share; 30% tax; sizes $1k-$25k; DD budgets 20/25/33%.

RESULT (after tax, whole-share, 2009-2026): TLT 1x ~4.3%/yr, -5.9% DD, $43/k; UBT 2x ~4.0%, -17%, $40/k (dominated by
its 15bp/side cost — reject); TMF 3x ~9.5%, -21.9%, $95/k; blend 0.5TLT+0.5TMF ~6.9%, -14.2%, $69/k. ETF drag
TMF-3xTLT -9.2bp/window (~-1.1%/yr). Risk-budget cap (TME-only account): 2.5x under 25% DD, 3.0x under 33%. VERDICT:
PROMISING as a STACKING overlay, not a standalone conviction leg — TMF 3x gives $95/k (vs IBS 1.25x $105/k at the same
~22% DD), and TME is deployed only ~14% of sessions, so it adds on month-end-idle capital. Best use: more IBS allocation
+ modest TME (TMF or the 0.5/0.5 blend). Caveat: 2009-2026 is bond-bull-flattered for 3x Treasuries. Runner
`research/sim/tme_leverage.py`; output `data/research/program/tme_leverage_out.txt`. No deployment.

## Amendment — Study CEF-TL: CEF year-end tax-loss forced selling -> January reversion (pre-register; 1 judged, N 823 -> 824)

Registered 2026-10-05. Frontier search for "edge #3": a named forced counterparty, short duration, small account, different
from IBS/TME. Chosen candidate: taxable CEF holders must realize YTD losses before Dec 31; CEFs are retail-held, hard to
short, thin books. Frozen: 142 CEFs (ib/cef/all, distribution-adjusted total returns 2016-26); rank by YTD total return
through last Nov session; bottom quintile; Dec leg (Nov_end->Dec_end) predicted underperformance, Jan leg (Dec_end->Jan_end)
predicted reversion vs equal-weight universe; long-only; 30bp round trip. PASS = Jan Q1-u >= +1.0% net, both halves,
ex-best-5>0, Dec forced sign.

RESULT: Dec Q1-u +0.27% (t 0.63, WRONG sign), Jan Q1-u +0.01% (t 0.01), Jan Q1-Q5 -0.93%; quintiles non-monotonic
(D5 best). The apparent Jan Q1 +2.7% is market beta (2018/2022 down-year rebounds), not tax-loss-specific. Gates 1/4.
**VERDICT: REJECTED** — no forced-selling signature. Runner `research/sim/cef_taxloss.py`; out `cef_taxloss_out.txt`.
Next candidates in the frontier: CEF discount-vs-own-history (needs a daily-NAV data build; strongest mechanism),
dividend-month premium (Hartzmark-Solomon; testable, weak/non-forced mechanism). No deployment.

## Amendment — Study FCC: commodity futures curve carry, frozen (pre-register; 1 judged, N 824 -> 825)

Registered/run 2026-10-05 exactly as frozen (RY=(F2/F1-1)*12/months -> front excess return over the next roll
period; CL/NG physical vs ES/NQ null; glbx 2011-2025; fut_roll roll-date definition; one tick/leg; fit 2011-17, OOS
2018-25). Data note: Databento single-digit years repeat every decade, so contracts were split into instances on
>400-day gaps; 2020-04 negative WTI makes one CL period return < -100% (flagged, not the verdict driver).

RESULT: OOS pooled physical L/S +87.7bp/period but the pooled equity is destroyed (cum -120%, maxDD -137%); CL
-86.6bp vs NG +344bp -> **sign carried by one commodity (kill #2 FIRES)**; RY quintiles non-monotonic (CL+NG
-154/+61/-65/+138/-44bp); NG's OOS is a 2021-22 gas-crisis outlier (sd 1650bp, maxDD -75%); ES/NQ ~0 (null
consistent, but physical not stably positive). Fit window physical -30.6bp. **VERDICT: REJECTED — commodity curve
carry permanently closed under this frozen formulation.** Runner `research/sim/fcc.py`; out `fcc_out.txt`.

## Amendment — Study PB: pre-boom predictability (tail-probability, pre-register; 13 conditions + 2 benchmarks, N 825 -> 826)

Registered 2026-10-05, **before any conditional outcome was computed**. Only the *unconditional* boom base rates and
the panel shape were read (explicitly permitted for threshold calibration). Question, frozen: does any condition
observable at close t raise **P(a stock enters the extreme right tail of future returns)**, not P(positive mean
return)? The already-killed family (buy-after-large-move, 52w breakouts, high-volume breakouts, 63d momentum, theme
clusters, residual momentum, ORB, IPO pops, trailing winners, generic cross-sectional momentum) is NOT re-run.

Data: the add. 28 survivorship-aware panel `data/research/program/add28/theme_panel.pkl` (14,697 symbols, 1,958
delisted, open/close/volume, 2016-01..2026-09, adjustment='all'). Honest window 2020-10-01..2026-09-21; 2016-2020
is **exploratory only** (pre-2021 inactive list is thin -> survivorship-flattered; never judged). Eligibility at t:
close >= $3, adv20 (median C*V) >= $5M, >= 120 bars, non-ETF (`theme_explosion.stock_mask`). No permanent security id
exists (tickers only); delisting is the last non-NaN bar; no vendor delisting return.

Boom definitions, frozen from the unconditional honest-window distribution (4.46M stock-days):
- **PRIMARY boom**: fwd20 = close(t+20)/close(t) - 1 >= +30%. Base rate **2.23%** (top ~2.2%).
- SECONDARY: fwd60 >= +50%. Base **2.66%**.
- DOWN control: fwd20 <= -30%. Base **1.42%** (used for the direction test).
- VOL-RELATIVE: fwd20/sigma20 >= 6. Base **12.3%** (q95 of the ratio is 9.07 -> a fixed +30% is only ~1.5 sigma for
  high-vol names, so the absolute target is vol-confounded; the vol-matched control below is mandatory).

Conditions, frozen (all computed from bars <= t; cross-sectional extreme decile each day; no threshold tuning):
1 `volcomp` vol20/vol60 bottom decile (volatility compression / coiling)
2 `rngcomp` mean((H-L)/C) 5d / 60d bottom decile (range contraction)
3 `voldry` (C*V) 5d / 60d bottom decile (volume dry-up)
4 `accumbias` 20d (up-volume - down-volume)/total, top decile (accumulation)
5 `amihudrise` Amihud |R|/(C*V) 10d / 60d top decile (illiquidity rising)
6 `ivolrise` residual-vol vs SPY 10d / 60d top decile (idiosyncratic vol rising)
7 `corrbreak` rolling 20d corr(stock, SPY) bottom decile (correlation breakdown)
8 `gapfreq` share of last 20d with |overnight gap| > 2%, top decile
9 `sincrease` FINRA short interest, latest published vs prior, top decile of delta (PIT pub date)
10 `dtchigh` FINRA days-to-cover top decile (PIT)
11 `ftdspike` FTD qty / 20d median dollar-vol top decile (PIT pub date)
12 `insiderbuy` any Form 4 open-market purchase (code P, acquired) filed in the last 10 sessions (binary, PIT filing date)
13 `earnprox` an earnings date in the next 5 sessions (binary; Nasdaq calendar, scheduled -> PIT)
BENCHMARKS (not conditions; the disguise test): `ret20top` trailing 20d return top decile; `nearhigh` within 5% of the
252d high. A condition that only beats the base rate because it is one of these is "momentum in disguise" and KILLED.

Split, frozen: **DISCOVERY 2021-01-01..2023-12-31**; **OOS 2024-01-01..2026-06-30** (last signal so fwd60 exists).
The 2016-2020 exploratory window is reported, never judged. Conditions are chosen from theory, not fit; no thresholds
are tuned on either window.

Metrics per condition x target: P(boom|cond), P(boom|no cond), base, lift, precision, recall, false-positive rate, n,
median fwd return, P(downside|cond), median sessions to boom, and maximum adverse excursion (min low) before the boom.
**A vs B discriminator (the point of the study):** (i) *vol-matched lift* = P(boom|cond) vs P(boom | a random pick
from the SAME sigma20 decile), via placebo (200 seeds) — a condition that raises both tails but not direction is
outcome **B**; (ii) *asymmetry* = lift_up(+30%) - lift_down(-30%) must be > 0 for a directional edge; (iii)
*momentum orthogonality* = lift computed WITHIN trailing-20d-return deciles.
Multiple testing: 13 conditions x 4 targets; family-wise bar from a max-statistic permutation (1,000 within-date
shuffles of the condition label) plus Bonferroni; a condition must clear the OOS bar, not just discovery.

KILL the branch if (any): lift is small (OOS P(boom|cond) < ~2x base, i.e. < ~4.5% for the primary); the result is
carried by < 5 names / < 3 months (report ex-top-5 and per-year); it vanishes OOS; it needs hindsight; it is
momentum/breakout in disguise (benchmark check); it predicts volatility but not direction (outcome B); or execution
destroys it. No threshold tuning to rescue.

Economic test (ONLY if the primary survives): arms 1 buy at condition, 2 condition + a directional confirmation,
3 fixed small allocation across qualifiers, 4 concentrated top-confidence. Net 3bp/side (10bp small names), whole
shares, 30% tax, no leverage. Leverage is downstream and is not tested unless the predictive test passes.

DATA-LIMITED (reported, NO proxies invented): options activity and realized-vs-implied vol (no broad stock OPRA
surface — only SPY/QQQ windows cached), institutional positioning (13F cached as cusip only, no shares/value),
borrow fees / recalls (no history), historical L1 spreads (no quote data). No deployment; no portfolio change; no
data purchase. Runner `research/sim/preboom.py`; output `data/research/program/preboom_out.txt`. One look.

RESULT (one look; `research/sim/preboom.py` + `preboom2.py`; out `preboom_out.txt` / `preboom2_out.txt`). Discovery 2021-23 base
P(fwd20>=+30%)=1.81%; OOS 2024-26H1 base 2.68% (P(fwd20<=-30%)=1.48%). Several conditions robustly raise the RIGHT tail OOS, per-year,
beyond a same-sigma20-decile control AND beyond momentum (ortho lift within the non-momentum universe): voldry 1.70x / ortho 1.93,
ftdspike 1.94x / 1.91, gapfreq 3.59x / 3.79, dtchigh 1.43x / 1.53, earnprox 1.43x / 1.44, volcomp 1.31x / 1.43, amihudrise 1.13x / 1.29.
Concentration is fine (thousands of events, 600-800 names, all 30 months, top-5 < 8%). **BUT every one raises the LEFT tail as much or
more:** up-lift minus down-lift is NEGATIVE with a day-clustered 95% CI excluding 0 for volcomp/rngcomp/voldry/accumbias/gapfreq/ftdspike
(and the ret20top benchmark), and the few positive ones (amihudrise, dtchigh, insiderbuy) flip sign between windows or have right-tail lift
~1.0. Median fwd20 conditional on the big-lift conditions is <= 0 (voldry -0.83%, gapfreq -0.83%); MAE -6..-12%. The conditions predict
VOLATILITY / big-move, not direction. The one consistently-positive-asymmetry condition (insiderbuy +0.07/+0.13) has no boom lift (~1.0).
Momentum itself (ret20top) raises the right tail 2.38x but is the killed family and even more bearish-skewed (-0.42). Data-limited (no
proxies invented): options/IV, 13F positioning, borrow fees, L1 spreads. VERDICT: **PREDICTABLE BUT NOT TRADEABLE (outcome B); the
pre-boom branch is KILLED.** No directional pre-boom signal; economic test not run (primary did not survive). No deployment.

## Amendment — Study PB-C: the confirmation arm — follow the direction once the move starts (pre-register; N 826 -> 827)

Registered 2026-10-05, before any confirmation-conditional number was read. User question: if a pre-boom condition says a
big move is coming (both ways), why not wait for the move to start, then go WITH it? Frozen test of PB's arm 2.
At t the PB condition is present; the early move is e5 = close(t+5)/close(t) - 1. **PRIMARY confirmation: e5 >= +10%
(up) or e5 <= -10% (down); entry at close(t+5); target from entry fwd20 = close(t+25)/close(t+5) - 1, boom >= +30%,
bust <= -30%.** Secondary reported (not judged): e3 >= +8%, e1 >= +5%. The decisive control is the SAME early move
WITHOUT the condition (plain momentum): if cond+up == plain-up, the condition adds nothing and this is the killed
"buy-after-a-large-move"/breakout family in a new costume (Lab-AX -33.7bp, ORB -23.5bp, add. 28 breakouts). Economic
bar: mean fwd20 net 20bp round trip > 0 AND P(boom|cond,up) > P(bust|cond,up) with a day-clustered CI. Kill otherwise.
Runner `research/sim/preboom3.py`; out `preboom3_out.txt`. One look.

RESULT (one look). OOS `e5>=+10%`, entry t+5, fwd20 from entry: the **plain up-move (no condition) mean +1.16% (net +0.96%)**,
but the SAME early move measured **DOWN is better: +2.20% (net +2.00%)**; discovery flips the up-move negative (net -0.97%)
while down is ~flat. Adding any PB condition to the up-move does **not** help (cond+up net 0.5-1.4% OOS, every one negative in
discovery; ALL-up >= cond+up). Boom/bust ratio: ALL-up 1.48, cond+up 1.0-1.8, cond+down often higher (dtchigh 1.98, amihudrise
2.22). Secondary e3/e1 identical. So the early move is a coin flip that leans toward **reversal (fade)**, not continuation, and
the pre-boom condition adds nothing. This is the killed buy-after-a-large-move / breakout family. **VERDICT: REJECTED.** No deployment.

## Amendment — Study PB-M: magnitude and skew of the conditional boom (pre-register; N 827 -> 828)

Registered 2026-10-05 before any magnitude number was read. PB measured the *probability* of crossing a fixed +30%/+50%
line; a pure vol increase fattens both tails proportionally and would show the symmetric lifts already seen. The untested
question: does any condition raise the **magnitude/skew** of the right tail (the long-only "golden egg": fat upside, capped
downside)? Frozen metrics, per condition, discovery 2021-23 and OOS 2024-26H1: mean fwd20/fwd60 net 20bp; P(fwd60>=+100%);
mean(fwd60 | fwd60>=+50%) [right magnitude] vs mean(fwd60 | fwd60<=-50%) [left magnitude]; conditional skew; the "boom
share given a big move" = P(+30% | |fwd20|>=30%, cond) vs base (the true direction-of-the-big-move test); and an additive
score = count of the 7 primary conditions true, its top decile, and its equal-weight daily basket (net, vs the eligible
universe). A golden egg requires a condition (or the score) with right-magnitude growth > left AND a positive net basket.
Kill otherwise. Runner `research/sim/preboom4.py`; out `preboom4_out.txt`. One look.

## Amendment — Study PB-O: does a pre-boom condition predict the OVERNIGHT (the book's mechanism)? (pre-register; N 828 -> 829)

Registered 2026-10-05 before any overnight number was read. PB/PB-M used 20/60-session targets the account cannot hold
cheaply. The account's actual mechanism is close(t) -> open(t+1) (MOC buy / MOO sell, the night leg) and, secondarily,
open(t+1) -> close(t+1) (intraday). Question: does a condition at close t predict the **next overnight** return (mean
and tails), and is it directional? Frozen, per condition, discovery 2021-23 and OOS 2024-26H1: mean overnight net 5bp,
P(>=+5%), P(<=-5%), up/down asymmetry, and the same for the next intraday. A golden egg requires a positive net overnight
mean with up/down asymmetry > 0 in both windows. Runner `research/sim/preboom5.py`; out `preboom5_out.txt`. One look.

## Amendment — Study PB-N: do the pre-boom conditions improve the night (crash-bounce) leg? (pre-register; N 829 -> 830)

Registered 2026-10-05 before any number was read. Synthesis test: PB says the conditions predict volatility; the reversal
premium scales with volatility (cross-asset scan); the night leg buys the -8% crash (close -> next open). Does a condition
at the signal close raise the night pick's next-open return? Frozen: merge the PB condition flags onto
`data.night_candidates()` (20,501 picks 2020-11..2026-09); per condition, discovery 2021-23 and OOS 2024-26H1, report
mean/median night ret (bp) cond vs not, hit rate, the day-clustered t of the difference, P(ret>=+5%) and P(ret<=-5%),
and the additive condition count (0..). Pass (a size-up candidate, shadow at most) requires the increment > 0 in BOTH
windows with day-clustered t >= 2 in at least the OOS window and not carried by < 5 names. Runner
`research/sim/preboom6.py`; out `preboom6_out.txt`. One look.

## Amendment — Study PB-S: do the conditions aggregate into a market stress-timing signal? (pre-register; N 830 -> 831)

Registered 2026-10-05 before any number was read. Different object: PB is cross-sectional; the conditions may share a
common factor. stress_t = mean condition count (0-8) across eligible names each day, plus the fraction with score >= 3.
Question: does stress_t predict forward market return (SPY 20d), forward realized vol (SPY 20d), and the book's own
forward IBS premium (open->open on the EQ18 ETFs)? Frozen: discovery 2021-23, OOS 2024-26H1; rank-correlation of stress
with each forward quantity, and the top/bottom stress decile forward means. A golden egg requires stress to predict a
POSITIVE forward market/vol premium with the sign stable in both windows. Runner `research/sim/preboom7.py`; out
`preboom7_out.txt`. One look.

RESULTS (PB-M / PB-O / PB-N / PB-S, one look each). The conditions are a **BEARISH / falling-knife screen, not a boom screen**.
- PB-M: the additive condition count is monotone NEGATIVE for forward return. Discovery mean20 net by count 0..6: +0.11 / -0.21 /
  -0.41 / -0.78 / -2.55 / -5.09 / -7.28%. OOS the count-4..6 buckets underperform the universe. The strongest right-tail-lift
  conditions (gapfreq, ftdspike, voldry) are the most bearish. Long basket (score top decile) is BELOW the universe in both
  windows (disc -1.31 vs +0.05%; OOS +0.78 vs +1.34%). Right-tail magnitude (mean fwd60 | >=+50%) ~85-95% vs left (| <=-50%) ~-60%,
  same as the universe (ordinary stock skew), no differential.
- PB-O: no positive overnight. Conditions predict a BIGGER close->open move (gapfreq P(>=5%) 3.81% vs base 3.24% OOS) but the mean
  is <= universe and up/down is symmetric. Only insiderbuy is mildly positive overnight (+0.086% OOS vs +0.061% base, +5bp) = noise.
- PB-N (the synthesis test): on the book's OWN -8% crash pool (20,501 picks), the condition count is monotone NEGATIVE for the
  next-open bounce. Discovery by count 0..4: **+23.4 / +2.2 / -6.2 / -11.7 / -54.3bp** (base +10.9); OOS noisy but clean-crash
  (count 0) +9.3bp vs base +3.6. So the conditions separate *liquidity* crashes (bounce) from *informed / falling-knife* crashes
  (keep falling). The high-count names are exactly the ones the night leg should NOT buy.
- PB-S: no market-timing signal. corr(stress, fwd SPY) +0.02 disc / -0.10 OOS (sign flip); corr(stress, fwd vol) ~0; corr(stress,
  IBS premium proxy) slightly NEGATIVE (-0.08 / -0.02). No aggregation edge.
VERDICT: **REJECTED as a long boom predictor.** The genuine pattern is bearish (falling knives); its tradeable long-only form is
the *inverse* (buy clean crashes / avoid stressed ones, a night-leg filter, increment ~+6bp disc but -2bp OOS) and its profitable
form (short the stressed names) is inaccessible (no shorting in the Roth, hard-to-borrow names, retail option spreads). No deployment.

## Amendment — Study SH: is the falling-knife short edge ACCESSIBLE? (pre-register; N 831 -> 832)

Registered 2026-10-05 before any short number was read. PB/PB-M found the pre-boom conditions are a bearish screen
(condition count monotone predicts underperformance; high-count -8% crashes keep falling). The repo's recurring short
conclusion is that the profitable side sits on unborrowable names (Study S, Lab-BA). Decisive test: does the edge survive
among **liquid, easy-to-borrow** names? Frozen: universe = eligible panel names split by `asset_meta.easy_to_borrow`
(current flag; survivorship caveat) and ADV20 >= $50M (liquid) vs $5-50M. Signal = condition count 0-8. Arms:
(a) SHORT top-decile count only; (b) dollar-neutral long bottom-decile / short top-decile count. Hold 20 sessions.
Costs: 20bp/side (40bp round trip per leg) + borrow 0.5%/yr on ETB (25bp/20d) or 5%/yr on non-ETB. Judge discovery
2021-23 and OOS 2024-26H1. PASS (a shadow short sleeve) requires (b) or (a) net > 0 in BOTH windows on ETB+liquid names
with day-clustered t >= 2 in OOS and not carried by < 5 names. Also report each individual condition's short edge by
liquidity/ETB. Runner `research/sim/short_pb.py`; out `short_pb_out.txt`. One look.

RESULT (one look). The falling-knife short is real in *discovery* but not accessible/stable.
- Market-neutral (long score==0 clean, short score>=3 stress, 20d): Discovery gross **+1.45%/20d (t 7.95)** on all names,
  but net of 40bp round trip + 0.5% borrow it is **-1.85%**; on the accessible **ETB** names gross +0.70% (t 3.99) and net
  **-0.35%**; on ETB+liquid gross +0.32% (t 1.34). **OOS the sign reverses** on ETB (-0.59% gross, t -3.6) — the
  high-stress names *outperformed* in the 2024-26 bull. Short-only loses everywhere (top-decile short net -0.5% disc,
  -2.9% OOS ETB+liquid: the names rose). Every individual condition's short edge is negative OOS (market beta + junk bid).
- Non-overlapping (every 20th session) LS is +1.46% disc (t 2.16) / +1.17% OOS (t 1.36), but the overlapping daily mean
  flips OOS sign -> not stationary. Regime split: works in risk-ON (+1.43%, t 2.3), ~0 in risk-off — i.e. it is the
  quality/junk-beta spread, not short alpha.
**VERDICT: REJECTED (no accessible short edge).** The falling-knife screen is a discovery-period junk-beta effect:
net-negative after costs on easy-to-borrow names, reverses OOS, and the profitable version sits on HTB/SSR names (the
repo's recurring short conclusion: Study S, Lab-BA). No deployment. The short frontier remains data-blocked (borrow/HTB
fee history, PIT ratings for fallen angels) rather than idea-poor.

## Amendment — Study EX: the falling-knife screen as a long-only night-leg filter (pre-register; N 832 -> 833)

Registered 2026-10-05 before any filter number was read. PB-N found the night (-8% crash) bounce worsens monotonically with
the condition count (score 0 -> 4: +23.4 -> -54.3bp discovery). Long-only use: does excluding / down-weighting stressed
crash picks, or up-weighting clean ones, improve the shipped night leg? Frozen, on `data.night_candidates()` (20,501
picks), discovery 2021-23 and OOS 2024-26H1, per-trade night ret: EX1 exclude score>=2; EX2 exclude score>=3; EX3
up-weight score==0 2x (renormalised); EX4 exclude picks whose individual `voldry` is set. Report kept/removed means,
the leg improvement = (kept_mean - base_mean) x kept_fraction, the day-clustered t of the kept-vs-all daily mean
difference, and a within-night placebo removing the same count of random picks (200 seeds). PASS (shadow at most)
requires improvement > 0 in BOTH windows, t >= 2 in OOS, and placebo >= 95th pct. Runner `research/sim/preboom8.py`;
out `preboom8_out.txt`. One look.

RESULT (one look). Discovery looks strong, OOS kills it. Discovery (base +10.9bp): EX1 excl score>=2 keep +17.0 / rem -10.3,
improve **+4.8bp** (t 1.15, placebo 99%); EX4 excl voldry keep +15.6 / rem -42.1, improve +4.3bp (t 1.05, placebo 100%);
EX3 tilt clean +4.4bp. OOS (base +3.6bp): EX1 improve **-1.9bp** (t -1.53, placebo 16%), EX2 -0.3bp, EX4 +0.6bp (t -1.49),
EX3 +2.0bp. The removed stressed picks did *better* OOS. No arm clears ">0 both windows, t>=2 OOS" — it is a
discovery-period artifact. **VERDICT: REJECTED.** The falling-knife screen is not a usable long-only night-leg filter
(and its short side is inaccessible, Study SH). No deployment.

## Amendment — Study ACC: account structure for the IBS edge at small size (pre-register; N 833 -> 834)

Registered 2026-10-05 before any account-structure return was read (only Study CLE / CLE-attack leverage rows, Study Y
scale, Study AL Roth-cash are cited as priors). User question: with the OOS-validated IBS leg taken as given, what
account structure maximizes after-tax %/yr on $2.3k / $10k / $25k over a 5-year horizon — Roth-first contribution
sequencing (+$7.5k/yr guaranteed), asset location, and the best non-callable leverage (3x-ETF allocation vs margin) —
subject to account maxDD <= 25% and no liquidation? Judged on the 2016-20 holdout.

Frozen leg: the live IBS rule only (`book.ibs_days`: top-3 of the 18 EQ18 ETFs by 12-1 momentum re-ranked monthly,
IBS(close d)<0.2, buy open d+1, exit open d+2), 3bp/side. Night and noise legs OFF (not OOS-validated). Unit returns
from the shipped simulator.

Frozen instruments/exposure: 3x-ETF partial allocation — invest f = min(L/3,1) of the sleeve in the actual 3x proxy
tracking each selected name (UPRO/TQQQ/TNA/UDOW/SOXL/TECL/FAS/LABU/MIDU/EDC), the rest in T-bills; names with no liquid
3x express 1x (the CLE frost). Margin arm: L x notional in the base ETF, borrow (L-1) at 12.5%/yr, Reg T $2,000 floor,
callable. L in {1, 1.25, 1.5, 2}. Cap: realized account maxDD <= 25%, zero liquidation.

Frozen accounts: taxable (30% on each year's net gain, loss carryforward, year-end) vs Roth (tax-free, cash IRA — no
borrowing). Whole shares; idle cash in BIL. Contributions: $7.5k/yr into the Roth ($625 every 21 sessions); no other
deposits.

Frozen structures: (A) all-taxable 1x; (B) all-taxable 3x-alloc 1.25x; (C) all-Roth 1x; (D) all-Roth 3x-alloc 1.25x;
(E) all-Roth 3x-alloc 1.5x; (F) Roth-first sequencing with the initial capital split rho in {0, 1} (rho = fraction of
starting capital that is Roth); (G) taxable margin 1.25x. Report money-weighted IRR, time-weighted %/yr, $/yr
(final - cumulative deposits), maxDD, liquidation count and final balance at $2.3k / $10k / $25k.

Judge (2016-02..2020-12): the structure with the highest after-tax IRR that keeps account maxDD <= 25% with zero
liquidation. Report the same for 2017-2019 (ex-2020) and per year, because CLE shows the IBS leverage return is
vol-regime-concentrated. Runner `research/sim/account_struct.py` -> `data/research/program/account_struct_out.txt`;
one look. Research only, no deployment.

RESULT (one look). Winner: **all-Roth / Roth-first, non-callable partial 3x-ETF allocation 1.5x** — IRR
27.5 / 24.4 / 21.8 %/yr at $2.3k / $10k / $25k (end $77,874 / $94,820 / $127,695 incl. $36,875
contributions), realized exposure 1.47x, judge-window strategy maxDD −20.8 to −21.3%, zero liquidation.
Stress gate (worst strategy maxDD across 2016-20, ex-2020, **2022 bear**, in-sample 2021-26, reject if
< −25%): 1.5x partial-3x **−24.1% (PASS, narrow)**; 2.0x −32% REJECT; margin 1.5x −28.1% REJECT; margin
1.25x −23.5% marginal. The **2022 bear is the separator**: partial-3x 1.5x −11.8% (half the capital is
T-bills, 3x leg not borrowed) vs margin 1.5x −27.8% and synthetic full 1.5x −29.0%. 3x-ETF beats the
callable margin twin at equal L on both return and risk (1.25x taxable: 17.0%/−17.1% vs 15.5%/−20.4%).
Tax-free Roth vs taxable 1x = +4.7/+4.2/+3.7pp; Roth-first sequencing with the starting capital stuck
taxable is within 0.3-2.5pp of all-Roth. Ex-2020 the same arms are 5-9% IRR, so the dollars are carried by
the $36,875 of forced Roth contributions, not the alpha; the 1.5x pass is narrow and CLE-attack's
whole-share path shows −27.7% for the same definition, so **1.25x is the prudent deployment cap**. **VERDICT:
PROMISING (structure only).** No deployment; a live 3x-ETF IBS mode would be a new switch needing a registry
entry, shadow and kill rule. Details: `research/drafts/study_acc_account_structure.md`.

DECISION (user, 2026-10-05): **accepted, structure only, no deployment; do not ship a live 3x-ETF IBS mode.**
(a) move IBS into the Roth and (b) sequence all $7.5k/yr Roth-first are **manual account actions, not bot
changes**; (c) non-callable partial-3x is the right form but **cap at 1.25x** (1.5x is a narrow in-sample
pass; CLE-attack whole-share −27.7%). Recorded caveat: the judge-window dollars are the $36,875 of forced
Roth contributions plus a 2020-vol regime (ex-2020 arms 5-9%), a structure/deposit result, not new alpha.

## Amendment — Study BSPD: bond-SPDR premium/discount and creation-flow reversion (pre-register; 1 judged, N 834 -> 835)
Pre-registered before outcomes; runner `research/sim/bond_spdr_flow.py` -> `data/research/program/bond_spdr_out.txt`.
Mechanism: illiquid bond ETFs (AP arbitrage slow) may mean-revert premium/discount and creation flow. Universe
JNK/SJNK/SPSB/SPIB/SPLB, SSGA navhist + raw Yahoo closes (never adjclose), pooled 2007-12..2026-10. H1: long
most-discounted quintile, h=1/5; H2: long top-creation quintile, 1d. Two-leg 4c cost; net_1x = gross - 8bp. Kill:
net <= 0, t < 2, < 30 events, or sign flip.

RESULT (one look). Every arm negative net of 1x and strongly negative at 2x/3x. H1 h=1 gross +0.32bp, net_1x
-7.68bp, median -7.63, hit 38.1%, clus_t -8.55, ex-top5 -8.24; H1 h=5 net_1x -9.54bp; most-discounted minus
most-premium net_1x -6.61bp; H2 net_1x -9.25bp, clus_t -11.60. Gross market-adjusted spreads ~0 (+0.32 / -1.54 /
-1.25bp): there is no reversion to harvest, the loss is the spread. Same sign in all sub-periods (2008-15 /
2016-20 / 2021-26). VERDICT: KILL. Closes the bond-SPDR arm; with SPY (Study ETC) and the broad SPDRs (Study EF)
rejected, the ETF premium/discount + creation-flow family is CLOSED. Files: `research/drafts/study_bspd.md`.

## Amendment — Study DM: dividend-month clientele premium (pre-register; 1 judged, N 835 -> 836)
Pre-registered before outcomes; runner `research/sim/dividend_month.py` -> `data/research/program/dividend_month_out.txt`.
Rule: each month M, long stocks with a regular ex-date in M, equal-weight vs the liquid non-payer benchmark, hold M;
secondary mechanism test = payer close(T-5)->close(T+5) minus SPY. Universe `data/research/night/panel.pkl`
(2020-10..2026-09, SIP total-return closes) + `dividends.json`. Panel is 2021+ only -> single regime, flagged.

RESULT (one look). Monthly long-minus-benchmark mean +66.8bp, median +20.1, hit 52%, month-clustered t +2.51,
ex-top5 +31.2; net@5bp +56.8, net@15bp +36.8, net@3x(45bp) -23.2. The mechanism test fails: payer T-5->T+5 minus
SPY mean -6.9bp, median -19.7, hit 48%, date-clustered t -0.04. The monthly +66.8bp is a size/value tilt (164
payers vs 3,081 smaller benchmark names), carried by 2021-22 (+162/+166bp), ~0 since 2023 (half2 median -10.4),
and dies at the 3x cost shock. VERDICT: KILL (gate 5: event-time mean <= 0). Files: `research/drafts/study_dm.md`.

## Amendment — Study VT-IBS: vol-proportional vs inverse-vol split of the IBS budget across simultaneous names (pre-register; 2 judged, N 836 -> 838)
Pre-registered before any outcome is read (only the count of multi-name days, 200+198 of 788 signal days, was seen);
runner `research/sim/ibs_voltilt.py` -> `research/sim/ibs_voltilt_out.txt`, note `research/drafts/study_ibs_voltilt.md`.
Theory (derived, not fitted). Established: IBS premium mu_i = k*sigma_i (ibs_xasset_scan). Growth of a day with weights
w: g = sum w_i mu_i - 0.5 sum w_i^2 sigma_i^2 (independent-names approx). Unconstrained Kelly w_i = k/sigma_i (inverse
vol). But the leg's Kelly fraction mu/sigma^2 ~ 15-20 >> 1, so the budget (sum w = 1, no leverage at $2-25k) BINDS, and
the constrained optimum is w_i = (k*sigma_i - lam)/sigma_i^2, which for a tight budget tilts toward the HIGH-vol name
(max mu per dollar), the opposite of inverse-vol. Prediction P: on days with >= 2 IBS names, w_i ~ sigma_i^g with g=+1
beats equal (g=0) beats g=-1 in mean day return and growth; Sharpe order reversed or flat.
Rule (live selection untouched via book.ibs_days = signals.momentum_top + signals.ibs_targets). sigma_i = stdev of the
last 20 close-to-close returns up to the signal close d (no look-ahead). Day return = sum w_i * (o2/o1-1) - 2*cost,
w_i = sigma_i^g / sum sigma^g, fully deployed on signal days (idle = BIL, unchanged). Arms: g=+1 (A), g=-1 (B), g=0 live.
Data: etf_daily.parquet raw prices. Judge: 2016-20 (never used to choose anything here; 2021-26 reported as the second
half, not as judge). Metric: paired day difference (arm - equal) on multi-name days, day-clustered t; plus growth
(mean log) and Sharpe on all signal days. Gates (arm A): paired mean > 0 AND t >= 2 in 2016-20, same sign in 2021-26,
ex-top-5-days > 0, median >= 0, survives 3x cost shock (1 -> 3bp/side), beats the random-weight placebo (>= 95th
pct of 1000 shuffles of the same weights across names), DSR(N=838) >= 0.5. Arm B judged symmetrically (gate on its own).
Ceiling gate (paper, before running): ~40 multi-name days/yr x paired spread x ibs_w 0.5 of account; a 5bp spread =
~1pp/yr, far under the +8pp gate. Therefore this is FALSIFICATION-ONLY: a PASS would still be a sub-1pp sizing tweak,
not worth shipping. Kill rule: any gate fails -> KILL, record in NEXT do-not-redo.

## Diagnostic amendment — Beta/alpha isolation of the current book, IBS, night, noise (NOT a variant: no N bump, no new rule, no orders)
Registered 2026-10-05 BEFORE any output of `research/sim/beta_alpha_iso.py` was read (only code of book.py, book_decomp.py,
ibs_oos.py, xb_alloc.py, tme_leverage.py and the prior outputs quoted in CLAUDE.md were read). Question: how much of the book's
historical return is alpha vs systematic exposure, and does IBS stay attractive after removing the exposures? Reuses
`book.Sim` (live signals), `book.ibs_days`, `ibs_oos._trades`, `xb_alloc.load_ohlc/load_treasury`, `book_decomp._ols`.
Nothing is tuned; no threshold, trigger, weight or leverage is chosen from outcomes.
- **Factors (window-matched to each leg's holding window; total-return adjusted bars from `data/cache/bars*`):** MKT = SPY,
  TECH = QQQ - SPY, SIZE = IWM - SPY, MOM = MTUM - SPY (MTUM is cached 2016+). TQQQ is NOT a factor (no live leg holds it;
  conviction is `shadow`); it is only a benchmark in the IBS comparison. XLK-SPY replaces QQQ-SPY as a robustness row.
  Windows: night close(d)->open(d+1); IBS open(d+1)->open(d+2); noise open(d)->close(d); TME close-to-close on T-2,T-1,T.
- **Exposure scaling:** night and IBS factors are multiplied by the day's invested fraction of equity (a flat factor on idle
  days mis-specifies the regression, the book_decomp first version). Noise has a sign-flipping exposure that is not logged, so
  it uses unscaled factors (caveat: beta ~0 by construction). Alpha = mean(y - beta.x*f) x 252 (arithmetic); t = Newey-West(5);
  weekly = non-overlapping 5-session compounded blocks x 52. Total book residual = sum of leg residuals + cash (r_cash).
- **OOS:** expanding window, fit betas on all years before Y (min 2 yrs), score alpha on year Y with those betas; report per
  year and pooled (NW t). Book legs 2021-26 (test 2023-26); IBS/TME sleeves 2017-26 (test 2019-26; 2017-20 is IBS's held-out
  window). In-sample flags: night 2021-26 FITTED; IBS 2016-20 OOS (rule chosen on 2021-23); TME 2002-15 validated, 2016+ touched.
- **A/B/C rule (frozen):** A = genuine independent alpha: pooled OOS alpha >= 60% of raw annual return AND NW t >= 2 AND alpha > 0
  in >= 75% of OOS years. C = essentially none: pooled OOS alpha <= 0, or < 20% of raw return, or |t| < 1. B = everything between
  (mostly beta + modest alpha). Applied separately to: current book, IBS sleeve, night, noise.
- **Portfolios (only validated evidence, no weight optimisation):** A current (V7 = `max_edge.BOOKS["V7"]`, 2.5bp night cost);
  B 100% IBS (live rule, fully deployed on signal days, idle BIL); C IBS + TME-A (TLT close(T-3)->close(T), XB rule: each at
  full notional, equal split when both are active, idle BIL); D = C with IBS at the 1.25x margin cap (CLE/ACC/XB decided; 12.5%
  financing on the excess; TME stays 1x per TME-L2 verdict). Whole shares by explicit loop at $1k/$3k/$5k/$10k/$25k (no
  deposits; A via `Sim.replay`). Dollars/yr = S x whole-share CAGR, pre-tax. Costs: IBS 1bp/side (3bp shock reported), TME 2bp/side.
- **IBS tests:** IBS<0.2 vs every-top-3 control vs random-day placebo (1000 draws, same day count) on 2017-20 and 2021-26 split;
  beta-adjusted (trailing-252d beta of each ETF on SPY, lagged 2 sessions); residualised on the 4 factors (betas fit on all
  control days); vs SPY/QQQ/TQQQ buy-hold and SPY scaled to IBS's utilisation. Kill/decision rule: IBS "survives" if residual
  IBS-specific premium > 0 with placebo percentile >= 95 in both windows.
- Diagnostics only; no deployment, no gate counted, no testing.py entry (no shadow/log-only switch is added).

## Clarification — Study NX (dated 2026-10-06, before `validate` or `run`; no night-rule outcome computed)

Written after the purchase and the raw download (row counts and schema only were looked at), before any eligibility
count, coverage check or night return. It settles the two wording issues LOOP_LOG flagged; neither changes the rule.
1. **Vendor/path.** The data was bought direct from sharadar.com (api.sharadar.com bulk `years=full`), not via Nasdaq
   Data Link. Same tables and legacy schema (SEP/SFP/TICKERS/ACTIONS; TICKERS.table = SEP/SFP; actions include
   delisted / bankruptcyliquidation / acquisitionof). `nx.py` reads the local store (~/data/sharadar, filled by the
   sharadar-data repo) when no raw export is present; the parsing after the read is unchanged.
2. **Delisting coverage gate.** ">= 20% of eligible-name-years ending in a delisting" is read **per distinct eligible
   name over the window** (>= 20% of names eligible at any point in 2003-15 end in a delisting by 2015-12-31), as
   `nx.py` check 9 already implements. A per-name-year share is an annual delisting rate (~5-8%) and could never reach
   20%, so that reading would fail every complete dataset; it is reported, not gated.
3. **Halted-then-resumed picks.** Kept exactly as registered: a pick with no next-session bar is scored at its
   delisting price/return, else -100%, even if bars resume later (the conservative reading). The count of such picks is
   printed; if it is material (> 1% of picks) the report also states the tier-net leg mean with those picks left out,
   as a sensitivity line that does not change the verdict.
No threshold, window, cost tier or pass-bar term is changed. N stays 809.

---

## Amendment — Study SHAR-IBS: the live IBS leg judged on untouched 2003-15 ETF data (pre-register; 1 judged rule, program N 838 -> 839)
`date`: Mon Oct 5 2026, written before any 2003-15 IBS outcome was computed. Sharadar SFP daily bars (delisted funds included) make a genuinely untouched pre-2016 window available; IBS was chosen on 2021-26 and OOS-tested on 2016-20 ETFs, so 2003-15 is new for this leg. 2008-09 is a stress subperiod.
- **Rule (frozen = live `signals.ibs_targets` + `signals.momentum_top`, run as `book.ibs_days`).** Universe = the 18 live `daily.ibs_symbols` (SPY,QQQ,IWM,DIA,MDY,XLK,XLF,XLE,XLV,XLI,XLY,XLP,XLU,XLB,SMH,XBI,EEM,EFA); an ETF absent on a date is simply not a candidate (effective count per year reported). At session d (>= 260 sessions into the panel): rank those ETFs by 12-1 momentum `close.shift(21)/close.shift(252)-1` at the last month-end strictly before d+1, keep top-3; hold each with IBS(d) = (close-low)/(high-low) < 0.2; buy at the open of d+1, sell at the open of d+2; per-name return = open(d+2)/open(d+1)-1, equal weight. Raw prices via closeunadj/close.
- **Judge window.** 2003-01-02..2015-12-31, one look. (2016-20 and 2021-26 are touched; not judged here.)
- **Costs.** `book.cost_bps("tier", raw_open, adv)` judged; "tier_hi" and 2*"tier_hi" stress. Per side.
- **Pass bar** (all at tier, standard error clustered by leg day): (1) mean net > 0 with t >= 2.0; (2) mean net > 0 in both halves 2003-09 AND 2010-15; (3) median per-trade net > 0; (4) mean net > 0 ex-best-5 leg days; (5) mean net > 0 after beta-adjusting each leg day to SPY window-matched open-to-open. FAIL if mean <= 0 or t < 1; PASS if all; else WEAK.
- **Reported, not judged:** 2000-02 and 2008-09 subperiods, per-year mean, effective universe size per year, hit rate, ex-top-5.
- Runner `research/sim/shar_ibs.py`; output `research/sim/shar_ibs_out.txt`. DSR at N 839.
- **Kill rule:** mean <= 0 or t < 1 -> FAIL: the durable-IBS claim is regime-bound to 2016+.

## Amendment — Study SHAR-CRASH: whole-book crash/stress replay, daily-bar form (pre-register; diagnostic, no judged rule; N unchanged 839)
`date`: Mon Oct 5 2026. Delisted-complete bars let the two daily-bar legs be replayed through 2000-02, 2008-09, 2011 and 2015-16. **Diagnostic: no pass/fail, no tuning, no new N.** The noise leg is excluded (no minute data).
- Legs (weights 0.5 / 0.5, live night_w/ibs_w): IBS exactly as SHAR-IBS (EQ18, top-3 momentum, IBS<0.2, open d+1 -> open d+2); night daily-bar form = live `loser_picks` at the close (close(d)/close(d-1)-1 <= -8%, IBS(d) < 0.10, raw price 5..2000, ADV$ >= 1e7, vol20 >= .60, corr dedupe .7, night_sizing crowd_n 30 cap .10), buy close(d), sell open(d+1). Daily-close proxy for the live 15:40 decision stated.
- Report per window: combined daily equal-weight book cumulative return, max drawdown, worst 5 and 20 sessions, sessions to recover the prior peak, and whether realised drawdown would have breached `signals.HALT_DRAWDOWN` (0.25) and `signals.LEVER_MAX_DD` (0.10).
- Runner `research/sim/shar_crash.py`; output `research/sim/shar_crash_out.txt`.

## Clarification — Study H-POOL, Sharadar data substitution and the SF2 2008 start (dated Mon Oct 5 2026, before any H-POOL outcome is read)
H-POOL (registered at N 796, `round1_prose.md` ~:2759; judge 2006-15) planned SEC Form 345 files + Yahoo survivor-only bars. Sharadar now supplies delisted-complete `insiders` (SF2) and `stocks`/`funds` bars. Substitutions, no threshold changed:
1. **Bars.** SEC/Yahoo bars -> Sharadar SEP/SFP raw OHLC (`closeunadj/close`), permaticker identity, delisted names retained. This removes H-POOL's survivor-only bias (an improvement, not a rule change).
2. **Events.** Form 345 sets -> SF2 (`formtype` 3/4/5 incl. RESTATED; officer/director open-market code-P purchases; `transactionvalue`, `transactiondate`, `date` = filing date). The event union (a)/(b)/(c) is unchanged.
3. **Window.** SF2 starts **2008-01-02** (not 2006q1), so the judged window becomes 2008-01-01..2015-12-31 and the two halves become 2008-10 and 2011-15. EV2's 730-day silence is evaluable only for fd >= 2010-01; the EV2-only subset is **reported, not judged**. The pass bar is otherwise unchanged: mean net > 0 with t >= 2.0 (day-clustered), positive in both halves, n >= 500, at `tier`.
4. **Data-adequacy gates become informational** (event-mapping rate and delisted coverage reported), since the survivor-only source they were written against is gone. One look.
- Runner `research/sim/hpool_sharadar.py` (new; does not edit `hpool.py`); output `research/sim/hpool_sharadar_out.txt`. N stays 796.

## Amendment — Study SHAR-SURV: survivorship audit of the 2021-26 stock-panel results (pre-register; diagnostic, no judged rule; N unchanged 839)
`date`: Mon Oct 5 2026. Diagnostic: re-run the 2021-26 night leg daily-bar form (live `loser_picks` at the close, filters as SHAR-CRASH) on (a) Sharadar delisted-complete common stocks and (b) the survivor-only 2021-26 source used for the published numbers, and report (a)-(b).
- Report mean net/trade at `tier` and flat 2.5bp, day-clustered t, ex-top-5, median, hit rate, by year, and the count of 2021-26 eligible names now delisted. If cheap, repeat for one other surviving stock-universe result (bounded to the night leg if time is short).
- Runner `research/sim/shar_surv.py`; output `research/sim/shar_surv_out.txt`.

### Correction — Study SHAR-IBS (dated 2026-10-05, adversarial check before acceptance; no re-look)
The first run reported FAIL. An independent verifier found a genuine data bug: the trade return was taken as a ratio of **raw** opens, so on 2 judged leg-days whose sell date d+2 was a split ex-date (EEM 2005-06-07, XBI 2015-09-09) it printed ~-67% instead of the split-adjusted return. Fixing the return to the split-adjusted `open` (raw still feeds tier/price/ADV) gives tier net **+4.99bp (t 1.03)**, gross +16.15bp (t 3.34), halves +11.84 / -4.69, median +10.69bp, ex-best-5 +1.84bp, beta-adj SPY resid -8.58bp (t -2.89); **2/5 checks pass**. By the registered kill rule (FAIL if mean<=0 or t<1; PASS if all; else WEAK) the verdict is **WEAK**, not FAIL. Rule, window, costs and pass bar unchanged; one look preserved. Runner/output updated in place.

### Correction — Study SHAR-CRASH (dated 2026-10-05, adversarial check before acceptance)
The night-leg daily return filtered outcomes to {open, delist_price}, dropping `delist_nopx` and `nobar_halt`, which the registered engine scores -100%. Including them: 2000-02 night +1537% -> **+1287%**, combined +310% -> **+278%**, maxDD -20.07% -> **-24.07%** (still shallower than the 0.25 halt, still trips the 0.10 lever gate). The other three windows are unchanged (no dropped outcomes). Diagnostic only; N unchanged.

## Amendment — Study SPIN-CHILD: spun-off child post-distribution drift (pre-register; 1 judged rule; program N 839 -> 840)
`date`: Tue Oct 6 2026, written before any spinoff-child outcome is computed. The daily-price-history dataset (delisted-complete daily bars 1997-12-31+, corporate-action table with spinoff/spunofffrom/spinoffdividend rows naming parent, child and ratio, distribution date = action date) makes a previously data-limited window testable: the child's first months of independent trading. Prior SHAR-EVENT work killed spin-offs at the gate on announcement-gap grounds; this is a genuinely different mechanism and window (post-distribution, not announcement).
- **Mechanism.** Parent shareholders receive child shares they did not choose; index funds and institutions that cannot hold the (usually smaller, often off-index) child must sell into the distribution. Forced sellers with a known date (distribution D); absorbers are new buyers. Predicts the child underperforms into/around D and drifts up afterwards as the overhang clears. Long-only, no borrow needed.
- **Events.** Every `spinoff` action row 1998-01-01..2026-06-30 (end early so the 60-session hold completes in panel): parent P = ticker, child C = contraticker, D = date. One row per (C, D) (dedupe).
- **Trade (frozen).** If C has a bar on D, buy C at close(D); else enter at the first available close within D..D+5 (count as late-entry, reported). Exit at close(D+60 sessions on C's calendar; if C delists/is acquired earlier, exit at its last close — scored as realised, and the delist-during-hold count is reported with a sensitivity line excluding those trades). Holds of 20 sessions reported, not judged. Universe: all categories (any child), no price/ADV filter for the primary (filters would select on the outcome's liquidity); a liquid subset (raw close(D) >= $2 AND $vol(D) >= $500k) is reported as a sensitivity line, not judged.
- **Return.** Split/dividend-adjusted (adjusted-close ratio) so distributions during the hold do not pollute; benchmark = SPY window-matched buy-hold close(D)->close(D+60) (SPY from the same panel; if SPY missing a date, use QQQ, reported). Statistic = abnormal return (child minus SPY), net of costs.
- **Costs.** Judged at 10bp/side; 25bp/side stress reported. (Small-cap children are wider than the ETF tier.)
- **Judge window.** All events 1998-2026 (single look). Halves 1998-2011 / 2012-2026 must both be > 0 net.
- **Pass bar** (SE clustered by exit month): (1) mean net abnormal > 0 with t >= 2.0; (2) both halves > 0; (3) median per-trade net abnormal > 0; (4) mean net > 0 ex-best-5 trades; (5) placebo (same children, pseudo-event 252 sessions before D, identical holds) mean |t| < 1.5 and smaller than 1/3 of the primary. FAIL if mean <= 0 or t < 1; PASS if all; else WEAK.
- **Reported, not judged:** per-year mean, 2000-02 / 2008-09 / 2020 / 2022 subperiods, hit rate, 20-session hold, parent post-spinoff drift (control: parent close(D)->close(D+60) abnormal — expected ~0), late-entry count, delist-during-hold count + sensitivity, entry-day $vol distribution and per-trade capacity, max drawdown of an equal-weight monthly-rebalanced child-drift portfolio, dollars/year at $1k/$3k/$5k/$10k/$25k under 50% capture and the liquid-subset fill cap.
- Runner `research/sim/spin_child.py`; output `research/sim/spin_child_out.txt`. DSR at N 840.
- **Kill rule:** mean <= 0 or t < 1 -> REJECTED: no harvestable distribution overhang in spun-off children.

## Amendment — Study MERG-CASH: cash-takeover target spread, long side (pre-register; 1 judged rule; program N 840 -> 841)
`date`: Tue Oct 6 2026, written before any merger-spread outcome is computed. The dataset's corporate-action table gives the cash deal price (`acquisitioncash` value = per-share cash price; verified: APGE 135.11 vs last close 135.07) and the close/delisting date, and the 8-K event table gives announcement timing (item 11 material-agreement / item 51 change-in-control filings). Combined they make a long-only cash-merger spread testable without a deals database.
- **Mechanism.** After a cash-bid announcement the target trades below the cash price (deal-break risk + time value + arb funding constraints); holders who cannot bear deal risk sell. A small long-only buyer with no funding constraint absorbs the spread and tenders/holds to close. Counterparty: risk-averse sellers; constraint: deal-break tail. No shorting, no borrow.
- **Events.** Every `acquisitioncash` action row 1998-01-01..2026-06-30 with numeric value P > 0: target T = ticker, close date C = date. Announcement proxy F = the latest 8-K filing date for T with an item-11 or item-51 code in [C-365d, C-1d] (events table); trades with no such filing are dropped (count reported). Entry at close(F+1) (first close after the filing is public); exit at T's last close on/before C (tender/close, scored realised). If T still trades 30 sessions after C (failed match), exit at C+30 and flag (count reported).
- **Trade (frozen).** Enter only if 0 < (P/close(F+1)-1) <= 30% (genuine pending-deal discount; wider = stale match, dropped and counted), raw close(F+1) >= $2, entry-day $vol >= $250k. Returns split-adjusted. Costs judged at 10bp/side, 25bp/side stress.
- **Judge window.** All events 1998-2026 (single look). Halves 1998-2011 / 2012-2026 both > 0 net.
- **Pass bar** (SE clustered by exit month): (1) mean net (raw, not benchmarked — the spread is the return; SPY window-matched abnormal also reported) > 0 with t >= 2.0; (2) both halves > 0; (3) median > 0; (4) mean > 0 ex-best-5; (5) placebo (same targets, pseudo-filing 252 sessions before F) mean |t| < 1.5 and < 1/3 of primary. FAIL if mean <= 0 or t < 1; PASS if all; else WEAK.
- **Reported, not judged:** per-year mean, stress regimes, hit rate, failed-match count + sensitivity, time-to-close distribution, break-tail (share of trades losing > 10%), capacity per trade, drawdown of a running equal-weight spread portfolio, dollars/year at $1k/$3k/$5k/$10k/$25k under 50% capture.
- Runner `research/sim/merg_cash.py`; output `research/sim/merg_cash_out.txt`. DSR at N 841.
- **Kill rule:** mean <= 0 or t < 1 -> REJECTED: the cash-merger long spread is competed away at retail scale.

## Amendment — Study DELIST-31: delisting-notice (8-K item 31) drift (pre-register; 1 judged rule; program N 841 -> 842)
`date`: Tue Oct 6 2026, written before any item-31 outcome is computed. The dataset's 8-K event table (item 31: notice of delisting / failure to satisfy a continued listing rule; 24,918 filings, 7,659 tickers, 2004-08+) plus delisted-complete bars makes the Priority-2 survivorship question directly testable: after compliance failure becomes public, do the (forced?) sellers overshoot, leaving a long bounce — or is the "return" a database illusion on names sliding to zero? Reg SHO threshold longs (Rule 203 study) lost -959bp to deadline; this is a different event (listing compliance, not settlement fails) and a different forced seller (institutions barred from holding non-compliant names), so it is not a rerun.
- **Trade (frozen).** Episodes: the first item-31 filing per ticker after >= 252 sessions without one (kills repeat-notice clustering), 2004-08-23..2026-06-30. Entry at close(F+1); exit at +60 sessions on the ticker's calendar or its last bar, whichever first (delist-during-hold scored at last close = realised; count reported with a sensitivity line excluding them). Filters: raw close(F+1) >= $1, entry-day $vol >= $100k (distressed names are low-priced; deliberately loose, reported). Returns split-adjusted; benchmark SPY window-matched; costs 10bp/side judged, 25bp stress.
- **Judge window.** All episodes 2004-2026, one look. Halves 2004-2015 / 2016-2026 both reported (pass needs both > 0).
- **Pass bar** (exit-month clustered): (1) mean net abnormal > 0, t >= 2.0; (2) both halves > 0; (3) median > 0; (4) ex-top-5 > 0; (5) placebo (same tickers, -252 sessions) |t| < 1.5 and < 1/3 of primary. FAIL if mean <= 0 or t < 1; PASS if all; else WEAK. Directional expectation (not a gate): REJECT — distressed longs lose; the value is closing the Priority-2 branch with numbers.
- **Reported, not judged:** per-year mean, delist-during-hold rate + sensitivity, break-down by first-notice vs repeat-episode, dollars/year at $1k-$25k under 50% capture (expected ~negative; reported for the record).
- Runner `research/sim/delist31.py`; output `research/sim/delist31_out.txt`. DSR at N 842.

### Correction — Study MERG-CASH (dated 2026-10-06, adversarial check before acceptance; no re-look)
The primary (+1.82% net, t 24.97, median +1.11%, both halves > 0, ex-top-5 intact) passes 4/5 registered checks but fails the fifth: the placebo mean (+2.95%) exceeds a third of the primary. Worse, the SPY window-matched abnormal is **+0.007% (t 0.02), median -0.73%**: the whole raw spread is market drift over the ~71d median hold (time value), not alpha. And the sample is completed deals only — a live buyer of announced deals eats ~5% breaks at ~-20%, a ~-1%/trade drag against +1.82%. Rule, window, costs unchanged; one look preserved. Re-classified from script verdict WEAK/PARTIAL to **PREDICTABLE BUT NOT TRADEABLE**: the spread is real in the database and ~fully explained by beta + time value + survivorship of the bid. No merger-arb variants.

## Overnight structural loop (2026-10-06) — queue gate decisions (no N)
- **(1) 13F crowding/unwind: KILLED AT THE GATE.** No named forced seller with a sharp date: 13F shows quarter-end positions 45 days late, so any liquidation is over before it is visible; the true forced seller (mutual-fund outflow fire sales, Coval-Stafford) needs fund-flow data (N-PORT/CRSP MF), not 13F. Crowding is a preference, not a constraint. No code.
- **(3) Small-cap/illiquid microstructure: KILLED AT THE GATE.** The only small-cap forced seller with a sharp date in this dataset is Russell reconstitution (index funds at the June recon close; membership proxyable from PIT market cap now). Research-priority ceiling: 1 event/yr x ~2-3% literature reversal x 100% deployable x 50% capture = ~1-1.5pp/yr at $10k, far under +8pp. A daily small-cap reversal without a forced seller is the night/IBS leg in a new costume (MISTAKES / do-not-redo). No code.
- **(4) Parent-side post-spinoff drift: KILLED AT THE GATE (PREDICTABLE BUT NOT TRADEABLE).** The -3.1% (t -3.3) parent drift is on the short side; the mandate is long-only (Roth: no shorting; taxable short needs borrow). Parent holders are not forced sellers of the parent (the child is the forced-sale object, already REJECTED in SPIN-CHILD). No long-only framing with a named counterparty exists. No code.

## Amendment — Study SPX-ELIG: S&P 500 GAAP-eligibility transition -> index-inclusion anticipation (pre-register; 1 judged rule; program N 842 -> 843)
`date`: Tue Oct 6 2026, written before any SPX-ELIG outcome is computed. Queue item (2), one PIT fundamental transition. Distinct from J1 (small caps, first profitable quarter after >= 6 losses, DEAD): this targets large non-members, where the transition unlocks a **named forced buyer with a sharp date** — S&P 500 index funds, which must buy at the close of the add's effective date. S&P's earnings rule (sum of the latest 4 quarters' GAAP earnings > 0 AND latest quarter > 0) is a hard gate; size-qualified non-members that cross it become add candidates. The add itself is in the announcement gap (dead, add. 34) — this trade is positioned *before* the announcement and sells *to* the index funds at the effective-date close.
- **Data.** Daily-price-history dataset (`~/data/sharadar`): SF1 `fundamentals` dimension ARQ (`date` = SEC filing date, `netinccmn`), `daily.marketcap`, `sp500` (quarterly membership snapshots 1998-03-31+ plus added/removed rows; `added` date = effective date, note carries the announcement), SEP bars delisted-complete, `tickers` (category, firstpricedate).
- **Universe.** SF1 tickers with category Domestic Common Stock (incl. Primary Class); not an S&P 500 member on E (PIT: latest snapshot <= E, rolled forward by added/removed rows); first price date <= E - 365d (S&P seasoning).
- **Event E.** An ARQ filing date where the S&P earnings test (sum netinccmn over the latest 4 ARQ quarters > 0 AND latest quarter > 0) is TRUE and was FALSE at the ticker's previous ARQ filing, and marketcap(E-1 session) >= the 20th percentile of S&P 500 members' marketcap on that session (PIT size-eligibility proxy; the published minimums are reported as a cross-check, not used). E in 2000-01-01..2026-03-31. One event per ticker per 252 sessions.
- **Trade (frozen).** Buy close of the first session strictly after E (no same-day filing lookahead). Exit at the earliest of: close of the S&P 500 add effective date (sell to the index funds), close of entry+126 sessions, or the last bar (delisting/acquisition scored at last close = realised; count reported). Returns split-adjusted (`close`), dividends ignored on both legs. Benchmark SPY close-to-close over the identical dates (window-matched abnormal). Costs 10bp/side judged, 25bp/side stress.
- **Placebo.** Same universe and size rule, ARQ filings where the earnings test was TRUE at that filing AND at each of the previous 4 ARQ filings (long-eligible, not transitioning), one per ticker per 252 sessions, same trade. Tests whether the *transition* (new add candidacy) matters vs. "profitable large non-member".
- **Pass bar** (SE clustered by exit month): (1) mean net abnormal > 0 with t >= 2.0; (2) both halves (E 2000-2012 / 2013-2026) > 0; (3) median net abnormal > 0; (4) ex-top-5 > 0; (5) placebo mean abnormal < 1/3 of primary; (6) 25bp stress mean > 0. FAIL if mean <= 0 or t < 1; PASS if all; else WEAK.
- **Reported, not judged:** add rate within the hold (primary vs placebo; the mechanism check), mean abnormal for added vs not-added trades, raw net mean, per-year mean, hold length, delist-during-hold count, dollars/yr at $1k/$3k/$5k/$10k/$25k under <= 50% capture (whole shares, events/yr x capital-share).
- **Kill rule:** mean <= 0 or t < 1 -> REJECTED. Directional expectation (not a gate): weak — S&P adds are discretionary and widely anticipated.
- Runner `research/sim/spx_elig.py`; output `research/sim/spx_elig_out.txt`. DSR at N 843.

### Result — Study SPX-ELIG (dated 2026-10-06, one look; adversarially checked)
472 trades / 297 tickers (18/yr, mean hold 119 sessions). Net SPY window-matched abnormal +0.61% (exit-month t 0.50), median -0.91%, hit 48.9%, ex-top-5 -0.61%; halves +1.14% / -0.05%; 25bp stress +0.31%; raw (unhedged) +4.73% = beta. Placebo (long-eligible) +1.81% t 2.44 (> primary; 2000-12 only, 2013-26 -1.05%). **Registered verdict FAIL (t < 1) -> REJECTED.** Mechanism check: add-within-hold 8.7% primary vs 10.1% placebo — the earnings transition does not raise the add probability; the 41 added trades (+16%) are the unpredictable announcement gap. Checks: no membership leakage (0 non-added primary names in the next quarterly snapshot), P20 size floor tracks the published minimums ($4.5B 2000 -> $25B 2025), no split artifacts (|ret|>100%: 4, all real moves: MRVL/TSLA/CVNA/MRNA). DSR at N 843 trivially fails. Economics ~0.6%/yr at any size ($65/yr at $10k). Do not chase the placebo's 2000-12 profitable-non-member tilt (unregistered, one half).

## Amendment — Study EXDIV-OPEN: ex-dividend open-auction under-adjustment (pre-register; 1 judged rule; program N 843 -> 844)
`date`: Tue Oct 6 2026 (golden-egg overnight loop), written before any official-auction outcome is computed.
**Disclosure (selection):** an exploratory Sharadar screen (1998-2026, all periods, so NOTHING on Sharadar is untouched)
found that on ex-dividend nights liquid high-yield stocks earn a total-return close->open excess over their own placebo
nights of +9bp (2020+) to +50bp (1998-2009) for yield >= 0.6%, with the ex-day session (open->close) giving it back. The
open price in daily vendor data may not be an executable auction price, so this study is an **execution verification on
official SIP cross prints**, not an out-of-sample test. True OOS = forward shadow only.
- **Mechanism (stated, falsifiable).** On the ex-date resting sell limit orders are not reduced by the dividend (FINRA
  5330 / exchange practice reduces only buy limits and sell stops), and tax-motivated holders who sold cum-dividend
  and buyers who waited for the ex-date meet at the opening cross; the open under-adjusts and the session completes the
  drop. Counterparty: ex-date opening buyers / cum-date tax sellers. Small accounts fill at the cross with no spread.
- **Data.** Alpaca `/v2/stocks/auctions` (SIP) official cross prints (largest-size print = the cross), 2021-01..2026-10,
  for the 400 most frequent liquid (price >= $5, 3m $ADV >= $2M) yield >= 0.6% ex-date tickers (selection by event
  count, not outcome; `exdiv_auction_fetch.py`). Ex-dates and dividend size from Sharadar `actions`; yield =
  dividend / raw close(T-1).
- **Trade (frozen).** Buy the closing cross on T-1, sell the opening cross on T (ex-date); P&L = (open_T + div)/close_{T-1} - 1.
  Judged excess = that minus the same ticker's mean official-auction overnight return on nights T-35..T-5 (placebo).
  Events with yield >= 0.6%.
- **Pass bar** (SE clustered by ex-date): (1) mean excess > 0, t >= 2.0; (2) halves 2021-23 / 2024-26 both > 0;
  (3) median > 0; (4) ex-top-5 > 0; (5) mean excess > 5bp (= 2x the 2.5bp/side research cost, a 2x cost shock);
  (6) SPY-overnight-adjusted (official SPY crosses) mean > 0. FAIL if mean <= 0 or t < 1; PASS if all; else WEAK.
- **Reported, not judged:** yield buckets, by-security-type split, cross size vs a $10k/$25k ticket, events per
  session (deployable capital), Sharadar open vs official cross gap, dollars/yr at $1k/$5k/$10k/$25k at <= 50% capture.
- **Kill rule:** FAIL -> the vendor-open effect is a data artifact; record and stop. Runner `research/sim/exdiv_open.py`.
- **Added arms (same family, registered before their official-auction data is fetched; N 844 -> 846):** (B) forward-split
  ex-date (Sharadar `split` value > 1), (C) spin-off parent ex-date (`spinoff` row date). Exploratory Sharadar screen
  (all periods touched): overnight excess vs own placebo +71bp (B, 2020+ +78bp, n 386 liquid) and +151bp (C, outlier-
  prone), each with a negative ex-day session. Same trade (close cross T-1 -> open cross T; raw auction prices
  converted by the split ratio; for C the child's value is NOT added, so C is judged only as "does the parent open
  print above the parent's own close-to-close path"), same placebo and pass bar, judged on official crosses 2021-26.

### Result — Study EXDIV-OPEN (2026-10-06, one look on official SIP crosses 2021-26)
- **A ex-dividend: FAIL.** n 13,199: excess vs own placebo -5.9bp (t -1.71; the placebo mean is inflated by split
  outliers), robust median +3.9bp / trimmed +2.6bp; SPY-adj -7.5bp. Vendor (Sharadar) overnight on the same events
  +14.0bp vs official +13.3bp: **the vendor open IS the official cross; the earlier "+9bp" was the names' normal
  overnight premium.** Ex-dividend capture is dead again (= Round 22 AZ), now on 2021-26 official crosses.
- **B forward split: WEAK** (t 1.76 < 2; halves, median, ex-top-5, >5bp, SPY-adj all pass). n 239: excess +42.7bp,
  median +17.6bp; raw-SPY +56.6bp t 2.43, median +19.6bp. Vendor vs official median |diff| 0.1bp.
- **C spin-off parent: WEAK** (n 88, +197bp, t 1.16, ex-top-5 negative: outlier-carried).

## Amendment — Study SPLIT-NIGHT: post-split retail open pressure, multi-night (pre-register; 1 judged rule; N 846 -> 847)
`date`: Tue Oct 6 2026, written before official crosses for nights T+1..T+4 are fetched.
**Disclosure (selection):** chosen after the Sharadar 1998-2026 date-shift profile of forward-split ex-dates
(common stock, raw px >= $5, $vol >= $1M; n 3,405): overnight raw-SPY T-5..T-1 +10..+15bp, **T+0 +94bp (t 10.7,
median +43), T+1 +46, T+2 +26, T+3 +26, T+4 +20, T+5 +16**, every post-split session -20..-33bp. All Sharadar years
are touched; official 2021-26 crosses for T+1..T+4 are new data in a touched period (execution verification, not OOS).
- **Mechanism (falsifiable).** A forward split lowers the per-share price; retail investors (price-level/"affordable"
  attention, fractional-share-naive) buy at the open with market orders for several sessions; opening crosses clear
  above fair value and the session reverts (Berkman-Koch-Tuttle-Zhang 2012 overnight/intraday attention pattern).
  Counterparty: retail open buyers. Prediction: the excess decays with nights since ex-date; reverse splits show the
  opposite sign (screen: -100bp); funds/ETFs weaker (screen +28bp).
- **Rule (frozen).** Each session D, hold overnight (buy closing cross D, sell opening cross D+1) an equal-weight basket
  of every common stock (Sharadar `src` stocks, ticker regex [A-Z]{1,5}) whose forward-split ex-date (`split` value > 1)
  E satisfies E <= D+1 <= E+4 sessions (nights T+0..T+4), with raw close(E-1) >= $5 and close(E-1)*volume >= $1M.
  Sleeve fully in cash on nights with no name.
- **Judge (official SIP crosses, 2021-01..2026-09, `split_night_fetch.py`).** Per-name-night raw minus SPY official
  overnight; SE clustered by night. Pass: (1) mean > 0, t >= 2; (2) halves 2021-23 / 2024-26 both > 0; (3) median > 0;
  (4) ex-top-5 names > 0; (5) at 5bp/side cost mean > 0; (6) nights T+1..T+4 alone (excluding T+0) mean > 0
  (the decay prediction). FAIL if mean <= 0 or t < 1; PASS if all; else WEAK.
- **Reported, not judged:** per-night-offset profile, per-year, basket nights/yr, sleeve daily-return series, maxDD,
  Sharpe, SPY overnight beta, correlation with the live night leg's nights, open-cross $ size, $/yr at $1k-$25k at
  50% capture. Vendor-based 1998-2026 sleeve reported as the long-history context (touched).
- **Kill rule:** FAIL -> record; the split effect is a single-night curiosity at best.

### Result — Study SPLIT-NIGHT (2026-10-06, one look on official SIP crosses 2021-26): WEAK (multi-night basket dead)
159 events / 870 name-nights (2 split-date/ratio mismatches with the tape — BRIA 2024-11-27, MBC 2022-12-15, |T+0| >
100% — dropped as vendor data errors). Basket raw-SPY +17.4bp t 1.42, **median -1.2bp**, ex-top-5 +1.7bp, 5bp/side
+7.4bp, **T+1..T+4 only -8.1bp (decay prediction FAILS: T+2 -30, T+4 -35bp)**. Checks: t no, halves yes, median no,
ex-top-5 yes, cost yes, T+1..4 no -> WEAK. Per offset: **T+0 n 174 +119.5bp t 2.42 median +17.4 hit 57% ex-top5
+31.3**; T+1 +29.2 (median +26.6); T+2..T+4 negative. The edge, if any, is the ex-date night alone (= EXDIV-OPEN arm B,
common stocks). Open cross median $0.55M, p10 $38k.

## Amendment — Study ATTN-OPEN: scheduled retail-attention events, ex-date-night open pressure (pre-register; N 847 -> 849)
`date`: Tue Oct 6 2026, written before official crosses for these events are fetched.
**Disclosure:** chosen after a Sharadar 1998-2026 screen (touched) of corporate-identity events with the split-night
signature (T+0 overnight up, session down): de-SPAC first day (`spacmerger`) T+0 overnight-SPY 2013+ +264bp / median
+86 (n 377), T+1 +135/+53; ticker change (`tickerchangeto`) T+0 2013+ +137/+19 (n 1106); name change +62/+12; OTC
uplisting +30/+19 (not judged: T-1 is an OTC price with no closing cross, not executable at an auction).
- **Mechanism.** Same as SPLIT-NIGHT T+0: a salient, scheduled identity event (new name/ticker, SPAC becomes an
  operating company, lower share price) draws retail market buys into the next opening cross; the session reverts.
  Counterparty: retail open buyers. Falsifier: the official opening cross is not above the prior closing cross.
- **Rule (frozen), per arm.** Buy the exchange closing cross on E-1 (old symbol if the symbol changes), sell the
  opening cross on E (the action date, first session under the new identity). Raw close(E-1) >= $5 (de-SPAC: >= $5 is
  the trust floor area, kept), $vol(E-1) >= $1M on the vendor series. Arms: **D de-SPAC**, **T ticker change** (excl.
  de-SPAC dates and preferred/unit tickers; regex [A-Z]{1,5}).
- **Judge (official SIP crosses 2021-01..2026-09, `attn_open_fetch.py`)**, per arm, raw minus SPY official overnight,
  clustered by date: (1) mean > 0, t >= 2; (2) halves 2021-23 / 2024-26 > 0; (3) median > 0; (4) ex-top-5 > 0;
  (5) 5bp/side mean > 0. FAIL if mean <= 0 or t < 1; PASS if all; else WEAK. Reported: T+1 night, cross size, by year.

### Result — Study ATTN-OPEN (2026-10-06, one look on official SIP crosses 2021-26)
- **T ticker change: FAIL.** n 387: raw-SPY -67.0bp (t -1.10), median -24.0bp, both halves negative. The vendor screen
  (+137/+19bp) was an artifact of stitching old/new symbol histories (vendor and tape disagree here; for splits they agree
  to 0.1bp).
- **D de-SPAC: WEAK, untradeable.** n 261: +159bp (t 1.32), median +99bp, ex-top-5 +15bp, but 143/261 events are the
  2021 SPAC bubble (median +210) and 2023 is -1361bp median; opening cross median **$50k** (p10 $4k). KILL as a sleeve.
- Spin-off child first nights (vendor screen, no N): overnight medians -23..-34bp on nights 1-4 — forced parent-holder
  selling shows up at the open (short side only). Consistent with the open-pressure mechanism; not tradeable long.

## Amendment — Study SPLIT-T0: forward-split ex-date night, official crosses 2016-2020 (pre-register; 1 judged rule; N 849 -> 850)
`date`: Tue Oct 6 2026, written before any 2016-2020 official cross is fetched. Rule frozen as SPLIT-NIGHT's T+0 night
(buy closing cross E-1, sell opening cross E; common stock, raw close(E-1) >= $5, $vol(E-1) >= $1M; |T+0| > 100% =
vendor/tape mismatch, dropped). Judge on Alpaca official SIP crosses 2016-01..2020-12 (vendor years touched: execution
verification on an earlier window, not OOS). Pass: (1) raw-SPY mean > 0, t >= 2; (2) halves 2016-18 / 2019-20 > 0;
(3) median > 0; (4) ex-top-5 > 0; (5) 5bp/side mean > 0. FAIL if mean <= 0 or t < 1. Runner `split_t0_1620.py`.

### Result — Study SPLIT-T0 (2026-10-06, one look on official SIP crosses 2016-2020): PASS
Registered rule: n 147, raw-SPY +203.5bp t 2.17, median +57.5bp, hit 69%, ex-top-5 +43.4bp, halves +242.6 / +99.1,
5bp/side +193.5 -> all 5 checks pass. **Adversarial fix (disclosed, not a re-look of the rule):** two events are not
splits — DELL 2018-12-28 (DVMT reverse merger, +90%) and UAA 2016-04-08 (Class C share distribution, +99%) — and slip
under the registered |T+0| > 100% mismatch filter; without them n 145 **+77.1bp t 2.99, median +56.5, ex-top-5 +38.4,
halves +68.7 / +99.1** (still PASS). By year (median): 2016 +79, 2017 +60, 2018 +49, 2019 +8, 2020 +56.
Caveat: Alpaca symbols are current, so names renamed/removed since 2016 are missing (survivor tilt in the fetch).
Combined official 2016-2026 ~320 events: median +57bp (2016-20) -> +17bp (2021-26); the effect is real at the auction
and shrinking. Status: STRONG CANDIDATE; next is a forward shadow (no deployment).

## Amendment — Study SPIN-T0: spin-off parent ex-date night with the child's actual open (pre-register; N 850 -> 851)
`date`: Tue Oct 6 2026, written before official child crosses are fetched. Vendor screen (touched): parent close E-1 ->
parent open E + ratio x child open E (Sharadar `spinoff` value = child shares per parent share), raw-SPY: n 409 mean
+43bp t 1.24, **median +70bp** (2013+ median +60). Mechanism: same price-drop salience as SPLIT-T0 (parent's price
falls at E) plus the child's first regular-way open. Rule: buy parent closing cross E-1, sell parent opening cross E
and the ratio's child shares at the child's opening cross E; parent raw close >= $5, $vol >= $1M; |P&L| > 50% dropped as
mismatch. Judge: official SIP crosses 2021-01..2026-09; checks as SPLIT-T0 (t >= 2, halves 2021-23/2024-26 > 0,
median > 0, ex-top-5 > 0, 5bp/side > 0). **Execution caveat (judged separately, not by data):** the child shares must be
credited and sellable at the E open; brokers sometimes credit spin shares late.

### Result — Study SPIN-T0 (2026-10-06, one look on official SIP crosses 2021-26): PASS (small n, execution caveat)
n 78: raw-SPY +83.0bp t 2.03, median +53.9bp, hit 60%, ex-top-5 +17.5bp, halves +95.8 / +65.6, 5bp/side > 0 -> all 5
checks pass. By year median: 2021 +42, 2022 +141, 2023 +31, 2024 +140, 2025 -10, 2026 +16. Child open cross median
$0.22M. Same family as SPLIT-T0 (price drop on a scheduled date -> rich open). Unverified operational risk: child shares
credited and sellable at the E open.

## Amendment — Study LETF-NIGHT: single-stock leveraged-ETF close rebalancing -> overnight reversal (forward-only registration; N 851 -> 852)
`date`: Tue Oct 6 2026. **No untouched history exists** (single-stock LETFs reach > 2% of underlying $volume only in
2024+); the 2023-26 exploratory read below is in-sample. This entry freezes the rule for a FORWARD test only.
- **Mechanism.** A daily-reset LETF with leverage L must trade L(L-1) x AUM x r_day of the underlying at the close
  (long and inverse funds both buy on up days, sell on down days). Close-auction pressure in the day's direction; the
  next open reverts. Counterparty: the LETF's swap/hedge desk forced into the closing cross. Prediction: reversal grows
  with LETF $vol share and with |r|; flat days show nothing; the mirror (up days -> negative overnight).
- **Exploratory evidence (2023-26, touched):** 520 single-stock LETFs over 278 underlyings (fund names parsed). Big
  down day (r <= -5%), LETF 20d $vol share (lagged) > 2%: n 2010, overnight raw-SPY mean +48bp t 2.38, median +39, hit
  56%, 81 names, ex-top-5 names median +32; same-period vol-matched no-LETF names ~0..+9; within the same 91 names
  pre-LETF median +4 vs post +39 at equal vol; adds beyond the night-leg filters (night-like days +109 vs +28 median;
  -5..-8% +18 vs 0; <= -8% with IBS >= .1 +66 vs +10). By |r|: -3..-5% nothing; asymmetric: r >= +8% -> -32bp. Flat
  days -10bp (no retail overnight premium). Sleeve at 2.5bp/side: 2024 +62%, 2025 +61%, 2026 YTD +28% (319 event days).
- **Analog check (2010-20, untouched, NOT a valid falsifier):** sector LETF share vs the underlying sector ETF's
  overnight after |z| >= 2 days: nothing (SOXX/SOXL share 119%: ~0bp). The sector flow lands on constituents via swap
  hedges, not on the ETF; reported, not judged.
- **Forward rule (frozen):** each session, common stocks with raw close >= $5, $vol >= $10M, close-to-close r <= -5%,
  and prior-day 20d (sum of single-stock LETF $vol on the name) / (name's 20d $vol) > 2%: buy the closing cross, sell
  the next opening cross; equal weight. Gate: 120 forward event days. Pass: mean > 15bp/event-day net of 2.5bp/side,
  median > 0, the no-LETF control (same r and price/volume screens, LETF share = 0) lower by >= 15bp. Kill: mean <= 0 or
  control not lower. Overlap with the live night leg reported (shared nights).
- Not deployed (user instruction 2026-10-06: discovery only, no deployment). A shadow needs the user's OK.
- **LETF-NIGHT execution check (2026-10-06, official SIP crosses 2024-26, same events):** n 2009, raw-SPY +43.9bp t 2.17,
  median +32.0bp (vendor +48.4 / +39.0; corr 0.990). By year (mean/median): 2024 +112/+80, 2025 +11/+34, 2026 +55/+24.
  Executable at the auctions; still in-sample. Status: STRONG CANDIDATE (forward test needs the user's OK).
- **LETF-NIGHT adversarial correction (2026-10-06, 2024-26, same events): about half is beta.** LETF names' median 120d
  daily beta 2.9 vs 1.6 for no-LETF big-down names; the raw-SPY excess carries (beta-1) x the overnight market rebound
  after down days. Beta-adjusted overnight (r <= -5%): LETF median +23bp (mean +36, t 2.6) vs no-LETF +7 (+16);
  market-down days +27 vs +8; flat-market days +13 vs +7 (raw-SPY +13 vs +10: no edge on flat days); within beta
  quartiles LETF beats no-LETF by 6-25bp. **Status downgraded to PROMISING**: the rebalancing-specific edge is ~+15-20bp
  per event, concentrated on market-down days; the rest is levered overnight market rebound.

## Amendment — Study CLOSE-DISLOC: passive limit-on-close liquidity to closing-cross dislocations (pre-register; N 852 -> 853)
`date`: Tue Oct 6 2026, written before any minute bar or cross for this universe is read (new, never-examined data).
- **Mechanism.** Price-insensitive MOC flow (index/LETF/fund rebalancing, retail MOC) sometimes clears the closing cross
  well away from the pre-close price; the next open reverts. A resting limit-on-close (LOC) buy below the pre-close price
  fills ONLY when the cross dislocates down, i.e. it sells liquidity exactly to forced sellers. Counterparty: MOC sellers.
- **Data.** Alpaca free SIP: 1-minute bars 15:50-15:56 ET + official open/close crosses (`close_disloc_fetch.py`);
  200 common stocks with 20d $vol $10-200M and raw close >= $10 on 2024-06-28 (chosen before the window);
  window 2024-07-01..2026-10-01.
- **Rule (frozen).** Pre-close price p = close of the 15:55 ET minute bar (last bar <= 15:55 if missing). LOC buy limit
  L = p x (1 - k), primary k = 1%. Fill if the official closing cross C <= L, at C. Exit at the next official opening
  cross. P&L = O/C - 1 minus SPY's official overnight; equal weight per fill.
- **Pass bar** (SE clustered by date): (1) mean > 0, t >= 2; (2) halves 2024-07..2025-06 / 2025-07..2026-09 > 0;
  (3) median > 0; (4) ex-top-5 > 0; (5) mean > 10bp (2x a 2.5bp/side cost; LOC in the cross pays no spread).
  FAIL if mean <= 0 or t < 1. Reported: k = 0.5% / 2%, fills/day, adverse-selection check (fills vs a matched
  no-dislocation control: same names' overnight when C is within 0.2% of p), next-day session, cross $ size.

### Result — Study CLOSE-DISLOC (2026-10-06, one look, new minute data): WEAK (no breadth)
198 names, 566 sessions; closing cross vs 15:55 price sd 21bp. Control (|dev| <= 0.2%) overnight -0.8bp. **k = 1%:
73 fills (0.13/session), +105.7bp t 1.76, median +29.4, ex-top-5 -11.2, halves -77.2 / +153.0 -> WEAK** (outlier-carried).
k = 0.5%: 1422 fills, +9.2bp t 1.06. Mirror (cross >= +1% above 15:55) -17.8bp. Mid-cap closing crosses absorb MOC
flow efficiently; dislocations big enough to pay are rare and lumpy. KILL as a sleeve.

## Result — CLOSE-DISLOC (judged 2026-10-06; N stays 853)
Data complete (window restored through 2026-10-01; 566 sessions, 107k name-days). **WEAK / kill.** k=1% (the
registered arm): fills 73, mean +105.7bp but **t 1.76 < 2**, halves -77.2 / +153.0 (flip), **ex-top-5 -11.2bp**
(carried by ~5 events), next-session +77.7bp (the "reversion" is the day AFTER the open, untradable end-first).
k=0.5% has fills (1422, 2.51/session) but +9.2bp t 1.06, below the >10bp bar. Mirror side (cross >= +1% above
15:55): -17.8bp — you must be the one SELLING into that dislocated cross
to collect; the collectible side is the dislocation event itself, not the open. Control (|dev|<=0.2%): -0.8bp — no conditional-alpha drift in
this universe at all. Final status: **REJECTED** (a >1% closing-cross dislocation is rare and its post-open drift
is tail-carried; do not re-tune k).

## Amendment — Study TL-JAN: tax-loss selling -> January reversal, delisted-complete (pre-register; N 853 -> 854)
`date`: Tue Oct 6 2026, written before any 1998-2025 December return for this cross-section is read.
Origin: RESURRECTION track (research/drafts/resurrection_inventory_2026-10-06.md, RES-1). The design is the
one frozen in research/drafts/seasonal_memo_2026-10-04.md (B.5), which was drafted but never run; the
resurrection upgrade permitted by the Sharadar panel is 28 formation years (1998-2025; Judge windows the
memo never saw: 1998-2015) instead of the memo's 10 Alpaca years, and a delisted-complete cross-section.
- **Mechanism (unchanged):** the statutory Dec-31 loss-harvest deadline makes taxable holders sell YTD losers
  into year-end; wash-sale rules stop immediate repurchase; sellers are price-insensitive and small/illiquid
  names bear the concession. The pressure lifts in January.
- **Universe:** common stocks (kbd src=0, alpha ticker), raw close >= $3 and 20d $ADV >= $1M at formation
  (nominal thresholds kept, as drafted; they also make the whole-share constraint realistic in the 1990s era).
- **Formation:** close of the 7th-last December session; rank by YTD (prior-year-end close -> formation, with
  dividend factors); take the worst 50 with YTD <= -30% AND December (start of Dec -> formation) daily mean
  $vol >= 1.0x the prior-6-month (Jun-Nov) daily mean $vol.
- **Trade:** equal weight, buy the close of the 5th-last December session, sell the close of the 10th January
  session (next year). One formation per year; all formation years 1998-2025 judged ONCE, no splits, no design
  changes after the first output line.
- **Benchmark:** IWM over the same window (Sharadar SFP, has a dividend factor); IWM starts 2000-05 so
  1998-00 events are ALSO reported vs SPY-equivalents (SPY starts 93-01) and raw; pre-IWM years are labelled
  and excluded from the headline judgement if they disagree.
- **Costs:** 25bp/side floor per name; also report 2x (the registered 2x shock). No Corwin-Schultz per-name
  spread estimate: the floor is the conservative side of the memo's spec.
- **Kill criteria (frozen, from the memo, adapted to 28 events):** mean net abnormal (vs IWM) < +1%/event; or
  fewer than 60% of pre-2016 judged years positive; or ex-best-single-year mean <= 0; or a June placebo
  (same rule, formation mid-June, sell mid-July) nets as much; or the effect is not monotone in YTD-loss
  terciles; or 2x costs flips the mean negative.
- **Pass bar:** mean net >= +1%/event, >= 60% years positive, ex-best-year > 0, placebo small, monotone.
- **Accounting:** the memo's ceiling is ~+1-2pp/yr at full deployment; this is a December sleeve, never a
  book. Multiple-testing: 1 judged rule (N 854).

## Result — TL-JAN (judged 2026-10-06; N stays 854)
28 formation years attempted (1998-2025; 1998-99 dropped: no IWM benchmark yet), delisted-complete Sharadar
panel, 468 fills, ~18 picks/yr (the px>=3/ADV>=$1M/YTD<=-30%/Dec-footprint gates bite hard), trunc 0%.
- [cost 25bp/side] mean +2.94%/event-year, **t(yr) 1.91**, median-year +2.87%, years+ 69%, ex-best-year +2.07%;
  [2x cost] +2.44% t 1.58 — still positive, fine.
- **June placebo: -0.31%/yr (42%+), median-yr -2.54%** — the December conditioning is real, not seasonal-lift.
- **Era split: 1998-2015 +4.45%/event t 2.13 (67%+) vs 2016-2025 +0.53% t 0.30** — the modern decade is dead.
- Monotonicity in YTD loss **FAILS**: pooled terciles +2.66 / +1.94 / +3.18 (worst, middle, least).
- Clustered-outlier audit: 1998-2015 ex-2010/2011/2012 = **+1.41% t 0.88** — the historical era's positive
  mean is three adjacent years.
- Year list (net): 2010 +15.5, 2011 +12.7, 2012 +24.7(!) vs 2013 -2.0, 2014 -8.1, 2015 -10.6, 2019 -9.4,
  2021 -6.1, 2024 -4.2, 2025 -0.5.
**Verdict: REJECTED AGAIN.** The resurrection test (insufficient power -> 28 events) was a fair retry and the
mechanism still fails: not monotone in the loss depth it is named for, and its only positive era is
2010-2012 + high-vol hoses (2009). Ceiling was ≤ +1-2pp/yr even if alive. No December sleeve. Status:
**PERMANENTLY DEAD** (December losers; the June placebo ex-relief result confirms seasonal conditioning once
existed pre-2016, which is history, not tradable alpha). Do not re-open without a *new measurement* of the
tax-loss footprint (e.g. actual sell-side imbalance), not another prices-only panel.

## Amendment — Study F13F-CAP: forced trim of concentrated fund holdings after a share-count shrink (pre-register; N 854 -> 856)
`date`: Tue Oct 6 2026, written after building the 13F STATE panel (ownership x implied shares outstanding,
data/research/f13f/agg.parquet, common shares only, quarters 2013-06..2026-06) and INSPECTING ONLY state
counts — no returns have been loaded for this family. NEW FRONTIER track (domain jump: regulatory-mandated
positioning; the program has never used 13F data at all).
- **Mechanism.** A diversified registered investment company may not own >10% of an issuer's outstanding
  voting shares (1940 Act §5(d) "diversified"; most active mutual funds apply far lower caps). When an
  issuer shrinks its share count (buybacks, exchange offers, tender-driven retirements), a fund whose
  position crosses the cap is a RULE-BOUND seller: it must trim regardless of price, in a small copy
  (implied shares ≤ 13F scale ≈ mostly small caps). The 13F snapshot makes the constraint observable
  one quarter after it binds. Counterparty: the diversified fund (forced); the flow is gradual
  (quarterly rebalance calendar, haircut small caps expensive to trade), which is why arbitrage does not
  remove it (shorting illiquid small caps is expensive and the constraint is per-fund, thousands of funds,
  each a slow small order).
- **Two judged arms (N 854 -> 855 and 855 -> 856):**
  1. **F13C-TRIM (short arm).** Set: common stocks with mxp >= 9.5% at reported quarter Q (largest single
     filer's units vs marketcap-implied shares outstanding) AND implied shares outstanding down <= -5%
     Q-1 -> Q. Entry: the first trading session AFTER the next 13F filing deadline for Q
     (04-30Q->May 15; 06-30Q->Aug 14; 09-30Q->Nov 14; 12-31Q->Feb 15, next session). Sell short; hedge with
     SPY over the same window (P&L = -(raw - SPY)); exit 63 sessions after entry. n: ~1,200 events.
  2. **F13C-FREED (long arm).** Names in the pressure set at Q-1 whose max-holder share has fallen <= 7%
     at Q (the mandated unwind appears complete in the NEXT filing). Buy at the first session after the
     next deadline, exit 63 sessions later, same benchmark.
- **Judgement (frozen):** date-clustered t on the pooled abnormal; halves (2013-2019 / 2020-2026) both
  non-negative; median > 0; ex-top-5 by NAME and by DATE; placebo = same dsh <= -5% set but mxp < 5%
  (shrink without the cap) must be lower or equal; 50bp/side headline, 100bp/side + no-hedge shown.
- **Kill:** trim arm net mean <= 0 at 2x cost, or placebo as good, or halves sign-disagree. Freed arm:
  mean >= 1%/event and placebo lower, else dead.
- **Honest ceiling (priority gate):** ~40-120 events/quarter x (overhang 0.5-2% per name over the window)
  x sleeve ~30% of account -> ~+2-4pp/yr at $10k IF it works; below the +8pp discovery gate, run anyway
  because the family (13F-state) is virgin and this de-blocks or kills it for pennies of compute.

## Result — F13F-CAP (judged 2026-10-06; N stays 856)
Panel: 674k->432k name-quarters (common-only), 53 filing deadlines 2014-2026, SPY-hedged 63-session holds,
25bp+25bp legs at 50bp/side (100bp stress shown), px >= $3, reverse-split contamination measured at ~3% of
the press set (split actions overlap), entry on the session AFTER each filing deadline.
- **F13C-TRIM (short arm, primary): KILL.** mean +1.31%/window gross-SPY but **t 0.80**; 2x cost +0.31% t
  0.19; **ex-top-5-names -0.03%** (the positive is 5 named events); halves both ~+1.3 but nothing survives
  cluster. The rule-bound trim flow leaves no stable short-side footprint in daily bars.
- **F13C-FREED (long arm): KILL.** -12.2%/window, t -3.2, both halves negative — names whose unwound
  position prints as complete keep FALLING (their problem is not the unwind).
- **Placebo / dilution observation (diagnostic, not judged):** names with implied shares down >= 5%/q and
  mxp < 5% lose ~4.7-5.7% per quarter vs SPY in BOTH halves (t -2.3/-2.8 pooled, 25-28% days+): heavy
  implied-shrink micro caps are a persistent drag — a risk-SCREEN candidate (avoid them in long sleeves),
  not an alpha arm; recorded, forward watch only.
13F-state family v1: **KILL both judged arms**. The family is not foreclosed (the participant-typed max
holder — actual diversified mutual funds, not all filers — was never tested; would need a new registration);
recorded as a v2 spec only, judged forward/no-run tonight. Do not re-run the as-registered rules.

## Amendment — Study F13C-CAP v2: participant-typed forced trim (pre-register; N 856 -> 857)
`date`: Tue Oct 6 2026, before any fund-typed return is read. The v1 rule's concentration state measured
ALL 13F filers; hedge/PE/partnership filers are NOT bound by RIC diversification caps, so v1's "press" set
grossly understates the forced-flow mechanism. v2 replaces the state variable only — everything else
unchanged (deadline entry, 63-session hold, SPY hedge, 50/100bp/side costs, kill/pass trees identical).
- **State:** mfx = the largest single FUND-NAME-flavored filer (mutual fund family regex, f13f_agg.py)
  as % of marketcap-implied common shares outstanding; press = (mfx >= 9.5%) AND dsh <= -5%/q.
- **F13C-TRIM2 (short) and F13C-FREED2 (long)** judged with the v1 gates; in addition, for TRIM2 the
  no-hedge raw loss of the short leg is shown (borrow-cost honesty).

## Study PCAL — negative-control calibration of the program's own PASS machinery (diagnostic, no N; third-robot session, 2026-10-06)

**Question.** Every judged candidate in this program (N≈856) clears one standard bar on an
overnight-reversal-shape rule on delisted-complete daily bars: day-clustered t ≥ 2, both halves
net-positive, median trade net-positive, ex-top-5 net-positive. The bar's FALSE-PASS rate has never
been measured empirically (per-study DSR is analytic and exchangeability-based). This study does not
judge a candidate; it calibrates the machinery that judges them.

**Template (exact NX night-leg machinery).** Candidate day T: c/c_prev-1 <= -0.08, IBS < 0.10, price
$5-2000 (raw), eligible pos>=20, cu_prev >= $5, adv >= $10M; dedupe corr <= 0.7; night_sizing
(vol_min 0.60, crowd 30, name cap 10%); overnight = o_next/c - 1 (+div/cu if ex = T+1); delisting by
actions price else -1.0; no-bar halt = -1.0; costs `tier` both sides. Judge window 2021-01-01..2026-08-31,
SEP panel, delisted-complete. No second look at any touched window is implied: no candidate is judged.

**Pre-named controls (frozen before any read):**
- C0 exact rule — implementation check only (outcome already known from the 2021-26 t.10.2 run);
- C1 entry lag +1 session; C2 lag +5; C7 lag +10 (reversal edges must decay with lag);
- C3 IBS gate inverted (>= 0.90);
- C4 momentum mirror (day_ret >= +0.08, IBS < 0.10);
- C5 within-day permutation of IBS across candidates (seed 20261006);
- C6 count-matched random eligible names on the days the real rule fires (same seed).
Acceptance bar (frozen): t_cl >= 2.0 AND halves both > 0 AND median > 0 AND ex-top-5 > 0, net at tier.

**Read.** p-hat = passing controls / 7. If >= 2 controls pass, the bar is loose: program-level rule
becomes "new one-look needs t >= 3 AND a forward shadow", and the current PASS verdicts get an error
bar. If 0-1 pass, the machinery stands and p-hat becomes the program's background false-pass estimate.

**No deployment. Diagnostic only.**

## Result — F13C-CAP v2 (participant-typed; judged 2026-10-06; N stays 857)
- **TRIM2: KILL.** press2 (fund-flavor max filer >= 9.5% + shrink) n 1888 events / 1207 names: short net
  +0.15%/window t 0.08; 2x cost -0.85% t -0.48; halves +1.41/-0.67; ex-top5-names -1.1.
- **FREED2: KILL.** n 36, mean ~0/median -6.5, halves +18.6/-5.7 (noise; n too small for anything).
- **13F-state family FINAL (v1+v2): no rate-bound flow footprint in daily data.** The name-based
  trim/freed constructions carry no shortable or longable edge at 50-100bp/side; the family's only value
  is defensive (see the dilution-drag screen) or as a quarterly STATE gate to be specified on LATER.
The program's regulatory-positioning domain jump is therefore answered NEGATIVELY at this data tier; the
open-but-data-gated branches (participant = actual RICs with fund-level caps > our proxy, borrow fees,
placement) stay on the frontier memo only. No deployment.

## Study COTX — COT positioning as a derivatives-only state (pre-register; renumbered N 862; originally filed 857->858 in a counter collision)
`date`: Tue Oct 6 2026, before any positioned return is read. Frontier branch: "participant
constraints / forced positioning" — margin-call cascade proxies; the state (who is positioned
how heavily) exists ONLY in CFTC data, invisible in equity daily prices.

**Data.** CFTC public Socrata API, free: TFF `gpe5-46if` (financials; weekly, Tue as-of) and
disaggregated for COMEX metals if TFF lacks gold/silver. Products: E-MINI S&P 500, NASDAQ MINI,
CRUDE OIL, NATURAL GAS, GOLD, SILVER (or HG/COPPER), EURO FX, UST 10Y NOTE. Cache to
`data/research/cot/`. Returns: weekly Fri->Fri (enter the first session after the report is
public, exit 5 or 10 sessions later) from Sharadar raw ETF closes (SPY, QQQ, USO, UNG, GLD, SLV,
CPER, UUP/IOO proxy as needed, IEF). Equity/rates events use SPY/QQQ/IEF; commodity events use
the product's own ETF.

**State (per product):** net participant positions / open interest, percentile of trailing
3y (156 obs, min 78 warmup): LP = leveraged funds, DP = dealers, AM = asset managers.
Pullback confirm: price <= 0.97 x 20d high; bounce confirm: price >= 1.03 x 20d low.

**Judged arms (directions fixed a priori; 1-week horizon primary):**
- A1 crowded-long unwind: LP >= 90th pct AND pullback -> SHORT 1 week (CTA/trend forced selling
  below model triggers; the unwind is mechanical, not informational).
- A2 crowded-short cover: LP <= 10th pct AND bounce -> LONG 1 week.
- A3 dealer-inventory extreme (contrarian to customer crowding): DP >= 90th -> SHORT;
  DP <= 10th -> LONG, 1 week.
Secondary (reported, not judged): 2-week horizon; AM percentile arms.
One open event per product max; no re-entry while holding.

**Gate:** pooled per arm across products: net (1bp/side ETF proxy) week-clustered t >= 2.0,
both halves of each product's own window net-positive, median > 0, ex-top-5 events > 0.
Cost shock 3bp/side reported; a PASS that dies at 3bp is DOWN-WEIGHTED not killed.
Kill rule: fail gate -> family KILL, no re-tuning percentiles/confirmations.

**Honest priors:** weekly frequency and 3y percentile windows mean low power and slow regimes;
expect A1/A2 to be the only plausible pass. This is a state test, not a strategy: even a PASS
feeds the book as a regime/size gate, never as a standalone futures strategy at $2-25k.

## Study CBAS — futures cash-basis dislocation (pre-register; renumbered N 863)
`date`: Tue Oct 6 2026, before any basis-flagged return is read. Frontier branch: "two
instruments that should coincide but temporarily disagree" — cash vs futures at the same 16:00
mark; the financing/dividend state visible only in the derivative.

**Data.** Cached GLBX ES/NQ daily contract bars 2011-2025 (front = min-exp, max-volume, same
rule as fut_roll.py); spot = SPY/QQQ raw close (Sharadar SFP); DTB3 for carry context only.
Basis b_t = ln(F_front_close / S_close) x 1e4 (bp). Known contamination: futures close prints
~16:00-17:00 Globex vs SPY 16:00:00 — noise ~15bp, small vs dislocation flags; accepted.

**Dislocation flag (frozen, not tuned):** z_t = (b_t - median21(b)) / MAD21(b). DISC: z <= -2;
PREM: z >= +2. Robustness grid k in {1.5, 2.5} reported only.

**Judged arms (entry next session t+1 open):**
- ETF leg (retail-feasible): DISC -> LONG SPY/QQQ, PREM -> SHORT SPY/QQQ; exit t+1 close
  (1-day arm primary) and t+3 close (secondary). Cost 1bp/side tier, 2bp tier_hi, 3x shock.
- Hedged info arm (not retail; measures the derivative content): long cheap leg vs short dear
  leg at same times, 0.5bp/side ES + 1bp SPY.
**Gate:** day-clustered t >= 2 net, both halves (2011-2018 / 2019-2025) net-positive, median > 0,
ex-top-5 > 0. Kill: fail -> KILL, no k re-tuning, no event-window re-scoping.

**Mechanism being tested:** arbitrage/hedging balance-sheet constraint at moments of stress
(deep futures discount) and forced hedging demand (premium); why not arbitraged instantly:
arbitrageurs are capital-constrained exactly then; observable daily. Priors: HFT keeps the
basis tight in liquid index space; expect KILL; the interesting residue would be the 2008/2020
and Aug-2024-style stress episodes — if the pooled edge is only those <5 events, that is a NO.

**Window note:** the GLBX cache is exploratory (touched by fut_roll/FND for spread shape only);
this is a new hypothesis on it; no deployment either way without a forward shadow.

## Amendment — Study PAIR-CLASS: same-issuer dual-class differential (pre-register; N 857 -> 858)
`date`: Tue Oct 6 2026 (continuation). Domain: same-issuer liability/capital-structure stack. This is the
family the program had never modeled; F13C killed one member (regulatory trim) — this is the OTHER member.
- **Mechanism.** Two classes of the same issuer with identical/dividend-identical cash flows (GOOGL/GOOG,
  NWSA/NWS, the Discovery pair in its era, and similar) trade separately. Their spread must behave like a
  stationary quasi-arbitrage with a persistent voting/control premium plus retail-flow noise, NOT like two
  independent stocks. Constraint force: nobody (retail) can cheaply force parity; arb funds hold it tight
  in liquid pairs, but retail flow pressure (salience, same-store index buying at the float-weighted class)
  can push the spread several bp-worth away for days, and it mean-reverts rather than trends.
- **Panel (frozen).** All same-name primary/secondary COMMON-stock pairs in Sharadar SEP, both classes
  listed (NASDAQ/NYSE/AMEX), each with >= 500 bars in 1998-2026, spread computed on raw closes
  (cu_A/cu_B). Panel printed BEFORE any signal is computed; no pair is added after results are seen.
- **Rule (frozen, ONE judged arm, long-only).** On day T close: z = (S - mean20)/sd20 of the log ratio
  (both classes' 20d window). If z <= -2 (the class is dislocated DOWN vs its own spread history): buy
  that class's close; exit its close 3 sessions later. Equal weight per fill. No short leg (retail borrow
  reality on both classes at $2-25k).
- **Pass bar:** date-clustered t >= 2; mean net > 5bp/event after 2.5bp/side; both calendar halves > 0;
  ex-top-5 > 0; a date-placebo (z computed on a 30-session-shifted spread) must be lower. Because the
  panel is small (few liquid dual-class pairs), ANY pass is a FORWARD-SHADOW candidate, never deployed on
  backtest alone.
- **Kill:** mean <= 5bp net, or either half <= 0, or placebo as good. Do not tune z-thresholds or the
  horizon afterwards.

## Amendment — FN-1 filing-lag map (OBSERVATION stage, no judged arm, N unchanged)
`date`: Tue Oct 6 2026. First program contact with SF1 (quar fundamentals) filing REPORTDATE.
Purpose: the OBSERVATION->MECHANISM steps only. Map, per firm-quarter, the filing lag
(filingdate/calendarQuarterEnd) vs the firm's own 3-yr median lag; publish the cross-tab of the NEXT-quarter
and SAME-quarter abnormal by lag-decile, FY-classes (10-K vs 10-Q), and delisted completeness. NO trade
rule is specified in this amendment; if the map shows a mechanism-shaped asymmetry consistent with a
constraint (filing-window stress: 10-K 60->90d, 10-Q 40->45d ceilings, the NT 60-day extension rules), a
SEPARATE pre-registration must precede any judged run. No returns-based tuning from the map is allowed.

## Amendment — Study SSR-LIFT: Rule 201 short-sale-restriction lift day, forward-only registration (N 859 -> 860)

Registered 2026-10-06 AFTER the exploratory evidence below was read (2011-26 daily, 2021-26 official crosses): every
historical window is TOUCHED, so the only judge is forward. (Concurrent session also bumped N to 859; if a collision
exists, renumber this entry, not the other.)

- **Mechanism (Rule 201).** A stock whose price falls >= 10% below the prior close is short-restricted (shorts only
  above the NBB) for the rest of T and all of T+1. Exploratory diff-in-discontinuity (`research/sim/ssr_rd.py`, Sharadar
  SEP 2003-26, local linear +/-3pp at L = low/prev_close - 1 = -10%, R control, date-clustered): post-rule (2011-11-10+)
  T+2 close-to-close discontinuity **-43bp (t -6.5)**, pre-rule **-0.3bp** (placebo); adjacent cutoffs -8/-9/-11% show
  no negative jump; leveraged/other ETFs (arbitrageable via unrestricted instruments) -19bp t -1.0; no reversal T+3..T+6
  (permanent = delayed price discovery). Dose-response by FINRA days-to-cover runs OPPOSITE to a pent-up-shorts story
  (low DTC -62bp, high -34bp): mechanism is the restriction's effect on T/T+1 price formation, not crowded shorts.
- **Official-cross check** (`ssr_fetch.py` -> `ssr_cross.py`, 2021-01..2026-10, 36.7k treated events): short at the T+2
  opening cross, cover at the T+2 closing cross, + 1.5 x SPY same-window hedge: **+16.7bp per EW day (t 2.72)**, per-event
  median +42bp, 5/6 years > 0 (2021 -1); control (L -10..-7%) +2.4bp. Price >= $10: +17.7bp/day t 2.73, 6/6 years.
  Tail: worst single-name -94%, 205 events < -20%; portfolio worst day -20.6%, maxDD -45% at 1x short notional.
- **Rule (frozen).** Universe: common stock, prior raw close >= $10, 20d ADV >= $20M, symbol on that day's official
  Rule 201 SSR list (or consolidated low <= -10% of prior close) on T, NOT re-triggered on T+1. Short at the T+2 opening
  auction, cover at the T+2 closing auction, equal weight, hedge 1.5 x notional SPY (open->close). Log-only; no orders.
  Report also per-name borrow status (ETB/HTB, fee) at the T+2 open from the broker; DTC tercile is reported, NOT used
  (it was chosen in-sample).
- **Gate (forward).** >= 120 lift sessions after 2026-12-06 (23/5 trading starts then: the overnight session may move
  the decline ahead of the open cross; that is part of what is judged). PASS: hedged EW-day mean > +8bp net of measured
  borrow, day-clustered t >= 2, median event > 0, ex-top-5 sessions > 0, ETB-only subset > 0. KILL: mean <= 0 at 120
  sessions or ETB-only <= 0.
- **Account eligibility (not part of the statistical verdict):** taxable margin account >= $2,000 only; Roth cannot
  short; $1k accounts cannot. FINRA Rule 4210 amendments (effective 2026-06-04) removed the PDT day-trade count, so a
  same-day short/cover is not trade-count-limited (Schwab: no counting since 2026-06-08, intraday margin buying power
  since 2026-07-13, per secondary sources). No deployment; sizing is a user decision.

## Result — PAIR-CLASS (judged 2026-10-06; N stays 858)
Panel frozen: same-name primary/secondary common pairs with $20M+ 20d $vol on BOTH classes — only
GOOGL/GOOG ($23-25B/day), WBD/DISCK (2008-2022, $51-139M), ZG/Z ($26-119M) survive; the rest are
SPAC-unit pairs with nothing but noise.
- Rule z<=-2 (dislocated class, long-only, 3-session exit, 2.5bp/side): pooled 1,027 fills, mean -0.08%
  net (t -0.61), 50bp cost -0.33% t -2.5 NEGATIVE; placebo (shift-30) -0.20% — same sign: there is no
  flow-release reversion across the panel at daily granularity.
- GOOGL/GOOG alone: 73 fills, MEDIAN +13bp and ex-split-artifact mean ~+26bp — the mechanism (spread
  reversion) EXISTS on the one big pair but is worth ~6 fills/yr x ~10bp x small sleeve ~ 0.03-0.1pp/yr
  at $10k: **killed by arithmetic of scale, not by falsity.**
Final: **rejected as a strategy; recorded as a real-but-unharvestable micro-mechanism.** No varied
horizons/thresholds afterward.

## Result — FN-LAG observation map (no judged arm; N unchanged)
SF1 publish-date lag (~filing lag) per firm-quarter vs own 8-q median, D+1..+5/+63 abnormal vs SPY:
- Quintiles 1-4 essentially flat (r5 ~ -0.2, r63 ~ +0.8..+1.0%);
- "Late" quintile: pooled +1.3% by D+5 and **+12.7% by D+63** — BUT decomposed: **$0-2 px bucket +421%**
  (sub-penny artifact pool: broken/melted micro caps), $2-5 = **-5.8%**, $5+ = **-3.0%**, and era split
  1998-2016 vs 2016-26 (-0.10 vs +3.66 by D+5).
- **Verdict: OBSERVATION DIES.** The pooled late-filer "premium" is a sub-$2 data artifact + going-private
  premium tail; the executable universe ($2-5/$5+) is NEGATIVE in every era. No state, no gate, no arm.
- Data-quality note recorded: SF1 `date` (publish date) as filing proxy is usable ONLY with restatement
  dedup (keep first); sub-$2 implied sizes are unreliable in daily bars. Do not reuse SF1 `date` for a
  "late-filing" state without this cleanup.

## Study VTS — vol term structure as an options sensor (pre-register; renumbered N 864)
`date`: Tue Oct 6 2026, before any curve-flagged return is read. Frontier branch: "options as a
sensor of hidden market state" — the ONLY options-family data that is free (Yahoo ^VIX9D/^VIX3M/
^VIX/^VIX6M daily closes, 2006/2007+). VIX roll (ETP) is separately TESTED-AND-REJECTED; this is
the curve STATE, not the roll.

**Mechanism under test (Cheng 2019 vol-demand):** contango (VIX3M/VIX9D >= 1.10) = harvesters
structurally short front vol = dealers' re-hedging buys dips -> LONG. Inversion (ratio <= 0.98)
= hedging demand front-loaded = dealer re-hedging amplifies downside -> SHORT. Directions frozen
by that mechanism; thresholds frozen (1.10 / 0.98), no tuning.

**Judged arms:** LONG SPY next open->close in contango; SHORT SPY next open->close in inversion.
Secondary (reported): 5-day O->O horizons; VIX6M/VIX3M same rule.
**Gate:** day-clustered t >= 2 net (1bp/side), both halves (2007-2016 / 2017-2026) net-positive,
median > 0, ex-top-5 > 0; 3bp/side shock reported. Kill: fail -> options-sensor branch recorded
DATA-WEAK at free tier; no re-tuned threshold reruns.
**Ceiling note (priority gate):** a daily ~10-20bp gross effect deploying ~50% of capital at ~30%
state frequency is ~+4-8%/yr pre-cost at best; this is a book-conditioning sensor test, not a
standalone strategy. Judged as a state, reported at the book level if it passes.
- **SSR-LIFT note (2026-10-06, after registration, no rule change):** the stronger C1->C2 variant (+37bp/day hedged t 4.9,
  6/6 years) needs a short into the T+1 closing auction while SSR is in force. Exchange rules (SEC Rule 201 FAQ; NYSE 2011
  no-action relief + Rule 123C; Nasdaq Reg SHO FAQ 2011) let short MOC/LOC orders participate but fill ONLY if the
  auction price is above the NBB (Nasdaq) / last exchange bid (NYSE, lower priority than unrestricted MOC). Fill odds
  need closing NBBO (DATA-LIMITED); the forward shadow should log a short-MOC on T+1 as a second, report-only arm.

## Results — COTX, CBAS, VTS (judged 2026-10-06; program N = 866 after counter renumber; all three KILL)

**COTX (N 862; COT positioning state, weekly, 9 products 2006-2026): KILL.** All four frozen arms fail:
A1 crowded-long-unwind short net -119bp t -1.05 (wrong sign); A2 crowded-short-cover long -15bp
t 0.25; A3 dealer extremes +6.7/-32.9bp t 0.97/-1.40. Halves flip, ex-top-5 negative, per-product
scatter (HG t -2.24 negative, NQ +1.17). **The weekly COT participant state (leveraged funds,
dealers, asset managers — information that exists ONLY in CFTC data) carries no tradable
1-2 week footprint at retail cost.** CL/NG series end 2022-02 (CFTC dataset split) — not the cause
of the null (they had 15y). Forced-positioning-via-COT branch closed.

**CBAS (N 863; ES-NQ cash-futures basis dislocation, daily, 2011-2025): KILL, with mechanism evidence.**
- First run was poisoned: GLBX daily bars are stamped by SESSION START (evening), not trade date;
  rebuilt on trade_date = next business day. (fut_roll/fnd event-window studies are label-shift
  invariant, so their verdicts stand.)
- Retail spot leg: DISC->long next-day -11.1bp t -2.71, PREM->short -12.1bp t -2.65 (SPY follows
  the futures-led move ~1 day, against convergence, cost-dominated). 3d arms t 1.47/-3.16. All fail.
- **Mechanism diagnostic (the real finding): the daily index basis has NO persistent dislocation
  regime.** MAD21 ~15-18bp; after a z<=-2 or z>=+2 flag, median z_(t+1) is -0.3/+0.4 and only
  14-26% of flags are still flagged next day. The 2008-style multi-day blowouts do not exist in
  2011-2025 daily index data — the arb is never balance-sheet-constrained for days at this
  frequency. The "hedged convergence" t=18-24 numbers are 2xMAD regression-to-median baked into
  the flag definition, not an edge. Cash-futures basis family closed at the daily tier.

**VTS (N 864; VIX term structure as the one free options sensor, 2007-2026): KILL.**
- contango (VIX3M/VIX9D>=1.10) LONG 1d: -0.04bp t -0.03 (dead); 5d: +17.1bp t 5.50 — but that is
  unconditional SPY drift (uncond 5d ~ +25bp), not state excess; per-year is +-5bp noise around
  beta. REJECTED as a sensor (t on drift, not on excess).
- inversion (<=0.98) SHORT: wrong sign both horizons (1d -11.7bp t -1.67, 5d -59.5bp t -3.35) —
  the market RELIEF-BOUNCES after inversion. The unregistered mirror (LONG after inversion,
  ~+59bp/5d excess, 11% of days) is recorded as an observation/forward-shadow candidate only —
  claiming it as a PASS would violate the registration. Overlapping 5d windows inflate its t.
**Options-as-sensor at the free tier is now answered: no.** The only remaining options→underlying
channel is the paid OI/gamma tier — see the frontier map; its prior is LOWER after today.

### Derivatives frontier map after today (mechanism -> status)
| mechanism (user's list) | status |
|---|---|
| cash-futures basis dislocation (ES/NQ) | TESTED-REJECTED (no persistent dislocation regime, daily) |
| COT positioning / forced unwind | TESTED-REJECTED (weekly, 9 products) |
| VIX term-structure sensor | TESTED-REJECTED (contango=drift; inversion wrong sign) |
| roll mechanics | TESTED-REJECTED (FUT-ROLL, arbitraged since ~2021) |
| delivery mechanics | TESTED-REJECTED (FND, closed) |
| Treasury auction / month-end | KILLED (TAC) / validated-small (TME, no variants) |
| OI pinning | TESTED-REJECTED (opex_pin) |
| generic options strategies | CLOSED (T1-T7/T5L) |
| ETF premium/discount + flows | CLOSED (ETC/EF/BSPD) |
| signed dealer gamma / OI concentration | DATA-LIMITED — paid OPRA statistics ~$180/yr; prior lowered by today's kills; do NOT fund automatically |
| CME margin-hike forced deleveraging | DATA-LIMITED — no free historical margin-rate series; scrape = CME notices archive; spec: event-study ±5d per hike, silver-2011 as canonical |
| SOQ / expiration day mechanics | NO POWER at daily tier (n≈60/root); would need minute data |
| cross-contract spreads (crack/crush/ES-NQ) | NOT TESTED — excluded as generic carry unless a named constrained participant is specified |
| rates futures → equities (beyond TME) | NOT SEARCHED; TAC killed the auction leg |
| commodity futures → producers | NOT TESTED — no forced-flow participant specified; generic risk |
| structured-product hedging (barriers, autocalls) | DATA-LIMITED — needs issuer OI/structure data that does not exist free |

**Meta answer (user question 12):** after COTX + CBAS + VTS (plus the prior roll/FND/TAC/OI-pin
kills): NO — the free derivative data does not reveal forced behavior invisible in equity daily
data at a harvestable tier. The derivative-market states we can see free (positioning weekly,
basis daily, vol curve daily) are either arbitraged flat, drift-only, or the wrong sign. The
invisible-in-equity-prices information that remains (OI by strike, signed gamma, margin rates,
skew) is exactly the paid tier — and today's evidence lowers its expected value.

## Mechanism-jump session — pre-test ceiling table (2026-10-06, evening; gate applied BEFORE any backtest)
Standing priority gate: kill before testing if ceiling at $10k < +8pp/yr under honest capture.
Shapes that clear: daily x >=15bp x >=50% deploy; ~monthly x >=2%; rare events x >=10-20% per-holder-capped.

| candidate (user's mechanism list) | participant / constraint | ceiling at $10k (honest) | verdict |
|---|---|---|---|
| CL/NG monthly index roll (GSCI 5th-9th bday) | index funds; tracked-weight mandate | ~1-4%/yr on futures notional (roll-window ~10-30bp/mo) | CEILING-KILL (TME-shape: real, small) — no backtest; do not revisit without a size-up mechanism |
| Buyback blackout window (10b-18) flow removal | issuer desk; blackout + 25% ADV cap | buyback factor lit ~2-3%/yr; 50% capture ~1-1.5%/yr | CEILING-KILL; the announcement event was already "in the gap" |
| SG-Trend / CTA crowding reversal | CTAs; trend-model stops | ~1-2%/yr, monthly, proxy loose | CEILING-KILL |
| DXJ/EWJ FX-forward-point wedge | currency hedgers; forward roll | 2-4%/yr gross, minus borrow | CEILING-KILL |
| Dividend-fail pre-ex-div front-run | failing shorts owing dividends | small, event-capped, hard-to-borrow side inaccessible | CEILING-KILL (adjacent to DM/FTD kills) |
| LDI funded-ratio de-risking (Milliman 100) | pension LDI desks; funded-ratio mandates | at-gate IF the state is real (0.5-1.5%/mo regime spread) | DATA-LIMITED-MEDIUM (290-page scrape); parked behind cheaper tests |
| Financing plumbing states (SOFR-DTB3 / -IORB, TGA) | levered funds & dealers; balance sheet at stress | standalone < 1%/yr (rare state) BUT = risk-GATE for the book's -10% lever | **RUN (gate research, pre-registered below)** |
| Margin-debt deleveraging state (FINRA monthly 1997-2026) | margin borrowers; house margin calls | standalone < gate; = crash-regime state + the one free forced-deleveraging observable | **RUN (pre-registered below)** |
| Signed dealer gamma / OI | option dealers; delta-hedge rebalance | unknown; prior lowered | PAID tier, user decision (unchanged) |
| Borrow fees / recalls | shorts; borrow availability | unknown | DATA-LIMITED (no free fee history) |
| TBA / dollar roll | mortgage origination; TBA delivery | unknown | DATA-LIMITED (no free TBA history) |

## Study PLUM — daily financing-plumbing stress states (pre-register; renumbered N 865)
`date`: Tue Oct 6 2026 evening, before any state-flagged return is read. Frame: gate research for
the book's -10% lever (financing/collateral constraint family), judged first as a standalone state.
**Data:** FRED SOFR, DTB3, IORB (free CSV, 2018-04+); SPY raw O/C (Sharadar); TGA daily if the
FiscalData field resolves, else dropped (no proxy invention).
**States (frozen):** S1 = (SOFR - DTB3) >= +25bp; S2 = (SOFR - IORB) >= +15bp. (Repo prints above
the unsecured proxy / administered rate = balance-sheet stress; thresholds are the literature's
"abnormal" levels, not tuned.) S3 (secondary, reported): S1 restricted to the last 2 sessions of
a quarter (window-dressing concentration).
**Arms:** after S1 or S2 on day D: SHORT SPY next O->C (forced-unwind continuation) and LONG SPY
next O->C (stress ends, relief) — both directions judged (family kill if neither passes);
horizons 1d and O->O+2. Cost 1bp/side, shock 3bp.
**Gate:** day-clustered t >= 2 net, both halves (2018-04..2022-06 / 2022-07..2026), median > 0,
ex-top-5 > 0. Low-power accepted (states are rare by construction); a t 1.5-2 single-direction
result = OBSERVATION, not PASS.
**Honest prior:** SRF (2021+) absorbs repo stress; expect near-null post-2021 and any signal
concentrated in 2019-09/2020-03 (< 5 events) = NO by the outlier rule.

## Study MFLW — monthly margin-debt deleveraging state (pre-register; renumbered N 866)
`date`: Tue Oct 6 2026 evening, before any monthly return is read.
**Data:** FINRA customer margin debit balances, monthly 1997-01..2026-08 (one XLSX, free,
data/research/finra/margin.xlsx); SPY monthly (Sharadar raw, total-return approx price-only).
**State (frozen):** m = log debit balance; d3 = m - m.shift(3). CASCADE state: d3 <= -0.10 AND
SPY < its 6m mean at month-end. EUPHORIA state: d3 >= +0.10 AND SPY > 6m mean. (10% in 3 months
= a real leverage deflation/blowoff, not drift; not tuned.)
**Arms (both judged, mechanism has two readings):** after CASCADE -> LONG next month (forced
liquidation exhausts the seller -> bounce); after EUPHORIA -> SHORT next month (leverage peak ->
deleveraging risk). Mirror continuations reported.
**Gate:** monthly t >= 2 net (1bp/side), both halves (1997-2011 / 2012-2026), median > 0,
ex-top-5 months > 0, 3bp shock reported. Fail either arm -> monthly-constraint-state family KILL.
**Honest prior:** margin debt is mostly coincident; monthly lag eats the cascade; expect WEAK.

## Amendment — Study CEF-TL2: December tax-loss in CEFs, delisted-complete (reopen on new data; N 863 -> 864)
`date`: Tue Oct 6 2026 evening. This is a REOPENING under the standing rule "do not re-open CEF-TL without
new data": the original kill (N 823->824) was judged on **142 SURVIVOR CEFs, 10 years, from CEFConnect**
(documented weakness: "survivor CEFs, price-only"; the CLAUDE.md CEF row separately says survivorship is
unhandled). Sharadar SFP now supplies **~1,891 CEF price series 1997-2026 including delisted**, which
removes the survivorship objection and extends the never-seen eras to 1998-2015. Same mechanism (statutory
Dec-31 loss harvesting by taxable retail CEF holders -> Jan reversion), same leg structure, NO design tuning.
- **Frozen rule (as in CEF-TL with the new universe):** all SFP CEF categories (tickers.parquet category
  contains "CEF"; common + preferred), raw close >= $3 at formation... (keep the original filters where
  they map: distribution-adjusted = total-return via the fac factor); formation = last November session;
  rank YTD total return; bottom quintile by year; Dec leg = Nov-end -> Dec-end; Jan leg = Dec-end ->
  Jan-end; long-only, equal weight per leg, per year.
- Benchmarks: the equal-weight CEF UNIVERSE (same-year, all SFP CEFs with bars) as the relative test, and
  IWM as a market check; both reported, universe-relative is the registered abnormal.
- Costs: 30bp/end leg round trip (original stated cost); report 2x.
- Judgement (frozen, one look): Jan-Feb unfolding legs computed as the ORIGINAL PASS bar: Jan Q1-u >=
  +1.0% net, both calendar halves positive, ex-best-5-years mean > 0, ex-best-year quintile > 0, Dec leg
  predicted sign (Q1-u <= 0 in Nov->Dec), and quintile monotonicity not required (the original test's bar).
- Kill: fails any original bar; or the "delisted-completeness" materially shrinks the set (n < 30/yr names,
  underpower note only, judged as-is).
- Ceiling note (priority gate): even a PASS is a ~+1-2pp/yr December/January sleeve; this is a
  data-fix-driven decision on a small mechanism family.

## Results — PLUM, MFLW (judged 2026-10-06 evening; N 864, 865; both KILL; financing region measured)

**PLUM (N 865; daily repo/financing stress states 2018-04..2026): KILL.**
S1 (SOFR-DTB3 >= 25bp, n 171, 8% of days): 1d both directions ~0 (t -0.43/-0.19); 3d short +44bp
t 1.77 but median -18.3bp (the mean is crash-carried — fails the median/outlier rule).
S2 (SOFR-IORB >= 15bp): n=3. S3 (S1 x quarter-end): n=5. Post-2021 flags (2025-10..12) were benign.
**The daily financing-plumbing state is not a risk gate at free observables post-SRF; nothing to
gate the book's -10% lever on.** Do not re-run SOFR-spread states at daily tier.

**MFLW (N 866; FINRA margin-debt monthly cascade state 1997-2026, n 356): KILL.**
CASCADE (3m log-debt contraction >= 10% + SPY < 6m mean, n 27) -> bounce-long: +16.4bp/mo
t 0.11, hit 52%, halves -16.6/+47.0 (2008/2009 next-months were -8% to -10.7%: NO reliable bounce;
the mean is one +12.7% month). EUPHORIA -> contrarian short: -46bp/mo t -1.05 wrong sign (leverage
peaks kept running months, 1999-2000, 2020-21); continuation mirror t 0.96. Margin debt is
coincident, as the prior said. Monthly-constraint-state family closed.

### Ceiling-killed pre-test (no backtest, recorded): CL/NG monthly index roll (~1-4%/yr),
buyback 10b-18 blackout flow (~1-2%/yr), SG-CTA crowding (~1-2%/yr), DXJ/EWJ forward-point wedge
(2-4%/yr minus borrow), dividend-fail pre-ex-div front-run (capped, hard-to-borrow side inaccessible).

### Region map after the financing jump (what is genuinely left)
- **FINRA ATS venue-mix / off-exchange share per symbol**: weekly panels EXIST behind the free
  FINRA API (otcMarket weeklySummary is key-less; equity ATS + short-interest datasets return
  401 until an API token is registered at api.finra.org). Mechanism: internalized retail flow
  share = inventory/state invisible in daily bars; would condition the IBS/night legs. Needs the
  user to mint a free FINRA API key — one action, then testable.
- **Paid tiers (each a user decision, none automatic):** OPRA OI/signed gamma (~$180/yr; prior
  lowered twice), CME margin-rate archive (scrape), borrow-fee history, PIT ratings, TBA/dollar
  roll, per-fund NAV (iShares CSVs), Milliman LDI (290-release scrape).
- **Unsearched but likely below gate on priors:** TGA debt-ceiling episodes (n tiny), GPIF quarterly
  rebalance (front-run), MMF/bill plumbing (macro-level), CP/corporate funding (no daily data).
**Session verdict:** the financing/collateral/margin region — the last free-data member of the
user's mechanism list — is now measured and empty at retail tier; discovery continues only with
(a) the free FINRA token, or (b) a paid-tier decision.

## Amendment — Study PREF-EX: preferred-stock ex-dividend under-adjustment captured in the auctions (registration after exploratory look; N 860 -> 861)

Registered 2026-10-06 AFTER the exploratory evidence below (Sharadar 2005-26 all touched; official crosses 2021-26
touched). Judge = forward only. (Concurrent session numbering: renumber this entry on collision.)
- **Mechanism.** Exchange-listed $25-par preferreds are held by taxable retail/income investors; dividends (often
  non-qualified: REIT, trust) are worth less than cash to the marginal holder, and dealer inventory is thin, so the
  ex-date drop is ~0.8 x the dividend. A Roth (dividend untaxed) buys the cum-dividend close and sells the ex open.
- **Evidence.** Sharadar (`pref_exdiv.py`, 19,853 ex-dates / 893 preferreds 2005-26): buy T-1 close, sell T open +45bp
  (t 23), 22/22 years > 0, non-ex nights +1..+3bp; drop lands on T only (T-1..T+3 flat; drop/div 0.80). Official SIP crosses
  2021-26 (`pref_fetch.py` -> `pref_cross.py`, 4,972 events): T-1 closing cross -> T opening cross +38.1bp mean, +34.8
  median, hit 78%, t(day) 20, every year +30..+50, ex-top-5 +37.5, ex-top-5 issuers +41; stable by cross size (min cross
  >= $30k: +30bp t 8.8). Quotes sample (`pref_quotes.py`, n 296): closing cross = mid -0.4bp, opening cross = mid -0.2bp
  (median +9); quoted spreads 38bp close / 88bp open -> crossing the spread LOSES -59bp: executable ONLY in the auctions.
  By issuer type: REIT +45.6 (drop 0.75), banks +28.4 (0.81), insurance/utilities ~+39 (0.76-0.77): partial tax-clientele
  support (banks = most liquid). Risk: EW ex-night portfolio maxDD -2.4% at full deployment, worst night -2.0%.
- **Rule (frozen).** Domestic preferred, raw price $10-60, 20d median $vol >= $100k, declared cash dividend with ex-date T,
  yield 0.2-4% per payment. MOC (or LOC at the 15:50 indicative) buy at T-1, MOO sell at T; equal $ per name, each order
  <= 10% of the name's 20-session median closing-cross $; Roth/cash account only.
- **Forward gate.** Phase 1 (log-only, >= 60 ex-dates): official-cross P&L >= +20bp mean and median > 0 with t >= 2 ->
  Phase 2 (user decision): tiny live pilot ($100-300/name) measuring fill rate and price vs the cross without us; PASS if
  realized capture >= +15bp net over >= 100 live fills. KILL: Phase-1 mean <= +5bp, or live capture <= 0.
- **Unverified constraints (not part of the statistical verdict):** price impact of our MOC/MOO in thin crosses (median
  close cross $5.3k); broker support for MOC/MOO on preferred symbols; Roth cash-account settlement (T+1) / good-faith rules
  on back-to-back ex-nights; taxable accounts likely net ~0 after dividend tax (Roth-specific edge).
- **PREF-EX independent evidence (2026-10-06, Sharadar SFP 2005-26, T-1 close -> T open + div, $vol >= $100k):** CEFs
  +13.0bp mean / +14.1 median (non-ex +3.8 / 0.0), drop/div 0.78, t 11, 21/22 yrs; ETFs (yield >= 0.5%) +17.5 / +12.1
  (non-ex +5.2 / +3.9), drop/div 0.86, 20/22 yrs. Same sign in other retail-income classes, scaled down with per-payment
  yield; common stocks show none (EXDIV-OPEN). Not judged (daily vendor opens, not official crosses).

## Result — CEF-TL2 (judged 2026-10-06 evening; N stays 864)
Universe restored: 1,156 SFP CEF series (delisted included) vs the original 142 survivors; 1999-2025 =
27 formation years; ~110 bottom-quintile names/yr from a ~549-name universe; px >= $3; trunc guard.
- **Dec leg (Nov-end -> Dec-end, Q1-u gross): +0.29% t 0.43, years+ 48%, median -0.16 — WRONG SIGN.**
  The bottom-YTD CEF quintile does NOT underperform in December in the delisted-complete universe.
- **Jan leg (Dec-end -> Jan-end, Q1-u gross): +2.72% t 3.28, years+ 81% (22/27), median +2.55,
  ex-best-year +2.31)** — the December-loser January bounce is REAL on CEFs across 27 years,
  including the never-seen pre-2016 eras (1999-2016 +2.59% t 2.44).
- **But net (30bp round trip): +0.13% t 0.27; median -0.25; years+ 48%. DEAD at cost.**
Final status: **REJECTED (net), with a mechanism-level finding: the December-loser January bounce is a
durable GROSS effect across three independent panels (stocks 1998-2025 t 1.91; CEFs 1999-2025 t 3.28;
both die at 25-60bp round trips). The January seasonal is gross-real and cost-bound at retail; treat
any future December-sleeve idea as non-viable unless it cuts round-trip cost below ~10bp. PERMANENT
CLASS VERDICT: December/January loser-bounce = cost-bound seasonal, no retail edge. Do not re-open on
prices-only data again.
- **PREF-EX execution attack — plan written before `pref_exec.py` was run (2026-10-06).** Descriptive only, no thresholds
  tuned, nothing here changes the frozen rule: (1) flat round-trip degradation 0/5/10/15/20/25bp and asymmetric close/open
  degradation incl. the full median half-spread on both legs; (2) capacity at p = 1/2/5/10/20% of each leg's auction $,
  on the event's own cross $ and on an ex-ante estimate (median cross$/20d $vol x the name's $vol); (3) account $/yr at
  $1k/3k/5k/10k/25k with whole shares, Roth (no leverage); (4) partitions by terciles or economic cut points fixed here:
  yield per payment (terciles), price vs $25 par (<20 / 20-24 / 24-25.5 / >25.5), 20d $vol (terciles), issuer type
  (SIC: REIT / bank-credit / insurance / utility / other), years since first price (<1 / 1-3 / >3), dividend $ (terciles).
  Prior expectations: thin > liquid, REIT > bank, deep-discount ambiguous (distress). Spread partition is limited to the
  296-event quote sample. Second executable form CC (MOC both legs) is reported alongside CO because Schwab has no MOO.
- **PREF-EX execution attack — RESULT (2026-10-06, `pref_exec_out.txt`).** Statistical verdict unchanged; size claim
  DOWNGRADED. (1) Degradation: CO +38 -> +13bp at 25bp round trip (t 6.4); CC +28 -> +13 at 15bp, ~0 at 25bp. If the open
  leg misses the auction and pays the median half-spread (44bp) CO is NEGATIVE (-6bp): the open-auction fill decides CO.
  (2) Capacity per ex-night (ex-ante): 1% of auction $ -> ~$280, 2% ~$550, 5% ~$1.4k, 10% ~$2.8k, 20% ~$5.5k (median).
  (3) Account $/yr, CO at 5% participation and 10bp: $1k $232 (23%), $3k $456 (15%), $5k $585 (12%), $10k $789 (7.9%),
  $25k $919 (3.7%); CC same: $168 / $310 / $396 / $498 / $552. Dollars plateau ~$0.9k (CO) / ~$0.55k (CC) per year at
  5% participation: capacity, not cost, binds above ~$5k. The earlier 10%-cap/0bp figures (~$840 at $3k, ~$1.6k at $10k)
  were optimistic by ~2x. (4) Partitions (pre-stated, no rule change): yield/payment terciles CO +26/+33/+56; dividend $
  +30/+35/+51; thin/mid/liquid +46/+38/+30; REIT +46 vs bank +28; price vs par and issue age flat. All in the predicted
  direction (tax value of the dividend, thin dealer inventory). (5) Broker: Schwab API supports MARKET_ON_CLOSE (live MOC
  fills = official close, n 61) but has NO market-on-open; directed opening routes are refused (400) and AUTO-routed
  pre-open sells filled at the official open for liquid names (n 72, median 0.0bp) -- unverified for preferreds. Schwab
  GFV definition ("not sold prior to the settlement date") + T+1 permits back-to-back ex-nights in a cash Roth.
  Unverified: Schwab acceptance of MOC on preferred symbols. (6) Shadow LIVE on him (log-only): `pref_ex_shadow.py`,
  REGISTRY "PREF-EX", gate 60 forward ex-nights; Sept-2026 backfill (touched) net CO +32bp, net CC -12bp over 15 nights.
  **Classification: strong candidate awaiting live validation, small Roth sleeve (~$0.2-0.9k/yr); passes the +8pp gate at
  $1-5k, borderline at $10k, fails at $25k.** Next decisive step (user decision): one tiny live MOC buy + pre-open sell of a
  liquid preferred in the Roth to verify symbol acceptance and the open fill vs the official cross.

## Study VENM — FINRA off-exchange venue-mix as an IBS conditioning state (pre-register; N 866 -> 867)
`date`: Tue Oct 6 2026 evening, before any venue-conditioned return is read.

**Data.** FINRA OTC Transparency `weeklySummary` (group otcMarket; key-less endpoint that carries BOTH
ATS and OTC weekly aggregates; the user's FINRA API key was stored in .env but the authed regData
groups still return 401 — not needed because weeklySummary is public). Partition field
weekStartDate (Monday); rows filtered locally to summaryTypeCode in {ATS_W_SMBL, OTC_W_SMBL};
sample validation that *_SMBL (not _FIRM) rows are one-per symbol-week. Coverage probe: weeklySummary
holds weeks 2018-01-08..2026-09-21 (no 4y-rolling limit). Cache: data/research/finra/ats.parquet.
Key stored as FINRA_API_KEY in .env (gitignored); never in code/commits/logs.

**Alignment (the lookahead rule).** Each row carries initialPublishedDate (empirically ~5 weeks after
the week for the historic sample row; the field is authoritative). A symbol's state is KNOWN on
 trading day D only if its week's initialPublishedDate < D (strictly earlier session). If
initialPublishedDate were missing/republished inconsistently across rows, the study is DATA-LIMITED
and I stop rather than silently lagging.

**Off-exchange share.** offshare_w(i) = (ATS_W_SMBL shares + OTC_W_SMBL shares) /  (sum of
Sharadar raw daily consolidated volume over the week's 5 sessions); clipped to [0,1]. Rationale:
ATS + non-ATS OTC = off-exchange/internalized flow (the wholesalers' inventory); the tape total
includes both, so the ratio is the off-exchange share of all reported volume.

**States (frozen; tercile/deciles NOT tuned after the look):**
- LV = previous-known week's offshare percentile vs each symbol's trailing 26 weeks: LOW < 1/3,
  HIGH > 2/3.
- DL = weekly change in offshare: RISING <= -3pp... (frozen: RISING: +3pp or more; FALLING: -3pp or
  more; else NEUTRAL).
- X = extreme: top decile level, bottom decile level.
- LX interaction is the judged object: the IBS leg (book.py ibs_days: EQ18, top-3 momentum,
  IBS<0.2, open d+1 -> open d+2) per trade bucketed by the above states.

**Judged tests.** (1) IBS net return by LV bucket (LOW/HIGH) with day... trade-day clustering;
(2) by DL bucket (RISING/FALLING); (3) X extremes. PASS bar: an interaction difference t >= 2
(bootstrap over entry days) AND both halves same sign AND ex-top-5 stable AND the conditioned
rule beats unconditional IBS by >= 20bp/trade; then the economic re-test (hit rate, $/yr at
1k/3k/10k/25k, capital utilization). PLACEBOS: symbol-permuted offshare (fixed seed), adjacent
tercile boundaries shifted one band, SPY-matched blanks. KILL: no bucket separation / placebo
passing. **Prior:** weak-positive (off-exchange share = retail/wholesale flow state; the mechanism
says high internalized share = the day's risk HAS ALREADY crossed retail hands; expected effect
size < 30bp/trade interaction).

**Documented data caveats:** SMBL aggregates; weeks containing holidays have 4-session tape sums
(denominator shrinks -> share inflated ~25% for those weeks; flag holiday weeks and report with
and without); ETF coverage in the tier identifiers ("selected exchange-traded products") verified
per symbol; missing symbol-weeks -> state carried forward max 4 weeks else excluded.

## Study FXD — fund ex-dividend under-adjustment by per-payment yield (pre-register; N 867 -> 868)
`date`: Tue Oct 6 2026, late evening. Written before any yield-partitioned fund number is read. Branch from PREF-EX:
its dollars plateau at ~$5k (capacity). Funds (CEFs, income ETFs) have far larger auctions.
**Already seen (touched):** pooled SFP 2005-26 fund ex-nights only (CEF +13.0bp, ETF yield >= 0.5% +17.5bp). Nothing
partitioned by yield, nothing pre-2005, no official crosses for funds.
- **Mechanism.** Same as PREF-EX: the marginal holder of income funds is taxable retail who values the distribution
  below cash, so the ex-date price drop < distribution. Prediction: under-adjustment (bp) grows with yield per payment;
  for ETFs the creation/redemption arb should cap it at the spread (competing explanation for any ETF effect: stale
  vendor opens / overnight drift, not under-adjustment).
- **Ceiling (gate before testing).** Monthly payers at 1-3%/payment, drop/div 0.86 -> 14-40bp/event; ex-nights on ~150+
  nights/yr with capacity of $100k+ per night in liquid funds -> if >= +15bp net it clears +8pp at $10k. Kill is cheap.
- **Rule (frozen).** SFP CEF / ETF / ETN (separately), raw price >= $5, 20d median $vol >= $200k, regular cash
  distribution with ex-date T, yield/payment y = div / close(T-1). Buy close(T-1), sell open(T) (CO) and close(T) (CC),
  + distribution. Excess = event return minus the SAME fund's mean non-ex CO/CC over the prior 60 sessions (removes the
  fund's own overnight drift). Yield bins fixed: <0.5% / 0.5-1% / 1-2% / 2-5% / >5% (>5% reported, not judged: ROC/
  YieldMax-type, path noise).
- **Judge (one look each).** J1 untouched era 1998-2004 (CEFs; ETFs too few): excess CO in y >= 0.5% bins > 0 with
  day-clustered t >= 2 and monotone in y across the three middle bins. J2 2005-2026 partitions: median > 0, ex-top-5,
  every 5-yr block > 0 for the bins carrying the claim. J3 execution (only if J1/J2 pass): official SIP crosses
  2021-26 via Alpaca auctions for the passing bins; mean >= +15bp net of 5bp round trip.
- **Kill.** J1 t < 2 or wrong sign in CEFs, OR effect not increasing in y, OR ETF effect present only in vendor opens and
  absent in official crosses (stale-open artifact).
- Runner `research/sim/fxd.py` -> `data/research/program/fxd_out.txt`.

## Result — FXD (judged 2026-10-06 late; N 868): KILL as a capacity extension; mechanism-supportive
`research/sim/fxd.py` -> `data/research/program/fxd_out.txt`. **Data bug found and guarded first:** 9.6% of eligible fund
ex-events (31% of those with y > 2%) carry a Sharadar dividend that disagrees with the dividend-adjusted series by > 10%
(split-adjusted dividends vs raw prices after later reverse splits: YieldMax-type funds); unguarded, the >5% bins showed a
fake +500..900bp/night with drop/div 0.31. Rule for any SFP dividend study: require |div/P - y(closeadj)| < 10%.
- **J1 (untouched 1998-2004, CEF, xCO):** 0.5-1% +3.4bp (t 2.45) / 1-2% +22.2 (t 4.77) / 2-5% +41.6 (t 5.09, med +42.8,
  ex-top5 +34.6). Monotone in yield: PASS (tax-clientele under-adjustment existed in CEFs and scaled with yield).
- **J2 (2005-26):** CEF 2-5% xCO +27.8 (t 7.7) but 5-yr blocks **+51 / +31 / +26 / +9 / +4**; CEF 1-2% decays to +1/+0.
  xCC (MOC both legs, the Schwab-executable form) is ~0 or negative in every CEF bin <5%: the excess sits in the vendor
  ex-date OPEN print and is given back intraday. ETFs: ~0, recent blocks negative (-15/-40bp in 2025 for 0.5-2%), as the
  creation/redemption arb predicts. ETNs noise.
- **Verdict: KILL for the purpose registered** (extend PREF-EX capacity). The fund effect has been arbitraged to < 10bp
  since 2020 and is not capturable with MOC; J3 (official crosses) not triggered. Supports the PREF-EX mechanism (the
  same clientele effect, alive only where holders are retail and dealer inventory thin). No fund ex-div variants.

## Study ETDX — PREF-EX rule on $25-par exchange-traded debt and CEF preferreds (pre-register; N 868 -> 869)
`date`: Tue Oct 6 2026, late evening. Coverage counted (SFP ETD 365 tickers / 9,819 distributions, CEF Preferred 76 /
2,205; ~700 + ~280 events/yr recently); NO return on these classes has been read.
- **Why.** FXD showed the clientele under-adjustment survives only where holders are retail and dealer inventory thin.
  Baby bonds (trade flat; coupon = ordinary income) and CEF term preferreds are the same holder class as PREF-EX. If
  they carry the effect they roughly double PREF-EX's ex-nights and its capacity ceiling (~$5k).
- **Rule (frozen = PREF-EX rule).** Raw price $10-60, 20d median $vol >= $100k, distribution y 0.2-4%/payment with the FXD
  dividend guard (|div/P - y(closeadj)| < 10%). CO = buy close(T-1), sell open(T) + div; CC = sell close(T). Placebo =
  same names' non-ex nights.
- **Judge, per class (ETD, CEF Preferred).** PASS if CO mean >= +20bp, median > 0, day-clustered t >= 2, ex-top-5 > +15bp,
  >= 75% of years > 0, and the 2021-26 block >= +20bp. CC reported (the Schwab-executable form) with the same bars as a
  secondary. Then (only if PASS): official SIP crosses 2021-26 and the capacity increment = share of ex-nights with no
  preferred ex-date + added $/yr at $3k/$10k/$25k at 5% participation, 10bp round trip.
- **Kill.** Any primary bar fails -> class closed, no variants.
- Runner `research/sim/etdx.py` -> `data/research/program/etdx_out.txt`.

## Result — ETDX (judged 2026-10-06 late; N 869): PASS (both classes); capacity extension of PREF-EX
Runners `etdx.py` (Sharadar SFP), `etdx_fetch.py` + `etdx_cross.py` (official SIP crosses), `etdx_exec.py` (accounts);
outputs `data/research/program/etdx_{out,cross_out,exec_out}.txt`. Dividend guard dropped 43 of 5,379 events.
- **Sharadar 1998-2026:** ETD CO +45.3bp, med +42.4, t(day) 19.0, ex-top5 +44.7, hit 82%, 28/29 years > 0, 2021-26
  +46.2; CC +36.3 (27/29 yrs). Flat by liquidity (dv >= $1M +39.3). Drop/div 0.76. CEF Preferred CO +31.2, med +32.2,
  t 11.3, 14/15 yrs, 2021-26 +34.0; CC +14.0. Non-ex nights ~+1bp. All primary bars pass.
- **Official crosses 2021-26 (J3):** ETD (n 1,995) CO +43.9 med +40.8 hit 83% t 16.3, CC +38.6 med +36.5;
  CEF Preferred (n 298) CO +37.9, CC +23.8; pooled years +39..+51 (CO). Drop at open / div 0.74. Close cross median
  $5.0k (the binding leg), open cross $11.5-12.7k.
- **Mechanism (stronger than for preferreds):** baby bonds trade FLAT, so a taxable holder who sells before the ex-date
  converts the accrued coupon (ordinary income) into a capital gain; the buyer-before-ex is taxed on the full coupon.
  Taxable supply before ex / demand after ex is systematic; a Roth is indifferent.
- **Capacity increment (5% participation, 10bp round trip, Roth, whole shares):** CO PREF $793 -> PREF+ETDX $1,107 at
  $10k (11.1%/yr), $923 -> $1,442 at $25k (5.8%), $459 -> $566 at $3k; CC $500 -> $737 at $10k (7.4%), $554 -> $844 at
  $25k. 51% of ETD ex-nights have no preferred ex-event (new nights, not just more names). At 10% participation CO
  $1,586 at $10k / $2,463 at $25k. The plateau rises ~1.5x but still binds above ~$10k.
- **Forward:** logged in the PREF-EX shadow (`pref_ex_shadow.py`, cls="etd", universe `etd_symbols.txt`, 185 listed
  ETDs from Sharadar 2026-10-05), gated separately: 60 forward ex-nights, PASS net CO >= +20bp, median > 0, t >= 2;
  KILL <= +5bp. Sept-2026 backfill (touched, 7 nights/71 events): gross CO +35bp, net CO +11, net CC -5 (shadow slip
  model charges CC ~19bp). Unverified: ETD spreads (impact rows use the preferred quote sample), Schwab MOC on ETDs.
- **ETDX/PREF-EX entry ladder (descriptive, no N; `etdx_ladder.py` -> `etdx_ladder_out.txt`).** Pre-ex sessions are flat
  (Sharadar 2005-26, night/day around ex: T-3..T-1 means -6..+5bp, medians 0; the whole move is the T night: prefs +41,
  ETD +46; ex-day open->close -10/-11bp = why CC < CO; T+1 day +3..+7). Day-level Roth sim (capital locked while held,
  3bp haircut per extra pre-ex session, 10bp round trip): L=1 reproduces etdx_exec ($1,103 at $10k CO 5%). **CO, 5%:
  L=2 (T-2 + T-1 closes) $10k $1,103 -> $1,261, $25k $1,437 -> $2,046 (+42%); L=3 no better.** CC: laddering LOWERS $
  (exit = one closing cross, so no capacity is added; only haircut + locked capital). The ladder is a lever only for the
  open-auction exit, i.e. only if a Schwab pre-open sell fills at the official open on these symbols (unverified).

## Study OVX — overnight-venue (BOATS) exit for night picks (pre-register; N 869 -> 870)
`date`: Tue Oct 6 2026, late. Correction to `index_beat_ideas.md` B1 ("forward only from 2026-12-06"): Alpaca serves
Blue Ocean ATS (`feed=boats`) bars from ~2024-10, so the 23/5 exit question is testable on ~2 years NOW. No overnight
price for any pick has been read.
- **Mechanism.** Night-leg picks are big same-day losers; overnight-venue liquidity is mostly retail (Robinhood/Schwab
  24h) dip-buying, dealers are thin. If retail overnight demand lifts loser prices above where the opening auction
  clears (institutional supply arrives at 09:30), the bounce is better harvested overnight. Competing: overnight prints
  are noisy/adverse (wide spreads), and the opening auction is the deepest exit.
- **Data.** Picks = `auction_audit_picks.pkl` (ok rows, 2024-10-01..2026-09-18; 4,419 picks / 484 nights; entry =
  official close cross c_auc, base exit = next official open cross o_auc). Path from Alpaca 1-min bars: SIP post-market
  16:00-20:00, BOATS 20:00-04:00 (split 20-24 / 00-04), SIP pre-market 04:00-09:28.
- **Primary (H1).** x = VWAP_BOATS(20:00-04:00) / o_auc - 1 per pick with >= 1 BOATS trade. PASS if mean x >= +20bp
  (a conservative half-spread allowance for overnight venues), median > 0, day-clustered t >= 2, ex-top-5 > +10bp, both
  halves (split at 2025-09-30) > 0, coverage (picks with BOATS trades) >= 50%. Secondary (report): same for post-market
  and pre-market windows; return decomposition close -> each window -> open; liquid (ADV top half) vs thin.
- **Kill.** H1 fails any bar -> the 23/5 exit stays forward-only (B1), no window tuning on this sample.
- Runner `research/sim/ovx.py` (fetch cached under data/research/ovx) -> `data/research/program/ovx_out.txt`.

## Study HYC — high-yield non-qualified common dividends (REIT/mREIT/BDC) ex-night (pre-register; N 870 -> 871)
`date`: Tue Oct 6 2026, late. Branch from PREF-EX/ETDX: same clientele (taxable retail, distributions taxed as
ordinary income) but deep auctions -> the capacity ceiling would lift. Partly touched: AZ/EXDIV-OPEN (common stocks,
top-500, mean yield ~0.7%/payment: +4..+7bp, dead) may include large REITs; no REIT/BDC or yield >= 1% split was read.
- **Rule (frozen).** SEP common (category contains "Common Stock"), raw price >= $5, 20d median $vol >= $1M, regular
  cash dividend with ex-date T, FXD dividend guard, y = div/close(T-1) in [1%, 6%]. Classes by SIC: REIT 6798, BDC/
  closed-end 6726, other. CO = close(T-1) -> open(T) + div; CC = -> close(T) + div. Excess = minus the name's own mean
  non-ex CO/CC over the prior 60 sessions.
- **Judge.** Per class (REIT, BDC), xCO and xCC: mean >= +15bp, median > 0, t(day) >= 2, ex-top-5 > +10bp, >= 75% of
  years > 0, 2021-26 >= +15bp. Report yield bins 1-2 / 2-4 / 4-6%, dv tiers ($1-10M / >= $10M), drop/div, by year.
  If a class passes -> official crosses 2021-26 (J3, same bars net of 5bp round trip) + capacity at $10k/$25k/$100k.
- **Kill.** Fails -> the clientele effect does not reach deep-auction common stock; PREF/ETDX stays capacity-capped.
- Runner `research/sim/hyc.py` -> `data/research/program/hyc_out.txt`.

## Result — HYC (judged 2026-10-06 late; N 871): KILL
`research/sim/hyc.py` -> `data/research/program/hyc_out.txt`. BDCs are SIC 6799 in Sharadar (6726 absent): 6799 used as
the BDC proxy. REIT (n 8,169) xCO +21.9bp t 7.9, 26/29 yrs, but **2021-26 +2.9**; by year +40..+70 (1998-2006) ->
+1..+18 (2013-19) -> -17..+18 (2020-26). BDC~6799 (n 1,201) xCO +16.8 but 2021-26 +5.7, xCC -19.6 (t -3.6). Fails
the 2021-26 >= +15bp bar in both classes. **Class verdict (with FXD): the tax-clientele ex-date under-adjustment has
been arbitraged to ~0 wherever the auction is deep (REIT/BDC common, CEFs, ETFs) and survives only in thin-inventory
$25-par securities (preferreds, baby bonds, CEF preferreds). The PREF/ETDX capacity ceiling is structural.** No more
ex-dividend security classes without a new thin-inventory class.
- **Correction — PREF/ETDX is NOT Roth-only (2026-10-06 late; economics, no N; `etdx_margin.py` -> `etdx_margin_out.txt`).**
  The prose above says "taxable accounts likely net ~0 after dividend tax". Wrong for this book: held one night, the
  distribution is ordinary income (qualified holding period unmet) and the ex-date drop is a short-term capital loss;
  against the taxable book's ST gains both sit at the ordinary rate, so after-tax = (1 - tau) x pre-tax, like any ST
  trade (the under-adjustment exists because buy-and-hold taxable holders do NOT realize that loss). Wash sales only
  defer (skip re-buying a name within 31 days of a losing exit). **Taxable margin account (Reg T, 13% debit, 10bp round
  trip, 5% participation), pre-tax $/yr:** $2.3k CO 1x $475 / 1.5x $587 / 2x $689 (financing $54, worst night -2.2%);
  CC $321 / $393 / $464; $10k CO $1,103 -> $1,322 at 2x; $25k flat (capacity binds). **Stacking on the night leg's
  overnight equity** (the book is 1.0x overnight, Reg T allows 2x): each PREF/ETDX dollar is then borrowed at ~3.6bp/night
  (x3 over weekends) vs ~+30bp net edge -> ~$410/yr CO, ~$270 CC pre-tax at $2.3k (~$190-290 after tax, +8..+13pp).
  Margin amplifies only below ~$10k; above, capacity binds. Same unverified broker items (MOC on preferred/ETD symbols,
  open-auction exit) apply in the taxable account.
- **New-issue $25-par probe (no N): CEILING-KILL.** First listed close vs $25: preferreds median +0.28% (2010+, n 958),
  ETDs 0.00% (n 417); +20d drift ~= accrued coupon. No retail new-issue concession worth an allocation.

## Result — OVX H1 (judged 2026-10-06 late; N 870): PASS on VWAP; executable test registered below
`ovx.py` -> `ovx_out.txt`; 4,419 picks / 484 nights 2024-10..2026-09. Base close->open cross +14.3bp (t 1.0).
BOATS 20-04 VWAP vs open cross: +76.1bp, med +32.4, t 2.40, ex-top5 +44.2, cov 72%; halves +144 / +41 (t 1.44 / 3.10);
ADV top half +44 (t 2.9). All H1 bars pass. **Bigger finding: SIP pre-market VWAP 08:00-09:28 vs the open cross +46.6,
med +38.1, t 8.88, hit 63%, cov 93%; 04-08 +68.4 med +46.** Decomposition (BOATS-covered picks): close -> 20-24 +60,
-> 04-08 +59, -> 08-09:28 +48 (med +71), -> open cross +17: the loser bounce is in the price by the evening and the
opening cross clears ~40-50bp BELOW the pre-market tape. VWAP is not a fill -> executable test:

## Amendment — Study OVX-Q: sell night picks at the pre-market NBBO bid (pre-register; N 871 -> 872)
Written before any quote is read. SIP NBBO (Alpaca quotes) last quote in [tau-60s, tau] at tau = 08:00 / 09:00 / 09:15
/ 09:24 ET on the session after the pick; drop locked/crossed, spread > 10%. x_bid = bid/o_auc - 1, also x_mid and the
quoted half-spread. **Primary: tau = 09:24** (inside every broker's pre-market session, deepest pre-open book).
PASS if x_bid mean >= +15bp, median > 0, t(day) >= 2, ex-top5 > +10bp, both halves > 0, coverage >= 70%; report
by ADV half and a placebo (same tau on random non-pick losers is NOT available cheaply: instead report the same x for the
picks' own previous-session 09:24 bid vs that session's open cross = a baseline of the generic pre-open/open gap).
Kill: fails -> night exits stay in the open auction. Caveat logged up front: a limit sell at the bid assumes the bid
size is available; report median bid size $.

## Data documentation — FINRA OTC Transparency venue-mix panel (as requested)
- **Endpoint/dataset:** POST https://api.finra.org/data/group/otcMarket/name/weeklySummary —
  partitioned by weekStartDate (Monday) + tierIdentifier (T1/T2/"NMS"/OTCE). KEY-LESS (public
  dataset); the user's FINRA API key (env FINRA_API_KEY) still 401s on group regData — not needed.
- **Types used:** ATS_W_SMBL_FIRM + OTC_W_SMBL_FIRM (per-firm rows, summed across firms) as the
  numerator; ATS_W_SMBL / OTC_W_SMBL aggregates exist and match the firm-sums (validated on SPY
  week 2025-06-02: 50.4M ATS + 52.6M OTC shrink-adjusted).
- **Fields:** issueSymbolIdentifier, weekStartDate, totalWeeklyShareQuantity, totalWeeklyTradeCount,
  summaryTypeCode, initialPublishedDate.
- **Coverage:** 2021-12-06..2026-09-14, 250 weekly partitions = ALL weeks in the window (the
  dataset is a rolling archive; weeks before 2021-12 return 204). 2016-2021 is NOT in the API
  (the web download-portal files remain the un-scraped fallback).
- **Off-exchange share definition:** offshare_w = (ATS w-shares + OTC w-shares) / (the symbol's
  consolidated Sharadar/panel tape volume over the week's sessions). EQ18 ETFs sanity: mean 22.5%,
  median 23.2%, range 4.7-82.3% — plausible ETF off-exchange shares.
- **Auth:** none for this dataset (Bearer key unused; regData groups 401 as of 2026-10-06 — do NOT
  re-test with the same 20-char key, it appears truncated/invalid; user will reissue).
- **Lookahead control:** per-row initialPublishedDate; empirical lag 3.00-3.14 weeks (99% at exactly
  3.00). A trading day D sees the latest week with initialPublishedDate < D (strict). Publication
  hour unknown -> strictness accepted.
- **Caveats (documented in the study file):** holiday weeks have a shrunken 4-session denominator
  (inflates offshare ~25%; not separately filtered in the JUDGED run — reported in the per-year
  diagnostics); weeks with >100k firm rows would be asynchronously truncated (EQ18 short names
  not truncated); survivorship: today's EQ18 listing, not a live PIT ETF set (the 18 ETFs never
  delisted during 2021-26 — minor).
- **Storage:** data/research/finra/ats_etf.parquet (175,071 rows; fetcher research/sim/finra_ats.py
  caches per (symbol, weekStart) with 3 workers + 429 backoff).

## Result — VENM (N 867; judged 2026-10-06 evening): KILL
- **The conditioning does not survive the placebo.** IBS net by offshare LEVEL percentile:
  LOW +10.1 / MID +28.9 / HIGH -4.5 (no monotone pattern; a dead-center bump);
  TOP decile -2.3, BOTTOM -1.8; weekly-CHANGE buckets RISING +6.3 (t 1.25) / FALLING +21.0 (t 1.93,
  halves -13.5/+25.8 flip). PLACEBO (symbol-permuted state, seed 20261006): LOW +2.0 / HIGH +15.9
  t 2.68 — **the permuted state separates MORE than the real one**: bucketing captures sample
  noise, not a venue-mix state.
- **Ceiling also fails the gate:** even a PERFECT bucket effect (±20bp/trade on ~30-60 IBS
  trades/yr) is ≈ +0.6-0.8pp/yr before honest-capture haircut — one order below the +8pp bar,
  and the measured $/year at $3k is metric-noise ($12-53/yr).
- **Verdict: venue-mix state (FINRA weekly ATS+OTC share of the ETF's consolidated volume) carries
  no usable conditioning information for the IBS leg at the ETF tier. KILL.**
- **Per-STOCK extension (not run, classified):** attaching venue-mix to the night leg's loser
  pool is data-feasible but heavy (full-week NMS extracts > 100k rows/week need sorted paging or
  multiple async pulls; ~2-5h fetch). Priors from the ETF-tier result + the placebo failure argue
  the same dead end: do not pursue without a NEW mechanism hypothesis (e.g., a borrow-squeeze
  state that is NOT derivable from prices and differs from the killed FTD/threshold family).

## Result — OVX-Q (judged 2026-10-06 late; N 872): KILL — the pre-open "premium" is the spread
`ovx_q.py` -> `ovx_q_out.txt`. SIP NBBO at 08:00/09:00/09:15/09:24 on the session after the pick (cov 46-54% after the
<=10% spread filter; median half-spread 23-25bp; median bid size ~$140k). **09:24 bid vs open cross -13.7bp (med -10.2,
t -1.1, hit 41%); halves -7.5 / -17.5; ADV halves -10.5 / -18.8.** Mid vs open +28.5 (t 3.9): the VWAP "premium" of
OVX H1 is the half-spread; the open cross gives a mid-like price for free. Control (same names, pick day, before the
crash): 09:24 bid vs open -5.5, median 0 -> after a crash day the open clears near the pre-market bid. Exploratory
(touched, not judged): a resting limit at the 09:00 mid, fallback to the open: fill 80%, +8.3bp vs open t 1.08 (no queue
haircut) — adverse selection eats it. **The opening auction stays the night-leg exit; the 23/5 / BOATS exit (index_beat
B1) is closed on 2024-26 data: BOATS spreads are wider than pre-market, so the BOATS VWAP edge (+76) is the same
spread artifact.** Lesson: any "sell in the tape beats the auction" result must be judged at the bid, never VWAP/mid.
- **ETDX attack (official crosses 2021-26, ETD n 1,995; descriptive).** Issuers: 108; top-10 = 34% of events; **95% of
  issuers have mean CO > 0; ex-top-5 issuers CO +45.5 med +42.3, CC +40.4.** Scales with the coupon as the tax mechanism
  predicts: coupon/payment terciles (median 138 / 164 / 207bp) -> CO +33.0 / +36.5 / +62.3, CC +21.8 / +31.8 / +62.3
  (under-adjustment 22-30% of the coupon). Not a few-issuer or few-event artifact.
- **Pre-test ceiling kills (2026-10-06 late):** preferred-index (PFF/PGX) month-end rebalance flow (no free historical
  holdings: iShares asOfDate returns HTML; month-end proxy <= 12 x ~50bp on part of capital < +8pp); royalty-trust /
  thin-common ex-div (HYC class verdict + small per-event under-adjustment).
- **Capital stacking on the taxable book (economics, no N; `etdx_stack.py` -> `etdx_stack_out.txt`).** V7 book (night 0.5
  + IBS 0.5, idle IBS cash counted as occupying buying power in BIL): overnight exposure on ex-eves median 0.64-0.70x
  equity -> Reg-T headroom ~1.3x. PREF/ETDX in that headroom (5% participation, 10bp round trip, incremental debit at
  12%): **$2.3k CO +$498/yr pre-tax (+21.6%), CC +$318 (+13.8%); $5k +$802 / +$547; $10k +$1,091 / +$623; $25k +$1,361
  / +$664**; financing $69-133/yr. After tax (x0.7) the $2.3k taxable gain is ~+15% (CO) / ~+10% (CC) of equity, on top of
  the book, without displacing a night or IBS dollar. **Capacity is shared across accounts:** Roth + taxable draw on the
  same auctions, so combined dollars plateau at the single-account $25k row once total equity > ~$10k.

## Study DDR — delayed-decision reversal: the lag+5 entry of the night signal (3rd-robot session; 1 judged rule; program N 858 -> 859)

**Why.** PCAL's pre-named lag controls were assumed to decay with lag. They did not: on the 2021-26
window the lag+1 entry is ~0 (t -0.85) but the lag+5 entry PASSES the full program bar (+57.4bp/night
net at tier, t_cl 3.41, both halves +61.5/+53.2, median +27.3, ex-top-5 +36.2, ~7.7k trades). If real,
"buy at the close five sessions after an -8%/IBS<0.10 crash day, hold one night" is a NEW leg whose
entry timing exploits the continuation of the after-crash weakness that the on-time rule does not.

**Contract (frozen).** The PCAL C2 machinery EXACTLY (same eligibility, gates, dedupe corr <= 0.7,
night_sizing vol_min 0.60/crowd 30/cap 10%, delisting -1.0 rules, dividend credit, one-look NO tuning).
Entry = close of the 5th session after the crashing day; exit = the next session's open.

**Judge window (clean, pre-registered):** 1998-01-01 .. 2020-12-31 Sharadar SEP, delisted-complete.
2021-2026 = already-read exploratory (PCAL), reported as context only, never judged.

**Gates (frozen):** n >= 300 events; day-clustered t >= 2.0 on pooled per-night net at `tier`;
halves (1998-2009 / 2010-2020) both net-positive; median trade net-positive; ex-top-5 net-positive;
2x-tier stress net-positive; hit rate >= 55%; proxy-abnormal (vs same-day equal-weight eligible
overnight) positive mean AND positive median.

**Kill:** median net <= 0, or the mean carried by <5 events, or halves sign-disagree. Verdict
PASS/WEAK/REJECT recorded in NEXT.md's do-not-redo table; no size-ups, no deployment regardless.

**No N beyond the registered increment; diagnostic economics at $2.3k/$10k/$25k reported in the study note.**

## Study PRV — liquidity-provision reversal in thin $25-par paper (pre-register; N 872 -> 873)
`date`: Tue Oct 6 2026, late. No non-ex-date preferred/ETD return conditioned on a prior move has been read.
- **Mechanism.** Dealer inventory in exchange-listed preferreds/baby bonds is thin (closing cross median ~$5k), holders
  are retail. An idiosyncratic down-move with no news is a liquidity shock nobody absorbs at the close; it should revert
  as dealers/arbs lean in. Distinct from IBS (no equity-vol/tech beta) and from PREF/ETDX (non-ex nights).
- **Rule (frozen).** SEP Domestic Preferred + SFP ETD/CEF Preferred, raw close $10-60, 20d median $vol >= $100k. Exclude
  sessions T-1..T+2 around any distribution ex-date of that name, and names with close(T) < $15 (distress). Idio move
  m = close(T)/close(T-1) - 1 minus the same-day cross-sectional median of the universe. Signal: m <= -2%. Trade: buy
  close(T); CO = sell open(T+1), CC = sell close(T+1). Placebo: m >= +2% (mirror), and |m| < 0.5% (control).
- **Judge.** J1 1998-2015 and J2 2016-2026 (Sharadar vendor closes): CC mean >= +20bp, median > 0, day-clustered t >= 2,
  ex-top-5 > +10bp, >= 75% of years > 0 in each. **J3 (decisive, artifact check):** official SIP crosses 2021-26 for the
  signals (entry = T closing cross, signal recomputed on CROSS prices) CC >= +15bp net of 10bp round trip. Vendor closes
  for thin names can be last-trade-at-bid: bid-ask bounce would fake a reversal, so J1/J2 alone cannot PASS.
- **Kill.** J3 fails, or J1/J2 sign-unstable.
- Runner `research/sim/prv.py` -> `data/research/program/prv_out.txt`.

## Result — PRV (judged 2026-10-06 late; N 873): KILL (bid-ask bounce signature)
`prv.py` -> `prv_out.txt`. J1 1998-2015 signal (m <= -2%) CC -4.2bp (med +18, t 1.04) -> fails. J2 2016-26 CC +19.4
(t 3.98), CO +33.6 (t 13.8) but the **mirror (m >= +2%) reverts as hard: CO -20.8 (t -14.0, 0/11 years > 0)**, control
~0. Symmetric reversal of vendor closes in thin names = last-trade-at-bid/ask bounce, not dealer-inventory reversal
(an inventory story predicts the down side only). J3 not fetched (registered: J1 failure kills; the symmetry already
answers the artifact question). Rule: in thin securities, any daily-close reversal must show asymmetry vs its mirror
before an official-cross check is worth running.
- **ADR preferreds under the frozen PREF-EX rule (Sharadar SEP 'ADR Preferred Stock', descriptive, same rule/guard):**
  1,212 events / 61 names, CO +59.8bp med +49.3 t 16.0, ex-top5 +57.7, 22/22 years, 2021-26 +61.3; CC +30.5 (2021-26
  +51.4); drop/div 0.84; ~46 ex-nights/yr since 2021. Same clientele effect, small capacity add; Alpaca ".PR" symbols are
  already in the shadow's filter. Official crosses not fetched (low marginal value vs ETDX).

## Study PXB — passive ex-eve bid entry for PREF/ETDX (pre-register; N 873 -> 874)
`date`: Tue Oct 6 2026, late. No intraday quote/trade on an ex-eve has been read.
- **Mechanism.** Before ex, taxable holders sell (that is the clientele flow). A resting limit buy at the NBBO bid in the
  afternoon of T-1 can be filled BY those sellers at the bid (~19bp below the mid the close cross prints at), and it
  draws on continuous-book liquidity instead of the thin closing cross (capacity). Risk: adverse selection (fills only
  when the price is falling).
- **Rule (frozen).** Events = official-cross rows of PREF (pref/cross_rows) + ETDX (etdx/cross_rows), 2021-26. Limit buy
  at the SIP NBBO bid as of 14:00 ET on T-1 (last quote in 13:59-14:00, spread <= 5%). Filled if any 1-min bar low on
  T-1 in 14:00-15:50 <= bid - $0.01 (conservative: a print THROUGH our price). Unfilled -> MOC at the closing cross
  (as now). Exit = T opening cross (CO) and T closing cross (CC), + dividend.
- **Judge.** Blended (filled at bid, else MOC) minus the MOC-only baseline on the same events: mean >= +5bp, median >= 0,
  t(day) >= 2, both years-halves (2021-23 / 2024-26) > 0. Report fill rate, filled-only return vs those events' MOC
  return (adverse-selection measure), and the extra $ capacity (min(bid size, our order)).
- **Kill.** Blended <= baseline: passive entry is adversely selected; keep MOC.
- Runner `research/sim/pxb.py` -> `data/research/program/pxb_out.txt`.

## Result — PXB (judged 2026-10-06 late; N 874): KILL as a replacement; positive as an add-on tranche
`pxb.py` -> `pxb_out.txt`; 7,265 PREF+ETDX events 2021-26. Quoted at 14:00 71%, filled (print through bid) 25%, median
half-spread 17bp, median bid size $7.1k. **Blended - MOC: -1.9bp (t -2.6), both halves negative -> KILL as registered.**
Adverse selection: filled events earn +33.6bp CO at our bid vs +41.4 at MOC on the same events; the close cross lands
4.5bp below our fill (price keeps falling). **But the filled tranche is itself +33.6bp CO (t 11.9) / +20.1 CC and draws
on bid liquidity (median $7k) instead of the closing cross:** an ADD-ON passive order (MOC at p of the cross PLUS a resting
bid for extra size) adds fills on ~25% of events at ~+34bp, i.e. ~+20-25% deployed $ where the cross caps the account
($10k+). Descriptive, not judged; queue position ignored (conservative fill rule partly offsets).

## Study THN — thin common ex-nights: mechanism test (pre-register; N 874 -> 875)
`date`: Tue Oct 6 2026, late. Not read: any common-stock ex-night with 20d median $vol < $1M.
- **Prediction (tax clientele x thin inventory).** Thin (20d $vol $100k-$1M) REIT 6798 / BDC~6799 commons (non-qualified
  distributions) show the under-adjustment (xCO >= +20bp, 2021-26 >= +15bp, t >= 2, median > 0). Thin OTHER commons
  (mostly qualified dividends: no tax reason to sell pre-ex) show ~0 (|xCO| < 10bp) -> the placebo. Same frozen HYC rule
  otherwise (price >= $5, y 0.5-6%, dividend guard, excess vs own 60-session non-ex mean).
- **Outcomes.** Thin REIT/BDC pass AND placebo ~0 -> mechanism confirmed, new (small) capacity; both ~0 -> thin-inventory
  alone is not enough; placebo also large -> the effect is thin-stock bounce, not tax (and PREF/ETDX needs a re-check).
- Runner `research/sim/thn.py` -> `data/research/program/thn_out.txt`.

## Result — THN (judged 2026-10-06 late; N 875): mechanism prediction FAILS; PREF/ETDX verdict unchanged, mechanism claim downgraded
`thn.py` -> `thn_out.txt` (20d $vol $100k-$1M). xCO full / 2021-26: thin REIT +69.1 / -11.5; thin BDC~6799 +22.3 / -31.5;
**thin OTHER commons (qualified-dividend placebo) +36.0 (t 16.7, 27/29 yrs) / +4.9**, scaling with yield (+29 / +44 / +50
/ +101bp). Registered outcome: the placebo is large historically -> the pre-2021 thin-stock ex-night effect was NOT
tax-specific, and since 2021 it is gone in ALL thin commons. **Consequences:** (1) thin REIT/BDC is not new capacity
(KILL). (2) PREF/ETDX re-check: in its own judge window (official crosses 2021-26) the placebo class is ~0 while PREF/ETDX
is +40..+60bp, non-ex nights ~0 and the crosses print at mid, so the PREF/ETDX verdict stands. (3) **Mechanism wording
corrected:** a dividend-proportional ex-date under-adjustment once common to thin stocks and now surviving only in $25-par
income paper (preferreds incl. bank prefs with QUALIFIED dividends +28bp, baby bonds, CEF and ADR preferreds). The tax
story (flat-trading coupons) is a contributing explanation, not a demonstrated one; the coupon scaling supports
under-adjustment in proportion to the payment, not tax specifically. Forward shadow is the arbiter of persistence.

## Study SSR-TD — Rule 201 trigger-day intraday path (pre-register; N 875 -> 876)
`date`: Tue Oct 6 2026 (intraday-sleeve loop, `research/drafts/intraday_sleeve_frontier_2026-10-06.md`). Not read: any
minute bar of any stock on a Rule 201 trigger day. SSR-LIFT (T+2) and the "-25% by 15:00" daily proxy are the only prior
looks; neither measured the path after the -10% cross on T.
- **Mechanism.** At the first trade <= 0.90 x prior official close, Rule 201 bars short sales at/below the national best
  bid for the rest of T and all of T+1. Aggressive short sellers (the marginal sellers in a crash) must post above the bid.
  Prediction: the post-trigger path is better than the smooth trend across thresholds implies (a discontinuity at -10%).
- **Data.** Alpaca SIP minute bars, adjustment=raw, 2021-01..2026-09 (2016-2020 SEALED as the holdout for anything that
  passes). Universe: common-stock tickers ([A-Z]{1,5}), prior raw close >= $5, 20d ADV >= $5M (Sharadar), day low <= -7%.
  No T+1 condition (the SSR-LIFT event file's L1 filter is lookahead here and is dropped).
- **Rule.** Threshold k in {-8, -9, -10, -11, -12}%. Trigger minute = first minute 09:30-15:00 whose low <= (1+k) x prior raw
  close. Gap triggers (09:30 bar open already <= k) are a separate arm (GAP) from intraday crosses (CROSS). Long entry at the
  NEXT minute's VWAP; exit at the 15:59 bar close (proxy for the closing cross); also +30m, +60m horizons (descriptive).
  Hedge: minus SPY over the same window (beta 1, descriptive). Costs: 10bp/side base, 20bp/side shock.
- **Gate (CROSS arm, k = -10%, long to close).** Net of 10bp/side: mean > 0 with day-clustered t >= 2.5, median > 0, both
  halves (2021-23, 2024-26) > 0, ex-top-5 days > 0; AND the discontinuity D = r(-10) - mean(r(-9), r(-11)) > 0 with t >= 2
  (paired by event day). Pass on the trade without D = a crash-bounce effect, not SSR (still reported as a trade candidate,
  then judged on sealed 2016-20). Kill: any gate fails -> trigger-day long is dead; no k/horizon re-tuning.
- Runner `research/sim/ssr_td.py` (fetch + judge) -> `research/sim/ssr_td_out.txt`.

## Study SS-LETF — single-stock leveraged-ETF rebalance flow into the close (pre-register; N 876 -> 877)
`date`: Tue Oct 6 2026. Not read: any late-day return conditioned on single-stock LETF presence. Prior related deaths:
Gao last-half-hour on 6 index ETFs (dead), LETF index flow (daily, dead). Neither had a single-name LETF whose flow is a
material share of the underlying's volume (MSTR: 2x-fund $vol ~18% of MSTR $vol in 2025-26; IONQ/RGTI/OKLO/BMNR 9-25%).
- **Mechanism.** A daily-reset fund with leverage L must trade L(L-1) x AUM x r_day of the underlying (via swap dealers) near
  the close, in the direction of the day's move for both long (L=2: 2x) and inverse (L=-2: 6x) funds. Prediction: where that
  demand is large relative to the underlying's volume, 15:45 -> closing-cross return continues the 09:30 -> 15:45 move.
- **Data.** Alpaca SIP 5-min bars (raw) + official crosses, 2022-07..2026-09; Sharadar SFP for the fund map and fund $vol.
  Intensity I(i,d) = sum over i's single-stock funds of w(L) x 20d median fund $vol / 20d median underlying $vol, lagged one
  day, w = L(L-1)/2 (1 for 2x, 3 for -2x); I = 0 before the first fund lists and for controls. Universe: common stock,
  price >= $5, 20d ADV >= $100M (all names with any 2x fund plus every other name above the bar as controls).
- **Model.** r_post (15:45 last trade -> official close) = day FE + b r_pre + c (I x r_pre); day-clustered SE. Prediction c > 0.
- **Trade.** I >= 0.05 and |r_pre| >= 3%: at 15:46 take the direction of r_pre, exit in the closing cross. Cost 5bp/side
  (shock 10bp). Long and short reported separately (short needs borrow; long-only is the cash/Roth version).
- **Gate.** c > 0 with t >= 2.5; trade net mean > 0 with day-clustered t >= 2.5, median > 0, both halves (2022-07..2024-12,
  2025-01..2026-09) > 0, ex-top-5 days > 0; placebo: same trade on controls (I = 0) with |r_pre| >= 3% is smaller (paired
  difference t >= 2). Kill: any fails -> single-stock LETF close flow is not tradable from 15:45; no window re-tuning.
- Runner `research/sim/ss_letf.py` -> `research/sim/ss_letf_out.txt`.

## Result — SSR-TD (judged 2026-10-06; N 876): KILL
`ssr_td.py` -> `ssr_td_out.txt`; 70,802 events / 1,440 days 2021-01..2026-09 (7,107 dropped: missing bars or last-minute
close >1% from Sharadar raw close). CROSS arm k=-10%, long trigger+1 VWAP -> 15:59, net 10bp/side: EW-day +3.4bp t 0.43,
trade mean +8.6 / median +18.2, SPY-hedged -7.0, ex-top-5 -1.2, H1 +23.5 / H2 -6.4 (2021 +68 carries it). Discontinuity
D = r(-10) - mean(r(-9), r(-11)) = -10.9bp t -9.7 (wrong sign): no SSR bounce. Every threshold is gross +17..+27bp at
+30/+60m (a generic post-cross bounce of ~one round-trip cost, same at -8% as -12%: not Rule 201) and decays to the close.
GAP arm (open already <= k): long 09:31 -> close loses -71..-89bp/EW-day (t -3..-5), both halves -> gap-down continuation,
consistent with the old "gap-down reclaim long dead" and "-25% by 15:00 keeps falling"; the short side is under SSR all day
(passive above-bid only) and often HTB: not executable as a cash/margin short. No k/horizon re-tuning.

## Study GAP-SHORT — short the >=10% gap-down from 09:31 to the close, judged on sealed 2016-20 (pre-register; N 877 -> 878)
`date`: Tue Oct 6 2026. Origin: SSR-TD's GAP arm (2021-26, TOUCHED): long 09:31 -> close -71..-89bp/EW-day, t -3..-5,
both halves. Not read: any 2016-2020 minute bar of any gap-down stock (sealed by SSR-TD).
- **Mechanism (hypothesis).** A >=10% opening gap-down is news-driven repricing that continues: forced/slow sellers
  (funds cutting risk, stop/margin liquidations, index-weight holders) keep selling through the day, while Rule 201 is in
  force all day (the open triggered it), so short liquidity provision is passive-only. Our trade is that passive short.
- **Rule.** Universe: common stock ([A-Z]{1,5}), prior raw close >= $10, 20d ADV >= $20M (PRIMARY: more likely ETB);
  BROAD = $5 / $5M reported. Gap: the 09:30 minute bar's open <= 0.90 x prior raw close. Short at the 09:31 bar VWAP (under
  SSR a short must be priced above the NBB: VWAP proxies a resting offer; fill realism is the EXECUTION question), cover at
  the 15:59 bar close. Cost 10bp/side; shock 20bp/side. No borrow fee (intraday round trip). P&L = -(r) - cost.
- **Gate (PRIMARY, 2016-01..2020-12).** Net EW-day mean > 0 with day-clustered t >= 2.5, trade median > 0, both halves
  (2016-18, 2019-20) > 0, ex-top-5 days > 0, positive at 20bp/side. Also report 2021-26 PRIMARY (touched), hit rate,
  worst trade, worst day, and the squeeze tail (share of trades losing >10%). Kill: any primary gate fails -> gap-down
  continuation is a 2021+ pattern, not an edge.
- Runner `research/sim/gap_short.py` -> `research/sim/gap_short_out.txt`.

## Result — GAP-SHORT (judged 2026-10-06; N 878): KILL (fails t gate on the sealed window; dead on 2021-26 liquid)
`gap_short.py` -> `gap_short_out.txt`. PRIMARY ($10 / $20M ADV) 2016-20: net +61.0bp/EW-day **t 2.45 (< 2.5)**, trade mean
+90.9 / median +79.5, hit 0.55, ex-top-5 +40.1, halves +46 / +119, 2019 -27, 20bp/side +70.9; but worst trade -58%, 6% of
trades lose >10%, p90 adverse excursion +13%. **PRIMARY 2021-26 (touched): -8.2bp t -0.37, trade mean -25.9, 2022-24 each
-63..-108, worst trade -212%.** BROAD 2021-26 +48.6/EW-day t 2.45 but trade mean -5.6: carried by sparse low-count days,
SPY-adj +0.3. Read: gap-down continuation was a 2016-20 (and 2020-crash) pattern in liquid names, gone since 2021, with
an un-capped squeeze tail on the short side. Executable short under all-day SSR untested and now moot. No re-tuning.

## Study BTC-FIX — spot-bitcoin ETF NAV-fixing window flow (pre-register; N 878 -> 879)
`date`: Tue Oct 6 2026. Not read: any intraday BTC return by hour. Prior crypto work: daily IBS only (rejected).
- **Mechanism.** Since 2024-01-11 US spot-bitcoin ETFs strike NAV on the CF Benchmarks NY variant (observation window
  15:00-16:00 ET). Authorized participants / issuers buy (sell) BTC for creations (redemptions) to match that window, so
  same-day net flow becomes price pressure inside 15:00-16:00 ET and should partly reverse afterwards (liquidity provision).
- **Data.** Alpaca crypto BTC/USD 1-min bars 2021-01-01..2026-09-30 (24/7). ET trading days (Mon-Fri, NYSE calendar).
- **Tests (pre vs post 2024-01-11, diff-in-diff).** (1) |W| where W = BTC log return 15:00-16:00 ET: post/pre ratio vs
  the same ratio for the 13:00-14:00 and 11:00-12:00 hours (window volatility share rises if flow trades there).
  (2) Reversal: corr(W, R) with R = 16:00-18:00 ET return; prediction post corr < pre corr (more negative).
  (3) Directional trade (needs a pre-window flow signal): sign of the 09:30-15:00 ET BTC return as a flow proxy (retail ETF
  buying follows price) -> long/short BTC 15:00 -> 16:00; and the reversal trade: at 16:00 fade W to 18:00 (24/7 spot, or
  IBIT next open is NOT the same trade). Cost 5bp/side (IBIT/spot).
- **Gate (for a trade candidate).** Post-period net mean > 0, day-clustered t >= 2.5, median > 0, both post halves
  (2024, 2025-26) > 0, ex-top-5 > 0, AND the same rule pre-2024 is materially smaller (diff t >= 2) — otherwise it is a
  generic BTC pattern, not ETF flow. Kill: tests (1)-(2) show no post shift AND trades fail -> fixing flow is absorbed.
- Runner `research/sim/btc_fix.py` -> `research/sim/btc_fix_out.txt`.

## Result — BTC-FIX (judged 2026-10-06; N 879): KILL
`btc_fix.py` -> `btc_fix_out.txt`; Alpaca BTC/USD 1-min, 755 pre / 682 post trading days. (1) The 15:00-16:00 ET window's
mean |return| FELL post-launch relative to other hours (W ratio 0.73 vs 0.84/0.93; relative 0.83): no added window
pressure. (2) corr(W, 16-18h) moved -0.05 -> -0.16 (a mild post-window give-back), but the fade trade nets +0.2bp t 0.09.
(3) Flow-proxy continuation is the wrong sign (corr(pre, W) +0.08 -> -0.08); its mirror grosses only ~+5bp (< 10bp round
trip). ETF fixing flow is absorbed in BTC's depth. Do not test IBIT/BTC fixing variants.

## Result — SS-LETF (judged 2026-10-06; N 877): MECHANISM CONFIRMED, TRADE KILLED
`ss_letf.py` -> `ss_letf_out.txt`; 674,593 stock-days 2022-07..2026-09, 224 names with a single-stock LETF.
Day-FE regression: c (I x r_pre) +0.050 **t 3.11**; placebo paired day diff treated - control +5.9bp **t 2.82**: single-stock
LETF rebalancing does push 15:45 -> close in the day's direction. But the size is +3..+5bp gross (I buckets 0.02+), and the
registered trade (I >= 0.05, |r_pre| >= 3%) nets -6.6bp/trade at 5bp/side (t -2.57), long -9.0, short -4.4, every year <= 0.
Highest-intensity names (MSTR I~0.30 +12bp gross, BMNR +16, SMCI +16) are post-hoc and still ~+$7/event at $9k intraday.
Read: real forced flow, absorbed to well inside one round trip by the 15:45 entry. No I/window re-tuning.

## Study PREF-DIP — resting dip bids in thin $25-par paper, exit in the closing cross (pre-register; N 879 -> 880)
`date`: Tue Oct 6 2026. Not read: any non-ex-date intraday path of a preferred / baby bond. PXB (ex-eve passive bid at
14:00 NBB) is the only related look; it showed filled bids still earn on ex-eves with mild adverse selection.
- **Mechanism.** Thin, retail-dominated $25-par paper (quoted spreads 38-88bp) has few market makers; an impatient retail
  sell pushes the print well below fair value and it recovers within the session. Who pays: the impatient seller. Why it
  persists: capacity is a few $k per name-day, below institutional interest (small-account advantage).
- **Data.** Universe = Sharadar SEP "Domestic Preferred Stock" ([A-Z]{1,5}-P[A-Z]{1,2} -> Alpaca XXX.PRY) + SFP "ETD"
  baby bonds; prior raw close $10-60, 20d median $vol >= $100k. Alpaca SIP 1-min raw. Judge 2021-01..2026-09; 2016-20
  SEALED. Exclude ex-dates and the session before (Sharadar dividend actions).
- **Rule.** Resting limit buy at L = prior official close x (1 - k), k = 1.0% PRIMARY (0.5%, 1.5% descriptive), live
  09:45-15:30. Fill only if a minute LOW < L - $0.01 (traded through by a cent); fill price L. Exit at the official close
  (Sharadar closeunadj on T = closing cross). Cost: 0 entry (passive), 5bp exit; shock 20bp exit. One fill per name-day.
- **Gate (PRIMARY).** Net mean per fill >= +15bp with day-clustered t >= 2.5, median > 0, both halves (2021-23, 2024-26) > 0,
  ex-top-5 days > 0, > 0 at the 20bp shock, and market-adjusted (minus the EW close/prev-close of the whole universe that
  day) > 0. Kill: any fails. Report fills/day, $ capacity proxy (fill-minute $vol), worst fill, worst day.
- Runner `research/sim/pref_dip.py` -> `research/sim/pref_dip_out.txt`.

## Study SQZ — forced short covering on gap-ups in high days-to-cover names (pre-register; N 880 -> 881)
`date`: Tue Oct 6 2026. Not read: any gap-up intraday return split by short interest. Old deaths: stock gap-and-go
(liquid universe, negative both halves), Lab-AS/AU gappers (no SI split), DS4 night tilt by DTC (overnight, dead). None
conditioned an intraday gap-up on short-seller pressure.
- **Mechanism.** A >= 5% opening gap-up in a name with large short interest relative to volume (days-to-cover) puts shorts
  through loss limits / margin calls; their covering is forced buying that should carry the stock up through the session.
  Counterparty: the forced short. Control: same gap-ups with low DTC.
- **Data.** Existing gm1 store (Alpaca SIP 1-min, adjustment=all, top-40 |gap| >= 3% names/day, price >= $3, ADV >= $5M,
  2020-11..2026-09) + its daily panel for the prior close; FINRA short interest (data/research/night/finra_si, bi-monthly),
  usable from settlementDate + 10 business days (publication lag, conservative).
- **Rule.** Gap = 09:30 minute open / prior close - 1 >= +5%. Long at the 09:31 bar VWAP, exit 15:59 close; cost
  10bp/side (shock 20bp). Arms by latest available DTC: HIGH >= 5, MID 2-5, LOW < 2.
- **Gate.** HIGH net EW-day mean > 0 with day-clustered t >= 2.5, median > 0, both halves (2021-23 incl. 2020-11/12,
  2024-26) > 0, ex-top-5 days > 0; AND HIGH - LOW (paired same-day where possible, else pooled diff) t >= 2. Report worst
  trade/day, hit, median win/loss. Kill: any fails -> short covering is not a tradable intraday force from 09:31.
- Runner `research/sim/sqz.py` -> `research/sim/sqz_out.txt`.

## Result — SQZ (judged 2026-10-06; N 881): KILL as registered; post-hoc branch -> GUF-LOW
`sqz.py` -> `sqz_out.txt`; 23,995 gap-ups >= 5% (gm1, 2020-11..2026-09). HIGH DTC long: -19.3bp/EW-day net t -1.11,
median -59.5 -> FAIL. Short covering is a real force (HIGH - LOW +82.6bp paired, t 3.41) but does not make the long
profitable. Post-hoc (not a pass): LOW-DTC gap-ups fade hard (long -102.7bp/EW-day net t -6.04, trade median -94, both
halves, every year but 2020) and NA (no SI record) -219bp. Branch registered below and judged ONLY on untouched data.

## Study GUF-LOW — short >= 5% gap-ups in low days-to-cover names, 09:31 -> close (pre-register; N 881 -> 882)
`date`: Tue Oct 6 2026. Discovery data (2020-11..2026-09, gm1) is TOUCHED. Judge = 2016-01-04..2020-10-30, never read
for gap-ups at minute level by this program (GAP-SHORT read only gap-DOWNS). Old related deaths: liquid-universe gap-up
fade (t 0.5-0.7, RS:722) and gap-up >= 15% fade (+55bp gross, "needs HTB", RS:650) — neither split by short interest,
which is what makes the short side borrowable and removes the covering bid.
- **Mechanism.** The opening gap-up is set by premarket/retail demand; with few shorts there is no forced covering to
  sustain it and the overshoot is faded through the session. Counterparty: open-chasing buyers. Low DTC also proxies an
  available borrow (crowded shorts are the HTB ones).
- **Rule.** Sharadar common stock [A-Z]{1,5}, prior raw close >= $3, 20d ADV >= $5M. Gap = 09:30 SIP minute open (raw) /
  prior raw close - 1 >= +5%. DTC = FINRA consolidated SI daysToCover usable from settlementDate + 10 business days
  (45-day staleness cap). LOW = DTC < 2 (PRIMARY), HIGH >= 5. Short at the 09:31 bar VWAP, cover at the 15:59 bar close.
  Cost 10bp/side; shock 25bp/side. No borrow fee (intraday). Liquid subset (>= $10, >= $20M) reported.
- **Gate (LOW, 2016-01..2020-10).** Short net EW-day mean > 0, day-clustered t >= 2.5, trade median > 0, both halves
  (2016-18, 2019-20.10) > 0, ex-top-5 days > 0, > 0 at 25bp/side; LOW short - HIGH short > 0 with t >= 2. Report worst
  trade, share losing > 20%, worst day. Kill: any fails.
- Runner `research/sim/guf_low.py` -> `research/sim/guf_low_out.txt`.
- **Amendment (before any outcome was read):** key-less FINRA consolidated SI returns no rows before 2018 (probe: 2016-06
  .. 2017-12 all HTTP 204; 2018-03 has 15,486). The DTC-split judge window is therefore the first available settlement
  date in 2018 .. 2020-10-30; halves become 2018-19 / 2020. Gap-ups 2016-17 (no DTC) are reported only as an all-DTC
  descriptive arm, not judged. Gate otherwise unchanged.

## Result — GUF-LOW (judged 2026-10-06; N 882): KILL on the untouched window
`guf_low.py` -> `guf_low_out.txt`. Judge 2018-01-12..2020-10 (first key-less FINRA SI), 13,409 gap-ups >= 5%.
LOW-DTC short: **-18.3bp/EW-day net t -0.43**, trade mean -60.0 / median -38.5, hit 0.47, halves +23.2 / -73.5, by year
+93 / -68 / -73; liquid subset -65.1 t -1.45; LOW - HIGH -8.8bp t -0.19 (the DTC split that defined the arm is flat).
2016-17 all-DTC descriptive: +23bp t 1.67. Read: the 2021-26 low-DTC gap-up fade (long -103bp t -6) is a retail/meme-era
pattern, absent in 2018-20. Lesson repeated from GAP-SHORT: an intraday stock pattern found only in 2021-26 must be judged
on pre-2021 minute data before it is believed. No DTC/gap re-tuning.

## Result — PREF-DIP (judged 2026-10-06; N 880): KILL
`pref_dip.py` -> `pref_dip_out.txt`; 803 names, 511,800 name-days 2021-26 (ex-dates excluded). PRIMARY k=1%: 84,966 fills
(59/day), net/fill **-7.5bp**, median +0.5, hit 0.50, halves -10.5 / -2.5, 20bp-exit -22.5 -> FAIL (bar +15bp). k=0.5%
-16.1, k=1.5% -1.3. EW-day means are positive (+13.9 / +24.1, t 9-10) only because heavy-fill days (pref-market selloffs)
lose: fills vs the same-day EW universe return are **+28bp (k 1%) / +45bp (k 1.5%)** -> idiosyncratic dips revert,
systemic dips continue. That relative number is close-to-close and NOT executable; a real hedge is a new test (below).
- **PREF-DIP-H descriptive (2021-26, no N; the touched window):** an executable PFF (or PGX) short from the fill minute to
  15:59 leaves the k=1% fill at -7.5bp (median +0.3), k=1.5% -1.7: corr(fill r, PFF) is only 0.25-0.30 and the hedge
  removes nothing. The +28bp "mkt-adj" above was the close-to-close universe move (it contains the morning dip itself),
  not an executable hedge. Branch closed; no 2016-20 holdout fetch.

## Study LIQ-CASC — fade crypto perp liquidation cascades (pre-register; N 882 -> 883)
`date`: Tue Oct 6 2026. Not read: any crypto open-interest series or intraday crypto event return. Prior crypto work:
daily IBS (rejected), BTC-FIX (ETF window, killed today).
- **Mechanism.** In a long-liquidation cascade, exchange risk engines market-sell levered longs regardless of price; the
  footprint is a sharp open-interest (OI) drop together with a sharp price drop. Forced selling overshoots and reverts once
  the engine is done. Counterparty: liquidated longs. Mirror: short squeezes (OI drop + price spike) -> fade down.
- **Data.** Binance USD-M BTCUSDT (PRIMARY) and ETHUSDT 5-min `metrics` (sum_open_interest, data.binance.vision, from
  2021-12); price = Alpaca crypto 1-min (BTC/USD, ETH/USD). OI snapshot at create_time t is used only from t + 5 min.
- **Event.** 15-min window (3 metric steps) ending t: OI change <= -3% AND price change <= -1.5% (LONG-LIQ); OI <= -3% AND
  price >= +1.5% (SHORT-SQZ). Re-arm only after 4h. CONTROL: same price thresholds with OI change >= 0.
- **Trade.** Enter at the 1-min close at t + 5 min (data latency), fade the move (long after LONG-LIQ, short after SHORT-SQZ),
  exit at +60m (PRIMARY) / +240m (descriptive). Cost 5bp/side (IBIT/CME-level); shock 25bp/side (retail spot fees).
  US-hours subset (entry 09:35-15:00 ET, IBIT-executable) reported.
- **Gate (BTC LONG-LIQ, 60m).** Net mean > 0 with day-clustered t >= 2.5, median > 0, both halves (2021-12..2023,
  2024..2026-09) > 0, ex-top-5 > 0, LIQ - CONTROL > 0 with t >= 2. Kill: any fails.
- Runner `research/sim/liq_casc.py` -> `research/sim/liq_casc_out.txt`.

## Result — LIQ-CASC (judged 2026-10-06; N 883): KILL
`liq_casc.py` -> `liq_casc_out.txt`; Binance UM 5-min OI 2021-12..2026-09. BTC LONG-LIQ (OI <= -3% & px <= -1.5% in 15m,
n 51) fade 60m **-14.3bp net t -0.71**, 240m -39.3, both halves negative; LIQ - CTRL-DOWN -32.6bp t -1.32 (wrong sign).
ETH LONG-LIQ -19.5 / -29.9; SHORT-SQZ fades negative both coins. Forced liquidation does not overshoot-and-revert at
60-240m; it continues relative to an ordinary drop. Post-hoc observation only (not a pass): BTC CTRL-DOWN (drop with OI
rising) 240m +46bp t 2.48, ETH +20.7 t 1.48 — +6bp at 25bp/side retail spot fees; not pursued.

## Study ETF-THIN — dip bids below hedged fair value in thin benchmark-tracking ETFs (pre-register; N 883 -> 884)
`date`: Tue Oct 6 2026. Not read: any intraday path of a thin ETF. Related deaths: ETF premium/discount + creation flow
(SPY/SPDRs/bond SPDRs, daily, liquid -> nothing to harvest); PREF-DIP (thin paper reverts only vs a non-executable
benchmark; unhedgeable, corr 0.28). Here fair value is observable minute by minute and the hedge is near-perfect.
- **Mechanism.** A thin ETF (median $vol $50k-$2M) holding a liquid basket has few quoting MMs; a retail market sell
  prints below fair value (FV) and the close (anchored to NAV by MMs/APs) repairs it. Who pays: the impatient seller. Small
  size is an advantage (capacity per print ~$1-10k).
- **Universe.** Sharadar SFP category ETF, excluding leveraged/inverse names, price >= $10, 20d median $vol $50k-$2M.
  Benchmark = the liquid ETF (SPY QQQ IWM DIA MDY IJR EFA EEM EWJ VNQ GLD AGG TLT IEF SHY LQD HYG XLB XLE XLF XLI XLK XLP XLU
  XLV XLY XLC XLRE) with the highest trailing-120-session daily R^2 (computed on data before T); require R^2 >= 0.97;
  beta from the same regression.
- **Rule.** FV(m) = prior raw close x (1 + beta x (B(m) / B prior close - 1)). Resting limit buy at FV(m-1) x (1 - k),
  k = 0.5% PRIMARY (1.0% descriptive), live 09:45-15:30; fill if the minute LOW < limit - $0.01, fill price = limit; one
  fill per name-day. Hedge: short beta x benchmark at the fill minute close, cover at the benchmark 15:59 close. Exit thin
  ETF at its official close (Sharadar closeunadj). Costs: benchmark 1bp/side, thin exit 5bp; shock 20bp exit.
- **Gate (PRIMARY, judge 2021-01..2026-09; 2016-20 SEALED).** Hedged net/fill >= +15bp, day-clustered t >= 2.5, median > 0,
  both halves (2021-23, 2024-26) > 0, ex-top-5 days > 0, > 0 at 20bp exit; unhedged long-only (Roth form) reported.
  Kill: any fails. If it passes, the 2016-20 holdout is judged once before anything else.
- Runner `research/sim/etf_thin.py` -> `research/sim/etf_thin_out.txt`.

## Result — ETF-THIN (judged 2026-10-06; N 884): KILL
`etf_thin.py` -> `etf_thin_out.txt`; 433 thin ETFs (R^2 >= 0.97 to a liquid benchmark), 87,083 name-days 2021-26.
PRIMARY k 0.5%: only 1,761 fills (2.5 per fill-day) — thin ETFs are quoted tightly around fair value; hedged net/fill
**-22.0bp** (median -4.9, hit 0.43, EW-day t -2.14), every year negative, unhedged -14.9. k 1%: 263 fills, -86bp (median
+7.9; fat left tail). Deviations below hedged FV are informed or erroneous, not impatient retail. 2016-20 holdout unused.
Closes the "resting liquidity in thin instruments" class (PREF-DIP, PREF-DIP-H, ETF-THIN) at minute tier.

## Study NEWS-DRIFT — intraday headline continuation (pre-register; N 884 -> 885)
`date`: Tue Oct 6 2026. Not read: any intraday return around a timestamped headline. Prior news work was overnight only
(8-K/X1-X6 "news moves in the gap, session after ~0"; LLM judge shadow; sentiment filter dead).
- **Mechanism.** In-session news is absorbed with a lag in mid/small caps (attention constraints): after the first fast
  reaction, the price keeps drifting in the news direction for tens of minutes. Counterparty: slow/stale liquidity.
- **Data.** Alpaca (Benzinga) news 2021-01..2026-09, headlines created 09:45-15:00 ET tagged with exactly ONE symbol that
  is a Sharadar common stock with prior raw close >= $5 and 20d ADV >= $5M. Alpaca SIP 1-min raw. 2016-20 SEALED.
- **Rule.** t = headline minute. m5 = close(t+5) / close(t-1) - 1. Event if |m5| >= 1% (PRIMARY; >= 2% descriptive).
  Enter at the t+6 bar VWAP in the direction of m5; exit at the t+66 bar close (PRIMARY) or the 15:59 close. One event per
  stock-day (first qualifying). Cost 10bp/side; shock 20bp. SPY-hedged reported.
- **Gate.** Net mean > 0, day-clustered t >= 2.5, median > 0, halves (2021-23, 2024-26) > 0, ex-top-5 days > 0, > 0 at
  20bp/side. Kill: any fails -> intraday news is absorbed within 5 minutes at retail reach.
- Runner `research/sim/news_drift.py` -> `research/sim/news_drift_out.txt`.

## Study CEF-RV — discount-to-NAV anchored reversion, weekly, CEFConnect panel (machinery-development; 1 judged arm; program N 859 -> 860; third-robot session 2026-10-06)

**Unlocked capability.** CEFConnect's free `/api/v3/pricinghistory/{T}/All` + the 360-name live
fund list give weekly NAV/price/discount history back to the fund's inception (first observed here:
2014). This is the NAV-anchor data the program had listed as the CEF-track blocker. Data
`data/research/cefconnect/` (collector `research/sim/cef_panel.py`).

**Mechanism.** A CEF's market price is anchored to a NAV the market itself cannot recreate
(dark/non-cooperative holdings, corporate/hedge/liability bag); buyers near the discount's own
extremes are paid the reversion led by institutional tender/liquidation/activation events. Economic
anchor: the NAV; counterparty: funds' boards/initiators and forced sellers of CEF shares.
Category A+liability-side trade of the type the blind-spot audit found missing.

**Frozen rule (no tuning at any point).** Per fund per week: d_t = (prev price/nav − 1). Own
trailing-52-week distribution of d; ENTRY when d_t <= own 10th percentile; EXIT when d_t >= own
median. One position per fund. Costs 50bp round trip base; shocks 2x/3x shown.

**Judge window 2016-01-01..2026-10-05** (fresh for this family; halves 2016-2021 / 2021-2026).
Gates (frozen): n >= 300 trades; weekly-clustered t >= 2; halves both > 0; median > 0;
ex-top-5_FUNDS and ex-top-5_DATES positive; hit rate >= 55%.

**Survivorship, pre-registered:** the panel is LIVE FUNDS ONLY (dead CEFs absent). Positive
measures on this panel are survivorship-flattered; a PASS is recorded PROMISING-SURV-LIMITED and
requires a delisted-complete replication before any upgrade. A FAIL is a plain kill of the freeze.

**Economics to report at $2.3k / $10k / $25k:** events/yr, max concurrency, per-trade net, annualized
pp at 100% deployment honesty, left-tail distribution, and the leg's market beta over held spans.

## Result — NEWS-DRIFT (judged 2026-10-06; N 885): KILL
`news_drift.py` -> `news_drift_out.txt`; 265,752 single-symbol in-session Benzinga headlines 2021-26, 9,729 events with a
>= 1% first-5-minute reaction. Continuation t+6 -> t+66: **-12.6bp net** (gross ~+7bp), median -22.8, hit 0.46, EW-day
t -1.13, halves -13.6 / -11.5; to the close -15.4; >= 2% reactions -5.5 (median -43); up-moves -24.0 (t -2.88, i.e. a
small fade, ~+4bp gross: inside costs); ADV >= $50M -14.4. In-session news is absorbed within ~5 minutes at retail reach.

## Audit — CEF-RV returns across splits (2026-10-06; no N)
`cef_rv.py` computes ret = raw exit close / raw entry close - 1 + raw dividends / entry. Across a split the raw ratio is
wrong: 21 CEF-RV funds have 25 split actions; 196 of 3,765 trades differ from Sharadar `closeadj` total return by >10%
(EMO 2020 +566% vs +70%; NXG 2020 +472% vs +65%; TYG 2020 -3% vs -77%). Recomputed on `closeadj` total return (next close
after each signal date), 2016+: **+447.8bp/trade net of 50bp (was +474), median +342.5, hit 74%, weekly-clustered t 8.93,
halves +584 / +326, ex-top-5 +436, ex-2020 +316, 2x cost +398; 2021 -87 (n 91) is the only negative entry year; 2020
+1138 is genuine (COVID discount blowout).** Verdict unchanged (PROMISING-SURV-LIMITED); the runner must switch to
closeadj (or split-adjust raw prices) before any shadow/pilot reads its numbers.

## CEF-RV execution gate (registered 2026-10-06 before any cross is fetched; attack on N 860, no N)
Runner fixed first (`cef_rv.py`): strictly-next close (the old searchsorted side="left" returned the SIGNAL day's own
close when the weekly date was a trading day — not executable, NAV publishes after the close) and closeadj total return
(raw closes broke across 25 reverse splits). Fixed run: +435.1bp/trade net, median +328, t_cl 8.73, hit 73%, halves
+311 / +249, PASS. `cef_rv_surv.py` reads the regenerated trades csv: rerun it before quoting its numbers again.
- **Test.** Reprice every 2016+ trade on official Alpaca SIP auction prints: CC = closing cross on the first session after
  the entry signal -> closing cross on the first session after the exit signal; OO = opening crosses of those sessions
  (an earlier, independent price source). Raw cross prices are converted with that day's closeadj/closeunadj factor.
- **Gate.** CC net (50bp) >= +300bp with weekly-clustered t >= 5; OO net >= +250bp; both halves (pre/post 2021-06) > 0;
  median entry closing-cross $ size >= $20k. Fail -> the edge lives in the price print, not in the discount.
- Runner `research/sim/cef_rv_cross.py` -> `research/sim/cef_rv_cross_out.txt`.

## Result — CEF-RV execution gate (judged 2026-10-06): returns PASS, capacity at the close FAILS -> gate FAIL as registered
`cef_rv_cross.py` -> `cef_rv_cross_out.txt`; 3,548 of 3,636 2016+ trades have both crosses (closing cross = Sharadar
raw close, median |dev| 0.0bp). **CC closing crosses +409.2bp net, median +333.9, hit 73%, t_wk 8.32, halves +538 / +331,
2x cost +359. OO opening crosses +486.1bp, median +353, t_wk 9.52, halves +643 / +354.** The edge is not a closing-print
artifact: an independent price source (the next open) earns as much or more. **Fails on capacity: median entry
closing-cross $ size $4,894 (p25 $2.2k, p10 $1.1k) < $20k bar** (494 trades have no closing cross at all); a $1k order
would be ~20% of the median cross. The opening cross is ~10x deeper (median $46k). Execution route therefore = the
OPENING cross (pre-open limit orders), which needs live verification at Schwab (no MOO; pre-open AUTO orders hit the
official open for liquid names only, per PREF-EX notes). Status: PROMISING-SURV-LIMITED + EXECUTION (open-cross route).

## Study LLM-EARN — LLM reads the earnings release; post-cutoff window only (pre-register; N 885 -> 886)
`date`: Tue Oct 6 2026. User-approved API spend (OpenCode Go key on the server; calls run there, outputs to /tmp only).
- **Why this is not a rerun.** Every earnings/news death in the repo used mechanical signals (gap, EPS beat/miss sign,
  sentiment, speed). Post-announcement drift is ~0 ON AVERAGE; the question is whether reading the release (guidance,
  one-offs, tone) separates the winners from the losers after the open. LLM backtests were "invalid by construction"
  (NEXT.md:1399: deepseek-v4-flash knows events through 2025-10). Fix: judge ONLY events after the cutoff, with margin.
- **Window.** Trade days 2026-01-05 .. 2026-09-30 (>= 2 months after the stated cutoff). Nothing earlier is scored.
- **Events.** Alpaca/Benzinga single-symbol headlines matching the Benzinga earnings template (`EPS ... (Beats|Misses|
  In-Line)` or `Q[1-4] ... EPS`) created between 16:00 ET on T-1 and 09:20 ET on T; Sharadar common stock, prior raw close
  >= $5, 20d ADV >= $5M. One event per (ticker, T).
- **LLM input.** Every news item for the ticker created and last-updated in [T-1 16:00, T 09:20] (headline, summary,
  content; <= 6,000 chars), plus the official opening gap on T. Model deepseek-v4-flash (the repo's judge), temperature 0.
  Output JSON: direction for 09:35 -> close (up/down/flat) + confidence; direction for close(T) -> close(T+3) + confidence.
- **Trades.** A (PRIMARY): confidence >= 0.6 and direction up/down -> enter 09:35 bar close, exit official close T, signed.
  B (secondary): close T -> close T+3 (closeadj), signed. Cost 10bp/side (shock 20bp). Long-only reported separately.
- **Controls.** (1) HEADLINE rule: EPS/sales beat-minus-miss sign from the Benzinga headline, same trade; (2) GAP rule:
  continue the gap sign; (3) **LEAKAGE PLACEBO: same model and question with ticker + date + gap only, no news.** If the
  placebo's signed return has |t| >= 1.5 in the right direction, the model is recalling outcomes -> study INVALID.
- **Gate (A).** LLM trades net mean >= +30bp, day-clustered t >= 2.5, median > 0, both halves (Jan-May / Jun-Sep) > 0,
  ex-top-5 > 0, beats the HEADLINE control by >= +20bp (t >= 2), placebo not significant. Kill: any fails. B judged by
  the same bars as a secondary.
- Runner `research/sim/llm_earn.py` (build/score/judge) -> `research/sim/llm_earn_out.txt`.
- **Added arm, registered before any score exists (N 886 -> 887): FINBERT.** ProsusAI/finbert (Hugging Face; trained on
  2010s financial text, so it cannot recall 2026 outcomes) scores each pre-open news text: signal = sign(P(pos) - P(neg))
  when |P(pos) - P(neg)| >= 0.3, else 0; same trades A/B, same gate. Read as: FINBERT ~ LLM -> the LLM is only sentiment;
  LLM > FINBERT (t >= 2) -> reading adds information beyond tone. Time-series foundation models (Chronos/TimesFM) are NOT
  added: price-only forecasting is the program's most-tested dead class. Online crowd sentiment (Reddit) was swept dead
  2026-10-02; StockTwits history is not free.
- **Amendment (before any score was read):** deepseek-v4-flash in its default thinking mode spent the whole token budget
  on hidden reasoning (400 and 3,000-token caps both returned empty replies; `reasoning_effort: low` did not bind). The
  LLM arm is therefore run with `thinking: {type: disabled}` (non-thinking mode, ~80 tokens/reply), max_tokens 400,
  temperature 0, same prompts. All else unchanged.

## Result — LLM-EARN + FINBERT (judged 2026-10-06; N 886-887): KILL both
`llm_earn.py` -> `llm_earn_out.txt`; 6,347 earnings events 2026-01-06..2026-09-30 (post model cutoff), 13,240 LLM calls
(48 parse failures), FinBERT on all 6,620 texts. **A (09:35 -> close): LLM conf >= 0.6 -14.4bp net, median -20.0, hit
0.47, EW-day t -0.03, halves -4.5 / -32.1; long-only +11.2 (n 1,860).** HEADLINE control +2.6 (t -1.45), GAP control -8.0;
LLM - HEADLINE +52bp t 1.30 (< 2). **B (close -> T+3): the LLM was confident on only 129 events** (+55bp, t 0.02, ex-top-5
-69). FINBERT A -10.1bp (t 0.94), B -13.0; LLM - FINBERT -20.8bp t -1.03 (sign agreement 0.57). Leakage placebo: -27.0bp,
t 1.13 -> not significant, no evidence of outcome recall (the test is valid). Read: reading the release (LLM) or its tone
(FinBERT) does not predict the post-open move; earnings information is in the opening price. Closes the news/earnings
class at retail reach (with NEWS-DRIFT, DS1, AS/AU, T3/T5).

## Study CEF-TXT — N-CSR shareholder-report text as a filter on CEF-RV entries (pre-register; N 887 -> 889)
`date`: Tue Oct 6 2026. Session "FinBERT discovery" (`research/drafts/prompt_finbert_discovery.md`); candidate ledger and
gate math in `research/drafts/nlp_ledger_2026-10-06.md`. Registered before any filing is fetched or scored.
- **Question.** CEF-RV (N 860) buys a CEF when its discount reaches its own trailing 52-week 10th percentile and earns
  +409..+486bp/trade at official crosses, hit ~73%. Do the losing ~27% carry a TEXT signature the market reads slowly:
  the manager's semi-annual shareholder report (N-CSR / N-CSRS, filed ~60-70 days after period end, read by few holders)?
  Mechanism: a discount that widens on information (deteriorating holdings, a distribution cut being prepared, leverage
  stress) should not revert; a discount that widens on flow should. FinBERT (ProsusAI/finbert, 2010s training data) has
  no memory of 2016-26 outcomes, so the 2016+ backtest is honest.
- **Trades.** The existing frozen CEF-RV trade list (`data/research/cefconnect/cef_rv_trades.csv`, 2016+ entries,
  closeadj total return, strictly-next close), net of 50bp. No change to the CEF-RV rule.
- **Text.** For each trade, the latest N-CSR or N-CSRS (incl. /A) of the fund's CIK with SEC acceptance datetime strictly
  before the entry signal date (`edate`). Trades with no report in the prior 400 days are excluded and counted. Text =
  primary document, HTML stripped, first 60,000 characters (the shareholder letter / manager commentary sits at the
  front; the schedule of investments follows). Sentences of 8-80 words; the first 64 such sentences are scored.
  Multi-fund reports are scored as filed (the same letter can cover several funds; stated, not fixed).
- **Arm A1 (PRIMARY, N 888): tone level.** tone = mean over scored sentences of P(neg) - P(pos). Within each entry
  calendar year, rank trades by tone into terciles; FILTER = drop the most-negative tercile.
- **Arm A2 (secondary, N 889): tone change.** dtone = tone(this report) - tone(the fund's previous report). Same
  within-year terciles; drop the most-deteriorated tercile. (Within-fund "lazy prices".)
- **Statistic.** spread = mean net return of kept trades - mean of dropped trades; lift = mean(kept) - mean(all).
- **Gate (each arm).** spread >= +150bp; weekly-clustered t(spread) >= 2.0 (cluster = entry week); spread > 0 in both
  halves (entries 2016-2020 / 2021-2026); median(kept) - median(dropped) > 0; spread ex-top-5 trades (by |ret|) > 0; real
  spread >= 95th pct of a PLACEBO (200 shuffles of report assignment across trades within the same entry year); and the
  NLP spread beats every NON-NLP CONTROL by >= +50bp: (C1) document length (drop the longest tercile... and the shortest
  tercile, both reported, the better one used), (C2) distribution-cut keyword flag (regex: reduc|decreas|cut|lower within
  60 chars of "distribution"; drop flagged), (C3) the fund's trailing 26-week NAV return at entry (drop the lowest
  tercile; CEFConnect panel), (C4) entry discount depth (drop the shallowest tercile). Kill: any gate fails -> the filter
  adds nothing to CEF-RV and N-CSR tone is closed.
- **Cost shock.** All spreads also at 100bp and 150bp round trip (a filter's spread is cost-invariant except via n).
- **Not a re-judge of CEF-RV.** The CEF-RV list was not chosen on text; the 2016-26 window is new for this feature. The
  CEF panel is live funds only (survivorship as in N 860).
- Runners `research/sim/cef_txt_fetch.py` (EDGAR, cached `data/research/cef_txt/`), `research/sim/cef_txt_score.py`
  (FinBERT, system python3 with torch; not the project venv), `research/sim/cef_txt.py` (judge) -> `cef_txt_out.txt`.
- **Amendment (before any document was scored or any outcome read).** Inspection of 3 fetched reports showed the first
  ~20 qualifying sentences are boilerplate (cover page, e-delivery notice, managed-distribution-plan legend) and HTML
  line breaks split sentences. Sentence selection is therefore: collapse all whitespace; start at the first anchor
  ("Dear Shareholder", "Letter to Shareholders", "Shareholder Letter", "Manager's Discussion", "Portfolio Manager",
  "Market Review", "Commentary"; from the start if none); drop sentences matching a boilerplate list (electronic
  delivery, paper copies, intermediary, Form N-CSR, Commission, FDIC, registrant, prospectus, "conclusions about",
  the distribution-plan legend); score the first 64 remaining sentences of 8-80 words. Control C1 uses the filing's
  full EDGAR size (submissions index `size`), not the 60k-truncated text. All else unchanged.

## Result — CEF-TXT (judged 2026-10-06; N 888-889): KILL both arms
`cef_txt_fetch.py` / `cef_txt_score.py` / `cef_txt.py` -> `cef_txt_out.txt`. 8,278 N-CSR/N-CSRS reports (0 fetch failures),
8,160 scored (>= 10 sentences); 3,562 of 3,636 2016+ CEF-RV trades have a report accepted in the prior 400 days (median
age 85d). Base: +451bp net, median +344, hit 0.74. Tone is a valid measure (most negative in reports filed after the 2022
bear market, most positive 2017/2021) but carries no CEF-RV information: corr(tone, ret) +0.04.
- **A1 tone level: spread -58bp (t_wk -1.86), the WRONG sign** (the most-negative-tone tercile earns the most, +490bp vs
  +454/+410), halves -86/-35, med-diff -39, placebo 5th pct. **A2 tone change: -31bp (t -0.79)**, halves +12/-69, placebo
  21st pct. 0/7 gate checks on each arm.
- Controls: size -70..+21bp, distribution-cut keyword +2bp, entry discount +121bp (t 1.53, one half negative). None of
  them is a filter either; no text or text-proxy separates CEF-RV losers.
- **Unregistered observation (control C3, not a PASS):** dropping the lowest trailing-26w NAV-return tercile LOSES -705bp
  (t -5.08, both halves -1016/-440): CEF-RV entries after a NAV fall are its best trades (hit 0.84). CEFConnect NAV is
  price-only (distributions lower it), so part of this is high-payout funds. It strengthens CEF-RV's "flow, not
  information" reading rather than suggesting a filter; a "NAV-fall x discount" arm would need its own pre-registration
  on data CEF-RV was not judged on.
- Read: the manager's semi-annual letter is market commentary; whether a CEF discount reverts is set by flow, not by
  anything the report says. Closes N-CSR text x CEF-RV. Program N = 889.

## Study CEF-OOS + NAVFALL — CEF-RV on its untouched 1999-2014 window, and the NAV-fall lead (pre-register; N 889 -> 891)
`date`: Tue Oct 6 2026. Registered before any pre-2015 CEF-RV trade is generated. The CEFConnect weekly panel reaches back
to 1996 (median fund start 2004) and Sharadar SFP to 1998, but CEF-RV (N 860) was only ever run from 2015: 1999-2014 has
never been used to choose or judge it. The NAV-fall lead (CEF-TXT control C3, 2016-26) was seen only on 2016-26.
- **Trades.** The exact frozen CEF-RV rule and code (`cef_rv.py` trade builder, factored out unchanged: own 52-week
  q10 entry, own-median exit, 260-day cap, strictly-next closeadj close), entries 1999-01-01..2014-12-31, net 50bp. Live
  funds only (CEFConnect): survivorship as in N 860 (measured benign, ~2pp/yr).
- **Arm O (N 890): CEF-RV out of sample.** The N 860 gates: n >= 300; weekly-clustered t >= 2; halves (entries 1999-2006 /
  2007-2014) both > 0; median > 0; hit >= 55%; ex-top-5 > 0. Also reported: ex-2008-09, 2x/3x cost.
- **Arm F (N 891): NAV-fall filter.** navtr26 = 26-week distribution-inclusive NAV return at the entry week: raw NAV ratio
  x the SFP (closeadj/closeunadj) ratio over the same weeks (adds distributions, undoes splits). Within entry year, LOW =
  bottom tercile of navtr26. Statistic: spread = mean(LOW) - mean(rest). Gate: spread >= +150bp; weekly-clustered t >= 2;
  both halves > 0; median(LOW) - median(rest) > 0; ex-top-5 > 0; >= 95th pct of a 200-shuffle within-year placebo;
  spread ex-2008-09 entries > 0; spread > 0 in >= 2 of 3 within-year entry-discount terciles (not just deep discounts).
  Raw (price-only) NAV return reported alongside, not judged. Kill: any check fails -> the lead was a 2016-26
  in-sample artifact. A PASS is a CONDITIONING result on CEF-RV (forward shadow, no orders), not a new strategy.
- Runner `research/sim/cef_oos.py` -> `research/sim/cef_oos_out.txt`.

## Result — CEF-OOS + NAVFALL (judged 2026-10-06; N 890-891): both PASS as registered; beta diagnostic changes the read
`cef_oos.py` -> `cef_oos_out.txt` (trades `cef_rv_trades_1999_2014.csv`); diagnostic `cef_beta_diag.py` (no N).
Runner fix first: `cef_rv.next_close` returned the loaded window's first close for a signal before the window (the 129
"2015" entries in the old trade list were priced at 2015-12 closes; 2016+ judge unaffected). Guard: no entry/exit close
> 14 days after the signal. 2016+ re-run: 3,629 trades, +443.2bp net, t 8.98, PASS (was 3,636 / +435).
- **Arm O (N 890): CEF-RV PASSES on untouched 1999-2014.** 3,673 trades / 276 funds: +333bp net, median +340, hit 0.73,
  t_wk 5.33, halves +404 / +297, ex-top-5 +322, ex-2008-09 +325, 3x cost +233; 15/16 entry years > 0 (2008 -78, 2009
  +2094). Live-funds survivorship as before.
- **Arm F (N 891): NAV-fall PASSES as registered** (8/8): LOW navtr26 tercile +586 vs rest +210, spread +376bp t 3.45,
  placebo 100th pct, all discount terciles +; but halves +18 / +550 and ex-2008-09 only +71.
- **Beta diagnostic (decisive for the read).** SPY total return over each trade's hold, pooled regression:
  - CEF-RV ALL 1999-2014: beta 0.53, **alpha +237bp t 5.24, median +239** -> genuine discount alpha.
  - **CEF-RV ALL 2016-2026: SPY +527bp per hold, beta 0.76, alpha +46bp t 0.74, median +65 -> the 2016-26 edge is mostly
    market rebound after selloffs (entries cluster when discounts widen in selloffs).** The +281bp "discount component"
    (N 860 attack) is real but co-moves with the market.
  - NAV-fall spread: 1999-2014 +198bp t 2.55 after 0.53*SPY (+41 t 0.62 after full SPY); 2016-26 +318 t 3.29 after
    0.76*SPY (+206 t 2.24 after full SPY). LOW entries get far more SPY rebound (+406 vs +71bp; +843 vs +369).
- **Read.** CEF-RV is a real out-of-sample effect over 1999-2016 with alpha, but in its 2016-26 window it is ~85% levered
  equity beta timed after selloffs; recent alpha is not significant. NAV-fall concentrates that timing (about half its
  spread is SPY rebound). Neither should be sized as alpha. Status: CEF-RV = OOS-VALIDATED (1999-2014), ALPHA DECAYED
  2016-26 (t 0.74), BETA-DOMINANT; NAV-fall = PASS-AS-REGISTERED, BETA-CONTAMINATED (conditioning only, forward shadow
  at most). Next registered question: a SPY-hedged or beta-matched CEF-RV (e.g. vs an equal-weight CEF index) forward.
  Program N = 891.

## Study CEF-ALPHA — is CEF-RV alpha or timed beta? (pre-register; N 891 -> 893; N 894 reserved, unused)
`date`: Wed Oct 7 2026. Task 1 of `research/drafts/prompt_numeric_subagents.md`. Registered before any comparator is
computed. (Task 2, survivorship, runs in parallel with N 895-896.)
- **Trades.** The CEF-RV trade lists from `build_trades`: 1999-2014 (`cef_rv_trades_1999_2014.csv`, touched once by N 890)
  and 2016-2026 (`cef_rv_trades.csv`, touched). Trade window = first close after edate -> first close after xdate
  (closeadj), net 50bp. Comparators are cumulated over exactly those two dates.
- **Comparator B (PRIMARY, N 892): equal-weight CEF universe incl. delisted.** Every Sharadar SFP ticker with
  category CEF (1,074 permatickers), rows restricted to that ticker's [firstpricedate, lastpricedate]; daily closeadj
  returns, |r| > 50% dropped as data errors; index = daily equal-weight mean, rebalanced daily. excess = trade net -
  index return over the window. **Gate (judged on 2016-2026):** mean excess >= +100bp, weekly-clustered t >= 2, median
  > 0, both halves (2016-20 / 2021-26) > 0, ex-top-5 > 0. **Kill:** t < 2 -> CEF-RV is beta-dominant in 2016-26, not a
  small-account alpha candidate. 1999-2014 reported by the same statistics, not judged.
- **Comparator A (N 893): fixed-beta SPY.** excess = net - beta x SPY closeadj return over the window, with beta taken
  from the OTHER window (0.53 from 1999-2014 applied to 2016-26; 0.76 from 2016-26 applied to 1999-2014) so no beta is
  fitted on the window it judges. Same gate on 2016-2026.
- **Control (no N): SPY-dip timing.** On each CEF-RV entry date, the SPY return over the same window is reported
  together with the share of CEF-RV entries that fall in SPY's bottom trailing-5-year tercile of 26-week return: if
  entries are mostly SPY-dip dates, the raw edge is a dip-buying rule in CEF form.
- **Economics.** Excess per trade x ~3.7 turns/yr at 100% deployment, at $2.3k / $10k / $25k under $1k slots (2 / 10 /
  25 concurrent), Roth long-only (the comparator is what the Roth could hold instead).
- Runner `research/sim/cef_alpha.py` -> `research/sim/cef_alpha_out.txt`.

## Result — CEF-ALPHA (judged 2026-10-07; N 892-893): both PASS; corrects the "beta-dominant" read of N 890-891
`cef_alpha.py` -> `cef_alpha_out.txt`. EW CEF universe = 1,074 SFP CEFs incl. delisted, median 533 names/day.
- **N 892 (net - EW CEF index over the hold), 2016-26: +125bp/trade, t_wk 5.59, median +92, hit 0.59, halves +159 / +97,
  ex-top-5 +119 -> PASS.** 1999-2014 (report): +187bp t 9.42, halves +175 / +194.
- **N 893 (net - fixed out-of-window beta x SPY), 2016-26: 0.53 x SPY -> +159bp t 3.49, halves +248 / +83 -> PASS.**
  1999-2014 with 0.76 x SPY: +203bp t 4.41.
- **Correction.** The "+46bp t 0.74" alpha in the N 890-891 beta diagnostic used a beta fitted on the same window
  (0.76); the intercept is very sensitive to that beta because entries cluster before large SPY rebounds (+544bp per
  hold). With the beta-matched comparators registered here, CEF-RV keeps ~+125..160bp/trade of excess in 2016-26 and
  ~+190..200bp in 1999-2014. Raw returns are still ~2/3 market (2016-26: +448 raw vs +125 excess).
- SPY-dip control: 50% of 2016-26 entries (31% of 1999-2014) are on SPY bottom-tercile dates; excess vs EW CEF is larger
  on those dates (+179 vs +71bp; +254 vs +157) -> discount reversion is strongest after selloffs, but is not only SPY.
- **Economics:** excess ~+4.8pp/yr on deployed capital (3.8 turns/yr) on top of holding CEF beta, the same %/yr at
  $2.3k / $10k / $25k with $1k slots, capacity-capped at the opening cross (N 860 execution note). Below the +8pp
  stand-alone gate, but it is a Roth-friendly upgrade over holding a CEF or equity index.
- Status: CEF-RV = OOS-VALIDATED (1999-2014) with ALPHA in both windows vs beta-matched comparators (live-funds
  survivorship still open: Task 2, N 895-896). Remaining caveat: deep-discount entries may carry higher beta than the
  average CEF; a same-category peer comparator is the next refinement. Program N = 893 (894 unused).

## Study CEF-SURV99 — survivorship of CEF-RV on 1999-2014, price-only proxy + how delisted CEFs end (pre-register; N 894 -> 896)
`date`: Wed Oct 7 2026. Registered before any delisted-CEF return is computed. N 895-896 only (Task 2 of
`prompt_numeric_subagents.md`). Question: the N 890 pass (+333bp net, alpha +237bp t 5.24 after 0.53*SPY, `cef_beta_diag.py`)
uses 276 CEFConnect funds that survived to 2026; 704 of 1,074 CEF permatickers are delisted and have no weekly NAV.
- **Arm S (N 895): price-only proxy entry on live vs delisted CEFs.** Universe: Sharadar `tickers.category == "CEF"`
  (not "CEF Preferred"), SFP daily `closeadj`, weekly grid (last trading close of each ISO week), entries 1999-01..2014-12.
  Eligible fund-week: >= 52 weekly closes of history, raw close >= $3, >= 30 eligible funds that week. Signal: own 26-week
  closeadj return in the bottom decile of that week's cross-section (live and delisted pooled, so dead funds' drawdowns set
  the cut too). Entry = the next trading day's close (strictly after the signal week); exit = close 14 weeks later (14.0 =
  CEF-RV mean hold) or the fund's LAST close if it delists first (delisting-day return included, never dropped); one
  position per fund at a time; net of 50bp. Groups: PANEL (the 276 funds with a CEF-RV 1999-2014 trade), LIVE_OTHER (live,
  not in those 276), DEAD (isdelisted == Y). Alpha = net - 0.53*SPY closeadj return over the exact hold (the frozen
  1999-2014 CEF-RV beta); also with a beta refit on the proxy trades. Statistics: mean/median alpha per group,
  entry-week-clustered t, delta = PANEL - DEAD (clustered t; year-reweighted so DEAD matches PANEL's entry-year mix),
  dead share p of proxy trades, ex-top-5, 2x/3x cost, entry-year cluster bootstrap (2,000 draws) of delta, ex-2008-09.
  Calibration: PANEL-proxy alpha vs CEF-RV alpha 237bp and the overlap of proxy entries with actual CEF-RV entries
  (the proxy is NOT CEF-RV; a proxy that does not select discount-widening entries limits what the bound can say).
- **Bound (the number).** adj_alpha = 237 - p*delta_bp (assumes CEF-RV's survivorship gap equals the proxy's gap), with
  the 90th-percentile bootstrap delta as the conservative end, plus the break-even: the alpha delisted funds' CEF-RV
  entries would have to earn for the pooled alpha to be 0 (= -237*(1-p)/p). Verdict classes: SURVIVORSHIP-IMMATERIAL
  (conservative adj_alpha >= 0.75*237 = 178bp), MATERIAL-BUT-SURVIVES (0 < conservative adj_alpha < 178), ERASED
  (conservative adj_alpha <= 0). A proxy whose PANEL alpha has the wrong sign or whose overlap with CEF-RV entries is
  < 10% is reported DATA-LIMITED for the bound (the gap is still reported).
- **Arm E (N 896): how delisted CEFs end, by era.** For every DEAD fund by delist-year era (1998-2004, 2005-09, 2010-14,
  2015-26): (a) price endgame from SFP: final-6-month and final-20-day closeadj return, last close vs the fund's own
  trailing-60-day median close (a last close far below = forced/ugly end), share with final-6m total return < -10%;
  (b) EDGAR: the fund's CIK (from `tickers.secfilings`), `data.sec.gov/submissions` form list, N-8F / N-8F/A /
  25-NSE / N-14 presence, and the N-8F text's stated type of deregistration (merger / liquidation / abandonment /
  BDC election; regex on the checked box), within 1 year of the last price. Classes: MERGER, LIQUIDATION,
  OPEN-END/CONVERSION (no N-8F, fund continues filing N-CSR/N-1A), BDC/OTHER, UNKNOWN. Claim tested: "CEFs die benignly"
  (measured before only on recent eras); flag if the pre-2010 final-6m return share < -10% exceeds the 2015-26 share
  by > 10pp. SEC requests via `swingtrader.daily.news_judge.sec_headers()`, <= 8 req/s, cache `data/research/cef_surv/`.
- Runners `research/sim/cef_surv99.py` (Arm S), `research/sim/cef_ends.py` (Arm E) -> `*_out.txt`; write-up
  `research/drafts/cef_surv99_2026-10.md`. Kill/alert rule: ERASED -> CEF-RV 1999-2014 alpha is a survivorship artifact.

## Result — CEF-SURV99 (judged 2026-10-07; N 895-896): survivorship is MATERIAL, alpha NOT provably erased, point-estimate +105bp and level-bound ~0
Pre-reg: round1_prose.md "Study CEF-SURV99" (N 895-896). Runners: research/sim/cef_surv99.py -> cef_surv99_out.txt (Arm S);
research/sim/cef_ends.py -> cef_ends_out.txt (Arm E; cache data/research/cef_surv/). Verdict: Arm S = MATERIAL-BUT-SURVIVES by the
registered class (conservative p90 bound +17bp), but 2 of 4 stated bounds are <= 0, so DATA-LIMITED for a confident survival claim.

**Arm S (price-only proxy, 6,655 entries 1999-2014, bottom-decile 26w return, 14-week hold, net 50bp, alpha after 0.53*SPY).**
- Delisted CEFs are 64% of eligible fund-weeks and 71% of PANEL+DEAD proxy trades (cef_surv99_out.txt:15), not a minority:
  the 276 CEF-RV funds are only a minority of the 1999-2014 CEF universe.
- Proxy alpha: PANEL +94bp (t 0.58; -4bp under a refit beta 0.92), LIVE_OTHER +161, DEAD -92bp (median -125, 5th pct -1750,
  worst = 2008 leveraged real-estate/equity CEFs). Delta PANEL-DEAD +186bp (naive t 5.3), year-reweighted +181, bootstrap p90 +310.
  Holds in both halves (+184 / +233) and ex-2008-09 (+104); 2x/3x cost leaves delta unchanged.
- Bounds on the +237bp (cef_surv99_out.txt:22-28): additive-gap point +105 (year-reweighted +108); conservative p90 +17;
  LEVEL bound (dead funds' CEF-RV alpha = their proxy alpha, -92) pooled +3bp; scaled-delta (delta x 237/94 = 2.53) -98bp.
  Break-even dead alpha is -96bp/trade, and the proxy's DEAD alpha is -92. Read: alpha falls by 55% (central) to ~100%.
- Calibration weakness: proxy is not CEF-RV. 52% of PANEL proxy entries fall inside an actual CEF-RV hold (line 21), but proxy
  PANEL alpha is only +94 vs +237, so the gap between live and dead on the real discount rule is unmeasured (no NAV for dead funds).
**Arm E (700 of 704 delisted CEFs; cef_ends_out.txt).** Final-6m closeadj return < -10%: 19% (1998-2004), 13% (2005-09), 8%
(2010-14), 6% (2015-26); pre-2010 16.2% vs 6.1% recent (+10.1pp -> FLAG as registered: older eras die less benignly). Mergers
dominate from 2005 (60% / 88% / 56%); liquidations 7-21%; median final-6m return positive in every era (+1.5% to +4.8%).
1998-2004 is 85% UNKNOWN (no usable N-8F in the EDGAR submissions window), so that era's classes are unmeasured.
5-line summary:
1. Delisted CEFs are 64% of 1999-2014 CEF fund-weeks; the 276-fund CEF-RV pass is on the survivor minority.
2. Price-only proxy: live-minus-dead alpha gap +186bp/trade (p90 +310), dead share of entries 71%.
3. Bound on +237bp: +105bp central, +17bp conservative, ~+3bp if dead funds earn their proxy alpha (-98bp if the gap is scaled up).
4. Delisted CEFs end by merger (56-88% post-2004) with a final-6m < -10% share 16% pre-2010 vs 6% since: benign claim holds only for recent eras.
5. Verdict: MATERIAL, not proven erased; CEF-RV 1999-2014 alpha is not established until dead-fund NAV is obtained.
- Program N = 896 (CEF-SURV99 used 895-896).

## Forward shadow CEF-RV-FWD (registered 2026-10-07; no N: forward-only, no orders)
`swingtrader/daily/cef_rv_shadow.py` (research-shadows, weekdays 08:20 ET; REGISTRY "CEF-RV: CEF discount reversion vs the
CEF universe"; `make cef-rv`). Frozen CEF-RV rule on the live CEFConnect weekly panel (signal logic tested equal to
`build_trades`); first forward signal week Fri 2026-10-09 (the 2026-09/10-02 weeks are logged as backfill, never gated).
- Execution: official SIP opening cross of the first session after the entry / exit signal week (OO, primary), closing
  crosses (CC) alongside; cash distributions with ex-date inside the hold added; 50bp round trip.
- Comparator: equal-weight CEF universe (every CEFConnect fund with closing crosses on both sessions, distributions in)
  over the same sessions. excess = net - EW.
- Gate after >= 60 closed forward trades spanning >= 10 entry weeks: PASS = mean OO excess >= +60bp, entry-week-clustered
  t >= 2, median > 0; KILL = mean OO excess <= 0; else HOLD. Live-execution question (does a Schwab pre-open order fill
  at the official open cross?) is separate: `research/sim/cef_open_test.py`, user-run.
- Context at registration: 188 of ~350 CEFs were at their own 10th-percentile discount in the 2026-10-02 week (a broad
  discount blowout), so early forward entries will cluster in one regime; the >= 10-entry-week condition exists for it.

### Study ROTH-STACK (pre-register 2026-10-08; N 896 -> 897)
Question (portfolio construction, no new signal): on a cash Roth (no margin, no shorting), how much does PREF-EX + ETDX (measured
+38/+44bp CO per ex-night, official crosses 2021-26) add on top of the AL1 cash book (IBS .5 + night .5, whole shares, 1-share probe)
when it is funded only from the cash that book leaves idle, with the cash-account constraints the taxable `etdx_stack` ignored?
Ceiling math (before running): ~200 ex-nights/yr x ~38bp x share of idle Roth cash deployable (idle ~50% of equity; capacity 5% of ex-ante
auction $ binds above ~$5k) -> $3k: ~$450/yr (15pp), $10k: ~$800 (8pp, at the gate edge), $25k: ~$900 (3.6pp). Passes at $2.3k-$10k, fails
the +8pp gate by $25k (capacity). Haircut for the idle-cash share: expect ~+10pp at $3k, ~+5-8pp at $10k.
Rule: cash_day (research/sim/roth_cash.py, copied with a reserve arg) + on each ex-eve d0 (events.parquet d0 = last close before ex-date) buy PREF/ETDX at the
d0 close, sell at the ex-date open (CO) with equal split across that night's events, per-event cap 5% x min(ex-ante close/open auction $),
whole shares at pc, 10bp round trip. Funding: STRICT = cash left after IBS held + BIL park + night buys (BIL kept, GFV-safe); LENIENT = BIL sold
(T+1 unsettled -> good-faith-violation risk, reported as an upper bound). Priority arms: night-first vs PREF-first (night takes remainder).
Data: official crosses 2021-26 (touched; this is economics, not signal selection). Mechanism out-of-sample support already registered (Sharadar 2005-26).
Sizes $1k/$3k/$7.8k/$10k/$25k, fixed equity. Metrics: incremental $/yr and pp of equity, halves 2021-23 / 2024-26, 3x cost (30bp), ex-top-5 events,
median and hit per event, day-clustered t of daily increment, placebo = shuffle event dates over the book's days (wrong-day cash state).
Gate (PASS): STRICT, night-first arm gives >= +8pp/yr at $3k and >= +5pp at $10k, both halves > 0, 3x cost > 0, ex-top-5 > 0, t >= 2, placebo < 5%.
Kill: STRICT < +3pp at $3k, or negative in a half, or only LENIENT works. One run, no tuning.

#### Result — ROTH-STACK (judged 2026-10-08, one run; N 897): PASS-SMALL, cost-fragile, placebo uninformative
Runner research/sim/roth_stack.py -> data/research/program/roth_stack_out.txt. STRICT (GFV-safe, BIL kept) night-first: +10.5pp/yr at $1k,
+8.4 at $3k, +5.9 at $7.8k, +5.4 at $10k, +3.6 at $25k (halves equal, ex-top-5 ~same, median +27bp/event, hit 72%). PREF-first (PREF
takes cash before the night buys) adds ~+1.7-2pp (STRICT $3k +10.5, $10k +7.1). LENIENT (BIL sold, unsettled-fund GFV risk) is +5pp higher.
3x cost (30bp RT) leaves only +1.6 ($3k) / +0.9 ($10k): the result stands or falls on the 10bp cross-cost assumption. The registered placebo
(event returns on random book days) cannot discriminate (the return is independent of the book day; real sits at pct 22-31), so that gate
item is NOT met; the edge itself rests on the PREF/ETDX studies. Gate otherwise met at $3k/$10k. Capacity binds above ~$5k.

## Study QI-HIST — does the 15:40 NBBO quote imbalance predict the night bounce? (pre-register 2026-10-08; N 897 -> 898)
Motivation: BB (Round 24) is forward-only; its first 44 picks were peeked (sell-heavy -185bp, mid -169, buy-heavy +20bp) and are NOT used here.
This tests the same hypothesis on data BB never saw.
- Data: exact 15:40 night picks 2016-2020 (`night_exact_pre2021.parquet`, 5,608 rows, outcome `ret` = adj next open / adj close - 1). Alpaca SIP
  NBBO: last valid quote (bid>0, ask>bid) with timestamp <= 15:40:00 ET (searched back to 15:30). QI = (bid_size - ask_size)/(bid_size + ask_size),
  as BB. Differences from BB: BB uses the Schwab L1 snapshot at 15:40 and 2x2.5bp costs; here SIP NBBO sizes (round lots) and costs 7.5bp/side (1x), 15bp/side (2x).
- Terciles of QI pooled over the whole sample (BB pools too); T1 sell-heavy, T3 buy-heavy. Rows with no quote are dropped (count reported).
- Arms: A1 tercile means; A2 "skip T1" vs all picks.
- Gate (judge 2016-2020, single run): A2 mean net/trade of kept minus all >= +30bp at 1x costs AND day-clustered t (T1 vs rest, clustered by date) >= 2 AND
  same sign in 2016-18 and 2019-20 AND holds ex-top-5 (drop the 5 best T1... i.e. drop the 5 largest-|net| rows of the sample, recompute) AND placebo
  (1000 random tercile assignments, same sizes) 95th percentile. Report median, hit rate, 2x cost.
- Kill: any gate failure = DEAD, no re-tuning of terciles/time cut. If it passes, 2021-26 is a secondary check only.

## Study EXDATE-OOS — SPLIT-T0 / SPIN-T0 ex-date night on Sharadar SEP, daily raw prices (pre-register 2026-10-08; N 898 -> 899)
Written before any Sharadar ex-date outcome is read. Rule = the live shadow (`exdate_open_shadow.py`): buy close(E-1), sell open(E), E = ex-date from
Sharadar `actions` (split value>1 = forward; spinoff via spunofffrom parent/child/ratio; the child's open at E is added at ratio x child raw open, else
spin-offs are dropped). Raw prices only: raw open = open*closeunadj/close, raw prior close = closeunadj(E-1); split-ratio adjusted. Common stock
(Domestic/Canadian common), raw close(E-1) >= $5, $vol(E-1) >= $1M, |T+0| > 100% dropped. Benchmark = raw SPY close(E-1)->open(E) (SFP).
Honest status: NOT a clean OOS. All Sharadar years were "touched" by the 1998-2026 vendor look in NEXT; the judged window is 1998-2012 (before the
2013-26 vendor look and 2016-20/2021-26 official-cross studies), 2013-26 reported as secondary. Sharadar open = daily-bar open (first print, not the official cross).
Pass: raw-SPY mean > 0, day-clustered t >= 2; halves > 0; median > 0; ex-top-5 > 0; mean > 0 at tier costs (book.cost_bps tier, 2x tier_hi shock).
Cuts (reported, not judged): forward vs reverse split, split ratio, liquidity bucket. Kill: median <= 0 or t < 1. Runner research/sim/exdate_oos.py.

### Result — EXDATE-OOS (2026-10-08, one run; N 899): forward splits PASS (touched window), spin-offs WEAK, reverse splits not testable
Out: data/research/program/exdate_oos_out.txt. Forward splits 1998-2012 (judged) n 3109: raw-SPY +82bp, median +43, hit 64%, clustered t 12.1, ex-top5 +77,
halves 1998-05 +89 / 2006-12 +58, tier net +69 (median +30), 2x tier_hi +45 (median +8). 2013-26 n 578: +105bp, median +40, tier +92, 2x tier_hi +66 (median +3).
Falls with ratio (>3:1 ~0) and rises with illiquidity (<$5M ADV +144bp; >$50M +67). Spin-offs (parent + ratio x child open) n 171 / 258: median +78 / +58 but t 1.4 / 1.8 and ex-top5 negative: fails. "rev" rows (-1000..-1900bp) are a value-convention/data problem and untested. Sharadar open is a daily-bar first print, not the official cross (official 2021-26 median is only +17).

## Study SPLIT-CROSS — forward-split ex-date night at OFFICIAL SIP crosses, 2016-2020 (pre-register 2026-10-08; N 899 -> 900)
Written before any cross outcome is read. Rule = EXDATE-OOS/shadow: buy the official closing cross of E-1, sell the official opening cross of E, forward splits only,
ratio-adjusted (open_cross x ratio / close_cross - 1), minus SPY official-cross overnight. Events: Sharadar `actions` splits value>1, ex 2016-01-04..2020-12-31,
common stock, raw close(E-1) >= $5, $vol(E-1) >= $1M, E-1 within 5 days (same filters as EXDATE-OOS). Crosses: Alpaca SIP `/v2/stocks/auctions` (the shadow's source).
Window 2016-20 was not used for the auction-tier question for this rule. Events with no open cross or no close cross are counted (missing share), and for the missing-open
case a labelled FALLBACK exit = Sharadar daily open (first print, proxy for first trade) is reported separately, not in the judged row.
Judged row = events with both crosses. Cost: 2x `tier` round trip (book.cost_bps), i.e. a 2x cost shock on the model.
Gate (all): cross median >= +15bp; mean net of 2x tier > 0 with day-clustered t >= 2; ex-top-5 mean > 0; halves (2016-18 / 2019-20) mean > 0.
Cuts (reported, not judged): $ADV20 bucket (<5M, 5-50M, >50M), split ratio, open-cross $ size (<$5k "tiny"), cross-vs-daily-open gap, compare to 2021-26 shadow backfill
(state/exdate-open.jsonl on him, ex < 2026-10-07, scored splits). Runner research/sim/split_cross.py; out data/research/program/split_cross_out.txt. One run, no tuning.

### Result — SPLIT-CROSS (2026-10-08, one run; N 899 -> 900): FAIL on the registered t >= 2 (net2 t 1.73); median/ex-top5/halves pass
Out: data/research/program/split_cross_out.txt (its printed GATE tuple omits the t test; t is read from the net-2x-tier row). Forward splits 2016-20, both crosses, n 152: gross-SPY mean +158bp, median +58, t 2.09, ex-top5 +44; net of 2x tier mean +129, median +28, t 1.73, ex-top5 +15. 2016-18 median +60 (net2 t 2.18); 2019-20 median +18, net2 median -2, ex-top5 negative. Open cross never missing (0/153) and daily open == cross (median gap 0bp) in 2016-20, so the 2021-26 collapse (+17 median; liquid close-cross >$1M n 18 median -17; 43% of splits have no cross at all) is decay/universe, not a daily-vs-auction artifact.

## Study FUND-STATE — does the loser's trailing-earnings state split the night bounce? (2026-10-08; N 900 -> 901)
Disclosure: the design below was frozen in the runner header (research/sim/fundstate.py) before the single run, but this prose entry was written AFTER the run
(process slip; the outcome was unread when the design was fixed, and the bar below is exactly what the code applies).
Hypothesis: a -8%/IBS<0.10 drop in a PROFITABLE name (Sharadar DAILY pe > 0 at the prior session) is more liquidity-driven and bounces more than a drop in a loss-making
name (pe <= 0; solvency/information continuation). Prediction: paired A(pe>0) - B(pe<=0) overnight >= +20bp. Data: nx daily-bar proxy (winsig_l harness), delisted-complete,
ticker-matched to daily.parquet pe at the prior session. Judge 1999-2015 (night unconditional result touched; this conditioner never examined there); 2016-26 reported.
Bar (all): paired >= +20bp, night-clustered t >= 2.5, both halves > 0, raw median diff > 0, ex-top-5 nights > 0, within-night label placebo >= 95th, t above expected-max z at N.
Diagnostics (ungated): marketcap tercile, value (pe 0-15) vs pe>25. Runner research/sim/fundstate.py; out data/research/program/fundstate_out.txt.
### Result: FAIL, wrong sign
1999-2015, 13,686 picks / 2,381 nights, pe coverage 97%, 52% loss-making: A(pe>0) +59.4bp, B(pe<=0) +82.1bp (medians +59.7/+70.7, hit 60.0/60.4%); paired -51.0bp,
t -3.49, halves -19.6/-82.3, ex-top5 -33.0, placebo 0th pct. 2016-26 confirm: paired -1.4bp (t -0.06; 76% loss-making). Marketcap tercile and value-vs-pe>25: null.
The reverse (loss-making bounce more) is unregistered, fails to replicate in 2016-26, and is likely a high-vol/microcap-regime proxy: not a rule. Do not size or filter on EPS sign.

### Result — QI-HIST (judged once 2026-10-08): DEAD on the registered +30bp gate (direction supportive)
Scored 5,602/5,608. 1x net: T1 sell-heavy +24.0bp (median +37, hit 55%), T2 +66.1, T3 +54.6. Skip-T1 gain +12.2bp/trade (< 30), clustered t -2.16,
halves +8.6 / +13.2, ex-top-5 +11.5, placebo 99th pct; by year 2017 -5, 2019 -2. Output data/research/program/qi_hist_out.txt. No re-tuning; BB stays forward.

## Study NEXIT — indicator-gated intraday exit for the night leg vs selling at the open auction (pre-register 2026-10-09; N 901 -> 907)
Question (user): instead of selling every night pick at the 09:30 auction, hold and sell at a local maximum detected by a gate/indicator.
Prior (do not re-derive): fixed later exits are dead (add. 7: open +20.1bp, 10:00 -9.3, 10:30 -21.5); a daily-bar look on 2021-26 (2026-10-09, unregistered)
found close-exit +17bp vs open +25bp and open+k% limit targets ~0. This study tests PATH-DEPENDENT rules that need minute bars, which were never run.
Data: Alpaca SIP 1-min bars 09:30-16:00 of the session after each pick. JUDGE = 2016-2020 exact 15:40 picks (night_exact_pre2021.parquet, n 5,608; exit rules
never examined there). REPORT = 2020-11..2026-09 picks (dtime.pkl T=1540, vol20 >= .6) — touched by the daily-bar look, not judged.
Mechanics: position bought at the prior close; all rules sell 100% once. Signal on a minute close -> fill at the NEXT minute's open. Any rule still holding sells
at the 15:59 bar close (close-auction proxy). Paired per trade vs B0 = (1+overnight) x (exit / 09:30 bar open - 1); intraday exits pay +10bp extra cost (also shown at 5/20).
Rules (frozen; 6 tests):
- R1 trailing stop: sell when a minute close is >= 1% below the running high since 09:30.
- R2 gated local max (user's rule): arm once a minute close >= 09:30 open x 1.02; after arming sell at the first minute close >= 1% below the running high. Never armed -> hold to close.
- R3 = R2 plus a protective stop: sell if a minute close <= 09:30 open x 0.98 before arming.
- R4 momentum turn: 5-min bars, MACD(12,26,9) histogram; sell when it turns negative after >= 3 consecutive positive bars, signals from 09:45 on.
- R5 squeeze fade: 5-min BB(20,2) inside KC(20,1.5) for >= 6 bars, then release; after a release, sell at the first 5-min close below EMA(5) while price > 09:30 open.
- R6 RSI fade: 1-min RSI(14); sell when it crosses back below 70 after >= 3 minutes above 70 and price > 09:30 open.
Gate (all, per rule, 2016-20): paired mean vs B0 >= +15bp at 10bp cost; day-clustered t >= 2.5 (6 tests); both halves 2016-18 / 2019-20 > 0; median paired diff > 0;
ex-top-5 days > 0. 2021-26 must have the same sign to call it supportive. Any PASS goes to forward shadow only. Runner research/sim/nexit.py; out
data/research/program/nexit_out.txt. One run, no tuning of 1%/2%/periods. Survivorship: picks without minute bars are dropped and the count reported.
### Result — NEXIT (2026-10-09, one run; N 901 -> 907): ALL SIX FAIL, every rule worse than selling at the open in both windows
Out: data/research/program/nexit_out.txt. Scored judge 5,484 / report 14,164 (216 dropped, no minute bars). At 10bp: day-clustered t vs B0 (judge / report)
R1 -3.62/-5.12, R2 -2.79/-5.28, R3 -3.85/-5.07, R4 -3.57/-3.09, R5 -3.50/-3.92, R6 -3.56/-4.78; ex-top-5-days negative for all; hold-to-close itself t -2.55/-3.59.
Caveat on the printed means: they are per-TRADE, and Mar-2020 crash days (hundreds of picks, +40..+135% intraday reversals; data checked, genuine) make the
judge-window trade means of CLOSE (+53.7) and R5 (+38.3) positive while the per-DAY mean (how the book sizes: one budget per night) is negative (t < 0).
Gated-local-max rules (R2, R6) win the median trade (~+100bp: they bank +2% on most names) but the un-armed ones bleed to the close. Verdict: the overnight
bounce is spent at the open; no path-dependent intraday exit beats the 09:30 auction. Do not retest with other thresholds/indicators.

## Study OPENSIG — a signal known at the 09:30 open that says "hold this night pick to the close" (pre-register 2026-10-09; N 907 -> 911)
Question (user): which night picks are better sold later in the day than at the open auction? Prior: Study A (hold hard gap-downs <= -5/-8% to 09:35-10:00) DEAD;
NEXIT (path-dependent intraday exits) DEAD; unconditional hold-to-close loses per day. Touched: a 2026-10-09 daily-bar look at 2021-26 showed picks that open red
gain +50bp mean / +10 median open->close, picks that open green -36 / -65. So 2021-26 is touched for gap sign and is the FIT/report window only.
Mechanism: overnight-intraday reversal (Della Corte et al.; CXO): when the overnight bounce has not happened by the open, the liquidity-provision payoff is still owed
and arrives intraday; when it has, the open is the peak of the trade. Market-wide down opens add index-level intraday reversal.
Data: fm1 minute bars (NEXIT). JUDGE 2016-2020 exact 15:40 picks (open-conditioned hold-to-close never examined there). Features at the open only: ovn = 09:30 open /
prior close - 1 (the stock's gap), spy = SPY open / prior close - 1, drop = the signal day's close-to-close return, lp = log 09:30 price.
Exit for a held name = 15:59 bar close (close-auction proxy), extra cost 0 (close cross ~0bp measured live), 5bp shock shown. Not-held names sell at the open (B0).
Paired per trade = held ? (1+ovn) x (close/open - 1) : 0; scored as the per-DAY mean over all picks (book sizes one budget per night).
Rules (frozen; 4 tests):
- S1 hold iff ovn <= 0 (opened red).
- S2 hold iff ovn <= -2%.
- S3 hold iff ovn <= 0 and spy <= 0.
- S4 OLS of open->close on [ovn, spy, drop, lp] fit on 2021-26 picks (winsorised at +-25%), hold iff prediction >= +20bp; applied unchanged to 2016-20.
Gate (all, 2016-20, per rule): per-day paired mean >= +10bp at 0 extra cost and > 0 at 5bp; day-clustered t >= 2.5; halves 2016-18 / 2019-20 > 0; ex-top-5-days > 0;
ex-March-2020 > 0; median open->close of held trades > 0. PASS -> forward shadow only. Runner research/sim/opensig.py; out data/research/program/opensig_out.txt. One run.
### Result — OPENSIG (2026-10-09, one run; N 907 -> 911): ALL FOUR FAIL
Out: data/research/program/opensig_out.txt. Judge 2016-20 per-day gain vs B0 / t: S1 +2.6/0.21, S2 +6.1/0.61, S3 +8.3/0.89, S4 +2.5/0.24; ex-top-5-days negative
for all. Report 2021-26: all negative (S1 -16.2 t -1.68). Held names DO rise open->close per TRADE (judge S1 +87bp, report S2 +97bp) but not per DAY: the
gain sits on crowded washout days (many picks), and on thin days held names keep falling. Unregistered lead, not a rule: "hold only when the night is crowded"
(a market-wide intraday reversal); both windows are now touched for it, so it can only be judged forward.

## Forward shadow CROWD-HOLD (registered 2026-10-09; forward only, no N consumed until judged)
From the OPENSIG lead. swingtrader/daily/crowd_hold_shadow.py (research-shadows, logs only) reads state/night-candidates.jsonl and scores each signal night on
official crosses: hold = (next close cross - next open cross) / signal-day close cross, mean over the night's candidates. crowded = >= 16 raw signals (replay
80th pct of raw signals/night 2020-11..2026-09, the same pre-filter definition the log uses). Gate after 30 crowded nights: mean >= +20bp, night t >= 2, both
halves > 0, median night > 0 -> PASS (pilot = user decision); mean <= 0 -> KILL. Thin nights are the control. Thresholds frozen.

## Study HC-BAN — ban Healthcare-sector names from the night leg (pre-register 2026-10-09; N 911 -> 912)
Question (user): biotech/healthcare picks look weak; does removing them (budget reallocated to the night's other picks) improve the leg, and does that pool
"dilution" explain failed leads? Prior: sector-context conditioners DEAD (K1-K3 industry-residual ranks, L3 sector crowding); a straight sector ban is untested.
Descriptive look (2026-10-09 subagent, 2016-26 exact replay): biotech +11.5bp t 0.84, other healthcare +7 t 0.29 vs all +36; biotech by era +34/+20/-12
(16-19/20-23/24-26), i.e. weak but positive and era-unstable. Rule: drop picks whose Sharadar sector == "Healthcare" (biotech, pharma, devices, services).
Harness = FUND-STATE (nx daily-bar proxy, delisted-complete), judge 1999-2015, 2016-26 reported. Per night: ban = mean of non-HC picks (0 = cash if none),
base = mean of all picks; diff = ban - base, at 5bp/side on both. Gate (all): mean diff >= +10bp, night-clustered t >= 2.5, halves > 0, ex-top-5 nights > 0,
HC picks' own mean < non-HC mean in BOTH halves. Runner research/sim/hc_ban.py; out data/research/program/hc_ban_out.txt. One run.
### Result — HC-BAN (2026-10-09, one run; N 911 -> 912): FAIL
Out: data/research/program/hc_ban_out.txt. Judge 1999-2015 (13,686 picks, HC 12.5%): HC +57.4bp vs non-HC +62.2 (halves +50.6/+68.9, then +71.8/+46.1: HC was
BETTER in 2007-15); per-night ban - base -7.7bp (t -1.37), halves +2.7/-18.1. Report 2016-26 (HC 29%): HC +3.9 vs non-HC +43.3 per trade, yet per night only
+2.1bp (t 0.33): HC picks cluster on nights whose other picks are weak too. "Healthcare is consistently weak" is a post-2016 per-trade pattern only.
Diagnostic (touched, not judged): OPENSIG re-run ex-HC changes nothing (judge S1-S4 t 0.08-1.32; report still negative except S4 +13.7 t 0.94): healthcare
dilution does not explain the dead exit leads. Variance machine categories.txt (2016-24 folds + 2024-10.. holdout): banning biotech worsens 2020-22 (-6.2 bp/day).

## Study CAT-MOM + DEPTH — category momentum and "trade deeper" for the night leg (pre-register 2026-10-10; N 912 -> 916)
Harness = HC-BAN / FUND-STATE (nx daily-bar proxy, delisted-complete). JUDGE 1999-2015, REPORT 2016-26. Per night: base = equal-weight mean of all picks;
each arm keeps the same one-night budget (0 = cash if it keeps nothing); diff = arm - base; 5bp/side. Gate (each arm): mean diff >= +10bp, night-clustered
t >= 2.5, halves > 0, ex-top-5 nights > 0. Risk reported (nightly std, Sharpe, worst night) because concentration changes variance, not just mean.
- CM12 (user: "predict what works in the current time frame"): category = nx sector of the pick. At each month start, rank categories by their trailing-12m
  mean net night return per trade (picks strictly before the month, >= 30 picks, else unranked = kept); keep picks in categories at or above the median ranked
  category. CM6: same with 6 months. Mechanism: if category edge comes from persistent flow/panic regimes, recent category returns persist.
- TOP2 (variance-machine winners' common theme, 2026-10-10): keep only the 2 deepest day_ret picks each night, equal weight. DEPTHW: all picks weighted by
  |day_ret|. Mechanism: deeper drops = more panic overshoot (2016-26 depth gradient +11bp at -8..-10% to +191 at <= -30%, descriptive; 1999-2015 unseen for depth).
Runner research/sim/catmom_depth.py; out data/research/program/catmom_depth_out.txt. One run.
### Result — CAT-MOM + DEPTH (2026-10-10, one run; N 912 -> 916)
Out: data/research/program/catmom_depth_out.txt. JUDGE 1999-2015 (13,686 picks, 2,381 nights, base +57.6bp/night, Sharpe 2.21):
- CM12 FAIL: -6.7bp (t -2.27); CM6 FAIL: -9.3bp (t -3.12). Category momentum is WRONG-SIGNED: last year's best categories do worse next. Report 2016-26 +0.6 / -7.3.
- TOP2 PASS: +71.8 vs +57.6, diff +14.2bp t 3.37 (expected-max z at N 916 ~3.06), halves +12.0/+16.4, ex-top5 +14.8; Sharpe 2.34 vs 2.21, std 488 vs 414.
  Report 2016-26: +17.5 t 2.05 but halves -0.7/+35.6, Sharpe 1.17 vs 1.16 at std 650 vs 414: in the recent era it is the base levered ~1.57x, no risk-adjusted gain.
  1999-2015: base levered to TOP2's std would be ~+67.9, so TOP2 beats leverage by only ~4bp. Mostly concentration; small selection gain in the old era.
- DEPTHW FAIL: +3.0 (t 1.86).
News-judge forward check (state/news-judge*.jsonl, crosses): calls 60/63 forward drops "liquidity", so it barely discriminates; forward liquidity +20.5bp
(n 57) vs fundamental n 2; Aug-2025 backfill liquidity -53.9 (n 121) vs fundamental +24.7 (n 42), the opposite sign. No evidence either way.

## ROBUST-MAP + TOP2-SIZE + TOP2-STRESS + HEDGE-SHADOW (registered 2026-10-10; descriptive, no settings change, no N consumed)
ROBUST-MAP (night, IBS, noise legs): random settings within stated ranges around the LIVE values; metric = net bp/day of account for the leg (no-trade days 0)
and annualised Sharpe, costs as each leg's research default. Outputs per leg: live's percentile among all settings; 1-D profiles (one param varied, others
at live); neighbourhood = settings within +-1 grid step on every param. FRAGILE if live > 1.5x the neighbourhood median OR any single +-1-step move loses
> 50% of live. PLATEAU if >= 70% of the neighbourhood keeps >= 50% of live. Else MIXED. A FRAGILE verdict is a sizing/caution flag for the user; no setting
is changed on this evidence (the map is not a search: the best cell is NOT a candidate).
TOP2-SIZE: account simulation at $2.3k / $10k / $25k (+$100k one line), whole shares, live night weight, cash vs Reg-T margin: (a) live all-picks, (b) TOP2,
(c) live all-picks levered to TOP2's nightly std, (d) TOP2 at live gross. Report CAGR, max DD, Sharpe, worst night; 1999-2015 and 2016-26 separately.
TOP2-STRESS: block bootstrap (20-night blocks) of the nightly TOP2-base diff, ex-crash years (2000-02, 2008-09, 2020), ex-top-10 nights, by year.
HEDGE-SHADOW (forward only, logs): exponential-weights (Hedge, learning rate eta=0.5 on nightly net return in %) over a fixed grid of night configs
(drop cutoff {-8,-10,-12,-15}% x top_k {all,2,4}); each night the weighted-top config is "chosen". Gate after 120 scored nights: chosen-config series beats
the live all-candidate series by >= +10bp/night, t >= 2, halves > 0; kill <= 0. Grid and eta frozen.
### Results — ROBUST-MAP / TOP2-SIZE / TOP2-STRESS (2026-10-10)
Outs: data/research/program/{robust_night,robust_ibs,robust_noise,top2_size,top2_stress}_out.txt.
- Night ROBUST-MAP: PLATEAU both eras (live/neighbourhood median 1.03x / 1.04x, every neighbour >= 50% of live, live 88th / 70th pct of 1,500 random
  settings, all random settings positive). Wide-table live reproduces nx base within -2.8 / -1.7bp (no dedupe/crowd). Sharpest axis: price_min ($3 > $5 > $10 in 2016-26).
- IBS ROBUST-MAP: FRAGILE 2004-15 (live 2.2x neighbourhood median) and 2016-20 (1.66x; 9-1 momentum keeps 37%), PLATEAU 2021-26 (where 99% of settings are positive).
- Noise ROBUST-MAP: PLATEAU at 1bp RT both eras; at 4bp RT 2016-20 live is negative and 2021-26 FRAGILE. Cost, not parameters, is the leg's risk.
- TOP2-SIZE: at matched risk the all-picks night levered ~3.8x beats TOP2 on Sharpe in both eras (1.98 vs 1.64; 1.23 vs 1.12); TOP2 at live gross has a lower
  Sharpe than live. TOP2-STRESS: 1999-2015 gain ex-crash-years +2.0bp t 0.54 (crash-carried); 2016-26 +18.1 t 2.0 ex-crash. => TOP2 is concentration, not edge.
- Finding: the live night leg deploys only ~0.16 of equity on average (per-name min(1/n, night_max_name_pct 0.10) x night_weight 0.5 binds when < 10 picks).
  Sizing is a user decision (NX: validated-small; size-ups only while live auction cost stays ~0bp).
### Result — NIGHT-CAP sizing grid (2026-10-10, descriptive; research/sim/night_cap.py, out night_cap_grid_out.txt)
Night leg alone, $10k, 5bp/side (cap = night_max_name_pct; live 0.10): 1999-2015 CAGR/maxDD/Sharpe/worst night: .10 15.1/-18.2/1.93/-5.2; .15 19.6/-22.2/2.03/-7.8;
.20 23.2/-25.2/2.06/-10.4; .30 27.8/-30.1/2.00/-15.7; .50 33.6/-33.6/1.84/-17.4. 2016-26: .10 12.4/-14.7/1.16/-7.2; .15 16.3/-20.9/1.19/-10.3; .20 19.2/-24.1/1.17/-11.6;
.30 23.3/-26.0/1.15/-17.4; .50 25.3/-37.9/1.03/-28.9. Sharpe flat-to-up through .20, falls above .30. At 10bp/side the ordering holds. Daily-bar proxy (~1.7x
optimistic vs exact 15:40 per NX): levels overstated, relative ordering is the read. Night-only drawdowns at .20 (-24/-25%) sit at the book's -25% halt before the IBS leg.

## Study TREND-NIGHT — night-leg picks split by the stock's own prior trend (pre-register 2026-10-10; N 916 -> 919)
Dedupe: NEXT do-not-redo has 20d/52w-distance night tilts (add. 23, dead), 52w-high nearness (Lab-BO, dead), and a trend filter on the IBS leg (AT: -7pp/yr,
"downtrend dips revert the most"); idea_scan 2026-10-08 row 18 left "ma200 trend state of the loser" OPEN. The night pick's own 200d SMA / 126d / 252d
trend has never been judged. Prior leans wrong-sign (AT), stated before the look.
Ceiling (filter on an existing leg): ~140 trade nights/yr x +10bp x night weight ~0.5 = ~+7pp/yr on the daily-bar proxy (~+4pp at the exact rule's ~1/1.7
ratio); clears the +1pp filter gate; daily bars only, cheap to run.
Harness = CAT-MOM (nx daily-bar proxy on Sharadar, delisted-complete, 5bp/side, nightly equal weight, arm reindexed to base nights with 0 when no pick qualifies
= budget to cash). Trend is measured on bars STRICTLY BEFORE the signal day (the shock day itself is excluded): c_prev = prior close, adjusted closes.
- TA: c_prev > mean of the 200 closes ending at c_prev (200d SMA).  - TB: c_prev / close 126 bars earlier - 1 > 0.  - TC: c_prev / close 252 bars earlier - 1 > 0.
Picks with fewer bars than the lookback are EXCLUDED from the arm (unknown trend is not an uptrend) and reported as a third bucket descriptively.
Hypothesis: a -8% day in an uptrending name is a dip in a strong stock and bounces more; arm (uptrend only) beats base (all picks).
Judge 1999-2015 (this variable never examined there); report 2016-26 (touched). One run, thresholds fixed.
Gate (all, per arm): diff = arm - base >= +10bp/night net of 5bp/side; night-clustered t >= 2.5 AND >= expected-max z at N 919 (~3.06); both halves > 0;
median of (arm - base) over nights where they differ > 0; ex-top-5 nights > 0; survives 2x cost (10bp/side); ex-crash years (drop 2000-02, 2008-09, 2020) > 0;
at matched std the arm beats the base levered to the arm's std (arm.mean > base.mean x arm.std/base.std + 0). Kill rule: any gate fails -> FAIL, no re-tuning of
lookbacks; if the split is wrong-signed (downtrend picks earn more), record that as the class verdict for trend-conditioning on the night leg.
Runner research/sim/trend_night.py; out data/research/program/trend_night_out.txt. Log research/drafts/trend_loop_2026-10-10.md.
### Result — TREND-NIGHT (2026-10-10, one run; N 916 -> 919): ALL THREE FAIL, wrong-signed
Out: data/research/program/trend_night_out.txt. JUDGE 1999-2015 (13,686 picks, 2,381 nights, base +57.6bp/night): TA (c_prev > SMA200) arm +36.5 vs base,
diff -21.1bp t -3.74, halves -27.0/-15.2, ex-top5 -25.4, 2x cost -17.7, ex-crash -19.0; TB (126d > 0) diff -16.0 t -2.96, halves -19.1/-13.0, ex-top5 -20.4;
TC (252d > 0) diff -23.4 t -3.86, halves -32.6/-14.2, ex-top5 -21.6. Per trade, uptrend picks earn LESS or the same as downtrend picks (TA +53.3 vs +58.3,
TB +59.9 vs +55.5, TC +55.5 vs +53.2): the -8% day in a strong stock does not bounce more. Report 2016-26: all diffs -12..-16bp (t -1.5..-2.0), up vs down
+29 vs +21. Every arm also loses to the base levered to its std. Disclosure: the first TA run used a cumulative-sum SMA that lost float precision (some
Sharadar adjusted closes are ~1e10; 93% "up" was an artifact); recomputed with an exact per-ticker rolling mean, TB/TC unchanged. nx._roll_prior uses the
same cumsum for ADV/vol20 but on sums (~1e8 / ~1e4) where the error (~1e2 absolute at the cumsum's ~2e17 scale) is immaterial; noted as a hazard.
CLASS VERDICT: trend-conditioning on the night leg is closed (with AT on IBS: "downtrend dips revert at least as much"). No lookback re-tuning.
Unregistered observation (both windows now peeked for it, descriptive only): picks with < 252 prior bars in the panel ("young listings": IPOs, de-SPACs, ticker
changes) earn +82.6bp mean / +74.1 median vs +43.1 / +41.0 for older names (1999-2015 ex first 430d, n 1,624 vs 9,608; young-old > 0 in 11/15 years) and
+65.7 / +54.9 vs +25.7 / +21.8 (2016-26, n 1,657 vs 8,585; 7/10 years). Candidate YOUNG-NIGHT (a per-night tilt, with ticker-change contamination removed via
permaticker first-price date) must be pre-registered as a PEEKED lead: per-trade means are known, the per-night budget statistic is not.

## Study REGIME-10M — Faber 10-month SMA market gate on the whole daily-bar book (pre-register 2026-10-10; N 919 -> 922)
Dedupe: add. 37 / NEXT "Regime gates (SPY 5d return, VIXY fear proxy): dead; SPY>200dma only buys Sharpe for return" was judged on the 2021-26 cache only; Lab-BY/BZ
used the 10m filter on momentum sleeves (not this book). The gate has never been run through 2000-02 / 2007-09 on the delisted-complete book. Purpose: cut
drawdowns in slow bears (SHAR-CRASH: 2000-02 maxDD -24%) without paying return. Prior (stated before the look): both legs earn MORE in high-vol/bear
states (NX, add. 26a), so the gate likely removes winning nights; the user's objective is %/yr, so a return-costing gate fails even if DD improves.
Ceiling: SPY is below its 10m SMA ~30% of months; if those nights earn the base mean, the gate costs ~30% of book return; if they earn <= 0 it adds up to that.
Harness = SHAR-CRASH daily-bar book (0.5 IBS EQ18 live rule + 0.5 night via nx.collect_trades, per*ret, delisted-complete SEP+SFP), extended to the full
1999-2015 judge span and 2016-26 report; costs 5bp/side on both legs. Signal: SPY month-end close (Sharadar SFP, split-adjusted) at m-1 vs the mean of the 10
month-end closes m-10..m-1; below -> OFF for every session of month m (cash = 0). Arms: G1 whole book OFF; G2 night leg OFF only; G3 IBS leg OFF only.
Gate (all, per arm, judge 1999-2015): (a) arm CAGR >= base CAGR - 0.5pp; (b) maxDD in 2000-02 AND 2007-09 improves by >= 5pp each; (c) arm Sharpe > base;
(d) mean book return on OFF sessions <= 0 (t <= 0) in both halves of the judge span. Report 2016-26 (incl. 2018Q4, 2020, 2022). FAIL if any gate fails; no
lookback (10m) or threshold re-tuning; a FAIL with gated-off nights earning MORE than the base closes the class "market-trend gates on the MR book".
Runner research/sim/regime_10m.py; out data/research/program/regime_10m_out.txt.
### Result — REGIME-10M (2026-10-10, one run; N 919 -> 922): ALL THREE FAIL; class "market-trend gates on the MR book" CLOSED
Out: data/research/program/regime_10m_out.txt. Judge 1999-2015 (4,277 sessions, SPY below 10m SMA on 31%): base CAGR 16.0%, Sharpe 1.41, maxDD -25.7%
(2000-02), -12.2% (2007-09). Book return on OFF sessions +4.9bp/day (t 1.95; halves +4.3/+5.6), ON +6.7; night leg OFF +9.9 vs ON +12.0bp/day, IBS OFF -0.2 vs
ON +1.4. G1 (book OFF): CAGR 12.1% (-3.9pp), Sharpe 1.54, maxDD -13.6% (2000-02 +19.4pp, 2007-09 +6.3pp better) - a drawdown dial paid for in return (gate a, d
fail). G2 (night OFF): CAGR 11.8%, Sharpe 1.23, maxDD worse (-27.6%): fails everything. G3 (IBS OFF): CAGR 16.3% (+0.3pp), Sharpe 1.66, maxDD -17.9%
(2000-02 +7.8pp, 2007-09 +6.1pp), but OFF-day removal t > 0 in one half (gate d) -> FAIL as registered; and in 2016-26 the IBS leg earns MORE on OFF days
(+6.4 vs +3.1bp/day) so G3 costs 1.4pp/yr there (CAGR 6.1 vs 7.5). Report 2016-26 (18% OFF): OFF sessions +5.3bp/day vs ON +2.5; G1 CAGR 5.1 vs 7.5 (2020 maxDD
-2.7 vs -11.7, 2022 -5.1 vs -10.2). Reading: both MR legs earn at least as much when SPY is below trend; any trend gate trades %/yr for drawdown, which is the
opposite of the user's objective. With TREND-NIGHT and AT this is three same-way deaths: trend/regime conditioning of the mean-reversion book is CLOSED (the
SPY>200dma "Sharpe for return" verdict of add. 37 now holds on 1999-2015 as well). G3 is the only arm that is return-neutral pre-2016; it is a drawdown lever
for the user to weigh, not an edge, and it is wrong-signed in the recent era.

## Study YOUNG-NIGHT — listing-age tilt on the night leg (pre-register 2026-10-10; N 922 -> 924; PEEKED lead)
Origin: TREND-NIGHT's "unknown trend" bucket (< 252 prior bars in the loaded panel) earned +83/+74 (mean/median) vs +43/+41 in 1999-2015 and +66/+55 vs +26/+22 in
2016-26 per trade. Those per-trade means were SEEN in both windows; the per-night budget statistics, halves, ex-top-5, placebo and the age definition below were
not. Dedupe: NEXT "night picks on lockup-expiry days" dead (n 23, -122bp) is a different (event-day) variable; de-SPAC / OTC-uplist FIRST-night studies are
different trades. Listing age as a night-leg conditioner is untested.
Mechanism: young listings (IPOs, direct listings, spin-offs, up-listings) have an unseasoned, retail- and allocation-flipper-heavy holder base, lock-up overhangs and
thin analyst coverage; a -8% day in such a name is more often a liquidity cascade than news, so the overnight bounce is larger. Named sellers: IPO flippers and
pre-lock-up holders (soft constraint), plus margin/retail capitulation. Capacity: small-account friendly (young names are thin).
Ceiling (filter on the night leg): young ~15% of picks; Y1 moves ~13% of budget to names earning ~+40bp more = ~+5bp/night ~ +3.5pp/yr proxy (~+2pp exact); Y2
(young-only on nights that have a young pick, ~50% of nights) could reach +10-20bp/night but is concentrated. Clears the +1pp filter gate; cheap (daily bars).
Definition (fixed): age = signal date - master.firstpricedate (SEP, Sharadar first price date; names at the 1997-12-31 floor are old); YOUNG = age < 365 days.
Harness = TREND-NIGHT (nx daily-bar proxy on Sharadar SEP, delisted-complete, 5bp/side, nightly EW, arm reindexed to base nights).
- Y1: young picks weighted 2x within the night's budget (others 1x; renormalised).  - Y2: on nights with >= 1 young pick keep only young picks, else all picks.
Descriptive (not arms): per-trade means by age bucket (<0.5y, 0.5-1y, 1-2y, 2-5y, 5y+), young picks' ADV/price/category mix and delisting-outcome counts, and a
PLACEBO: 200 random pick subsets of the same share per night given the same Y1/Y2 treatment (the real diff must exceed the 99th percentile).
Gate (PEEKED => must hold in BOTH 1999-2015 and 2016-26, each): diff >= +10bp/night net; night-clustered t >= 3.06 (expected-max z at N 924); halves > 0; median of
diff over nights where arm != base > 0; ex-top-5 > 0; 2x cost > 0; ex-crash (2000-02, 2008-09, 2020) > 0; beats the base levered to the arm's std; placebo < real.
Kill: any gate fails in either window -> FAIL, no re-definition of "young" (no age re-tuning). If the age gradient is monotone and Y1 passes only the sign,
record as a validated-small observation, not a pass. Runner research/sim/young_night.py; out data/research/program/young_night_out.txt.
### Result — YOUNG-NIGHT (2026-10-10, one run; N 922 -> 924): BOTH ARMS FAIL; listing-age gradient recorded as a validated-small observation
Out: data/research/program/young_night_out.txt. Young (< 365d since first price) = 17.8% of 1999-2015 picks (on 34% of nights), 15.7% of 2016-26 (39%).
Per-trade age gradient is monotone in 1999-2015 (<0.5y +100 / 0.5-1y +90 / 1-2y +69 / 2-5y +50 / 5y+ +50 bp net; medians +109/+80/+69/+55/+35) and nearly so in
2016-26 (+82 / +43 / +57 / +21 / +21; medians +55/+53/+33/+20/+20); young-old > 0 in 12/16 and 7/11 years. Young picks are NOT thinner (ADV median $25-34M vs
$30-38M), are higher-priced and higher-vol, no delisting outcomes. But per NIGHT (budget reallocated): Y1 (2x weight) +0.64bp t 1.03 (placebo 99th +1.48) and
+1.16 t 1.18 (99th +3.34); Y2 (young-only when available) +4.69 t 1.66, halves +4.3/+5.1, median(!=0) +20.2, ex-top5 +5.1, ex-crash +1.5, placebo 99th +7.69;
2016-26 +7.63 t 1.72, halves +8.8/+6.4, ex-top5 +11.3, placebo 99th +19.5. Y2 beats the levered base by ~2-4bp only. FAIL on size (< +10bp), t and placebo in
both windows. Reading: a real per-trade effect (~+40bp) that the night leg's EW budget can only convert into +1-8bp/night because young names are a sixth of
picks on a third of nights; concentrating on them adds variance faster than return. Not a filter candidate; no re-definition of "young". Kept as an
observation for per-name sizing research only if a sizing framework ever exists (none planned). Program N = 924.

## Study BREAK-REV — post-deal-break forced liquidation by merger arbitrageurs (pre-register 2026-10-10; N 924 -> 927)
Dedupe: Round 32 B3 held cash-tender targets to completion (dead: spread ~+0.4%, failures -20..-42%); the FAILURE itself as an event, and what happens AFTER the
break-day drop, has never been tested. Not a night-leg costume: the night leg trades only close->open on the shock day; this trades the following 1-20 sessions.
Mechanism: on a deal break, merger-arb funds (levered, mandate-bound to deal spreads, often with the acquirer short) must liquidate the target over the following
sessions; the shock-day price absorbs part of it, the remainder is multi-day price pressure that reverses once the arb inventory is gone. Named, constrained
counterparty (merger arbs); thin post-break books favour small size; history 2001+ (EDGAR FTS). Falsifiable: if post-break returns are flat or negative, the
break-day price already clears the arb inventory (or the drop is information, not flow).
Ceiling (standalone): ~30-60 US listed-target breaks/yr; need >= +1% net abnormal per event: 40 x 1.0% x ~70% of capital deployable (one event at a time,
10-day hold) x 50% capture = ~+14pp/yr at $10k; at +0.5%/event ~+7pp (fails). Gate bar set at +1.0%/event accordingly.
Data: EDGAR FTS 8-K metadata 2001-2026 for merger-termination phrases (research/sim/break_fetch.py, items include 1.02), filer tickers from display_names;
Sharadar SEP raw-adjusted prices (delisted-complete) + SPY. Event identification (fixed): for each filer ticker with Sharadar bars, D0 = the session in
[file_date - 3 sessions, file_date + 1 session] with the most negative close/close return; keep if ret(D0) <= -7% (the target; acquirers rise or move little).
One event per ticker per 60 sessions. Costs 25bp/side (mid-cap, post-break spreads); 2x = 50bp/side.
Arms (abnormal = raw - SPY over the same window; net of 2 sides): A1 buy D1 close -> sell D10 close; A2 buy D0 close -> sell D5 close; A3 buy D3 close -> sell
D20 close. Also reported (not arms): D0 close -> D1 open (the night leg's piece), the D0 shock size, the path D0..D20 in 1-session steps.
Control (required): all Sharadar common stocks with a close/close day <= -7% in the same calendar month (<= 300 sampled per month, excluding event names), the
same three windows, EW: the generic post-crash drift. Real arm must beat the control by >= +1.0%.
Gate (all, per arm): mean net abnormal >= +1.0%/event; month-clustered t >= 2.5 and >= 3.06 (expected-max z at N 927); halves (2001-13 / 2014-26) > 0;
median > 0; ex-top-5 > 0; survives 2x cost; ex-crash years (2001-02, 2008-09, 2020) > 0; beats the control by >= +1.0% (t >= 2). Kill: any gate fails -> FAIL;
no horizon or threshold re-tuning. n < 60 identified events -> UNDERPOWERED, report only.
Runner research/sim/break_rev.py; out data/research/program/break_rev_out.txt.
### Result — BREAK-REV (2026-10-10, one run; N 924 -> 927): UNDERPOWERED (n 44), edge unproven, ceiling-limited by event identification
Out: data/research/program/break_rev_out.txt; events data/research/events/break_events.csv; FTS metadata break_hits.json (1,008 8-Ks with item 1.02 matching
merger-termination phrases, 2004+; FTS item tags are empty before 2004). Only 44 filers had a <= -7% session in [file-3, file+1] (2007-2026, 2-6/yr; median shock
-12%): most 1.02 filers are acquirers or private-target parents, and breaks announced > 3 sessions before the 8-K are missed. Pre-registered rule: n < 60 ->
report only. A2 (D0 close -> D5 close) net +3.04% (t 1.53), median +2.92, hit 55%, halves +1.18/+3.65, ex-top-5 -0.44, control (68k generic <= -7% days) -0.18%,
diff +3.22 t 1.52. A1 (D1c -> D10c) +2.16% t 0.69, median -1.97, ex-top-5 -2.71. A3 (D3c -> D20c) -3.48% t -1.59. Path: D0 close -> Dk mean abnormal -0.2 (k1),
+2.8 (k3), +4.4 (k9), +1.3 (k11-13), ~0 by k15-20: a reversal that fades, consistent with a flow effect but outlier-carried at this n. Night piece D0c -> D1o
-0.13% mean. Status: EDGE UNPROVEN (not "no edge"): a bettor-scale +3%/event point estimate with CI through zero. Ceiling re-estimate with the OBSERVED
identifiable rate (<= 6/yr via free EDGAR text): 6 x 3% x 70% x 50% ~ +0.6pp/yr -> fails the +8pp gate regardless of significance. A decisive test needs a
deal database with announced break dates and public targets (SDC/Refinitiv/Bloomberg: paid) or a much better free identifier (press-release 8-K 8.01 scan with
both parties). Any re-run must be a new registration judged on events NOT among these 44. DATA-LIMITED; no re-tuning of the -7% / window / horizons.

## Study DRIP-PAY — dividend PAY-DATE reinvestment price pressure (pre-register 2026-10-10; N 927 -> 930)
Dedupe: DM (dividend-month premium, N 836) tested the monthly payer spread and the EX-DATE window (T-5..T+5, dead); DL1/CPC tested DRIP optional-cash DISCOUNTS;
EXDIV-OPEN / PREF-EX trade the ex-night. The PAY date (2-4 weeks after ex) has never been examined. Mechanism (Berkman & Koch 2017, JFQA "DRIPs and the dividend
pay date effect"; Hartzmark & Solomon's pay-date leg): brokers and transfer agents reinvest DRIP cash in the market ON the pay date, a mechanical, dated buy
order whose size is the cash paid x the DRIP participation share; it is price-insensitive and concentrated in retail-heavy payers. Named constrained buyer:
DRIP agents (must buy that day). Expected sign: positive close(D-1) -> close(D) abnormal return on pay date D, larger when cash paid is large relative to
daily volume; placebo dates (D-5, D+5) ~ 0. Who pays: DRIP holders (they buy at a pressured price). Persists because DRIP execution is contractual.
Ceiling (daily shape): ~20 tradable pay dates per session; buy close(D-1) / sell close(D) at the auctions (cost ~0-5bp/side); if +10bp net x 50% of capital
daily -> ~+12pp/yr at any size <= $25k; at 50% capture of a +15bp published effect -> ~+9pp. Clears the +8pp gate only if the net effect is >= ~+8-10bp/event.
Data: Alpaca corporate actions (cash_dividend with payable_date; available 2021+, absent before), fetched by research/sim/drip_fetch.py to
data/research/events/alpaca_cash_divs.parquet; prices = Sharadar SEP split-adjusted close/open + SPY (funds). Universe: Sharadar common stocks (SEP), raw price
>= $5 at D-1, 20d ADV$ >= $5M, rate > 0, non-special. Pressure proxy = rate x shares outstanding (Sharadar DAILY/SF1 'sharesbas' nearest prior) / 20d ADV$ =
"days of volume paid out". Judge 2021-01..2026-09 (the only era with pay dates; halves 2021-23 / 2024-26; this variable is new to every window).
Arms: P1 all qualifying pay dates, EW per day, close(D-1) -> close(D) abnormal (minus SPY); P2 top tercile of the pressure proxy (tercile cut within each
calendar month, no look-ahead); P3 = P2 but open(D) -> close(D) (the reinvestment executes during the day). Also reported: ex-date-same-day exclusion (pay dates
that coincide with another ex-date are dropped from all arms), the P2 night piece close(D-1)->open(D), and the D-5 / D+5 placebo for each arm.
Gate (all, per arm): mean net >= +10bp/event at 5bp/side; day-clustered t >= 2.5 and >= 3.06 (expected-max z at N 930); halves > 0; median per-day > 0; ex-top-5
days > 0; survives 2x cost (10bp/side); beats the same-names D-5 and D+5 placebos by >= +8bp each (placebo |mean| < half the real); not carried by one
sector (ex-REIT/utilities > 0). Kill: any gate fails -> FAIL; no tercile/threshold re-tuning; P1 passing with P2 not larger than P1 = mechanism unsupported -> FAIL.
Runner research/sim/drip_pay.py; out data/research/program/drip_pay_out.txt.
(Implementation note, written before the look: Sharadar DAILY carries marketcap, not shares; the pressure proxy is therefore (rate / close(D-1)) x marketcap(D-1) /
ADV20$(D-1) = cash paid / daily dollar volume, algebraically the same quantity.)
### Result — DRIP-PAY (2026-10-10, one run; N 927 -> 930): ALL THREE FAIL, wrong-signed; no pay-date footprint
Out: data/research/program/drip_pay_out.txt. 189k Alpaca cash dividends with pay dates 2021-01..2026-09; 25,783 qualifying events (price >= $5, ADV >= $5M) on 1,439
sessions (17.9/day). P1 (all payers, close(D-1)->close(D) minus SPY) net -15.5bp/day, t -6.36, median -17.6, halves -14.9/-16.1, ex-top-5 -16.8; placebos D-5
-12.5 (t -5.3), D+5 -11.1 (t -4.5). P2 (top pressure tercile) -15.6 t -4.35; terciles show NO gradient (gross -6.5 / -7.4 / -3.9bp). P3 (top tercile intraday
open->close) -27.8bp t -8.72: the reinvestment hours are the WORST part of the day. Payer universe lags SPY ~5-7bp/day gross on every day (size/beta tilt of
EW payers in a tech-led market), pay dates no better than placebo days. By year P2: 2021 -10, 2022 -3, 2023 -27, 2024 -24, 2025 -21, 2026 -8. Only positive
piece: P2 close->open +12.1bp gross (no placebo computed; unregistered, not a candidate: the common ex-night/overnight family is closed). Note: Sharadar DAILY
marketcap is in $ millions, so the printed pressure medians read 0.000; ranking (terciles) is scale-invariant and unaffected. CLASS: dividend-calendar flows on
common stock (ex-date: DM/EXDIV-OPEN; pay date: DRIP-PAY) are closed at the daily tier; the only surviving dividend mechanism is the $25-par income-paper ex-night
(PREF-EX/ETDX). Program N = 930.

## Study BREAK-REV2 — post-deal-break reversal, free-identifier widening via CIK (pre-register 2026-10-10; N 930 -> 931)
Why: BREAK-REV (N 924-927) was UNDERPOWERED (n 44) because the free identifier mapped EDGAR FTS hits to tickers only through the
"(TICK)" in display_names, which only currently-listed filers carry: 710 of the 1,008 item-1.02 hits have no ticker (delisted
targets, i.e. exactly the names that later got acquired or died). Sharadar TICKERS carries the CIK (secfilings URL) for 73,716 rows
incl. 36,723 delisted, so the same hits can be mapped by CIK. This is the "cheaper dataset" alternative to a paid deal database
(deploy_loop_2026-10-10.md 2(b)); no new text queries, no new price data. Written before any price of a new event is read.
Rule (FROZEN, identical to BREAK-REV): for each hit, candidate tickers = display-name ticker (as before) UNION Sharadar common-stock
tickers (categories Domestic Common Stock / ... Primary Class) whose CIK equals a hit CIK and whose price history covers
[file_date - 3, file_date + 1] sessions; D0 = the session in that window with the most negative close/close return; keep if
ret(D0) <= -7% and prior raw close >= $2; one event per adsh (most negative shock across its tickers) and one per ticker per 60
sessions. EXCLUDE the 44 adsh judged in BREAK-REV (data/research/events/break_events.csv): the new sample is disjoint. Arms, costs,
control, windows, SPLIT 2014, crash years: unchanged (A1 D1c->D10c, A2 D0c->D5c, A3 D3c->D20c; 25bp/side; same-month <= -7% control).
Gate (per arm, unchanged): mean net abnormal >= +1.0%/event; month-clustered t >= 2.5 and >= 3.06 (expected-max z at N 931);
halves (<2014 / >= 2014) > 0; median > 0; ex-top-5 > 0; 2x cost > 0; ex-crash > 0; beats control by >= +1.0% (t >= 2). Kill: any gate
fails -> FAIL. n < 60 new events -> UNDERPOWERED again and the free path is exhausted (then only a paid deal database remains).
Also reported (not gated): the pooled 44 + new sample, and the identified rate/yr (ceiling re-estimate: rate x median net x 70% x 50%).
Prediction: if the mechanism is flow, the delisted-heavy new sample (smaller, thinner targets) should show a LARGER A2 than the 44.
Runner research/sim/break_rev2.py; out data/research/program/break_rev2_out.txt. Program N = 931.

### Result — BREAK-REV2 (2026-10-10, one run; N 930 -> 931): FAIL x3, wrong-signed; post-break reversal DEAD at free data
CIK mapping worked: 85 NEW events (all via Sharadar CIK, 0 via display-name ticker), 2004-2026, median shock -16.8%, 42/43 by era;
pooled with the 44: 128 events, 5.8 breaks/yr identified. Judged arms (new events, net 25bp/side): A1 D1c->D10c -2.26% (t -0.55,
median -4.18, hit 33%, halves -3.55/-0.97, ex-top5 -8.42); **A2 D0c->D5c -2.84% (t -1.22, median -4.22, hit 32%, halves -4.63/-1.05,
control -0.08, diff -2.76 t -1.17)**; A3 D3c->D20c +1.62% (t 0.30, median -2.37, ex-top5 -5.86). Path: -4.3% by day 9, back to ~+1 by
day 14 = no reversal, a continued slide then noise. Pooled 128: A1 -0.74, A2 -0.82 (median -2.60), A3 -0.13; every arm fails every
gate. Shock buckets invert the flow story again: <= -20% breaks -12.1% (new) / -8.3% (pooled); only the mildest (-12..-7) are positive
(+0.7 / +3.5). Prediction falsified: the delisted-heavy sample bounces LESS, not more. Read: the break-day drop is information
(the target's standalone value is lower than the pre-deal price), not arb inventory; BREAK-REV's +3.04% on 44 was a small-sample
outlier draw (ex-top-5 was already negative). Night piece D0c->D1o +1.41% mean / +0.24 median (n 84; unregistered, overlaps the
night leg's class, not a candidate). CLASS CLOSED: post-deal-break target reversal at daily prices. The free identifier now reaches
~6 breaks/yr identified / 128 total; a paid deal database would add events, not change the sign. Do NOT buy one for this. Program N = 931.

## Amendment — Study GAMMA-FREE: signed dealer gamma (free proxy) -> SPY last-30-minute continuation, forward-only (2026-10-10; N 931 -> 932)
Written before any forward row is read; the 2016-26 minute window is TOUCHED (market-map probe +8.3bp t 1.9; the free proxy also
failed the untouched 2016-20 window as a night-leg gate), so this is a forward falsification only, as `shadow_dealer_gamma.md`
specifies and as the data-buy rule requires before any OPRA purchase. Mechanism: dealers short gamma hedge WITH the move into
the close. Observable: SqueezeMetrics model-signed SPX GEX (DIX.csv, free, published after the close) -> on session D use
GEX(D-1); short_gamma = GEX(D-1) < 0 (z vs the prior 21 sessions logged, not gated). Trade logged: SPY enter 15:30 in the
direction of the 09:30 -> 15:30 move (first regular minute's open -> 15:29 bar close), exit at the official closing cross;
cont = sign(move) x (close/p1530 - 1); net 1bp/side. Long-gamma days = control; long-only half (move > 0) reported for the Roth.
Gate: 120 forward short-gamma days (FORWARD_FROM 2026-10-13). KILL = mean net <= 0; PASS = mean >= +5bp/trade and t >= 2
(= the bar for considering ~$180/yr OPRA strike-level data); else HOLD. Ceiling is small by construction (~10-40 short-gamma
days/yr x <= 10bp on the SPY sleeve): this is a sensor test, not a standalone edge. Runner swingtrader/daily/gamma_state_shadow.py
(research-shadows), REGISTRY "GAMMA-FREE". Program N = 932.

## Amendment — Study CEF-PEER: CEF-RV excess vs a SAME-CATEGORY equal-weight CEF peer index (pre-register 2026-10-10; N 932 -> 933)
Open question left by CEF-ALPHA (N 892): the +125bp/trade excess vs the EW CEF universe could be a category tilt (CEF-RV
entries cluster in whichever sector just sold off; the EW universe is ~45% muni). Registered BEFORE any peer number is read.
- Rule under test: the frozen CEF-RV trade list (`data/research/cefconnect/cef_rv_trades.csv`, 2016-26; 1999-2014 reported
  only, survivorship caveat CEF-SURV99 stands), net of 50bp. Comparator = EW return over the same hold of every Sharadar SFP
  CEF (delisted included) in the SAME category, category assigned by a frozen name regex written in `research/sim/cef_peer.py`
  (order: muni, preferred/convertible, sector/real-asset, taxable fixed income, international/global, equity default). The
  regex is fixed before the run; misclassification is noise, not tuning.
- Judge (one look, 2016-26, N 933): excess vs same-category peers >= +60bp/trade (the CEF-RV-FWD bar), week-clustered t >= 2,
  median > 0, both halves (2016-20 / 2021-26) > 0, ex-top-5 > 0, and the peer excess retains >= 50% of the EW-universe excess.
  PASS = CEF-RV is fund-specific discount reversion, not a category rotation. KILL = peer excess < +30bp or t < 1 (then CEF-RV
  = buying the sector that fell; the forward shadow's comparator must change to peers before any Roth deployment).
  Anything between = WEAK: keep the forward shadow, add the peer comparator to it, no deployment on history.
- Also reported (no gate): category mix of entries vs the universe, per-category excess, 1999-2014 peer excess.

## Result — CEF-PEER (judged 2026-10-10, one look; N 933): PASS
`research/sim/cef_peer_out.txt`. 2016-26, 3,611 trades: excess vs same-category EW peers **+114.2bp/trade, week-clustered t 5.78,
median +78.3, hit 0.60, halves +127.2 / +102.9, ex-top-5 +108.3**; retains 91% of the +125bp EW-universe excess (N 892). Positive in
every category (taxable FI +74, muni +94, intl +97, equity +132, pref/conv +148, sector +173). 1999-2014 (report only, survivorship
caveat stands): +159bp t 12.9, median +133, all six categories > +100. Entry mix is close to the universe mix (equity 25 vs 21%,
muni 20 vs 34%): CEF-RV is not a category rotation; the alpha is fund-specific discount reversion. Peer indices include the
traded fund itself (conservative). No change to the forward shadow's comparator is required (PASS branch); the CEF-RV-FWD gate
(60 forward trades) still decides deployment. Program N = 933.

## Study NOISE-GATE — a realized-intraday-vol regime gate for the intraday (noise) leg (pre-register 2026-10-11; N 933 -> 934)
Why: the PROD noise leg (QQQ+SMH 30-min band breakout, hold beyond band/VWAP, flat 15:57) is long volatility: levered Sharpe 1.7-2.9 in
2018/2020/2022-24 and ~0 or negative in 2017/2019/2025/2026 (noise_audit_out.txt, noise_recent_2026-10-08.md). Costs are not the
cause (0.4bp/fill live). A Level-5 regime gate (CLAUDE.md "Conditioning / regimes") is the one allowed fix; registered before any gated
number is read. One rule, one threshold, no tuning.
- Gate: trade session d only if QQQ's realized intraday vol, std of (close/open - 1) over sessions d-20..d-1, is ABOVE the trailing
  252-session median of that same series (ending d-1). Computed from the same minute cache the replay uses; no look-ahead.
- Leg under test: `research/sim/noise_recent.trades_for` with lag 30 (what live does), 0.5bp/fill (1bp RT), PROD weights/vol-target.
  Runner `research/sim/noise_gate.py`, output `data/research/program/noise_gate_out.txt`.
- Judge (one look, 2016-01..2026-05 cache, N 934): PASS if ALL: ON-day Sharpe >= 0.8 in both 2016-20 and 2021-26; OFF-day mean net
  per trade <= 0 over the whole sample; ON mean net >= +4bp/trade; ON Sharpe >= ungated Sharpe + 0.3; the ON-minus-OFF Sharpe gap
  beats >= 95% of 200 random 50% day-masks (placebo). KILL if ON mean <= OFF mean or either half's ON Sharpe < 0.3. Between = WEAK
  (no live change; report). Also reported, no gate: share of 2025-26 sessions gated OFF, ON/OFF by year, trades/day ON.
- If PASS: the live change is `daytrade_mode` stays `auto` plus a gate in the executor (user decision, config switch); if KILL/WEAK:
  recommend `daytrade_mode: off` with a vol-based re-arm note. No live change in this loop either way.

## Result — NOISE-GATE (judged 2026-10-11, one look; N 934): WEAK, no live change
`data/research/program/noise_gate_out.txt`. 2,548 sessions 2016-08..2026-09, gate ON 47%. ON: +5.03bp/trade, Sharpe +0.82 (halves
+0.99 / +0.66), ann +7.7%; OFF: +0.61bp, Sharpe -0.41; ungated +2.60bp, Sharpe +0.14. Placebo 96% (random-mask p95 gap +1.17 vs
+1.23: barely). Fails off_mean <= 0 and ON Sharpe 2021-26 >= 0.8. **Decisive detail: 2026 is ON 61% of sessions and the ON days are
the losers (ON Sharpe -1.78, OFF -0.11).** The gate rescues the calm years (2017, 2019: OFF Sharpe -1.6 / -2.5) but not 2026, where
vol is high and breakouts still fail: the 2026 failure is intraday non-persistence (V-shaped high-vol days), not low vol. A
trendiness gate would be variant 2 of a conditioner on a ~4%/yr leg: not run (anti-local-optimum rule). Recommendation to the user
unchanged: `daytrade_mode: off`; re-arm only on a positive 60-session replay, not on a vol gate. Program N = 934.

## Watch — NOISE-REARM (registered 2026-10-11; no N: the accepted decision rule applied forward, not a new hypothesis)
- Context: `daily.daytrade_mode: "off"` (user 2026-10-11). Accepted re-arm rule: "only on a positive 60-session replay". This
  freezes what "positive" means and reads it weekly so the leg is neither forgotten nor re-armed on a feeling.
- Rule: `swingtrader/daily/noise_rearm_watch.py` in research-shadows. PROD daybook replay (`replay_instrument`, the live
  code's own replay, now with `lag=30`: fills one 30-min bar after the decision print, as live does) on the last 60 complete
  SIP sessions, QQQ + SMH at .5/.5, 0.5bp per fill. POSITIVE iff n >= 30 trades AND annualised daily-P&L Sharpe >= 0.5 AND
  mean net per trade > 0 at 2bp per fill. Positive = re-arm CANDIDATE (user decision); nothing switches automatically.
  No tuning of 60 / 0.5 / 2bp / 30 ever; if the rule needs changing, it is a new registration.
- Equivalence check: lagged `replay_instrument` reproduces `research/sim/noise_recent.py::trades_for(lag=30)` on the
  research cache (QQQ, last 70 cached sessions: n 49 both, mean -6.16bp both, max |diff| 0.005bp rounding).
- First read (2026-10-11, sessions 2026-07-16..2026-10-09): n 85, mean -12.1bp, median -10.9, t -2.07, hit 36.5%,
  Sharpe -4.2, ann -28%; at 2bp/fill mean -15.1. QQQ -9.4, SMH -14.5. NEGATIVE: leg stays off.

## Study LUCK-B1 — random-rule discovery batch, grammar 1 (pre-register 2026-10-12; N 934 -> 935, DSR at 934 + 1000 trials)
Deep loop iter 2, Track B (`research/drafts/prompt_deep_loop_2026-10-12.md`). Not read: any outcome of any rule below.
- **Data.** Sharadar SEP (stocks.parquet, delisted included) + DAILY (daily.parquet: marketcap, pe, pb, ps, evebitda).
  Universe per day: domestic common stock (tickers category starts "Domestic Common Stock"), raw close >= $5, 20d median
  dollar volume >= $5M. Returns from adjusted prices (closeadj; adjusted open = open * closeadj/close). Delisting: last
  available price, then flat (survivorship-free panel; delisting return not modelled beyond the last print).
- **Grammar 1 (seeded, seed 20261012, `research/sim/luck_gen.py`).** Features at close t: ret 1/5/20/60/250d, IBS, gap
  (open/prev close - 1), range/close, vol20, volume ratio (vol/avg20 vol), log $ADV20, log price, dist to 252d high,
  dist to 252d low, log marketcap, pe, pb, ps, evebitda, day-of-week, month. A rule = feature f1 (cross-sectional decile
  1 or 10), optionally AND f2 (tercile 1 or 3), x horizon {overnight: close t -> open t+1 (daily-close proxy, optimistic);
  1d / 5d / 20d: open t+1 -> open t+1+h} x side {long, short}. Calendar features act as day filters on an f1 rule.
  Need >= 10 names that day. 1000 rules.
- **Score.** Per signal date: EW selected-name return minus EW universe return (same window), signed by side, minus 20bp
  round trip (10bp/side). For h > 1 only every h-th signal date (non-overlapping). **Discovery = 2006-01..2015-12 only.**
- **Pass (discovery).** Net mean > 0, t >= 3.0 on the per-date series, both halves (2006-10, 2011-15) net > 0, median > 0.
- **Null (mandatory).** 10 replicates of the same 1000 rules with the feature columns permuted across names within each
  date (seeds 1..10) + 1 time-shift placebo (all features lagged 252 trading days). **The batch counts only if the real pass
  count > max null pass count AND > 3 x mean null pass count.** Otherwise the batch is luck: log and stop.
- **Survivors.** At most 5 top-t passing rules that have a plausible after-the-fact mechanism and are NOT a member of a
  known/dead family (night-leg loser bounce, IBS reversal, momentum/value factor tilts already in NEXT) get a separate
  amendment, then ONE look on the confirmation set **1998-01..2005-12** at 10bp/side and a 3x cost shock (30bp/side), gate:
  net mean > 0, t >= 2, median > 0, ex-top-5-dates > 0, DSR > 0.95 at the full trial count. 2016-26 reported descriptive only.
- Kill: batch fails the null test -> LUCK, no survivors carried. Out: `data/research/program/luck_b1_out.txt`.

## Study WIKI-ATTN — Wikipedia pageview spikes -> overnight retail-attention pressure (pre-register 2026-10-12; N 935 -> 937)
Deep loop iter 5, Track A. New data source for the program (Wikimedia pageviews; no prior study in NEXT/prose). Not read:
any return conditioned on pageviews.
- **Mechanism.** Attention-limited retail buyers act on names they just noticed; their market orders arrive at the next
  open, so attention spikes earn overnight and give it back intraday (Berkman-Koch-Tuttle-Zhang 2012; Da-Engelberg-Gao 2011
  with Google SVI). Who pays: retail buyers paying the opening cross. Why it persists: retail order flow is structural.
- **Data.** enwiki daily user pageviews (Wikimedia REST per-article, 2015-07+), ticker -> article via Wikidata (P414/P249,
  enwiki sitelink; one article per ticker, ambiguous maps dropped). Prices: Sharadar SEP (delisted included), SPY from SFP.
  Pageview day = UTC day; **day d's count is used only from the close of d+1** (UTC d ends 20:00 ET, after the close).
- **Signal.** spike(i,d) = views(i,d) / median(views(i,d-30..d-1)) >= 3 AND median >= 100 views/day. Universe: domestic common,
  raw close >= $5, 20d median $vol >= $10M on d+1. Re-arm only after 10 sessions per name.
- **PRIMARY arm (night).** Buy the close of d+1, sell the open of d+2; return minus SPY close->open same night; cost 7.5bp/side.
- **SECONDARY arm (drift).** Buy open d+2, sell open d+7, minus SPY same window, same cost.
- **Judge.** 2016-01..2026-09, halves 2016-20 / 2021-26 (this rule has never been read on either; same post-2016 regime: stated).
- **Gate (PRIMARY).** Net mean >= +15bp/event (ceiling floor: ~250 nights x 15bp x 50% capital x 50% capture ~= +4.7pp is
  already below +8pp, so >= +15bp is necessary not sufficient), day-clustered t >= 2.5, median > 0, both halves > 0,
  ex-top-5 > 0, and a time-shift placebo (spike dates moved +60 sessions, same names) mean <= one third of the real mean.
  Also reported: overlap with night-leg picks (-8% losers), 2x cost. Kill: any fails. No threshold re-tuning (3x / 100 / 30d frozen).
- Runner `research/sim/wiki_attn.py` -> `data/research/program/wiki_attn_out.txt`; cache `data/research/wiki/`.

## Study LEG-HEALTH — own-P&L kill switch for the night and IBS legs (pre-register 2026-10-12; N 937 -> 938)
Deep loop iter 7, Track A (robustness). Not read: any rolling/autocorrelation statistic of leg P&L. Distinct from the closed
"market-trend gates on the MR book" class (REGIME-10M): the conditioner here is the leg's OWN trailing P&L, not the market.
- **Question.** Does switching a leg off after a bad trailing stretch cut drawdowns at <= 1pp/yr cost (prompt §1 robustness
  bar)? Mechanism if true: edge decay arrives in regimes (2017 night leg, 2026 noise leg); if false, leg P&L has no
  persistence and any controller only costs return.
- **Data.** Night leg exact 15:40 rule: `data/research/program/night_exact_pre2021.parquet` (2016-20) +
  `data/research/recent/night_replay.parquet` (2021-26), 7.5bp/side. IBS leg: the live rule replay used by
  `research/sim/recent_ibs.py` (adjusted ETF panel, 2016-26), 5bp/side. Daily leg P&L = mean net return of that day's picks
  (leg fully invested in its picks; 0 on no-pick days). No 2003-15 data (touched for both legs).
- **Controller (frozen).** Leg weight on day t = 0 if the sum of the leg's daily P&L over the previous 63 sessions (t-63..t-1)
  < 0, else 1. Shadow P&L keeps being computed while off (so it can re-arm).
- **Report.** Per leg: ann. return, vol, Sharpe, maxDD, worst 12m, for always-on vs controlled; by half (2016-20 / 2021-26);
  share of days off; lag-1..3 autocorrelation of 63-session P&L blocks (non-overlapping); placebo = 200 random on/off masks
  with the same off share (percentile of the controlled maxDD and return).
- **Gate (per leg).** PASS iff in BOTH halves controlled ann. return >= always-on - 1pp AND controlled maxDD <= 0.75 x
  always-on maxDD, AND the controlled maxDD beats the 90th percentile of the random-mask placebo. WEAK if one half. Kill otherwise.
  No re-tuning of 63 / 0 threshold.
- Runner `research/sim/leg_health.py` -> `data/research/program/leg_health_out.txt`.

### Result — LEG-HEALTH (judged 2026-10-12, one run; N 938): KILL both legs
`leg_health_out.txt`. Ann return / maxDD always-on -> controlled. Night 2016-20 +27.3/-64.6 -> +20.2/-63.1; 2021-26
+56.0/-58.1 -> +41.5/-43.0 (off 35%). IBS 2016-20 +11.2/-19.7 -> +9.3/-11.6; 2021-26 +10.7/-21.0 -> +2.9/-31.2 (off 40%).
Return cost 2-14pp/yr vs the 1pp allowance; controlled maxDD never beats the 90th pct of random masks (night 22nd, IBS 2nd).
Non-overlapping 63-session leg-P&L blocks have no persistence (lag-1 autocorr -0.21 night, +0.16 IBS). Deviations: IBS starts
2017-02 (warmup); first 63 sessions dropped. Class "own-P&L kill switches on the MR legs" CLOSED: leg P&L does not persist.
Program N = 938.

## Study OVN-MOM — overnight-return momentum held only overnight, reopened on measured auction cost (pre-register 2026-10-12; N 938 -> 939)
Deep loop iter 9, Track A. **Resurrection test ("what changed?").** RESULTS.md "Dead" row: overnight momentum (Lou-Polk-Skouras)
"replicates, monotone deciles, but top decile +8.7bp/night < 15bp auction round trip" (2021-26 cache). What changed: the 15bp
round trip was an assumption; live auction cost is now MEASURED at ~0bp (213/216 auction fills at the official SIP print,
2026-10-10 audit). That kill reason is gone; the effect itself was never judged pre-2016. Not read: any pre-2016 overnight
decile return, any 2016-20 one.
- **Mechanism.** Clientele persistence (LPS 2019): some names carry a persistent overnight buyer clientele (retail/opening-cross
  demand) and an intraday seller clientele; the overnight part persists for months. Who pays: opening-cross buyers.
- **Data.** Sharadar SEP raw open/close (delisted included), splits/dividends guarded (drop nights with an action, |ret|>50%).
  SPY overnight from SFP. Universe on day t: domestic common, raw close >= $5, 20d median $vol >= $20M.
- **Rule (frozen).** Score(i,t) = mean of open_s/close_{s-1} - 1 over the 252 sessions ending with day t's open (known before the
  15:50 MOC cutoff); need >= 200 valid nights. Each day hold the top decile EW: buy the close t, sell the open t+1.
- **Metric.** Per night: EW top-decile overnight return minus SPY close->open the same night; cost 2bp/side primary (above the
  measured ~0bp), shocks 5bp and 7.5bp/side.
- **Judge.** 1998-01..2015-12 (this rule never read there; LPS's own sample overlaps to 2013 = literature-touched, stated);
  halves 1998-2006 / 2007-2015. Descriptive: 2016-20 and 2021-26 (2021-26 touched by the RESULTS row).
- **Gate.** Net excess >= +6.5bp/night at 2bp/side (ceiling floor: 250 x 6.5bp x 100% x 50% = +8.1pp/yr at $10k), day-clustered
  t >= 3, both halves > 0, median night > 0, ex-top-5-nights > 0, still > 0 at 5bp/side, and 2016-26 descriptive > 0 at 2bp/side.
  Also report: bottom decile, decile monotonicity, names/night, median $ADV of picks, overlap with -8% night-leg picks, share of
  nights with an action dropped. Kill: any fails. No re-tuning of 252 / decile / $20M.
- Runner `research/sim/ovn_mom.py` -> `data/research/program/ovn_mom_out.txt`.

### Result — OVN-MOM (judged 2026-10-12, one run; N 939): REGISTERED PASS (all 7 gates), pending adversarial check; decaying
`ovn_mom_out.txt`. Judge 1998-12..2015-12, n 4278 nights, top decile EW minus SPY overnight: gross +19.4bp; net 2bp/side +15.4
(t 12.3, NW t 12.3, median +11.1, ex-top-5 +14.8, hit 63%); 5bp/side +9.4; 7.5bp/side +4.4. Halves at 2bp/side: 1998-2006 +26.2,
2007-15 +5.9 (~0 at 5bp/side). Deciles monotone (D1 -6.3 ... D10 +19.4). Descriptive 2016-20 +2.0 (t 1.45), 2021-26 +3.8
(t 1.70), 2016-26 +3.0 (t 2.18) at 2bp/side, negative at 5bp/side. ~82 names/night, median pick $ADV ~$59M, 2.4% overlap with
-8% losers. Deviations: split-adjusted open/close (split-invariant), $vol median through t-1, SPY dividend added back, delisting
nights NaN, ex-action nights NaN. **Open risk: Sharadar opens before 2016 may be first prints, not the official open cross
(bid-ask bounce; pre-2001 fractional ticks) - the strongest half is 1998-2006.** Current-regime ceiling at 2016-26: ~+3bp net
x 250 x 100% x 50% ~= +3.75pp at $10k (full capture at ~0bp measured cost ~ +7bp gross -> ~+17pp excess): the decision hinges
on the real auction cost on these names and on 2016-26 official-cross prints.

### Result — LUCK-B1 (2026-10-12, discovery 2006-15 only; N 935, 1000 trials): LUCK — 0 passes, null 0/0, placebo 0
`luck_b1_out.txt`, `luck_b1_rules.parquet`. Real passes 0/1000 (988 scorable); permutation null 0 in all 10 replicates; 252d
time-shift placebo 0. Best t 2.27; only 71 rules net-positive after 20bp RT; median rule t -5.9 (the cost floor dominates the
1d/overnight rules: a one-feature decile rarely earns 20bp per round trip). Confirmation set 1998-2005 untouched. Lesson for
grammar 2: at retail cost, random single-feature deciles on daily US stocks are cost-dominated; a random grammar needs either
longer horizons (cost/day small) or event-type features, not more price features.

## Study LUCK-B2 — random-rule discovery batch, grammar 2: events x price state, 20/60-session horizons (pre-register 2026-10-12; N 939 -> 940, DSR at 940 + 600 trials)
Deep loop iter 10, Track B. Grammar changed per the B1 lesson (cost-dominated short horizons; price-only features). Not read:
any return conditioned on a Sharadar EVENTS code or an ACTIONS type.
- **Data.** Sharadar EVENTS (8-K item codes per ticker-date, 1993+) and ACTIONS (dividend, initiated, split, exchangefrom/to,
  sicchange, namechange, tickerchange, listed, acquisitionby, spinoff ...), SEP prices (delisted incl., last print then flat),
  DAILY marketcap. Universe: domestic common, raw close >= $5, 20d median $vol >= $2M on the entry day.
- **Timing guard.** EVENTS date may be the event date, not the filing date (8-K due within 4 business days): entry at the
  OPEN of the 5th session after the event date. Actions: entry at the open of the 2nd session after the action date.
- **Grammar 2 (seed 20261013, `research/sim/luck_gen2.py`).** Rule = event type e (one 8-K code, one action type, or a derived
  dividend change: increase >= 10% / cut >= 10% vs prior regular dividend) x optional price-state filter (tercile 1 or 3 of
  ret20, ret60, vol20, dist-to-252d-high, log marketcap, measured the session before entry) x horizon {20, 60 sessions} x side
  {long, short}. 600 rules. Re-arm: one event per ticker per 20 sessions per rule.
- **Score.** Per event: name open-to-open return minus EW universe same window, signed, minus 20bp round trip. Cluster by
  entry calendar month. Need n >= 100 events.
- **Discovery = 2005-01..2015-12 only** (8-K items were renumbered in Aug 2004; earlier codes not comparable).
- **Pass.** Net mean > 0, month-clustered t >= 3, halves 2005-10 / 2011-15 > 0, median > 0, ex-top-5-events > 0.
- **Null.** 10 replicates: event types permuted across events within each calendar year (keeps timing and counts), seeds 1..10;
  plus a date placebo (each event moved to a random date of the same ticker 250-750 sessions earlier). Batch counts only if real
  passes > max null AND > 3 x mean null.
- **Survivors.** At most 5 with a plausible mechanism and not a known family (PEAD / earnings 8-K, insider, S&P add/delete,
  dividend-initiation drift, spin-off, buyback - all in NEXT) get an amendment, then ONE look on **2016-01..2020-12** (never read
  for these rules; post-2016 regime, stated) at 20bp and 60bp round trip; gate as LUCK-B1 plus DSR > 0.95. 2021-26 descriptive.
- Out: `data/research/program/luck_b2_out.txt`, rules `luck_b2_rules.parquet`.

### Adversarial check — OVN-MOM (2026-10-12; `ovn_mom_adv.py`, `ovn_mom_adv_out.txt`): PASS stands historically; current regime SMALL
- Pre-decimal inflates the headline (1998-12..2001-04 +47.6bp); post-decimal 2001-05..2015 still +10.3bp t 12.2.
- Not bid-ask bounce: a stale (skip-a-night) score keeps +19.0bp gross; edge is flat across $ADV terciles, mildly stronger <$10.
  Close-to-close excess ~0 (next-day intraday -19.5bp): pure overnight clientele (LPS), nothing for a close-to-close holder.
- Official crosses 2021-26 (141k pick-nights matched): close == official close; open median 0bp but 15.5% differ > 20bp; on matched
  nights official-print excess +7.2bp gross / +3.2 net at 2bp/side (t 2.9) vs +9.0 / +5.0 on Sharadar prints.
- By year (net 2bp/side): 1999 +64, 2003 +18, 2010 +9.5, 2015 -0.3, 2016-19 ~-0.5, 2020 +12, 2021 +7.3, 2022 -0.8, 2023 +0.5, 2024
  +5.8, 2025 +3.5, 2026 +7.9: decayed, alive at a few bp. Median pick closing print $5.5M (a $1k order is trivial).
- **Verdict: PASS (registered, historical) / SMALL now.** Current ceiling at $10k: +3.2bp net x 250 x 100% x 50% ~= +4pp at
  2bp/side; ~+9pp only if the measured ~0bp auction cost holds on these names (7.2bp gross, 50% capture). Forward shadow decides:
  real cross prints, real decile excess. Not deployable; it also competes with the night leg for overnight capital.

## Watch — OVN-MOM-FWD forward shadow gate (registered 2026-10-12, before any forward read; no new N)
- Log-only. Each session: rank the live universe (raw close >= $5, 20d median $vol >= $20M, domestic common) by the mean of the
  last 252 overnight returns ending with today's open; log the top decile (registered) and the top 10 by score (executable at
  $2-25k, whole shares) at the 16:00 official close; next morning score both against the official open cross, minus SPY
  close->open.
- **Gate (decile, 120 forward nights):** mean gross excess >= +5bp/night with t >= 2 and median > 0. Reported, not gated: top-10
  arm, cross-print coverage, share of picks without a cross. PASS -> user decision on an overnight sleeve for idle capital
  (it competes with the night leg's overnight cash). FAIL -> class closed (overnight clientele at retail).

### Result — LUCK-B2 (2026-10-12, discovery 2005-15 only; N 940, 600 trials): LUCK — the date placebo beats the real batch
`luck_b2_out.txt`, `luck_b2_rules.parquet`. Real passes 5/600 but only 2 distinct rules (generator repeats); permutation nulls
0 in all 10; **date placebo (same tickers, event moved 250-750 sessions earlier) 34 passes > real 5.** The registered null
includes the placebo, so the batch FAILS: what passes is the TYPE of firm (frequent small equity issuers / 8-K 3.02 filers, short
60d +173bp net), not the event's timing - the known issuance/dilution drag (cf. F13C implied-shares diagnostic), short-side only.
No confirmation look; 2016-20 stays unseen. Deviations: 8-K code = item x10 assumed (codes 34/35/37 unmapped); 'initiated' in
ACTIONS is a coverage marker, not a dividend initiation. Lesson for grammar 3: dedupe rules; the null must always include a
same-ticker date placebo (the permutation null alone would have passed this).

## Study LUCK-B3 — random-rule discovery batch, grammar 3: crypto alts, delisted-complete, long-only (pre-register 2026-10-12; N 940 -> 941, DSR at 941 + 800 trials)
Deep loop iter 13, Track B (grammar change = new asset + new panel). Not read: any return statistic on the Binance alt panel.
Prior crypto work touched only majors (BTC/ETH IBS, trend, BTC-FIX, LIQ-CASC); alts never studied here.
- **Data.** `data/research/crypto_spot/panel.parquet` (Binance spot USDT pairs 2017-08..2026-09, 249 delisted kept; UTC days).
  Universe on day d: not stablecoin/fiat/leveraged-token, >= 60 days since first bar, 30d median quote volume >= $1M.
  A symbol's last bar is its exit (delisting): return to its last close, then flat (optimistic for delistings; stated).
- **Grammar 3 (seed 20261014, `research/sim/luck_gen3.py`, rules DEDUPED).** Features at the close of UTC day d: ret 1/3/7/14/30/90d,
  vol30, range/close, volume ratio (qv/avg30 qv), log qv30, trades ratio, age (days listed), ret vs BTC 7d/30d, dist to 90d high,
  dist to 90d low, BTC's own ret7/vol30 (regime, as a day filter tercile), day-of-week. Rule = f1 cross-sectional quintile 1 or 5,
  optionally AND f2 tercile 1 or 3 (or a BTC-regime / weekday filter) x horizon {7, 30 days} x LONG only (no alt shorting for US
  retail). Need >= 5 names that day. 800 distinct rules.
- **Score.** Enter at the close of d+1 (one full day of lag), exit at the close of d+1+h; EW selected minus EW universe, minus
  80bp round trip (Coinbase US maker ~40bp/side at small volume; shock 120bp). Non-overlapping (every h-th signal day).
- **Discovery = 2019-01..2022-12 only** (halves 2019-20 / 2021-22). Confirmation = **2023-01..2026-09**, unseen.
- **Pass.** Net mean > 0, t >= 3, both halves > 0, median > 0, ex-top-5 dates > 0, n >= 30 dates.
- **Null.** 10 replicates of within-date feature permutation (seeds 1..10) AND a date placebo (all features lagged 365 days per
  symbol). Batch counts only if real passes > max over ALL 11 null runs AND > 3 x their mean.
- **Survivors.** <= 5 with a plausible mechanism, not a known dead family (crypto IBS/short-term reversal, BTC trend), get an
  amendment, then ONE look on 2023-01..2026-09 at 80bp and 120bp RT, restricted also to `on_coinbase_us` names (descriptive:
  current listing, not PIT). Gate as discovery with t >= 2 and DSR > 0.95.
- Out: `data/research/program/luck_b3_out.txt`, `luck_b3_rules.parquet`.

### Result — LUCK-B3 (2026-10-12, discovery 2019-22 only; N 941, 800 trials): LUCK — 0 passes, nulls 0, placebo 0
`luck_b3_out.txt`. 0/800 deduped long-only alt rules pass at 80bp RT; all 10 permutation nulls and the 365d date placebo 0. Best t
1.69 (n 38, median negative, ex-top-5 negative). Universe thin early (mean eligible 22 in 2019, 51 in 2020, ~220 in 2021-22).
Deviations: token-swap price breaks split into new symbols (DREP, LUNA relaunch, COCOS, SUN, VEN); greedy non-overlap; cost on the
basket only. Confirmation 2023-26 unseen. Reading: at US-retail spot cost (80bp RT), random long-only alt rules at 7-30d have no
discoverable edge; with B1-B3 all luck, random search on daily price/event data is cost- and null-bound across stocks, events, crypto.

### Result — WIKI-ATTN (judged 2026-10-12, one run; N 936-937): KILL
`wiki_attn_out.txt`. 1,899 in-universe tickers mapped (Wikidata 1:1), pageviews for 1,898. PRIMARY night arm n 5,854 spike events:
gross -1.0bp (median -1.2, hit 49%, t -0.28); net -16.0bp (t -4.42, ex-top-5 -18.5); halves -12.5 / -18.9; placebo net -9.7.
SECONDARY 5d drift gross -2.2, net -17.2 (t -1.80). Overlap with -8% losers 2.8% (net +17.8 but median -32.6, t 0.28). No raw
attention effect overnight at all on Wikipedia spikes 2016-26. Survivorship: current tickers without Wikidata dates accepted.
Wikipedia-attention family closed (night and 5d). Program N = 941.

## Study CRSP-EARLY — night leg + OVN-MOM on untouched 1992-97 CRSP (pre-register 2026-10-13; N 941 -> 943)
Registered before any CRSP price was loaded. New data source: WRDS CRSP daily stock file (user's Wharton access, 2026-10-12),
delisted-complete (dlret), permno ids, shrcd/exchcd security type. **1992-97 has never been read by any rule in this program**
(Sharadar starts 1997-12-31; all Alpaca work is 2016+). Purpose = robustness: does the live night leg's mechanism and the
OVN-MOM clientele effect exist in a regime they were not chosen on? Pre-decimal (1/8-1/16 ticks), so this confirms SIGN and
mechanism; the net economics of today's market are not judged here.
- **Window.** CRSP OPENPRC starts mid-1992. Start = first month with OPENPRC on >= 90% of eligible common-stock days on
  NYSE/AMEX/Nasdaq (coverage check reads no returns), through 1997-12-31. Days with BIDLO/ASKHI < 0 or missing (bid/ask
  stand-ins, no trades) are ineligible for IBS. Universe: shrcd 10/11, exchcd 1/2/3. Splits: cfacpr. Delisting: dlret
  (missing -> -30% for performance codes 500-599, else 0, Shumway), applied to a pick with no next open.
- **N1 night leg (N 942).** The Study NX primary rule verbatim (daily-bar form: drop <= -8%, IBS < 0.10, $5-2000,
  vol20 >= 0.60, 20d mean $vol >= $10M nominal, crowd 30, corr-0.7 dedupe, night_tilt v1, cap 10%, gap_scale), buy close,
  sell next open. Gate: per-night equity-weighted GROSS mean > 0 with night-clustered t >= 2; median trade > 0; mean > 0 ex
  best 5 nights; both halves (start..1994-12 / 1995-01..1997-12) > 0. Reported: tier, tier_hi, beta x same-night small-cap
  EW close->open residual, $10M-bar count by year. FAIL: gross mean <= 0 or t < 1; else WEAK.
- **N2 OVN-MOM (N 943).** The Study OVN-MOM rule verbatim (252-night mean overnight return, >= 200 valid, |night| > 50%
  dropped, close >= $5, 20d median $vol >= $20M, no funds; top decile EW; excess vs same-night CRSP VW-index proxy =
  EW of the top-500 $vol names close->open, since SPY did not exist before 1993-01). Judge from the first night with 252
  prior nights. Gate: gross excess mean > 0, night-clustered t >= 2, median night > 0, both halves > 0. Reported: net at
  2bp/side vs the registered +6.5bp economic bar (expected to fail it in a pre-decimal market), ex-top-5, top-10 arm.
- One run each, no re-tuning, no second look. A FAIL on N1 is recorded as evidence against the night leg's durability
  (the user's S2 size-up is not changed by this study; any sizing reaction is a user decision).

Program N = 943.

### Result — CRSP-EARLY (judged 2026-10-13, one run; N 942-943) + adversarial check
Window 1992-11..1997-12 (coverage rule: first month OPENPRC >= 90%). `crsp_early.py` -> `crsp_early_out.txt`; adversary
`crsp_early_adv.py` -> `crsp_early_adv_out.txt` (closing bid/ask from CRSP dsf).
- **N1 night leg: registered PASS (gross +2.87bp/night, t 2.47, median trade +58.6bp, halves +1.58/+3.80) -> NOT CONFIRMED.**
  The pick's close sits 27bp below the closing midquote (median 24): from the mid the gross is +1.55bp t 1.33 (fails t >= 2), from
  the ask -1.7bp; top-10 nights = 68% of P&L; 1996-97 negative on trade and mid bases; beta-adjusted residual ~0 (+1.08 t 0.99).
  Read: in 1992-97 the night leg is bid-ask bounce + small-cap beta. Adds to the regime-concentration evidence (exact 2016-20, NX
  small). No sizing reaction from this study (S2 is a user decision on live cost/forward fills).
- **N2 OVN-MOM: registered PASS -> MECHANISM CONFIRMED, economics not judged.** Excess +16.55bp t 8.4, median +16.8, deciles
  monotone (-7.5..+16.5), halves +8.3/+19.7. Survives the closing midquote (+16.2 t 8.1; mid-ranked +16.4, 86% overlap), NYSE
  alone (+10.6 t 4.6; Nasdaq +18.0), no high-spread concentration, stale scores (lag 126/252/504 nights +14.5/+13.0/+10.5),
  random-decile placebo +1.4. Next-day open->close -17.1bp (t -4.3), close->close ~0: night-only clientele, as in LPS.
  **The registered "net +12.6bp at 2bp/side" is INVALID** for 1992-97: half-spreads were ~37bp (buy-at-ask vs mid benchmark
  -22bp). So 1992-97 confirms the effect exists in a third, untouched era (now 1993-2026 all positive gross), not that it paid.
  Today's cost question stays with the OVN-MOM-FWD forward shadow (live from 2026-10-13).
Program N = 943.

## Study LUCK-B4 — random-rule discovery batch, grammar 4: options-implied + short-interest features (pre-register 2026-10-13; N 943 -> 944, DSR at 944 + 1000 trials)
Deep loop iter 17, Track B (grammar change = new feature families + new data source, WRDS). Not read: any return statistic
conditioned on an OptionMetrics or Compustat short-interest feature by this program (the only prior options-state work is
index-level: OPEX pin, VTS, gamma proxy; per-stock option-implied features never studied here).
- **Data.** CRSP daily (prices, delisting dlret, shrcd 10/11, exchcd 1/2/3) linked to OptionMetrics via
  wrdsapps_link_crsp_optionm (score >= 1 best links only), and Compustat comp.sec_shortint (via CCM link, as of the
  settlement date, usable from the PUBLICATION lag: settlement + 8 business days). Universe on d: close >= $5, 20d median
  $vol >= $10M, has an IV surface that day.
- **Grammar 4 (seed 20261013, `research/sim/luck_gen4.py`, deduped).** Features known at the close of d: from optionm.vsurfd
  (30-day): ATM IV (call delta 50), put-call IV spread (put -50 minus call 50), skew (put -25 minus ATM), IV minus RV20, IV
  change 5d/21d, IV term slope (91d minus 30d ATM); from optionm.opvold: log option volume / 20d avg, put/call volume ratio,
  option $-volume / stock $-volume; from sec_shortint: SI/shares, SI change vs prior report, days-to-cover; plus controls
  ret 5/21d, size. Rule = f1 cross-sectional decile 1 or 10, optionally AND f2 tercile 1 or 3 x horizon {overnight (close d+1
  -> open d+2), 5d, 21d} x LONG only (excess vs EW universe). 1000 distinct rules.
- **Score.** Enter at the close of d+1 (one day lag), cost 5bp/side (shock 15bp), non-overlapping for 5d/21d.
- **Discovery = 2001-01..2010-12 only** (halves 2001-05 / 2006-10). Confirmation = **2011-01..2019-12**, unseen for these
  features. 2020+ is not used.
- **Pass (discovery).** Net mean > 0, t >= 3, both halves > 0, median > 0, ex-top-5 dates > 0, n >= 30 dates, AND an annualized
  net excess at 100% deployment >= 16%/yr (the +8pp-at-50%-capture ceiling).
- **Null.** 10 within-date feature permutations + a date placebo (features lagged 252 trading days per stock). Batch counts only
  if real passes > max over all 11 null runs AND > 3 x their mean.
- **Survivors.** <= 5 with a plausible mechanism, not a known dead family (short-term reversal, IBS, size), get an amendment, then
  ONE look on 2011-19 at 5bp and 15bp/side; gate as discovery with t >= 2 and DSR > 0.95.
- Out: `data/research/program/luck_b4_out.txt`, `luck_b4_rules.parquet`.
Program N = 944.

### Result — LUCK-B4 (2026-10-13, discovery 2001-10 only; N 944, 1000 trials): LUCK — 0 passes, nulls 0 (10/10), placebo 0
`luck_gen4.py` (pull `luck_b4_pull.py`, cache data/research/wrds_b4/), out `luck_b4_out.txt`. Disclosed: one NA-dtype crash fixed
before any scoring (dsf/dlret cast to float64); SI-feature rules split halves at their own median date (sec_shortint starts
2006-07, so the registered 2001-05 half is empty for them); 10bp RT; link score 1. Confirmation 2011-19 NOT pulled or read.
Best rules (all fail): top-ATM-IV decile overnight +3.9..5.3bp/night t 2.4-3.1 (the known high-vol overnight premium, same family
as the night leg / OVN-MOM, ~+10-13%/yr at 100% gross, below the 16% floor); 5d short-term reversal x short interest +52..68bp
on 224 dates (known reversal family, t < 3). Per-stock option-implied state + short interest add nothing beyond known families.
Program N = 944.

## Study LATE-FLOW — late-day signed trade flow -> overnight reversal, stock cross-section (pre-register 2026-10-13; N 944 -> 945)
Deep loop iter 18, Track A. New data source (WRDS TAQ millisecond trades, taqm_YYYY.ctm_YYYYMMDD + complete_nbbo), new
mechanism vs the book (ORDER FLOW, not price: the night leg/IBS select on the price path), counterparty = late-day liquidity
demanders (institutional/benchmark-close sellers) paying an overnight premium to the closing liquidity supplier. Prior tests
here are different objects: closing-cross IMBALANCE (Lab-BB, dead), opening quote imbalance on ETFs (AT), 15:40 quote imbalance
as a filter on night picks (QI-HIST, dead). Not read: any return conditioned on intraday signed trade flow.
- **Ceiling.** Every night x top decile (~50-100 names, top 10 executable at $2-25k) x 100% of the overnight capital x 50% capture:
  needs >= +6.5bp/night net excess -> 250 x 6.5 x 50% = +8.1pp/yr at $10k; $100k fine (closing auction of top-1000 names).
- **Rule (frozen).** Universe on d: CRSP common (shrcd 10/11, exchcd 1/2/3), prior close >= $5, top 1000 by 20d median $vol (from
  days before d). FLOW(i,d) = sum over regular-hours trades 15:00:00-15:44:59 of sign x size / 20d median daily share volume, sign
  by Lee-Ready (trade vs prevailing NBBO mid at 1ms-before; at the mid -> tick test), excluding odd-lot-flagged/out-of-sequence/
  corrected trades and auction prints (cond codes O,Q,6,M). Pick = bottom decile of FLOW (heaviest net selling). Buy the 16:00
  close of d (CRSP prc), sell the next open (CRSP openprc); excess = EW pick close->open minus EW universe close->open.
- **Window.** Judge 2010-01-04..2015-12-31 (post-Reg NMS, millisecond TAQ, decimal; this rule never read anywhere). Halves
  2010-12 / 2013-15. Overnight returns: CRSP, ex-dividend nights dropped, delisting as in CRSP-EARLY.
- **Gate (all).** Net excess >= +6.5bp/night at 2bp/side; night-clustered t >= 2; median night > 0; ex-top-5 nights > 0; both
  halves > 0; AND the WITHIN-day-return-tercile spread (bottom-FLOW decile vs universe, computed inside terciles of the day's
  close-to-close return and averaged) > 0 with t >= 2 — so the effect is order flow, not the price reversal the night leg already
  owns. Reported: top-FLOW decile (buy pressure; expect negative), deciles monotone?, 5bp/side shock, overlap with the night leg's
  picks, top-10-by-FLOW arm. Kill: any gate fails. No re-tuning of the 15:00-15:45 window, decile or 1000-name universe.
Program N = 945.

## Watch — ARETE-DIP-FWD forward shadow (registered 2026-10-13, before any forward read; N 945 -> 946)
Origin: `../alpha-chasers` (Andrew's Discord alert-service study, arete1061, 1,912 messages 2023-26). Not discovered in this
repo; imported with its full record so the count stays honest. alpha-chasers N for this family ≈ 6 cells × 4 exits × 3 eras +
6 state gates + 39k-trade options sweep (PREREG2-4 there).
- **What was found there.** His alerts buy liquid, high-momentum, high-vol names AFTER a 1-2 week run; from the alert on they go
  nowhere (paired edge vs ±5/±10-day shifted copies −1.9 % [−2.9, −0.9], n 331). The same profile bought on a dip (IBS < 0.2,
  1d <= −2 %) beat the EW liquid universe by +0.60 % (d+5, 2021-24, CI ∋ 0) and +1.47 % (2025-26, CI > 0, ex-top-5 +0.89 %),
  but LOST −0.46 % on untouched 2016-20 (this repo's bars_pre2021). Frozen bar there: **KILL**. No market-state gate (SPY trend,
  calm, dip regime, momentum in favour, dispersion, SPY 60d) made it positive in all three eras. Options versions lose.
- **So this watch tests one narrow claim:** the post-2020 regime that paid for it persists. It is NOT a validated edge.
- **Rule (frozen).** Session d, eligible: close >= $5, 20d mean $vol >= $20M. Profile: 60d >= +20 %, close > 50d avg, 20d return >
  SPY's, 20d vol in the top third of eligible names. Dip: IBS < 0.2 and 1d <= −2 %. Log every hit at d's close; score close d ->
  close d+5 (primary) and d+3 minus the EW return of all names eligible on d, minus 20bp RT. Bar close stands in for the cross.
- **Gate (60 signal days scored at d+5):** per-signal-day mean > 0, t >= 2, median day > 0 -> PASS -> user decision on a small
  sleeve. Mean <= 0 -> FAIL, family closed for good. Otherwise HOLD. No parameter changes; no sizing on the backtest.
- Code: `swingtrader/daily/arete_dip_shadow.py` (logs only), `make arete-dip`, research-shadows service; REGISTRY entry in
  `testing.py`. Program N = 946.

## Study LUCK-B5 — random-rule discovery batch, grammar 5: analyst-forecast (IBES) features (pre-register 2026-10-13; N 946 -> 947, DSR at 947 + 1000 trials)
Deep loop iter 19, Track B (grammar change = new data family: IBES summary statistics, never used in this program). Not read: any
return conditioned on an IBES consensus/dispersion/revision feature here. Same scoring frame as LUCK-B4 so the nulls are comparable.
- **Data.** CRSP daily (cached `data/research/wrds_b4/` dsf 2000-06..2011-02 + delist/names) linked to IBES via
  wrdsapps.ibcrsphist (score <= 2 only). IBES unadjusted summary `ibes.statsumu_epsus`, FY1 (fpi '1') and LTG (fpi '0'), usable from
  the trading day AFTER statpers. Universe on d: CRSP common, close >= $5, 20d median $vol >= $10M, has a FY1 consensus within 45d.
- **Grammar 5 (seed 20261014, `research/sim/luck_gen5.py`, deduped).** Features known at the close of d: consensus earnings yield
  (FY1 mean / price), dispersion (stdev / |price|), dispersion / |mean|, 1m and 3m revision of the FY1 mean / price, net revision
  breadth (numup - numdown) / numest, numest, numest change 3m, LTG mean, LTG minus its 3m-ago value, mean-vs-median gap / price;
  plus controls ret 5/21d, size. Rule = f1 cross-sectional decile 1 or 10, optionally AND f2 tercile 1 or 3 x horizon {overnight
  (close d+1 -> open d+2), 5d, 21d} x LONG only (excess vs EW universe). 1000 distinct rules.
- **Score.** Enter at the close of d+1, cost 5bp/side (shock 15bp), non-overlapping for 5d/21d.
- **Discovery = 2001-01..2010-12 only** (halves 2001-05 / 2006-10). Confirmation = **2011-01..2019-12**, unseen for these features
  (not pulled in this run). 2020+ not used.
- **Pass (discovery).** Net mean > 0, t >= 3, both halves > 0, median > 0, ex-top-5 dates > 0, n >= 30 dates, AND annualized net
  excess at 100% deployment >= 16%/yr (the +8pp-at-50%-capture ceiling).
- **Null.** 10 within-date feature permutations + a date placebo (features lagged 252 trading days per stock). Batch counts only if
  real passes > max over all 11 null runs AND > 3 x their mean.
- **Survivors.** <= 5 with a plausible mechanism, not a known dead family (PEAD/revision drift is in the gap per CLAUDE.md, short-term
  reversal, IBS, size), get an amendment, then ONE look on 2011-19 at 5bp and 15bp/side; gate as discovery with t >= 2 and DSR > 0.95.
- Out: `data/research/program/luck_b5_out.txt`, `luck_b5_rules.parquet`.
Program N = 947.

### Result — LUCK-B5 (2026-10-13, discovery 2001-10 only; N 947, 1000 trials): LUCK — 0 passes, nulls 0 (10/10), placebo 0
`luck_gen5.py` (pull `luck_b5_pull.py`, cache data/research/wrds_b5/), out `luck_b5_out.txt`; scoring imported unchanged from
luck_gen4. Disclosed choices: IBES measure='EPS'; ibcrsphist lowest score kept; revisions vs the prior snapshot of the same fiscal
period (1m: 20-45d gap, 3m: 70-120d); float64 casts; late-2010 exits use Jan-2011 closes. Confirmation 2011-19 NOT pulled or read.
Best rules (all fail: t <= 2.00 vs 3, ann <= 11%/yr vs 16%): FY1 1m revision bottom decile x low dispersion 21d +75bp t 2.00 (halves
+161/-19); 5d loser x high earnings yield 21d +92bp t 2.00 (both halves +, known reversal family); high EY x low coverage +71bp t 1.97.
Analyst-forecast state adds nothing beyond known families (revision drift, reversal, value).
Program N = 947.

## Study BOND-LEAD — corporate-bond price moves lead the issuer's stock, next day (pre-register 2026-10-13; N 947 -> 948)
Deep loop iter 21, Track A. New data family (TRACE enhanced, `wrdsapps_bondret.trace_enhanced_clean`, never used here), new
mechanism (cross-market information flow: informed institutional bond traders vs a stock that under-reacts), counterparty = the
equity side that is slow to price credit news. Literature is mixed (Downing-Underwood-Xing 2009: bonds lag; Hotchkiss-Ronen 2002:
no lead); this is a cheap kill test, not a prior. Not read: any stock return conditioned on a bond-trade feature.
- **Ceiling.** Daily x top decile (~50-150 issuers; 10 names executable at $2-25k) x 100% of the overnight/day capital x 50% capture:
  needs >= +6.5bp/day net excess -> 250 x 6.5 x 50% = +8.1pp/yr at $10k; $100k fine (large-cap bond issuers).
- **Rule (frozen).** Bond day-price for (cusip_id, d) = the last trade with entrd_vol_qt >= 100,000 executed by 15:59:59 ET on d
  (trd_exctn_tm), excluding when-issued, commissioned, special-condition (spcl_trd_fl) and as-of trades; the enhanced-clean table's
  cancel/correction handling is taken as given. Bond return = day-price(d) / day-price(prev day the bond had one) - 1, only if that
  prev day is within 5 trading days. BRET(issuer, d) = median bond return over the issuer's bonds (issuer = first 6 CUSIP chars),
  needs >= 1 bond. Map issuer -> CRSP permno by ncusip[:6] valid on d (CRSP common shrcd 10/11, exchcd 1/2/3). Universe on d: has
  BRET, prior close >= $5, 20d median $vol >= $10M. Pick = top decile of BRET (bonds up most). Hold the stock from the 16:00 close of
  d to the 16:00 close of d+1 (CRSP ret d+1); excess = EW pick minus EW universe. Delisting returns as in CRSP-EARLY.
- **Window.** Judge 2006-01-03..2015-12-31 (full TRACE dissemination from 2005-02; enhanced TRACE). Halves 2006-10 / 2011-15.
  2016+ not used (kept for a confirmation look if this ever passes).
- **Gate (all).** Net excess >= +6.5bp/day at 2bp/side; day-clustered t >= 2; median day > 0; ex-top-5 days > 0; both halves > 0;
  AND the WITHIN-stock-return-tercile spread (top-BRET decile vs universe inside terciles of the stock's own close-to-close return on
  d, averaged) > 0 with t >= 2, so the effect is bond information, not the stock's own momentum/reversal. Reported: bottom-BRET decile
  (expect negative), decile monotonicity, overnight (close d -> open d+1) vs day split, 5bp/side shock, IG vs HY issuers (by the
  bond's FISD rating if cheaply available; else skip). Kill: any gate fails. No re-tuning of size cut, time cut, decile or horizon.
Program N = 948.

### Result — BOND-LEAD (2026-10-13, 2006-01..2015-12, one look; N 948): KILL, 0/6 gates
`bond_lead.py` (pull `bond_lead_pull.py`, cache data/research/bond_lead/), out `bond_lead_out.txt`. 2515 days, ~1161 issuers/day with
BRET, universe 327/day, 33 picks/day. Net excess -4.51bp/day at 2bp/side (gross -0.51), t -3.95, median -5.97, ex-top-5 -5.42; halves
-4.53 / -4.50; within-stock-return-tercile spread +0.03bp t 0.03. Bottom decile -3.0bp (t -2.3); deciles not monotone (D8/D9 +1.9/+2.8,
D10 -0.5); overnight +1.0 / day -1.5; per-year negative except 2009. Disclosed: cmsn_trd is NULL from 2012-02 on, so the filter is
`cmsn_trd IS DISTINCT FROM 'Y'` (first pull wrongly dropped NULLs; re-pulled before scoring); issuer->permno link resolves 32.6% of
issuer-days (ambiguous cusip6 links dropped); IG/HY split skipped. Read: stocks already price same-day bond moves; no lead to harvest.
Program N = 948.

## Study LUCK-B6 — random-rule discovery batch, grammar 6: ETF cross-section with fund-level features (pre-register 2026-10-13; N 948 -> 949, DSR at 949 + 800 trials)
Deep loop iter 22, Track B. Grammar change per checkpoint 4: leaves the single-stock cross-section (B1/B2/B4/B5 were stocks, B3
crypto alts). Asset = all US exchange-traded funds/notes in CRSP (shrcd 73, delisted included), Roth-eligible. New feature family:
fund flows (shares-outstanding change), premium/discount to NAV (CRSP MF daily NAV), fund age/size. Touched for ETFs before: IBS on
equity ETFs (live rule; 2003-15 SHAR-IBS, 2016-20 OOS), SPY creation flow (ETC 2016+), bond-SPDR premium (BSPD 2007+), broad SPDR
discounts (EF). Not read: any cross-sectional ETF rule on flow/premium/age/size features.
- **Data.** CRSP daily dsf/dsenames/dsedelist for shrcd 73 (2003-07..2013-01 for discovery features and exits). CRSP MF daily_nav
  linked to permno (via fund_hdr ticker/cusip -> dsenames ncusip; disclose the link rate; if < 50% of ETF-days link, the premium
  features are dropped and disclosed, the rest of the grammar runs). Universe on d: close >= $5, 20d median $vol >= $1M, listed >= 60d.
- **Grammar 6 (seed 20261015, `research/sim/luck_gen6.py`, deduped).** Features known at the close of d: shares-outstanding change
  5d / 21d / 63d (flow), premium to NAV (close/NAV - 1) and its 21d z-score, dollar volume / 63d avg, ln(market cap), fund age,
  ret 1/5/21/63/252d, 21d vol, 252d max drawdown, distance to 52w high. Rule = f1 cross-sectional decile 1 or 10, optionally AND f2
  tercile 1 or 3 x horizon {overnight (close d+1 -> open d+2), 5d, 21d} x LONG only, excess vs EW universe. 800 distinct rules.
- **Score.** Enter at the close of d+1, cost 5bp/side (shock 15bp), non-overlapping for 5d/21d. Same scorer frame as LUCK-B4.
- **Discovery = 2004-01..2012-12 only** (halves 2004-08 / 2009-12). Confirmation = **2013-01..2019-12**, not pulled. 2020+ unused.
- **Pass (discovery).** Net mean > 0, t >= 3, both halves > 0, median > 0, ex-top-5 dates > 0, n >= 30 dates, annualized net excess
  at 100% deployment >= 16%/yr.
- **Null.** 10 within-date feature permutations + a date placebo (features lagged 252 trading days per fund). Batch counts only if
  real passes > max over all 11 null runs AND > 3 x their mean.
- **Survivors.** <= 5 with a plausible mechanism, not a known dead family (IBS/short-term reversal, leverage-only, ETF discount
  reversion), get an amendment, then ONE look on 2013-19 at 5bp and 15bp/side; gate as discovery with t >= 2 and DSR > 0.95.
- Out: `data/research/program/luck_b6_out.txt`, `luck_b6_rules.parquet`.
Program N = 949.

### Result — LUCK-B6 (2026-10-13, discovery 2004-12 only; N 949, 800 trials): LUCK — 0 passes, nulls 0 (10/10), placebo 0
`luck_gen6.py` (pull `luck_b6_pull.py`, cache data/research/wrds_b6/), out `luck_b6_out.txt`; scorer from luck_gen4 unchanged
(halves split set to 2009-01-01 as registered). NAV link 94% of ETF-days (fund_hdr cusip8 -> ncusip), so premium features kept;
universe ~95 (2004) -> 465 (2012) funds/day. Disclosed: CRSP ETF shrout updates irregularly (5d change exactly 0 on 80% of rows), so
flow features are coarse; fund age from the earliest namedt; last Dec-2012 21d exits dropped. Confirmation 2013-19 NOT pulled.
Best (all fail): premium top decile x 21d loser 21d +145bp t 2.06 median +1 (outlier-carried); old fund x 252d winner +43bp t 2.03
(5%/yr); 63d flow top decile x 5d outflow +241bp t 1.90 n 32, first half negative. ETF fund-level features add nothing.
Program N = 949.

## Study MODERN-XS — which stock characteristics pick winners in the modern regime (pre-register 2026-10-13; N 949 -> 977, 28 candidates scored)
User request 2026-10-13: "strategy picking specific stocks that succeed especially well during the current modern timeframe ...
categories ... volume". Inventory (agent, 2026-10-13): monthly 12-1 momentum, 52w-high, low-vol, 1m reversal, sector/industry
momentum, theme clusters, calendar seasonality are ALL already judged on 2017-26 and dead (NEXT 1386-1400, 1308) -> excluded.
Never judged here as a monthly sort on any window: value, profitability/quality, size, investment, issuance, leverage, turnover,
dollar-volume trend. Not read: any monthly return sorted on these features.
- **Honesty caveat (stated before running).** Discovery 2021-23 and judge 2024-26 are the SAME regime (CLAUDE.md "two halves is
  not OOS"). The user asked for modern-regime-specific edges on purpose, so the within-regime judge is the design; a PASS is
  therefore a forward-shadow candidate only, never sized on the backtest. The 1998-2015 run is descriptive (always-worked vs
  modern-only), not a gate.
- **Data.** Sharadar SEP (raw close for price filters, closeadj for returns), DAILY (marketcap, pb, pe, ps, evebitda), SF1 ARQ/ART
  usable from datekey + 1 trading day, TICKERS (category Domestic Common Stock*, sector); delisted included; SFP QQQ/SPY closeadj.
- **Universe at each month-end t.** Domestic common, raw close >= $5, 63d median $vol >= $10M, >= 252 sessions listed.
- **Features (14, each scored in BOTH directions = 28 candidates).** ln marketcap; book-to-market (1/pb); earnings yield (1/pe, all
  signs as is); sales yield (1/ps); EV/EBITDA inverse; gross profitability (gp / assets, ART); ROE (netinc / equity, ART); accruals
  ((netinc - ncfo) / assets, ART); asset growth (assets yoy, ARQ); share issuance (sharesbas yoy); leverage (debt / assets); turnover
  (63d mean volume / shares outstanding); dollar-volume trend (21d / 252d median $vol); ln 63d median $vol.
- **Rule.** Each month-end: EW top decile of the feature (direction as the candidate says), buy the close of the first session of
  t+1 (one-session lag), hold to the close of the first session of t+2. Cost 10bp round trip (shock 30bp). Delisting: last close,
  -30% if delisted for cause (Sharadar action), as SHAR-SURV.
- **Metrics per month.** Excess vs QQQ (the user's real benchmark) and vs the EW universe (alpha vs beta); report beta to QQQ,
  sector mix of picks (the "categories" read), median pick $ADV.
- **Discovery 2021-01..2023-12 (36 months).** Rank the 28 by t of excess vs the EW universe; keep the top 3 with t >= 2.
- **Judge (one look) 2024-01..2026-09 (33 months), each of the <= 3 kept.** PASS all: annualized net excess vs QQQ >= +16%/yr
  (= +8pp at $10k at 50% capture); excess vs EW universe t >= 2; median month vs QQQ > 0; ex-top-3 months > 0; 30bp shock still
  > 0 vs QQQ; DSR > 0.95 at N 977. Otherwise KILL (or WEAK if vs-EW t >= 2 but vs-QQQ fails: a beta-matched tilt, not an index beater).
- **Descriptive.** 1998-2015 same rule for all 28 (sign/magnitude: always vs modern-only); per-year table; liquidity buckets ($10-50M,
  $50-500M, > $500M ADV) for the kept features. No re-tuning of decile, universe, lag or features after outcomes.
- Runner `research/sim/modern_xs.py` -> `data/research/program/modern_xs_out.txt`.
Program N = 977.

### Result — MODERN-XS (2026-10-13, one look; N 977): KILL
`modern_xs.py`, out `modern_xs_out.txt`. Panel 1999-01..2026-09, median 1,405 names/month. Discovery 2021-23 top 5 by t vs EW: sales
yield+ 2.20, issuance- 2.09, b2m+ 1.75, ey+ 1.70, evebitda_inv+ 1.57 -> kept sy+ and issuance- (selection written before 2024+ was
computed). Judge 2024-01..2026-09: sy+ vs QQQ -1.10%/mo (t -1.07), vs EW -0.17 (t -0.38), median -2.37, hit 39%; issuance- vs QQQ
-1.09%/mo (t -1.17), vs EW -0.16 (t -0.56); all gates FAIL, DSR 0. Picks tilt Consumer Cyclical/Defensive and Financials, away from
Tech; beta to QQQ 0.26-0.43 in the judge window. 1998-2015 descriptive: sy+ +0.20%/mo t 0.70, issuance- +0.31 t 1.42 (issuance+ -0.67
t -3.5). Disclosed choices: SF1 strict datekey < t with a 450d staleness cap; ROE needs positive equity; $vol from split-adjusted
close x volume; turnover via marketcap/raw close; for-cause delisting = bankruptcy/regulatory action within 10d; ticker as key.
Read: no untested characteristic beats QQQ in 2024-26; modern winners were index/tech beta, which a QQQ benchmark already holds.
Program N = 977.

### Result — LATE-FLOW (2026-10-13, 2010-01..2015-12, one full run; N 945): KILL, 0/6 gates
`late_flow.py` (aggregation `late_flow_run.py`/`late_flow_day.py`, cache data/research/late_flow/), out `late_flow_out.txt`. 1510 days,
universe 1000/day, link 0.976, flow rate 0.968, 2072 trades/name in the window, 9.5% signed by tick test. Bottom-FLOW decile: gross
+0.87bp/night, net -3.13bp at 2bp/side (t -9.6), median -3.3, ex-top-5 -3.4, halves -2.5 / -3.8; 5bp/side -9.1. Deciles monotone
(D1 +0.9 t 2.7 ... D10 -1.3 t -3.5, Spearman -0.85); top-FLOW decile -5.2 net; within-day-return-tercile spread gross +0.55 t 1.72.
Disclosed: excluded cond codes O,Q,6,M plus I,Z,U (odd-lot / out-of-sequence) and tr_corr != 00; the runner agent read a 166-day
(2010) preview (-2.1bp net) before the run finished; the design was not changed. Read: late-day order flow does carry a real
overnight premium, but ~1bp/night, an order of magnitude below the gate and below any realistic cost.
Program N = 977.

## Study SECT-LAG — sector ETF -> laggard constituent catch-up scalp (pre-register 2026-10-13; N 977 -> 978)
Scalp loop iteration 2 (`research/drafts/prompt_scalp_loop_2026-10-13.md`, ledger `scalp_loop_ledger.md`). Track A. Nothing read.
- **Mechanism / counterparty.** When a sector ETF moves sharply in 5 minutes, the move is priced first in the ETF and the most
  liquid members; stale limit orders in thinner same-sector names are picked off over the next minutes as market makers re-quote and
  index/ETF arbitrage plus sector traders buy the laggards. Counterparty: resting liquidity in the laggard that has not updated. Why it
  could survive at $2-25k: the laggards are thin ($10M-$1B ADV), where HFT cross-asset arb has a small notional per event.
- **Note (written before any data).** A TP/stop/time-out does not create edge (optional stopping): the scalp nets > 0 only if the mean
  move to exit beats c. The barriers only shape the distribution; p vs p* is reported as the user's "confidence" read.
- **Data.** WRDS TAQ ms (ctm trades, complete_nbbo) built server-side into per-minute NBBO mid/ask/bid marks per symbol; CRSP dsf for
  universe, hsiccd for sector, taqmclink for the link. Regular hours only.
- **Sectors (ETF -> CRSP SIC set, as of the prior day):** XLF/KRE -> 6020-6029 (banks); XBI -> 2833-2836 (drugs/biotech); XLE -> 1311,
  1381-1389, 2911 (oil & gas); SMH -> 3674 (semis); GDX -> 1040 (gold miners); XHB -> 1520-1531 (homebuilders). ETF used for a sector
  = the first listed that traded that day (KRE exists from 2006, XBI 2006, GDX 2006, SMH 2000/2011 relaunch: use whichever SMH ticker
  trades).
- **Universe (per day, from data up to d-1).** Common (shrcd 10/11), price >= $5, 20d median $vol $10M-$1B, SIC in a sector set.
- **Signal at minute t, 10:00 <= t <= 15:30.** ETF mid return over (t-5, t] >= +2 x sd, sd = the ETF's 5-min mid-return std over the
  prior 20 trading days (10:00-15:30 only). Laggard: constituent mid return over (t-5, t] <= 0.25 x the ETF return. Quoted spread at t
  <= 30bp. One entry per name per day; at most 3 names per signal (the lowest own-return ones); ETF signals spaced >= 15 min.
- **Trade.** Long only. Entry = NBBO ask at t + 1s. G = clamp(0.5 x ETF 5-min return, 15bp, 50bp); S = G; time-out T = 15 min.
  - Pessimistic fill: TP fills only if a lit trade (exchange != 'D', regular condition, size >= 100) prints strictly above entry x (1+G);
    stop triggers when the NBBO bid <= entry x (1-S) and exits at that bid (or the next trade if lower); time-out exits at the bid.
  - Optimistic fill: TP on touch of any trade at/above the level; exits at mid.
  - c (reported) = entry ask vs mid + exit vs mid, as measured in-trade. "2x cost" = net minus one more measured round-trip spread.
- **Eras.** Discover 2010-2014 (120 random trading days, fixed seed 978); judge 2015-2019 (120 random days, seed 979), one look.
  If discovery is net < 0 at 1x on the pessimistic bound, KILL without opening the judge era.
- **Gate (judge era, pessimistic fills).** Net at 2x cost > 0 with day-clustered t >= 2; hit rate p > p* = (S + c)/(G + S) on the
  measured c; ex-top-5 trades > 0; both halves of the judge era (2015-17 / 2018-19) > 0; >= 200 trades; control beaten: the same entry
  rule on NON-laggard constituents (own return >= 0.75 x ETF) and a time-shift placebo (same names, signal minute shifted by +60 min,
  same day) must both be below the laggard arm. Ceiling at $10k must clear +8pp/yr. Otherwise KILL (WEAK if 1x passes, 2x fails).
- **Reported.** p, p*, gross, net 1x/2x, optimistic vs pessimistic, by sector, by spread bucket, by time of day, trades/day.
- Runner `research/sim/sect_lag.py` -> `data/research/program/sect_lag_out.txt`.
Program N = 978.

### Result — SECT-LAG (2026-10-13, discovery 2010-14 only; N 978): KILL at the registered early-kill
`sect_lag.py`, out `sect_lag_out.txt:18-34`. 120 days, 3,334 laggard trades (27.8/day). Pessimistic: gross +0.08bp, net 1x -9.27bp
(day-clustered t -24), net 2x -18.9, median -16.3, ex-top-5 -9.3; optimistic net 1x -4.6. Measured c 9.35bp vs mean G=S 16.7bp:
p(TP/all) 0.254 vs p* 0.786. Non-laggard control gross -0.05bp, +60m placebo +0.15bp: laggards no different. Halves -8.6 / -9.9;
every sector negative. **The 2015-19 judge era was NOT opened.** Read: there is no 1-15 min catch-up in thin same-sector names after
a 2-sd sector-ETF move even in 2010-14; the cross-asset lag is gone inside the first minute. Disclosed choices 1-12 in the out file.
Program N = 978.

## Study ISO-BURST — intermarket-sweep buy bursts in large caps, 1-10 min continuation scalp (pre-register 2026-10-13; N 978 -> 979)
Scalp loop iteration 3, Track A. Changes vs SECT-LAG: mechanism (order flow, not lead-lag), universe (large caps, not thin sector
names), counterparty (urgent institutional parent order, not stale quotes). Nothing read.
- **Mechanism / counterparty.** An intermarket sweep order (ISO, TAQ sale condition 'F') takes every displayed offer at once instead
  of working the book: the buyer pays for immediacy, which is the signature of an urgent, informed or deadline-bound parent order
  (Chakravarty, Jain, Upson & Wood 2012: ISOs carry more information than other trades). If the parent is not done, its remaining
  child orders keep lifting offers for minutes. Large caps (c ~ a few bp) are where c is smallest relative to a minute-scale drift.
- **Data.** WRDS TAQ ms ctm (trades) aggregated server-side per name per minute with an explicit `sym_root IN (...)` list; NBBO only for
  triggered names in the 10 minutes after a signal. CRSP dsf / dsf_v2 for universe. Regular hours.
- **Universe (from d-1).** CRSP common (shrcd 10/11), price >= $10, 20d median $vol >= $200M. ~top 300-600 names per day.
- **Signal at minute end t, 10:00 <= t <= 15:30.** In the minute (t-1, t]: ISO buy $ (ISO trades signed buy by the tick test, i.e. price
  > previous trade, or equal and previous sign buy) >= 0.25% of the name's 20d median $vol, AND ISO buy $ >= 3 x ISO sell $, AND the
  minute's last-trade return > 0. One entry per name per day. Tick-test signing is disclosed (no quote join needed for the signal).
- **Trade.** Long only. Entry = NBBO ask at t + 1s. G = 20bp, S = 20bp, T = 10 min (fixed; a large cap's 10-min sd is ~20-30bp).
  - Pessimistic fill: TP only if a lit trade (exchange != 'D', regular condition, size >= 100) prints strictly above entry x 1.002; stop
    when the NBBO bid <= entry x 0.998, exit at that bid (or the next trade if lower); time-out at the bid.
  - Optimistic: TP on touch, exits at mid. c = entry vs mid + exit vs mid, measured. 2x cost = net minus the entry quoted spread x 1.
- **Also reported (the real edge test):** mid drift from t+1s to +1, +5, +10 min, gross, vs (a) a matched control: same name, same day,
  a random minute with no burst; (b) bursts on the SELL side (mirror) — sign check, not traded.
- **Eras.** Discover 2010-14 (100 random days, seed 980); judge 2015-19 (100 random days, seed 981), one look. Early kill: discovery
  net < 0 at 1x pessimistic -> KILL without opening 2015-19.
- **Gate (judge era, pessimistic).** Net at 2x cost > 0, day-clustered t >= 2; p > p*; ex-top-5 > 0; both judge halves > 0; >= 200 trades;
  +10m mid drift beats the matched control with t >= 2. Otherwise KILL (WEAK if 1x passes and 2x fails).
- Runner `research/sim/iso_burst.py` -> `data/research/program/iso_burst_out.txt`.
Program N = 979.

## Study SCALP-CLF — honest classifier for P(+30bp before -30bp) in large caps, midday (pre-register 2026-10-13; N 979 -> 980)
Scalp loop iteration 4, Track B (first B batch; feature family F1 = price/volume path). Nothing read. Costs from the Track C table
(`scalp_cost_out.txt`, ledger "Cost table").
- **Label.** For name i at decision minute t (10:30 <= t <= 15:00, one decision per name every 15 min): entry = minute-t close + the
  measured 2018 >$1B half-spread for that time bucket; y = 1 if the minute high reaches entry x 1.003 + one half-spread (pessimistic
  "through" proxy) before the minute low reaches entry x 0.997 within 30 min; if both inside one bar -> stop first; neither -> time-out at
  the t+30 close minus a half-spread (P&L still counted). G = S = 30bp, T = 30m (large-cap 30-min sd ~ 40bp; min G for >$1B midday ~22bp).
- **Breakeven.** c ~ 5-7bp midday (2025) / ~3-4bp (2018): p* = (30 + c)/60 ~ 0.56-0.62 at 1x, ~0.61-0.72 at 2x.
- **Universe.** Alpaca SIP minute bars, raw (split-adjusted only) prices; common stocks with 20d median $vol >= $1B as of d-1 (Sharadar
  SEP, delisted included). Regular hours.
- **Features F1 (all <= t):** own returns over 1/5/15/30/60 min and since open, gap vs prior close, minute range and its 20-min mean,
  relative volume (last 15 min vs the same clock window over the prior 20 days), distance to session VWAP, HOD and LOD, SPY return over
  5/30 min and since open, name minus SPY over 30 min, minute of day, realized 30-min vol.
- **Model.** sklearn HistGradientBoostingClassifier (defaults, max_iter 200, learning_rate 0.05), isotonic calibration on the inner
  validation fold. Purged walk-forward on 2016-01..2018-12: train on all months before month m minus a 5-session embargo, predict month m
  (m from 2017-01). Top-confidence bucket = predictions >= the 95th percentile of the out-of-fold scores of the training window.
- **Nulls (mandatory).** (a) labels permuted within day; (b) time-shift placebo: features from t paired with the label at t+60min.
  Same model, same threshold rule.
- **Judge (one look): 2019-01..2019-12**, model retrained on 2016-2018 once, threshold frozen from 2016-18 out-of-fold scores.
  2019 single-stock minute data is TOUCHED only by the night exact study (different class: 15:40 close->open), disclosed.
- **Gate (2019, pessimistic labels).** Top-bucket hit rate p > p* at 2x cost with binomial lower 95% bound > p*(1x); net/trade at 2x
  > 0 with day-clustered t >= 2; top bucket beats BOTH nulls' top buckets on hit rate; reliability curve monotone in the top 3 deciles;
  ex-top-5 > 0; >= 300 trades; non-overlapping per name (one open trade per name). Ceiling at $10k >= +8pp. Otherwise KILL.
- Runner `research/sim/scalp_clf.py` -> `data/research/program/scalp_clf_out.txt`.
Program N = 980.

### Result — SCALP-CLF (2026-10-13, OOF 2017-18 + one 2019 look; N 980): KILL, 3/8 gate items
`scalp_clf.py`, out `scalp_clf_out.txt:5-55`. 79 names (>$1B $vol), 525k decisions. 2019 top bucket (frozen thr 0.428): n 7,742 (31/day),
p 0.431 (Wilson lo 0.420) vs p* 0.560 (1x) / 0.619 (2x); net -2.97bp 1x (t -5.7), -6.60bp 2x (t -12.5), ex-top-5 -6.6. Nulls: permuted
0.335, +60m time-shift 0.413 (AUC 0.730 real vs 0.722 shift). Calibration good (D10 hit 0.423 vs score 0.434); base rate 0.205.
Importance led by rv30, rng20: the model learns that high-vol states resolve inside 30 min, not direction. OOF 2017-18 the same
(p 0.411, nulls 0.400/0.413). A lookahead (r60 wrap at 10:30) was found and fixed before any run. Disclosed choices in the out file.
Program N = 980.

## Study RETAIL-HERD — first-hour retail buy imbalance -> 10:30-11:30 continuation scalp (pre-register 2026-10-13; N 980 -> 981)
Scalp loop iteration 6, Track A. Changes vs the last rows: counterparty (retail herd + wholesaler hedging, not institutions or stale
quotes), data field (BJZZ sub-penny TRF prints), universe ($50M-$1B mid caps), time of day (fixed 10:30 decision). Nothing read.
- **Mechanism / counterparty.** Retail attention clusters within the day (Barber, Huang, Odean & Schwarz 2022 herding). Marketable retail
  orders are internalized by wholesalers, who hedge part of the net inventory on lit markets; persistent first-hour retail BUY pressure
  in a name that is also up should keep lifting offers as more retail arrives. Counterparty: wholesaler hedging plus late retail.
- **Retail sign (BJZZ 2021).** TAQ trades on exchange 'D' with price p >= $1: Z = 100 x (p mod 0.01) in cents; 0.6 < Z < 1 = retail BUY,
  0 < Z < 0.4 = retail SELL, else unsigned. Known caveat (Barber et al. 2023): sign accuracy is imperfect; disclosed.
- **Data.** WRDS TAQ ms ctm, server-side per-day aggregation with explicit sym_root lists; NBBO + trades only for triggered names 10:30-
  11:31. CRSP dsf / dsf_v2 universe. Reuse `research/sim/iso_burst.py` / `sect_lag.py` fill and cost code.
- **Universe (from d-1).** Common (shrcd 10/11), price >= $5, 20d median $vol $50M-$1B.
- **Signal at 10:30.** Over 09:30-10:30: retail $ (buy + sell) >= 0.5% of 20d median $vol; RIB = (buy$ - sell$)/(buy$ + sell$) >= 0.5;
  09:30->10:30 last-trade return > 0. Take the top 5 by RIB (ties: larger retail $).
- **Trade.** Long. Entry = NBBO ask at 10:30:01. G = 40bp, S = 40bp, T = 60 min (mid-cap 60-min sd ~ 60-80bp; 2025 c for this bucket at
  10:30-12 is ~9-10bp, so G >= 4c). Pessimistic / optimistic fills, c and 2x cost exactly as ISO-BURST.
- **Controls.** (a) momentum without retail: same universe, top 5 by 09:30->10:30 return among names with RIB <= 0 and the same retail-$
  floor; (b) +60 min time-shift: the same picks entered at 11:30. Also reported: mid drift +5/+15/+30/+60 min.
- **Eras.** Discover 2010-14 (100 random days, seed 982); judge 2015-19 (100 days, seed 983), one look. Early kill: discovery net 1x
  pessimistic < 0 -> KILL, judge era unopened.
- **Gate (judge, pessimistic).** Net 2x > 0 with day-clustered t >= 2; p > p*; ex-top-5 > 0; both halves > 0; >= 200 trades; beats control
  (a) on net with t >= 2. Ceiling at $10k >= +8pp. Else KILL (WEAK if 1x passes, 2x fails).
- Runner `research/sim/retail_herd.py` -> `data/research/program/retail_herd_out.txt`.
Program N = 981.

### Result — ISO-BURST (2026-10-13, discovery 2010-14 only; N 979): KILL at the registered early-kill
`iso_burst.py`, out `iso_burst_out.txt:2-16`. 100 days, 6,995 trades (~70/day). Pessimistic gross +0.10bp, net 1x -3.26bp (t -12.1),
net 2x -7.04, ex-top-5 -3.27; optimistic net 1x -1.58. c 3.36bp; p 0.248 vs p* 0.584. Mid drift after a buy-ISO burst minus a matched
same-name no-burst minute: +1m -0.17bp, +5m +0.11, +10m +0.06 (t 0.1). Sell mirror not a continuation either. **Judge era 2015-19
NOT opened.** Read: ISO buy sweeps carry no 1-10 min continuation in large caps even in 2010-14. Disclosed: universe ~100-150 linked
names/day (fewer than the prose guess); ~45% of entries at 10:00-10:01; clustered t not bootstrap-validated.
Program N = 981.

## Study SCALP-OFI — honest classifier on ORDER-FLOW features for P(+20bp before -20bp in 15 min), large caps (pre-register 2026-10-13; N 981 -> 982)
Scalp loop iteration 7, Track B, feature family F2 (order flow / quotes; F1 price path died in SCALP-CLF). Changes vs SCALP-CLF: data
(TAQ quotes + signed trades, not minute bars), features, era, horizon. Nothing read.
- **Why it could differ.** SCALP-CLF's features forecast volatility, not direction. Order-flow imbalance (Cont, Kukanov & Stoikov 2014)
  and quote imbalance are the strongest documented short-horizon DIRECTION predictors; the question is whether any of it survives c.
- **Label (pessimistic).** Name i, decision minute t (10:00-15:30, every 5 min). Entry = NBBO ask at t. y = 1 if a lit trade (exch != 'D',
  regular condition, size >= 100) prints strictly above entry x 1.002 before the NBB falls to <= entry x 0.998, within 15 min; same-minute
  conflicts -> stop first. P&L: TP = +20bp - exit half... exactly as ISO-BURST (stop exits at the bid, time-out at the bid at t+15).
- **Universe (d-1).** CRSP common, price >= $10, 20d median $vol >= $500M (TAQ-linked). Sample <= 120 names/day (fixed seed).
- **Features F2 (all strictly <= t):** Cont OFI over 1/5/15 min normalized by mean depth; quote imbalance (bidsz - asksz)/(bidsz + asksz)
  at t and its 5-min mean; Lee-Ready signed $ imbalance over 1/5/15 min / 20d $vol; ISO share of volume 5 min; BJZZ retail imbalance
  15 min; trade-count intensity vs the name's same-clock 20d mean; spread at t / day-to-t median; odd-lot share 15 min; own mid return
  5/15 min; SPY mid return 5/15 min; minute of day.
- **Model.** sklearn HistGradientBoostingClassifier (max_iter 200, lr 0.05), isotonic calibration. Purged walk-forward on 2011-13 sampled
  days (120 days, seed 984): train on earlier months, 5-session embargo, predict month m (m from 2012-01). Threshold = 95th pct of the
  training window's OOF scores.
- **Nulls.** (a) labels permuted within day; (b) time-shift: features at t paired with the label at t+60. Same model/threshold rule.
- **Judge (one look): 2015, 60 random days (seed 985)**, model retrained once on all 2011-13 data, threshold frozen.
- **Gate (2015, pessimistic).** Top-bucket p > p*(2x) with Wilson lower bound > p*(1x); net/trade at 2x > 0 with day-clustered t >= 2;
  top bucket beats both nulls; reliability monotone top 3 deciles; ex-top-5 > 0; >= 300 trades; one open trade per name. Ceiling >= +8pp.
  Also reported: mean mid drift at +1/+5/+15 min in the top bucket vs all decisions (direction check). Else KILL.
- Runner `research/sim/scalp_ofi.py` -> `data/research/program/scalp_ofi_out.txt`.
Program N = 982.

### Result — RETAIL-HERD (2026-10-14, discovery 2010-14 only; N 981): KILL at the registered early-kill
`retail_herd.py`, out `retail_herd_out.txt`. 100 days, ~487 names/day in universe, 412 herd trades (4.1/day). Pessimistic gross -0.10bp,
net 1x -4.45bp (t -1.89), net 2x -9.66; optimistic net 1x -2.47; ex-top-5 -5.0; halves -7.1 / -0.6. c 4.35bp; p 0.313 vs p* 0.554.
Mid drift herd +5/+15/+30/+60m: +0.09/-0.16/-2.46/-4.52bp vs control (a, momentum without retail) +0.75/+2.40/+5.16/+4.43 (herd minus
control at +60m -10.2bp, t -1.3). **Judge era 2015-19 NOT opened.** Read: first-hour retail buy imbalance carries no continuation; if
anything the herd names fade over the next hour (not significant). Retail $ ~0.8% of ADV, ~19% of TRF volume.
Program N = 982.

## Study STOP-RUN — prior-day-low stop cascade exhaustion, long reversal scalp (pre-register 2026-10-14; N 982 -> 983)
Scalp loop iteration 8, Track A. New mechanism class: forced stop-loss selling and its overshoot (reversal, not continuation; the last
four mechanisms showed zero continuation). Changes vs the last rows: mechanism (forced stops), counterparty (stop-loss sellers),
signal geometry (a price level). Nothing read.
- **Mechanism / counterparty.** Stop-loss sell orders cluster just below obvious levels such as the prior day's low (Osler 2003/2005 for
  FX; retail and algo stops in equities). A breach triggers them as market orders; the cascade pushes price below where unconstrained
  liquidity would set it, then reverts once the stops are exhausted. Counterparty: stop-loss sellers who must sell at any price.
- **Data.** WRDS TAQ ms, server-side per-day per-minute aggregation with explicit sym_root lists; NBBO + lit trades for event names only.
  CRSP dsf universe; prior-day regular-session low from TAQ (09:30-16:00 trades, regular conditions), not CRSP (CRSP low can include
  odd prints / is not regular-hours only).
- **Universe (d-1).** Common, price >= $10, 20d median $vol >= $500M.
- **Event.** First minute m in 10:00-15:00 whose minute low (regular lit trades) is <= PDL x (1 - 0.001) with the session low before m
  still > PDL (first breach of the day). Cascade footprint: volume over minutes m..m+2 >= 3 x the name's mean per-minute volume from
  09:30 to m-1. Decision t = end of minute m+3 (exhaustion window; fixed). One event per name per day.
- **Trade.** Long. Entry = NBBO ask at t + 1s. G = 30bp, S = 30bp, T = 30 min. Pessimistic/optimistic fills, c and 2x cost exactly as
  ISO-BURST.
- **Controls.** (a) mechanism test: breaches WITHOUT the volume footprint (< 1.5x), same entry; (b) placebo level: first crossing of
  PDL x 1.005 from above with the same volume footprint (a level with no stop cluster); (c) mirror: prior-day-HIGH breach with footprint,
  sign check only (not traded). Mid drift +1/+5/+15/+30 min reported for all.
- **Eras.** Discover 2010-14 (100 days, seed 986); judge 2015-19 (100 days, seed 987), one look. Early kill as before.
- **Gate (judge, pessimistic).** Net 2x > 0 with day-clustered t >= 2; p > p*; ex-top-5 > 0; both halves > 0; >= 200 trades; event arm
  beats BOTH (a) and (b) on +30m mid drift with t >= 2. Ceiling at $10k >= +8pp. Else KILL (WEAK if 1x passes, 2x fails).
- Runner `research/sim/stop_run.py` -> `data/research/program/stop_run_out.txt`.
Program N = 983.

### Result — STOP-RUN (2026-10-14, discovery 2010-14 only; N 983): KILL (infeasible + mechanism sign wrong); judge era not opened
`stop_run.py`, out `stop_run_out.txt:18-64`. **Registration error disclosed:** the >= $500M universe is only 24-55 linked names/day, so
the rule fires 14 times in 100 days (0.14/day); the >= 200-trade gate is unreachable even on every 2015-19 day (~175), so the judge era
was not opened although the letter of the early kill (net 1x pess < 0) did not trip (+4.26bp, t 0.54; net 2x -0.92; p 0.50 vs p* 0.58).
Mechanism test fails in sign: the stop-cascade footprint arm drifts -14.5bp at +30m vs +36.9bp for breaches WITHOUT the footprint (a,
n 20, t 2.1); placebo level (b) -30bp. Ceiling at $10k -0.16pp. Read: no stop-cascade overshoot to buy; the footprint marks real
selling, not exhausted stops. Disclosed: footprint read as a per-minute rate (mean of m..m+2 >= 3x baseline); decision at (m+4) min.
Observation only (not a test, tiny n, 2010-14 >= $500M now TOUCHED for it): first breaches of the prior-day low WITHOUT a volume burst
(+36.9bp, n 20) and of the prior-day high (+35.4bp mirror, n 13) both reverted.
Program N = 983.

## Study LEVEL-BOUNCE — quiet first touch of the prior-day low in mid caps, long reversal scalp (pre-register 2026-10-14; N 983 -> 984)
Scalp loop iteration 9, Track A. Origin: STOP-RUN's control (a) (quiet breaches reverted, n 20, 2010-14 >= $500M; that universe is now
touched for this idea and is EXCLUDED here). Changes vs STOP-RUN: mechanism (resting liquidity at a reference level, not forced
stops), universe ($50M-$500M, untouched for this), counterparty (limit buyers at support). Nothing read on this universe.
- **Mechanism / counterparty.** Limit orders cluster at salient reference prices (prior-day extremes; Kavajecz & Odders-White 2004:
  technical support/resistance levels coincide with depth peaks in the book). A quiet first touch (no volume burst = no informed seller)
  meets that depth and bounces. Counterparty: the patient limit buyers at the level, plus sellers who run out at it.
- **Data / fills / c / 2x cost.** As STOP-RUN (reuse `stop_run.py`): TAQ ms, explicit sym_root lists, prior-day regular-hours lit low
  from TAQ, NBBO + lit trades for event names.
- **Universe (d-1).** Common, price >= $5, 20d median $vol $50M-$500M.
- **Event.** First minute m in 10:00-15:00 with minute low <= PDL x 0.999 and session low before m > PDL. Quiet: mean per-minute volume
  over m..m+2 < 1.5 x the name's mean per-minute volume 09:30..m-1. Decision t = (m+4) min (same as STOP-RUN). One event per name/day.
- **Trade.** Long. Entry = NBBO ask at t + 1s. G = 40bp, S = 40bp, T = 30 min.
- **Controls.** (a) burst breaches (>= 3x, same entry); (b) placebo level PDL x 1.005 quiet first crossing from above; (c) same name-day
  random minute in 10:00-15:00 (no level). Mirror PDH quiet breach reported as sign check only.
- **Eras.** Discover 2010-14 (100 days, seed 988); judge 2015-19 (100 days, seed 989), one look. Early kill: discovery net 1x
  pessimistic < 0, or < 200 discovery trades -> KILL, judge era unopened.
- **Gate (judge, pessimistic).** Net 2x > 0 with day-clustered t >= 2; p > p*; ex-top-5 > 0; both halves > 0; >= 200 trades; event beats
  (b) and (c) on +30m mid drift with t >= 2. Ceiling at $10k >= +8pp. Else KILL (WEAK if 1x passes, 2x fails).
- Runner `research/sim/level_bounce.py` -> `data/research/program/level_bounce_out.txt`.
Program N = 984.

### Result — LEVEL-BOUNCE (2026-10-14, discovery 2010-14 only; N 984): KILL at the registered early-kill
`level_bounce.py`, out `level_bounce_out.txt`. 100 days, 387 events (3.9/day). Pessimistic gross +2.99bp, net 1x -3.24bp (t -1.39), net
2x -10.6; optimistic net 1x +0.18; median -7.4, ex-top-5 -5.7; halves -0.2 / -6.8. c 6.23bp; p 0.380 vs p* 0.578. +30m mid drift: event
+7.3bp vs placebo level PDL x 1.005 (b) +7.3, burst (a) +18.4, random minute (c) -9.1; event minus (b) -5.8 (t -1.25). **Judge era
2015-19 NOT opened.** Read: the "bounce" after a quiet low touch is the same as after crossing any nearby level (a generic short-term
reversal after a dip), not support liquidity; and it is smaller than c. The STOP-RUN control lead does not replicate in mid caps.
Program N = 984.

## Study UPG-DAY0 — pre-open analyst upgrade, buy the opening cross, scalp or sell the closing cross (pre-register 2026-10-14; N 984 -> 985)
Scalp loop iteration 10, Track A. **New class:** execution through the auctions (entry at the official open, exit at a take-profit limit
or the official close), so c ~ 0 instead of 3-10bp (live audit: 213/216 auction fills at the official SIP price). Changes vs the last
rows: horizon (session, not minutes), counterparty (broker clients acting on the call through the day), data (IBES point-in-time
recommendations), execution (crosses). Nothing read. Not a redo: J7 (two upgrades in 10 days, small caps, multi-day), LLM-EARN
(earnings text) and NEWS-DRIFT (headline minutes) are different events/horizons; RESULTS "analyst-ratings trap" is solved by IBES recdet
timestamps (point-in-time).
- **Mechanism / counterparty.** A broker's upgrade issued before the open is acted on by its clients through the session (sales-desk
  calls, PM decisions), not all at 09:30; the opening cross prices the headline, the day's order flow follows. Counterparty: slower
  institutional clients of the issuing broker.
- **Events.** IBES recommendation detail (`ibes.recddet`), US firms: a broker's new rating strictly better than its own prior rating for
  the same firm (ireccd decreases), announced (anndats/anntims) after 16:00 on d-1 and before 09:00 on d (pre-open only). CRSP link via
  ibcrsphist / ncusip. One event per firm-day (any broker).
- **Universe (d-1).** CRSP common, price >= $5, 20d median $vol >= $50M.
- **Trades.** (A) Auction-to-auction: buy the official open (CRSP openprc), sell the official close (CRSP prc). c = 0, reported also at
  2bp/side shock. (B) Scalp: same entry; sell a limit at open x 1.005 (G = 50bp) if a lit TAQ trade prints strictly above it with size
  >= 100 before 15:55; stop at -50bp exits at the NBB when the NBB <= open x 0.995 (pays the half-spread); else the closing cross.
- **Controls.** (a) downgrades (mirror, sign check); (b) same firms' non-event days matched on open gap decile (gap-continuation
  baseline); (c) upgrades announced 09:30-16:00 on d (excluded from the trade; drift reported).
- **Eras.** (A) runs on ALL days: discover 2010-14, judge 2015-19 (one look). (B) TAQ: 100 random event-days per era (seeds 990/991).
  Early kill: discovery (A) mean net at 2bp/side < 0 -> KILL, judge era unopened.
- **Gate (judge, A and B separately, pessimistic).** Mean net at 2x cost (4bp/side for A; 2x measured stop half-spread for B) > 0 with
  day-clustered t >= 2; median > 0 (A) / p > p* (B); ex-top-5 > 0; both halves > 0; >= 200 events; beats control (b) with t >= 2.
  Ceiling at $10k >= +8pp (events/day x net x deployed share x 50% x 250). Else KILL.
- Runner `research/sim/upg_day0.py` -> `data/research/program/upg_day0_out.txt`.
Program N = 985.

### Result — SCALP-OFI (2026-10-14, WF 2011-13 + one 2015 look; N 982): KILL, 2/8 gate items
`scalp_ofi.py`, out `scalp_ofi_out.txt:28-59`. ~30-40 names/day (>= $500M), 120 + 60 days. 2015 top bucket (frozen thr 0.361): n 4,490,
p 0.376 (Wilson lo 0.362) vs p* 0.605 (1x) / 0.711 (2x); c 4.2bp; net -3.97bp 1x (t -7.4), -8.20bp 2x (t -14.5); ex-top-5 -8.2. Top-bucket
mid drift minus all decisions: +1m -0.05bp, +5m +0.21, +15m +0.60 (t < 1). Time-shift null top bucket 0.353 (vs real 0.376); the permuted
null produced no scores above its threshold (reported as FAIL). Importance: ret15, ret5, minute of day, relative spread; order-flow
features (OFI, quote imbalance, BJZZ, ISO) add ~0.001-0.003 AUC each. Read: with the strongest documented order-flow features the top
bucket still has ~0 directional drift; the model again ranks volatility/resolution, not direction.
Program N = 985.

### Result — UPG-DAY0 (2026-10-14, discovery 2010-14 + one 2015-19 look; N 985): KILL (A and B)
`upg_day0.py`, out `upg_day0_out.txt:24-80`. Discovery A (open cross -> close cross, 5,437 upgrades, 4.3/day): +14.3bp gross, +10.3 at
2bp/side (t 2.10), event minus same-firm gap-matched control +12.5 (t 2.54); downgrade mirror -21.2bp (t -4.8). **Judge 2015-19 A (6,910):
+5.9bp gross, +1.9 at 2bp/side (t 0.44), -2.1 at 4bp/side; median -3.1, ex-top-5 -3.5, halves -2.6/-1.6; minus control +3.0 (t 0.71).
Ceiling -2.6pp (discovery's +7.4pp was also under the gate).** Downgrade shorts +12.2bp (t 3.2): sign right, not tradable long-only.
B (TP +50 / stop -50): judge p 0.368 vs p* 0.607, net 1x -30.1bp; ~62% stopped out on wide post-open quotes (stop half-spread ~41bp).
Read: the pre-open upgrade's day-0 drift halved after 2014 and is now inside one tick of cost; the opening cross prices most of it.
Post-hoc pockets (NOT gated, judge era now TOUCHED for them): gap <= 0 +28.0bp (t 2.9, n 1,008), $vol >= $1B +27.3bp. Data caveats:
recddet holds revised ratings (PIT not guaranteed); a 16:00 anntims spike (22k rows) unresolved.
Program N = 985.

## Study ETF-CLF — honest classifier for P(+15bp before -15bp in 30 min) on 26 non-QQQ ETFs with cross-asset features (pre-register 2026-10-14; N 985 -> 986)
Scalp loop iteration 11, Track B, feature family F3 (cross-asset state). New universe after the single-stock class verdict: ETFs, where
c ~0.5-3bp, so a few bp of drift would clear p*. Nothing read. QQQ and SMH (TOUCHED 2016-26 intraday) and TQQQ are excluded.
- **Universe (fixed list):** SPY, IWM, DIA, XLF, XLE, XLK, XLV, XLI, XLY, XLP, XLU, XLB, EEM, EFA, EWJ, FXI, TLT, IEF, HYG, LQD, GLD, SLV,
  USO, GDX, XBI, KRE. Alpaca SIP minute bars, split-adjusted only (no dividend adjustment), regular hours.
- **Cost.** Half-spread 0.25bp for SPY/IWM/DIA, 1.5bp for every other ETF (pessimistic vs the measured ~0.25bp ETF median; per-ETF quotes
  not measured). 2x cost doubles both.
- **Label (pessimistic).** Decision every 10 min 10:00-15:20. Entry = minute-t close + half-spread. y = 1 if the minute high >= entry x 1.0015
  + half-spread before the minute low <= entry x 0.9985; same-bar conflicts -> stop; else time-out at the t+30 close - half-spread.
- **Features F3 (all <= t):** own returns 1/5/15/30/60 min and since open; own minus SPY over 30 min; SPY, TLT, GLD, USO, EEM, HYG returns
  over 5 and 30 min; own realized 30-min vol; relative volume (last 30 min vs same clock 20d mean); distance to session VWAP; overnight gap;
  minute of day; ETF id (categorical).
- **Model / nulls / threshold.** As SCALP-CLF: sklearn HistGradientBoostingClassifier (max_iter 200, lr 0.05), isotonic calibration;
  purged walk-forward on 2016-01..2018-12 (monthly, 5-session embargo, predictions from 2017-01); threshold = 95th pct of the training
  window's OOF scores; nulls (a) labels permuted within day, (b) features at t with labels at t+60.
- **Judge (one look): 2019,** model retrained on 2016-18, threshold frozen.
- **Gate (2019, pessimistic).** Top-bucket p > p*(2x) with Wilson lower bound > p*(1x); net/trade at 2x > 0 with day-clustered t >= 2; beats
  both nulls; reliability monotone top 3 deciles; ex-top-5 > 0; >= 300 trades; one open trade per ETF; ceiling at $10k >= +8pp (4x intraday
  BP allowed in the deployed share). Also: top-bucket mean mid drift at +5/+15/+30 vs all decisions. Else KILL.
- Runner `research/sim/etf_clf.py` -> `data/research/program/etf_clf_out.txt`.
Program N = 986.

### Result — ETF-CLF (2026-10-14, OOF 2017-18 + one 2019 look; N 986): KILL, 3/8 gate items
`etf_clf.py`, out `etf_clf_out.txt:104-114`. 26 ETFs, 0 fetch errors; a lookahead (30-bar lookbacks wrapping at 10:00) was caught by the
corruption test and fixed before any model ran. 2019 top bucket: n 1,659, p 0.464 (Wilson lo 0.440) vs p* 0.572 (1x) / 0.643 (2x); net
-1.15bp 1x (t -2.2), -3.14bp 2x (t -6.1); ex-top-5 -3.2. Beats both nulls (perm 0.360, shift 0.430) and is calibrated (D10 0.430), but
AUC 0.775 vs shift-null 0.767: it sorts by volatility (rv30 importance 0.093, all else < 0.011). Top-bucket drift minus all: +1.2 / +2.3 /
+2.4bp at +5/+15/+30 (t 1.9 / 1.9 / 1.1); OOF the same drift was only +0.4-0.5bp. Read: even with c ~1-3bp the cross-asset state gives
~2bp of 30-min drift at best, below the 15bp-barrier cost.
Program N = 986.

## Study UPG-POCKET — UPG-DAY0 post-hoc pocket (gap <= 0), open cross -> close cross, untouched 2020-24 (pre-register 2026-10-14; N 986 -> 987)
Nothing from 2020-24 read. **Low prior:** a post-hoc pocket of a dead rule (UPG-DAY0 killed: 2010-14 +10.3bp, 2015-19 +1.9bp t 0.4). The pocket
was picked AFTER the 2015-19 judge look (gap <= 0 +28.0bp t 2.9 n 1,008; adv >= $1B +27.3bp n 250), so 2015-19 is touched for it and the only
clean test is a period never seen: 2020-24. 2004-09 stays untouched and is NOT opened.
- **Rule (frozen = UPG-DAY0 arm A).** Same event definition (IBES recddet, broker's new rating strictly better than its own prior, announced
  after 16:00 d-1 / before 09:00 d, strictly > 16:00 and < 09:00 so the 16:00 anntims spike and 09:00-09:30 are excluded; one event per firm-day,
  firm-days with both up and down dropped; CRSP common shrcd 10/11, pclose >= $5, adv (20d median $vol, lagged) >= $50M). Buy the CRSP open
  (official open cross), sell the CRSP close (official close cross). **Definitions reused verbatim:** gap = openprc / prior-close - 1 (prior close
  = |prc| of the previous trading day); ">$1B" = adv >= 1e9. PRIMARY = gap <= 0. SECONDARY (reported only, no gate) = adv >= $1B.
- **Data.** IBES recddet + ibcrsphist link + CRSP dsf as in `upg_day0.py` (CRSP dsf/names and the link end 2024-12-31), WRDS standby.
- **Judge window.** 2020-01-01..2024-12-31, one look. Halves: 2020-22 / 2023-24. Cost 2bp/side (1x) and 4bp/side (2x).
- **Gate (PASS), all required, primary arm.** Mean net at 2bp/side > 0 with day-clustered t >= 2; median > 0; ex-top-5 mean > 0; both halves > 0;
  mean still > 0 at 4bp/side; n >= 200. Else KILL (WEAK if only t < 2 with every other item met).
- **Ceiling (reported; PASS also needs it for deployment).** days_with_event/yr x net bp(2bp/side) x share deployed (1.0, one name per day,
  whole shares) x 50% capture x (1 - 35% tax, taxable) at $2.3k / $10k / $25k; deployment gate +8pp/yr at $10k. A statistical PASS below +8pp
  is PASS-SMALL.
- **Failure-mode checks.** Announcement timestamp before 09:30 of day 0 (hand-check sample), 16:00 spike, link/survivorship (CRSP incl. delisted),
  overlapping events (one per firm-day; same-day multiple names reported), year-by-year, 2x cost, median vs ex-top-5, control = all universe
  name-days with gap <= 0 (unconditional), event minus control.
- DSR computed at N 987. Runner `research/sim/upg_pocket.py` -> `data/research/program/upg_pocket_out.txt`.
Program N = 987.

### Result — UPG-POCKET (2026-10-14, one look 2020-24; N 987): KILL, 2/7 gate items
`upg_pocket.py`, out `upg_pocket_out.txt:36-60`. PRIMARY gap <= 0: n 1,496 (0.50 of days): net 2bp/side **-3.7bp** (t -0.35), 4bp/side -7.7; median +7.2,
ex-top-5 -8.6; halves 2020-22 -8.2 / 2023-24 +6.1; years -4.8/-12.7/-9.7/+20.2/-9.4. Equals unconditional gap<=0 name-days (-3.8bp): event minus control +0.1bp
(day-level +1.3bp t 0.17). All upgrades 2020-24: +4.3bp net (t 0.71). SECONDARY adv >= $1B (report only): n 707, +16.0bp (t 1.13), 4bp/side +12.0; its gap<=0
overlap n 178 +2.0. Ceiling -1.5pp/yr after tax. Read: the 2015-19 pocket was mined noise; UPG family closed.
Program N = 987.

## Amendment — Study GOLD-IFVG: Reddit "first 15m IFVG in the Asia session, gold, 1:1" (pre-register; program N 987 -> 988)
`date`: Wed Oct 14 2026, before any GC bar is read. Source: r/Daytrading "First 10k month" (claims 75% WR this month, ~65% normal, 1:1 RR,
BE at 68% of TP). Not a structural mechanism; tested because the claim is specific and the data costs $0.47. Prior: random-walk 1:1 with a BE
move at 0.68R gives win 40.5% / BE 19% / loss 40.5%, expectancy 0.
- **Data.** Databento GLBX.MDP3 ohlcv-1m GC.v.0 (continuous front, calendar roll), 2016-01-01..2025-12-31; 15m bars built from 1m (ET clock,
  bars on :00/:15/:30/:45). Sessions with a roll jump inside the window dropped. Plus Yahoo GC=F 15m last 60d (2026-08..10) as a direct check of
  the claimed month (report only).
- **Rule (frozen).** Asia window = 19:00-03:00 ET (America/New_York). FVG at 15m bar i: bull if high[i-2] < low[i], bear if low[i-2] > high[i],
  i inside the window. Inversion at a later bar j (j - i <= 16, j in window): a bull FVG closed below high[i-2] -> SHORT at close[j]; a bear FVG
  closed above low[i-2] -> LONG at close[j]. Take only the FIRST inversion of the session. Stop: S1 = the gap's far edge (short: low[i]; long:
  high[i]); S2 = extreme of bars i-2..j (short: max high; long: min low). PRIMARY = S2 (S1 report only). Skip if risk < 0.5 $/oz. TP = entry +/- 1R;
  once price reaches 0.68R move stop to entry. Path on 1m bars; stop-first when a 1m bar touches both. Unfilled at 12:00 ET -> exit at the 12:00
  close. Cost 0.20 $/oz RT (1x, ~2 ticks), 0.40 (2x).
- **Placebo.** Same entry time and stop distance, direction from a fixed-seed coin flip (200 draws -> distribution of mean R).
- **Gate (PASS), all required, PRIMARY.** Mean net R > 0 at 1x with day-clustered t >= 2; both halves (2016-20 / 2021-25) > 0; still > 0 at 2x;
  win rate (TP hits / trades) >= 50% AND mean above the placebo 95th pct; n >= 300. Else KILL. Reddit claim test (report): win rate near 65-75%.
- **Ceiling (report).** Futures = taxable only. MGC (10 oz) whole-contract risk; trades/yr x net R x risk per trade (1% of account, rounded to
  whole MGC; if one MGC's risk > 2% of account, the account cannot trade it) at $2.3k / $10k / $25k.
- Runner `research/sim/gold_ifvg.py` -> `data/research/program/gold_ifvg_out.txt`.
Program N = 988.
- **Deviation (2026-10-14, before any valid result).** GC.c.0 (calendar front) is a thin serial month for most of the year (~2 1m bars/hour,
  15m sessions median 3 bars): that run is VOID as a data bug and its numbers are not a verdict. The registered data line now reads GC.v.0
  (volume front). The 2016-25 GC.v.0 pull costs $12.73 (Databento) and waits on the user's OK (data-buy rule). Yahoo 60d check (report only):
  S2 n 46, TP 22 / SL 15 / BE 8, gross +0.16R; Oct 2026 n 10, TP 4 / SL 4 (50%, vs the claimed 75%).
Program N = 988 (study open, judge not run).

### Result — GOLD-IFVG (2026-10-15; N 988): CLOSED UNJUDGED, treated as dead (user: do not buy the $12.73 GC.v.0 pull)
The registered 2016-25 judge was never run (data not bought); this is NOT a gate verdict. Evidence on file: Yahoo GC=F 15m 60d (report only)
S2 n 46, TP 22 / SL 15 / BE 8, gross +0.16R (t ~1.3); the claimed month Oct 2026 n 10, TP 4 / SL 4 (50% vs claimed 75%). Outside systematic tests
agree: r/algotrading 1x2owmo (SMC/FVG on 4H, 477 stocks 2023-26: win rate = random entries with the same stop/target, 3.8-16.5bp/trade worse) and
1qvovpv (order blocks, 30 futures incl. GC, 1m-1d: negative almost everywhere). The 1:1 + BE-at-0.68R win rate is a stop/target geometry property
(random walk 40.5/19/40.5), not a setup property. Do not reopen ICT/SMC/FVG/IFVG/order-block patterns on any instrument without a stated mechanism.
Program N = 988.

## Amendment — Study VOLDAY: standard day-trading alerts on a point-in-time volatile-liquid watchlist (pre-register; program N 988 -> 993)
`date`: Thu Oct 15 2026, before any minute bar is read. User request: day trade especially volatile stocks, hybrid automatic + alert.
What is NEW vs the day-trading lab (Lab-AS gap/VWAP, Lab-AU ORB on stocks-in-play, halts, scalp loop): the UNIVERSE (liquid high-vol names whose
spread is small relative to the range, picked point-in-time, not gappers) and a same-geometry random-entry placebo on every arm.
- **Watchlist (frozen).** On the last session of each month, from Sharadar SEP (delisted included), Domestic Common Stock, closeunadj >= $10,
  20d median $vol (closeunadj x volume) >= $500M, rank by 20d realized vol of closeadj returns; the top 10 trade the next month. 2016-01..2026-09.
- **Data.** Alpaca SIP 1m bars, adjustment raw, 09:30-16:00 ET (signals.regular_clock / RTH only). Name-days with < 300 bars dropped.
- **Arms (5, all frozen, one trade per arm per name-day, exit by 15:55 at the latest, path on 1m bars, stop-first on a bar touching both):**
  A1 ORB15: 15m opening range; first 1m close beyond it 09:45-11:00 -> trade that side; stop = opposite side of the range; target 2R.
  A2 VWAP-RECLAIM (long): before 11:00 price trades >= 1% below session VWAP, then the first 1m close back above VWAP -> long; stop = session low so far; target 2R.
  A3 HOD-BREAK (long): 11:00-15:00, first 1m close above the prior high of day with that minute's volume >= 2x the session's mean 1m volume so far;
     stop = low of the last 15 bars; target 2R.
  A4 FLUSH-REVERSAL (long): at 10:30, if price <= open x 0.985 and (price - low)/(high - low) of the session so far < 0.15 -> long; stop = session low
     so far - 0.25 x (high - low); hold to 15:55 (no target).
  A5 GAP-FADE (short): gap (open / prior RTH close - 1) >= +3% and the first 5m bar closes below its open -> short at 09:35 close; stop = session high
     so far; target = prior close (gap fill) else 15:55.
- **Placebo.** Per arm: same name-day, same entry time, same stop distance and target rule, direction from a fixed-seed coin flip (A4 and A5
  flip the side), 200 draws. Also the arm minus the same-name-day open->close drift (A4, A5) reported.
- **Costs.** 5bp/side (1x) and 10bp/side (2x) on notional; R = return / stop distance; mean reported in bp of notional and in R.
- **Gate (per arm, PASS needs all):** mean net at 1x > 0 with day-clustered t >= 2; > 0 at 2x; halves 2016-20 / 2021-26 both > 0; median > 0 or (hit
  rate x avg win) > (miss x avg loss) stated; ex-top-5 > 0; real gross mean above the placebo 95th pct; n >= 300. DSR at N 993.
- **Ceiling (report).** trades/yr x net bp x 100% of account per trade (one at a time, whole shares) x 50% capture at $2.3k / $10k / $25k, taxable
  (shorts margin only; post-2026-06 intraday margin rules, no PDT count). Deployment gate +8pp/yr at $10k.
- **Human layer.** Not backtestable. A PASS arm (or, failing that, the best arm as a control) becomes a forward alert + decision journal:
  every alert logged, the human marks TAKE/SKIP within 2 minutes, outcomes scored for TAKEN vs SKIPPED vs ALL vs placebo.
- Runner `research/sim/volday.py` -> `data/research/program/volday_out.txt`.
Program N = 993.
- **Deviation (fetch, before any outcome).** Sharadar suffixes reused delisted tickers (APC1); the fetcher queries the base symbol (APC resolves to
  Anadarko 2019 on Alpaca) and maps it back. Coverage 1,285 / 1,290 name-months (missing UAA 2016-02, TFCFA, SAVEQ, PSKY, WBD 2021-04).

### Result — VOLDAY (2026-10-15, one look 2016-01..2026-09; N 993): KILL, all 5 arms
`volday.py`, out `volday_out.txt`. 26,244 name-days, 46,007 trades. Net at 5bp/side (1x):
A1 ORB15 n 23,430 gross +4.1bp, net -5.9 (t -2.54), median -30.9, halves -5.6/-6.1, placebo pct 92%;
A2 VWAP-RECLAIM n 12,639 gross -1.8, net -11.8 (t -2.84), placebo pct 7%;
A3 HOD-BREAK n 5,906 gross +4.8, net -5.2 (t -5.49), halves -3.5/-6.7, placebo pct 94%;
A4 FLUSH-REVERSAL n 2,940 gross -5.3, net -15.3 (t -1.28), placebo pct 22%;
A5 GAP-FADE n 1,092 gross +5.2, net -4.8 (t -0.75), halves +21.0/-14.8, placebo pct 68%.
Read: the breakout arms (ORB, HOD) carry a real but tiny continuation (~+2-3bp over same-geometry random entries, below the 95th pct) that a 10bp
round trip eats 2-3x over; win rates 35-44% at 2R targets are the stop/target geometry. The (open->close minus) column for A4/A5 is report-only and
conditioned on the trigger, not informative. Ceiling negative at every size. Volatile liquid names do not rescue retail day-trading alert setups;
with Lab-AS/AU/halts and the scalp loop this closes the class. Human layer: no PASS arm, so no forward journal is built by default.
Program N = 993.

## Amendment — Study INPLAY: in-play scanner (RVOL + catalyst + two-way liquidity + levels) x 3 trade styles (pre-register; N 993 -> 996)
`date`: Thu Oct 15 2026, before any minute bar is read. User follow-up to VOLDAY: not one-way volatile names but liquid, high-volume, two-way
"stocks in play", cherry-picked; styles = fade extremes, ride volume bursts, and a mix where the bot states the direction.
- **Universe / scanner (all ex-ante).** Sharadar SEP Domestic Common, prior close >= $10, ADV20 $ (closeunadj x volume, through d-1) >= $200M.
  POOL-G (catalyst proxy): top 25 by |gap| = |open_d / close_{d-1} - 1| (adjusted, both known at 09:30), |gap| >= 1%.
  POOL-C (two-way chop): among ADV20 >= $500M not in POOL-G, top 10 by twoway20 x range20, twoway = 1 - |close-open|/(high-low), range = (high-low)/close,
  20-day means through d-1. Window 2019-01-02..2026-09-30. Alpaca SIP 1m raw, RTH; SPY 1m for the market term.
  At 10:00 a name is IN PLAY if RVOL30 = $vol(09:30-10:00) / ADV20$ >= 0.30 (normal ~0.12-0.15, i.e. >= ~2x). Only IN-PLAY name-days trade.
  Name-days with < 300 bars dropped. Leakage check: none (no full-day field used).
- **Styles (entries 10:00-15:30, one trade per style per name-day, flat by 15:55, stop-first on a 1m bar touching both):**
  S1 FADE: dev = close - VWAP; sd = std of dev over the session so far (>= 30 bars). When |dev| >= 2 sd and the next bar closes back inside 2 sd,
     enter against the deviation at that close; target VWAP (at entry); stop = session extreme on that side + 0.25 x |entry - VWAP|.
  S2 BURST: levels = prior-day RTH high/low (Sharadar adjusted high/low x closeunadj/close of d-1) and the 09:30-10:00 range high/low. First 1m close
     through a level with bar volume >= 3x the session mean 1m volume -> trade the break side; stop = the breakout bar's opposite extreme; target 2R;
     time exit 30 min.
  S3 MIX (bot direction): event = first 1m bar after 10:00 that touches any level above or VWAP. Direction score D = sign(c - VWAP) + sign(c - open)
     + sign(SPY c - SPY open) + sign(gap). Trade sign(D) if |D| >= 2 (else no trade); stop = 1.5 x mean 1m range of the last 30 bars x sqrt(15)... frozen as
     stop distance = 1.5 x ATR15, ATR15 = mean(high-low) of the last 15 bars x sqrt(15); target 1.5R; time exit 60 min.
- **Placebo.** Per style: same name-day, entry bar, stop distance and target rule, coin-flip direction, 200 draws. S3 also: the opposite of the bot
  direction (direction value = S3 minus its mirror / 2).
- **Costs.** 5bp/side (1x), 10bp/side (2x). Halves 2019-22 / 2023-26.
- **Gate (per style, PASS needs all):** mean net 1x > 0, day-clustered t >= 2; > 0 at 2x; both halves > 0; ex-top-5 > 0; median > 0 or stated payoff
  asymmetry; real gross above the placebo 95th pct; n >= 300. DSR at N 996.
- **Cherry-pick diagnostics (report only, no gate):** each style by RVOL30 tercile, by pool (G/C), by level type (S2/S3), by |D| (S3), by gap sign.
  A monotone, both-halves improvement is a hypothesis for a forward test, never a pass.
- **Ceiling.** trades/yr x net x 100% x 50% capture at $10k (+8pp gate). Forward human TAKE/SKIP journal is built only for a PASS style.
- Runner `research/sim/inplay.py` -> `data/research/program/inplay_out.txt`.
Program N = 996.
- **Deviation (before any minute bar or outcome).** POOL-C as registered (twoway20 x range20) selected one-way high-vol names (AAOI, CIFR, IONQ...),
  which the user excluded. Frozen replacement: among ADV20 >= $1B with range20 >= 2%, not in POOL-G, top 10 by twoway20.

### Study ROTH-COMBO (pre-register 2026-10-15, before the runner exists; N 996 -> 997)
Question (portfolio construction, no new signal): on a cash Roth, does adding a CEF-RV sleeve and a Treasury month-end (TME) sleeve to the
ROTH-STACK book (AL1 IBS .5 + night .5, PREF+ETDX CO on the book's idle cash, STRICT night-first) raise total %/yr once the three compete for
the same cash? Every component is judged elsewhere (CEF-RV/CEF-PEER, TME 2002-15, ROTH-STACK); this run is arithmetic on touched data.
Ceiling (before running): CEF-RV ~+3.8%/trade raw over ~13 weeks, ~-0.5% cost -> ~+13%/yr on the sleeve's deployed cash, but its alternative
is the book (~10-20%/yr on the same cash in 2021-26), so the increment from a carve-out may be ~0 or negative; TME +32bp x 12 = ~3.8%/yr on
its sleeve for 3 sessions/month, displacing the book for those sessions. Prior: increment small (< +2pp) unless the book leaves the carved
cash idle most days.
Rule: days = ROTH-STACK book days (2021-02-01..2026-09-18). Each day the book runs `roth_stack.book_day` on E_book = E x (1 - f - g_d) and PREF
takes `alloc(free)` exactly as ROTH-STACK STRICT night-first. CEF sleeve = f x E, 8 equal slots; CEF-RV trades from `cef_rv_trades.csv`
(frozen rule; entry = first SFP close after the signal week, exit = first close after the exit-signal week), new signals of a week ranked by
disc_in - med ascending, fill free slots, whole shares at the raw entry close, marked daily on SFP closeadj, 25bp per side; empty slots earn
BIL. TME sleeve: on the book days whose close is T-3, T-2, T-1 of each month (T = last TLT trading day), g_d = g, and g x E is held in TLT
close(T-3) -> close(T) (Yahoo adjclose), 1bp per side. Configs: f in {0, .25, .5} x g in {0, .5}; PRIMARY = f .25, g .5; baseline = f 0, g 0.
Sizes $3k / $10k / $25k fixed equity. Metrics per config: total %/yr, increment vs baseline (pp/yr), halves 2021-23 / 2024-26, 3x cost (PREF
30bp RT, CEF 150bp RT, TME 6bp RT), maxDD of the daily total, NW t of the daily increment; per sleeve: CEF trades taken, mean net, hit.
Gate (PASS, PRIMARY at $10k): increment >= +2pp/yr, both halves > 0, increment > 0 at 3x cost, NW t >= 2. Kill: increment <= 0 at $10k or
negative in a half. A non-primary config that beats PRIMARY is a hypothesis for the forward gates, never a pass. Survivorship: the CEF panel
is live funds only (2016-26 benign-death era, CEF-SURV99); stated, not corrected. One run, no tuning.
Runner research/sim/roth_combo.py -> data/research/program/roth_combo_out.txt. Program N = 997.

#### Result — ROTH-COMBO (judged 2026-10-15, one run; N 997): KILL
Runner research/sim/roth_combo.py -> data/research/program/roth_combo_out.txt (run under pandas 3: the night/sim caches are pandas-3 pickles,
.venv has pandas 2.2.3 since 10-12). Baseline (book + PREF) +21.8 / +19.3 / +17.9 %/yr at $3k / $10k / $25k. PRIMARY (f .25, g .5) increment
-3.0 / -0.8 / -0.1pp, both halves negative at $10k, NW t -0.33. Every config is <= +0.5pp at every size. The CEF sleeve itself is fine (187 trades,
+426bp net, hit 78%, ~17.6%/yr on its cash) and TME adds +1.2pp on its sleeve, but each only matches what the same cash earns in the book in
2021-26, so carving cash out of the book buys nothing. Side effect, not a pass: f .25 cuts maxDD (-13.5% -> -10.2% at $10k). Caveat: the
comparison prices the book at its in-window 2021-26 return (~19%/yr), above the ~8-15% forward estimate; if the book delivers only that,
a CEF sleeve would add. That is a forward question (CEF-RV-FWD gate), not this study's. Do not re-run sleeve weights.

### Result — INPLAY (2026-10-15, one look 2019-01..2026-09; N 996): KILL, all 3 styles
`inplay.py`, out `inplay_out.txt`. 63,050 candidate name-days, 13,186 in play (RVOL30 >= 0.30), 23,473 trades. (A first run crashed on `df.style`, the
pandas Styler, before printing anything; fixed, then the single look.) Net at 5bp/side:
S1 FADE n 12,652 gross -4.3bp, net -14.3 (t -9.0), halves -11.1/-16.9, placebo pct 4%, direction value -3.2 (fading VWAP extremes is WORSE than riding them);
S2 BURST n 1,131 gross +1.5, net -8.5 (t -2.6), halves -11.2/-6.0, placebo pct 79%;
S3 MIX (bot direction) n 9,690 gross -4.4, net -14.4 (t -4.2), halves -15.9/-13.1, placebo pct 2%, direction value -4.0 (|D| = 4, all signals agree: -6.8):
the composite direction call is mildly ANTI-predictive at level touches; its mirror (+4bp gross) is still under the 10bp round trip.
Cherry-pick diagnostics: no RVOL tercile, pool (gap vs two-way chop), level type or |D| bucket is positive in both halves (best: S3 chop pool -11.0/+2.7 n 428;
S2 PDH +6.2/-13.8). Scanner features do not separate good from bad in-play trades. Ceiling negative. No forward human journal (no PASS style).
Program N = 996.

## Study CRYPTO-TA — MACD / RSI pattern rules on the five Schwab-tradable coins (pre-register 2026-10-15, before the runner exists; N 997 -> 998, DSR at 998 + 8 rules)
User request: MACD/RSI strategies on swing + crypto. Swing side NOT re-run (window_signals_loop rounds 1-11: F3/F4/F6/F11/H6 dead in liquid
stocks/ETFs; usethinkscript harvest dead). Untested cell: oscillator patterns on crypto majors (prior crypto work = SMA trend, IBS only).
- **Data.** Binance USDT spot daily (UTC days), BTC ETH SOL AVAX LINK (Schwab Crypto list 2026-10), 2018-01-01..2026-09-30, each coin from
  its first 200 bars. Signal at the close of UTC day d, fill at the close of d (24/7 market, no gap; Schwab trades 24/7). Long only.
- **Rules (frozen, long-only, indicators on closes, standard parameters; lookback patterns per lesson L1):**
  R1 RSI(14) crosses back above 30 after >= 3 days below; exit RSI(14) >= 50 or 20 days.
  R2 RSI(2) < 10 with close > SMA200; exit close > SMA5 or 10 days.
  R3 MACD(12,26,9) line crosses above signal while MACD < 0; exit at the cross back down.
  R4 MACD histogram turns > 0 after >= 5 bars < 0; hold 10 days.
  R5 MACD zero-line cross up; exit at the zero-line cross down (trend).
  R6 RSI(14) bullish divergence: low_d < min(low d-20..d-5), RSI_d > RSI at that prior low, RSI_d < 40; hold 10 days.
  R7 RSI(14) crosses above 70 (momentum); exit RSI(14) < 50 or 20 days.
  R8 regime: in when MACD > 0 AND close > SMA200, out otherwise (time-in-market).
- **Benchmark.** Exposure-matched: trade return minus the coin's own mean daily log return x days held (full-sample drift of that coin);
  plus whole-period CAGR / Sharpe / maxDD vs buy-and-hold of an equal-weight basket of the coins (rule capital split equally per coin,
  cash 0% when out).
- **Costs.** Schwab 75bp/side (150bp RT) = judge; 2x shock 300bp RT; report 25bp/side (Coinbase/IBIT-like) as information only.
- **Gate (per rule, trades pooled across coins, date-clustered t).** PASS needs ALL: mean excess net of 150bp > 0 with t >= 2.0; halves
  2018-22 / 2023-26 both > 0; median excess net > 0; ex-top-5 trades > 0; survives 300bp RT. For R5/R8 (time-in-market) instead: Sharpe net
  >= B&H Sharpe + 0.2 in BOTH halves and maxDD better than B&H. DSR reported at N 998 + 8. Any PASS -> forward shadow only; no live order.
- **Kill rule.** No rule passes -> MACD/RSI on crypto majors CLOSED at Schwab cost; record in NEXT do-not-redo.
- Runner `research/sim/crypto_ta.py` -> `data/research/program/crypto_ta_out.txt`.
Program N = 998.
- **RESULT (2026-10-15): no usable rule; R7 = WEAK (passed the registered gate, failed the adversarial checks).** EW B&H basket CAGR +32.7%,
  Sharpe 0.76, maxDD -85%. Net of 150bp RT: R1 -120bp t -0.01, R2 -111 t -1.70, R3 +250 t 0.97 (median -545), R4 -76, R6 -265 t -2.08 (wrong
  sign): FAIL. R5 zero-line trend Sharpe 1.14/0.99 vs B&H 0.69/0.92 and R8 (MACD>0 & >SMA200) 1.28/0.99, maxDD -49%: FAIL (second half +0.07
  < +0.2; the gain is dodging the 2018 and 2022 bears, 2023-26 CAGR +32% vs B&H +46%). **R7 (RSI14 crosses above 70, exit <50 or 20d)**: +777bp
  mean, median +22, date-clustered t 2.50, halves +964/+606, ex-top-5 +322, 2x cost +627 -> registered PASS, book CAGR +27.9% Sh 1.01 mDD -26%.
  But the coins move together: week-clustered t 2.09, **month-clustered t 1.25**; carried by SOL/AVAX (+1641/+2266, survivor coins Schwab
  picked in 2026) and 2020-21/2023; 2024-26 ~0 with negative medians; **2022+ net +542 median -5, month t -0.06**; BTC alone +487 median +395
  t 1.95 (n 34); thresholds 60/65 dead (median -544/-593), 75/80 stronger. Placebo 100th pct (random holds +189bp gross). Read: R7 is crypto
  time-series momentum (known trend family), real gross in 2019-23 but not a robust net edge at Schwab cost, and it has not worked since 2024.
  Lesson for the gate: date-clustered t is too generous for a basket of ~0.8-correlated coins; cluster by month.

## Study CRYPTO-TA12 — the CRYPTO-TA rules on 12-hour bars (pre-register 2026-10-15, before any 12h data is read; N 998 -> 999)
User follow-up: "fails on a daily scale, how about half day". Same five coins, same 8 rules with the SAME parameters in BARS (RSI 14/2, MACD
12/26/9, SMA200/5, hold caps 10/20 bars = 5/10 days), on Binance spot 12h klines (UTC 00-12, 12-24), 2018-01-01..2026-09-30, signal and fill
at the bar close (Schwab trades 24/7). Same exposure-matched excess, costs (judge 150bp RT, shock 300bp, info 50bp).
- Gate: as CRYPTO-TA, but the t-stat is **clustered by calendar month** (lesson from CRYPTO-TA: coin entries in the same weeks are one bet),
  and a PASS also needs the 2023-26 half > 0 with month t computed on 2022+ >= 1.0. Regime rules (R5/R8): Sharpe (annualised x sqrt(730))
  >= B&H + 0.2 in both halves and better maxDD. Prior: worse than daily (twice the turnover at 150bp RT); the daily R7 is NOT re-judged here.
- Runner `research/sim/crypto_ta12.py` -> `data/research/program/crypto_ta12_out.txt`; data `data/research/crypto_spot/raw12h/`.
- **Amendment (2026-10-15, before any intraday bar was read; user: "or quarter day / or third / etc"):** run the identical design on 12h, 8h,
  6h and 4h bars (four timeframes, each its own judged family; N 998 -> 1002). Hold caps stay in BARS (so 4h caps = 40/80h). Annualise Sharpe by
  bars/yr. Data `data/research/crypto_spot/raw{12h,8h,6h,4h}/`. Report every timeframe; no picking the best one after the fact.
Program N = 1002.
- **RESULT CRYPTO-TA12 (2026-10-15): KILL, 0 of 32 cells pass (8 rules x 12h/8h/6h/4h).** Results get worse as bars get shorter. Oversold / MACD-
  cross / divergence rules are negative net at every timeframe (RSI2 month t -3.5 -> -8.9 from 12h to 4h). R7 RSI>70 net mean +534/+239/+168/+24bp
  with NEGATIVE medians (-159..-245) and 2022+ month t <= 0 at every timeframe. Trend filters R5/R8 2023-26 CAGR +19/+16/+10/-16% net vs B&H +46%;
  even at 25bp/side (info) their 2023-26 Sharpe is 0.47-1.11 vs B&H 0.91-0.92: all of the gain came from dodging the 2018 and 2022 crashes.
  (B&H differs from daily only because the 200-bar warm-up is shorter in calendar time.) Out `crypto_ta12_out.txt`.
  Class verdict: MACD/RSI on crypto majors is CLOSED at every bar size from 4h to 1d at Schwab cost and, for 2022+, even at 25bp/side.

## Study IND-SWING — 38 swing indicators, extreme "confident" tails + combos + an ML composite, 2-30 day holds (pre-register 2026-10-15, before the runner exists; N 1002 -> 1003, DSR at 1002 + all trials)
User request: test a pasted list of 65 indicators (volatility, volume, statistical, options, microstructure, positioning) "for very confident
picks at a high interval". Not read: any outcome of any rule below. Runner `research/sim/ind_swing.py` -> `data/research/program/ind_swing_out.txt`.
- **Data.** Sharadar SEP, domestic common stock, delisted included; load 2002-01..2026-10 (warm-up). Universe per day: raw close >= $5, 20d median
  $vol >= $5M. Returns from adjusted prices (adjusted open = open*closeadj/close). Signals at close t on every 5th trading day (weekly);
  entry open t+1, exit open t+1+h, **h in {2, 5, 10, 20, 30}**; non-overlapping (h > 5 uses every ceil(h/5)-th signal date).
- **Features (40 — 13 vol + 14 volume + 13 stat, count corrected before any run; daily-bar computable; cross-sectional percentile among eligible names).** Volatility: VCP (range5/range20 x range20/range60),
  TTM squeeze ratio (BB20 width / KC20 width), TTM squeeze days-on, HVP (vol20 percentile in own 252d), Parkinson / Garman-Klass /
  Rogers-Satchell / Yang-Zhang 20d each / own 252d level, Choppiness 14, Ulcer 14, FDI 30 (Sevcik), Hurst (variance-ratio proxy, 120d), Donchian
  20 width / close. Volume: CMF 20, Klinger (34/55), NVI and PVI vs own 255-EMA, EMV 14, VPT 20d change / avg vol, Twiggs MF 21, Elder force 13
  / $ADV, close vs rolling 50d VWAP, close vs VWAP anchored at the 252d-high date, pocket pivot flag (up day, vol > max down-day vol of prior
  10, close > 10d and 50d SMA), VDU (vol5/vol50), up/down volume ratio 50d, RVOL (vol/avg20). Statistical: OU half-life (AR1 of log price
  minus 20d mean, 60d), variance ratio VR(5) 120d, z of 5d return vs own 252d, residual momentum (12-1 vs EW-universe beta), idio vol 60d,
  trend t-stat (60d log-price regression; Kalman stand-in), CUSUM break (mean ret 20d minus 120d, / vol), sign entropy 20d, permutation entropy
  (order 3, 60d), beta instability (beta60 - beta250), lag-1 autocorr 60d, Amihud 20d, Roll spread 60d.
- **Not run (reason stated, not tested here):** HMM regimes (#32; market-regime gates dead, NOISE-GATE/regime rows); cointegration pairs (#37;
  ETF pairs dead); volume profile HVN/LVN (#22; needs intraday volume-at-price); options #39-50 (LUCK-B4 tested IV/skew/PC on OptionMetrics,
  OI-pin killed, signed gamma ceiling < 4pp); microstructure #51-53, 55, 57-59 (minute/book scale; scalp loop 7 studies dead); short interest
  #61-62 (LUCK-B4); borrow #63-64 (no data); PEAD #65 (effect in the announcement gap).
- **Rules (long-only).** (a) TAILS: each feature's top 2% and bottom 2% of the cross-section (pocket pivot: flag = 1 only) x 5 horizons.
  (b) COMBOS, frozen: C1 user's combo = ret120 pct >= 0.8 & VDU of the prior 10 sessions (vol10[t-1]/vol50) pct <= 0.2 & today RVOL >= 2 & up
  day; C2 VCP pct <= 0.1 & pocket pivot; C3 TTM squeeze on >= 5 of the prior 6 days & off today & close > 20d high; C4 Donchian width pct
  <= 0.1 & close > prior 20d high & RVOL >= 1.5; C5 CMF pct >= 0.9 & up/down vol pct >= 0.9 & ret120 pct >= 0.8. x 5 horizons.
  (c) ML: sklearn HistGradientBoosting on all 38 percentiles, target = 10d excess-return percentile, trained on the prior 5 years of weekly
  rows ending 30 sessions before each test year (retrained yearly), long the top 1% predicted names, x 5 horizons.
  Min 3 names on a signal date, >= 30 dates.
- **Score.** Per signal date: EW selected minus EW eligible-universe return (same window), minus 20bp round trip. Raw (not excess) reported.
- **Discovery 2004-01..2014-12 (ML: 2009-14).** Pass = net mean > 0, t >= 3, both halves (2004-09, 2010-14) > 0, median > 0.
  **Null:** 5 permutations of every feature across names within date, tails only; the tail batch counts only if real passes > max null and
  > 3 x mean null. Otherwise LUCK.
- **Judge 2015-01..2026-09, one look** for every discovery pass (and every combo/ML cell regardless): net > 0, t >= 2, median > 0,
  ex-top-5-dates > 0, both halves (2015-20, 2021-26) > 0. Robust only if also > 0 at 3x cost (60bp RT). DSR at the full trial count.
  Family flags: momentum, ST reversal, vol/size/liquidity tilt (known; a pass that is only one of these is not new).
- **Kill:** no judged cell passes -> the indicator list is closed at the daily tier. No retuning of tails, windows or horizons after reading.
Program N = 1003.
- **Amendment IND-SWING-PAIRS (2026-10-15, user: "combinations of strategies change the outcome"; written while the main run was scoring, before
  any IND-SWING outcome was read; N 1003 -> 1004).** Every PAIR of the 40 features: intersection of decile tails (each feature top 10% or bottom
  10%; pocket = flag), 4 sign pairs x 780 pairs x 5 horizons (~15.6k cells), same universe, score, discovery/judge windows and gates as the
  tails. Triples are NOT enumerated (~400k cells; the ML composite is the interaction test). **Null:** 3 replicates in which each date's
  forward returns are shuffled across eligible names (keeps every feature's joint structure, breaks only the link to returns); the pair batch
  counts only if real discovery passes > max null and > 3 x mean null. Judged pairs must also not be a single known family (momentum, ST
  reversal, vol/size tilt) by inspection. Runner `research/sim/ind_pairs.py` -> `data/research/program/ind_pairs_out.txt`.
Program N = 1004.
- **RESULT IND-SWING + PAIRS (2026-10-15): KILL, LUCK.** Tails: 0/395 discovery passes (max discovery t 0.92), random same-size null 0 x5. Combos C1-C5
  negative in both windows (user's RS + dry-up + volume expansion -63..-183bp/trade net vs universe 2015-26; TTM fire -14..-55). ML top 1%: -21..+5bp,
  t <= 0.2 at its best horizons. Pairs: 0/15,210 discovery passes vs shuffled-return null 1/1/2. Positive "raw" returns are market drift. Outputs
  `ind_swing_out.txt`, `ind_pairs_out.txt`. **2015-26 is now TOUCHED for the daily-indicator family.** Class closed: OHLCV indicators (vol/volume/stat)
  and their pairwise combinations carry no cross-sectional selection edge at 2-30 day holds for $5+/$5M names.

## Study CUST-MOM — customer-supplier momentum (Cohen-Frazzini 2008), long-only, post-publication (pre-register 2026-10-15, before any customer/return data is pulled; N 1004 -> 1005)
User-forwarded advice ("customer-supplier momentum"); the only item of that list not already in NEXT/prose. Mechanism: investors under-react to news about a
supplier's major customer (limited attention to economic links); named, persistent information friction. **Ceiling (pre-test, stated):** CF long-short
~1.2-1.5%/mo 1981-2004; long-only top quintile plausibly +0.5-1.0%/mo excess -> ~3-6pp/yr at 50% capture: BELOW the +8pp gate. Run as a one-look
kill test at the user's explicit request (WRDS login approved for it); a pass would still need the gate argued with measured numbers.
- **Data.** WRDS `compseg.wrds_seg_customer` (ctype COMPANY, salecs) -> customer name matched to Compustat/CRSP firm names (normalized: upper case,
  punctuation and legal suffixes INC/CORP/CO/LTD/LLC/PLC/HOLDINGS/GROUP/THE stripped; exact match on the normalized name, else unique-prefix match
  with >= 8 chars; drop generic names: "NOT REPORTED", "\d+ CUSTOMERS", "GOVERNMENT", "DISTRIBUTOR", etc.). Supplier and customer gvkey -> CRSP permno
  via CCM (LU/LC, primary). Link usable from srcdate + 6 months to srcdate + 18 months (point-in-time; the next filing replaces it). CRSP monthly
  returns incl. delisting returns, common shares (shrcd 10/11), NYSE/AMEX/Nasdaq.
- **Signal.** Month m: customer return of supplier s = sales-weighted (salecs; EW if missing) month-m return of its linked customers. Suppliers with price
  >= $5 and market cap >= $50M at end of m are sorted into quintiles; **long Q5 (best customer returns), EW, hold month m+1, skipping m+1's first trading
  day** (the signal uses m's last close; entry is the close of day 1 of m+1; return = (1+ret_m+1)/(1+ret_day1) - 1).
- **Benchmarks.** (B1) EW all CRSP names passing the same price/cap filter; (B2) EW same-SIC2 peers passing the filter (industry-adjusted);
  also Q5 - Q1 (diagnostic). Cost 30bp round trip per month (full turnover assumed), shock 90bp.
- **Judge = 2005-01..2026-latest (post-publication, never read by this repo), ONE look.** Pass: B1 excess net mean > 0, t >= 2, median > 0,
  ex-top-5-months > 0, both halves (2005-15, 2016-26) > 0, AND B2 excess > 0 with t >= 2. Replication 1981-2004 reported only as a data check
  (expect positive; if not, the matching is broken and the judge is void, not a fail). Runner `research/sim/cust_mom.py` ->
  `data/research/program/cust_mom_out.txt`; caches `data/research/wrds_cust/`.
- **Kill:** any judge gate fails -> customer-supplier momentum closed at retail long-only; no re-tuning of quintile, lag, filters or weights.
Program N = 1005.
- **RESULT CUST-MOM (2026-10-15): KILL.** Replication 1981-2004 reproduces Cohen-Frazzini (Q5-Q1 gross +1.13%/mo, t 3.95): matching works. Judge
  2005-2024 (CRSP ends 2024-12): long Q5 vs EW universe net 30bp -0.29%/mo (t -2.23), vs SIC2 peers -0.32 (t -3.57); halves -0.08 / -0.54; even the
  gross long-short decays +0.49 (2005-15, t 2.3) -> 0.00 (2016-24). Published anomaly arbitraged after 2008; long-only side never paid net. Closed.
## Study BORROW-XS — option-implied borrow-rate cross-section (pre-register 2026-10-16, before any borrate value is read; N 1005 -> 1006, DSR at 1006)
New WRDS data unlocks the implied borrow rate (`optionm.borrateYYYY`, 1996-2025), which the program has never read.
Mechanism: short-sale constraints (Miller 1977) — a high borrow fee is a *binding* constraint, so hard-to-short names are
overpriced and underperform. Named counterparty = short sellers. **Ceiling (pre-test, stated):** literature fee-sorted
extreme-decile LS is ~0.5-1.0%/mo gross, mostly microcap and decaying post-2008; the LS side is NOT deployable for this
account (Roth cannot short; the high-fee leg pays its own fee), so the only deployable form is a long-only avoidance/low-fee
tilt, plausibly +1-2pp/yr. Run as a **one-look kill test**; a pass earns at most a forward shadow, never a size-up.
- **Data.** `optionm.borrateYYYY` 1996-2025; one rate per (securityid, month) = the LAST valid daily row in the month with
  tenor nearest 30d (`borrowrate > -99`; sentinel is exactly -99.99). `securityid` -> CRSP `permno` via
  `wrdsapps_link_crsp_optionm.opcrsphist` (score=1, overlap join on `sdate <= obsdate <= edate`). CRSP monthly `crsp.msf`
  (`ret`,`prc`,`shrout`,`hexcd`) for common shares (`crsp.dsenames` shrcd in (10,11)); delisting returns from
  `crsp.dsedelist.dlret` applied in the delisting month when `msf` has no row.
- **Signal (formation = end of month m, hold month m+1).** Arm A (level): cross-sectional deciles of the borrow rate in m;
  Arm B (change): deciles of borrowrate(m) - borrowrate(m-3). Portfolios EW within decile: LS = D1 - D10 (low-fee minus
  high-fee, expected > 0); long-only reference = D1 excess over EW eligible universe. Universe at formation: prc >= $5,
  shrcd 10/11, non-missing borrow rate and next-month return (or a delisting return).
- **Costs.** 20bp round trip + borrow on the short leg at the *actual* implied rate (annual/12, D10 average); 2x shock.
- **Benchmark.** EW eligible universe same month. LS reported gross and net; long-only reported as excess over universe.
- **Judge = 1996-2025 (full), sub-periods 1996-2007 / 2008-2015 / 2016-2025; ONE look, no parameter selection.**
  Pass: LS gross mean > 0, month-clustered t >= 2, median > 0, ex-top-5-months > 0, >= 2 of 3 sub-periods > 0, AND LS net
  (20bp + actual borrow) > 0, AND long-only D1 excess net > 0 with t >= 2. DSR at N 1006 (2 arms).
- **Kill:** any gate fails -> borrow-rate cross-section closed at the monthly tier; no re-tuning of tenor, deciles, lag,
  price filter, or arm definitions. Runner `research/sim/borrow_xs.py` -> `data/research/program/borrow_xs_out.txt`;
  cache `data/research/borrate/`.
Program N = 1006.
- **RESULT BORROW-XS (2026-10-16, one look 1996-2025, N 1006): Arm A = PASS-statistical / NOT DEPLOYABLE; Arm B = FAIL.**
  Arm A (fee level): LS gross FULL +106.5bp/mo (month-clustered t 6.43), net of 20bp + actual borrow +84.0bp (t 5.08),
  median +89.3, ex-top-5 +91.8; sub-period gross +142.9 / +96.7 / +66.3 (all t >= 2.56); monotone decile ladder
  D1=119 ... D5=99 ... D10=13bp/mo (D1-D5 +19.7 t 2.84; D5-D10 +86.8 t 5.88). Long-only D1-EW net +22.3bp/mo (t 3.58).
  Arm B (3m change): net FULL +41.3bp t 3.69 but dead in the modern regime (2016-25 net +1.1bp t 0.05) and long-only ~0 -> FAIL.
  **Disposition:** the cross-section is real and monotone (short-sale constraints are priced), but it is not a new edge for this
  account: (i) the payoff is concentrated in the high-fee tail = the SHORT leg the account cannot take (Roth cannot short;
  the same "profitable side is unharvestable" pattern as SSR-LIFT and threshold-flow), (ii) the long-only D1 form is a
  size/low-vol/quality tilt the program already killed in the modern regime (MODERN-XS), and (iii) the effect decays
  (2016-25 net t 1.65). No live change, no size-up, no shadow. The only open follow-up is a pre-registered size/vol-neutral
  long-only test; absent that, BORROW-XS is a new-data replication of a known constraint, not a deployable strategy. Output
  `data/research/program/borrow_xs_out.txt`. 1996-2025 borrow-rate cross-section is now TOUCHED.
Program N = 1006.
## Study BORROW-XS2 — is the low-fee long-only tilt alpha, or size/vol? (pre-register 2026-10-16, before reading any bucketed outcome; N 1006 -> 1007)
Motivated by the BORROW-XS confound (D1-EW +22bp/mo net may be a size/low-vol tilt). Same panel/rule as BORROW-XS (formation
end of m, hold m+1, EW, 1996-2025, common shares $5+). Arm 1 (size): each month split eligible names into size terciles by
market cap (prc*shrout), and WITHIN each tercile decile by borrow rate; report long-only D1 - EW_within_tercile and LS D1-D10
per tercile. Arm 2 (vol): identical but terciles by trailing 24-month return volatility. Report 1996-2025 and 2016-2025.
- **Pass (resolves the confound):** long-only D1 - EW(within tercile) net of 10bp > 0 with t >= 2 in the MID and LARGE size
  terciles AND in the LOW and MID vol terciles -> the tilt is not merely size/vol and earns a forward shadow.
- **Kill:** survives only in the small/high-vol tercile -> BORROW-XS is size/vol beta; cross-section closed, no shadow.
Runner `research/sim/borrow_xs2.py` -> `data/research/program/borrow_xs2_out.txt`; reuses the BORROW-XS panel/cache.
Program N = 1007.
- **RESULT BORROW-XS2 (2026-10-16, N 1007): KILL — the long-only tilt is size/vol beta.**
  Identical panel (717,758 rows, 8,046 names). FULL 1996-2025 long-only D1 - EW(within tercile) net 10bp: SIZE small +44.5bp
  t 4.46, MID +20.6 t 2.38, LARGE +8.2 t 1.29; VOL low -0.6 t -0.11, MID +13.2 t 1.70, HIGH +57.2 t 5.33. Required {MID,LARGE}
  size and {LOW,MID} vol -> fails both -> KILL. 2016-2025: nothing clears t>=2 (best VOL HIGH +37.3bp t 1.80). The long-only
  tilt lives in exactly the small-cap and high-vol buckets — the confound is confirmed. (LS D1-D10 stays significant inside
  MID/LARGE size and MID vol, so the *level* information is not pure beta, but the deployable long-only form is.) BORROW-XS
  closed: short-sale-constraint cross-section replicated, no deployable edge. Output `data/research/program/borrow_xs2_out.txt`.
Program N = 1007.

## Study REV-TONE — does Amazon review tone predict sales / EA returns? (pre-register 2026-10-16, before any tone is computed; N 1007 -> 1008)
User request (Jin 2023 JBFA "More than words"; the "review tone called Nike's fall" anecdote). Live Amazon scraping is not
possible (review pages need sign-in; checked 2026-10-16), so the data is McAuley-Lab Amazon Reviews 2023 (HF, reviews to
2023-09, exact timestamps), streamed and filtered by `store` to 20 firms fixed here, chosen as US-listed consumer brands with a
big Amazon presence (not by outcome): NKE (Nike, Jordan, Converse), UAA, CROX, SKX, HBI (Hanes, Champion, Maidenform, Bali),
LEVI, COLM (+Sorel, Mountain Hardwear, prAna), DECK (UGG, HOKA, Teva, Sanuk), YETI, HELE (OXO, Hydro Flask, PUR), IRBT, GPRO,
SONO, LOGI (+Logitech G, Ultimate Ears, Astro, Blue Microphones), GRMN, HAS (+Nerf, Play-Doh, Hasbro Gaming), MAT (+Barbie,
Hot Wheels, Fisher-Price, Mega Bloks), ELF, NWL (Rubbermaid, Sharpie, Crock-Pot, Mr. Coffee, Coleman, Yankee Candle, Graco,
Oster, Sunbeam, Paper Mate, Expo, Elmer's, Calphalon, Contigo, FoodSaver), ENR (Energizer, Rayovac, Armor All).
- Tone: `cardiffnlp/twitter-roberta-base-sentiment-latest`, tone = p(pos) - p(neg) on title + text (256 tokens); random cap
  1,000 reviews per firm-month (seed 0). Reason tags: fixed keyword aspect lexicon (fit/size, quality/durability,
  defect/broken, comfort, price/value, shipping/packaging, fake, service, battery/connectivity/app), descriptive only.
- Firm-quarter (Sharadar SF1 ARQ fiscal quarters): TONE = mean tone of reviews dated inside the fiscal quarter; dTONE =
  TONE_q - TONE_{q-4} (seasonality-safe); controls dRATING (mean stars, same diff) and dlogN. Needs >= 100 reviews in both q, q-4.
- H1 sales: ACC_q = ln(Rev_q/Rev_{q-4}) - ln(Rev_{q-1}/Rev_{q-5}) on dTONE + dRATING + dlogN, quarter-clustered t.
- H2 market: CAR[-1,+1] vs SPY around the quarter's earnings 8-K (Sharadar EVENTS item 2.02) on the same regressors.
- H3 tradable: each fiscal-quarter end, rank firms by dTONE within the calendar quarter; hold quarter-end+1 close -> EA+1
  close, beta-adjusted vs SPY (252d beta before entry). Report bottom tercile, top - bottom, net 10bp/side, ex-top-5,
  halves, hit rate; plus the "always" check: P(next ACC < 0 / CAR < 0 / H3 return < 0 | bottom-tercile dTONE) vs base rate.
- Windows: report 2014Q1-2018Q4 (the paper's era); **judge 2019Q1-2023Q2** (after the paper's data).
- **PASS:** judge-window H1 dTONE t >= 2 (with dRATING, dlogN in) AND H3 top - bottom > 0 net, t >= 2, both judge halves > 0,
  ex-top-5 > 0. **KILL:** H3 fails (H1 alone = information that is already in the price). Ceiling note (priority gate): ~4
  rebalances/yr on 20 names needs >= ~4%/quarter spread at 50% capture to reach +8pp: run at the user's explicit request.
- Caveats fixed in advance: Nike left Amazon as a direct seller 2019-11 (later reviews are 3P listings); review deletions and
  2023 listing survivorship are unfixable; the Nike 2023-12 / 2024-06 drops fall after the data ends (descriptive only).
Runner `research/sim/rev_tone.py` -> `data/research/program/rev_tone_out.txt`; data `data/research/reviews/`.
Program N = 1008.
## Study GAMMA-MKT — index dealer-gamma exposure and next-day return/vol (pre-register 2026-10-16, before reading any gamma value; N 1007 -> 1008)
options-induced underlying flow, index-level. OPEX OI-pinning was killed (K1/K2); this is the untested signed-gamma state.
- **Data.** `optionm.opprcdYYYY` for SPY (secid 109820; confirm vs `optionm.secnmd` ticker='SPY'), 1996-2025. Daily, per
  contract: sum `open_interest * gamma * contract_size` separately for calls (CG) and puts (PG); underlying spot ~ `optionm.secprdYYYY`
  (or SPY close). Dollar-gamma per 1% = value * spot^2 * 0.01.
- **Signal (dealer proxy).** Dealers are assumed net short customer index-option demand: net dealer gamma
  `DG = PG - CG` (short call gamma + long put gamma). Standardize DG by its trailing 252d mean/MAD. Also report the raw
  put/call gamma ratio.
- **Mechanism / pre-signed predictions.** Negative DG (dealers short gamma) -> hedging AMPLIFIES moves: next-day realized vol
  HIGHER, and returns trend (today's sign persists). Positive DG -> hedging DAMPENS: vol LOWER, returns mean-revert.
  Arms: (V) next-day realized vol |ret|/range ~ DG, expect negative slope; (M) 5-day return ~ DG x sign(today's ret),
  expect positive slope on DG*sign (i.e. short-gamma trends).
- **Judge = 1996-2025, halves 1996-2010 / 2011-2025; ONE look, no tuning.** Pass: pre-signed slope with day-clustered
  t >= 2 in BOTH halves and ex-top-5 intact (cost 2bp round trip on the directional arm). Kill: fail -> index gamma/pinning
  family closed for this account. Runner `research/sim/gamma_mkt.py` -> `data/research/program/gamma_mkt_out.txt`.
Program N = 1008.

## Study SKEW-MKT — index option skew / term structure and forward returns (pre-register 2026-10-16, before reading any vsurf value; N 1008 -> 1009)
The vol-surface row was "UNEXPLORED"; vsurf is now free. Lab-CC used the Cboe SKEW *index* (z->20d -30/-110bp); this is the
purer per-delta surface. Distinct dataset, same economic family -> run as a kill test.
- **Data.** `optionm.vsurfdYYYY` for SPY, sigma=30, delta ladder -90..+90. Risk reversal `RR30 = IV(delta=+25) - IV(delta=-25)`
  (call minus put; negative = puts bid = fear). Term slope `TS = IV(30d, delta~ -10) - IV(180d, delta~ -10)`.
- **Pre-signed prediction.** Low/negative RR30 (expensive puts, fear) -> LOWER forward 5d and 20d SPY returns (the SKEW
  direction). High TS (near fear) same sign. Standardize each vs trailing 252d.
- **Judge = 1996-2025, halves 1996-2010 / 2011-2025; ONE look.** Pass: 20d forward return slope with the pre-signed sign,
  Newey-West (or day-clustered) t >= 2 in BOTH halves, ex-top-5 > 0. Kill: fail -> skew/term family closed. Runner
  `research/sim/skew_mkt.py` -> `data/research/program/skew_mkt_out.txt`.
Program N = 1009.
- **RESULT GAMMA-MKT (2026-10-16, one look; N 1008): KILL.** Material coverage caveat: `optionm.opprcd` has NO SPY rows
  before 2005-01-10, so the registered H1 is really 2005-2010 (28% of sample), not 1996-2010; 2025 partial. Arm V
  (|next-day ret| ~ DG_z, pre-signed negative): slope +11.6bp/1sd (NW t 9.85), decile-monotone (D1 51bp -> D10 105bp) — but
  the WRONG sign, and it is a contemporaneous vol-regime proxy (vol clusters), not a hedging-direction signal. Arm M
  (5d fwd ~ DG_z*sign(ret), pre-signed positive): -1.95bp (t -0.97), null; the mechanism-consistent form is right-signed only
  in H2 (-7.45, t -2.57) and flips in H1. No arm has the pre-signed slope with t>=2 in both halves -> KILL. Index
  gamma/pinning family closed. Output `data/research/program/gamma_mkt_out.txt`.
Program N = 1008.
- **RESULT SKEW-MKT (2026-10-16, one look; N 1009): KILL.** Coverage caveat: `optionm.vsurfd` has no SPY before 2005-01-10,
  so the judge is 2005-2025 (5,193 days), not 1996-2025. Grid used: delta +25/-25 (exact), days 30 exact vs 182 (proxy for
  180). Pre-signed z_RR30 -> fwd20 positive, z_TS -> fwd20 negative. RR30 H2_reg (>=2011) has the WRONG sign (t -1.67); H1_reg
  right sign but t 1.44 (<2); ex-top-5 fails in H2; deciles non-monotone (D1 +142bp > D10 +85bp, no fear->lower-return ladder).
  TS fails the same way. Every limb fails -> KILL. Skew/term family closed. Output `data/research/program/skew_mkt_out.txt`.
Program N = 1009.
- **RESULT REV-TONE (2026-10-16, N 1008): KILL — review tone predicts neither sales nor returns for these 20 firms.**
  8.5M matched reviews (2014-01..2023-09), 1.99M scored. Judge 2019Q1-2023Q2 (338 firm-quarters): H1 acc ~ dTONE t -0.68
  (with controls -1.17); H2 CAR t -0.45; H3 top-bottom net +63bp t 0.46, ex-top-5 -201bp; short-bottom -112bp. Paper era
  2014-18 also null (H1 t -0.82, H3 net -282bp t -1.46): the effect does not replicate even where Jin's data lived. "Always"
  check: bottom-tercile dTONE -> P(acc<0) 57% vs base 49%, P(CAR<0) 52% vs 52%. Tone and stars are 0.97 correlated (tone
  adds no separate information here). Per-firm corr(dTONE, acc) spans -0.51 (YETI) .. +0.57 (SKX), sign random.
  Nike: tone fell 0.68 (2015) -> 0.42 (2021) while revenue and the stock rose to their 2021 peak; the fall happened in
  ALL 20 firms (median -0.20; IRBT -0.56, NKE -0.27, DECK -0.20, CROX -0.05): a platform-wide drift in Amazon reviews, not a
  Nike signal. Nike's "fake" tag rose 0.5% -> 2.0% after it left Amazon in 2019 (3P listings). Output `rev_tone_out.txt`.
Program N = 1008.

## Study TOK-GAP (pre-register 2026-10-16, before reading any token outcome or drift; N 1009 -> 1010)
Source: mega_research_out_2026-10-15.md rank 1. Tokenized US-stock certificates on Gate
(MSTRX/NVDAX/AAPLX/TSLAX_USDT; 24/7, NOT tradeable by US persons — used ONLY as a free overnight
sensor; the account would trade the US-listed underlying at the ~0bp 09:30 open auction). New data
channel, not the dead cross-asset lead-lag class (that tested venue-to-venue return transfers; here
the token prices information that arrived while the primary market was closed). Evidence base:
arXiv 2610.21491 (NEST, posted 2026-10-15; spot-verified): token explains 15.7% of the MSTRx
gap-variation residual after BTC/mark-age/premarket controls (frontier 0.031); "NVDAX and AAPLX
clear their frontiers, whereas TSLAX does not". **NEST predicts the GAP only; this study judges the
open->close DRIFT, which is the thing NEST deliberately did not test.**
- **Data.** Gate public 5m candles, 4 tokens + BTC_USDT, 2025-06-01..2026-10 (backfill to API limit);
  cache `data/research/tok/`. US daily OHLC Sharadar SEP (MSTR/NVDA/AAPL/TSLA), ET calendar from
  America/New_York (DST handled); no premarket data — declared limitation.
- **Marks (per token-day).** M09 = last token candle close with open time <= 09:00 ET on day t;
  M04 = same at <= 04:00 ET; R(t-1) = first candle close at/after 16:00 ET on the prior US trade
  day. Signals: tok_day = log(M09/R)-1... log; tok_late = log(M09/M04); btc_day = BTC_USDT log
  return over the same [R(t-1), M09] window. Stale-mark guard: >= 8 zero-volume-excluded candles in
  the window AND the M09 candle opened within 30 min of 09:00 ET; exclude stock split days (and the
  day after) and days with no US bar.
- **Judge tokens = {NVDAX, AAPLX, MSTRX} (NEST frontier-clearers); TSLAX pre-registered PLACEBO
  (NEST failed it; expected null).**
- **Residual (pre-specified).** Per token, rolling trailing-60-obs OLS of tok_day on [btc_day,
  tok_late] -> resid, standardized by trailing-60-obs MAD -> resid_z. Only past data used.
- **Trade (one look).** Panel OLS drift = log(close_t/open_t) on resid_z, day-clustered; the
  account would buy at the 09:30 open (official cross) and hold to the 16:00 close.
- **Pre-signed prediction: b CONTINUATION > 0** (token sign slowly absorbed in the session).
- **Pass:** pooled day-clustered t >= 2, both halves (2025-06..2025-12 / 2026-01..2026-10) positive,
  ex-top-5 |contributions| > 0, survives 10bp RT and reported at 30bp RT (3x) stress. **Anti-check:
  TSLAX placebo must NOT pass at the same bar.**
- **Kill:** fail -> tokenized-twins sensor closed for this account (do not re-open with other
  certificates). TSLAX passing while judged tokens fail = anti-validation, kill likewise.
- **Ceiling context:** ~200 qualified token-days/yr x drift x ~100% deployable x 50% capture ->
  needs >= 8bp/day at $10k to clear +8pp.
- Runner `research/sim/tok_gap.py` -> `data/research/program/tok_gap_out.txt`. Program N 1010.

## Study BTC-ETF-FLOW (pre-register 2026-10-16, before reading any flow outcome; N 1010 -> 1011)
Source: mega_research_out_2026-10-15.md rank 2 (practitioner screen). Daily US spot-BTC ETF net
flow state (AP creations/redemptions are forced same-day BTC basket trades) -> next-day IBIT
open(t)->open(t+1) return, IBIT Roth-eligible, ~5-10bp spread.
- **Data (locked).** Farside full daily flow table (per-ticker + Total, US$m, 707 rows 2024-01-11
  .. 2026-10-09) via the Wayback capture 2026-10-10 of `farside.co.uk/bitcoin-etf-flow-all-data/`
  (live site Cloudflare-blocked); CROSS-VALIDATE the Total column against two independent mirrors:
  github canadiancode/btc-etf-flows (Jan 2024 - May 2025) and github isaergun/etf-flows-data
  (2026+); report |disagreement| > 5% rows. IBIT/FBTC/ETHA daily OHLC from Sharadar SFP (SFP ends
  2026-10-05). Cache `data/research/crypto_etf/`.
- **Signal.** f(t-1) = Total net flow on t-1; z = f / trailing-60-trade-day MAD; buckets: STRONG
  (|z| >= 1), off (else). Decision at open(t) using flow(t-1) (finalized EOD t-1; no lookahead).
- **Judge (one look).** Mean IBIT open(t)->open(t+1) on STRONG-IN minus STRONG-OUT days, day-clus-
  tered t, 10bp RT stress and 30bp (3x) shock; halves 2024-01..2025-06 / 2025-07..2026-10; ex-top-5
  days; secondary arms (report only): FBTC price leg; flow-t signal (lag -1) contemporaneous check
  to prove the timing bar.
- **Pass:** IN-minus-OUT >= 25bp net at 10bp RT, day-clustered t >= 2, both halves positive,
  ex-top-5 > 0.
- **Kill:** fail or sign-flip -> crypto-ETF flow family closed like CBAS/BSPD.
- **Ceiling context:** ~120 STRONG-day pairs/yr x 30bp x ~100% deployable x 50% = +18pp IF the raw
  spread >= 60bp; effect UNVERIFIED anywhere.
- Runner `research/sim/btc_etf_flow.py` -> `data/research/program/btc_etf_flow_out.txt`.
  Program N 1011.
- **RESULT BTC-ETF-FLOW (2026-10-16, one look; N 1011): KILL.** Farside flow series validated: 705
  daily rows 2024-01-11..2026-10-09, Total internally exact (0 mismatches vs per-ticker sum) and
  exact vs the canadiancode mirror (328 rows). IBIT judge (total-flow 1d-lag, |z|>=1, open->open):
  IN n=208 mean 43.9bp vs OUT n=117 mean 20.3bp; pair spread 23.7bp (bar 35bp raw / 25bp net);
  net@10bpRT 13.7bp, net@30bpRT -6.3bp; day-cluster t 1.39; **halves FLIP (-36.6 / +69.1)**;
  ex-top-5 7.6bp. FBTC leg identical (24.5bp, t 1.44). **Read: strong-flow days are momentum days
  (~44bp unconditional drift) but the predictive pair residual fails every registered gate — the
  flow state is contemporaneous BTC momentum already in the 09:30 price, exactly the memo's
  biggest-fail-reason. Crypto-ETF flow family closed.** Output `data/research/program/btc_etf_flow_out.txt`.
  Program N = 1011.
- **STATUS TOK-GAP (2026-10-16): DATA-BLOCKED at $0; the registered one look is NOT consumed.**
  Gate's public API serves only ~2 weeks of 5m history (all four xStock-style pairs begin
  2026-10-01); Kraken does not expose xStock pairs to the public API (AssetPairs returns none);
  GeckoTerminal minute OHLCV depth is far short of the registered 2025-06 window; iShares/Kraken/
  SoSoValue routes are blocked or keyed. NEST's own trade-level Gate reconstruction (arXiv
  2610.21491, gap-prediction only) could not be replicated forward for drift. Runner staged
  (`research/sim/tok_gap.py`) with a declared minimum-n guard (>= 60 qualified days per half per
  judged token); it refuses to judge below it. Cache `data/research/tok/` (2-week Gate sample).
  **Two honest paths to a judge: (i) start a log-only Gate 5m collector now (free, ~6 months to a
  forward sample; needs a place to run + REGISTRY entry), or (ii) buy token-mark history (Gate/
  Kraken export or Dune) — data-buy rule applies, and the prior stays LOW because NEST's controls
  already ate the mechanical fit and the 04:00-09:30 premarket may arbitrage the token's edge
  before the open. No decision taken; user call.** Note: ISA mirror `isaergun/etf-flows-data`
  excluded from BTC-ETF-FLOW validation — its "flow" is ΔAUM (price-inclusive), median |diff| vs
  Farside IBIT $143.8m. Program N = 1011.

## NBH: night-leg market beta hedge + market-state gates (2026-10-16, N 1011 -> 1014)
- **Why:** live Oct-2026 night trips lost -119bp (live) / -272bp (Roth) per trip, but after the QQQ overnight
  move the loss is ~-17 / -63bp: picks carry ~3-5x QQQ overnight beta. Question: does removing the market part
  (hedge) or skipping bad-market nights improve the leg? Prior evidence (downday_buckets, regime_tilt, REGIME-10M)
  says the leg earns MORE on bad days, so gates are expected to fail; the overnight beta HEDGE is untested anywhere.
- **Data (all TOUCHED for the night leg -> exploratory; forward shadow decides):** exact 15:40 pick panels
  `night_exact_pre2021.parquet` (2016-02..2020-10) + `recent/night_replay.parquet` (2020-11..2026-09-18);
  QQQ daily `etf_daily.parquet`, QQQ 15:40 from `night/m1/QQQ_YYYY.parquet`. Equal-weight picks per night,
  7.5bp/side on picks, 1bp/side on QQQ hedge notional, nights with no picks = 0. Eras 2016-20 / 2021-26.
- **Arms (frozen):**
  - H1 (N 1012) beta hedge: short b_t x QQQ close->next open, b_t = OLS beta of the net night-portfolio return on
    QQQ overnight over the prior 250 pick-nights (min 60), clipped [0, 6]. Roth form = long PSQ/SQQQ (same math).
  - G1 (N 1013) skip the night if QQQ(15:40)/prev close - 1 <= -1.0%.
  - G2 (N 1014) skip the night if QQQ(15:40) < mean of its prior 20 daily closes.
- **PASS (per arm):** in BOTH eras, Sharpe of the night series up >= 0.15 AND maxDD smaller; hedge also needs
  annual return to fall <= 25%; gates also need skipped nights net-negative in both eras. Report mean, median,
  day t, ex-top-5, %/yr at night weight 0.65, H1 residual alpha (mean, t, halves).
- **Kill:** fail -> record; no threshold/window re-tuning. Runner `research/sim/nbh.py` ->
  `data/research/program/nbh_out.txt`. Program N = 1014.
- **RESULT NBH (2026-10-16, one look; N 1012-1014): all three FAIL as registered.** H1 hedge: ex-ante beta of the
  equal-weight night portfolio is ~1.2 (p10 0.56, p90 1.75), not the 3-5x seen in 4 weeks of live trips; hedging
  removes QQQ's +6bp overnight drift with it: Sharpe 0.48->0.04 (2016-20), 1.06->0.79 (2021-26), maxDD worse.
  Residual alpha +11bp/night t 1.45 (2016-20 +1bp). G1 (skip QQQ 15:40 <= -1%): skipped nights ~0 net (-13bp /
  +5bp), Sharpe +0.14 / +0.05, maxDD -47->-36% in 2016-20 only: a near-miss risk dial, not alpha. G2 (skip QQQ <
  MA20): maxDD -47->-23% in 2016-20 but costs ~10pp/yr in 2021-26 (skipped nights +17bp). No re-tuning.
  Output `data/research/program/nbh_out.txt`. Program N = 1014.

## NDISC: when does the night leg lose? Discovery -> holdout conditioning search (2026-10-16, N 1014 -> 1015)
- **Why:** user asked to search hard for conditions that predict losing night-leg nights/picks. NBH showed single
  hand-picked market gates fail. This is an explicit SEARCH, so the protocol controls for it. All night-leg data is
  touched; the conditioning features are mostly not (exceptions disclosed: QQQ 15:40 / MA20 (NBH), SPY same-day bucket
  and crowding (downday_buckets), SPY vol / d-1 (regime_tilt), stock trend (TREND-NIGHT), pe sign (FUND-STATE), QI (QI-HIST)).
- **Data:** exact 15:40 picks 2016-02..2026-09 (`night_exact_pre2021` + `recent/night_replay`); market from SIP m1
  (QQQ/SPY/IWM etc.), `etf_daily`, CBOE VIX/VIX9D csv; 2003-15 daily-close proxy picks via `nx.collect_trades`.
  Net = gross - 7.5bp/side.
- **Splits (frozen):** DISCOVERY = 2016-02..2022-12 (exact), with sub-halves 2016-19 / 2020-22.
  HOLDOUT A = 2023-01..2026-09 (exact). HOLDOUT B = 2003-2015 (Sharadar daily proxy; only daily-computable features).
- **Feature families (all known by 15:40 on day d):** (M) market: QQQ/SPY/IWM 15:40 day return, 5d/20d return,
  vs MA20/50/200, intraday range, IWM-QQQ spread, VIX prior close level / 1d / 5d change / 252d pct, VIX9D/VIX,
  realized vol 20d; (C) calendar: weekday, pre-weekend/holiday, month-end +-2, FOMC eve, OPEX week; (B) breadth:
  number of candidates, share of candidates that are ETFs, mean candidate day_ret; (P) pick: day_ret depth, ibs, vol20,
  adv, price, leveraged/inverse ETF flag, intraday path (p40 vs open; open gap), prior-night repeat, 5d prior return.
  Each continuous feature -> quintiles on DISCOVERY breakpoints; categorical as-is.
- **Discovery selection rule:** a bucket is a candidate if its net mean is < 0 in BOTH discovery sub-halves AND
  day-clustered t <= -2.0 on discovery AND it holds >= 5% of discovery trades. Family-wise control: 500 date-shuffle
  placebos of the whole scan (feature series permuted across nights; pick features permuted within night-date blocks
  preserved) -> report the count of candidates per placebo; the scan is informative only if the real count exceeds
  the placebo 95th pct.
- **Combined rule (frozen at discovery end, before any holdout read):** HALVE size on picks/nights in any candidate
  bucket (and SKIP when >= 2 candidates fire). Also report the pure-skip version.
- **PASS (holdout A, and B where features exist):** flagged trades net-negative; Sharpe of the rule >= base + 0.15;
  maxDD smaller; %/yr not lower than base - 2pp. Report per-candidate holdout results individually too.
- **Kill:** holdout fail -> record the candidates as DISCOVERY-ONLY; no re-scan, no re-cut. Runner
  `research/sim/ndisc.py` -> `data/research/program/ndisc_out.txt`. Program N = 1015.
- **RESULT NDISC (2026-10-16, one look; N 1015): FAIL - scan uninformative.** 47 features / 210 buckets on discovery
  2016-22 (10,912 trades): ZERO buckets met the registered rule; placebo (500 night-block shuffles) mean 0.15, p95 1.
  Strongest negatives sign-flip between halves (LETF picks +47/-50bp, ETF +46/-40, gap -3..-1% +14/-30, 8+ picks
  -42/+14); only Friday (-28/-72, t -0.79) and deep intraday path (-10/-13, t -0.99) agree, both noise. Descriptive
  holdout: the weak negatives turn positive in 2023-26 and all 10 computable ones are positive in 2003-15. **Read:
  losing nights are not identifiable from anything known at 15:40; the loss is the overnight move itself.** Do not
  re-scan conditioning features on the night leg. Output `data/research/program/ndisc_out.txt`. Program N = 1015.

## PMX: pre-market exit of night picks when QQQ falls overnight (2026-10-16, N 1015 -> 1016)
- **Why:** NBH/NDISC show losing nights are not identifiable at 15:40; the loss is the overnight move. PMX acts after
  entry: if QQQ is down hard pre-market, sell the picks before the open instead of at the 09:30 cross. Exploratory
  (night-leg data touched); the pre-market exit itself is untested anywhere (OPENSIG was an open-time exit).
- **Data:** exact 15:40 pick panels 2016-02..2026-09 (as NDISC); Alpaca SIP minute bars incl. extended hours for each
  pick on day d+1 04:00-09:30 ET (fetched to `data/research/pmx/`) and QQQ from `night/m1`.
- **Rule (frozen):** q_pm = QQQ 08:59 bar close (d+1) / QQQ 15:59 bar close (d) - 1. If q_pm <= -1.0%, sell every
  pick at its own pre-market price = close of its last 1-min bar in 08:30-08:59 ET; if the pick has no print in that
  window it is held to the open (counted, reported). Otherwise hold to the open as now.
- **Costs:** open exit 7.5bp/side as base; pre-market exit 50bp/side (thin extended-hours book); also report at
  100bp/side (shock) and 7.5bp (lower bound).
- **Primary stat:** on flagged pick-nights, d = (pm-exit net) - (open-exit net) per trade, night-clustered.
- **PASS:** mean d > 0 with night-clustered t >= 2 at 50bp in BOTH eras 2016-20 and 2021-26; leg Sharpe up >= 0.1 and
  maxDD smaller in both eras; ex-top-5-nights d still > 0. Descriptive only (not judged): thresholds -0.5/-1.5%, exit
  time 08:00 / 09:15, QQQ pm->open continuation vs reversal on all nights.
- **Kill:** fail -> pre-market exits closed for the night leg; no re-tuning of threshold/time. Runner
  `research/sim/pmx.py` -> `data/research/program/pmx_out.txt`. Program N = 1016.
- **RESULT PMX (2026-10-16, one look; N 1016): FAIL both eras.** Flagged (QQQ 08:59 <= -1%): 54 nights / 541 trades
  (2016-20), 120 / 1636 (2021-26); 65% / 83% had an 08:30-08:59 print. d (pm exit - open exit) at 50bp: -39.6bp t -2.44
  / -20.3bp t -1.98; at 7.5bp -7.0 / +16.2 (t 1.59). Leg Sharpe -0.09 / -0.10, maxDD slightly worse. Every descriptive
  cell (08:00/08:59/09:15 x -0.5/-1/-1.5%) negative at 50bp. QQQ 08:59->open slightly REVERTS (+2.9bp t 1.28 after
  <= -1%), no continuation. Pre-market exits closed for the night leg.
  **Descriptive lead (not judged, not a pass):** pick last pre-market prints sit ABOVE the 09:30 bar open on most
  nights (+35bp mean / +27 median on random nights, +15/+9 on flagged): a general gap-to-open effect, unconditional on
  QQQ. Last print is not an executable bid; only a forward test of real pre-market bids could tell if any of it is
  capturable. Output `data/research/program/pmx_out.txt`. Program N = 1016.

## Amendments 2026-10-16 (improvement set deployed, no N consumed)
- **NAVFALL is a KEEP-constraint, not a filter.** Re-read of the session memory: CEF-RV entries after a trailing-26w
  NAV fall are the rule's BEST trades (dropping them costs -705bp t -5.1). The deployed rule already keeps them; the
  only work is informational: `cef_rv_shadow` now stores NAV in the weekly panel `(date, discount, nav)` triples
  (legacy pairs tolerated) and backfills `navfall26w` onto every logged row, with the digest line reporting
  NAVFALL-on vs NAVFALL-off excess so no future session "improves" the rule by dropping them. No gate change.
- **Fill-cost ledger built** (`swingtrader/daily/fill_cost_scorer.py`, REGISTRY "Fill-cost ledger", audit
  `audit_execution_1002.md` item 1): every daily-fills row scored vs the official SIP auction print of its own
  session (night sells vs 'O' open, night buys / MOC legs vs '6' close), intraday legs logged mid_unclosed.
  `state/fill-costs.jsonl`; idempotent on (coid, filled_at, fill_px). Executor `ref_px`/`slippage_bps` stay as the
  decision reference; cost is now a separate computed field (items 3/4 of the audit reduce to this for any consumer
  of cost numbers).
- **PREF-first wiring verified (no change needed).** `executor.py` already subtracts `state/pref-ex-reserved.json`
  (dated, cash/Roth account only) from the night leg's sizing, and `pref_ex_live` writes the reservation in dry as
  well as live; CEF-RV held value is subtracted separately. The ROTH-STACK +2pp PREF-first ordering holds.

## Pre-registrations 2026-10-16 evening burst (user: "everything on, as much as possible"; N 1011 -> 1015)
PREF-EX mode flips OFF -> LIVE this commit (dry's 10-20 run will place Tuesday's real MOC buy; kill rule unchanged:
>25bp live cost or event mean net <= 0 at 30 trips).

### Study PREF-PART (N 1012) — participation-impact ladder for the PREF stack (the v2-raise question)
Replay the PREF-EX shadow's scored events (state/pref-ex.jsonl, official sizes on disk) at participation 5% (the
registered setting), 10%, 20%, 50% of the trailing median closing cross; fill capped by the event's own cross size;
sizes rounded to whole shares at the $25-par price. ONE LOOK. Judged statistic: mean extra cross-cost per event
(marginal impact) at 10% and 20% vs the 5% baseline. PASS = extra cost <= 10bp at 10% AND <= 20bp at 20%; the 50% run
is report-only (it informs, not decides). In-sample (2026 backfill + these sessions); the v2 raise itself waits for
the live 30-trip gate. Runner `research/sim/pref_part.py` (data from him's state/pref-ex.jsonl) -> out txt. N 1012.

### Study SSR-T1 (N 1013) — did T+1 settlement (2024-05-28) shift the Rule 201 lift-day executable window?
SSR-LIFT confirmed the trigger->lift mechanism (-43bp diff-in-disc) and an executable short T+2-open -> T+2-close
2021-26 (+16.7bp/day t 2.72, official crosses). Pre-signed: post-T+1 (2024-06-01+) the forced buy arrives ~1 day
earlier, so the SAME-session short (short T+1 open -> cover T+1 close, arm B) should hold/recover excess vs arm A
(longer window). Judge = post-T+1 era only (2024-06..2026-10), official crosses, tier costs, day-clustered; one look.
PASS = arm B era mean >= arm A era mean + 10bp with t >= 2 in the era; else the executable window stays T+2 as deployed.
Runner `research/sim/ssr_t1.py` (reuses data/research/ssr events + research/sim/ssr_cross.py plumbing). N 1013.

### Study CEF-ACCEL (N 1014) — faster exit arm for CEF-RV (forward-only)
CEF-RV exits at its own trailing-52w 50th percentile. Pre-registered arm: exit at the 60th percentile instead
(accelerated), same entry rule. Judge = FORWARD (CEF-RV-FWD's own pipeline; the shadow logs the accelerated exit
signal beside the registered one; NO backtest look: the family's 1999-2014 and 2016-26 windows are touched).
Decision at cef_rv_mode enable time: adopt the accelerated exit only if at 60-closed-trade read it keeps excess
>= 60bp per trade AND yields >= 1.5x the events at equal t. Until then the deployed exit stays the registered median.
Built into `swingtrader/daily/cef_rv_shadow.py` (adds `exit_signal_accel` + summary readouts). N 1014.

### No new registration
TME-BOOST (3x via TMF) stays per the 2026-10-11 ceiling-kill: reopenable only with a measured FORWARD capture rate
for TME itself — `research.sim.tme_shadow forward` is already in research-shadows and is the measurement. No backtest.

### RESULTS (2026-10-16 evening burst, one look each; program N = 1015)
- **PREF-PART (N 1012): PASS (model-based).** 319 scored eligible events; square-root-impact ladder on the events'
  own cross dollars: participation 5% -> 10% adds ~+0.7bp/event, -> 20% ~ +1.8bp, 50% ~ +3.9bp — every rung inside
  the +38bp/event trade. The registered bar (<=10bp extra at 10%, <=20bp at 20%) is comfortably met, so the v2
  participation raise (5% -> 10% at first) is bookable at the live 30-trip gate's discretion. Caveat once: it is an
  impact MODEL; the real judge is live cost at raised participation. Output `research/sim/pref_part_out.txt`.
- **SSR-T1 (N 1013): KILL.** Post-T+1 era judged, official crosses (45,037 events, 585 sessions, trigger
  2024-06-03..2026-10-01). Arm A (deployed: short T+2 open, cover T+2 close) SURVIVES the T+1 era: treated mean
  +42.5bp (day-t 1.80), hedged +33.5 (day-t 2.50), ADV>=$20M mean +43.9 (day-t 2.20). The pre-signed T+1 arm is the
  OPPOSITE: T+1 open -> T+1 close = -116.9bp mean (day-t -9.87), hit 45%, also negative on the control set (-60.1bp
  day-t -5.75) — the T+1 open->close leg is a losing leg broadly, not a timing upgrade. Verdict: the executable
  Rule-201 window stays T+2 open -> close, as deployed. Positive confirmation for the aggressed sleeve. Output
  `research/sim/ssr_t1_out.txt`.
- **CEF-ACCEL (N 1014): deployed forward-shadow arm only.** `cef_rv_shadow` now logs exit_signal_accel (60th-pct
  exit) beside the registered median exit; adopted or killed at cef_rv_mode enable (60 forward trades, excess>=60bp
  AND >=1.5x the events at equal t). NO backtest look taken.
- **TME-BOOST (N 1015 slot; no new look):** `research.sim.tme_shadow forward` already measures the forward capture
  rate; the 3x reopen decision reads THAT when enough sessions accumulate. Nothing to run today.
Program N = 1015.

## PROVOL: size the overnight legs UP on high-vol states (2026-10-17): CEILING-KILL, no N consumed, no backtest
- **Idea:** night weight x1.3 (cap .15/name, 2x gross) when a pre-15:40 vol state is in its top trailing-1y tercile.
- **Dedupe:** not tested as a within-leg pro-vol size-up, but every neighbour is dead: vol-targeted gross (add. 32, NW t -1.8/-2.4),
  cross-leg regime tilt (add. 26a, placebo-level), night size-up after big down days (add. 34), SPY/VIX/QQQ-state gates (NBH G1/G2, REGIME-10M),
  NDISC (47 features incl. vix_pct252, rv20: 0 buckets pass, strongest sign-flip between halves; vix mid-bucket +133/+24bp, rv20 -50/+228bp), VTS.
- **Ceiling (gate arithmetic):** base night series %/yr at weight 0.65 = +23.9 (2016-26; nbh_out.txt), +11.4 (2016-20), +35.3 (2021-26).
  x1.3 on one tercile of nights adds at most 0.3 x 23.9 = +7.2pp/yr gross even if ALL P&L sat in that tercile (it does not: terciles are roughly
  equal-weighted in ndisc/downday_buckets, so ~+2.4pp), minus ~0.7bp/night margin interest (12.5%/yr on ~0.2 of account), x 50% honest capture
  = ~+1.2pp (range +1..+3.6pp). Same at $2.3k/$10k/$25k (rate, not dollars); Roth cannot lever, so the Roth is the same math with 0.65 -> 1.0 cash cap. 
  Even a 2x multiplier is bounded by the .15 name cap and the 2x Reg T gross. All << the +8pp gate.
- **Verdict: CEILING-KILL.** Selection/sizing conditioning on the night leg is a closed class (FUND-STATE, NDISC, NBH, add. 32). Reopen only with a
  forward-shadow-measured high-vol-tercile excess that is a multiple of the leg mean. No code, no shadow, no REGISTRY entry.

## Study TAX-STACK (pre-register 2026-10-17, N 1016 -> 1017)
Question (portfolio construction, no new signal): in the TAXABLE margin account running the live nx_s2 book (night .65, name cap .15, IBS .5 = 1.15x gross overnight),
how much %/yr do PREF-EX + ETDX CO ex-nights add after 35% tax and Schwab margin interest (assumed 12.5%/yr, unverified; the repo has no number)?
Ceiling math (before running): ROTH-STACK STRICT pref-first (cash Roth, book 1.0x) = +10.5pp ($3k) / +7.1pp ($10k) / +4.5pp ($25k) pre-tax. Taxable book is 1.15x so
idle cash is smaller; margin lets PREF borrow up to Reg T 2x (preferred/baby-bond marginability UNVERIFIED; assumed marginable) at 3.4bp/night vs ~27bp median net edge.
Tax: dividends held <61d are non-qualified; price drop is a short-term loss. View A: loss offsets the book's STCG, after-tax = 0.65 x pre-tax. View B (bound): loss unusable,
tax = 35% x dividend $ (wash sales on monthly payers push toward B). Expected: $10k pre ~+6, after-tax A ~+4, B possibly <= 0; $100k capacity-bound ~+1. Ceiling at $10k
after tax A is > +2pp so not ceiling-killed; B decides robustness.
Rule: roth_stack.load_groups events + alloc (equal split per night, 5% of min ex-ante auction $, whole shares, 10bp RT); buy d0 close, sell ex-date open. Book: AL1 cash logic
with night cash 1.15E and IBS .5 (BIL on idle IBS slice). Arms: CASH night-first, CASH pref-first (pref from own cash only), MARGIN 2x (night undisturbed, PREF may use
headroom to 2E, BIL sold when needed with yield lost, interest 12.5% x calendar gap on incremental debit). Incremental = with-PREF minus no-PREF book.
Data: official crosses 2021-26 (touched; economics only). Sizes $2.3k/$10k/$25k/$100k, fixed equity. Out: data/research/program/tax_stack_out.txt.
Gate (PASS): at $10k, best executable arm adds >= +2pp/yr after tax (view A), halves both > 0, 3x cost > 0 (after tax A), ex-top-5 > 0. View B reported, not gated.
Kill: any failure = SMALL/KILL, no re-tuning of tax rate, interest rate or arms.
- **RESULT TAX-STACK (run 2026-10-17, one run, N 1017): PASS-SMALL, tax-fragile.** Added %/yr, pre-tax / after-tax view A (loss offsets book STCG, x0.65): $2.3k CASH pref-first +12.4/+8.1, MARGIN 2x +24.5/+15.9;
  $10k CASH pref-first +6.8/+4.4, MARGIN +11.6/+7.5; $25k +4.1/+2.6, +5.6/+3.6; $100k +1.3/+0.8, +1.5/+0.9 (capacity-bound). Margin interest drag (12.5%, unverified) -1.0pp at $10k, -2.7pp at $2.3k; halves both > 0
  (10k margin A +8.7/+6.2); ex-top-5 same sign; median +27bp, hit 72%. **3x cost (30bp RT) leaves +0.6pp after-tax at $10k margin (+1.1 at $2.3k): cost-fragile.** View B (pref price loss NOT usable against gains, 35% on dividends) is
  deeply negative at every size (-18pp at $10k margin): the result depends on the loss offsetting the book's short-term gains and on wash-sale rules not deferring it (monthly payers re-bought within 30 days). Preferred/baby-bond marginability UNVERIFIED. Runner research/sim/tax_stack.py, out data/research/program/tax_stack_out.txt. Uses cached raw night pool (s.N) because night_trades.v2.pkl is unreadable under the venv's pandas 2.2.3.

## STANDING USER RULING (2026-10-17 morning): TENDERS ARE DEAD — user, permanently
"No tenders — tenders are dead because they take too long." Scope: ALL tender-offer classes
(odd-lot tenders, CEF trigger tenders like BMEZ/HERZ, issuer self-tenders, tender-style NAV
payouts with multi-week capital locks). The lock (weeks-months of capital) kills them at this
program's capital turnover regardless of win rate (odd-lot: 14/15, +5.5% median — still dead).
Also retired by the same ruling: voluntary-liquidation multi-tranche classes where the FIRST
distribution has passed (the remainder locks). Do not re-propose any of these.
Scanner extensions for tender flags: NOT BUILT (dropped with the ruling). Liquidation 8-K flag:
built ONLY as a log-only flag if trivially cheap (it feeds nothing else); deprioritized.

## Study PANIC-IDX — rare index washout buy (pre-register 2026-10-17, before any outcome read; N 1017 -> 1018)
User ask: "rare through signals, but when it hits you make a lot." Mechanism: forced de-risking (margin calls, vol-target /
risk-parity cuts, redemptions) peaks in fast index selloffs inside a drawdown; the forced sellers' price concession pays the
buyer over the next ~2 weeks. Named counterparty = levered/vol-targeted holders who must cut. Index-level, so whole-share and
liquidity limits do not bind at $2-25k; Roth-eligible (long only, no margin).
- Data: Sharadar SFP SPY closeadj (total return), 1998-01..2026-10. Not untouched in the human sense (2008/2020 are famous)
  but this rule has never been run in the program.
- Signal at close T: SPY drawdown from trailing-252-session max close >= 15% AND SPY 5-session return <= -7%.
- Trade: buy close T, sell close T+10 sessions. No new entry while a trade is open (non-overlapping). Cost 2bp/side.
- Statistic: excess = trade return minus the mean of all 10-session SPY returns (unconditional drift). Report raw, excess,
  median, hit rate, events/yr, halves 1998-2011 / 2012-2026, ex-top-5, worst trade, per-event list, and a 3x (UPRO-like,
  daily-rebalanced synthetic) column. Sensitivity grid (dd {10,15,20} x 5d {-5,-7,-10} x hold {5,10,20}) is DESCRIPTIVE only.
- Gate: mean excess >= +2%/event, median raw > 0, hit >= 60%, both halves mean > 0, ex-top-5 mean > 0. Else KILL.
- Ceiling check (research-priority gate) reported alongside: events/yr x net edge x 100% of account (Roth idle cash or the
  book's cash) x 50% capture.
Runner research/sim/panic_idx.py; out data/research/program/panic_idx_out.txt. One run.
### Result — PANIC-IDX (2026-10-17, one run, N 1018): KILL
Out data/research/program/panic_idx_out.txt. n 18 (0.65/yr): raw -0.94% mean, median +0.34%, hit 56%, excess -1.35% (t -0.80), halves -1.19 / -1.79,
ex-top-5 -4.21%; 3x synthetic worst -52.7% (2020-03-09). 2008-09 and 2020 fired early and kept falling. Gate 1/5. Grid (descriptive, NOT a candidate):
only the 5d <= -10% cells are positive (+1..+6% excess, n 6-15, the same 4-5 crises counted repeatedly); ceiling there ~0.4/yr x ~4% x 50% ~ +0.8pp/yr
(3x ~ +2.5pp). Index washout buying is closed: rare + large does not clear the +8pp gate unless the payoff per event is >> 10% or the event is frequent.

## Study PCP-HTB — hard-to-borrow conversion carry (pre-register 2026-10-17, before any outcome read; N 1018 -> 1019)
Mechanism (contractual, not predictive): when a stock is hard to borrow, option market makers who must short stock to hedge
puts/synthetic shorts pass the borrow fee into put-call parity (puts rich, calls cheap). A holder who BUYS the stock, BUYS
the K put and SELLS the K call (a same-strike collar = conversion) locks payoff = K at expiry whatever the price does, and
earns ~ r + borrow fee on cost S + P - C. Who pays: short sellers / put buyers who cannot borrow. Why it persists: it is the
lending fee, paid for supplying borrow; retail long holders rarely lend and institutions lend directly. Why small accounts
can harvest it: 1-10 contracts per name, no capacity limit at $2-25k; Roth-legal (long stock + long put + covered call).
This is NOT a premium-buying options trade (closed class): delta-neutral, payoff fixed at entry. Never run in the program.
- Data: WRDS optionm.opprcd (EOD best_bid/best_offer, OI, contract_size), optionm.borrate (prefilter), CRSP dsf (closing
  ask, dividends, delistings), FRED DTB3 (T-bill). CRSP ends 2024-12 -> window 2005-2024.
- Universe/date: every Wednesday close t (next session if holiday); prefilter borrate (nearest-30d tenor) >= 10%/yr at t.
- Contract: expiry with 21 <= DTE <= 70 nearest 45; strikes with |K/S-1| <= 15%, standard contracts only (contract_size 100,
  no adjusted roots), call best_bid > 0 and put best_offer > 0, both OI > 0. Exclude windows with a CRSP ordinary dividend
  ex-date before expiry (exclusion only; count reported).
- Far-side cost/share = stock closing ask (CRSP; else close x 1.005) + put offer - call bid; + $2.60/contract reserve
  (Schwab $0.65 x 2 legs + exit/exercise reserve). Locked payoff = K. yield_ann = (K - cost)/cost x 365/DTE;
  excess = yield_ann - DTB3. Signal at t: best strike excess >= 10%/yr. Staleness guard: the SAME (K, expiry) must still show
  excess >= 10%/yr on the next session's quotes, and the trade ENTERS at those next-session (t+1) prices. Hold to expiry
  (payoff K; delisted/merged before expiry = K with the adjusted deliverable, counted).
- Portfolio sim (cash account, Roth-like, no margin), $2.3k / $10k / $25k / $100k: each entry day fill free cash with the
  highest-excess confirmed conversions, 1 position per name, whole contracts, <= 10 contracts and <= 5% of the smaller leg's
  OI; idle cash at DTB3. Report %/yr and excess over T-bill by year, utilization, names, events/yr.
- Gate (judge 2016-2024): (1) $10k excess >= +8pp/yr; (2) 2016-20 and 2021-24 both > 0 at $10k; (3) >= 100 confirmed
  entries/yr pooled, and report the t -> t+1 survival rate (low survival = stale quote artifact); (4) 2x spread shock (each leg
  pays one more half-spread) keeps $10k excess > 0; (5) ex-top-5 names > 0; (6) 2005-2015 $10k excess > 0.
  Fail (1) with the rest passing = SMALL; any other fail = KILL. No re-tuning of 10%, DTE window, strike band or prefilter.
- Not testable on EOD data (forward step if it passes): fill at the NBBO for 1-10 contracts on live Schwab quotes, Roth
  approval for same-strike collars, early-assignment handling.
Runner research/sim/pcp_htb.py; out data/research/program/pcp_htb_out.txt. One run.

## Study BK-EMERGE-GV — Chapter 11 emergence equity (pre-register 2026-10-17, before any outcome read; N 1019 -> 1020)
Reopen reason (low power, not proxies): jump R2-14 had n 4 (name match). Mechanism: the plan hands new equity to old creditors
(banks, CLOs, distressed/HY bond funds) who are mandated or built to hold debt, not small-cap equity; they sell into a stock with
no analyst coverage and no index membership, so the new equity starts at a concession that later re-rates (Eberhart-Altman-Aggarwal
1999 report positive post-emergence excess returns). Queue: research/drafts/mechanism_queue_2026-10-17.md #3.
- Events: Compustat gvkey continuity via CCM link (crsp.ccmxpf_lnkhist, linktype LU/LC) from an OLD permno whose CRSP delisting
  code is bankruptcy/performance related (dlstcd 574, or 550-585 with a bankruptcy name flag if 574 is sparse — report counts) to a
  NEW permno first trading within 36 months after the old delisting. Common shares (shrcd 10/11), first price >= $1. 1990-2024.
- Entry: close of the 5th trading day of the new permno. Hold 120 trading days (exit earlier only on delisting, using dlret).
- Benchmark: CRSP EW return of the same NYSE size decile over the same window. Cost 50bp/side (thin new listings); 2x cost column.
- Report: n, n/yr, mean/median raw and excess, hit rate, halves 1990-2007 / 2008-2024, ex-top-5, worst, per-event list,
  listing venue mix, ceiling %/yr at $2.3k/$10k/$25k (whole shares, up to 5 concurrent equal positions, 50% capture).
- Gate: n >= 100; median excess >= +4% per 120d; mean excess > 0 net; both halves mean > 0; ex-top-5 mean > 0; 2x cost mean > 0.
  Any fail = KILL. No re-tuning of entry day, hold, benchmark or cost.
Runner research/sim/bk_emerge.py; out data/research/program/bk_emerge_out.txt. One run.
### Result — PCP-HTB (2026-10-17, one run, N 1019): KILL (and a sign error in the registration, disclosed)
Out data/research/program/pcp_htb_out.txt. Prefilter borrowrate >= 10% gave 359 Wednesday name-dates (3 before 2016: OptionMetrics
borrow is ~empty pre-2016); 163 had a valid same-strike conversion; best-strike far-side excess median -77.7%/yr, p90 -23.4, max -3.7:
ZERO signals, 0 entries, gate 0/6. **Registration error:** with borrow fee b, C - P = S e^-bT - K e^-rT, so the conversion (long stock,
long put, short call) costs MORE than PV(K) and earns r - b, not r + b. The fee accrues to the SYNTHETIC LONG (long call, short put),
which is directional: it earns the HTB stock's return + b (= BORROW-XS long D10 + fee) and is not hedgeable without shorting. Either way
the four-leg far-side spreads in HTB chains (OI 1-10, wide quotes) dwarf any fee, and the mid-implied rate is uncorrelated with
OptionMetrics borrowrate (r ~ 0, n 163): EOD quotes in these chains are not tradable prices. **Class closed: retail cannot harvest the
borrow fee through options parity; it needs a lending program (Schwab fully-paid lending), not a trade.** Not re-run reversed (unregistered).
### Result — BK-EMERGE-GV (2026-10-17, one run, N 1020): KILL
Out data/research/program/bk_emerge_out.txt. Registered set (dlstcd 574 + gvkey continuity) n 58 (1.7/yr) < 100; registered fallback
(dlstcd 550-585, no extra name flag — the flag was undefined in the registration, disclosed) n 153: median excess -6.5% / 120d (set A +0.3%),
mean net +1.4% t 0.27, ex-top-5 -6.9% (A -5.0%), hit 44%; mean carried by Bradlees +515%, TWA, Core Scientific. Ceiling ~+0.7pp/yr excess.
Post-Chapter-11 equity is a lottery, not a creditor-dump concession; class closed at CRSP/Compustat (do not re-run with other links/holds).

## Study INCOME-SHOCK — dormant $25-par panic rule with an issuer-quality screen (pre-register 2026-10-17, N 1020 -> 1021)
Source card: research/drafts/branch_A_dysfunction_2026-10-17.md (INCOME-PAPER-SHOCK). Mechanism: in a funding panic, levered income
holders (CEFs, BDCs, mREITs, fund redemptions) dump $25-par preferreds/baby bonds together regardless of issuer solvency; paper of
issuers that stay solvent recovers toward the pre-shock price/par. Touched already (descriptive, unscreened): 2020 strongly +, 2008
triggers -25..-27% at 60d. The ONLY open question this study answers: does a point-in-time issuer-quality screen, knowable on the
trigger day, separate the recoveries from the 2008 losses? Rare trigger, effective n of events tiny: judged per event, not by t-stat.
- Universe: Sharadar SEP "Domestic Preferred Stock" + SFP ETD, raw price, 20d median $vol >= $50k, 2002-2026.
- Trigger (frozen from the card): universe EW 10-session return <= -10% AND universe median price <= 0.90 x $25; one event per
  episode (no new trigger within 120 sessions after a fire).
- Screen (PIT, trigger-day knowable): issuer has a WRDS TRACE senior unsecured bond trade in the prior 10 sessions with yield < 8%,
  OR FISD issuer/issue rating (as of trigger date) investment grade. Matched by issuer (FISD issuer_cusip / name link; report match rate).
- Trade: equal-weight screened names, entry 1/3 each at trigger close, +5, +10 sessions (raw closes + 50bp/side); exit +120 sessions
  (also report +60, +250); dividends included (Sharadar dividends with the FXD guard); delisted = last price.
- Report per event: n screened / unscreened, screened vs unscreened return, worst name, % of names < -30%.
- Gate (PASS = worth a dormant live monitor + tiny staged real-money rule): screened basket +120d return > 0 in EVERY fired event incl.
  each 2008 fire; median across events >= +10%; screened beats unscreened in >= 75% of events. Else KILL (record which event broke it).
  No change of trigger, screen thresholds, or horizons after reading.
Runner research/sim/income_shock.py; out data/research/program/income_shock_out.txt. One run.
### Result — INCOME-SHOCK (2026-10-17, one run, N 1021): KILL
Out data/research/program/income_shock_out.txt. Fires 2008-07-14 / 2009-01-20 / 2020-03-16 (120-session lockout suppressed 2008-09-15).
Screened +120d: -13.0% / +34.6% / +24.9% (unscreened -16.4 / +35.1 / +39.3); screened beat unscreened 1/3; 43% of 2008-07 screened names
< -30% at +60d. Gate: every-event > 0 FAILS (2008-07), median +24.9% passes, screen-beats 33% FAILS. Failure type: BAD HYPOTHESIS — an
issuer-quality screen (TRACE yield < 8% or PIT IG) does not separate a solvency crisis from a funding panic at trigger time; the early fire
in a solvency crisis loses even in IG paper. Caveats: FISD link by name (match 9/34, 9/28, 243/619; 16/20 hand-checked), Sharadar pref
panel thin pre-2014; two FISD bugs fixed after a first (empty) output was seen (disclosed). $25-par panic class closed; no trigger/screen variants.

## Study INTL-PREF — PREF-EX replication on Canadian (TSX) $25-par preferreds (pre-register 2026-10-17, N 1021 -> 1022)
Source: research/drafts/branch_H_access_unlocks_2026-10-17.md H-2. Purpose: a genuinely untouched market for the program's one alive
mechanism (dividend-proportional ex-date under-adjustment in thin retail $25-par paper). Different tax clientele (Canadian eligible-
dividend credit; prefs held in taxable and TFSA/RRSP): the test is whether the effect is a thin-inventory/retail-paper property, not US tax.
- Data: WRDS Datastream (or any WRDS source with TSX preferred daily raw prices + dividend ex-dates/amounts); the runner may first
  check DATA AVAILABILITY (coverage, opens present?) without computing returns. If unavailable -> DATA-LIMITED, no N consumed.
- Universe: TSX-listed preferred shares, par C$25, raw price C$10-30, 20d median C$ value traded >= C$50k, 2005-2025 (all untouched).
- Primary statistic: CO = close(E-1) -> open(E) + dividend, in % of close(E-1), net of 10bp round trip, per ex-event. If Datastream has
  no reliable opens, primary becomes CC = close(E-1) -> close(E) + dividend (stated before reading). Also report drop/dividend ratio.
- Gate: net mean >= +15bp/event, median > 0, day-clustered t >= 2, >= 80% of years > 0, drop/div <= 0.9, ex-top-5 > +10bp, both halves
  2005-14 / 2015-25 > 0. Else KILL. Report by yield bin and liquidity tier (descriptive). No re-tuning.
- Trading would need IBKR + CAD (user decision); this study decides only whether the mechanism transfers.
Runner research/sim/intl_pref.py; out data/research/program/intl_pref_out.txt. One run.
### Result — INTL-PREF (2026-10-17, one run, N 1022): PASS (gate 7/7), pending adversarial checks on opens + execution
Out data/research/program/intl_pref_out.txt. WRDS Datastream tr_ds_equities (ds2ctryqtinfo CA/PREF, ds2primqtprc exch 197 raw CAD,
ds2div); 1,166 CA pref quotes of which 999 delisted (survivorship-free); eligible 471 names / 12,460 ex-events 2005-2025. Deviation
(disclosed): runner also applied the US rule's yield filter 0.2-4%/payment, not in the INTL-PREF text. CO primary (reliability rule fixed
before reading: opens present 100%, open==prior close 16.6% of non-ex days / 3.4% of ex-events). CO net 10bp RT: mean +32.1bp, median
+30.4, day-clustered t 31, ex-top-5 +31.8, hit 72%, 21/21 years, halves +38.8 / +27.1, drop/div 0.66; monotone in yield (<1% +11.6,
1-1.5% +31, >=1.5% +54); flat across liquidity tiers; non-ex nights -0.2bp; offsets -2..+2 flat. CC +15.8bp mean / +14.8 median
(drop/div 0.79): misses the 15bp bar on the median. **Mechanism transfers to an untouched market with a different tax regime: the
ex-date under-adjustment is a property of retail $25-par paper, not of US tax.** Open caveats: Datastream opens may be back-filled
(not proven to be TSX opening-auction prints); executability (IBKR + CAD, TSX opening/closing auction depth, Canadian 15% withholding on
dividends vs the US-IRA treaty exemption) unverified. No trading until those are checked.
- **INTL-PREF verification (2026-10-17, research/drafts/intl_pref_verify_2026-10-17.md): PASS survives.** No lookahead; yield filter is a no-op
  (n 12,462, +32.1 / +30.4 without it); issuer-clustered t 12 (+51bp issuer-mean) — the day-clustered t 31 overstated; 2023-25 +33.5bp (no
  decay); Yahoo .TO matches Datastream open/close/div on 28/28 sampled 2023-25 events. Unverified: retail IBKR MOO fill at the TSX open print,
  MOC eligibility for prefs, Roth withholding at IBKR (DTC says IRAs exempt; custodians often withhold 15%: +33 -> ~+13bp). Executable at $10k
  (5% of auction, 50% capture, auction = 10-25% of day volume): ~6-9%/yr at 0% withholding, ~2-3% at 15%. **Additive to US PREF-EX/ETDX
  (different auctions, capacity binds per market).**

## Study CEFX5 — CEF large-distribution (>5%/payment) ex-night at OFFICIAL crosses (pre-register 2026-10-18, N 1022 -> 1023)
`date`: Sun Oct 18 2026, before any official-cross number for this bin is read. Schwab-only ruling (2026-10-18) applies.
- **Already seen (touched):** FXD (N 868) REPORTED but did not judge the CEF y>5% bin on Sharadar vendor bars
  (`data/research/program/fxd_out.txt:12-13,34-35,62`): 1998-2004 xCC +123bp med +54 (n 45); 2005-26 xCO +98 / xCC +68,
  med +45, t 5.0, blocks +128/+85/+84/+77/+47 (2025 n 11). Vendor opens/closes only; official SIP crosses never read.
- **Mechanism.** Same clientele under-adjustment as PREF-EX, concentrated in rare large CEF distributions (year-end capital
  gain / special / ROC-heavy payouts) held by taxable retail; no creation/redemption arb in a CEF (unlike ETFs, where the
  >5% bin shows drop/div 1.01).
- **Rule (frozen = FXD rule, bin y > 5%).** SFP CEF, raw price >= $5, 20d median $vol >= $200k, regular-or-special cash
  distribution with ex-date T, y = div/close(T-1) > 5%, FXD dividend guard |div/P - y(closeadj)| < 10%. Buy the official
  closing cross T-1; sell the official closing cross T (CC, Schwab MOC both legs) [primary]; CO (official opening cross T)
  reported. Excess = same as FXD (minus the fund's mean non-ex return over the prior 60 sessions). Events 2021-01..2026-09.
- **Gate (one look).** CC excess net of 10bp round trip: mean >= +20bp AND median > 0 AND day-clustered t >= 2 AND
  ex-top-5 mean > 0; report 3x-cost, per-year, drop/div. Ceiling (stated now): ~13 events/yr x ~45bp x up to 100% of a
  $10k account x 50% capture ~ +3pp/yr: below the +8pp stand-alone gate, so a PASS = additive Roth-sleeve candidate only.
- **Kill.** Any gate leg fails, or the official-cross effect is < half the vendor-bar effect (vendor print artifact).
- Runner `research/sim/cefx5.py` -> `data/research/program/cefx5_out.txt`.

### Result — CEFX5 (2026-10-18, one run, N 1023)
Runner `research/sim/cefx5.py`, out `data/research/program/cefx5_out.txt`, official-cross cache `data/research/cefx5/auctions.json`. 68 events / 38 funds
(FXD CEF y>5% bin, 2021-01..2026-09); all 68 had both official crosses (0 missing, 0 unmappable tickers). Excess baseline = FXD vendor non-ex 60-session
mean; net = minus 10bp RT. **CC official: mean +15.2bp, median +21.6, day-t +0.46, ex-top-5 -17.4, hit 0.56**; CO official +52.4 (med +45.7, t +2.85,
ex-top-5 +24.1, hit 0.65) reported only. Vendor bars on the same events: CC +14.2 / CO +55.2 (official ~= vendor, so no print artifact). Drop/div 0.96.
3x cost CC -4.8bp. Per year CC: 2021 +45.8 (24), 2022 -13.0 (17), 2023 +34.7 (8), 2024 -36.1 (8), 2025 +15.5 (11). Median cross $ ~$10k (T-1) / $7k (T).
Gate: mean >= +20bp FAIL; median > 0 PASS; day-t >= 2 FAIL; ex-top-5 > 0 FAIL; official >= half vendor PASS. **VERDICT: KILL (primary CC arm).**
The CO arm looks better but is not the registered primary (no gate applied; Schwab has no MOO). No deviations. Do not retune bin/horizon.

### CEFX5-FWD (forward shadow arm, no N consumed, 2026-10-18)
Registered BEFORE any code. Forward measurement of a POST-HOC observation (CEFX5's CO arm; the registered primary CC arm was KILLED), not a pass.
- **Rule.** `cls="cef"` arm inside the PREF-EX shadow (`pref_ex_shadow.py`), log-only, never orders. Universe = the CEF-RV panel symbols
  (`state/cef-rv-panel.json`; arm skipped with a log line if absent), excluding ".PR" and ETD symbols. Alpaca cash dividend (non-special, non-foreign)
  with div / prior-session closing cross > 5% and <= 30%; prior close $5-60; ex-ante 20-session median closing-cross $ >= the shadow's MIN_CROSS.
  Scored exactly like the pref arm at official SIP crosses: buy E-1 closing cross, sell E opening cross (CO) / E closing cross (CC), dividend included,
  net of the shadow's COST (10bp RT) + modeled impact, own $10k ACCT split across the night's cef events only (never shares cash with pref/etd).
- **Gate.** 30 forward events (ex >= 2026-10-18). PASS = mean net CO >= +20bp, median > 0, day-clustered t >= 2. KILL = mean net CO <= +5bp at 30. Else HOLD.
- **Execution caveat.** CO needs an open-cross sell Schwab cannot place as MOO (the JRI CEF AUTO pre-open test filled at the official open, 0.0bp, 2026-10-10),
  so CC (MOC both legs, the Schwab-safe form) is reported beside CO. CEFX5 CC was +15bp / t 0.46 (KILL); CO +52bp / t 2.85.
- No live trading of this class: `pref_ex_live.CLASSES = ("pref", "etd")` must stay as is; any live use is a separate user decision after the gate.

## Study CRASH-B (N 1025, pre-registered 2026-10-18, BEFORE any outcome is read)
User goal: profit from a >=30% drawdown if one comes, acceptable bleed if not. Schwab-only; Roth allows long puts / debit spreads (options approval level UNVERIFIED).
Not a premium-harvest idea: the question is the payoff ratio of a rolled, fixed-budget tail position at FAR-SIDE fills.
- **Data.** OptionMetrics `optionm.opprcd{2005..2025}`, SPY secid 109820, cp_flag='P', strike = strike_price/1000, days-to-expiry 15..130; underlying + total return from `optionm.secprd`. Buy at best_offer, sell at best_bid (bid 0 = worth 0); short leg of a spread bought back at ask, sold at bid. No mid fills anywhere. Commission/exchange fees ignored (flagged).
- **Common rules (frozen).** Buy on the first trading day of each month, expiry nearest 90 calendar days (60-120 allowed), budget b = 0.10% of account equity per month (1.2%/yr max), fractional contracts in the model; whole-contract feasibility reported separately. Ladders stack (up to ~3 live). Proceeds go to cash (not re-spent beyond b).
- **Monetization (frozen, primary).** Sell the long put at bid when its delta <= -0.70 (delta from opprcd; if missing, Black-Scholes from impl_vol) or when DTE <= 21, whichever first. Reference arm M0 (no early sale, exit at DTE 21) reported, NOT used for the gate. Spread: same trigger on the long leg, both legs closed together.
- **Candidates (3, no others).** (1) PUT10: put strike nearest 90% of spot. (2) SPR: long 90% put / short 75% put (debit spread), spend b on spreads. (3) COND: PUT10 bought only when (3a) the put's IV is <= its own trailing-252-session 33rd percentile (IV series: nearest-90d 90%-strike put each day; needs 252 sessions so starts 2006), or (3b) SPY close < its 200d SMA. Both gate arms reported; skipped months spend nothing.
- **Gate (tightened, one look, primary monetization, calendar-year net P&L of the put book, bid-marked, after premium, % of account).** PASS needs ALL: net P&L 2008 >= 10x the annual budget (>= +12% of account) AND net P&L 2020 >= +12%, AND every non-crash year (all years except 2008, 2020, and 2022 reported separately) net P&L >= -(annual budget actually spent) [i.e. bleed <= budget], AND cumulative 2010-2019 bleed reported. 2022 reported honestly, not in the gate. COND arms: budget = what they actually spend; 10x test uses 12% for comparability and also 10x actual spend.
- **Combined book.** 100% SPY (total return) with b funded monthly by selling SPY, 2005-2025: report terminal wealth, CAGR, maxDD vs SPY alone. PASS-ECON additionally requires terminal wealth within -0.5%/yr CAGR of SPY alone... recorded as description only; the verdict is the payoff gate.
- **Kill.** Any gate leg fails for a candidate -> that candidate dies. All die -> class KILL (listed tail puts at fixed budget). Only 2 crash episodes exist (2008, 2020): a PASS is "not killed", not validated; 2005-2025 is entirely touched. No re-tuning of OTM, tenor, delta trigger, budget.
- Runner `research/sim/crash_b.py` -> `data/research/program/crash_b_out.txt`; note `research/drafts/crash_B_puts_2026-10-18.md`.

## Study CRASH-A — rule-based regime exit + inverse-ETF short on SPY (pre-register 2026-10-18, N 1023 -> 1024)
Question (user 2026-10-18): the best Schwab-executable way to profit if a >=30% SPY/QQQ drawdown happens, at an acceptable bleed if not. We do NOT assume a crash is coming; crash timing is not forecastable here (VTS, PLUM, MFLW, SHAR-CRASH all dead as timing signals). This tests only whether a trend rule is crisis alpha or a cost of insurance.
- **Rules (canonical, no tuning, at most 3).** All on SPY total-return (Sharadar SFP closeadj, 1998-2026). R1 Faber: month-end close < 10-month SMA of month-end closes. R2: daily close < 200d SMA x 0.99 (exit) / > SMA x 1.01 (re-enter), 1% band. R3 Moskowitz TSMOM: trailing 12-month total return (month-end) < trailing 12-month cash return. Risk-off state -> defensive book. Defensive primary D1 = 50% inverse (-1x SPY) + 50% cash; secondary D2 = 100% cash (reported, not gated).
- **Instruments.** Long = SPY closeadj. Inverse = SH actual 2006-06-21+, synthetic (-1x SPY total daily - 0.9%/yr + cash) before, labelled SYNTHETIC; synthetic is checked vs SH over the overlap. Cash = FRED DTB3 daily (BIL proxy, less 0.1%/yr). 60/40 = 60% SPY / 40% IEF monthly rebalance, 2002-08+.
- **Execution.** Signal on close t, trade at close t+1 (Schwab MOC; conservative, 1 day lag), so day d return uses the signal from close d-2. Cost 3bp per notional traded.
- **Gate (all must hold; D1).** (a) In each crash episode (SPY peak-to-trough: 2000-03-24..2002-10-09, 2007-10-09..2009-03-09, 2020-02-19..2020-03-23, 2022-01-03..2022-10-12) the rule account return beats buy-and-hold SPY by >= +15pp; (b) in non-crash years (all calendar years 1998-2026 except 2000,2001,2002,2008,2020,2022) geometric CAGR cost vs SPY <= 3pp/yr; (c) whipsaw count reported. A rule that fails (a) in 2020 is "slow", reported plainly.
- **Kill.** Any rule failing (a) in any episode or (b) = no crisis alpha; reported as insurance cost or nothing. No re-tuning of windows/bands. 1987-style one-day crash cannot be tested (data 1998+) and cannot be caught by any close-based rule: stated, not tested.
- Runner `research/sim/crash_a.py` -> `data/research/program/crash_a_out.txt`; memo `research/drafts/crash_A_trend_2026-10-18.md`.

## Study CRASH-C — buy forced CEF sellers in a >=20% SPY drawdown with a discount blowout (pre-register 2026-10-18, N 1025 -> 1026)
Source: user 2026-10-18 ("profit from a >=30% drawdown"), branch C. Mechanism: levered-CEF deleveraging / fund redemptions push CEF price below NAV
beyond what NAV falls; the price-vs-NAV wedge, not beta, is the forced-seller component. NOT INCOME-SHOCK ($25-par panic, killed) and NOT branch N.
Evidence question (2) ($25-par IG paper < $18) is NOT run: INCOME-SHOCK (N 1021) already measured it on 2008-07/2009/2020 and killed it. Question (3) is
answered from existing outputs (shar_crash_out.txt, nx_out.txt), no new N.
- Data: CEFConnect weekly price/NAV panel (data/research/cefconnect/cef_panel.parquet, 355 LIVE-to-2026 funds: survivorship stated, bias favours the rule);
  Sharadar SFP closeadj/closeunadj (TR); SPY from SFP. NAV TR = NAV_t x (adjfactor_t / adjfactor_0), adjfactor = closeadj/closeunadj.
- Trigger (frozen): first panel week with SPY close <= 0.80 x its trailing-252-session high AND EW-median universe discount (pct points) <= its own
  trailing-52-week median minus 3.0 points; 52-week lockout after a fire. Episodes expected 2008, 2020, 2022; a non-fire counts as non-positive.
- Selection: funds with >= 52 weeks of history at the trigger; bottom decile of (disc - own trailing-52w median) = widest blowout. Subsets reported:
  all deciles, and "levered proxy" = name category in {muni, taxable_fi, pref_conv} (cef_peer.CATS).
- Trade: three equal tranches, entry at the first SFP close strictly after the signal week, +4 and +8 weeks (selection fixed at trigger); each tranche exits at
  the first week disc >= the fund's pre-trigger 52w median, else 260 calendar days. Cost 50bp/side base (RT 1.0%), 2x = 2.0% RT.
- Metrics per episode (EW across funds): price TR, own-NAV TR (wedge = price - NAV), same-category EW NAV TR of all panel funds over the same window (primary
  comparator), SPY TR over the same window and EW-all-funds price TR (beta comparators). Primary excess = price TR - same-category EW NAV TR - cost.
- Gate (PASS): per episode mean primary excess >= +10%, median > 0, ex-top-5 funds mean > 0, still >= +10% at 2x cost; in >= 2 of 3 episodes. Else KILL.
  No change of trigger/decile/exit after reading. One run. Runner research/sim/crash_c.py; out data/research/program/crash_c_out.txt.

### Result — CRASH-A (2026-10-18, one run, N 1024): KILL all three rules (gate (b) fails; R1 and R3 also fail (a))
Out `data/research/program/crash_a_out.txt`. Episode excess vs SPY (D1, pp): R1 +66/+75/+39/+10; R2 +63/+62/+20/+16 (passes (a)); R3 +73/+68/0/+18. Non-crash-year CAGR cost: R1 8.4, R2 7.9, R3 5.9pp/yr (gate 3). Memo `research/drafts/crash_A_trend_2026-10-18.md`.
### Result — CRASH-C (2026-10-18, one run, N 1026): gate PASSES 2 of 3 (2008-09, 2020; 2022 fails), WEAK-PASS pending survivorship; no deployment
Out data/research/program/crash_c_out.txt. Fires: 2001-09-21, 2002-12-20 (extra, reported, both FAIL: +3.5%/+6.0% net), 2008-09-26, 2020-03-13, 2022-06-17.
Selected decile excess vs same-category NAV, net 1x / 2x cost: 2008-09 +17.3 / +16.3% (median +13.1, ex-top5 +9.8, SPY over window -0.5); 2020 +14.0 / +13.0%
(median +12.7, ex-top5 +8.7); 2022 -0.6 / -1.6%. Wedge is the source (2008 +26pp, 2020 +12pp); price TR is NOT beta-free in 2020 (+28.8% vs SPY +31%).
Caveats: live-fund panel (non-panel CEFs earned 12pp less than panel funds in the 2020 window), 3 effective episodes, 2008 tranche 0 priceTR -3%.

### CRASH-A extension (pre-register 2026-10-18, BEFORE any pre-1998 outcome is read; N stays 1024)
User clarified: a Great-Crash-scale event (1929-32, about -86%, multi-year, with sharp bear rallies). Same frozen rules R1/R2/R3, D1/D2, lag and cost; nothing re-tuned.
- **Data.** WRDS CRSP `crsp.dsi` vwretd (total) / vwretx daily from 1926 = "SPY" (VW index, NYSE-era, not investable; also NO dividend-cut/closure risk modelled). -1x synthetic = -vwretd - 0.9%/yr + cash. Cash = `crsp.mcti` t30ret (monthly, spread to daily /21). Long Treasuries b10ret/b20ret where present, reported only (not in the rules).
- **Windows (judge, pre-1998: untouched by any rule in the program).** W1 1929-09..1932-07 (index peak-to-trough by data), W2 1937-03..1938-03, W3 1973-01..1974-12, plus full 1926-1950. Rule return vs buy-and-hold per window; gate for the extension: D1 beats buy-and-hold by >= +15pp in W1 and W3 and non-crash-year bleed 1926-1950 (excl. 1929-32, 1937-38) reported vs the same 3pp tolerance.
- **Reports.** per-window P&L; whipsaw count in the 1930-31 bear rallies (spring 1930 about +45%); -1x leg path decay vs a static short from the 1929 peak; $ at $2.3k/$10k/$25k; systemic risks (listed in memo, not modelled). Optional evidence (not Schwab-tradable): Japan 1990-2003 via Datastream.
- **Kill.** Any gated window failed = no giant-crash alpha. Daily-data caveat: 1926-52 `dsi` daily exists; the rules use a 1-day lag as before.

### CRASH-C extension — Great-Crash-scale test on CRSP (pre-register 2026-10-18, before any output is read; N 1026 -> 1027)
User clarification: "crash" means 1929-32 scale (about -86%, false bottoms). Question: does early bottom-buying ruin the account, and which staging/confirmation rule survives?
- Data: WRDS crsp.dsi (daily vwretd, 1926+; total-return index, TR level = cumprod(1+vwretd)). Windows (peak = max TR level before the window trough): 1929-32, 1937-38,
  1973-74, 2000-02, 2007-09. Peak date = TR-level max in [window start - 1y, window start +1y]: 1929-01..1930-12... fixed as: 1929 [1928-01,1930-01], 1937 [1936-01,1938-01],
  1973 [1972-01,1974-01], 2000 [1999-01,2001-01], 2007 [2007-01,2008-01]; evaluation runs to peak+6 years or the first date the TR level regains the peak (the "break even" of the index).
- Rules (frozen, long-only, cash earns 0, no leverage, no costs beyond 0.25% per entry tranche):
  R1 staged: 1/3 of the account bought at close when the index is first -30%, -50%, -70% below its peak (a tranche that never triggers stays cash).
  R2 all-in at -30%. R3 trend-confirmed: all-in the first close after a >= 40% drawdown when the index close is above its 210-session SMA (about 10 months); sell back to cash
  if it closes below the SMA by 5% (one whipsaw exit allowed per window; re-entry by the same rule). R4 buy-and-hold from the peak (benchmark).
  R5 cheapest decile: on each entry date (R2 date) buy the decile of stocks with the lowest price/52-week-high (CRSP dsf, NYSE/AMEX common, share price >= 1, equal weight, held to window end)
  versus the index return over the same hold; report the excess.
- Metrics per window and rule: worst interim drawdown of the account from entry (peak-to-trough of the equity curve after first purchase), sessions from first purchase to account break-even,
  final value at window end, and dollars at $2.3k / $10k / $25k starting cash. Window end = the earlier of index recovery of its prior peak or peak+6y, capped by data.
- Gate (answer to the user question, no PASS/KILL of a strategy): "early bottom buying ruins" if R1 or R2 in 1929-32 has worst interim drawdown <= -50% of deployed capital and
  has not broken even by window end; a rule SURVIVES if in all 5 windows its worst drawdown >= -50% and it breaks even within the window. Report plainly; no rule edits after reading.
Runner research/sim/crash_c_great.py; out data/research/program/crash_c_great_out.txt. One run.

### Result — CRASH-A extension (2026-10-18, one run, N 1024): PASS on the extension gate, premium unchanged
`research/sim/crash_a_ext.py` -> `data/research/program/crash_a_ext_out.txt`. CRSP VW 1926-98, D1 excess vs VW: W1 1929-32 +101/+98/+86pp (R1/R2/R3), W2 1937-38 +56/+64/+44, W3 1973-74 +43/+63/+70 (gate >= +15 in W1, W3: all pass). 1930-31: 0 whipsaws R1/R3, R2 3 spells (2 lost ~2%). Non-crash 1926-50 bleed D1 R1 10.2 / R2 6.3 / R3 5.8pp/yr (D2 6.6/3.8/3.5): the insurance premium stays 4-10pp/yr. The VW index is not investable; Japan optional case not run.
### Result — CRASH-C extension (2026-10-18, one run, N 1027): early bottom-buying RUINS a 1929-scale account; only trend-confirmed re-entry survives all 5 windows
Out data/research/program/crash_c_great_out.txt. 1929-32 (index -84.0%): R2 all-in at -30% worst account dd -80.2%, final -25.5%, never breaks even in 6y; R1 staged
-30/-50/-70 worst -65.2%, final +12.8%, break-even 1,086 sessions; R3 trend-confirmed worst -36.8%, final +83.2%, break-even 901 sessions; buy&hold from the peak -84.0%.
R3 survives all 5 windows (worst dd -8.6..-36.8%, breaks even in all). Caveat: in 1929 R3 bought the April-1930 false bottom, was stopped out 4 weeks later (-21%), and only the
re-entry (Aug 1932) made +83%: the stop, not the entry, did the work. Cheapest decile (R5) from the -30% date: 1929 -0.5% with -80.8% dd; mixed elsewhere.

### Result — CRASH-B (2026-10-18, one run, N 1025)
Runner `research/sim/crash_b.py`, out `data/research/program/crash_b_out.txt`, note `research/drafts/crash_B_puts_2026-10-18.md`. Primary PUT10 net P&L 2008 +1.1% (0.9x budget), 2020 +2.4% (2.0x), 2010-19 cum -6.3% (spent 12.0%); SPR, COND-IV, COND-SMA all lower. Gate needed >= +12% both years: ALL FAIL. Combined with SPY: CAGR -0.5pp/yr, maxDD -55.2% -> -54.7%. Whole contracts need ~$170k+. MODEL 1929-32 (BS, not a backtest): ~+5.7% of account (4.7x budget) at k=1.68, 43.8x only at k=0.89 (generous). **VERDICT: KILL.** No re-tuning of OTM/tenor/trigger/budget.

## Study CRASH-D — inverse-ETF sleeve funded from T-bills, trend-gated (pre-register 2026-10-18, BEFORE any outcome is read; N 1027 -> 1028)
Question: CRASH-A priced the trend rules against buy-and-hold SPY. The live book is mostly cash/T-bills between trades, so the relevant cost of a crash sleeve is the sleeve's P&L (1x inverse index when the rule says risk-off, T-bills otherwise) minus T-bills, per unit of sleeve capital.
- **Rules**: the same three frozen CRASH-A rules R1 Faber 10m SMA, R2 200d SMA +-1% band, R3 12m TSMOM, signal at close t, trade close t+1 (held = state.shift(2)), 3bp of sleeve notional per switch. No tuning, none dropped.
- **Series**: CRSP VW total return 1926-01..1997-12 spliced to SPY (Sharadar total) 1998-01..2026-10; cash = CRSP t30ret (monthly) then FRED DTB3 - 0.1%. Inverse = actual SH from 2006-06, synthetic -1x daily (-r - 0.9%/yr + cash) before.
- **Measure**: sleeve excess = compounded(sleeve) - compounded(cash) over a window, as % of sleeve capital. Episodes: 1929-09..1932-07, 1937-03..1938-03, 1973-01..1974-12, 2000-03-24..2002-10-09, 2007-10-09..2009-03-09, 2020-02-19..2020-03-23, 2022-01-03..2022-10-12. Non-crash years = all calendar years except 1929-32, 1937-38, 1973-74, 2000-02, 2008, 2020, 2022 (2009 and 1933 stay in, as in CRASH-A). Whipsaw = risk-off spell whose sleeve excess < 0.
- **Gate (fixed now)**: average non-crash-year sleeve excess >= -2.0%/yr (1926-2026 is the gate window; 1998-2026 reported) AND sleeve gain >= +30% of sleeve capital in 1929-32, 1937-38 and 2007-09. Per rule. All three reported; picking the cheapest rule afterwards is a multiple-testing choice and is labelled so.
- Dollars: a 50%-of-account sleeve at $2.3k/$10k/$25k, 1929 replay and an average non-crash year. Kill: any rule failing either arm fails; no re-tuning.

### Result — CRASH-D (2026-10-18, one run, N 1028): KILL all three rules (arm (a) cost fails; arm (b) payoff passes)
Out `data/research/program/crash_d_out.txt`; memo `crash_D_overlay_2026-10-18.md`. Non-crash-year cost of the T-bill-funded inverse sleeve: R1 4.81, R2 4.06, R3 4.18 %/yr of sleeve capital (gate 2.0). Gains in 1929-32/1937-38/2007-09: R1 +142/+53/+52%, R2 +130/+59/+41%, R3 +129/+43/+46% (gate 30). All-years mean -2.8/-1.9/-2.2 %/yr. Cheapest per payoff R2 (57 vs 52/51) is a post-hoc pick within noise. No re-tuning.

### CRASH-D addendum — MODERN -80% test on QQQ (pre-register 2026-10-18, added BEFORE any QQQ output is read; user request; N 1028 same study)
Same three frozen rules, signal AND sleeve both on QQQ (Sharadar SFP total return, from 1999-03). Inverse = actual PSQ from 2006-06, synthetic -1x QQQ (-0.95%/yr + cash) before. Cash = DTB3 - 0.1%. Episode: QQQ close peak 2000-03-10 to trough 2002-10-09 (fixed now); R3 needs 12m of history so it cannot signal before 2000-03; reported as is. Non-crash years on QQQ = 1999-2026 minus {2000,2001,2002,2008,2020,2022}. Gate as CRASH-D (cost <= 2%/yr; gain >= +30% in the 2000-02 episode); also 2008 and 2020/2022 reported. Reported as its own row beside 1929. Nikkei 1990-2003 (WRDS Datastream) as evidence only, skipped if no clean index series. QQQ results do not change the verdict on SPY; no re-tuning.
### Result — CRASH-D addendum, QQQ (2026-10-18, one run): KILL on cost, payoff real
Out `crash_d_qqq_out.txt`. 2000-03-10..2002-10-09 QQQ -82.6%: sleeve excess R1 +99 / R2 +104 / R3 +104% of sleeve capital (gate 30 passes). Non-crash cost R1 7.13 / R2 7.81 / R3 6.22 %/yr (gate 2.0 fails). Weak in 2008 (+27%) and 2020 (0-5%). Nikkei skipped (no clean Datastream series).

## Study TAX-NOWASH — wash-sale-free design of TAX-STACK (pre-register 2026-10-18, BEFORE any output is read; N 1028 -> 1029)
Question: TAX-STACK (N 1017) pays only if the ex-date price drop is a usable ST loss (view A); wash sales (view B) turn $10k cash-only from +4.4 to -10.8pp. Does a design that never creates a washable loss rescue it?
- **Rule (taxable account)**: process nights chronologically; never BUY a pref/baby bond whose key had a LOSS sale (event net return after 10bp RT < 0, sold at the ex-date open) within the prior 31 days. (Buys within 30d before a later loss sale cannot be known ex-ante; they are counted as residual washes, not hidden.) Keys: (S) same symbol; (I) same-issuer proxy = pref ticker before '-' ; ETDX ticker[:-1] if len >= 4 (deliberately over-groups = conservative). Excluded rows are removed before the equal-split allocation (the dollars go to the other events that night).
- **Residual washes**: any loss sale with ANOTHER taxable buy of the key within +-30d of the sale. Tax treatment (conservative, deferral treated as permanent): residual washed losses get no ST-loss offset; the other losses offset STCG at 35% (view A). Everything else (data, events 2021-02..2026-09 official crosses, tier costs, whole shares, 5% of ex-ante auction $, idle-cash funding, 12.5% margin, BIL, night .65 / IBS .5 book, arms CASH night-first / CASH pref-first / MARGIN 2x) = tax_stack.py, imported not copied.
- **Roth overlap**: the live PREF-EX/ETDX runs in the Roth on the SAME nightly event set (5% cap). A taxable loss sale followed by a Roth buy of the same symbol/issuer within 30d is permanently disallowed (Rev. Rul. 2008-5). Primary arm "ROTH-CONCURRENT": Roth (assume $3k) buys every event with whole-share alloc > 0; any taxable loss on a key the Roth buys within +-30d of the sale is unusable. Secondary "DISJOINT": issuers split by a fixed hash parity, taxable trades only even issuers, the Roth the odd (the Roth gives up half its events; its P&L is not counted here).
- **Gate (fixed now)**: after-tax gain at $10k CASH-ONLY (pref-first, the TAX-STACK headline arm) >= +3.0pp/yr under view A with the exclusion applied (both keys; Roth-inclusive ROTH-CONCURRENT is the gated arm, no-Roth and DISJOINT reported) AND both halves (split 2024-01-01) > 0 AND 3x cost (RT 30bp) > 0. Otherwise KILL. Report % of events removed, $2.3k/$10k/$25k cash and margin. No re-tuning of the 31-day window or key.
Runner research/sim/tax_nowash.py; out data/research/program/tax_nowash_out.txt. One run.

### Result — TAX-NOWASH (2026-10-18, one design, N 1029): KILL as gated (Roth-inclusive); taxable-only wash risk was small, the Roth is the whole problem
Out `data/research/program/tax_nowash_out.txt`; runner `research/sim/tax_nowash.py`. **Disclosure**: v1 (kept as `tax_nowash_out_v1_netdef.txt`) defined "loss" as net-of-dividend return < 0; that is a tax-definition error (a wash-sale loss is proceeds < basis, price only, which is ~98% of events). v2 (final, reported here) uses price-only loss (co - dividend yield - rt < 0). Corrected after seeing v1 outcomes; no other change, no window/key tuning.
- Events removed by the rule: same-symbol 2% (134/7174), same-issuer proxy 10% (687/7174). Residual (earlier buy within 30d before a loss sale) washed losses: 6-7 of ~6,900 trades with the rule; WITHOUT the rule only 247 of 7,040 losses (3.5%) are washed by taxable buys alone (monthly payers are rare in the panel), so TAX-STACK view B (-10.8pp) overstated the taxable-only risk.
- After-tax pp/yr, CASH pref-first, view A with exclusion, no Roth overlap: $2.3k +8.0 (S) / +7.6 (I); $10k +4.4 / +4.4 (halves +4.8/+4.1, 3x cost +0.4/+0.5); $25k +2.7 / +2.5. MARGIN 2x: $2.3k +15.7/+15.8, $10k +7.4/+7.0, $25k +3.6/+3.4.
- **Roth overlap kills it**: the live Roth PREF-EX/ETDX buys the same nightly events, so 99.9% of taxable price losses have a Roth buy of the same symbol within 30d (permanent disallowance). With it: $10k cash -10.7 (S) / -10.0 (I) (halves -9.5/-12.1; 3x -17.0); $2.3k -17.5; $25k -6.9; margin $10k -17.9. Gate (>= +3pp at $10k cash, Roth-inclusive) FAILS.
- Escape (DISJOINT: taxable trades only even-hash issuers, Roth the odd): $10k cash +2.0 (halves +2.8/+1.1, 3x -0.3) FAILS +3.0; $2.3k +5.6, $25k +1.0; margin $10k +3.7. It also halves the Roth's events, which is not costed here.
- Verdict: taxable PREF-EX is viable only if the Roth does NOT trade the same symbols/issuers within +-30d of any taxable sale (or taxable skips pref entirely). Not both. Unverified: issuer proxy for ETDX tickers (over-groups), deferral vs permanent for taxable-only washes (modelled as permanent: conservative), Roth assumed $3k buying every event with whole-share alloc > 0.

## Amendment - Study SEL-NIGHT: the night leg's duplicate-bet survivor tie-break (pre-register 2026-10-18, BEFORE any pair-level return is computed; N 1029 -> 1030)

Motivation (measured 2026-10-18 from live logs on him): the night leg has no top-k; its only ranking decision that actually binds nightly is `signals.dedupe_correlated` (executor.py:1052-1056, keep whoever comes first in `day_ret`-ascending order). Live: taxable dropped 118 duplicate names over 17 sessions (57 on 10-16), Roth 130 over 14; buys otherwise equal the post-vol count (taxable cash never bound; Roth cash bound 4/14 sessions; 0-4 names/night die to whole-share rounding or the $150 probe cap). The survivor choice is therefore the one live selection lever that acts every night (~7 swaps/night).
Dead-list dedupe: idea_scan_2026-10-08 #1 (cross-sectional rank of same-day candidates) is DEAD - that ranked DISTINCT bets; here the bet set is fixed and only WHICH TWIN of one correlated bet is held changes. Study W (night_letf, dead) compared LETF picks vs same-vol non-LETF picks as groups; PQ1 (exclude LETF picks, dead) removed names; neither tested the within-pair survivor. Ceiling: ~2,000-4,000 twin-swaps/yr across both books x $10-150 notional/name; delta >= +15-30bp per swapped name moves >= +0.5pp/yr at $10k -> in gate range.
- **Pairs.** Frozen live rule on Sharadar SEP+SFP (delisted included, permaticker ids, raw-price filters; `research/sim/nx.py` loaders), 1999-01-02..2026-09-30, both universes (primary common; all-listed incl funds, reported). Each night: `loser_picks` then the exact `signals.dedupe_correlated`; every `(dropped, kept_as)` pair recorded with both names' overnight outcomes.
- **Outcome.** r(x) = next official open / close_t - 1 (NX scoring: unadjusted close, split at the open; delisting price or -100%). Pair-night delta_alt = r(alt survivor) - r(current survivor), bp.
- **Alternative survivor rules (fixed now, 6).** A1 least-beaten (last in day_ret order); A2 higher vol20 twin; A3 lower vol20 twin; A4 lower raw price; A5 higher ADV20; A6 random twin (placebo; must show ~0 or the harness is broken).
- **Gate per rule (its own direction).** n_nights >= 300; night-clustered t >= 2; mean, median, both halves (1999-2012 / 2013-2026) and ex-top-5-pair-nights all same sign as the rule's direction; AND the full-leg replay (same engine, survivor rule swapped in) improves leg bp/night by >= +0.5pp/yr at $10k. Otherwise NO CHANGE.
- **Kill.** All six (incl placebo) within noise -> survivor tie is neutral; record; current rule stands.
- **Windows.** Every window is touched for the LEG (NX 2003-15, CRSP-EARLY 1992-97, fitting 2021-23, live); no survivor rule was ever examined on any window. Pair test is within-night by construction (a period confounder cannot create a within-pair delta); leg-replay numbers are labelled not-OOS.
- Runner `research/sim/sel_night.py`; out `data/research/program/sel_night_out.txt`.

## Amendment - Study SEL-NIGHT-B: night-leg cash-starvation order (pre-register 2026-10-18; N 1030 -> 1031)

Motivation: when the Roth night budget binds, buys go in `day_ret`-ascending order (executor.py:1121) and the least-beaten tail starves (10-16: 12/41 skipped for cash; 10-08: 7/10; 10-05: 3/3). Alternatives: (A) current day_ret asc; (B) raw price asc (cheap-first, max names per dollar); (C) tilt weight desc (`night_tilt` value, deepest x most volatile first); (D) random.
- **Sim.** Frozen rule picks 1999-2026; per night target = per x w_i (live formula, node x crowd x gs); buy loop with whole shares, probe=1 share when target<1 and price<=$150, filling in the rule's order from a cash pool = kappa x sum(targets); kappa in {1.0, 0.5, 0.25} at book equity $2.3k/$4k/$10k. Metric: per-night total return ($ and bp on deployed), binding-nights count, and paired per-night deltas vs (A).
- **Gate.** An order beats (A) by >= +0.5pp/yr at $10k (paired night-clustered t >= 2, both halves same sign, ex-top-5 nights) else NO CHANGE. Kill: all orders within noise -> the starvation order is neutral; record.
- Runner same file; out same.

## Amendment - Study SEL-CEF: CEF-RV slot ranking among concurrent signals (pre-register 2026-10-18; N 1031 -> 1032)

Motivation: the live CEF-RV leg has `max_positions = floor(0.50 x equity / slot)` with `slot = max($500, min($1000, equity/10))` (cef_rv_live.py:68-73) and ranks candidates by `depth = discount(signal week) - trailing-52w median`, most negative first (cef_rv_live.py:121). At $1k Roth that is ONE slot vs ~12 open signals in the first live week; at $10k it is 5 slots vs ~45 signals/yr backlog. The slot choice has never been tested (CEF-RV/PEER/OOS studies assumed all signals taken).
- **Data.** `data/research/cefconnect/cef_panel.parquet` + all signals behind `cef_rv_trades.csv` (3,629 rows 2016-2026; edate/xdate/ret/disc_in/med/q10/hold_weeks; ret = the leg's recorded per-trade return, cost convention as in cef_rv.py, verified before results).
- **Test A (paired cohorts).** By edate: delta = ret(rank-1 by depth) - mean(ret(others)), bp; entry-date-clustered t; halves 2016-20 / 2021-26; ex-top-5; within-cohort Spearman(ret, depth) over all members.
- **Test B (slot simulation).** Chronological weekly replay at $2.3k/$10k/$25k: slots per live formula; free slot takes the rule's rank-1 among pool (signals not held/not exited); hold to the CSV xdate. Rules: R0 depth (current), R1 random, R2 newest signal, R3 shallowest. Compare $/yr and per-trade means vs R0 (block bootstrap by year).
- **Gate.** Adopt an alternative only if (Test B) it beats R0 by >= +0.5pp/yr at $10k AND (Test A) its delta_alt has t >= 2 with both halves same sign. Depth itself is "validated as principled" only if rank-1 >= cohort mean with t >= 2 in the positive direction; otherwise the tie is neutral and is reported as such (no change).
- **Kill.** No stable sign anywhere -> ranking neutral at these sizes; record and stop.
- **Windows.** 2016-26 is the leg's own validated data (touched by CEF-RV/PEER/OOS); the RANKING contrast is new on all of it; levels are in-sample and labelled.
- Runner `research/sim/sel_cef.py`; out `data/research/program/sel_cef_out.txt`.

## Amendment - Study SEL-PREF: PREF-EX/ETDX same-ex-date bundle ranking (pre-register 2026-10-18; N 1032 -> 1033)

Motivation: pref_ex_live.size() buys up to MAX_NAMES=3 candidates per ex-date ranked by yield = div/price descending (pref_ex_live.py:90). From `data/research/pref/events.parquet`: 47.7% of ex-dates have >3 candidates, carrying 88% of event volume (ETDX: 42%/82%). Live starts 2026-10-21 (0/30 trips so far); the ranking has never been tested.
- **Data.** `data/research/pref/{events,cross_rows}.parquet`, `data/research/etdx/{events,cross_rows}.parquet` (official crosses 2021-26; raw-close rows 2005-26 reported separately). Live-form capture (CC): (cc_T + div) / cc_{T-1} - 1 where cc = official closing cross (raw close when a cross is missing). CO form reported alongside.
- **Test.** On each ex-date with k > 3 candidates: delta = mean(capture of yield-top-3) - mean(capture of the rest); ex-date-clustered t; halves (2005-15 / 2016-26, and 2021-26 crosses); ex-top-5 dates; medians; 2x cost shock (10bp -> 20bp RT); within-date Spearman(capture, yield). Alternatives: div-$ absolute, cross-size, price, random top-3 (placebo).
- **Gate.** Adopt an alternative only if it beats yield-top3 by >= +0.5pp/yr at $10k (approx >= +20bp x ~250 trades x ~$200) with t >= 2 both halves same sign. Yield itself is "right" only if its own delta >= 0 with t >= 2 in the positive direction; otherwise the ranking is neutral/arbitrary and reported so.
- **Kill.** No stable sign anywhere -> neutral; record; do not change the live order silently.
- Runner `research/sim/sel_pref.py`; out `data/research/program/sel_pref_out.txt`.

(DSR note for all four: 16 alternative rules total are examined across these studies; the report applies a deflation for 16 trials to any passing cell.)

## RESULTS - SEL-NIGHT / SEL-NIGHT-B / SEL-CEF / SEL-PREF (2026-10-18, one look each; outputs data/research/program/sel_{night,night_b,cef,pref}_out.txt)
- **SEL-NIGHT (N 1030): current survivor rule STANDS; every alternative worse or neutral.** Sharadar 1999-2026, primary (common) universe,
  5,636 activity nights, 22,098 dedupe pairs on 1,591 nights (80% of nights have >= 1 dedupe). Leg bp/night vs current: A1 least-beaten
  -1.50 t -2.97 (h1 -1.10 / h2 -1.84, ex5 -1.90); A2 hi-vol -0.47 t -1.43; A3 lo-vol -1.22 t -2.48; A4 cheap -0.77 t -1.93; A5 liquid
  -0.58 t -1.61; A6 random -0.80 t -1.83. All-listed universe: same signs (A1 -1.43 t -2.09; A2 +0.08 t 0.18 = noise). Ann. Sharpe
  current 2.10 vs 2.01-2.07 (primary); 2.11 vs 2.09-2.16 (all): the current rule has the best mean and a tied Sharpe. Pair level: the kept
  (most-beaten) twin earns +207bp vs the dropped twin +47bp (median +132 vs +64; night-clustered t -2.74 on dropped-kept; 20/28 years;
  crash nights carry the mean, the night-weighted delta is ~-30bp). Kept twins are the higher-vol, lower-priced member (vol20 1.07 vs
  0.85): "most-beaten" = the leveraged/beta-heavier version, consistent with the vol-proportional premium. Placebo A6 ~0 at the pair
  level (t -0.2 all / -3.6 primary, pair-weighted). No alternative clears +0.5pp/yr; A1 is rejected in its own direction. NO CHANGE.
  Bug fixed before the judged run: `sel_night.py` indexed tickers from the pre-filter frame (df.index) instead of picks.index.
- **Ordering flaw measured (not a rule):** dedupe runs before the vol20 filter (executor.py:1052 then signals.night_sizing), so a kept twin
  that then fails vol20 silently kills its passing twin: 1,002 lost twins 1999-2026 (36/yr, 4.5% of pairs; all-listed 39/yr), mean r
  +19bp (all-listed +39). Upper bound if re-admitted: +30bp of leg budget/yr = +0.2pp/yr of equity (primary), +0.6pp (all-listed).
  Zero-cost code-order cleanup candidate (filter vol20 before the correlation walk); below the tie-breaker gate on the common universe.
- **SEL-NIGHT-B (N 1031): current cash-starvation order (day_ret asc) STANDS.** Names from the current rule, kappa x needed cash.
  kappa 1.0 binds 0.5-3.0% of nights; at kappa 0.5 (always binding): C tilt-desc +0.35-0.40 bp/night of leg t 1.2-1.5 (identical to A on
  93% of nights), B price-asc -1.2..-1.5 t -1..-1.3, D random -5.1..-5.5 t -4 (= -8..-9pp/yr of equity at w .65). kappa 0.25: same signs.
  Buying the deepest first when cash binds is right; cheap-first is worse; tilt order is a tie. NO CHANGE.
- **SEL-CEF (N 1032): live depth ranking VALIDATED as principled.** 3,731 trades / 404 multi-signal cohorts 2015-12..2026-09 (in-sample for
  the leg, new for the ranking). Test A: rank-1-by-depth minus cohort rest +277bp/trade, week-clustered t 6.21, median +290, hit 69%,
  halves +204 / +341, ex-top-5 +239; shallowest-first -179bp t -3.27; random +1.8bp t 0.04 (placebo clean). Within-cohort Spearman(net,
  depth) -0.26; terciles deep +617 / mid +435 / shallow +327bp. Deep picks also exit FASTER (8.9 vs 14.8 weeks): per week held +64bp
  t 6.1. Test B slot replay: R0 depth $2.3k +28.6%/yr (2 slots), $10k +27.0% (5 slots), $25k +21.0% (12 slots) vs random +9-11%/yr
  (R0 = 100th pct of 20 random seeds), newest +6-8%, shallow -0.1..+3%, oldest +7-11% (late entries credited with the original per-trade
  net: a bound). Levels are in-sample and the leg still waits on CEF-RV-FWD; the RANKING contrast is the finding. NO CHANGE.
- **SEL-PREF (N 1033): live yield-desc ranking VALIDATED; the research/shadow order (smallest cross first) is a worse ranking.**
  Official crosses 2021-26, live pool (PREF+ETDX): 411 of 857 ex-dates have k > 3 (6,527 of 7,265 events). CC form net 10bp: yield-top3
  minus rest +21.1bp t(date) 5.35, median +19, hit 61%, halves +19.6 / +22.5, ex-top-5 +18.2; CO +20.1 t 7.50. Alternatives paired vs
  yield-top3 (CC): div-$ -6.3 t -2.7; cross-asc (shadow/research order) -10.2 t -2.9; cross-desc -17.5 t -4.9; price-asc -12.4 t -3.5;
  random -14.0 t -3.9. Sharadar raw closes 2005-26 (916 multi-candidate dates): yield-top3 vs rest +15.9 t 4.08 (CC), +18.4 t 8.41 (CO),
  both halves positive, every alternative <= yield. Mechanism: capture is dividend-proportional under-adjustment (drop ~0.8 x div), so the
  highest yield carries the most bp. Worth ~+14bp x 3 names x ~72 dates/yr vs random = ~$60/yr at $200 tickets ($10k): principled, small.
  Flag (unchanged): live ranks by div / live last with no yield cap (shadow screens y <= 4%); a mis-keyed special dividend ranks first.
  NO CHANGE to the order; the shadow's allocation order understates the live rule.
- **Deflation:** 16 alternative rules across the four studies; the passing cells are the CURRENT rules (CEF depth t 6.2, PREF yield t 5-8),
  which survive a 16-trial deflation (max-of-16 null 95th pct t ~2.9). No alternative passes before or after deflation. Program N = 1033.

## Amendment - Study THEME-NIGHT: night picks in a "bubble" theme, and healthcare/biotech avoidance (pre-register 2026-10-18, user request; N 1033 -> 1034)

User hypothesis (2026-10-18): inside the night leg, prefer dips in the theme that is currently the speculative mania (e.g. quantum 2025-26)
and avoid medtech/biotech drops. Dead-list: CAT-MOM (N 912-914) tested the TOP HALF of categories by momentum (wrong sign, -7..-9bp);
HC-BAN (N 911-912) tested banning healthcare on 1999-2015 (-7.7bp t -1.4). This reopens both only in the forms not yet examined: the
EXTREME theme state (mania tail, not top half) and healthcare/biotech on 2016-2026 (never judged by HC-BAN). Declared a reopen, not new ground.
- **Data.** Kept night picks from SEL-NIGHT's current-rule replay (`sel_night_names_primary.parquet`, Sharadar common stocks 1999-2026,
  r = close -> next official open, delisting-complete) joined to Sharadar `tickers` sector/industry. Industry daily EW return = mean log
  close-to-close return of all SEP common stocks with prior close >= $5 in that industry (>= 10 members that day).
- **Theme state (fixed now).** mom126(ind, t-1) = sum of the industry EW log returns over the 126 sessions ending the PRIOR session.
  BUBBLE = industry in the top decile of mom126 across industries that day AND mom126 >= +0.40 (log, ~+50%). Anchors reported: top-half
  (CAT-MOM replication), bottom decile, and vol state (industry 20d EW vol top quintile) x BUBBLE.
- **Arm T1 (bubble tilt).** Paired same-night: delta = mean r(picks in BUBBLE industries) - mean r(other picks), nights with both present.
  User's prediction: delta > 0. Gate: n_nights >= 150, day-clustered t >= 2, both halves (1999-2012 / 2013-2026) same sign, ex-top-5
  nights same sign, median same sign, placebo (industry labels permuted within night, 200 draws) p <= 0.05, and leg ceiling >= +0.5pp/yr
  at $10k (delta x share of picks re-weighted x leg weight). Either sign qualifies as a finding; a tilt is adopted only in the measured sign.
- **Arm T2 (healthcare/biotech avoid, 2016-2026 judge; 1999-2015 reported as HC-BAN's window).** Paired same-night: delta = mean r(picks
  with sector Healthcare) - mean r(other picks); sub-arm biotech/medical-devices industries only. User's prediction: delta < 0 (avoid).
  Same gate, plus the avoid-rule leg replay: drop those picks, re-normalise weights, bp/night vs current.
- **Descriptive only (no gate): quantum 2024-26.** Picks in IONQ/RGTI/QBTS/QUBT/ARQQ/LAES/QMCO-like names and their 2x ETFs: count, mean
  and median r, vs the same-night other picks.
- **Kill.** Any gate fails -> the theme/sector dimension of night-pick selection is CLOSED at the extreme tail too; no further sector,
  theme, or industry conditioning on the night leg without a new data source. Ceiling note: any pick-level tilt acts on a ~4%/yr leg.
- Runner `research/sim/theme_night.py`; out `data/research/program/theme_night_out.txt`.

## RESULT - THEME-NIGHT (N 1034, 2026-10-18, one look): KILL both arms; theme/sector conditioning on night picks CLOSED at the extreme tail too
- T1 bubble tilt (1,907 picks in top-decile-momentum industries, 328 nights): delta in-minus-out -7.7bp, night t -0.36, halves -40 / +30
  (flip), perm p 0.72; x vol-top-quintile -21.9 t -0.99. Up-weighting x2 changes the leg by -0.06 bp/night; dropping them +0.33 t 0.64.
  Anchors: top-half momentum +2.6 t 0.20 (CAT-MOM form, now ~0 on the delisted-complete panel), bottom decile +9.9 t 0.62. Mania-theme
  dips bounce like any other dip. User's prediction (delta > 0) not supported; the opposite tilt is not supported either.
- T2 healthcare avoid, judge 2016-26 (2,764 HC picks / 1,068 nights): -34.4bp t -1.68, med -14.6, halves -15 / -42, ex-top-5 -52,
  ex-bottom-5 -6.7, perm p 0.105. Biotech+devices: -43.9bp t -1.87, perm p 0.050, ex-bottom-5 -8.7. Leg replay dropping them with
  re-normalised weights: HC +0.43 bp/night t 0.16 (~+0.7pp/yr at w .65), bio -0.11 t -0.04. The per-night deficit is carried by a handful
  of nights (2017, 2022, 2024) and vanishes at the leg level because those picks already carry small weights. 1999-2015: HC +0.2 t 0.01,
  bio -10 t -0.37 (matches HC-BAN). FAILS the gate (t < 2, outlier-carried, leg ceiling < +1pp and insignificant). No avoid rule.
- Quantum 2024-26 (descriptive, no gate): 52 picks / 41 nights, mean +47bp med +79 vs +62 for the other picks on those nights. QMCO
  (Quantum Corp, storage, mis-listed in the registered set) is -487bp x 10; the computing names IONQ +213 (n 12), RGTI +128 (10), QUBT
  +108 (9), ARQQ +135 (9), QBTS/LAES 1 each. 42 picks is not evidence; the leg already buys these names on every -8% day.
- Kill rule applies: no further sector, theme, industry or "next bubble" conditioning on the night leg without a new data source.
  Runner research/sim/theme_night.py; out data/research/program/theme_night_out.txt. Program N = 1034.

## Amendment - Study SSR-NIGHT: Rule 201 short-sale restriction state as a night-pick selector (pre-register 2026-10-18, before any outcome; N 1034 -> 1035)

Mechanism: Rule 201 (effective 2011-02-28) switches the uptick test on for the rest of day T and all of T+1 once a stock's price falls
10% below the prior close. At the T+1 09:30 open, where the night leg sells, short sellers cannot hit the bid in SSR-on names. Named
constrained counterparty: short sellers. The program confirmed the mechanism from the lift side (SSR-LIFT, N 860: -43bp diff-in-disc
on the lift day). Prediction: among night picks, SSR-on names open higher than otherwise-identical SSR-off names, post-2011 only.
- **Data.** SEL-NIGHT kept picks (current rule, Sharadar common stocks 1999-2026) + Sharadar daily low/prev close (raw). low_ret =
  low_T / close_{T-1} - 1. SSR-on at the T+1 open = low_ret_T <= -10% OR low_ret_{T-1} <= -10%. Daily close stands in for 15:40 (labelled).
- **Design (RD / diff-in-disc).** Bins of low_ret, 0.5pp wide. Discontinuity D = mean r(bin [-10.5,-10)) - mean r(bin [-9.5,-10)),
  computed within night (same-night pairs, picks of both bins present) and pooled. Trend control = mean of the adjacent-bin steps
  ([-10,-10.5) vs [-10.5,-11)) and ([-9,-9.5) vs [-9.5,-10)). diff-in-disc = D - trend. Judge 2011-03..2026-09; placebo 1999-2010
  (no rule: must be ~0); adjacent-cutoff placebos at -9% and -11% post-2011 (must be ~0). Secondary: SSR-on vs SSR-off within night among
  picks with close day_ret in [-9.5%, -8%] (band where both states occur).
- **Gate.** Post-2011 diff-in-disc > 0, night-clustered t >= 2, halves 2011-18 / 2019-26 same sign, ex-top-5 nights same sign, median
  same sign; pre-2011 placebo |t| < 2 and |effect| < half the post-2011 one; adjacent cutoffs clean. Ceiling check: effect x share of
  picks affected x leg weight >= +0.5pp/yr at $10k, else report-only. Kill: any gate fails -> SSR state is not a night-pick selector;
  class closed (the last mechanism-based selector on the leg).
- Runner `research/sim/ssr_night.py`; out `data/research/program/ssr_night_out.txt`.

## Amendment - Study PATTERN-NIGHT: multivariate ranker over everything knowable at the close (pre-register 2026-10-18; N 1035 -> 1036)

User question (2026-10-18): "there must be a common pattern among the picks that worked". This is the strongest form of that search the
data allows: one learner over all pick-level features at once, pairwise within night, judged on years it never saw. Prior univariate
scans (NDISC 47 x 210 buckets), random-rule batches (LUCK-B1..B6) and Study E (ml_picker, 15:50 features 2021-26) found nothing; a
multivariate pass on the 28-year delisted-complete panel either finds the pattern or closes the class.
- **Sample.** SEL-NIGHT kept picks 1999-2026 (primary), r = close -> next official open. Label = r demeaned within night, winsorised at
  +-50%.
- **Features (fixed now, all known by the close of T).** day_ret, ibs, vol20, log adv, log price, low_ret, high_ret, gap (open/prev
  close), ret5, ret20, ret63, ret252 (adjusted, ending T-1), distance to 252d high, volume / 20d median volume (full-day proxy),
  prev-day low_ret, SSR flag, repeat-pick flag (picked in prior 5 sessions), n_picks that night, SPY day return, day of week, sector
  (11 one-hots). No names, no future data, no fundamentals (FUND-STATE dead).
- **Model.** sklearn HistGradientBoostingRegressor (max_iter 300, lr 0.05, max_leaf_nodes 15, min_samples_leaf 200, l2 1.0; fixed, no
  tuning). Fit 1999-2015 -> judge 2016-2026 (primary). Walk-forward expanding by year from 2006 (secondary). Ridge on the same features
  as the linear anchor.
- **Judge.** Within night: top-half by prediction minus bottom-half (nights with >= 4 picks), night-clustered t; Spearman(pred, r) per
  night; prediction-decile means; both halves 2016-20 / 2021-26; ex-top-5 nights. Placebo: 20 fits on within-night-shuffled labels; the
  real top-minus-bottom must exceed the placebo 95th percentile. Leg replay: shipped weight form clip(1 + 0.25 z_pred, 0.25, 2)/mean
  applied to the current per-name weights -> bp/night vs current. Permutation feature importance reported (which features carry it).
- **Gate.** Top-minus-bottom >= +20bp, t >= 2, both halves same sign, ex-top-5 same sign, placebo-beaten, and leg replay >= +1pp/yr at
  $10k. Kill: pattern search on night picks is CLOSED as a class; do not re-run with another learner or feature list without new data.
- Runner `research/sim/pattern_night.py`; out `data/research/program/pattern_night_out.txt`.

## RESULTS - SSR-NIGHT (N 1035) and PATTERN-NIGHT (N 1036), 2026-10-18, one look each (picks deduplicated to the current-rule rows; a first pass on a file carrying one row per survivor rule was discarded)
- **SSR-NIGHT: FAIL.** 24,417 picks; 76% of post-2011 picks are SSR-on (the -8% close with IBS < 0.1 usually means the low crossed
  -10%), so the RD lives in a thin band. Post-2011 within-night step at -10%: +74bp, night t 1.32, median +8, hit 0.51, ex-top-5 nights
  -8.9bp (outlier-carried); pooled +5.5bp. Pre-2011 placebo (no rule) +19bp / diff-in-disc +33: not clean. Adjacent cutoffs -16 / +18 =
  noise of the same size. Secondary band test (close -8..-9.5%, SSR-on vs off, same night): +2.2bp t 0.19 post-2011, -7.6 pre-2011.
  Rule 201 state does not move the next open for these names: by the time a name qualifies for the leg, short pressure at the open is
  not the marginal flow. Kill rule applies: the last mechanism-based night-pick selector is closed.
- **PATTERN-NIGHT: FAIL (gate), with the one real pattern named.** 31 close-time features, GBM fit 1999-2015 -> judge 2016-26 (809
  nights): top-half minus bottom-half +29.1bp, t 1.63, median +14.5, hit 53.5%, halves +11 / +35, ex-top-5 +6.6; Spearman 0.024;
  beats the shuffled-label placebo 95th pct (+20.8) narrowly. In-sample +118bp t 9.7 (Spearman 0.16): the usual fit-then-fade.
  Ridge -10.6 t -0.62. Walk-forward 2006-26: +14.3bp t 1.05, ex-top-5 +1.4, 11/17 years > 0. Leg replay with the shipped tilt form:
  +1.6 bp/night t 1.4 (judge), +1.1 t 1.3 (walk-forward). Permutation importance: vol20 carries +26 of the +29bp, then low_ret and
  day_ret: the learner re-discovers the vol/depth tilt the leg already runs (night_tilt k .25); nothing else is in the residual. Fails
  t >= 2, ex-top-5 >= 20, and +1pp at t >= 2. Class closed: no further learners or feature lists on night-pick selection without new data.
- Runner research/sim/pattern_night.py; outputs data/research/program/{ssr_night,pattern_night}_out.txt. Program N = 1036.
- Follow-up noted, not registered: the decision-to-auction gap (15:43 submit vs 16:00 close) costs ~half the edge per NX's daily-close
  vs 15:40 comparison; a later submit (as close to the exchange MOC cutoff as Schwab allows) is a TIMING study on the 2016-26 minute
  panel, not a selection study, and is the one night-leg lever left with a known upper bound.

## Amendment - Study NIGHT-TAU: decision time of the night leg (pre-register 2026-10-18, before any outcome; N 1036 -> 1037)

Mechanism: the leg is paid for providing liquidity into the close; the entry is the 16:00 auction regardless of when the decision is
made, so a later decision only improves the INFORMATION about the closing state (which names are still -8% at the low). NX measured
the rule at the actual close at ~1.7x the 15:40 rule. The bot submits at ~15:43. Question: how much of that gap is recoverable at times
Schwab can still place a MOC order (NYSE cutoff 15:50, Nasdaq 15:55).
- **Data.** `data/research/night/lm1` + `data/research/recent/lm1`: SIP minute bars 15:30-16:00 for every name whose daily low
  touched -8% (eligibility superset), 2020-11-05..2026-10-07, plus the daily panel (`panel()`) for prev close, H/L, vol20, ADV20,
  close and next open. Same code path as `research/sim/recent_night.py`. No pre-2021 minutes exist past 15:40 (not fetched).
- **Rule at tau.** For tau in {15:35, 15:40, 15:45, 15:48, 15:50, 15:52, 15:55, 15:58, 15:59, close}: p = last minute close <= tau
  (close: the daily close), H/L through tau (day extreme if it occurred before tau, else running extreme), day_ret = p/prev_close-1
  <= -8%, IBS < 0.10, p in [5, 2000], vol20 >= 0.60, ADV20 >= $10M. Entry = daily close, exit = next daily open, r = open/close - 1.
  No dedupe/tilt (equal weight); leg proxy per night = min(1, 0.15 x n_picks) x mean r (the live per-name cap, no crowd scaling).
- **Report per tau.** n picks, nights, mean/median r bp, day-clustered t, hit, at 0 and 7.5bp/side; per year; set change vs 15:40
  (common / added / dropped and each group's r); paired per-night leg delta vs 15:40 (nights where either has picks), day-clustered t,
  halves 2020-11..2023-06 / 2023-07..2026-10, ex-top-5 nights, median.
- **Gate (per tau, its own cell).** Leg delta vs 15:40 >= +1.0 bp/night (~+1.6pp/yr of equity at w .65), paired day-clustered t >= 2,
  both halves same sign, ex-top-5 same sign. Feasible set = tau <= 15:48 (NYSE names) / 15:53 (Nasdaq names); later taus are the
  ceiling only. Nine taus examined: deflate (report the max-of-9 null t ~2.6 alongside). Window is the leg's own 2021-26 (touched);
  the timing contrast is new on all of it and is within-night by construction.
- **Kill.** No feasible tau clears the gate -> the 15:40 decision stands; record the ceiling at the close for the record.
- Runner `research/sim/night_tau.py`; out `data/research/program/night_tau_out.txt`.

## RESULT - NIGHT-TAU (N 1037, 2026-10-18, one look): KILL in the feasible window; the "close" edge is the auction print, not clock time
- lm1 minute panel 2020-11..2026-10, 1,485 sessions, ~14-15k picks per tau. Per-pick gross r: 15:35 +24.3, 15:40 +25.5, 15:45 +22.2,
  15:48 +24.1, 15:50 +22.0, 15:52 +29.2, 15:55 +36.0, 15:58 +37.7, 15:59 +37.9, close +46.7bp. Leg proxy (min(1, .15n) x mean r):
  15:40 +24.7 bp/night; paired deltas vs 15:40: 15:45 -2.1 (t -0.9), 15:48 -1.1 (t -0.4), 15:50 -3.3 (t -1.1), 15:52 -0.6 (t -0.2),
  15:55 +0.1 (t 0.04, halves +5.9 / -4.6), 15:58 +1.8 (t 0.5), 15:59 +1.3 (t 0.4), close +9.4 (t 2.56, both halves, ex-top-5 +7.0).
  No feasible tau (<= 15:48 NYSE / 15:53 Nasdaq) clears any gate; none is even positive. The pick set is ~fixed by 15:35 (11.7k of 14.1k
  common); late additions after 15:55 earn +32-53bp and the names that recover after 15:40 earn ~0, but that information exists only in
  the last 1-2 minutes and in the auction print itself (the 16:00 cell is a look-ahead: it conditions on the closing price).
- Reading: NX's "rule at the close earns ~1.7x" (here 1.38x) is not a decision-time effect; it is the closing auction's own information
  (a sell-imbalance print at the low), which the ledger already tested as the closing-imbalance feed (dead, paid). Decision time stands at
  the current ~15:43 submit; moving it earlier or later within the MOC window changes nothing. Timing on the night leg is CLOSED.
- Runner research/sim/night_tau.py (builds the daily panel from sipd parquet; data/research/night/panel.pkl no longer loads under pandas
  2.2.3, left untouched); out data/research/program/night_tau_out.txt, picks night_tau_picks.parquet. Program N = 1037.

## Amendment - Studies SEQ-NIGHT (A) and SEQ-ENTRY (B): indicator SEQUENCES as a ranker and as an entry (pre-register 2026-10-19, before any outcome; N 1037 -> 1039)

User question: "hundreds of indicators mixed together could create a working signal". Every indicator is a transform of OHLCV, so a
single model over a wide, sequence-shaped feature set searches every hand-mix at once. PATTERN-NIGHT (N 1036) tested SNAPSHOT
features only (today's values); a trader's combo is a sequence (squeeze held k days then released, histogram run then flip, divergence
over 20 bars). Sequences are untested here. Two labels on one feature set.

- **Features (shared, ~150, computed at the decision bar T from the 60 prior daily bars, Sharadar raw OHLCV, no look past T).**
  Sequences: TTM squeeze state (BB(20,2) inside Keltner(20,1.5)) days-on, days-since-release, momentum-histogram sign and run
  length; Squeeze Pro compression level (KC 1.0/1.5/2.0); Explosive-bandwidth (60d mean BB width > 30 and current < 15, and the
  ratio); MACD(12,26,9) histogram sign run length, days since cross, slope; RSI(14) level, days < 30 / > 70, bullish/bearish
  divergence over 20 bars (price lower low, RSI higher low); RSI-Laguerre(0.8) state; ADX(14) level, DI cross age; Hull MA(20)
  concavity and days since turning point; SlimRibbons alignment (8/13/21/34/55 EMA stack order, days held); SMA 20/50/200 stack
  state and age, days since each cross; Three-weeks-tight (15-day close range < 1.5%); consecutive down/up days, count of <= -3% days
  in 20; days since 52w high / low; volume climax (vol > 3x 20d median) age, dry-up (< 0.5x) run; gap count in 20; "buy the dip"
  proxy (close near 20d low, RSI < 30, above SMA200); plus PATTERN-NIGHT's snapshots (ret5/20/63/252, dist_hi, volratio, vol20,
  log_adv, log_px, gap, low_ret, day_ret, ibs). Excluded: the forum's most-viewed "Repainting Trend Reversal" (it repaints: uses
  future bars). Scan sources: usethinkscript threads 2751 (TTM), 4021 (Squeeze Pro), 3840 (bandwidth), 1094 (3-weeks-tight),
  3553 (buy the dip), 8853 (common set: Hull, MACD_BB, RSI, ADX/DMI, Squeeze Pro).
- **Model.** HistGradientBoostingRegressor (max_iter 300, lr .05, 15 leaves, min_leaf 200, l2 1.0), Ridge anchor; fit 1999-2015,
  judge 2016-2026, one look; 20 shuffled-label (within-day) placebo fits; permutation importance; walk-forward by year as a secondary.
- **A: SEQ-NIGHT (N 1038).** Rows = SEL-NIGHT current-rule picks (`sel_night_names_primary.parquet`, rule == current, 24,417 picks
  1999-2026; daily-bar proxy of the 15:40 rule, same as PATTERN-NIGHT). Label = r minus the night's mean r (clip +-50%). Judge:
  within-night top-half minus bottom-half of predicted score, bp, day-clustered t; quintile means; leg replay as tilt (k .25) and as a
  FILTER (drop the bottom predicted quintile, cap .15n). Gate: top-minus-bottom >= +15bp, t >= 2, halves 2016-20 / 2021-26 same sign,
  ex-top-5 nights same sign, beats the placebo 95th pct, AND either tilt gain >= +0.5pp/yr or filter gain >= +1.0pp/yr of equity at
  w .65 (the SEL task's own bars). Kill otherwise; a pass carried by vol20/day_ret alone (permutation importance) = the live tilt, KILL.
- **B: SEQ-ENTRY (N 1039).** Universe = Sharadar common stocks (SEP, category Domestic/ADR common), closeunadj >= $5, ADV20 >= $10M,
  every trading day 1999-2026 (train rows subsampled to ~1.5M for the fit; judge on all 2016-26 rows). Two labels, both fixed now:
  L1 = next open / close - 1 (one night, auction-to-auction) and L3 = close(T+3) / close(T) - 1, each minus SPY over the same window.
  Portfolio: each day long the top decile of predicted score, equal weight (L3: 1/3 of capital per daily cohort), 10bp round trip.
  Judge 2016-26: mean net excess per trade, day-clustered t, median, hit, halves 2016-20 / 2021-26, 2022 alone, ex-top-5 days,
  placebo 95th pct; alpha vs window-matched SPY beta (t); and total 2016-26 net return vs holding QQQ (MODERN-XS bar). Gate (per label,
  its own cell): net excess >= +5bp per night (L1) / >= +15bp per 3d trade (L3), t >= 2, both halves and 2022 positive, median > 0,
  ex-top-5 positive, placebo beaten, alpha t >= 2, and the leg beats QQQ hold 2016-26 after costs. Kill otherwise. Four cells
  (A, B-L1, B-L3, walk-forward secondary): deflate; a single marginal pass is a NO.
- **Kills the class if empty:** any hand-mixed combination of these indicators and sequences is a point in the space the model searched;
  if the model finds nothing out of sample, hand-mixing is the same search with worse statistics. Record as "indicator sequences:
  CLOSED" in NEXT.md. If A or B finds something, report WHICH sequences carry it (permutation importance) and whether it is a regime
  (2016-20 vs 2021-26) before anything is built.
- Runner `research/sim/seq_night.py` (builds features once to `data/research/program/seq_feats_*.parquet`); outs
  `data/research/program/seq_night_out.txt`, `seq_entry_out.txt`.

## Amendment - Study NIGHT-BAND: the night rule below the -8% cutoff (pre-register 2026-10-19, before any outcome; N 1039 -> 1040)

User question (after SEQ-NIGHT/SEQ-ENTRY): the fixed -8% cutoff was never chosen by a sweep (grep: every sim uses -0.08; CLAUDE.md lists
the fixed thresholds as an assumption to challenge). Mechanism: the same close-of-day liquidity provision; the reversal premium scales with
the size of the drop, so the question is whether the 4-8% band still pays after the ~1.7x daily-proxy optimism and costs, and how many
extra deployment nights it adds (the -8% pool has picks on ~31% of sessions).
- **Data.** Sharadar SEP common stocks 1999-2026 (delisted included), daily bars; the daily-close proxy of the live rule
  (close/prev_close <= cutoff, daily IBS < 0.10, closeunadj $5-2000, vol20 >= 0.60, ADV20 >= $10M; buy close, sell next open). All
  Sharadar years are TOUCHED for the -8% rule; this study is a within-night contrast of a NEW band against the known band, not an OOS
  claim. Minute (15:40) replay is impossible for the band (lm1 panels hold only names whose low touched -8%).
- **Arms.** Cutoff c in {-4, -5, -6, -7%}; band = picks with c <= day_ret < -8%... i.e. [c, -8%) excluding the live pool. Report per band:
  n, nights with picks, mean/median r bp, hit, day-clustered t, at 0 and 7.5bp/side, by year, halves 1999-2012 / 2013-26, ex-top-5 nights.
  Primary contrast: on nights where BOTH the -8% pool and the band have picks, band mean r minus pool mean r (paired, day-clustered t).
  Leg replay: current leg proxy min(1, .15n) x mean r on the -8% pool vs the union pool, per night over all sessions; delta bp/night and
  pp/yr at w .65; also the band ALONE on nights with no -8% pick (the added-nights value).
- **Gate (per band, its own cell).** Band mean r at 7.5bp/side >= +8bp (half the -8% pool's proxy level, i.e. ~0 after the 1.7x proxy
  haircut is the kill line), day-clustered t >= 2, both halves positive, ex-top-5 positive, median > 0; union-leg delta >= +1.0 bp/night
  (~+1.6pp/yr at w .65) with t >= 2. Four cutoffs examined: deflate (max-of-4 null t ~2.2).
- **If a band passes:** no live change; register a log-only 15:40 forward shadow (the executor's own signal path with the lower cutoff,
  scored at the official crosses) with a 60-night gate before any size. If none passes: record "night cutoff below -8%: dead at the
  daily proxy; not tested: exact 15:40 band replay (no minute data), band-specific IBS cutoffs".
- Runner `research/sim/night_band.py`; out `data/research/program/night_band_out.txt`.

## RESULT - NIGHT-BAND (N 1040, 2026-10-19, one look): FAILS the registered bar; UNPROVEN, forward shadow registered
- Sharadar daily proxy 1999-2026 (primary universe, no dedupe): live pool (<= -8%) n 41,037 mean +54.7bp (med +55.7, net +39.7 at
  7.5bp/side, t 10.3). Band (-8%, -4%]: n 74,827, nights 5,740, mean +17.9 (med +15.7), net +2.9 (bar was +8: FAIL), hit 53%,
  t 11.7, halves 1999-2012 +27.2 / 2013-26 +7.6, ex-top-5 +26.0; narrower bands (-5/-6/-7) +17.9..+18.5, same halves. Paired band
  minus pool on common nights -26..-29bp t -5. Union-leg replay vs the live pool: +3.5 bp/night t 3.3 (h1 +6.6 / h2 +0.8, ex-top-5
  +3.0, +5.7pp/yr at w .65 GROSS proxy) but -1.3 bp/night net of 15bp on the added exposure. Band alone on the 1,594 no-pool nights
  (26% of sessions): +28.7bp/name, +9.7 bp/night t 5.7.
- Reading: the band carries ~1/3 of the pool's premium and most of it pre-2013; after the ~1.7x daily-proxy haircut the 2013-26 band
  is ~+4bp gross, i.e. inside the live auction cost (measured ~0bp on fills). Not dead: right sign in every arm, mechanism shared with
  the live leg, and the added-nights value is real at 0 cost. Decided by forward prints only.
- **Forward shadow registered (user OK 2026-10-19): `swingtrader/daily/night_band_shadow.py`** (research-shadows, REGISTRY
  "NIGHT-BAND-FWD"): exact 15:40 state from SIP minutes on the live universe, band and pool rows, official close -> open crosses,
  gate 60 forward band nights, band EW-night mean >= +5bp gross, t >= 2, median > 0. Local 4-session backfill (10-12..10-15, look-
  alike): 47 names, band -154bp, pool -164bp (the week the live leg lost too). PASS = propose the lower cutoff; no live change.
- Not tested: exact 15:40 band replay (no minute history for names that never touched -8%); band-specific IBS cutoffs; the band
  under the live dedupe/tilt. Runner `research/sim/night_band.py`; out `data/research/program/night_band_out.txt`. Program N = 1040.

## RESULT - SEQ-NIGHT (N 1038) and SEQ-ENTRY (N 1039), 2026-10-19, one look each: both KILL as registered
- Features built: 105 per-name sequence/indicator states + market state (124 in A incl. sectors; 111 in B), Sharadar common stocks
  1999-2026, `research/sim/seq_night.py`, batches in `data/research/program/seq_feats/`.
- **A (SEQ-NIGHT, 23,166 of 24,417 picks covered): KILL.** GBM judge 2016-26 top-half minus bottom-half +18.3bp, t 1.10, halves +1.2 /
  +23.5, ex-top-5 -1.4; placebo 95th +32.4 (not beaten); tilt replay +1.1 bp/night t 1.0; filter (drop bottom quintile) +0.2 t 0.2.
  In-sample +169bp t 14 (memorises). Ridge +31.6bp t 2.09 (halves +43/+28, ex-top-5 +14.4 < 15 bar). Walk-forward 2006-26 +22.5 t 1.72,
  tilt +1.4 bp/night t 1.5 (+2.3pp/yr at w .65), by year positive through 2022 then 2023 -60 / 2024 -51 / 2025 -24. Top features:
  range_pct, rsi_chg5, ribbon_width, bear_div_age, age_c_s200. No cell clears the gate; the Ridge/walk-forward tilt is UNPROVEN
  (NEXT.md unproven table), not a pass.
- **B (SEQ-ENTRY, 5.5M judge rows 2016-26, 204 names/day in the top decile): KILL both labels.** L1 (one night): net excess vs SPY
  +0.1bp/trade t 0.09, median -1.2, 2022 -11.5, beta 1.62, alpha -1.9bp t -1.5, total 2016-26 +100% vs QQQ +640%. L3 (3 days):
  +0.7bp t 0.11, median -7.3, beta 1.48, alpha -8.2 t -1.4, +373% vs +630%. Ridge same. Both beat the shuffled-label placebo
  (placebo top deciles are -5.8 / -14.6bp: the universe's own negative excess), and the predicted deciles are MONOTONE
  (L1 -4.8 .. +8.8bp; L3 -35 .. +7.4bp): the sequence model does rank stocks out of sample, but the long top decile is ~+9bp gross
  per night, below a 10bp round trip, and most of the spread is the bottom decile (the unshortable side, as in BORROW-XS/SSR-LIFT).
  Walk-forward L1 2006-26 +3.8bp net t 3.9 (2006-13 +7..+20bp/night, ~0 since 2014); 2016-26 only +1.4 t 0.9. Top features:
  spy_ret20, dist_hi, spy_c_s200, ibs, breadth200 (market state and the IBS snapshot, not the sequences).
- Answer to the user's question ("hundreds of indicators mixed together"): a learned mix of 105 indicator sequences carries a real,
  monotone, decaying ranking signal of ~10-15bp/night top-to-bottom in 2016-26; it is smaller than the cost of trading its long side
  and does not re-sort the night pool. Hand-mixed combinations are points in this space. **Indicator sequences: CLOSED as a long-only
  entry and as a night-pool ranker.** Not tested: minute-path sequences (15:30-15:40) as a night ranker; the short/avoid side of the
  B ranking as a filter on OTHER legs (bottom-decile avoidance; ceiling small); sequences on ETFs for the IBS leg. Program N = 1040.

## Amendment - Study BREADTH-GATE: market breadth as a leg-level gate on the night leg (pre-register 2026-10-19, before any outcome; N 1040 -> 1041)
Context: SEQ-ENTRY's permutation importance put market state first (breadth200, spy_ret20, spy_c_s200). Prior is LOW: REGIME-10M (N 919-922)
closed "trend/regime gates on the MR book" (a drawdown dial), NDISC bucketed SPY vs MA20/50/200 and 5d/20d returns on the night leg (dead).
Not previously run: breadth itself (share of the $5+/$10M universe above its own 200d / 50d SMA). Cheap (data already built): run as a
class-level falsification; if breadth behaves like SPY-vs-200d the class stays closed.
- **Data.** Night pool = `night_band_rows.parquet` (Sharadar daily proxy of the live rule, day_ret <= -8%, 1999-2026); per-night leg
  proxy min(1, .15n) x mean r over all sessions with a <= -4% candidate. Breadth = `seq_market.parquet` breadth200 / breadth50 (prior
  day's values: shift 1 session, no look-ahead), spy_c_s200 for comparison.
- **Rule.** Quintile breakpoints of breadth200 fit on 1999-2015; judge 2016-26: leg proxy per quintile; the frozen gate = OFF when
  breadth200 is in the bottom quintile (the only economically-motivated arm: broad selling = the bounce fails). Report ON/OFF means,
  the difference, day-clustered t, halves 2016-20 / 2021-26, ex-top-5, maxDD of the leg ON-only vs always-on, and the same for
  spy_c_s200 < 0 as the dead comparator.
- **Gate.** OFF-session leg mean < 0 in 2016-26 AND ON-minus-always-on >= +1.0 bp/night with t >= 2 AND both halves same sign; else KILL
  (an OFF arm that merely lowers maxDD while costing return is REGIME-10M again: a dial). One look.
- Runner `research/sim/breadth_gate.py`; out `data/research/program/breadth_gate_out.txt`.

## RESULT - BREADTH-GATE (N 1041, 2026-10-19, one look): KILL; regime-gate class stays closed
- Night-leg proxy 2016-26 by prior-day breadth200 quintile (breakpoints 1999-2015): +15.1 / +11.6 / +17.5 / +16.2 / +41.9 bp/night
  (fit era: +19 / +32 / +39 / +16 / +8: the ordering FLIPS between eras). OFF in Q1 (18% of sessions): OFF sessions still earn +15.1
  bp/night; ON-only minus always-on -2.8 bp/night t -1.4 (-4.5pp/yr at w .65), maxDD -49.7% -> -25.0%. breadth50: OFF sessions +1.3,
  delta -0.3 t -0.1. SPY<200d comparator -1.6 t -0.8; corr(breadth200, spy_c_s200) 0.89: breadth is the dead class in a new costume.
- Reading: as in REGIME-10M, a breadth gate is a drawdown dial that costs return; the night leg's OFF sessions are not losers. The
  SEQ-ENTRY importance of market state was the universe's beta timing, not a night-leg gate. Not tested: breadth as a SIZING dial
  (continuous weight) -- same class, ceiling < 1pp, do not run. Runner `research/sim/breadth_gate.py`; out `breadth_gate_out.txt`.
  Program N = 1041.

## Amendment - Studies MINPATH-NIGHT (N 1042) and CROWD-NIGHT (N 1043): pre-register 2026-10-19, before any outcome; N 1041 -> 1043

**MINPATH-NIGHT.** The night pool's variance lives in the last half hour (NIGHT-TAU: the pick set is fixed by 15:35, the outcome moves with
the auction print). Every ranker so far used daily history (PATTERN-NIGHT snapshots, SEQ-NIGHT sequences). Not tested: the 15:30-15:40
minute path itself as a within-night ranker.
- Data: `data/research/night/lm1` + `data/research/recent/lm1` minute bars (15:30-16:00) for the tau-15:40 picks of NIGHT-TAU
  (`night_tau_picks.parquet`, sig rows at tau 1540; 2020-11..2026-10, ~14.5k picks). Features from bars with hm <= 15:40 only:
  r_1530_1540, window low vs p40 (drawup from the window low), minutes since the window low, new-low-at-15:40 flag, window range /
  p40, VWAP(15:30-15:40) distance, share of down minutes, last-minute return, last-5-minute return, window $vol / (ADV20 / 39) (the
  per-10-minute baseline), $vol acceleration (last 5 vs first 5 minutes), plus day_ret, ibs, vol20, log_adv at 15:40.
- Model/judge: GBM (SEQ settings) + Ridge; fit 2020-11..2023-06, judge 2023-07..2026-10 (the NIGHT-TAU halves); label r - night mean
  (clip +-50%); within-night top-half minus bottom-half, day-clustered t, quintiles, 20 shuffled-label placebos, permutation importance,
  tilt (k .25) and filter (drop bottom quintile, cap .15n) replays. Gate as SEQ-NIGHT: >= +15bp, t >= 2, placebo 95th beaten, ex-top-5
  same sign, and tilt >= +0.5pp/yr or filter >= +1pp/yr at w .65. Kill otherwise; a pass carried by day_ret/vol20 alone = the live tilt.
- Runner `research/sim/minpath_night.py`; out `data/research/program/minpath_night_out.txt`.

**CROWD-NIGHT.** The live crowd rule (night_sizing: exposure x crowd_n / n when more than crowd_n = 30 names fire; h1port rule R6,
fit 2021-23: "-9bp vs +25bp on ordinary days") was never re-judged on a long delisted-complete panel. Mechanism either way: market-wide
selloffs = weaker idiosyncratic bounce (the rule) or = the high-vol regime where the premium is largest (NX: premium tracks vol).
- Data: `night_band_rows.parquet` pool rows (day_ret <= -8%, Sharadar daily proxy, primary universe, vol20 >= .6 applied, no dedupe),
  1999-2026; n = pool names per night. Judge 1999-2015 (the crowd rule never saw it; the leg LEVEL is touched by NX, the by-n contrast is
  not); report 2016-26.
- Report: per-name mean/median r, hit, day-clustered t by n bucket (1-5, 6-10, 11-20, 21-30, 31-60, 61+), both eras; leg per night under
  (a) live = min(1, .15n) x min(1, 30/n) x mean r, (b) no crowd scaling = min(1, .15n) x mean r, (c) crowd_n 60; delta (b)-(a) and (c)-(a)
  bp/night, t, halves, ex-top-5, maxDD of each leg; crowded-night (n > 30) count and share.
- Gate: (b) or (c) minus (a) >= +1.0 bp/night (judge era), t >= 2, both halves same sign, ex-top-5 same sign, maxDD no worse than (a) by
  more than 5pp. Else KILL (the rule stands). Either way record the by-n gradient as the mechanism read.
- Runner `research/sim/crowd_night.py`; out `data/research/program/crowd_night_out.txt`.

## RESULT - CROWD-NIGHT (N 1043, 2026-10-19, one look): KILL at the bar; the crowd rule is a wash, not a mechanism
- Per-name r by names-per-night, judge 1999-2015: 1-5 +65 / 6-10 +76 / 11-20 +68 / 21-30 +113 / 31-60 +67 / 61+ +34bp: NOT monotone
  in n; 2016-26: +54 / +37 / +31 / -18 / -7 / +133 (the 61+ bucket = 34 nights, 2020-03 and 2025-04 type crashes, med +140).
  Leg per night, judge era: live (x 30/n above 30) +21.89; no crowd scaling +22.85 (delta +0.96 bp/night, t 2.01, halves +0.74 / +1.22,
  ex-top-5 +0.49, maxDD -26.3% vs -26.2%); crowd_n 60 +0.74 t 2.71. 2016-26: no-crowd +0.54 t 0.76, ex-top-5 -0.44. Neither cell
  clears +1.0 bp/night with ex-top-5 agreement; the rule stands. Reading: "crowded = weak bounce" (h1port R6, 2021-23) does not hold
  across 27 years; crowded nights are neither reliably worse nor better, and the cap .15n already bounds the exposure. Changing
  crowd_n is a ~+1 bp/night gross-proxy question (< +1.5pp/yr) with the crash tail on the other side: leave it.
- Not tested: crowd scaling by market breadth of the selloff (share of the universe down > 3%) instead of pool size (same class,
  REGIME-10M/BREADTH-GATE say dial). Runner `research/sim/crowd_night.py`; out `crowd_night_out.txt`. Program N = 1043.

## RESULT - MINPATH-NIGHT (N 1042, 2026-10-19, one look): KILL
- 13,923 pick-rows (15:40 picks with 15:30-15:40 minutes), fit 2020-11..2023-06 -> judge 2023-07..2026-10 (552 nights). GBM top-half minus
  bottom-half +7.6bp t 0.37 (ex-top-5 -10.7), placebo 95th +21.4 not beaten; tilt +0.8 bp/night t 0.4; filter -4.4 t -2.1 (drops good
  names); in-sample +273bp (memorises). Ridge -18.9 t -0.9. Single features: only log_adv +56bp t 2.6 (liquid names bounce more; already
  known from NX/SHAR-SURV) and new_low -42bp t -2.1 (a fresh low AT 15:40 bounces less) reach |t| ~2 of 16 looks (max-of-16 null ~2.5).
- Reading: the last ten minutes before the decision carry no usable ranking beyond liquidity; the variance is in the auction print and
  after. With PATTERN (snapshots), SEQ (sequences) and MINPATH (path) all empty, **within-pool ranking of the night leg is closed in
  every representation tried.** Not tested: an explicit ADV tilt (log_adv +56 t 2.6 here, liquid +138 vs illiquid +91 in NX; unproven,
  ceiling < 1pp since the per-name cap already favours many names); the new-low flag as a skip (t -2.1 of 16, do not run alone).
  Runner `research/sim/minpath_night.py`; out `minpath_night_out.txt`, rows `minpath_night_rows.parquet`. Program N = 1043.

## Amendment - Study INTRA-ANY (N 1044-1045): pre-register 2026-10-19, before any outcome; N 1043 -> 1045

**Question (user, 2026-10-19).** Every live rule checks at a fixed clock time. The scalp loop (15 studies) tested condition-triggered
intraday entries, but all of them exited intraday (1-60 min) and were one family: hand-written setups or flow classifiers on the
stock's own tape. Not tested: a learned model that may fire at ANY intraday check time on ANY eligible name, with the exit at the
free closing auction (hours horizon, entry pays the spread once, exit 0bp). This is the streaming/"checker at any interval" form.
- Data: point-in-time minute panels already on disk. `data/research/volday/m1_*.parquet` (2016-01..2026-09; each month the 10
  highest-realized-vol names with ADV20 >= $500M, px >= $10, chosen from the prior month; full sessions) and
  `data/research/inplay/m1_*.parquet` (2019-01..2026-09; per day the 25 largest |gap| >= 1% names with ADV20 >= $200M and 10
  two-way deep-liquidity names, chosen pre-open). Alpaca SIP raw 1-min bars, regular hours only (minute-of-session 0..389).
  SPY minutes from `data/research/night/m1/SPY_*.parquet`. Daily context from Sharadar (prev close unadjusted, 1/5/20d returns,
  vol20, $ADV20, next-day open/close ratio). Universe = both panels pooled with a source flag.
- Decision grid: every 5 minutes from 10:00 to 15:30 (k = 30..360). Hourly subset (10:00, 11:00, ..., 15:00) reported as well.
  Features use bars with minute <= k only: return since open / since prev close / gap, r5/r15/r30/r60, distance to session high,
  low and VWAP, session range, realized vol last 30 min and since open, cumulative $volume vs $ADV20, last-5-min volume share,
  SPY return since open and last 30 min, stock-minus-SPY since open, time of day, day of week, prev-day / 5d / 20d returns, vol20,
  log $ADV20, source flag. Entry price = the OPEN of bar k+1 (no bar-close lookahead).
- Labels. A (N 1044): entry -> the session's last 1-min close (proxy for the 16:00 cross; the live form is an MOC sell).
  B (N 1045): entry -> next session's open (A compounded with Sharadar open(d+1)/close(d)).
- Model: HistGradientBoostingRegressor (same GBM as SEQ-NIGHT), fit 2016-01..2021-12 on all grid rows; a development read trains
  on 2016-19 and reads 2020-21 (reported, not judged). JUDGE = 2022-01..2026-09, one look, untouched by any learned
  intraday-to-close model (SCALP-CLF judged 2019; VOLDAY/INPLAY judged fixed rules with intraday exits on these bars).
- Executable form: per name-day, the FIRST grid time whose prediction >= the fit-period 90th percentile of predictions; one
  trade, hold to the exit. Cost: 5bp entry (marketable order in $200M+ names), 0bp exit; also shown at 10bp.
- PASS (per label): first-trigger trades, net of 5bp: mean >= +10bp, day-clustered t >= 2, median > 0, both halves
  (2022-23 / 2024-26) > 0, ex-top-5 > 0, excess over the time-matched unconditional mean >= +10bp, and every within-day
  shuffled-label placebo (3 refits) below the real mean. Also reported: per-row prediction deciles, hourly-only subset, hit rate
  of the top decile vs all rows, corr(pred, y) vs corr(pred, |y|) (direction vs volatility), permutation importance, by year.
- KILL rule: fail any gate -> "learned any-time intraday trigger with auction exit, on the tape of volatile-liquid and in-play
  US names 2016-26, is closed." Not tested after this: non-tape inputs (exchange imbalance feeds, L2 depth, news), names below
  $200M ADV, limit (passive) entries, and the short side.
- Runner `research/sim/intra_any.py` (build | run); rows `data/research/program/intra_any_rows.parquet`; out `intra_any_out.txt`.

**INTRA-ANY v1 run DISCARDED (2026-10-19, disclosed).** The first run's daily-context features ret1/ret5/ret20/vol20 were computed
as of the SAME day's close (no shift): corr(pred, y) 0.96, hit 0.99, placebo +282bp. That is the day's close leaking into the
features, not an outcome. Fixed to the prior close (shift 1) and rerun once; the leaked output is kept as
`intra_any_out_v1_LEAK.txt` and is not a look at the judged question.

## RESULT - INTRA-ANY (N 1044-1045, 2026-10-19, one look after the disclosed leak fix): KILL both labels
- A (any 5-min check -> closing auction): first-trigger n 16,397, gross +7.5bp, net 5bp +2.5 (t 0.28, median -5.0, hit 0.49),
  halves -4.9 / +7.8, placebo refits +3.1/+3.0/+4.4 >= real, excess over time-matched +7.4; corr(pred, y) 0.018. 2/8 gates.
- B (any check -> next open): n 14,371, net +20.7 (t 1.60, median +4.7, hit 0.51), halves +9.9 / +27.4, excess +16.9, but placebo
  refits +22.1/+20.4/+20.6 = real: a shuffled-label model selects the same name-days. The number is the overnight premium of
  volatile in-play names (all rows +9.3/night), not model information. 6/8 gates (t, placebo fail).
- Dev read (2016-19 -> 2020-21): A +7.6 gross, B +53.6 gross (2020 vol), consistent.
- Verdict per registration: learned any-time intraday trigger with auction exit on the tape of volatile-liquid and in-play names,
  2016-26, is CLOSED. Not tested: non-tape inputs (imbalance feeds, L2, timestamped news), < $200M ADV, passive limit entries,
  short side; and two siblings of the same root left open: pre-market tape -> open cross (both legs free), halt-reopening auctions.
  Out `intra_any_out.txt`; rows `intra_any_rows.parquet` (6.1M, rebuildable). Program N = 1045.

## Amendment - Studies HALT-REOPEN (N 1046) and PREMKT-CROSS (N 1047-1048): pre-register 2026-10-19, before any outcome; N 1045 -> 1048

Two siblings of the "streaming / any-time" root left open by INTRA-ANY; the LLM/text sibling is closed by the user (no N).

**HALT-REOPEN (N 1046). Mechanism:** a Limit-Up-Limit-Down pause halts a stock for 5 minutes after a >=5-10% move inside 5 minutes;
it reopens through a reopening auction (halt cross). The imbalance that tripped the band must clear in that cross while most
participants are frozen or absent; the cross is a free fill (an order entered during the halt participates). Hypothesis: the reopen
print after a DOWN halt is below where the stock trades at the close (liquidity provision at the point of maximal dislocation).
- Events: NYSE trade-halt history API (all US exchanges; `data/research/halts/nyse_halts_2016_2026.parquet`, coverage 2019-07+),
  Reason "LULD pause", halt time 09:35-15:50 ET, resumed the same day, FIRST halt of the symbol-day (re-halts counted as risk, not
  traded), Sharadar-matched with prev close >= $5 and 20-session median $ADV >= $10M (the night leg's universe). n = 1,240
  (2019 17, 2020 647, 2021-26 ~90-110/yr), 688 symbols. Minute bars: Alpaca SIP raw 1-min for each symbol-day.
- Prices: pre-halt = last 1-min close before the halt time; p-5 = close 5 minutes before that; reopen = OPEN of the first bar at or
  after the resume time (proxy for the halt-cross print); then +5m, +30m, the session's last close, and next open (Sharadar
  open(d+1)/close(d)). Direction: DOWN halt if pre-halt < p-5, else UP. SPY from `night/m1` over the same minutes.
- Arms: D = buy the reopen after a DOWN halt, sell the closing cross (primary). D-N = same, sell next open. U = short the reopen
  after an UP halt, cover at the close (informational; Roth cannot short). Cost: 0bp at both auctions in the base case; reported
  at 10bp and 25bp (thin reopening crosses). Also reported: reopen -> +5m / +30m paths, re-halt rate within 30 min, reopen-bar
  $volume (capacity), ADV buckets (>= $10M / $50M), by year, 2020 vs ex-2020.
- PASS (arm D): net 10bp mean >= +30bp, day-clustered t >= 2, median > 0, hit >= 0.5, both halves (2019-20 / 2021-26) > 0,
  ex-top-5 > 0, SPY-adjusted mean >= +20bp. A pass carried by 2020 alone (ex-2020 <= 0) is a NO.
- KILL: fail -> "buying the LULD reopening cross after a down halt in $5+/$10M+ names, 2019-26, is closed". Not tested after
  this: news-pending halts (T1; a different auction with news), re-halts, names < $10M ADV, limit orders inside the halt
  (price improvement vs the print), pre-2019 (no halt history), the UP side as a live short.
- Runner `research/sim/halt_reopen.py` (fetch | run); out `halt_reopen_out.txt`.

**PREMKT-CROSS (N 1047-1048). Mechanism:** the two official auctions are the only free fills at this size; a trade that buys the
09:30 cross and sells the 16:00 cross pays 0bp on both legs, so any 10bp of conditional open-to-close drift is kept whole. The
pre-market tape (04:00-09:29) has never been modelled here (fixed gap-fade / gap-continuation rules died with intraday exits).
- Data: the INTRA-ANY panels (volday 2016-26 with bars from 04:00 ET; inplay 2019-26 with bars from 08:25 ET). Features from bars
  BEFORE 09:30 only: pre-market return vs prev close (last pre-market print), 08:30-09:29 return, pre-market range, pre-market
  $volume / $ADV20, number of pre-market minutes with prints, last print vs pre-market VWAP, 09:00-09:29 realized vol, SPY
  pre-market return (same window), stock-minus-SPY; plus the prior-close daily context (ret1/5/20, vol20, log ADV, dow, source).
  Volday-only full-session pre-market features are NaN for inplay rows (the GBM handles NaN).
- Entry = the first regular-hours bar's open (== the official open cross in 2016-20 per SPLIT-CROSS); exit A (N 1047) = the
  session's last 1-min close (proxy for the 16:00 cross); exit B (N 1048) = next open. One decision per name-day.
- Model: same GBM as INTRA-ANY; fit 2016-01..2021-12, judge 2022-01..2026-09 one look; trade when pred >= fit-period p90.
- PASS (per label): selected trades net 5bp (safety margin on two 0bp auctions): mean >= +10bp, day-clustered t >= 2, median > 0,
  both halves (2022-23 / 2024-26) > 0, ex-top-5 > 0, excess over the universe's unconditional open-to-exit mean >= +10bp, every
  within-day shuffled-label placebo (3 refits) below the real mean. Also reported: deciles, hit rate, corr(pred, y) vs
  corr(pred, |y|), importance, by year, the bottom decile (informational short).
- KILL: fail -> "learned pre-market-tape selection into the open cross with an auction exit, on these universes 2016-26, is
  closed". Not tested after this: pre-market NEWS content (LLM branch closed by the user), names < $200M ADV, pre-market
  limit entries (fills before 09:30), the short side live.
- Runner `research/sim/premkt_cross.py` (build | run); rows `premkt_rows.parquet`; out `premkt_cross_out.txt`.

## RESULT - PREMKT-CROSS (N 1047-1048, 2026-10-19, one look): KILL both labels; the signal it found is day-level
- A (open cross -> close cross): selected n 6,706 (13.8% of name-days), net 5bp +26.2 (t 1.36, median +13.6, hit 0.51), halves
  -10.5 / +55.5, by year 2022 -25, 2023 +31, 2024 +31, 2025 +69, 2026 +55; placebo refits +18.9/+20.3/+11.7 (real +26.2); top
  features ret1, spy_pm. 6/8 gates (t, h1 fail).
- B (-> next open): net +54.8 (t 2.00, median +21.6), halves +2.1 / +94.2, placebo +57.1/+56.1/+39.9 = real: a shuffled-label
  model picks the same days. 7/8 (placebo fails).
- Diagnostic (no N): by SPY pre-market quintile, the universe's EW open->close is +29.6 / +4.7 / -4.9 / -24.3 / -2.5 bp (2016-21) and
  +15.5 / +7.4 / -6.5 / -11.8 / +3.1 (2022-26) from the most negative SPY pre-market to the most positive; SPY itself ~flat. Volatile
  names reverse the market's pre-market move intraday: a day-level ~+15-30bp on 20% of days, dial class, not stock selection.
- Verdict: learned pre-market-tape selection into the open cross, on these universes 2016-26, is CLOSED. The stock-specific
  pre-market tape adds ~+6-14bp over the day-level placebo (A), under the bar and with flipped halves. Not tested: pre-market news
  content (LLM branch closed by the user), < $200M ADV, pre-market limit entries, the short side, the day-level reversal as its own
  registered rule (dial class: do not run). Out `premkt_cross_out.txt`; rows `premkt_rows.parquet`. Program N = 1048.

## Amendment - Study CHART-YOLO (N 1049): pre-register 2026-10-19, before any outcome; N 1048 -> 1049

**Root (user material, 2026-10-19):** a list of public models. Branches: (1) financial-headline sentiment classifiers = the LLM/NLP
branch the user closed today (and data-blocked: no point-in-time headline archive) -> not run; (2) LSTM price predictors = tape
sequence models, already covered and stronger here (SEQ-ENTRY, INTRA-ANY with placebos) -> not run; (3) Mistral/Gemma "advisor"
chat models -> no testable number -> not run; (4) `foduucom/stockmarket-pattern-detection-yolov8` = a NEW representation: the
visual chart patterns a human reads (head-and-shoulders top/bottom, double top "M_Head", double bottom "W_Bottom", triangle),
detected on rendered daily candlestick charts. Never tested here (SEQ-NIGHT used indicator sequences; GOLD-IFVG closed ICT shapes).
- Universe: Sharadar domestic common stocks, prev close >= $5, 20-session median $ADV >= $10M (the night leg's universe), 2016-01..
  2026-09. Sample: 30,000 (name, date) pairs drawn uniformly at random (seed 0) from eligible name-days (one look, no re-sampling).
- Image: the 100 daily bars ending at the signal close, rendered in the model's training style (mplfinance-like candlesticks, green
  up / red down, grey grid, right price axis), 640x480. Model as published (YOLOv8s, conf 0.25). A detection counts as a SIGNAL only
  when its box's right edge is in the last 15% of the chart width (the pattern completed at the signal close); detections that end
  earlier are the STALE control (same names, same chart style, pattern already over).
- Direction (textbook, fixed): BULL = W_Bottom, Head and shoulders bottom; BEAR = M_Head, Head and shoulders top; Triangle and
  StockLine reported, no direction.
- Labels (Sharadar, split-adjusted ratios): L1 = close d -> open d+1 (overnight); L2 = open d+1 -> close d+1 (the two free crosses);
  L5 = close d -> close d+5; each minus SPY over the same window. Costs: 0bp for the auction legs; L5 shown net 10bp.
- PASS: BULL right-edge signals L5 excess >= +30bp, day-clustered t >= 2, median > 0, both halves (2016-20 / 2021-26) > 0,
  ex-top-5 > 0; BULL minus BEAR L5 >= +40bp with t >= 2; the STALE control of the same class must be at least 20bp weaker than the
  right-edge signal (else it is the chart's trend, not the pattern); the 1-day auction trade (L2) reported with a +10bp bar.
- KILL: fail -> "visual chart patterns (the four textbook reversal shapes, as detected by a public YOLOv8 chart model) carry no
  tradable 1-5 day information in liquid US stocks 2016-26". Not tested after this: intraday chart images, other pattern
  vocabularies (flags, cup-and-handle), a model retrained on this book's own labels, options-implied confirmation.
- Runner `research/sim/chart_yolo.py` (probe | run); detections `data/research/chart_yolo/detections.parquet`; out `chart_yolo_out.txt`.

## RESULT - HALT-REOPEN (N 1046, 2026-10-19, one look on the full set after a disclosed partial read): KILL
- The first bar fetch died on a connection error at 457/1,240 symbol-days; a partial read (439 events, kept as
  `halt_reopen_out_PARTIAL439.txt`) was seen before the fetch was resumed. Full set: 1,194 scored, 656 symbols, 530 down / 664 up.
- Mechanics confirmed: trigger move median -564bp (down) / +514 (up) in the 5 minutes before the halt; the reopen print is -78bp
  below the pre-halt price after down halts and +188 above after up halts; 32% of down halts re-halt within 30 minutes; reopen-bar
  median $1.7M (capacity is not the constraint).
- D (buy the reopen after a DOWN halt, sell the close), net 10bp: n 530, mean +580, median +122, hit 0.55, day-clustered t 1.60,
  ex-top-5 +161; 2019-20 +469 (median +387, hit 0.62, t 2.79) vs 2021-26 +696 mean / **-51 median, hit 0.47, ex-top-5 -155, t 0.96**;
  by year 2021 -223, 2022 -467, 2023 +262, 2024 -14, 2025 +3,764 (lottery tail), 2026 -207. The first 5 minutes after the reopen are
  NEGATIVE (-66 mean, -32 median, t -1.9); +30m +115. 7/9 gates (t, SPY-adj fail) -> KILL as registered.
- U (short the reopen after an UP halt): -44 mean / +32 median to the close, next-open -254 (t -2.2): up-halt names keep going; no
  short edge, and the Roth cannot short anyway.
- Read: in the 2020 crash the reopening cross after a down halt was a real liquidity-provision trade (median +387bp, 62% hit). Since
  2021 the median trade LOSES; the positive mean is a handful of re-halt squeezes (re-halt bucket mean +1,497, median +176). A
  lottery with a negative median is not a leg. Verdict per registration: buying the LULD reopening cross after a down halt in
  $5+/$10M+ names, 2019-26, is CLOSED. Not tested: news-pending (T1) halts; re-halts as their own event; names < $10M ADV; entry 5
  minutes after the reopen (bounded: the +5m dip is -32bp median, which cannot lift the 2021-26 median of -51 to the +30 bar);
  limit orders inside the halt; pre-2019. Runner `research/sim/halt_reopen.py`; out `halt_reopen_out.txt`; rows
  `data/research/halts/halt_reopen_rows.parquet`; halt history `nyse_halts_2016_2026.parquet` (74,686 halts, reusable). Program N = 1049.

## Amendment - Study GAP-NIGHT (N 1050): pre-register 2026-10-19 (branch loop), before any outcome; N 1049 -> 1050

Branch of today's root ("searchers that find a person who must trade, executed at an auction"). INTRA-ANY/PREMKT label B found that
the in-play / volatile universes earn +9-14bp per night close -> open unconditionally in 2022-26 (placebo = real: a universe
property). Not in the ledgers as a standalone: Lab-BH/BI is the multi-day drift of gappers (negative over 20d); the EXDIV "+9bp" note
is ex-dividend names. Mechanism (Lou-Polk-Skouras overnight/intraday clientele): retail attention names are bought at the open and
sold into the close by day traders, so the close is depressed relative to the next open; the two legs are the free crosses.
- Form A (Sharadar, 2016-01..2026-09): every name-day with |open / prev close - 1| >= 3% at the open, prev close >= $5, 20-session
  median $ADV >= $50M, domestic common stock. Trade: buy the close cross of the gap day, sell the next open cross. Form B: the
  point-in-time inplay pool G name-days (25 largest |gap| >= 1%, ADV >= $200M, 2019-01..2026-09, `data/research/inplay/pools.parquet`).
- Label: open(d+1)/close(d) - 1 (split-adjusted ratios; daily open == official open cross per SPLIT-CROSS 2016-20). Per-night
  equal-weight portfolio. Comparators: SPY overnight; the EW overnight of ALL eligible names (ADV >= $50M, px >= $5) the same night;
  the same with the night leg's own picks (day_ret <= -8%, IBS < 0.1) EXCLUDED, so the result is not the night leg in disguise.
- Arms: all gaps; up-gaps; down-gaps; |gap| 3-5 / 5-10 / 10%+. Costs: 0bp (two auctions); shown at 5bp total.
- JUDGE = 2016-01..2021-12 (never read for this question: the +9-14bp observation is from 2022-26, which is reported as the touched
  period). PASS: per-night EW excess over the EW universe overnight >= +8bp, day-clustered (per-night) t >= 2, median night > 0, both
  halves (2016-18 / 2019-21) > 0, ex-top-5 nights > 0, excess over SPY-beta-matched overnight > 0, and the night-leg-excluded
  universe comparator does not close the gap. KILL otherwise: "gap names held close -> open earn no premium beyond the universe
  overnight premium". Not tested after this: intraday-volume-based attention (RVOL) instead of the gap; names < $50M ADV; the
  intraday short side.
- Runner `research/sim/gap_night.py`; out `gap_night_out.txt`.

## RESULT - GAP-NIGHT (N 1050, 2026-10-19 branch loop, one look): PASS-SMALL on the registered gates (2016-21), decaying, up-gap carried
- Form A, arm all: 91,441 gap name-days on 2,691 nights (median 15 names/night). JUDGE 2016-21: raw +14.0bp/night (median +12.9, hit
  0.57, t 3.43); excess over the EW universe overnight +8.6 (median +1.3, t 3.03, ex-top-5 +5.7); over SPY +9.9 (t 3.27); SPY-beta
  1.54 overnight, beta-adjusted +7.7 (t 2.65); halves x-univ +11.0 (t 3.1) / +6.1 (t 1.4, median -1.2); night-leg picks excluded +7.7
  (t 2.7). 8/8 gates -> PASS as registered.
- Decomposition: UP gaps +13.0 x-univ (t 3.45, both halves > 0) carry it; DOWN gaps +0.2 (t 0.04). Size: 3-5% +4.2 (t 1.3), 5-10%
  +6.9 (t 1.4), 10%+ +20.8 mean / -6.5 median (lottery). Form B (PIT inplay pool G, 2019-21): raw +17.0 (t 2.5), x-univ +8.6 (t 2.3).
- Touched 2022-26: raw +7.8 (t 1.65), x-univ +5.4 (t 1.59); 2022 -13 x-univ, 2023-25 +7..+15, 2026 +3. Universe overnight itself
  fell from +5.6 (2016-21) to +2.3 (2022-26).
- Read: the overnight attention premium (Lou-Polk-Skouras) exists in gap names at the two free crosses, strongest in UP gaps; the
  median night is small and the effect is about half as strong since 2022. Not a new mechanism: it is the same overnight-clientele
  family as OVN-MOM (decayed to ~+3bp net) and part of what the night leg's beta decomposition already carries. Economics at 0bp:
  ~+8bp/night x ~250 nights = ~+20pp/yr gross over the universe at 100% of capital; realistic (50% capture, 50% capital, 2022-26
  strength) ~+3-5pp/yr, overnight SPY-beta 1.5. Status: FORWARD-SHADOW CANDIDATE (user decision), not a deployment. Not tested:
  RVOL-based attention instead of the gap; < $50M ADV; official cross prints (daily open/close used); the night-leg interaction
  (capital competes on the same close->open window); up-gap-only as its own registered rule (do not re-tune on 2016-21).
  Runner `research/sim/gap_night.py`; out `gap_night_out.txt`. Program N = 1050.

## Amendment - GAP-NIGHT-FWD forward shadow (no N; registered 2026-10-19 after the user's "shadow", before any forward print)
- Module `swingtrader/daily/gap_night_shadow.py` (research-shadows 08:20 ET, log-only, `state/gap-night.jsonl`, REGISTRY
  "GAP-NIGHT-FWD"). Frozen rule = the registered form A on the live night universe: common stock, SIP daily bars, |open(T)/close(T-1)
  - 1| >= 3%, close(T-1) >= $5, ADV20 (median $vol, 20 prior sessions) >= $50M. Trade: official CLOSE cross of T -> official OPEN cross
  of T+1 (Alpaca SIP trades, largest print per auction), EW per night. Comparator per night: EW overnight open(T+1)/close(T) - 1 of all
  eligible names (`univ`) and of those that are not night-leg picks (`univ_x`; day_ret <= -8%, IBS < 0.10 excluded), from the same
  daily bars. SPY logged per row.
- Gate: 60 forward gap nights (first forward session 2026-10-20), per-night excess over `univ` >= +5bp, night-clustered t >= 2,
  median night excess > 0. Read by hand from the same log: up vs down arms (the study's +13.0 vs 0), excess vs `univ_x`, SPY beta,
  net at 5bp round trip. PASS = propose a tiny live pilot (user decision); FAIL (excess <= 0 at 60 nights) closes the gap form of the
  overnight-attention family at the crosses. Backfill rows (`--backfill N`) are labelled and excluded from the gate.
- Not tested by this shadow: RVOL-based attention; < $50M ADV; up-gap-only as a rule; the night-leg capital interaction.

## Amendment - Study NEWS-HALT (N 1051): pre-register 2026-10-19 (branch loop), before any outcome; N 1050 -> 1051

Sibling of HALT-REOPEN left open: news-pending halts (T1/T2, "News pending/released/dissemination"), where trading stops for a
material announcement and reopens intraday through the halt cross after the news is out. Mechanism: the reopening cross is the first
print that clears all orders accumulated during a ~40-minute halt on fresh news; the question is whether that print over- or
under-reacts relative to the close (the counterparty is everyone who had to re-mark at once). Direction comes from the news, i.e.
from the reopen print vs the pre-halt price (there is no trigger move).
- Events: NYSE halt history, reasons News pending / News Released / News dissemination, resumed the same day between 09:35 and 15:50
  ET (560 of 1,448 such halts began pre-open), first halt of the symbol-day, Sharadar-matched prev close >= $5 and 20-session median
  $ADV >= $10M: n = 245 (2019 14, 2020 31, 2021 41, 2022 38, 2023 31, 2024 30, 2025 37, 2026 23), 190 symbols, median halt 38 min.
  Bars: Alpaca SIP raw 1-min (fetch 228 new symbol-days). `data/research/halts/news_events.parquet`.
- Prices as HALT-REOPEN: pre-halt = last close before the halt time (for pre-open halts: the prior close); reopen = open of the
  first bar at/after the resume time; +5m, +30m, close, next open; SPY same window. Direction: NEWS-DOWN if reopen < pre-halt, else
  NEWS-UP (registered: the direction uses the reopen print itself, so "buy the reopen" means buying after a down news print).
- Arms: D = buy the reopen after NEWS-DOWN, sell the close (primary; also next open); U = short the reopen after NEWS-UP (informational).
  Costs 0bp base, 10bp and 25bp shown.
- PASS (arm D): net 10bp mean >= +30bp, day-clustered t >= 2, median > 0, hit >= 0.5, both halves (2019-22 / 2023-26) > 0, ex-top-5
  > 0, SPY-adjusted >= +20bp. KILL otherwise: "buying the news-halt reopening cross after a down news print, $5+/$10M+ names,
  2019-26, is closed". Not tested after this: halts that reopen at the regular 09:30 cross, the up side as a live short, re-halts,
  < $10M ADV, the content of the news (LLM branch closed).
- Runner `research/sim/halt_reopen.py` with HALT_EVENTS=news_events.parquet HALT_OUT=news_halt_out.txt HALT_DIR=reopen (direction
  from the reopen print); out `news_halt_out.txt`.

## RESULT - NEWS-HALT (N 1051, 2026-10-19 branch loop, one look): KILL (arm D); up-news fade observed on the short side
- 242 scored of 245; 75 NEWS-DOWN / 167 NEWS-UP reopens; reopen print vs pre-halt -117bp median (down) / +241 (up); re-halts ~3%;
  reopen-bar median $3-5.5M.
- D (buy the reopen after a down news print, sell the close), net 10bp: n 75, mean -40.5, median -3.6, hit 0.49, t -0.7, ex-top-5
  -121; 2021-26 -60; ADV >= $50M -142 (t -2.0); next open -72 (t -1.0). 1/9 gates -> KILL. Bad news keeps going after the reopen.
- U (short the reopen after an UP news print, cover at the close): n 167, net 10bp +111.9, median +48.1, hit 0.57, t 2.65, ex-top-5
  +69; +5m +108 (t 3.7), +30m +158 (t 3.9); 2021-26 +131 (t 3.3), 2019-20 +42 (t 0.3); ADV >= $50M +82 (t 1.5); by year positive in
  6/8. Informational (not gated): the good-news reopening cross OVERSHOOTS and fades into the close. Short-side only (taxable margin;
  not the Roth), ~35 events/yr, ceiling ~35 x ~1% x a 10-20% position = ~+0.4-0.7pp/yr at $10k -> below the gate as a leg.
  Recorded in NEXT.md's unproven table as a short-side observation; not a shadow (ceiling), not re-tuned.
- Not tested: halts reopening at the regular 09:30 cross; the up-fade as a registered short rule on an untouched period (none
  exists: 2019-26 is all the halt history); re-halts; < $10M ADV. Out `news_halt_out.txt`; rows `data/research/halts/news_halt_rows.parquet`.
  Program N = 1051.

## Amendment - Study SPECIAL-EX (N 1052): pre-register 2026-10-19 (branch loop), before any outcome; N 1051 -> 1052

Pivot from halts to the ex-date family. PREF-EX/ETDX showed dividend-proportional under-adjustment survives in $25-par paper;
common-stock REGULAR ex-dates are dead (EXDIV-OPEN, THN: ~0 since 2021). Not tested: SPECIAL dividends on commons (one-off payouts
of 3%+ of price), where the ex-day price drop is a large, discrete, tax-clientele event and the holder base must re-mark at the open
cross. Due-bill specials appear only in a ceiling-scan row (>= 25% payouts, where the ex-date follows the pay date).
- Events: Sharadar `actions` dividends (date = ex-date) on domestic common stocks, 2000-01..2026-09, value / prev closeunadj between
  3% and 50%, prev close >= $5, 20-session median $ADV >= $10M. Arms by size: 3-10%, 10-25% (standard ex-date mechanics) and 25-50%
  (due-bill regime; reported, NOT gated: the vendor ex-date convention is unverified there).
- Trade: buy the close cross on E-1, sell the open cross on E, receive the dividend: r = (open_E_raw + div) / close_{E-1}_raw - 1,
  raw prices (open_E_raw = open_E x closeunadj_E / close_E), minus SPY overnight. Costs 0bp (two auctions), shown at 5bp.
- Mechanism check: drop ratio = (close_{E-1} - open_E) / div; < 0.9 means under-adjustment (the PREF-EX signature).
- PASS (pooled 3-25%): net mean >= +30bp, date-clustered t >= 2, median > 0, hit >= 0.55, both halves (2000-12 / 2013-26) > 0,
  ex-top-5 > 0, drop ratio < 0.9, and 2021-26 alone > 0 (the regular-dividend version died there). KILL otherwise: "special-dividend
  ex-nights on liquid commons carry no capturable under-adjustment". Not tested after this: the due-bill regime as a trade; selling
  at the ex-date CLOSE instead of the open; the Roth vs taxable tax treatment (specials may be non-qualified).
- Runner `research/sim/special_ex.py`; out `special_ex_out.txt`.

## RESULT - SPECIAL-EX (N 1052, 2026-10-19 branch loop): KILL; the registered "PASS" was a vendor-date artifact (disclosed)
- As registered (pooled 3-25%, 1,517 ex-nights): +229bp mean, median +92, hit 0.74, t 21, 9/9 gates -> PASS on paper.
- Adversarial check (failure-mode order: data bug first): 40% of pre-2013 events (18% in 2020-23, 8% in 2024+) show NO price drop at
  the recorded date and none over the next 5 sessions (median drop 0.18 x dividend): the Sharadar `actions` dividend record is
  mis-dated or mis-valued there. Using the vendor's own total-return factor (closeadj/close jump on E implies a dividend within
  0.8-1.25x the recorded value) as a point-in-time confirmation splits the sample: CONFIRMED n 954 (drop ratio 0.95): 2000-12 +91,
  2013-20 +39, **2021-26 +13.3bp mean, median +4.5, hit 0.54, t 1.7** (2024 -2, 2026 -5; ADV >= $50M +30 t 1.8); NOT confirmed n 581:
  +526bp, hit 0.98 (impossible: a fake dividend added to an unchanged price). COST's five specials are correctly dated and drop
  0.73-1.07x.
- Verdict: liquid commons adjust ~fully for special dividends (drop 0.95-0.97 in the modern era); the capturable residual is
  ~+5-13bp/event at 0bp, t < 2, not a leg. KILL. Not tested: the due-bill (>= 25%) regime; selling at the E close (confirmed set
  not re-run; the open result is already under the bar); the Roth-vs-taxable angle. DATA RULE (new): any study using Sharadar
  `actions` dividends as ex-dates must confirm each row against the closeadj/close factor jump; unconfirmed rows must be dropped
  BEFORE any outcome is read (PREF-EX/ETDX used SFP/official prints and are unaffected; EXDATE-OOS/EXDIV-OPEN used actions —
  re-check their unconfirmed share before citing them). Runner `research/sim/special_ex.py`; out `special_ex_out.txt` (artifact
  numbers) + this note. Program N = 1052.

## Amendment - Study RE-HALT (N 1053): pre-register 2026-10-19 (branch loop), before any outcome; N 1052 -> 1053

Sibling of HALT-REOPEN: the SECOND LULD halt of a symbol-day. HALT-REOPEN found the first down-halt reopen loses in the modern era,
and that the re-halt bucket carried the positive mean (+1,497 mean / +176 median, n 170, outlier-driven). Question: is the second
halt's reopen a different event (the pool of forced sellers has already cleared once)? Same universe, same symbol-days (bars on disk).
- Events: LULD pauses with nth >= 1 on the symbol-days already in `luld_events.parquet` (first halt in the $5+/$10M+ universe),
  resumed the same day 09:35-15:50, one row per halt (the 2nd, 3rd... halts each count); prices as HALT-REOPEN (pre-halt, p-5,
  reopen, +5m/+30m/close/next open), direction from the 5-min move into THAT halt.
- Arms and PASS/KILL exactly as HALT-REOPEN (arm D net 10bp >= +30, t >= 2, median > 0, hit >= 0.5, halves 2019-20 / 2021-26 > 0,
  ex-top-5 > 0, SPY-adj >= +20, not 2020-only). Not tested after this: halts on symbol-days whose FIRST halt was outside the
  universe; 4th+ halts separately. Runner `halt_reopen.py` with HALT_EVENTS=rehalt_events.parquet HALT_OUT=rehalt_out.txt.

## RESULT - RE-HALT (N 1053, 2026-10-19 branch loop, one look): KILL
- 1,224 scored (480 down / 744 up re-halts on 399 symbol-days; names already -23% on the day at the 2nd+ halt; 56% halt again within
  30 min). D (buy the reopen after a down re-halt, sell the close), net 10bp: mean +1,662 (one +214,834bp row = a bad print; ex-top-5
  +896), median +375, hit 0.59, t 1.99; halves +912 / +2,026; ADV >= $50M +322 / median +187 (t 1.9). Gates: t and SPY-adj fail -> KILL.
- Why it is not "unproven": the yearly MEDIAN flips sign (2019 -973, 2020 +363, 2021 +46, 2022 -124, 2023 +1,004, 2024 +195,
  2025 +991, 2026 -279); the 10-90% range of a single trade is -1,771 .. +4,208bp. That is crash-day lottery variance, not a
  median effect; the +30m path is ~0 in 5/8 years. Not tested: 4th+ halts separately; symbol-days whose first halt was outside the
  universe; the UP side (short, +? not read). The LULD family (first halt, re-halt, news halt) is now closed in every form on
  2019-26 halt history. Out `rehalt_out.txt`; rows `data/research/halts/rehalt_rows.parquet`. Program N = 1053.

## Amendment - Study F-SALE (N 1054): pre-register 2026-10-19 (branch loop), before any outcome; N 1053 -> 1054

New family (none of today's): mutual-fund FIRE SALES (Coval-Stafford 2007). A fund facing heavy redemptions must sell what it holds,
pro rata, regardless of price; stocks held by several such funds are pushed down over the outflow quarter and recover over the
following 6-12 months. A named, constrained counterparty; long-only; Roth-friendly; capacity irrelevant at $2-25k. Never tested
here (the ledgers have ETF creation/redemption and 13F crowding only). Data entitled at $0: WRDS `tfn.s12` (mutual-fund holdings by
fund and quarter, through 2026-03) and Sharadar prices.
- Build: s12 holdings 2009-12..2026-03 for funds with assets >= $100M (fdate, fundno, cusip, shares, assets). Fund flow proxy per
  quarter: assets_t / assets_{t-1} - (1 + r_t), where r_t is the fund's holdings-weighted stock return over the quarter from its
  PRIOR quarter's holdings (Sharadar closeadj; cusip -> Sharadar via tickers.cusips). Heavy outflow = flow <= -5%; heavy inflow
  >= +5% (Coval-Stafford thresholds). PRESSURE(stock, q) = [sum over outflow funds of shares reduced - sum over inflow funds of
  shares added] / stock's 20-session median volume at quarter end, restricted to funds whose change is in the flow's direction.
- Signal: quarters end 3/6/9/12; holdings become public with a lag; the signal date = quarter end + 60 calendar days (conservative
  vs the 45-day filing deadline). Portfolio: bottom decile of PRESSURE (most fire-sold) among names with prev close >= $5 and
  $ADV20 >= $10M, EW, bought at the next open cross after the signal date, held to the next signal date (quarterly rebalance; ~90
  sessions). Benchmark: EW of all eligible names with a PRESSURE value that quarter, and SPY.
- Reported: the pressure-quarter return itself (the fire sale must be visible: bottom decile should UNDERPERFORM during the quarter
  it is measured); the holding-period excess by decile; top-decile (inflow-bought) as the mirror; by year; halves 2010-17 / 2018-26;
  ex-top-5 quarters; quarter-clustered t (quarters are the cluster, ~64).
- PASS: bottom-decile holding-period excess over the eligible EW >= +150bp per quarter (~+6pp/yr), quarter-clustered t >= 2, median
  quarter > 0, both halves > 0, ex-top-5 quarters > 0, monotone-ish deciles (bottom > middle), and the pressure-quarter return of
  the bottom decile < the EW (the mechanism is visible). KILL otherwise: "fund fire-sale pressure from s12 holdings carries no
  exploitable 1-quarter reversal at the 60-day lag". Not tested after this: shorter lags (needs N-PORT monthly), daily-flow
  versions (needs MFLinks/CRSP daily), the inflow-side short, ETF fire sales.
- Runner `research/sim/f_sale.py` (pull | run); data `data/research/fsale/`; out `f_sale_out.txt`.

## RESULT - CHART-YOLO (N 1049, 2026-10-19, one look): KILL, and the textbook sign is WRONG
- 30,000 charts; the public model fires on 81% of them (43,481 boxes); right-edge (completed) signals: BULL 1,298 (W_Bottom 734, H&S
  bottom 564), BEAR 2,463 (H&S top 1,448, M_Head 1,015), Triangle 49.
- BULL right-edge: L1 -2.2, L2 (open->close crosses) -7.0, L5 -33.2bp vs SPY (median -40.5, hit 0.46, t -1.7); 2021-26 -43.5 (t -2.1).
  Higher model confidence is worse (conf terciles +26 / -60 / -66). BEAR right-edge: L5 +16.2 (median -8.8, t 1.3). BULL minus BEAR
  L5 = -49bp (t -2.2). Stale (already-over) patterns ~ the universe (-4 / -13). Triangle (n 49) -167/5d. 0/8 gates -> KILL.
- Read: a double bottom / inverse head-and-shoulders completing at the right edge of a daily chart is, if anything, a short-term
  negative in liquid US stocks 2016-26 (the shape is "just stopped falling", and the next week continues down more often than not);
  "textbook" pattern direction is a contrarian indicator at this horizon. Verdict per registration: visual chart patterns as detected
  by a public chart model carry no tradable 1-5 day information. Not tested: intraday chart images; other pattern vocabularies
  (flags, cup-and-handle); a model retrained on this book's own labels; the CONTRARIAN use (short completed bull patterns) as a
  registered rule (do not re-tune on the same sample). Detections `data/research/chart_yolo/detections.parquet` (reusable). Out
  `chart_yolo_out.txt`. Program N = 1054 (F-SALE registered).

## RESULT - F-SALE (N 1054, 2026-10-19 branch loop, one look): KILL at this flow proxy; the hypothesis is NOT tested at a proper flow measure
- Build: tfn.s12 2009Q4-2026Q1, 97.9M fund-quarter-stock rows (49.5k fund ids, 13.6k Sharadar tickers), 1.04M fund-quarters with a
  flow proxy (34% outflow <= -5%, 27% inflow >= +5%: the proxy is far too dispersed for real quarterly fund flows, which are mostly
  within +/-5%). 109.6k eligible stock-quarters, 65 quarters.
- Bottom decile (most "fire-sold"): next-quarter excess vs EW -80bp (median -59, hit 0.38, quarter-t -2.1), vs SPY -107; halves -37 /
  -122; top decile -11. Mechanism check FAILS: the bottom decile OUTPERFORMED during the pressure quarter (+128bp vs EW, t 3.3), i.e.
  the measure flags funds trimming winners, not forced selling at a loss. 0/8 gates -> KILL.
- Read: with fund flow inferred from s12 `assets` minus a holdings-weighted return, "pressure" is dominated by noise and by winner
  trimming; the Coval-Stafford fire-sale signature (negative pressure-quarter return, positive reversal) is not reproduced, so this
  run does not falsify the mechanism, it falsifies the proxy. Not tested: pressure from CRSP monthly flows (needs MFLinks, absent on
  this account) or N-PORT monthly holdings; daily-flow ETFs; the open-cross entry at quarter end + 60d (moot). Data kept:
  `data/research/fsale/s12_*.parquet` (3.2GB, reusable), `pressure.parquet`. Runner `research/sim/f_sale.py`; out `f_sale_out.txt`.
  Program N = 1054.

## Amendment - Study HL-BOUNCE (N 1055): pre-register 2026-10-19 (user: "bounce back in an uptrend"), before any outcome; N 1054 -> 1055
- Branch list first (CLAUDE.md rule): trend-filter+dip (DEAD: W4/U1/F7/U5/AT3/TREND-NIGHT), indicator turn-ups (DEAD: U9/H5/F3/F4/F5),
  intraday level bounces (DEAD: VOLDAY/INPLAY/LEVEL-BOUNCE/STOP-RUN), momentum pullback (ARETE-DIP killed, shadow), weekly (low ceiling,
  not run), breakout retest (not run, breakout neighbours all lose). This study = the one untested shape: SWING STRUCTURE.
- Hypothesis: in a daily uptrend defined by market structure (rising pivot highs, a new pivot low ABOVE the prior pivot low), the first
  close back above the pivot-low bar's high (the "confirmed bounce") is followed by continuation over 1-10 sessions, in excess of the
  equal-weight liquid universe. Mechanism claimed by practitioners: trend followers buy the pullback and stops sit under the pivot.
  Prior from the ledgers: bounces are larger in DOWNtrends (AT3, TREND-NIGHT) and textbook bull shapes are contrarian (CHART-YOLO).
- Pre-test ceiling (research-priority gate): liquid stocks, if ~1% of liquid name-days signal (~13/day) and the H5 net excess is at the
  +25bp bar, ~5 overlapping slots x 50% of capital -> ~+6pp/yr at $10k at 100% capture, ~3pp at honest 50%: BELOW the +8pp gate. Run
  anyway on the user's instruction (test before pushing back; the shape has never been measured); a PASS is a sleeve candidate, not a 2x.
- Data: `winsig.load_panel("stock")` and `("etf")` (Sharadar SEP common / SFP non-leveraged ETFs, 2002-06..2026-10, delisted included),
  `liq` = closeunadj >= $5 and 20d $ADV >= $20M; split-adjusted OHLC for structure; forward returns f1/f3/f5/f10 from the open at t+1 on
  the total-return scale (closeadj), excess x{H} vs the EW liq universe (`add_bench`).
- Pivots (k = 3): pivot low at t if low[t] < min(low[t-3..t-1]) and low[t] <= min(low[t+1..t+3]); pivot high symmetric with high. A pivot is
  CONFIRMED at bar t+3 (no lookahead: all state used at s is from pivots confirmed at or before s).
- State at bar s: PL_cur = latest confirmed pivot low (bar t), PL_prev = the one before it; PH1 > PH2 = the two latest confirmed pivot highs.
  Bounce confirmation: s in [t+3, t+10], close[s] > high[t], and no close in (t, s) exceeded high[t] (first cross only; one signal per pivot).
- Arms (all: buy open s+1, excess vs EW liq, 10bp round trip, shock 30bp, primary H5, H1/H3/H10 reported):
  A1 HL-UP (PRIMARY): PL_cur > PL_prev AND PH1 > PH2 (higher low inside rising highs).
  A2 LL (control): PL_cur < PL_prev (lower low, any highs). A3 ALL: every confirmed pivot-low bounce.
  Diagnostics (not judged): A1 & close > SMA200; A1 by pullback depth terciles (PL_cur/PH1 - 1); A1 by ADV tercile; by year.
- Universes: stocks (primary) and ETFs (second primary, same bar). Periods: 2016-01..2026-09 (discovery per the winsig loop) and
  2003-01..2015-12 (confirm; untouched for any structure rule). ONE run; no re-tuning of k, the 10-bar window or the confirmation rule.
- PASS (per universe): `winsig.passes` on H5 in BOTH periods (net excess >= +25bp, NW t >= 3, both halves > 0, median > 0, ex-top-5 > 0)
  AND A1 minus A2 (date-paired on common dates) >= +10bp, else the structure condition adds nothing. KILL otherwise, stated as: "a
  confirmed bounce from a higher low inside rising pivot highs has no 1-10 day continuation in excess of the universe, at daily tier".
- Not tested after this (to be carried on the do-not-redo row): stop/target exits (exit at PH1 or below PL_cur), k other than 3,
  weekly bars, intraday pivots, the SHORT mirror (lower high in falling lows), breakout-level retest (branch D), deep momentum
  pullback 3-10d (branch E). Runner `research/sim/hl_bounce.py`; out `data/research/program/hl_bounce_out.txt`.

## Amendment - Study BNC-IBS (N 1056): pre-register 2026-10-19 (same request), before any outcome; N 1055 -> 1056
- Question (the user's premise, isolated): does WAITING FOR THE BOUNCE after a dip beat buying the dip? Tested on the live IBS universe
  (18 ETFs in config.yaml ibs_symbols, all 18, no momentum rank) so the comparator is the live leg's own form.
- Data: Sharadar SFP via `sharadar.prices` (split-adjusted OHLC; total-return scale by closeadj/close applied to open and close), 2003-01..
  2026-09. IBS(d) = (C-L)/(H-L) on day d; signal day d: IBS(d) < 0.2. Costs 5bp/side (ETF tier), shock 15bp/side.
- Arms (per signal day d, per name):
  DIP (live form, baseline): buy open d+1 -> sell open d+2.
  WAIT (unconditional one-day delay): buy open d+2 -> sell open d+3.
  BNC-O: close(d+1) > close(d) (up day after the dip): buy open d+2 -> sell open d+3.   NOB: close(d+1) <= close(d), same legs.
  BNC-C: close(d+1) > close(d): buy close d+1 -> sell open d+2 (the bounce night itself).
  BNC-H: close(d+1) > high(d) (reclaim of the dip bar): both the close d+1 -> open d+2 and the open d+2 -> open d+3 legs.
- Stats per arm and period (2003-15 PRIMARY, untouched for every bounce form; 2016-26 reported): mean, net, median, hit, day-clustered
  t (daily means, NW lag 1), halves, ex-top-5 days, per-year table. Paired: BNC-O minus WAIT and BNC-O minus NOB on common dates.
- PASS (bounce thesis): BNC-O or BNC-C net >= +15bp/trade, day-t >= 2.5, both halves > 0, median > 0, ex-top-5 > 0 in BOTH periods, AND
  BNC-O minus NOB >= +10bp (t >= 2) (the confirmation carries information rather than the calendar). KILL otherwise, stated as: "on the
  live IBS ETF universe, waiting for an up-close after an IBS<0.2 dip does not add to, and may forfeit, the dip's next-open edge".
- Not tested after this: the top-3 momentum rank, a 15:40 intraday confirmation, holds beyond one session, single stocks, the night leg's
  -8% picks (TREND-NIGHT/M2-M5 already cover multi-day there). Runner `research/sim/bnc_ibs.py`; out `data/research/program/bnc_ibs_out.txt`.
  Program N = 1056.

## RESULT - HL-BOUNCE (N 1055, 2026-10-19, one look): KILL in both universes and both periods; the uptrend structure adds nothing
- Signals: ETFs 17,148 liq (A1 4,116 in 2016-26 / 1,838 in 2003-15); stocks 152,772 liq (A1 25,905 / 23,366). Excess vs the EW liq
  universe, buy open s+1, 10bp RT.
- A1 (higher low inside rising highs) H5: stocks 2016-26 -5.5bp gross, -15.5 net, t -2.2, median -10.3, hit 49%, halves -14.3/-13.0,
  ex-top-5 -17.2; 2003-15 -7.4 / -17.4, t -1.2, halves -24.1/+8.6. ETFs 2016-26 -12.2 / -22.2 (t -1.8, halves -1.8/-23.4); 2003-15
  -8.9 / -18.9. H1, H3, H10 all <= +1.6bp in every cell. 0 of 4 primary cells pass.
- A1 - A2 (lower-low control) date-paired: -8.8 / -10.5 (ETF), -8.3 / -5.3 (stock) bp, |t| <= 1.1: a higher low is no better than a lower
  low (bar was +10). A1 - not-A1: -7..+1. A2 is itself negative (stocks -7..-12, ETFs -2.5 / -21.4).
- Diagnostics: deepest-pullback tercile is the worst (-16..-23bp) and the shallowest is ~0..+2.6; no ADV tercile positive; close>SMA200
  does not rescue (stocks -2.4 / -7.7). By year (stocks): 20 of 25 years <= +7bp, best 2015 +20, 2024 +4, 2025 +6, 2026 -19.
- Read: the "confirmed bounce" bar is a short-term up move in a liquid name, and liquid names mean-revert over 1-10 days, so buying it is
  buying after the bounce; the structure labels (higher low, rising highs) do not change that. Consistent with CHART-YOLO (bull shapes
  contrarian) and AT3/TREND-NIGHT (uptrend dips bounce less). Verdict as registered. Not tested: stop/target exits, k != 3, weekly bars,
  intraday pivots, the short mirror, breakout-level retest, deep 3-10d momentum pullback. Program N = 1056.

## RESULT - BNC-IBS (N 1056, 2026-10-19, one look): KILL; waiting for the up-close carries no information and forfeits the dip night
- 21,839 IBS<0.2 name-days on the 18 ibs_symbols (no momentum rank). 2003-15 (primary): DIP +16.9bp gross / +6.9 net (t 4.0, median
  +14.9); WAIT +9.7 / -0.3 (t 2.5); BNC-O +12.4 / +2.4 (t 1.3, halves +0.2/+10.5); NOB +6.3; BNC-C (bounce night) +2.5 / -7.5; NOB-C
  +11.5 (t 4.0); BNC-H reclaim +0.4 / -9.6 and +10.0 / 0.0. Paired BNC-O - WAIT -0.5 (t -0.4); BNC-O - NOB -0.3 (t -0.1).
- 2016-26: DIP +13.2 / +3.2 (t 3.0); BNC-O +6.2 / -3.8 (t 0.7, halves +11.1/-5.8); NOB +15.8 / +5.8 (t 3.0); BNC-O - NOB -7.7 (t -2.1),
  i.e. the dipped names that did NOT bounce on d+1 are the better buys; BNC-H reclaim night -8.6 gross. 0 of 2 periods pass.
- Caution on one printed line: "BNC-O - DIP (same signal days)" (-42bp) conditions DIP's window on the d+1 up-close that overlaps it and
  is NOT a valid comparison; ignore it. The valid comparisons are BNC-O vs WAIT and vs NOB.
- Read: on this universe the dip's edge is the next-open entry; one day later it has halved (WAIT), and the up-close filter selects the
  half that already bounced. Verdict as registered. Not tested: top-3 momentum rank, 15:40 confirmation, holds > 1 session, stocks.
  Program N = 1056.

## Amendment - Studies DEEP-PULL (N 1057) and BRK-RETEST (N 1058): pre-register 2026-10-19 (bounce tree, level 2), before any outcome; N 1056 -> 1058
- These are the two siblings left open by HL-BOUNCE/BNC-IBS (branches E and D). Same data and judge as HL-BOUNCE: `winsig` stock and ETF
  panels (liq: >= $5, ADV20 >= $20M), buy open s+1, excess vs the EW liq universe, 10bp RT, shock 30bp, periods 2016-26 and 2003-15,
  `winsig.passes` bar in BOTH periods. One run, no re-tuning. Weekly bars (branch F) are NOT run: ~6 events/yr per name, ceiling < 1pp.
- DEEP-PULL (N 1057): a confirmed bounce (HL-BOUNCE pivot definition, k=3, first close above the pivot bar's high within 10 bars) in a name
  that was AT a 52-week high recently: max close over the 60 bars before the pivot low >= 0.97 x the 252-bar max close, and the pivot low
  sits 5-20% below that recent high (depth = pivot low / recent high - 1 in [-0.20, -0.05]). PRIMARY horizon H10 (the "hold for a week or
  two" the practitioners describe), H5 reported. Control: the same bounce in names NOT near a 52w high (recent high < 0.90 x 252d max).
  Ceiling: ARETE-DIP-like frequency (~hundreds/yr); even at +25bp/10d net x 50% capital ~ +3pp/yr: below the gate, run on the user's
  instruction as the last open leaf of the pullback branch. KILL statement: "a confirmed bounce from a 5-20% pullback in a recent
  52-week-high name has no 5-10 day continuation over the universe". Not tested after this: holds > 10d, trailing stops, 52w-high
  defined on intraday highs, weekly bars.
- BRK-RETEST (N 1058): breakout at bar b = close > max close of the prior 50 bars (level L = that prior max). First retest within [b+3,
  b+30]: low[t] <= 1.01 x L and close[t] > L (touch-and-hold), buy open t+1. PRIMARY H5, H10 reported. Control: the failed retest
  (close[t] < L on the touch day, same window) and the breakout day itself (buy open b+1). KILL statement: "the first pullback to a 50-day
  breakout level that holds on the close has no 5-10 day continuation over the universe". Not tested after this: 20d / 252d levels,
  touch tolerance != 1%, intraday retests, a volume condition on the breakout, the short side of failed retests.
- Runner `research/sim/pull_retest.py` (imports `hl_bounce.pivots`); out `data/research/program/pull_retest_out.txt`. Program N = 1058.

## RESULT - DEEP-PULL (N 1057) + BRK-RETEST (N 1058), 2026-10-19, one look: KILL, all four primary cells
- DEEP-PULL E1 (H10 excess vs EW liq, 10bp RT): stocks 2016-26 n 25,081: -1.6bp gross / -11.6 net, median -14.6, hit 49%, halves
  +3.7/-8.3, ex5 -11.5; 2003-15 n 24,491: +3.5 / -6.5, t 1.0, median -0.3, halves +9.1/+8.9, ex5 +3.3 (the only cell with both halves
  positive, and it is below cost). ETFs: 2016-26 +2.3 / -7.7 (median +12.4 but halves +14.1/-47.8, ex5 -33.3); 2003-15 -22.5 / -32.5
  (t -2.8). The far-from-high control (E2) is indistinguishable (-5.9 / +3.8 stocks); the shallow (<5%) arm is -5.9 / -8.6 and the >20%
  arm -3.8 / -54.7. By year (stocks) the best years are 2019 +37 and 2021 +59; 2018 -54, 2020 -61, 2022 -52: it is a regime bet.
- BRK-RETEST D1 (H5): stocks 2016-26 n 28,859: +8.3 / -1.7 (t -0.7, median -0.9, halves +7.8/-19.2, ex5 -10.8); 2003-15 n 27,310:
  -1.0 / -11.0. ETFs +4.9 / -5.1 and -0.1 / -10.1. The failed-retest control (close back below the level) earns the same (+2.9 / +2.0
  stocks): whether the level "holds" on the close carries no information about the next week. The breakout day itself is -5.5bp
  (t -2.4) in stocks, consistent with the loop's "breakouts fade" finding.
- Read: level 2 of the bounce tree is closed. Every leaf (structure, confirmation, momentum pullback, breakout retest) is <= 0 in excess of
  the universe at the daily tier, in both the discovery and the untouched periods. Not tested (carried on the rows): holds > 10d,
  trailing stops, other level lookbacks/tolerances, intraday retests, weekly bars, short sides. Program N = 1058.

## Amendment - Study ETF-PD (N 1059): pre-register 2026-10-19 (open loop, pivot 1), before any outcome; N 1058 -> 1059
- Why reopened: the ETF premium/discount family was CLOSED on SPY (ETC), broad SPDRs (EF) and bond SPDRs (BSPD) and marked
  "do not re-open without new data; a smaller/international fund needs its own NAV history". The WRDS reconciliation (2026-10-16)
  found `crsp_q_mutualfunds.daily_nav` + `fund_hdr_hist` (et_flag F): daily NAV for 6,637 US ETFs incl. dead funds, 2010-01..2026-06,
  with dated tickers. That is the new data. Petajisto (2017) reports the mispricing lives in illiquid / international / bond ETFs
  where AP arbitrage is costly, not in SPY.
- Mechanism: APs arbitrage ETF price to NAV only when the creation/redemption cost (basket spread, FX, foreign-market closure) is below the
  deviation; between those bounds retail order flow moves the price away from NAV and it reverts within a day. Named counterparty: retail/
  flow traders on the wrong side of a thin ETF's close. Competing explanation to measure: STALE NAV (international funds: price leads NAV
  after the foreign close), in which case NAV moves to price and there is nothing to trade.
- Ceiling (gate): ~2,000 live ETFs/day, bottom decile ~200, executable (ADV20 >= $5M) ~50. If the deepest-discount names earn +15bp net
  per session at 50% of capital: 250 x 15bp x 0.5 x 50% capture ~ +9pp/yr at $10k; thin names have no capacity issue at $2-25k. Clears
  on paper; the test decides whether +15bp net exists in executable names.
- Data: NAV panel pulled to `data/research/etf_pd/nav.parquet` (crsp_fundno, caldt, dnav, ticker valid that day); prices = Sharadar SFP
  (winsig etf panel: non-leveraged ETFs, delisted included), RAW close = closeunadj, raw open = open x closeunadj/close. Premium
  p_d = closeunadj_d / dnav_d - 1; drop |p| > 20% (bad prints/splits). Signal z_d = p_d - median(p_{d-60..d-1}) (own-history
  centred, removes persistent stale-NAV offsets and fee effects). Universe each day: ETFs with a NAV, >= 60 prior premia, closeunadj >= $5,
  ADV20 >= $1M. Ranked into deciles daily (D1 = deepest discount vs own history).
- Legs (auction fills; the NAV is published after the close, so the first executable fill is the d+1 open cross): S1 = open d+1 -> close
  d+1 (PRIMARY, one session); N1 = open d+1 -> open d+2; W5 = open d+1 -> close d+5. Excess vs the EW universe of the same ETFs that day.
  Costs 10bp RT flat, shock 30bp. Executability bucket: ADV20 >= $5M at 30bp RT.
- Reported: D1..D10 means (monotonicity), D1 and D10 full stats (mean, net, median, hit, NW t on daily means, halves 2010-17 / 2018-26,
  ex-top-5 days, shock), D1 by category (international / bond / domestic equity / other by fund-name regex) and by ADV bucket, by year;
  mechanism split: next-day NAV change and next-day price change regressed on z by category (stale NAV vs mispricing).
- PASS: D1 S1 net >= +15bp, NW t >= 3, both halves > 0, median > 0, ex-top-5 > 0, D1 > D5 > D10 (monotone), AND the ADV >= $5M bucket
  net >= +10bp at 30bp RT. KILL otherwise, stated as: "own-history ETF discounts carry no executable next-session reversion in US ETFs
  2010-26 at auction fills". Not tested after this: the premium short side, intraday (non-auction) entries, international funds with an
  FX/futures hedge, creation-flow (shares outstanding) conditioning, holding to NAV convergence beyond 5 sessions.
- Runner `research/sim/etf_pd.py` (pull | run); out `data/research/program/etf_pd_out.txt`. Program N = 1059.

## RESULT - ETF-PD (N 1059, 2026-10-19, one look): KILL; the ETF premium/discount family is closed delisted-complete
- Panel: 2,737 ETFs with CRSP NAV and Sharadar prices, 2.89M name-days, 4,149 sessions 2009-12..2026-06. Premium median +2.2bp, p10 -19.5,
  p90 +32.6; own-history z p10 -23.3 / p90 +20.8: US ETF deviations from NAV are a few tens of bp even at the tails.
- D1 (deepest discount) S1 (open d+1 -> close d+1) excess vs the EW universe: +0.9bp gross, -9.1 net, median +1.0, hit 51%, NW t 2.7,
  halves +0.6/+1.4, ex5 +0.7, shock -29.1. N1 +1.0, W5 +1.4. D10 -1.4 (t -3.7). Deciles monotone but the whole D1-D10 span is ~2bp.
  Bond D1 +2.8, intl +1.0, domestic -0.3; ADV > $50M +2.0, $5-50M +0.4; ADV >= $5M at 30bp RT net -29.1 (bar +10). No year above +8bp.
  1 of 7 registered gates (monotonicity) -> KILL.
- Mechanism: per 100bp of z, next-day NAV moves +23 (bond) / +59 (domestic) / +61 (intl) bp toward the price, and the price moves only
  -13 / -16 / -19bp. The deviation is mostly information the NAV has not yet absorbed (stale or lagged pricing), and the tradable residual
  on a 20bp tail is ~3bp: inside any spread. Verdict as registered. With SPY (ETC), broad SPDRs (EF), bond SPDRs (BSPD) and now every
  US ETF incl. dead funds, the ETF premium/discount family is CLOSED at the daily auction tier; do not reopen without intraday iNAV data
  and a specific constrained-AP episode (e.g. a creation halt).
- Ceiling-killed on paper this tick (no N): fallen-angel forced selling on ISSUER EQUITY (FISD PIT ratings): ~40 US fallen angels/yr x
  <= 1-2% equity effect around the index exit x ~10% of account per name ~ +0.4pp/yr; the bond side is not retail-executable at Schwab.
  Not tested: a pooled HY-ETF (HYG/JNK) rebalance-day arm (deep market; TME-class ceiling ~1-2pp).
- Not tested after ETF-PD: premium short side, intraday (iNAV) entries, FX-hedged international funds, creation-flow (shares outstanding)
  conditioning, holding to convergence beyond 5 sessions. Program N = 1059.

## Amendment - Study F-SALE2 (N 1060): pre-register 2026-10-19 (open loop, pivot 2), before any outcome; N 1059 -> 1060
- Completes F-SALE (N 1054), which was killed "at this flow proxy" with the hypothesis explicitly untested at a proper flow measure. New
  data: `crsp_q_mutualfunds` has its OWN holdings (`holdings`, keyed by crsp_portno, with permno/cusip, 460M rows) plus `monthly_tna` and
  `monthly_returns`, so Coval-Stafford / Edmans-Goldstein-Jiang flow-induced pressure can be built without MFLinks.
- Mechanism (unchanged): open-end funds facing redemptions must sell pro rata; the sold stocks are pushed down in the event quarter and
  revert over the following quarters. Named constrained counterparty: the redeeming fund.
- Measure (Edmans et al. 2012 MFFlow, hypothetical pro-rata sale, exogenous to the fund's choice): for domestic equity portfolios
  (fund_style crsp_obj_cd 'ED%', share classes summed per crsp_portno), quarterly flow pct = sum over months of
  [TNA_m - TNA_{m-1}(1+r_m)] / TNA at the prior quarter end. For portfolios with flow <= -5%: sell_sh_iq = sum_j flowpct_jq x shares_ij
  (shares held at the latest report date before the quarter start, within 6 months). Mirror buy_sh for flow >= +5%. PRESSURE_iq =
  sell_sh_iq / quarterly share volume of stock i (days of volume, negative); permno -> Sharadar ticker via ncusip/cusip map.
- Design, same as F-SALE's registration: eligible = prev close >= $5 and $ADV20 >= $10M, EW bottom decile of PRESSURE each quarter
  (most fire-sold), held the next quarter (close q-end -> close q+1-end as the proxy, disclosed; the registered open-cross entry at q-end +
  60d is stricter), benchmark EW eligible universe with a pressure value and SPY. Also report the Coval-Stafford variant (sell pressure
  from funds with flow <= 5th percentile only) as a diagnostic.
- PASS (F-SALE bar): bottom-decile next-quarter excess vs eligible EW >= +150bp, quarter-clustered t >= 2, median quarter > 0, both halves
  (2010-17 / 2018-26) > 0, ex-top-5 quarters > 0, bottom > middle deciles, AND the pressure-quarter return of the bottom decile < EW (the
  fire sale must be visible). KILL otherwise, stated as: "flow-induced mutual-fund selling pressure carries no exploitable next-quarter
  reversal in $5+/$10M+ US stocks at a 60-day lag". Ceiling (disclosed): quarterly, ~100% of capital, literature reversal ~+6-8%/yr gross
  -> ~+3-4pp at honest capture: BELOW the +8pp stand-alone gate; run because it completes an open registration and is the one named-
  counterparty mechanism with newly available data. A PASS is a Roth sleeve over beta, not a 2x.
- Not tested after this: monthly rebalance (needs monthly holdings / N-PORT), the inflow-bought short side, ETF fire sales, lags < 60d.
- Runner `research/sim/f_sale2.py` (pull | run); data `data/research/fsale2/`; out `f_sale2_out.txt`. Program N = 1060.

## CORRECTION - F-SALE (N 1054) decile labels were inverted (found 2026-10-19 while building F-SALE2)
- `f_sale.py` defines pressure = (sell_p - buy_p)/advsh, so POSITIVE = net flow-forced selling, but the comment says "negative = net
  fire-sold" and run() labels the LOWEST decile "most fire-sold". The printed D1 (mean pressure -4.32 days of volume) is therefore the most
  INFLOW-BOUGHT decile and D10 (+2.54) the most fire-sold.
- Re-read of the recorded numbers with correct labels: fire-sold D10 earned +464bp in the pressure quarter vs ~+600 for the middle deciles
  (the fire sale IS visible, ~-150bp relative) and -11bp excess the next quarter (NO reversal, t -0.3). Inflow-bought D1 earned +745 in the
  pressure quarter (+128 vs EW, t 3.3) and -80bp excess the next quarter (t -2.1): inflow pressure reverses, outflow pressure does not.
- Verdict unchanged (KILL for the long side; the registered gates fail on either labelling), but the recorded mechanism statement ("flags funds
  trimming winners, falsifies the proxy") was wrong: the s12 proxy did reproduce the event-quarter price pressure on the fire-sold side.
  The row in NEXT.md is annotated. Lesson: print the mean signal value per decile next to the label on every sort (done here, which is how
  the inversion was caught); never trust a sign comment.

## RESULT - F-SALE2 (N 1060, 2026-10-19, one look): KILL; the fire sale is visible, the reversal is not
- Panel: 222k (permno, quarter) pressure rows 2009Q1-2026Q2 from 18 server-side yearly queries (sell median 21 / buy median 24 funds per
  stock-quarter); 7,901 Sharadar tickers; 83,659 eligible stock-quarters ($5+, $10M+ ADV), 64 judged quarters 2009Q1-2024Q4. Pressure
  median -0.011 days of volume, p10 -0.52, p90 +0.54.
- Mechanism (registered check) PASSES strongly: D1 (most flow-forced selling) pressure-quarter excess vs EW -273bp (median -206, hit 0.16,
  t -6.3, ex-top-5 -319); raw pressure-quarter returns are monotone D1 +356 ... D10 +910. Flow-forced selling is in the price.
- Reversal FAILS: D1 next-quarter excess vs EW +15bp (median +48, hit 0.61, t 0.49, ex-top-5 -19), vs SPY +23; halves +38 / -14; by year
  -370 (2020) .. +253 (2023). D10 (inflow-bought) -25 (t -0.6). 3 of 8 gates (median, h1, monotone-vs-middle, mechanism) -> KILL.
- Read: at the quarterly horizon flow pressure behaves like information (or like Lou-2012 persistence that has already run), not like a
  liquidity dislocation that snaps back; the Coval-Stafford reversal, if it exists, is a 12-18 month phenomenon (diagnostic below), i.e. a
  slow value-like sleeve, not a $2-25k edge. Verdict as registered. Not tested: 2-4 quarter holds as a registered rule, monthly lag (CRSP
  monthly TNA permits it; holdings stay quarterly), ETF fire sales, the inflow short side. Program N = 1060.
- DIAGNOSTIC (unregistered, not a verdict): D1 cumulative excess vs eligible EW over q+1..q+k, non-overlapping quarters only (every k-th quarter)
    k=2: all quarters mean +11bp (n 64); non-overlapping mean +24 med +77 t 0.31 (n 32); D10 -75
    k=4: all quarters mean -63bp (n 64); non-overlapping mean -17 med +75 t -0.09 (n 16); D10 -198
    k=6: all quarters mean -175bp (n 64); non-overlapping mean -183 med -121 t -0.67 (n 11); D10 -369

## Open-loop close-out 2026-10-19: candidates ceiling-killed on paper (no N, no backtest), so the next agent does not redo them
Gate: ceiling %/yr = events/yr x net edge x share of account x honest capture (<= 50%), kill if < +8pp at $10k.
- Single-stock OPEX pinning toward the max-OI strike (OptionMetrics opprcd OI by strike is available): 12 monthlies (+ ~40 weeklies in
  the ~500 names with weeklies) x <= 30bp x 50% capital x 50% = +1.8..4pp. Index OI-pinning already killed (N 1065-era opex_pin). Not run.
- Per-stock signed dealer gamma -> next-day continuation: GAMMA-MKT (index) killed, LUCK-B4 (per-stock option state, random rules) null;
  conditional continuation effects in the literature are <= 10bp/day -> ceiling marginal, prior low. Not run.
- SPX AM-settlement (SOQ) open-cross dislocation fade on the third Friday (TAQ ms available): ~12/yr x <= 20bp x 100% = ~2.4pp. Not run.
- Mutual-fund liquidations (fund_hdr end dates) -> forced sale of holdings: liquidating funds are small, sold stakes are tiny vs ADV. Not run.
- ADR premium vs home-market close: same stale-price structure ETF-PD just measured (deviation = information the lagging leg absorbs);
  cross-venue inaccessible at Schwab. Not run.
- SPAC trust-value yield (buy below trust, redeem): redemption is a manual election with weeks of capital lock = the odd-lot tender
  objection (user retired tenders 2026-10-13). Not run.
- Earnings-announcement night (IBES anndats/anntims on WRDS would give exact timing): DS1 (Round 29) already dead on 2021-26 at +0..+6bp
  gross; pre-FOMC drift is addendum 33 (F3 adopted small). Not re-run.
- Status after this loop (N 1055-1060, six kills + one correction): the data-unlocked frontier from the WRDS reconciliation is now measured
  (borrow, index gamma, skew/term, ETF NAV, fund flows). Remaining DATA-LIMITED rows are unchanged (margin-rate history, custodial borrow
  fees, intraday iNAV, N-PORT monthly holdings). Program N = 1060.

## Amendment - Studies REC-RECALL (N 1061), NIGHT-SHORT (N 1062), STK-IBS-OPEN (N 1063): pre-register 2026-10-25, before any outcome; N 1060 -> 1063
Source: `docs/research/hypothesis-space.md` (built 2026-10-25 from NEXT do-not-redo + docs/memory + this ledger). After N 1060 only three cells
clear the +8pp-at-$10k paper gate and are runnable on data on disk; all three are registered here as one-look studies. No tuning of any cutoff.

### REC-RECALL (N 1061): pre-ex-date covering window in hard-to-borrow dividend payers (the deferred RECORD-RECALL leaf, 2026-10-19)
- Mechanism: lenders recall loaned shares before the holder-of-record date (dividend tax / substitute-payment reasons; Thornock 2013), so short
  sellers in hard-to-borrow names must cover in the sessions before the ex-date. Named constrained counterparty: the recalled short.
- Rule (fixed, standalone long, auction-executed): buy the closing cross at E-5, sell the closing cross at E-1 (E = ex-date; the ex drop is
  excluded), for ordinary cash dividends (CRSP distcd 12xx) in names whose option-implied borrow fee (`optionm.borrate`, nearest-30d tenor,
  -99.99 dropped, as of E-6) is in the top decile of that month's cross-section. Eligible: prev close >= $5, $ADV20 >= $5M.
- Data: WRDS `crsp.dsedist` (exdt) x `optionm.borrate` x `crsp.dsf` 2001-2024 (CRSP ends 2024-12); permno->secid via
  `wrdsapps_link_crsp_optionm.opcrsphist`. No record-date rule exists in the program, so the whole period is a first look.
- Benchmark: the same name's unconditional 4-session close->close return (all non-event windows), and the same fee-decile EW universe over the
  same calendar window. Report fee deciles D1..D10 (print the mean fee next to each decile label; assert the sign in code).
- PASS: D10 excess >= +40bp/event net (tier 5bp/side), day-clustered t >= 2, median > 0, both halves (2001-12 / 2013-24) > 0, ex-top-5 > 0,
  and monotone (D10 > D5 > D1). WEAK: +20..+40bp with t >= 2 (below the gate; forward shadow only). KILL otherwise, stated as "the pre-ex
  covering window in top-decile borrow-fee dividend payers carries no exploitable long return at the closing crosses".
- Ceiling (disclosed): ~60 full-capital 4-session holds/yr x net x 50% capture: +12pp at +40bp, +6pp at +20bp.
- Not tested after this: proxy (DEF 14A) record dates (needs SEC_USER_AGENT), the short side after the record date, custodial (not
  option-implied) fees, intraday entries, 2025-26 (CRSP not licensed there).
- Runner `research/sim/rec_recall.py`; data `data/research/rec_recall/`; out `data/research/program/rec_recall_out.txt`.

### NIGHT-SHORT (N 1062): the night leg's short mirror (close cross -> open cross), taxable margin only
- Rule: daily-bar proxy of the live night rule mirrored: day_ret >= +8% and IBS >= 0.90 at the close, prev close >= $5, $ADV20 >= $10M,
  domestic common stock; short the closing cross, cover the next opening cross; net 5bp/side + 2bp overnight borrow; excess vs the EW
  eligible-universe overnight (so the overnight premium is netted out).
- Why it is not a costume: every prior short was intraday (Study S, GAP-SHORT, Lab-BA, NEWS-HALT, SSR-LIFT) or a tilt; the overnight short of
  a close-at-high crash-up is the "short side: not tested" sibling on INTRA-ANY, PREMKT-CROSS, BRK-RETEST, HL-BOUNCE, ETF-PD, F-SALE2.
- Prior: negative (OVN-MOM N 939, GAP-NIGHT N 1050: attention names earn the overnight premium). The value is a class kill.
- Data: Sharadar SEP 2003-26 (delisted-complete). Judge 2003-15 (never used for any short rule); report 2016-20 and 2021-26 separately.
- PASS: 2003-15 short return (negative of the overnight excess) >= +15bp/night net, day-clustered t >= 2, median night > 0, ex-top-5 > 0, both
  subperiods (2003-08 / 2009-15) > 0. KILL otherwise, stated as "shorting close-at-high +8% names overnight at the crosses loses or is ~0;
  the short side of the night-leg family is closed at daily tier". Roth excluded by rule (no shorting).
- Ceiling: ~250 nights/yr x +15bp x 50% size x 50% capture = +9pp. Squeeze tail applies (SSR-LIFT maxDD -41% at 0.5x).
- Not tested after this: exact 15:40 minute form (SIP 2016-26) unless the proxy passes; ETB-filtered universe (borrow availability not on
  disk); holding past the open cross; cutoffs other than the mirror (+8% / 0.90) by construction.
- Runner `research/sim/night_short_mirror.py`; out `data/research/program/night_short_out.txt`.

### STK-IBS-OPEN (N 1063): the ETF IBS leg's open-to-open form on liquid single stocks, disjoint from the night leg
- Rule: on day d, name in the top 500 by 20d $ADV (prev close >= $5, domestic common), IBS < 0.2 and day_ret > -4% (disjoint from the night
  leg and NIGHT-BAND); buy the d+1 opening cross, sell the d+2 opening cross; equal weight across signals; tier 5bp/side; excess vs the EW
  top-500 universe open(d+1)->open(d+2).
- Why it is not a costume: the IBS leg was only ever run on ETFs (18 names; "all liquid ETFs" dead); stock forms were close-cross entries
  with a drop gate (night leg, NIGHT-BAND). The one-session open-to-open stock form has no row.
- Prior: low (NIGHT-BAND -4..-8% ~ +4bp gross; ETF leg 2003-15 net +5bp t 1.0).
- Data: Sharadar SEP 2003-26. Judge 2003-15 (touched for the ETF rule, never for a stock rule; say so). Report 2016-20 and 2021-26
  (official open crosses on disk if cheap; else Sharadar open, which matched the cross 2016-20 per SPLIT-CROSS).
- PASS: 2003-15 net >= +10bp/signal-day, day-clustered t >= 2, median day > 0, ex-top-5 > 0, both subperiods > 0, and 2016-26 same sign.
  KILL if net < +8bp or t < 2. Stated as "IBS<0.2 without a large drop, bought at the next open cross and sold at the following open cross,
  earns < +8bp net in liquid US stocks 2003-15".
- Ceiling: 250 x +15bp x 100% x 50% = +19pp paper; ~0 at +4bp gross.
- Not tested after this: IBS cutoffs other than 0.2 and universes other than top-500 ADV (no tuning); close-cross entry (that is the
  night family); multi-day holds; ETF-momentum-style ranking within the stock set.
- Runner `research/sim/stk_ibs_open.py`; out `data/research/program/stk_ibs_open_out.txt`. Program N = 1063.

## RESULT - STK-IBS-OPEN (N 1063, 2026-10-25, one look): KILL
- Judge 2003-15: net -4.1bp/signal-day (gross +5.9, below the 10bp round trip), t -1.78, median +0.6, ex-top-5 -5.5, subperiods 2003-08 -2.4 /
  2009-15 -5.6, 2016-26 -1.6 (same sign). 3,246 judge signal days, ~93 names/day (550k name-days 2003-26). Only 2003 and 2020 clear +5bp net.
- The registered sentence holds: "IBS<0.2 without a large drop, bought at the next open cross and sold at the following open cross, earns < +8bp
  net in liquid US stocks 2003-15". Excess vs the EW top-500 open-to-open is +1.7bp (t 1.5), carried by 2003-08 and 2022; the universe's own
  open-to-open drift (+2.4..+6.6bp) exceeds the signal's increment in every period. ETF anchors on the same days: SPY +8.4 (t 1.4), QQQ +7.5
  (t 1.2) 2003-15, consistent with the ETF leg's known 2003-15 prior. Read: by the d+1 open the overnight bounce has already happened.
- Diagnostic read (not a rule): signal days where SPY's own IBS<0.2 are net positive (+4.4 judge) but their excess vs the universe is ~0 or
  negative (-2.1, t -1.3): market beta, not a stock signal. Days with SPY IBS>=0.2: +2.7 excess (t 1.9), below cost.
- Prices: Sharadar open for all periods (no official open-cross series exists on disk for this set; the night cache holds only night picks).
- Not tested: as registered (other IBS cutoffs / universes, close-cross entry, multi-day holds, ranking within the set) plus official 2021-26
  open crosses. Runner `research/sim/stk_ibs_open.py`; out `data/research/program/stk_ibs_open_out.txt`.

## RESULT - NIGHT-SHORT (N 1062, 2026-10-25, one look): KILL; the short side of the night-leg family is closed at daily tier
- Judge 2003-15 (2,229 nights, 16,509 name-nights): excess short net -12.8bp/night (t -3.01), median -1.0, hit .49, ex-top-5 -15.4, subperiods
  -16.8 / -9.1; raw short net -14.8 (t -3.2). All six gates fail. 2016-20 -24.9 (t -3.3), 2021-26 -7.8 (t -1.4). Gross the short excess is
  ~-1bp in 2003-15: the mechanism is ~0 and the 12bp cost makes it a loser; in 2016-20 the picks earn +12.9bp over the universe overnight
  (OVN-MOM/GAP-NIGHT's attention premium), so the short loses most there.
- Registered sentence holds: "shorting close-at-high +8% names overnight at the crosses loses or is ~0; the short side of the night-leg family
  is closed at daily tier". Wins only in bear years (2008 +29, 2022 +27, 2015 +5, 2026 YTD +8): short-beta plus short-momentum.
- Volunteered, post-hoc, NOT judged (selection on 2003-15): the >20% day-return bin shorts at +53.1 mean / +47.9 median / hit .65 / t 3.25 /
  ex-top-5 +32.6 (390 nights, 892 name-nights, ~30 nights/yr); 8-12% is -16.3 (t -4.4), 12-20% -3.7. Crowded nights (>10 names) +12.7 (t 2.3,
  183 nights) = bear-rally regime. Size bins: none pass.
- Not tested: exact 15:40 minute form, ETB-filtered universe, holding past the open cross, cutoffs other than the mirror (the >20% bin is
  registered separately below as NIGHT-SHORT-20, judged on 2016-26 which was never inspected for that bin).
- Runner `research/sim/night_short_mirror.py`; out `data/research/program/night_short_out.txt`.

## Amendment - Study NIGHT-SHORT-20 (N 1064): pre-register 2026-10-25, before any outcome; N 1063 -> 1064
- Origin: the >20% day-return bin volunteered by NIGHT-SHORT on 2003-15 (selection sample; the number above was read, so 2003-15 cannot judge).
- Rule: day_ret >= +20% and IBS >= 0.90 at the close (daily bars), prev close >= $5, $ADV20 >= $10M, domestic common; short the closing cross,
  cover the next opening cross; net 5bp/side + 2bp borrow; excess vs the EW eligible-universe overnight. No other cutoff is touched.
- Judge: 2016-01-01..2026-09-30 (never inspected for this bin). Report 2016-20 and 2021-26 and the per-year table; report 2003-15 as the
  selection sample only.
- PASS: 2016-26 excess short net >= +25bp/night, day-clustered t >= 2, median > 0, ex-top-5 > 0, 2016-20 and 2021-26 both > 0, hit >= 0.55.
  KILL otherwise, stated as "the >20% close-at-high overnight short does not survive out of its selection sample".
- Ceiling (disclosed, BELOW the +8pp gate): ~30 nights/yr x +50bp x 0.5 size x 50% capture = ~+4pp, taxable margin only, borrow availability
  unmodelled, squeeze tail. Run because it is a 10-minute read on a built runner; a PASS is a small taxable sleeve to forward-shadow, not a 2x.
- Not tested after this: holding past the open, ETB filter, exact 15:40 form, the 12-20% band, long side of the mirror (that is the live leg).
- Runner: `research/sim/night_short_mirror.py --min-dr 0.20` (or a sibling function); out `data/research/program/night_short20_out.txt`. Program N = 1064.

## RESULT - NIGHT-SHORT-20 (N 1064, 2026-10-25, one look): KILL; the >20% close-at-high overnight short does not survive out of its selection sample
- Judge 2016-26 (747 nights, 1,557 name-nights, ~70 nights/yr): excess short net -27.6bp/night (t -0.99), median +22.8, hit .56, ex-top-5
  -44.5; 2016-20 -51.8, 2021-26 -16.0. 2 of 7 gates (median, hit). Selection sample 2003-15 was +53.1 (t 3.25), in-sample.
- Shape: classic squeeze profile. The median night wins (the typical name mean-reverts) and a broad right tail of continuation destroys the
  mean (2018 -213, 2021 -266bp/night; picks continue +200-270bp gross on those years). ex-top-5 -44.5 vs mean -27.6: the tail is broad.
  Borrow modelled at 2bp; these are the names where borrow is actually hard, so real costs are higher.
- Volunteered, not judged: 100-500M ADV bin +44 mean / +75 median (t 1.1, 196 nights); >500M -382 (t -2.0); 3-5-name nights -142 (t -2.1).
  Nothing clears the bar. Not tested: holding past the open, ETB filter, 15:40 form, 12-20% band. Runner `research/sim/night_short_mirror.py
  --min-dr 0.20`; out `data/research/program/night_short20_out.txt`. Program N = 1064.

## RESULT - REC-RECALL (N 1061, 2026-10-25, one look): KILL (WEAK by bars, placebo-equal; the recall mechanism is unsupported)
- 127,275 eligible ordinary-dividend events 2001-24 with an option-implied fee at E-6 (36% of 464k CRSP 12xx events; D10 = 5,033 events,
  ~210/yr, 2,023 names, no single name carries it). Decile mean fees asserted monotone (D1 0.1% .. D10 29.5%/yr).
- D10, buy close E-5 sell close E-1, net 10bp: raw +35.3bp (t 3.6); excess vs own-name baseline +29.4 (t 2.96, median +11, halves +25/+32,
  ex-top-5 +25); excess vs same-decile universe +21.3 (t 2.76, median +1.5, 2013-24 +14.4 t 1.3 median -10.7 hit .48). Monotone D10>D5>D1.
  By the bars: WEAK on both benchmarks (+20..+40, t >= 2), never +40.
- Placebo (E-10..E-6) reproduces it: D10 +24.3 / +19.6 (t 2.5 / 2.6) with the same decile profile. Paired same-event main minus placebo:
  -23 to -34bp (t -1.0 to -1.7). The excess is not specific to the covering window, so the stated mechanism (lender recall -> short covering
  E-5..E-1) is unsupported; under the protocol a number with no mechanism is a NO. No forward shadow.
- Volunteered: (1) the D10 fee at E-6 is a pre-dividend SPIKE (same-name fee E-6 minus E-36: +21.6pp mean, up in 92% of D10 events):
  OptionMetrics' implied borrow comes from put-call parity, so a dividend the vendor under-projects prints as "borrow fee" before ex. The
  top fee decile before an ex-date is partly a dividend-projection artifact. DATA RULE: `optionm.borrate` around ex-dates is contaminated;
  any borrow-fee study near dividends must use a fee read >= 30 sessions before ex or a custodial fee. (2) Low-fee payers (D1-D6) underperform
  their own baseline by 12-20bp (t -2..-3) in E-5..E-1: dividend payers are weak the week before ex (one look, not registered).
  (3) The unconditional D10 4-session base is +7.2bp vs +15-17 for D6-D9: BORROW-XS confirmed.
- Not tested: proxy (DEF 14A) record dates (needs SEC_USER_AGENT), the post-record short side, custodial fees, a fee read at E-36 instead of
  E-6 (would separate the standing-HTB names from the spike artifact; ceiling at the observed +21-29bp is ~+6-9pp before the placebo, so a
  clean re-run is below the gate unless the artifact-free subset is much stronger), 2025-26.
- Runner `research/sim/rec_recall.py` (pull | run); cache `data/research/rec_recall/` (~700MB); out `data/research/program/rec_recall_out.txt`.
- Session close: N 1061-1064 all KILL. The three cells that cleared the paper gate after N 1060 are now measured; the matrix has no Tier A
  cell left on data on disk. Program N = 1064.

## Amendment - Study LETF-REV (N 1065): pre-register 2026-10-26 (user picked branch 1 of the market scan), before any outcome; N 1064 -> 1065
- Origin: SS-LETF (N 877) confirmed that single-stock LETF rebalancing pushes 15:45 -> close in the day's direction (+3-5bp gross, placebo
  diff +5.9bp t 2.8) and killed the continuation trade. The reversal side was never read. Beckmeyer-Branger-Gayda find the LETF close
  impact "quickly reverts at the next day's open". Named counterparty: the LETF that must sell (buy) at the close of a down (up) day.
- Pressure I: exactly `ss_letf.panel()` (fund $ volume x leverage demand / underlying 20d $ volume), no redefinition. Period 2022-07..2026-09
  (the SS-LETF panel; the overnight leg of it is untouched). Underlying universe: names with >= 1 single-stock LETF (fund_map).
- Rule A (long, both accounts): day_ret <= -3% (LETF must sell at the close) and I >= 0.05; buy the closing cross, sell the next opening
  cross (Sharadar closeunadj -> next open, as in GAP-NIGHT); net 5bp/side. Excess vs (i) the EW overnight of all LETF-underlying names that
  night and (ii) the paired placebo of SS-LETF: same-day names with I = 0 and day_ret <= -3%.
- Rule B (read only, no short): day_ret >= +3% and I >= 0.05; report the overnight return vs the same benchmarks (a negative number = the
  up-side reversal; it would be a long-AVOID filter, since the short side is closed by NIGHT-SHORT).
- Tilt read: the live night-leg subset (day_ret <= -8% & IBS < 0.10) split by I >= 0.05 vs I = 0 (does pressure add to the live leg?).
- I buckets [0, 0.02, 0.05, 0.10, 0.20, 1): print the mean I next to each label; assert monotone labels in code.
- PASS (standalone A): net >= +15bp/night, day-clustered t >= 2, median > 0, ex-top-5 > 0, halves (2022-07..2024-06 / 2024-07..2026-09) > 0,
  treated minus placebo > 0, monotone in I. WEAK: +8..+15 with t >= 2 and placebo diff > 0 -> night-leg tilt candidate (forward shadow).
  KILL otherwise, stated as "the LETF close impact does not revert at the next open by more than the round trip in the names with it".
- Ceiling (disclosed, BELOW the gate): bounded by the measured impact (3-5bp average, +12-16 in the top names): ~+1-2pp as a night tilt,
  ~1pp standalone on top-I names. Run because the user picked it and the runner exists (30-min read).
- Not tested after this: holding past the open, entry before the close (that is SS-LETF), intraday 15:45 entry + open exit, index LETFs
  (Ivanov-Lenkey: modest), the short side.
- Runner `research/sim/letf_rev.py` (imports ss_letf.panel / fund_map); out `data/research/program/letf_rev_out.txt`. Program N = 1065.

## RESULT - LETF-REV (N 1065, 2026-10-26, one look): KILL standalone; the tilt read is a bettor-scale night-leg candidate (edge unproven)
- Rule A (day_ret <= -3%, I >= 0.05, close cross -> open cross): 366 nights, 38 names, 2024+ almost entirely (I >= 0.05 barely exists
  before 2024, so the halves gate is vacuous: H1 = 13 nights). Net +12.4bp/night (t 0.83), median +32.8, hit .58, ex-top-5 +4.2; excess vs
  the LETF-underlying EW overnight -1.5 (that universe earns +9.0bp/night itself); paired treated-minus-placebo +11.0 (t 0.93); I buckets
  non-monotone. Decaying: 2024 +58, 2025 +14, 2026 -8. Gates: 4/7, t fails. KILL as registered: "the LETF close impact does not revert at
  the next open by more than the round trip in the names with it"; at the median Rule A captures the high-vol-name overnight premium.
- Rule B (up days, read only): excess vs LETF-underlying EW -10.5 (t -1.0); only the top bucket I >= 0.20 reverses (-49.3, t -2.5, 158 nights,
  median -72). Non-monotone; ~70 name-days/yr; not a filter by the bars.
- Volunteered: the Rule A signal sits entirely in the <= -8% tail (I >= 0.05: +74.5 net, t 2.6, 142 nights; -3..-5%: -10.9). The -3% cutoff
  diluted it; not re-cut.
- TILT READ (the live night subset, day_ret <= -8% & IBS < 0.10, 2022-07..2026-09): all 612 nights +28.3 net (t 2.45); I >= 0.05: 88 nights,
  30 names, 176 name-days, **+99.6bp/night net, median +152.6, hit .69, t 3.33, ex-top-5 +67.3, ex-top-3-names +95.9 (t 3.2)**; 0 < I < 0.05:
  +46.0 (t 2.0); I = 0: +21.6 (t 1.8). Paired nights I >= 0.05 minus I = 0: +57.9 (median +62, hit .64, t 1.66, 76 nights). By year 2024 +164
  (6 nights), 2025 +73 (36), 2026 +112 (46). Still ~+90 at a 20bp round trip. Names: AAOI, CRWV, IONQ, COIN, CRCL, MU, OKLO, BMNR, SMR, POET.
  Reading: in the live night leg's own picks, the ones a single-stock LETF must sell at the close bounce 3-4x harder at the open. This is a
  named-counterparty mechanism inside the live leg, bettor-scale (~+60-80bp/night over controls), 88 nights on 30 names, 2024-26 only,
  paired t 1.66: EDGE UNPROVEN, not no-edge. Shape = night-leg weight tilt (size-up), which CLAUDE.md makes a user decision; the protocol
  step is a log-only forward shadow (NIGHT-LETF-TILT: live picks with I >= 0.05 vs the rest, gate ~40 shadow nights), REGISTRY entry in the
  same commit. Not built in this session.
- Not tested: holding past the open, 15:45 entry + open exit, index LETFs, the short side, cost shock on the tilt beyond 20bp, DSR across the
  program, overlap of tilt nights with GAP-NIGHT / live fills, whether the live leg's per-name cap binds on these names.
- Runner `research/sim/letf_rev.py`; out `data/research/program/letf_rev_out.txt`. Program N = 1065.

## Amendment - Study NIGHT-BOATS (N 1066): pre-register 2026-10-26 (market scan branch 3, unblocked: Alpaca feed=boats has Blue Ocean overnight bars from 2024-09-16), before any outcome; N 1065 -> 1066
- Question: do the night leg's picks (bought at the closing cross) trade at a better price in the 20:00-04:00 Blue Ocean overnight session than
  at the 09:30 opening cross where the leg exits, and is there enough overnight volume at $2-25k to use it? This is an EXIT read on a live leg,
  not a new entry. The exchange overnight sessions start 2026-12-06; Blue Ocean is the venue that exists today (Schwab does not route there;
  Alpaca does), so a PASS is a venue/broker question before it is a trade.
- Picks: the daily-bar proxy of the live rule (day_ret <= -8%, IBS < 0.10, prev close >= $5, $ADV20 >= $10M, domestic common; Sharadar), nights
  2024-09-16..2026-09-30; plus the actual live picks from the server decisions log where they exist (reported separately, not judged).
- Data: Alpaca StockBarsRequest(feed=DataFeed.BOATS, Minute) per pick-night, 20:00 ET (= 00:00 UTC) to 04:00 ET; next-day official open from
  Sharadar open (as GAP-NIGHT). Overnight VWAP, last print, high, $ volume, number of prints, first/last print time.
- Reads (all vs the opening cross, bp, no costs on the overnight side since a passive sale pays no spread; the cross exit is the live baseline):
  A. overnight VWAP minus open cross; B. last overnight print minus open; C. share of nights with any BOATS print and with >= $5k overnight
  $ volume (capacity at $2-25k); D. passive-offer form: resting offer at close x (1 + k), k = 1% primary (2%, 3% descriptive), filled if an
  overnight minute HIGH > level + $0.01, fill at level, else exit at the open cross; compare to exit-at-open on the same nights.
- PASS (D primary): per-night improvement over exit-at-open >= +15bp, day-clustered t >= 2, median > 0, halves (2024-09..2025-09 /
  2025-10..2026-09) > 0, ex-top-5 > 0, and C >= 50% of nights with a print. WEAK: +8..+15 with t >= 2. KILL otherwise, stated as "the
  night leg's picks do not print materially above the next open cross in the Blue Ocean session, or do so on too few nights to matter".
- Ceiling (disclosed): ~250 nights/yr x improvement x night-leg share (~50%) x 50% capture: +15bp -> ~+1pp; +50bp -> ~+3pp. BELOW the gate;
  run because it is a free exit improvement on a validated leg and the data just turned out to be on hand. Also a pre-read for Dec 6.
- Not tested after this: the entry side (buying overnight instead of at the close cross), names outside the night rule, the exchange
  overnight sessions (not launched), Schwab access to overnight venues (date-versioned: check), the IBS/GAP-NIGHT legs' exits.
- Runner `research/sim/night_boats.py` (fetch | run; cache `data/research/night_boats/`); out `data/research/program/night_boats_out.txt`.
  Program N = 1066.

## Amendment - NIGHT-LETF-TILT forward shadow (no N; log-only, 2026-10-26, built from LETF-REV N 1065): gate pre-registered before any forward row
- `swingtrader/daily/night_letf_tilt_shadow.py` (REGISTRY entry, start 2026-10-27). Population: every 15:40 night-rule candidate in
  `state/night-candidates.jsonl` (both accounts), scored on the official close cross -> open cross by repeat_shadow; I = ss_letf.panel()
  formula on Alpaca SIP daily bars with the static `data/letf_map.csv` (499 single-stock LETFs; rebuilt monthly on the Mac); tilt = I >= 0.05.
- Gate at 40 tilt nights: PASS = paired per-night tilt-minus-rest >= +30bp net, night-clustered t >= 2, median > 0 -> propose a night-leg
  weight tilt (user decision, night size-up class). FAIL = paired <= 0. Else HOLD. Backfill rows (candidates before 2026-10-27) are
  labelled look-alikes and excluded from the gate.

## RESULT - NIGHT-BOATS (N 1066, 2026-10-26, one look): KILL; Blue Ocean overnight prints are a tail stop, not an exit improvement
- 5,173 proxy picks on 478 nights 2024-09-16..2026-09-30 (Alpaca feed=boats minute bars; AAPL/SPY as venue-liveness control). D primary
  (resting offer at close x 1.01, else exit at the open cross): +22.6bp/night mean, t 1.08, median 0.0, hit .41, ex-top-5 -7.1; halves +29.5 /
  +15.8 (t 0.8 each). 3/7 gates. The mean is two catastrophe nights (FLNA 2024-11-25 opened -85%, CORT 2025-12-31 -45%) and 48% of fills were
  on names that opened above +1% anyway (capped upside). k = 2% / 3%: t 2.0 / 2.1 but medians 0 and outlier-carried (ex-top-5 +12..+17).
- A/B: on printed picks the overnight VWAP and last print sit +33 / +27bp (median) above the open cross, per-night t 1.6; the printed subset is
  selected on interest. Coverage: 61% of picks print (49% -> 69% H1 -> H2; 85% in 2026), 89% of nights have a printed pick; median overnight
  $ volume per printed pick $76k, front-loaded at 20:00 ET (68% first print in that hour). Capacity is not the constraint at $2-25k; price is.
- Live picks 2026-09-24..10-22 (228, not judged): 82% print, median $126k; the +1% offer lost money this month (-59bp/night, t -1.6) because
  the picks gapped up +500-950bp at the open on 10-16.
- Read: an overnight resting offer is a free pre-news stop on the night leg's tail, too rare to move the mean; the median pick gains nothing.
  Not tested: a dynamic / VWAP-based overnight exit (not registered), the entry side, the exchange overnight sessions from 2026-12-06,
  Schwab overnight access, IBS / GAP-NIGHT exits. Data caveat: BOATS minute coverage grows across the sample, so halves are not like-for-like.
- Runner `research/sim/night_boats.py` (fetch | run); cache `data/research/night_boats/` (15MB); out `data/research/program/night_boats_out.txt`.
  Program N = 1066.
