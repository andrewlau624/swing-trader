"""PREF-NOAUC (N 1210-1211, pre-registered in round1_prose.md 2026-11-17): PREF-EX returns on events with vs without a real
('6') closing auction print, and an ex-ante filter (AUC on >= 4 of the 5 sessions before T-1).

    PYTHONPATH=. python3 -m research.sim.pref_noauc          # fetch is resumable
"""
from __future__ import annotations

import json
import pathlib
import time

import numpy as np
import pandas as pd

from .auction_fetch import _env, fetch
from .pref_fetch import events

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/pref_noauc"
OUT = pathlib.Path(__file__).resolve().parent / "pref_noauc_out.txt"
RT = 10e-4            # 10bp round trip (registered)
ACCT, PART = 10_000, 0.05


def grab(e: pd.DataFrame) -> None:
    (D / "x").mkdir(parents=True, exist_ok=True)
    H, t0 = _env(), time.time()
    grp = list(e.groupby("date"))
    for i, (d, x) in enumerate(grp):
        f = D / "x" / f"{pd.Timestamp(d).date()}.json"
        if f.exists():
            continue
        syms, rows = sorted(set(x.sym)), {}
        a = str((pd.Timestamp(x.d0.min()) - pd.Timedelta(days=10)).date())
        for k in range(0, len(syms), 100):
            rows.update(fetch(syms[k:k + 100], a, str(pd.Timestamp(d).date()), H))
        json.dump(rows, open(f, "w"))
        time.sleep(0.2)
        if i % 100 == 0:
            print(f"{i}/{len(grp)} {time.time() - t0:.0f}s", flush=True)


def day_table(rows: list[dict]) -> pd.DataFrame:
    out = []
    for x in rows:
        c = x.get("c") or []
        six = [p for p in c if p.get("c") == "6"]
        m = sorted({p["p"] for p in c if p.get("c") == "M"})
        cp = max(six or c, key=lambda p: p.get("s", 0)) if c else None
        o = max(x["o"], key=lambda p: p.get("s", 0)) if x.get("o") else None
        band = (m[-1] - m[0]) / ((m[-1] + m[0]) / 2) * 1e4 if len(m) > 1 else 0.0
        out.append((pd.Timestamp(x["d"]), o["p"] if o else np.nan, cp["p"] if cp else np.nan,
                    cp["s"] if cp else np.nan, bool(six), band))
    t = pd.DataFrame(out, columns=["d", "op", "cp", "cs", "auc", "band"])
    return t.drop_duplicates("d", keep="last").set_index("d").sort_index()


def build(e: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d, x in e.groupby("date"):
        f = D / "x" / f"{pd.Timestamp(d).date()}.json"
        if not f.exists():
            continue
        j = json.load(open(f))
        for r in x.itertuples():
            if r.sym not in j:
                continue
            t = day_table(j[r.sym])
            d0, d1 = pd.Timestamp(r.d0), pd.Timestamp(d)
            if d0 not in t.index or d1 not in t.index:
                continue
            prior = t[t.index < d0].tail(5)
            c0, o1, c1 = t.loc[d0, "cp"], t.loc[d1, "op"], t.loc[d1, "cp"]
            rows.append(dict(t=r.ticker, d=d1, co=(o1 + r.div) / c0 - 1, cc=(c1 + r.div) / c0 - 1, c0=c0,
                             auc=bool(t.loc[d0, "auc"] and t.loc[d1, "auc"]),
                             band=max(t.loc[d0, "band"], t.loc[d1, "band"]),
                             kept=len(prior) == 5 and int(prior.auc.sum()) >= 4,
                             xa=float((prior.cp * prior.cs).median()) if len(prior) else np.nan))
    return pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).dropna(subset=["co", "cc"])


