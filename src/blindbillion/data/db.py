"""DuckDB analytical storage manager and raw table ingestion engine."""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/blindbillion.duckdb")


def get_analytical_db_path() -> Path:
    """Resolve analytical DuckDB cache path from environment or default."""
    env_path = os.environ.get("ANALYTICAL_DB_PATH")
    if env_path and env_path.strip():
        p = Path(env_path.strip())
        return p if p.is_absolute() else Path.cwd() / p
    return Path.cwd() / "data" / "blindbillion.duckdb"


REQUIRED_ANALYTICAL_TABLES: tuple[str, ...] = (
    "raw_players",
    "player_annual_valuations",
    "player_season_stats",
)


def validate_analytical_database(
    db_path: Path | str | None = None,
) -> tuple[bool, str, list[str]]:
    """Validate existence, readability, and required analytical tables.

    Returns:
        tuple of (is_valid: bool, status_code: str, details_or_missing_tables: list[str])
    """
    path = Path(db_path) if db_path is not None else get_analytical_db_path()
    if not path.exists():
        return False, "missing_database", [f"File not found: {path}"]
    if not os.access(path, os.R_OK):
        return False, "unreadable_database", [f"Permission denied: {path}"]

    try:
        con = duckdb.connect(str(path), read_only=True)
        tables = {
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
        con.close()

        missing: list[str] = []
        for tbl in REQUIRED_ANALYTICAL_TABLES:
            if tbl == "player_annual_valuations":
                if (
                    "player_annual_valuations" not in tables
                    and "materialized_valuations" not in tables
                ):
                    missing.append("player_annual_valuations")
            elif tbl not in tables:
                missing.append(tbl)

        if missing:
            return False, "missing_tables", missing
        return True, "connected", []
    except Exception as exc:  # noqa: BLE001
        return False, "database_error", [str(exc)]


class DuckDBManager:
    """Manages the local DuckDB analytical database for Blind Billion 2.0."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else get_analytical_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Create and return a new DuckDB connection."""
        return duckdb.connect(str(self.db_path))

    def initialize_metadata_tables(self) -> None:
        """Initialize tracking tables for provenance and ingestion logs."""
        with self.get_connection() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_runs (
                    run_id VARCHAR PRIMARY KEY,
                    table_name VARCHAR NOT NULL,
                    source_path VARCHAR NOT NULL,
                    data_source VARCHAR NOT NULL,
                    row_count BIGINT NOT NULL,
                    status VARCHAR NOT NULL,
                    imported_at TIMESTAMP NOT NULL
                );
            """)

    def ingest_raw_table(
        self,
        table_name: str,
        csv_gz_path: Path | str,
        data_source: str,
        run_id: str | None = None,
    ) -> int:
        """Ingest a gzipped CSV table into DuckDB with schema inference and type safety.

        Args:
            table_name: Target raw table name (e.g. 'competitions' -> 'raw_competitions').
            csv_gz_path: Absolute or relative path to the .csv.gz file.
            data_source: Provenance identifier string.
            run_id: Optional tracking identifier.

        Returns:
            The number of rows imported into the table.
        """
        raw_table = f"raw_{table_name}"
        csv_path_str = str(Path(csv_gz_path).resolve())
        actual_run_id = run_id or f"run_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{table_name}"

        logger.info("Ingesting %s into %s from %s...", table_name, raw_table, csv_path_str)

        with self.get_connection() as con:
            # Recreate raw table deterministically
            con.execute(f"""
                CREATE OR REPLACE TABLE {raw_table} AS
                SELECT * FROM read_csv_auto(
                    '{csv_path_str}',
                    header=true,
                    all_varchar=false,
                    ignore_errors=false
                );
            """)

            row_count_res = con.execute(f"SELECT COUNT(*) FROM {raw_table}").fetchone()
            row_count: int = row_count_res[0] if row_count_res else 0

            # Record provenance log
            con.execute(
                """
                INSERT INTO ingestion_runs (
                    run_id, table_name, source_path, data_source, row_count, status, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
                [
                    actual_run_id,
                    raw_table,
                    csv_path_str,
                    data_source,
                    row_count,
                    "SUCCESS",
                    datetime.now(UTC),
                ],
            )

            logger.info("Imported %d rows into %s", row_count, raw_table)
            return row_count

    def ingest_all_raw_tables(
        self,
        downloaded_tables: dict[str, Path],
        data_source: str,
    ) -> dict[str, int]:
        """Ingest all downloaded tables and return their row counts."""
        self.initialize_metadata_tables()
        run_id = f"batch_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        counts: dict[str, int] = {}

        for table_name, path in downloaded_tables.items():
            count = self.ingest_raw_table(
                table_name=table_name,
                csv_gz_path=path,
                data_source=data_source,
                run_id=f"{run_id}_{table_name}",
            )
            counts[table_name] = count

        return counts

    def get_table_counts(self) -> dict[str, int]:
        """Return row counts for all raw tables in the database."""
        with self.get_connection() as con:
            tables = con.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'main' AND table_name LIKE 'raw_%'
            """).fetchall()

            counts: dict[str, int] = {}
            for (tbl,) in tables:
                cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
                counts[tbl] = cnt[0] if cnt else 0
            return counts
