"""Feature extraction and candidate scoring engines for AI opponents."""

from __future__ import annotations

import math
import random
from typing import Final

from blindbillion.ai.models import AIDifficulty, CandidateScore
from blindbillion.ai.temporal_guard import AIObservationContext
from blindbillion.data.models import PositionType, ScoutingHints

# Top-tier European domestic leagues (codes and canonical slug names)
TOP_TIER_LEAGUES: Final[set[str]] = {
    "gb1",
    "es1",
    "it1",
    "l1",
    "fr1",
    "premier-league",
    "laliga",
    "serie-a",
    "bundesliga",
    "ligue-1",
}


def normalize_hints(hints: dict[str, str | int]) -> dict[str, str | int]:
    """Normalize dictionary keys to lowercase (e.g. 'Clean Sheets' -> 'clean_sheets')."""
    return {str(k).strip().lower().replace(" ", "_"): v for k, v in hints.items()}


class CandidateEvaluator:
    """Evaluates and scores candidates based on anonymized historical scouting hints."""

    @staticmethod
    def _extract_raw_performance(norm_hints: dict[str, str | int], position: PositionType) -> float:
        """Compute base statistical performance score from visible hint attributes."""
        goals = float(norm_hints.get("goals", 0))
        assists = float(norm_hints.get("assists", 0))
        clean_sheets = float(norm_hints.get("clean_sheets", 0))
        ucl_goals = float(norm_hints.get("ucl_goals", 0))
        cards = float(norm_hints.get("cards", 0))

        if position in ("ST", "WG"):
            return goals * 4.0 + assists * 2.5 + ucl_goals * 5.0
        if position == "CM":
            return assists * 4.0 + goals * 3.0 - cards * 0.8
        if position == "CB":
            return clean_sheets * 4.5 + goals * 2.0 - cards * 1.0
        if position == "GK":
            return clean_sheets * 5.0
        return goals + assists + clean_sheets

    @staticmethod
    def _compute_age_factor(age: int | None, position: PositionType) -> float:
        """Calculate age curve multiplier based on developmental trajectory and resale value."""
        if age is None:
            return 1.0

        if position in ("ST", "WG"):
            if age <= 23:
                return 1.30  # High growth potential & future resale
            if 24 <= age <= 28:
                return 1.00  # Prime years
            if 29 <= age <= 31:
                return 0.80  # Beginning of physical decline
            return 0.60  # Rapid depreciation

        if position in ("CM", "CB"):
            if age <= 24:
                return 1.25
            if 25 <= age <= 29:
                return 1.00
            if 30 <= age <= 32:
                return 0.85
            return 0.65

        # Goalkeeper (longer longevity)
        if age <= 25:
            return 1.20
        if 26 <= age <= 32:
            return 1.00
        if 33 <= age <= 35:
            return 0.90
        return 0.70

    @staticmethod
    def _score_rookie(
        candidate: ScoutingHints,
        raw_perf: float,
        cost_m: float,
        rng: random.Random,
    ) -> CandidateScore:
        """Rookie: primary counting stats with Gaussian exploration noise."""
        noise = rng.gauss(0.0, 3.5)
        final = max(0.1, raw_perf + noise)
        return CandidateScore(
            candidate_token=candidate.candidate_token,
            cost_usd=candidate.cost_usd,
            raw_performance_score=round(raw_perf, 2),
            age_adjustment_factor=1.0,
            cost_efficiency_score=round(raw_perf / max(1.0, cost_m), 2),
            final_score=round(final, 2),
        )

    @staticmethod
    def _score_pro(
        candidate: ScoutingHints,
        raw_perf: float,
        age_factor: float,
        cost_m: float,
        context: AIObservationContext,
        unfilled_slots_count: int,
    ) -> CandidateScore:
        """Pro: performance * age curve / cost dampener + budget awareness."""
        adjusted_perf = raw_perf * age_factor
        cost_factor = math.sqrt(max(1.0, cost_m)) + 1.0
        efficiency = (adjusted_perf / cost_factor) * 10.0

        target_budget = context.cash_balance / max(1, unfilled_slots_count)
        budget_penalty = 0.6 if candidate.cost_usd > (target_budget * 1.8) else 1.0

        final = max(0.1, efficiency * budget_penalty)
        return CandidateScore(
            candidate_token=candidate.candidate_token,
            cost_usd=candidate.cost_usd,
            raw_performance_score=round(raw_perf, 2),
            age_adjustment_factor=round(age_factor, 2),
            cost_efficiency_score=round(efficiency, 2),
            final_score=round(final, 2),
        )

    @staticmethod
    def _score_legend(
        candidate: ScoutingHints,
        raw_perf: float,
        age_factor: float,
        cost_m: float,
        norm_hints: dict[str, str | int],
        context: AIObservationContext,
        unfilled_slots_count: int,
    ) -> CandidateScore:
        """Legend: multi-attribute optimization, league tier multiplier, capital preservation."""
        league = str(norm_hints.get("league", "")).lower()
        league_mult = 1.15 if league in TOP_TIER_LEAGUES else 1.00
        adjusted_perf = raw_perf * age_factor * league_mult

        reserved_capital_floor = max(0, unfilled_slots_count - 1) * 35_000_000.0
        remaining_after_buy = context.cash_balance - candidate.cost_usd

        solvency_penalty = 1.0
        if remaining_after_buy < reserved_capital_floor:
            solvency_penalty = 0.20

        cost_factor = math.sqrt(max(1.0, cost_m)) + 0.8
        efficiency = (adjusted_perf / cost_factor) * 12.0
        final = max(0.1, efficiency * solvency_penalty)

        return CandidateScore(
            candidate_token=candidate.candidate_token,
            cost_usd=candidate.cost_usd,
            raw_performance_score=round(raw_perf, 2),
            age_adjustment_factor=round(age_factor, 2),
            cost_efficiency_score=round(efficiency, 2),
            final_score=round(final, 2),
        )

    @classmethod
    def score_candidate(
        cls,
        candidate: ScoutingHints,
        difficulty: AIDifficulty,
        context: AIObservationContext,
        unfilled_slots_count: int,
        rng: random.Random,
    ) -> CandidateScore:
        """Compute comprehensive score breakdown for a candidate under specified difficulty."""
        norm_hints = normalize_hints(candidate.hints)
        cost_m = candidate.cost_usd / 1_000_000.0

        raw_perf = cls._extract_raw_performance(norm_hints, candidate.position)
        age = int(norm_hints["age"]) if "age" in norm_hints else None
        age_factor = cls._compute_age_factor(age, candidate.position)

        if difficulty == AIDifficulty.ROOKIE:
            return cls._score_rookie(candidate, raw_perf, cost_m, rng)
        if difficulty == AIDifficulty.PRO:
            return cls._score_pro(
                candidate, raw_perf, age_factor, cost_m, context, unfilled_slots_count
            )
        return cls._score_legend(
            candidate, raw_perf, age_factor, cost_m, norm_hints, context, unfilled_slots_count
        )
