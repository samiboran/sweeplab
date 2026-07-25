"""Binance WebSocket kline (mum) veri katmanı.

Tüm semboller tek bir "combined stream" bağlantısı üzerinden dinlenir
(wss://stream.binance.com:9443/stream?streams=...). Bu, genel (public) market
data soketidir — API key gerekmez, sadece piyasa fiyatı akışı sağlar.
Emir yürütme ayrı olarak `bot/execution.py` üzerinden Futures REST API ile
yapılır.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

import websockets

from bot.config import Config
from bot.models import Candle

logger = logging.getLogger(__name__)

OnCandle = Callable[[str, Candle], None]


def _stream_name(symbol: str, interval: str) -> str:
    return f"{symbol.lower()}@kline_{interval}"


class BinanceKlineStream:
    """Birden çok sembol için otomatik yeniden bağlanan WebSocket istemcisi."""

    def __init__(self, config: Config, on_candle: OnCandle):
        self.config = config
        self.on_candle = on_candle
        self._stop = asyncio.Event()
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    def stop(self) -> None:
        self._stop.set()

    def _url(self) -> str:
        streams = "/".join(_stream_name(s, self.config.kline_interval) for s in self.config.symbols)
        return f"{self.config.ws_base_url}/stream?streams={streams}"

    async def run(self) -> None:
        consumer = asyncio.create_task(self._consume())
        try:
            await self._read_loop()
        finally:
            consumer.cancel()

    async def _consume(self) -> None:
        """Mesajları sıraya girdikleri sırayla, tek seferde bir tane işler —
        WS okuma döngüsünü (bloklayan emir/REST çağrıları yüzünden) kilitlemeden
        mum sırasını (open_time sırasını) bozmadan işlemeyi garanti eder."""
        while True:
            raw = await self._queue.get()
            try:
                await asyncio.to_thread(self._handle_message, raw)
            except Exception:
                logger.exception("Mesaj işleme kuyruğunda beklenmeyen hata.")

    async def _read_loop(self) -> None:
        url = self._url()
        backoff = 1.0
        while not self._stop.is_set():
            try:
                logger.info("Binance WS bağlantısı kuruluyor: %s", url)
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    backoff = 1.0
                    logger.info("Binance WS bağlandı (%d sembol).", len(self.config.symbols))
                    while not self._stop.is_set():
                        raw = await asyncio.wait_for(ws.recv(), timeout=90)
                        await self._queue.put(raw)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Binance WS bağlantısı koptu, %.0fs sonra yeniden denenecek.", backoff
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
            data = msg.get("data", msg)
            k = data["k"]
            symbol = data["s"]
            candle = Candle(
                open_time=k["t"],
                open=float(k["o"]),
                high=float(k["h"]),
                low=float(k["l"]),
                close=float(k["c"]),
                close_time=k["T"],
                is_closed=bool(k["x"]),
            )
        except (KeyError, TypeError, ValueError):
            logger.exception("WS mesajı işlenemedi: %.300s", raw)
            return

        try:
            self.on_candle(symbol, candle)
        except Exception:
            logger.exception("on_candle callback hata verdi (sembol=%s)", symbol)
