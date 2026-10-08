"""Round 6: window states on the night rule's own picks (L1 repeat loser, L2 3-day slide, L3 sector crowding)."""
import numpy as np, pandas as pd
from research.sim import shar_surv as ss, nx, winsig_fam as F
LO, HI = pd.Timestamp("2016-01-04"), pd.Timestamp("2026-09-18")
bars = ss.load_bars(pd.Timestamp("2015-10-01"), pd.Timestamp("2026-09-25"))
pn = nx.build_panel(bars)
tr = nx.collect_trades(pn, ss.load_master(), ss.load_actions(), "primary", LO, HI)["trades"]
c = bars["close"].to_numpy(float); code = pn["code"]
i = tr["row"].astype(int).to_numpy()
ok = lambda k: (i - k >= 0) & (code[np.maximum(i - k, 0)] == code[i])
tr["slide"] = ok(3) & (c[i - 1] < c[i - 2]) & (c[i - 2] < c[i - 3])
tr["fresh"] = ok(2) & (c[i - 1] > c[i - 2])
sess = np.sort(tr.date.unique()); sidx = {d: k for k, d in enumerate(sess)}
tr["sk"] = tr.date.map(sidx)
seen = {}
rep = []
for tk, sk in zip(tr.ticker, tr.sk):
    rep.append(tk in seen and sk - seen[tk] <= 5 and sk > seen[tk]); seen[tk] = sk
# repeat computed in date order
tr = tr.sort_values(["date"]).reset_index(drop=True)
seen = {}; rep = []
for tk, sk in zip(tr.ticker, tr.sk):
    rep.append(tk in seen and 0 < sk - seen[tk] <= 5); seen[tk] = sk
tr["repeat"] = rep
tk = pd.read_parquet(ss.STORES / "tickers.parquet", columns=["table", "ticker", "famaindustry"])
tr["ind"] = tr.ticker.map(tk[tk.table == "SEP"].drop_duplicates("ticker").set_index("ticker").famaindustry).fillna("NA")
tr["crowd"] = tr.groupby(["date", "ind"]).ticker.transform("size")
tr["d"] = tr.ret - tr.groupby("date").ret.transform("mean")
lines = [f"night picks 2016-26 (daily-bar proxy): n {len(tr)}, nights {tr.date.nunique()}, mean overnight {tr.ret.mean()*1e4:+.1f}bp"]
def split(lab, a, b):
    da = tr[a].groupby("date").ret.mean(); db = tr[b].groupby("date").ret.mean(); d = (da - db).dropna()
    tt = d.mean() / (d.std() / np.sqrt(len(d))) if len(d) > 5 else np.nan
    mid = d.index[len(d)//2] if len(d) else None
    h = (d[d.index < mid].mean()*1e4, d[d.index >= mid].mean()*1e4) if len(d) else (np.nan, np.nan)
    md = tr[a].d.median() - tr[b].d.median()
    okk = abs(d.mean())*1e4 >= 30 and abs(tt) >= 2.5 and np.sign(h[0]) == np.sign(h[1]) == np.sign(d.mean()) == np.sign(md)
    lines.append(f"{lab:44} A n {int(a.sum()):5} {tr[a].ret.mean()*1e4:+6.1f}bp med {tr[a].ret.median()*1e4:+5.1f} | B n {int(b.sum()):5} {tr[b].ret.mean()*1e4:+6.1f}bp med {tr[b].ret.median()*1e4:+5.1f}"
                 f" | paired A-B {d.mean()*1e4:+6.1f} (t {tt:+4.1f}, nights {len(d)}) halves {h[0]:+6.1f}/{h[1]:+6.1f} med-diff {md*1e4:+5.1f} -> {'PASS' if okk else 'fail'}")
split("L1 repeat loser (picked <=5 sessions ago)", tr.repeat, ~tr.repeat)
split("L2 3-day slide vs fresh drop after up day", tr.slide, tr.fresh)
split("L3 >=3 picks same industry vs alone", tr.crowd >= 3, tr.crowd == 1)
# L3 extra: whole-night outcome for crowded nights (the portfolio-level risk the sector cap targets)
nt = tr.groupby("date").agg(n=("ret", "size"), mx=("crowd", "max"), r=("ret", "mean"), sd=("ret", "std"))
for lab, m in (("nights with an industry cluster >= 3", nt.mx >= 3), ("nights without", nt.mx < 3)):
    s = nt[m & (nt.n >= 3)]
    lines.append(f"  L3 portfolio view, {lab:36}: nights {len(s)}, EW night {s.r.mean()*1e4:+.1f}bp, sd of night EW {s.r.std()*1e4:.0f}bp, worst {s.r.min()*1e4:+.0f}bp, 5th pct {s.r.quantile(.05)*1e4:+.0f}bp")
tr.to_parquet(w_cache := (ss.ROOT / "data" / "research" / "winsig" / "night_picks_l.parquet"))
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 6 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
