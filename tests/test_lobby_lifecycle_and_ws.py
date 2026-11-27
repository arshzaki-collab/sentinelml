"""Regression tests for lobby lifecycle, session retention, and WebSocket transport."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.engine.engine import GameEngine
from blindbillion.multiplayer.app import create_app, get_db, get_game_coordinator
from blindbillion.multiplayer.db_models import Base
from blindbillion.multiplayer.game_coordinator import GameCoordinator
from blindbillion.multiplayer.rate_limiter import global_rate_limiter


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    """Provide isolated in-memory SQLite session factory."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    """Provide FastAPI test client wired with test database and game coordinator."""
    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db

    if not Path(DEFAULT_DB_PATH).exists():
        pytest.skip(f"Live database {DEFAULT_DB_PATH} not found; run pipeline first.")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    engine = GameEngine(con=con)
    coord = GameCoordinator(engine=engine)
    app.dependency_overrides[get_game_coordinator] = lambda: coord

    global_rate_limiter.reset()

    with TestClient(app) as test_client:
        yield test_client


def test_room_creation_and_lobby_lifecycle(client: TestClient) -> None:
    """Cover scenarios 1-7:
    1. Creating a room.
    2. Creating a room without requesting game state (asserting 404 if state requested prematurely).
    3. Joining a room while in LOBBY.
    4. Refreshing a LOBBY room (asserting public room is returned).
    5. Confirming lobby actions do not clear session (session token remains valid).
    6. Starting a game when players ready.
    7. Fetching game state after start.
    """
    # 1. Host creates a room
    res_create = client.post("/api/rooms", json={"host_name": "HostAlpha"})
    assert res_create.status_code == 201
    create_data = res_create.json()
    room_code = create_data["room"]["room_code"]
    host_token = create_data["session_token"]
    host_id = create_data["player_id"]

    assert len(room_code) == 4
    assert create_data["room"]["status"] == "LOBBY"
    assert create_data["room"]["host_player_id"] == host_id
    assert len(create_data["room"]["players"]) == 1

    # 2. Premature game state request in LOBBY returns 404
    # Client must not request game state in LOBBY.
    res_state_lobby = client.get(
        f"/api/rooms/{room_code}/state",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_state_lobby.status_code == 404
    assert "not found" in res_state_lobby.json()["detail"].lower()

    # 3. Player 2 joins while in LOBBY
    res_join = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "PlayerBravo"})
    assert res_join.status_code == 200
    join_data = res_join.json()
    p2_token = join_data["session_token"]
    p2_id = join_data["player_id"]
    assert join_data["room"]["status"] == "LOBBY"
    assert len(join_data["room"]["players"]) == 2

    # 4. Refreshing a LOBBY room via GET /api/rooms/{room_code} returns public room view
    res_refresh = client.get(f"/api/rooms/{room_code}")
    assert res_refresh.status_code == 200
    refresh_data = res_refresh.json()
    assert refresh_data["room_code"] == room_code
    assert refresh_data["status"] == "LOBBY"
    assert len(refresh_data["players"]) == 2
    assert refresh_data["host_player_id"] == host_id

    # 5. Confirming lobby does not invalidate or clear session tokens
    # Both host and guest can use their session tokens to update readiness
    res_p2_ready = client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {p2_token}"},
    )
    assert res_p2_ready.status_code == 200
    players = res_p2_ready.json()["players"]
    assert any(p["player_id"] == p2_id and p["is_ready"] is True for p in players)

    res_host_ready = client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_host_ready.status_code == 200

    # 6. Starting the game
    res_start = client.post(
        f"/api/rooms/{room_code}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_start.status_code == 200
    start_data = res_start.json()
    assert start_data["room"]["status"] == "IN_GAME"
    assert start_data["room"]["current_year"] == 2016

    # 7. Fetching game state after start succeeds for both players
    res_host_state = client.get(
        f"/api/rooms/{room_code}/state",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_host_state.status_code == 200
    host_state = res_host_state.json()
    assert host_state["room"]["room_code"] == room_code
    assert host_state["my_state"]["current_year"] == 2016
    assert host_state["my_state"]["cash_balance"] == 1_000_000_000.0
    assert len(host_state["my_state"]["shortlists"]) > 0

    res_p2_state = client.get(
        f"/api/rooms/{room_code}/state",
        headers={"Authorization": f"Bearer {p2_token}"},
    )
    assert res_p2_state.status_code == 200
    p2_state = res_p2_state.json()
    assert p2_state["room"]["room_code"] == room_code
    assert p2_state["my_state"]["cash_balance"] == 1_000_000_000.0


def test_auth_and_membership_rejection(client: TestClient) -> None:
    """Cover scenarios 8 and 9:
    8. Invalid token returns 401.
    9. Invalid room membership returns 403.
    """
    # Create Room 1
    r1 = client.post("/api/rooms", json={"host_name": "Host1"}).json()
    room_1 = r1["room"]["room_code"]

    # Create Room 2
    r2 = client.post("/api/rooms", json={"host_name": "Host2"}).json()
    token_2 = r2["session_token"]

    # 8. Invalid token returns 401 Unauthorized
    res_bad_token = client.get(
        f"/api/rooms/{room_1}/state",
        headers={"Authorization": "Bearer non_existent_token_xyz"},
    )
    assert res_bad_token.status_code == 401
    bad_detail = res_bad_token.json()["detail"].lower()
    assert "invalid" in bad_detail or "missing" in bad_detail

    # 9. Token from Room 2 used on Room 1 returns 403 Forbidden (cross-room access blocked)
    res_cross_room = client.post(
        f"/api/rooms/{room_1}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {token_2}"},
    )
    assert res_cross_room.status_code == 403
    assert "not a member" in res_cross_room.json()["detail"].lower()


def test_websocket_upgrade_ping_pong_and_auth(client: TestClient) -> None:
    """Cover scenario 10:
    10. WebSocket connection succeeds with upgrade and ping/pong.
    Also confirms unauthenticated connection is rejected with policy violation (1008).
    """
    # Create room
    res = client.post("/api/rooms", json={"host_name": "SocketHost"})
    room_code = res.json()["room"]["room_code"]
    token = res.json()["session_token"]

    # Valid token upgrades and responds to ping
    with client.websocket_connect(f"/ws/rooms/{room_code}?token={token}") as ws:
        # Reconnect broadcast event received on connect
        welcome_raw = ws.receive_text()
        welcome = json.loads(welcome_raw)
        assert welcome["event"] == "PLAYER_RECONNECTED"

        # Ping / Pong check
        ws.send_text("ping")
        response = ws.receive_text()
        assert response == "pong"

    # Connection with invalid token closes immediately with 1008 policy violation
    with pytest.raises(WebSocketDisconnect) as exc_info, client.websocket_connect(
        f"/ws/rooms/{room_code}?token=invalid_token_abc"
    ):
        pass
    assert exc_info.value.code == 1008
