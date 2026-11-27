"""Version-controlled historical football familiarity registry."""

import json
import logging
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH: Final[Path] = Path(__file__).parent / "familiarity_registry.json"


class FamiliarityRegistry:
    """Manages manually reviewed, version-controlled player familiarity tiers.

    Tiers:
    - Tier 1: Globally famous household names.
    - Tier 2: Well-known players recognised by regular football fans.
    - Tier 3: Less obvious but still recognisable players from major top flights.
    - Tier 4: Obscure / regional / unrecognisable (excluded from game shortlists).
    """

    def __init__(
        self,
        registry_path: Path | str | None = None,
        default_unregistered_tier: int | None = None,
    ) -> None:
        self.registry_path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
        self.default_unregistered_tier = default_unregistered_tier
        self._data: dict[str, dict[str, object]] = {}
        self.load()

    def load(self) -> None:
        """Load the registry JSON from disk if it exists."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, encoding="utf-8") as f:
                    raw = json.load(f)
                    if (
                        isinstance(raw, dict)
                        and "players" in raw
                        and isinstance(raw["players"], dict)
                    ):
                        self._data = raw["players"]
                    elif isinstance(raw, dict):
                        self._data = raw
                    else:
                        self._data = {}
            except Exception as e:
                logger.warning(
                    f"Failed to load familiarity registry from {self.registry_path}: {e}"
                )
                self._data = {}
        else:
            self._data = {}

    def register_player(
        self,
        player_id: str | int,
        tier: int,
        year: int | None = None,
    ) -> None:
        """Register or override a player's familiarity tier in-memory."""
        pid = str(player_id)
        if pid not in self._data:
            self._data[pid] = {
                "name": f"Player {pid}",
                "default_tier": tier,
                "tier_by_year": {},
            }
        entry = self._data[pid]
        if year is not None:
            tier_by_year = entry.setdefault("tier_by_year", {})
            if isinstance(tier_by_year, dict):
                tier_by_year[str(year)] = tier
        else:
            entry["default_tier"] = tier

    def get_tier(
        self,
        player_id: str | int,
        year: int,
        domestic_league_code: str | None = None,
    ) -> int | None:
        """Retrieve the historically accurate familiarity tier for a player as of a scouting year.

        Returns:
            1 for Tier 1 (Household Name / Superstar)
            2 for Tier 2 (Well-Known Top-5 Star)
            3 for Tier 3 (Recognisable Top-Flight Player)
            None if Tier 4 (Obscure / Unrecognisable -> Excluded)
        """
        pid = str(player_id)
        player_entry = self._data.get(pid)
        if player_entry:
            tier_by_year = player_entry.get("tier_by_year", {})
            if isinstance(tier_by_year, dict):
                yr_str = str(year)
                if yr_str in tier_by_year:
                    val = int(str(tier_by_year[yr_str]))
                    return val if val in (1, 2, 3) else None

            default_tier = player_entry.get("default_tier")
            if default_tier is not None:
                dt = int(str(default_tier))
                return dt if dt in (1, 2, 3) else None

        # Fallback for Top 5 domestic leagues (GB1, ES1, IT1, L1, FR1) -> Tier 3
        if domestic_league_code in ("GB1", "ES1", "IT1", "L1", "FR1"):
            return 3

        return self.default_unregistered_tier
