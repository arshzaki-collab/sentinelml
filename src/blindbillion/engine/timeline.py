"""Authoritative game timeline and step transitions for Blind Billion 2.0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from blindbillion.engine.exceptions import TimelineError
from blindbillion.engine.models import GamePhase


@dataclass(frozen=True)
class TimelineStep:
    """A discrete chronological milestone in the game session."""

    step_index: int
    year: int
    phase: GamePhase
    slot_index: int | None = None
    description: str = ""


GAME_TIMELINE_STEPS: Final[tuple[TimelineStep, ...]] = (
    TimelineStep(
        step_index=0,
        year=2016,
        phase=GamePhase.BUYING_SEASON,
        slot_index=1,
        description="2016 Buying Season: Sign Striker (Slot 1 - ST)",
    ),
    TimelineStep(
        step_index=1,
        year=2017,
        phase=GamePhase.BUYING_SEASON,
        slot_index=2,
        description="2017 Buying Season: Sign Winger (Slot 2 - WG)",
    ),
    TimelineStep(
        step_index=2,
        year=2018,
        phase=GamePhase.BUYING_SEASON,
        slot_index=3,
        description="2018 Buying Season: Sign Central Midfielder (Slot 3 - CM)",
    ),
    TimelineStep(
        step_index=3,
        year=2019,
        phase=GamePhase.TRANSFER_WINDOW,
        slot_index=None,
        description="2019 Transfer Window 1: Squad Rebalancing (Slots 1-3)",
    ),
    TimelineStep(
        step_index=4,
        year=2020,
        phase=GamePhase.BUYING_SEASON,
        slot_index=4,
        description="2020 Buying Season: Sign Centre-Back (Slot 4 - CB)",
    ),
    TimelineStep(
        step_index=5,
        year=2021,
        phase=GamePhase.BUYING_SEASON,
        slot_index=5,
        description="2021 Buying Season: Sign Central Midfielder (Slot 5 - CM)",
    ),
    TimelineStep(
        step_index=6,
        year=2022,
        phase=GamePhase.TRANSFER_WINDOW,
        slot_index=None,
        description="2022 Transfer Window 2: Squad Rebalancing (Slots 1-5)",
    ),
    TimelineStep(
        step_index=7,
        year=2023,
        phase=GamePhase.BUYING_SEASON,
        slot_index=6,
        description="2023 Buying Season: Sign Centre-Back (Slot 6 - CB)",
    ),
    TimelineStep(
        step_index=8,
        year=2024,
        phase=GamePhase.BUYING_SEASON,
        slot_index=7,
        description="2024 Buying Season: Sign Goalkeeper (Slot 7 - GK)",
    ),
    TimelineStep(
        step_index=9,
        year=2025,
        phase=GamePhase.TRANSFER_WINDOW,
        slot_index=None,
        description="2025 Transfer Window 3: Final Squad Adjustments (All 7 Slots)",
    ),
    TimelineStep(
        step_index=10,
        year=2026,
        phase=GamePhase.FINAL_SETTLEMENT,
        slot_index=None,
        description="2026 Final Settlement: Portfolio Revaluation & Scoring",
    ),
)


def get_timeline_step(step_index: int) -> TimelineStep:
    """Retrieve timeline step by index (0 to 10)."""
    if step_index < 0 or step_index >= len(GAME_TIMELINE_STEPS):
        max_idx = len(GAME_TIMELINE_STEPS) - 1
        raise TimelineError(
            f"Step index {step_index} out of bounds. Valid range is 0 to {max_idx}."
        )
    return GAME_TIMELINE_STEPS[step_index]


def find_step_index(year: int, phase: GamePhase) -> int:
    """Locate the timeline step index for a given year and phase."""
    for idx, step in enumerate(GAME_TIMELINE_STEPS):
        if step.year == year and step.phase == phase:
            return idx
    raise TimelineError(f"No timeline step matching year={year}, phase={phase}")
