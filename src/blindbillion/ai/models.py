"""Domain models and schemas for AI opponents in Blind Billion 2.0."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AIDifficulty(StrEnum):
    """Supported difficulty tiers for AI opponents."""

    ROOKIE = "ROOKIE"
    PRO = "PRO"
    LEGEND = "LEGEND"


class ActionType(StrEnum):
    """Action chosen by an AI opponent."""

    BUY = "BUY"
    HOLD = "HOLD"
    SELL_AND_REPLACE = "SELL_AND_REPLACE"
    ADVANCE = "ADVANCE"


class CandidateScore(BaseModel):
    """Scoring breakdown for an individual shortlist candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_token: str
    cost_usd: float
    raw_performance_score: float
    age_adjustment_factor: float
    cost_efficiency_score: float
    final_score: float
    confidence: float = 1.0


class AIDecision(BaseModel):
    """Authoritative decision payload emitted by an AI agent."""

    model_config = ConfigDict(frozen=True)

    difficulty: AIDifficulty
    year: int
    action_type: ActionType
    slot_index: int | None = None
    selected_candidate_token: str | None = None
    reasoning: str = ""
    scores: tuple[CandidateScore, ...] = Field(default_factory=tuple)
