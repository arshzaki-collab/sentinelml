"""Exhaustive automated tests for the server-authoritative Blind Billion 2.0 game engine."""

from collections.abc import Generator
from pathlib import Path

import duckdb
import pytest

from blindbillion.constants import (
    CANDIDATES_PER_SLOT,
    STARTING_BUDGET_USD,
)
from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.engine.engine import GameEngine
from blindbillion.engine.exceptions import (
    DuplicatePlayerError,
    InsufficientFundsError,
    InvalidGameActionError,
    InvalidPhaseError,
    InvalidReplacementCandidateError,
    InvalidSlotError,
    SlotAlreadyFilledError,
    TimelineError,
    TransferNotAllowedError,
)
from blindbillion.engine.models import GamePhase
from blindbillion.engine.timeline import find_step_index, get_timeline_step


@pytest.fixture(scope="module")
def live_con() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    if not Path(DEFAULT_DB_PATH).exists():
        pytest.skip(f"Live database {DEFAULT_DB_PATH} not found; run pipeline first.")
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    yield con
    con.close()


def test_initial_budget_and_squad_structure(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify initial game state: exactly $1B, 7 unfilled slots, correct positions and timeline."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="GAME_INIT_TEST", room_seed="SEED_123")

    assert state.cash_balance == float(STARTING_BUDGET_USD)
    assert state.cash_balance == 1_000_000_000.0
    assert len(state.slots) == 7
    assert state.filled_slots_count == 0
    assert not state.is_completed

    # Validate slot configurations against game specification
    expected_slots = [
        (1, "ST", 2016),
        (2, "WG", 2017),
        (3, "CM", 2018),
        (4, "CB", 2020),
        (5, "CM", 2021),
        (6, "CB", 2023),
        (7, "GK", 2024),
    ]

    for slot, (idx, pos, yr) in zip(state.slots, expected_slots, strict=True):
        assert slot.slot_index == idx
        assert slot.required_position == pos
        assert slot.buying_year == yr
        assert slot.current_player_id is None
        assert not slot.is_filled
        assert len(slot.original_shortlist_player_ids) == CANDIDATES_PER_SLOT


def test_exactly_four_candidates_per_slot(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that every slot has an authoritative shortlist with exactly 4 distinct candidates."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="SHORTLIST_TEST", room_seed="TEST_SEED_456")

    assert len(state.shortlists) == 7
    for slot_idx in range(1, 8):
        shortlist = state.shortlists[slot_idx]
        assert len(shortlist.candidates) == 4
        assert len(shortlist.secret_player_ids) == 4
        # Verify no duplicate player IDs within the shortlist
        assert len(set(shortlist.secret_player_ids)) == 4


def test_valid_purchase_and_balance_deduction(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify purchasing a candidate for Slot 1 correctly updates balance and slot."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="BUY_TEST", room_seed="ROOM_ALPHA")

    shortlist_1 = state.shortlists[1]
    candidate = shortlist_1.candidates[0]
    expected_cost = candidate.cost_usd
    expected_secret_id = shortlist_1.secret_player_ids[0]

    updated_state = engine.purchase_candidate(
        state, candidate_token_or_id=candidate.candidate_token
    )

    # Balance must be exactly debited
    assert updated_state.cash_balance == round(STARTING_BUDGET_USD - expected_cost, 2)
    assert updated_state.filled_slots_count == 1
    assert updated_state.state_version == state.state_version + 1

    slot_1 = updated_state.slots[0]
    assert slot_1.is_filled
    assert slot_1.current_player_id == expected_secret_id
    assert slot_1.purchase_price_usd == expected_cost
    assert slot_1.purchase_year == 2016

    # Verify transaction record
    assert len(updated_state.transaction_history) == 1
    tx = updated_state.transaction_history[0]
    assert tx.action == "BUY"
    assert tx.amount_usd == -expected_cost
    assert tx.slot_index == 1
    assert tx.player_id == expected_secret_id
    assert tx.provenance is not None


def test_slot_already_filled_rejection(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify purchasing when a slot is already occupied is rejected."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="DOUBLE_BUY_TEST", room_seed="ROOM_ALPHA")

    shortlist = state.shortlists[1]
    state_after_first = engine.purchase_candidate(state, shortlist.candidates[0].candidate_token)

    # Second purchase attempt on the same slot must raise SlotAlreadyFilledError
    with pytest.raises(SlotAlreadyFilledError, match="already occupied"):
        engine.purchase_candidate(state_after_first, shortlist.candidates[1].candidate_token)


def test_invalid_candidate_token_rejection(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify purchasing a candidate token not in current slot shortlist is rejected."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="INVALID_TOKEN_TEST", room_seed="ROOM_ALPHA")

    with pytest.raises(InvalidGameActionError, match="not in shortlist"):
        engine.purchase_candidate(state, candidate_token_or_id="NON_EXISTENT_TOKEN_123")


def test_insufficient_funds_rejection(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify purchasing when balance is insufficient is rejected and preserves state."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="INSUFFICIENT_FUNDS_TEST", room_seed="ROOM_ALPHA")

    # Manually drain balance to $1.00 to trigger insolvency check
    broke_state = state.model_copy(update={"cash_balance": 1.00})
    candidate = state.shortlists[1].candidates[0]

    with pytest.raises(InsufficientFundsError, match="Insufficient funds"):
        engine.purchase_candidate(broke_state, candidate_token_or_id=candidate.candidate_token)


def test_buying_sequence_advance_enforcement(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that advancing the season without purchasing the required player is blocked."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="ADVANCE_EMPTY_TEST", room_seed="ROOM_ALPHA")

    # Slot 1 is empty; advancing must fail
    with pytest.raises(InvalidGameActionError, match="Must purchase a candidate for Slot 1"):
        engine.advance_season(state)

    # After filling Slot 1, advancing succeeds to 2017 (Slot 2)
    state_filled = engine.purchase_candidate(
        state, state.shortlists[1].candidates[0].candidate_token
    )
    state_advanced = engine.advance_season(state_filled)

    assert state_advanced.current_year == 2017
    assert state_advanced.current_phase == GamePhase.BUYING_SEASON
    assert state_advanced.current_slot_index == 2


def test_transfer_window_rules_and_rejection_outside_windows(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Verify transfer actions (sell/replace) are rejected outside transfer windows."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="TW_REJECT_TEST", room_seed="ROOM_ALPHA")

    # Slot 1 buying season: sell/replace is prohibited
    state_filled = engine.purchase_candidate(
        state, state.shortlists[1].candidates[0].candidate_token
    )

    with pytest.raises(
        TransferNotAllowedError, match="only permitted during scheduled transfer windows"
    ):
        engine.sell_player(state_filled, slot_index=1)

    with pytest.raises(
        TransferNotAllowedError, match="only permitted during scheduled transfer windows"
    ):
        engine.replace_player(state_filled, slot_index=1, replacement_candidate_token_or_id="DUMMY")


def test_transfer_window_sell_and_replace_from_original_shortlist(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Verify selling in 2019 credits valuation, and replacement must come from shortlist."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="TW_EXEC_TEST", room_seed="ROOM_ALPHA")

    # Complete 2016 (Slot 1 ST), 2017 (Slot 2 WG), 2018 (Slot 3 CM)
    s1 = engine.purchase_candidate(state, state.shortlists[1].candidates[0].candidate_token)
    s1_adv = engine.advance_season(s1)

    s2 = engine.purchase_candidate(s1_adv, s1_adv.shortlists[2].candidates[0].candidate_token)
    s2_adv = engine.advance_season(s2)

    s3 = engine.purchase_candidate(s2_adv, s2_adv.shortlists[3].candidates[0].candidate_token)
    # Advance to 2019 Transfer Window 1!
    tw1_state = engine.advance_season(s3)

    assert tw1_state.current_year == 2019
    assert tw1_state.current_phase == GamePhase.TRANSFER_WINDOW
    assert tw1_state.current_slot_index is None

    # Test Sell Player from Slot 1 in 2019
    balance_before_sale = tw1_state.cash_balance
    sold_state = engine.sell_player(tw1_state, slot_index=1)

    # Cash balance must have increased by the player's 2019 valuation
    assert sold_state.cash_balance > balance_before_sale
    assert not sold_state.slots[0].is_filled
    assert sold_state.slots[0].current_player_id is None

    # Replacement candidate must come from original 4-player shortlist for Slot 1
    shortlist_1 = tw1_state.shortlists[1]
    sold_candidate_token = shortlist_1.candidates[0].candidate_token
    valid_replacement_candidate = shortlist_1.candidates[1]
    invalid_candidate_from_slot_2 = tw1_state.shortlists[2].candidates[0]

    # Test: replacement from another slot must fail
    with pytest.raises(InvalidReplacementCandidateError, match="not in the original shortlist"):
        engine.replace_player(
            sold_state,
            slot_index=1,
            replacement_candidate_token=invalid_candidate_from_slot_2.candidate_token,
        )

    # Test: re-signing the exact player that was just sold must fail
    with pytest.raises(InvalidGameActionError, match="previously owned and sold"):
        engine.replace_player(
            sold_state,
            slot_index=1,
            replacement_candidate_token=sold_candidate_token,
        )

    # Test: valid replacement from original shortlist succeeds
    replaced_state = engine.replace_player(
        sold_state,
        slot_index=1,
        replacement_candidate_token=valid_replacement_candidate.candidate_token,
    )

    assert replaced_state.slots[0].is_filled
    assert replaced_state.slots[0].current_player_id == shortlist_1.secret_player_ids[1]


def test_complete_game_playthrough_and_2026_settlement(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Execute a complete 10-year historical game session from 2016 to 2026 final valuation."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="FULL_PLAYTHROUGH", room_seed="CHAMPION_SEED")

    # Step 0: 2016 (Slot 1 ST)
    assert state.current_year == 2016 and state.current_slot_index == 1
    state = engine.purchase_candidate(state, state.shortlists[1].candidates[0].candidate_token)
    state = engine.advance_season(state)

    # Step 1: 2017 (Slot 2 WG)
    assert state.current_year == 2017 and state.current_slot_index == 2
    state = engine.purchase_candidate(state, state.shortlists[2].candidates[0].candidate_token)
    state = engine.advance_season(state)

    # Step 2: 2018 (Slot 3 CM)
    assert state.current_year == 2018 and state.current_slot_index == 3
    state = engine.purchase_candidate(state, state.shortlists[3].candidates[0].candidate_token)
    state = engine.advance_season(state)

    # Step 3: 2019 (Transfer Window 1) - choose to hold squad
    assert state.current_year == 2019 and state.current_phase == GamePhase.TRANSFER_WINDOW
    state = engine.advance_season(state)

    # Step 4: 2020 (Slot 4 CB)
    assert state.current_year == 2020 and state.current_slot_index == 4
    state = engine.purchase_candidate(state, state.shortlists[4].candidates[0].candidate_token)
    state = engine.advance_season(state)

    # Step 5: 2021 (Slot 5 CM)
    assert state.current_year == 2021 and state.current_slot_index == 5
    state = engine.purchase_candidate(state, state.shortlists[5].candidates[0].candidate_token)
    state = engine.advance_season(state)

    # Step 6: 2022 (Transfer Window 2) - replace Slot 2 (WG) with candidate 1 from shortlist
    assert state.current_year == 2022 and state.current_phase == GamePhase.TRANSFER_WINDOW
    state = engine.replace_player(
        state,
        slot_index=2,
        replacement_candidate_token_or_id=state.shortlists[2].candidates[1].candidate_token,
    )
    state = engine.advance_season(state)

    # Step 7: 2023 (Slot 6 CB)
    assert state.current_year == 2023 and state.current_slot_index == 6
    state = engine.purchase_candidate(state, state.shortlists[6].candidates[0].candidate_token)
    state = engine.advance_season(state)

    # Step 8: 2024 (Slot 7 GK)
    assert state.current_year == 2024 and state.current_slot_index == 7
    state = engine.purchase_candidate(state, state.shortlists[7].candidates[0].candidate_token)
    state = engine.advance_season(state)

    # Step 9: 2025 (Transfer Window 3) - hold squad
    assert state.current_year == 2025 and state.current_phase == GamePhase.TRANSFER_WINDOW
    state = engine.advance_season(state)

    # Step 10: 2026 (Final Settlement)
    assert state.current_year == 2026
    assert state.is_completed
    assert state.current_phase == GamePhase.COMPLETED
    assert state.final_net_worth is not None
    assert state.final_squad_valuation is not None
    assert len(state.settlement_records) == 7

    # Verify formula: Final Net Worth = Remaining Cash + Sum of 2026 valuations of 7 owned players
    expected_squad_valuation = sum(r.valuation_2026_usd for r in state.settlement_records)
    expected_net_worth = round(state.cash_balance + expected_squad_valuation, 2)

    assert state.final_squad_valuation == round(expected_squad_valuation, 2)
    assert state.final_net_worth == expected_net_worth
    assert state.final_net_worth > 0


def test_transactional_integrity_on_failure(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that when an action fails validation, state remains completely unmodified."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="TX_INTEGRITY_TEST", room_seed="ROOM_ALPHA")

    initial_version = state.state_version
    initial_balance = state.cash_balance
    initial_tx_count = len(state.transaction_history)

    # Attempt invalid purchase
    with pytest.raises(InvalidGameActionError):
        engine.purchase_candidate(state, candidate_token_or_id="NON_EXISTENT")

    # Verify state was not modified in any way
    assert state.state_version == initial_version
    assert state.cash_balance == initial_balance
    assert len(state.transaction_history) == initial_tx_count


def test_client_view_zero_leakage_and_post_reveal(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that to_client_view strictly masks player IDs before reveal and reveals at end."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="LEAK_TEST", room_seed="SEED_LEAK")

    # Purchase candidate for Slot 1
    state = engine.purchase_candidate(state, state.shortlists[1].candidates[0].candidate_token)

    # Pre-settlement client view
    client_view = state.to_client_view()
    assert client_view["is_completed"] is False
    assert client_view["settlement_records"] == []

    # Verify shortlists do not leak secret_player_ids
    shortlists = client_view["shortlists"]
    assert isinstance(shortlists, dict)
    for sl in shortlists.values():
        assert isinstance(sl, dict)
        assert "secret_player_ids" not in sl
        for cand in sl["candidates"]:
            assert "candidate_token" in cand
            assert "player_id" not in cand
            assert "name" not in cand

    # Verify slot does not leak player ID or original shortlist IDs
    slots = client_view["slots"]
    assert isinstance(slots, list)
    assert slots[0]["is_filled"] is True
    assert slots[0]["current_player_id"] is None
    assert slots[0]["current_player_name"] == "Anonymous Signed Player"
    assert slots[0]["original_shortlist_player_ids"] == []

    # Verify transaction history does not leak player ID or provenance
    txs = client_view["transaction_history"]
    assert isinstance(txs, list)
    assert txs[0]["player_id"] == "HIDDEN"
    assert txs[0]["player_name"] == "Anonymous Player"
    assert txs[0]["provenance"] is None


def test_premature_transfer_window_action_rejected(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify slots scheduled for future seasons cannot be traded in earlier transfer windows."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="PREMATURE_TEST", room_seed="ROOM_ALPHA")

    # Fill slots 1, 2, 3 and advance to 2019 TW1
    for s_idx in (1, 2, 3):
        cand_tok = state.shortlists[s_idx].candidates[0].candidate_token
        state = engine.purchase_candidate(state, cand_tok)
        state = engine.advance_season(state)

    assert state.current_year == 2019
    assert state.current_phase == GamePhase.TRANSFER_WINDOW

    # Attempting to trade Slot 4 (scheduled for 2020) must be rejected
    with pytest.raises(InvalidPhaseError, match="has buying year 2020 and cannot be traded"):
        engine.sell_player(state, slot_index=4)

    with pytest.raises(InvalidPhaseError, match="has buying year 2020 and cannot be traded"):
        engine.replace_player(
            state,
            slot_index=4,
            replacement_candidate_token=state.shortlists[4].candidates[0].candidate_token,
        )


def test_unfilled_vacated_slot_blocks_timeline_advance(
    live_con: duckdb.DuckDBPyConnection,
) -> None:
    """Verify that advancing from a transfer window with a vacated slot is blocked."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="VACATED_ADVANCE_TEST", room_seed="ROOM_BETA")

    for s_idx in (1, 2, 3):
        cand_tok = state.shortlists[s_idx].candidates[0].candidate_token
        state = engine.purchase_candidate(state, cand_tok)
        state = engine.advance_season(state)

    # Sell Slot 1 in 2019
    sold_state = engine.sell_player(state, slot_index=1)
    assert not sold_state.slots[0].is_filled

    # Advancing without replacement must fail
    with pytest.raises(InvalidGameActionError, match="vacated during transfer window"):
        engine.advance_season(sold_state)


def test_duplicate_player_signing_rejected(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify signing a player already owned in squad raises DuplicatePlayerError."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="DUP_TEST", room_seed="DUP_SEED")

    # Purchase candidate for Slot 1
    cand_tok = state.shortlists[1].candidates[0].candidate_token
    signed_state = engine.purchase_candidate(state, cand_tok)
    first_player_id = signed_state.slots[0].current_player_id
    assert first_player_id is not None

    # Simulate an edge case where Slot 1 is reopened but the player is owned in Slot 2
    from blindbillion.engine.models import PlayerSlot

    mock_slots = list(signed_state.slots)
    mock_slots[1] = PlayerSlot(
        slot_index=2,
        required_position="WG",
        buying_year=2017,
        current_player_id=first_player_id,
    )
    mock_slots[0] = PlayerSlot(
        slot_index=1,
        required_position=signed_state.slots[0].required_position,
        buying_year=signed_state.slots[0].buying_year,
        current_player_id=None,
    )
    dup_state = signed_state.model_copy(update={"slots": tuple(mock_slots)})

    with pytest.raises(DuplicatePlayerError, match="Duplicate signings are prohibited"):
        engine.purchase_candidate(dup_state, cand_tok)


def test_invalid_slot_bounds_rejected(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify out-of-bounds slot indices are rejected with InvalidSlotError."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="BOUNDS_TEST", room_seed="BOUNDS_SEED")

    # Fill slots and advance to 2019 TW1
    for s_idx in (1, 2, 3):
        cand = state.shortlists[s_idx].candidates[0].candidate_token
        state = engine.purchase_candidate(state, cand)
        state = engine.advance_season(state)

    with pytest.raises(InvalidSlotError):
        engine.sell_player(state, slot_index=0)

    with pytest.raises(InvalidSlotError):
        engine.sell_player(state, slot_index=8)

    with pytest.raises(InvalidSlotError):
        engine.replace_player(state, slot_index=0, replacement_candidate_token="TOKEN")

    with pytest.raises(InvalidSlotError):
        engine.replace_player(state, slot_index=8, replacement_candidate_token="TOKEN")


def test_sell_empty_slot_rejected(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify selling an unfilled slot raises InvalidGameActionError."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="EMPTY_SELL_TEST", room_seed="EMPTY_SEED")

    for s_idx in (1, 2, 3):
        cand = state.shortlists[s_idx].candidates[0].candidate_token
        state = engine.purchase_candidate(state, cand)
        state = engine.advance_season(state)

    sold_state = engine.sell_player(state, slot_index=1)
    with pytest.raises(InvalidGameActionError, match="no signed player to sell"):
        engine.sell_player(sold_state, slot_index=1)


def test_completed_game_rejects_further_mutations(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify all mutating actions are rejected once the game is completed."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="COMPLETED_MUTATION_TEST", room_seed="SEED_DONE")

    # Run complete game
    for s_idx in (1, 2, 3):
        cand = state.shortlists[s_idx].candidates[0].candidate_token
        state = engine.purchase_candidate(state, cand)
        state = engine.advance_season(state)
    state = engine.advance_season(state)  # TW1
    for s_idx in (4, 5):
        cand = state.shortlists[s_idx].candidates[0].candidate_token
        state = engine.purchase_candidate(state, cand)
        state = engine.advance_season(state)
    state = engine.advance_season(state)  # TW2
    for s_idx in (6, 7):
        cand = state.shortlists[s_idx].candidates[0].candidate_token
        state = engine.purchase_candidate(state, cand)
        state = engine.advance_season(state)
    state = engine.advance_season(state)  # TW3 -> finalizes

    assert state.is_completed

    with pytest.raises(InvalidGameActionError, match="completed game"):
        engine.purchase_candidate(state, candidate_token="ANY")

    with pytest.raises(InvalidGameActionError, match="completed game"):
        engine.sell_player(state, slot_index=1)

    with pytest.raises(InvalidGameActionError, match="completed game"):
        engine.replace_player(state, slot_index=1, replacement_candidate_token="ANY")

    with pytest.raises(InvalidGameActionError, match="already completed"):
        engine.advance_season(state)

    # Calling finalize_game again is idempotent
    final_again = engine.finalize_game(state)
    assert final_again.final_net_worth == state.final_net_worth


def test_finalize_game_with_unfilled_squad_rejected(live_con: duckdb.DuckDBPyConnection) -> None:
    """Verify finalize_game requires all 7 squad slots to be filled."""
    engine = GameEngine(con=live_con)
    state = engine.initialize_game(game_id="UNFILLED_SETTLE_TEST", room_seed="SEED_UNFILLED")

    with pytest.raises(InvalidGameActionError, match="all 7 squad slots must be filled"):
        engine.finalize_game(state)


def test_timeline_step_out_of_bounds_and_missing() -> None:
    """Verify get_timeline_step and find_step_index raise TimelineError on invalid queries."""
    with pytest.raises(TimelineError, match="out of bounds"):
        get_timeline_step(-1)

    with pytest.raises(TimelineError, match="out of bounds"):
        get_timeline_step(99)

    with pytest.raises(TimelineError, match="No timeline step"):
        find_step_index(year=2099, phase=GamePhase.BUYING_SEASON)
