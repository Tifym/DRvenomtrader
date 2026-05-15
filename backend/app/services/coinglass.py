"""
Dr. Venom Trader - CoinGlass API Client
Fetches real-time liquidation data across all exchanges.
"""

import asyncio
import time
import structlog
import httpx
from typing import Callable, Dict, List, Optional

from app.config import settings

logger = structlog.get_logger()

COINGLASS_BASE = "https://open-api-v3.coinglass.com/api"


class CoinGlassClient:
    """
    Polls CoinGlass API for aggregated liquidation data.
    Falls back to exchange-direct streams if API key is missing.
    """

    def __init__(
        self,
        symbols: List[str],
        on_liquidation_update: Optional[Callable] = None,
        poll_interval: int = 15,  # seconds between polls
    ):
        self.symbols = symbols
        self.on_liquidation_update = on_liquidation_update
        self.poll_interval = poll_interval
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def _headers(self) -> dict:
        return {
            "accept": "application/json",
            "CoinGlass-API-Key": settings.coinglass_api_key,
        }

    @property
    def is_available(self) -> bool:
        """Check if CoinGlass API key is configured."""
        return bool(settings.coinglass_api_key)

    async def start(self) -> None:
        """Start polling loop for liquidation data."""
        if not self.is_available:
            logger.warning("CoinGlass API key not set, skipping liquidation polling")
            return

        self._running = True
        self._client = httpx.AsyncClient(timeout=10.0)
        logger.info("CoinGlass client started", poll_interval=self.poll_interval)

        while self._running:
            try:
                for symbol in self.symbols:
                    data = await self._fetch_liquidations(symbol)
                    if data and self.on_liquidation_update:
                        await self.on_liquidation_update(data)
            except Exception as e:
                logger.error("CoinGlass poll error", error=str(e))

            await asyncio.sleep(self.poll_interval)

    async def _fetch_liquidations(self, symbol: str) -> Optional[Dict]:
        """
        Fetch liquidation data for a symbol.
        Returns aggregated longs/shorts liquidated per timeframe.
        """
        try:
            # Liquidation history endpoint
            resp = await self._client.get(
                f"{COINGLASS_BASE}/futures/liquidation/v2/history",
                params={"symbol": symbol.replace("USDT", ""), "timeType": "all"},
                headers=self._headers,
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == "0" and result.get("data"):
                    return self._parse_liquidation_data(symbol, result["data"])
            elif resp.status_code == 429:
                logger.warning("CoinGlass rate limited, backing off")
                await asyncio.sleep(30)
            else:
                logger.warning("CoinGlass API error", status=resp.status_code)

        except httpx.TimeoutException:
            logger.warning("CoinGlass timeout", symbol=symbol)
        except Exception as e:
            logger.error("CoinGlass fetch error", symbol=symbol, error=str(e))

        return None

    def _parse_liquidation_data(self, symbol: str, data: list) -> Dict:
        """Parse CoinGlass liquidation response into our format."""
        # Aggregate longs vs shorts across exchanges
        total_long_liq = 0.0
        total_short_liq = 0.0

        for entry in data[-10:]:  # Last 10 data points
            total_long_liq += float(entry.get("longLiquidationUsd", 0))
            total_short_liq += float(entry.get("shortLiquidationUsd", 0))

        return {
            "symbol": symbol,
            "long_liquidations_usd": total_long_liq,
            "short_liquidations_usd": total_short_liq,
            "net_direction": "SELL" if total_long_liq > total_short_liq else "BUY",
            "ratio": (
                total_long_liq / max(total_short_liq, 1)
                if total_long_liq > total_short_liq
                else total_short_liq / max(total_long_liq, 1)
            ),
            "timestamp": time.time(),
            "source": "coinglass",
        }

    async def get_liquidation_history(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Fetch liquidation history for a specific symbol and timeframe."""
        if not self.is_available:
            return None
        if not self._client:
            self._client = httpx.AsyncClient(timeout=10.0)

        try:
            resp = await self._client.get(
                f"{COINGLASS_BASE}/futures/liquidation/v2/history",
                params={"symbol": symbol.replace("USDT", ""), "timeType": timeframe},
                headers=self._headers,
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == "0" and result.get("data"):
                    return result["data"]
            elif resp.status_code == 429:
                logger.warning("CoinGlass rate limited")
        except Exception as e:
            logger.error("CoinGlass history error", symbol=symbol, error=str(e))
        return None

    async def get_aggregated_liquidations(self) -> Optional[Dict]:
        """Fetch globally aggregated liquidations."""
        if not self.is_available:
            return None
        if not self._client:
            self._client = httpx.AsyncClient(timeout=10.0)

        try:
            resp = await self._client.get(
                f"{COINGLASS_BASE}/futures/liquidation/v2/aggregated",
                headers=self._headers,
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except Exception as e:
            logger.error("CoinGlass aggregated error", error=str(e))
        return None

    async def stop(self) -> None:
        """Stop polling."""
        self._running = False
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("CoinGlass client stopped")
