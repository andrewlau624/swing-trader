# Discovery loop, second session (llm-trader-c5), started 2026-10-02 ~10:45 PT

Same brief (`prompt_discovery_loop.md`). Session llm-trader-mid-01 wrote `discovery_ideas.md` (I1-I40) and claimed
I1/I2/I15, I14, I26/I28/I30, I29, I37, I4/I39. **This session takes only unclaimed rows**: peer rows it ranked "low"
or left unclaimed (I3, I6, I7, I8, I10, I11, I12, I19) plus new rows C1-C14 below. Written **before any outcome on
them** (only counts were looked at). N at start: 760. Log of every look: `discovery_log_c5.md`.

Count probes run (EDGAR FTS, counts only, 2018 / 2022 / 2025): S-3D/424B3 "optional cash purchase" + "discount"
17 / 11 / 8; "waiver discount" 6 / 2 / 0; DEF 14A/8-K "plan of dissolution" + "liquidating distribution" 32 / 24 / 38;
8-K "liquidating distribution" + "per share" 126 / 150 / 120; SC TO-T "subsequent offering period" 151 / 119 / 125;
SC TO-T "short-form merger" 11 / 8 / 7; 424B3 cash/stock election + proration 36 / 24 / 27; 497/N-2 CEF rights
"discount to net asset value" 278 / 64 / 84; 424B "over-subscription privilege" 245 / 443 / 686; SC TO-T/DEFM14A
"contingent value right" 50 / 95 / 228; DEF 14C "odd-lot" 7 / 9 / 14. Form census 2020-26 (10-3,000/yr): 264 forms;
DEFM14C ~14/yr, PREM14C ~13/yr, N-8F ~100/yr, N-23C-2 ~110/yr, N-23C3A ~390/yr, T-3 ~85/yr, CB ~80/yr.

