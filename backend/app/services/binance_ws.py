"""
Dr. Venom Trader - Binance Futures WebSocket Connector
Primary data source for real-time price, candles, and liquidation streams.
Uses raw WebSocket for maximum control and reliability.
"""

import asyncio
import json
import time
import structlog
from typing import Callable, Dict, List, Optional
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

logger = structlog.get_logger()

# Binance Futures WebSocket base URL
BINANCE_WS_BASE = "wss://fstream.binance.com"


class BinanceWSConnector:
    """
    Manages WebSocket connections to Binance Futures.
    Streams: klines (candles), markPrice, forceOrder (liquidations).
    """

    def __init__(
        self,
        symbols: List[str],
        timeframes: List[str],
        on_candle: Optional[Callable] = None,
        on_price: Optional[Callable] = None,
        on_liquidation: Optional[Callable] = None,
    ):
        self.symbols = [s.lower() for s in symbols]
        self.timeframes = timeframes
        self.on_candle = on_candle
        self.on_price = on_price
        self.on_liquidation = on_liquidation
        self._running = False
        self._ws = None
        self._reconnect_delay = 1  # seconds, exponential backoff
        self._max_reconnect_delay = 60
        self._last_pong = time.time()

    def _build_stream_url(self) -> str:
        """Build the combined stream URL for all symbols and timeframes."""
        streams = []
        for symbol in self.symbols:
            # Mark price stream (real-time price)
            streams.append(f"{symbol}@markPrice@1s")
            # Liquidation stream
            streams.append(f"{symbol}@forceOrder")
            # Kline streams for each timeframe
            for tf in self.timeframes:
                binance_tf = self._normalize_timeframe(tf)
                if binance_tf:
                    streams.append(f"{symbol}@kline_{binance_tf}")
        stream_param = "/".join(streams)
        return f"{BINANCE_WS_BASE}/stream?streams={stream_param}"

    @staticmethod
    def _normalize_timeframe(tf: str) -> Optional[str]:
        """Convert our timeframe format to Binance's format."""
        mapping = {
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", 
            "30m": "30m", "1H": "1h", "2H": "2h", "4H": "4h", "1D": "1d",
        }
        return mapping.get(tf)

    async def connect(self) -> None:
        """Main connection loop with automatic reconnection."""
        self._running = True
        while self._running:
            try:
                url = self._build_stream_url()
                logger.info("Connecting to Binance Futures WS", url=url[:80] + "...")
                async with ws_connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1  # Reset on successful connect
                    self._last_pong = time.time()
                    logger.info("Binance WS connected", symbols=self.symbols)
                    await self._listen(ws)
            except ConnectionClosed as e:
                logger.warning("Binance WS connection closed", code=e.code, reason=str(e.reason))
            except Exception as e:
                logger.error("Binance WS error", error=str(e))

            if self._running:
                logger.info("Reconnecting in {delay}s", delay=self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

    async def _listen(self, ws) -> None:
        """Process incoming WebSocket messages."""
        async for raw_msg in ws:
            try:
                msg = json.loads(raw_msg)
                stream = msg.get("stream", "")
                data = msg.get("data", {})

                if "@kline_" in stream:
                    await self._handle_kline(data)
                elif "@markPrice" in stream:
                    await self._handle_mark_price(data)
                elif "@forceOrder" in stream:
                    await self._handle_liquidation(data)

            except json.JSONDecodeError:
                logger.warning("Failed to parse Binance message")
            except Exception as e:
                logger.error("Error processing Binance message", error=str(e))

    async def _handle_kline(self, data: dict) -> None:
        """Process kline/candle data."""
        k = data.get("k", {})
        candle = {
            "symbol": data.get("s", ""),
            "timeframe": k.get("i", ""),
            "open_time": k.get("t", 0),
            "close_time": k.get("T", 0),
            "open": float(k.get("o", 0)),
            "high": float(k.get("h", 0)),
            "low": float(k.get("l", 0)),
            "close": float(k.get("c", 0)),
            "volume": float(k.get("v", 0)),
            "is_closed": k.get("x", False),
            "timestamp": time.time(),
        }
        if self.on_candle:
            await self.on_candle(candle)

    async def _handle_mark_price(self, data: dict) -> None:
        """Process mark price updates."""
        price_data = {
            "symbol": data.get("s", ""),
            "price": float(data.get("p", 0)),
            "index_price": float(data.get("i", 0)),
            "funding_rate": float(data.get("r", 0)),
            "timestamp": data.get("E", 0),
        }
        if self.on_price:
            await self.on_price(price_data)

    async def _handle_liquidation(self, data: dict) -> None:
        """Process forced liquidation orders."""
        o = data.get("o", {})
        liq = {
            "symbol": o.get("s", ""),
            "side": o.get("S", ""),  # BUY = short liq, SELL = long liq
            "price": float(o.get("p", 0)),
            "quantity": float(o.get("q", 0)),
            "usd_value": float(o.get("p", 0)) * float(o.get("q", 0)),
            "trade_time": o.get("T", 0),
            "timestamp": time.time(),
        }
        if self.on_liquidation:
            await self.on_liquidation(liq)

    async def disconnect(self) -> None:
        """Gracefully disconnect."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Binance WS disconnected")
