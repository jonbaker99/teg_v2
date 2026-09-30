"""Each admin action must make exactly ONE GitHub commit on Railway.

Several commits in quick succession can trigger a full Railway redeploy, so
``execute_data_update``, ``execute_data_deletion`` and ``finalize_live_round``
each fold their backups (and, for finalise, the live-round registry) into the
single ``batch_commit_to_github`` call. Railway is simulated on a scratch copy
of ``data/`` with the GitHub layer recorded, never called.
"""

import shutil
from pathlib import Path

import pandas as pd
import pytest

import teg_analysis.io as tio
import teg_analysis.io.file_operations as file_operations
import teg_analysis.io.volume_operations as volume_operations
from teg_analysis.analysis import live_round as lr
from teg_analysis.analysis.data_update import (
    execute_data_deletion,
    execute_data_update,
    process_google_sheets_data,
)


class GitHubRecorder:
    def __init__(self):
        self.batches = []   # (paths, data-by-path, message)
        self.single = []    # any non-batch write (must stay empty)
        self.fail_batch = False

    def batch(self, files, message="Batch update data"):
        if self.fail_batch:
            raise RuntimeError("github down")
        self.batches.append(
            ([f["file_path"] for f in files], {f["file_path"]: f["data"] for f in files}, message)
        )

    def write(self, path, *args, **kwargs):
        self.single.append(path)


@pytest.fixture
def railway(tmp_path, monkeypatch):
    """Railway simulation: volume == scratch copy of data/, GitHub recorded."""
    shutil.copytree(Path(__file__).resolve().parent.parent / "data", tmp_path / "data")
    monkeypatch.setattr(volume_operations, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(volume_operations, "_get_volume_path", lambda p: str(tmp_path / p))
    # Local (non-Railway) phase first; tests flip this on with go_railway().
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)

    rec = GitHubRecorder()
    monkeypatch.setattr(tio, "batch_commit_to_github", rec.batch)
    monkeypatch.setattr(file_operations, "write_to_github", rec.write)
    monkeypatch.setattr(file_operations, "write_text_to_github", rec.write)

    def go_railway():
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "test")

    rec.go_railway = go_railway
    rec.root = tmp_path
    return rec


def _wide_round(teg_num=50, round_num=1):
    players = ["DM", "GW", "HM", "JP", "JB", "SN", "AB"]
    rows = []
    for hole in range(1, 19):
        row = {"TEGNum": teg_num, "Round": round_num, "Hole": hole, "Par": 4, "SI": hole}
        row.update({p: 4 for p in players})
        rows.append(row)
    return pd.DataFrame(rows)


def _assert_single_commit(rec, result, extra=()):
    assert len(rec.batches) == 1
    assert rec.single == []
    paths, _, _ = rec.batches[0]
    assert len(result["backups"]) == 2
    for backup in result["backups"]:
        assert backup in paths
    assert "data/all-scores.parquet" in paths
    for p in extra:
        assert p in paths
    assert paths[:2] == list(result["backups"])  # backups first
    assert result["committed"] is True
    assert result["files_committed"] == len(paths)


def test_execute_data_update_one_commit(railway):
    railway.go_railway()
    result = execute_data_update(process_google_sheets_data(_wide_round()), overwrite=True)
    _assert_single_commit(railway, result)


def test_execute_data_update_commit_false_returns_pending(railway):
    railway.go_railway()
    result = execute_data_update(
        process_google_sheets_data(_wide_round()), overwrite=True, commit=False
    )
    assert railway.batches == [] and railway.single == []
    assert result["committed"] is False
    paths = [f["file_path"] for f in result["pending_files"]]
    assert paths[:2] == list(result["backups"])
    assert "data/all-scores.parquet" in paths


def test_pending_files_only_present_when_commit_false(railway):
    result = execute_data_update(process_google_sheets_data(_wide_round()), overwrite=True)
    assert "pending_files" not in result


