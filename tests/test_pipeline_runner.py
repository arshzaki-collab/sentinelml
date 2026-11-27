"""Unit test for the master pipeline runner with mock data."""

import gzip
from pathlib import Path
from unittest.mock import patch

from blindbillion.data.pipeline import run_pipeline


def test_run_pipeline_isolated(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "test_pipeline.duckdb"

    # Pre-populate dummy raw files for all core tables
    raw_dir.mkdir(parents=True, exist_ok=True)
    for tbl in (
        "competitions",
        "games",
        "clubs",
        "players",
        "appearances",
        "player_valuations",
        "club_games",
        "transfers",
    ):
        csv_file = raw_dir / f"{tbl}.csv.gz"
        with gzip.open(csv_file, "wt", encoding="utf-8") as gz:
            if tbl == "competitions":
                gz.write("competition_id,name\nGB1,Premier League\n")
            elif tbl == "players":
                gz.write(
                    "player_id,name,position,sub_position,date_of_birth,"
                    "current_club_domestic_competition_id\n"
                    "P1,Striker 1,Attack,Centre-Forward,1990-01-01,GB1\n"
                    "P2,Striker 2,Attack,Centre-Forward,1992-01-01,GB1\n"
                    "P3,Striker 3,Attack,Centre-Forward,1993-01-01,GB1\n"
                    "P4,Striker 4,Attack,Centre-Forward,1994-01-01,GB1\n"
                )
            elif tbl == "player_valuations":
                header = (
                    "player_id,date,market_value_in_eur,current_club_id,"
                    "player_club_domestic_competition_id\n"
                )
                lines = [header]
                for pid in ("P1", "P2", "P3", "P4"):
                    for yr in (2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026):
                        lines.append(f"{pid},{yr}-06-01,1000000.0,C1,GB1\n")
                gz.writelines(lines)
            elif tbl == "appearances":
                app_hdr = (
                    "appearance_id,player_id,game_id,date,competition_id,"
                    "goals,assists,yellow_cards,red_cards,minutes_played,player_club_id\n"
                )
                lines = [app_hdr]
                for pid in ("P1", "P2", "P3", "P4"):
                    for yr in range(2016, 2027):
                        lines.append(
                            f"APP_{pid}_{yr},{pid},G_{yr},{yr}-03-01,GB1,10,2,1,0,90,CLUB_A\n"
                        )
                gz.writelines(lines)
            elif tbl == "games":
                lines = ["game_id,home_club_id,away_club_id,home_club_goals,away_club_goals\n"]
                for yr in range(2016, 2027):
                    lines.append(f"G_{yr},CLUB_A,CLUB_B,2,0\n")
                gz.writelines(lines)
            elif tbl == "clubs":
                gz.write("club_id,name\nCLUB_A,Club A\nCLUB_B,Club B\n")
            elif tbl == "club_games":
                lines = ["game_id,club_id,own_goals,opponent_goals\n"]
                for yr in range(2016, 2027):
                    lines.append(f"G_{yr},CLUB_A,2,0\n")
                gz.writelines(lines)
            elif tbl == "transfers":
                trans_hdr = (
                    "player_id,player_name,transfer_date,transfer_season,"
                    "from_club_id,from_club_name,to_club_id,to_club_name,"
                    "transfer_fee,market_value_in_eur\n"
                )
                lines = [trans_hdr]
                for pid in ("P1", "P2", "P3", "P4"):
                    lines.append(
                        f"{pid},Player {pid},2018-07-01,18/19,CLUB_A,Club A,"
                        "CLUB_B,Club B,25000000,20000000\n"
                    )
                gz.writelines(lines)

    # Mock the download_all call so it returns existing raw files without network call
    with patch(
        "blindbillion.data.r2_provider.TransfermarktR2Provider.download_all"
    ) as mock_download:
        mock_download.return_value = {
            tbl: raw_dir / f"{tbl}.csv.gz"
            for tbl in (
                "competitions",
                "games",
                "clubs",
                "players",
                "appearances",
                "player_valuations",
                "club_games",
                "transfers",
            )
        }

        report = run_pipeline(raw_dir=raw_dir, db_path=db_path, force_download=False)
        assert report["status"] == "SUCCESS"
        assert report["database_path"] == str(db_path)
        assert db_path.exists()
        assert (db_path.parent / "data_quality_report.json").exists()


def test_validate_analytical_database_on_missing_file(tmp_path: Path) -> None:
    from blindbillion.data.db import validate_analytical_database

    non_existent = tmp_path / "does_not_exist.duckdb"
    is_valid, status_code, details = validate_analytical_database(non_existent)
    assert not is_valid
    assert status_code == "missing_database"
    assert "File not found" in details[0]


def test_pipeline_runner_cli_dry_run() -> None:
    from blindbillion.data.pipeline_runner import main

    exit_code = main(["--dry-run"])
    assert exit_code == 0


def test_pipeline_runner_cli_check_existing_data() -> None:
    from blindbillion.data.pipeline_runner import main

    existing_db = Path("data/blindbillion.duckdb")
    if existing_db.exists():
        exit_code = main(["--check", "--db-path", str(existing_db)])
        assert exit_code == 0

