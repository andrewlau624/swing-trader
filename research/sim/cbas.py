"""Study CBAS runner (pre-reg research/drafts/round1_prose.md N 858->859).

Futures cash-basis dislocation: front ES/NQ close vs SPY/QQQ close; z vs trailing
21-session median/MAD; DISC (z<=-2) -> LONG ETF next open, PREM (z>=+2) -> SHORT.
Convergence channels: arb (spot follows) vs forced-flow (futures reverts, spot follows).

Run: PYTHONPATH=. .venv/bin/python -m research.sim.cbas
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .fut_roll import load  # same GLBX cache + contract parsing

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/cbas_out.txt"
B = 1e4


def trade_dates(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """GLBX daily bars are stamped by SESSION START (evening). Trade date = next business day."""
    d = idx.values.astype("datetime64[D]")
    td = np.busday_offset(d, 1, roll="backward")  # Sat/Sun -> Mon, Mon -> Tue, ...
    return pd.DatetimeIndex(td)


def front_series(root: str) -> pd.DataFrame:
    """Daily front contract (min exp, close>0) close + roll flag, by TRADE date."""
    d = load(root)
    td = trade_dates(pd.DatetimeIndex(d["date"]))
    d = pd.DataFrame({"date": td, "sym": d["sym"].values, "close": d["close"].values,
                      "exp": d["exp"].values, "volume": d["volume"].values})
    rows = []
    for date, g in d.groupby("date"):
        g = g[g.close > 0].sort_values("exp")
        if len(g) == 0:
            continue
        f = g.iloc[0]
        rows.append(dict(date=date, sym=f.sym, close=f.close))
    R = pd.DataFrame(rows).set_index("date").sort_index()
    R["roll5"] = R["sym"] != R["sym"].shift(5)   # front changed within 5 sessions -> mechanical jump
    return R


def spot(tkr: str) -> pd.DataFrame:
    from sharadar import prices as SP
    p = SP([tkr], adjust="raw").reset_index()
    p["date"] = p["date"].astype("datetime64[ns]")
    return p.set_index("date")[["open", "close"]].astype(float)


def build(root: str, tkr: str) -> pd.DataFrame:
    F = front_series(root)
    S = spot(tkr)
    idx = F.index.union(S.index).astype("datetime64[ns]")
    f = F["close"].reindex(idx)          # no ffill: require a real futures bar + real spot close
    s = S["close"].reindex(idx)
    o = S["open"].reindex(idx)
    D = pd.DataFrame({"f": f, "s": s, "o": o, "roll5": F["roll5"].reindex(idx)}, index=idx)
    D["roll5"] = D["roll5"].fillna(True).astype(bool)
    D = D.dropna(subset=["f", "s"])
    D["basis"] = np.log(D["f"] / D["s"]) * B
    med = D["basis"].rolling(21, min_periods=15).median()
    mad = (D["basis"] - med).abs().rolling(21, min_periods=15).median()
    D["z"] = (D["basis"] - med) / mad.replace(0, np.nan)
    D["disc"] = D["z"] <= -2
    D["prem"] = D["z"] >= 2
    D.loc[D["roll5"], ["disc", "prem"]] = False   # exclude roll-window basis jumps
    return D, med, mad


def arms(D: pd.DataFrame) -> pd.DataFrame:
    E = []
    idx = D.index
    for t, r in D.iterrows():
        j = idx.searchsorted(t)
        if j + 1 >= len(idx):
            continue
        t1 = idx[j + 1]
        t3 = idx[j + 3] if j + 3 < len(idx) else None
        e = D.loc[t1, "o"]
        c1 = D.loc[t1, "s"]
        c3 = D.loc[t3, "s"] if t3 is not None else np.nan
        if not (np.isfinite(e) and np.isfinite(c1) and e > 0):
            continue
        for tag, sig in (("DISC", r["disc"]), ("PREM", r["prem"])):
            if sig:
                dr = 1.0 if tag == "DISC" else -1.0
                E.append(dict(date=t, ent=t1, tag=tag, r1=dr * (c1 / e - 1),
                              r3=dr * (c3 / e - 1) if t3 is not None else np.nan,
                              z=r["z"], basis=r["basis"]))
    return pd.DataFrame(E)


def evaluate(E: pd.DataFrame, hedged: pd.DataFrame | None, label: str) -> list[str]:
    L = []
    for tag in ("DISC", "PREM"):
        sub = E[E["tag"] == tag]
        for h, col, cost in (("1d", "r1", 2e-4), ("3d", "r3", 2e-4)):
            x = sub.dropna(subset=[col]).copy()
            if len(x) < 15:
                L.append(f"  {label} {tag:4s} {h} n={len(x):4d} (too few)"); continue
            x["net"] = x[col] - cost
            g = x.groupby("ent")["net"].mean()
            t = g.mean() / g.std() * np.sqrt(len(g)) if g.std() > 0 else np.nan
            med = x["net"].median()
            ex5 = x.nsmallest(max(len(x) - 5, 1), "net")["net"].mean()
            x = x.sort_values("ent")
            k = len(x) // 2
            h1, h2 = x["net"].iloc[:k], x["net"].iloc[k:]
            L.append(f"  {label} {tag:4s} {h} n={len(x):4d} net={x['net'].mean()*B:6.1f}bp t={t:5.2f} "
                     f"med={med*B:6.1f} ex5={ex5*B:6.1f} halves={h1.mean()*B:6.1f}/{h2.mean()*B:6.1f} "
                     f"hit={(x['net']>0).mean()*100:3.0f}%")
    return L


def main():
    parts = ["Study CBAS: futures cash-basis dislocation (front close vs spot close, z vs 21d med/MAD)",
             "DISC z<=-2 -> LONG ETF next open; PREM z>=+2 -> SHORT; exits +1d / +3d close; roll5 excluded",
             "tier = 1bp/side ETF; tier_hi = 2bp; shock = 3bp/side. Hedged arm = long cheap leg vs short dear leg.", ""]
    for root, tkr in (("ES", "SPY"), ("NQ", "QQQ")):
        D, med, mad = build(root, tkr)
        E = arms(D)
        L = [f"===== {root}/{tkr}: days={len(D)} events DISC={int((E.tag=='DISC').sum())} PREM={int((E.tag=='PREM').sum())}"]
        L += evaluate(E, None, "etf")
        # cost variants on 1d
        for tag in ("DISC", "PREM"):
            x = E[(E.tag == tag)].dropna(subset=["r1"])
            if len(x):
                L.append(f"  cost tier_hi(2bp) {tag}: {((x.r1-4e-4).mean()*B):6.1f}bp | shock(3bp): {((x.r1-6e-4).mean()*B):6.1f}bp")
        # hedged info arm: basis convergence t -> t+1 (futures outperformance vs spot)
        hed = []
        for t, r in D.iterrows():
            if not (r["disc"] or r["prem"]):
                continue
            idx = D.index
            j = idx.searchsorted(t)
            if j + 1 >= len(idx):
                continue
            t1 = idx[j + 1]
            dr = 1.0 if r["disc"] else -1.0
            # convergence of the basis itself: -(z sign) * basis change t -> t1 (futures outperformance)
            chg = (np.log(D.loc[t1, "f"] / D.loc[t1, "s"]) - np.log(D.loc[t, "f"] / D.loc[t, "s"])) * B
            hed.append(dict(date=t, ent=t1, tag="DISC" if r["disc"] else "PREM",
                            conv=dr * chg))  # dr=+1 for DISC: futures outperf = basis up = convergence
        H = pd.DataFrame(hed)
        if len(H):
            for tag in ("DISC", "PREM"):
                x = H[H.tag == tag]
                if len(x) >= 15:
                    g = x.groupby("ent")["conv"].mean()
                    tt = g.mean() / g.std() * np.sqrt(len(g)) if g.std() > 0 else np.nan
                    L.append(f"  hedged {tag:4s} basis-convergence t->t1: n={len(x):4d} mean={x['conv'].mean():6.1f}bp t={tt:5.2f} "
                             f"halves={x.sort_values('ent')['conv'].iloc[:len(x)//2].mean():6.1f}/{x.sort_values('ent')['conv'].iloc[len(x)//2:].mean():6.1f}")
        # mechanism diagnostic: is the flag a 1-day outlier (regression to median) or a
        # persistent dislocation regime (arb-constrained for days)?
        z = D["z"]
        for tag, col in (("DISC", "disc"), ("PREM", "prem")):
            flagged = D[D[col]]
            if len(flagged) >= 15:
                pos = D.index.get_indexer(flagged.index) + 1
                z1 = z.iloc[pos[pos < len(D)]].dropna()
                same = ((z1 <= -2) if tag == "DISC" else (z1 >= 2)).mean() * 100
                L.append(f"  mechanism {tag}: MAD21 med={mad.median():.1f}bp; z_(t+1) median={z1.median():.1f}; "
                         f"still-flagged next day={same:.0f}% (low=persistent dislocation absent)")
        # top events table
        top = E.nlargest(5, "r1") if len(E) else E
        L.append("  top-5 net 1d events: " + (", ".join(f"{r.date.date()}:{r.tag}:{r.r1*B:.0f}bp" for _, r in top.iterrows()) if len(E) else "-"))
        parts += L
    text = "\n".join(parts) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
