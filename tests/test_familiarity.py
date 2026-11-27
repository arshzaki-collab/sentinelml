"""Unit tests for FamiliarityRegistry and 2-1-1 shortlist composition."""

from pathlib import Path

import duckdb
import pytest

from blindbillion.constants import SQUAD_SLOTS
from blindbillion.data.familiarity import FamiliarityRegistry
from blindbillion.data.shortlist import ShortlistGenerator


def test_familiarity_registry_tier_classification() -> None:
    registry = FamiliarityRegistry()

    # Cristiano Ronaldo (8198) and Lionel Messi (28003) must be Tier 1 across all scouting years
    assert registry.get_tier(8198, 2016) == 1
    assert registry.get_tier(8198, 2024) == 1
    assert registry.get_tier(28003, 2016) == 1
    assert registry.get_tier(28003, 2024) == 1

    # Temporal breakout: Kylian Mbappé (342229)
    # In 2016: Not yet a global superstar (Tier 2 breakout prospect)
    assert registry.get_tier(342229, 2016) == 2
    # In 2018+: World Cup winner & global superstar (Tier 1)
    assert registry.get_tier(342229, 2018) == 1


def test_top_five_league_fallback_to_tier_three() -> None:
    registry = FamiliarityRegistry()

    # Unregistered player playing in Premier League (GB1) or La Liga (ES1) falls back to Tier 3
    assert registry.get_tier("UNREGISTERED_PLAYER_1", 2018, domestic_league_code="GB1") == 3
    assert registry.get_tier("UNREGISTERED_PLAYER_2", 2020, domestic_league_code="ES1") == 3

    # Unregistered player in an obscure/lower league without fallback returns None (Tier 4 obscure)
    assert registry.get_tier("UNREGISTERED_PLAYER_3", 2020, domestic_league_code="RU1") is None


def test_shortlist_tier_composition_and_zero_tier_four() -> None:
    """Verify live database generates exact 2-1-1 composition and zero Tier 4 candidates."""
    db_file = Path("data/blindbillion.duckdb")
    if not db_file.exists():
        pytest.skip("Live database not found.")

    con = duckdb.connect(str(db_file), read_only=True)
    generator = ShortlistGenerator(con=con)
    registry = FamiliarityRegistry()

    # Test all 7 slots for Rookie, Pro, and Legend
    for slot_idx in range(1, len(SQUAD_SLOTS) + 1):
        slot_cfg = SQUAD_SLOTS[slot_idx - 1]
        buying_year = int(str(slot_cfg["year"]))

        # Pro difficulty: Target 2x T1, 1x T2, 1x T3
        pro_slot = generator.generate_slot_shortlist(
            slot_index=slot_idx, room_seed=f"PRO_TEST_{slot_idx}", difficulty="PRO"
        )
        assert len(pro_slot.candidates) == 4
        assert len(pro_slot.secret_player_ids) == 4

        pro_tiers = []
        for pid in pro_slot.secret_player_ids:
            row = con.execute(
                "SELECT domestic_league_code FROM player_season_stats "
                "WHERE player_id = ? AND season_year = ?",
                [pid, buying_year],
            ).fetchone()
            league = row[0] if row else None
            tier = registry.get_tier(pid, buying_year, domestic_league_code=league)
            assert tier is not None
            pro_tiers.append(tier)

        # Absolutely NO Tier 4 (None) allowed
        assert all(t in (1, 2, 3) for t in pro_tiers)
        # Should have at least two Tier 1 stars
        assert pro_tiers.count(1) >= 2

        # Legend difficulty: 2x T1, 2x T2 (elite stars only, no obscure players)
        legend_slot = generator.generate_slot_shortlist(
            slot_index=slot_idx, room_seed=f"LEGEND_TEST_{slot_idx}", difficulty="LEGEND"
        )
        assert len(legend_slot.candidates) == 4
        legend_tiers = []
        for pid in legend_slot.secret_player_ids:
            row = con.execute(
                "SELECT domestic_league_code FROM player_season_stats "
                "WHERE player_id = ? AND season_year = ?",
                [pid, buying_year],
            ).fetchone()
            league = row[0] if row else None
            tier = registry.get_tier(pid, buying_year, domestic_league_code=league)
            assert tier is not None
            legend_tiers.append(tier)

        assert all(t in (1, 2, 3) for t in legend_tiers)
        assert legend_tiers.count(1) == 2
        assert legend_tiers.count(2) == 2


def test_full_game_shortlists_mutual_exclusivity() -> None:
    """Verify full game shortlists across all 7 slots contain no duplicate players."""
    db_file = Path("data/blindbillion.duckdb")
    if not db_file.exists():
        pytest.skip("Live database not found.")

    con = duckdb.connect(str(db_file), read_only=True)
    generator = ShortlistGenerator(con=con)

    for seed in ("SEED_A", "SEED_B", "SEED_C"):
        full_shortlists = generator.generate_full_game_shortlists(room_seed=seed, difficulty="PRO")
        assert len(full_shortlists) == 7

        all_player_ids: list[str] = []
        for _slot_idx, slot in full_shortlists.items():
            assert len(slot.secret_player_ids) == 4
            all_player_ids.extend(slot.secret_player_ids)

        # 7 slots * 4 candidates = exactly 28 unique candidate presentations
        assert len(all_player_ids) == 28
        assert len(set(all_player_ids)) == 28
