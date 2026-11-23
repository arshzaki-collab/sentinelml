"""Unit tests for DuckDB analytical database manager."""

import gzip
from pathlib import Path

from blindbillion.data.db import DuckDBManager


def test_duckdb_manager_initialization(tmp_path: Path) -> None:
    db_file = tmp_path / "test.duckdb"
    manager = DuckDBManager(db_path=db_file)
    manager.initialize_metadata_tables()

    with manager.get_connection() as con:
        tables = con.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert "ingestion_runs" in table_names


def test_duckdb_manager_ingest_raw_table(tmp_path: Path) -> None:
    db_file = tmp_path / "test.duckdb"
    manager = DuckDBManager(db_path=db_file)
    manager.initialize_metadata_tables()

    csv_gz = tmp_path / "competitions.csv.gz"
    with gzip.open(csv_gz, "wt", encoding="utf-8") as gz:
        gz.write("competition_id,name,type\n")
        gz.write("GB1,Premier League,first_tier\n")
        gz.write("ES1,La Liga,first_tier\n")

    count = manager.ingest_raw_table(
        table_name="competitions",
        csv_gz_path=csv_gz,
        data_source="test_source",
    )
    assert count == 2

    counts = manager.get_table_counts()
    assert counts.get("raw_competitions") == 2

    # Verify ingestion log record
    with manager.get_connection() as con:
        log = con.execute("SELECT table_name, row_count, status FROM ingestion_runs").fetchone()
        assert log is not None
        assert log[0] == "raw_competitions"
        assert log[1] == 2
        assert log[2] == "SUCCESS"
