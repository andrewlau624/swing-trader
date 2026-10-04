# Study CPC: census of all per-holder-capped contract payoffs 2016-26, as one opportunity (N 817 -> 818)

Pre-registration: `round1_prose.md`, commit 40e3910. Runner `research/sim/cpc.py`; full output `data/research/program/cpc_out.txt`;
$10k ledger `cpc_ledger_10k.csv`. One run, nothing fitted. Selection-bias caveat: B1, B2, odd-lot tenders and DL1 were chosen because they
paid on this same history, so this is a ceiling check on survivors, not a fresh test.

## Verdict (judged line: taxable $10k, B1 "rounded", after-tax excess over T-bills)
**PASS on the registered gates: mean +13.3pp/yr ($1,330/yr), 10 of 11 calendar years positive (91%), ex-best-5 +8.5pp.**
But read the composition before believing it: 79% of the pre-tax dollars are DRIP (UMH/MNR, $820/yr) and B2 ($934/yr). Leave-one-out
at $10k: ex-DRIP +8.4pp (still >= 8), ex-B2 +7.4, ex-B1 +12.4, ex-tender +12.0. UMH-only DRIP (MNR ended 2022): +11.4pp. 2021-26 only
+9.2pp, 2023-26 +9.6pp. At $2.3k +32.4pp (PASS); at $25k +7.6pp (NEAR, ex-best-5 +3). The label is PASS at $10k only because
DRIP and B2 are both in; each is a single issuer or ~1.4 deals/yr.

| after-tax excess, taxable | $2.3k | $10k | $25k |
|---|---|---|---|
| mean pp/yr (primary) | +32.4 ($744) | **+13.3 ($1,330)** | +7.6 ($1,911) |
| 2016-20 / 2021-26 | +40.9 / +24.9 | +18.1 / +9.2 | +11.0 / +4.7 |
| years > 0 / median year | 100% / +31.5 | 91% / +12.4 | 91% / +5.0 |
| ex-best-5 | +26.9 | +8.5 | +3.1 |
| B1 cash in lieu instead | +28.7 | +12.4 | +7.3 |
| excess over SPY instead of T-bills | +30.2 | +13.3 | (+7.6) |
| label | PASS | PASS | NEAR |
| max simultaneous capital | $2,300 (100%) | $10,000 deployed at peak, 12.7% of capital-time | $25,000 peak |

By year at $10k (pp): 2016 +27.4, 2017 +12.2, 2018 +12.4, 2019 +15.7, 2020 +22.6, 2021 +17.7, 2022 -1.0, 2023 +6.0, 2024 +15.8,
2025 +8.8, 2026 YTD +5.3. The decline from 2016-20 to 2021-26 is B2 (rich 2016-20 deals), DRIP losing MNR in 2022 and UMH's lower cap.

## By family (pre-tax $/yr, full 10.75 years, $10k account; T-bill carry is under $20/yr in total)
| family | events/yr | $/yr | per event | capital per event | notes |
|---|---|---|---|---|---|
| B1 round-up (1 share/account) | 31.8 (2016-22: ~5; 2023-26: ~75) | $129 (2023-26: $312; 2016-20: $28) | $4.07 | $0.26 median | cash in lieu: -$0.9/yr; break-even P(round) 0.7%; 1 day had > 3 deals |
| B2 split-off, odd-lot priority | 1.3 | $934 ($135 at $2.3k) | $717 | $8.0k median, <= 99 shares | MMM -$815, MCK -$461 at $10k; 5 of top-5 events are B2/tender |
| Odd-lot cash tenders, floor >= +1% | 1.3 | $190 | $146 | $0.9k median | all 14 positive on their own table; no-floor variant (65 deals) takes the total to -0.6pp |
| DRIP/DSPP (UMH, MNR) | 18.7 (12 since 2023) | $820 | $44 | $1,000 | worst month -$205 (2020-03); UMH-only ~$540/yr |
| Total | ~53 | **$2,073** | | | |
| Excluded: thrift conversions | 1.4-1.7 | $390-623 if eligible for all (~$270-360 median-2/yr) | $280-372 | $2,000 for 29 days | requires a depositor account 1-2 years earlier; hit 80-83% |
| Excluded: CEF tenders, pro-rata | 1.3 | $11-118 (capital-proportional) | | | 54 of 55 have no odd-lot priority; p = proration or 25%; after-tax -0.2pp. Not per-holder capped |
| Unscored: rights offerings | | $0 assumed | | | capital-proportional; no table; earlier rounds found payoff ~0 |

Roth (B1 only): $130/yr full period, $312/yr 2023-26 = +5.6%/yr on $2.3k, +3.7% on $8.5k (untaxed). If the 99-share families
(B2 + tenders + B1) sit in an $8.5k Roth instead: $1,209/yr = +14.2%/yr untaxed (report-only; DRIP cannot move, plan accounts are personal).

