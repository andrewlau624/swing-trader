"""Round 20: PREF-EX ex-night capture split by the prior 10-session window (avoid-screen test)."""
import sys, numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
CONF = "--confirm" in sys.argv
t = w.load_panel(kind="pref")
g = t.groupby("ticker", sort=False)
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[a.action == "dividend"].copy(); a["date"] = pd.to_datetime(a.date)
t = t.merge(a[["ticker", "date", "value"]].drop_duplicates(["ticker", "date"]), on=["ticker", "date"], how="left")
g = t.groupby("ticker", sort=False)
pc = g["closeunadj"].shift(1)                                   # T-1 close (raw)
t["cc"] = (t.closeunadj + t.value) / pc - 1
t["pre10"] = pc / g["closeunadj"].shift(11) - 1                 # T-11 -> T-1
f4 = list(F.F4(t).values())[0]
t["f4prev"] = f4.groupby(t.ticker, sort=False).shift(1)         # oversold cross known at T-1 close
liqprev = g["liq"].shift(1).fillna(False).astype(bool)
ev = t[t.value.notna() & liqprev & (t.value / pc < 0.25) & t.cc.notna() & t.pre10.notna()].copy()
lo, hi = ("2005-01-01", "2015-12-31") if CONF else ("2016-01-01", "2026-09-30")
ev = ev[(ev.date >= lo) & (ev.date <= hi)]
lines = [f"R20 {'CONFIRM ' if CONF else ''}{lo[:4]}-{hi[:4]} PREF-EX CC events {len(ev)}: mean {ev.cc.mean()*1e4:+.1f}bp med {ev.cc.median()*1e4:+.1f}"]
def split(lab, A, B):
    da = ev[A].groupby("date").cc.mean(); db = ev[B].groupby("date").cc.mean(); d = (da - db).dropna()
    tt = d.mean() / (d.std() / np.sqrt(len(d))) if len(d) > 5 else np.nan
    mid = d.index[len(d)//2] if len(d) else ev.date.median()
    h = (d[d.index < mid].mean()*1e4, d[d.index >= mid].mean()*1e4)
    ok = d.mean()*1e4 <= -15 and tt <= -2.5 and h[0] < 0 and h[1] < 0
    lines.append(f"  {lab:34} A n {int(A.sum()):6} {ev[A].cc.mean()*1e4:+6.1f}bp med {ev[A].cc.median()*1e4:+5.1f} | B n {int(B.sum()):6} {ev[B].cc.mean()*1e4:+6.1f} med {ev[B].cc.median()*1e4:+5.1f}"
                 f" | paired {d.mean()*1e4:+6.1f} (t {tt:+4.1f}, days {len(d)}) halves {h[0]:+6.1f}/{h[1]:+6.1f} -> {'PASS' if ok else 'fail'}")
split("prior 10d <= -3% vs > -3%", ev.pre10 <= -0.03, ev.pre10 > -0.03)
split("diag: F4 oversold at T-1 vs not", ev.f4prev.fillna(False).astype(bool), ~ev.f4prev.fillna(False).astype(bool))
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 20 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
