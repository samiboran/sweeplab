"""Telegram bildirimleri + kill switch komut dinleyicisi.

TradingView/3. parti köprü yok — doğrudan Telegram Bot API (`requests` ile
`sendMessage` / `getUpdates`). `/dur` komutu kill switch dosyasını
(`bot_state/DUR`) oluşturur; `RiskManager` bunu her yeni pozisyon
denemesinde kontrol eder.
"""
from __future__ import annotations

import logging
import threading
import time

import requests

from bot.config import Config
from bot.models import Signal, Trade
from bot.state import StateStore

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}"


class TelegramNotifier:
    def __init__(self, config: Config, state: StateStore):
        self.config = config
        self.state = state
        self._last_update_id = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.config.telegram_bot_token and self.config.telegram_chat_id)

    def _api_url(self, method: str) -> str:
        return f"{API_BASE.format(token=self.config.telegram_bot_token)}/{method}"

    def send(self, text: str) -> None:
        if not self.enabled:
            logger.info("[Telegram devre dışı] %s", text)
            return
        try:
            requests.post(
                self._api_url("sendMessage"),
                json={"chat_id": self.config.telegram_chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
        except requests.RequestException:
            logger.exception("Telegram mesajı gönderilemedi.")

    # --- olay bildirimleri ---

    def notify_signal(self, signal: Signal, auto_executed: bool) -> None:
        mode = "OTOMATİK EMİR AÇILDI" if auto_executed else "SADECE BİLDİRİM (manuel onay bekleniyor)"
        text = (
            f"\U0001F4E1 <b>{signal.symbol}</b> — {signal.direction.upper()} sinyali\n"
            f"Mod: {mode}\n"
            f"Giriş: {signal.entry}\nStop: {signal.stop}\nHedef: {signal.target}\n"
            f"Süpürülen seviye: {signal.swept_level}\nSebep: {signal.reason}"
        )
        self.send(text)

    def notify_signal_blocked(self, signal: Signal, reason: str) -> None:
        text = (
            f"⚠️ <b>{signal.symbol}</b> {signal.direction.upper()} sinyali bulundu "
            f"ama emir açılmadı ({reason})."
        )
        self.send(text)

    def notify_trade_closed(self, trade: Trade) -> None:
        emoji = "✅" if trade.pnl_usdt >= 0 else "\U0001F6D1"
        text = (
            f"{emoji} <b>{trade.symbol}</b> pozisyon kapandı ({trade.exit_reason.upper()})\n"
            f"Yön: {trade.direction} Miktar: {trade.qty}\n"
            f"Giriş: {trade.entry} Çıkış: {trade.exit_price}\n"
            f"PnL: {trade.pnl_usdt:.2f} USDT"
        )
        self.send(text)

    def notify_daily_loss_limit(self, loss_pct: float) -> None:
        self.send(
            f"\U0001F6A8 GÜNLÜK ZARAR LİMİTİ AŞILDI (%{loss_pct:.1f}) — bot yeni işlem açmayı durdurdu.\n"
            f"Limit yarın (UTC) otomatik sıfırlanır. Erken devam etmek için /devam yazın."
        )

    def notify_kill_switch(self, active: bool) -> None:
        if active:
            self.send(
                "\U0001F6D1 KILL SWITCH AKTİF — bot durduruldu, yeni işlem açılmayacak.\n"
                "Devam için /devam yazın."
            )
        else:
            self.send("▶️ Kill switch kaldırıldı, bot normal çalışmaya devam ediyor.")

    def notify_error(self, context: str, error: Exception) -> None:
        self.send(f"❌ Hata ({context}): {error}")

    # --- komut dinleyici ---

    def start_command_listener(self) -> None:
        if not self.enabled:
            logger.warning("Telegram token/chat_id tanımlı değil, komut dinleyici başlatılmadı.")
            return
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="telegram-poller")
        self._thread.start()
        logger.info("Telegram komut dinleyici başlatıldı (/dur, /devam, /durum).")

    def stop(self) -> None:
        self._stop.set()

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._poll_once()
            except Exception:
                logger.exception("Telegram komut sorgusu başarısız.")
            time.sleep(self.config.telegram_poll_interval_sec)

    def _poll_once(self) -> None:
        resp = requests.get(
            self._api_url("getUpdates"),
            params={"offset": self._last_update_id + 1, "timeout": 0},
            timeout=15,
        )
        resp.raise_for_status()
        for update in resp.json().get("result", []):
            self._last_update_id = max(self._last_update_id, update["update_id"])
            message = update.get("message") or {}
            chat_id = str(message.get("chat", {}).get("id", ""))
            text = (message.get("text") or "").strip().lower()
            if not text or chat_id != str(self.config.telegram_chat_id):
                continue
            self._handle_command(text)

    def _handle_command(self, text: str) -> None:
        if text in ("/dur", "dur"):
            self.state.set_kill_switch(True)
            self.notify_kill_switch(True)
        elif text in ("/devam", "/basla", "devam", "basla"):
            self.state.set_kill_switch(False)
            self.state.set_daily_loss_limit_hit(False)
            self.notify_kill_switch(False)
        elif text in ("/durum", "durum"):
            self._send_status()

    def _send_status(self) -> None:
        snap = self.state.snapshot()
        lines = [
            f"Faz: {self.config.phase}",
            f"Kill switch: {'AKTİF' if snap.get('kill_switch') else 'kapalı'}",
            f"Günlük zarar limiti: {'AŞILDI' if snap.get('daily_loss_limit_hit') else 'normal'}",
            f"Günlük PnL: {snap.get('daily_pnl_usdt', 0):.2f} USDT",
            f"Açık pozisyon: {len(snap.get('positions', {}))}/{self.config.max_concurrent_positions}",
        ]
        self.send("\n".join(lines))
