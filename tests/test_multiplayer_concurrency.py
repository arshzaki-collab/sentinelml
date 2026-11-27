"""Automated tests for multiplayer idempotency, concurrency controls, and state locking."""

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


def test_action_idempotency_key_deduplication(client: TestClient) -> None:
    """Verify duplicate idempotency key returns cached response without double deduction."""
    res_host = client.post("/api/rooms", json={"host_name": "HostPlayer"})
    room_code = res_host.json()["room"]["room_code"]
    t1 = res_host.json()["session_token"]

    res_p2 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "SecondPlayer"})
    t2 = res_p2.json()["session_token"]

    client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {t2}"},
    )
    client.post(f"/api/rooms/{room_code}/start", headers={"Authorization": f"Bearer {t1}"})

    state = client.get(
        f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"}
    ).json()["my_state"]
    cand_token = state["shortlists"]["1"]["candidates"][0]["candidate_token"]
    idemp_key = str(uuid.uuid4())

    # 1. First execution
    action_payload = {
        "action_type": "BUY",
        "candidate_token": cand_token,
        "idempotency_key": idemp_key,
    }
    res_act1 = client.post(
        f"/api/rooms/{room_code}/action",
        json=action_payload,
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert res_act1.status_code == 200
    data_1 = res_act1.json()
    balance_1 = data_1["new_balance"]

    # 2. Second execution with identical idempotency key (network retry simulation)
    res_act2 = client.post(
        f"/api/rooms/{room_code}/action",
        json=action_payload,
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert res_act2.status_code == 200
    data_2 = res_act2.json()

    # Must return exact same response and no second deduction
    assert data_2["new_balance"] == balance_1
    assert data_2["action_type"] == data_1["action_type"]
    assert data_2["message"] == data_1["message"]


def test_concurrent_turn_conflict_rejected(client: TestClient) -> None:
    """Verify attempting to submit a new action after already submitting is rejected."""
    res_host = client.post("/api/rooms", json={"host_name": "HostPlayer"})
    room_code = res_host.json()["room"]["room_code"]
    t1 = res_host.json()["session_token"]

    res_p2 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "SecondPlayer"})
    t2 = res_p2.json()["session_token"]

    client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {t2}"},
    )
    client.post(f"/api/rooms/{room_code}/start", headers={"Authorization": f"Bearer {t1}"})

    state = client.get(
        f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"}
    ).json()["my_state"]
    cand0 = state["shortlists"]["1"]["candidates"][0]["candidate_token"]
    cand1 = state["shortlists"]["1"]["candidates"][1]["candidate_token"]

    # First purchase
    client.post(
        f"/api/rooms/{room_code}/action",
        json={"action_type": "BUY", "candidate_token": cand0, "idempotency_key": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {t1}"},
    )

    # Second purchase attempt with different idempotency key
    res_conflict = client.post(
        f"/api/rooms/{room_code}/action",
        json={"action_type": "BUY", "candidate_token": cand1, "idempotency_key": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert res_conflict.status_code == 400
    assert "already submitted" in res_conflict.json()["detail"].lower()
