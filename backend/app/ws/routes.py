"""
Dr. Venom Trader - WebSocket Routes
FastAPI WebSocket endpoint for real-time frontend communication.
"""

import json
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.manager import ws_manager
from app.services.candle_cache import CandleCache

logger = structlog.get_logger()

ws_router = APIRouter()


@ws_router.websocket("/ws/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time data streaming.
    Clients connect with a symbol (e.g., BTCUSDT) or ALL for all symbols.
    
    Incoming messages:
      {"action": "subscribe", "symbol": "BTCUSDT"}
      {"action": "get_signals"}
      {"action": "ping"}
    
    Outgoing messages:
      {"type": "signal_update", ...}
      {"type": "price_update", ...}
      {"type": "alert", ...}
      {"type": "snapshot", ...}
    """
    await ws_manager.connect(websocket, symbol.upper())

    try:
        # Send initial snapshot
        signals = await CandleCache.get_all_signals(symbol.upper())
        price = await CandleCache.get_price(symbol.upper())
        await websocket.send_text(json.dumps({
            "type": "snapshot",
            "symbol": symbol.upper(),
            "signals": signals,
            "price": price,
        }))

        # Listen for client messages
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                action = msg.get("action", "")

                if action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

                elif action == "get_signals":
                    target = msg.get("symbol", symbol).upper()
                    signals = await CandleCache.get_all_signals(target)
                    await websocket.send_text(json.dumps({
                        "type": "snapshot",
                        "symbol": target,
                        "signals": signals,
                    }))

                elif action == "subscribe":
                    new_symbol = msg.get("symbol", "").upper()
                    if new_symbol:
                        ws_manager.disconnect(websocket, symbol.upper())
                        await ws_manager.connect(websocket, new_symbol)

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, symbol.upper())
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        ws_manager.disconnect(websocket, symbol.upper())
