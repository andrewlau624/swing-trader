"""Study THEME-NIGHT (round1_prose.md, N 1033 -> 1034): night picks in a "bubble" theme; healthcare/biotech avoidance.

Picks = SEL-NIGHT current-rule kept names (Sharadar common stocks 1999-2026, r = close -> next official open).
Theme state = industry EW log-return momentum over the 126 sessions ending the prior session; BUBBLE = top decile
across industries that day AND mom126 >= +0.40. Arms: T1 bubble vs other picks (same night), T2 healthcare /
biotech+devices vs other picks (judge 2016-26), plus a quantum 2024-26 descriptive.

Run:  PYTHONPATH=. .venv/bin/python research/sim/theme_night.py
Out:  data/research/program/theme_night_out.txt
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data" / "research" / "program"
S = pathlib.Path.home() / "data" / "sharadar"
MOM_W, MOM_MIN, MIN_MEMBERS = 126, 0.40, 10
QUANTUM = {"IONQ", "RGTI", "QBTS", "QUBT", "ARQQ", "LAES", "QMCO", "QSI"}
BIO = {"Biotechnology", "Medical Devices", "Medical Instruments & Supplies", "Diagnostics & Research"}


def industry_map() -> pd.DataFrame:
    t = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "sector", "industry", "lastupdated"])
    t = t[t.table == "SEP"].sort_values("lastupdated").drop_duplicates("ticker", keep="last")
    return t.set_index("ticker")[["sector", "industry"]]


def industry_state(imap: pd.DataFrame) -> pd.DataFrame:
    """Per (date, industry): EW log return, members, mom126 (prior-session end), vol20, cross-sectional pct."""
    b = ds.dataset(S / "stocks.parquet").to_table(columns=["ticker", "date", "close", "closeunadj"]).to_pandas()
    b["date"] = pd.to_datetime(b["date"])
    b = b.sort_values(["ticker", "date"], kind="mergesort")
    g = b.groupby("ticker", sort=False)
    b["lr"] = np.log(b["close"] / g["close"].shift(1))
    b["pc"] = g["closeunadj"].shift(1)
    b = b[(b.pc >= 5) & np.isfinite(b.lr) & (b.lr.abs() < 1.5)]
    b["industry"] = b["ticker"].map(imap["industry"])
    b = b[b.industry.notna() & (b.industry != "")]
    agg = b.groupby(["industry", "date"])["lr"].agg(["mean", "size"]).reset_index()
    agg = agg[agg["size"] >= MIN_MEMBERS]
    wide = agg.pivot(index="date", columns="industry", values="mean").sort_index()
    mom = wide.rolling(MOM_W, min_periods=int(MOM_W * 0.9)).sum().shift(1)       # ends the PRIOR session
    vol = wide.rolling(20, min_periods=15).std().shift(1) * np.sqrt(252)
    pct = mom.rank(axis=1, pct=True)
    volpct = vol.rank(axis=1, pct=True)
    out = pd.concat({"mom": mom.stack(), "pct": pct.stack(), "vol": vol.stack(), "volpct": volpct.stack()}, axis=1)
    out.index.names = ["date", "industry"]
    return out.reset_index()


def clus_t(x: np.ndarray) -> float:
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def paired(nm: pd.DataFrame, flag: str, label: str, lo="1999-01-01", hi="2026-12-31", split="2013-01-01",
           n_perm: int = 200) -> list[str]:
    d = nm[(nm.date >= lo) & (nm.date <= hi)]
    rows = []
    rng = np.random.default_rng(20261018)
    perm_means = np.zeros(n_perm)
    perm_rows = []
    for dt, g in d.groupby("date"):
        f = g[flag].to_numpy(bool)
        if f.any() and (~f).any():
            r = g["r"].to_numpy(float)
            rows.append(dict(date=dt, k=int(f.sum()), n=len(g), delta=r[f].mean() - r[~f].mean(),
                             share=f.mean(), r_in=r[f].mean(), r_out=r[~f].mean()))
            # permutation: shuffle labels within night
            pm = np.empty(n_perm)
            for p in range(n_perm):
                fp = rng.permutation(f)
                pm[p] = r[fp].mean() - r[~fp].mean()
            perm_rows.append(pm)
    t = pd.DataFrame(rows)
    L = [f"-- {label} [{lo[:4]}-{hi[:4]}] --"]
    if len(t) < 10:
        return L + [f"  nights with both groups: {len(t)} (too few)"]
    dl = t["delta"].to_numpy(float) * 1e4
    yr = t["date"].dt.year.to_numpy()
    h1, h2 = dl[t["date"] < split], dl[t["date"] >= split]
    s = np.sort(dl)
    ex5 = s[:-5].mean()
    ex5lo = s[5:].mean()
    perm = np.vstack(perm_rows).mean(axis=0) * 1e4
    p_perm = float((np.abs(perm) >= abs(dl.mean())).mean())
    tot_in = int(t["k"].sum())
    L.append(f"  nights {len(t)} (picks in group {tot_in}, share of picks on those nights {t['share'].mean():.1%}); "
             f"r in {t['r_in'].mean()*1e4:+.1f} vs out {t['r_out'].mean()*1e4:+.1f}bp")
    L.append(f"  delta(in - out) {dl.mean():+.1f}bp  t(night) {clus_t(dl):.2f}  med {np.median(dl):+.1f}  hit {(dl > 0).mean():.3f}  "
             f"h1 {h1.mean() if len(h1) else float('nan'):+.1f} (n {len(h1)})  h2 {h2.mean() if len(h2) else float('nan'):+.1f} (n {len(h2)})  "
             f"ex-top-5 {ex5:+.1f}  ex-bottom-5 {ex5lo:+.1f}  perm p {p_perm:.3f} (null sd {perm.std():.1f})")
    by = pd.Series(dl).groupby(yr).mean()
    L.append("  by year: " + " ".join(f"{y}:{v:+.0f}" for y, v in by.items()))
    return L


def leg_replay(nm: pd.DataFrame, flag: str, mode: str, lo="1999-01-01", hi="2026-12-31") -> str:
    """Leg bp/night when picks with flag are dropped (mode='drop') or up-weighted x2 (mode='x2'), re-normalised."""
    d = nm[(nm.date >= lo) & (nm.date <= hi)]
    base, alt = [], []
    for dt, g in d.groupby("date"):
        w = (g["per"]).to_numpy(float)
        r = g["r"].to_numpy(float)
        f = g[flag].to_numpy(bool)
        base.append(float((w * r).sum()))
        if mode == "drop":
            w2 = np.where(f, 0.0, w)
        else:
            w2 = np.where(f, 2 * w, w)
        w2 = w2 * (w.sum() / w2.sum()) if w2.sum() > 0 else w2
        alt.append(float((w2 * r).sum()))
    b, a = np.array(base) * 1e4, np.array(alt) * 1e4
    dd = a - b
    return (f"  leg replay {mode} {flag}: current {b.mean():+.2f} bp/night -> {a.mean():+.2f}; diff {dd.mean():+.2f} t {clus_t(dd):.2f} "
            f"(x250 = {dd.mean()*250/100:+.2f}% of leg budget/yr, ~{dd.mean()*250/100*0.65:+.2f}pp of equity at w .65)")


def main() -> int:
    imap = industry_map()
    nm = pd.read_parquet(PROG / "sel_night_names_primary.parquet")
    nm["date"] = pd.to_datetime(nm["date"])
    nm["sector"] = nm["ticker"].map(imap["sector"])
    nm["industry"] = nm["ticker"].map(imap["industry"])
    st = industry_state(imap)
    nm = nm.merge(st, on=["date", "industry"], how="left")
    nm["bubble"] = (nm["pct"] >= 0.9) & (nm["mom"] >= MOM_MIN)
    nm["tophalf"] = nm["pct"] >= 0.5
    nm["bottomdec"] = nm["pct"] <= 0.1
    nm["bubble_hivol"] = nm["bubble"] & (nm["volpct"] >= 0.8)
    nm["hc"] = nm["sector"] == "Healthcare"
    nm["bio"] = nm["industry"].isin(BIO)
    nm["quantum"] = nm["ticker"].isin(QUANTUM)
    L = [f"THEME-NIGHT: picks {len(nm)} nights {nm.date.nunique()} {nm.date.min().date()}..{nm.date.max().date()}; "
         f"industry mapped {nm.industry.notna().mean():.1%}, state available {nm.mom.notna().mean():.1%}",
         f"bubble picks {int(nm.bubble.sum())} ({nm.bubble.mean():.1%}); healthcare {int(nm.hc.sum())} ({nm.hc.mean():.1%}); "
         f"bio/devices {int(nm.bio.sum())} ({nm.bio.mean():.1%})", ""]
    L.append("== T1: bubble-theme picks (top-decile industry mom126 and mom >= +0.40) vs other picks, same night ==")
    L += paired(nm, "bubble", "BUBBLE")
    L.append(leg_replay(nm, "bubble", "x2"))
    L.append(leg_replay(nm, "bubble", "drop"))
    L += paired(nm, "bubble_hivol", "BUBBLE x industry vol top quintile")
    L += paired(nm, "tophalf", "anchor: top-half momentum (CAT-MOM form)")
    L += paired(nm, "bottomdec", "anchor: bottom-decile momentum (busted theme)")
    L.append("")
    L.append("== T2: healthcare / biotech avoidance ==")
    L += paired(nm, "hc", "Healthcare sector", lo="2016-01-01", split="2021-01-01")
    L.append(leg_replay(nm, "hc", "drop", lo="2016-01-01"))
    L += paired(nm, "bio", "Biotech + devices + diagnostics", lo="2016-01-01", split="2021-01-01")
    L.append(leg_replay(nm, "bio", "drop", lo="2016-01-01"))
    L += paired(nm, "hc", "Healthcare sector (HC-BAN window, reported)", hi="2015-12-31", split="2008-01-01")
    L += paired(nm, "bio", "Biotech + devices (HC-BAN window, reported)", hi="2015-12-31", split="2008-01-01")
    L.append("")
    L.append("== descriptive: quantum names 2024-26 ==")
    q = nm[(nm.date >= "2024-01-01")]
    qq = q[q.quantum]
    L.append(f"  quantum picks {len(qq)} on {qq.date.nunique()} nights: mean r {qq.r.mean()*1e4:+.1f}bp med {qq.r.median()*1e4:+.1f}; "
             f"other picks same nights {q[q.date.isin(qq.date) & ~q.quantum].r.mean()*1e4:+.1f}bp; "
             f"by name {qq.groupby('ticker').r.agg(['size','mean']).assign(mean=lambda x: (x['mean']*1e4).round(0)).to_dict('index')}")
    txt = "\n".join(L) + "\n"
    (PROG / "theme_night_out.txt").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
