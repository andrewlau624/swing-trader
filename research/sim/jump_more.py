"""Jump hunt, remaining feasible ideas (rules written before any outcome; jump_ideas.md):

- H20: a subreddit for the ticker is created (Arctic Shift subreddit metadata: display name == ticker, or ticker + one of
  stock/stocks/army/squeeze/investors/gang/holders/official), for tickers with >= 20 small-sub/WSB mentions; event = the
  first such subreddit's creation (fd_of(created_utc)); ADV$ < $20M at the time.
- H19: a theme's Wikipedia article (THEME_PAGES) at >= 3x its trailing-90-day median views (first in 60 days per
  theme) -> every small cap (ADV$ < $20M) whose 8-K or 10-K mentioned that theme (jump_d4 FTS hits) in the prior 730
  days; fd = the spike day.
- C9: the same, with the theme's Benzinga headline count over 5 days >= 3x its trailing-90-day 5-day mean.
- R2-24: an issuer's modified Dutch auction tender reports final results (FTS SC TO-I/A "final results" "modified
  Dutch auction"); first per company in 365 days; ADV$ < $20M.
- R4-7: an 8-K adopting advance-notice / exclusive-forum bylaws (FTS 8-K "Item 5.03" "advance notice") within 60 days
  after a Schedule 13D on the company (EDGAR form.idx SC 13D rows mapped by CIK); ADV$ < $20M.
- R4-10: >= 3 officer/director open-market purchase filings within 10 days at a company that filed an R4-5 8-K
  ("strategic alternatives" + "financial advisor") in the prior 180 days; fd = the third filing.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_more h20|h19|c9|r2_24|r4_7|r4_10
"""
from __future__ import annotations

import json
import sys
import time
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

from . import event_fetch as F
from .jump_common import ROOT, cik_sym, fd_of, first_in, resolve, save, small_only

OUT = ROOT / "data/research/jump"
UA = {"User-Agent": "swing-trader personal research (jump hunt)"}
SUFFIX = ("", "stock", "stocks", "army", "squeeze", "investors", "gang", "holders", "official")
THEME_PAGES = {'"blockchain"': "Blockchain", '"bitcoin"': "Bitcoin", '"metaverse"': "Metaverse",
               '"artificial intelligence"': "Artificial_intelligence", '"generative AI"': "Generative_artificial_intelligence",
               '"quantum computing"': "Quantum_computing", '"cannabidiol"': "Cannabidiol", '"psilocybin"': "Psilocybin",
               '"small modular reactor"': "Small_modular_reactor", '"eVTOL"': "EVTOL", '"lithium"': "Lithium",
               '"uranium"': "Uranium", '"hydrogen fuel"': "Hydrogen_fuel", '"GLP-1"': "Glucagon-like_peptide-1"}
HEAD = {'"blockchain"': "blockchain", '"bitcoin"': "bitcoin", '"metaverse"': "metaverse", '"artificial intelligence"': r"\bAI\b|artificial intelligence",
        '"generative AI"': "generative AI", '"quantum computing"': "quantum", '"cannabidiol"': r"CBD|cannabidiol",
        '"psilocybin"': "psilocybin|psychedelic", '"small modular reactor"': r"SMR|small modular", '"eVTOL"': "eVTOL",
        '"lithium"': "lithium", '"uranium"': "uranium", '"hydrogen fuel"': "hydrogen", '"GLP-1"': r"GLP-1|semaglutide|tirzepatide"}


# ---- H20 ------------------------------------------------------------------------------------------------------------
def h20() -> pd.DataFrame:
    from .jump_reddit import M
    X = M()
    cnt = X.sym.value_counts()
    syms = sorted(cnt[cnt >= 20].index)
    f = OUT / "subreddits.json"
    got = json.load(open(f)) if f.exists() else {}
    for s in syms:
        if s in got:
            continue
        try:
            r = requests.get("https://arctic-shift.photon-reddit.com/api/subreddits/search",
                             params={"subreddit_prefix": s, "limit": 100}, headers=UA, timeout=60)
            got[s] = [(x.get("display_name"), x.get("created_utc")) for x in (r.json().get("data") or [])]
        except (requests.RequestException, ValueError):
            got[s] = None
        time.sleep(0.5)
        if len(got) % 100 == 0:
            json.dump(got, open(f, "w"))
    json.dump(got, open(f, "w"))
    rows = []
    for s, subs in got.items():
        if not subs:
            continue
        ok = [c for n, c in subs if c and str(n).lower() in {(s + x).lower() for x in SUFFIX}]
        if ok:
            rows.append(dict(sym=s, t=pd.Timestamp(min(ok), unit="s", tz="UTC")))
    E = pd.DataFrame(rows)
    E["fd"] = fd_of(E.t)
    return small_only(E[E.fd >= "2016-01-01"][["sym", "fd"]], 20e6)


