"""
Dr. Venom Trader - Confluence Alert Engine
Monitors signal states and triggers alerts when 3+ signals align.
"""

import asyncio
import json
import structlog
from typing import Dict, Set

from app.config import settings
from app.services.candle_cache import CandleCache
from app.services.alerts.telegram import send_telegram_alert, format_confluence_alert
from app.services.alerts.discord import send_discord_alert
from app.ws.manager import ws_manager

logger = structlog.get_logger()

# Track already-fired alerts to avoid duplicates (symbol:tf:direction)
_fired_alerts: Set[str] = set()
CONFLUENCE_THRESHOLD = 3
CHECK_INTERVAL = 10  # seconds


class ConfluenceMonitor:
    """Monitors signals for confluence and fires alerts."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="confluence_monitor")
        logger.info("Confluence monitor started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        while self._running:
            try:
                for symbol in settings.default_symbols:
                    await self._check_confluence(symbol)
            except Exception as e:
                logger.error("Confluence check error", error=str(e))
            await asyncio.sleep(CHECK_INTERVAL)

    async def _check_confluence(self, symbol: str) -> None:
        """Check if 3+ signals align on any timeframe."""
        all_signals = await CandleCache.get_all_signals(symbol)

        # Group by timeframe
        tf_directions: Dict[str, Dict[str, list]] = {}  # tf -> {LONG: [types], SHORT: [types]}
        for sig_type, timeframes in all_signals.items():
            for tf, sig_data in timeframes.items():
                if not sig_data or sig_data.get("direction") == "NEUTRAL":
                    continue
                if tf not in tf_directions:
                    tf_directions[tf] = {"LONG": [], "SHORT": []}
                direction = sig_data["direction"]
                if direction in tf_directions[tf]:
                    tf_directions[tf][direction].append(sig_type)

        # Check for confluence
        for tf, dirs in tf_directions.items():
            for direction, sig_types in dirs.items():
                if len(sig_types) >= CONFLUENCE_THRESHOLD:
                    alert_key = f"{symbol}:{tf}:{direction}"
                    if alert_key not in _fired_alerts:
                        _fired_alerts.add(alert_key)
                        await self._fire_alert(symbol, tf, direction, len(sig_types), sig_types)
                else:
                    # Clear fired state if confluence breaks
                    for d in ["LONG", "SHORT"]:
                        clear_key = f"{symbol}:{tf}:{d}"
                        _fired_alerts.discard(clear_key)

    async def _fire_alert(self, symbol: str, tf: str, direction: str, count: int, sig_types: list) -> None:
        """Send confluence alert to all channels."""
        logger.info("Confluence alert", symbol=symbol, tf=tf, direction=direction, count=count)

        msg = format_confluence_alert(symbol, tf, direction, count, sig_types)

        # Send to Telegram
        await send_telegram_alert(msg)

        # Send to Discord
        discord_msg = f"**{symbol} {tf}** — {direction} confluence ({count}/4): {', '.join(sig_types)}"
        await send_discord_alert(discord_msg, title="🎯 Confluence Alert")

        # Broadcast to WebSocket clients
        await ws_manager.broadcast_alert({
            "type": "confluence",
            "symbol": symbol,
            "timeframe": tf,
            "direction": direction,
            "count": count,
            "signals": sig_types,
            "message": f"{symbol} {tf}: {direction} confluence ({count}/4) — {', '.join(sig_types)}",
        })


# Global singleton
confluence_monitor = ConfluenceMonitor()