| # | idea | method | contract / forced-trader sentence | source | est deals/yr | small-size edge | novelty (searched) | kill |
|---|---|---|---|---|---|---|---|---|
| I7 | **DRIP optional cash purchases (OCP) at a fixed 1-5% discount** | A | The plan prospectus fixes OCP price = average of the pricing period's prices x (1 - d); any registered holder may buy up to a cap (often $5-10k/month) and sell when shares post; the issuer pays d to raise equity cheaply. | S-3D / S-3 / 424B3 plan prospectus | ~5-15 issuers, monthly | caps bind only large buyers (Scholes-Wolfson 1989: arbs exploited OCP discounts until caps); $2-25k sits under the cap | 3 (Scholes & Wolfson 1989; peer #14 parked as "not testable" — but the fill is a formula, so it is simulable) | live |
| C1 | **Warrant-for-share exchange offers** (de-SPAC SC TO-I: r shares per warrant, plus a consent that forces the rest at ~0.9r) | A | The issuer offers r shares per warrant to clean its cap table; if a warrant trades below r x share, a holder buys warrants, tenders, receives r shares (2-4 weeks). | SC TO-I "warrants" + "exchange offer" | ~20-60 (2021-24) | thin warrants; no cap but small names | 4 (not on any list; grep "warrant" in drafts: only SPAC trust) | live |
| C2 | **Warrant redemptions with a cashless make-whole table** (stock > $10/$18 trigger; notice fixes shares per warrant) | A | Once the notice fixes the cashless ratio, a warrant is worth ratio x share; holders who ignore notices sell warrants cheaply or get $0.01-0.10. | 8-K "notice of redemption" + "cashless" | ~20-50 (2021) | thin | 4 | live (folded into C1's study) |
| C3 | **Written-consent cash mergers (DEFM14C)**: the vote is already won; closing >= 20 days after mailing | A, C | The majority signed; the information statement mails; the deal closes at a fixed cash price; a small account buys below it. | DEFM14C "per share in cash" | ~10-15 | thin names; no vote risk (unlike B3) | 4 (B3 tested SC TO-T only; DEFM14C unused, grep) | live |
| I8 | **Liquidations below the estimated distribution** (plan of dissolution approved; trading below the proxy's low estimate) | A | The plan fixes an estimated range; holders who want out sell below it; a holder buys and collects the distributions. | DEF 14A "plan of dissolution" + 8-K distributions | ~10-30 | thin, odd lots | 3 (Kim-Schatzberg 1987 on announcements; post-approval arb not tested here) | live |
| I10 | **Subsequent offering period after a tender is accepted** (conditions satisfied; payment in ~3 days) | A, B | After acceptance the acquirer must pay the same cash price to anyone tendering in the SOP; the deal can no longer fail. | SC TO-T/A "subsequent offering period" + "accepted for payment" | ~10-30 | none (tiny spread, tiny risk) | 3 | live |
| C4 | **ETF liquidations after the fund has gone to cash** | A | A closing ETF sells its holdings and holds cash for the last days; its price should equal the known cash NAV; holders who panic-sell give a discount to NAV that the liquidating distribution pays. | 497 "plan of liquidation" + bars | ~100-250 closures (few go to cash early) | thin, odd lots | 4 (Round 30 #21 killed for "NAV is paid data"; a cash fund's NAV is the cash) | live |
| I6 | **CEF rights offerings** (formula price ~95% of market or NAV; over-subscription) | A | The fund sells new shares at a discount to the expiry price; a holder at the record date subscribes (+ over-subscribes) and sells the new shares on delivery. | 497 / N-2 "rights offering" | ~10-20 | over-subscription favours small orders | 2 (peer #9: "CEF rights trade down to the price") | live (low prior) |
| C5 | **IPO retail access (SoFi / Robinhood / Public)**: get allocations at the offer price | F (queueing) | Underwriters must place shares; retail platforms receive a slice; first-day pops pay the allottee. | 424B4 offer price + first-day bars | ~100-200 IPOs | allocation is per account, small orders filled first in some programs | 2 (Ritter's IPO data; allocation history unobservable) | live as a bound only |
| C6 | **Enrichment scan**: which form types precede the biggest 5-day moves in $1-100M ADV names | D | — (a scan, guarded: discover 2020-10..2022-06, confirm 2022-07..2023-12 once, log K) | full_index + SIP panel | — | — | 3 | live |
| I11 | Cash/stock election with proration | A | — | 424B3 election clause | ~25 | small holders exempt? (read) | 2 | live (low prior) |
| I3 | Odd-lot buyback programs | A | The issuer buys <100-share holdings, sometimes with a premium | 8-K "odd-lot" + "program" | ~5 | odd lots only | 3 | live (low prior) |
| C7 | CEF mergers (N-14, NAV-for-NAV): buy the target at a wider discount than the acquirer | A | The exchange ratio is NAV/NAV; a target at a 12% discount turns into acquirer shares at a 6% discount. | N-14 | ~10-20 | none | 3 | **kill X**: CEF NAV history is not free on our data; and the lock needs a short of the acquirer |
| C8 | Transferable rights below intrinsic near expiry | A, F | — | 424B3 + rights tickers | ~5 | thin | 3 | **kill X**: no historical bars for rights symbols |
| C9 | Special-dividend cash/stock elections (REIT E&P purges) | A | Cash is capped at ~20%; elect cash | 8-K | ~2-8 | none (prorated pro rata) | 2 | **kill**: < 5/yr and no small-holder clause |
| C10 | Share-class collapse at a fixed ratio | A | — | 8-K / DEF 14A | ~2-5 | none | 2 | **kill W**: locking the spread needs a short; long-only is the twin trade (Round 30 dead) |
| C11 | Due bills / when-issued around spin-offs | A | — | — | — | — | 2 | **kill X/D**: WI prices not in data; spin-offs dead |
| C12 | CEF discount-management triggers (tender if the average discount > x%) | B | — | N-2 / 8-K | ~10 | none | 3 | **kill X**: needs NAV history |
| C13 | Interval-fund repurchases (N-23C3A) | C | — | — | ~390 | — | 1 | **kill**: interval funds are not exchange-traded (peer I19 is the same; no bars) |
| C14 | Bank/fintech sign-up bonuses, I-bonds, T-bill ladders | — | — | — | — | large %/yr at $2k | 1 | **kill**: not a market edge; outside this repo |
| I12 | CVR deals | A | — | — | ~10 | none | 2 | **kill**: CVRs are mostly non-transferable; the tradable part is the B3 cash spread (dead) |

## Ranking (survivors), by (%/yr at $2.3k-25k) x P(real) x novelty / manual hours

1. **I7 DRIP OCP discount** — a repeating monthly payoff under the cap; P(real) depends on which issuers still offer
   a discount and whether a street-name (Schwab) holder can use it. Simulate the formula on history.
2. **C1/C2 warrant exchanges and cashless redemptions** — contract ratio vs. a thin warrant's price.
3. **C3 DEFM14C written-consent cash mergers** — B3 without vote risk.
4. **I8 liquidations below the low estimate.**
5. **I10 subsequent offering periods** (tiny edge, near-zero risk).
6. **C4 ETF liquidations in cash.**
7. **I6 CEF rights offerings.**
8. **C5 IPO retail access** (a bound: the allocation is unknowable).
9. **C6 enrichment scan.**
10. I11 elections, I3 odd-lot buybacks (low).

Every deal-rule idea: the selection rule and payoff formula go into `round1_prose.md` as an amendment (no N) and are
pushed before the deal list is computed.

## Added 2026-10-02 12:00 (before any outcome on it)
| # | idea | method | contract sentence | source | est/yr | small-size edge | novelty | kill |
|---|---|---|---|---|---|---|---|---|
| C16 | **Forward splits and stock dividends whose fractional shares are ROUNDED UP** (3-for-2, 5-for-4, 5% stock dividends) | A | The issuer's 8-K says fractions are rounded up to a whole share; a holder of 1 share gets 2 in a 3-for-2 (+33% over the ratio), 2 in a 5% stock dividend (+95%). | 8-K / press release "stock split"/"stock dividend" + "rounded up" | ? | per account, 1-share positions only | 4 (B1 covered reverse splits only; grep) | live |
| C17 | Bankruptcy convenience classes for small note claims | A | Small claims get paid more cash | court plans | rare | yes | 5 | **kill X**: court documents, noteholder claims usually a separate class |
| C15 | **Term / target-term CEFs in their final year** | A, B | The charter makes the fund liquidate at NAV on a fixed date (or run a 100%-of-NAV tender); a discount must close by then; a holder buys ~1 year before and collects NAV. | N-CSR / N-2 "will terminate on or about" + bars + distributions | ~2-4 terminations | none (thin CEFs fine) | 3 (CEF practitioners know it; not on any list here) | live |
| I6 | CEF rights offerings | A | — | — | — | — | 2 | **fast kill**: the subscription value is the ex-rights drop (priced); no small-holder clause; peer #9 "CEF rights trade down" |
| I10 | Subsequent offering periods after tender acceptance | A | — | SC TO-T/A | 0.5 | none | 3 | **fast kill**: 5 SOPs with a "commenced" sentence 2016-26, mostly foreign targets (< 1/yr) |
