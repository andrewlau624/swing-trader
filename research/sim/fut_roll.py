"""Study FUT-ROLL runner (pre-reg research/drafts/study_fut_roll.md).

Futures calendar-spread distortion at the scheduled institutional roll.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.fut_roll
"""
from __future__ import annotations

import pathlib
import re

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/fut_roll_out.txt"
ROOTS = {"ES": "$12.50", "NQ": "$5.00", "CL": "$10.00", "NG": "$10.00"}
TICK = {"ES": 0.25, "NQ": 0.25, "CL": 0.01, "NG": 0.001}
MON = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6, "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}


def load(root):
    f = ROOT / "data/research/program" / f"glbx_{root}_daily.parquet"
    d = pd.read_parquet(f)
    d["date"] = pd.to_datetime(d["ts_event"], utc=True).dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    # keep single outright contracts only: root + month code + year (no '-', no space, no ':')
    pat = re.compile(rf"^{root}([FGHJKMNQUVXZ])(\d)$")
    out = []
    for sym, g in d.groupby("symbol"):
        m = pat.match(str(sym))
        if not m:
            continue
        out.append(pd.DataFrame({"date": g["date"].values, "sym": sym, "close": g["close"].values,
                                 "volume": g["volume"].values,
                                 "exp": g["date"].min().year * 100 + MON[m.group(1)]}))
    return pd.concat(out) if out else pd.DataFrame()


def study(root):
    d = load(root)
    if d.empty:
        return None, f"{root}: no contracts\n"
    b = 1e4
    rows = []
    for date, g in d.groupby("date"):
        g = g[g.close > 0].sort_values("exp")
        if len(g) < 2:
            continue
        f1, f2 = g.iloc[0], g.iloc[1]
        rows.append(dict(date=date, f1=f1.sym, f1c=f1.close, f2=f2.sym, f2c=f2.close,
                         spread=f1.close - f2.close,
                         sp_pct=(f1.close - f2.close) / f2.close))
    R = pd.DataFrame(rows).set_index("date").sort_index()
    R["d_sp_pct"] = R["sp_pct"].diff()
    # LTD per front contract = last date it is F1
    f1_change = R["f1"] != R["f1"].shift(1)
    ltd = R.index[f1_change].tolist() + [R.index[-1]]
    # event study: for each LTD, [t-5,t], [t,t+5], and cumulative spread move
    ev = []
    idx = R.index
    for t in ltd[:-1]:
        j = idx.searchsorted(t)
        if j < 6 or j + 5 >= len(idx):
            continue
        w_pre = R["sp_pct"].iloc[j - 5:j + 1]
        w_post = R["sp_pct"].iloc[j:j + 6]
        ev.append(dict(t=t, r5=R["sp_pct"].iloc[j] - R["sp_pct"].iloc[j - 5],
                       pre_dmean=R["d_sp_pct"].iloc[j - 5:j + 1].mean(),
                       post_dmean=R["d_sp_pct"].iloc[j + 1:j + 6].mean(),
                       pre_mean=w_pre.mean(), post_mean=w_post.mean()))
    E = pd.DataFrame(ev)
    if E.empty:
        return None, f"{root}: no events\n"
    # CST = mean daily spread change pre vs post (bp of F2), t
    def line(x, lab):
        x = x.dropna()
        if len(x) < 10:
            return f"  {lab:28s} n={len(x)}"
        t = x.mean() / x.std() * np.sqrt(len(x))
        return (f"  {lab:28s} n={len(x):4d} mean={x.mean()*b:6.2f}bp med={x.median()*b:6.2f} "
                f"t={t:5.2f} hit={(x>0).mean()*100:3.0f}% ex5={x.sort_values().iloc[:-5].mean()*b:6.2f}")
    txt = [f"===== {root}  contracts={d.sym.nunique()}  days={len(R)}  events={len(E)}"]
    txt.append(" daily spread-change PRE (t-5..t) vs POST (t+1..t+5), bp of F2 price:")
    txt.append(line(E["pre_dmean"], "pre-roll daily"))
    txt.append(line(E["post_dmean"], "post-roll daily"))
    txt.append(" 5-session spread change into LTD (t-5 -> t), bp:")
    txt.append(line(E["r5"], "r5 (into LTD)"))
    # placebo: same stat on 200 random non-event windows
    rng = np.random.default_rng(0)
    plac = []
    for _ in range(200):
        j = rng.integers(6, len(idx) - 6)
        plac.append(R["sp_pct"].iloc[j] - R["sp_pct"].iloc[j - 5])
    plac = pd.Series(plac)
    txt.append(f"  placebo r5: mean={plac.mean()*b:.2f}bp t={plac.mean()/plac.std()*np.sqrt(len(plac)):.2f}")
    tick_bp = TICK[root] / R["f2c"].median() * b
    txt.append(f"  one-tick round trip on 2 legs ~= {2*tick_bp:.1f}bp of F2 price (cost bar)")
    return E, "\n".join(txt) + "\n"


def main():
    parts = ["Study FUT-ROLL: calendar-spread distortion at the scheduled roll",
             "spread S = F1_close - F2_close; changes in bp of F2 price; LTD = last day a contract is F1",
             "PRE>0 then POST<0 would be the predicted roll pressure (front weakens, then recovers).", ""]
    allE = {}
    for root in ROOTS:
        E, txt = study(root)
        parts += [txt]
        if E is not None:
            allE[root] = E
    # cross-contract summary
    parts.append("\nCROSS-CONTRACT (pre-roll daily spread change, bp):")
    for root, E in allE.items():
        x = E["pre_dmean"].dropna()
        t = x.mean() / x.std() * np.sqrt(len(x))
        parts.append(f"  {root:3s} n={len(x):4d} mean={x.mean()*1e4:6.2f}bp t={t:5.2f}")
    text = "\n".join(parts) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
