"""Study HC-BAN (N 911 -> 912): night leg without Healthcare-sector names, budget reallocated within the night.
Pre-reg research/drafts/round1_prose.md "Study HC-BAN". Harness = FUND-STATE (nx daily-bar proxy, delisted-complete). Run once.
  PYTHONPATH=. .venv/bin/python -m research.sim.hc_ban"""
import numpy as np, pandas as pd
from research.sim import shar_surv as ss, nx
OUT = ss.ROOT / "data/research/program/hc_ban_out.txt"
COST = 5e-4
L = []
def P(s=""): print(s); L.append(s)

M = ss.load_master()
key = "permaticker"

def picks(lo, hi):
    bars = ss.load_bars(lo - pd.Timedelta(days=90), hi + pd.Timedelta(days=10))
    pn = nx.build_panel(bars)
    tr = nx.collect_trades(pn, M, ss.load_actions(), "primary", lo, hi)["trades"].copy()
    k = key if key in tr.columns else "ticker"
    sec = M.drop_duplicates(k).set_index(k)["sector"]
    tr["sector"] = tr[k].map(sec)
    return tr

def run(tr, name, judge):
    tr = tr.copy(); tr["r"] = tr.ret - 2 * COST; tr["hc"] = tr.sector.eq("Healthcare")
    base = tr.groupby("date").r.mean()
    ban = tr[~tr.hc].groupby("date").r.mean().reindex(base.index).fillna(0.0)
    dd = ban - base; t = dd.mean() / dd.std(ddof=1) * np.sqrt(len(dd))
    mid = dd.index[len(dd) // 2]; h = (dd[dd.index < mid].mean(), dd[dd.index >= mid].mean())
    ex5 = dd.drop(dd.abs().nlargest(5).index).mean()
    tm = tr.date < mid
    hh = [(tr[m & tr.hc].r.mean(), tr[m & ~tr.hc].r.mean()) for m in (tm, ~tm)]
    P(f"== {name}: picks {len(tr)}, nights {len(base)}, sector coverage {tr.sector.notna().mean()*100:.1f}%, HC share {tr.hc.mean()*100:.1f}%")
    P(f"   HC picks {tr[tr.hc].r.mean()*1e4:+.1f}bp (med {tr[tr.hc].r.median()*1e4:+.1f}) vs non-HC {tr[~tr.hc].r.mean()*1e4:+.1f}bp (med {tr[~tr.hc].r.median()*1e4:+.1f}), net 5bp/side")
    P(f"   halves HC vs non-HC: {hh[0][0]*1e4:+.1f}/{hh[0][1]*1e4:+.1f}  |  {hh[1][0]*1e4:+.1f}/{hh[1][1]*1e4:+.1f}")
    P(f"   per-night ban - base {dd.mean()*1e4:+.2f}bp (t {t:+.2f}, nights {len(dd)}) halves {h[0]*1e4:+.2f}/{h[1]*1e4:+.2f} ex-top5 {ex5*1e4:+.2f}; base {base.mean()*1e4:+.1f} -> ban {ban.mean()*1e4:+.1f}")
    if judge:
        bar = [("diff >= +10bp", dd.mean() >= 1e-3), ("t >= 2.5", t >= 2.5), ("halves > 0", min(h) > 0), ("ex-top-5 > 0", ex5 > 0),
               ("HC < non-HC both halves", all(a < b for a, b in hh))]
        for n_, ok in bar: P(f"   [{'ok' if ok else 'NO'}] {n_}")
        P(f"VERDICT: {'PASS' if all(ok for _, ok in bar) else 'FAIL'}")
    P("")

run(picks(pd.Timestamp("1999-01-04"), pd.Timestamp("2015-12-31")), "JUDGE 1999-2015", True)
run(picks(pd.Timestamp("2016-01-04"), pd.Timestamp("2026-09-18")), "REPORT 2016-26 (touched)", False)
OUT.write_text("\n".join(L))
