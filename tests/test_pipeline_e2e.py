"""End-to-end integration tests validating the live DuckDB database and pipeline outputs."""

from collections.abc import Generator
from pathlib import Path

import duckdb
import pytest

from blindbillion.constants import SQUAD_SLOTS
from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.data.shortlist import ShortlistGenerator


@pytest.fixture(scope="module")
def live_con() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    if not Path(DEFAULT_DB_PATH).exists():
        pytest.skip(f"Live database {DEFAULT_DB_PATH} not found; run pipeline first.")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    yield con
    con.close()


def test_live_database_tables(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify all raw and analytical tables exist and have positive row counts."""
    tables = live_con.execute("SHOW TABLES").fetchall()
    table_names = {t[0] for t in tables}

    expected_tables = {
        "raw_competitions",
        "raw_games",
        "raw_clubs",
        "raw_players",
        "raw_appearances",
        "raw_player_valuations",
        "raw_club_games",
        "player_annual_valuations",
        "player_season_stats",
        "ingestion_runs",
    }
    for expected in expected_tables:
        assert expected in table_names

        cnt = live_con.execute(f"SELECT COUNT(*) FROM {expected}").fetchone()
        assert cnt is not None and cnt[0] > 0


def test_live_valuations_integrity(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify strict valuation constraints: 180-day max age, no nulls, positive USD values."""
    # Check 180-day age invariant
    invalid_age = live_con.execute("""
        SELECT COUNT(*) FROM player_annual_valuations
        WHERE observation_age_days > 180 OR observation_age_days < 0;
    """).fetchone()
    assert invalid_age is not None and invalid_age[0] == 0

    # Check non-null / positive USD invariant
    invalid_values = live_con.execute("""
        SELECT COUNT(*) FROM player_annual_valuations
        WHERE converted_usd_value IS NULL OR converted_usd_value <= 0;
    """).fetchone()
    assert invalid_values is not None and invalid_values[0] == 0

    # Check years cover 2016 through 2026
    years = live_con.execute("""
        SELECT DISTINCT reference_year FROM player_annual_valuations ORDER BY reference_year;
    """).fetchall()
    observed_years = [y[0] for y in years]
    assert observed_years == list(range(2016, 2027))


def test_live_all_seven_slots_shortlists(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify deterministic shortlist generation for all seven required slots."""
    generator = ShortlistGenerator(con=live_con)
    shortlists = generator.generate_full_game_shortlists(room_seed="INTEGRATION_TEST_ROOM")

    assert len(shortlists) == 7

    for slot_idx in range(1, 8):
        assert slot_idx in shortlists
        shortlist = shortlists[slot_idx]
        slot_cfg = SQUAD_SLOTS[slot_idx - 1]

        assert shortlist.slot_index == slot_idx
        assert shortlist.buying_year == slot_cfg["year"]
        assert shortlist.position == slot_cfg["position"]
        assert len(shortlist.candidates) == 4
        assert len(shortlist.secret_player_ids) == 4

        # Validate hint rules for each candidate
        for cand in shortlist.candidates:
            assert len(cand.hints) == 3
            assert cand.cost_usd > 0

            if shortlist.position in ("ST", "WG"):
                assert "Goals" in cand.hints
            elif shortlist.position == "CM":
                assert "Assists" in cand.hints
            elif shortlist.position == "CB":
                assert "Clean Sheets" in cand.hints
            elif shortlist.position == "GK":
                assert "Clean Sheets" in cand.hints
                assert "Age" in cand.hints
                assert "League" in cand.hints
