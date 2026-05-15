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

        # Primary: Binance
        self._tasks.append(
            asyncio.create_task(self.binance.connect(), name="binance_ws")
        )

        # Secondary: Bybit (redundancy)
        self._tasks.append(
            asyncio.create_task(self.bybit.connect(), name="bybit_ws")
        )

        logger.info("DataManager started", tasks=len(self._tasks))

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

    async def _on_liquidation(self, liq: dict) -> None:
        """Process incoming liquidation event."""
        await CandleCache.store_liquidation(liq)
