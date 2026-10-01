"""Background deletion: single-flight claim, staleness, outcome recording."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import teg_analysis.analysis.data_update as du
from webapp import deps, delete_jobs


@pytest.fixture(autouse=True)
def _store(tmp_path, monkeypatch):
    monkeypatch.setattr(delete_jobs, "_store_path", lambda rel: tmp_path / rel)
    monkeypatch.setattr(deps, "clear_all_data_caches", lambda: None)
    return tmp_path


def _age(seconds):
    path = delete_jobs.status_path()
    data = json.loads(path.read_text())
    data["updated_at"] = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(timespec="seconds")
    path.write_text(json.dumps(data))


def test_status_file_is_outside_sync_folders():
    from teg_analysis.io.sync import SYNC_FOLDERS
    rel = "data/_delete_status/current.json"
    assert str(Path(rel).parent) not in SYNC_FOLDERS


def test_claim_is_single_flight():
    assert delete_jobs.claim(19, [1, 2]) is None
    s = delete_jobs.read_status()
    assert (s["state"], s["teg"], s["rounds"]) == ("queued", 19, [1, 2])
    active = delete_jobs.claim(19, [3])
    assert active["state"] == "queued" and active["rounds"] == [1, 2]
    assert delete_jobs.read_status()["rounds"] == [1, 2]  # untouched


def test_done_status_does_not_block_new_claim():
    delete_jobs.claim(19, [1])
    delete_jobs.write_status(state="done", result={"rows_deleted": 72})
    assert delete_jobs.claim(19, [2]) is None
    s = delete_jobs.read_status()
    assert s["state"] == "queued" and s["rounds"] == [2] and s["result"] is None


def test_error_status_does_not_block_new_claim():
    delete_jobs.claim(19, [1])
    delete_jobs.write_status(state="error", error="boom")
    assert delete_jobs.claim(19, [1]) is None


def test_stale_age_reads_as_interrupted_and_lets_claim_through():
    delete_jobs.claim(19, [1])
    _age(delete_jobs.STALE_AFTER_SECONDS + 5)
    status = delete_jobs.read_status()
    assert not delete_jobs.is_active(status)
    assert delete_jobs.error_message(status) == (
        "The deletion was interrupted. Check the round is gone on the site, then retry if needed.")
    assert delete_jobs.claim(19, [1]) is None


def test_other_boot_id_reads_as_interrupted():
    delete_jobs.claim(19, [1])
    path = delete_jobs.status_path()
    data = json.loads(path.read_text())
    data["boot_id"] = "some-other-boot"
    path.write_text(json.dumps(data))
    status = delete_jobs.read_status()
    assert not delete_jobs.is_active(status)
    assert delete_jobs.error_message(status) == delete_jobs.INTERRUPTED_MESSAGE


def test_run_deletion_records_done_json_safe(monkeypatch):
    def fake(teg, rounds, progress=None):
        progress("backup", "running")
        progress("backup", "done")
        return {"rows_deleted": 72, "teg": teg, "rounds": rounds,
                "backups": [Path("data/backups/a.parquet")], "committed": True,
                "files_committed": 9, "cache_errors": [{"step": "streaks", "error": "x"}],
                "reports_archived": ["r.md"], "archive_dir": Path("data/archive/x")}
    monkeypatch.setattr(du, "execute_data_deletion", fake)
    delete_jobs.claim(19, [1, 2])
    delete_jobs.run_deletion(19, [1, 2])
    s = delete_jobs.read_status()
    assert s["state"] == "done" and s["finished_at"]
    r = s["result"]
    assert r["rows_deleted"] == 72 and r["rounds"] == [1, 2]
    assert r["backups"] == [str(Path("data/backups/a.parquet"))]
    assert r["archive_dir"] == str(Path("data/archive/x"))
    assert r["cache_errors"] == [{"step": "streaks", "error": "x"}]
    assert s["steps"]["backup"]["state"] == "done"
    assert not delete_jobs.is_active(s)


def test_run_deletion_busy_lock_is_a_clear_error(monkeypatch):
    def busy(teg, rounds, progress=None):
        raise du.UpdateInProgressError("Another data update is already in progress.")
    monkeypatch.setattr(du, "execute_data_deletion", busy)
    delete_jobs.claim(19, [1])
    delete_jobs.run_deletion(19, [1])
    s = delete_jobs.read_status()
    assert s["state"] == "error"
    assert delete_jobs.error_message(s) == "Another update is running. Try again in a minute."


def test_run_deletion_records_unexpected_error(monkeypatch):
    def boom(teg, rounds, progress=None):
        raise RuntimeError("disk full")
    monkeypatch.setattr(du, "execute_data_deletion", boom)
    delete_jobs.claim(19, [1])
    delete_jobs.run_deletion(19, [1])  # never raises
    s = delete_jobs.read_status()
    assert s["state"] == "error"
    assert "disk full" in delete_jobs.error_message(s)


def test_step_rows_and_current_step():
    delete_jobs.claim(19, [1])
    rec = delete_jobs._progress_recorder()
    rec("backup", "done")
    rec("delete", "running")
    s = delete_jobs.read_status()
    rows = {r["key"]: r["state"] for r in delete_jobs.step_rows(s)}
    assert rows["backup"] == "done" and rows["delete"] == "running" and rows["commit"] == "todo"
    assert delete_jobs.current_step(s) == {"index": 2, "total": len(du.DELETION_STEPS),
                                           "label": "Remove the rounds"}
    delete_jobs.write_status(state="error", error="x")
    rows = {r["key"]: r["state"] for r in delete_jobs.step_rows(delete_jobs.read_status())}
    assert rows["delete"] == "notrun" and rows["commit"] == "notrun"
