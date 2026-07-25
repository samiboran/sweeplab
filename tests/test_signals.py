from bot.models import Candle, Swing
from bot.signals import detect_sweep_signal, determine_trend, find_fractal_swings, next_watch_levels


def make_candle(o: float, h: float, l: float, c: float, t: int = 0) -> Candle:
    return Candle(open_time=t, open=o, high=h, low=l, close=c, close_time=t, is_closed=True)


def test_find_fractal_swings_detects_peak_and_trough():
    highs = [1, 2, 3, 2, 1]
    lows = [5, 4, 3, 4, 5]
    candles = [make_candle(h, h, l, h, i) for i, (h, l) in enumerate(zip(highs, lows))]
    swings = find_fractal_swings(candles, window=2)

    kinds = {(s.index, s.kind) for s in swings}
    assert (2, "high") in kinds
    assert (2, "low") in kinds


def test_find_fractal_swings_requires_unique_extreme():
    candles = [make_candle(5, 5, 5, 5, i) for i in range(5)]
    swings = find_fractal_swings(candles, window=2)
    assert swings == []


def test_determine_trend_up_on_higher_highs_and_lows():
    swings = [
        Swing(0, 100, "low"),
        Swing(1, 110, "high"),
        Swing(2, 105, "low"),
        Swing(3, 115, "high"),
    ]
    assert determine_trend(swings) == "up"


def test_determine_trend_down_on_lower_highs_and_lows():
    swings = [
        Swing(0, 100, "high"),
        Swing(1, 90, "low"),
        Swing(2, 95, "high"),
        Swing(3, 85, "low"),
    ]
    assert determine_trend(swings) == "down"


def test_determine_trend_neutral_when_insufficient_swings():
    assert determine_trend([Swing(0, 100, "high")]) == "neutral"


def test_determine_trend_neutral_when_mixed_structure():
    swings = [
        Swing(0, 100, "low"),
        Swing(1, 110, "high"),
        Swing(2, 95, "low"),   # lower low
        Swing(3, 115, "high"),  # higher high -> mixed, not up
    ]
    assert determine_trend(swings) == "neutral"


def test_long_sweep_signal_detected_in_uptrend():
    swings = [Swing(0, 90, "low"), Swing(1, 120, "high"), Swing(2, 100, "low"), Swing(3, 125, "high")]
    candle = make_candle(o=100.5, h=101.2, l=95.0, c=101.0)

    sig = detect_sweep_signal(
        "AVAXUSDT", candle, swings, "up", wick_min_pct=0.40, rr=2.0, stop_buffer_pct=0.0005
    )

    assert sig is not None
    assert sig.direction == "long"
    assert sig.entry == 101.0
    assert sig.stop < 95.0
    assert sig.swept_level == 100
    assert sig.target > sig.entry
    risk = sig.entry - sig.stop
    assert sig.target == sig.entry + 2.0 * risk


def test_short_sweep_signal_detected_in_downtrend():
    swings = [Swing(0, 120, "high"), Swing(1, 90, "low"), Swing(2, 110, "high"), Swing(3, 85, "low")]
    candle = make_candle(o=100.0, h=115.0, l=99.5, c=100.2)

    sig = detect_sweep_signal(
        "AVAXUSDT", candle, swings, "down", wick_min_pct=0.40, rr=2.0, stop_buffer_pct=0.0005
    )

    assert sig is not None
    assert sig.direction == "short"
    assert sig.entry == 100.2
    assert sig.stop > 115.0
    assert sig.swept_level == 110
    assert sig.target < sig.entry


def test_no_signal_when_wick_too_small():
    swings = [Swing(0, 90, "low"), Swing(1, 120, "high"), Swing(2, 100, "low"), Swing(3, 125, "high")]
    # low wick barely below the sweep level, most of the range is the body -> wick % too small
    candle = make_candle(o=95.5, h=101.0, l=95.0, c=100.9)

    sig = detect_sweep_signal(
        "AVAXUSDT", candle, swings, "up", wick_min_pct=0.40, rr=2.0, stop_buffer_pct=0.0005
    )
    assert sig is None


def test_no_signal_when_trend_does_not_match_direction():
    swings = [Swing(0, 90, "low"), Swing(1, 120, "high"), Swing(2, 100, "low"), Swing(3, 125, "high")]
    candle = make_candle(o=100.5, h=101.2, l=95.0, c=101.0)

    sig = detect_sweep_signal(
        "AVAXUSDT", candle, swings, "down", wick_min_pct=0.40, rr=2.0, stop_buffer_pct=0.0005
    )
    assert sig is None


def test_no_signal_when_close_does_not_reclaim_level():
    swings = [Swing(0, 90, "low"), Swing(1, 120, "high"), Swing(2, 100, "low"), Swing(3, 125, "high")]
    candle = make_candle(o=97.0, h=98.0, l=95.0, c=96.0)  # closes below swept level, no reclaim

    sig = detect_sweep_signal(
        "AVAXUSDT", candle, swings, "up", wick_min_pct=0.40, rr=2.0, stop_buffer_pct=0.0005
    )
    assert sig is None


def test_next_watch_levels_up_trend():
    swings = [Swing(0, 90, "low"), Swing(1, 120, "high"), Swing(2, 100, "low"), Swing(3, 125, "high")]
    info = next_watch_levels(swings, "up")
    assert info["watch_level"] == 100
    assert info["watch_direction"] == "long"
