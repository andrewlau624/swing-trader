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
