"""Round 32 B1 (rules: round1_prose.md Round 32 amendment, cf5d8cf): reverse-split round-up, deal by deal.

Buy 1 share at the raw close of S (the last session before the split's ex-date E). If the issuer rounds fractional
post-split shares up at the holder level, the holder ends with 1 post-split share (~N x the price); if it pays cash
in lieu, the holder gets P_E / N.

    PYTHONPATH=. .venv/bin/python -m research.sim.roundup fetch|report
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np
import pandas as pd

from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTF = ROOT / "data/research/program/roundup_out.txt"
UP_Q = ['"rounded up to the nearest whole share" "reverse stock split"',
        '"rounded up to the next whole share" "reverse stock split"',
        '"round up to the nearest whole share" "reverse stock split"',
        '"rounded up to the nearest whole number" "reverse stock split"',
        '"rounded up to the nearest share" "reverse stock split"']
PL_Q = ['"participant level" "reverse stock split" "rounded up"',
        '"DTC participant" "reverse stock split" "rounded up"',
        '"Cede" "reverse stock split" "rounded up"']
UP = re.compile(r"round(?:ed)? up[^.]{0,80}?(?:whole|full|next|nearest) (?:share|number)|"
                r"(?:fraction|fractional)[^.]{0,200}?round(?:ed)? up", re.I)
PL = re.compile(r"participant level|DTC participant|at the participant|Cede ?& ?Co", re.I)


def hits(qs):
    out = []
    for q in qs:
        out += F.fts_years(q, "", 2015, 2026)
    return list({r["id"]: r for r in out}.values())


def norm(name: str) -> str:
    n = re.sub(r"\(.*", "", name).upper()
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    n = re.sub(r"\b(INC|CORP|CORPORATION|CO|LTD|LIMITED|PLC|HOLDINGS?|GROUP|THE|NV|SA|AG|LLC|LP|COMPANY|TRUST)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def alpaca_names() -> dict[str, str]:
    f = F._cache("alpaca_asset_names.json")
    if f.exists():
        import json
        return json.load(open(f))
    import json
    from alpaca.trading.enums import AssetClass, AssetStatus
    from alpaca.trading.requests import GetAssetsRequest
    from swingtrader.daily.marketdata import _clients
    _, tr = _clients()
    m = {}
    for st in (AssetStatus.ACTIVE, AssetStatus.INACTIVE):
        for a in tr.get_all_assets(GetAssetsRequest(status=st, asset_class=AssetClass.US_EQUITY)):
            m[a.symbol] = a.name or ""
    json.dump(m, open(f, "w"))
    return m


def events():
    RS = F.reverse_splits()
    RS["N"] = RS.old / RS.new
    RS = RS[(RS.N >= 2) & (RS.N < 1000) & (RS.ex >= "2016-01-01")].copy()
    U, P = hits(UP_Q), hits(PL_Q)
    names = alpaca_names()
    by_tk, by_nm = {}, {}
    for kind, H in (("up", U), ("pl", P)):
        for h in H:
            for nm in h["names"]:
                for t in F.ticker_of(nm):
                    by_tk.setdefault(t.replace("-", "."), []).append((kind, h))
                by_nm.setdefault(norm(nm), []).append((kind, h))
    rows = []
    for r in RS.itertuples():
        cand = by_tk.get(r.symbol, []) + [x for x in by_nm.get(norm(names.get(r.symbol, "")) or "~", [])
                                         if x not in by_tk.get(r.symbol, [])]
        win = [(k, h) for k, h in cand if r.ex - pd.Timedelta(days=90) <= pd.Timestamp(h["date"]) < r.ex]
        rows.append(dict(symbol=r.symbol, ex=r.ex, N=r.N, n_up=sum(k == "up" for k, _ in win),
                         n_pl=sum(k == "pl" for k, _ in win), hits=[(k, h["adsh"], h["id"], h["date"], h["ciks"][0]) for k, h in win]))
    return pd.DataFrame(rows)


def fetch():
    E = events()
    print(len(E), "reverse splits;", (E.n_up > 0).sum(), "with a round-up hit in the 90 days before E;", (E.n_pl > 0).sum(), "participant-level")
    q = E[E.n_up > 0]
    F.raw_bars(sorted(q.symbol.unique()))
    for r in q.itertuples():                              # headers (acceptance time) + the matched documents
        for k, adsh, i, d, cik in r.hits:
            F.hdr(cik, adsh)
            F.doc(cik, adsh, i.split(":", 1)[1])
    E.to_pickle(F._cache("roundup_events.pkl"))


def deals(E: pd.DataFrame) -> pd.DataFrame:
    q = E[E.n_up > 0]
    bars = F.raw_bars(sorted(q.symbol.unique()))
    out = []
    for r in q.itertuples():
        b = bars.get(r.symbol)
        if b is None or not len(b):
            out.append(dict(symbol=r.symbol, ex=r.ex, N=r.N, status="no bars")); continue
        b = b.sort_index(); b.index = pd.to_datetime(b.index)
        pre, post = b[b.index < r.ex], b[b.index >= r.ex]
        if not len(pre) or not len(post) or post.index[0] > r.ex + pd.Timedelta(days=7):
            out.append(dict(symbol=r.symbol, ex=r.ex, N=r.N, status="no bars at S/E")); continue
        S = pre.index[-1]
        cut = S + pd.Timedelta(hours=15, minutes=30)
        up_ok, pl, txt_up = False, False, False
        for k, adsh, i, d, cik in r.hits:
            h = F.hdr(cik, adsh)
            t = F.accepted_et(h)
            if t is None or t > cut:
                continue
            body = F.doc(cik, adsh, i.split(":", 1)[1])
            if k == "pl" or PL.search(body):
                pl = True
            if k == "up":
                up_ok = True
                txt_up |= bool(UP.search(body))
        ps, pe = float(pre.close.iloc[-1]), float(post.close.iloc[0])
        pe5 = float(post.close.iloc[min(5, len(post) - 1)])
        status = ("participant level" if pl else "ok") if up_ok else "filed too late"
        out.append(dict(symbol=r.symbol, ex=r.ex, S=S, N=r.N, status=status, regex_up=txt_up, ps=ps, pe=pe, pe5=pe5,
                        ratio_chk=pe / ps / r.N, up=pe - ps, up5=pe5 - ps, cash=pe / r.N - ps))
    return pd.DataFrame(out)


def report():
    E = pd.read_pickle(F._cache("roundup_events.pkl"))
    D = deals(E)
    f = open(OUTF, "w")

    def log(*a):
        x = " ".join(str(i) for i in a); print(x); f.write(x + "\n")
    log(f"B1 reverse-split round-up. Alpaca reverse splits 2016-01..2026-09 with 2 <= N < 1000: {len(E)}; "
        f"with a round-up FTS hit in [E-90d, E): {(E.n_up > 0).sum()}")
    log(D.status.value_counts().to_string())
    ok = D[D.status == "ok"].copy()
    bad = ok[(ok.ratio_chk < 0.33) | (ok.ratio_chk > 3)]
    log(f"price check P_E / P_S / N outside [0.33, 3] (split not in raw bars or wrong ratio): {len(bad)} -> listed, excluded")
    ok = ok[(ok.ratio_chk >= 0.33) & (ok.ratio_chk <= 3)]
    ok["y"] = ok.ex.dt.year
    log(f"\nqualifying deals: {len(ok)} (doc regex confirms a round-up clause in {ok.regex_up.mean():.0%})")
    g = ok.groupby("y").agg(n=("up", "size"), up_mean=("up", "mean"), up_med=("up", "median"), up_sum=("up", "sum"),
                            up5_sum=("up5", "sum"), cash_sum=("cash", "sum"), pos=("up", lambda x: (x > 0).mean()),
                            cost=("ps", "sum"))
    log(g.round(2).to_string())
    for lab, x in (("all", ok), ("2024-26", ok[ok.y >= 2024])):
        brk = -x.cash.sum() / max(x.up.sum() - x.cash.sum(), 1e-9)
        log(f"[{lab}] n {len(x)}  rounded: mean ${x.up.mean():.2f} median ${x.up.median():.2f} worst ${x.up.min():.2f} "
            f"> 0 {(x.up > 0).mean():.0%}; at E+5 mean ${x.up5.mean():.2f} worst ${x.up5.min():.2f}; cash-in-lieu: mean ${x.cash.mean():.2f} "
            f"worst ${x.cash.min():.2f}; break-even P(round up) {brk:.1%}; capital per deal median ${x.ps.median():.2f}")
    yrs = ok[ok.y.between(2023, 2025)]
    log(f"per account per year (2023-25 average): rounded {yrs.up.sum()/3:,.0f} $/yr on {len(yrs)/3:.0f} deals; "
        f"E+5 {yrs.up5.sum()/3:,.0f}; if none rounded {yrs.cash.sum()/3:,.0f}")
    log("\nworst 10 (rounded, at E):"); log(ok.nsmallest(10, "up")[["symbol", "ex", "N", "ps", "pe", "pe5", "up", "up5"]].round(3).to_string())
    log("\nbest 10:"); log(ok.nlargest(10, "up")[["symbol", "ex", "N", "ps", "pe", "pe5", "up", "up5"]].round(3).to_string())
    D.to_csv(ROOT / "data/research/program/roundup_deals.csv", index=False)


if __name__ == "__main__":
    {"fetch": fetch, "report": report}[sys.argv[1]]()
