import datetime as dt
import json

from swingtrader.daily import crowd_hold_shadow as W


def test_score_night_uses_close_open_close_crosses():
    X = {"A": {"2026-10-08": (9.0, 1, 10.0, 1), "2026-10-09": (10.5, 1, 10.8, 1)},
         "B": {"2026-10-08": (5.0, 1, 5.0, 1), "2026-10-09": (5.1, 1, 5.0, 1)}}
    r = W.score_night("2026-10-08", ["A", "B"], X)
    assert r["exit"] == "2026-10-09" and r["scored"] == 2 and not r["crowded"]
    assert abs(r["hold_bp"] - 1e4 * (0.03 + -0.02) / 2) < 0.01          # A (10.8-10.5)/10, B (5.0-5.1)/5
    assert W.score_night("2026-10-09", ["A"], X) is None                # next session not in yet


def test_line_gates_on_crowded_nights_only():
    rows = [dict(date=f"2026-11-{i:02d}", crowded=True, hold_bp=30.0 + i) for i in range(1, W.NEED + 1)]
    rows += [dict(date="2026-11-01", crowded=False, hold_bp=-50.0)]
    assert W.line(rows).endswith("-> PASS")
    assert "-> KILL" in W.line([dict(r, hold_bp=-abs(r["hold_bp"])) for r in rows])


def test_run_scores_pending_nights_and_skips_done(tmp_path, monkeypatch):
    cand = [dict(date="2026-10-08", sym=s) for s in ("A", "B")]
    (tmp_path / W.CAND).write_text("".join(json.dumps(r) + "\n" for r in cand))
    X = {"A": {"2026-10-08": (9.0, 1, 10.0, 1), "2026-10-09": (10.5, 1, 10.8, 1)}}
    import swingtrader.daily.pref_ex_shadow as P
    calls = []
    monkeypatch.setattr(P, "crosses", lambda syms, s, e, H: calls.append(syms) or X)
    W.run(tmp_path, tmp_path, log=lambda *_: None, today=dt.date(2026, 10, 12), H={})
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["n"] == 2 and rows[0]["scored"] == 1
    W.run(tmp_path, tmp_path, log=lambda *_: None, today=dt.date(2026, 10, 12), H={})
    assert len(calls) == 1
