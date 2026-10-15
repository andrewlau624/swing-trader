"""CEF-TXT (N 888-889) judge: does N-CSR shareholder-report tone separate CEF-RV winners from losers?

    PYTHONPATH=. .venv/bin/python -m research.sim.cef_txt     # -> research/sim/cef_txt_out.txt

Inputs: cef_rv_trades.csv (2016+ entries), data/research/cef_txt/{filings,scores}.parquet, CEFConnect panel.
Pre-registration: round1_prose.md "Study CEF-TXT".
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/cef_txt"
CEF = ROOT / "data/research/cefconnect"
OUT = ROOT / "research/sim/cef_txt_out.txt"
COST = 0.005
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)


def sizes(fl: pd.DataFrame) -> pd.Series:
    """accession -> full EDGAR filing size (control C1), from the submissions index; cached."""
    fp = D / "sizes.parquet"
    if fp.exists():
        return pd.read_parquet(fp).set_index("accession")["size"]
    from research.sim.cef_txt_fetch import FORMS, get
    rows = []
    for cik in sorted(fl["cik"].unique()):
        sub = get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json").json()
        blocks = [sub["filings"]["recent"]] + [get(f"https://data.sec.gov/submissions/{f['name']}").json()
                                               for f in sub["filings"].get("files", [])]
        for b in blocks:
            for i, form in enumerate(b.get("form", [])):
                if form in FORMS:
                    rows.append(dict(accession=b["accessionNumber"][i], size=int(b["size"][i])))
    s = pd.DataFrame(rows).drop_duplicates("accession")
    s.to_parquet(fp)
    return s.set_index("accession")["size"]


def clus_t(x: np.ndarray, g: np.ndarray) -> float:
    """t of mean(x) with clusters g (entry week)."""
    df = pd.DataFrame(dict(x=x - x.mean(), g=g))
    s = df.groupby("g")["x"].sum().to_numpy()
    n, k = len(x), len(s)
    se = np.sqrt((s ** 2).sum() * k / max(k - 1, 1)) / n
    return float(x.mean() / se) if se > 0 else float("nan")


def spread_stats(r: np.ndarray, drop: np.ndarray, wk: np.ndarray) -> dict:
    """kept - dropped mean spread with a clustered t via the regression-equivalent difference."""
    keep = ~drop
    sp = r[keep].mean() - r[drop].mean()
    # difference-in-means as a mean of a scaled indicator contrast: x_i = r_i * (k_i/p_k - d_i/p_d)
    pk, pd_ = keep.mean(), drop.mean()
    resid = r - np.where(keep, r[keep].mean(), r[drop].mean())
    x = resid * (keep / pk - drop / pd_)
    df = pd.DataFrame(dict(x=x, g=wk)).groupby("g")["x"].sum().to_numpy()
    k = len(df)
    se = np.sqrt((df ** 2).sum() * k / max(k - 1, 1)) / len(r)
    return dict(spread=sp, t=sp / se if se > 0 else np.nan, lift=r[keep].mean() - r.mean(),
                med=np.median(r[keep]) - np.median(r[drop]), n_keep=int(keep.sum()), n_drop=int(drop.sum()),
                hit_keep=(r[keep] > 0).mean(), hit_drop=(r[drop] > 0).mean())


def tercile_drop(v: pd.Series, year: pd.Series, worst: str) -> np.ndarray:
    """Within entry year, flag the worst tercile of v ('high' = largest values worst)."""
    rk = v.groupby(year).rank(pct=True)
    return (rk > 2 / 3).to_numpy() if worst == "high" else (rk <= 1 / 3).to_numpy()


def ex_top5(r, drop):
    idx = np.argsort(-np.abs(r))[5:]
    m = np.zeros(len(r), bool)
    m[idx] = True
    return r[m & ~drop].mean() - r[m & drop].mean()


def main() -> int:
    tr = pd.read_csv(CEF / "cef_rv_trades.csv", parse_dates=["edate", "xdate"])
    tr = tr[tr["edate"] >= "2016-01-01"].reset_index(drop=True)
    fl = pd.read_parquet(D / "filings.parquet")
    sc = pd.read_parquet(D / "scores.parquet")
    fl["adate"] = pd.to_datetime(fl["accepted"].str[:10])
    fl = fl.merge(sc, on="accession", how="inner").dropna(subset=["tone"])
    fl = fl[fl["n_sent"] >= 10]
    sz = sizes(fl)
    fl["size"] = fl["accession"].map(sz)
    fl = fl.sort_values(["ticker", "adate"])
    # within-fund previous report tone (A2): previous distinct accession of the same ticker
    fl = fl.drop_duplicates(["ticker", "accession"])
    fl["prev_tone"] = fl.groupby("ticker")["tone"].shift(1)
    fl["prev_adate"] = fl.groupby("ticker")["adate"].shift(1)
    say(f"CEF-TXT judge  trades 2016+ {len(tr)}  reports scored {fl['accession'].nunique()}  funds {fl['ticker'].nunique()}")

    # attach the latest report accepted strictly before edate (calendar day), within 400 days
    m = pd.merge_asof(tr.sort_values("edate"), fl.rename(columns={"adate": "rdate"}).sort_values("rdate"),
                      left_on="edate", right_on="rdate", by="ticker", allow_exact_matches=False, direction="backward")
    m = m[(m["edate"] - m["rdate"]).dt.days <= 400].reset_index(drop=True)
    say(f"trades with a report in the prior 400d: {len(m)} of {len(tr)} (excluded {len(tr) - len(m)}); "
        f"median report age {int((m['edate'] - m['rdate']).dt.days.median())}d")

    # controls C3/C4 inputs
    pan = pd.read_parquet(CEF / "cef_panel.parquet")[["ticker", "date", "nav"]].sort_values(["ticker", "date"])
    pan["nav26"] = pan.groupby("ticker")["nav"].pct_change(26)
    m = pd.merge_asof(m.sort_values("edate"), pan[["ticker", "date", "nav26"]].sort_values("date"),
                      left_on="edate", right_on="date", by="ticker", direction="backward")
    m = m.sort_values(["edate", "ticker"]).reset_index(drop=True)
    r = m["ret"].to_numpy(float) - COST
    yr = m["edate"].dt.year
    wk = m["edate"].dt.strftime("%G-%V").to_numpy()
    half = (m["edate"] >= "2021-01-01").to_numpy()
    say(f"base: mean {r.mean()*1e4:+.1f}bp  median {np.median(r)*1e4:+.1f}  hit {(r>0).mean():.2f}  "
        f"t_wk {clus_t(r, wk):.2f}")
    say(f"tone: mean {m['tone'].mean():+.3f} sd {m['tone'].std():.3f}; dist_cut flagged {m['dist_cut'].mean():.2f}; "
        f"corr(tone, ret) {np.corrcoef(m['tone'], r)[0,1]:+.3f}")

    arms = {
        "A1 tone level (drop most-negative tercile)": tercile_drop(m["tone"], yr, "high"),
        "A2 tone change (drop most-deteriorated)": None,
        "C1a size (drop largest tercile)": tercile_drop(m["size"].astype(float), yr, "high"),
        "C1b size (drop smallest tercile)": tercile_drop(m["size"].astype(float), yr, "low"),
        "C2 distribution-cut keyword (drop flagged)": m["dist_cut"].to_numpy(bool),
        "C3 trailing 26w NAV return (drop lowest)": tercile_drop(m["nav26"], yr, "low"),
        "C4 entry discount (drop shallowest)": tercile_drop(m["disc_in"], yr, "high"),
    }
    res = {}
    for name, drop in arms.items():
        rr, ww, hh, sub = r, wk, half, m
        if name.startswith("A2"):
            ok = m["prev_tone"].notna().to_numpy()
            sub = m[ok].reset_index(drop=True)
            rr, ww, hh = r[ok], wk[ok], half[ok]
            drop = tercile_drop(sub["tone"] - sub["prev_tone"], sub["edate"].dt.year, "high")
        if drop.sum() == 0 or drop.all():
            say(f"{name}: degenerate (drop {drop.sum()})")
            continue
        s = spread_stats(rr, drop, ww)
        h0 = spread_stats(rr[~hh], drop[~hh], ww[~hh])["spread"]
        h1 = spread_stats(rr[hh], drop[hh], ww[hh])["spread"]
        s.update(h0=h0, h1=h1, ex5=ex_top5(rr, drop), n=len(rr))
        res[name] = (s, rr, drop, ww, sub)
        say(f"{name}: n {len(rr)} keep {s['n_keep']} drop {s['n_drop']}  SPREAD {s['spread']*1e4:+.1f}bp "
            f"t_wk {s['t']:.2f}  lift {s['lift']*1e4:+.1f}  med-diff {s['med']*1e4:+.1f}  hit keep/drop "
            f"{s['hit_keep']:.2f}/{s['hit_drop']:.2f}  halves {h0*1e4:+.1f}/{h1*1e4:+.1f}  ex-top5 {s['ex5']*1e4:+.1f}")

    # placebo: shuffle report assignment across trades within the same entry year (200x)
    rng = np.random.default_rng(888)
    say("")
    for key, col in (("A1 tone level (drop most-negative tercile)", "tone"),
                     ("A2 tone change (drop most-deteriorated)", "dtone")):
        if key not in res:
            continue
        s, rr, drop, ww, sub = res[key]
        v = (sub["tone"] - sub["prev_tone"]) if col == "dtone" else sub["tone"]
        y = sub["edate"].dt.year
        pl = []
        for _ in range(200):
            vs = v.groupby(y).transform(lambda x: x.sample(frac=1, random_state=int(rng.integers(1e9))).to_numpy())
            d = tercile_drop(vs, y, "high")
            pl.append(rr[~d].mean() - rr[d].mean())
        pl = np.array(pl)
        pct = (pl < s["spread"]).mean() * 100
        say(f"PLACEBO {key[:2]}: real {s['spread']*1e4:+.1f}bp vs shuffled mean {pl.mean()*1e4:+.1f} "
            f"p95 {np.percentile(pl, 95)*1e4:+.1f}  -> real at {pct:.0f}th pct")
        res[key][0]["pct"] = pct

    # decile/tercile profile of A1
    say("")
    q = m["tone"].groupby(yr).rank(pct=True)
    for lo, hi in ((0, 1/3), (1/3, 2/3), (2/3, 1.01)):
        k = ((q > lo) & (q <= hi)).to_numpy()
        say(f"A1 tone tercile ({lo:.2f},{hi:.2f}]: n {k.sum()} mean {r[k].mean()*1e4:+.1f}bp "
            f"median {np.median(r[k])*1e4:+.1f} hit {(r[k]>0).mean():.2f}")

    say("\nGATE (each arm): spread>=+150bp, t_wk>=2, halves>0, med-diff>0, ex-top5>0, placebo>=95th pct, "
        "beats best non-NLP control by >=+50bp")
    ctrl = max((v[0]["spread"] for k, v in res.items() if k.startswith("C")), default=np.nan)
    say(f"best control spread {ctrl*1e4:+.1f}bp")
    for key in [k for k in res if k.startswith("A")]:
        s = res[key][0]
        checks = dict(spread=s["spread"] >= 0.015, t=s["t"] >= 2, halves=s["h0"] > 0 and s["h1"] > 0,
                      med=s["med"] > 0, ex5=s["ex5"] > 0, placebo=s.get("pct", 0) >= 95,
                      control=s["spread"] - ctrl >= 0.005)
        say(f"{key[:2]}: {'PASS' if all(checks.values()) else 'KILL'}  " +
            " ".join(f"{k}={'Y' if v else 'n'}" for k, v in checks.items()))
    say("\ncost shock: spreads are kept-minus-dropped, so a uniform round-trip cost cancels; at 100/150bp the kept "
        f"leg mean is {(r.mean()+COST-0.010)*1e4:+.1f} / {(r.mean()+COST-0.015)*1e4:+.1f}bp before filtering")
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
