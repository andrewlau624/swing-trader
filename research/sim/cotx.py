"""Study COTX runner (pre-reg research/drafts/round1_prose.md N 857->858).

CFTC COT positioning as a derivatives-only state -> forced unwind / forced cover.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.cotx
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/cotx_out.txt"
CACHEDIR = ROOT / "data/research/cot"
CACHEDIR.mkdir(parents=True, exist_ok=True)

TFF = "gpe5-46if"      # traders in financial futures
DISAGG = "72hh-3qpy"   # disaggregated futures-only

# product -> (dataset, [market names to union, preferring later-named series on date clash])
PRODUCTS = {
    "ES": (TFF, ["E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
                 "E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",
                 "S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE"], "SPY"),
    "NQ": (TFF, ["NASDAQ MINI - CHICAGO MERCANTILE EXCHANGE",
                 "NASDAQ-100 STOCK INDEX (MINI) - CHICAGO MERCANTILE EXCHANGE",
                 "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE"], "QQQ"),
    "6E": (TFF, ["EURO FX - CHICAGO MERCANTILE EXCHANGE"], "FXE"),
    "ZN": (TFF, ["UST 10Y NOTE - CHICAGO BOARD OF TRADE"], "IEF"),
    "CL": (DISAGG, ["CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE"], "USO"),
    "NG": (DISAGG, ["NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"], "UNG"),
    "GC": (DISAGG, ["GOLD - COMMODITY EXCHANGE INC."], "GLD"),
    "SI": (DISAGG, ["SILVER - COMMODITY EXCHANGE INC."], "SLV"),
    "HG": (DISAGG, ["COPPER-GRADE #1 - COMMODITY EXCHANGE INC.",
                    "COPPER- #1 - COMMODITY EXCHANGE INC."], "CPER"),
}
PREF = ["Consolidated"]  # prefer consolidated series on date clash

BASE = "https://publicreporting.cftc.gov/resource/{}.json"


def _get(url: str, retries: int = 4) -> list:
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "swing-trader research"}), timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))
    return []


def fetch(dataset: str, names: list[str]) -> pd.DataFrame:
    cache = CACHEDIR / f"{dataset}_{hashlib.md5('|'.join(names).encode()).hexdigest()[:10]}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    frames = []
    for n in names:
        w = urllib.parse.quote(f"market_and_exchange_names='{n}'")
        rows = []
        off = 0
        while True:
            chunk = _get(f"{BASE.format(dataset)}?$limit=50000&$offset={off}&$where={w}")
            if not chunk:
                break
            rows += chunk
            if len(chunk) < 50000:
                break
            off += 50000
        if rows:
            frames.append(pd.DataFrame(rows))
            print(f"  {n}: {len(rows)} rows")
    if not frames:
        return pd.DataFrame()
    d = pd.concat(frames, ignore_index=True)
    d.to_parquet(cache)
    return d


def load_product(prod: str) -> pd.DataFrame:
    ds, names, _ = PRODUCTS[prod]
    d = fetch(ds, names)
    if d.empty:
        return pd.DataFrame()
    d["date"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None).dt.normalize()
    if ds == TFF:
        lp_l, lp_s = "lev_money_positions_long", "lev_money_positions_short"
        dp_l, dp_s = "dealer_positions_long_all", "dealer_positions_short_all"
        am_l, am_s = "asset_mgr_positions_long", "asset_mgr_positions_short"
    else:
        lp_l, lp_s = "m_money_positions_long_all", "m_money_positions_short_all"
        dp_l, dp_s = "swap_positions_long_all", "swap__positions_short_all"
        am_l = am_s = None
    keep = {"date": d["date"], "oi": pd.to_numeric(d["open_interest_all"]),
            "lp_l": pd.to_numeric(d[lp_l]), "lp_s": pd.to_numeric(d[lp_s]),
            "dp_l": pd.to_numeric(d[dp_l]), "dp_s": pd.to_numeric(d[dp_s])}
    if am_l is not None:
        keep["am_l"] = pd.to_numeric(d[am_l]); keep["am_s"] = pd.to_numeric(d[am_s])
    out = pd.DataFrame(keep)
    out["src"] = d["market_and_exchange_names"].values
    out = out.sort_values("date")
    # prefer consolidated series on clashing dates
    out["pref"] = out["src"].str.contains("|".join(PREF)).astype(int)
    out = out.sort_values(["date", "pref"]).drop_duplicates("date", keep="last").drop(columns=["src", "pref"])
    out["date"] = out["date"].astype("datetime64[ns]")   # align with Sharadar ns dates
    return out.reset_index(drop=True)


def spot_px(tkr: str) -> pd.Series:
    from sharadar import prices as SP
    p = SP([tkr], adjust="raw")
    s = p.reset_index().set_index("date")["close"].astype(float).sort_index()
    s.index = pd.DatetimeIndex(s.index).as_unit("ns")   # normalize resolution
    return s


def study(prod: str, data: pd.DataFrame, px: pd.Series) -> dict:
    """Build weekly states + events for the pre-registered arms."""
    d = data.copy()
    d["date"] = pd.DatetimeIndex(d["date"]).as_unit("ns")
    d["lp"] = d["lp_l"] - d["lp_s"]
    d["dp"] = d["dp_l"] - d["dp_s"]
    d["lpp"] = d["lp"] / d["oi"]
    d["dpp"] = d["dp"] / d["oi"]
    if "am_l" in d.columns:
        d["amp"] = (d["am_l"] - d["am_s"]) / d["oi"]
    # spot as of the report date (signal = Friday close)
    s = px.reindex(px.index.union(d["date"])).ffill()
    d["px"] = s.reindex(d["date"]).values
    d = d.dropna(subset=["px", "lpp", "oi"])
    d = d[d["oi"] > 0]
    # percentiles of trailing 3y (156 obs, min 78 warmup)
    for col in ("lpp", "dpp"):
        d[f"{col}_pct"] = d[col].rolling(156, min_periods=78).apply(
            lambda x: (np.sum(x[:-1] < x[-1]) + 0.5 * np.sum(x[:-1] == x[-1])) / len(x[:-1]) if len(x) > 1 else np.nan,
            raw=True)
    # 20d high / low as of signal
    hp = px.rolling(20).max()
    lp20 = px.rolling(20).min()
    d["hi20"] = hp.reindex(d["date"]).values
    d["lo20"] = lp20.reindex(d["date"]).values
    # entry: first session close strictly AFTER the report is public (Fri 15:30) = next session close
    idx = px.index
    pos = idx.searchsorted(d["date"], side="right")
    ok = pos + 5 < len(idx)
    ent = pd.Series(idx[np.clip(pos, 0, len(idx) - 1)].values, index=d.index)
    ext1 = pd.Series([idx[p + 5] if p + 5 < len(idx) else pd.NaT for p in pos], index=d.index)
    ext2 = pd.Series([idx[p + 10] if p + 10 < len(idx) else pd.NaT for p in pos], index=d.index)
    d["ent"] = ent
    d["r1"] = px.reindex(ext1).values / px.reindex(ent).values - 1
    d["r2"] = px.reindex(ext2).values / px.reindex(ent).values - 1
    return d


def arms(d: pd.DataFrame) -> pd.DataFrame:
    E = []
    open_until = pd.Timestamp("1900-01-01")
    for _, r in d.iterrows():
        e = r["ent"]
        if e is pd.NaT or pd.isna(r["r1"]) or e <= open_until:
            continue
        tag = None
        if pd.notna(r["lpp_pct"]) and r["lpp_pct"] >= 0.90 and r["px"] <= 0.97 * r["hi20"]:
            tag = "A1_long_unwind"
        elif pd.notna(r["lpp_pct"]) and r["lpp_pct"] <= 0.10 and r["px"] >= 1.03 * r["lo20"]:
            tag = "A2_short_cover"
        elif pd.notna(r["dpp_pct"]):
            if r["dpp_pct"] >= 0.90:
                tag = "A3_dealer_hi"
            elif r["dpp_pct"] <= 0.10:
                tag = "A3_dealer_lo"
        if tag is not None:
            E.append(dict(prod=r.name if isinstance(r.name, str) else None, date=r["date"], ent=e,
                          tag=tag, r1=r["r1"], r2=r["r2"]))
            open_until = e  # one open event per product
    return pd.DataFrame(E)


def evaluate(E: pd.DataFrame, half_split: str) -> str:
    b = 1e4
    lines = []
    for tag in sorted(E["tag"].unique()):
        sub = E[E["tag"] == tag].copy()
        for h, col in (("1w", "r1"), ("2w", "r2")):
            x = sub.dropna(subset=[col]).copy()
            if h == "2w":
                continue  # secondary: computed below in aggregate
            if len(x) < 15:
                lines.append(f"  {tag:16s} {h} n={len(x):3d}  (too few)")
                continue
            x["dir"] = -1.0 if tag in ("A1_long_unwind", "A3_dealer_hi") else 1.0
            x["net"] = x["dir"] * x[col] - 2e-4  # 1bp/side round trip
            x["shk"] = x["dir"] * x[col] - 6e-4  # 3bp/side shock
            # day (entry-date) clustering
            g = x.groupby("ent")["net"].mean()
            t = g.mean() / g.std() * np.sqrt(len(g))
            med = x["net"].median()
            ex5 = x.nsmallest(max(len(x) - 5, 1), "net")["net"].mean()
            # halves by event count
            x = x.sort_values("ent")
            k = len(x) // 2
            h1, h2 = x["net"].iloc[:k], x["net"].iloc[k:]
            lines.append(
                f"  {tag:16s} {h} n={len(x):3d} net={x['net'].mean()*b:6.1f}bp t={t:5.2f} "
                f"med={med*b:6.1f} ex5={ex5*b:6.1f} halves={h1.mean()*b:6.1f}/{h2.mean()*b:6.1f} "
                f"shock3bp={x['shk'].mean()*b:6.1f} hit={(x['net']>0).mean()*100:3.0f}%")
    return "\n".join(lines)


def main():
    parts = ["Study COTX: COT positioning -> forced unwind / forced cover (weekly, ETF proxies)",
             "LP=leveraged funds/MoneyMgmt, DP=dealers/swap, pctile of trailing 3y; pullback/bounce confirm",
             "net at 1bp/side; shock=3bp/side; entry = first session close after report is public", ""]
    allE = []
    for prod in PRODUCTS:
        d = load_product(prod)
        if d.empty:
            parts.append(f"===== {prod}: NO DATA"); continue
        px = spot_px(PRODUCTS[prod][2])
        D = study(prod, d, px)
        E = arms(D)
        E["prod"] = prod
        allE.append(E)
        parts.append(f"===== {prod}: reports {d['date'].min().date()}..{d['date'].max().date()} n={len(d)} events={len(E)} "
                     f"({E['tag'].value_counts().to_dict() if len(E) else ''})")
    E = pd.concat(allE, ignore_index=True) if allE else pd.DataFrame()
    if not E.empty:
        parts.append("\nPOOLED ARMS (judged, 1w):")
        parts.append(evaluate(E, None))
        # secondary: 2w
        sub = E.copy()
        sub["net2"] = sub.apply(lambda r: (-1 if r["tag"] in ("A1_long_unwind", "A3_dealer_hi") else 1) * r["r2"] - 2e-4, axis=1)
        sub = sub.dropna(subset=["net2"])
        parts.append("\nSECONDARY 2w:")
        for tag, df in sub.groupby("tag"):
            x = df.groupby("ent")["net2"].mean()
            t = x.mean() / x.std() * np.sqrt(len(x)) if x.std() > 0 else np.nan
            parts.append(f"  {tag:16s} n={len(x):3d} mean={x.mean()*1e4:6.1f}bp t={t:5.2f}")
        # per-product diagnostics for A1/A2 (crowding must not be one product)
        parts.append("\nPER-PRODUCT (A1+A2 only):")
        c = E[E.tag.isin(["A1_long_unwind", "A2_short_cover"])].copy()
        c["net"] = c.apply(lambda r: (-1 if r["tag"] == "A1_long_unwind" else 1) * r["r1"] - 2e-4, axis=1)
        for p, x in c.groupby("prod"):
            gg = x.groupby("ent")["net"].mean()
            t = gg.mean() / gg.std() * np.sqrt(len(gg)) if len(gg) > 2 and gg.std() > 0 else np.nan
            parts.append(f"  {p:3s} n={len(gg):3d} net={gg.mean()*1e4:6.1f}bp t={t if pd.isna(t) else round(t,2)}")
    text = "\n".join(parts) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
