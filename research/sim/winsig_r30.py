"""Round 30: PREF-CHAIN capacity/concurrency at $2-25k."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
p = w.load_panel(kind="pref"); g = p.groupby("ticker", sort=False)
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(p.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
keep = (P.notna().all(axis=1) & ((P.max(axis=1) / P.min(axis=1) - 1) <= 0.02)) & ((a.value / P.median(axis=1) - 1).abs() < 0.10)
p["d10"] = g["date"].shift(10); p["adv10"] = g["adv20"].shift(10); p["px10"] = g["closeunadj"].shift(10); p["liq10"] = g["liq"].shift(10)
ev = a[keep].merge(p[["ticker", "date", "liq", "d10", "adv10", "px10"]], on=["ticker", "date"])
ev = ev[ev.liq & (ev.date >= "2021-01-01") & (ev.date <= "2026-09-30")].dropna()
days = pd.bdate_range("2021-01-04", "2026-09-30")
open_ = pd.Series(0, index=days)
for s, e in zip(ev.d10, ev.date):
    open_[(open_.index >= s) & (open_.index < e)] += 1
lines = [f"R30 PREF-CHAIN 2021-26: {len(ev)} events ({len(ev)/5.75:.0f}/yr) | open windows per day: median {open_.median():.0f}, 10th pct {open_.quantile(.1):.0f}, 90th {open_.quantile(.9):.0f}",
         f"   entry $ADV (20d): median ${ev.adv10.median()/1e3:.0f}k, 25th pct ${ev.adv10.quantile(.25)/1e3:.0f}k | a $500 position = {500/ev.adv10.median():.2%} of median daily $vol, $1,000 = {1000/ev.adv10.median():.2%}",
         f"   entry price median ${ev.px10.median():.2f} (whole shares: $25 lots, no rounding problem)",
         f"   capital at $10k with 20 slots of $500: always full if median open windows >= 20 -> {'yes' if open_.median() >= 20 else 'no'}"]
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 30 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
