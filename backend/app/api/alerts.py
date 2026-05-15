"""
Dr. Venom Trader - Alerts API Router
Endpoints for alert history and manual alert testing.
"""

from fastapi import APIRouter
from app.services.alerts.telegram import send_telegram_alert
from app.services.alerts.discord import send_discord_alert

alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])


@alerts_router.get("/history")
async def get_alert_history():
    """Get recent alert history (placeholder — Stage 6 will use DB)."""
    return {"alerts": [], "total": 0}


@alerts_router.post("/test/telegram")
async def test_telegram():
    """Send a test alert to Telegram."""
    ok = await send_telegram_alert("🐍 <b>Dr. Venom Trader</b>\n\nTest alert — system is working!")
    return {"sent": ok, "channel": "telegram"}


@alerts_router.post("/test/discord")
async def test_discord():
    """Send a test alert to Discord."""
    ok = await send_discord_alert("Test alert — system is working!", title="🐍 Dr. Venom Trader")
    return {"sent": ok, "channel": "discord"}
