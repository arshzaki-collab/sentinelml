"""Automated tests for multiplayer room creation, joining, lobby validation, and rate limiting."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.engine.engine import GameEngine
from blindbillion.multiplayer.app import create_app, get_db, get_game_coordinator
from blindbillion.multiplayer.db_models import Base
from blindbillion.multiplayer.game_coordinator import GameCoordinator
from blindbillion.multiplayer.rate_limiter import global_rate_limiter


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    """Provide isolated in-memory SQLite session factory with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    """Provide FastAPI test client wired with isolated test database and live DuckDB engine."""
    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db

    # Live DuckDB for game coordinator
    if not Path(DEFAULT_DB_PATH).exists():
        pytest.skip(f"Live database {DEFAULT_DB_PATH} not found; run pipeline first.")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    engine = GameEngine(con=con)
    coord = GameCoordinator(engine=engine)
    app.dependency_overrides[get_game_coordinator] = lambda: coord

    global_rate_limiter.reset()

    with TestClient(app) as test_client:
        yield test_client


def test_create_room_and_join_two_players(client: TestClient) -> None:
    """Verify room creation and joining for a standard 2-player match."""
    # 1. Host creates room
    res1 = client.post("/api/rooms", json={"host_name": "Alice"})
    assert res1.status_code == 201
    data1 = res1.json()

    room_code = data1["room"]["room_code"]
    host_token = data1["session_token"]
    host_id = data1["player_id"]
    assert len(room_code) == 4
    assert data1["room"]["host_player_id"] == host_id
    assert len(data1["room"]["players"]) == 1
    assert data1["room"]["players"][0]["is_host"] is True

    # 2. Player 2 joins with case-insensitive code
    res2 = client.post(f"/api/rooms/{room_code.lower()}/join", json={"player_name": "Bob"})
    assert res2.status_code == 200
    data2 = res2.json()

    p2_token = data2["session_token"]
    assert p2_token != host_token
    assert len(data2["room"]["players"]) == 2
    assert data2["room"]["players"][1]["display_name"] == "Bob"
    assert data2["room"]["players"][1]["is_host"] is False


def test_four_player_room_and_fifth_player_rejection(client: TestClient) -> None:
    """Verify room supports up to 4 players and rejects a 5th player with 409 Conflict."""
    res_host = client.post("/api/rooms", json={"host_name": "Player1"})
    room_code = res_host.json()["room"]["room_code"]

    # Players 2, 3, 4 join successfully
    for i in range(2, 5):
        r = client.post(f"/api/rooms/{room_code}/join", json={"player_name": f"Player{i}"})
        assert r.status_code == 200
        assert len(r.json()["room"]["players"]) == i

    # 5th player attempts to join
    res_p5 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Player5"})
    assert res_p5.status_code == 409
    assert "full" in res_p5.json()["detail"].lower()


def test_invalid_room_code_rejection(client: TestClient) -> None:
    """Verify non-existent room code returns 404 Not Found."""
    res = client.get("/api/rooms/ZZZZ")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_unauthorized_room_access_rejected(client: TestClient) -> None:
    """Verify requests with missing or invalid session tokens are rejected with 401."""
    res = client.post("/api/rooms", json={"host_name": "Host"})
    room_code = res.json()["room"]["room_code"]

    # Missing auth header
    res_unauth = client.post(f"/api/rooms/{room_code}/ready", json={"is_ready": True})
    assert res_unauth.status_code == 401

    # Fake auth token
    res_fake = client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": "Bearer fake_token_xyz"},
    )
    assert res_fake.status_code == 401


def test_host_only_start_game_validation(client: TestClient) -> None:
    """Verify only the room host can start the game and requires readiness."""
    res_host = client.post("/api/rooms", json={"host_name": "Host"})
    room_code = res_host.json()["room"]["room_code"]
    host_token = res_host.json()["session_token"]

    res_p2 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Guest"})
    p2_token = res_p2.json()["session_token"]

    # Non-host attempts to start
    res_guest_start = client.post(
        f"/api/rooms/{room_code}/start",
        headers={"Authorization": f"Bearer {p2_token}"},
    )
    assert res_guest_start.status_code == 403
    assert "only the host" in res_guest_start.json()["detail"].lower()

    # Host attempts to start when guest is not ready
    res_premature_start = client.post(
        f"/api/rooms/{room_code}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_premature_start.status_code == 400
    assert "not ready" in res_premature_start.json()["detail"].lower()

    # Guest sets ready
    res_ready = client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {p2_token}"},
    )
    assert res_ready.status_code == 200

    # Host starts successfully
    res_start = client.post(
        f"/api/rooms/{room_code}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_start.status_code == 200
    start_data = res_start.json()
    assert start_data["room"]["status"] == "IN_GAME"
    assert start_data["room"]["current_year"] == 2016
    assert start_data["room"]["current_phase"] == "BUYING_SEASON"


def test_start_game_rejects_single_player_room(client: TestClient) -> None:
    """Verify game cannot start with fewer than 2 players."""
    res_host = client.post("/api/rooms", json={"host_name": "SoloHost"})
    room_code = res_host.json()["room"]["room_code"]
    host_token = res_host.json()["session_token"]

    res_start = client.post(
        f"/api/rooms/{room_code}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_start.status_code == 400
    assert "at least 2 players" in res_start.json()["detail"].lower()


def test_late_join_rejected_after_game_started(client: TestClient) -> None:
    """Verify new players cannot join a room once the game has started."""
    res_host = client.post("/api/rooms", json={"host_name": "Host"})
    room_code = res_host.json()["room"]["room_code"]
    host_token = res_host.json()["session_token"]

    res_p2 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Guest"})
    p2_token = res_p2.json()["session_token"]

    client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {p2_token}"},
    )
    client.post(
        f"/api/rooms/{room_code}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )

    # 3rd player attempts to join active game
    res_late = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "LatePlayer"})
    assert res_late.status_code == 403
    assert "in state 'IN_GAME'" in res_late.json()["detail"]


def test_rate_limiting_on_room_creation(client: TestClient) -> None:
    """Verify rate limiter blocks rapid room creation exceeding 10 requests per minute."""
    for _ in range(10):
        r = client.post("/api/rooms", json={"host_name": "SpamHost"})
        assert r.status_code == 201

    # 11th request triggers rate limit
    res_blocked = client.post("/api/rooms", json={"host_name": "SpamHost"})
    assert res_blocked.status_code == 429
    assert "rate limit exceeded" in res_blocked.json()["detail"].lower()


def test_health_check_endpoints(client: TestClient) -> None:
    """Verify /health and /api/health report correct statuses."""
    for endpoint in ("/health", "/api/health"):
        res = client.get(endpoint)
        assert res.status_code == 200
        data = res.json()
        assert data["version"] == "2.0.0"
        assert data["database"] == "connected"
        assert data["status"] in ("healthy", "degraded")


def test_health_check_degraded_when_analytical_db_missing(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify /health reports degraded when DuckDB path is invalid."""
    monkeypatch.setenv("ANALYTICAL_DB_PATH", str(tmp_path / "nonexistent.duckdb"))
    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as tc:
        res = tc.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["analytical_cache"] == "missing_database"
        assert "analytical_cache_help" in data

