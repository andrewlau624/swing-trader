"""Study CPC (rules: round1_prose.md amendment "Study CPC", commit 40e3910): census of all per-holder-capped contract
payoffs 2016-2026 as ONE opportunity. One run; nothing fitted.

    PYTHONPATH=. .venv/bin/python -m research.sim.cpc
"""
from __future__ import annotations

import math
import pathlib

import numpy as np
import pandas as pd

from research.sim.event_fetch import raw_bars

ROOT = pathlib.Path(__file__).resolve().parents[2]
P = ROOT / "data/research/program"
OUT = P / "cpc_out.txt"
TB = dict(zip(range(2016, 2027), [0.3, 0.9, 1.9, 2.1, 0.4, 0.05, 2.0, 5.1, 5.0, 4.2, 3.7]))
YEARS = list(range(2016, 2027))
EXPO = 10.75
PRIO = {"B2": 0, "TENDER": 1, "DRIP": 2, "THRIFT": 3, "CEF": 4, "B1": 5}
LINES: list[str] = []


def say(s=""):
    print(s)
    LINES.append(s)


def h(p: float) -> float:
    if p < 1:
        return min(max(0.005 / max(p, 1e-6), 0.01), 0.04)
    if p < 5:
        return 0.01
    if p < 20:
        return 0.003
    if p < 100:
        return 0.0015
    return 0.0007


# ------------------------------------------------------------------ events
def ev(fam, sym, entry, exit_, ucost, upnl, maxu, cont=False, spy_ret=None):
    return dict(fam=fam, sym=sym, entry=pd.Timestamp(entry), exit=pd.Timestamp(exit_), ucost=ucost, upnl=upnl,
                maxu=maxu, cont=cont)


def b1(mode="up5", cash=False):
    d = pd.read_csv(P / "roundup_deals.csv")
    d = d[(d.status == "ok") & d.ratio_chk.between(0.33, 3)].copy()
    out = []
    for r in d.itertuples():
        cost = r.ps * (1 + h(r.ps))
        if cash:
            pnl = r.cash - r.ps * h(r.ps)
        else:
            pe = r.pe5 if mode == "up5" else r.pe
            pnl = pe * (1 - h(pe)) - cost
        ex = pd.Timestamp(r.ex)
        out.append(ev("B1", r.symbol, r.S, ex + pd.Timedelta(days=7 if mode == "up5" else 1), cost, pnl, 1))
    return out


def b2():
    d = pd.read_csv(P / "splitoff_deals.csv")
    out = []
    for r in d.itertuples():
        cost = r.entry * (1 + h(r.entry))
        pnl = r.value * (1 - h(r.recv_px)) - cost
        out.append(ev("B2", r.parent, r.entry_d, r.exit_d, cost, pnl, 99))
    return out


def tenders(all_prio=False):
    t = pd.read_csv(ROOT / "data/research/night/tender/oddlot_trades_rule.csv")
    q = t[(t.kind != "nav") & (t.entry == "B") & (t.oddp == "Y")]
    if not all_prio:
        q = q[q.floor_gain >= 0.01]
    out = []
    for r in q.itertuples():
        fin = r.floor if (r.kind == "cash_dutch" and pd.notna(r.floor)) else r.final
        if pd.isna(fin):
            continue
        cost = r.px * (1 + h(r.px))
        d0 = pd.Timestamp(r.date)
        out.append(ev("TENDER", r.oid.split("_")[0], d0, d0 + pd.Timedelta(days=int(r.days)), cost, fin - cost, 99))
    return out


