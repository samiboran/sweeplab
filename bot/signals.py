"""Likidite süpürme (liquidity sweep) reversal strateji mantığı.

Backtest'te doğrulanan mantık:
  1. Fraktal swing tespiti (pencere = w): high[i] çevresindeki 2w+1 barın en
     yükseği ise swing-high, low[i] en düşüğü ise swing-low.
  2. Trend: son iki swing-high artıyorsa (HH) ve son iki swing-low artıyorsa
     (HL) -> yukarı trend. Tersi (LH+LL) -> aşağı trend.
  3. Süpürme: yukarı trendde fiyat son swing-low'un altına sarkıp (likidite
     süpürme) kapanışta geri üstüne dönerse VE alt fitil, mumun toplam
     aralığının en az %wick_min_pct'i ise -> long sinyali. Aşağı trendde
     simetriği -> short sinyali.
  4. entry = mumun kapanışı, stop = süpürülen mumun ucu + buffer,
     target = entry ± RR * risk.

Bu modül saf fonksiyonlardır; hiçbir I/O (ağ, dosya) yapmaz — test edilmesi
ve backtest sonuçlarıyla birebir karşılaştırılması bunun içindir.
"""
from __future__ import annotations

from bot.models import Candle, Signal, Swing


def find_fractal_swings(candles: list[Candle], window: int) -> list[Swing]:
    """Kapanmış mumlar üzerinde fraktal swing high/low listesi döner.

    Bir swing, ancak kendisinden sonra en az `window` mum geldiğinde
    doğrulanabilir (lookahead yok — doğrulama gecikmesi budur).
    """
    if window < 1:
        raise ValueError("window en az 1 olmalı")

    swings: list[Swing] = []
    n = len(candles)
    for i in range(window, n - window):
        seg = candles[i - window : i + window + 1]
        seg_highs = [c.high for c in seg]
        seg_lows = [c.low for c in seg]
        center = candles[i]

        if center.high == max(seg_highs) and seg_highs.count(center.high) == 1:
            swings.append(Swing(index=i, price=center.high, kind="high"))
        if center.low == min(seg_lows) and seg_lows.count(center.low) == 1:
            swings.append(Swing(index=i, price=center.low, kind="low"))

    return swings


def determine_trend(swings: list[Swing]) -> str:
    """Son iki swing-high ve son iki swing-low'a göre 'up' / 'down' / 'neutral'."""
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if len(highs) < 2 or len(lows) < 2:
        return "neutral"

    higher_high = highs[-1].price > highs[-2].price
    higher_low = lows[-1].price > lows[-2].price
    lower_high = highs[-1].price < highs[-2].price
    lower_low = lows[-1].price < lows[-2].price

    if higher_high and higher_low:
        return "up"
    if lower_high and lower_low:
        return "down"
    return "neutral"


def detect_sweep_signal(
    symbol: str,
    candle: Candle,
    swings: list[Swing],
    trend: str,
    *,
    wick_min_pct: float,
    rr: float,
    stop_buffer_pct: float,
) -> Signal | None:
    """Kapanmış bir mum üzerinde süpürme + reddetme (rejection) sinyali arar.

    `swings`, bu mumdan ÖNCE doğrulanmış swing'leri içermelidir (lookahead yok).
    """
    rng = candle.high - candle.low
    if rng <= 0:
        return None

    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    # LONG: yukarı trend, son swing-low'un altı süpürülüp üstüne dönülüyor.
    if trend == "up" and lows:
        level = lows[-1].price
        if candle.low < level <= candle.close:
            lower_wick = min(candle.open, candle.close) - candle.low
            if lower_wick / rng >= wick_min_pct:
                entry = candle.close
                stop = candle.low * (1 - stop_buffer_pct)
                risk = entry - stop
                if risk > 0:
                    target = entry + rr * risk
                    return Signal(
                        symbol=symbol,
                        direction="long",
                        entry=entry,
                        stop=stop,
                        target=target,
                        swept_level=level,
                        reason="sweep_hl_reversal",
                        candle_time=candle.open_time,
                    )

    # SHORT: aşağı trend, son swing-high'ın üstü süpürülüp altına dönülüyor.
    if trend == "down" and highs:
        level = highs[-1].price
        if candle.high > level >= candle.close:
            upper_wick = candle.high - max(candle.open, candle.close)
            if upper_wick / rng >= wick_min_pct:
                entry = candle.close
                stop = candle.high * (1 + stop_buffer_pct)
                risk = stop - entry
                if risk > 0:
                    target = entry - rr * risk
                    return Signal(
                        symbol=symbol,
                        direction="short",
                        entry=entry,
                        stop=stop,
                        target=target,
                        swept_level=level,
                        reason="sweep_lh_reversal",
                        candle_time=candle.open_time,
                    )

    return None


def next_watch_levels(swings: list[Swing], trend: str) -> dict:
    """Panelde göstermek için: mevcut trend ve bir sonraki tetik seviyesi
    (Pine v4'teki 'İZLE' çizgisinin karşılığı)."""
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    watch_level = None
    watch_direction = None
    if trend == "up" and lows:
        watch_level = lows[-1].price
        watch_direction = "long"
    elif trend == "down" and highs:
        watch_level = highs[-1].price
        watch_direction = "short"

    return {
        "trend": trend,
        "watch_level": watch_level,
        "watch_direction": watch_direction,
        "last_swing_high": highs[-1].price if highs else None,
        "last_swing_low": lows[-1].price if lows else None,
    }
