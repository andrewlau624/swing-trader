# Scale plan: where each leg stops (Studies V, X + diagnostic scale_legs_diag.txt)

| leg | where the money goes | impact at $1M equity (round trip, Y 1) | vs its edge | stops scaling |
|---|---|---|---|---|
| night (auctions, small caps) | opening auction ~$0.74M median | 19-60bp (model A) | gross ~24.6bp | **~$100-250k**; cap it (Study X) |
| noise QQQ (intraday) | $32.8B ADV | 1.4bp | ~+2bp/day planning edge | ~$1M; MNQ past ~$160k also removes this (NQ ≫ QQQ) |
| noise SMH | $4.1B ADV | 7.7bp | same | ~$250k: drop SMH to QQQ/MNQ as capital grows |
| IBS (18 ETFs, 3 at a time) | $0.55-47B ADV | median 2.3bp, worst XBI 4.1bp | per-trade edge: check before $5M | low single-digit $M |

So the order of operations as money arrives (CLAUDE.md: large sums are coming):
1. Now-$25k: nothing changes; the live bot logs participation; review section 8 watches Y.
2. $25k-$100k: set `night_impact_y: 4` (or the fitted value). The night leg stops growing in dollars.
3. ~$160k+: MNQ swap for the QQQ noise leg (Study D: 60/40 tax + capacity), retire SMH.
4. $1M+: the book is IBS + futures-noise + whatever the night leg's cap allows; new edges must
   be found in liquid instruments (the research program's next frontier), or the surplus sits
   in index exposure.
The Roth's $7.5k/yr shares the same night-leg auctions: the dollar cap is per BOTH accounts.
