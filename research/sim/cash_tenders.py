"""Round 32 B3 (rules: round1_prose.md Round 32 amendment, cf5d8cf): cash tender offers by acquirers (SC TO-T), deal by deal.

Entry: the close of the first session after the original SC TO-T's filing date. Exit: the last raw close if the
target's bars end within 250 sessions (completion at the final price); otherwise failed: the close 5 sessions after
the first close < 0.85 x offer, else session 250.

    PYTHONPATH=. .venv/bin/python -m research.sim.cash_tenders fetch|report
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np
import pandas as pd

from . import event_fetch as F
from .roundup import alpaca_names, norm

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTF = ROOT / "data/research/program/cash_tenders_out.txt"
PRICE = re.compile(r"\$\s?(\d[\d,]*\.\d{2,4}) (?:per|for each) (?:share|Share)[^.]{0,120}?net to the seller in cash", re.I)
SYM = re.compile(r"under the (?:trading |ticker )?symbols? [\"“”']{1,2}([A-Z][A-Z.]{0,6})[\"“”']{1,2}")


def offers() -> pd.DataFrame:
    H = F.fts_years('"net to the seller in cash"', "SC TO-T", 2016, 2026)
    by = {}
    for h in H:
        by.setdefault(h["adsh"], []).append(h)
    rows = []
    for adsh, hs in by.items():
        h0 = hs[0]
        hd = F.hdr(h0["ciks"][0], adsh)
        subj = hd.get("subject")
        name = next((n for c, n in zip(h0["ciks"], h0["names"]) if c.lstrip("0") == subj), h0["names"][0])
        price, sym = None, None
        for h in hs:
            t = F.doc(h["ciks"][0], adsh, h["id"].split(":", 1)[1])
            m = PRICE.search(t)
            if m and price is None:
                price = float(m.group(1).replace(",", ""))
            s = SYM.search(t)
            if s and sym is None:
                sym = s.group(1)
        tk = F.ticker_of(name)
        rows.append(dict(adsh=adsh, date=pd.Timestamp(h0["date"]), subject=subj, name=name, price=price,
                         sym=sym or (tk[0] if tk else None), accepted=hd.get("accepted")))
    O = pd.DataFrame(rows).sort_values("date")
    # one deal per subject company per 120 days (competing / re-filed originals keep the first)
    keep, last = [], {}
    for r in O.itertuples():
        k = r.subject or r.name
        if k in last and (r.date - last[k]).days < 120:
            continue
        last[k] = r.date; keep.append(r.Index)
    return O.loc[keep]


def fetch():
    O = offers()
    names = alpaca_names()
    nm = {}
    for s, n in names.items():
        nm.setdefault(norm(n), []).append(s)
    O["sym2"] = [s if s else (nm.get(norm(n)) or [None])[0] for s, n in zip(O.sym, O.name)]
    O.to_pickle(F._cache("cash_tender_offers.pkl"))
    print(len(O), "deals;", O.price.notna().sum(), "with a price;", O.sym2.notna().sum(), "with a symbol")
    F.raw_bars(sorted(O.sym2.dropna().unique()))


def deals() -> pd.DataFrame:
    O = pd.read_pickle(F._cache("cash_tender_offers.pkl"))
    O = O[(O.date >= "2016-01-01") & (O.date <= "2026-03-31")]
    bars = F.raw_bars(sorted(O.sym2.dropna().unique()))
    out = []
    for r in O.itertuples():
        base = dict(date=r.date, sym=r.sym2, name=r.name[:40], offer=r.price)
        b = bars.get(r.sym2) if r.sym2 else None
        if r.price is None or b is None or not len(b):
            out.append({**base, "status": "no price" if r.price is None else "no bars"}); continue
        b = b.sort_index(); b.index = pd.to_datetime(b.index)
        pre = b[b.index <= r.date]
        post = b[b.index > r.date]
        if len(post) < 2 or not len(pre) or (post.index[0] - r.date).days > 7:
            out.append({**base, "status": "no bars"}); continue
        ent = float(post.close.iloc[0])
        if not 0.5 < ent / r.price < 1.3:                      # wrong symbol / unit (e.g. ADS ratio): listed, excluded
            out.append({**base, "status": "price mismatch", "entry": ent}); continue
        adv = float((pre.close * pre.volume).tail(20).mean()) if len(pre) >= 5 else np.nan
        P = post.iloc[1:]
        # gap: delisted = bars end and no bar for 30 days after
        gap = P.index.to_series().diff().dt.days
        end_i = int(np.argmax(gap.values > 30)) - 1 if (gap > 30).any() else len(P) - 1
        last = P.index[end_i]
        n_sess = end_i + 1
        if n_sess <= 250 and last < pd.Timestamp("2026-09-15"):
            ex, exd, st = float(P.close.iloc[end_i]), last + pd.Timedelta(days=3), "completed"
        else:
            Q = P.iloc[:250]
            hit = np.where(Q.close.values < 0.85 * r.price)[0]
            j = min(hit[0] + 5, len(Q) - 1) if len(hit) else len(Q) - 1
            ex, exd, st = float(Q.close.iloc[j]), Q.index[j], "failed" if (len(hit) or n_sess > 250) else "open"
        days = max((exd - post.index[0]).days, 1)
        out.append({**base, "status": st, "entry": ent, "exit": ex, "ret": ex / ent - 1, "days": days,
                    "spread0": r.price / ent - 1, "adv": adv})
    return pd.DataFrame(out)


def report():
    D = deals()
    f = open(OUTF, "w")

    def log(*a):
        x = " ".join(str(i) for i in a); print(x); f.write(x + "\n")
    log(f"B3 cash tender offers (SC TO-T originals 2016-01..2026-03): {len(D)} deals")
    log(D.status.value_counts().to_string())
    X = D[D.status.isin(["completed", "failed"])].copy()
    X["fin"] = 0.12 * X.days / 365
    X["net"] = X.ret - X.fin
    X["ann"] = (1 + X.ret) ** (365 / X.days) - 1
    X["size"] = pd.cut(X.adv, [0, 5e6, 5e7, np.inf], labels=["small <$5M", "$5-50M", ">$50M"])
    X["y"] = X.date.dt.year
    for lab, g in [("all", X)] + [(str(k), v) for k, v in X.groupby("size", observed=True)]:
        log(f"[{lab}] n {len(g)}  failed {(g.status == 'failed').mean():.0%}  ret mean {g.ret.mean():+.2%} median {g.ret.median():+.2%} "
            f"worst {g.ret.min():+.1%}  > 0 {(g.ret > 0).mean():.0%}  days median {g.days.median():.0f}  "
            f"net of 12% fin mean {g.net.mean():+.2%}  initial spread median {g.spread0.median():+.2%}")
    log("\nby year (all): " + " ".join(f"{y}: n{len(g)} {g.ret.mean():+.2%}" for y, g in X.groupby("y")))
    log("\nworst 10:"); log(X.nsmallest(10, "ret")[["date", "sym", "name", "offer", "entry", "exit", "ret", "days", "status", "adv"]].round(3).to_string())
    # book use: capital C per deal; deals overlap little at ~1-2 months; $/yr = sum of P&L / years at a per-deal size
    yrs = (X.date.max() - X.date.min()).days / 365
    for E in (2300, 10000, 25000):
        per = min(E, 5000) if E > 2300 else E
        log(f"${E/1e3:.1f}k account, one deal at a time at ${per:,.0f}: ~{len(X)/yrs:.0f} deals/yr available; "
            f"mean P&L/deal ${per*X.ret.mean():,.0f}, net of fin ${per*X.net.mean():,.0f}")
    D.to_csv(ROOT / "data/research/program/cash_tender_deals.csv", index=False)


if __name__ == "__main__":
    {"fetch": fetch, "report": report}[sys.argv[1]]()
