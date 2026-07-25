"""Güvenlik katmanı: günlük zarar limiti, eşzamanlı pozisyon sınırı, kill switch.

Bu modül emir açmadan ÖNCE her zaman danışılması gereken tek kapıdır
(`RiskManager.can_open_position`). Hiçbir yürütme kodu bu kontrolü atlamamalı.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from bot.config import Config
from bot.state import StateStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str = ""


class RiskManager:
    def __init__(self, config: Config, state: StateStore):
        self.config = config
        self.state = state

    def register_daily_start_balance(self, balance: float) -> float:
        return self.state.ensure_daily_start_balance(balance)

    def evaluate_daily_loss(self, current_balance: float) -> bool:
        """Günlük gerçekleşen zararı gün başı bakiyeye göre kontrol eder.
        Limit aşıldıysa True döner ve durumu kalıcı olarak işaretler."""
        start_balance = self.state.ensure_daily_start_balance(current_balance)
        if start_balance <= 0:
            return False

        daily_pnl = self.state.daily_pnl_usdt()
        loss_pct = max(0.0, -daily_pnl) / start_balance * 100
        breached = loss_pct >= self.config.daily_loss_limit_pct

        if breached and not self.state.is_daily_loss_limit_hit():
            logger.warning(
                "Günlük zarar limiti aşıldı: %.2f%% >= %.2f%% — bot yeni işlem açmayı durduruyor.",
                loss_pct,
                self.config.daily_loss_limit_pct,
            )
            self.state.set_daily_loss_limit_hit(True)

        return breached

    def can_open_position(self, symbol: str) -> RiskDecision:
        if self.state.is_kill_switch_active():
            return RiskDecision(False, "kill_switch_active")

        if self.state.is_daily_loss_limit_hit():
            return RiskDecision(False, "daily_loss_limit_hit")

        if self.state.has_position(symbol):
            return RiskDecision(False, "position_already_open_for_symbol")

        if self.state.open_position_count() >= self.config.max_concurrent_positions:
            return RiskDecision(False, "max_concurrent_positions_reached")

        return RiskDecision(True)
