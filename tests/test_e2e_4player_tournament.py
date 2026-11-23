"""End-to-End 4-Player Tournament Simulation.

Simulates 4 players (2 humans + 2 AI personas: Pro and Legend) competing
across all 11 timeline steps (2016-2026), testing:
- 4-player capacity enforcement
- Automated AI turn synchronization
- Mid-game session refresh & recovery
- Authentic transfer window sale & replacement
- 2026 final valuation reveal, arithmetic invariants, and tournament leaderboard.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

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
    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db

    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    engine = GameEngine(con=con)
    coord = GameCoordinator(engine=engine)
    app.dependency_overrides[get_game_coordinator] = lambda: coord

    global_rate_limiter.reset()

    with TestClient(app) as test_client:
        yield test_client


def test_full_4player_tournament_simulation(client: TestClient) -> None:
    """Run an entire 4-player tournament (2 humans + Pro AI + Legend AI) from 2016 to 2026."""
    # --------------------------------------------------------------------------
    # 1. Room Creation & Lobby Setup
    # --------------------------------------------------------------------------
    res_host = client.post(
        "/api/rooms", json={"host_name": "Helena", "room_seed": "SEED_TOURNAMENT_4P"}
    )
    assert res_host.status_code == 201
    room_code = res_host.json()["room"]["room_code"]
    t_h1 = res_host.json()["session_token"]
    h1_id = res_host.json()["player_id"]

    # Human 2 Joins
    res_h2 = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "Marcus"})
    assert res_h2.status_code == 200
    t_h2 = res_h2.json()["session_token"]

    # Add Pro AI
    res_ai_pro = client.post(
        f"/api/rooms/{room_code}/ai",
        json={"difficulty": "PRO"},
        headers={"Authorization": f"Bearer {t_h1}"},
    )
    assert res_ai_pro.status_code == 200

    # Add Legend AI
    res_ai_legend = client.post(
        f"/api/rooms/{room_code}/ai",
        json={"difficulty": "LEGEND"},
        headers={"Authorization": f"Bearer {t_h1}"},
    )
    assert res_ai_legend.status_code == 200
    players = res_ai_legend.json()["players"]
    assert len(players) == 4

    # Verify 5th player rejected (capacity limit)
    res_5th = client.post(f"/api/rooms/{room_code}/join", json={"player_name": "ExtraPlayer"})
    assert res_5th.status_code == 409

    # Human 2 marks ready
    client.post(
        f"/api/rooms/{room_code}/ready",
        json={"is_ready": True},
        headers={"Authorization": f"Bearer {t_h2}"},
    )

    # Host starts the game
    start_res = client.post(
        f"/api/rooms/{room_code}/start",
        headers={"Authorization": f"Bearer {t_h1}"},
    )
    assert start_res.status_code == 200
    assert start_res.json()["room"]["status"] == "IN_GAME"

    # --------------------------------------------------------------------------
    # 2. Playthrough across 10 rounds (7 Buying Seasons + 3 Transfer Windows)
    # --------------------------------------------------------------------------
    for round_num in range(10):
        room_info = client.get(f"/api/rooms/{room_code}").json()
        current_year = room_info["current_year"]
        current_phase = room_info["current_phase"]
        slot_idx = room_info["current_slot_index"]

        # Fetch current state for both human players
        st1 = client.get(
            f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t_h1}"}
        ).json()["my_state"]
        client.get(f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t_h2}"})

        # Assert zero identity leakage in responses
        for _shortlist_key, sl in st1.get("shortlists", {}).items():
            for cand in sl.get("candidates", []):
                assert "player_name" not in cand
                assert "player_id" not in cand
                assert "url" not in cand

        if current_phase == "BUYING_SEASON":
            assert slot_idx is not None
            cands = st1["shortlists"][str(slot_idx)]["candidates"]
            assert len(cands) == 4

            # Human 1 buys candidate 0
            act1 = client.post(
                f"/api/rooms/{room_code}/action",
                json={
                    "action_type": "BUY",
                    "candidate_token": cands[0]["candidate_token"],
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"Authorization": f"Bearer {t_h1}"},
            )
            assert act1.status_code == 200

            # Human 2 buys candidate 1
            act2 = client.post(
                f"/api/rooms/{room_code}/action",
                json={
                    "action_type": "BUY",
                    "candidate_token": cands[1]["candidate_token"],
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"Authorization": f"Bearer {t_h2}"},
            )
            assert act2.status_code == 200

            # Once both humans submit, AI turns execute automatically and barrier clears!
            assert act2.json()["is_barrier_cleared"] is True

        elif current_phase == "TRANSFER_WINDOW":
            if current_year == 2019:
                # Test active transfer: Human 1 sells Slot 1 (ST) and buys replacement candidate
                shortlist_slot1 = st1["shortlists"]["1"]["candidates"]
                # Pick candidate 2 as replacement
                rep_candidate = shortlist_slot1[2]["candidate_token"]

                act1_rep = client.post(
                    f"/api/rooms/{room_code}/action",
                    json={
                        "action_type": "REPLACE",
                        "slot_index": 1,
                        "candidate_token": rep_candidate,
                        "idempotency_key": str(uuid.uuid4()),
                    },
                    headers={"Authorization": f"Bearer {t_h1}"},
                )
                assert act1_rep.status_code == 200

                # Human 1 submits PASS to conclude transfer turn
                act1_pass = client.post(
                    f"/api/rooms/{room_code}/action",
                    json={"action_type": "PASS", "idempotency_key": str(uuid.uuid4())},
                    headers={"Authorization": f"Bearer {t_h1}"},
                )
                assert act1_pass.status_code == 200

                # Human 2 passes
                act2 = client.post(
                    f"/api/rooms/{room_code}/action",
                    json={"action_type": "PASS", "idempotency_key": str(uuid.uuid4())},
                    headers={"Authorization": f"Bearer {t_h2}"},
                )
                assert act2.status_code == 200
                assert act2.json()["is_barrier_cleared"] is True

            else:
                # Other transfer windows (2022, 2025): both humans pass
                client.post(
                    f"/api/rooms/{room_code}/action",
                    json={"action_type": "PASS", "idempotency_key": str(uuid.uuid4())},
                    headers={"Authorization": f"Bearer {t_h1}"},
                )
                act2 = client.post(
                    f"/api/rooms/{room_code}/action",
                    json={"action_type": "PASS", "idempotency_key": str(uuid.uuid4())},
                    headers={"Authorization": f"Bearer {t_h2}"},
                )
                assert act2.status_code == 200
                assert act2.json()["is_barrier_cleared"] is True

        # Test mid-game reconnection resilience on round 5
        if round_num == 5:
            refresh_res = client.get(
                f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t_h2}"}
            )
            assert refresh_res.status_code == 200
            recovered_state = refresh_res.json()["my_state"]
            assert recovered_state["cash_balance"] > 0
            filled_slots = [s for s in recovered_state["slots"] if s["is_filled"]]
            assert len(filled_slots) >= 3

    # --------------------------------------------------------------------------
    # 3. Final Settlement & Tournament Leaderboard Audit
    # --------------------------------------------------------------------------
    final_res = client.get(
        f"/api/rooms/{room_code}/state", headers={"Authorization": f"Bearer {t_h1}"}
    )
    assert final_res.status_code == 200
    final_payload = final_res.json()

    assert final_payload["room"]["status"] == "COMPLETED"
    assert final_payload["room"]["is_completed"] is True
    assert final_payload["my_state"]["is_completed"] is True

    leaderboard = final_payload["leaderboard"]
    assert leaderboard is not None
    assert len(leaderboard) == 4

    # Verify ranks strictly ordered 1 through 4 by final_net_worth DESC
    ranks = [entry["rank"] for entry in leaderboard]
    assert ranks == [1, 2, 3, 4]

    for i in range(len(leaderboard) - 1):
        assert leaderboard[i]["final_net_worth"] >= leaderboard[i + 1]["final_net_worth"]

    # Verify participant identities in leaderboard
    leaderboard_names = {entry["display_name"] for entry in leaderboard}
    assert "Helena" in leaderboard_names
    assert "Marcus" in leaderboard_names
    assert any("Pro" in name for name in leaderboard_names)
    assert any("Legend" in name for name in leaderboard_names)

    # Verify arithmetic invariant on Helena's state:
    # final_net_worth == remaining_cash + sum(final_player_values)
    helena_entry = next(e for e in leaderboard if e["player_id"] == h1_id)
    my_st = final_payload["my_state"]

    cash = my_st["cash_balance"]
    slots = my_st["slots"]
    assert len(slots) == 7  # All 7 positions filled: ST, WG, CM, CB, CM, CB, GK

    # In 2026 reveal, player identities are unmasked
    for slot_view in slots:
        assert slot_view["current_player_name"] is not None
        assert slot_view["current_player_name"] != "Anonymous Signed Player"
        assert len(slot_view["current_player_name"]) > 0

    settlement_records = my_st["settlement_records"]
    assert settlement_records is not None
    assert len(settlement_records) == 7

    total_squad_value = sum(r["valuation_2026_usd"] for r in settlement_records)
    expected_net_worth = cash + total_squad_value

    assert abs(my_st["final_net_worth"] - expected_net_worth) < 1.0
    assert abs(helena_entry["final_net_worth"] - expected_net_worth) < 1.0

    # Verify starting budget invariant: no player ever went below $0
    for entry in leaderboard:
        assert entry["final_net_worth"] > 0
        assert entry["remaining_cash"] >= 0
        expected_total = entry["remaining_cash"] + entry["squad_valuation"]
        assert abs(entry["final_net_worth"] - expected_total) < 1.0
