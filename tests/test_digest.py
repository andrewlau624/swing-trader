"""Weekly digest: read-only numbers from the books and logs; projections compound with deposits."""
import datetime as dt
import json

import pytest

from swingtrader.daily import digest as D
from swingtrader.daily.book import DailyBook, book_file


def _state(tmp_path):
    st, lg = tmp_path / "state", tmp_path / "logs"
    st.mkdir(); lg.mkdir()
    today = dt.date.today()
    d = lambda k: (today - dt.timedelta(days=k)).isoformat()
    live = DailyBook(cash=900.0, start_equity=2000.0)
    live.equity_log = [{"date": d(10), "equity": 2200.0}, {"date": d(1), "equity": 2260.0}]
    live.closed = [
        {"sym": "AAA", "leg": "night", "entry_date": d(3), "exit_date": d(2), "pnl": 10.0, "ret": 0.02},
        {"sym": "BBB", "leg": "night", "entry_date": d(3), "exit_date": d(2), "pnl": -6.0, "ret": -0.01},
    ]
    live.conviction = {"history": [{"date": d(1), "ret": 0.01}]}
    live.save(st, book_file("live"))
    roth = DailyBook(cash=1000.0, start_equity=1000.0)
    roth.equity_log = [{"date": d(1), "equity": 1000.0}]
    roth.save(st, book_file("roth"))
    (lg / "daily-decisions-live.jsonl").write_text("\n".join(json.dumps(x) for x in [
        {"date": d(3), "sym": "AAA", "tow": 9, "bid_size": 900, "ask_size": 100},
        {"date": d(3), "sym": "BBB", "tow": 1, "bid_size": 100, "ask_size": 900}]) + "\n")
    fills = [{"leg": "noise", "side": "buy", "slippage_bps": 0.1, "filled_at": d(k) + "T10:01"} for k in (1, 2, 3)]
    fills.append({"leg": "night", "side": "sell", "slippage_bps": 0.0, "filled_at": d(2) + "T09:30"})
    (lg / "daily-fills-live.jsonl").write_text("\n".join(json.dumps(x) for x in fills) + "\nnot json\n\"a string\"\n")
    (st / "news-judge.jsonl").write_text(json.dumps({"date": d(3), "sym": "BBB", "verdict": "fundamental",
                                                     "confidence": 0.8}) + "\n")
    return st, lg


def test_project_compounds_with_monthly_deposits():
    assert D.project(1000, 0.0, 1, 1200) == pytest.approx(2200)
    assert D.project(1000, 0.10, 1) == pytest.approx(1100, rel=1e-9)
    assert D.project(1000, 0.15, 3, 7500) > 1000 * 1.15 ** 3 + 22500


def test_digest_numbers_from_books_and_logs(tmp_path):
    st, lg = _state(tmp_path)
    data = D.build(st, lg, 3000.0, 0.5)
    w = {r["idea"]: r for r in data["whatif"]["live"]}
    assert w["conviction trade"]["usd"] == pytest.approx(0.5 * 2260 * 0.01)
    assert w["tug-of-war tilt"]["usd"] > 0, "high-TOW winner up-weighted, low-TOW loser down-weighted"
    assert w["quote imbalance tilt"]["usd"] > 0
    assert w["LLM news judge (x0.25 on 'fundamental')"]["usd"] == pytest.approx(-0.75 * -6.0)
    g = {x["gate"]: x for x in data["gates"]}
    assert g["Conviction trade on"]["n"] == 3 and not g["Conviction trade on"]["ready"]
    assert g["LLM news judge verdict"]["n"] == 1
    p = [x for x in data["proj"] if x["account"] == "roth" and x["years"] == 3][0]
    assert p["with_levers"] > p["without"] > 3 * D.ROTH_DEPOSIT_YR
    subj, html, text = D.render(data)
    assert "$3,260 total" in subj and "In 5 years" in text
    assert "+$4 from trades this week" in text and "+$4 from trades this week" in html, \
        "trades' P&L (10 - 6), not the equity change, which includes deposits"
    assert "Next step" in html and "Conviction trade on" in html and "<pre" not in html
    assert "Paper" not in html, "virtual book left out of the email"
