"""
Dr. Venom Trader - FastAPI Application Entry Point
Configures lifespan events, middleware, and mounts all routers.
"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.redis_client import RedisManager
from app.api.router import api_router
from app.api.alerts import alerts_router
from app.api.settings import settings_router
from app.ws.routes import ws_router
from app.services.data_manager import DataManager

logger = structlog.get_logger()

# Global data manager instance
data_manager = DataManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # --- Startup ---
    logger.info("Starting Dr. Venom Trader backend", version="1.0.0")

    await init_db()
    logger.info("Database initialized")

    await RedisManager.connect()
    logger.info("Redis connected")

    await data_manager.start()
    logger.info("Data streams started")

    from app.signals.engine import signal_engine
    await signal_engine.start()
    logger.info("Signal engine started")

    from app.services.alerts.confluence import confluence_monitor
    await confluence_monitor.start()
    logger.info("Confluence monitor started")

    yield

    # --- Shutdown ---
    logger.info("Shutting down Dr. Venom Trader backend")
    from app.services.alerts.confluence import confluence_monitor
    await confluence_monitor.stop()
    from app.signals.engine import signal_engine
    await signal_engine.stop()
    await data_manager.stop()
    await RedisManager.disconnect()
    await close_db()
    logger.info("All connections closed")


app = FastAPI(
    title=settings.app_name,
    description="Professional real-time crypto trading signals dashboard",
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [f"https://{settings.app_name}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check for Docker."""
    redis = await RedisManager.get_client()
    redis_ok = await redis.ping()
    from app.ws.manager import ws_manager
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "1.0.0",
        "redis": "connected" if redis_ok else "disconnected",
        "ws_clients": ws_manager.client_count,
    }


# --- Mount all routers ---
app.include_router(api_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(ws_router)