def test_execute_data_deletion_one_commit(railway):
    railway.go_railway()
    execute_data_update(process_google_sheets_data(_wide_round()), overwrite=True)
    railway.batches.clear()
    result = execute_data_deletion(50, [1])
    _assert_single_commit(railway, result)


def test_deletion_archives_reports_and_marks_registry_in_one_commit(railway, monkeypatch):
    """Issue 22 regression: deleting a finalised round moves its round report
    and the TEG's tournament report to data/commentary/archive/ and flips its
    registry row to 'deleted', all in the deletion's one commit."""
    import teg_analysis.analysis.data_update as du

    execute_data_update(process_google_sheets_data(_wide_round()), overwrite=True)
    commentary = railway.root / "data" / "commentary"
    stale = ["teg_50_round_1_report_storylinefirst_styled.md", "teg_50_round_1_claims.json",
             "teg_50_report_storylinefirst_styled.md"]
    kept = ["teg_50_round_2_report_storylinefirst_styled.md", "teg_5_round_1_claims.json"]
    for name in stale + kept:
        (commentary / name).write_text(f"report {name}")
    registry = lr._read_registry()
    registry = pd.concat([registry, pd.DataFrame([{
        "Token": "tok50", "TEGNum": 50, "Round": 1, "CreatedAt": "2026-09-30T00:00:00+00:00",
        "Status": "finalized",
    }])], ignore_index=True)
    lr._write_registry(registry)
    # Everything but one round-1 file is already on GitHub.
    monkeypatch.setattr(du, "_github_commentary_names", lambda: set(stale[1:] + kept))

    railway.go_railway()
    railway.batches.clear()
    result = execute_data_deletion(50, [1])

    assert result["cache_errors"] == []
    assert result["reports_archived"] == sorted(stale)
    archive_dir = result["archive_dir"]
    assert archive_dir.startswith("data/commentary/archive/teg_50_deleted_")

    assert len(railway.batches) == 1 and railway.single == []
    paths, data, _ = railway.batches[0]
    for name in stale:
        assert f"{archive_dir}/{name}" in paths
        assert data[f"{archive_dir}/{name}"] == f"report {name}"
        assert not (commentary / name).exists()
        assert (railway.root / archive_dir / name).exists()
    # Removals only for files GitHub has.
    assert f"data/commentary/{stale[0]}" not in paths
    for name in stale[1:]:
        assert f"data/commentary/{name}" in paths
    for name in kept:
        assert (commentary / name).exists()
        assert f"data/commentary/{name}" not in paths

    assert "data/live_rounds.csv" in paths
    row = lr._read_registry().set_index("Token").loc["tok50"]
    assert row["Status"] == "deleted"
    readiness = lr.report_readiness(50, 1)
    assert readiness["ready"] is False and readiness["state"] == "deleted"


def _stale_report(railway):
    execute_data_update(process_google_sheets_data(_wide_round()), overwrite=True)
    report = railway.root / "data" / "commentary" / "teg_50_round_1_report_storylinefirst_styled.md"
    report.write_text("stale")
    return report


def test_deletion_commit_failure_keeps_reports(railway, monkeypatch):
    """Reports leave the store only once the commit lands."""
    import teg_analysis.analysis.data_update as du

    report = _stale_report(railway)
    monkeypatch.setattr(du, "_github_commentary_names", lambda: {report.name})
    railway.go_railway()
    railway.fail_batch = True
    with pytest.raises(RuntimeError):
        execute_data_deletion(50, [1])
    assert report.exists()


def test_deletion_github_listing_failure_keeps_reports(railway, monkeypatch):
    """A failed GitHub listing must not read as "nothing on GitHub"."""
    import teg_analysis.analysis.data_update as du

    report = _stale_report(railway)

    def boom():
        raise RuntimeError("github listing down")

    monkeypatch.setattr(du, "_github_commentary_names", boom)
    railway.go_railway()
    result = execute_data_deletion(50, [1])
    assert [e["step"] for e in result["cache_errors"]] == ["reports_archive"]
    assert result["reports_archived"] == []
    assert report.exists()


