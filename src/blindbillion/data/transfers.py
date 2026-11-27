"""Historical transfer records and fee processing engine."""

import logging
from typing import Final

import duckdb

from blindbillion.constants import ECB_EUR_USD_RATES

logger = logging.getLogger(__name__)

TRANSFERS_TABLE_NAME: Final[str] = "player_transfer_history"


class TransferEngine:
    """Manages raw transfer records and builds normalized player_transfer_history table."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con

    def build_transfer_history_table(self, data_source: str) -> int:
        """Process raw transfers and materialize player_transfer_history table.

        Enforces:
        1. Clean separation between actual transfer fees and market valuations.
        2. Currency conversion using verified ECB reference rates.
        3. Clear identification of paid transfers vs free/loan transfers.
        4. Data provenance tracking.
        """
        logger.info("Materializing %s from raw_transfers...", TRANSFERS_TABLE_NAME)

        # Check if raw_transfers table exists
        exists = self.con.execute("""
            SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'raw_transfers'
        """).fetchone()
        if not exists or exists[0] == 0:
            logger.warning(
                "raw_transfers table does not exist. Creating empty %s table.",
                TRANSFERS_TABLE_NAME,
            )
            self.con.execute(f"""
                CREATE TABLE IF NOT EXISTS {TRANSFERS_TABLE_NAME} (
                    player_id VARCHAR,
                    player_name VARCHAR,
                    transfer_date DATE,
                    transfer_year INTEGER,
                    transfer_season VARCHAR,
                    from_club_id VARCHAR,
                    from_club_name VARCHAR,
                    to_club_id VARCHAR,
                    to_club_name VARCHAR,
                    actual_transfer_fee_eur DOUBLE,
                    actual_transfer_fee_usd DOUBLE,
                    market_value_at_transfer_eur DOUBLE,
                    market_value_at_transfer_usd DOUBLE,
                    is_paid_transfer BOOLEAN,
                    fee_to_valuation_ratio DOUBLE,
                    data_source VARCHAR
                )
            """)
            return 0

        # Build mapping for ECB exchange rates by year
        years = sorted(ECB_EUR_USD_RATES.keys())
        rates = [ECB_EUR_USD_RATES[y] for y in years]

        query = f"""
            CREATE OR REPLACE TABLE {TRANSFERS_TABLE_NAME} AS
            WITH ecb_rates AS (
                SELECT
                    unnest(?::INTEGER[]) AS rate_year,
                    unnest(?::DOUBLE[]) AS exchange_rate
            ),
            cleaned_transfers AS (
                SELECT
                    CAST(t.player_id AS VARCHAR) AS player_id,
                    p.name AS player_name,
                    CAST(t.transfer_date AS DATE) AS transfer_date,
                    YEAR(CAST(t.transfer_date AS DATE)) AS transfer_year,
                    t.transfer_season,
                    CAST(t.from_club_id AS VARCHAR) AS from_club_id,
                    t.from_club_name,
                    CAST(t.to_club_id AS VARCHAR) AS to_club_id,
                    t.to_club_name,
                    -- Actual transfer fee in EUR (NULL if 0 or unknown)
                    CASE
                        WHEN t.transfer_fee IS NOT NULL AND t.transfer_fee > 0
                        THEN CAST(t.transfer_fee AS DOUBLE)
                        ELSE NULL
                    END AS actual_transfer_fee_eur,
                    -- Market value in EUR at time of transfer
                    CASE
                        WHEN t.market_value_in_eur IS NOT NULL AND t.market_value_in_eur > 0
                        THEN CAST(t.market_value_in_eur AS DOUBLE)
                        ELSE NULL
                    END AS market_value_at_transfer_eur,
                    CASE
                        WHEN t.transfer_fee IS NOT NULL AND t.transfer_fee > 0 THEN TRUE
                        ELSE FALSE
                    END AS is_paid_transfer,
                    CASE
                        WHEN t.transfer_fee IS NULL OR t.transfer_fee = 0 THEN TRUE
                        ELSE FALSE
                    END AS is_free_transfer,
                    COALESCE(r.exchange_rate, 1.1104) AS exchange_rate,
                    ? AS data_source,
                    current_timestamp AS import_timestamp
                FROM raw_transfers t
                LEFT JOIN raw_players p
                  ON CAST(t.player_id AS VARCHAR) = CAST(p.player_id AS VARCHAR)
                LEFT JOIN ecb_rates r
                  ON YEAR(CAST(t.transfer_date AS DATE)) = r.rate_year
                WHERE t.transfer_date IS NOT NULL
            )
            SELECT
                player_id,
                player_name,
                transfer_date,
                transfer_year,
                transfer_season,
                from_club_id,
                from_club_name,
                to_club_id,
                to_club_name,
                actual_transfer_fee_eur,
                CASE
                    WHEN actual_transfer_fee_eur IS NOT NULL
                    THEN ROUND(actual_transfer_fee_eur * exchange_rate, 2)
                    ELSE NULL
                END AS actual_transfer_fee_usd,
                market_value_at_transfer_eur,
                CASE
                    WHEN market_value_at_transfer_eur IS NOT NULL
                    THEN ROUND(market_value_at_transfer_eur * exchange_rate, 2)
                    ELSE NULL
                END AS market_value_at_transfer_usd,
                is_paid_transfer,
                is_free_transfer,
                CASE
                    WHEN actual_transfer_fee_eur IS NOT NULL
                     AND market_value_at_transfer_eur IS NOT NULL
                     AND market_value_at_transfer_eur > 0
                    THEN ROUND(actual_transfer_fee_eur / market_value_at_transfer_eur, 4)
                    ELSE NULL
                END AS fee_to_valuation_ratio,
                data_source,
                import_timestamp
            FROM cleaned_transfers
            ORDER BY transfer_date DESC, player_id ASC;
        """

        self.con.execute(query, [years, rates, data_source])

        # Create indexes
        self.con.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_pth_player_date
            ON {TRANSFERS_TABLE_NAME} (player_id, transfer_date);
        """)

        count_res = self.con.execute(f"SELECT COUNT(*) FROM {TRANSFERS_TABLE_NAME}").fetchone()
        row_count: int = count_res[0] if count_res else 0
        logger.info("Successfully populated %s with %d rows", TRANSFERS_TABLE_NAME, row_count)
        return row_count
