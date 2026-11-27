"""Unit tests for seasonal stats aggregation and clean sheet calculations."""

import duckdb

from blindbillion.data.stats import StatsAggregator


def test_stats_aggregator() -> None:
    con = duckdb.connect(":memory:")

    # Setup mock raw tables
    con.execute("""
        CREATE TABLE raw_players (
            player_id VARCHAR,
            name VARCHAR,
            position VARCHAR,
            sub_position VARCHAR,
            date_of_birth VARCHAR,
            current_club_domestic_competition_id VARCHAR
        );

        CREATE TABLE raw_appearances (
            player_id VARCHAR,
            game_id VARCHAR,
            date VARCHAR,
            competition_id VARCHAR,
            goals INTEGER,
            assists INTEGER,
            yellow_cards INTEGER,
            red_cards INTEGER,
            minutes_played INTEGER,
            player_club_id VARCHAR
        );

        CREATE TABLE raw_games (
            game_id VARCHAR,
            home_club_id VARCHAR,
            away_club_id VARCHAR,
            home_club_goals INTEGER,
            away_club_goals INTEGER
        );

        CREATE TABLE raw_competitions (
            competition_id VARCHAR,
            name VARCHAR
        );
    """)

    # Populate: Player 1 (Striker, born 1990-01-01 -> age 26 on 2016-07-01)
    # Populate: Player 2 (Defender, born 1992-01-01 -> age 24 on 2016-07-01)
    con.execute("""
        INSERT INTO raw_players VALUES
        ('P1', 'Test Striker', 'Attack', 'Centre-Forward', '1990-01-01', 'GB1'),
        ('P2', 'Test Defender', 'Defender', 'Centre-Back', '1992-01-01', 'GB1');

        INSERT INTO raw_competitions VALUES
        ('GB1', 'Premier League'),
        ('CL', 'UEFA Champions League');

        -- Match 1: Premier League game on 2015-10-10, Player club is Home (won 2-0 -> Clean sheet)
        INSERT INTO raw_games VALUES ('G1', 'CLUB_A', 'CLUB_B', 2, 0);
        INSERT INTO raw_appearances VALUES
        ('P1', 'G1', '2015-10-10', 'GB1', 1, 1, 0, 0, 90, 'CLUB_A'),
        ('P2', 'G1', '2015-10-10', 'GB1', 0, 0, 0, 0, 90, 'CLUB_A');

        -- Match 2: UCL game on 2016-03-15 (lost 1-2 -> conceded 2 goals, 1 UCL goal scored)
        INSERT INTO raw_games VALUES ('G2', 'CLUB_C', 'CLUB_A', 2, 1);
        INSERT INTO raw_appearances VALUES (
            'P1', 'G2', '2016-03-15', 'CL', 1, 0, 1, 0, 90, 'CLUB_A'
        );
    """)

    aggregator = StatsAggregator(con=con)
    aggregator.build_season_stats_table()

    res = con.execute("""
        SELECT
            player_id,
            season_year,
            player_name,
            age_at_reference,
            appearances,
            goals,
            assists,
            yellow_cards,
            clean_sheets,
            ucl_goals,
            ucl_appearances,
            domestic_league_name
        FROM player_season_stats
        WHERE player_id = 'P1' AND season_year = 2016;
    """).fetchone()

    assert res is not None
    assert res[0] == "P1"
    assert res[1] == 2016
    assert res[2] == "Test Striker"
    assert res[3] == 26  # Born Jan 1990 -> Age 26 on July 1, 2016
    assert res[4] == 2  # 2 appearances
    assert res[5] == 2  # 1 league + 1 UCL goal
    assert res[6] == 1  # 1 assist
    assert res[7] == 1  # 1 yellow card
    assert res[8] == 0  # 0 clean sheets (Striker position excluded from clean sheet credit)
    assert res[9] == 1  # 1 UCL goal
    assert res[10] == 1  # 1 UCL appearance
    assert res[11] == "Premier League"

    # Verify Defender P2 receives clean sheet credit
    res_p2 = con.execute("""
        SELECT clean_sheets FROM player_season_stats
        WHERE player_id = 'P2' AND season_year = 2016;
    """).fetchone()
    assert res_p2 is not None
    assert res_p2[0] == 1  # Defender credited with clean sheet