def test_update_batch_failure_still_raises(railway):
    railway.go_railway()
    railway.fail_batch = True
    with pytest.raises(RuntimeError):
        execute_data_update(process_google_sheets_data(_wide_round()), overwrite=True)


def test_backup_paths_are_distinct_snapshots(railway):
    railway.go_railway()
    execute_data_update(process_google_sheets_data(_wide_round()), overwrite=True)
    paths, data, _ = railway.batches[0]
    backups = [p for p in paths if p.startswith("data/backups/")]
    assert len(backups) == 2
    assert all(isinstance(data[p], pd.DataFrame) for p in backups)


# ---------------------------------------------------------------------------
# finalize_live_round
# ---------------------------------------------------------------------------

@pytest.fixture
def live_token(railway, monkeypatch):
    """An active live round for fake TEG 999 R1 with DM/GW complete, ready to finalise."""
    root = railway.root
    ri = pd.read_csv(root / "data" / "round_info.csv")
    ri = pd.concat([ri, pd.DataFrame([{
        "TEGNum": 999, "Round": 1, "Course": "Ashdown", "Date": "01/01/2099",
        "TEGRd": "TEG 999|1", "TEG": "TEG 999", "Area": "Test", "Year": 2099,
    }])], ignore_index=True)
    ri.to_csv(root / "data" / "round_info.csv", index=False)
    pd.DataFrame(
        [{"TEGNum": 999, "Round": 1, "Hole": h, "Par": 4, "SI": h} for h in range(1, 19)]
    ).to_csv(root / "data" / "round_pars.csv", index=False)
    hc = pd.read_csv(root / "data" / "handicaps.csv")
    row = {c: 0 for c in hc.columns}
    row.update({"TEG": "TEG 999", "DM": 18, "GW": 16})
    pd.concat([hc, pd.DataFrame([row])], ignore_index=True).to_csv(
        root / "data" / "handicaps.csv", index=False
    )

    import teg_analysis.analysis.round_setup as rs
    monkeypatch.setattr(rs, "get_round_setup_form", lambda t, r: {"source": "confirmed"})
    monkeypatch.setattr(lr, "_finalizing", set())

    token = lr.start_live_round(999, 1)["Token"]
    cells = [{"hole": h, "player": p, "value": 4} for h in range(1, 19) for p in ("DM", "GW")]
    lr.apply_score_writes(token, "dev-A", "Jon", cells)
    railway.go_railway()
    railway.batches.clear()
    railway.single.clear()
    return token


def _registry_status(railway, token):
    reg = pd.read_csv(railway.root / "data" / "live_rounds.csv")
    return reg[reg["Token"] == token].iloc[0]["Status"]


def test_finalize_live_round_one_commit(railway, live_token):
    result = lr.finalize_live_round(live_token)
    _assert_single_commit(railway, result, extra=("data/live_rounds.csv",))
    _, data, _ = railway.batches[0]
    reg = data["data/live_rounds.csv"]
    assert reg[reg["Token"] == live_token].iloc[0]["Status"] == "finalized"
    assert _registry_status(railway, live_token) == "finalized"
    assert live_token not in lr._finalizing
    assert "pending_files" not in result


def test_finalize_commit_failure_leaves_round_active(railway, live_token):
    railway.fail_batch = True
    with pytest.raises(RuntimeError):
        lr.finalize_live_round(live_token)
    assert _registry_status(railway, live_token) == "active"
    assert live_token not in lr._finalizing
    assert railway.single == []


def test_cancel_refused_while_finalizing(railway, live_token, monkeypatch):
    lr._finalizing.add(live_token)
    try:
        with pytest.raises(lr.LiveRoundInactiveError):
            lr.cancel_live_round(live_token)
    finally:
        lr._finalizing.discard(live_token)
    assert _registry_status(railway, live_token) == "active"


# ---------------------------------------------------------------------------
# Progress steps and report readiness
# ---------------------------------------------------------------------------

def _recorder():
    events = []
    return events, lambda step, state, error=None: events.append((step, state, error))