# ---- H19 / C9 -------------------------------------------------------------------------------------------------------
def _theme_members() -> pd.DataFrame:
    from .jump_d4 import hits
    H = pd.concat([hits("8-K"), hits("10-K")])
    H = resolve(H.rename(columns={"date": "fd"}))
    return H[["theme", "sym", "fd"]]


def _theme_events(spikes: dict) -> pd.DataFrame:
    Mb = _theme_members()
    rows = []
    for th, days in spikes.items():
        G = Mb[Mb.theme == th]
        for d in days:
            S = G[(G.fd <= d) & (G.fd >= d - pd.Timedelta(days=730))].sym.unique()
            rows += [dict(sym=s, fd=d) for s in S]
    E = pd.DataFrame(rows).drop_duplicates()
    return small_only(E[E.fd >= "2016-01-01"], 20e6)


def h19() -> pd.DataFrame:
    spikes = {}
    for th, page in THEME_PAGES.items():
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{quote(page, safe='')}/daily/20150701/20260930"
        try:
            j = requests.get(url, headers=UA, timeout=60).json()
        except ValueError:                                  # missing article: no spikes for this theme
            print("no pageviews for", page, flush=True)
            j = {}
        v = pd.Series({pd.Timestamp(x["timestamp"][:8]): x["views"] for x in j.get("items", [])}, dtype=float).sort_index()
        if not len(v):
            continue
        v = v.asfreq("D", fill_value=0)
        med = v.rolling(90, min_periods=90).median().shift(1)
        d = v.index[(v >= 3 * med) & (med > 0)]
        spikes[th] = list(first_in(pd.DataFrame(dict(sym=th, fd=d)), 60).fd)
    return _theme_events(spikes)


def c9() -> pd.DataFrame:
    from .jump_news import news
    L = news()[["id", "fd", "headline"]].drop_duplicates("id")
    spikes = {}
    for th, pat in HEAD.items():
        n = L[L.headline.str.contains(pat, case=False, regex=True)].groupby("fd").size().asfreq("D", fill_value=0)
        r5 = n.rolling(5).sum()
        base = r5.rolling(90, min_periods=90).mean().shift(5)
        d = r5.index[(r5 >= 3 * base) & (base > 0) & (r5 >= 5)]
        spikes[th] = list(first_in(pd.DataFrame(dict(sym=th, fd=d)), 60).fd)
    return _theme_events(spikes)


# ---- R2-24, R4-7, R4-10 ---------------------------------------------------------------------------------------------
def r2_24() -> pd.DataFrame:
    from .jump_edgar import _fts
    H = _fts('"final results" "modified Dutch auction"', "SC TO-I/A", 2015)
    H = H[H.form == "SC TO-I/A"].rename(columns={"date": "fd"})
    E = resolve(H[H.fd >= "2016-01-01"])
    return small_only(first_in(E[["sym", "fd"]], 365), 20e6)


def r4_7() -> pd.DataFrame:
    from .jump_edgar import _fts
    I = pd.concat([F.full_index(y, q) for y in range(2015, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)])
    D13 = I[I.form == "SC 13D"].copy()
    cs = cik_sym()
    D13["sym"] = D13.cik.astype(str).map(cs)
    D13 = D13.dropna(subset=["sym"])
    d13 = {s: np.sort(pd.to_datetime(g.date).to_numpy()) for s, g in D13.groupby("sym")}
    H = _fts('"Item 5.03" "advance notice"', "8-K", 2015)
    H = resolve(H[H.form == "8-K"].rename(columns={"date": "fd"}))
    keep = [((a := d13.get(r.sym)) is not None) and ((a <= r.fd.to_datetime64()) & (a >= (r.fd - pd.Timedelta(days=60)).to_datetime64())).any()
            for r in H.itertuples()]
    E = first_in(H[keep][["sym", "fd"]], 365)
    return small_only(E[E.fd >= "2016-01-01"], 20e6)


def r4_10() -> pd.DataFrame:
    from .jump_insider import buys
    R = pd.read_parquet(ROOT / "data/research/program/events_jump_r4_5.parquet")
    rv = {s: np.sort(g.fd.to_numpy()) for s, g in R.groupby("sym")}
    B = buys()
    B = B[B.insider & (B.usd >= 1e3)].dropna(subset=["sym"]).sort_values("fd")
    rows = []
    for s, g in B.groupby("sym"):
        a = rv.get(s)
        if a is None:
            continue
        d = g.fd.to_numpy()
        for i in range(2, len(d)):
            if (d[i] - d[i - 2]) <= np.timedelta64(10, "D") and ((a <= d[i]) & (a >= d[i] - np.timedelta64(180, "D"))).any():
                rows.append(dict(sym=s, fd=pd.Timestamp(d[i])))
    return first_in(pd.DataFrame(rows, columns=["sym", "fd"]), 180)


if __name__ == "__main__":
    what = sys.argv[1]
    save(globals()[what](), what)
