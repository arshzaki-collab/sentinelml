"""Unit tests for shortlist generation, deterministic reproducibility, and anonymous hints."""

import duckdb

from blindbillion.data.shortlist import ShortlistGenerator


def setup_mock_db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")

    con.execute("""
        CREATE TABLE player_annual_valuations (
            player_id VARCHAR,
            reference_year INTEGER,
            converted_usd_value DOUBLE,
            original_value DOUBLE
        );

        CREATE TABLE player_season_stats (
            player_id VARCHAR,
            season_year INTEGER,
            player_name VARCHAR,
            sub_position VARCHAR,
            age_at_reference INTEGER,
            domestic_league_code VARCHAR,
            domestic_league_name VARCHAR,
            appearances INTEGER,
            goals INTEGER,
            assists INTEGER,
            yellow_cards INTEGER,
            red_cards INTEGER,
            clean_sheets INTEGER,
            ucl_appearances INTEGER,
            ucl_goals INTEGER
        );
    """)

    # Populate 12 mock strikers for 2016 (Slot 1) with complete valuation history through 2026
    for i in range(1, 13):
        pid = f"ST_{i}"
        # Stats in 2016
        con.execute(f"""
            INSERT INTO player_season_stats VALUES (
                '{pid}', 2016, 'Striker {i}', 'Centre-Forward', 24, 'GB1', 'Premier League',
                30, {10 + i}, {2 + i}, 2, 0, 8, 4, {i},
            );
        """)
        # Valuations across 2016, 2019, 2022, 2025, 2026
        for yr in (2016, 2019, 2022, 2025, 2026):
            val = float(i * 10_000_000)
            con.execute(f"""
                INSERT INTO player_annual_valuations VALUES (
                    '{pid}', {yr}, {val}, {val / 1.11}
                );
            """)

    return con


def test_shortlist_generator_slot_1_st() -> None:
    con = setup_mock_db()
    generator = ShortlistGenerator(con=con)

    shortlist = generator.generate_slot_shortlist(slot_index=1, room_seed="GAME_123")

    assert shortlist.slot_index == 1
    assert shortlist.buying_year == 2016
    assert shortlist.position == "ST"
    assert len(shortlist.candidates) == 4
    assert len(shortlist.secret_player_ids) == 4

    for candidate in shortlist.candidates:
        assert candidate.position == "ST"
        assert candidate.cost_usd > 0
        assert len(candidate.hints) == 3
        assert "Goals" in candidate.hints  # Compulsory for forwards
        # The other 2 must be from Age, Assists, League, UCL Goals
        allowed_options = {"Age", "Assists", "League", "UCL Goals"}
        for k in candidate.hints:
            if k != "Goals":
                assert k in allowed_options


def test_shortlist_reproducibility() -> None:
    con = setup_mock_db()
    generator = ShortlistGenerator(con=con)

    # Same seed must produce identical shortlists
    s1 = generator.generate_slot_shortlist(slot_index=1, room_seed="SEED_ALPHA")
    s2 = generator.generate_slot_shortlist(slot_index=1, room_seed="SEED_ALPHA")

    assert s1.secret_player_ids == s2.secret_player_ids
    assert [c.candidate_token for c in s1.candidates] == [c.candidate_token for c in s2.candidates]
    assert [c.cost_usd for c in s1.candidates] == [c.cost_usd for c in s2.candidates]
    assert [c.hints for c in s1.candidates] == [c.hints for c in s2.candidates]


def test_hints_position_rules() -> None:
    # Test Midfielder rules (Assists compulsory)
    mock_player = {
        "age_at_reference": 27,
        "domestic_league_name": "La Liga",
        "goals": 5,
        "assists": 14,
        "clean_sheets": 6,
        "total_cards": 3,
        "ucl_goals": 2,
    }
    import random
    rng = random.Random(42)

    cm_hints = ShortlistGenerator._build_position_hints(mock_player, position="CM", rng=rng)
    assert len(cm_hints) == 3
    assert "Assists" in cm_hints
    assert cm_hints["Assists"] == 14

    # Test Defender rules (Clean sheets compulsory)
    cb_hints = ShortlistGenerator._build_position_hints(mock_player, position="CB", rng=rng)
    assert len(cb_hints) == 3
    assert "Clean Sheets" in cb_hints
    assert cb_hints["Clean Sheets"] == 6

    # Test Goalkeeper rules (Clean Sheets, Age, League)
    gk_hints = ShortlistGenerator._build_position_hints(mock_player, position="GK", rng=rng)
    assert len(gk_hints) == 3
    assert "Clean Sheets" in gk_hints
    assert "Age" in gk_hints
    assert "League" in gk_hints
