"""Track C: passive (buy limit at NBB) entry vs aggressive (pay ask), after adverse selection.
Uses only cached Alpaca SIP samples from scalp_cost_alpaca.py (loaders/filters reused). No orders, no network.
Fill: pess = lit regular trade strictly < P (last in queue); opt = lit trade <= P. P fixed at the decision NBB (no chase). Window 10 min.
Markout_h = mid(fill+h) - P (bp of P), last available quote if fill+h is past the sample end. Eff passive cost_h = -markout + exit half-spread at fill+h.
Aggressive: buy ask at decision, exit at bid at t0+h: cost_h = (ask0 - mid(t0+h))/mid0 + exit half-spread (includes drift, same convention).
Run: python -m research.sim.scalp_passive"""
import json, glob
from pathlib import Path
import numpy as np, pandas as pd
from .scalp_cost_alpaca import SAM, qdf, TOD, REG, BUCKETS, ETFS
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "data/research/program/scalp_passive_out.txt"
HS = [1, 5, 15]; WIN = 10

def one(f):
    r = json.loads(Path(f).read_text()); t0 = pd.Timestamp(r["t0"]).tz_convert("UTC"); t1 = t0 + pd.Timedelta(minutes=30)
    if not r["pq"] or not r["q"] or not r["tr"]: return None
    pt, pb, pa = r["pq"]; mid0 = (pb + pa) / 2; P = pb
    q = qdf([dict(t=a, bp=b, ap=c) for a, b, c in r["q"]])
    tr = pd.DataFrame(r["tr"], columns=["t", "p", "s", "x", "c"]); tr["t"] = pd.to_datetime(tr.t, utc=True, format="ISO8601")
    end = t1
    if r["qcap"]: end = min(end, q.t.iloc[-1])
    if r["tcap"]: end = min(end, tr.t.iloc[-1])
    q = q[q.t <= end]; tr = tr[(tr.t >= t0) & (tr.t <= end)]
    if q.empty or tr.empty: return None
    hz = (end - t0).total_seconds() / 60
    if hz < WIN - 0.05: return None  # fill window not fully observed
    lit = tr[(tr.x != "D") & tr.c.map(lambda s: all(ch in REG for ch in s))].sort_values("t")
    w = lit[lit.t <= t0 + pd.Timedelta(minutes=WIN)]
    mq = ((q.bp + q.ap) / 2).values; hq = ((q.ap - q.bp) / 2 / ((q.bp + q.ap) / 2) * 1e4).values; qt = q.t.values
    def at(t):  # last quote at/before t (else decision quote)
        i = np.searchsorted(qt, np.datetime64(t.tz_convert("UTC").tz_localize(None)), side="right") - 1
        return (mid0, (pa - pb) / 2 / mid0 * 1e4) if i < 0 else (mq[i], hq[i])
    o = dict(date=r["date"], sym=r["sym"], bucket=r["bucket"], tod=r["tod"], year=r["date"][:4], hz=hz, mid0=mid0)
    for h in HS:
        tt = min(t0 + pd.Timedelta(minutes=h), end); m, hh = at(tt)
        o[f"drift{h}"] = (m - mid0) / mid0 * 1e4                      # unconditional mid drift from t0
        o[f"agg{h}"] = (pa - m) / mid0 * 1e4 + hh                     # aggressive eff cost incl. drift
    o["agg_clean"] = (pa - mid0) / mid0 * 1e4 + (pa - pb) / 2 / mid0 * 1e4
    for nm, hit in (("pess", w[w.p < P]), ("opt", w[w.p <= P])):
        o[f"fill_{nm}"] = len(hit) > 0
        if len(hit):
            tf = hit.t.iloc[0]; o[f"tf_{nm}"] = (tf - t0).total_seconds()
            for h in HS:
                tt = min(tf + pd.Timedelta(minutes=h), end); m, hh = at(tt)
                o[f"mo_{nm}{h}"] = (m - P) / P * 1e4; o[f"pc_{nm}{h}"] = -o[f"mo_{nm}{h}"] + hh
                # unconditional drift over the same absolute window [tf, tf+h] (adverse-selection reference = mid drift from tf)
                m_f, _ = at(tf); o[f"fdrift_{nm}{h}"] = (m - m_f) / m_f * 1e4
    return o

