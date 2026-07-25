"""Binance Futures emir yürütme katmanı (python-binance).

Faz 1 (testnet) ve Faz 3 (gerçek hesap, tam otomatik) için kullanılır.
Faz 2'de (`config.auto_execute == False`) bu modül hiç çağrılmaz — sadece
bildirim gider, emir açılmaz.

Güvenlik notu: buradaki `Client`, API key'in SADECE "Futures Trading" izniyle
oluşturulduğunu varsayar. "Withdrawal" (para çekme) izni açık bir key ile bu
botu ASLA çalıştırmayın.
"""
from __future__ import annotations

import logging
import math
import time
from decimal import ROUND_DOWN, Decimal

from bot.config import Config
from bot.models import Position, Signal, Trade

logger = logging.getLogger(__name__)

try:
    from binance.client import Client
except ImportError:  # pragma: no cover - python-binance opsiyonel (test ortamı)
    Client = None  # type: ignore


class ExecutionError(RuntimeError):
    pass


def _round_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    d_value = Decimal(str(value))
    d_step = Decimal(str(step))
    return float((d_value / d_step).to_integral_value(rounding=ROUND_DOWN) * d_step)


class FuturesExecutor:
    def __init__(self, config: Config):
        if Client is None:
            raise ExecutionError(
                "python-binance kurulu değil. `pip install python-binance` çalıştırın."
            )
        if not config.binance_api_key or not config.binance_api_secret:
            raise ExecutionError("BINANCE_API_KEY / BINANCE_API_SECRET tanımlı değil.")

        self.config = config
        self.client = Client(config.binance_api_key, config.binance_api_secret, testnet=config.is_testnet)
        self._symbol_filters: dict[str, dict] = {}
        self._leverage_set: set[str] = set()

    # --- borsa bilgisi ---

    def _symbol_filters_for(self, symbol: str) -> dict:
        if symbol not in self._symbol_filters:
            info = self.client.futures_exchange_info()
            for s in info["symbols"]:
                filters = {f["filterType"]: f for f in s["filters"]}
                self._symbol_filters[s["symbol"]] = {
                    "step_size": float(filters["LOT_SIZE"]["stepSize"]),
                    "min_qty": float(filters["LOT_SIZE"]["minQty"]),
                    "tick_size": float(filters["PRICE_FILTER"]["tickSize"]),
                }
        if symbol not in self._symbol_filters:
            raise ExecutionError(f"{symbol} için borsa bilgisi bulunamadı.")
        return self._symbol_filters[symbol]

    def ensure_leverage(self, symbol: str) -> None:
        if symbol in self._leverage_set:
            return
        self.client.futures_change_leverage(symbol=symbol, leverage=self.config.leverage)
        self._leverage_set.add(symbol)

    def get_available_balance_usdt(self) -> float:
        balances = self.client.futures_account_balance()
        for b in balances:
            if b["asset"] == "USDT":
                return float(b["availableBalance"])
        return 0.0

    # --- pozisyon büyüklüğü ---

    def compute_quantity(self, symbol: str, signal: Signal, balance_usdt: float) -> float:
        filters = self._symbol_filters_for(symbol)
        risk_amount = balance_usdt * (self.config.risk_pct_per_trade / 100)
        risk_per_unit = abs(signal.entry - signal.stop)
        if risk_per_unit <= 0:
            raise ExecutionError("risk_per_unit sıfır veya negatif, pozisyon açılamaz.")

        qty = risk_amount / risk_per_unit

        # Kaldıraçla mevcut marjini aşmayacak şekilde sınırla (güvenlik payı %95).
        max_notional = balance_usdt * self.config.leverage * 0.95
        if qty * signal.entry > max_notional:
            qty = max_notional / signal.entry

        qty = _round_step(qty, filters["step_size"])
        if qty < filters["min_qty"]:
            raise ExecutionError(
                f"{symbol}: hesaplanan miktar ({qty}) borsa min. miktarının ({filters['min_qty']}) altında."
            )
        return qty

    # --- emir açma ---

    def open_position(self, signal: Signal) -> Position:
        symbol = signal.symbol
        self.ensure_leverage(symbol)

        balance = self.get_available_balance_usdt()
        qty = self.compute_quantity(symbol, signal, balance)

        side = "BUY" if signal.direction == "long" else "SELL"
        opposite = "SELL" if signal.direction == "long" else "BUY"
        filters = self._symbol_filters_for(symbol)
        stop_price = _round_step(signal.stop, filters["tick_size"])
        target_price = _round_step(signal.target, filters["tick_size"])

        entry_order = self.client.futures_create_order(
            symbol=symbol, side=side, type="MARKET", quantity=qty
        )

        sl_order = self.client.futures_create_order(
            symbol=symbol,
            side=opposite,
            type="STOP_MARKET",
            stopPrice=stop_price,
            closePosition=True,
            workingType="MARK_PRICE",
        )
        tp_order = self.client.futures_create_order(
            symbol=symbol,
            side=opposite,
            type="TAKE_PROFIT_MARKET",
            stopPrice=target_price,
            closePosition=True,
            workingType="MARK_PRICE",
        )

        logger.info(
            "Pozisyon açıldı: %s %s qty=%s entry=%s stop=%s target=%s",
            symbol,
            signal.direction,
            qty,
            signal.entry,
            stop_price,
            target_price,
        )

        return Position(
            symbol=symbol,
            direction=signal.direction,
            entry=signal.entry,
            stop=stop_price,
            target=target_price,
            qty=qty,
            entry_order_id=str(entry_order.get("orderId")),
            sl_order_id=str(sl_order.get("orderId")),
            tp_order_id=str(tp_order.get("orderId")),
            mode="auto",
        )

    # --- kapanış senkronizasyonu ---

    def check_closed(self, position: Position) -> Trade | None:
        """Borsadan pozisyonun kapanıp kapanmadığını kontrol eder; kapandıysa
        hangi emrin (SL/TP) dolduğunu tespit edip diğerini iptal eder ve bir
        `Trade` kaydı döner. Hâlâ açıksa None döner."""
        positions = self.client.futures_position_information(symbol=position.symbol)
        amt = float(positions[0]["positionAmt"]) if positions else 0.0
        if abs(amt) > 1e-12:
            return None  # hâlâ açık

        sl_status = self.client.futures_get_order(symbol=position.symbol, orderId=position.sl_order_id)
        tp_status = self.client.futures_get_order(symbol=position.symbol, orderId=position.tp_order_id)

        if tp_status["status"] == "FILLED":
            exit_reason = "tp"
            exit_price = float(tp_status.get("avgPrice") or position.target)
            self._cancel_quiet(position.symbol, position.sl_order_id)
        elif sl_status["status"] == "FILLED":
            exit_reason = "sl"
            exit_price = float(sl_status.get("avgPrice") or position.stop)
            self._cancel_quiet(position.symbol, position.tp_order_id)
        else:
            exit_reason = "manual"
            exit_price = position.stop if position.direction == "long" else position.target
            self._cancel_quiet(position.symbol, position.sl_order_id)
            self._cancel_quiet(position.symbol, position.tp_order_id)

        direction_sign = 1 if position.direction == "long" else -1
        pnl = (exit_price - position.entry) * position.qty * direction_sign

        return Trade(
            symbol=position.symbol,
            direction=position.direction,
            entry=position.entry,
            stop=position.stop,
            target=position.target,
            qty=position.qty,
            opened_at=position.opened_at,
            closed_at=time.time(),
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl_usdt=pnl,
            mode=position.mode,
        )

    def _cancel_quiet(self, symbol: str, order_id: str | None) -> None:
        if not order_id:
            return
        try:
            self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
        except Exception:
            logger.debug("Emir zaten kapalı/iptal edilmiş olabilir: %s/%s", symbol, order_id)
