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
    subj, html, text, images = D.render(data, charts=False)
    assert "$3,260 total" in subj and "10 years" in text and images == []
    assert "+$4 from trades this week" in text and "+$4" in html, \
        "trades' P&L (10 - 6), not the equity change, which includes deposits"
    assert "NEXT STEP" in html and "Conviction trade on" in html and "Index fund" in html
    assert "Paper" not in html, "virtual book left out of the email"


def test_ten_year_lines_and_charts(tmp_path):
    yrs, lines, marks = D.ten_year("roth", 1000.0)
    assert len(yrs) == 121 and set(lines) == {"This bot", "Everything on", "Backtest", "Index fund"}
    assert marks["Backtest"][1] > marks["Everything on"][1], "the research rate is above every planning line"
    assert marks["Everything on"][1] > marks["This bot"][1] > marks["Index fund"][1] > 75000, "deposits + growth"
    _, tl, tm = D.ten_year("live", 2000.0)
    assert tm["This bot"][1] < D.project(2000.0, D.PLAN["taxable"]["base"], 10), "brokerage lines are after tax"
    st, lg = _state(tmp_path)
    _, html, _, images = D.render(D.build(st, lg, 3000.0, 0.5), charts=True)
    cids = [c for c, _ in images]
    assert cids == ["proj-live", "proj-roth"] and all(png[:4] == b"\x89PNG" for _, png in images)
    assert all(f"cid:{c}" in html for c in cids)


def test_pace_compares_live_to_backtest_on_the_same_balances(tmp_path):
    st, lg = _state(tmp_path)
    a = D.load_account("live", st, 3000.0)
    assert D.pace(a) is None, "fewer than 5 trades: no pace yet"
    today = dt.date.today()
    a.closed += [{"sym": "X", "leg": "night", "exit_date": (today - dt.timedelta(days=k)).isoformat(), "pnl": 1.0}
                 for k in range(1, 6)]
    a.equity_log = [{"date": (today - dt.timedelta(days=k)).isoformat(), "equity": 2000.0} for k in range(6, 0, -1)]
    pc = D.pace(a)
    assert pc["live"][-1] == pytest.approx(9.0), "10 - 6 + 5 x 1"
    n = len(pc["days"])
    assert pc["backtest"][-1] == pytest.approx(n * 2000 * D.BACKTEST["taxable"]["rate"] / 252)
    assert pc["backtest"][-1] > pc["plan"][-1] > 0 and pc["sd"][-1] == pytest.approx(2000 * 0.010 * n ** 0.5)
    _, html, _, imgs = D.render({**D.build(st, lg, 3000.0, 0.5), "accounts": {"live": a}}, charts=True)
    assert "Backtest pace" in html and "normal range" in html and ("pnl-live" in [c for c, _ in imgs])
