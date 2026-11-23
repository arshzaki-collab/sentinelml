"""Historical valuation observation selection and ECB currency conversion engine."""

import logging
from datetime import date
from typing import Final

import duckdb

from blindbillion.constants import ECB_EUR_USD_RATES, REFERENCE_DATES, VALUATION_MAX_AGE_DAYS
from blindbillion.data.models import HistoricalValuation, ProvenanceRecord

logger = logging.getLogger(__name__)

VALUATION_TABLE_NAME: Final[str] = "player_annual_valuations"


class ValuationEngine:
    """Computes authoritative historical player valuations aligned to July 1 reference dates."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con

    def build_annual_valuations_table(self, data_source: str) -> int:
        """Process raw valuations and materialize player_annual_valuations table.

        Enforces:
        1. Reference date: July 1 for each year 2016-2026.
        2. Maximum age: 180 days on or before reference date.
        3. Latest observation chosen if multiple exist.
        4. Currency conversion using verified ECB rates.
        5. Zero fabrication / zero silent interpolation.
        """
        years: list[int] = sorted(REFERENCE_DATES.keys())
        ref_dates: list[date] = [REFERENCE_DATES[y] for y in years]
        rates: list[float] = [ECB_EUR_USD_RATES[y] for y in years]

        logger.info(
            "Materializing %s for years %d-%d with max age %d days...",
            VALUATION_TABLE_NAME,
            years[0],
            years[-1],
            VALUATION_MAX_AGE_DAYS,
        )

        query = f"""
            CREATE OR REPLACE TABLE {VALUATION_TABLE_NAME} AS
            WITH reference_grid AS (
                SELECT
                    unnest(?::INTEGER[]) AS reference_year,
                    unnest(?::DATE[]) AS reference_date,
                    unnest(?::DOUBLE[]) AS exchange_rate
            ),
            candidate_observations AS (
                SELECT
                    CAST(pv.player_id AS VARCHAR) AS player_id,
                    rg.reference_year,
                    rg.reference_date,
                    CAST(pv.date AS DATE) AS observation_date,
                    DATE_DIFF(
                        'day', CAST(pv.date AS DATE), rg.reference_date
                    ) AS observation_age_days,
                    'EUR' AS original_currency,
                    CAST(pv.market_value_in_eur AS DOUBLE) AS original_value,
                    ROUND(
                        CAST(pv.market_value_in_eur AS DOUBLE) * rg.exchange_rate, 2
                    ) AS converted_usd_value,
                    rg.exchange_rate,
                    'European Central Bank' AS exchange_rate_source,
                    ? AS data_source,
                    current_timestamp AS import_timestamp,
                    ROW_NUMBER() OVER (
                        PARTITION BY pv.player_id, rg.reference_year
                        ORDER BY
                            CAST(pv.date AS DATE) DESC,
                            CAST(pv.market_value_in_eur AS DOUBLE) DESC
                    ) AS rank_order
                FROM raw_player_valuations pv
                JOIN reference_grid rg
                  ON CAST(pv.date AS DATE) <= rg.reference_date
                 AND CAST(pv.date AS DATE) >= (
                     rg.reference_date - INTERVAL '{VALUATION_MAX_AGE_DAYS} days'
                 )
                WHERE pv.market_value_in_eur IS NOT NULL
                  AND pv.market_value_in_eur > 0
            )
            SELECT
                player_id,
                reference_year,
                reference_date,
                observation_date,
                observation_age_days,
                original_currency,
                original_value,
                converted_usd_value,
                exchange_rate,
                exchange_rate_source,
                data_source,
                import_timestamp
            FROM candidate_observations
            WHERE rank_order = 1;
        """

        self.con.execute(query, [years, ref_dates, rates, data_source])

        # Create indexing for rapid game queries
        self.con.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_pav_player_year
            ON {VALUATION_TABLE_NAME} (player_id, reference_year);
        """)

        row_count_res = self.con.execute(f"SELECT COUNT(*) FROM {VALUATION_TABLE_NAME}").fetchone()
        row_count: int = row_count_res[0] if row_count_res else 0
        logger.info("Successfully populated %s with %d rows", VALUATION_TABLE_NAME, row_count)
        return row_count

    def get_player_valuation(self, player_id: str, year: int) -> HistoricalValuation | None:
        """Retrieve the exact valuation model for a player in a specific year, if eligible."""
        query = f"""
            SELECT
                player_id,
                reference_year,
                original_currency,
                original_value,
                converted_usd_value,
                observation_date,
                reference_date,
                observation_age_days,
                exchange_rate_source,
                exchange_rate,
                data_source,
                import_timestamp
            FROM {VALUATION_TABLE_NAME}
            WHERE player_id = ? AND reference_year = ?;
        """
        row = self.con.execute(query, [str(player_id), year]).fetchone()
        if not row:
            return None

        provenance = ProvenanceRecord(
            original_currency=row[2],
            original_value=row[3],
            converted_usd_value=row[4],
            valuation_date=row[5],
            reference_date=row[6],
            observation_age_days=row[7],
            exchange_rate_source=row[8],
            exchange_rate=row[9],
            data_source=row[10],
            import_timestamp=row[11],
        )

        return HistoricalValuation(
            player_id=row[0],
            reference_year=row[1],
            provenance=provenance,
        )

    def get_annual_valuation_counts(self) -> dict[int, int]:
        """Return the count of valid player valuations by year."""
        rows = self.con.execute(f"""
            SELECT reference_year, COUNT(*)
            FROM {VALUATION_TABLE_NAME}
            GROUP BY reference_year
            ORDER BY reference_year;
        """).fetchall()
        return {r[0]: r[1] for r in rows}
