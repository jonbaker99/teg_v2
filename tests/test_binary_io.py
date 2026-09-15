"""Unit tests for teg_analysis.io.file_operations.read_binary_file.

Railway/GitHub calls are monkeypatched out; these tests never touch real
GitHub or a real Railway volume.
"""

import pytest

from teg_analysis.io import file_operations

# Bytes that are not valid UTF-8 (\xff\xfe is an invalid continuation byte
# sequence), so a test-mode-accidentally-text-mode bug would surface as a
# UnicodeDecodeError or corrupted round-trip rather than passing silently.
BINARY_CONTENT = b"\x89PNG\r\n\x1a\n\x00\xff\xfe"


def test_read_binary_file_local_returns_exact_bytes(monkeypatch, tmp_path):
    """Off Railway, read_binary_file is a plain local filesystem read that
    round-trips non-UTF8 bytes exactly (opened in binary mode, not text)."""
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setattr(file_operations.volume_operations, "_REPO_ROOT", tmp_path)

    source = tmp_path / "data" / "commentary" / "pdfs" / "teg_1_report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(BINARY_CONTENT)

    result = file_operations.read_binary_file("data/commentary/pdfs/teg_1_report.pdf")

    assert result == BINARY_CONTENT


def test_read_binary_file_local_missing_raises_file_not_found_error(monkeypatch, tmp_path):
    """Off Railway, a missing file raises FileNotFoundError so callers can
    distinguish 'no PDF for this report yet' from a real error."""
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setattr(file_operations.volume_operations, "_REPO_ROOT", tmp_path)

    with pytest.raises(FileNotFoundError):
        file_operations.read_binary_file("data/commentary/pdfs/does_not_exist.pdf")


def test_read_binary_file_railway_uses_volume_copy(monkeypatch, tmp_path):
    """On Railway, an existing volume copy is read directly (no GitHub call)."""
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "true")

    volume_dir = tmp_path / "volume"
    volume_file = volume_dir / "data" / "commentary" / "pdfs" / "teg_1_report.pdf"
    volume_file.parent.mkdir(parents=True)
    volume_file.write_bytes(BINARY_CONTENT)

    monkeypatch.setattr(
        file_operations.volume_operations,
        "_get_volume_path",
        lambda path: str(volume_dir / path),
    )

    def fail_github_download_bytes(path):
        raise AssertionError("must not read from GitHub when the volume copy exists")

    monkeypatch.setattr(file_operations, "github_download_bytes", fail_github_download_bytes)

    result = file_operations.read_binary_file("data/commentary/pdfs/teg_1_report.pdf")

    assert result == BINARY_CONTENT


def test_read_binary_file_railway_falls_back_to_github_and_caches(monkeypatch, tmp_path):
    """On Railway, if the volume copy isn't cached yet, download from GitHub
    (via the shared github_download_bytes helper) and cache it to the volume."""
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "true")

    volume_dir = tmp_path / "volume"
    monkeypatch.setattr(
        file_operations.volume_operations,
        "_get_volume_path",
        lambda path: str(volume_dir / path),
    )

    captured = {}

    def fake_github_download_bytes(path):
        captured["path"] = path
        return BINARY_CONTENT

    monkeypatch.setattr(file_operations, "github_download_bytes", fake_github_download_bytes)

    result = file_operations.read_binary_file("data/commentary/pdfs/teg_1_report.pdf")

    assert result == BINARY_CONTENT
    assert captured["path"] == "data/commentary/pdfs/teg_1_report.pdf"

    # Cached to the volume for next time.
    cached = volume_dir / "data" / "commentary" / "pdfs" / "teg_1_report.pdf"
    assert cached.read_bytes() == BINARY_CONTENT


def test_read_binary_file_railway_github_404_raises_file_not_found_error(monkeypatch, tmp_path):
    """On Railway, a GitHub 404 (file genuinely absent) is translated to
    FileNotFoundError, not left as a raw GithubException."""
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "true")

    volume_dir = tmp_path / "volume"
    monkeypatch.setattr(
        file_operations.volume_operations,
        "_get_volume_path",
        lambda path: str(volume_dir / path),
    )

    from github import GithubException

    def fake_github_download_bytes(path):
        raise GithubException(404, "Not Found", None)

    monkeypatch.setattr(file_operations, "github_download_bytes", fake_github_download_bytes)

    with pytest.raises(FileNotFoundError):
        file_operations.read_binary_file("data/commentary/pdfs/does_not_exist.pdf")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
