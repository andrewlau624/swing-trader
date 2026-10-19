"""TAX-NOWASH (N 1029): TAX-STACK with a wash-sale exclusion. Pre-reg: round1_prose.md "Study TAX-NOWASH".
    PYTHONPATH=. .venv/bin/python -m research.sim.tax_nowash
"""
from __future__ import annotations

import zlib
import numpy as np
import pandas as pd

from . import tax_stack as T
from .roth_stack import ROOT, alloc as _alloc, load_groups
from .validate import load_sim

OUT = ROOT / "data/research/program/tax_nowash_out.txt"  # v2: loss = CAPITAL (price-only) loss; v1 used net-of-dividend return (tax-definition error)
WIN = 31
REC = {}


def _rec_alloc(avail, g, col="co"):
    a = _alloc(avail, g, col); REC["a"] = a; return a


T.alloc = _rec_alloc  # tax_stack.day calls module-level alloc; record what was bought


def issuer(t):
    if "-" in t: return t.split("-")[0]
    return t[:-1] if len(t) >= 4 else t


def key_of(t, mode):
    return t if mode == "S" else issuer(t)


def roth_picks(groups, roth_usd, mode):
    """{d0: set(keys)} the Roth buys (alloc>0) on each night."""
    out = {}
    for d, g in groups.items():
        a = _alloc(roth_usd, g)
        out[d] = {key_of(t, mode) for t, x in zip(g.t.values, a) if x > 0}
    return out


def run(s, N, groups, E, pref_first, margin, rt, mode, roth, part):
    """mode None = no exclusion. roth: {d0:set(keys)} or None. part: 0/1 issuer-hash parity filter or None."""
    rows, tr, nxt = [], [], dict(zip(s.days[:-1], s.days[1:]))
    lastloss = {}
    for d in s.days:
        g = groups.get(d)
        removed = total = 0
        if g is not None:
            total = len(g)
            if part is not None:
                g = g[[zlib.crc32(issuer(t).encode()) % 2 == part for t in g.t.values]].reset_index(drop=True)
            if mode is not None and len(g):
                keep = [not (key_of(t, mode) in lastloss and (d - lastloss[key_of(t, mode)]).days <= WIN) for t in g.t.values]
                removed = len(g) - sum(keep)
                g = g[keep].reset_index(drop=True)
            if not len(g): g = None
        REC.pop("a", None)
        pnl, pp, intr, lost, divu, ev = T.day(s, N, E, d, "tier", pref_first, g, margin, rt, (nxt[d] - d).days if d in nxt else 1)
        rows.append((pnl, pp, intr, lost, divu))
        a = REC.get("a")
        if g is not None and a is not None:
            for j in np.nonzero(a)[0]:
                r = g.co.values[j] - rt; cap = r - g.dy.values[j]; k = key_of(g.t.values[j], mode or "S")
                sale = pd.Timestamp(g.d.values[j])
                tr.append((k, d, sale, a[j], a[j] * cap, r, g.t.values[j], cap))
                if cap < 0 and mode is not None: lastloss[key_of(g.t.values[j], mode)] = sale
        tr_removed.append((removed, total))
    r = pd.DataFrame(rows, columns=["book", "pref", "intr", "lost", "div"], index=pd.Index(s.days)) / E
    return r, pd.DataFrame(tr, columns=["k", "buy", "sale", "usd", "pnl", "ret", "t", "cap"])


def washed(tr, mode, roth_set):
    """Series flag per trade: loss with another taxable buy of key within +-30d of sale (residual), or a Roth buy within +-30d."""
    w = np.zeros(len(tr), bool)
    wr = np.zeros(len(tr), bool)
    by = {k: g for k, g in tr.groupby("k")}
    for i, row in enumerate(tr.itertuples()):
        if row.cap >= 0: continue
        g = by[row.k]
        oth = g[(g.buy != row.buy) & ((g.buy - row.sale).abs().dt.days <= 30)]
        w[i] = len(oth) > 0
        if roth_set is not None:
            for dd, ks in roth_set.items():
                pass
    return w


tr_removed = []