## Costs, fills, taxes (as registered)
Half-spread h(P) both sides on bars (1.0% for $1-5, 4% cap sub-$1, 0.15% for $20-100), $0 commission, whole shares, odd lots accepted in
full (tender/exchange), final proration used only for the CEF line. B1 sold at E+5 close (E close: +$138 vs $130/yr, no difference).
Tax 35% on each year's net, no carryover. Idle capital earns T-bills in the baseline, so "excess" excludes it; vs SPY the means are
within 0.3pp (hold times are short).

## Correlation with the live book
Monthly CPC P&L vs T0L monthly returns (127 months, 'ho' 2016-02..2020-12 plus tier_hi 2021-02..2026-09 from
`program_books_res_rawpool.pkl`): **-0.06 at $2.3k, -0.08 at $10k** (ex-B1 identical). Effectively uncorrelated; the capital-time (12.7% of
capital at $10k) is the only thing it competes with.

## Operational burden (manual steps per year; what is automated today)
- B1: automated (ROUNDUP_AUTO, 1 share per account, sell after the ex-date). Manual: 0, plus an email check. Depends on Schwab rounding.
- B2: alert exists (`splitoff_watch`); manual buy confirm (`make splitoff-buy`), Schwab tender form with odd-lot box, sell/hold: ~4 steps x 1.3 = ~5/yr.
- Odd-lot tenders: alert exists (`tender_watch`/`tender_buy`); manual tender election and certification: ~4 x 1.3 = ~5/yr.
- DRIP (UMH): NOT automated, no alert exists (spec in study_dl1_drip_ocp.md). 3 steps a month (ACH to Equiniti by the 12th, DRS transfer, sale) = ~36/yr, ~15 min each time. This is where most of the burden is.
- Thrift: not automatable (account must pre-exist, state residency rules).
Total manual: ~46/yr, 36 of them DRIP. B1 + B2 + tenders alone: ~10/yr.

## Capacity per account / owner
B1: 1 share per account (not per owner), so it scales with accounts. B2 and tenders: <= 99 shares per beneficial owner across ALL accounts
(about $8-10k at $100, up to $27k for CMI-type names, so the cap binds only on the $25k account and the Roth-venue case). DRIP: $1,000/month
per plan participant ($12k/yr). Thrift: ~$2,000 per eligible depositor.

## Accounts needed (honest arithmetic, not a recommendation)
One owner's non-B1 stack is $1,945/yr pre-tax over 2016-26 ($1,201/yr over 2023-26), $1,264 ($781) after tax. The only family that grows per
account is B1: $130/account/yr (2016-26) or $312 (2023-26). Reaching after-tax $1k/yr: one owner is enough on the full-period mean (2
taxable B1 accounts on the 2023-26 mean). $5k/yr: 45 taxable (29 Roth-type) B1 accounts on the full mean, 21 (14) on 2023-26. $10k/yr: 104 (68)
or 46 (30). The B1 number is tiny per account and needs the Schwab round-up to pass to every account, so the total does NOT scale in
practice: a single owner tops out near $1-2k/yr from this stack.
What is and is not legitimate:
- Odd-lot priority (B2, tenders): conditioned on beneficial ownership of < 100 shares in total. The offers' own certification counts all
  accounts of the same owner (taxable, IRA, joint). A second account does not buy a second odd lot, and certifying otherwise is a false
  certification. Separate people's own money in their own accounts is a different owner; one person opening accounts to multiply the limit is not.
- B1 rounding is a broker allocation per account. The repo's G1 note and the VIVK check (~10-07) are the only evidence; issuers or brokers
  may aggregate or cap rounding per beneficial owner, and brokers may restrict sub-dollar buys or close accounts for abusive patterns.
  Nothing here recommends proliferating accounts; wash-sale and 35% short-term tax apply to each taxable account, Roth is untaxed but
  contribution-limited ($7.5k/yr, the repo's number).
- DRIP: personal plan registration, $1,000/month per participant; other family members' own accounts are separate participants but
  that is their money and their tax.

## Caveats and what remains
- DRIP is one issuer family whose discount could be cut (UMH reserves the right; 2021 cap cut $5,000 -> $1,000). Whether UMH still grants
  the 5% in 2026 was not re-verified in this study (no new EDGAR/web read).
- B2: 14 offers, 12 of 14 positive, the pass leans on ~5 big ones. The no-floor tender variant is negative, so the tender line depends on the
  floor filter (decidable ex ante; but chosen on this history).
- B1 earlier years (2016-22) show far fewer qualified deals than 2023-26; that may be filing-text coverage, not fewer rounding splits.
- 2026 is YTD to 09-30; mean uses 10.75 years. T-bill yields are the pre-registered approximations.
- Rights offerings are an unscored gap; the CEF line used a 25% proration default when the table had none.
- B1 headline hinges on VIVK; the cash-in-lieu scenario removes only ~$130/yr here because DRIP and B2 carry the total.
