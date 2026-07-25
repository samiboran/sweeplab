from bot.config import Config
from bot.models import Candle
from bot.state import StateStore
from bot.strategy_engine import SymbolEngine


def make_config(tmp_path, **overrides):
    kwargs = dict(state_dir=tmp_path / "state", swing_window=2)
    kwargs.update(overrides)
    return Config(**kwargs)


def make_candle(o, h, l, c, t, closed=True):
    return Candle(open_time=t, open=o, high=h, low=l, close=c, close_time=t + 1, is_closed=closed)


def test_unclosed_candle_ignored(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config)
    engine = SymbolEngine("BTCUSDT", config, state)

    result = engine.on_candle(make_candle(10, 11, 9, 10, t=0, closed=False))
    assert result is None
    assert engine.candles == []


def test_same_open_time_replaces_last_candle(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config)
    engine = SymbolEngine("BTCUSDT", config, state)

    engine.on_candle(make_candle(10, 11, 9, 10, t=0))
    engine.on_candle(make_candle(10, 12, 9, 11, t=0))  # aynı mumun güncellenmiş kapanışı

    assert len(engine.candles) == 1
    assert engine.candles[0].close == 11


def test_new_candle_appends_and_updates_symbol_state(tmp_path):
    config = make_config(tmp_path)
    state = StateStore(config)
    engine = SymbolEngine("BTCUSDT", config, state)

    engine.on_candle(make_candle(10, 11, 9, 10, t=0))
    engine.on_candle(make_candle(10, 12, 9, 11, t=1))

    assert len(engine.candles) == 2
    info = state.snapshot()["symbols"]["BTCUSDT"]
    assert info["last_price"] == 11
    assert "trend" in info
