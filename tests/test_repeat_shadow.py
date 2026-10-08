import json

import pandas as pd

from swingtrader.daily import repeat_shadow as W


def test_log_candidates_appends_once_per_symbol_per_day(tmp_path):
    picks = pd.DataFrame({"price": [10.0, 20.0], "day_ret": [-0.1, -0.09], "ibs": [0.02, 0.05]}, index=["AAA", "BBB"])
    assert W.log_candidates(tmp_path, "2026-10-08", picks, "roth") == 2
    assert W.log_candidates(tmp_path, "2026-10-08", picks.iloc[:1], "live") == 0      # the other account, same night
    rows = [json.loads(x) for x in (tmp_path / W.LOG_NAME).read_text().splitlines()]
    assert [(r["sym"], r["account"], r["status"]) for r in rows] == [("AAA", "roth", "pending"), ("BBB", "roth", "pending")]


def test_flag_marks_repeats_by_logged_sessions_and_first_by_20():
    rows = [dict(date=f"d{k:02d}", sym="X") for k in (0, 3, 30)] + [dict(date=f"d{k:02d}", sym="Y") for k in range(31)]
    W.flag(rows)
    x = [r for r in rows if r["sym"] == "X"]
    assert (x[0]["gap"], x[0]["first"], x[0]["repeat"]) == (None, True, False)
    assert (x[1]["gap"], x[1]["repeat"]) == (3, True)
    assert (x[2]["gap"], x[2]["first"], x[2]["repeat"]) == (27, True, False)


def test_score_uses_signal_close_cross_and_next_open_cross():
    p = {"2026-10-08": (9.0, 1, 10.0, 1), "2026-10-09": (10.5, 1, 10.4, 1)}
    r = W.score(dict(date="2026-10-08", sym="A", status="pending"), p)
    assert r["status"] == "scored" and r["exit"] == "2026-10-09" and abs(r["ret"] - 0.05) < 1e-12
    assert W.score(dict(date="2026-10-09", sym="A", status="pending"), p)["status"] == "pending"


def test_paired_compares_repeat_and_first_on_the_same_nights():
    rows = []
    for n in range(4):
        rows += [dict(date=f"n{n}", sym="R", status="scored", repeat=True, first=False, ret=0.02),
                 dict(date=f"n{n}", sym="F", status="scored", repeat=False, first=True, ret=0.01 + 0.001 * n)]
    p = W.paired(rows)
    assert p["nights"] == 4 and abs(p["mean_bp"] - (100 - 15)) < 1e-6
