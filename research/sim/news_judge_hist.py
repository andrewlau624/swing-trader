"""Round 25, Study BC: the LLM news judge (Study BA's exact prompt/model) on PAST night picks, only
after the model's knowledge cutoff (pre-registered; round1_prose.md Round 25).

    PYTHONPATH=. .venv/bin/python -m research.sim.news_judge_hist probe            # find the cutoff
    PYTHONPATH=. .venv/bin/python -m research.sim.news_judge_hist run --start YYYY-MM-DD
    PYTHONPATH=. .venv/bin/python -m research.sim.news_judge_eval state/news-judge-hist.jsonl   # score

Why the probe: an LLM remembers how events before its training cutoff turned out, so a verdict on a
pre-cutoff drop can smuggle in the outcome. The probe asks dated true/false questions about public
events (plus fabricated controls) and reports the last month the model knows; the pre-registered
window starts two calendar months after that month. The prompt never contains the date.

Point-in-time inputs per pick (date d): Alpaca/Benzinga news published from the previous session's
16:00 ET to 15:40 ET on d, and SEC filings accepted in the same window. Picks come from
research/sim/news_judge_hist_picks.csv (the shipped night pool, raw prices, corr .7, 2025-01..2026-09),
committed so this runs on the server, which has the API keys but not the research data.
Runs with the same provider/model/client as the live judge (config.daily.news_judge_*), rate-limited,
resumable: verdicts append to state/news-judge-hist.jsonl in the live log's format.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

from swingtrader.config import ROOT, Config, load_dotenv, require_alpaca_keys
from swingtrader.daily import news_judge as nj

ET = "America/New_York"
PICKS = Path(__file__).with_name("news_judge_hist_picks.csv")
OUT = ROOT / "state" / "news-judge-hist.jsonl"
BDAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())

# (month, statement, truth). True events are well-documented public events; F rows are fabricated
# controls: a model that calls any control true is guessing, and the probe is void.
PROBES = [
    ("2024-11", "Donald Trump won the November 2024 US presidential election.", True),
    ("2025-01", "Nvidia's stock fell about 17% in one day in January 2025 after DeepSeek released its R1 model.", True),
    ("2025-04", "In early April 2025 the US announced broad 'Liberation Day' tariffs and the S&P 500 fell more than 10% over the following days.", True),
    ("2025-05", "In May 2025 the US and China agreed in Geneva to cut their reciprocal tariffs for 90 days.", True),
    ("2025-06", "In June 2025 the United States carried out air strikes on Iranian nuclear facilities.", True),
    ("2025-07", "In July 2025 Nvidia became the first public company to reach a $4 trillion market value.", True),
    ("2025-09", "In September 2025 the Federal Reserve cut its policy rate by 25 basis points.", True),
    ("2025-10", "A US federal government shutdown began on October 1, 2025.", True),
    ("2025-10", "In late October 2025 Nvidia became the first company to reach a $5 trillion market value.", True),
    ("F", "In March 2025 Apple agreed to acquire Netflix.", False),
    ("F", "In August 2025 the Federal Reserve raised its policy rate to 6%.", False),
    ("F", "Tesla was removed from the S&P 500 in 2025.", False),
]
PROBE_SYSTEM = ("For each numbered statement, answer true, false or unknown from your own training "
                "knowledge only. Say unknown if the event is after what you know or you are not sure. "
                "Reply with only a JSON object mapping each number (as a string) to true, false or unknown.")


def client_and_model():
    load_dotenv()
    d = Config.load().daily
    c = nj.make_client(d.news_judge_provider)
    if c is None:
        raise SystemExit(f"no {nj.KEY_VAR[d.news_judge_provider]} in .env")
    return c, d


def probe() -> int:
    c, d = client_and_model()
    body = "\n".join(f"{i + 1}. {s}" for i, (_, s, _) in enumerate(PROBES))
    if hasattr(c, "chat"):
        j = c.chat({"model": d.news_judge_model, "temperature": 0, "max_tokens": 800,
                    "messages": [{"role": "system", "content": PROBE_SYSTEM}, {"role": "user", "content": body}]})
        text, served = j["choices"][0]["message"]["content"], j.get("model")
    else:
        r = c.messages.create(model=d.news_judge_model, max_tokens=2000, system=PROBE_SYSTEM,
                              messages=[{"role": "user", "content": body}])
        text, served = next(b.text for b in r.content if b.type == "text"), r.model
    t = text.strip().strip("`").removeprefix("json").strip()
    ans = json.loads(t[t.find("{"): t.rfind("}") + 1])
    known, void = [], False
    print(f"served by {served}")
    for i, (m, s, truth) in enumerate(PROBES):
        a = str(ans.get(str(i + 1), "?")).lower()
        flag = ""
        if m == "F" and a == "true":
            void, flag = True, "  <- CONTROL CALLED TRUE"
        if m != "F" and a == "true":
            known.append(m)
        print(f"  [{m}] {a:8s} {s[:90]}{flag}")
    if void:
        print("\nprobe VOID: the model calls fabricated events true; the historical test does not run.")
        return 1
    if not known:
        print("\nthe model knows none of the dated events; cannot place the cutoff."); return 1
    last = max(known)
    start = (pd.Period(last, "M") + 3).start_time.date()      # two full months after the last known month
    print(f"\nlast month known: {last} -> pre-registered window starts {start} (run --start {start})")
    return 0


def window(day: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    d = pd.Timestamp(day)
    prev = d - BDAY
    return pd.Timestamp(f"{prev.date()} 16:00", tz=ET), pd.Timestamp(f"{d.date()} 15:40", tz=ET)


def run(start: str, pause: float, limit: int | None) -> int:
    c, d = client_and_model()
    keys = require_alpaca_keys()
    P = pd.read_csv(PICKS)
    P = P[P.date >= start]
    done = nj.load_log(OUT)
    todo = [r for r in P.itertuples() if (r.date, r.sym) not in done]
    if limit:
        todo = todo[:limit]
    print(f"{len(P)} picks from {start}; {len(done)} already judged; {len(todo)} to go "
          f"({d.news_judge_provider}/{d.news_judge_model}, {pause}s between calls)")
    cik_cache: dict = {}
    t0 = time.time()
    for k, r in enumerate(todo):
        a, b = window(r.date)
        rec = {"date": r.date, "sym": r.sym, "day_ret": r.day_ret, "price": r.price, "hist": True,
               "provider": d.news_judge_provider, "model": d.news_judge_model}
        try:
            news = nj.headlines(r.sym, a, b, keys)
        except Exception as exc:                                     # noqa: BLE001
            news = []; rec["news_error"] = f"{type(exc).__name__}: {str(exc)[:80]}"
        try:
            sec = filings_window(r.sym, a, b, cik_cache)
        except Exception as exc:                                     # noqa: BLE001
            sec = []; rec["sec_error"] = f"{type(exc).__name__}: {str(exc)[:80]}"
        rec.update(n_news=len(news), n_sec=len(sec))
        try:
            rec.update(nj.judge(c, d.news_judge_model, d.news_judge_effort, r.sym, r.day_ret, r.price, news, sec))
        except Exception as exc:                                     # noqa: BLE001
            rec.update(verdict=None, error=f"{type(exc).__name__}: {str(exc)[:120]}")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        if k % 25 == 0:
            print(f"  {k + 1}/{len(todo)}  {time.time() - t0:.0f}s  last {r.date} {r.sym}: {rec.get('verdict')}", flush=True)
        time.sleep(pause)
    print("done")
    return 0


def filings_window(sym: str, a: pd.Timestamp, b: pd.Timestamp, cache: dict) -> list[dict]:
    """SEC filings accepted in [a, b]; one submissions fetch per company per run."""
    cik = nj._cik_map(ROOT / "state").get(sym.upper().replace(".", "-"))
    if cik is None:
        return []
    if cik not in cache:
        cache[cik] = nj._sec_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        time.sleep(0.15)                                             # SEC fair access: < 10 req/s
    rec = cache[cik].get("filings", {}).get("recent", {})
    out = []
    for i, acc in enumerate(rec.get("acceptanceDateTime", [])):
        t = pd.Timestamp(acc)
        t = t.tz_localize("UTC") if t.tzinfo is None else t
        if a.tz_convert("UTC") <= t <= b.tz_convert("UTC"):
            out.append({"form": rec["form"][i], "time": str(t.tz_convert(ET))[:16],
                        "items": (rec.get("items") or [""] * (i + 1))[i],
                        "description": (rec.get("primaryDocDescription") or [""] * (i + 1))[i]})
    return out[:15]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("probe")
    r = sp.add_parser("run")
    r.add_argument("--start", required=True, help="first pick date (from the probe)")
    r.add_argument("--pause", type=float, default=2.0, help="seconds between LLM calls")
    r.add_argument("--limit", type=int, default=None, help="at most this many new picks (test runs)")
    a = ap.parse_args(argv)
    return probe() if a.cmd == "probe" else run(a.start, a.pause, a.limit)


if __name__ == "__main__":
    raise SystemExit(main())
