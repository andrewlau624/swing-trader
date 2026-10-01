"""Round 28 BF: the halt rule (5+ silent minutes right after a >=5% 5-minute move)."""
from research.sim.halt_study import halt_flags


def test_down_move_then_silence_is_a_halt():
    m = list(range(0, 21)) + list(range(27, 40))          # bars 0..20, silence 21..26 (6 minutes), resume 27
    c = [10.0] * 15 + [10.0, 9.8, 9.6, 9.4, 9.2, 9.3] + [9.3] * 13   # 15->20: 10.0 -> 9.3 = -7%
    assert halt_flags(m, c) == (True, True)


def test_silence_without_a_big_move_is_not_a_halt():
    m = list(range(0, 21)) + list(range(27, 40))
    c = [10.0] * len(m)
    assert halt_flags(m, c) == (False, False)


def test_short_gap_after_a_move_is_not_a_halt():
    m = list(range(0, 21)) + list(range(24, 40))           # only 3 silent minutes
    c = [10.0] * 15 + [10.0, 10.2, 10.4, 10.6, 10.8, 10.7] + [10.7] * 16
    assert halt_flags(m, c) == (False, False)


def test_up_halt_is_not_a_down_halt():
    m = list(range(0, 21)) + list(range(27, 40))
    c = [10.0] * 15 + [10.0, 10.2, 10.4, 10.6, 10.8, 10.7] + [10.7] * 13
    assert halt_flags(m, c) == (True, False)
