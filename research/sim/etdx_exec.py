"""ETDX capacity increment: account $/yr of PREF-EX alone vs PREF-EX + ETD + CEF preferreds on official crosses 2021-26.

Reuses pref_exec.account (equal split across a night's events, each capped at p x ex-ante auction $, whole shares, Roth,
no leverage). Ex-ante auction size is estimated per source (cross $ / 20d $vol median x the name's 20d $vol).
The 'impact' row uses the PREFERRED quote sample's spreads for all classes (ETD spreads not sampled).

    PYTHONPATH=. .venv/bin/python -m research.sim.etdx_exec
"""
from __future__ import annotations

import pathlib

import pandas as pd

from .pref_exec import ACCTS, account

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/etdx_exec_out.txt"


def rows(sub: str) -> pd.DataFrame:
    d = ROOT / "data/research" / sub
    df = pd.read_parquet(d / "cross_rows.parquet")
    ev = pd.read_parquet(d / "events.parquet")[["ticker", "date", "pc"]].rename(columns={"ticker": "t", "date": "d"})
    df = df.merge(ev.drop_duplicates(["t", "d"]), on=["t", "d"], how="left")
    kc, ko = (df.close_usd / df.dv).median(), (df.open_usd / df.dv).median()
    df["cap_close_ea"], df["cap_open_ea"] = kc * df.dv, ko * df.dv
    df["src"] = sub
    return df


def main():
    pref, etd = rows("pref"), rows("etdx")
    both = pd.concat([pref, etd], ignore_index=True)
    lo, hi = max(pref.d.min(), etd.d.min()), min(pref.d.max(), etd.d.max())
    sets = {k: v[(v.d >= lo) & (v.d <= hi)] for k, v in [("PREF", pref), ("ETDX", etd), ("PREF+ETDX", both)]}
    yrs = (hi - lo).days / 365.25
    L = [f"ETDX capacity increment, official crosses {lo.date()}..{hi.date()}"]
    for k, v in sets.items():
        L.append(f"  {k:10s}: {len(v)} events, {v.d.nunique() / yrs:.0f} ex-nights/yr, CO mean {v.co.mean()*1e4:+.1f}bp, "
                 f"CC mean {v.cc.mean()*1e4:+.1f}bp")
    L += ["", "set        form p    cost   " + " ".join(f"{'$'+format(int(a),','):>18s}" for a in ACCTS)]
    for col in ["co", "cc"]:
        for p in [0.05, 0.10]:
            for lab, c, imp in [("10bp", 0.0005, False), ("impact", 0, True)]:
                for k, v in sets.items():
                    cells = []
                    for a in ACCTS:
                        dol, pct, use = account(v, col, a, p, c, c, True, imp)
                        cells.append(f"${dol:6,.0f} {pct*100:5.1f}% {use*100:3.0f}%")
                    L.append(f"{k:10s} {col.upper()}  {p:3.0%} {lab:6s} " + " ".join(f"{x:>18s}" for x in cells))
            L.append("")
    L.append("cell = gross $/yr, %/yr of the account, mean share deployed on ex-nights")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
