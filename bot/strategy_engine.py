"""Sembol başına sinyal üretimini; risk kontrolünü, yürütmeyi ve bildirimi
birbirine bağlayan orkestrasyon katmanı."""
from __future__ import annotations

import logging

from bot.config import Config
from bot.execution import FuturesExecutor
from bot.models import Candle, Position
from bot.notifier import TelegramNotifier
from bot.risk import RiskManager
from bot.signals import detect_sweep_signal, determine_trend, find_fractal_swings, next_watch_levels
from bot.state import StateStore

logger = logging.getLogger(__name__)

MAX_CANDLE_BUFFER = 500


class SymbolEngine:
    """Tek bir sembol için mum tamponu, swing/trend hesabı ve sinyal üretimi."""

    def __init__(self, symbol: str, config: Config, state: StateStore):
        self.symbol = symbol
        self.config = config
        self.state = state
        self.candles: list[Candle] = []

    def on_candle(self, candle: Candle):
        if not candle.is_closed:
            return None  # kararlar sadece kapanmış mumlarda alınır (lookahead yok)

        if self.candles and candle.open_time == self.candles[-1].open_time:
            self.candles[-1] = candle
        else:
            self.candles.append(candle)
        if len(self.candles) > MAX_CANDLE_BUFFER:
            self.candles = self.candles[-MAX_CANDLE_BUFFER:]

        swings = find_fractal_swings(self.candles, self.config.swing_window)
        trend = determine_trend(swings)
        watch = next_watch_levels(swings, trend)

        self.state.set_symbol_info(self.symbol, {"last_price": candle.close, **watch})

        return detect_sweep_signal(
            self.symbol,
            candle,
            swings,
            trend,
            wick_min_pct=self.config.wick_min_pct,
            rr=self.config.rr,
            stop_buffer_pct=self.config.stop_buffer_pct,
        )


class StrategyEngine:
    def __init__(
        self,
        config: Config,
        state: StateStore,
        risk: RiskManager,
        notifier: TelegramNotifier,
        executor: FuturesExecutor | None,
    ):
        self.config = config
        self.state = state
        self.risk = risk
        self.notifier = notifier
        self.executor = executor
        self.symbol_engines = {s: SymbolEngine(s, config, state) for s in config.symbols}

    def handle_candle(self, symbol: str, candle: Candle) -> None:
        engine = self.symbol_engines.get(symbol)
        if engine is None:
            return

        try:
            signal = engine.on_candle(candle)
        except Exception:
            logger.exception("Sinyal hesaplanırken hata (%s)", symbol)
            return

        if signal is None:
            return

        logger.info("Sinyal bulundu: %s", signal)
        decision = self.risk.can_open_position(symbol)
        if not decision.allowed:
            logger.info("Sinyal engellendi (%s): %s", symbol, decision.reason)
            self.notifier.notify_signal_blocked(signal, decision.reason)
            return

        auto = self.config.auto_execute
        self.notifier.notify_signal(signal, auto_executed=auto)

        if not auto:
            return  # Faz 2: sadece bildirim; Sami elle onaylayıp açacak

        if self.executor is None:
            logger.error("auto_execute=True ama yürütme istemcisi kurulu değil (%s)", symbol)
            return

        try:
            position = self.executor.open_position(signal)
            self.state.upsert_position(position)
        except Exception as exc:
            logger.exception("Emir açılamadı (%s)", symbol)
            self.notifier.notify_error(f"emir açma {symbol}", exc)

    def sync_closed_positions(self) -> None:
        """Açık pozisyonların TP/SL ile kapanıp kapanmadığını borsadan kontrol eder."""
        if self.executor is None:
            return
        snap = self.state.snapshot()
        for symbol, pos_dict in list(snap.get("positions", {}).items()):
            position = Position(**pos_dict)
            try:
                trade = self.executor.check_closed(position)
            except Exception:
                logger.exception("Pozisyon senkronizasyonu başarısız (%s)", symbol)
                continue
            if trade is not None:
                self.state.add_trade(trade)
                self.state.remove_position(symbol)
                self.notifier.notify_trade_closed(trade)

    def check_daily_loss_limit(self) -> None:
        if self.executor is None:
            return
        try:
            balance = self.executor.get_available_balance_usdt()
        except Exception:
            logger.exception("Bakiye alınamadı, günlük zarar kontrolü atlandı.")
            return

        was_hit = self.state.is_daily_loss_limit_hit()
        breached = self.risk.evaluate_daily_loss(balance)
        if breached and not was_hit:
            snap = self.state.snapshot()
            start_balance = snap.get("daily_start_balance") or balance
            loss_pct = max(0.0, -snap.get("daily_pnl_usdt", 0.0)) / start_balance * 100
            self.notifier.notify_daily_loss_limit(loss_pct)
