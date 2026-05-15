"""
Dr. Venom Trader - Redis Candle Cache
Stores latest candles (multiple timeframes) in Redis for fast signal computation.
Also handles liquidation aggregation and price caching.
"""

import json
import time
import structlog
from typing import Dict, List, Optional
import redis.asyncio as aioredis

from app.redis_client import RedisManager

logger = structlog.get_logger()

# Redis key patterns
CANDLE_KEY = "candle:{symbol}:{timeframe}"        # Latest N candles
PRICE_KEY = "price:{symbol}"                       # Current price
LIQ_KEY = "liq:{symbol}:{timeframe}"              # Liquidation aggregates
LIQ_STREAM_KEY = "liq_stream:{symbol}"            # Recent liquidation events
SIGNAL_KEY = "signal:{symbol}:{signal_type}:{timeframe}"  # Signal states

# Number of candles to keep per timeframe
MAX_CANDLES = 300


class CandleCache:
    """
    Manages candle data in Redis using sorted sets (score = open_time).
    Provides fast reads for signal computation.
    """

    @staticmethod
    async def store_candle(candle: dict) -> None:
        """Store a candle update in Redis."""
        redis = await RedisManager.get_client()
        symbol = candle["symbol"]
        tf = candle["timeframe"]
        key = CANDLE_KEY.format(symbol=symbol, timeframe=tf)

        # Use open_time as score for ordering
        score = candle.get("open_time", time.time())
        value = json.dumps(candle)

        await redis.zadd(key, {value: score})

        # Trim to MAX_CANDLES (remove oldest)
        count = await redis.zcard(key)
        if count > MAX_CANDLES:
            await redis.zremrangebyrank(key, 0, count - MAX_CANDLES - 1)

        # Set TTL (24 hours)
        await redis.expire(key, 86400)

    @staticmethod
    async def get_candles(
        symbol: str, timeframe: str, count: int = 100
    ) -> List[dict]:
        """Retrieve latest N candles for a symbol/timeframe."""
        redis = await RedisManager.get_client()
        key = CANDLE_KEY.format(symbol=symbol, timeframe=timeframe)

        # Get latest candles (highest scores = newest)
        raw = await redis.zrevrange(key, 0, count - 1)
        candles = []
        for item in reversed(raw):  # Reverse to get chronological order
            try:
                candles.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        return candles

    @staticmethod
    async def store_price(price_data: dict) -> None:
        """Store current price for a symbol."""
        redis = await RedisManager.get_client()
        symbol = price_data["symbol"]
        key = PRICE_KEY.format(symbol=symbol)
        await redis.set(key, json.dumps(price_data), ex=60)  # 60s TTL

    @staticmethod
    async def get_price(symbol: str) -> Optional[dict]:
        """Get current price for a symbol."""
        redis = await RedisManager.get_client()
        key = PRICE_KEY.format(symbol=symbol)
        raw = await redis.get(key)
        if raw:
            return json.loads(raw)
        return None

    @staticmethod
    async def store_liquidation(liq: dict) -> None:
        """Store a liquidation event in a sorted set for true rolling window."""
        redis = await RedisManager.get_client()
        symbol = liq["symbol"]
        stream_key = LIQ_STREAM_KEY.format(symbol=symbol)

        timestamp = liq.get("timestamp", time.time())
        value = json.dumps(liq)

        # Store with timestamp as score
        await redis.zadd(stream_key, {value: timestamp})

        # Remove events older than 24 hours
        cutoff = timestamp - 86400
        await redis.zremrangebyscore(stream_key, "-inf", cutoff)
        await redis.expire(stream_key, 86400)

    @staticmethod
    async def get_liquidation_agg(symbol: str, timeframe: str) -> Dict:
        """Calculate aggregated liquidation data over the exact timeframe window."""
        redis = await RedisManager.get_client()
        stream_key = LIQ_STREAM_KEY.format(symbol=symbol)

        # Convert timeframe to seconds
        mapping = {
            "1m": 60, "3m": 180, "5m": 300, "6m": 360, "12m": 720, "15m": 900, "24m": 1440,
            "1H": 3600, "2H": 7200, "3H": 10800, "4H": 14400, "1D": 86400,
        }
        seconds = mapping.get(timeframe, 3600)
        
        now = time.time()
        cutoff = now - seconds

        # Get events within the timeframe
        raw_events = await redis.zrangebyscore(stream_key, cutoff, "+inf")

        long_usd = 0.0
        short_usd = 0.0
        count = 0

        for raw in raw_events:
            try:
                liq = json.loads(raw)
                usd_val = liq.get("usd_value", 0)
                if liq.get("side") == "SELL":  # Long position got sold (liquidated)
                    long_usd += usd_val
                elif liq.get("side") == "BUY": # Short position got bought (liquidated)
                    short_usd += usd_val
                count += 1
            except Exception:
                continue

        return {
            "long_usd": long_usd,
            "short_usd": short_usd,
            "total_count": count,
        }

    @staticmethod
    async def store_signal(
        symbol: str, signal_type: str, timeframe: str, signal_data: dict
    ) -> None:
        """Cache a computed signal state."""
        redis = await RedisManager.get_client()
        key = SIGNAL_KEY.format(
            symbol=symbol, signal_type=signal_type, timeframe=timeframe
        )
        await redis.set(key, json.dumps(signal_data), ex=300)  # 5 min TTL

    @staticmethod
    async def get_signal(
        symbol: str, signal_type: str, timeframe: str
    ) -> Optional[dict]:
        """Get cached signal state."""
        redis = await RedisManager.get_client()
        key = SIGNAL_KEY.format(
            symbol=symbol, signal_type=signal_type, timeframe=timeframe
        )
        raw = await redis.get(key)
        if raw:
            return json.loads(raw)
        return None

    @staticmethod
    async def get_all_signals(symbol: str) -> Dict:
        """Get all cached signals for a symbol."""
        redis = await RedisManager.get_client()
        signals = {}
        for sig_type in ["ALFA", "BETA", "DELTA", "GAMMA"]:
            signals[sig_type] = {}
            # Scan for all timeframes
            pattern = SIGNAL_KEY.format(
                symbol=symbol, signal_type=sig_type, timeframe="*"
            )
            async for key in redis.scan_iter(match=pattern):
                raw = await redis.get(key)
                if raw:
                    data = json.loads(raw)
                    tf = key.split(":")[-1]
                    signals[sig_type][tf] = data
        return signals
