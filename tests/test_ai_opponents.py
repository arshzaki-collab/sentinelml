"""Exhaustive tests for AI opponent difficulty levels and decision engines."""

from __future__ import annotations

import random
from collections.abc import Generator
from datetime import date
from pathlib import Path

import duckdb
import pytest

from blindbillion.ai.agent import AIAgent
from blindbillion.ai.evaluator import CandidateEvaluator
from blindbillion.ai.models import ActionType, AIDifficulty
from blindbillion.ai.temporal_guard import AIObservationContext, TemporalGuard
from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.data.models import ScoutingHints
from blindbillion.engine.engine import GameEngine
from blindbillion.engine.models import GamePhase


@pytest.fixture(scope="module")
def live_con() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    if not Path(DEFAULT_DB_PATH).exists():
        pytest.skip(f"Live database {DEFAULT_DB_PATH} not found; run pipeline first.")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    yield con
    con.close()


def test_ai_candidate_evaluator_differences() -> None:
    """Verify statistical, age curve, and solvency differences across Rookie, Pro, and Legend."""
    rng = random.Random(42)

    # Test with authentic Title-Case hints from production pipeline
    young_striker = ScoutingHints(
        candidate_token="TOKEN_YOUNG_ST",
        cost_usd=50_000_000.0,
        position="ST",
        hints={"Goals": 25, "Assists": 8, "Age": 21, "League": "premier-league"},
    )
    aging_striker = ScoutingHints(
        candidate_token="TOKEN_OLD_ST",
        cost_usd=50_000_000.0,
        position="ST",
        hints={"Goals": 25, "Assists": 8, "Age": 34, "League": "premier-league"},
    )

    mock_context = AIObservationContext(
        as_of_year=2016,
        as_of_date=date(2016, 7, 1),
        current_phase=GamePhase.BUYING_SEASON,
        cash_balance=1_000_000_000.0,
        slots=(),
    )

    # Rookie: ignores age factor
    rookie_young = CandidateEvaluator.score_candidate(
        young_striker, AIDifficulty.ROOKIE, mock_context, 7, rng
    )
    rookie_old = CandidateEvaluator.score_candidate(
        aging_striker, AIDifficulty.ROOKIE, mock_context, 7, rng
    )
    assert rookie_young.age_adjustment_factor == 1.0
    assert rookie_old.age_adjustment_factor == 1.0

    # Pro: recognizes age curve (21yo receives appreciation boost, 34yo receives decline penalty)
    pro_young = CandidateEvaluator.score_candidate(
        young_striker, AIDifficulty.PRO, mock_context, 7, rng
    )
    pro_old = CandidateEvaluator.score_candidate(
        aging_striker, AIDifficulty.PRO, mock_context, 7, rng
    )
    assert pro_young.age_adjustment_factor == 1.30
    assert pro_old.age_adjustment_factor == 0.60
    assert pro_young.final_score > pro_old.final_score
    assert pro_young.raw_performance_score == 120.0  # (25 * 4.0) + (8 * 2.5)

    # Legend: incorporates top-flight league multiplier and evaluates age
    legend_young = CandidateEvaluator.score_candidate(
        young_striker, AIDifficulty.LEGEND, mock_context, 7, rng
    )
    assert legend_young.final_score > 0
    assert legend_young.raw_performance_score == 120.0

    # Verify backward compatibility with lowercase keys
    lower_cand = ScoutingHints(
        candidate_token="TOKEN_LOWER",
        cost_usd=20_000_000.0,
        position="CM",
        hints={"assists": 10, "goals": 5, "cards": 2, "age": 24},
    )
    pro_lower = CandidateEvaluator.score_candidate(
        lower_cand, AIDifficulty.PRO, mock_context, 7, rng
    )
    assert pro_lower.raw_performance_score > 0.0
    assert pro_lower.age_adjustment_factor == 1.25


