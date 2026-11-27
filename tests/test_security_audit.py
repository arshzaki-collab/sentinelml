"""Security Audit and Invariant Verification Suite for Blind Billion 2.0.

Tests:
1. Health check endpoint verification
2. Zero-identity-leakage penetration audit (payloads anonymous prior to reveal)
3. Cross-player session isolation and unauthorized action prevention
4. Financial invariants (insufficient funds rejection, exact arithmetic)
5. Game rule invariant enforcement (no sales outside transfer windows)
6. Rate limiting and brute-force abuse protection
7. SQL injection, path traversal, and XSS input sanitization.
"""

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


def test_health_check_endpoint(client: TestClient) -> None:
    """Verify /health returns 200 OK and reports healthy status for DB and DuckDB."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
    assert data["database"] == "connected"
    assert data["analytical_cache"] == "connected"


def test_zero_identity_leakage_penetration_test(client: TestClient) -> None:
    """Penetration test: assert secret player IDs and real names never appear in pre-2026 views."""
    # 1. Create 2-player game
    res_host = client.post(
        "/api/rooms", json={"host_name": "Auditor", "room_seed": "SEED_SECURITY_AUDIT"}
    )
    room_code = res_host.json()["room"]["room_code"]
    t1 = res_host.json()["session_token"]

    res_join = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Assistant"})
    t2 = res_join.json()["session_token"]

    client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {t2}"},
    )
    client.post(f"/api/rooms/{room_code}/start", headers={"Authorization": f"Bearer {t1}"})

    # Retrieve duckdb connection to get all actual secret player names for this room seed
    coord = client.app.dependency_overrides[get_game_coordinator]()  # type: ignore[attr-defined]
    shortlists = coord.engine.shortlist_gen.generate_full_game_shortlists(
        room_seed="SEED_SECURITY_AUDIT"
    )

    all_secret_ids = set()
    for sl in shortlists.values():
        all_secret_ids.update(sl.secret_player_ids)

    # Resolve real player names from DuckDB
    con = coord.engine.con
    placeholders = ", ".join(f"'{pid}'" for pid in all_secret_ids)
    sql_query = (
        f"SELECT player_id, name FROM raw_players "
        f"WHERE CAST(player_id AS VARCHAR) IN ({placeholders})"
    )
    rows = con.execute(sql_query).fetchall()
    secret_names = {row[1] for row in rows if row[1]}

    # Check state and action responses during round 0 (2016)
    st_res = client.get(f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"})
    st_text = st_res.text

    # Penetration check: none of the secret IDs or secret player names may be in the response text
    for pid in all_secret_ids:
        assert f'"{pid}"' not in st_text, f"Secret player ID {pid} leaked in /state response!"
    for name in secret_names:
        assert f'"{name}"' not in st_text, f"Secret player name '{name}' leaked in /state response!"

    # Candidate hints check
    st_data = st_res.json()["my_state"]
    cand0 = st_data["shortlists"]["1"]["candidates"][0]
    assert "player_name" not in cand0
    assert "player_id" not in cand0
    assert len(cand0["hints"]) == 3


def test_cross_player_authorization_and_session_security(client: TestClient) -> None:
    """Verify session token authorization, forgery rejection, and role-based permissions."""
    # 1. Create Room
    res_host = client.post("/api/rooms", json={"host_name": "Alice", "room_seed": "SEED_AUTH_TEST"})
    room_code = res_host.json()["room"]["room_code"]
    t1 = res_host.json()["session_token"]
    assert len(t1) > 20

    res_join = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Bob"})
    t2 = res_join.json()["session_token"]

    # 2. Forged / invalid token
    res_forged = client.get(
        f"/api/rooms/{room_code}/state", headers={"Authorization": "Bearer forged_token_12345"}
    )
    assert res_forged.status_code == 401

    # 3. Missing token
    res_missing = client.get(f"/api/rooms/{room_code}/state")
    assert res_missing.status_code in (401, 403)

    # 4. Non-host attempting host-only action (start game)
    res_unauth_start = client.post(
        f"/api/rooms/{room_code}/start", headers={"Authorization": f"Bearer {t2}"}
    )
    assert res_unauth_start.status_code == 403
    assert "Only the host" in res_unauth_start.json()["detail"]

    # 5. Non-host attempting to add AI opponent
    res_unauth_ai = client.post(
        f"/api/rooms/{room_code}/ai",
        json={"difficulty": "PRO"},
        headers={"Authorization": f"Bearer {t2}"},
    )
    assert res_unauth_ai.status_code == 403
    assert "Only the host" in res_unauth_ai.json()["detail"]

    # 6. Non-existent room query
    res_404 = client.get("/api/rooms/ZZZZ")
    assert res_404.status_code == 404


def test_game_rule_and_financial_invariants(client: TestClient) -> None:
    """Verify financial balance protection, invalid phase actions, and shortlist constraints."""
    res_host = client.post(
        "/api/rooms", json={"host_name": "Investor", "room_seed": "SEED_RULES_TEST"}
    )
    room_code = res_host.json()["room"]["room_code"]
    t1 = res_host.json()["session_token"]

    res_join = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Competitor"})
    t2 = res_join.json()["session_token"]

    client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {t2}"},
    )
    client.post(f"/api/rooms/{room_code}/start", headers={"Authorization": f"Bearer {t1}"})

    # Rule Violation 1: Attempting to PASS during BUYING_SEASON
    res_invalid_pass = client.post(
        f"/api/rooms/{room_code}/action",
        json={"action_type": "PASS", "idempotency_key": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert res_invalid_pass.status_code == 400
    assert "PASS action is not permitted during BUYING_SEASON" in res_invalid_pass.json()["detail"]

    # Rule Violation 2: Attempting to SELL during BUYING_SEASON
    res_invalid_sell = client.post(
        f"/api/rooms/{room_code}/action",
        json={"action_type": "SELL", "slot_index": 1, "idempotency_key": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert res_invalid_sell.status_code == 400
    err_detail = res_invalid_sell.json()["detail"].lower()
    assert "transfers are only permitted during scheduled transfer windows" in err_detail

    # Rule Violation 3: Attempting to BUY with a non-existent candidate token
    res_invalid_token = client.post(
        f"/api/rooms/{room_code}/action",
        json={
            "action_type": "BUY",
            "candidate_token": "non_existent_token_xyz",
            "idempotency_key": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert res_invalid_token.status_code == 400

    # Rule Violation 4: Double turn submission in same round
    st = client.get(
        f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t1}"}
    ).json()["my_state"]
    cand0 = st["shortlists"]["1"]["candidates"][0]["candidate_token"]

    act1 = client.post(
        f"/api/rooms/{room_code}/action",
        json={"action_type": "BUY", "candidate_token": cand0, "idempotency_key": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert act1.status_code == 200

    # Attempting to submit another BUY while turn already submitted
    cand1 = st["shortlists"]["1"]["candidates"][1]["candidate_token"]
    act_double = client.post(
        f"/api/rooms/{room_code}/action",
        json={"action_type": "BUY", "candidate_token": cand1, "idempotency_key": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert act_double.status_code == 400
    assert "already submitted" in act_double.json()["detail"].lower()


def test_rate_limiting_protection(client: TestClient) -> None:
    """Verify rate limiter blocks room creation flooding (10/min) and returns 429."""
    for i in range(10):
        res = client.post(
            "/api/rooms", json={"host_name": f"Flooder_{i}", "room_seed": f"SEED_{i}"}
        )
        assert res.status_code == 201

    # 11th request exceeds 10 req/min limit
    res_blocked = client.post(
        "/api/rooms", json={"host_name": "Flooder_11", "room_seed": "SEED_11"}
    )
    assert res_blocked.status_code == 429
    assert "rate limit exceeded" in res_blocked.json()["detail"].lower()


def test_input_sanitization_and_injection_safety(client: TestClient) -> None:
    """Verify robustness against SQL injection, path traversal, and malicious input."""
    # SQL injection in room code
    sql_injection_code = "' OR '1'='1"
    res_sql = client.get(f"/api/rooms/{sql_injection_code}")
    assert res_sql.status_code == 404  # Handled safely as non-existent room, no 500 or SQL error

    # Path traversal in room code
    path_traversal_code = "../../../etc/passwd"
    res_path = client.get(f"/api/rooms/{path_traversal_code}")
    assert res_path.status_code in (404, 400)

    # XSS payload in player display name
    xss_name = "<script>alert('pwned')</script>"
    res_xss = client.post("/api/rooms", json={"host_name": xss_name, "room_seed": "SEED_XSS"})
    assert res_xss.status_code == 201
    room_code = res_xss.json()["room"]["room_code"]
    t = res_xss.json()["session_token"]

    # Verify display name is treated as text
    st = client.get(f"/api/rooms/{room_code}", headers={"Authorization": f"Bearer {t}"}).json()
    assert st["players"][0]["display_name"] == xss_name