def cef():
    t = pd.read_csv(ROOT / "data/research/night/tender/oddlot_trades_rule.csv")
    n = t[(t.kind == "nav") & (t.entry == "B")]
    syms = sorted({o.split("_")[0] for o in n.oid})
    bars = raw_bars(syms, "2015-10-01", "2026-09-30")
    out = []
    for r in n.itertuples():
        s = r.oid.split("_")[0]
        b = bars.get(s)
        d0 = pd.Timestamp(r.date)
        ex = d0 + pd.Timedelta(days=int(r.days))
        if b is None or not len(b):
            continue
        later = b.index[b.index >= ex + pd.Timedelta(days=7)]
        if not len(later):
            continue
        res = b.close.loc[later[0]]
        p = (r.prorate / 100.0) if pd.notna(r.prorate) else 0.25
        p = min(max(p, 0.0), 1.0)
        cost = r.px * (1 + h(r.px))
        val = p * r.final + (1 - p) * res * (1 - h(res))
        out.append(ev("CEF", s, d0, later[0], cost, val - cost, 10**6))
    return out


def drip():
    d = pd.read_csv(P.parent / "events/drip_ocp_deals.csv")
    out = []
    for r in d.itertuples():
        i = pd.Timestamp(r.id)
        proceeds = 1000 + r.pnl5
        pnl = r.pnl5 - proceeds * h(r.close_id)
        out.append(ev("DRIP", r.sym, i - pd.Timedelta(days=5), i + pd.Timedelta(days=14), 1.0, pnl / 1000.0, 1000, cont=True))
    return out


def thrift():
    d = pd.read_csv(P / "goal_dl27_deals.csv")
    out = []
    for r in d.itertuples():
        i = pd.Timestamp(r.ipo)
        pnl = 10 * r.d1 - 10 * (1 + r.d1) * h(10 * (1 + r.d1))
        out.append(ev("THRIFT", r.tk, i - pd.Timedelta(days=28), i + pd.Timedelta(days=1), 10.0, pnl, 200))
    return out


# ------------------------------------------------------------------ allocator
def allocate(events, C, tb=True, spy=None):
    evs = sorted(events, key=lambda e: (e["entry"], PRIO[e["fam"]]))
    active: list[tuple[pd.Timestamp, float]] = []
    rows = []
    maxcap = 0.0
    for e in evs:
        active = [(r, c) for r, c in active if r > e["entry"]]
        free = C - sum(c for _, c in active)
        if e["cont"]:
            u = min(e["maxu"], free / e["ucost"])
            if u < 1:
                continue
        else:
            u = min(e["maxu"], math.floor(free / e["ucost"]))
            if u < 1:
                continue
        dep = u * e["ucost"]
        pnl = u * e["upnl"]
        days = max((e["exit"] - e["entry"]).days, 1)
        opp = dep * TB[e["exit"].year] / 100 * days / 365
        active.append((e["exit"] + pd.Timedelta(days=1), dep))
        maxcap = max(maxcap, sum(c for _, c in active))
        spyopp = np.nan
        if spy is not None:
            a = spy.asof(e["entry"])
            b = spy.asof(e["exit"])
            spyopp = dep * (b / a - 1)
        rows.append(dict(fam=e["fam"], sym=e["sym"], entry=e["entry"], exit=e["exit"], year=e["exit"].year, dep=dep,
                         pnl=pnl, opp=opp, spyopp=spyopp, ex=pnl - opp, exspy=pnl - spyopp, days=days))
    return pd.DataFrame(rows), maxcap


def tax_year(df, col, rate):
    g = df.groupby("year")[col].sum().reindex(YEARS, fill_value=0.0)
    return g - np.where(g > 0, g * rate, 0.0)


def summarize(df, C, col="ex", rate=0.35, drop5=False):
    if drop5:
        df = df.sort_values(col, ascending=False).iloc[5:]
    at = tax_year(df, col, rate)
    return at


def stats(at, C):
    pp = at / C * 100
    mean = at.sum() / EXPO / C * 100
    return dict(mean=mean, pos=(at > 0).mean(), med=pp.median(), h1=at.loc[2016:2020].sum() / 5 / C * 100,
                h2=at.loc[2021:2026].sum() / 5.75 / C * 100, pp=pp)


def label(mean, pos, ex5):
    if mean >= 8 and pos >= 0.6 and ex5 >= 5:
        return "PASS"
    if mean >= 5:
        return "NEAR"
    return "FAIL"


def run_total(events, C, spy, rate=0.35):
    df, mx = allocate(events, C, spy=spy)
    return df, mx


