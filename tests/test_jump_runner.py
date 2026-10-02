"""Jump runner (prompt_jump_hunt.md): exit rules and the fixed gates. No network."""
import numpy as np
import pandas as pd

from research.sim import jump_runner as J


def _bars(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


def test_exit_rules():
    a = _bars([(10, 11, 9, 10.5), (10.5, 12.5, 10, 11), (11, 11, 10, 10)])
    assert abs(J._ret(a, 0, 1, "hold") - 0.05) < 1e-12
    assert abs(J._ret(a, 0, 3, "hold") - 0.0) < 1e-12
    assert J._ret(a, 0, 3, "tp20") == J.TP                     # high 12.5 >= 12 on day 2: filled at the limit
    gap = _bars([(10, 10.5, 9, 10), (13, 14, 12, 13), (13, 13, 13, 13)])
    assert abs(J._ret(gap, 0, 3, "tp20") - 0.3) < 1e-12       # opens above the limit: filled at the open


def test_costs_by_adv():
    assert J.cost_side(5e5) == 75e-4 and J.cost_side(3e6) == 40e-4 and J.cost_side(1e7) == 15e-4 and J.cost_side(1e8) == 5e-4


def test_gates_need_lift_and_no_single_lottery_ticket():
    good = dict(n=40, jump=0.15, lift=3.0, mean=0.03, ex3=0.01, median=-0.01, p0=0.03)
    assert J.explore_gate(good) and J.judge_gate(good)
    assert not J.explore_gate({**good, "ex3": -0.01})          # carried by its 3 best trades
    assert not J.explore_gate({**good, "lift": 1.8})            # jumps no more often than the stock normally does
    assert not J.explore_gate({**good, "n": 19})
    assert not J.judge_gate({**good, "p0": 0.2})
    assert J.judge_gate({**good, "lift": 1.6, "n": 15}) and not J.explore_gate({**good, "lift": 1.6})


def test_evaluate_uses_same_stock_base():
    T = pd.DataFrame(dict(sym=["A"] * 4, d=pd.to_datetime(["2022-01-03"] * 4), adv=[1e8] * 4, hold1=[0.3, 0.25, -0.05, 0.01]))
    B = pd.DataFrame(dict(sym=["A"] * 10, d=pd.to_datetime(["2022-02-01"] * 10), adv=[1e8] * 10, hold1=[0.3] + [0.0] * 9))
    e = J.evaluate(T, B, "hold1")
    assert e["jump"] == 0.5 and abs(e["base"] - 0.1) < 1e-12 and abs(e["lift"] - 5.0) < 1e-12


def test_confirm_gate_needs_more_than_one_winner():
    T = pd.DataFrame(dict(adv=[1e8] * 10, c=[0.5] + [-0.01] * 9))
    e = dict(n=10, mean=0.04, lift=2.0)
    assert not J.confirm_gate(e, T, "c")                       # one +50% trade carries it
    T2 = T.assign(c=[0.3, 0.25] + [0.0] * 8)
    assert J.confirm_gate(e, T2, "c")


def test_trail_exit_and_ride_gates():
    a = _bars([(10, 10, 10, 10), (10, 13, 10, 13), (13, 14, 12, 14), (14, 14, 11, 11.8), (12, 20, 12, 20)])
    assert abs(J._ret(a, 0, 5, "trail") - 0.18) < 1e-12      # peak close 14, 11.8 <= 14 x 0.85 = 11.9: out at 11.8
    up = _bars([(10, 10, 10, 10), (10, 12, 10, 12), (12, 13, 12, 13)])
    assert abs(J._ret(up, 0, 3, "trail") - 0.3) < 1e-12        # never trips: the hold's last close
    good = dict(n=30, mean=0.05, excess=0.03, ex3=0.02, median=0.0, p0=0.02)
    assert J.ride_explore_gate(good) and J.ride_judge_gate(good)
    assert not J.ride_explore_gate({**good, "excess": 0.01})   # no better than the stock normally does
    assert not J.ride_explore_gate({**good, "mean": 0.02})
    T = pd.DataFrame(dict(adv=[1e8] * 10, c=[0.1, 0.08] + [0.01] * 8))
    assert J.confirm_gate(dict(n=10, mean=0.02, lift=0.5, excess=0.01), T, "c", "ride")
    assert not J.confirm_gate(dict(n=10, mean=0.02, lift=0.5, excess=-0.01), T, "c", "ride")
