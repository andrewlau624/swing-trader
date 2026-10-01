# Studies Lab-BE / Lab-BF — Nasdaq opening-cross imbalance (Databento): reversal DEAD; continuation decayed

Data: Databento XNAS.ITCH `imbalance`, opening-cross messages. Lab-BE: 09:27-09:28, 102 names, **$27.13, unusable**.
Lab-BF: 09:28:00-09:28:30, top 28 Nasdaq names + QQQ/TQQQ, **$8.21**. Entry: the official opening cross (no
spread). Exit: 10:00 at the SIP NBBO. 2022-01 .. 2026-09.

## Lab-BE (Lab Round 29): UNTESTABLE as registered
Nasdaq's opening messages carry near/far only from 09:28:00; the registered window ended at 09:28:00. 0 signals.
The second registration error of this kind (MISTAKES.md); a probe gate is now in code.

## Lab-BF (Lab Round 30): DEAD — the rule had the sign wrong
Long the 2 names whose 09:28:30 near price is furthest BELOW the reference (sell imbalance), short the 2 furthest above.

| variant | n | gross | 1x net (t) | H1 / H2 1x | 2x H1 / H2 | placebo |
|---|---|---|---|---|---|---|
| Lab-BF1 long+short | 4,693 | **−7.8** | −12.6 (t −5.1) | −18.3 / −6.6 | −23.2 / −11.4 | 0.4 |
| Lab-BF2 long only | 2,350 | −8.9 | −14.0 (t −3.1) | −16.8 / −11.0 | −21.9 / −16.1 | 0.8 |

## Reading
- Opening imbalance pressure does NOT revert by 10:00; it continues (placebo 0.4th pct = reliably the wrong side).
- The continuation (diagnostic, not registered): H1 +13.5bp gross (2022 +17.8, 2023 +8.2), **H2 +1.9bp** (2025 +5.0,
  2026 YTD −1.8). The exit spread costs ~3.7bp. It has decayed below cost.
- H2 has now been seen, so no honest holdout remains for a continuation variant. **Not registered.**
- Opening-imbalance family closed for the lab.
