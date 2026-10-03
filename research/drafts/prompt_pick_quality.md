# PICK-QUALITY HUNT: better night-leg picks (user, 2026-10-02: "improving the stocks the bot picks makes or breaks it")

Run in ~/Documents/Code/Projects/swing-trader, session llm-trader-ee, as a /loop; resume from pick_quality_log.md STATE.
Same discipline as prompt_index_beat.md: every idea written before its outcome; select 2021-23; any rule that touches 2024+
outcomes is registered in round1_prose.md first (program N counted); judge once on 2024-26; RAW night pool
(load_sim(raw_price=True) / cache_rawprice.pkl); tier and tier_hi costs; report $/yr at $2.3k / $10k / $25k; whole shares.
Do not redo the ~30 dead pick filters/tilts in NEXT.md (add. 23 features, Study E ML, news sentiment, FINRA SVR/DTC,
imbalance, cross shares, new listings, LETF weighting (Study W), classes (U), NT/144, lockups, sympathy, $5 cliff, insider tilt).
PASS (book idea) = judge-half book increment > 0 at tier AND tier_hi, NW t >= 2 on the daily increment, placebo (the same
number of picks removed/changed at random per night) >= 95th pct, select half not worse than -0.5pp. A PASS becomes a
switch spec (default off) + shadow, never a live change by this session. Stop when a PASS is shipped as a shadow and two
more ideas have been tried, or after 15 ideas, and tell the user plainly.
Starting ideas: PQ1 single-stock / leveraged / inverse ETFs (3% of picks in 2021 -> 24% in 2026); PQ2 why the stock fell
(headline facts: earnings / offering / downgrade / none) from the Alpaca news archive; PQ3 same-story clusters (one theme,
many picks); PQ4 2026 crowding (picks/night doubled).
