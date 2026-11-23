"""WebSocket connection registry, heartbeat tracking, and room event broadcasting."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from blindbillion.multiplayer.models import RealtimeEventType, WebSocketEvent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSockets and coordinates realtime broadcasts across rooms."""

    def __init__(self) -> None:
        # room_code -> dict[player_id, WebSocket]
        self._rooms: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def connect(self, room_code: str, player_id: str, websocket: WebSocket) -> None:
        """Register newly connected WebSocket."""
        await websocket.accept()
        code = room_code.upper()
        async with self._lock:
            self._rooms[code][player_id] = websocket
        logger.info("Player %s connected to room %s", player_id, code)

    async def disconnect(self, room_code: str, player_id: str) -> None:
        """Remove WebSocket connection on client departure or network break."""
        code = room_code.upper()
        async with self._lock:
            if code in self._rooms and player_id in self._rooms[code]:
                del self._rooms[code][player_id]
                if not self._rooms[code]:
                    del self._rooms[code]
        logger.info("Player %s disconnected from room %s", player_id, code)

    async def broadcast_to_room(
        self,
        room_code: str,
        event: RealtimeEventType,
        payload: dict[str, Any],
    ) -> None:
        """Broadcast event to every connected client in the specified room."""
        code = room_code.upper()
        async with self._lock:
            connections = list(self._rooms.get(code, {}).items())

        if not connections:
            return

        msg = WebSocketEvent(event=event, room_code=code, payload=payload)
        json_data = msg.model_dump_json()

        dead_connections: list[str] = []
        for pid, ws in connections:
            try:
                await ws.send_text(json_data)
            except Exception as err:
                logger.warning("Failed to send to player %s in room %s: %s", pid, code, err)
                dead_connections.append(pid)

        if dead_connections:
            async with self._lock:
                for pid in dead_connections:
                    if code in self._rooms and pid in self._rooms[code]:
                        del self._rooms[code][pid]

    async def send_personal_message(
        self,
        room_code: str,
        player_id: str,
        event: RealtimeEventType,
        payload: dict[str, Any],
    ) -> None:
        """Send a direct event message to an individual player."""
        code = room_code.upper()
        async with self._lock:
            ws = self._rooms.get(code, {}).get(player_id)

        if ws:
            msg = WebSocketEvent(event=event, room_code=code, payload=payload)
            try:
                await ws.send_text(msg.model_dump_json())
            except Exception as err:
                logger.warning("Failed to send direct message to %s: %s", player_id, err)


# Global singleton connection manager
connection_manager = ConnectionManager()
