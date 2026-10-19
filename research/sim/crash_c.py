"""Study CRASH-C (N 1026): CEF discount blowout in a >=20% SPY drawdown. Pre-reg in round1_prose.md."""
from __future__ import annotations
import pathlib, sys
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.cef_peer import category  # noqa: E402

STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = ROOT / "data" / "research" / "program" / "crash_c_out.txt"
lines: list[str] = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); lines.append(s)

COST_RT, WIDEN, DD = 0.010, 3.0, 0.20

def main():
    p = pd.read_parquet(ROOT / "data/research/cefconnect/cef_panel.parquet")
    p["date"] = pd.to_datetime(p["date"]); p = p.dropna(subset=["price", "nav"])
    p = p[(p.price > 0) & (p.nav > 0)].copy()
    p["disc"] = (p.price / p.nav - 1) * 100
    names = p.drop_duplicates("ticker").set_index("ticker")["name"]
    cat = names.map(category)
    tk = sorted(p.ticker.unique())
    f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "closeadj", "closeunadj"],
                        filters=[("ticker", "in", tk + ["SPY"])])
    f["date"] = pd.to_datetime(f["date"]); f = f.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"])
    f["af"] = f.closeadj / f.closeunadj
    spy = f[f.ticker == "SPY"].set_index("date")["closeadj"]
    dd = spy / spy.rolling(252, min_periods=200).max() - 1
    fd = {t: g.set_index("date") for t, g in f.groupby("ticker")}

    wk = p.pivot_table(index="date", columns="ticker", values="disc")
    med = wk.median(axis=1); med52 = med.rolling(52, min_periods=40).median()
    widen = med - med52
    z = wk - wk.rolling(52, min_periods=40).median()
    say("Study CRASH-C (N 1026): CEF blowout in SPY drawdown. pre-reg round1_prose.md")
    say(f"panel weeks {wk.index.min().date()}..{wk.index.max().date()}, funds {len(tk)} (LIVE only)")
    fires, last = [], None
    for d in wk.index:
        i = spy.index.searchsorted(d, side="right") - 1
        if i < 0 or not np.isfinite(dd.iloc[i]): continue
        if last is not None and (d - last).days < 364: continue
        if dd.iloc[i] <= -DD and widen.get(d, np.nan) <= -WIDEN:
            fires.append(d); last = d
    say("fires:", [str(d.date()) for d in fires])
    for d in fires:
        i = spy.index.searchsorted(d, side="right") - 1
        say(f"  {d.date()} SPY dd {dd.iloc[i]*100:.1f}%  EW med disc {med[d]:.1f} vs 52w med {med52[d]:.1f}")

    def px_at(t, d, side):
        g = fd.get(t)
        if g is None: return None
        pos = g.index.searchsorted(d, side=side)
        if side == "left": pos -= 0
        if side == "right" and pos >= len(g): return None
        if side == "left": pos = g.index.searchsorted(d, side="left")
        if pos >= len(g) or (g.index[pos] - d).days > 10: return None
        return g.index[pos], g.iloc[pos]

    for ep in fires:
        say(f"\n=== episode {ep.date()} ===")
        zz = z.loc[ep].dropna()
        hist = wk.loc[:ep].notna().sum()
        zz = zz[hist.reindex(zz.index) >= 52]
        sel = zz[zz <= zz.quantile(0.10)].index.tolist()
        say(f"selected {len(sel)} of {len(zz)}; mean z {zz[sel].mean():.1f} pts; cats {cat.reindex(sel).value_counts().to_dict()}")
        pre_med = wk.loc[:ep].tail(52).median()
        rows = []
        for tr in (0, 4, 8):
            sig = wk.index[wk.index.get_loc(ep) + tr] if wk.index.get_loc(ep) + tr < len(wk.index) else None
            if sig is None: continue
            for t in zz.index:  # all funds (comparators + selected)
                e = px_at(t, sig, "right")
                if e is None: continue
                ed, er = e
                w = wk.loc[sig:, t].dropna()
                xd = None
                for d2 in w.index[1:]:
                    if w[d2] >= pre_med[t] or (d2 - sig).days > 260:
                        xd = d2; break
                if xd is None: xd = w.index[-1] if len(w) and (w.index[-1]-sig).days>=260 else None
                if xd is None: continue
                x = px_at(t, xd, "right")
                if x is None: continue
                xdate, xr = x
                pr = xr.closeadj / er.closeadj - 1
                navr = p[(p.ticker == t)].set_index("date")["nav"]
                if sig not in navr.index or xd not in navr.index: continue
                nav_tr = navr[xd] / navr[sig] * (xr.af / er.af) - 1
                sp0 = spy.iloc[spy.index.searchsorted(ed)]; sp1 = spy.iloc[min(spy.index.searchsorted(xdate), len(spy)-1)]
                rows.append(dict(t=t, tr=tr, sel=t in sel, cat=cat[t], pr=pr, nav=nav_tr, spy=sp1 / sp0 - 1,
                                 hold=(xdate - ed).days, edate=ed))
        r = pd.DataFrame(rows)
        if r.empty: say("no trades"); continue
        catnav = r.groupby(["cat", "tr"])["nav"].mean().rename("catnav")
        r = r.join(catnav, on=["cat", "tr"])
        r["wedge"] = r.pr - r.nav
        r["exc"] = r.pr - r.catnav
        s = r[r.sel]
        say(f"trades {len(s)} selected / {len(r)} universe; mean hold {s.hold.mean():.0f}d")
        per = s.groupby("t")[["pr", "nav", "wedge", "exc", "spy"]].mean()
        def rep(label, df):
            if df.empty: say(f"  {label}: n=0"); return None
            x = df.exc.values; o = np.sort(x)[::-1]
            ex5 = o[5:].mean() if len(o) > 5 else float("nan")
            say(f"  {label}: n {len(df)} priceTR {df.pr.mean()*100:+.1f}% navTR {df.nav.mean()*100:+.1f}% wedge {df.wedge.mean()*100:+.1f}% | excess vs cat-NAV "
                f"gross mean {x.mean()*100:+.1f}% median {np.median(x)*100:+.1f}% ex-top5 {ex5*100:+.1f}% | net1x {(x.mean()-COST_RT)*100:+.1f}% net2x {(x.mean()-2*COST_RT)*100:+.1f}% | SPY {df.spy.mean()*100:+.1f}% hit {np.mean(x>0)*100:.0f}%")
            return (x.mean()-COST_RT, np.median(x), ex5, x.mean()-2*COST_RT)
        res = rep("selected decile (all)", per)
        for sub, cats in (("levered proxy", {"muni", "taxable_fi", "pref_conv"}),):
            rep(sub, per[cat.reindex(per.index).isin(cats).values])
        for tr_ in (0, 4, 8):
            q = s[s.tr == tr_].groupby("t")[["pr", "nav", "wedge", "exc", "spy"]].mean()
            rep(f"  tranche +{tr_}w", q)
        u = r.groupby("t")[["pr", "nav", "wedge", "exc", "spy"]].mean()
        say(f"  universe EW (all panel funds): priceTR {u.pr.mean()*100:+.1f}% navTR {u.nav.mean()*100:+.1f}% wedge {u.wedge.mean()*100:+.1f}%")
        if res:
            ok = res[0] >= .10 and res[1] > 0 and res[2] > 0 and res[3] >= .10
            say(f"  GATE episode: net1x>=10 {res[0]>=.1}, median>0 {res[1]>0}, ex5>0 {res[2]>0}, net2x>=10 {res[3]>=.1} -> {'PASS' if ok else 'FAIL'}")
    OUT.write_text("\n".join(lines) + "\n")

main()