def stat(x: pd.DataFrame, c: str) -> str:
    if not len(x):
        return "n 0"
    day = x.groupby("d")[c].mean()
    t = day.mean() / day.std() * np.sqrt(len(day)) if len(day) > 1 else np.nan
    srt = np.sort(x[c].to_numpy())
    return (f"n {len(x):5d} mean {x[c].mean() * 1e4:+6.1f} med {x[c].median() * 1e4:+6.1f} hit {(x[c] > 0).mean():.2f} "
            f"t(day) {t:+5.2f} ex-top5 {srt[:-5].mean() * 1e4:+6.1f}")


def dollars(x: pd.DataFrame, extra: pd.Series | None = None) -> float:
    """Net CC $ per ex-date night at $10k: min(5% of ex-ante cross $, equal share), whole shares, 10bp RT (+ extra)."""
    tot, nights = 0.0, x.d.nunique()
    for d, g in x.groupby("d"):
        cap = ACCT / len(g)
        for r in g.itertuples():
            pos = min(PART * r.xa, cap) if np.isfinite(r.xa) else 0.0
            sh = np.floor(pos / r.c0)
            ex = extra.loc[r.Index] if extra is not None else 0.0
            tot += sh * r.c0 * (r.cc - RT - ex)
    return tot / max(nights, 1)


def main():
    e = events()
    grab(e)
    df = build(e)
    L = [f"PREF-NOAUC: {len(df)} events / {df.d.nunique()} ex-dates / {df.t.nunique()} prefs ({df.d.min().date()}..{df.d.max().date()})",
         f"AUC (a '6' close print on T-1 and T): {df.auc.mean():.1%} of events", ""]
    L.append("N 1210 primary (gross, no cost):")
    for lab, x in (("AUC  ", df[df.auc]), ("NOAUC", df[~df.auc])):
        for c in ("cc", "co"):
            L.append(f"  {lab} {c}: {stat(x, c)}")
    nb = df[~df.auc].band
    L.append(f"  NOAUC median M-band {nb.median():.1f}bp (p75 {nb.quantile(.75):.1f}); AUC median {df[df.auc].band.median():.1f}bp")
    diff = (df[~df.auc].cc.mean() - df[df.auc].cc.mean()) * 1e4
    L.append(f"  NOAUC - AUC cc mean {diff:+.1f}bp -> "
             + ("FALSIFIED (edge sits where price is least knowable)" if diff > 10 and nb.median() >= 10 else "not falsified"))
    L.append("")
    L.append("N 1211 ex-ante filter (AUC on >= 4 of 5 sessions before T-1):")
    k, dr = df[df.kept], df[~df.kept]
    L.append(f"  kept {len(k)} ({len(k) / len(df):.1%}); dropped {len(dr)}; dropped median M-band {dr.band.median():.1f}bp")
    for lab, x in (("kept   ", k), ("dropped", dr)):
        L.append(f"  {lab} cc: {stat(x, 'cc')}")
    net = k.assign(n=k.cc - RT)
    h1, h2 = net[net.d.dt.year <= 2023].n.mean() * 1e4, net[net.d.dt.year >= 2024].n.mean() * 1e4
    L.append(f"  kept cc net halves 2021-23 {h1:+.1f} / 2024-26 {h2:+.1f}bp")
    shock = 2 * dr.band.median() * 1e-4
    extra = pd.Series(np.where(df.kept, 0.0, shock), index=df.index)
    du, dk = dollars(df, extra), dollars(k)
    L.append(f"  $/night at $10k: unfiltered (dropped charged 2x median M-band = {shock * 1e4:.1f}bp) ${du:,.2f}; kept-only ${dk:,.2f}; "
             f"ratio {dk / du if du else np.nan:.2f}; unfiltered no charge ${dollars(df):,.2f}")
    ok = len(k) / len(df) >= .40 and h1 > 0 and h2 > 0 and du > 0 and dk >= .9 * du
    L.append(f"  N 1211 verdict: {'PASS (filter is a user decision)' if ok else 'KILL'}")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
