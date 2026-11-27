"""Deterministic, reproducible 4-player shortlist generator and anonymous hint masking engine."""

import hashlib
import logging
import random
import uuid
from typing import Final

import duckdb

from blindbillion.constants import (
    CANDIDATES_PER_SLOT,
    SQUAD_SLOTS,
    TRANSFER_WINDOWS,
)
from blindbillion.data.familiarity import FamiliarityRegistry
from blindbillion.data.models import PositionType, ScoutingHints, ShortlistSlot
from blindbillion.data.stats import POSITION_CATEGORY_MAP

logger = logging.getLogger(__name__)

FINAL_VALUATION_YEAR: Final[int] = 2026


class ShortlistGenerator:
    """Generates server-authoritative 4-candidate shortlists with anonymous 3-hint veils."""

    def __init__(
        self,
        con: duckdb.DuckDBPyConnection,
        familiarity_registry: FamiliarityRegistry | None = None,
    ) -> None:
        self.con = con
        self.familiarity_registry = familiarity_registry or FamiliarityRegistry()

    def get_eligible_candidates(
        self, buying_year: int, position: PositionType
    ) -> list[dict[str, object]]:
        """Retrieve all players eligible for a specific buying year and position.

        Eligibility criteria:
        1. Sub-position matches the target position category.
        2. Valid historical valuation exists in buying_year ($T_obs <= 180 days).
        3. Match appearances in preceding season > 0.
        4. Continuous valuation exists in 2026 (final settlement) and all relevant transfer windows.
        """
        sub_positions = POSITION_CATEGORY_MAP[position]

        # Milestone years that this slot might be held across
        required_milestone_years = [buying_year, FINAL_VALUATION_YEAR]
        for tw in TRANSFER_WINDOWS:
            if tw > buying_year:
                required_milestone_years.append(tw)

        required_milestones_count = len(required_milestone_years)

        query = f"""
            WITH milestone_coverage AS (
                SELECT
                    player_id,
                    COUNT(DISTINCT reference_year) AS covered_milestones
                FROM player_annual_valuations
                WHERE reference_year IN ({",".join(str(y) for y in required_milestone_years)})
                GROUP BY player_id
                HAVING COUNT(DISTINCT reference_year) = {required_milestones_count}
            )
            SELECT
                stats.player_id,
                stats.player_name,
                stats.sub_position,
                stats.age_at_reference,
                stats.domestic_league_code,
                stats.domestic_league_name,
                stats.appearances,
                stats.goals,
                stats.assists,
                stats.yellow_cards + stats.red_cards AS total_cards,
                stats.clean_sheets,
                stats.ucl_appearances,
                stats.ucl_goals,
                val.converted_usd_value AS cost_usd,
                val.original_value AS cost_eur
            FROM player_season_stats stats
            JOIN milestone_coverage mc
              ON stats.player_id = mc.player_id
            JOIN player_annual_valuations val
              ON stats.player_id = val.player_id
             AND stats.season_year = val.reference_year
            WHERE stats.season_year = ?
              AND stats.sub_position IN ({",".join(f"'{p}'" for p in sub_positions)})
              AND stats.appearances > 0
              AND val.converted_usd_value > 0
            ORDER BY val.converted_usd_value DESC, stats.player_id ASC;
        """

        rows = self.con.execute(query, [buying_year]).fetchall()
        columns = [
            "player_id",
            "player_name",
            "sub_position",
            "age_at_reference",
            "domestic_league_code",
            "domestic_league_name",
            "appearances",
            "goals",
            "assists",
            "total_cards",
            "clean_sheets",
            "ucl_appearances",
            "ucl_goals",
            "cost_usd",
            "cost_eur",
        ]

        return [dict(zip(columns, r, strict=True)) for r in rows]

    def generate_slot_shortlist(
        self,
        slot_index: int,
        room_seed: int | str,
        difficulty: str = "PRO",
        excluded_player_ids: set[str] | None = None,
    ) -> ShortlistSlot:
        """Deterministically generate exactly 4 candidates for a given squad slot index (1-7).

        Familiarity Composition:
        - Target: 2x Tier 1 (Superstars), 1x Tier 2 (Well-Known), 1x Tier 3 (Top-Flight).
        - Legend: 2x Tier 1, 2x Tier 2 (closely matched elite stars, no obscure difficulty).
        - Tier 4 obscure players are strictly filtered out.
        """
        if slot_index < 1 or slot_index > len(SQUAD_SLOTS):
            raise ValueError(f"Invalid slot index {slot_index}. Must be 1 to 7.")

        slot_cfg = SQUAD_SLOTS[slot_index - 1]
        buying_year = int(str(slot_cfg["year"]))
        position = str(slot_cfg["position"])  # ST, WG, CM, CB, GK

        eligible = self.get_eligible_candidates(buying_year=buying_year, position=position)  # type: ignore[arg-type]
        if excluded_player_ids:
            filtered_eligible = [
                c for c in eligible if str(c["player_id"]) not in excluded_player_ids
            ]
            if len(filtered_eligible) >= CANDIDATES_PER_SLOT:
                eligible = filtered_eligible

        if len(eligible) < CANDIDATES_PER_SLOT:
            raise RuntimeError(
                f"Insufficient eligible candidates ({len(eligible)}) for slot {slot_index} "
                f"({buying_year} {position}). Requires at least {CANDIDATES_PER_SLOT}."
            )

        # Partition eligible candidates into verified familiarity tiers (as of scouting year)
        t1_candidates: list[dict[str, object]] = []
        t2_candidates: list[dict[str, object]] = []
        t3_candidates: list[dict[str, object]] = []

        for c in eligible:
            league_code = str(c.get("domestic_league_code") or "")
            tier = self.familiarity_registry.get_tier(
                str(c["player_id"]),
                buying_year,
                domestic_league_code=league_code,
            )
            if tier == 1:
                t1_candidates.append(c)
            elif tier == 2:
                t2_candidates.append(c)
            elif tier == 3:
                t3_candidates.append(c)

        total_familiar = len(t1_candidates) + len(t2_candidates) + len(t3_candidates)
        if total_familiar < CANDIDATES_PER_SLOT:
            raise RuntimeError(
                f"Insufficient verified familiar candidates ({total_familiar}) "
                f"for slot {slot_index} ({buying_year} {position}). "
                f"Requires at least {CANDIDATES_PER_SLOT}."
            )

        # Derive a deterministic integer seed from room_seed + slot_index + difficulty
        seed_str = f"{room_seed}_{slot_index}_{buying_year}_{position}_{difficulty.upper()}"
        derived_seed = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(derived_seed)

        # Sort within tiers deterministically on player_id
        t1_candidates.sort(key=lambda x: str(x["player_id"]))
        t2_candidates.sort(key=lambda x: str(x["player_id"]))
        t3_candidates.sort(key=lambda x: str(x["player_id"]))

        selected_players: list[dict[str, object]] = []
        diff_upper = difficulty.upper()

        if diff_upper == "LEGEND" and len(t1_candidates) >= 2 and len(t2_candidates) >= 2:
            # Legend: 2x Tier 1 and 2x Tier 2 (closely matched famous stars, no obscure names)
            selected_players.extend(rng.sample(t1_candidates, k=2))
            selected_players.extend(rng.sample(t2_candidates, k=2))
        else:
            # Rookie / Pro / Default: 2x Tier 1, 1x Tier 2, 1x Tier 3
            num_t1 = min(2, len(t1_candidates))
            selected_players.extend(rng.sample(t1_candidates, k=num_t1))

            remaining_needed = CANDIDATES_PER_SLOT - len(selected_players)
            if t2_candidates and remaining_needed > 0:
                num_t2 = min(1 if t3_candidates else remaining_needed, len(t2_candidates))
                selected_players.extend(rng.sample(t2_candidates, k=num_t2))

            remaining_needed = CANDIDATES_PER_SLOT - len(selected_players)
            if t3_candidates and remaining_needed > 0:
                num_t3 = min(remaining_needed, len(t3_candidates))
                selected_players.extend(rng.sample(t3_candidates, k=num_t3))

            # If still needed, fill from remaining verified pools
            remaining_needed = CANDIDATES_PER_SLOT - len(selected_players)
            if remaining_needed > 0:
                unused_pool = [
                    c for c in (t1_candidates + t2_candidates + t3_candidates)
                    if c not in selected_players
                ]
                if len(unused_pool) >= remaining_needed:
                    selected_players.extend(rng.sample(unused_pool, k=remaining_needed))
                else:
                    raise RuntimeError(
                        f"Shortage of familiar candidates for slot {slot_index} "
                        f"({buying_year} {position})."
                    )

        # Shuffle presentation order deterministically so card index does not reveal tier
        rng.shuffle(selected_players)

        secret_ids: list[str] = []
        scouting_candidates: list[ScoutingHints] = []

        for p in selected_players:
            pid = str(p["player_id"])
            secret_ids.append(pid)

            # Generate consistent candidate UUID derived from candidate + room seed
            token_seed = f"{room_seed}_{slot_index}_{pid}"
            token_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, token_seed))

            cand_seed_int = int(hashlib.sha256(token_seed.encode("utf-8")).hexdigest()[:8], 16)
            candidate_rng = random.Random(cand_seed_int)
            hints = self._build_position_hints(p, position=position, rng=candidate_rng)

            scouting_candidates.append(
                ScoutingHints(
                    candidate_token=token_uuid,
                    cost_usd=float(str(p["cost_usd"])),
                    position=position,  # type: ignore[arg-type]
                    hints=hints,
                )
            )

        return ShortlistSlot(
            slot_index=slot_index,
            buying_year=buying_year,
            position=position,  # type: ignore[arg-type]
            candidates=scouting_candidates,
            secret_player_ids=secret_ids,
        )

    def generate_full_game_shortlists(
        self,
        room_seed: int | str,
        difficulty: str = "PRO",
    ) -> dict[int, ShortlistSlot]:
        """Generate shortlists for all 7 squad buying seasons deterministically.

        Ensures no player is presented in multiple shortlists within the same game.
        """
        shortlists: dict[int, ShortlistSlot] = {}
        used_player_ids: set[str] = set()
        for slot_idx in range(1, len(SQUAD_SLOTS) + 1):
            slot = self.generate_slot_shortlist(
                slot_index=slot_idx,
                room_seed=room_seed,
                difficulty=difficulty,
                excluded_player_ids=used_player_ids,
            )
            used_player_ids.update(slot.secret_player_ids)
            shortlists[slot_idx] = slot
        return shortlists

    @staticmethod
    def _build_position_hints(
        player: dict[str, object],
        position: str,
        rng: random.Random,
    ) -> dict[str, str | int]:
        """Construct the exact 3 authorized hints according to position rules."""
        age_val = player["age_at_reference"]
        age = int(str(age_val)) if age_val is not None else 25
        raw_league = player["domestic_league_name"]
        league = str(raw_league) if raw_league else "European League"
        goals = int(str(player["goals"]))
        assists = int(str(player["assists"]))
        clean_sheets = int(str(player["clean_sheets"]))
        total_cards = int(str(player["total_cards"]))
        ucl_goals = int(str(player["ucl_goals"]))

        hints: dict[str, str | int] = {}

        if position in ("ST", "WG"):
            # Forwards: Goals compulsory; 2 from {Age, Assists, Domestic League, UCL Goals}
            hints["Goals"] = goals
            options: list[tuple[str, str | int]] = [
                ("Age", age),
                ("Assists", assists),
                ("League", league),
                ("UCL Goals", ucl_goals),
            ]
            picked = rng.sample(options, k=2)
            for k, v in picked:
                hints[k] = v

        elif position == "CM":
            # Midfielders: Assists compulsory; 2 from {Age, Goals, Cards, Domestic League}
            hints["Assists"] = assists
            options = [
                ("Age", age),
                ("Goals", goals),
                ("Cards", total_cards),
                ("League", league),
            ]
            picked = rng.sample(options, k=2)
            for k, v in picked:
                hints[k] = v

        elif position == "CB":
            # Defenders: Clean sheets compulsory; 2 from {Age, Goals, Cards, Domestic League}
            hints["Clean Sheets"] = clean_sheets
            options = [
                ("Age", age),
                ("Goals", goals),
                ("Cards", total_cards),
                ("League", league),
            ]
            picked = rng.sample(options, k=2)
            for k, v in picked:
                hints[k] = v

        elif position == "GK":
            # Goalkeepers: Exactly Clean Sheets, Age, League
            hints["Clean Sheets"] = clean_sheets
            hints["Age"] = age
            hints["League"] = league

        return hints
