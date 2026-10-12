# Study PCAL — negative-control calibration of the program's PASS machinery (diagnostic, no N)

Registered `round1_prose.md` (2026-10-06, third-robot session). One read. Runner `research/sim/pcal.py`,
out `research/sim/pcal_out.txt` / `/tmp/pcal3.log`.

**Mechanism.** The program judges overnight-reversal candidates on delisted-complete daily bars with
one frozen bar: t_cl >= 2 at `tier` cost, halves both positive, median > 0, ex-top-5 > 0. Its FALSE-PASS
rate was never measured. PCAL runs the NX night-leg machinery with 7 pre-named negative controls on
2021-2026 (no candidate judged).

**Result (deterministic, machine-load-contended): 0/7 controls pass.**

| control | nights/trades | mean net | median | t_cl | halves | verdict |
|---|---|---|---|---|---|---|
| C0 exact rule (check) | 1252/7792 | +16.1bp | +10.2bp | 1.11 | +23 / +9 | consistent with known (gross ~+47bp, tier eats the t) |
| C1 lag+1 | 1251/7792 | −13.7bp | −15.2bp | −0.85 | −17 / −11 | null — correctly rejected |
| C2 lag+5 | 1246/7748 | −30.7bp | −15.0bp | −2.65 | −26 / −36 | correctly rejected |
| C3 IBS>=0.90 | 98/106 | −125.5bp | −36.7bp | −2.57 | −163 / −88 | correctly rejected |
| C4 momentum mirror | 119/124 | +157.1bp | +21.7bp | 1.90 | +62 / +251 | **fails the t bar** — machinery excludes it |
| C5 IBS permuted in-day | 1272/8560 | −24.5bp | −7.9bp | −1.53 | −34 / −15 | null |
| C6 random names | 1252/7792 | −29.3bp | −9.7bp | −2.47 | −35 / −23 | null |
| C7 lag+10 | 1241/7701 | −31.7bp | −24.5bp | −2.78 | −30 / −34 | correctly rejected |

**Verdict: the machinery is CALIBRATED (p-hat = 0/7).** Any 2021-26-feasible spurious rule in the
night-leg shape fails the bar; the exact rule itself fails it NET at `tier` in this window (its live
edge rests on the ~0bp measured auction costs, not on the `tier` assumption). The verdict list (IBS
OOS, night NX, TME, H-POOL-conditional) stands with the measured p-hat as its background error rate.

**Adversarial notes.** (1) A same-day-open shift bug (collapsed o_next) produced fake +1430bp/+145bp
"+edges" — the same artifact class the program's part-3 memory attributes to daily-proxy optimism;
any consumer of adjusted open/close series must re-validate the shift (this session's build_panel had
it, nx.py does not). (2) C4 (buy after UP-8% days at close) earns +157bp mean but t_cl 1.90 — real
overnight drift in momentum names, BELOW the bar: recorded as an observation, not a PASS (long-only
equity beta + squeeze-era overhang; not tested further).

**Program-level implication.** Judged verdicts in the record ≈ 60; expected spurious passes ≈ 60 ×
(0-1/7) ≈ 0-8. The non-decayed C4 near-miss shows the bar never got there — trims, not tightens.
