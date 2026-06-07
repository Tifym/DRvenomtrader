"""
Dr. Venom Trader - Settings API Router
Endpoints for reading/updating configuration at runtime.
"""

import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, Any, List

from app.database import get_db
from app.models.settings import SignalSetting
from app.redis_client import RedisManager

settings_router = APIRouter(prefix="/settings", tags=["Settings"])

class SignalSettingUpdate(BaseModel):
    signal_type: str
    timeframe: str
    parameters: Dict[str, Any]
    is_active: bool = True

@settings_router.get("/")
async def get_all_settings(db: AsyncSession = Depends(get_db)):
    """Get all settings from DB."""
    result = await db.execute(select(SignalSetting))
    settings_list = result.scalars().all()
    return {
        "settings": [
            {
                "signal_type": s.signal_type,
                "timeframe": s.timeframe,
                "parameters": s.parameters,
                "is_active": s.is_active,
            }
            for s in settings_list
        ]
    }

@settings_router.post("/")
async def update_settings(body: List[SignalSettingUpdate], db: AsyncSession = Depends(get_db)):
    """Update specific signal settings and trigger hot reload."""
    updated = []
    for item in body:
        result = await db.execute(
            select(SignalSetting).where(
                SignalSetting.signal_type == item.signal_type,
                SignalSetting.timeframe == item.timeframe
            )
        )
        setting = result.scalars().first()
        if not setting:
            setting = SignalSetting(
                signal_type=item.signal_type,
                timeframe=item.timeframe
            )
            db.add(setting)
        
        setting.parameters = item.parameters
        setting.is_active = item.is_active
        updated.append(item.signal_type)
    
    await db.commit()
    
    # Trigger hot reload via Redis Pub/Sub
    redis = await RedisManager.get_client()
    await redis.publish("settings:reload", json.dumps({"signals_updated": list(set(updated))}))
    
    return {"status": "updated"}
