"""
Dr. Venom Trader - Signal Engine v2
Orchestrates all four upgraded signal modules.
"""

import asyncio
import structlog
from typing import Dict, List

from app.config import settings
from app.services.candle_cache import CandleCache
from app.signals.alfa import AlfaSignal
from app.signals.beta import BetaSignal
from app.signals.delta import DeltaSignal
from app.signals.gamma import GammaSignal
from app.signals.base import SignalResult
from app.ws.manager import ws_manager

logger = structlog.get_logger()

# Upgraded to 300 to support longer-term zigzag and squeeze lookbacks
CANDLE_COUNT = 300
CANDLE_TIMEFRAMES = ["1D", "4H", "2H", "1H", "30m", "15m", "5m", "3m", "1m"]
COMPUTE_INTERVAL = 5  


class SignalEngine:
    """Runs all signal modules periodically and caches results."""

    def __init__(self):
        self.alfa = AlfaSignal()
        self.beta = BetaSignal()
        self.delta = DeltaSignal()
        self.gamma = GammaSignal()
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="signal_engine")
        self._pubsub_task = asyncio.create_task(self._listen_for_settings(), name="settings_listener")
        logger.info("Signal engine v2 started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        if hasattr(self, '_pubsub_task') and self._pubsub_task:
            self._pubsub_task.cancel()
        logger.info("Signal engine stopped")

    async def _listen_for_settings(self) -> None:
        from app.redis_client import RedisManager
        import json
        redis = await RedisManager.get_client()
        pubsub = redis.pubsub()
        await pubsub.subscribe("settings:reload")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    logger.info("Hot-reloading settings for signals", updated=data.get("signals_updated"))
                    await self.reload_settings_from_db()
        except asyncio.CancelledError:
            await pubsub.unsubscribe("settings:reload")

    async def reload_settings_from_db(self) -> None:
        from app.database import async_session
        from sqlalchemy import select
        from app.models.settings import SignalSetting
        
        try:
            async with async_session() as db:
                result = await db.execute(select(SignalSetting))
                settings_list = result.scalars().all()
                
            settings_dict = {"ALFA": {}, "BETA": {}, "DELTA": {}, "GAMMA": {}}
            for s in settings_list:
                if s.signal_type in settings_dict:
                    settings_dict[s.signal_type][s.timeframe] = s.parameters
                    
            if hasattr(self.alfa, "update_settings"): self.alfa.update_settings(settings_dict["ALFA"])
            if hasattr(self.beta, "update_settings"): self.beta.update_settings(settings_dict["BETA"])
            if hasattr(self.delta, "update_settings"): self.delta.update_settings(settings_dict["DELTA"])
            if hasattr(self.gamma, "update_settings"): self.gamma.update_settings(settings_dict["GAMMA"])
            
            logger.info("Settings reloaded successfully from DB")
        except Exception as e:
            logger.error("Failed to reload settings from DB", error=str(e))

    async def _run_loop(self) -> None:
        while self._running:
            try:
                for symbol in settings.default_symbols:
                    await self._compute_for_symbol(symbol)
            except Exception as e:
                logger.error("Signal engine error", error=str(e))
            await asyncio.sleep(COMPUTE_INTERVAL)

    async def _compute_for_symbol(self, symbol: str) -> None:
        candles_by_tf: Dict[str, List[dict]] = {}
        for tf in CANDLE_TIMEFRAMES:
            candles_by_tf[tf] = await CandleCache.get_candles(symbol, tf, count=CANDLE_COUNT)

        for module in [self.alfa, self.beta, self.delta, self.gamma]:
            try:
                results = await module.compute_all_timeframes(symbol, candles_by_tf)
                for result in results:
                    await CandleCache.store_signal(
                        symbol=result.symbol,
                        signal_type=result.signal_type,
                        timeframe=result.timeframe,
                        signal_data=result.to_dict(),
                    )
                    await ws_manager.broadcast_signal(symbol, result.to_dict())
            except Exception as e:
                logger.error("Signal compute error", module=module.SIGNAL_TYPE, error=str(e))

    async def compute_now(self, symbol: str) -> Dict:
        candles_by_tf = {}
        for tf in CANDLE_TIMEFRAMES:
            candles_by_tf[tf] = await CandleCache.get_candles(symbol, tf, count=CANDLE_COUNT)

        all_results = {}
        for module in [self.alfa, self.beta, self.delta, self.gamma]:
            results = await module.compute_all_timeframes(symbol, candles_by_tf)
            all_results[module.SIGNAL_TYPE] = {r.timeframe: r.to_dict() for r in results}
        return all_results

signal_engine = SignalEngine()
