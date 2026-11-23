"""Room lifecycle, collision-safe code generation, membership, and host governance."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Final

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from blindbillion.multiplayer.db_models import RoomModel, RoomPlayerModel
from blindbillion.multiplayer.models import (
    CreateRoomResponse,
    JoinRoomResponse,
    PlayerPublicView,
    RoomPublicView,
    RoomStatus,
)
from blindbillion.multiplayer.session_manager import generate_player_id, generate_session_token

# 32 unambiguous characters (excludes 0, O, 1, I to prevent user entry confusion)
ROOM_CODE_ALPHABET: Final[str] = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
ROOM_CODE_LENGTH: Final[int] = 4
MAX_ROOM_PLAYERS: Final[int] = 4
MIN_ROOM_PLAYERS: Final[int] = 2
ROOM_EXPIRATION_HOURS: Final[int] = 24


def generate_room_code(session: Session, max_attempts: int = 10) -> str:
    """Generate unique 4-character uppercase alphanumeric room code with collision safety."""
    for _ in range(max_attempts):
        code = "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))
        exists = session.query(RoomModel).filter(RoomModel.room_code == code).first()
        if not exists:
            return code
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Unable to generate a unique room code. Please try again.",
    )


def _ensure_utc(dt: datetime | None) -> datetime:
    """Ensure datetime has UTC timezone to support SQLite without timezone drivers."""
    if dt is None:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def serialize_room_view(room: RoomModel) -> RoomPublicView:
    """Convert persistent RoomModel into a clean, client-safe RoomPublicView schema."""
    sorted_players = sorted(room.players, key=lambda p: _ensure_utc(p.joined_at))
    player_views = tuple(
        PlayerPublicView(
            player_id=p.player_id,
            display_name=p.display_name,
            is_host=p.is_host,
            is_ready=p.is_ready,
            is_connected=p.is_connected,
            is_turn_submitted=p.is_turn_submitted,
            joined_at=_ensure_utc(p.joined_at),
        )
        for p in sorted_players
    )

    return RoomPublicView(
        room_code=room.room_code,
        status=RoomStatus(room.status),
        host_player_id=room.host_player_id,
        current_year=room.current_year,
        current_phase=room.current_phase,
        current_slot_index=room.current_slot_index,
        timeline_step_index=room.timeline_step_index,
        players=player_views,
        created_at=_ensure_utc(room.created_at),
        is_game_started=room.status in (RoomStatus.IN_GAME, RoomStatus.COMPLETED),
        is_completed=room.status == RoomStatus.COMPLETED,
    )


class RoomManager:
    """Orchestrates room creation, player joining, lobby readiness, and host migration."""

    @staticmethod
    def create_room(
        session: Session,
        host_name: str,
        custom_seed: str | int | None = None,
    ) -> CreateRoomResponse:
        """Create a new room with caller assigned as host."""
        clean_name = host_name.strip()
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Host name cannot be empty."
            )

        room_code = generate_room_code(session=session)
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=ROOM_EXPIRATION_HOURS)
        seed = str(custom_seed) if custom_seed is not None else secrets.token_hex(8)

        host_id = generate_player_id()
        session_token = generate_session_token()

        room = RoomModel(
            room_code=room_code,
            status=RoomStatus.LOBBY.value,
            host_player_id=host_id,
            room_seed=seed,
            current_year=2016,
            current_phase="BUYING_SEASON",
            current_slot_index=1,
            timeline_step_index=0,
            state_version=1,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
        )
        host_player = RoomPlayerModel(
            player_id=host_id,
            room_code=room_code,
            display_name=clean_name,
            session_token=session_token,
            is_host=True,
            is_ready=True,  # Host is ready by default
            is_connected=True,
            is_turn_submitted=False,
            joined_at=now,
            last_seen_at=now,
        )

        session.add(room)
        session.add(host_player)
        session.commit()
        session.refresh(room)

        return CreateRoomResponse(
            room=serialize_room_view(room),
            session_token=session_token,
            player_id=host_id,
        )

    @staticmethod
    def join_room(session: Session, room_code: str, player_name: str) -> JoinRoomResponse:
        """Join an existing room as a standard player."""
        clean_code = room_code.strip().upper()
        clean_name = player_name.strip()
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Player name cannot be empty."
            )

        room = session.query(RoomModel).filter(RoomModel.room_code == clean_code).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Room '{clean_code}' not found."
            )

        if room.status != RoomStatus.LOBBY.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Cannot join room in state '{room.status}'. Only reconnecting players allowed."
                ),
            )

        if len(room.players) >= MAX_ROOM_PLAYERS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room '{clean_code}' is full (maximum {MAX_ROOM_PLAYERS} players).",
            )

        # Check duplicate name within room
        existing_names = {p.display_name.lower() for p in room.players}
        if clean_name.lower() in existing_names:
            clean_name = f"{clean_name} ({len(room.players) + 1})"

        player_id = generate_player_id()
        session_token = generate_session_token()
        now = datetime.now(UTC)

        new_player = RoomPlayerModel(
            player_id=player_id,
            room_code=clean_code,
            display_name=clean_name,
            session_token=session_token,
            is_host=False,
            is_ready=False,
            is_connected=True,
            is_turn_submitted=False,
            joined_at=now,
            last_seen_at=now,
        )

        session.add(new_player)
        room.updated_at = now
        session.commit()
        session.refresh(room)

        return JoinRoomResponse(
            room=serialize_room_view(room),
            session_token=session_token,
            player_id=player_id,
        )

    @staticmethod
    def set_player_ready(
        session: Session, player: RoomPlayerModel, is_ready: bool
    ) -> RoomPublicView:
        """Toggle player's ready state in lobby."""
        room = session.query(RoomModel).filter(RoomModel.room_code == player.room_code).first()
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

        if room.status != RoomStatus.LOBBY.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ready status can only be toggled in LOBBY phase.",
            )

        player.is_ready = is_ready
        player.last_seen_at = datetime.now(UTC)
        room.updated_at = datetime.now(UTC)
        session.commit()
        session.refresh(room)
        return serialize_room_view(room)

    @staticmethod
    def migrate_host_if_needed(session: Session, room: RoomModel) -> str | None:
        """Reassign host to earliest active player if current host is disconnected."""
        current_host = next((p for p in room.players if p.player_id == room.host_player_id), None)
        if current_host and current_host.is_connected:
            return None  # Host is active and connected

        connected_players = sorted(
            [p for p in room.players if p.is_connected and p.player_id != room.host_player_id],
            key=lambda p: _ensure_utc(p.joined_at),
        )

        if not connected_players:
            return None  # No connected players to migrate to

        new_host = connected_players[0]
        if current_host:
            current_host.is_host = False
        new_host.is_host = True
        room.host_player_id = new_host.player_id
        room.updated_at = datetime.now(UTC)
        session.commit()
        return new_host.player_id
