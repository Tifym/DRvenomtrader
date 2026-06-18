"""
Dr. Venom Trader - Confluence Alert Engine v2
=============================================
Upgrades from v1:
  - Weighted Scoring system: tf_weight x signal_weight x strength.
  - Signal Tiers: VALID, STRONG, ULTRA based on score thresholds.
  - Score-band dedup: Re-fires alert if confluence score jumps to next tier.
  - Minimum strength gate for components.
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

# Track alerts to avoid duplicates: (symbol:tf:direction) -> tier
_fired_alerts: Dict[str, str] = {}

# v2 Weighted Scoring parameters
TF_WEIGHTS = {
    "1D": 4.0, "4H": 3.0, "2H": 2.0, "1H": 2.0,
    "30m": 1.5, "15m": 1.0, "5m": 0.75, "3m": 0.5, "1m": 0.25
}

SIG_WEIGHTS = {
    "ALFA": 1.0,  # Fib Zone
    "BETA": 1.0,  # Divergence
    "GAMMA": 0.9, # Liquidations
    "DELTA": 0.8  # Bollinger
}

# Score Thresholds for alerting
TIER_VALID = 4.0
TIER_STRONG = 6.0
TIER_ULTRA = 8.0
MIN_CONFLUENCE_COUNT = 2
MIN_STRENGTH = 0.25

CHECK_INTERVAL = 10  # seconds

class ConfluenceMonitor:
    """Monitors signals for weighted confluence and fires alerts."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="confluence_monitor")
        logger.info("Confluence monitor v2 started")

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

    def _get_tier(self, score: float) -> str:
        if score >= TIER_ULTRA: return "ULTRA"
        if score >= TIER_STRONG: return "STRONG"
        if score >= TIER_VALID: return "VALID"
        return "NONE"

    async def _check_confluence(self, symbol: str) -> None:
        """Check weighted confluence on all timeframes."""
        all_signals = await CandleCache.get_all_signals(symbol)

        # tf -> direction -> list of signal dicts
        tf_data: Dict[str, Dict[str, list]] = {} 
        
        for sig_type, timeframes in all_signals.items():
            for tf, sig_data in timeframes.items():
                if not sig_data or sig_data.get("direction") == "NEUTRAL":
                    continue
                    
                strength = sig_data.get("strength", 0.0)
                if strength < MIN_STRENGTH:
                    continue

                if tf not in tf_data:
                    tf_data[tf] = {"LONG": [], "SHORT": []}
                    
                direction = sig_data["direction"]
                if direction in tf_data[tf]:
                    tf_data[tf][direction].append({
                        "type": sig_type,
                        "strength": strength,
                        "label": sig_data.get("label", "")
                    })

        # Calculate scores
        for tf, dirs in tf_data.items():
            tf_w = TF_WEIGHTS.get(tf, 1.0)
            
            for direction, signals in dirs.items():
                if len(signals) < MIN_CONFLUENCE_COUNT:
                    self._clear_alert(symbol, tf, direction)
                    continue

                score = 0.0
                sig_types = []
                for s in signals:
                    s_w = SIG_WEIGHTS.get(s["type"], 1.0)
                    score += tf_w * s_w * s["strength"]
                    sig_types.append(f"{s['type']}({s['strength']:.1f})")

                tier = self._get_tier(score)
                alert_key = f"{symbol}:{tf}:{direction}"

                if tier != "NONE":
                    prev_tier = _fired_alerts.get(alert_key)
                    # Fire if it's a new alert, OR if it upgraded to a higher tier
                    if prev_tier != tier and (prev_tier is None or self._is_upgrade(prev_tier, tier)):
                        _fired_alerts[alert_key] = tier
                        await self._fire_alert(symbol, tf, direction, len(signals), sig_types, score, tier)
                else:
                    self._clear_alert(symbol, tf, direction)

    def _is_upgrade(self, old_tier: str, new_tier: str) -> bool:
        ranks = {"NONE": 0, "VALID": 1, "STRONG": 2, "ULTRA": 3}
        return ranks[new_tier] > ranks[old_tier]

    def _clear_alert(self, symbol: str, tf: str, direction: str):
        key = f"{symbol}:{tf}:{direction}"
        if key in _fired_alerts:
            del _fired_alerts[key]

    async def _fire_alert(self, symbol: str, tf: str, direction: str, count: int, sig_types: list, score: float, tier: str) -> None:
        logger.info("Confluence alert v2", symbol=symbol, tf=tf, direction=direction, tier=tier, score=round(score,2))

        # Standard v1 format for Telegram but augmented
        msg = format_confluence_alert(symbol, tf, direction, count, [s.split('(')[0] for s in sig_types])
        msg += f"\n\n🔥 **Tier:** {tier} | Score: {score:.1f}"

        await send_telegram_alert(msg)

        emoji = "🚀" if direction == "LONG" else "🩸"
        discord_msg = f"{emoji} **[{tier}] {symbol} {tf}** — {direction} confluence ({count}/4) | Score: {score:.1f}\n`{', '.join(sig_types)}`"
        await send_discord_alert(discord_msg, title="🎯 V2 Confluence Alert")

        await ws_manager.broadcast_alert({
            "type": "confluence",
            "symbol": symbol,
            "timeframe": tf,
            "direction": direction,
            "count": count,
            "signals": [s.split('(')[0] for s in sig_types],
            "score": round(score, 1),
            "tier": tier,
            "message": f"[{tier}] {symbol} {tf} {direction} (Score: {score:.1f})",
        })
