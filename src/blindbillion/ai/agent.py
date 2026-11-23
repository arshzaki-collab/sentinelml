"""Autonomous AI agents with distinct difficulty profiles and temporal isolation."""

from __future__ import annotations

import logging
import math
import random
from typing import Final

from blindbillion.ai.evaluator import CandidateEvaluator
from blindbillion.ai.models import ActionType, AIDecision, AIDifficulty, CandidateScore
from blindbillion.ai.temporal_guard import AIObservationContext, TemporalGuard
from blindbillion.engine.engine import GameEngine
from blindbillion.engine.models import GamePhase, GameState

logger = logging.getLogger(__name__)


class AIAgent:
    """Server-side autonomous agent playing Blind Billion 2.0."""

    def __init__(self, difficulty: AIDifficulty, seed: int | str | None = None) -> None:
        self.difficulty: Final[AIDifficulty] = difficulty
        self.seed = seed
        self.rng = random.Random(seed)

    def _select_probabilistic(
        self, scored: list[tuple[CandidateScore, float]], temperature: float
    ) -> CandidateScore:
        """Select candidate using Boltzmann exploration over scores."""
        scores = [s[1] for s in scored]
        max_s = max(scores)
        exp_weights = [math.exp((s - max_s) / temperature) for s in scores]
        total_weight = sum(exp_weights)
        probs = [w / total_weight for w in exp_weights]

        r = self.rng.random()
        cumulative = 0.0
        for idx, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return scored[idx][0]
        return scored[-1][0]

    def select_buying_candidate(
        self, context: AIObservationContext, unfilled_slots_count: int
    ) -> AIDecision:
        """Select a candidate from the temporally isolated observation context."""
        affordable = [c for c in context.candidates if c.cost_usd <= context.cash_balance]

        if not affordable:
            cheapest = min(context.candidates, key=lambda c: c.cost_usd)
            return AIDecision(
                difficulty=self.difficulty,
                year=context.as_of_year,
                action_type=ActionType.BUY,
                slot_index=context.active_slot_index,
                selected_candidate_token=cheapest.candidate_token,
                reasoning=f"Insolvent: selecting cheapest candidate (${cheapest.cost_usd:,.2f}).",
            )

        scored_candidates: list[CandidateScore] = [
            CandidateEvaluator.score_candidate(
                candidate=c,
                difficulty=self.difficulty,
                context=context,
                unfilled_slots_count=unfilled_slots_count,
                rng=self.rng,
            )
            for c in affordable
        ]

        if self.difficulty == AIDifficulty.ROOKIE:
            scored_pairs = [(sc, sc.final_score) for sc in scored_candidates]
            chosen = self._select_probabilistic(scored_pairs, temperature=1.5)
            reason = f"Rookie probabilistic selection (score={chosen.final_score:.2f})."
        else:
            # Pro and Legend use argmax with secondary tie-break on lower cost
            chosen = max(scored_candidates, key=lambda s: (s.final_score, -s.cost_usd))
            reason = (
                f"{self.difficulty} value selection (score={chosen.final_score:.2f}, "
                f"efficiency={chosen.cost_efficiency_score:.2f})."
            )

        return AIDecision(
            difficulty=self.difficulty,
            year=context.as_of_year,
            action_type=ActionType.BUY,
            slot_index=context.active_slot_index,
            selected_candidate_token=chosen.candidate_token,
            reasoning=reason,
            scores=tuple(scored_candidates),
        )

    def _should_pro_replace(
        self, replacement_candidate_token: str, context: AIObservationContext
    ) -> bool:
        """Pro transfer logic: evaluate whether replacement offers superior upside."""
        cand = next(
            (c for c in context.candidates if c.candidate_token == replacement_candidate_token),
            None,
        )
        if not cand:
            return False

        if cand.cost_usd > context.cash_balance:
            return False

        rep_score = CandidateEvaluator.score_candidate(
            candidate=cand,
            difficulty=self.difficulty,
            context=context,
            unfilled_slots_count=1,
            rng=self.rng,
        )
        return rep_score.final_score > 35.0

    def _should_legend_replace(
        self, replacement_candidate_token: str, context: AIObservationContext
    ) -> bool:
        """Legend transfer logic: evaluate strategic resale arbitrage and portfolio upgrade."""
        cand = next(
            (c for c in context.candidates if c.candidate_token == replacement_candidate_token),
            None,
        )
        if not cand:
            return False

        if cand.cost_usd > context.cash_balance:
            return False

        rep_score = CandidateEvaluator.score_candidate(
            candidate=cand,
            difficulty=self.difficulty,
            context=context,
            unfilled_slots_count=1,
            rng=self.rng,
        )
        return rep_score.cost_efficiency_score >= 8.5

    def evaluate_transfer_window_action(self, state: GameState, slot_index: int) -> str | None:
        """Evaluate a specific slot during transfer window and return replacement token or None."""
        slot = state.slots[slot_index - 1]
        if not slot.is_filled or slot.buying_year >= state.current_year:
            return None

        # Extract temporally isolated and server-filtered replacement candidate pool
        context = TemporalGuard.extract_transfer_window_observation(
            state=state, slot_index=slot_index
        )
        available_cands = list(context.candidates)
        if not available_cands:
            return None

        if self.difficulty == AIDifficulty.ROOKIE:
            # Rookie: 20% random chance to rebalance if an affordable replacement exists
            if self.rng.random() < 0.20:
                affordable = [c for c in available_cands if c.cost_usd <= state.cash_balance]
                if affordable:
                    return self.rng.choice(affordable).candidate_token
            return None

        # Pro & Legend: find highest scoring available replacement candidate
        best_cand = max(
            available_cands,
            key=lambda c: (
                CandidateEvaluator.score_candidate(
                    c, self.difficulty, context, 1, self.rng
                ).final_score
            ),
        )

        if self.difficulty == AIDifficulty.PRO and self._should_pro_replace(
            best_cand.candidate_token, context
        ):
            return best_cand.candidate_token

        if self.difficulty == AIDifficulty.LEGEND and self._should_legend_replace(
            best_cand.candidate_token, context
        ):
            return best_cand.candidate_token

        return None

    def play_turn(self, state: GameState, engine: GameEngine) -> GameState:
        """Execute a single server-authoritative turn action for this AI agent."""
        if state.is_completed:
            return state

        if state.current_phase == GamePhase.BUYING_SEASON:
            unfilled = 7 - state.filled_slots_count
            context = TemporalGuard.extract_buying_observation(state=state)
            decision = self.select_buying_candidate(context=context, unfilled_slots_count=unfilled)
            assert decision.selected_candidate_token is not None
            return engine.purchase_candidate(
                state=state, candidate_token=decision.selected_candidate_token
            )

        if state.current_phase == GamePhase.TRANSFER_WINDOW:
            current_state = state
            # Inspect each eligible slot
            for slot_idx in range(1, len(state.slots) + 1):
                slot = current_state.slots[slot_idx - 1]
                if slot.buying_year < current_state.current_year and slot.is_filled:
                    replacement_token = self.evaluate_transfer_window_action(
                        state=current_state, slot_index=slot_idx
                    )
                    if replacement_token:
                        current_state = engine.replace_player(
                            state=current_state,
                            slot_index=slot_idx,
                            replacement_candidate_token=replacement_token,
                        )
            return current_state

        return state

    def autoplay_game(self, initial_state: GameState, engine: GameEngine) -> GameState:
        """Autoplay game session from initial state through 2026 final settlement."""
        current_state = initial_state

        while not current_state.is_completed:
            if current_state.current_phase in (
                GamePhase.BUYING_SEASON,
                GamePhase.TRANSFER_WINDOW,
            ):
                current_state = self.play_turn(state=current_state, engine=engine)
                current_state = engine.advance_season(current_state)
            else:
                current_state = engine.finalize_game(current_state)

        return current_state
