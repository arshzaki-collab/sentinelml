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
from blindbillion.data.models import PositionType, ScoutingHints, ShortlistSlot
from blindbillion.data.stats import POSITION_CATEGORY_MAP

logger = logging.getLogger(__name__)

FINAL_VALUATION_YEAR: Final[int] = 2026


class ShortlistGenerator:
    """Generates server-authoritative 4-candidate shortlists with anonymous 3-hint veils."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con

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
                WHERE reference_year IN ({','.join(str(y) for y in required_milestone_years)})
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
              AND stats.sub_position IN ({','.join(f"'{p}'" for p in sub_positions)})
              AND stats.appearances > 0
              AND val.converted_usd_value > 0
            ORDER BY val.converted_usd_value DESC;
        """

        rows = self.con.execute(query, [buying_year]).fetchall()
        columns = [
            "player_id", "player_name", "sub_position", "age_at_reference",
            "domestic_league_code", "domestic_league_name", "appearances",
            "goals", "assists", "total_cards", "clean_sheets", "ucl_appearances",
            "ucl_goals", "cost_usd", "cost_eur"
        ]

        return [dict(zip(columns, r, strict=True)) for r in rows]

    def generate_slot_shortlist(
        self,
        slot_index: int,
        room_seed: int | str,
    ) -> ShortlistSlot:
        """Deterministically generate exactly 4 candidates for a given squad slot index (1-7)."""
        if slot_index < 1 or slot_index > len(SQUAD_SLOTS):
            raise ValueError(f"Invalid slot index {slot_index}. Must be 1 to 7.")

        slot_cfg = SQUAD_SLOTS[slot_index - 1]
        buying_year = int(str(slot_cfg["year"]))
        position = str(slot_cfg["position"])  # ST, WG, CM, CB, GK

        eligible = self.get_eligible_candidates(buying_year=buying_year, position=position)  # type: ignore[arg-type]
        if len(eligible) < CANDIDATES_PER_SLOT:
            raise RuntimeError(
                f"Insufficient eligible candidates ({len(eligible)}) for slot {slot_index} "
                f"({buying_year} {position}). Requires at least {CANDIDATES_PER_SLOT}."
            )

        # Derive a deterministic integer seed from room_seed + slot_index
        seed_str = f"{room_seed}_{slot_index}_{buying_year}_{position}"
        derived_seed = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(derived_seed)

        # Stratified selection into 4 distinct valuation tiers to ensure diverse financial options
        # Sort by valuation descending
        sorted_candidates = sorted(
            eligible, key=lambda c: float(str(c["cost_usd"])), reverse=True
        )
        n = len(sorted_candidates)
        q = n // 4

        tier1 = sorted_candidates[:q]  # Top valuation tier
        tier2 = sorted_candidates[q : 2 * q]  # Upper middle tier
        tier3 = sorted_candidates[2 * q : 3 * q]  # Lower middle tier
        tier4 = sorted_candidates[3 * q :]  # Value tier

        selected_players = [
            rng.choice(tier1),
            rng.choice(tier2),
            rng.choice(tier3),
            rng.choice(tier4),
        ]

        # Shuffle presentation order deterministically
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

    def generate_full_game_shortlists(self, room_seed: int | str) -> dict[int, ShortlistSlot]:
        """Generate shortlists for all 7 squad buying seasons deterministically."""
        return {
            slot_idx: self.generate_slot_shortlist(slot_index=slot_idx, room_seed=room_seed)
            for slot_idx in range(1, len(SQUAD_SLOTS) + 1)
        }

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
