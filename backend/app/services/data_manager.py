"""
Dr. Venom Trader - Data Manager
Orchestrates all data sources (Binance, Bybit, CoinGlass) and feeds
data into the Redis cache. Runs as background tasks during app lifespan.
"""

import asyncio
import structlog
from typing import List

from app.config import settings
from app.services.binance_ws import BinanceWSConnector
from app.services.bybit_ws import BybitWSConnector
from app.services.candle_cache import CandleCache
from app.ws.manager import ws_manager

logger = structlog.get_logger()

# All supported timeframes across signals
ALL_TIMEFRAMES = [
    "1D", "4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"
]


class DataManager:
    """
    Central data orchestrator. Connects to exchanges and feeds
    real-time data into the Redis candle cache.
    """

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or settings.default_symbols
        self._tasks: List[asyncio.Task] = []

        # Initialize connectors with cache callbacks
        self.binance = BinanceWSConnector(
            symbols=self.symbols,
            timeframes=ALL_TIMEFRAMES,
            on_candle=self._on_candle,
            on_price=self._on_price,
            on_liquidation=self._on_liquidation,
        )
        self.bybit = BybitWSConnector(
            symbols=self.symbols,
            timeframes=ALL_TIMEFRAMES,
            on_candle=self._on_candle,
            on_price=self._on_price,
            on_liquidation=self._on_liquidation,
        )

    async def start(self) -> None:
        """Start all data source connections as background tasks."""
        logger.info("DataManager starting", symbols=self.symbols)

        # Warm up the candle cache in the background to solve cold start
        asyncio.create_task(self.warm_candle_cache())

        # Primary: Binance
        self._tasks.append(
            asyncio.create_task(self.binance.connect(), name="binance_ws")
        )

        # Secondary: Bybit (redundancy)
        self._tasks.append(
            asyncio.create_task(self.bybit.connect(), name="bybit_ws")
        )

        logger.info("DataManager started", tasks=len(self._tasks))

    async def warm_candle_cache(self) -> None:
        """Fetch historical candles from Binance REST API to warm the Redis cache."""
        import httpx
        import time

        logger.info("Warming candle cache from Binance REST API...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            for symbol in self.symbols:
                for tf in ALL_TIMEFRAMES:
                    # Map standard tf to Binance REST interval
                    binance_tf = tf.lower()  # e.g., "1h", "4h", "1d"
                    
                    try:
                        # Check if we already have enough candles in Redis
                        existing_candles = await CandleCache.get_candles(symbol, tf, count=50)
                        if len(existing_candles) >= 50:
                            logger.debug("Cache already warm", symbol=symbol, timeframe=tf, count=len(existing_candles))
                            continue

                        url = "https://fapi.binance.com/fapi/v1/klines"
                        params = {
                            "symbol": symbol.upper(),
                            "interval": binance_tf,
                            "limit": 150
                        }
                        
                        response = await client.get(url, params=params)
                        if response.status_code == 200:
                            klines = response.json()
                            logger.info("Fetched historical candles", symbol=symbol, timeframe=tf, count=len(klines))
                            
                            for k in klines:
                                candle = {
                                    "symbol": symbol.upper(),
                                    "timeframe": tf,
                                    "open_time": int(k[0]),
                                    "close_time": int(k[6]),
                                    "open": float(k[1]),
                                    "high": float(k[2]),
                                    "low": float(k[3]),
                                    "close": float(k[4]),
                                    "volume": float(k[5]),
                                    "is_closed": True,
                                    "timestamp": time.time(),
                                    "source": "binance",
                                }
                                await CandleCache.store_candle(candle)
                        else:
                            logger.warning("Failed to fetch historical candles", symbol=symbol, timeframe=tf, status_code=response.status_code)
                            
                        # Small delay to respect rate limits
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error("Error warming candle cache", symbol=symbol, timeframe=tf, error=str(e))
        logger.info("Candle cache warming complete")

    async def stop(self) -> None:
        """Stop all data sources and cancel background tasks."""
        logger.info("DataManager stopping")
        await self.binance.disconnect()
        await self.bybit.disconnect()

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("DataManager stopped")

    # --- Callbacks ---

    async def _on_candle(self, candle: dict) -> None:
        """Process incoming candle from any source."""
        await CandleCache.store_candle(candle)

    async def _on_price(self, price_data: dict) -> None:
        """Process incoming price update."""
        await CandleCache.store_price(price_data)
        # Broadcast to connected WS clients
        await ws_manager.broadcast_price(price_data["symbol"], price_data)

    async def _on_liquidation(self, liq: dict) -> None:
        """Process incoming liquidation event."""
        await CandleCache.store_liquidation(liq)
