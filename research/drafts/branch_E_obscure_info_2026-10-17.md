# Branch E: obscure-venue public information, small-cap targets (2026-10-17)

Verdict: **zero surviving cards.** One venue (DoD daily contract announcements) is genuinely slow and point-in-time, but it
fails the ceiling gate and its closest tested neighbours (C5, D2, R3-7) are dead. Everything else is either already tested
and dead in this repo, or has no lag. No backtest was run; return numbers below are descriptive only.

## What I verified (opened / ran)
- defense.gov and war.gov contract pages: HTTP 403 to curl and WebFetch (same as `jump_hunt_log.md:20`, D3 never run for this
  reason). The mirror forth.news returns a Vercel 429 challenge. Govly's public signal page opened but is a weekly digest
  (dated 2026-09-19, no time of day, names only the big primes). So **a point-in-time DoD archive cannot be collected from
  this machine**; the Wayback CDX endpoint returned 503 on one try (not retried).
- **USAspending lag is the key structural fact.** `spending_by_award_count`, DoD awarding agency, contracts >= $7.5M
  (queried 2026-10-17): May 2026 = 11,481; Jun = 8,998; Jul = 4,113; Aug = 12. DoD data on USAspending is ~90 days late.
  So the defense.gov daily list (posted ~5pm ET, awards >= $7.5M per its own header in the search result for
  https://defense.gov/News/Article/Article/4609970/contracts-for-sept-23-2026) is the only real-time public venue, and
  USAspending cannot be used to timestamp events (only action dates, which precede public availability by up to 90 days).
- Descriptive size count, USAspending DoD contract obligations >= $7.5M per award, summed by recipient, FY2023 and FY2024
  (touched; not a test), name-matched to Sharadar domestic common stocks with median mcap < $1.5B (script
  `/tmp/e_work/match.py`, crude exact-name match, so an undercount): only 27 recipient-years matched. Annual DoD sum >= 10%
  of mcap: 7 (FY23) and 4 (FY24); >= 20%: 2 and 3. Names: XXII, GLDD (dredging, recurring Army Corps), DPSI, TLS, CVU, FEIM,
  TPC, IPW. These are annual sums over many awards, so single-award events >= 10% of mcap are fewer, order **~5-15/yr
  across all listed names**. Directly awarded small public primes are rare; most small defense caps are subcontractors to
  primes and never appear on defense.gov.
- Lag evidence from one web search (CPI Aerostructures, https://www.stocktitan.net/overview/CVU/ and investing.com items):
  its award announcements are by company press release, mostly from primes (Raytheon, L3Harris, Northrop), and the
  one-day moves cited are +1.5%, +1.9%, +4.6%, +6.8%, +13.6%. The search found no case of a defense.gov listing preceding a
  company release. I did not hand-collect dated lags; that sample is not in hand.

## Why no card
1. **Gap.** The list is posted after the close; the issuer's own release/8-K normally lands the same evening or next
   morning (the issuer wants it public). The tradable window opens at the same time as the company's PR, so the "obscure
   venue" lead is hours, not days. This is the D2/C5 failure (`jump_hunt_log.md:351,365`): D2 hold60 +2.4%/+0.3%/+0.6% P0.06;
   C5 (contract >= 10% mcap + float < 20M) n=109, hold60 +6.4% but ex-top3 -0.5%, all arms fail. R3-7 (value >= 25% of
   revenue from 8-K Item 1.01) n=7 events, dead for rarity.
2. **Ceiling.** ~5-15 events/yr x assume +5% net edge (generous; C5 measured ~0 ex-top3) x 100% of a $10k account x 50%
   capture = **~1.3-3.8pp/yr**, versus the +8pp gate. At $2.3k and $25k the pp figure is the same (event-count bound);
   dollars ~$30-90 / $130-380 / $320-950. Capital lock a few days, not the issue.
3. **Mechanism reliability.** Primes' subcontract awards (the majority for small caps) are not in the venue at all.

## Dropped list (one line each)
- DoD daily contracts (this file): ceiling < 4pp, gap, C5/D2 dead; D3 stays "not explored: venue inaccessible".
- USAspending / SAM.gov awards: ~90-day lag for DoD (verified above); civilian agencies post faster but awardee press
  releases precede; no timestamp of public availability. Covered in spirit by C5/D2.
- FDA 510(k) clearances: D1 dead (`jump_hunt_log.md:350`, n=180 hold60 +1.2% P0.20; clearance precedes press release but no lift).
- ClinicalTrials.gov status changes: D9 dead (`:358`, hold60 n=111 +1.9%/-3.0%/-7.2%).
- FDA adcom Federal Register notices: R3-3 dead (`:410`, too rare, notice weeks ahead).
- Federal Register naming companies: adcom case above; other rule texts are not company-specific (no event).
- PACER / CourtListener / PTAB / ITC rulings: orders post to the public docket at once and are monitored by event-driven
  desks and litigation newsletters; small-cap exposure exists but I found no point-in-time archive in hand and did not
  open one; binary outcome with unknown prior, so it fails "reason prices lag". Not verified either way; no card.
- FERC / state PUC rate orders: utilities are large, covered, and 8-K'd; not small/uncovered.
- NI 43-101 / mining permits: filed on SEDAR+ at the same time as the company news release; no lag; Canadian venue.
- FAA type certificates, CMS NCDs / reimbursement codes: sparse (a few per year across tiny names), manually sourced, no
  archive with timestamps; cannot reach a count that clears the gate even at 50% payoffs. Unverified, dropped on ceiling.
- Gaps in my evidence: no hand-collected lag sample (the DoD source was blocked), and PTAB/ITC/CMS were reasoned not
  sampled.

## Falsification spec if the user wants it closed anyway (not recommended)
Needs a DoD-list archive (Wayback snapshots of defense.gov article pages 2019-2025, unverified accessible). Event = awardee
maps to a listed ticker with mcap < $1B and award >= 10% of mcap, announced in the evening list, with no company 8-K or PR
in the prior 24h (EDGAR submissions timestamp). Enter next open cross, exit at +5 sessions close cross; gate: n >= 40, median
> 2x cost, ex-top-5 > 0, day-clustered t >= 2, halves agree; pre-2020 untouched (the repo's C5 used 2021+). Expected n is the
problem: ~5-15/yr gives 40 events only after ~4-8 years.
