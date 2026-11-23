"""Unit tests for the ValuationEngine, recency window, and currency conversion."""

from datetime import date

import duckdb

from blindbillion.constants import ECB_EUR_USD_RATES
from blindbillion.data.valuations import ValuationEngine


def test_valuation_engine_selection_and_conversion() -> None:
    con = duckdb.connect(":memory:")

    # Create dummy raw_player_valuations table
    con.execute("""
        CREATE TABLE raw_player_valuations (
            player_id VARCHAR,
            date VARCHAR,
            market_value_in_eur DOUBLE,
            current_club_id VARCHAR,
            player_club_domestic_competition_id VARCHAR
        );
    """)

    # Populate test cases:
    # Player 1: Valid observation on 2016-06-15 (16 days before July 1, 2016)
    # Player 2: Older observation on 2016-01-01 (182 days before July 1, 2016 -> EXCLUDED)
    # Player 3: Future observation on 2016-07-02 (after July 1, 2016 -> EXCLUDED for 2016)
    # Player 4: Observations on 2016-03-01 (50k) & 2016-06-01 (100k) -> picks 2016-06-01
    con.execute("""
        INSERT INTO raw_player_valuations VALUES
        ('P1', '2016-06-15', 10000000.0, 'C1', 'GB1'),
        ('P2', '2016-01-01', 5000000.0, 'C1', 'GB1'),
        ('P3', '2016-07-02', 8000000.0, 'C1', 'GB1'),
        ('P4', '2016-03-01', 50000.0, 'C1', 'GB1'),
        ('P4', '2016-06-01', 100000.0, 'C1', 'GB1');
    """)

    engine = ValuationEngine(con=con)
    engine.build_annual_valuations_table(data_source="test_source")

    # Verify P1
    val_p1 = engine.get_player_valuation("P1", 2016)
    assert val_p1 is not None
    assert val_p1.player_id == "P1"
    assert val_p1.reference_year == 2016
    assert val_p1.provenance.original_currency == "EUR"
    assert val_p1.provenance.original_value == 10000000.0
    expected_rate = ECB_EUR_USD_RATES[2016]
    expected_usd = round(10000000.0 * expected_rate, 2)
    assert val_p1.provenance.converted_usd_value == expected_usd
    assert val_p1.provenance.valuation_date == date(2016, 6, 15)
    assert val_p1.provenance.observation_age_days == 16
    assert val_p1.provenance.exchange_rate == expected_rate
    assert val_p1.provenance.data_source == "test_source"

    # Verify P2: Excluded because age > 180 days (no fabrication / interpolation)
    assert engine.get_player_valuation("P2", 2016) is None

    # Verify P3: Excluded because observation is in the future relative to July 1, 2016
    assert engine.get_player_valuation("P3", 2016) is None

    # Verify P4: Multiple observations -> strictly picks latest observation (2016-06-01)
    val_p4 = engine.get_player_valuation("P4", 2016)
    assert val_p4 is not None
    assert val_p4.provenance.original_value == 100000.0
    assert val_p4.provenance.valuation_date == date(2016, 6, 1)
