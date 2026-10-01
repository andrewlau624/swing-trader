"""LLM news judge for the night leg's picks — SHADOW ONLY (Round 23, Study BA; round1_prose.md).

At 15:40, AFTER the night leg's close-auction orders are placed, each pick's news and SEC filings
since the previous close are sent to Claude with one question: is today's drop FUNDAMENTAL (new
information about the company's value, which tends to drift) or LIQUIDITY (forced/flow selling with
no new information, which the night leg is paid to absorb)? The verdict is logged and never changes
an order. It is judged later, forward only, by research/sim/news_judge_eval.py: an LLM knows how
events before its training cutoff turned out, so a historical backtest would be contaminated.

Cost control: one verdict per (date, symbol) shared by every book (cache file in state_dir), at most
`max_calls` new calls a night, low effort. Every failure is logged and swallowed: the judge must never
cost the night leg anything.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

SEC_UA = {"User-Agent": "swing-trader news-judge (personal research)"}
LOG_NAME = "news-judge.jsonl"

SYSTEM = """You classify why a US-listed stock fell sharply today, for a strategy that buys big \
one-day losers at the close and sells them at the next open. Decide from the news and filings \
provided only. Do not use anything you may remember about what happened to this company after \
today.

- fundamental: the drop follows new information about the company's value (earnings or guidance \
miss, offering/dilution, failed trial or regulatory rejection, fraud or legal finding, lost \
contract or customer, credit event, merger terms or termination, a substantive downgrade).
- liquidity: no company-specific news explains the drop, or the news is stale or immaterial; the \
selling looks like flow (sector or market selloff, a peer's news, forced or technical selling, \
index or ETF flows, a short report without new facts).
- unclear: there is news, but it is ambiguous whether it changes the company's value.

confidence is your probability (0 to 1) that the verdict is right. Keep catalyst and reason short."""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["fundamental", "liquidity", "unclear"]},
        "confidence": {"type": "number"},
        "catalyst": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "confidence", "catalyst", "reason"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------- inputs
def headlines(sym: str, start: pd.Timestamp, end: pd.Timestamp, keys: tuple[str, str]) -> list[dict]:
    """Alpaca (Benzinga) news for one symbol published in [start, end]."""
    from alpaca.data.historical.news import NewsClient
    from alpaca.data.requests import NewsRequest
    r = NewsClient(*keys).get_news(NewsRequest(symbols=sym, start=start.to_pydatetime(),
                                               end=end.to_pydatetime(), limit=20)).dict()
    out = []
    for n in r.get("news", []):
        out.append({"time": str(n.get("created_at"))[:16], "headline": n.get("headline", ""),
                    "summary": (n.get("summary") or "")[:600]})
    return out


def _cik_map(cache_dir: Path) -> dict:
    f = cache_dir / f"sec-tickers-{dt.date.today().isoformat()}.json"
    if f.exists():
        return json.loads(f.read_text())
    j = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_UA, timeout=20).json()
    mp = {v["ticker"].upper(): int(v["cik_str"]) for v in j.values()}
    cache_dir.mkdir(parents=True, exist_ok=True)
    for old in cache_dir.glob("sec-tickers-*.json"):
        old.unlink(missing_ok=True)
    f.write_text(json.dumps(mp))
    return mp


def filings(sym: str, start: pd.Timestamp, cache_dir: Path) -> list[dict]:
    """SEC filings by the issuer accepted since `start` (form, time, 8-K items, description)."""
    cik = _cik_map(cache_dir).get(sym.upper().replace(".", "-"))
    if cik is None:
        return []
    j = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=SEC_UA, timeout=20).json()
    rec = j.get("filings", {}).get("recent", {})
    out = []
    for i, acc in enumerate(rec.get("acceptanceDateTime", [])):
        t = pd.Timestamp(acc)
        t = t.tz_localize("UTC") if t.tzinfo is None else t
        if t >= start.tz_convert("UTC"):
            out.append({"form": rec["form"][i], "time": str(t.tz_convert("America/New_York"))[:16],
                        "items": rec.get("items", [""] * (i + 1))[i],
                        "description": rec.get("primaryDocDescription", [""] * (i + 1))[i]})
    return out[:15]


# ---------------------------------------------------------------- the call
def judge(client, model: str, effort: str, sym: str, day_ret: float, price: float,
          news: list[dict], sec: list[dict]) -> dict:
    """One Claude call; returns the parsed verdict plus usage, or {'verdict': None, 'error': ...}."""
    body = (f"Symbol: {sym}\nToday's move at 15:40 ET: {day_ret * 100:+.1f}% (price {price:.2f})\n\n"
            f"News since the previous close ({len(news)}):\n"
            + ("\n".join(f"- [{n['time']}] {n['headline']} — {n['summary']}" for n in news) or "- none")
            + f"\n\nSEC filings since the previous close ({len(sec)}):\n"
            + ("\n".join(f"- [{s['time']}] {s['form']} {s['items']} {s['description']}".rstrip() for s in sec)
               or "- none"))
    resp = client.beta.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": body}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        return {"verdict": None, "error": "refusal", "request_id": resp._request_id}
    text = next((b.text for b in resp.content if b.type == "text"), "")
    out = json.loads(text)
    out.update(request_id=resp._request_id, served_by=resp.model,
               tokens_in=resp.usage.input_tokens, tokens_out=resp.usage.output_tokens)
    return out


# ---------------------------------------------------------------- shadow run
def load_log(path: Path) -> dict:
    """(date, sym) -> record, from the shared JSONL log."""
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        try:
            r = json.loads(line)
            out[(r["date"], r["sym"])] = r
        except (ValueError, KeyError):
            continue
    return out


def run_shadow(picks: pd.DataFrame, today: str, prev_close: pd.Timestamp, now: pd.Timestamp,
               cache_dir: Path, log, *, model: str, effort: str, max_calls: int, keys,
               client=None, fetch_news=headlines, fetch_filings=filings) -> int:
    """Judge tonight's picks (index = symbol; columns day_ret, price), deepest drops first, at most
    `max_calls` new calls. Returns the number of new verdicts written."""
    path = cache_dir / LOG_NAME
    done = load_log(path)
    todo = [s for s in picks.sort_values("day_ret").index if (today, str(s)) not in done][:max_calls]
    if not todo:
        return 0
    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            log("[news] skipped: no ANTHROPIC_API_KEY in .env (shadow judge off)")
            return 0
        import anthropic
        client = anthropic.Anthropic(timeout=90.0, max_retries=2)
    n = 0
    t0 = time.time()
    for sym in todo:
        if time.time() - t0 > 600:
            log("[news] time budget (10 min) spent; rest of tonight's picks not judged"); break
        r = picks.loc[sym]
        rec = {"date": today, "sym": str(sym), "day_ret": round(float(r.day_ret), 5),
               "price": round(float(r.price), 4), "model": model, "effort": effort,
               "judged_at": str(pd.Timestamp.now(tz="America/New_York"))[:19]}
        try:
            news = fetch_news(str(sym), prev_close, now, keys)
        except Exception as exc:                       # noqa: BLE001 — inputs are best effort
            news = []; rec["news_error"] = f"{type(exc).__name__}"
        try:
            sec = fetch_filings(str(sym), prev_close, cache_dir)
        except Exception as exc:                       # noqa: BLE001
            sec = []; rec["sec_error"] = f"{type(exc).__name__}"
        rec.update(n_news=len(news), n_sec=len(sec))
        try:
            rec.update(judge(client, model, effort, str(sym), float(r.day_ret), float(r.price), news, sec))
        except Exception as exc:                       # noqa: BLE001 — never cost the night leg
            rec.update(verdict=None, error=f"{type(exc).__name__}: {str(exc)[:120]}")
        with open(path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        n += 1
        log(f"[news] {sym} {rec['day_ret']*100:+.1f}%: {rec.get('verdict')} "
            f"({rec.get('confidence', float('nan')):.2f}) {str(rec.get('catalyst', rec.get('error', '')))[:60]}")
    return n


def main(argv=None) -> int:
    """Smoke test on one symbol: `python -m swingtrader.daily.news_judge SYM [DAY_RET]` (one API call,
    prints the verdict; writes nothing)."""
    import sys
    from ..config import ROOT, load_dotenv, require_alpaca_keys
    load_dotenv()
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python -m swingtrader.daily.news_judge SYM [DAY_RET, e.g. -0.10]"); return 2
    sym, day_ret = args[0].upper(), float(args[1]) if len(args) > 1 else -0.10
    import anthropic
    now = pd.Timestamp.now(tz="America/New_York")
    start = now - pd.Timedelta(days=1)
    news = headlines(sym, start, now, require_alpaca_keys())
    sec = filings(sym, start, ROOT / "state")
    from ..config import Config
    d = Config.load().daily
    out = judge(anthropic.Anthropic(timeout=90.0), d.news_judge_model, d.news_judge_effort, sym, day_ret,
                0.0, news, sec)
    print(f"{sym}: {len(news)} news, {len(sec)} filings in the last 24h")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
