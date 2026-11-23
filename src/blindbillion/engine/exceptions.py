"""Domain exceptions for the Blind Billion 2.0 game engine."""

from __future__ import annotations


class BlindBillionEngineError(Exception):
    """Base exception for all game engine validation and runtime failures."""


class TimelineError(BlindBillionEngineError):
    """Raised when an invalid timeline transition or step index lookup occurs."""


class InvalidGameActionError(BlindBillionEngineError):
    """Raised when an action is illegal under current game state."""


class InsufficientFundsError(BlindBillionEngineError):
    """Raised when an attempted purchase or replacement exceeds remaining cash."""


class InvalidSlotError(BlindBillionEngineError):
    """Raised when referencing an invalid squad slot (valid range 1 to 7)."""


class InvalidPhaseError(BlindBillionEngineError):
    """Raised when an action is attempted outside its designated phase or year."""


class SlotAlreadyFilledError(BlindBillionEngineError):
    """Raised when attempting to buy a player for a slot that is already occupied."""


class DuplicatePlayerError(BlindBillionEngineError):
    """Raised when attempting to sign a player already present in the squad."""


class TransferNotAllowedError(BlindBillionEngineError):
    """Raised when transfer actions are attempted outside scheduled transfer windows."""


class InvalidReplacementCandidateError(BlindBillionEngineError):
    """Raised when replacement candidate is not from the slot's original 4-player shortlist."""


class MissingValuationError(BlindBillionEngineError):
    """Raised when an authoritative historical valuation cannot be found."""
