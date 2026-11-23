"""Temporal isolation guard preventing future data leakage into AI decision processes."""

from __future__ import annotations

from datetime import date
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from blindbillion.constants import REFERENCE_DATES
from blindbillion.data.models import PositionType, ScoutingHints
from blindbillion.engine.models import GamePhase, GameState, PlayerSlot


class SlotObservation(BaseModel):
    """Anonymized, temporally safe view of a squad slot as of current game year."""

    model_config = ConfigDict(frozen=True)

    slot_index: int
    required_position: PositionType
    buying_year: int
    is_filled: bool
    purchase_price_usd: float | None = None
    purchase_year: int | None = None
    years_held: int = 0


class AIObservationContext(BaseModel):
    """Immutable, temporal-walled observation payload available to an AI decision engine."""

    model_config = ConfigDict(frozen=True)

    as_of_year: int
    as_of_date: date
    current_phase: GamePhase
    cash_balance: float = Field(..., ge=0.0)
    slots: tuple[SlotObservation, ...]
    active_slot_index: int | None = None
    candidates: tuple[ScoutingHints, ...] = Field(default_factory=tuple)


class TemporalGuard:
    """Enforces mathematical temporal isolation barrier t <= T_current."""

    @staticmethod
    def _build_slot_observations(
        slots: tuple[PlayerSlot, ...], as_of_year: int
    ) -> tuple[SlotObservation, ...]:
        """Construct sanitized, client-safe slot summaries without player identities."""
        return tuple(
            SlotObservation(
                slot_index=s.slot_index,
                required_position=s.required_position,
                buying_year=s.buying_year,
                is_filled=s.is_filled,
                purchase_price_usd=s.purchase_price_usd,
                purchase_year=s.purchase_year,
                years_held=(as_of_year - s.purchase_year)
                if (s.is_filled and s.purchase_year)
                else 0,
            )
            for s in slots
        )

    @staticmethod
    def extract_buying_observation(state: GameState) -> AIObservationContext:
        """Construct an observation context for a buying season strictly isolated at T_current."""
        as_of_year = state.current_year
        as_of_date: Final[date] = REFERENCE_DATES[as_of_year]

        if state.current_slot_index is None:
            raise ValueError("Cannot extract buying observation without an active slot index.")

        slot_idx = state.current_slot_index
        shortlist = state.shortlists[slot_idx]

        # Verify buying year matches current year
        if shortlist.buying_year != as_of_year:
            raise ValueError(
                f"Temporal discrepancy: shortlist buying year {shortlist.buying_year} "
                f"does not match current year {as_of_year}."
            )

        slot_obs = TemporalGuard._build_slot_observations(state.slots, as_of_year)

        return AIObservationContext(
            as_of_year=as_of_year,
            as_of_date=as_of_date,
            current_phase=state.current_phase,
            cash_balance=state.cash_balance,
            slots=slot_obs,
            active_slot_index=slot_idx,
            candidates=tuple(shortlist.candidates),
        )

    @staticmethod
    def extract_transfer_window_observation(
        state: GameState, slot_index: int
    ) -> AIObservationContext:
        """Construct an observation context for transfer window evaluation on a specific slot."""
        as_of_year = state.current_year
        as_of_date: Final[date] = REFERENCE_DATES[as_of_year]

        slot = state.slots[slot_index - 1]
        shortlist = state.shortlists[slot_index]

        # Server-authoritatively filter replacement candidates:
        # Exclude currently owned, previously sold, and players owned in squad.
        available_cands: list[ScoutingHints] = []
        for idx, cand in enumerate(shortlist.candidates):
            secret_id = shortlist.secret_player_ids[idx]
            if (
                secret_id != slot.current_player_id
                and secret_id not in slot.previous_player_ids
                and secret_id not in state.owned_player_ids
            ):
                available_cands.append(cand)

        slot_obs = TemporalGuard._build_slot_observations(state.slots, as_of_year)

        return AIObservationContext(
            as_of_year=as_of_year,
            as_of_date=as_of_date,
            current_phase=state.current_phase,
            cash_balance=state.cash_balance,
            slots=slot_obs,
            active_slot_index=slot_index,
            candidates=tuple(available_cands),
        )
