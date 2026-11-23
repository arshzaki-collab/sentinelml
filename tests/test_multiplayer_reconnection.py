"""Automated tests for player reconnection, refresh state recovery, host migration, and restart."""

from __future__ import annotations

import tempfile
import uuid
from collections.abc import Generator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.engine.engine import GameEngine
from blindbillion.multiplayer.app import create_app, get_db, get_game_coordinator
from blindbillion.multiplayer.db_models import Base, RoomModel
from blindbillion.multiplayer.game_coordinator import GameCoordinator
from blindbillion.multiplayer.rate_limiter import global_rate_limiter


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


def test_refresh_state_recovery_via_session_token(temp_db_path: Path) -> None:
    """Verify player can refresh their browser and immediately recover their full game state."""
    engine = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session_factory()

    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    coord = GameCoordinator(engine=GameEngine(con=con))
    app.dependency_overrides[get_game_coordinator] = lambda: coord
    global_rate_limiter.reset()

    with TestClient(app) as client:
        # 1. Host creates room and joins
        res_host = client.post("/api/rooms", json={"host_name": "Alice"})
        room_code = res_host.json()["room"]["room_code"]
        t1 = res_host.json()["session_token"]

        res_p2 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Bob"})
        t2 = res_p2.json()["session_token"]

        client.post(
            f"/api/rooms/{room_code}/ready",
            json={"is_ready": True},
            headers={"Authorization": f"Bearer {t2}"},
        )
        client.post(f"/api/rooms/{room_code}/start", headers={"Authorization": f"Bearer {t1}"})

        # Alice purchases Slot 1
        st_before = client.get(
            f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"}
        ).json()["my_state"]
        cand = st_before["shortlists"]["1"]["candidates"][0]["candidate_token"]
        client.post(
            f"/api/rooms/{room_code}/action",
            json={
                "action_type": "BUY",
                "candidate_token": cand,
                "idempotency_key": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {t1}"},
        )

        # 2. Simulate browser refresh by fetching state again using only session_token
        res_refresh = client.get(
            f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"}
        )
        assert res_refresh.status_code == 200
        refreshed_data = res_refresh.json()

        assert refreshed_data["room"]["room_code"] == room_code
        assert refreshed_data["room"]["status"] == "IN_GAME"
        assert refreshed_data["my_state"]["is_turn_submitted"] is True
        assert refreshed_data["my_state"]["cash_balance"] < 1_000_000_000.0


def test_host_migration_when_host_disconnects(temp_db_path: Path) -> None:
    """Verify host role automatically migrates to earliest connected player if host drops."""
    engine = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session_factory()
    global_rate_limiter.reset()

    with TestClient(app) as client:
        # Create 3-player room: Host, Player2, Player3
        r1 = client.post("/api/rooms", json={"host_name": "Host1"}).json()
        room_code = r1["room"]["room_code"]
        host_id = r1["player_id"]

        r2 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Player2"}).json()
        p2_id = r2["player_id"]

        r3 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Player3"}).json()

        # Connect WebSocket for Player2 and Player3, and Host
        with (
            client.websocket_connect(f"/ws/rooms/{room_code}?token={r2['session_token']}"),
            client.websocket_connect(f"/ws/rooms/{room_code}?token={r3['session_token']}"),
        ):
            with client.websocket_connect(f"/ws/rooms/{room_code}?token={r1['session_token']}"):
                room_view = client.get(f"/api/rooms/{room_code}").json()
                assert room_view["host_player_id"] == host_id

            # Host socket closed; WebSocket handler automatically executed host migration!
            with session_factory() as s:
                room = s.query(RoomModel).filter(RoomModel.room_code == room_code).first()
                assert room is not None
                assert room.host_player_id == p2_id  # Host migrated to earliest active player

                p2_player = next(p for p in room.players if p.player_id == p2_id)
                assert p2_player.is_host is True

                old_host = next(p for p in room.players if p.player_id == host_id)
                assert old_host.is_host is False


def test_server_restart_state_recovery(temp_db_path: Path) -> None:
    """Verify persistent room and player state survives complete server reboot."""
    engine_1 = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine_1)
    factory_1 = sessionmaker(bind=engine_1, expire_on_commit=False)

    app_1 = create_app()
    app_1.dependency_overrides[get_db] = lambda: factory_1()

    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    coord_1 = GameCoordinator(engine=GameEngine(con=con))
    app_1.dependency_overrides[get_game_coordinator] = lambda: coord_1
    global_rate_limiter.reset()

    # Session 1: Create room and progress game
    with TestClient(app_1) as client1:
        res = client1.post("/api/rooms", json={"host_name": "PreRestartHost"})
        room_code = res.json()["room"]["room_code"]
        token = res.json()["session_token"]

        res2 = client1.post(f"/api/rooms/{room_code}/join", json={"player_name": "P2"})
        t2 = res2.json()["session_token"]

        client1.post(
            f"/api/rooms/{room_code}/ready",
            json={"is_ready": True},
            headers={"Authorization": f"Bearer {t2}"},
        )
        client1.post(f"/api/rooms/{room_code}/start", headers={"Authorization": f"Bearer {token}"})

    # Dispose of server 1 and engine 1 (simulating crash / reboot)
    engine_1.dispose()

    # Session 2: Fresh engine instance pointing to the same database
    engine_2 = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})
    factory_2 = sessionmaker(bind=engine_2, expire_on_commit=False)

    app_2 = create_app()
    app_2.dependency_overrides[get_db] = lambda: factory_2()
    coord_2 = GameCoordinator(engine=GameEngine(con=con))
    app_2.dependency_overrides[get_game_coordinator] = lambda: coord_2

    with TestClient(app_2) as client2:
        res_recovered = client2.get(f"/api/rooms/{room_code}")
        assert res_recovered.status_code == 200
        data = res_recovered.json()
        assert data["room_code"] == room_code
        assert len(data["players"]) == 2
        assert data["players"][0]["display_name"] == "PreRestartHost"

        res_state = client2.get(
            f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {token}"}
        )
        assert res_state.status_code == 200
        assert res_state.json()["room"]["room_code"] == room_code
