"""Realtime multiplayer synchronization tests with multiple independent WebSocket clients."""

from __future__ import annotations

import json
import uuid
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


def test_realtime_websocket_synchronization_e2e(client: TestClient) -> None:
    """Verify bidirectional realtime synchronization across two independent WebSocket clients."""
    # 1. Host creates room
    res1 = client.post("/api/rooms", json={"host_name": "HostPlayer"})
    room_code = res1.json()["room"]["room_code"]
    t1 = res1.json()["session_token"]

    # 2. Host opens WebSocket connection
    with client.websocket_connect(f"/ws/rooms/{room_code}?token={t1}") as ws_host:
        # Initial connection event broadcast
        init_msg = json.loads(ws_host.receive_text())
        assert init_msg["event"] == "PLAYER_RECONNECTED"

        # Heartbeat ping/pong check
        ws_host.send_text("ping")
        pong = ws_host.receive_text()
        assert pong == "pong"

        # 3. Guest joins via REST
        res2 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "GuestPlayer"})
        t2 = res2.json()["session_token"]

        # Host receives PLAYER_JOINED event over WebSocket
        event_raw = ws_host.receive_text()
        event_joined = json.loads(event_raw)
        assert event_joined["event"] == "PLAYER_JOINED"
        assert event_joined["room_code"] == room_code

        # 4. Guest connects their own WebSocket
        with client.websocket_connect(f"/ws/rooms/{room_code}?token={t2}") as ws_guest:
            # Both players receive the connection broadcast for guest
            _ = ws_host.receive_text()
            _ = ws_guest.receive_text()

            # Guest toggles ready via REST
            client.post(
                f"/api/rooms/{room_code}/ready",
                json={"is_ready": True},
                headers={"Authorization": f"Bearer {t2}"},
            )

            # Both WebSockets receive PLAYER_READY
            msg_ready_host = json.loads(ws_host.receive_text())
            msg_ready_guest = json.loads(ws_guest.receive_text())
            assert msg_ready_host["event"] == "PLAYER_READY"
            assert msg_ready_guest["event"] == "PLAYER_READY"

            # 5. Host starts game
            client.post(
                f"/api/rooms/{room_code}/start",
                headers={"Authorization": f"Bearer {t1}"},
            )

            # Both WebSockets receive GAME_STARTED
            msg_start_host = json.loads(ws_host.receive_text())
            msg_start_guest = json.loads(ws_guest.receive_text())
            assert msg_start_host["event"] == "GAME_STARTED"
            assert msg_start_guest["event"] == "GAME_STARTED"

            # 6. Host makes a purchase
            state1 = client.get(
                f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"}
            ).json()["my_state"]
            cand_token = state1["shortlists"]["1"]["candidates"][0]["candidate_token"]

            client.post(
                f"/api/rooms/{room_code}/action",
                json={
                    "action_type": "BUY",
                    "candidate_token": cand_token,
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"Authorization": f"Bearer {t1}"},
            )

            # Both receive ACTION_COMMITTED
            msg_act_host = json.loads(ws_host.receive_text())
            msg_act_guest = json.loads(ws_guest.receive_text())
            assert msg_act_host["event"] == "ACTION_COMMITTED"
            assert msg_act_guest["event"] == "ACTION_COMMITTED"
            assert msg_act_host["payload"]["is_barrier_cleared"] is False
