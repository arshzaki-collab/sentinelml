"""Server-authoritative game engine for Blind Billion 2.0."""

from __future__ import annotations

import logging
import uuid
from typing import Final, cast

import duckdb

from blindbillion.constants import (
    SQUAD_SLOTS,
    STARTING_BUDGET_USD,
    TRANSFER_WINDOWS,
)
from blindbillion.data.models import PositionType, ShortlistSlot
from blindbillion.data.shortlist import ShortlistGenerator
from blindbillion.data.valuations import ValuationEngine
from blindbillion.engine.exceptions import (
    DuplicatePlayerError,
    InsufficientFundsError,
    InvalidGameActionError,
    InvalidPhaseError,
    InvalidReplacementCandidateError,
    InvalidSlotError,
    MissingValuationError,
    SlotAlreadyFilledError,
    TransferNotAllowedError,
)
from blindbillion.engine.models import (
    GamePhase,
    GameState,
    PlayerSlot,
    SettlementRecord,
    TransactionRecord,
)
from blindbillion.engine.timeline import (
    GAME_TIMELINE_STEPS,
    find_step_index,
    get_timeline_step,
)

logger = logging.getLogger(__name__)

FINAL_VALUATION_YEAR: Final[int] = 2026


class GameEngine:
    """Core game engine managing state transitions, valuation rules, and transactions."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con
        self.valuation_engine = ValuationEngine(con=self.con)
        self.shortlist_gen = ShortlistGenerator(con=self.con)

    def initialize_game(
        self,
        game_id: str,
        room_seed: str | int,
        difficulty: str = "PRO",
    ) -> GameState:
        """Create and initialize a new game session with $1B and deterministic shortlists."""
        shortlists = self.shortlist_gen.generate_full_game_shortlists(
            room_seed=room_seed,
            difficulty=difficulty,
        )

        slots: list[PlayerSlot] = []
        for slot_cfg in SQUAD_SLOTS:
            idx = int(str(slot_cfg["slot_index"]))
            pos = cast(PositionType, slot_cfg["position"])
            yr = int(str(slot_cfg["year"]))
            shortlist_slot = shortlists[idx]

            slots.append(
                PlayerSlot(
                    slot_index=idx,
                    required_position=pos,
                    buying_year=yr,
                    original_shortlist_player_ids=tuple(shortlist_slot.secret_player_ids),
                )
            )

        initial_step = get_timeline_step(0)  # 2016 Buying Season, Slot 1

        return GameState(
            game_id=game_id,
            room_seed=room_seed,
            current_year=initial_step.year,
            current_phase=initial_step.phase,
            current_slot_index=initial_step.slot_index,
            cash_balance=float(STARTING_BUDGET_USD),
            slots=tuple(slots),
            shortlists=shortlists,
            transaction_history=(),
            event_log=(
                f"Game {game_id} initialized with ${STARTING_BUDGET_USD:,.2f} starting capital.",
            ),
            state_version=1,
            is_completed=False,
        )

    def _validate_purchase(
        self, state: GameState, candidate_token: str
    ) -> tuple[int, PlayerSlot, str, float]:
        """Validate buying preconditions and return validated slot, player_id, and cost."""
        if state.is_completed:
            raise InvalidGameActionError("Cannot purchase candidates in a completed game.")

        if state.current_phase != GamePhase.BUYING_SEASON:
            raise InvalidPhaseError(
                f"Purchases only permitted during BUYING_SEASON (current: {state.current_phase})."
            )

        if state.current_slot_index is None:
            raise InvalidSlotError("No active slot index defined for current buying season.")

        slot_idx = state.current_slot_index
        slot = state.slots[slot_idx - 1]

        if slot.is_filled:
            raise SlotAlreadyFilledError(
                f"Slot {slot_idx} ({slot.required_position}) is already occupied by "
                f"{slot.current_player_name}."
            )

        shortlist = state.shortlists[slot_idx]
        player_id, cost_usd = self._resolve_candidate(
            shortlist=shortlist, candidate_token=candidate_token
        )

        if player_id in state.owned_player_ids:
            raise DuplicatePlayerError(
                f"Player {player_id} is already owned in squad. Duplicate signings are prohibited."
            )

        if cost_usd > state.cash_balance:
            raise InsufficientFundsError(
                f"Insufficient funds: purchase costs ${cost_usd:,.2f} but available balance is "
                f"${state.cash_balance:,.2f}."
            )

        return slot_idx, slot, player_id, cost_usd

    def purchase_candidate(
        self,
        state: GameState,
        candidate_token: str | None = None,
        candidate_token_or_id: str | None = None,
    ) -> GameState:
        """Purchase a candidate for the currently active buying season slot."""
        token = candidate_token or candidate_token_or_id
        if not token:
            raise InvalidGameActionError("Candidate token must be provided.")

        slot_idx, slot, player_id, cost_usd = self._validate_purchase(
            state=state, candidate_token=token
        )

        valuation = self.valuation_engine.get_player_valuation(
            player_id=player_id, year=state.current_year
        )
        if not valuation:
            raise MissingValuationError(
                f"Authoritative valuation for player {player_id} in {state.current_year} not found."
            )

        player_name = self._lookup_player_name(player_id)
        new_balance = round(state.cash_balance - cost_usd, 2)

        updated_slot = PlayerSlot(
            slot_index=slot.slot_index,
            required_position=slot.required_position,
            buying_year=slot.buying_year,
            current_player_id=player_id,
            current_player_name=player_name,
            purchase_price_usd=cost_usd,
            purchase_year=state.current_year,
            original_shortlist_player_ids=slot.original_shortlist_player_ids,
            previous_player_ids=slot.previous_player_ids,
        )

        new_slots = list(state.slots)
        new_slots[slot_idx - 1] = updated_slot

        tx = TransactionRecord(
            transaction_id=str(uuid.uuid4()),
            year=state.current_year,
            phase=state.current_phase,
            action="BUY",
            slot_index=slot_idx,
            player_id=player_id,
            player_name=player_name,
            amount_usd=-cost_usd,
            balance_before=state.cash_balance,
            balance_after=new_balance,
            provenance=valuation.provenance,
        )

        event_msg = (
            f"Signed {player_name} for Slot {slot_idx} ({slot.required_position}) "
            f"in {state.current_year} for ${cost_usd:,.2f}."
        )

        return GameState(
            game_id=state.game_id,
            room_seed=state.room_seed,
            current_year=state.current_year,
            current_phase=state.current_phase,
            current_slot_index=state.current_slot_index,
            cash_balance=new_balance,
            slots=tuple(new_slots),
            shortlists=state.shortlists,
            transaction_history=(*state.transaction_history, tx),
            event_log=(*state.event_log, event_msg),
            state_version=state.state_version + 1,
            is_completed=False,
        )

    def _validate_transfer_slot(self, state: GameState, slot_index: int) -> PlayerSlot:
        """Validate phase and slot constraints during a transfer window."""
        if state.is_completed:
            raise InvalidGameActionError("Cannot perform transfer actions in a completed game.")

        if state.current_phase != GamePhase.TRANSFER_WINDOW:
            raise TransferNotAllowedError(
                f"Transfers are only permitted during scheduled transfer windows "
                f"{TRANSFER_WINDOWS} (current: {state.current_phase})."
            )

        if slot_index < 1 or slot_index > len(state.slots):
            raise InvalidSlotError(f"Invalid slot index {slot_index}.")

        slot = state.slots[slot_index - 1]
        if slot.buying_year >= state.current_year:
            raise InvalidPhaseError(
                f"Slot {slot_index} ({slot.required_position}) has buying year {slot.buying_year} "
                f"and cannot be traded during the {state.current_year} transfer window."
            )

        return slot

    def sell_player(self, state: GameState, slot_index: int) -> GameState:
        """Sell currently held player in slot during a transfer window at historical valuation."""
        slot = self._validate_transfer_slot(state=state, slot_index=slot_index)

        if not slot.is_filled or slot.current_player_id is None:
            raise InvalidGameActionError(f"Slot {slot_index} has no signed player to sell.")

        player_id = slot.current_player_id
        player_name = slot.current_player_name or self._lookup_player_name(player_id)

        valuation = self.valuation_engine.get_player_valuation(
            player_id=player_id, year=state.current_year
        )
        if not valuation:
            raise MissingValuationError(
                f"Historical valuation for player {player_id} at {state.current_year} not found."
            )

        sale_credit_usd = round(valuation.value_usd, 2)
        new_balance = round(state.cash_balance + sale_credit_usd, 2)

        updated_slot = PlayerSlot(
            slot_index=slot.slot_index,
            required_position=slot.required_position,
            buying_year=slot.buying_year,
            current_player_id=None,
            current_player_name=None,
            purchase_price_usd=None,
            purchase_year=None,
            original_shortlist_player_ids=slot.original_shortlist_player_ids,
            previous_player_ids=(*slot.previous_player_ids, player_id),
        )

        new_slots = list(state.slots)
        new_slots[slot_index - 1] = updated_slot

        tx = TransactionRecord(
            transaction_id=str(uuid.uuid4()),
            year=state.current_year,
            phase=state.current_phase,
            action="SELL",
            slot_index=slot_index,
            player_id=player_id,
            player_name=player_name,
            amount_usd=sale_credit_usd,
            balance_before=state.cash_balance,
            balance_after=new_balance,
            provenance=valuation.provenance,
        )

        event_msg = (
            f"Sold {player_name} from Slot {slot_index} in {state.current_year} "
            f"for ${sale_credit_usd:,.2f}."
        )

        return GameState(
            game_id=state.game_id,
            room_seed=state.room_seed,
            current_year=state.current_year,
            current_phase=state.current_phase,
            current_slot_index=state.current_slot_index,
            cash_balance=new_balance,
            slots=tuple(new_slots),
            shortlists=state.shortlists,
            transaction_history=(*state.transaction_history, tx),
            event_log=(*state.event_log, event_msg),
            state_version=state.state_version + 1,
            is_completed=False,
        )

    def _resolve_replacement_candidate(
        self, state: GameState, slot_index: int, slot: PlayerSlot, candidate_token: str
    ) -> tuple[str, float]:
        """Validate replacement candidate against original shortlist and eligibility rules."""
        shortlist = state.shortlists[slot_index]
        try:
            rep_player_id, _ = self._resolve_candidate(
                shortlist=shortlist, candidate_token=candidate_token
            )
        except InvalidGameActionError as err:
            raise InvalidReplacementCandidateError(
                f"Candidate token '{candidate_token}' is not in the original "
                f"shortlist for Slot {slot_index}."
            ) from err

        allowed_ids = set(slot.original_shortlist_player_ids) | set(shortlist.secret_player_ids)
        if rep_player_id not in allowed_ids:
            raise InvalidReplacementCandidateError(
                f"Candidate {rep_player_id} is not in the original shortlist for Slot {slot_index}."
            )

        if rep_player_id in slot.previous_player_ids:
            raise InvalidGameActionError(
                f"Player {rep_player_id} was previously owned and sold from Slot {slot_index}."
            )

        if rep_player_id in state.owned_player_ids:
            raise DuplicatePlayerError(
                f"Player {rep_player_id} is already in squad. Duplicate signings are prohibited."
            )

        rep_val = self.valuation_engine.get_player_valuation(
            player_id=rep_player_id, year=state.current_year
        )
        if not rep_val:
            raise MissingValuationError(
                f"Authoritative valuation for replacement player {rep_player_id} in "
                f"{state.current_year} not found."
            )

        rep_cost_usd = round(rep_val.value_usd, 2)
        if rep_cost_usd > state.cash_balance:
            raise InsufficientFundsError(
                f"Insufficient funds: costs ${rep_cost_usd:,.2f} but available balance is "
                f"${state.cash_balance:,.2f}."
            )

        return rep_player_id, rep_cost_usd

    def replace_player(
        self,
        state: GameState,
        slot_index: int,
        replacement_candidate_token: str | None = None,
        replacement_candidate_token_or_id: str | None = None,
    ) -> GameState:
        """Replace a player in a slot during a transfer window using original shortlist."""
        token = replacement_candidate_token or replacement_candidate_token_or_id
        if not token:
            raise InvalidGameActionError("Replacement candidate token must be provided.")

        slot = self._validate_transfer_slot(state=state, slot_index=slot_index)

        current_state = state
        if slot.is_filled:
            current_state = self.sell_player(current_state, slot_index=slot_index)
            slot = current_state.slots[slot_index - 1]

        rep_player_id, rep_cost_usd = self._resolve_replacement_candidate(
            state=current_state,
            slot_index=slot_index,
            slot=slot,
            candidate_token=token,
        )

        rep_val = self.valuation_engine.get_player_valuation(
            player_id=rep_player_id, year=current_state.current_year
        )
        assert rep_val is not None

        player_name = self._lookup_player_name(rep_player_id)
        new_balance = round(current_state.cash_balance - rep_cost_usd, 2)

        updated_slot = PlayerSlot(
            slot_index=slot.slot_index,
            required_position=slot.required_position,
            buying_year=slot.buying_year,
            current_player_id=rep_player_id,
            current_player_name=player_name,
            purchase_price_usd=rep_cost_usd,
            purchase_year=current_state.current_year,
            original_shortlist_player_ids=slot.original_shortlist_player_ids,
            previous_player_ids=slot.previous_player_ids,
        )

        new_slots = list(current_state.slots)
        new_slots[slot_index - 1] = updated_slot

        tx = TransactionRecord(
            transaction_id=str(uuid.uuid4()),
            year=current_state.current_year,
            phase=current_state.current_phase,
            action="REPLACE",
            slot_index=slot_index,
            player_id=rep_player_id,
            player_name=player_name,
            amount_usd=-rep_cost_usd,
            balance_before=current_state.cash_balance,
            balance_after=new_balance,
            provenance=rep_val.provenance,
        )

        event_msg = (
            f"Signed replacement {player_name} for Slot {slot_index} in "
            f"{current_state.current_year} for ${rep_cost_usd:,.2f}."
        )

        return GameState(
            game_id=current_state.game_id,
            room_seed=current_state.room_seed,
            current_year=current_state.current_year,
            current_phase=current_state.current_phase,
            current_slot_index=current_state.current_slot_index,
            cash_balance=new_balance,
            slots=tuple(new_slots),
            shortlists=current_state.shortlists,
            transaction_history=(*current_state.transaction_history, tx),
            event_log=(*current_state.event_log, event_msg),
            state_version=current_state.state_version + 1,
            is_completed=False,
        )

    def advance_season(self, state: GameState) -> GameState:
        """Advance the game timeline to the next milestone step."""
        if state.is_completed:
            raise InvalidGameActionError("Game is already completed.")

        if state.current_phase == GamePhase.BUYING_SEASON and state.current_slot_index is not None:
            current_slot = state.slots[state.current_slot_index - 1]
            if not current_slot.is_filled:
                raise InvalidGameActionError(
                    f"Must purchase a candidate for Slot {state.current_slot_index} "
                    f"({current_slot.required_position}) before advancing to the next season."
                )

        if state.current_phase == GamePhase.TRANSFER_WINDOW:
            for s in state.slots:
                if s.buying_year < state.current_year and not s.is_filled:
                    raise InvalidGameActionError(
                        f"Slot {s.slot_index} ({s.required_position}) was vacated during "
                        f"transfer window and must be filled with a replacement before advancing."
                    )

        current_step_idx = find_step_index(year=state.current_year, phase=state.current_phase)
        next_step_idx = current_step_idx + 1

        if next_step_idx >= len(GAME_TIMELINE_STEPS):
            raise InvalidGameActionError("Already at the final milestone of the timeline.")

        next_step = get_timeline_step(next_step_idx)

        if next_step.phase == GamePhase.FINAL_SETTLEMENT:
            return self.finalize_game(state)

        event_msg = f"Advanced timeline to {next_step.description}."

        return GameState(
            game_id=state.game_id,
            room_seed=state.room_seed,
            current_year=next_step.year,
            current_phase=next_step.phase,
            current_slot_index=next_step.slot_index,
            cash_balance=state.cash_balance,
            slots=state.slots,
            shortlists=state.shortlists,
            transaction_history=state.transaction_history,
            event_log=(*state.event_log, event_msg),
            state_version=state.state_version + 1,
            is_completed=False,
        )

    def _build_settlement_record(self, slot: PlayerSlot) -> SettlementRecord:
        """Compute the 2026 valuation and ROI for an individual squad slot."""
        player_id = str(slot.current_player_id)
        player_name = str(slot.current_player_name)
        purchase_price = float(slot.purchase_price_usd or 0.0)
        purchase_yr = int(slot.purchase_year or slot.buying_year)

        val_2026 = self.valuation_engine.get_player_valuation(
            player_id=player_id, year=FINAL_VALUATION_YEAR
        )
        if not val_2026:
            raise MissingValuationError(
                f"2026 final valuation for player {player_id} ({player_name}) not found."
            )

        val_2026_usd = round(val_2026.value_usd, 2)
        gain_usd = round(val_2026_usd - purchase_price, 2)
        roi = round((gain_usd / purchase_price) * 100.0, 2) if purchase_price > 0 else 0.0

        return SettlementRecord(
            slot_index=slot.slot_index,
            position=slot.required_position,
            player_id=player_id,
            player_name=player_name,
            purchase_year=purchase_yr,
            purchase_price_usd=purchase_price,
            valuation_2026_usd=val_2026_usd,
            value_gain_usd=gain_usd,
            roi_percentage=roi,
            provenance=val_2026.provenance,
        )

    def finalize_game(self, state: GameState) -> GameState:
        """Calculate final 2026 valuations, squad valuation, and total net worth."""
        if state.is_completed:
            return state

        if state.filled_slots_count != 7:
            unfilled = [s.slot_index for s in state.slots if not s.is_filled]
            raise InvalidGameActionError(
                f"Cannot finalize game: all 7 squad slots must be filled (unfilled: {unfilled})."
            )

        records: list[SettlementRecord] = [
            self._build_settlement_record(slot) for slot in state.slots
        ]
        total_squad_valuation = round(sum(r.valuation_2026_usd for r in records), 2)
        final_net_worth = round(state.cash_balance + total_squad_valuation, 2)

        tx = TransactionRecord(
            transaction_id=str(uuid.uuid4()),
            year=FINAL_VALUATION_YEAR,
            phase=GamePhase.FINAL_SETTLEMENT,
            action="FINAL_SETTLEMENT",
            slot_index=0,
            player_id="SQUAD",
            player_name="Full Squad",
            amount_usd=total_squad_valuation,
            balance_before=state.cash_balance,
            balance_after=state.cash_balance,
            net_worth_after=final_net_worth,
        )

        event_msg = (
            f"Game completed! 2026 Final Settlement: Remaining Cash = ${state.cash_balance:,.2f}, "
            f"Squad Valuation = ${total_squad_valuation:,.2f}, "
            f"Total Net Worth = ${final_net_worth:,.2f}."
        )

        return GameState(
            game_id=state.game_id,
            room_seed=state.room_seed,
            current_year=FINAL_VALUATION_YEAR,
            current_phase=GamePhase.COMPLETED,
            current_slot_index=None,
            cash_balance=state.cash_balance,
            slots=state.slots,
            shortlists=state.shortlists,
            transaction_history=(*state.transaction_history, tx),
            event_log=(*state.event_log, event_msg),
            state_version=state.state_version + 1,
            is_completed=True,
            final_net_worth=final_net_worth,
            final_squad_valuation=total_squad_valuation,
            settlement_records=tuple(records),
        )

    def _resolve_candidate(
        self,
        shortlist: ShortlistSlot,
        candidate_token: str,
    ) -> tuple[str, float]:
        """Resolve an opaque candidate token to (player_id, cost_usd) within a shortlist."""
        for idx, cand in enumerate(shortlist.candidates):
            if cand.candidate_token == candidate_token:
                secret_id = shortlist.secret_player_ids[idx]
                return secret_id, float(cand.cost_usd)

        raise InvalidGameActionError(
            f"Candidate token '{candidate_token}' is not in shortlist for "
            f"slot {shortlist.slot_index} ({shortlist.buying_year} {shortlist.position})."
        )

    def _lookup_player_name(self, player_id: str) -> str:
        """Fetch human-readable player name from database."""
        row = self.con.execute(
            "SELECT name FROM raw_players WHERE CAST(player_id AS VARCHAR) = ?", [str(player_id)]
        ).fetchone()
        return str(row[0]) if row and row[0] else f"Player_{player_id}"
