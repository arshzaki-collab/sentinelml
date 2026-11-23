"""SQLAlchemy database models for multiplayer persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RoomModel(Base):
    """Persistent storage for a multiplayer room session."""

    __tablename__ = "rooms"

    room_code: Mapped[str] = mapped_column(String(4), primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="LOBBY")
    host_player_id: Mapped[str] = mapped_column(String(64), nullable=False)
    room_seed: Mapped[str] = mapped_column(String(64), nullable=False)
    current_year: Mapped[int] = mapped_column(Integer, nullable=False, default=2016)
    current_phase: Mapped[str] = mapped_column(String(32), nullable=False, default="BUYING_SEASON")
    current_slot_index: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    timeline_step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    players: Mapped[list[RoomPlayerModel]] = relationship(
        "RoomPlayerModel", back_populates="room", cascade="all, delete-orphan", lazy="joined"
    )
    player_states: Mapped[list[PlayerGameStateModel]] = relationship(
        "PlayerGameStateModel", back_populates="room", cascade="all, delete-orphan", lazy="select"
    )


class RoomPlayerModel(Base):
    """Persistent record of an authorized player participating in a room."""

    __tablename__ = "room_players"

    player_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    room_code: Mapped[str] = mapped_column(
        String(4), ForeignKey("rooms.room_code", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    session_token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    is_host: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_turn_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    room: Mapped[RoomModel] = relationship("RoomModel", back_populates="players")

    __table_args__ = (
        Index("idx_room_players_room_code", "room_code"),
        Index("idx_room_players_session_token", "session_token"),
    )


class PlayerGameStateModel(Base):
    """Serialized authoritative player game state snapshot."""

    __tablename__ = "player_game_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_code: Mapped[str] = mapped_column(
        String(4), ForeignKey("rooms.room_code", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[str] = mapped_column(String(64), nullable=False)
    serialized_state: Mapped[str] = mapped_column(Text, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    room: Mapped[RoomModel] = relationship("RoomModel", back_populates="player_states")

    __table_args__ = (
        UniqueConstraint("room_code", "player_id", name="uq_room_player_state"),
        Index("idx_player_game_states_room_player", "room_code", "player_id"),
    )


class ActionIdempotencyModel(Base):
    """Storage for idempotency keys to safely process concurrent/retry actions."""

    __tablename__ = "action_idempotency_records"

    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    room_code: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    response_payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
