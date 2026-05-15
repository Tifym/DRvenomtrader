"""
Dr. Venom Trader - Discord Alert Service
Sends signal alerts to Discord via Webhook.
"""

import structlog
import httpx
from app.config import settings

logger = structlog.get_logger()


async def send_discord_alert(message: str, title: str = "Dr. Venom Trader") -> bool:
    """Send an alert to the configured Discord webhook."""
    if not settings.discord_webhook_url:
        logger.debug("Discord not configured, skipping alert")
        return False

    payload = {
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": 0x7C4DFF,  # Purple accent
                "footer": {"text": "Dr. Venom Trader • Real-Time Signals"},
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.discord_webhook_url, json=payload)
            if resp.status_code in (200, 204):
                logger.info("Discord alert sent")
                return True
            else:
                logger.warning("Discord send failed", status=resp.status_code)
                return False
    except Exception as e:
        logger.error("Discord alert error", error=str(e))
        return False


def format_discord_signal(symbol: str, sig: dict) -> str:
    """Format a signal for Discord embed."""
    emoji = "🟢" if sig.get("direction") == "LONG" else "🔴" if sig.get("direction") == "SHORT" else "⚪"
    return (
        f"{emoji} **{sig['signal_type']}** {sig['timeframe']}: "
        f"**{sig['direction']}** ({sig.get('strength', 0)*100:.0f}%) — {sig.get('label', '')}"
    )
