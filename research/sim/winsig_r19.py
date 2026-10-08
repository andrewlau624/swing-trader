"""Round 19 audit: ex-dividend days that would fake the night leg's -8% signal on unadjusted closes."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
t = w.load_panel()
g = t.groupby("ticker", sort=False)
raw = t.close / g["close"].shift(1) - 1                 # split-adjusted, NOT dividend-adjusted (Sharadar close)
adj = t.closeadj / g["closeadj"].shift(1) - 1           # total return
co = g["open"].shift(-1) * (t.closeadj / t.close).groupby(t.ticker, sort=False).shift(-1) / t.closeadj - 1
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[a.action == "dividend"]; a["date"] = pd.to_datetime(a.date)
div = t.merge(a[["ticker", "date", "value"]], on=["ticker", "date"], how="left")["value"].to_numpy()
t["divpct"] = div / g["closeunadj"].shift(1).to_numpy()
win = (t.date >= "2016-01-01") & (t.closeunadj >= 5)
fake = win & (raw <= -0.08) & (adj > -0.08) & (t.divpct >= 0.03)
real = win & (adj <= -0.08)
lines = [f"R19 2016-26: days with raw <= -8% but total-return > -8% due to an ex-div >= 3%: {int(fake.sum())} "
         f"({int(fake.sum())/10.7:.1f}/yr); real -8% days: {int(real.sum())}",
         f"   fake-signal names overnight (close->open, total return): mean {co[fake].mean()*1e4:+.1f}bp med {co[fake].median()*1e4:+.1f}; "
         f"real -8% days overnight mean {co[real].mean()*1e4:+.1f}bp"]
ex = t.loc[fake, ["ticker", "date", "divpct"]].assign(raw=raw[fake].round(3), adj=adj[fake].round(3)).tail(8)
lines.append("   recent fakes: " + "; ".join(f"{r.ticker} {str(r.date)[:10]} div {r.divpct:.0%} raw {r.raw:+.0%} adj {r.adj:+.0%}" for r in ex.itertuples()))
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 19 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
