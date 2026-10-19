# Branch C: cross-field / cross-asset mechanisms (2026-10-17)

Verdict: zero cards clear the gate. Two weak leads are written up as cards so the next agent does not redo them. No backtest run, no return numbers computed. Sources opened: crowdfundedwealth SmartStop page (WebFetch). Search snippets only (not opened): goodwinlaw, irei.com, akingump, lucasandersen.ai MLP/IRA pages.

## Repo check (grepped NEXT.md, MISTAKES.md, drafts/*)
- Intl-holiday ETF mismatches, Treasury-closed/equity-open: closed under ETF premium/discount family (BSPD, ETC); `mechanism_queue_2026-10-17.md` states it.
- USO/commodity ETP roll: `frontier_futures_2026-10-04.md` (ETF roll yield contaminates; Bessembinder spread widening noted), noise leg on USO dead (DS11).
- ETN acceleration/issuer redemption: `idea_scan_events_2026-10-08.md` row 5, CEILING-KILL (<0.3pp).
- Interval funds: `event_edge_candidates.md` C13 kill (not exchange traded).
- Non-traded BDC/REIT listings: only a one-line "fold / forward watch, ~0-2%/yr or unknown" in `alpha_frontier_2026-10-04.md:19`. Never tested. IPO lockup expiry: dead (Round 30 #7, -122bp, drift down).
- MLP K-1 conversion: only named in `prompt_hidden_edges.md`; never tested.
- Not in repo at all: cat bonds/ILS (only generic hits), muni de minimis, TIPS floor, on/off-the-run, utility rate cases, tanker charters, closing-line value.

## Card 1 (weak lead): non-traded REIT/BDC exchange listing
- Mechanism: holders of a non-traded vehicle with gated/suspended redemptions get their first exit at listing; sellers are forced liquidity-seekers, price may open below true value. Sponsor-managed staged-release or lockup expiries add supply on known dates.
- Evidence: SmartStop (SMA) listed NYSE 2025-04-02, IPO $30.00, first close $33.09, vs board NAV ~$58 split-adjusted (calculated as of 2024-06-30, i.e. stale); redemptions suspended repeatedly 2019-2024; price "about $32" in June 2026 per the article (market data, not a filing). Source: https://www.crowdfundedwealth.com/reviews/smartstop-self-storage-reit-review
- Falsifying fact: no convergence visible in the one case found. Price ~flat 14 months after a 43-48% "discount to NAV". The NAV was stale and a large part of the gap is likely a valuation, not forced flow. Article reports no lockup/buyback terms.
- Frequency: unknown, maybe 1-4 listings/yr (not counted). Payoff and lock: unknown. Downside: large (illiquid, new tickers, equity beta).
- Ceiling at $10k: 3 events x 10% edge x 20% of account x 50% = 0.3pp/yr even if the edge were 10%. Fails gate at every size; capacity cap is not the limit.
- Data: Sharadar/CRSP lack the pre-listing NAV; would need EDGAR hand sample (needs ~15 listings 2004-2025, NAV from 10-K/8-K). Free to collect but manual.
- Test spec if anyone insists: list all US non-traded REIT/BDC exchange listings 2004-2025 (EDGAR S-11/424B4 "estimated per share NAV" and listing), entry first close, exit +60/+120 trading days, benchmark = sector ETF (VNQ/BIZD-type), report median and ex-top-5, require n>=15. Untouched: all years; touched: none. Expected: killed by stale NAV. Not recommended ahead of other work.

## Card 2 (weak lead): MLP K-1 to 1099 conversion at effective date
- Mechanism: after conversion, UBTI (IRA owners above $1,000 file Form 990-T), K-1 and RIC 25%-of-assets limits vanish, so the buyer base widens (IRAs, mutual funds, FTSE Russell index eligibility). Source (snippet, not opened): https://www.akingump.com/en/insights/tax-insights/major-corporate-rate-cut-could-alter-mlp-landscape
- Problem: the conversion is announced months ahead; the widening is priced at announcement (the gap), the same pattern the repo found for index add/delete. Index inclusion is excluded by the brief. Existing taxable holders face a taxable exchange (sellers, not buyers, around the date).
- Frequency: ~1-3/yr and falling as simplification wave ends. Payoff unknown; no data seen (the searches found no price studies).
- Ceiling at $10k: 2 x 5% x 50% x 50% = 0.25pp/yr. Fails.
- Not testable without a hand list of conversions; do not pre-register.

## Dropped
- Cat bonds / ILS seasonality: only listed expression is a small ETF (launched 2023) at NAV; no discount mechanism, short history, pricing is model-marked. Ceiling-kill.
- Hurricane-landfall overreaction in Florida insurers: prediction not forced flow; names fail/recapitalise (mixed outcomes); no constrained counterparty.
- Sports-betting/prediction-market mechanisms (stale line, closing-line value, limits): transferable form is stale-quote vs faster venue = ETF/CEF NAV staleness, already closed; bet limits have no equity analogue.
- Commodity ETP structural events (USO 2020, position-limit-forced product changes): one-off, 2020 chain covered by futures-roll/FND kills; ETP premium/discount excluded.
- K-1 to 1099 for commodity pools: same UBTI logic as Card 2, no event stream.
- Grayscale-type trust-to-ETF conversions: ETF premium/discount, crypto, excluded.
- TIPS deflation floor, on/off-the-run, muni de minimis: individual bonds or Treasury, no listed expression at good spreads; TIP/SCHP hold the floor only per-bond.
- Country ETF during home-market holiday: premium/discount family closed (BSPD/ETC); intl ETF overnight rejected.
- Interval funds / BREIT gates: not exchange traded; the only listed spillover (public REIT sell-off in 2022) is beta, no forced counterparty to the listed shares.
- Utility rate cases, tanker charters: company-specific information, no forced participant.
