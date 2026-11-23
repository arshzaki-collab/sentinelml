"""Master pipeline runner for Blind Billion 2.0 historical data foundation."""

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from blindbillion.constants import (
    SQUAD_SLOTS,
)
from blindbillion.data.db import DEFAULT_DB_PATH, DuckDBManager
from blindbillion.data.r2_provider import TransfermarktR2Provider
from blindbillion.data.shortlist import ShortlistGenerator
from blindbillion.data.stats import StatsAggregator
from blindbillion.data.valuations import ValuationEngine

logger = logging.getLogger("blindbillion.data.pipeline")


def run_pipeline(
    raw_dir: Path = Path("data/raw"),
    db_path: Path = DEFAULT_DB_PATH,
    force_download: bool = False,
) -> dict[str, Any]:
    """Execute the end-to-end historical data ingestion and materialization pipeline.

    Steps:
    1. Download/verify core tables from Cloudflare R2 mirror.
    2. Ingest raw gzipped CSVs into DuckDB database (data/blindbillion.duckdb).
    3. Materialize annual valuations (player_annual_valuations) using July 1 dates.
    4. Materialize seasonal match performance stats (player_season_stats).
    5. Validate data integrity, schema consistency, and eligibility counts.
    6. Generate comprehensive data quality report.
    """
    start_time = datetime.now(UTC)
    raw_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "pipeline_version": "2.0.0",
        "started_at": start_time.isoformat(),
        "database_path": str(db_path),
        "raw_directory": str(raw_dir),
        "steps": {},
    }

    # Step 1: Download core tables
    logger.info("--- Step 1: Downloading core dataset tables ---")
    provider = TransfermarktR2Provider()
    downloaded_files = provider.download_all(target_dir=raw_dir, force=force_download)
    report["steps"]["download"] = {
        "source": provider.get_source_identifier(),
        "files": {tbl: str(p) for tbl, p in downloaded_files.items()},
    }

    # Step 2: Ingest into DuckDB
    logger.info("--- Step 2: Ingesting raw tables into DuckDB ---")
    db_manager = DuckDBManager(db_path=db_path)
    ingest_counts = db_manager.ingest_all_raw_tables(
        downloaded_tables=downloaded_files,
        data_source=provider.get_source_identifier(),
    )
    report["steps"]["ingestion"] = {
        "raw_table_counts": ingest_counts,
    }

    # Step 3 & 4: Materialize analytical tables
    logger.info("--- Step 3: Materializing player_annual_valuations ---")
    with db_manager.get_connection() as con:
        val_engine = ValuationEngine(con=con)
        valuations_count = val_engine.build_annual_valuations_table(
            data_source=provider.get_source_identifier()
        )
        annual_val_counts = val_engine.get_annual_valuation_counts()
        report["steps"]["valuations"] = {
            "total_materialized_observations": valuations_count,
            "observations_by_year": annual_val_counts,
        }

        logger.info("--- Step 4: Materializing player_season_stats ---")
        stats_aggregator = StatsAggregator(con=con)
        stats_count = stats_aggregator.build_season_stats_table()
        report["steps"]["stats"] = {
            "total_season_stats_rows": stats_count,
        }

        # Step 5: Data validation and shortlist verification
        logger.info("--- Step 5: Validating shortlist eligibility ---")
        shortlist_gen = ShortlistGenerator(con=con)
        slot_candidate_counts: dict[str, int] = {}

        for slot in SQUAD_SLOTS:
            idx = int(str(slot["slot_index"]))
            yr = int(str(slot["year"]))
            pos = str(slot["position"])
            eligible = shortlist_gen.get_eligible_candidates(buying_year=yr, position=pos)  # type: ignore[arg-type]
            slot_candidate_counts[f"Slot {idx} ({yr} {pos})"] = len(eligible)

        report["steps"]["eligibility"] = {
            "candidates_per_slot": slot_candidate_counts,
        }

        # Sample 4-player shortlist verification
        test_shortlist = shortlist_gen.generate_slot_shortlist(
            slot_index=1, room_seed="INTEGRITY_CHECK"
        )
        assert len(test_shortlist.candidates) == 4

    end_time = datetime.now(UTC)
    duration_sec = (end_time - start_time).total_seconds()
    report["completed_at"] = end_time.isoformat()
    report["duration_seconds"] = duration_sec
    report["status"] = "SUCCESS"

    # Write report to disk
    report_path = db_path.parent / "data_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Pipeline completed successfully in %.2f seconds", duration_sec)
    logger.info("Data quality report written to %s", report_path)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(
        description="Blind Billion 2.0 Historical Data Ingestion Pipeline"
    )
    parser.add_argument(
        "--raw-dir", type=Path, default=Path("data/raw"), help="Directory for raw files"
    )
    parser.add_argument(
        "--db-path", type=Path, default=DEFAULT_DB_PATH, help="Target DuckDB database path"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-download of raw tables"
    )

    args = parser.parse_args()
    run_pipeline(raw_dir=args.raw_dir, db_path=args.db_path, force_download=args.force)
