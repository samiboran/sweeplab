"""Paylaşılan veri modelleri: mum, swing, sinyal, pozisyon, işlem kaydı."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Candle:
    open_time: int  # ms epoch
    open: float
    high: float
    low: float
    close: float
    close_time: int = 0
    is_closed: bool = True


@dataclass(frozen=True)
class Swing:
    index: int
    price: float
    kind: str  # 'high' | 'low'


@dataclass(frozen=True)
class Signal:
    symbol: str
    direction: str  # 'long' | 'short'
    entry: float
    stop: float
    target: float
    swept_level: float
    reason: str
    candle_time: int


@dataclass
class Position:
    symbol: str
    direction: str
    entry: float
    stop: float
    target: float
    qty: float
    opened_at: float = field(default_factory=time.time)
    entry_order_id: str | None = None
    sl_order_id: str | None = None
    tp_order_id: str | None = None
    mode: str = "auto"  # 'auto' | 'notify_only'


@dataclass
class Trade:
    symbol: str
    direction: str
    entry: float
    stop: float
    target: float
    qty: float
    opened_at: float
    closed_at: float
    exit_price: float
    exit_reason: str  # 'tp' | 'sl' | 'manual'
    pnl_usdt: float
    mode: str = "auto"
