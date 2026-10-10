import json

from swingtrader.daily import hedge_shadow as W


def _c(d, sym, dr, ret, status="scored"):
    return dict(date=d, sym=sym, day_ret=dr, ret=ret, status=status)


def test_cfg_ret_filters_by_cut_and_topk():
    sc = [_c("n", "A", -0.20, 0.04), _c("n", "B", -0.13, 0.02), _c("n", "C", -0.09, -0.02)]
    assert abs(W.cfg_ret(sc, (-0.08, None)) - (0.04 / 3 - 0.001)) < 1e-12
    assert abs(W.cfg_ret(sc, (-0.12, 2)) - (0.03 - 0.001)) < 1e-12
    assert W.cfg_ret(sc, (-0.25, None)) == 0.0


def test_learn_uses_only_prior_nights_and_stops_at_pending():
    c = []
    for i in range(5):                       # deep names win every night
        c += [_c(f"d{i}", "DEEP", -0.20, 0.05), _c(f"d{i}", "SHALLOW", -0.085, -0.05)]
    c += [_c("d9", "X", -0.2, 0.0, status="pending"), _c("d9", "Y", -0.1, 0.0)]
    rows = W.learn(c)
    assert len(rows) == 5
    assert rows[0]["chosen"] == "-8%/all"    # equal weights on night 1 -> first config
    assert rows[-1]["chosen"] != "-8%/all" and rows[-1]["diff_bp"] > 0


def test_run_writes_log(tmp_path):
    c = [_c("d0", "A", -0.1, 0.01), _c("d0", "B", -0.2, 0.02)]
    (tmp_path / W.CAND).write_text("".join(json.dumps(x) + "\n" for x in c))
    assert W.run(tmp_path, tmp_path, log=lambda *_: None)["n"] == 1