def test_finalize_reports_every_step_in_order(railway, live_token):
    events, progress = _recorder()
    lr.finalize_live_round(live_token, progress=progress)
    done = [s for s, st, _ in events if st == "done"]
    assert done == [k for k, _ in lr.FINALIZE_STEPS]
    assert all(st in ("running", "done") for _, st, _ in events)


def test_finalize_cache_failure_is_reported_and_recorded(railway, live_token, monkeypatch):
    import teg_analysis.analysis.pipeline as pipeline
    monkeypatch.setattr(pipeline, "update_streaks_cache",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("streaks broke")))
    events, progress = _recorder()
    result = lr.finalize_live_round(live_token, progress=progress)
    assert ("streaks", "failed", "streaks broke") in events
    # Later steps still ran (pipelines fail loudly, not early).
    assert ("winners", "done", None) in events and ("commit", "done", None) in events
    assert [c["step"] for c in result["cache_errors"]] == ["streaks"]
    reg = pd.read_csv(railway.root / "data" / "live_rounds.csv")
    assert reg[reg["Token"] == live_token].iloc[0]["FailedSteps"] == "streaks"
    # Streaks isn't a report input, so the round report may still run.
    assert lr.report_readiness(999, 1)["ready"] is True


def test_finalize_commit_failure_reports_failed_step(railway, live_token):
    railway.fail_batch = True
    events, progress = _recorder()
    with pytest.raises(RuntimeError):
        lr.finalize_live_round(live_token, progress=progress)
    assert events[-1] == ("commit", "failed", "github down")


def test_finalize_refusal_fails_validate_step(railway, live_token):
    lr.cancel_live_round(live_token)
    events, progress = _recorder()
    with pytest.raises(lr.LiveRoundInactiveError):
        lr.finalize_live_round(live_token, progress=progress)
    assert [(s, st) for s, st, _ in events] == [("validate", "running"), ("validate", "failed")]


def test_readiness_not_finalised(railway, live_token):
    r = lr.report_readiness(999, 1)
    assert r["ready"] is False and r["state"] == "not_finalised" and r["token"] == live_token
    assert lr.report_readiness(999)["ready"] is False  # tournament too


def test_readiness_processing_while_finalizing(railway, live_token):
    lr._finalizing.add(live_token)
    try:
        r = lr.report_readiness(999, 1)
    finally:
        lr._finalizing.discard(live_token)
    assert r["state"] == "processing" and "still being processed" in r["reason"]


def test_readiness_failed_when_finalise_wrote_data_but_did_not_finish(railway, live_token):
    railway.fail_batch = True
    with pytest.raises(RuntimeError):
        lr.finalize_live_round(live_token)
    r = lr.report_readiness(999, 1)
    assert r["ready"] is False and r["state"] == "failed" and "Retry" in r["reason"]


def test_readiness_ready_after_finalise(railway, live_token):
    lr.finalize_live_round(live_token)
    assert lr.report_readiness(999, 1) == {
        "ready": True, "state": "ready", "reason": None, "token": None, "round": None,
    }
    assert lr.report_readiness(999)["ready"] is True


def test_readiness_ignores_cancelled_and_rounds_without_live_round(railway, live_token):
    lr.cancel_live_round(live_token)
    assert lr.report_readiness(999, 1)["ready"] is True
    assert lr.report_readiness(18, 2)["ready"] is True


def test_finalize_retry_after_failed_commit_recommits_scores(railway, live_token):
    """Regression (review): a retry used to find every row already on the volume,
    add nothing and commit only the registry, leaving GitHub without the round."""
    railway.fail_batch = True
    with pytest.raises(RuntimeError):
        lr.finalize_live_round(live_token)
    railway.fail_batch = False
    result = lr.finalize_live_round(live_token)
    paths, _, _ = railway.batches[0]
    assert len(railway.batches) == 1
    assert "data/all-scores.parquet" in paths and "data/all-data.parquet" in paths
    assert result["records_added"] == 36
    assert _registry_status(railway, live_token) == "finalized"
