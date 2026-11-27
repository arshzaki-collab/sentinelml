"""Tests for multiplayer round synchronization, shared shortlists, and final leaderboard."""

from __future__ import annotations

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


def test_shared_shortlists_and_round_barrier_progression(client: TestClient) -> None:
    """Verify all players share identical shortlists and timeline advances only when all submit."""
    # 1. Setup 2-player game
    res_host = client.post(
        "/api/rooms", json={"host_name": "Alice", "room_seed": "SEED_TEST_MULTI"}
    )
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

    # 2. Verify both players receive identical 4-candidate shortlists for Slot 1 (ST)
    s1_res = client.get(f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"})
    s2_res = client.get(f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t2}"})

    s1_data = s1_res.json()["my_state"]
    s2_data = s2_res.json()["my_state"]

    cands_p1 = [c["candidate_token"] for c in s1_data["shortlists"]["1"]["candidates"]]
    cands_p2 = [c["candidate_token"] for c in s2_data["shortlists"]["1"]["candidates"]]

    assert len(cands_p1) == 4
    assert cands_p1 == cands_p2  # Identical shared scenario

    # 3. Alice buys candidate 0
    act1 = client.post(
        f"/api/rooms/{room_code}/action",
        json={
            "action_type": "BUY",
            "candidate_token": cands_p1[0],
            "idempotency_key": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert act1.status_code == 200
    assert act1.json()["is_barrier_cleared"] is False  # Awaiting Bob!
    assert act1.json()["room"]["current_year"] == 2016
    assert act1.json()["room"]["current_slot_index"] == 1

    # Verify Alice cannot buy again in the same round
    act1_duplicate = client.post(
        f"/api/rooms/{room_code}/action",
        json={
            "action_type": "BUY",
            "candidate_token": cands_p1[1],
            "idempotency_key": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert act1_duplicate.status_code == 400
    assert "already submitted" in act1_duplicate.json()["detail"].lower()

    # 4. Bob buys candidate 1 -> barrier clears!
    act2 = client.post(
        f"/api/rooms/{room_code}/action",
        json={
            "action_type": "BUY",
            "candidate_token": cands_p2[1],
            "idempotency_key": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {t2}"},
    )
    assert act2.status_code == 200
    assert act2.json()["is_barrier_cleared"] is True  # Barrier cleared!
    assert act2.json()["room"]["current_year"] == 2017
    assert act2.json()["room"]["current_slot_index"] == 2
    assert act2.json()["room"]["current_phase"] == "BUYING_SEASON"


def test_complete_multiplayer_game_and_leaderboard_generation(client: TestClient) -> None:
    """Verify 2 players complete an entire 11-step game to 2026 settlement and leaderboard."""
    res_host = client.post(
        "/api/rooms", json={"host_name": "Alice", "room_seed": "SEED_LEADERBOARD_1"}
    )
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

    # Play through all rounds (7 buying seasons + 3 transfer windows = 10 action rounds)
    for _ in range(10):
        # Fetch current room state
        room_info = client.get(f"/api/rooms/{room_code}").json()
        phase = room_info["current_phase"]
        slot_idx = room_info["current_slot_index"]

        st1 = client.get(
            f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"}
        ).json()["my_state"]
        client.get(f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t2}"})

        if phase == "BUYING_SEASON":
            assert slot_idx is not None
            cands = st1["shortlists"][str(slot_idx)]["candidates"]
            # Alice picks candidate 0, Bob picks candidate 1
            client.post(
                f"/api/rooms/{room_code}/action",
                json={
                    "action_type": "BUY",
                    "candidate_token": cands[0]["candidate_token"],
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"Authorization": f"Bearer {t1}"},
            )
            client.post(
                f"/api/rooms/{room_code}/action",
                json={
                    "action_type": "BUY",
                    "candidate_token": cands[1]["candidate_token"],
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"Authorization": f"Bearer {t2}"},
            )
        elif phase == "TRANSFER_WINDOW":
            # Both players pass to advance
            client.post(
                f"/api/rooms/{room_code}/action",
                json={"action_type": "PASS", "idempotency_key": str(uuid.uuid4())},
                headers={"Authorization": f"Bearer {t1}"},
            )
            client.post(
                f"/api/rooms/{room_code}/action",
                json={"action_type": "PASS", "idempotency_key": str(uuid.uuid4())},
                headers={"Authorization": f"Bearer {t2}"},
            )

    # Game should now be COMPLETED
    final_res = client.get(
        f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"}
    )
    final_data = final_res.json()

    assert final_data["room"]["status"] == "COMPLETED"
    assert final_data["room"]["is_completed"] is True
    assert final_data["my_state"]["is_completed"] is True
    assert final_data["my_state"]["final_net_worth"] is not None

    leaderboard = final_data["leaderboard"]
    assert leaderboard is not None
    assert len(leaderboard) == 2
    assert leaderboard[0]["rank"] == 1
    assert leaderboard[1]["rank"] == 2
    assert leaderboard[0]["final_net_worth"] >= leaderboard[1]["final_net_worth"]
    # Verify player names revealed
    assert {leaderboard[0]["display_name"], leaderboard[1]["display_name"]} == {"Alice", "Bob"}
