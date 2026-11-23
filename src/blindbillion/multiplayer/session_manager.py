"""Cryptographic session and identity security for guest and authenticated players."""

from __future__ import annotations

import secrets
from typing import Final

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from blindbillion.multiplayer.db_models import RoomPlayerModel

SESSION_TOKEN_BYTES: Final[int] = 32
PLAYER_ID_BYTES: Final[int] = 8


def generate_session_token() -> str:
    """Generate cryptographically secure 256-bit URL-safe session token."""
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def generate_player_id() -> str:
    """Generate unique player identifier."""
    return f"usr_{secrets.token_hex(PLAYER_ID_BYTES)}"


def authenticate_player(
    session: Session,
    session_token: str,
    room_code: str | None = None,
) -> RoomPlayerModel:
    """Authenticate player by session token and optionally verify room membership."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is required.",
        )

    player = (
        session.query(RoomPlayerModel)
        .filter(RoomPlayerModel.session_token == session_token)
        .first()
    )
    if not player:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )

    if room_code and player.room_code.upper() != room_code.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Player is not a member of room {room_code.upper()}.",
        )

    return player


def get_authenticated_player(
    authorization: str | None = Header(default=None),
    x_session_token: str | None = Header(default=None),
) -> str:
    """Extract session token from Authorization: Bearer or X-Session-Token header."""
    if x_session_token:
        return x_session_token.strip()

    if authorization:
        parts = authorization.strip().split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return authorization.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing auth credentials (provide Authorization: Bearer or X-Session-Token).",
    )
