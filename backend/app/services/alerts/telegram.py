"""
Dr. Venom Trader - Telegram Alert Service
Sends signal alerts to Telegram via Bot API.
"""

import structlog
import httpx
from app.config import settings

logger = structlog.get_logger()

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram_alert(message: str, parse_mode: str = "HTML") -> bool:
    """Send an alert message to the configured Telegram chat."""
    if not settings.telegram_bot_token:
        logger.debug("Telegram bot token not configured, skipping alert")
        return False

    if not settings.telegram_chat_id:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                updates_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"
                resp = await client.get(updates_url)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("result", [])
                    if results:
                        for update in reversed(results):
                            message_obj = update.get("message") or update.get("edited_message") or update.get("channel_post")
                            if message_obj and "chat" in message_obj:
                                chat_id = str(message_obj["chat"]["id"])
                                settings.telegram_chat_id = chat_id
                                logger.info("Dynamically retrieved Telegram chat ID from getUpdates", chat_id=chat_id)
                                break
        except Exception as ex:
            logger.warning("Failed to auto-retrieve Telegram chat ID", error=str(ex))

    if not settings.telegram_chat_id:
        logger.debug("Telegram chat ID not configured or found, skipping alert")
        return False

    url = TELEGRAM_API.format(token=settings.telegram_bot_token)
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram alert sent")
                return True
            else:
                logger.warning("Telegram send failed", status=resp.status_code, body=resp.text[:200])
                return False
    except Exception as e:
        logger.error("Telegram alert error", error=str(e))
        return False


def format_signal_alert(symbol: str, signals: list) -> str:
    """Format signal data into a Telegram message."""
    direction_emoji = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪"}
    lines = [f"<b>🐍 Dr. Venom Trader</b>", f"<b>{symbol}</b> Signal Update\n"]
    for sig in signals:
        emoji = direction_emoji.get(sig.get("direction", ""), "⚪")
        lines.append(
            f"{emoji} <b>{sig['signal_type']}</b> {sig['timeframe']}: "
            f"{sig['direction']} ({sig.get('strength', 0)*100:.0f}%) — {sig.get('label', '')}"
        )
    return "\n".join(lines)


def format_confluence_alert(symbol: str, timeframe: str, direction: str, count: int, signals: list) -> str:
    """Format a confluence alert."""
    emoji = "🟢" if direction == "LONG" else "🔴"
    return (
        f"<b>🎯 CONFLUENCE ALERT</b>\n\n"
        f"{emoji} <b>{symbol} {timeframe}</b>\n"
        f"Direction: <b>{direction}</b>\n"
        f"Aligned Signals: <b>{count}/4</b>\n"
        f"Signals: {', '.join(signals)}\n\n"
        f"<i>Dr. Venom Trader</i>"
    )
