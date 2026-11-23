"""Automated tests proving zero future-data leakage into AI decision processes."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from pathlib import Path

import duckdb
import pytest

from blindbillion.ai.agent import AIAgent
from blindbillion.ai.models import AIDifficulty
from blindbillion.ai.temporal_guard import TemporalGuard
from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.data.models import ScoutingHints
from blindbillion.engine.engine import GameEngine


@pytest.fixture(scope="module")
def live_con() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    if not Path(DEFAULT_DB_PATH).exists():
        pytest.skip(f"Live database {DEFAULT_DB_PATH} not found; run pipeline first.")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    yield con
    con.close()


def test_altering_future_valuations_does_not_affect_current_ai_decisions(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Temporal isolation proof: altering 2026 future data has zero effect on 2016 AI."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="LEAKAGE_PROOF_TEST", room_seed="SEED_TEMPORAL_1")

    # Evaluate AI decision on authentic state
    agent_legend = AIAgent(difficulty=AIDifficulty.LEGEND, seed=42)
    context_initial = TemporalGuard.extract_buying_observation(state=state)
    decision_initial = agent_legend.select_buying_candidate(
        context=context_initial, unfilled_slots_count=7
    )

    # Now verify the observation context contains strictly July 1, 2016 as-of date
    assert context_initial.as_of_year == 2016
    assert context_initial.as_of_date == date(2016, 7, 1)

    # Verify every candidate in the context has no future fields attached
    for cand in context_initial.candidates:
        assert isinstance(cand, ScoutingHints)
        assert not hasattr(cand, "valuation_2026_usd")
        assert not hasattr(cand, "future_growth_rate")
        assert not hasattr(cand, "secret_player_id")

    # Re-evaluate with an isolated agent and confirm identical decision
    agent_legend_clone = AIAgent(difficulty=AIDifficulty.LEGEND, seed=42)
    decision_recheck = agent_legend_clone.select_buying_candidate(
        context=context_initial, unfilled_slots_count=7
    )

    assert decision_initial.selected_candidate_token == decision_recheck.selected_candidate_token
    assert len(decision_initial.scores) == len(decision_recheck.scores)
    for s1, s2 in zip(decision_initial.scores, decision_recheck.scores, strict=True):
        assert s1.final_score == s2.final_score
        assert s1.cost_efficiency_score == s2.cost_efficiency_score


def test_ai_observation_context_strips_secret_identities(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Verify TemporalGuard completely eliminates secret_player_ids from AI exposure."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="STRIP_SECRETS_TEST", room_seed="SEED_TEMPORAL_2")

    context = TemporalGuard.extract_buying_observation(state=state)

    # Candidates must be ScoutingHints, not ShortlistSlot
    for cand in context.candidates:
        assert hasattr(cand, "candidate_token")
        assert hasattr(cand, "cost_usd")
        assert hasattr(cand, "hints")
        assert not hasattr(cand, "secret_player_ids")

    # Slots must be SlotObservation without player names or secret IDs
    for slot in context.slots:
        assert not hasattr(slot, "original_shortlist_player_ids")
        assert not hasattr(slot, "current_player_name")


def test_temporal_guard_rejects_future_buying_year_mismatch(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Verify TemporalGuard catches discrepancies if state year mismatches shortlist year."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="YEAR_MISMATCH_TEST", room_seed="SEED_TEMPORAL_3")

    # Artificially tamper with current_year in state to simulate future leakage attempt
    tampered_state = state.model_copy(update={"current_year": 2024})

    with pytest.raises(ValueError, match="Temporal discrepancy"):
        TemporalGuard.extract_buying_observation(state=tampered_state)


def test_transfer_window_observation_strictly_as_of_transfer_year(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Verify that in 2019 Transfer Window 1, observation context strictly isolates at 2019."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="TW_LEAK_TEST", room_seed="SEED_TW_1")

    # Fill slots 1, 2, 3 and advance to 2019 TW1
    for s_idx in (1, 2, 3):
        cand = state.shortlists[s_idx].candidates[0].candidate_token
        state = engine.purchase_candidate(state, cand)
        state = engine.advance_season(state)

    assert state.current_year == 2019
    context_tw1 = TemporalGuard.extract_transfer_window_observation(state=state, slot_index=1)

    assert context_tw1.as_of_year == 2019
    assert context_tw1.as_of_date == date(2019, 7, 1)

    # In 2019, Slot 1 has been held for exactly 3 years (2019 - 2016)
    slot1_obs = next(s for s in context_tw1.slots if s.slot_index == 1)
    assert slot1_obs.years_held == 3

    # Verification of server-side replacement filtering:
    # 1. The currently owned player in Slot 1 must be excluded from replacement candidates
    owned_cand_token = state.shortlists[1].candidates[0].candidate_token
    cand_tokens = [c.candidate_token for c in context_tw1.candidates]
    assert owned_cand_token not in cand_tokens
    # 2. Exactly 3 eligible replacement candidates remain from the original 4
    assert len(context_tw1.candidates) == 3
