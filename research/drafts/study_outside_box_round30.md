# Round 30 (outside the box): 47 forced-trader ideas, 9 explored, none survived; nothing registered (N stays 752)

Brief: `prompt_outside_box.md`. Ideas, kills and novelty searches: `outside_box_ideas.md` (commit e5fd4e2, before
any number). Every look: `outside_box_explore_log.md` (L1-L15). Script: `research/sim/outside_box.py`. Outputs:
`data/research/program/outside_box_explore*_out.txt`.

## What was done
1. **Diverge:** 47 ideas, each written as "who must trade at a bad price, and why". They came from 7 methods,
   with a WebSearch on the 6 leading ideas to score novelty.
2. **Kill fast:** 34 died on the dead-list check (NEXT / RESULTS), as renamed common strategies, as untestable on free
   data, or on whole-share size. 4 were parked because they need EDGAR (#8 supply shocks, #11 odd-lot tender offers,
   #13 SPAC trust as T-bill substitute, #44 NT 10-K filers), and this Mac's `.env` has no SEC User-Agent.
3. **Explore (select data only: panel cut at 2023-12-31, night picks 2021-23):** 9 ideas, 15 logged looks. All 9
   died. Nothing reached step 4, so 2024-26 was never read for any Round 30 idea, and the judge half stays clean for
   the next round.

## Closing table

No idea reached the book stage, so there is no %/yr figure. The gross per event is the select-data number.

| idea | the forced trader | verdict | %/yr and $/yr at $2.3k / $10k / $25k | capacity | what live evidence would change it |
|---|---|---|---|---|---|
| LETF closing cross vs L × underlying (#3) | LETF holders selling into the LETF's own closing cross below NAV; APs skip gaps under their fixed cost | **dead (lookahead)**: +12.4bp overnight on the official close (t 10.1, every year), but 0.0bp when decided at 15:45-15:59; the cross itself makes the gap. The LOC version earns +1bp vs L × underlying (it buys late selloffs) | n/a (would be ~0 net) | — | quotes at 15:59:59 (the lab recorder's L1) showing a same-instant gap that the cross then closes. A lab/intraday question, not a night-book one |
| share-class twins (#1) | index funds / MOC flow trading the indexed class at any price | **dead**: liquid pairs +6.8bp next close (mostly daytime), below a 5bp round trip plus beta; the big gross is stale prints in < $1M ADV classes | n/a | — | none |
| same-index ETF clones (#2) | thin-clone sellers taking the print | **dead**: +5.6bp, t 13.8: real and consistent, but it equals one round trip | n/a | — | only as a free substitution when the bot must buy the index anyway (SPY → IVV/VOO/SPLG; QQQ → QQQM): ~+5bp × the V6 shadow's trades, not worth code today |
| wash-sale day-31 rebuy (#4) | harvesters who can't rebuy for 30 days | **dead**: no bump; day 0 −19.5bp (Oct-Dec −47) | n/a | — | none |
| retail trade size on night picks (#5) | app users' queued open buys | **dead**: $/trade ≈ price (ρ 0.83); price tilt is already dead | n/a | — | none |
| the $5 cliff (#6) | mandates/margin desks dumping sub-$5 names | **dead for a long book**: crossers keep falling (1d −52, 5d −109, 10d −167bp; $4 placebo −31, $7 +2) | n/a | — | a short book with cheap borrow on sub-$5 names (not this account) |
| lockup-expiry night picks (#7) | pre-IPO holders selling at day ~180 | **dead**: −122bp within-night, n 23 | n/a | — | none |
| sympathy losers (#9) | sector funds dumping a crashed name's peers | **dead**: peers bounce less (−7.9 vs −2.8bp) | n/a | — | none |
| listing exchange (#10) | MOC sellers routed to each exchange's auction | **dead**: Nasdaq/NYSE order flips 2021-22 vs 2023 | n/a | — | none |
| Treasury auction cycle in IEF (#14) | dealers absorbing new supply | **dead at the bar**: +2.7bp/day on days +1..+3 (t 2.0) ≈ the 5bp switching cost × 38 auctions/yr | ~0 | large | none at retail cost |

## The three most surprising things

1. **The leveraged-ETF "mispricing" is made by the closing cross itself, and it looks great if you cheat by one
   second.** On official closes, liquid 2x/3x ETFs that closed ≥ 2σ below L × their underlying recovered +12bp
   overnight, t 10, positive every year. That is the cleanest-looking result the program has seen in a while. Measured
   at 15:45, 15:50, 15:55 or 15:59, the same signal earns 0.0bp. The cross removes the 15:45 gap (+21bp) and creates
   its own gap, which you can only see after the print. General lesson for the program: **any feature that uses day
   d's official close is lookahead for an order in day d's closing cross**, however mechanical the story (add. 14 was
   the same trap on the night pool). The share-class and clone versions carry the same caveat.
2. **Forced sellers are usually right, or at least persistent.** Every idea that assumed forced selling is
   uninformed and bounces went the other way. Stocks crossing below $5 keep falling (−109bp in 5 days, three times the
   $4 placebo). Losers on lockup-expiry day fall another −122bp. SIC peers of a crash bounce *less* than unrelated
   stocks that fell the same amount. The forced selling that does pay a long-only small account is the generic
   overnight capitulation the night leg already buys. Adding a "why" to it hasn't improved it in this round or in
   Studies T, AY, BD and DS4.
3. **The rules everyone obeys leave no footprint.** The wash-sale rule makes tens of thousands of harvesters wait
   exactly 31 days, yet crashed names show no buying at day 31 (day 0 −19.5bp). The Treasury auction cycle is real
   (+2.7bp/day after auctions, as published) but exactly as large as the cost of switching in and out of it. Rules
   that are known to everyone, by date, are arbitraged down to the cost of trading them. The constraints still worth
   chasing are the ones that **only bind on large accounts**: odd-lot tender priority (#11) and SPAC trust floors
   (#13). Both are parked on the missing SEC User-Agent.

## What is left
- **Needs the user:** add `SEC_USER_AGENT` (or `NOTIFY_EMAIL`) to this Mac's `.env`. That unblocks #11 odd-lot tender
  offers, the only idea on the list that pays *more* the smaller the account (an operational report, not a
  statistical test), plus #13, #8 and #44.
- Program N unchanged at 752 (exploration looks do not count toward N). The 2024-26 judge half was not touched.
