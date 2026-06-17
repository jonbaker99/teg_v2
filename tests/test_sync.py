"""Unit tests for the GitHub <-> store sync logic (teg_analysis.io.sync).

The listing functions touch GitHub / the filesystem, so they are monkeypatched;
these tests cover the pure comparison/classification and orchestration plumbing.
"""

import pytest

from teg_analysis.io import sync


def test_build_sync_status_classifies(monkeypatch):
    gh = {"a.csv": 100, "b.csv": 200, "shared.csv": 50}
    store = {"b.csv": 999, "shared.csv": 50, "c.csv": 10}
    monkeypatch.setattr(sync, "list_github_files", lambda folder: gh)
    monkeypatch.setattr(sync, "list_store_files", lambda folder: store)

    rows = {r["name"]: r for r in sync.build_sync_status("data")}

    assert rows["a.csv"]["status"] == "Only on GitHub"
    assert rows["c.csv"]["status"] == "Only in store"
    assert rows["b.csv"]["status"] == "Different size"
    assert rows["shared.csv"]["status"] == "Same size"


def test_build_sync_status_ordering(monkeypatch):
    """Actionable rows come before in-sync rows."""
    monkeypatch.setattr(sync, "list_github_files", lambda folder: {"only_gh": 1, "match": 5})
    monkeypatch.setattr(sync, "list_store_files", lambda folder: {"match": 5})

    statuses = [r["status"] for r in sync.build_sync_status("data")]
    assert statuses.index("Only on GitHub") < statuses.index("Same size")


def test_pull_files_writes_to_store(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "github_download_bytes", lambda path: b"payload:" + path.encode())
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)

    out = sync.pull_files("data", ["x.csv", "y.csv"])

    assert out["pulled"] == 2
    assert out["failed"] == []
    assert (tmp_path / "data/x.csv").read_bytes() == b"payload:data/x.csv"


def test_pull_files_records_failures(monkeypatch, tmp_path):
    def boom(path):
        raise RuntimeError("nope")
    monkeypatch.setattr(sync, "github_download_bytes", boom)
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)

    out = sync.pull_files("data", ["x.csv"])
    assert out["pulled"] == 0
    assert out["failed"][0][0] == "x.csv"


def test_push_files_batches(monkeypatch, tmp_path):
    # Seed the fake store.
    (tmp_path / "data").mkdir(parents=True)
    (tmp_path / "data/x.csv").write_bytes(b"hello")
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)

    captured = {}
    def fake_batch(files_data, message):
        captured["files"] = files_data
        captured["message"] = message
    monkeypatch.setattr(sync, "batch_commit_to_github", fake_batch)

    out = sync.push_files("data", ["x.csv"], commit_message="msg")
    assert out["pushed"] == 1
    assert out["committed"] is True
    assert captured["files"][0]["file_path"] == "data/x.csv"
    assert captured["files"][0]["data"] == b"hello"
    assert captured["message"] == "msg"


def test_push_files_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    monkeypatch.setattr(sync, "batch_commit_to_github", lambda *a, **k: None)

    out = sync.push_files("data", ["missing.csv"])
    assert out["pushed"] == 0
    assert out["committed"] is False
    assert out["failed"][0][0] == "missing.csv"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
