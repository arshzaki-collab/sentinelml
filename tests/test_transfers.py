"""Unit tests for TransferEngine and player transfer history materialization."""

from pathlib import Path

import duckdb
import pytest

from blindbillion.constants import ECB_EUR_USD_RATES
from blindbillion.data.transfers import TRANSFERS_TABLE_NAME, TransferEngine


def setup_mock_transfers_db() -> duckdb.DuckDBPyConnection:
    """Create in-memory DuckDB with raw_players and raw_transfers tables."""
    con = duckdb.connect(":memory:")

    con.execute("""
        CREATE TABLE raw_players (
            player_id VARCHAR,
            name VARCHAR,
            position VARCHAR,
            sub_position VARCHAR,
            date_of_birth VARCHAR,
            current_club_domestic_competition_id VARCHAR
        );

        CREATE TABLE raw_transfers (
            player_id VARCHAR,
            transfer_date VARCHAR,
            transfer_season VARCHAR,
            from_club_id VARCHAR,
            from_club_name VARCHAR,
            to_club_id VARCHAR,
            to_club_name VARCHAR,
            transfer_fee DOUBLE,
            market_value_in_eur DOUBLE
        );
    """)

    con.execute("""
        INSERT INTO raw_players VALUES
        ('P1', 'Neymar Jr', 'Attack', 'Left Winger', '1992-02-05', 'FR1'),
        ('P2', 'Kylian Mbappé', 'Attack', 'Centre-Forward', '1998-12-20', 'ES1'),
        ('P3', 'Free Agent Star', 'Midfield', 'Central Midfield', '1995-01-01', 'GB1');

        INSERT INTO raw_transfers VALUES
        (
            'P1', '2017-08-03', '17/18', '131', 'FC Barcelona',
            '583', 'Paris Saint-Germain', 222000000.0, 100000000.0
        ),
        (
            'P2', '2018-07-01', '18/19', '162', 'AS Monaco',
            '583', 'Paris Saint-Germain', 180000000.0, 120000000.0
        ),
        ('P3', '2021-07-01', '21/22', '100', 'Old Club', '200', 'New Club', 0.0, 45000000.0);
    """)

    return con


def test_transfer_engine_build_table() -> None:
    con = setup_mock_transfers_db()
    engine = TransferEngine(con=con)
    count = engine.build_transfer_history_table(data_source="test_provenance")

    assert count == 3

    # Verify schema and columns
    cols = [col[0] for col in con.execute(f"DESCRIBE {TRANSFERS_TABLE_NAME}").fetchall()]
    assert "player_id" in cols
    assert "actual_transfer_fee_eur" in cols
    assert "actual_transfer_fee_usd" in cols
    assert "market_value_at_transfer_eur" in cols
    assert "market_value_at_transfer_usd" in cols
    assert "is_paid_transfer" in cols
    assert "fee_to_valuation_ratio" in cols


def test_transfer_fee_separation_and_currency_conversion() -> None:
    con = setup_mock_transfers_db()
    engine = TransferEngine(con=con)
    engine.build_transfer_history_table(data_source="test_provenance")

    # Record 1: Neymar record fee in 2017 (ECB rate = 1.137)
    neymar = con.execute(f"""
        SELECT
            actual_transfer_fee_eur,
            actual_transfer_fee_usd,
            market_value_at_transfer_eur,
            market_value_at_transfer_usd,
            is_paid_transfer,
            fee_to_valuation_ratio
        FROM {TRANSFERS_TABLE_NAME}
        WHERE player_id = 'P1';
    """).fetchone()

    assert neymar is not None
    assert neymar[0] == 222_000_000.0
    expected_usd_2017 = round(222_000_000.0 * ECB_EUR_USD_RATES[2017], 2)
    assert abs(neymar[1] - expected_usd_2017) < 0.01
    assert neymar[2] == 100_000_000.0
    expected_mv_usd_2017 = round(100_000_000.0 * ECB_EUR_USD_RATES[2017], 2)
    assert abs(neymar[3] - expected_mv_usd_2017) < 0.01
    assert neymar[4] is True
    assert round(neymar[5], 2) == 2.22

    # Record 3: Free transfer (Fee = 0)
    free_agent = con.execute(f"""
        SELECT
            actual_transfer_fee_eur,
            actual_transfer_fee_usd,
            market_value_at_transfer_eur,
            is_paid_transfer,
            fee_to_valuation_ratio
        FROM {TRANSFERS_TABLE_NAME}
        WHERE player_id = 'P3';
    """).fetchone()

    assert free_agent is not None
    assert free_agent[0] is None
    assert free_agent[1] is None
    assert free_agent[2] == 45_000_000.0
    assert free_agent[3] is False
    assert free_agent[4] is None


def test_missing_raw_transfers_table_graceful_handling() -> None:
    """Ensure engine does not crash if raw_transfers is missing."""
    con = duckdb.connect(":memory:")
    engine = TransferEngine(con=con)
    count = engine.build_transfer_history_table(data_source="empty_source")
    assert count == 0

    exists = con.execute(f"""
        SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{TRANSFERS_TABLE_NAME}'
    """).fetchone()
    assert exists is not None
    assert exists[0] == 1


def test_live_database_transfer_records() -> None:
    """Verify live database has actual historical transfers populated."""
    db_file = Path("data/blindbillion.duckdb")
    if not db_file.exists():
        pytest.skip("Live database not found.")

    con = duckdb.connect(str(db_file), read_only=True)
    count = con.execute(f"SELECT COUNT(*) FROM {TRANSFERS_TABLE_NAME}").fetchone()
    assert count is not None
    assert count[0] > 100_000

    # Verify Neymar's world record transfer exists
    neymar = con.execute(f"""
        SELECT player_name, transfer_year, actual_transfer_fee_eur, actual_transfer_fee_usd
        FROM {TRANSFERS_TABLE_NAME}
        WHERE player_id = '68290' AND transfer_year = 2017;
    """).fetchone()
    assert neymar is not None
    assert neymar[2] == 222_000_000.0
    expected_usd = round(222_000_000.0 * ECB_EUR_USD_RATES[2017], 2)
    assert abs(neymar[3] - expected_usd) < 0.01
