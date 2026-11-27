"""Entrypoint CLI for Blind Billion 2.0 Historical Data Pipeline.

Supports:
- Running full ingestion: python -m blindbillion.data.pipeline_runner
- Health check without ingestion: python -m blindbillion.data.pipeline_runner --check
- Dry run: python -m blindbillion.data.pipeline_runner --dry-run
- Force re-download: python -m blindbillion.data.pipeline_runner --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import duckdb

from blindbillion.data.db import (
    get_analytical_db_path,
    validate_analytical_database,
)
from blindbillion.data.pipeline import run_pipeline
from blindbillion.data.r2_provider import TransfermarktR2Provider

logger = logging.getLogger("blindbillion.data.pipeline_runner")


def check_pipeline_data(db_path: Path) -> bool:
    """Perform health and completeness verification on the analytical DuckDB cache.

    Prints table counts, valuation coverage for 2016-2026, and returns True if READY.
    """
    print(f"Checking analytical database: {db_path.resolve()}")

    is_valid, status_code, details = validate_analytical_database(db_path)
    if not is_valid:
        print(f"Status: NOT READY ({status_code})")
        for detail in details:
            print(f"  - {detail}")
        return False

    try:
        con = duckdb.connect(str(db_path), read_only=True)
        print("\n=== Analytical Tables & Row Counts ===")
        all_tables = [
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' ORDER BY table_name"
            ).fetchall()
        ]
        for tbl in all_tables:
            row = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            count = row[0] if row else 0
            print(f"  ✓ {tbl:30s}: {count:,} rows")

        # Check annual valuation coverage 2016-2026
        val_table = (
            "player_annual_valuations"
            if "player_annual_valuations" in all_tables
            else "materialized_valuations"
        )
        print(f"\n=== Historical Valuations Coverage ({val_table}) ===")
        expected_years = list(range(2016, 2027))
        year_rows = con.execute(
            f"SELECT reference_year, COUNT(*) FROM {val_table} "
            f"GROUP BY reference_year ORDER BY reference_year"
        ).fetchall()
        counts_by_year = dict(year_rows)

        missing_years: list[int] = []
        for yr in expected_years:
            yr_count = counts_by_year.get(yr, 0)
            if yr_count > 0:
                print(f"  ✓ July 1, {yr}: {yr_count:,} player valuations")
            else:
                print(f"  ✗ July 1, {yr}: MISSING")
                missing_years.append(yr)

        con.close()

        if missing_years:
            print(f"\nStatus: NOT READY (Missing valuation coverage for years: {missing_years})")
            return False

        print("\n======================================")
        print("Verdict: READY - Analytical database is fully populated and healthy.")
        print("======================================\n")
        return True

    except Exception as exc:
        print(f"\nError querying analytical database: {exc}")
        print("Verdict: NOT READY")
        return False


def dry_run_check(raw_dir: Path, db_path: Path) -> bool:
    """Verify source availability and prerequisites without modifying databases."""
    print("Executing Dry-Run Verification...")
    print(f"  Target database: {db_path.resolve()}")
    print(f"  Raw directory:   {raw_dir.resolve()}")

    provider = TransfermarktR2Provider()
    print(f"  Data source:     {provider.get_source_identifier()}")
    print("  Checking source file manifest...")
    try:
        manifest = provider.get_manifest()
        for tbl, filename in manifest.items():
            print(f"    - Table '{tbl}' -> {filename}")
        print("Dry run passed: Source manifest is valid and accessible.")
        return True
    except Exception as exc:
        print(f"Dry run failed: {exc}")
        return False


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint parsing arguments and dispatching action."""
    parser = argparse.ArgumentParser(
        description="Blind Billion 2.0 Historical Data Pipeline Runner"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check analytical database health, table rows, and valuation coverage",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify data source availability and prerequisites without modifying database",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download of raw tables even if cached locally",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to DuckDB database (defaults to ANALYTICAL_DB_PATH or data/blindbillion.duckdb)",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory where raw compressed files are downloaded",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    resolved_db_path = args.db_path if args.db_path is not None else get_analytical_db_path()

    if args.check:
        is_ready = check_pipeline_data(resolved_db_path)
        return 0 if is_ready else 1

    if args.dry_run:
        is_ok = dry_run_check(args.raw_dir, resolved_db_path)
        return 0 if is_ok else 1

    print(f"Executing pipeline targeting database: {resolved_db_path}")
    report = run_pipeline(
        raw_dir=args.raw_dir,
        db_path=resolved_db_path,
        force_download=args.force,
    )
    if report.get("status") == "SUCCESS":
        print("\nPipeline run succeeded.")
        return 0
    else:
        print(f"\nPipeline run failed: {report}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