def main():
    rows = [x for x in (one(f) for f in sorted(glob.glob(str(SAM / "*.json")))) if x]
    df = pd.DataFrame(rows)
    df["grp"] = np.where(df.sym.isin(ETFS), "ETF", df.bucket)
    L = []; p = lambda s="": L.append(s)
    p(f"Scalp passive entry (buy limit at NBB) vs aggressive (pay ask). Samples with full 10-min fill window: {len(df)}. bp; means unless stated.")
    p("pess = lit trade strictly < P; opt = lit trade <= P; no chase; fill window 10m. mo_h = mid(fill+h)-P. pcost_h = -mo_h + exit half-spread. aggM_h = aggressive cost (ask0 vs mid(t0+h) + exit hs) on the SAME filled samples.")
    p("AS_h = mean mid move fill->fill+h (filled) minus mean mid move t0->t0+h (all samples in cell). aggM is biased high (filled set is selected on a down-move); the drift-neutral aggressive comparator is aggClean (= full spread, no drift).\n")
    def table(d, title):
        p(f"== {title}")
        hdr = f"{'grp':10}{'n':>5} {'fillP':>6}{'fillO':>6} {'tfP_s':>6} | " + " ".join(f"{'moP'+str(h):>7}" for h in HS) + " | " + " ".join(f"{'pcP'+str(h):>7}{'aggM'+str(h):>7}" for h in HS) + " | " + " ".join(f"{'AS'+str(h):>6}" for h in HS) + " | " + " ".join(f"{'pcO'+str(h):>7}" for h in HS) + f" | {'aggClean':>8}"
        p(hdr)
        for g, x in d.groupby("grp", sort=True):
            fp = x[x.fill_pess == True]; fo = x[x.fill_opt == True]
            def m(s, c): return s[c].mean() if c in s and len(s) else np.nan
            cells = [f"{g:10}{len(x):5d} {x.fill_pess.mean():6.2f}{x.fill_opt.mean():6.2f} {fp.tf_pess.median() if len(fp) else np.nan:6.0f} | "]
            cells.append(" ".join(f"{m(fp,f'mo_pess{h}'):7.1f}" for h in HS) + " | ")
            for h in HS:
                a = fp[f"agg{h}"].mean() if len(fp) else np.nan
                cells.append(f"{m(fp,f'pc_pess{h}'):7.1f}{a:7.1f}")
            cells.append(" | " + " ".join(f"{(m(fp,f'fdrift_pess{h}') - x[f'drift{h}'].mean()):6.1f}" for h in HS) + " | ")
            cells.append(" ".join(f"{m(fo,f'pc_opt{h}'):7.1f}" for h in HS) + f" | {x.agg_clean.mean():8.1f}")
            p(" ".join(cells) if False else "".join(cells))
        p()
    for y in ["2018", "2025"]:
        table(df[df.year == y], f"{y} all time-of-day")
    mid = df[df.tod.isin(["1030-1200", "1200-1400"]) & df.grp.isin(["A>1B", "ETF"])]
    for y in ["2018", "2025"]:
        table(mid[mid.year == y], f"{y} midday 10:30-14:00 (tod buckets 1030-1200,1200-1400), A>1B and ETF only")
    p("== unfilled vs filled unconditional mid drift from t0 (pessimistic), bp; positive for unfilled = price ran away from the bid")
    p(f"{'grp':10}{'yr':>5}{'nUnf':>6}{'nFil':>6} " + " ".join(f"{'unf'+str(h):>7}{'fil'+str(h):>7}" for h in HS))
    for (y, g), x in df.groupby(["year", "grp"]):
        u = x[x.fill_pess == False]; f_ = x[x.fill_pess == True]
        p(f"{g:10}{y:>5}{len(u):6d}{len(f_):6d} " + " ".join(f"{u[f'drift{h}'].mean():7.1f}{f_[f'drift{h}'].mean():7.1f}" for h in HS))
    p("\n== medians, pooled by year (pess fills): pcost5 passive / aggM5 aggressive")
    for (y, g), x in df.groupby(["year", "grp"]):
        fp = x[x.fill_pess == True]
        if len(fp): p(f"{g:10}{y:>5} n_fill {len(fp):4d}  pc5 med {fp.pc_pess5.median():7.1f}  agg5 med {fp.agg5.median():7.1f}  agg_clean(all) med {x.agg_clean.median():6.1f}")
    p("\nNotes: odd-lot (' I') and TRF (x='D') prints excluded from fills (conservative). Sample size per cell ~70-100; CIs wide. Exit = market sell at bid at h; mid is last quote <= time.")
    OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))

if __name__ == "__main__": main()