def test_ai_reproducibility_with_fixed_seed(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that an AI agent with a fixed seed makes 100% deterministic buying decisions."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="REPRO_TEST", room_seed="SEED_ALPHA")

    agent_1 = AIAgent(difficulty=AIDifficulty.PRO, seed=12345)
    agent_2 = AIAgent(difficulty=AIDifficulty.PRO, seed=12345)

    context = TemporalGuard.extract_buying_observation(state=state)
    d1 = agent_1.select_buying_candidate(context=context, unfilled_slots_count=7)
    d2 = agent_2.select_buying_candidate(context=context, unfilled_slots_count=7)

    assert d1.selected_candidate_token == d2.selected_candidate_token
    assert d1.action_type == ActionType.BUY
    assert len(d1.scores) == len(d2.scores)


def test_legend_capital_preservation_under_constrained_budget() -> None:
    """Verify Legend AI enforces capital reservation floor when cash is constrained."""
    rng = random.Random(100)

    # 5 slots remain unfilled. Legend reserved capital floor is (5 - 1) * $35M = $140M
    mock_context = AIObservationContext(
        as_of_year=2018,
        as_of_date=date(2018, 7, 1),
        current_phase=GamePhase.BUYING_SEASON,
        cash_balance=160_000_000.0,  # $160M cash
        slots=(),
    )

    expensive_candidate = ScoutingHints(
        candidate_token="TOKEN_EXPENSIVE",
        cost_usd=90_000_000.0,  # Leaves $70M (breaches $140M floor)
        position="CM",
        hints={"Assists": 15, "Goals": 8, "Age": 26, "League": "premier-league"},
    )
    prudent_candidate = ScoutingHints(
        candidate_token="TOKEN_PRUDENT",
        cost_usd=15_000_000.0,  # Leaves $145M (satisfies floor)
        position="CM",
        hints={"Assists": 12, "Goals": 6, "Age": 24, "League": "laliga"},
    )

    score_exp = CandidateEvaluator.score_candidate(
        expensive_candidate, AIDifficulty.LEGEND, mock_context, 5, rng
    )
    score_prud = CandidateEvaluator.score_candidate(
        prudent_candidate, AIDifficulty.LEGEND, mock_context, 5, rng
    )

    # Prudent candidate should be strongly preferred due to solvency penalty on expensive
    assert score_prud.final_score > score_exp.final_score


def test_ai_insufficient_funds_handling() -> None:
    """Verify AI handles edge case where cash balance cannot afford standard candidate."""
    # Balance has only $10M, but candidates cost $20M and $40M
    cand1 = ScoutingHints(
        candidate_token="TOK_1",
        cost_usd=20_000_000.0,
        position="ST",
        hints={"Goals": 10},
    )
    cand2 = ScoutingHints(
        candidate_token="TOK_2",
        cost_usd=40_000_000.0,
        position="ST",
        hints={"Goals": 20},
    )

    context = AIObservationContext(
        as_of_year=2016,
        as_of_date=date(2016, 7, 1),
        current_phase=GamePhase.BUYING_SEASON,
        cash_balance=10_000_000.0,
        slots=(),
        active_slot_index=1,
        candidates=(cand1, cand2),
    )

    agent = AIAgent(difficulty=AIDifficulty.PRO, seed=99)
    decision = agent.select_buying_candidate(context=context, unfilled_slots_count=7)

    # Insolvent fallback selects cheapest available
    assert decision.selected_candidate_token == "TOK_1"
    assert "Insolvent" in decision.reasoning


def test_transfer_window_multi_seed_crash_resilience(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Verify autoplay completes 100% crash-free across various random seeds (including seed 3)."""
    engine = GameEngine(con=live_con)

    # Test across seeds that exercise diverse transfer window replacement combinations
    for seed in (0, 1, 2, 3, 5, 10, 42):
        state = engine.initialize_game(game_id=f"RESILIENCE_{seed}", room_seed=f"ROOM_{seed}")
        agent = AIAgent(difficulty=AIDifficulty.ROOKIE, seed=seed)
        final_state = agent.autoplay_game(initial_state=state, engine=engine)
        assert final_state.is_completed
        assert final_state.current_year == 2026
        assert final_state.filled_slots_count == 7


@pytest.mark.parametrize("diff", [AIDifficulty.ROOKIE, AIDifficulty.PRO, AIDifficulty.LEGEND])
def test_full_game_autoplay_for_all_difficulties(
    live_con: duckdb.DuckDBPyConnection, diff: AIDifficulty
) -> None:
    """Verify all three AI difficulty levels can successfully complete a full 11-step game."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id=f"AUTOPLAY_{diff}", room_seed=f"ROOM_{diff}")

    agent = AIAgent(difficulty=diff, seed=42)
    final_state = agent.autoplay_game(initial_state=state, engine=engine)

    assert final_state.is_completed
    assert final_state.current_year == 2026
    assert final_state.current_phase == GamePhase.COMPLETED
    assert final_state.final_net_worth is not None
    assert final_state.final_squad_valuation is not None
    assert final_state.filled_slots_count == 7
    assert len(final_state.settlement_records) == 7
    assert final_state.cash_balance >= 0.0

    # Ensure transaction history contains 7 buys and 1 final settlement
    buy_txs = [tx for tx in final_state.transaction_history if tx.action == "BUY"]
    settle_txs = [tx for tx in final_state.transaction_history if tx.action == "FINAL_SETTLEMENT"]
    assert len(buy_txs) == 7
    assert len(settle_txs) == 1
