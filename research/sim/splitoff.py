"""Round 32 B2 (rules: round1_prose.md Round 32 amendment, cf5d8cf): split-off exchange offers with odd-lot priority.

Entry: buy up to 99 parent shares at the close 5 sessions before expiry. Odd lots are accepted in full; each parent
share becomes `final_ratio` received shares, valued at the received stock's close on the first session after expiry.
Terms: research/data/splitoff_terms.csv (read from the offers' filings; no prices).

    PYTHONPATH=. .venv/bin/python -m research.sim.splitoff
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
TERMS = ROOT / "research/data/splitoff_terms.csv"
ALIAS = {"PARA": ["CBS"], "APY": ["APY", "CHX"], "ETM": ["ETM", "AUD"], "AIMC": ["AIMC"], "CHNG": ["CHNG"], "BXLT": ["BXLT"]}
SIZES = (2300, 10000, 25000)


def bars_for(sym: str) -> pd.Series:
    """Raw closes, joined across a ticker change (Apergy APY -> ChampionX CHX, Entercom ETM -> Audacy AUD)."""
    parts = []
    for s in ALIAS.get(sym, [sym]):
        b = F.raw_bars([s], tag="raw").get(s)
        if b is not None and len(b):
            c = b.close.copy(); c.index = pd.to_datetime(c.index)
            parts.append(c)
    if not parts:
        return pd.Series(dtype=float)
    c = pd.concat(parts).sort_index()
    return c[~c.index.duplicated()]


def main():
    T = pd.read_csv(TERMS)
    T = T[T.final_ratio.notna()]
    rows = []
    for r in T.itertuples():
        P, R = bars_for(r.parent_ticker), bars_for(r.received_ticker)
        exp = pd.Timestamp(r.expiry_date)
        pre = P[P.index <= exp]
        if len(pre) < 6 or not len(R):
            rows.append(dict(parent=r.parent_ticker, recv=r.received_ticker, exp=exp.date(), status="no bars")); continue
        ent_d, ent = pre.index[-6], float(pre.iloc[-6])
        Rp = R[R.index > exp]
        ex_d, rx = Rp.index[0], float(Rp.iloc[0])
        val = r.final_ratio * rx
        # sanity: value per parent share at the last pre-expiry session should be ~ (1 + discount) x parent
        chk = r.final_ratio * float(R[R.index <= exp].iloc[-1]) / float(pre.iloc[-1]) if len(R[R.index <= exp]) else np.nan
        g = val / ent - 1
        d = dict(parent=r.parent_ticker, recv=r.received_ticker, exp=exp.date(), entry_d=ent_d.date(), entry=ent,
                 exit_d=ex_d.date(), recv_px=rx, ratio=r.final_ratio, cap=r.upper_limit_in_effect, value=val, gain=g,
                 chk_at_expiry=chk, days=(ex_d - ent_d).days)
        for E in SIZES:
            sh = min(99, int(E // ent))
            d[f"usd_{E}"] = sh * (val - ent)
        d["usd_99"] = 99 * (val - ent); d["cap99"] = 99 * ent
        rows.append(d)
    D = pd.DataFrame(rows)
    out = ROOT / "data/research/program/splitoff_out.txt"
    pd.set_option("display.width", 250)
    lines = [f"B2 split-off exchange offers with odd-lot priority: {len(T)} completed 2016-25 (all oversubscribed, all odd-lot priority)",
             D.round(4).to_string(),
             f"\ngain per parent share: mean {D.gain.mean():+.2%} median {D.gain.median():+.2%} worst {D.gain.min():+.2%} > 0 {(D.gain > 0).mean():.0%}"
             f" | upper limit in effect: {D[D.cap == 'Y'].gain.mean():+.2%} (n {(D.cap == 'Y').sum()}) vs not {D[D.cap == 'N'].gain.mean():+.2%}",
             f"value check (ratio x received / parent at the last pre-expiry close): median {D.chk_at_expiry.median():.3f}"]
    yrs = 10.0
    for E in SIZES:
        lines.append(f"${E/1e3:.1f}k: mean ${D[f'usd_{E}'].mean():,.0f}/deal, worst ${D[f'usd_{E}'].min():,.0f}, ~{len(D)/yrs:.1f} deals/yr -> ~${D[f'usd_{E}'].sum()/yrs:,.0f}/yr")
    lines.append(f"99 shares: mean ${D.usd_99.mean():,.0f}/deal on median capital ${D.cap99.median():,.0f}, ~${D.usd_99.sum()/yrs:,.0f}/yr")
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    D.to_csv(ROOT / "data/research/program/splitoff_deals.csv", index=False)


if __name__ == "__main__":
    main()
