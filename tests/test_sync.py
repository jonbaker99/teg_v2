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


# ---------------------------------------------------------------------------
# Backups + restore
# ---------------------------------------------------------------------------

def test_pull_backs_up_existing_then_overwrites(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    # Seed an existing store file that pulling will overwrite.
    (tmp_path / "data").mkdir(parents=True)
    (tmp_path / "data/round_info.csv").write_bytes(b"OLD")
    monkeypatch.setattr(sync, "github_download_bytes", lambda path: b"NEW")

    out = sync.pull_files("data", ["round_info.csv"])

    assert out["pulled"] == 1
    assert len(out["backups"]) == 1                      # existing file was backed up
    assert (tmp_path / "data/round_info.csv").read_bytes() == b"NEW"
    # The backup holds the pre-overwrite bytes.
    assert (tmp_path / out["backups"][0]).read_bytes() == b"OLD"


def test_backup_returns_none_when_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    assert sync.backup_store_file("data/nope.csv", "20260101_000000") is None


def test_list_and_restore_backup(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    (tmp_path / "data").mkdir(parents=True)
    (tmp_path / "data/round_info.csv").write_bytes(b"ORIGINAL")

    backup_rel = sync.backup_store_file("data/round_info.csv", "20260101_000000")
    assert backup_rel == "data/backups/sync/20260101_000000/data/round_info.csv"

    listed = sync.list_sync_backups()
    assert len(listed) == 1
    assert listed[0]["original"] == "data/round_info.csv"
    assert listed[0]["backup_rel"] == backup_rel

    # Mutate the live file, then restore should bring back the original bytes.
    (tmp_path / "data/round_info.csv").write_bytes(b"CHANGED")
    restored = sync.restore_backup(backup_rel)
    assert restored == "data/round_info.csv"
    assert (tmp_path / "data/round_info.csv").read_bytes() == b"ORIGINAL"


def test_restore_rejects_non_backup_path(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    with pytest.raises(ValueError):
        sync.restore_backup("data/round_info.csv")


# ---------------------------------------------------------------------------
# Overwrite-conflict detection
# ---------------------------------------------------------------------------

def test_detect_pull_conflicts(monkeypatch):
    from datetime import datetime, timezone
    newer = datetime(2026, 6, 1, tzinfo=timezone.utc)
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # store newer than github -> pull would clobber a newer store file
    monkeypatch.setattr(sync, "_store_mtime", lambda rel: newer)
    monkeypatch.setattr(sync, "github_commit_time", lambda path: older)
    assert [c["name"] for c in sync.detect_pull_conflicts("data", ["a.csv"])] == ["a.csv"]
    # vice versa -> no pull conflict
    monkeypatch.setattr(sync, "_store_mtime", lambda rel: older)
    monkeypatch.setattr(sync, "github_commit_time", lambda path: newer)
    assert sync.detect_pull_conflicts("data", ["a.csv"]) == []


def test_detect_push_conflicts_and_unknown_times(monkeypatch):
    from datetime import datetime, timezone
    newer = datetime(2026, 6, 1, tzinfo=timezone.utc)
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # github newer than store -> push would clobber a newer github file
    monkeypatch.setattr(sync, "_store_mtime", lambda rel: older)
    monkeypatch.setattr(sync, "github_commit_time", lambda path: newer)
    assert [c["name"] for c in sync.detect_push_conflicts("data", ["a.csv"])] == ["a.csv"]
    # unknown github time -> never flagged (no false positives)
    monkeypatch.setattr(sync, "github_commit_time", lambda path: None)
    assert sync.detect_push_conflicts("data", ["a.csv"]) == []


# ---------------------------------------------------------------------------
# Pre-action preview
# ---------------------------------------------------------------------------

def test_build_sync_preview_pull_outcomes(monkeypatch):
    from datetime import datetime, timezone
    newer = datetime(2026, 6, 1, tzinfo=timezone.utc)
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(sync, "list_github_files", lambda folder: {"a.csv": 10, "new.csv": 5})
    monkeypatch.setattr(sync, "list_store_files", lambda folder: {"a.csv": 10})
    # a.csv: store newer than GitHub -> pulling it is a conflict (overwrites newer store)
    monkeypatch.setattr(sync, "_store_mtime", lambda rel: newer)
    monkeypatch.setattr(sync, "github_commit_time", lambda path: older)

    rows = {r["name"]: r for r in sync.build_sync_preview("pull", "data", ["a.csv", "new.csv"])}

    assert rows["a.csv"]["outcome"] == "overwrite"
    assert rows["a.csv"]["is_conflict"] is True
    assert rows["a.csv"]["newer"] == "store"
    # new.csv has no store copy -> creates, never a conflict
    assert rows["new.csv"]["outcome"] == "create"
    assert rows["new.csv"]["is_conflict"] is False


def test_build_sync_preview_push_conflict_direction(monkeypatch):
    from datetime import datetime, timezone
    newer = datetime(2026, 6, 1, tzinfo=timezone.utc)
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(sync, "list_github_files", lambda folder: {"a.csv": 10})
    monkeypatch.setattr(sync, "list_store_files", lambda folder: {"a.csv": 10})
    # GitHub newer than store -> pushing is the conflict (overwrites newer GitHub)
    monkeypatch.setattr(sync, "_store_mtime", lambda rel: older)
    monkeypatch.setattr(sync, "github_commit_time", lambda path: newer)

    row = sync.build_sync_preview("push", "data", ["a.csv"])[0]
    assert row["outcome"] == "overwrite"
    assert row["is_conflict"] is True
    assert row["newer"] == "github"


def test_build_sync_preview_diffable_flag(monkeypatch):
    monkeypatch.setattr(sync, "list_github_files", lambda folder: {})
    monkeypatch.setattr(sync, "list_store_files", lambda folder: {})
    monkeypatch.setattr(sync, "_store_mtime", lambda rel: None)
    monkeypatch.setattr(sync, "github_commit_time", lambda path: None)

    rows = {r["name"]: r for r in
            sync.build_sync_preview("pull", "data", ["x.csv", "y.parquet"])}
    assert rows["x.csv"]["diffable"] is True
    assert rows["y.parquet"]["diffable"] is False
    assert rows["y.parquet"]["newer"] == "unknown"


# ---------------------------------------------------------------------------
# File diff
# ---------------------------------------------------------------------------

def test_file_diff_text_changes(monkeypatch, tmp_path):
    (tmp_path / "data").mkdir(parents=True)
    (tmp_path / "data/round_info.csv").write_bytes(b"a\nb\nc\n")
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    monkeypatch.setattr(sync, "github_download_bytes", lambda path: b"a\nB\nc\n")

    out = sync.file_diff("data", "round_info.csv")
    assert out["diffable"] is True
    assert out["identical"] is False
    body = "\n".join(out["lines"])
    assert "-b" in body and "+B" in body


def test_file_diff_identical(monkeypatch, tmp_path):
    (tmp_path / "data").mkdir(parents=True)
    (tmp_path / "data/round_info.csv").write_bytes(b"same\n")
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    monkeypatch.setattr(sync, "github_download_bytes", lambda path: b"same\n")

    out = sync.file_diff("data", "round_info.csv")
    assert out["diffable"] is True
    assert out["identical"] is True


def test_file_diff_binary_extension(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    out = sync.file_diff("data", "all-data.parquet")
    assert out["diffable"] is False
    assert "binary" in out["reason"]


# ---------------------------------------------------------------------------
# Volume browsing + delete
# ---------------------------------------------------------------------------

def test_safe_rel_rejects_traversal():
    assert sync._safe_rel("data/x.csv") == "data/x.csv"
    assert sync._safe_rel("/data//x.csv/") == "data/x.csv"
    assert sync._safe_rel("") == ""
    with pytest.raises(ValueError):
        sync._safe_rel("../etc/passwd")


def test_list_store_dir(monkeypatch, tmp_path):
    (tmp_path / "data/commentary").mkdir(parents=True)
    (tmp_path / "data/a.csv").write_bytes(b"hello")
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel if rel else tmp_path)

    out = sync.list_store_dir("data")
    names = [e["name"] for e in out["entries"]]
    # Directories sort before files.
    assert names == ["commentary", "a.csv"]
    assert out["entries"][0]["is_dir"] is True
    assert out["entries"][1]["size"] == 5
    assert out["parent"] == ""


def test_read_store_file(monkeypatch, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/a.csv").write_bytes(b"payload")
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel if rel else tmp_path)
    assert sync.read_store_file("data/a.csv") == b"payload"
    with pytest.raises(FileNotFoundError):
        sync.read_store_file("data/missing.csv")


def test_delete_store_file_backs_up(monkeypatch, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/a.csv").write_bytes(b"DELME")
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel if rel else tmp_path)

    out = sync.delete_store_file("data/a.csv")
    assert out["deleted"] == "data/a.csv"
    assert out["backup_rel"] is not None
    assert not (tmp_path / "data/a.csv").exists()           # removed
    assert (tmp_path / out["backup_rel"]).read_bytes() == b"DELME"  # backed up


def test_delete_store_file_refuses_dir_and_backup_area(monkeypatch, tmp_path):
    (tmp_path / "data/sub").mkdir(parents=True)
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel if rel else tmp_path)
    with pytest.raises(IsADirectoryError):
        sync.delete_store_file("data/sub")
    with pytest.raises(ValueError):
        sync.delete_store_file("data/backups/sync/x/data/a.csv")


# ---------------------------------------------------------------------------
# Backups: restore backs up the replaced file; backups_for filter
# ---------------------------------------------------------------------------

def test_restore_backs_up_current_first(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    (tmp_path / "data").mkdir(parents=True)
    (tmp_path / "data/round_info.csv").write_bytes(b"ORIGINAL")
    backup_rel = sync.backup_store_file("data/round_info.csv", "20260101_000000")

    # Mutate the live file, then restore. The replaced (CHANGED) copy must be kept.
    (tmp_path / "data/round_info.csv").write_bytes(b"CHANGED")
    sync.restore_backup(backup_rel)
    assert (tmp_path / "data/round_info.csv").read_bytes() == b"ORIGINAL"

    saved = [b for b in sync.list_sync_backups()
             if b["original"] == "data/round_info.csv" and b["backup_rel"] != backup_rel]
    assert any((tmp_path / b["backup_rel"]).read_bytes() == b"CHANGED" for b in saved)


def test_backups_for_filters(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "_store_path", lambda rel: tmp_path / rel)
    (tmp_path / "data").mkdir(parents=True)
    (tmp_path / "data/a.csv").write_bytes(b"A")
    (tmp_path / "data/b.csv").write_bytes(b"B")
    sync.backup_store_file("data/a.csv", "20260101_000000")
    sync.backup_store_file("data/b.csv", "20260101_000001")

    only_a = sync.backups_for("data/a.csv")
    assert len(only_a) == 1 and only_a[0]["original"] == "data/a.csv"


# ---------------------------------------------------------------------------
# File catalog
# ---------------------------------------------------------------------------

def test_file_catalog_lookup_and_ordering():
    from teg_analysis.io import file_catalog as fc

    by_imp = fc.catalog_by_importance()
    assert by_imp[0]["name"] == "all-scores.parquet"  # importance 1
    imps = [e["importance"] for e in by_imp]
    assert imps == sorted(imps)

    entry = fc.get_file_definition("round_info.csv")
    assert entry and entry["edit_slug"] == "round_info"
    assert fc.get_file_definition("nope.csv") is None
    assert fc.file_anchor("all-data.parquet") == "file-all-data-parquet"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
