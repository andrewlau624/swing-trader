# Discovery loop (Round 33, second session) — no new independent edge; nothing registered (N stays 760)

Brief: `prompt_discovery_loop.md`. Method: 40 candidate ideas written before any outcome (`discovery_ideas.md`,
bc536c... commit b1c536c), 8 killed, the rest ranked; a 168-form-type enrichment census (method D); then the top
candidates tested. Session: llm-trader-mid-01.

## Verdicts (not counting quick-kills)

| idea | method | track | events/yr | verdict | numbers |
|---|---|---|---|---|---|
| I26 insider exercise-and-hold (Form 4 code M, no same-day S) | E | statistical | ~2400 trades | **explored-dead** | select ADV>=$20M: 9610 trades, net -0.3bp, median -1.8bp, hit 49%, t -0.11 |
| 8-K12B successor/shell registration, next session | D confirm | statistical (rare) | ~6 | **explored-dead** | select: RARE gate fails; deal report (37 deals, hold 1) hit 38%, mean -2.19%, worst -36.2% |

**Why I26 fails:** an option exercise (M) delivers shares at a strike, so — unlike an open-market purchase (P) —
it carries no purchase information; it is the ID3 mechanism's null.

**Why 8-K12B fails:** the successor (often a shell after a merger) trades down hard the next session; there is no
forced buyer on the long side.

## Method D — enrichment scan (`research/sim/discovery_enrich.py`, K=168)

162,848 big 5-day-move events ($1-100M ADV, 2020-10..2022-06) over 4,086 names; 89,256 issuer-days with a form in
the prior 10 days. Top enrichment ratios (95% CI): 8-K12B 5.62 [3.10,159.9] (n 34), S-11/A 2.85 (17), 15-12B 2.69 (16),
144/A 2.53 (15), **SC TO-I 2.53 [1.26,14.6] (46)**, 25 2.45 [1.63,6.75] (135), CT ORDER 2.26 (41), S-3MEF 2.04 (87),
S-3 1.75 (1043), 424B5 1.72 (2556), 424B3 1.70 (3327), 25-NSE 1.59 (360), SC 13D 1.46 (1152). Nothing here is a new
forced-trader form: the shelf/registration forms are the banned next-session-drift family, 25-NSE is dead, SC TO-I is
the already-covered tender family, and 8-K12B (the one with a tight-enough CI) failed its confirmation test.

## Quick-kills (written reason, no outcome looked at)

- **I14 Reg SHO threshold-list close-out:** the Nasdaq daily list is 16-39 names with ~3 new/day, almost all sub-$2
  thin names — no statistical power and the wrong name profile.
- **I29 CEF manager buys:** only 58 in the whole 2020-26 Form-345 cache; too rare and a subset of ID3.
- **I37 odd-lot same-issuer exchange offers:** the corpus has 18 exchange offers, ~5 same-issuer over 10 years; B2
  already covers the paying split-off shape.
- **I4/I39 rights offerings at a fixed discount:** "over-subscription privilege" is shelf/ATM boilerplate; genuine
  completed offers cannot be separated by text and the payoff is ~0.
- **I1/I2/I15 round-up pre-announcement window:** the proxy does announce the clause weeks early, but the payoff is
  B1's exact formula; entering earlier is a banned announcement-drift bet. `roundup_watch` already fires on terms.
- **I22 deregistration 15-12B/G:** OTC with no Alpaca bars and the long side is the wrong side.

## Closing

The surviving families after 168-form census + contract probes are exactly the ones already known: own-money
purchases (ID3, EV2) and odd-lot / round-up / split-off contract payoffs (B1, B2, all with live alerts). No new
independent book; **no N registered; program N stays 760**. The open live question is unchanged: whether Schwab passes
a reverse-split round-up to a 1-share holder (2-3 real deals settle it at ~$0.25 of risk each).
