# Round 19 — max edge from the current bot: the outside-first candidate list (2026-10-01)

Brief: `research/drafts/prompt_max_edge.md`. Written **before any backtest**; this file is the record
of what was chosen and why. Program N at the start: **675** (Round 18, not the 669 the brief names).

How it was built: three searches (papers; strategy collections + forums + data pricing; GitHub repos +
Hugging Face models), then a dead-list check of every idea against NEXT.md's do-not-redo table
**and RESULTS.md**. NEXT's table is incomplete: night exit timing (add. 7), gap share / relative
volume / late selling (add. 23), news-day filters (add. 12) and IBS-at-the-MOC (add. 6) are dead
in RESULTS.md but not listed there. They are added to the table with this round.

Decay rule (brief): published edge x 2/3 at most; x 1/2 or less if old and easy, large-cap/crowded,
or gross-only; forum/blog ideas get no credit for their reported number. "%/yr" is the rough
increment to the book at $2.3k / $10k / $25k after our costs, before any test; most are ~0 by
the time decay, costs and overlap with the legs are applied, and the table says so.

Legend — leg: N night, I IBS, Z noise, C conviction, R Roth, new. Status: **SELECT** (tested this
round), dead (already tested here), drop (with reason).

## A. Research papers

| # | idea | source | why it should work | who pays | leg / fits $2-25k | dead-list check | reported → decayed edge; rough %/yr | data | status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Night picks: prefer drops that happened intraday, not in the gap | Lou-Polk-Skouras JFE 2019 ([pdf](http://www.econ.yale.edu/~shiller/behfin/2015-04-11/lou_polk_skouras.pdf)); Della Corte-Kosowski-Wang 2016 ([pdf](https://www.mcgill.ca/desautels/files/desautels/dkw_2016.pdf)) | intraday (institutional) moves revert overnight; gap moves are news | daytime liquidity demanders | N / yes | **add. 23 "gap share": not monotone, flips halves** | 1.68%/day gross L/S tiny caps → 0 | in hand | dead |
| 2 | Night picks: tilt by trailing overnight-return persistence (20d mean overnight return; tug-of-war count) | Aboody et al. JFQA 2018 ([pdf](https://anderson-review.ucla.edu/wp-content/uploads/2021/03/Aboody-et-al_overnight_returns_and_firmspecific_investor_sentiment_JFQA2018.pdf)); Akbas-Boehmer-Jiang-Koch JFE 2022 ([link](https://ink.library.smu.edu.sg/lkcsb_research/7712/)); CXO "overnight momentum" ([link](https://www.cxoadvisory.com/calendar-effects/overnight-momentum-informed-overnight-trading/)) | names with persistent retail demand at the open get bid again at the next open — the night leg sells into that open | retail buyers at the open (attention, sentiment) | N / yes (a weight, no new names) | add. 7 killed overnight momentum as a **standalone** strategy (+8.7bp/night < cost); add. 23's nine tilt features did not include it. **Different: a tilt inside picks that already pay the cost** | CXO 10.4-15.7%/yr net alpha (monthly, 1995-2014) → x 1/2 (old, US-only per Akbas) → tilt of k 0.25: ~+0.3-1pp/yr ($7-23 / $30-100 / $75-250) | panel open/close (in hand) | **SELECT → Study AU** |
| 3 | Night picks: up-weight "top movers" (retail attention lists) | Barber-Huang-Odean-Schwarz JF 2022 ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3715077)) | app lists route retail buying to the next open | Robinhood-style buyers | N / yes | the top-mover list is ranked by % move = our depth (add. 7: depth ≤ −12% monotone but halves trades) | opening return ~11% on buy-herding (not losers) → 0 | needs market cap | drop (≈ depth) |
| 4 | IBS leg: decide at 15:50, buy in the close auction | Pagonidis NAAIM 2014 ([pdf](https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf)); Bogousslavsky-Muravyev JFM 2023 ([SSRN](https://www.ssrn.com/abstract=3485840)) | IBS reversion begins overnight | close-auction flow | I, R / yes | **add. 6: 15:50 signal + MOC degrades QQQ 13.9 → 8.8%**; V6 (index close→open) is shadow | +0.35%/day gross (pre-2013) → 0 | in hand | dead |
| 5 | Night picks: penalise a late bounce (15:30-15:50) | Baltussen-Da-Soebhag 2024 ([pdf](https://academicweb.nd.edu/~zda/EOD.pdf)) | retail dip-buying/short covering in the last 30 min is temporary | EOD dip buyers | N / yes | **add. 23 "late selling": not monotone**; add. 7: entering at 15:50 no gain | 6.9bp/day EW gross → 0 | 15:30-50 bars partly | dead |
| 6 | SPY/QQQ overnight sleeve after sell-offs | Boyarchenko-Larsen-Whelan RFS 2023 ([NY Fed](https://www.newyorkfed.org/research/staff_reports/sr917)); same authors 2026 "Disappearing overnight drift" ([link](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/)) | dealers paid for absorbing the close imbalance | close sellers | new / yes | V6 (oversold index close→open) already shadow; authors say ~0 since 2021 | 3.6%/yr → ~0 (authors' own decay) | in hand | drop |
| 7 | Night picks: tilt toward names with single-stock LETFs (rebalance pressure at the close) | Barbon-Beckmeyer-Buraschi-Moerke 2022 ([pdf](https://wp.lancs.ac.uk/fofi2022/files/2022/08/FoFI-2022-027-Mathis-Moerke.pdf)); Ivanov-Lenkey JFM 2018 ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2504012)) | known-size MOC sells revert at the open | LETF holders | N / yes | add. 34 / Study W (LETF picks themselves). Different (underlyings) but the effect declined over time and Ivanov-Lenkey call it insignificant | → ~0 | LETF AUM history (no) | drop |
| 8 | IBS SPY/QQQ: size up on VIX-ETP rebalancing days | Bangsgaard-Kokholm JBF 2025 ([RePEc](https://ideas.repec.org/a/eee/jbfina/v180y2025ics0378426625001761.html)) | VIX ETP hedging pushes SPX at the close, then reverses | VIX ETP holders | I / yes | regime/VIX gates dead; this is a flow, not a level | OOS claimed, size not found → unknown | VIX futures + ETP AUM (no) | drop (data) |
| 9 | Night leg: sell at 09:35 / 10:00 / hold to close | Berkman et al. JFQA 2012 ([link](https://www.semanticscholar.org/paper/Paying-Attention:-Overnight-Returns-and-the-Hidden-Berkman-Koch/ff64bccbd678828e4a83fb0304e8e15148ef67a6)); Dyl et al. JBR 2019 | open prices of attention stocks are too high | retail at the open | N | **add. 7: open auction best (+20.1bp vs 9:35 +1.9, 10:00 −9.3)** | — | in hand | dead (the papers agree with it) |
| 10 | IBS leg: hold until a state exit (IBS > 0.5, or close > prior high) instead of "hold while IBS < 0.2" | Pagonidis 2014; IBS-country-ETF arXiv 2306.12434 ([link](https://arxiv.org/abs/2306.12434)); idousse repo (clean, costed: exit close > yesterday's high) | the reversion may take more than one session to complete | the same short-horizon liquidity demanders the IBS leg already serves | I, R / yes (same names) | dead exits are price targets/trailing on the swing book (add. 5); no IBS-leg exit rule was ever tested | idousse QQQ 13.0% → 10.3% at 10bp/side (all-day Sharpe 0.74-0.87) → x 1/2; prior ±1pp/yr ($23 / $100 / $250) | in hand | **SELECT → Study AV** |
| 11 | OU optimal stopping with costs + stop-loss | Leung-Li IJTAF 2015 ([arXiv](https://arxiv.org/abs/1411.5062)) | optimal exit band for an OU spread | — | N, I | Bertram entries dead; stops dead (AH, add. 5) | theory, no backtest | — | drop |
| 12 | Shrunk Kelly per leg (more shrink for few-trade legs) | Baker-McHale Decis. Anal. 2013 ([link](https://pubsonline.informs.org/doi/10.1287/deca.2013.0271)) | plug-in Kelly over-bets under estimation error | — (sizing, not an edge) | all | Roth below Kelly peak (add. 31); noise x1.5 shadow (add. 40); vol-target dead (add. 32); AS dead. **Adds only a reason to keep conviction at 0.5 and noise at x1.0 — no new number** | none | in hand | drop (report: confirms current weights) |
| 13 | Risk-constrained Kelly across legs (convex program, P(DD) cap) | Busseti-Ryu-Boyd 2016 ([arXiv](https://arxiv.org/pdf/1603.06183)) | maximise growth subject to a drawdown-probability bound | — | all | the program's frontier (add. 32, `taxable_frontier.py`) already searches weights under P(DD>30/50%) bars | sim only | in hand | drop (already done in another form) |
| 14 | Statistical jump model regime switch for the IBS leg | Shu-Yu-Mulvey 2024 ([arXiv](https://arxiv.org/abs/2402.05272)); Nystrup et al. QF 2018 | persistence penalty reduces whipsaw vs CUSUM | — | I | CUSUM/rolling-t de-risk dead (add. 37); **AT: downtrend dips revert most** — a bear off-switch removes the best trades | times beta, not reversal | in hand | drop |
| 15 | BOCPD on/off | Adams-MacKay 2007 ([arXiv](https://arxiv.org/abs/0710.3742)) | online change-point posterior | — | all | add. 37 | no OOS strategy evidence | — | drop |
| 16 | Night picks: drop news days (8-K/earnings) | Savor JFE 2012 ([RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:106:y:2012:i:3:p:635-659)); Da-Liu-Schaumburg MS 2014 ([pdf](https://academicweb.nd.edu/~zda/Reversal.pdf)) | informed drops drift, uninformed revert | — | N | **add. 12: news vs none +2bp excess, t 0.8**; Study T offerings shadow | 1.34%/mo gross → 0 | EDGAR | dead |
| 17 | Night picks: abnormal turnover; lower the $5 floor | Avramov-Chordia-Goyal JF 2006 ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=555968)); Medhat-Schmeling RFS 2022 ([pdf](https://openaccess.city.ac.uk/id/eprint/31278/1/MS_short_term_mom_v27.pdf)) | non-information volume reverts | — | N | **add. 23 rvol dead; add. 30 $3/$2/$1 floors dead** | ACG: costs exceed profits | in hand | dead |

## B. Strategy collections

| # | idea | source | why | who pays | leg | dead-list check | edge → decayed; %/yr | data | status |
|---|---|---|---|---|---|---|---|---|---|
| 18 | **Audit: do the backtest's night-leg returns use the official auction prints?** Vendor OHLC "open" is the first trade, not the opening cross | Quantpedia "Dangers of relying on OHLC prices" 2025 ([link](https://quantpedia.com/dangers-of-relying-on-ohlc-prices-the-case-of-overnight-drift-in-gdx-etf/)); perthoptions repo note; codecat repo (first-bar open) | in thin names the first print can sit far from the cross; GDX overnight 30%/yr on OHLC vs 8.6% at 09:31 | nobody: a data artifact that could inflate every night-leg number | N, R | add. 6 checked the **close** (= auction 90% exact); live costs are measured vs auction prints (add. 29), but the **backtest's open was never audited** | not an edge; it can only move the leg's level down (or confirm it) | Alpaca `/v2/stocks/auctions` (free, works with our keys) | **SELECT → Study AW (report)** |
| 19 | IBS ETF creation/redemption flow surprise as a filter | Xu-Yin-Zhao via Quantpedia ([link](https://quantpedia.com/how-to-use-etf-flows-to-predict-subsequent-daily-etf-performance/)) | unexpected flow = temporary pressure | flow-driven ETF traders | I | not tested | 14%/yr L/S net, 2012-16 only → x 1/3, and our IBS uses 3 names | daily shares outstanding + NAV (no) | drop (data; future) |
| 20 | Quantpedia "short-term reversals and intraday transactions" (Miwa) | [link](https://quantpedia.com/short-term-return-reversals-and-intraday-transactions/) | intraday part reverses, overnight part does not | liquidity demanders | N | = #1, add. 23 | — | — | dead |
| 21 | Alpha Architect: end-of-day reversal | [link](https://alphaarchitect.com/end-of-trading/) | = #5 | | N | add. 23 | | | dead |
| 22 | Alpha Architect: closing-auction deviation reverts overnight (feature = close print − 15:59:59 mid; ex-ante = 15:50 imbalance) | Bogousslavsky-Muravyev via AA; [SSRN](https://www.ssrn.com/abstract=3485840) | passive flow pushes the cross off the mid; ~85% reverts by the morning | index/passive close flow | N | AC (Round 13) untested for data | 8bp mean abs deviation; tradable only ex-ante → unknown | imbalance (see pricing) | drop this round (data; price below) |
| 23 | Alpha Architect: plain ETF buy-close/sell-open is dead after costs | [link](https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/) | negative control | — | I | consistent with add. 16 (IBS idle in index overnight dead) | — | — | drop (confirms) |
| 24 | Allocate Smartly: tranche the IBS momentum top-3 reselection weekly | [link](https://allocatesmartly.com/taming-excessive-timing-luck-in-taa-by-tranching-strategies/) | removes timing luck of the monthly reselect date | — | I | not tested | 14.2 vs 13.9%/yr in TAA → ~0 mean, lower variance | in hand | drop: a variance reducer cannot clear an increment-t ≥ 2 bar; adoptable on robustness grounds without a test if wanted |
| 25 | Allocate Smartly: "the close is not the close" (last trade vs official close) | [link](https://allocatesmartly.com/when-the-close-is-not-really-the-close-a-geeky-discussion/) | 0.006% mean gap, 0.09% of signals flip | — | I | add. 6 (90% exact) | ~0 | — | drop (immaterial for ETFs; #18 checks thin names) |
| 26 | CXO: hold losers that gap down further past the open | Della Corte et al. via CXO ([link](https://www.cxoadvisory.com/technical-trading/overnightintraday-return-reversal-trading/)); QuantConnect "Mind the Gap" ([link](https://www.quantconnect.com/forum/discussion/19075/mind-the-gap-an-intraday-reversal-strategy-using-gap-downs-and-atr/)) | overnight moves reverse intraday | opening liquidity demanders | N | **Study A (gap-conditioned exit): DEAD, all 5 variants** | 1.68%/day gross, 1-min delay kills it | in hand | dead |
| 27 | CXO: overnight-momentum tie-breaker | [link](https://www.cxoadvisory.com/calendar-effects/overnight-momentum-informed-overnight-trading/) | = #2 | | N | | | | merged into AU |

## C. GitHub repos (lookahead / cost audit; code read, not run)

| # | repo | idea | lookahead | costs | verdict | use |
|---|---|---|---|---|---|---|
| 28 | [toniker10/SPY-IBS-Mean-Reversion-Strategy](https://github.com/toniker10/SPY-IBS-Mean-Reversion-Strategy) | SPY IBS < .2 / > .8 | **yes**: L51-52 `position.shift(1) * close.pct_change()` earns close t → close t+1 with the signal from close t, i.e. buys the signal bar's close; README says "next open" | none (L53) | hypothesis only | confirms only that the edge starts overnight (our V6) |
| 29 | [CazSyd/IBS-Strategy](https://github.com/CazSyd/IBS-Strategy) | IBS on QQQ/SPY/3x ETFs | open mode clean (L266, L274-276); close mode same-bar by design; whole shares on adjusted prices (L274); survivor LETF list | none (docstring L13) | clean (open mode), no costs | bottom-IBS close→open +7..16bp across ETFs: same mechanism as IBS/V6, nothing new |
| 30 | [idousse/mean-reversion-strategy](https://github.com/idousse/mean-reversion-strategy) | QQQ: close < 10d high − 2.5 x range and IBS < .3; **exit close > yesterday's high** | none found (backtesting.py, `trade_on_close=False`) | 0-10bp/side sweep | clean, costed; headline Sharpe counts invested days only | **source for AV2** |
| 31 | [codecat-ops/zarattini-2024-momentum-spy](https://github.com/codecat-ops/zarattini-2024-momentum-spy) | noise area (our Z leg) | causal sigma (L85 `.shift(1)`); fills at the decision bar's close (zero latency); first-bar open, not the auction | commission only, slippage 0 in the headline | clean, optimistic fills | **SPY Sharpe ~0 since 2025; 27-variant grid picks the paper config; walk-forward hurts** — confirms add. 37 and that noise exit tinkering is dead; watch QQQ/SMH by year |
| 32 | [giovannibrusco/zarattini-2023-orb-qqq](https://github.com/giovannibrusco/zarattini-2023-orb-qqq) | QQQ 5-min ORB | clean | 0 in headline; 2¢ slippage → Sharpe 1.06 → 0.23; break-even ~2.2¢ | clean, no costs in headline | ORB dead (add. 8/24) — agrees |
| 33 | [perthoptions/overnight-research](https://github.com/perthoptions/overnight-research) | S&P 500 intraday-loser → overnight decile L/S, 15:55 entry | **small leak** (`ib_loader_v2.py` L223 features include the entry bar); Bloomberg arm used the close as entry; current-constituent universe (survivorship) | flat 12bp RT | hypothesis only | long side (D10) carries it; **all variants collapsed in the last ~126 sessions (≈ Feb-Sep 2026)** — a decay watch for the night leg (large caps; ours are small/volatile) |
| 34 | [sarthakdass/statarb](https://github.com/sarthakdass/statarb) | cointegration pairs, OU half-life | clean (lag 1) | 1bp + 2bp + borrow | clean, no real-data result | needs shorting (no Roth); ETF pairs dead (add. 27) — drop |

## D. Hugging Face forecasting models

| # | idea | source | leakage / clean holdout | CPU cost per decision | what it sees that hand signals don't | status |
|---|---|---|---|---|---|---|
| 35 | Chronos-Bolt / Chronos-2 zero-shot next-day forecast as an IBS or night-pick filter | [chronos-forecasting](https://github.com/amazon-science/chronos-forecasting), [amazon/chronos-2](https://huggingface.co/amazon/chronos-2) | M4 (≤2018, incl. finance) in training; strict holdout = after release: Bolt Dec 2024+, Chronos-2 Nov 2025+ (~11-21 months) | ~1-2 s for 20 ETFs; < 1 min batched for 3,000 names | nothing specific: univariate shape of the price path, which IBS/depth already summarise | drop: **power**. In ~11-21 months the IBS leg has ~200-400 trades; detecting a +5bp/trade filter gain at sd ~1.2%/trade needs ~2,300. Rahimikia et al. 2025 ([arXiv](https://arxiv.org/html/2511.18578v1)): zero-shot Chronos ~51% directional, every model net-negative at 11-21bp costs |
| 36 | TimesFM 2.0/2.5, Moirai 2.0, TiRex, Toto, Sundial zero-shot | [timesfm](https://github.com/google-research/timesfm), [moirai-2.0](https://huggingface.co/Salesforce/moirai-2.0-R-small) | holdouts: TimesFM 2.5 Oct 2025+, Moirai 2.0 Sep 2025+, Toto Jun 2025+ | TimesFM 2.5 2-5 s/series unbatched (repo) | same | drop (same power argument; TimesFM-500M zero-shot −1.5%/yr gross in Rahimikia) |
| 37 | Kronos (OHLCV-pretrained on 45 exchanges) / TimesFM-fin | [Kronos](https://github.com/shiyu-coder/Kronos); [arXiv 2412.09880](https://arxiv.org/abs/2412.09880) | **trained on stock bars to Jun 2024** → 2016-Jun 2024 contaminated; clean Jul 2024+ | small | the only one trained on equity OHLCV | drop: TimesFM-fin reports no costs and one overlapping year; Kronos claims inflated per an independent review; same power limit. Revisit as a pre-registered forward log only |
| 38 | TimeGPT | [paper](https://arxiv.org/pdf/2310.03589) | training data undisclosed, finance included → no certifiable clean window | API, paid | — | drop |

## E. Forums (ideas only)

reddit.com was not reachable from the search tools (no r/algotrading threads read); practitioner
GitHub replications (#31-33) stand in. Nothing relevant on Wilmott.

| # | idea | source | who pays | dead-list / note | status |
|---|---|---|---|---|---|
| 39 | Night buys as LOC with a loose cap (vs MOC) to dodge a freak close | Elite Trader ([thread](https://www.elitetrader.com/et/threads/should-i-use-moc-or-loc.348163/page-3)) | — | AM (limits) dead; a loose cap fills > 99.9% = MOC; a tail-risk control, not an edge | drop |
| 40 | Rank night picks by published sell imbalance / ADV at 15:50 | Elite Trader ([thread](https://www.elitetrader.com/et/threads/early-moc-imbalance-data.378955/)) | close sellers | = AC (Round 13), untested for data — priced below | drop this round (data) |
| 41 | MOC cutoff ops: NYSE 15:50 (after that only imbalance-offsetting orders), Nasdaq 15:55 | Elite Trader + NYSE filing ([SEC](https://www.sec.gov/files/rules/sro/nyse/2024/34-100327.pdf)) | — | ops note: the 15:40 scan is inside both cutoffs; log any CLS rejections | note only |
| 42 | SPY MOC/MOO overnight is fee-dead | QuantConnect ([research](https://www.quantconnect.com/research/15296/overnight-anomaly/)) | — | agrees with add. 16 / #23 | drop |
| 43 | Shorting overnight winners loses | QuantConnect ([league](https://www.quantconnect.com/league/17425/2024-q3/overnight-mean-reversion/)) | — | agrees with Study S | drop |
| 44 | Stocks-in-play 5-min ORB (top-20 by opening rvol) | Zarattini-Barbon-Aziz 2024 ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284)) via forum write-ups | slow reactors to news | ORB dead (add. 8/24), single-stock noise dead (add. 41); needs all-stock minute bars and shorting | drop |

## Ranking (brief's rule: decayed %/yr × P(pass) × independence × data × effort)

| rank | candidate | decayed %/yr ($2.3k / $10k / $25k) | P(pass) | independence | data | effort | pick |
|---|---|---|---|---|---|---|---|
| 1 | #18 auction-print audit (report) | not an edge; protects every night-leg number (the night leg is half of the Roth cash book) | n/a | — | free API | low | **AW** |
| 2 | #2 overnight-persistence tilt on night picks | +0.3-1pp: $7-23 / $30-100 / $75-250 | low-med (~15%) | inside the night leg (re-weights only) | in hand | low | **AU** |
| 3 | #10 IBS state exit | ±1pp: ≤ $23 / $100 / $250 | low (~10%; Pagonidis/CazSyd say the reversion decays after the first night) | inside the IBS leg; runs in the Roth | in hand | low | **AV** |
| 4 | #22/#40 closing imbalance | unknown; the only untested mechanism with a named payer | — | new information | candidate-only Databento pull may fit the $125 free credit; live ≥ ~$33k/yr Databento or $49/mo Massive (NYSE only) | high | not this round |
| 5 | #24 tranching | ~0 mean | ~0 (cannot clear t) | — | in hand | low | no |
| — | everything else | 0 after the dead-list check or no data | | | | | no |

**Honest prior:** the outside literature mostly re-discovers mechanisms this program already
harvests (overnight reversal, IBS, noise momentum) or already killed (exit timing, gap share, news,
late bounce, ORB). Rows 2-3 are small refinements with small expected money at $2-25k; row 1 is
the most useful outcome because it can only lower or confirm the night leg's level.

## Data pricing (closing / opening auction imbalance; brief's ask)

| need | source | history 2018-26 | live / yr | % of $2.3k / $10k / $25k |
|---|---|---|---|---|
| NYSE/Arca imbalance | Databento XNYS/ARCX.PILLAR `imbalance` | from 2018-05; usage-based $/GB unpublished. Candidate-only pull (≈30 names x 15:50-16:00 x ~2,100 days, est. a few GB) may fit the $125 signup credit — confirm with `metadata.get_cost` | Plus $1,750/mo or Unlimited $4,500/mo + NYSE licence ≥ $1,000/mo → **≥ ~$33k/yr** | 1,400% / 330% / 130% |
| NYSE imbalance (retail) | Massive (Polygon) add-on | none | **$49/mo = $588/yr**, NYSE-listed only | 26% / 5.9% / 2.4% |
| Nasdaq NOII | Databento XNAS.ITCH | from 2018-05 (confirm) | Standard $199/mo + Nasdaq licence (~$84/mo pro) ≈ $3.4k/yr | 150% / 34% / 14% |
| NBBO 15:50-16:00 (ex-post deviation study) | Alpaca historical SIP quotes | **free** (> 15 min old, 2016+) | $99/mo real-time | — |
| Official auction prints | Alpaca `/v2/stocks/auctions` | **free**, works with the repo's keys | — | — |

A cheap pilot (not this round): pull candidate-only imbalance history on the free credit, test AC
ex-ante as one pre-registered tilt; buy a live feed only if it clears the bar and the account is ≥ ~$25k
(the Massive add-on is 2.4% of $25k a year; Nasdaq names stay uncovered).
