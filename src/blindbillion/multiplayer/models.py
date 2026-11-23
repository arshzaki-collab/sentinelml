"""Domain models, schemas, and event definitions for multiplayer game sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RoomStatus(StrEnum):
    """Lifecycle status of a multiplayer room."""

    LOBBY = "LOBBY"
    IN_GAME = "IN_GAME"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class RealtimeEventType(StrEnum):
    """Event types broadcast over WebSocket and Realtime channels."""

    ROOM_UPDATED = "ROOM_UPDATED"
    PLAYER_JOINED = "PLAYER_JOINED"
    PLAYER_LEFT = "PLAYER_LEFT"
    PLAYER_DISCONNECTED = "PLAYER_DISCONNECTED"
    PLAYER_RECONNECTED = "PLAYER_RECONNECTED"
    PLAYER_READY = "PLAYER_READY"
    HOST_MIGRATED = "HOST_MIGRATED"
    GAME_STARTED = "GAME_STARTED"
    ACTION_COMMITTED = "ACTION_COMMITTED"
    ROUND_ADVANCED = "ROUND_ADVANCED"
    GAME_FINISHED = "GAME_FINISHED"
    HEARTBEAT = "HEARTBEAT"
    ERROR = "ERROR"


# Request Payloads
class CreateRoomRequest(BaseModel):
    """Payload to create a new multiplayer room."""

    model_config = ConfigDict(frozen=True)

    host_name: str = Field(..., min_length=1, max_length=32, description="Display name of host")
    room_seed: str | int | None = Field(default=None, description="Optional deterministic seed")


class JoinRoomRequest(BaseModel):
    """Payload to join an existing multiplayer room."""

    model_config = ConfigDict(frozen=True)

    player_name: str = Field(..., min_length=1, max_length=32, description="Display name of player")


class SetReadyRequest(BaseModel):
    """Payload to toggle player ready status in lobby."""

    model_config = ConfigDict(frozen=True)

    is_ready: bool = Field(..., description="Desired ready status")


class MultiplayerGameActionRequest(BaseModel):
    """Payload to perform an action during buying season or transfer window."""

    model_config = ConfigDict(frozen=True)

    action_type: Literal["BUY", "SELL", "REPLACE", "PASS"] = Field(
        ..., description="Action to perform"
    )
    slot_index: int | None = Field(default=None, ge=1, le=7, description="Target squad slot")
    candidate_token: str | None = Field(default=None, description="Candidate token to buy/replace")
    idempotency_key: str = Field(
        ..., min_length=8, max_length=128, description="Unique client idempotency token"
    )


# Response & View Payloads
class PlayerPublicView(BaseModel):
    """Sanitized public profile of a player in a room."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    display_name: str
    is_host: bool
    is_ready: bool
    is_connected: bool
    is_turn_submitted: bool = False
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RoomPublicView(BaseModel):
    """Sanitized public summary of a multiplayer room."""

    model_config = ConfigDict(frozen=True)

    room_code: str
    status: RoomStatus
    host_player_id: str
    current_year: int
    current_phase: str
    current_slot_index: int | None
    timeline_step_index: int
    players: tuple[PlayerPublicView, ...]
    created_at: datetime
    is_game_started: bool
    is_completed: bool


class CreateRoomResponse(BaseModel):
    """Response returned upon successfully creating a room."""

    model_config = ConfigDict(frozen=True)

    room: RoomPublicView
    session_token: str
    player_id: str


class JoinRoomResponse(BaseModel):
    """Response returned upon successfully joining a room."""

    model_config = ConfigDict(frozen=True)

    room: RoomPublicView
    session_token: str
    player_id: str


class PlayerGameStateView(BaseModel):
    """Temporally-walled personal game state returned to the player."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    cash_balance: float
    current_year: int
    current_phase: str
    current_slot_index: int | None
    slots: tuple[dict[str, Any], ...]
    shortlists: dict[int, dict[str, Any]]
    transaction_history: tuple[dict[str, Any], ...]
    is_turn_submitted: bool
    is_completed: bool
    final_net_worth: float | None = None
    final_squad_valuation: float | None = None
    settlement_records: tuple[dict[str, Any], ...] | None = None


class LeaderboardEntry(BaseModel):
    """Individual player result in final 2026 leaderboard ranking."""

    model_config = ConfigDict(frozen=True)

    rank: int
    player_id: str
    display_name: str
    final_net_worth: float
    remaining_cash: float
    squad_valuation: float
    squad: tuple[dict[str, Any], ...]


class RoomGameStateResponse(BaseModel):
    """Composite state response returned on game screen loads or reloads."""

    model_config = ConfigDict(frozen=True)

    room: RoomPublicView
    my_state: PlayerGameStateView
    leaderboard: tuple[LeaderboardEntry, ...] | None = None


class ActionResponse(BaseModel):
    """Result of submitting a game action."""

    model_config = ConfigDict(frozen=True)

    success: bool
    message: str
    action_type: str
    new_balance: float
    is_barrier_cleared: bool = False
    room: RoomPublicView
    my_state: PlayerGameStateView


class WebSocketEvent(BaseModel):
    """Structured message broadcast to connected clients over WebSocket."""

    model_config = ConfigDict(frozen=True)

    event: RealtimeEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    room_code: str
    payload: dict[str, Any] = Field(default_factory=dict)
