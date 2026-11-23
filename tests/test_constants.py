"""Unit tests for foundational game constants and rules in Blind Billion 2.0."""

from datetime import date

from blindbillion.constants import (
    CANDIDATES_PER_SLOT,
    CORE_TABLE_FILES,
    ECB_EUR_USD_RATES,
    EUROPEAN_TOP_FLIGHT_LEAGUES,
    REFERENCE_DATES,
    SQUAD_SLOTS,
    STARTING_BUDGET_USD,
    TRANSFER_WINDOWS,
    UEFA_COMPETITIONS,
    VALUATION_MAX_AGE_DAYS,
)


def test_starting_budget() -> None:
    """Verify starting capital is exactly $1,000,000,000 USD."""
    assert STARTING_BUDGET_USD == 1_000_000_000


def test_valuation_recency_window() -> None:
    """Verify maximum valuation age is strictly 180 days."""
    assert VALUATION_MAX_AGE_DAYS == 180


def test_candidates_per_slot() -> None:
    """Verify exactly 4 anonymous options per buying season."""
    assert CANDIDATES_PER_SLOT == 4


def test_transfer_windows() -> None:
    """Verify exactly 3 transfer windows exist: 2019, 2022, 2025."""
    assert len(TRANSFER_WINDOWS) == 3
    assert TRANSFER_WINDOWS == (2019, 2022, 2025)


def test_squad_slots_rules() -> None:
    """Verify exactly 7 squad positions are enforced with correct timeline and positions."""
    assert len(SQUAD_SLOTS) == 7

    expected = [
        (1, 2016, "ST"),
        (2, 2017, "WG"),
        (3, 2018, "CM"),
        (4, 2020, "CB"),
        (5, 2021, "CM"),
        (6, 2023, "CB"),
        (7, 2024, "GK"),
    ]

    for slot, (idx, yr, pos) in zip(SQUAD_SLOTS, expected, strict=True):
        assert slot["slot_index"] == idx
        assert slot["year"] == yr
        assert slot["position"] == pos


def test_reference_dates() -> None:
    """Verify reference dates run from July 1, 2016 through July 1, 2026."""
    assert len(REFERENCE_DATES) == 11
    for year in range(2016, 2027):
        assert year in REFERENCE_DATES
        assert REFERENCE_DATES[year] == date(year, 7, 1)


def test_ecb_exchange_rates() -> None:
    """Verify all 11 years have verified positive ECB EUR/USD exchange rates."""
    assert len(ECB_EUR_USD_RATES) == 11
    for year in range(2016, 2027):
        assert year in ECB_EUR_USD_RATES
        rate = ECB_EUR_USD_RATES[year]
        assert isinstance(rate, float)
        assert 0.9 < rate < 1.4  # Historical EUR/USD sanity boundary


def test_core_tables_and_competitions() -> None:
    """Verify dataset table mappings and league codes."""
    assert "players" in CORE_TABLE_FILES
    assert "player_valuations" in CORE_TABLE_FILES
    assert "appearances" in CORE_TABLE_FILES
    assert "games" in CORE_TABLE_FILES
    assert "club_games" in CORE_TABLE_FILES
    assert "competitions" in CORE_TABLE_FILES

    assert "GB1" in EUROPEAN_TOP_FLIGHT_LEAGUES
    assert "ES1" in EUROPEAN_TOP_FLIGHT_LEAGUES
    assert "CL" in UEFA_COMPETITIONS
