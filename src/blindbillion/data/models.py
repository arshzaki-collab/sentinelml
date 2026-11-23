"""Domain models and data schemas for Blind Billion 2.0."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceRecord(BaseModel):
    """Immutable audit trail for every valuation observation."""

    model_config = ConfigDict(frozen=True)

    original_currency: str = Field(default="EUR", description="Original currency code")
    original_value: float = Field(..., ge=0.0, description="Original valuation amount")
    converted_usd_value: float = Field(..., ge=0.0, description="Valuation converted to USD")
    valuation_date: date = Field(..., description="Actual observation date")
    reference_date: date = Field(..., description="Reference date (July 1)")
    observation_age_days: int = Field(..., ge=0, le=180, description="Age in days at reference")
    exchange_rate_source: str = Field(
        default="European Central Bank", description="Source of currency exchange rate"
    )
    exchange_rate: float = Field(..., gt=0.0, description="Exchange rate applied (EUR to USD)")
    data_source: str = Field(..., description="Origin dataset identifier or URI")
    import_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="UTC timestamp of import"
    )


class HistoricalValuation(BaseModel):
    """Player valuation record for a specific milestone year."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    reference_year: int
    provenance: ProvenanceRecord

    @property
    def value_usd(self) -> float:
        return self.provenance.converted_usd_value


class PlayerBio(BaseModel):
    """Player biographical and registration metadata."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    name: str
    date_of_birth: date | None = None
    position: str
    sub_position: str | None = None
    country_of_citizenship: str | None = None
    current_club_name: str | None = None
    image_url: str | None = None


class SeasonStats(BaseModel):
    """Trailing seasonal performance statistics preceding July 1."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    season_year: int  # e.g., 2016 represents the 2015-2016 season ending by 2016-07-01
    domestic_league_code: str | None = None
    domestic_league_name: str | None = None
    appearances: int = 0
    minutes_played: int = 0
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    clean_sheets: int = 0
    ucl_appearances: int = 0
    ucl_goals: int = 0
    age_at_reference: int | None = None

    @property
    def total_cards(self) -> int:
        return self.yellow_cards + self.red_cards


PositionType = Literal["ST", "WG", "CM", "CB", "GK"]


class ScoutingHints(BaseModel):
    """Anonymized scouting card payload sent to players."""

    model_config = ConfigDict(frozen=True)

    candidate_token: str  # Opaque UUID - hides player identity
    cost_usd: float
    position: PositionType
    hints: dict[str, str | int]  # Exactly 3 hints per game rules


class ShortlistSlot(BaseModel):
    """Server-side representation of a buying season's candidate pool."""

    model_config = ConfigDict(frozen=True)

    slot_index: int
    buying_year: int
    position: PositionType
    candidates: list[ScoutingHints]  # Exactly 4 candidates
    secret_player_ids: list[str] = Field(
        default_factory=list,
        description="Kept on server; index corresponds to candidates",
    )