def main():
    bars = raw_bars(["SPY"], "2015-10-01", "2026-09-30")["SPY"]
    spy = bars.close
    B1 = b1()
    B1c = b1(cash=True)
    B1e = b1(mode="up")
    B2 = b2()
    TD = tenders()
    TDall = tenders(all_prio=True)
    CEF = cef()
    DR = drip()
    TH = thrift()
    say("# Study CPC run (cpc.py)")
    say(f"events: B1 {len(B1)}, B2 {len(B2)}, tender(primary) {len(TD)}, tender(all priority, no floor) {len(TDall)}, "
        f"CEF {len(CEF)}, DRIP {len(DR)}, thrift {len(TH)}")
    b1d = pd.DataFrame(B1)
    byday = b1d.groupby("entry").size()
    say(f"B1 days with > 3 deals: {(byday > 3).sum()} of {len(byday)}")
    prim = {}
    res = {}
    for C in (2300, 10000, 25000):
        say(f"\n## taxable ${C:,}")
        for name, ev_list in [("PRIMARY (B1 rounded E+5)", B1 + B2 + TD + DR), ("B1 cash-in-lieu", B1c + B2 + TD + DR),
                              ("B1 rounded, exit E close", B1e + B2 + TD + DR),
                              ("PRIMARY with tender all-priority (no floor)", B1 + B2 + TDall + DR),
                              ("no B1 at all", B2 + TD + DR)]:
            df, mx = allocate(ev_list, C, spy=spy)
            at = summarize(df, C)
            s = stats(at, C)
            at5 = summarize(df, C, drop5=True)
            s5 = stats(at5, C)
            # SPY-opp variant
            ats = summarize(df, C, col="exspy")
            ss = stats(ats, C)
            lab = label(s["mean"], s["pos"], s5["mean"])
            say(f"{name}: n {len(df)}  mean after-tax excess {s['mean']:+.2f}pp/yr (${s['mean']*C/100:,.0f}/yr)  years>0 {s['pos']:.0%}  "
                f"median yr {s['med']:+.2f}pp  2016-20 {s['h1']:+.2f}  2021-26 {s['h2']:+.2f}  ex-best-5 {s5['mean']:+.2f}  "
                f"[vs SPY {ss['mean']:+.2f}]  max capital ${mx:,.0f}  -> {lab}")
            res[(C, name)] = (df, mx, s, s5, ss)
        df, mx, s, s5, ss = res[(C, "PRIMARY (B1 rounded E+5)")]
        say("by-year after-tax pp (primary): " + "  ".join(f"{y}:{v:+.1f}" for y, v in s["pp"].items()))
        say("per family pre-tax $/yr (primary), events/yr, median capital/event, excess pp:")
        for fam, g in df.groupby("fam"):
            say(f"  {fam:7s} ${g.pnl.sum()/EXPO:9,.0f}/yr  net of T-bill ${g.ex.sum()/EXPO:9,.0f}  {len(g)/EXPO:5.1f} ev/yr  "
                f"median cap ${g.dep.median():9,.2f}  max cap/event ${g.dep.max():9,.0f}  mean/event ${g.pnl.mean():8,.2f}")
        dfbest = df.sort_values("ex", ascending=False).head(5)
        say("best 5 events: " + "; ".join(f"{r.fam}:{r.sym}:{r.entry.date()} ${r.ex:,.0f}" for r in dfbest.itertuples()))
        say("worst 3: " + "; ".join(f"{r.fam}:{r.sym}:{r.entry.date()} ${r.ex:,.0f}" for r in df.sort_values('ex').head(3).itertuples()))
        say(f"share of days in a deal (capital-weighted occupancy): {(df.dep*df.days).sum()/ (EXPO*365*C):.1%} of capital-time")
        if C == 10000:
            prim = df

    # ---- report-only diagnostics (not judged): leave-one-family-out, UMH-only DRIP, 2023-26 window
    say("\n## diagnostics (report-only), taxable, primary scenario, after-tax excess pp/yr")
    DRu = [e for e in DR if e["sym"] == "UMH"]
    for C in (2300, 10000, 25000):
        sets = {"all": B1 + B2 + TD + DR, "ex-DRIP": B1 + B2 + TD, "ex-B2": B1 + TD + DR, "ex-tender": B1 + B2 + DR,
                "ex-B1": B2 + TD + DR, "DRIP UMH-only (forward-like)": B1 + B2 + TD + DRu,
                "DRIP alone": DR, "B2+tender alone": B2 + TD}
        for k, v in sets.items():
            d, mx = allocate(v, C, spy=spy)
            at = summarize(d, C)
            s0 = stats(at, C)
            r2326 = at.loc[2023:2026].sum() / 3.75 / C * 100
            say(f"  ${C:>6,} {k:30s} mean {s0['mean']:+6.2f}  2016-20 {s0['h1']:+6.2f}  2021-26 {s0['h2']:+6.2f}  2023-26 {r2326:+6.2f}  "
                f"yrs>0 {s0['pos']:.0%}  ${at.sum()/EXPO:,.0f}/yr")
    # family totals by year for $10k
    df = prim
    say("\n## family $ by year, $10k, pre-tax net of nothing (primary)")
    pv = df.pivot_table(index="year", columns="fam", values="pnl", aggfunc="sum", fill_value=0).reindex(YEARS, fill_value=0)
    say(pv.round(0).to_string())
    cnt = df.pivot_table(index="year", columns="fam", values="pnl", aggfunc="count", fill_value=0).reindex(YEARS, fill_value=0)
    say("events per year:\n" + cnt.to_string())
    # B1 per account details
    b1only, _ = allocate(B1, 2300, spy=spy)
    b1c, _ = allocate(B1c, 2300, spy=spy)
    say(f"\nB1 per account: rounded ${b1only.pnl.sum()/EXPO:,.0f}/yr (full 10.75y), 2023-26 ${b1only[b1only.year>=2023].pnl.sum()/3.75:,.0f}/yr; "
        f"cash-in-lieu ${b1c.pnl.sum()/EXPO:,.1f}/yr; 2016-20 ${b1only[b1only.year<=2020].pnl.sum()/5:,.0f}/yr; "
        f"E-close exit ${allocate(B1e,2300,spy=spy)[0].pnl.sum()/EXPO:,.0f}/yr")
    pbe = b1only.pnl.sum() / (b1only.pnl.sum() - b1c.pnl.sum()) if len(b1only) else np.nan
    cost_all = -b1c.pnl.sum()
    say(f"B1 break-even P(round): {(-b1c.pnl.sum())/(b1only.pnl.sum()-b1c.pnl.sum()):.2%}")
    # Roth: B1 only, untaxed
    at_roth = b1only.groupby("year").pnl.sum().reindex(YEARS, fill_value=0)
    for C in (2300, 8500):
        say(f"Roth B1-only at ${C:,}: ${at_roth.sum()/EXPO:,.0f}/yr = {at_roth.sum()/EXPO/C*100:+.1f}%/yr untaxed (2023-26 ${at_roth.loc[2023:2026].sum()/3.75:,.0f}/yr)")
    # Roth-venue variant for the 99-share families
    rv, mx = allocate(B2 + TD + B1, 8500, spy=spy)
    rat = rv.groupby("year").pnl.sum().reindex(YEARS, fill_value=0)
    say(f"Roth-venue variant (B1+B2+tender in an $8.5k Roth, untaxed): ${rat.sum()/EXPO:,.0f}/yr = {rat.sum()/EXPO/8500*100:+.1f}%/yr; "
        f"DRIP is taxable-only")
    # separate: CEF, thrift
    for C in (2300, 10000, 25000):
        cf, mx = allocate(CEF, C, spy=spy)
        say(f"CEF tenders (pro-rata, capital-proportional, excluded) ${C:,}: n {len(cf)} pre-tax ${cf.pnl.sum()/EXPO:,.0f}/yr, net of T-bill ${cf.ex.sum()/EXPO:,.0f}/yr, "
            f"max cap ${mx:,.0f}; after-tax {stats(summarize(cf, C), C)['mean']:+.2f}pp")
    for C in (2300, 10000, 25000):
        th, mx = allocate(TH, C, spy=spy)
        thy = th.groupby("year").size()
        two = th.sort_values("pnl").iloc[:0]
        # eligible for 2 deals a year: the median-by-year two
        sel = th.groupby("year", group_keys=False).apply(lambda g: g.sort_values("pnl").iloc[len(g) // 2 - (1 if len(g) > 1 and len(g) % 2 == 0 else 0): len(g) // 2 - (1 if len(g) > 1 and len(g) % 2 == 0 else 0) + 2])
        say(f"Thrift conversions ($2,000 order, pre-positioning required, excluded) ${C:,}: n {len(th)} ({len(th)/EXPO:.1f}/yr) pre-tax ${th.pnl.sum()/EXPO:,.0f}/yr "
            f"(eligible for all listed deals); mean/deal ${th.pnl.mean():,.0f}, hit {(th.pnl>0).mean():.0%}; "
            f"median-2-per-year scenario ${sel.pnl.sum()/EXPO:,.0f}/yr; after-tax all {stats(summarize(th, C), C)['mean']:+.2f}pp; locked $2,000 x 29 days")
    # correlation with live book
    r = pd.read_pickle(P / "program_books_res_rawpool.pkl")
    ho = r[("T", "T0L live today 1.0x cap.10 no conv", "ho")]
    rr = r[("T", "T0L live today 1.0x cap.10 no conv", "tier_hi")]["r"]
    book = pd.concat([ho[ho.index < rr.index[0]], rr]).sort_index()
    bm = (1 + book).groupby(book.index.to_period("M")).prod() - 1
    for C in (2300, 10000):
        d = res[(C, "PRIMARY (B1 rounded E+5)")][0]
        m = d.groupby(d.exit.dt.to_period("M")).pnl.sum()
        idx = bm.index
        x = m.reindex(idx, fill_value=0.0)
        c_all = np.corrcoef(x, bm)[0, 1]
        nb = d[d.fam != "B1"].groupby(d[d.fam != "B1"].exit.dt.to_period("M")).pnl.sum().reindex(idx, fill_value=0.0)
        say(f"monthly corr with live T0L book (n {len(idx)} months, {idx[0]}..{idx[-1]}), ${C:,}: all {c_all:+.3f}, ex-B1 {np.corrcoef(nb, bm)[0,1]:+.3f}")
    # accounts needed
    say("\n## accounts needed (taxable-equivalent $10k each; B1 is per account, the rest per beneficial owner)")
    df10, _ = res[(10000, "PRIMARY (B1 rounded E+5)")][0], 0
    fixed_pre = df10[df10.fam != "B1"].pnl.sum() / EXPO
    fixed_recent = df10[(df10.fam != "B1") & (df10.year >= 2023)].pnl.sum() / 3.75
    b1_full = b1only.pnl.sum() / EXPO
    b1_recent = b1only[b1only.year >= 2023].pnl.sum() / 3.75
    for lab, f, b in [("2016-26 mean", fixed_pre, b1_full), ("2023-26 mean", fixed_recent, b1_recent)]:
        say(f"{lab}: non-B1 ${f:,.0f}/yr pre-tax (${f*0.65:,.0f} after tax) + B1 ${b:,.0f}/account/yr")
        for tgt in (1000, 5000, 10000):
            kt = max(0, math.ceil((tgt - f * 0.65) / (b * 0.65)))
            kr = max(0, math.ceil((tgt - f * 0.65) / b))
            say(f"  after-tax ${tgt:,}/yr: taxable accounts for B1 beyond the one owner's non-B1 stack: {kt}; Roth-type (untaxed) B1 accounts: {kr}")
    OUT.write_text("\n".join(LINES) + "\n")
    df10.to_csv(P / "cpc_ledger_10k.csv", index=False)


if __name__ == "__main__":
    main()
