# Research prompt: more edges like the insider-buy trade and odd-lot tenders (event and structural edges)

You are working in the `swing-trader` repo. The last round found two edges the program had never had:
- **Insider-buy day trade (ID3, SHADOW):** an officer/director files a Form 4 purchase -> buy at the next opening
  auction, sell at that day's close; $20M+ ADV; +16.6bp/trade net, held on 2024-26.
- **Odd-lot tender offers:** a buyback above market that fills holders of <= 99 shares in full -> buy 99, tender.
  Every qualifying deal made money; ~1-2 a year; ~$150-200/yr that doesn't scale, which is perfect at $2-25k.

Both share a shape. **Find more of that shape.** Read their writeups first (grep `research/drafts/` for ID3 and
odd-lot), then `CLAUDE.md`, NEXT.md (top + do-not-redo table), and the last amendment of
`research/drafts/round1_prose.md` for the current program N (shared with the lab session).

## The shape (every candidate must have all four)
1. **A public, timestamped event**: an SEC filing, an exchange notice or a corporate action, knowable before you
   trade (point-in-time: use EDGAR `acceptanceDateTime`, not the filing date).
2. **A reason someone pays**: an insider's information, a company's contractual offer, a fund's forced action, or
   a deadline. Name them.
3. **A small-size advantage or a capacity cap** that keeps funds away: odd lots, whole-share limits, deals too
   small to matter, manual steps, a payoff capped per holder.
4. **Fits the accounts**: long-only works in the Roth; whole shares; regular session; at $2.3k / $10k / $25k.

## Two families, judged differently
**A. Statistical event edges (like ID3)**: a type of event predicts a return over a fixed window. Judge with the
program's full bar: pre-register; select 2016-23 (or 2021-23), judge once on 2024-26; official auction prices;
2.5bp/side judged, tier_hi reported; increment > 0 both halves; NW t >= 2; sign-flip AND event-shuffle placebos
(random same-size events on matched dates) >= 95th pct; DSR at the new N.

**B. Contractual / bounded-payoff edges (like odd-lot tenders)**: the payoff comes from a contract, with a known
best case and a bounded worst case. Judge deal by deal: list EVERY qualifying past deal (no cherry-picking: the
rule that selects deals is written before you look at outcomes), the realized P&L of each at whole-share sizes,
the worst case and how often it happened, capital locked and for how long, the manual steps, and $/yr at
$2.3k / $10k / $25k. A "pass" is: positive in aggregate, the worst deal's loss small and explained, the rule
mechanical enough to alert on.

## Where to look (each is a starting point; verify none is already dead)
**Insider and holder filings (EDGAR, free):**
- Form 4 variants:
  - cluster buys (several insiders within a few days);
  - the first purchase in years by a CEO/CFO;
  - buys after a large drop (overlap with the night leg's picks?);
  - 10% owner buys;
  - buys disclosed late (filing lag).
- Form 144 (intent to sell) and its absence, 10b5-1 plan adoptions or terminations (disclosed in 10-Q/10-K since
  2023), and Schedule 13D / 13D/A (activists) vs 13G.
- Buyback authorizations (8-K) vs buybacks actually executed (10-Q tables).

**Contractual offers that favour small holders:**
- Other odd-lot provisions: Dutch-auction tenders with odd-lot priority, mini-tenders, mergers with cash/stock
  elections and proration, and odd-lot buyback programs (companies buying back <100-share holdings, sometimes at a
  premium).
- Rights offerings with oversubscription privileges, DRIP plans that buy at a discount, and thrift
  (mutual-to-stock) conversions, where depositors get subscription rights.
- SPACs trading below their trust value near a redemption deadline (redeem at trust).
- Closed-end fund tender offers, liquidations and conversions to open-end (discount collapse).
- Preferreds and baby bonds near a call date, and liquidation trusts.

**Forced and mechanical flows on known dates:**
- IPO lockup expirations (the date is in the S-1).
- Spin-offs (index funds and mandates sell the spun-off stock).
- Reverse splits that push holders below round lots.
- Delisting notices (Form 25) and uplistings from OTC.
- Index additions and deletions in small indexes nobody front-runs.
- Follow-on offerings priced at a discount (424B pricing vs the next open).
- SSR (Rule 201) days, and NT 10-K / NT 10-Q late filings.

**The bot's own advantage:** it already watches the night leg's beaten-down names at 15:40. Which of these events
land on its picks, and do they change the picture? (Offering filings did: Study T shadow.)

## Process
1. **Build an event pipeline first**: a cached, point-in-time EDGAR index for the form types you use. EDGAR full-text
   search and the daily form indexes are free. The contact User-Agent comes from `NOTIFY_EMAIL` / `SEC_USER_AGENT`
   in `.env` via `swingtrader.daily.news_judge.sec_headers()`; if neither is set, ask the user. Prices: Alpaca
   (free, raw prices for any filter, official auction prints for entries/exits).
2. **List >= 30 candidates** in `research/drafts/event_edge_candidates.md`. For each:
   - family A or B;
   - the event, who pays and the small-size advantage;
   - the dead-list check (NEXT + RESULTS; Study T, AN and add. 12 covered some filings and news);
   - data cost, events per year, and expected $/yr at $2.3k / $10k / $25k.

   Commit it before any test.
3. **Test the best 4-6**: family A pre-registered in `round1_prose.md` (<= 3 variants each, N from the last
   amendment); family B with its deal-selection rule written and committed before you look at outcomes.
4. **Build what passes**:
   - Family A: a default-off switch with a shadow log (like ID3), a kill rule, tests, and a gate in the weekly digest
     (`swingtrader/daily/digest.py`).
   - Family B: an alert job like the odd-lot one (email via the existing Resend notifier) with the deal terms, the
     exact action in Schwab, the deadline and the worst case. Nothing places orders; the user acts.
5. **Paid data**: price it and ask the user (and tell the lab session by SendMessage) before spending; the shared
   Databento credit is nearly used up.

## Deliverables
- `event_edge_candidates.md` (>= 30, committed first); one writeup per tested idea with a NEXT.md entry (dead ones
  in the do-not-redo table); switches and alerts for the passes, with `make test` green.
- A closing table: event | family | who pays | verdict | events/yr | $/yr at $2.3k / $10k / $25k | capacity |
  what live evidence would change it.
- Add each live alert or shadow to the weekly digest so the user sees it without asking.
- Commit and push after each study; merge (never rebase) `origin/main` first, because the lab session pushes too.
