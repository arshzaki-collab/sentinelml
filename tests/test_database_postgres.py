"""Tests for PostgreSQL URL normalization, model serialization, and dialect compatibility."""

from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import sessionmaker

from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.engine.engine import GameEngine
from blindbillion.multiplayer.db import normalize_database_url
from blindbillion.multiplayer.db_models import (
    ActionIdempotencyModel,
    Base,
    PlayerGameStateModel,
    RoomModel,
    UniversalJson,
)
from blindbillion.multiplayer.game_coordinator import parse_stored_game_state


def test_normalize_database_url_converts_postgres_scheme() -> None:
    raw_supabase_url = "postgres://postgres:secret@db.supabase.co:5432/postgres?sslmode=require"
    normalized = normalize_database_url(raw_supabase_url)
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=require" in normalized


def test_normalize_database_url_converts_bare_postgresql_scheme() -> None:
    raw_url = "postgresql://user:pass@localhost:5432/bb"
    normalized = normalize_database_url(raw_url)
    assert normalized == "postgresql+psycopg://user:pass@localhost:5432/bb"


def test_normalize_database_url_preserves_explicit_driver_or_sqlite() -> None:
    psycopg_url = "postgresql+psycopg://user:pass@localhost:5432/bb"
    assert normalize_database_url(psycopg_url) == psycopg_url

    sqlite_url = "sqlite:///data/test.db"
    assert normalize_database_url(sqlite_url) == sqlite_url


def test_universal_json_bind_param_handling() -> None:
    uj = UniversalJson()

    pg_dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    sqlite_dialect = sqlite.dialect()

    # When binding to PostgreSQL: raw JSON string should be converted to dict
    json_str = '{"cash_balance": 1000000000, "current_year": 2016}'
    pg_val = uj.process_bind_param(json_str, pg_dialect)
    assert isinstance(pg_val, dict)
    assert pg_val["cash_balance"] == 1000000000

    # When binding dict to PostgreSQL: preserved as dict
    sample_dict = {"a": 1}
    assert uj.process_bind_param(sample_dict, pg_dialect) == sample_dict

    # When binding to SQLite: converted to string
    sqlite_val = uj.process_bind_param(sample_dict, sqlite_dialect)
    assert isinstance(sqlite_val, str)
    assert '"a": 1' in sqlite_val


def test_parse_stored_game_state_handles_both_dict_and_str() -> None:
    if not Path(DEFAULT_DB_PATH).exists():
        pytest.skip("DuckDB analytical cache not found.")

    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    engine = GameEngine(con=con)
    real_state = engine.initialize_game(game_id="G1", room_seed="S1")
    con.close()

    # Dict input (PostgreSQL JSONB behavior)
    state_dict = real_state.model_dump(mode="json")
    state1 = parse_stored_game_state(state_dict)
    assert state1.cash_balance == 1000000000.0
    assert state1.current_year == 2016

    # String input (SQLite TEXT behavior)
    state_json = real_state.model_dump_json()
    state2 = parse_stored_game_state(state_json)
    assert state2.cash_balance == 1000000000.0
    assert state2.current_year == 2016


def test_sqlite_in_memory_crud_with_universal_json() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        room = RoomModel(
            room_code="TEST",
            status="IN_GAME",
            host_player_id="p1",
            room_seed="SEED",
            expires_at=datetime.now(UTC),
        )
        session.add(room)

        state_rec = PlayerGameStateModel(
            room_code="TEST",
            player_id="p1",
            serialized_state={"cash_balance": 800000000, "current_year": 2017},
        )
        session.add(state_rec)

        idemp_rec = ActionIdempotencyModel(
            idempotency_key="key_1",
            room_code="TEST",
            player_id="p1",
            action_type="BUY",
            response_payload={"success": True, "message": "Signed"},
        )
        session.add(idemp_rec)
        session.commit()

        # Query back
        loaded = session.query(PlayerGameStateModel).filter_by(room_code="TEST").first()
        assert loaded is not None
        assert "800000000" in loaded.serialized_state
