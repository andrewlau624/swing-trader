"""Round 8: falsification checks on L1 repeat-loser (uses the Round 6 picks parquet)."""
import numpy as np, pandas as pd
from research.sim import winsig_fam as F
tr = pd.read_parquet(F.w.CACHE / "night_picks_l.parquet").sort_values("date").reset_index(drop=True)
last = {}; gap = []
for tk, sk in zip(tr.ticker, tr.sk):
    gap.append(sk - last[tk] if tk in last and sk > last[tk] else np.nan); last[tk] = sk
tr["gap"] = gap
lines = []
def paired(a, b):
    da = tr[a].groupby("date").ret.mean(); db = tr[b].groupby("date").ret.mean(); d = (da - db).dropna()
    return d.mean()*1e4, d.mean()/(d.std()/np.sqrt(len(d))) if len(d) > 5 else np.nan, len(d)
none = tr.gap.isna() | (tr.gap > 20)
for lab, m in (("1", tr.gap == 1), ("2-3", tr.gap.between(2, 3)), ("4-5", tr.gap.between(4, 5)), ("6-20", tr.gap.between(6, 20))):
    p = paired(m, none)
    lines.append(f"P1 gap {lab:5}: n {int(m.sum()):5} mean {tr[m].ret.mean()*1e4:+6.1f} med {tr[m].ret.median()*1e4:+5.1f} | vs none paired {p[0]:+6.1f} (t {p[1]:+4.1f}, nights {p[2]})")
lines.append(f"P1 none (>20 or never): n {int(none.sum())} mean {tr[none].ret.mean()*1e4:+.1f} med {tr[none].ret.median()*1e4:+.1f}")
A = tr.gap <= 5; B = ~A
for col, lab in (("cu", "price"), ("vol20", "vol20")):
    q = pd.qcut(tr[col], 3, labels=["lo", "mid", "hi"])
    for k in ["lo", "mid", "hi"]:
        p = paired(A & (q == k), B & (q == k))
        lines.append(f"P2 {lab} tercile {k:3}: A n {int((A&(q==k)).sum()):5} {tr[A&(q==k)].ret.mean()*1e4:+6.1f} | B {tr[B&(q==k)].ret.mean()*1e4:+6.1f} | paired {p[0]:+6.1f} (t {p[1]:+4.1f})")
ex = ~(tr.date.between("2020-03-01", "2020-06-30") | tr.date.between("2021-01-01", "2021-03-31"))
p = paired(A & ex, B & ex)
lines.append(f"P3 ex 2020-03..06 & 2021-01..03: paired {p[0]:+.1f} (t {p[1]:+.1f}, nights {p[2]})")
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 8 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
