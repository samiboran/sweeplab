from bot.execution import _round_step


def test_round_step_rounds_down_to_step_size():
    assert _round_step(1.23456, 0.001) == 1.234
    assert _round_step(1.239, 0.01) == 1.23
    assert _round_step(10.0, 1.0) == 10.0


def test_round_step_handles_zero_step():
    assert _round_step(1.23456, 0) == 1.23456
