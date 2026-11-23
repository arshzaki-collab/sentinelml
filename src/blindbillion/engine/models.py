"""State models and schemas for the Blind Billion 2.0 game engine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from blindbillion.data.models import PositionType, ProvenanceRecord, ShortlistSlot


class GamePhase(StrEnum):
    """Execution phases in a Blind Billion 2.0 game session."""

    BUYING_SEASON = "BUYING_SEASON"
    TRANSFER_WINDOW = "TRANSFER_WINDOW"
    FINAL_SETTLEMENT = "FINAL_SETTLEMENT"
    COMPLETED = "COMPLETED"


class PlayerSlot(BaseModel):
    """One of the seven authoritative squad slots."""

    model_config = ConfigDict(frozen=True)

    slot_index: int = Field(..., ge=1, le=7, description="Slot index (1 to 7)")
    required_position: PositionType = Field(..., description="Tactical position for slot")
    buying_year: int = Field(..., description="Original buying season year")
    current_player_id: str | None = Field(default=None, description="Currently owned player ID")
    current_player_name: str | None = Field(default=None, description="Currently owned player name")
    purchase_price_usd: float | None = Field(default=None, ge=0.0, description="Price paid in USD")
    purchase_year: int | None = Field(default=None, description="Year player was signed")
    original_shortlist_player_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Original 4 player IDs for this slot (server-only)",
    )
    previous_player_ids: tuple[str, ...] = Field(
        default_factory=tuple, description="Player IDs previously held and sold in this slot"
    )

    @property
    def is_filled(self) -> bool:
        return self.current_player_id is not None


class TransactionRecord(BaseModel):
    """Immutable record of every financial transaction in the game."""

    model_config = ConfigDict(frozen=True)

    transaction_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    year: int
    phase: GamePhase
    action: Literal["BUY", "SELL", "REPLACE", "FINAL_SETTLEMENT"]
    slot_index: int
    player_id: str
    player_name: str
    amount_usd: float  # Negative for debits/purchases, positive for credits/sales
    balance_before: float
    balance_after: float
    net_worth_after: float | None = None
    provenance: ProvenanceRecord | None = None


class SettlementRecord(BaseModel):
    """Detailed valuation audit record at 2026 final game settlement."""

    model_config = ConfigDict(frozen=True)

    slot_index: int
    position: PositionType
    player_id: str
    player_name: str
    purchase_year: int
    purchase_price_usd: float
    valuation_2026_usd: float
    value_gain_usd: float
    roi_percentage: float
    provenance: ProvenanceRecord


class GameState(BaseModel):
    """Complete, immutable snapshot of the game session state."""

    model_config = ConfigDict(frozen=True)

    game_id: str
    room_seed: str | int
    current_year: int
    current_phase: GamePhase
    current_slot_index: int | None = None  # None during transfer windows or settlement
    cash_balance: float = Field(..., ge=0.0, description="Available USD balance ($B_t >= 0)")
    slots: tuple[PlayerSlot, ...] = Field(..., min_length=7, max_length=7)
    shortlists: dict[int, ShortlistSlot] = Field(
        ..., description="Original shortlists keyed by slot_index (1 to 7)"
    )
    transaction_history: tuple[TransactionRecord, ...] = Field(default_factory=tuple)
    event_log: tuple[str, ...] = Field(default_factory=tuple)
    state_version: int = Field(default=1, ge=1)
    is_completed: bool = False
    final_net_worth: float | None = None
    final_squad_valuation: float | None = None
    settlement_records: tuple[SettlementRecord, ...] = Field(default_factory=tuple)

    @property
    def filled_slots_count(self) -> int:
        return sum(1 for s in self.slots if s.is_filled)

    @property
    def owned_player_ids(self) -> set[str]:
        return {s.current_player_id for s in self.slots if s.current_player_id is not None}

    def to_client_view(self) -> dict[str, object]:
        """Produce a sanitized client-safe view ensuring zero data leakage before reveal."""
        is_revealed = self.is_completed

        client_slots: list[dict[str, object]] = []
        for slot in self.slots:
            slot_data: dict[str, object] = {
                "slot_index": slot.slot_index,
                "required_position": slot.required_position,
                "buying_year": slot.buying_year,
                "is_filled": slot.is_filled,
                "purchase_price_usd": slot.purchase_price_usd,
                "purchase_year": slot.purchase_year,
            }
            if is_revealed:
                slot_data["current_player_id"] = slot.current_player_id
                slot_data["current_player_name"] = slot.current_player_name
                slot_data["original_shortlist_player_ids"] = list(
                    slot.original_shortlist_player_ids
                )
                slot_data["previous_player_ids"] = list(slot.previous_player_ids)
            else:
                slot_data["current_player_id"] = None
                slot_data["current_player_name"] = (
                    "Anonymous Signed Player" if slot.is_filled else None
                )
                slot_data["original_shortlist_player_ids"] = []
                slot_data["previous_player_ids"] = []
            client_slots.append(slot_data)

        client_shortlists: dict[int, dict[str, object]] = {}
        for s_idx, sl in self.shortlists.items():
            client_shortlists[s_idx] = {
                "slot_index": sl.slot_index,
                "buying_year": sl.buying_year,
                "position": sl.position,
                "candidates": [
                    {
                        "candidate_token": c.candidate_token,
                        "cost_usd": c.cost_usd,
                        "position": c.position,
                        "hints": c.hints,
                    }
                    for c in sl.candidates
                ],
            }

        client_transactions: list[dict[str, object]] = []
        for tx in self.transaction_history:
            tx_data: dict[str, object] = {
                "transaction_id": tx.transaction_id,
                "year": tx.year,
                "phase": tx.phase,
                "action": tx.action,
                "slot_index": tx.slot_index,
                "amount_usd": tx.amount_usd,
                "balance_before": tx.balance_before,
                "balance_after": tx.balance_after,
                "net_worth_after": tx.net_worth_after,
                "timestamp": tx.timestamp.isoformat(),
            }
            if is_revealed:
                tx_data["player_id"] = tx.player_id
                tx_data["player_name"] = tx.player_name
                tx_data["provenance"] = tx.provenance.model_dump() if tx.provenance else None
            else:
                tx_data["player_id"] = "HIDDEN"
                tx_data["player_name"] = "Anonymous Player"
                tx_data["provenance"] = None
            client_transactions.append(tx_data)

        return {
            "game_id": self.game_id,
            "room_seed": self.room_seed,
            "current_year": self.current_year,
            "current_phase": self.current_phase,
            "current_slot_index": self.current_slot_index,
            "cash_balance": self.cash_balance,
            "slots": client_slots,
            "shortlists": client_shortlists,
            "transaction_history": client_transactions,
            "event_log": list(self.event_log),
            "state_version": self.state_version,
            "is_completed": self.is_completed,
            "final_net_worth": self.final_net_worth,
            "final_squad_valuation": self.final_squad_valuation,
            "settlement_records": (
                [r.model_dump() for r in self.settlement_records] if is_revealed else []
            ),
        }
