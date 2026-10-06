"""Forced-flow capacity scanner: rank per-holder-capped contract payoffs by
events/yr x net edge x deployable share x capture at $2.3k/$10k/$25k against a
+8pp/yr after-tax gate.

This is a CENSUS / RANK of families whose outcomes were already read (Study CPC
N 818, odd-lot tenders, DL2 warrants, DL4 liquidations, DL-G27 thrift, G1). It
reads no new outcome and registers no new N. Costs, the capital allocator and the
PASS/NEAR/FAIL labels are reused verbatim from research.sim.cpc -- do not fork the
economics here.

    PYTHONPATH=. .venv/bin/python -m research.sim.forced_flow_scan
"""
from __future__ import annotations

import pathlib

from research.sim import cpc
from research.sim.cpc import EXPO

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/forced_flow_scan_out.txt"
SIZES = (2300, 10000, 25000)
GATE = 8.0  # pp/yr after-tax excess; cpc.label's PASS threshold is mean >= 8

LINES: list[str] = []


def say(s=""):
    print(s)
    LINES.append(s)


def stat_family(evs, C):
    """Run one family alone through cpc's allocator at capital C."""
    df, mx = cpc.allocate(evs, C, spy=None)
    if df.empty:
        return dict(fired=0.0, elig=len(evs) / EXPO, dep=float("nan"), net=float("nan"),
                    pp=float("nan"), ex5=float("nan"), pos=float("nan"), cap=float("nan"),
                    mx=0.0, usd=0.0, label="NO-FIRE")
    at = cpc.summarize(df, C, "ex")
    s = cpc.stats(at, C)
    s5 = cpc.stats(cpc.summarize(df, C, "ex", drop5=True), C)
    theo = sum(e["maxu"] * e["upnl"] for e in evs) / EXPO
    real = df.pnl.sum() / EXPO
    return dict(fired=len(df) / EXPO, elig=len(evs) / EXPO, dep=df.dep.median() / C,
                net=df.ex.mean(), pp=s["mean"], ex5=s5["mean"], pos=s["pos"],
                cap=(real / theo if theo else float("nan")), mx=mx, usd=at.sum() / EXPO,
                label=cpc.label(s["mean"], s["pos"], s5["mean"]))


def main():
    families = [
        ("B1 reverse-split round-up", cpc.b1(), "1 share/account; needs broker to round up (VIVK check)"),
        ("B2 split-off (odd-lot prio)", cpc.b2(), "<=99 sh/owner; manual Schwab exchange"),
        ("TENDER odd-lot cash (floor>=1%)", cpc.tenders(), "<=99 sh/owner; manual election"),
        ("TENDER Dutch/cash all-priority, no floor", cpc.tenders(all_prio=True), "filter removed; coin-flip"),
        ("DRIP discount", cpc.drip(), "$1k/mo plan; taxable-only; not automated"),
        ("THRIFT conversion", cpc.thrift(), "$2k order; needs depositor acct 1-2y earlier"),
    ]

    say("# Forced-flow capacity scanner (rank of already-read families; no new N)")
    say(f"gate: after-tax excess >= {GATE:.0f}pp/yr  |  exposure {EXPO} yr (2016-01..2026-09)  |  "
        "economics/allocator reused from research.sim.cpc")

    for C in SIZES:
        say(f"\n## ${C:,}")
        say(f"{'family':42s} {'ev/yr':>6s} {'net $/ev':>9s} {'dep/cap':>8s} {'capt':>6s} "
            f"{'pp/yr':>7s} {'ex5':>7s} {'pos':>5s} {'$/yr':>8s}  label")
        for name, evs, note in families:
            r = stat_family(evs, C)
            say(f"{name:42s} {r['elig']:6.1f} {r['net']:9,.0f} {r['dep']*100:7.2f}% "
                f"{r['cap']*100:5.0f}% {r['pp']:+7.2f} {r['ex5']:+7.2f} {r['pos']:4.0%} "
                f"{r['usd']:8,.0f}  {r['label']}  [{note}]")

        combined = cpc.b1() + cpc.b2() + cpc.tenders() + cpc.drip()
        cd, cmx = cpc.allocate(combined, C, spy=None)
        ca = cpc.summarize(cd, C, "ex")
        cs = cpc.stats(ca, C)
        cs5 = cpc.stats(cpc.summarize(cd, C, "ex", drop5=True), C)
        say(f"{'PRIMARY stack (B1+B2+tender+DRIP)':42s} {len(cd)/EXPO:6.1f} {cd.ex.mean():9,.0f} "
            f"{'':8s} {'':6s} {cs['mean']:+7.2f} {cs5['mean']:+7.2f} {cs['pos']:4.0%} "
            f"{ca.sum()/EXPO:8,.0f}  {cpc.label(cs['mean'], cs['pos'], cs5['mean'])}")

    say("\n## families named in the request with no scorable table (do not fabricate)")
    say("RIGHTS OFFERINGS      : no per-deal table exists; study_cpc.md line 38 scores $0; earlier rounds ~0.")
    say("SPAC LIQUIDATIONS     : liquidations.py 76 DEF14As -> 16 priced, rule met 1/16 (OTIC); ~0.1 deals/yr (DL4).")
    say("WARRANT OFFERS        : warrant_offers.py 38 deals, -2.2%/trade mean, 53% hit -> DEAD (DL2).")
    say("CEF NAV TENDERS       : pro-rata (54/55 no odd-lot priority); capital-proportional, ~-0.2pp; not per-holder-capped.")
    say("DUTCH AUCTIONS        : included inside TENDER (kind=cash_dutch); the floor>=1% filter is what makes it pay.")

    say("\n## keep/drop against the +8pp/yr gate, by size")
    for C in SIZES:
        keep = []
        for name, evs, _ in families:
            r = stat_family(evs, C)
            if r["pp"] >= GATE:
                keep.append(f"{name} ({r['pp']:+.1f}pp)")
        say(f"${C:>6,}: " + ("; ".join(keep) if keep else "none clear +8pp standalone"))

    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
