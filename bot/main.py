"""Bot giriş noktası: `python -m bot.main`.

Faz, güvenlik parametreleri vb. her şey `.env` üzerinden `bot/config.py` ile
okunur — burada hiçbir sabit değer yoktur.
"""
from __future__ import annotations

import asyncio
import logging

from bot.config import CONFIG, Config
from bot.execution import FuturesExecutor
from bot.notifier import TelegramNotifier
from bot.risk import RiskManager
from bot.state import StateStore
from bot.strategy_engine import StrategyEngine
from bot.ws_client import BinanceKlineStream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("bot.main")

POSITION_SYNC_INTERVAL_SEC = 30
DAILY_LOSS_CHECK_INTERVAL_SEC = 60


async def _run_periodic(fn, interval_sec: float) -> None:
    while True:
        await asyncio.sleep(interval_sec)
        try:
            await asyncio.to_thread(fn)
        except Exception:
            logger.exception("Periyodik görev hata verdi.")


def _build_executor(config: Config) -> FuturesExecutor | None:
    if not config.auto_execute:
        logger.info("Faz=%s -> auto_execute kapalı, yürütme istemcisi kurulmayacak (sadece bildirim).", config.phase)
        return None
    try:
        return FuturesExecutor(config)
    except Exception:
        logger.exception(
            "Binance Futures istemcisi kurulamadı — API key/secret .env dosyasında tanımlı mı kontrol edin."
        )
        raise


async def main() -> None:
    config = CONFIG
    logger.info(
        "SweepLab Bot başlıyor — faz=%s testnet=%s auto_execute=%s semboller=%s kaldıraç=%sx risk/işlem=%%%s",
        config.phase,
        config.is_testnet,
        config.auto_execute,
        config.symbols,
        config.leverage,
        config.risk_pct_per_trade,
    )

    state = StateStore(config)
    risk = RiskManager(config, state)
    notifier = TelegramNotifier(config, state)
    notifier.start_command_listener()

    executor = _build_executor(config)
    engine = StrategyEngine(config, state, risk, notifier, executor)

    stream = BinanceKlineStream(config, engine.handle_candle)

    notifier.send(
        f"\U0001F916 Bot başladı — faz: {config.phase}, semboller: {', '.join(config.symbols)}, "
        f"kaldıraç: {config.leverage}x, günlük zarar limiti: %{config.daily_loss_limit_pct}"
    )

    tasks = [asyncio.create_task(stream.run(), name="ws-stream")]
    if executor is not None:
        tasks.append(
            asyncio.create_task(
                _run_periodic(engine.sync_closed_positions, POSITION_SYNC_INTERVAL_SEC),
                name="sync-positions",
            )
        )
        tasks.append(
            asyncio.create_task(
                _run_periodic(engine.check_daily_loss_limit, DAILY_LOSS_CHECK_INTERVAL_SEC),
                name="daily-loss-check",
            )
        )

    try:
        await asyncio.gather(*tasks)
    finally:
        stream.stop()
        notifier.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot durduruldu (Ctrl+C).")
