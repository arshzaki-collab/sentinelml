"""Multiplayer backend package for Blind Billion 2.0."""

from __future__ import annotations

from blindbillion.multiplayer.app import app, create_app
from blindbillion.multiplayer.game_coordinator import GameCoordinator
from blindbillion.multiplayer.models import (
    ActionResponse,
    CreateRoomRequest,
    CreateRoomResponse,
    JoinRoomRequest,
    JoinRoomResponse,
    MultiplayerGameActionRequest,
    PlayerPublicView,
    RealtimeEventType,
    RoomPublicView,
    RoomStatus,
)
from blindbillion.multiplayer.room_manager import RoomManager

__all__ = [
    "ActionResponse",
    "CreateRoomRequest",
    "CreateRoomResponse",
    "GameCoordinator",
    "JoinRoomRequest",
    "JoinRoomResponse",
    "MultiplayerGameActionRequest",
    "PlayerPublicView",
    "RealtimeEventType",
    "RoomManager",
    "RoomPublicView",
    "RoomStatus",
    "app",
    "create_app",
]
