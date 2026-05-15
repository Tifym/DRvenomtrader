"""
Dr. Venom Trader - Settings API Router
Endpoints for reading/updating configuration at runtime.
"""

import json
from fastapi import APIRouter
from app.config import settings
from app.redis_client import RedisManager

settings_router = APIRouter(prefix="/settings", tags=["Settings"])

SETTINGS_KEY = "app:settings"


@settings_router.get("/")
async def get_settings():
    """Get current application settings."""
    redis = await RedisManager.get_client()
    raw = await redis.get(SETTINGS_KEY)
    custom = json.loads(raw) if raw else {}
    return {
        "symbols": custom.get("symbols", settings.default_symbols),
        "fib_zone_low": custom.get("fib_zone_low", 0.618),
        "fib_zone_high": custom.get("fib_zone_high", 0.786),
        "bb_period": custom.get("bb_period", 20),
        "bb_std_dev": custom.get("bb_std_dev", 2.0),
        "rsi_period": custom.get("rsi_period", 14),
        "confluence_threshold": custom.get("confluence_threshold", 3),
        "alert_telegram": bool(settings.telegram_bot_token),
        "alert_discord": bool(settings.discord_webhook_url),
        "coinglass_enabled": bool(settings.coinglass_api_key),
    }


@settings_router.post("/")
async def update_settings(body: dict):
    """Update application settings (persisted in Redis)."""
    redis = await RedisManager.get_client()
    # Merge with existing
    raw = await redis.get(SETTINGS_KEY)
    current = json.loads(raw) if raw else {}
    allowed_keys = [
        "symbols", "fib_zone_low", "fib_zone_high",
        "bb_period", "bb_std_dev", "rsi_period", "confluence_threshold",
    ]
    for k in allowed_keys:
        if k in body:
            current[k] = body[k]
    await redis.set(SETTINGS_KEY, json.dumps(current))
    return {"status": "updated", "settings": current}
