"""Unit tests for the DataPipelineProvider and TransfermarktR2Provider."""

import gzip
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from blindbillion.data.r2_provider import TransfermarktR2Provider


def test_provider_source_identifier() -> None:
    provider = TransfermarktR2Provider(base_url="https://mock.r2.dev/data")
    assert "mock.r2.dev" in provider.get_source_identifier()


def test_download_table_unknown_table_raises(tmp_path: Path) -> None:
    provider = TransfermarktR2Provider()
    with pytest.raises(ValueError, match="Unknown table 'invalid_table'"):
        provider.download_table("invalid_table", target_dir=tmp_path)


def test_download_table_uses_valid_cache(tmp_path: Path) -> None:
    provider = TransfermarktR2Provider()
    test_file = tmp_path / "competitions.csv.gz"

    # Write a valid small gzip file
    with gzip.open(test_file, "wt", encoding="utf-8") as gz:
        gz.write("competition_id,name\nGB1,Premier League\n")

    with patch("httpx.Client") as mock_client:
        result_path = provider.download_table("competitions", target_dir=tmp_path, force=False)
        assert result_path == test_file
        # Client should not have been called because valid cache exists
        mock_client.assert_not_called()


def test_download_table_fetches_stream(tmp_path: Path) -> None:
    provider = TransfermarktR2Provider()
    target_file = tmp_path / "competitions.csv.gz"

    # Create dummy gzipped bytes
    import io

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(b"competition_id,name\nGB1,Premier League\n")
    valid_gz_bytes = buf.getvalue()

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_bytes.return_value = [valid_gz_bytes]

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__.return_value = mock_response

    mock_client_instance = MagicMock()
    mock_client_instance.stream.return_value = mock_stream_ctx

    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value = mock_client_instance

    with patch("httpx.Client", return_value=mock_client_ctx):
        res = provider.download_table("competitions", target_dir=tmp_path, force=True)
        assert res.exists()
        assert res == target_file

        with gzip.open(res, "rt", encoding="utf-8") as gz:
            content = gz.read()
            assert "GB1,Premier League" in content
