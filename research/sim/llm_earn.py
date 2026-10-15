"""Study LLM-EARN (N 886): an LLM reads the pre-open earnings news; post-cutoff window 2026-01..2026-09 only.

    PYTHONPATH=. .venv/bin/python -m research.sim.llm_earn events    # earnings headlines -> events.parquet
    PYTHONPATH=. .venv/bin/python -m research.sim.llm_earn prompts [w W]  # news text -> prompts_<w>.jsonl (+ placebo)
    PYTHONPATH=. .venv/bin/python -m research.sim.llm_earn bars      # 09:35 price per event (raw SIP 1-min)
    # scoring runs on the server (key lives there): research/sim/llm_earn_score.py prompts.jsonl out.jsonl
    PYTHONPATH=. .venv/bin/python -m research.sim.llm_earn           # judge -> llm_earn_out.txt
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

import numpy as np
import pandas as pd

from . import ssr_rd as m

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/llm_earn"
OUT = pathlib.Path(__file__).with_name("llm_earn_out.txt")
START, END = "2026-01-05", "2026-09-30"
TZ = "America/New_York"
EPS = re.compile(r"(\bEPS\b.*\b(Beats|Misses|In-Line)\b)|(\bQ[1-4]\b.*\bEPS\b)", re.I)
COST = 0.001


def _news():
    sys.path.insert(0, str(ROOT))
    from alpaca.data.historical.news import NewsClient
    from swingtrader.config import require_alpaca_keys
    k, s = require_alpaca_keys()
    return NewsClient(k, s)


def _get(c, **kw):
    from alpaca.data.requests import NewsRequest
    for a in range(6):
        try:
            r = c.get_news(NewsRequest(limit=5000, **kw))
            return r.df.reset_index() if len(r.df) else pd.DataFrame()
        except Exception as ex:  # noqa: BLE001
            print("err", str(ex)[:100], flush=True)
            time.sleep(5 * (a + 1))
    return pd.DataFrame()


def sessions() -> pd.DatetimeIndex:
    s = m.load()  # trading calendar = AAPL's Sharadar sessions
    d = pd.DatetimeIndex(sorted(s.loc[s.ticker == "AAPL", "date"].unique()))
    return d


def events():
    D.mkdir(parents=True, exist_ok=True)
    c = _news()
    days = sessions()
    days = days[(days >= pd.Timestamp(START) - pd.Timedelta(days=7)) & (days <= END)]
    rows = []
    for prev, T in zip(days[:-1], days[1:]):
        if T < pd.Timestamp(START):
            continue
        st = (prev + pd.Timedelta(hours=16)).tz_localize(TZ)
        en = (T + pd.Timedelta(hours=9, minutes=20)).tz_localize(TZ)
        x = _get(c, start=st, end=en, include_content=False)
        if not len(x):
            continue
        x = x[x.headline.str.contains(EPS) & (x.symbols.map(len) == 1)]
        for r in x.itertuples():
            rows.append(dict(ticker=r.symbols[0], T=T, prev=prev, created=r.created_at, headline=r.headline))
        print(T.date(), len(x), flush=True)
    e = pd.DataFrame(rows)
    b = m.load()
    g = b.groupby("ticker", sort=False)
    b["praw"] = g.closeunadj.shift(1)
    b["adv"] = (b.close * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=15).mean())
    b["gap"] = b.open / g.close.shift(1) - 1
    b = b[(b.date >= START) & (b.praw >= 5) & (b.adv >= 5e6)][["ticker", "date", "praw", "adv", "gap"]]
    e["T"] = e["T"].astype("datetime64[ns]")
    b["date"] = b.date.astype("datetime64[ns]")
    e = e.merge(b, left_on=["ticker", "T"], right_on=["ticker", "date"]).drop(columns="date")
    e = e.sort_values("created").drop_duplicates(["ticker", "T"])
    e.to_parquet(D / "events.parquet")
    print("events", len(e), e["T"].nunique(), flush=True)


def prompts(w=0, W=1):
    c = _news()
    e = pd.read_parquet(D / "events.parquet")
    out = open(D / f"prompts_{w}.jsonl", "w")
    for i, r in enumerate(e.itertuples()):
        if i % W != w:
            continue
        st = (pd.Timestamp(r.prev) + pd.Timedelta(hours=16)).tz_localize(TZ)
        en = (pd.Timestamp(r.T) + pd.Timedelta(hours=9, minutes=20)).tz_localize(TZ)
        x = _get(c, start=st, end=en, symbols=r.ticker, include_content=True)
        txt = []
        if len(x):
            x = x[pd.to_datetime(x.updated_at, utc=True) <= en.tz_convert("UTC")].sort_values("created_at")
            for y in x.itertuples():
                body = re.sub(r"<[^>]+>", " ", str(y.content or ""))
                body = re.sub(r"\s+", " ", body)[:1500]
                txt.append(f"[{pd.Timestamp(y.created_at).tz_convert(TZ):%Y-%m-%d %H:%M}] {y.headline}\n{y.summary or ''}\n{body}")
        news = "\n\n".join(txt)[:6000] or r.headline
        key = f"{r.ticker}|{pd.Timestamp(r.T).date()}"
        base = (f"Stock {r.ticker}. Trading date {pd.Timestamp(r.T).date()}. It opened {r.gap*100:+.1f}% versus the prior "
                f"close.")
        q = (" Predict (1) the direction of the stock's move from 09:35 ET to today's close, and (2) the direction from "
             "today's close to the close three trading days later. Reply with only a JSON object with keys: intraday "
             "(one of up, down, flat), intraday_conf (0-1), drift3d (one of up, down, flat), drift3d_conf (0-1), "
             "reason (short string).")
        out.write(json.dumps({"key": key, "arm": "news", "prompt": base + " News published before the open:\n\n" + news
                              + "\n\n" + q}) + "\n")
        out.write(json.dumps({"key": key, "arm": "placebo", "prompt": base + " No news text is provided." + q}) + "\n")
        if i % 100 == 0:
            print(i, len(e), flush=True)
    out.close()


def bars():
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    e = pd.read_parquet(D / "events.parquet")
    c, _ = _clients()
    rows = []
    for T, x in e.groupby("T"):
        s = (pd.Timestamp(T) + pd.Timedelta(hours=9, minutes=35)).tz_localize(TZ).tz_convert("UTC")
        syms = sorted(set(x.ticker))
        for a in range(8):
            try:
                df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=s,
                                                       end=s + pd.Timedelta(minutes=1), feed="sip", adjustment="raw")).df
                for (sym, ts), v in df.iterrows():
                    rows.append(dict(ticker=sym, T=pd.Timestamp(T), p935=v.close))
                break
            except Exception as ex:  # noqa: BLE001
                msg = str(ex)
                if "invalid symbol:" in msg:
                    bad = msg.split("invalid symbol:")[1].split('"')[0].strip()
                    syms = [y for y in syms if y != bad]
                    continue
                time.sleep(5 * (a + 1))
    pd.DataFrame(rows).drop_duplicates(["ticker", "T"]).to_parquet(D / "p935.parquet")
    print("bars", len(rows), flush=True)


def ct(x, keys):
    dm = pd.Series(np.asarray(x)).groupby(np.asarray(keys)).mean()
    return dm.mean(), (dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))) if len(dm) > 2 else np.nan, dm


def headline_score(h: str) -> int:
    s = 0
    for part in re.split(r",|;", h):
        if re.search(r"\bbeats?\b", part, re.I):
            s += 1
        elif re.search(r"\bmiss(es)?\b", part, re.I):
            s -= 1
    return int(np.sign(s))


def judge():
    e = pd.read_parquet(D / "events.parquet")
    e["key"] = e.ticker + "|" + e["T"].dt.date.astype(str)
    sc = pd.DataFrame([json.loads(l) for l in open(D / "scores.jsonl")])
    p = pd.read_parquet(D / "p935.parquet")
    b = m.load()
    b["date"] = b.date.astype("datetime64[ns]")
    adj = pd.read_parquet(pathlib.Path.home() / "data/sharadar/stocks.parquet", columns=["ticker", "date", "closeadj"])
    adj["date"] = pd.to_datetime(adj.date)
    adj = adj[adj.ticker.isin(e.ticker.unique()) & (adj.date >= "2025-12-01")].sort_values(["ticker", "date"])
    adj["c3"] = adj.groupby("ticker").closeadj.shift(-3)
    e = e.merge(p, on=["ticker", "T"], how="left").merge(
        b[["ticker", "date", "closeunadj"]], left_on=["ticker", "T"], right_on=["ticker", "date"], how="left").drop(columns="date")
    e = e.merge(adj[["ticker", "date", "closeadj", "c3"]], left_on=["ticker", "T"], right_on=["ticker", "date"], how="left")
    e["rA"] = e.closeunadj / e.p935 - 1
    e["rB"] = e.c3 / e.closeadj - 1
    e = e[e.rA.abs() < 0.5]
    sgn = {"up": 1, "down": -1}
    L = []
    pr = lambda s_: (print(s_), L.append(s_))  # noqa: E731
    pr(f"LLM-EARN events {len(e)} on {e['T'].nunique()} days ({e['T'].min().date()} .. {e['T'].max().date()}); "
       f"scored rows {len(sc)}, parse failures {sc.get('error', pd.Series(dtype=str)).notna().sum()}")

    def report(nm, sig, r, keys, dates):
        q = sig != 0
        x = pd.Series(sig[q] * r[q] - 2 * COST)
        if q.sum() < 20:
            pr(f"  {nm:34s} n {q.sum()} (too few)")
            return None
        mu, t, dm = ct(x, keys[q])
        dt = dates[q]
        cut = np.datetime64("2026-06-01")
        h1, h2 = x[dt < cut].mean(), x[dt >= cut].mean()
        lo = (sig[q] > 0)
        pr(f"  {nm:34s} n {q.sum():4d} net mean {x.mean()*1e4:+7.1f}bp med {x.median()*1e4:+7.1f} hit {(x>0).mean():.2f} "
           f"EWday t {t:+5.2f} | halves {h1*1e4:+6.1f} / {h2*1e4:+6.1f} | ex-top5 {dm.sort_values().iloc[:-5].mean()*1e4:+6.1f} "
           f"| long-only {x[lo].mean()*1e4:+6.1f} (n {lo.sum()}) | 20bp/side {(sig[q]*r[q]-0.004).mean()*1e4:+6.1f}")
        return x

    for arm in ["news", "placebo"]:
        s = sc[sc.arm == arm].set_index("key")
        for hz, col, conf, ret in [("A 09:35->close", "intraday", "intraday_conf", "rA"),
                                   ("B close->T+3", "drift3d", "drift3d_conf", "rB")]:
            z = e.join(s[[col, conf]], on="key").dropna(subset=[ret])
            sig = z[col].map(sgn).fillna(0) * (pd.to_numeric(z[conf], errors="coerce").fillna(0) >= 0.6)
            pr(f"\n[{arm}] {hz}")
            report(f"LLM conf>=0.6 ({arm})", sig.values, z[ret].values, z["T"].values, z["T"].values)
            if arm == "news":
                hs = z.headline.map(headline_score).values
                report("HEADLINE beat/miss control", hs, z[ret].values, z["T"].values, z["T"].values)
                report("GAP continuation control", np.sign(z.gap.values), z[ret].values, z["T"].values, z["T"].values)
                both = (sig.values != 0) & (hs != 0)
                d = (sig.values * z[ret].values - hs * z[ret].values)[both]
                if both.sum() > 20:
                    mu, t, _ = ct(d, z["T"].values[both])
                    pr(f"  LLM - HEADLINE on shared events: n {both.sum()} {mu*1e4:+.1f}bp t {t:+.2f}")
    fp = D / "finbert.jsonl"
    if fp.exists():
        fb = pd.DataFrame([json.loads(l) for l in open(fp)]).drop_duplicates("key").set_index("key")
        news = sc[sc.arm == "news"].set_index("key")
        for hz, col, conf, ret in [("A 09:35->close", "intraday", "intraday_conf", "rA"),
                                   ("B close->T+3", "drift3d", "drift3d_conf", "rB")]:
            z = e.join(fb, on="key").join(news[[col, conf]], on="key").dropna(subset=[ret, "p_pos"])
            d = z.p_pos - z.p_neg
            fs = (np.sign(d) * (d.abs() >= 0.3)).values
            pr(f"\n[finbert] {hz}")
            report("FINBERT |pos-neg|>=0.3", fs, z[ret].values, z["T"].values, z["T"].values)
            ls = (z[col].map(sgn).fillna(0) * (pd.to_numeric(z[conf], errors="coerce").fillna(0) >= 0.6)).values
            both = (ls != 0) & (fs != 0)
            if both.sum() > 20:
                mu, t, _ = ct((ls * z[ret].values - fs * z[ret].values)[both], z["T"].values[both])
                pr(f"  LLM - FINBERT on shared events: n {both.sum()} {mu*1e4:+.1f}bp t {t:+.2f}; "
                   f"sign agreement {(np.sign(ls[both]) == np.sign(fs[both])).mean():.2f}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    if a == "prompts":
        prompts(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        {"events": events, "bars": bars}.get(a, judge)()