def main():
    s = load_sim(raw_price=True); N = s.N; s.days = list(s.days)
    groups = load_groups()
    for k, g in groups.items():
        if "d" not in g: raise SystemExit("group lacks d")
    divs = pd.concat([pd.read_parquet(ROOT / f"data/research/{x}/events.parquet")[["ticker", "date", "div", "pc"]].rename(columns={"ticker": "t", "date": "d"}).drop_duplicates(["t", "d"]) for x in ("pref", "etdx")])
    for k, g in groups.items():
        m = g.merge(divs[["t", "d", "div"]], on=["t", "d"], how="left"); g["dy"] = m["div"].fillna(0).values / g.pc.values
    ix = pd.DatetimeIndex(s.days); yrs = (ix[-1] - ix[0]).days / 365.25
    h1 = ix < "2024-01-01"; h2 = ~h1
    L = [f"TAX-NOWASH N 1029: TAX-STACK + wash exclusion ({WIN}d), tax {T.TAX:.0%}; residual-washed losses get no offset (deferral treated as permanent: conservative)",
         f"book days {ix[0].date()}..{ix[-1].date()}; yrs {yrs:.2f}; groups events {sum(len(g) for g in groups.values())}"]
    def a_(x): return x.sum() / yrs * 100
    def hv(x, h): return x[h].sum() / ((x.index[h][-1] - x.index[h][0]).days / 365.25) * 100
    roth = {m: roth_picks(groups, 3000.0, m) for m in ("S", "I")}
    arms = [("CASH night-first", False, False), ("CASH pref-first", True, False), ("MARGIN 2x", False, True)]
    # scenarios: (label, mode, roth_on, part)
    scen = [("BASELINE none, realistic wash", None, False, None), ("S no-Roth", "S", False, None), ("I no-Roth", "I", False, None),
            ("S ROTH-CONCURRENT", "S", True, None), ("I ROTH-CONCURRENT", "I", True, None), ("I DISJOINT (taxable even issuers)", "I", False, 0)]
    for E in (2300.0, 10000.0, 25000.0):
        L.append(f"\n== equity ${E:,.0f} ==")
        base, _ = T.run(s, N, groups, E, "tier", False, False, pref=False)
        for nm, pf, mg in arms:
            for lab, mode, rothon, part in scen:
                res = {}
                for rt in (0.0010, 0.0030):
                    tr_removed.clear()
                    r, tr = run(s, N, groups, E, pf, mg, rt, mode, None, part)
                    res[rt] = (r, tr, list(tr_removed))
                r, tr, rem = res[0.0010]
                def tax(r, tr):
                    pre = r.pref - r.intr - r.lost + (r.book - base.book)
                    t1 = (1 - T.TAX) * pre
                    if not len(tr): return pre, t1
                    w = washed(tr, mode, None)
                    if rothon:
                        rs = roth[mode]
                        rb = []
                        for row in tr.itertuples():
                            hit = False
                            for dd in rs:
                                if abs((dd - row.sale).days) <= 30 and row.k in rs[dd]: hit = True; break
                            rb.append(hit)
                        w = w | np.array(rb)
                    wl = tr[w & (tr.cap < 0)].groupby("buy").pnl.sum() / E     # negative
                    wl = wl.reindex(r.index).fillna(0.0)
                    return pre, t1 + T.TAX * wl, w
                out = tax(r, tr); pre, t1 = out[0], out[1]
                out3 = tax(res[0.0030][0], res[0.0030][1]); t13 = out3[1]
                nrem = sum(x for x, _ in rem); ntot = sum(y for _, y in rem)
                nloss = int((tr.cap < 0).sum()) if len(tr) else 0
                nw = int((out[2] & (tr.cap.values < 0)).sum()) if len(tr) and len(out) > 2 else 0
                L.append(f"{nm:17s} {lab:34s}: pre {a_(pre):+5.1f} | afterA* {a_(t1):+5.1f} (halves {hv(t1,h1):+5.1f}/{hv(t1,h2):+5.1f}) | 3x afterA* {a_(t13):+5.1f} | "
                         f"trades {len(tr)}, losses {nloss}, washed-losses {nw} | rows removed by rule {nrem}/{ntot} ({nrem/max(ntot,1)*100:.0f}% of candidate rows)")
    OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
