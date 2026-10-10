import json

from swingtrader.daily import top2_shadow as W


def _c(d, sym, dr, ret, status="scored"):
    return dict(date=d, sym=sym, day_ret=dr, ret=ret, status=status)


def test_nights_takes_two_deepest_and_skips_pending():
    c = [_c("n1", "A", -0.30, 0.05), _c("n1", "B", -0.20, 0.01), _c("n1", "C", -0.09, -0.03),
         _c("n2", "D", -0.10, 0.02), _c("n2", "E", -0.12, 0.0, status="pending")]
    r = W.nights(c)
    assert [x["date"] for x in r] == ["n1"]
    assert r[0]["top2"] == ["A", "B"] and r[0]["judged"]
    assert abs(r[0]["top2_bp"] - 300) < 1e-6 and abs(r[0]["base_bp"] - 100) < 1e-6 and abs(r[0]["diff_bp"] - 200) < 1e-6


def test_line_gates_after_need_nights():
    rows = [dict(date=f"d{i:03d}", judged=True, base_bp=10.0 + (i % 7), top2_bp=40.0 + 2 * (i % 5), diff_bp=30.0 + 2 * (i % 5) - (i % 7))
            for i in range(W.NEED)]
    assert W.line(rows).endswith("-> PASS")
    neg = [dict(r, top2_bp=-r["top2_bp"], diff_bp=-abs(r["diff_bp"]) - 1) for r in rows]
    assert W.line(neg).endswith("-> KILL")


def test_run_writes_log(tmp_path):
    c = [_c("n1", s, -0.1 - i / 100, 0.01 * i) for i, s in enumerate("ABC")]
    (tmp_path / W.CAND).write_text("".join(json.dumps(x) + "\n" for x in c))
    assert W.run(tmp_path, tmp_path, log=lambda *_: None)["n"] == 1
    assert len((tmp_path / W.LOG_NAME).read_text().splitlines()) == 1
