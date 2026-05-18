"""
Dr. Venom Trader - Bybit V5 WebSocket Connector
Secondary/fallback data source for price and liquidation streams.
"""

import asyncio
import json
import time
import structlog
from typing import Callable, List, Optional
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

logger = structlog.get_logger()

BYBIT_WS_PUBLIC = "wss://stream.bybit.com/v5/public/linear"


class BybitWSConnector:
    """
    Manages WebSocket connections to Bybit V5 linear (futures).
    Streams: kline, tickers, liquidation.
    """

    def __init__(
        self,
        symbols: List[str],
        timeframes: List[str],
        on_candle: Optional[Callable] = None,
        on_price: Optional[Callable] = None,
        on_liquidation: Optional[Callable] = None,
    ):
        self.symbols = symbols  # Bybit uses uppercase: BTCUSDT
        self.timeframes = timeframes
        self.on_candle = on_candle
        self.on_price = on_price
        self.on_liquidation = on_liquidation
        self._running = False
        self._ws = None
        self._reconnect_delay = 1

    def _build_subscriptions(self) -> List[str]:
        """Build Bybit subscription topics."""
        subs = []
        for symbol in self.symbols:
            # Ticker for real-time price
            subs.append(f"tickers.{symbol}")
            # Liquidation
            subs.append(f"liquidation.{symbol}")
            # Klines per timeframe
            for tf in self.timeframes:
                bybit_tf = self._normalize_timeframe(tf)
                if bybit_tf:
                    subs.append(f"kline.{bybit_tf}.{symbol}")
        return subs

    @staticmethod
    def _normalize_timeframe(tf: str) -> Optional[str]:
        """Convert our timeframe format to Bybit's format."""
        mapping = {
            "1m": "1", "3m": "3", "5m": "5", "6m": "5",
            "12m": "15", "15m": "15", "24m": "30", "30m": "30",
            "1H": "60", "2H": "120", "3H": "240", "4H": "240",
            "1D": "D",
        }
        return mapping.get(tf)

    async def connect(self) -> None:
        """Main connection loop with automatic reconnection."""
        self._running = True
        while self._running:
            try:
                logger.info("Connecting to Bybit V5 WS")
                async with ws_connect(
                    BYBIT_WS_PUBLIC, ping_interval=20, ping_timeout=10
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1

                    # Subscribe to topics
                    subs = self._build_subscriptions()
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": subs,
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info("Bybit WS subscribed", topics=len(subs))

                    await self._listen(ws)

            except ConnectionClosed as e:
                logger.warning("Bybit WS closed", code=e.code)
            except Exception as e:
                logger.error("Bybit WS error", error=str(e))

            if self._running:
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    async def _listen(self, ws) -> None:
        """Process incoming messages."""
        logger.info("Bybit WS listening loop started")
        async for raw_msg in ws:
            logger.info("Bybit WS raw message received", msg_len=len(raw_msg))
            try:
                msg = json.loads(raw_msg)
                topic = msg.get("topic", "")
                data = msg.get("data", {})

                if topic.startswith("kline."):
                    await self._handle_kline(topic, data)
                elif topic.startswith("tickers."):
                    await self._handle_ticker(data)
                elif topic.startswith("liquidation."):
                    await self._handle_liquidation(data)

            except Exception as e:
                logger.error("Error processing Bybit message", error=str(e))

    async def _handle_kline(self, topic: str, data_list) -> None:
        """Process kline data from Bybit."""
        if not isinstance(data_list, list):
            data_list = [data_list]
        
        bybit_tf = topic.split(".")[1]
        tf_map = {
            "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
            "60": "1H", "120": "2H", "240": "4H", "D": "1D"
        }
        standard_tf = tf_map.get(bybit_tf, bybit_tf)

        for d in data_list:
            symbol = d.get("symbol", topic.split(".")[-1])
            logger.info("Bybit kline received", symbol=symbol, timeframe=standard_tf, is_closed=d.get("confirm", False))
            candle = {
                "symbol": symbol,
                "timeframe": standard_tf,
                "open_time": int(d.get("start", 0)) if d.get("start") else int(time.time() * 1000),
                "close_time": int(d.get("end", 0)) if d.get("end") else int(time.time() * 1000),
                "open": float(d.get("open", 0)),
                "high": float(d.get("high", 0)),
                "low": float(d.get("low", 0)),
                "close": float(d.get("close", 0)),
                "volume": float(d.get("volume", 0)),
                "is_closed": d.get("confirm", False),
                "timestamp": time.time() * 1000,
                "source": "bybit",
            }
            if self.on_candle:
                await self.on_candle(candle)

    async def _handle_ticker(self, data) -> None:
        """Process ticker price data."""
        symbol = data.get("symbol", "")
        price = float(data.get("lastPrice", 0))
        logger.info("Bybit price received", symbol=symbol, price=price)
        price_data = {
            "symbol": symbol,
            "price": price,
            "funding_rate": float(data.get("fundingRate", 0)),
            "timestamp": time.time() * 1000,
            "source": "bybit",
        }
        if self.on_price:
            await self.on_price(price_data)

    async def _handle_liquidation(self, data) -> None:
        """Process liquidation data."""
        liq = {
            "symbol": data.get("symbol", ""),
            "side": data.get("side", ""),
            "price": float(data.get("price", 0)),
            "quantity": float(data.get("size", 0)),
            "usd_value": float(data.get("price", 0)) * float(data.get("size", 0)),
            "timestamp": time.time() * 1000,
            "source": "bybit",
        }
        if self.on_liquidation:
            await self.on_liquidation(liq)

    async def disconnect(self) -> None:
        """Gracefully disconnect."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Bybit WS disconnected")
