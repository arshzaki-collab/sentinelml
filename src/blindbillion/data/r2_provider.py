"""Cloudflare R2 dataset provider implementation for dcaribou/transfermarkt-datasets."""

import gzip
import logging
from pathlib import Path

import httpx

from blindbillion.constants import CORE_TABLE_FILES, R2_DATASET_BASE_URL
from blindbillion.data.provider import DataPipelineProvider

logger = logging.getLogger(__name__)


class TransfermarktR2Provider(DataPipelineProvider):
    """Downloads raw Transfermarkt dataset tables from public Cloudflare R2 mirror."""

    def __init__(self, base_url: str = R2_DATASET_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.table_files = dict(CORE_TABLE_FILES)

    def get_source_identifier(self) -> str:
        return f"dcaribou/transfermarkt-datasets@r2 ({self.base_url})"

    def download_table(self, table_name: str, target_dir: Path, force: bool = False) -> Path:
        """Download a single table file with streaming and gzip verification."""
        if table_name not in self.table_files:
            raise ValueError(
                f"Unknown table '{table_name}'. Supported tables: {list(self.table_files.keys())}"
            )

        filename = self.table_files[table_name]
        url = f"{self.base_url}/{filename}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename

        if target_path.exists() and not force and target_path.stat().st_size > 0:
            if self._verify_gzip(target_path):
                logger.info("Using cached table '%s' at %s", table_name, target_path)
                return target_path
            logger.warning("Cached file %s is corrupt, re-downloading...", target_path)

        logger.info("Downloading %s from %s...", table_name, url)
        temp_path = target_path.with_suffix(".tmp")

        try:
            with (
                httpx.Client(timeout=120.0, follow_redirects=True) as client,
                client.stream("GET", url) as response,
            ):
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):  # 1MB chunks
                        if chunk:
                            f.write(chunk)

            if not self._verify_gzip(temp_path):
                raise ValueError(f"Downloaded file for {table_name} failed gzip integrity check")

            temp_path.replace(target_path)
            logger.info(
                "Successfully downloaded %s (%d bytes)", table_name, target_path.stat().st_size
            )
            return target_path

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            logger.error("Failed to download %s: %s", table_name, e)
            raise

    def download_all(self, target_dir: Path, force: bool = False) -> dict[str, Path]:
        """Download all core tables sequentially and return their local paths."""
        results: dict[str, Path] = {}
        for table_name in self.table_files:
            results[table_name] = self.download_table(
                table_name=table_name, target_dir=target_dir, force=force
            )
        return results

    @staticmethod
    def _verify_gzip(file_path: Path) -> bool:
        """Check that the file is a valid, readable gzip archive."""
        try:
            with gzip.open(file_path, "rb") as gz:
                # Read first 100 bytes to ensure header is valid
                header = gz.read(100)
                return len(header) > 0
        except Exception:
            return False
