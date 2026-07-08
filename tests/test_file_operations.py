"""Unit tests for teg_analysis.io.file_operations.

Railway/GitHub calls are monkeypatched out; these tests never touch real
GitHub or a real Railway volume.
"""

import pandas as pd
import pytest

from teg_analysis.io import file_operations


def test_backup_file_railway_uses_volume_copy(monkeypatch, tmp_path):
    """On Railway, backup_file backs up the current volume copy (Phase 1.2 fix),
    not the last GitHub commit."""
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "true")

    volume_dir = tmp_path / "volume"
    volume_file = volume_dir / "data" / "all-scores.parquet"
    volume_file.parent.mkdir(parents=True)
    current_df = pd.DataFrame({"a": [1, 2, 3]})
    current_df.to_parquet(volume_file, index=False)

    monkeypatch.setattr(
        file_operations.volume_operations,
        "_get_volume_path",
        lambda path: str(volume_dir / path),
    )

    def fail_read_from_github(path):
        raise AssertionError("must not read from GitHub when the volume copy exists")

    monkeypatch.setattr(file_operations, "read_from_github", fail_read_from_github)

    captured = {}

    def fake_write_to_github(path, data, msg):
        captured["path"] = path
        captured["data"] = data
        captured["msg"] = msg

    monkeypatch.setattr(file_operations, "write_to_github", fake_write_to_github)

    file_operations.backup_file("data/all-scores.parquet", "data/backups/x.parquet")

    assert captured["path"] == "data/backups/x.parquet"
    pd.testing.assert_frame_equal(captured["data"].reset_index(drop=True), current_df)


def test_backup_file_railway_falls_back_to_github_if_volume_missing(monkeypatch, tmp_path):
    """If the volume copy isn't cached yet, fall back to the last GitHub commit."""
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "true")

    monkeypatch.setattr(
        file_operations.volume_operations,
        "_get_volume_path",
        lambda path: str(tmp_path / "does-not-exist" / path),
    )

    github_df = pd.DataFrame({"a": [9]})
    monkeypatch.setattr(file_operations, "read_from_github", lambda path: github_df)

    captured = {}

    def fake_write_to_github(path, data, msg):
        captured["data"] = data

    monkeypatch.setattr(file_operations, "write_to_github", fake_write_to_github)

    file_operations.backup_file("data/all-scores.parquet", "data/backups/x.parquet")

    pd.testing.assert_frame_equal(captured["data"], github_df)


def test_backup_file_local_copies_filesystem(monkeypatch, tmp_path):
    """Off Railway, backup_file is a plain local filesystem copy (unchanged behaviour)."""
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setattr(file_operations.volume_operations, "_REPO_ROOT", tmp_path)

    source = tmp_path / "data" / "all-scores.parquet"
    source.parent.mkdir(parents=True)
    pd.DataFrame({"a": [1]}).to_parquet(source, index=False)

    file_operations.backup_file("data/all-scores.parquet", "data/backups/x.parquet")

    assert (tmp_path / "data" / "backups" / "x.parquet").exists()


def test_write_file_local_creates_missing_parent_directory(monkeypatch, tmp_path):
    """write_file's local path didn't mkdir before writing (unlike write_text_file
    and the Railway branch), so writing the first file into a brand-new
    subdirectory (e.g. data/live_rounds/{token}.csv) raised OSError. Caught by
    the live-round E2E test starting a live round in a scratch repo."""
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setattr(file_operations.volume_operations, "_REPO_ROOT", tmp_path)

    file_operations.write_file("data/brand_new_dir/x.csv", pd.DataFrame({"a": [1]}))

    assert (tmp_path / "data" / "brand_new_dir" / "x.csv").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
