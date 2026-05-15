"""
Dr. Venom Trader - API Router
Full REST endpoints for signals, prices, and system status.
"""

from fastapi import APIRouter
from app.services.candle_cache import CandleCache
from app.signals.engine import signal_engine
from app.config import settings

api_router = APIRouter()


@api_router.get("/status", tags=["System"])
async def api_status():
    """API status with active symbols and signal types."""
    return {
        "status": "operational",
        "signals": ["ALFA", "BETA", "DELTA", "GAMMA"],
        "symbols": settings.default_symbols,
    }


@api_router.get("/signals/{symbol}", tags=["Signals"])
async def get_signals(symbol: str):
    """Get all cached signal states for a symbol."""
    sym = symbol.upper()
    signals = await CandleCache.get_all_signals(sym)
    price = await CandleCache.get_price(sym)
    return {"symbol": sym, "price": price, "signals": signals}


@api_router.get("/signals/{symbol}/compute", tags=["Signals"])
async def compute_signals(symbol: str):
    """Force re-computation of all signals for a symbol."""
    sym = symbol.upper()
    results = await signal_engine.compute_now(sym)
    return {"symbol": sym, "signals": results}


@api_router.get("/signals/{symbol}/{signal_type}", tags=["Signals"])
async def get_signal_type(symbol: str, signal_type: str):
    """Get a specific signal type for a symbol across all timeframes."""
    sym = symbol.upper()
    sig = signal_type.upper()
    signals = await CandleCache.get_all_signals(sym)
    return {"symbol": sym, "signal_type": sig, "timeframes": signals.get(sig, {})}


@api_router.get("/price/{symbol}", tags=["Market Data"])
async def get_price(symbol: str):
    """Get current price for a symbol."""
    price = await CandleCache.get_price(symbol.upper())
    return {"symbol": symbol.upper(), "price": price}


@api_router.get("/liquidations/{symbol}", tags=["Market Data"])
async def get_liquidations(symbol: str, timeframe: str = "1H"):
    """Get aggregated liquidation data."""
    liq = await CandleCache.get_liquidation_agg(symbol.upper(), timeframe)
    return {"symbol": symbol.upper(), "timeframe": timeframe, "data": liq}


@api_router.get("/candles/{symbol}/{timeframe}", tags=["Market Data"])
async def get_candles(symbol: str, timeframe: str, limit: int = 100):
    """Get cached candles for a symbol/timeframe."""
    candles = await CandleCache.get_candles(symbol.upper(), timeframe, count=min(limit, 300))
    return {"symbol": symbol.upper(), "timeframe": timeframe, "count": len(candles), "candles": candles}
