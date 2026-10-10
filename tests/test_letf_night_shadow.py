import datetime as dt
import json

import pandas as pd

from swingtrader.daily import letf_night_shadow as W


def _bars(rows, dates):
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    return pd.DataFrame({"open": rows, "high": rows, "low": rows, "close": rows, "volume": [1_000_000] * len(rows)}, index=idx)


DATES = [str((dt.date(2026, 9, 1) + dt.timedelta(days=i))) for i in range(30)]


def test_screen_marks_treated_control_and_sub_share():
    lmap = {"AAAL": "AAA", "BBBL": "BBB"}
    # AAA: -6% on the last day, LETF with 5% of its $vol -> treated; BBB: LETF too small -> neither; CCC: no LETF -> control;
    # DDD: only -3% -> no event; AAAL itself is never an event
    bars = {"AAA": _bars([20.0] * 29 + [18.8], DATES), "BBB": _bars([20.0] * 29 + [18.0], DATES),
            "CCC": _bars([20.0] * 29 + [18.5], DATES), "DDD": _bars([20.0] * 29 + [19.4], DATES),
            "AAAL": _bars([1.0] * 30, DATES), "BBBL": _bars([0.01] * 30, DATES)}
    bars["AAAL"]["volume"] = 1_000_000          # 20d LETF $vol = 20 x $1M = $20M vs AAA 20 x $20M = $400M -> 5%
    ev = {e["sym"]: e for e in W.screen(DATES[-1], bars, lmap)}
    assert set(ev) == {"AAA", "BBB", "CCC"}
    assert ev["AAA"]["treated"] and not ev["AAA"]["control"] and abs(ev["AAA"]["share"] - 0.05) < 1e-6
    assert not ev["BBB"]["treated"] and not ev["BBB"]["control"]
    assert ev["CCC"]["control"] and not ev["CCC"]["treated"]
    assert ev["AAA"]["r"] == round(18.8 / 20 - 1, 5)


def test_score_uses_closing_then_opening_cross_and_spy():
    X = {"AAA": {"2026-10-08": (18.0, 1, 18.8, 1), "2026-10-09": (19.2, 1, 19.0, 1)},
         "SPY": {"2026-10-08": (500.0, 1, 500.0, 1), "2026-10-09": (501.0, 1, 502.0, 1)}}
    r = W.score(dict(date="2026-10-08", sym="AAA", treated=True, control=False, status="pending"), X)
    assert r["exit"] == "2026-10-09" and abs(r["ret"] - (19.2 / 18.8 - 1)) < 1e-6
    assert abs(r["net"] - (r["ret"] - 2 * W.COST)) < 1e-6 and abs(r["bench"] - 0.002) < 1e-6
    assert W.score(dict(date="2026-10-09", sym="AAA", status="pending"), X) is None


def test_line_gates_on_event_days():
    rows = []
    for i in range(W.NEED):
        d = str(dt.date(2026, 10, 1) + dt.timedelta(days=i))
        rows.append(dict(date=d, sym="A", treated=True, control=False, status="scored", net=0.0030, xs=0.001))
        rows.append(dict(date=d, sym="C", treated=False, control=True, status="scored", net=0.0005))
    assert W.line(rows).endswith("-> PASS (mean > 15bp, median > 0, beats control by >= 15bp)")
    assert "-> KILL" in W.line([dict(r, net=-r["net"]) if r["treated"] else r for r in rows])
    assert W.line(rows[:10]).startswith("5/120 event days")


def test_run_scans_scores_and_is_idempotent(tmp_path, monkeypatch):
    (tmp_path / "daily-universe-2026-10-09.json").write_text(json.dumps([{"symbol": "AAA"}, {"symbol": "CCC"}, {"symbol": "AAAL"}]))
    (tmp_path / W.CAND).write_text(json.dumps(dict(date="2026-10-08", sym="AAA")) + "\n")
    monkeypatch.setattr(W, "letf_map", lambda path=None: {"AAAL": "AAA"})
    days = [str(dt.date(2026, 8, 25) + dt.timedelta(days=i)) for i in range(45)]
    days = [d for d in days if pd.Timestamp(d).weekday() < 5]
    spy = _bars([500.0] * len(days), days)
    aaa = _bars([20.0] * (len(days) - 2) + [18.0, 18.5], days)           # -10% on 10-08 if it is the 2nd-last session
    ccc = _bars([20.0] * (len(days) - 2) + [18.0, 18.5], days)
    letf = _bars([1.0] * len(days), days)
    calls = []

    def bars_fn(syms, start, end):
        calls.append(list(syms))
        return {s: {"SPY": spy, "AAA": aaa, "CCC": ccc, "AAAL": letf}[s] for s in syms if s in ("SPY", "AAA", "CCC", "AAAL")}

    sig = days[-2]
    X = {"AAA": {sig: (18.0, 1, 18.0, 1), days[-1]: (18.4, 1, 18.5, 1)},
         "CCC": {sig: (18.0, 1, 18.0, 1), days[-1]: (17.9, 1, 18.5, 1)},
         "SPY": {sig: (500.0, 1, 500.0, 1), days[-1]: (500.0, 1, 500.0, 1)}}
    today = dt.date.fromisoformat(days[-1]) + dt.timedelta(days=1)
    W.run(tmp_path, tmp_path, log=lambda *_: None, today=today, H={}, bars_fn=bars_fn, crosses_fn=lambda s, a, b, H: X)
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    ev = {r["sym"]: r for r in rows if "sym" in r}
    assert ev["AAA"]["treated"] and ev["AAA"]["night_pick"] is (sig == "2026-10-08") and ev["AAA"]["status"] == "scored"
    assert ev["CCC"]["control"] and ev["CCC"]["status"] == "scored" and abs(ev["CCC"]["ret"] - (17.9 / 18 - 1)) < 1e-6
    assert any(r.get("status") == "scanned" and r["date"] == sig for r in rows)
    n_calls = len(calls)
    W.run(tmp_path, tmp_path, log=lambda *_: None, today=today, H={}, bars_fn=bars_fn, crosses_fn=lambda s, a, b, H: X)
    assert len(calls) == n_calls + 1, "a second run only re-reads SPY's sessions; nothing is re-scanned or re-scored"
