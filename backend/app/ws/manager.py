"""
Dr. Venom Trader - WebSocket Broadcast Manager
Manages connected frontend clients and broadcasts signal updates.
"""

import asyncio
import json
import time
import structlog
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


class ConnectionManager:
    """
    Manages WebSocket connections from frontend clients.
    Supports per-symbol subscriptions and broadcast.
    """

    def __init__(self):
        # symbol -> set of connected WebSockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        # All connections (for global broadcasts)
        self._all: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, symbol: str = "ALL") -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self._all.add(websocket)
        if symbol not in self._connections:
            self._connections[symbol] = set()
        self._connections[symbol].add(websocket)
        logger.info("WS client connected", symbol=symbol, total=len(self._all))

    def disconnect(self, websocket: WebSocket, symbol: str = "ALL") -> None:
        """Remove a disconnected client."""
        self._all.discard(websocket)
        if symbol in self._connections:
            self._connections[symbol].discard(websocket)
        logger.info("WS client disconnected", total=len(self._all))

    async def broadcast_signal(self, symbol: str, data: dict) -> None:
        """Broadcast signal update to all clients subscribed to a symbol."""
        message = json.dumps({
            "type": "signal_update",
            "symbol": symbol,
            "data": data,
            "timestamp": time.time(),
        })

        # Send to symbol-specific subscribers
        targets = self._connections.get(symbol, set()) | self._connections.get("ALL", set())
        disconnected = []

        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        # Cleanup disconnected clients
        for ws in disconnected:
            self.disconnect(ws, symbol)

    async def broadcast_price(self, symbol: str, price_data: dict) -> None:
        """Broadcast price update to all subscribers."""
        message = json.dumps({
            "type": "price_update",
            "symbol": symbol,
            "data": price_data,
            "timestamp": time.time(),
        })

        disconnected = []
        targets = self._connections.get(symbol, set()) | self._connections.get("ALL", set())

        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws, symbol)

    async def broadcast_alert(self, alert_data: dict) -> None:
        """Broadcast alert to all connected clients."""
        message = json.dumps({
            "type": "alert",
            "data": alert_data,
            "timestamp": time.time(),
        })

        disconnected = []
        for ws in self._all.copy():
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    @property
    def client_count(self) -> int:
        return len(self._all)


# Global singleton instance
ws_manager = ConnectionManager()
