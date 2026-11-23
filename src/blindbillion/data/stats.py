"""Seasonal performance statistics and match analytics aggregator."""

import logging
from typing import Final

import duckdb

from blindbillion.constants import REFERENCE_DATES

logger = logging.getLogger(__name__)

STATS_TABLE_NAME: Final[str] = "player_season_stats"

POSITION_CATEGORY_MAP: Final[dict[str, tuple[str, ...]]] = {
    "ST": ("Centre-Forward", "Second Striker"),
    "WG": ("Left Winger", "Right Winger"),
    "CM": ("Central Midfield", "Defensive Midfield", "Attacking Midfield"),
    "CB": ("Centre-Back",),
    "GK": ("Goalkeeper",),
}


class StatsAggregator:
    """Aggregates player match appearances, goals, assists, clean sheets, and cards per season."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con

    def build_season_stats_table(self) -> int:
        """Aggregate match appearances and events for each 12-month season preceding July 1."""
        years = sorted(REFERENCE_DATES.keys())

        logger.info("Materializing %s for seasons preceding years %s...", STATS_TABLE_NAME, years)

        query = f"""
            CREATE OR REPLACE TABLE {STATS_TABLE_NAME} AS
            WITH season_intervals AS (
                SELECT
                    unnest(?::INTEGER[]) AS season_year,
                    unnest(?::DATE[]) AS end_date,
                    (unnest(?::DATE[]) - INTERVAL '365 days') AS start_date
            ),
            matched_appearances AS (
                SELECT
                    CAST(app.player_id AS VARCHAR) AS player_id,
                    si.season_year,
                    CAST(app.game_id AS VARCHAR) AS game_id,
                    CAST(app.date AS DATE) AS match_date,
                    app.competition_id,
                    COALESCE(app.goals, 0) AS goals,
                    COALESCE(app.assists, 0) AS assists,
                    COALESCE(app.yellow_cards, 0) AS yellow_cards,
                    COALESCE(app.red_cards, 0) AS red_cards,
                    COALESCE(app.minutes_played, 0) AS minutes_played,
                    app.player_club_id,
                    -- Clean sheet evaluation: opponent scored 0 goals in match
                    CASE
                        WHEN g.home_club_id IS NOT NULL AND (
                            (
                                app.player_club_id = g.home_club_id
                                AND COALESCE(g.away_club_goals, 1) = 0
                            ) OR (
                                app.player_club_id = g.away_club_id
                                AND COALESCE(g.home_club_goals, 1) = 0
                            )
                        ) THEN 1
                        ELSE 0
                    END AS is_clean_sheet,
                    CASE
                        WHEN app.competition_id IN ('CL', 'CLQ') THEN COALESCE(app.goals, 0)
                        ELSE 0
                    END AS ucl_goals,
                    CASE WHEN app.competition_id IN ('CL', 'CLQ') THEN 1 ELSE 0 END AS is_ucl_app
                FROM raw_appearances app
                JOIN season_intervals si
                  ON CAST(app.date AS DATE) >= si.start_date
                 AND CAST(app.date AS DATE) <= si.end_date
                LEFT JOIN raw_games g
                  ON CAST(app.game_id AS VARCHAR) = CAST(g.game_id AS VARCHAR)
            ),
            aggregated_stats AS (
                SELECT
                    player_id,
                    season_year,
                    COUNT(game_id) AS appearances,
                    SUM(minutes_played) AS minutes_played,
                    SUM(goals) AS goals,
                    SUM(assists) AS assists,
                    SUM(yellow_cards) AS yellow_cards,
                    SUM(red_cards) AS red_cards,
                    SUM(is_clean_sheet) AS clean_sheets,
                    SUM(is_ucl_app) AS ucl_appearances,
                    SUM(ucl_goals) AS ucl_goals
                FROM matched_appearances
                GROUP BY player_id, season_year
            )
            SELECT
                p.player_id,
                agg.season_year,
                p.name AS player_name,
                p.position AS broad_position,
                p.sub_position,
                p.date_of_birth,
                CASE
                    WHEN p.date_of_birth IS NOT NULL
                    THEN FLOOR(
                        DATE_DIFF('day', CAST(p.date_of_birth AS DATE), si.end_date) / 365.25
                    )::INTEGER
                    ELSE NULL
                END AS age_at_reference,
                p.current_club_domestic_competition_id AS domestic_league_code,
                comp.name AS domestic_league_name,
                COALESCE(agg.appearances, 0) AS appearances,
                COALESCE(agg.minutes_played, 0) AS minutes_played,
                COALESCE(agg.goals, 0) AS goals,
                COALESCE(agg.assists, 0) AS assists,
                COALESCE(agg.yellow_cards, 0) AS yellow_cards,
                COALESCE(agg.red_cards, 0) AS red_cards,
                COALESCE(agg.clean_sheets, 0) AS clean_sheets,
                COALESCE(agg.ucl_appearances, 0) AS ucl_appearances,
                COALESCE(agg.ucl_goals, 0) AS ucl_goals
            FROM (
                SELECT DISTINCT
                    CAST(player_id AS VARCHAR) AS player_id,
                    name,
                    position,
                    sub_position,
                    date_of_birth,
                    current_club_domestic_competition_id
                FROM raw_players
            ) p
            CROSS JOIN season_intervals si
            LEFT JOIN aggregated_stats agg
              ON p.player_id = agg.player_id AND si.season_year = agg.season_year
            LEFT JOIN raw_competitions comp
              ON p.current_club_domestic_competition_id = comp.competition_id
            WHERE agg.appearances > 0;
        """

        ref_dates = [REFERENCE_DATES[y] for y in years]
        self.con.execute(query, [years, ref_dates, ref_dates])

        self.con.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_pss_player_season
            ON {STATS_TABLE_NAME} (player_id, season_year);
        """)

        row_count_res = self.con.execute(f"SELECT COUNT(*) FROM {STATS_TABLE_NAME}").fetchone()
        row_count: int = row_count_res[0] if row_count_res else 0
        logger.info("Successfully populated %s with %d rows", STATS_TABLE_NAME, row_count)
        return row_count
