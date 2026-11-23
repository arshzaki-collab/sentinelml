"""Abstract interface for dataset providers."""

from abc import ABC, abstractmethod
from pathlib import Path


class DataPipelineProvider(ABC):
    """Abstract interface for downloading and supplying historical football data."""

    @abstractmethod
    def download_table(self, table_name: str, target_dir: Path, force: bool = False) -> Path:
        """Download or fetch a single table asset.

        Args:
            table_name: Canonical name of the table (e.g. 'players', 'player_valuations').
            target_dir: Local directory to store raw assets.
            force: If True, redownload even if local cache exists.

        Returns:
            Path to the downloaded file.
        """
        raise NotImplementedError

    @abstractmethod
    def download_all(self, target_dir: Path, force: bool = False) -> dict[str, Path]:
        """Download all approved source tables.

        Args:
            target_dir: Local directory to store raw assets.
            force: If True, redownload even if local cache exists.

        Returns:
            Dictionary mapping table names to their local file Paths.
        """
        raise NotImplementedError

    @abstractmethod
    def get_source_identifier(self) -> str:
        """Return the unique provenance identifier for this data provider."""
        raise NotImplementedError
