from bot.config import Config
from bot.models import Trade
from bot.risk import RiskManager
from bot.state import StateStore


def make_config(tmp_path, **overrides):
    kwargs = dict(
        state_dir=tmp_path / "state",
        max_concurrent_positions=1,
        daily_loss_limit_pct=20.0,
    )
    kwargs.update(overrides)
    return Config(**kwargs)


def test_can_open_position_allowed_by_default(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config)
    risk = RiskManager(config, state)

    decision = risk.can_open_position("BTCUSDT")
    assert decision.allowed


def test_kill_switch_blocks_new_positions(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config)
    risk = RiskManager(config, state)

    state.set_kill_switch(True)
    decision = risk.can_open_position("BTCUSDT")
    assert not decision.allowed
    assert decision.reason == "kill_switch_active"


def test_max_concurrent_positions_blocks_extra_symbol(tmp_path):
    config = make_config(tmp_path, max_concurrent_positions=1)
    state = StateStore(config)
    risk = RiskManager(config, state)

    from bot.models import Position

    state.upsert_position(Position("BTCUSDT", "long", 100, 90, 120, 0.01))

    decision = risk.can_open_position("ETHUSDT")
    assert not decision.allowed
    assert decision.reason == "max_concurrent_positions_reached"


def test_duplicate_symbol_position_blocked(tmp_path):
    config = make_config(tmp_path, max_concurrent_positions=5)
    state = StateStore(config)
    risk = RiskManager(config, state)

    from bot.models import Position

    state.upsert_position(Position("BTCUSDT", "long", 100, 90, 120, 0.01))

    decision = risk.can_open_position("BTCUSDT")
    assert not decision.allowed
    assert decision.reason == "position_already_open_for_symbol"


def test_daily_loss_limit_trips_and_blocks(tmp_path):
    config = make_config(tmp_path, daily_loss_limit_pct=20.0)
    state = StateStore(config)
    risk = RiskManager(config, state)

    risk.register_daily_start_balance(1000.0)
    # %25 zarar kaydet -> limit (%20) aşılmalı
    state.add_trade(
        Trade("BTCUSDT", "long", 100, 90, 120, 1, 0, 1, 90, "sl", pnl_usdt=-250.0)
    )

    breached = risk.evaluate_daily_loss(750.0)
    assert breached is True

    decision = risk.can_open_position("ETHUSDT")
    assert not decision.allowed
    assert decision.reason == "daily_loss_limit_hit"


def test_daily_loss_limit_not_tripped_below_threshold(tmp_path):
    config = make_config(tmp_path, daily_loss_limit_pct=20.0)
    state = StateStore(config)
    risk = RiskManager(config, state)

    risk.register_daily_start_balance(1000.0)
    state.add_trade(
        Trade("BTCUSDT", "long", 100, 90, 120, 1, 0, 1, 90, "sl", pnl_usdt=-50.0)
    )

    breached = risk.evaluate_daily_loss(950.0)
    assert breached is False
    assert risk.can_open_position("ETHUSDT").allowed
