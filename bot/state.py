"""JSON tabanlı, süreçler arası paylaşılan durum deposu.

Bot ve panel (Streamlit) ayrı süreçler olarak çalışır; aralarında veritabanı
kurmaya gerek yok — bot her güncellemede `state.json`'ı atomik olarak yazar,
panel periyodik olarak okur. Kill switch ayrı bir dosya bayrağıdır
(`bot_state/DUR`) böylece panel/Telegram, botun JSON yazma döngüsüyle
yarışmadan anında durdurabilir.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bot.config import Config
from bot.models import Position, Trade

MAX_TRADE_HISTORY = 500


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _empty_state(config: Config) -> dict[str, Any]:
    return {
        "updated_at": _now_iso(),
        "phase": config.phase,
        "kill_switch": config.kill_switch_path.exists(),
        "daily_pnl_usdt": 0.0,
        "daily_pnl_date": _today_str(),
        "daily_loss_limit_hit": False,
        "daily_start_balance": None,
        "positions": {},
        "trades": [],
        "symbols": {},
    }


class StateStore:
    """Bot tarafında yazan, panel tarafında okunan tek gerçek kaynak (source of truth)."""

    def __init__(self, config: Config):
        self.config = config
        self._lock = threading.Lock()
        if not self.config.state_file.exists():
            self._write(_empty_state(config))

    # --- düşük seviye I/O ---

    def _read(self) -> dict[str, Any]:
        try:
            with open(self.config.state_file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return _empty_state(self.config)

    def _write(self, data: dict[str, Any]) -> None:
        data["updated_at"] = _now_iso()
        dir_ = self.config.state_file.parent
        fd, tmp_path = tempfile.mkstemp(prefix=".state_", dir=dir_)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.config.state_file)
        except BaseException:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def _mutate(self, fn) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            fn(data)
            self._roll_daily_pnl_if_new_day(data)
            self._write(data)
            return data

    @staticmethod
    def _roll_daily_pnl_if_new_day(data: dict[str, Any]) -> None:
        today = _today_str()
        if data.get("daily_pnl_date") != today:
            data["daily_pnl_date"] = today
            data["daily_pnl_usdt"] = 0.0
            data["daily_loss_limit_hit"] = False
            data["daily_start_balance"] = None

    # --- genel okuma ---

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            self._roll_daily_pnl_if_new_day(data)
            return data

    # --- kill switch ---

    def is_kill_switch_active(self) -> bool:
        return self.config.kill_switch_path.exists()

    def set_kill_switch(self, active: bool) -> None:
        if active:
            self.config.kill_switch_path.write_text(_now_iso())
        elif self.config.kill_switch_path.exists():
            self.config.kill_switch_path.unlink()

        def _mut(data: dict[str, Any]) -> None:
            data["kill_switch"] = active

        self._mutate(_mut)

    # --- sembol bilgisi (trend + izlenen seviye) ---

    def set_symbol_info(self, symbol: str, info: dict[str, Any]) -> None:
        def _mut(data: dict[str, Any]) -> None:
            data["symbols"][symbol] = {**info, "updated_at": _now_iso()}

        self._mutate(_mut)

    # --- pozisyonlar ---

    def upsert_position(self, position: Position) -> None:
        def _mut(data: dict[str, Any]) -> None:
            data["positions"][position.symbol] = asdict(position)

        self._mutate(_mut)

    def remove_position(self, symbol: str) -> None:
        def _mut(data: dict[str, Any]) -> None:
            data["positions"].pop(symbol, None)

        self._mutate(_mut)

    def open_position_count(self) -> int:
        return len(self.snapshot().get("positions", {}))

    def has_position(self, symbol: str) -> bool:
        return symbol in self.snapshot().get("positions", {})

    # --- işlem geçmişi + günlük PnL ---

    def add_trade(self, trade: Trade) -> None:
        def _mut(data: dict[str, Any]) -> None:
            data["trades"].append(asdict(trade))
            data["trades"] = data["trades"][-MAX_TRADE_HISTORY:]
            data["daily_pnl_usdt"] = round(data.get("daily_pnl_usdt", 0.0) + trade.pnl_usdt, 8)

        self._mutate(_mut)

    def set_daily_loss_limit_hit(self, hit: bool) -> None:
        def _mut(data: dict[str, Any]) -> None:
            data["daily_loss_limit_hit"] = hit

        self._mutate(_mut)

    def daily_pnl_usdt(self) -> float:
        return self.snapshot().get("daily_pnl_usdt", 0.0)

    def is_daily_loss_limit_hit(self) -> bool:
        return self.snapshot().get("daily_loss_limit_hit", False)

    # --- gün başı bakiye (günlük zarar limiti yüzdesi bunun üzerinden hesaplanır) ---

    def ensure_daily_start_balance(self, balance: float) -> float:
        """Gün için başlangıç bakiyesi henüz kaydedilmemişse şimdi kaydeder,
        kaydedilmişse mevcut değeri döner (gün içinde sabit kalmalı)."""
        data = self.snapshot()
        if data.get("daily_start_balance") is None:
            def _mut(d: dict[str, Any]) -> None:
                if d.get("daily_start_balance") is None:
                    d["daily_start_balance"] = balance

            data = self._mutate(_mut)
        return data.get("daily_start_balance") or balance
