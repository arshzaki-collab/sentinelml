"""Comprehensive tests for AI bot opponents in multiplayer and single-player rooms."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from blindbillion.multiplayer.app import create_app
from blindbillion.multiplayer.db import get_db
from blindbillion.multiplayer.db_models import Base


@pytest.fixture
def test_db_session() -> Generator[Session, None, None]:
    """Provide a isolated shared in-memory SQLite database session for AI bot tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_db_session: Session) -> Generator[TestClient, None, None]:
    """Provide FastAPI test client wired with test DB and real GameEngine."""
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_add_and_remove_ai_opponent_in_lobby(client: TestClient) -> None:
    """Verify host can add and remove AI opponents with difficulty profiles."""
    res = client.post("/api/rooms", json={"host_name": "Manager Alice"})
    assert res.status_code == 201
    room_code = res.json()["room"]["room_code"]
    host_token = res.json()["session_token"]

    # 1. Host adds Pro AI
    res_ai1 = client.post(
        f"/api/rooms/{room_code}/ai",
        json={"difficulty": "PRO"},
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_ai1.status_code == 200
    players = res_ai1.json()["players"]
    assert len(players) == 2
    ai1 = next(p for p in players if p["is_ai"])
    assert ai1["display_name"] == "Bot (Pro)"
    assert ai1["ai_difficulty"] == "PRO"
    assert ai1["is_ready"] is True

    # 2. Host adds Legend AI
    res_ai2 = client.post(
        f"/api/rooms/{room_code}/ai",
        json={"difficulty": "LEGEND"},
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_ai2.status_code == 200
    assert len(res_ai2.json()["players"]) == 3

    # 3. Non-host cannot add AI
    res_guest = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Bob"})
    assert res_guest.status_code == 200
    guest_token = res_guest.json()["session_token"]

    res_forbidden = client.post(
        f"/api/rooms/{room_code}/ai",
        json={"difficulty": "ROOKIE"},
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert res_forbidden.status_code == 403

    # 4. Adding 5th player rejected (max 4)
    res_full = client.post(
        f"/api/rooms/{room_code}/ai",
        json={"difficulty": "ROOKIE"},
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_full.status_code == 409
    assert "already full" in res_full.json()["detail"]

    # 5. Host removes Legend AI
    ai_legend_id = next(
        p["player_id"] for p in res_ai2.json()["players"] if p["ai_difficulty"] == "LEGEND"
    )
    res_del = client.delete(
        f"/api/rooms/{room_code}/ai/{ai_legend_id}",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_del.status_code == 200
    assert len(res_del.json()["players"]) == 3


def test_human_vs_ai_gameplay_and_automated_barrier_clearance(client: TestClient) -> None:
    """Verify human vs AI: human turn automatically triggers AI turn to advance round."""
    res = client.post("/api/rooms", json={"host_name": "SoloManager", "room_seed": "SEED_SOLO_AI"})
    room_code = res.json()["room"]["room_code"]
    host_token = res.json()["session_token"]

    # Add Pro AI
    client.post(
        f"/api/rooms/{room_code}/ai",
        json={"difficulty": "PRO"},
        headers={"Authorization": f"Bearer {host_token}"},
    )

    # Start game (Host + 1 AI = 2 players, valid!)
    res_start = client.post(
        f"/api/rooms/{room_code}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert res_start.status_code == 200
    assert res_start.json()["room"]["status"] == "IN_GAME"
    assert res_start.json()["room"]["current_year"] == 2016

    # Fetch initial human state and shortlist
    st_res = client.get(
        f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {host_token}"}
    )
    st = st_res.json()["my_state"]
    cands = st["shortlists"]["1"]["candidates"]
    assert len(cands) == 4

    # Human buys candidate 0 -> triggers AI turn and barrier immediately clears!
    act_res = client.post(
        f"/api/rooms/{room_code}/action",
        json={
            "action_type": "BUY",
            "candidate_token": cands[0]["candidate_token"],
            "idempotency_key": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert act_res.status_code == 200
    assert act_res.json()["is_barrier_cleared"] is True  # Because AI automatically submitted!
    assert act_res.json()["room"]["current_year"] == 2017
    assert act_res.json()["room"]["current_slot_index"] == 2
