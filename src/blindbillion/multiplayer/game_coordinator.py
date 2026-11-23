"""Server-authoritative game action coordinator, turn barriers, and leaderboard computation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from blindbillion.engine.engine import GameEngine
from blindbillion.engine.models import GamePhase, GameState
from blindbillion.engine.timeline import GAME_TIMELINE_STEPS, get_timeline_step
from blindbillion.multiplayer.db_models import (
    ActionIdempotencyModel,
    PlayerGameStateModel,
    RoomModel,
    RoomPlayerModel,
)
from blindbillion.multiplayer.models import (
    ActionResponse,
    LeaderboardEntry,
    MultiplayerGameActionRequest,
    PlayerGameStateView,
    RoomGameStateResponse,
    RoomStatus,
)
from blindbillion.multiplayer.room_manager import serialize_room_view


class GameCoordinator:
    """Coordinates turn synchronization, action validation, and final settlement across players."""

    def __init__(self, engine: GameEngine) -> None:
        self.engine = engine

    def start_game(
        self, session: Session, room_code: str, caller_player_id: str
    ) -> RoomGameStateResponse:
        """Host-only start game: validates lobby, initializes players, starts 2016."""
        clean_code = room_code.strip().upper()
        room = session.query(RoomModel).filter(RoomModel.room_code == clean_code).first()
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

        if room.host_player_id != caller_player_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the host player can start the game.",
            )

        if room.status != RoomStatus.LOBBY.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start game in status '{room.status}'.",
            )

        if len(room.players) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"At least 2 players are required to start the game "
                    f"(currently {len(room.players)})."
                ),
            )

        # Non-host players must be ready
        unready_players = [p.display_name for p in room.players if not p.is_ready and not p.is_host]
        if unready_players:
            names = ", ".join(unready_players)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start: players not ready: {names}.",
            )

        # Initialize GameState for every player in the room using shared room_seed
        for player in room.players:
            game_id = f"{room.room_code}_{player.player_id}"
            state = self.engine.initialize_game(game_id=game_id, room_seed=room.room_seed)
            serialized = state.model_dump_json()

            existing_state_record = (
                session.query(PlayerGameStateModel)
                .filter(
                    PlayerGameStateModel.room_code == clean_code,
                    PlayerGameStateModel.player_id == player.player_id,
                )
                .first()
            )
            if existing_state_record:
                existing_state_record.serialized_state = serialized
                existing_state_record.state_version = 1
                existing_state_record.updated_at = datetime.now(UTC)
            else:
                session.add(
                    PlayerGameStateModel(
                        room_code=clean_code,
                        player_id=player.player_id,
                        serialized_state=serialized,
                        state_version=1,
                    )
                )

            player.is_turn_submitted = False
            player.last_seen_at = datetime.now(UTC)

        room.status = RoomStatus.IN_GAME.value
        room.current_year = 2016
        room.current_phase = "BUYING_SEASON"
        room.current_slot_index = 1
        room.timeline_step_index = 0
        room.state_version += 1
        room.updated_at = datetime.now(UTC)

        session.commit()
        session.refresh(room)

        return self.get_room_game_state(
            session=session, room_code=clean_code, player_id=caller_player_id
        )

    def submit_action(
        self,
        session: Session,
        room_code: str,
        player: RoomPlayerModel,
        request: MultiplayerGameActionRequest,
    ) -> ActionResponse:
        """Execute a validated player action with idempotency and round barrier coordination."""
        clean_code = room_code.strip().upper()

        # 1. Idempotency Check
        idempotency_rec = (
            session.query(ActionIdempotencyModel)
            .filter(
                ActionIdempotencyModel.idempotency_key == request.idempotency_key,
                ActionIdempotencyModel.room_code == clean_code,
                ActionIdempotencyModel.player_id == player.player_id,
            )
            .first()
        )
        if idempotency_rec:
            cached_dict = json.loads(idempotency_rec.response_payload)
            return ActionResponse.model_validate(cached_dict)

        # 2. Room & Phase Validation
        room = session.query(RoomModel).filter(RoomModel.room_code == clean_code).first()
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

        if room.status != RoomStatus.IN_GAME.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot perform actions in room state '{room.status}'.",
            )

        # 3. Load Player State
        state_model = (
            session.query(PlayerGameStateModel)
            .filter(
                PlayerGameStateModel.room_code == clean_code,
                PlayerGameStateModel.player_id == player.player_id,
            )
            .first()
        )
        if not state_model:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Player game state not found.",
            )

        current_state = GameState.model_validate_json(state_model.serialized_state)

        # 4. Execute Action
        msg = ""
        if request.action_type == "BUY":
            if not request.candidate_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="candidate_token is required for BUY action.",
                )
            if player.is_turn_submitted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Purchase already submitted for this slot. Awaiting other players.",
                )
            current_state = self.engine.purchase_candidate(
                state=current_state, candidate_token=request.candidate_token
            )
            player.is_turn_submitted = True
            msg = f"Candidate purchased for Slot {current_state.current_slot_index}."

        elif request.action_type == "REPLACE":
            if request.slot_index is None or not request.candidate_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="slot_index and candidate_token required for REPLACE action.",
                )
            current_state = self.engine.replace_player(
                state=current_state,
                slot_index=request.slot_index,
                replacement_candidate_token=request.candidate_token,
            )
            msg = f"Replaced player in Slot {request.slot_index}."

        elif request.action_type == "SELL":
            if request.slot_index is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="slot_index required for SELL action.",
                )
            current_state = self.engine.sell_player(
                state=current_state, slot_index=request.slot_index
            )
            msg = f"Sold player from Slot {request.slot_index}."

        elif request.action_type == "PASS":
            player.is_turn_submitted = True
            msg = f"Ready for next round in {room.current_year}."

        # 5. Persist Player State
        state_model.serialized_state = current_state.model_dump_json()
        state_model.state_version += 1
        state_model.updated_at = datetime.now(UTC)
        player.last_seen_at = datetime.now(UTC)

        # 6. Check Round Barrier
        all_submitted = all(p.is_turn_submitted for p in room.players)
        is_cleared = False
        if all_submitted:
            self._advance_room_timeline(session=session, room=room)
            is_cleared = True

        session.commit()
        session.refresh(room)
        session.refresh(state_model)

        my_state_view = self._build_player_state_view(player.player_id, current_state, player)
        action_resp = ActionResponse(
            success=True,
            message=msg,
            action_type=request.action_type,
            new_balance=current_state.cash_balance,
            is_barrier_cleared=is_cleared,
            room=serialize_room_view(room),
            my_state=my_state_view,
        )

        # Store idempotency record
        session.add(
            ActionIdempotencyModel(
                idempotency_key=request.idempotency_key,
                room_code=clean_code,
                player_id=player.player_id,
                action_type=request.action_type,
                response_payload=action_resp.model_dump_json(),
            )
        )
        session.commit()

        return action_resp

    def _advance_room_timeline(self, session: Session, room: RoomModel) -> None:
        """Advance synchronized timeline for all players after barrier clearance."""
        next_step_idx = room.timeline_step_index + 1

        if next_step_idx < len(GAME_TIMELINE_STEPS):
            next_step = get_timeline_step(next_step_idx)
            if next_step.phase == GamePhase.FINAL_SETTLEMENT:
                # Final 2026 Settlement reached
                room.status = RoomStatus.COMPLETED.value
                room.timeline_step_index = next_step_idx
                room.current_year = 2026
                room.current_phase = GamePhase.COMPLETED.value
                room.current_slot_index = None

                for p in room.players:
                    p_state_model = (
                        session.query(PlayerGameStateModel)
                        .filter(
                            PlayerGameStateModel.room_code == room.room_code,
                            PlayerGameStateModel.player_id == p.player_id,
                        )
                        .first()
                    )
                    if p_state_model:
                        p_state = GameState.model_validate_json(p_state_model.serialized_state)
                        if not p_state.is_completed:
                            p_state = self.engine.finalize_game(p_state)
                            p_state_model.serialized_state = p_state.model_dump_json()
                            p_state_model.state_version += 1
                    p.is_turn_submitted = True
            else:
                room.timeline_step_index = next_step_idx
                room.current_year = next_step.year
                room.current_phase = next_step.phase.value
                room.current_slot_index = next_step.slot_index

                # Advance every player's game state
                for p in room.players:
                    p_state_model = (
                        session.query(PlayerGameStateModel)
                        .filter(
                            PlayerGameStateModel.room_code == room.room_code,
                            PlayerGameStateModel.player_id == p.player_id,
                        )
                        .first()
                    )
                    if p_state_model:
                        p_state = GameState.model_validate_json(p_state_model.serialized_state)
                        advanced = self.engine.advance_season(p_state)
                        p_state_model.serialized_state = advanced.model_dump_json()
                        p_state_model.state_version += 1
                    p.is_turn_submitted = False
        else:
            # Final 2026 Settlement reached
            room.status = RoomStatus.COMPLETED.value
            room.current_year = 2026
            room.current_phase = GamePhase.COMPLETED.value
            room.current_slot_index = None

            for p in room.players:
                p_state_model = (
                    session.query(PlayerGameStateModel)
                    .filter(
                        PlayerGameStateModel.room_code == room.room_code,
                        PlayerGameStateModel.player_id == p.player_id,
                    )
                    .first()
                )
                if p_state_model:
                    p_state = GameState.model_validate_json(p_state_model.serialized_state)
                    if not p_state.is_completed:
                        p_state = self.engine.finalize_game(p_state)
                        p_state_model.serialized_state = p_state.model_dump_json()
                        p_state_model.state_version += 1
                p.is_turn_submitted = True

        room.state_version += 1
        room.updated_at = datetime.now(UTC)

    def get_room_game_state(
        self, session: Session, room_code: str, player_id: str
    ) -> RoomGameStateResponse:
        """Retrieve sanitized current game state view for client display and reloads."""
        clean_code = room_code.strip().upper()
        room = session.query(RoomModel).filter(RoomModel.room_code == clean_code).first()
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

        player = next((p for p in room.players if p.player_id == player_id), None)
        if not player:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Player not in room.")

        state_model = (
            session.query(PlayerGameStateModel)
            .filter(
                PlayerGameStateModel.room_code == clean_code,
                PlayerGameStateModel.player_id == player_id,
            )
            .first()
        )
        if not state_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Game state not found for player."
            )

        game_state = GameState.model_validate_json(state_model.serialized_state)
        my_state_view = self._build_player_state_view(player_id, game_state, player)

        leaderboard: tuple[LeaderboardEntry, ...] | None = None
        if room.status == RoomStatus.COMPLETED.value:
            leaderboard = self._compute_leaderboard(session=session, room=room)

        return RoomGameStateResponse(
            room=serialize_room_view(room),
            my_state=my_state_view,
            leaderboard=leaderboard,
        )

    def _build_player_state_view(
        self, player_id: str, state: GameState, player: RoomPlayerModel
    ) -> PlayerGameStateView:
        """Produce client view masking secret identities until final reveal."""
        client_dict = state.to_client_view()
        slots_list = client_dict.get("slots", [])
        tx_list = client_dict.get("transaction_history", [])
        raw_shortlists = client_dict.get("shortlists", {})

        settlement_recs: tuple[dict[str, Any], ...] | None = None
        if state.is_completed:
            settlement_recs = tuple(r.model_dump() for r in state.settlement_records)

        return PlayerGameStateView(
            player_id=player_id,
            cash_balance=state.cash_balance,
            current_year=state.current_year,
            current_phase=state.current_phase.value,
            current_slot_index=state.current_slot_index,
            slots=tuple(slots_list) if isinstance(slots_list, list) else (),
            shortlists=raw_shortlists if isinstance(raw_shortlists, dict) else {},
            transaction_history=tuple(tx_list) if isinstance(tx_list, list) else (),
            is_turn_submitted=player.is_turn_submitted,
            is_completed=state.is_completed,
            final_net_worth=state.final_net_worth,
            final_squad_valuation=state.final_squad_valuation,
            settlement_records=settlement_recs,
        )

    def _compute_leaderboard(
        self, session: Session, room: RoomModel
    ) -> tuple[LeaderboardEntry, ...]:
        """Compute final 2026 rankings ordered by descending final net worth."""
        results: list[tuple[str, str, float, float, float, tuple[dict[str, Any], ...]]] = []

        for p in room.players:
            p_state_model = (
                session.query(PlayerGameStateModel)
                .filter(
                    PlayerGameStateModel.room_code == room.room_code,
                    PlayerGameStateModel.player_id == p.player_id,
                )
                .first()
            )
            if p_state_model:
                st = GameState.model_validate_json(p_state_model.serialized_state)
                net_worth = st.final_net_worth or 0.0
                cash = st.cash_balance
                squad_val = st.final_squad_valuation or 0.0
                raw_slots = st.to_client_view().get("slots", [])
                squad_slots: tuple[dict[str, Any], ...] = (
                    tuple(raw_slots) if isinstance(raw_slots, list) else ()
                )
                results.append(
                    (p.player_id, p.display_name, net_worth, cash, squad_val, squad_slots)
                )

        # Sort descending by net worth
        results.sort(key=lambda r: r[2], reverse=True)

        return tuple(
            LeaderboardEntry(
                rank=idx + 1,
                player_id=r[0],
                display_name=r[1],
                final_net_worth=r[2],
                remaining_cash=r[3],
                squad_valuation=r[4],
                squad=r[5],
            )
            for idx, r in enumerate(results)
        )
