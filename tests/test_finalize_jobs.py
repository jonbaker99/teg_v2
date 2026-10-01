"""Background live-round finalise: single-flight claim, staleness, outcome recording."""

from datetime import datetime, timedelta, timezone

import pytest

import teg_analysis.analysis.live_round as lrmod
from webapp import deps, finalize_jobs


@pytest.fixture(autouse=True)
def _store(tmp_path, monkeypatch):
    monkeypatch.setattr(finalize_jobs, "_store_path", lambda rel: tmp_path / rel)
    monkeypatch.setattr(deps, "clear_all_data_caches", lambda: None)
    return tmp_path


def test_claim_is_single_flight():
    assert finalize_jobs.claim("tok") is None
    assert finalize_jobs.read_status("tok")["state"] == "queued"
    active = finalize_jobs.claim("tok")
    assert active["state"] == "queued"
    assert finalize_jobs.claim("other") is None  # other tokens are independent


def test_stale_status_lets_new_claim_through():
    old = (datetime.now(timezone.utc) - timedelta(seconds=finalize_jobs.STALE_AFTER_SECONDS + 5))
    finalize_jobs.claim("tok")
    path = finalize_jobs.status_path("tok")
    import json
    data = json.loads(path.read_text())
    data["updated_at"] = old.isoformat(timespec="seconds")
    path.write_text(json.dumps(data))

    status = finalize_jobs.read_status("tok")
    assert not finalize_jobs.is_active(status)
    assert finalize_jobs.error_message(status) == finalize_jobs.INTERRUPTED_MESSAGE
    assert finalize_jobs.claim("tok") is None
    assert finalize_jobs.is_active(finalize_jobs.read_status("tok"))


def test_run_finalize_records_done(monkeypatch):
    monkeypatch.setattr(lrmod, "finalize_live_round", lambda token, progress=None: {
        "teg_num": 19, "round_num": 2, "records_added": 72, "committed": True,
        "cache_errors": [{"step": "streaks", "error": "x"}, {"step": "records", "error": "y"}],
    })
    finalize_jobs.claim("tok")
    finalize_jobs.run_finalize("tok")
    s = finalize_jobs.read_status("tok")
    assert s["state"] == "done"
    assert (s["teg"], s["round"], s["records_added"], s["committed"]) == (19, 2, 72, True)
    assert s["cache_errors"] == ["streaks", "records"]
    assert s["finished_at"]
    assert not finalize_jobs.is_active(s)


def test_run_finalize_refusal_shows_message(monkeypatch):
    def refuse(token, progress=None):
        raise lrmod.ConflictsUnresolvedError("Resolve every conflicted cell.")
    monkeypatch.setattr(lrmod, "finalize_live_round", refuse)
    finalize_jobs.claim("tok")
    finalize_jobs.run_finalize("tok")
    s = finalize_jobs.read_status("tok")
    assert s["state"] == "error"
    assert s["error"] == "Resolve every conflicted cell."


def test_run_finalize_unexpected_error_never_raises(monkeypatch):
    def boom(token, progress=None):
        raise RuntimeError("push failed")
    monkeypatch.setattr(lrmod, "finalize_live_round", boom)
    finalize_jobs.claim("tok")
    finalize_jobs.run_finalize("tok")
    s = finalize_jobs.read_status("tok")
    assert s["state"] == "error"
    assert s["error"] == "Finalize failed: push failed"
    assert finalize_jobs.claim("tok") is None  # an error is not "active": retry allowed


def _steps_fake(script, result=None):
    """A finalize_live_round that replays `script` = [(step, state, error)] via progress."""
    def fake(token, progress=None):
        for step, state, err in script:
            progress(step, state, err)
            if state == "failed" and step in ("validate", "backup", "scores", "all_data", "status", "commit"):
                raise RuntimeError(err)
        return result or {"teg_num": 19, "round_num": 2, "records_added": 72, "committed": True,
                          "cache_errors": []}
    return fake


def test_run_finalize_records_steps_and_cache_failure_while_done(monkeypatch):
    monkeypatch.setattr(lrmod, "finalize_live_round", _steps_fake([
        ("validate", "running", None), ("validate", "done", None),
        ("streaks", "running", None), ("streaks", "failed", "bad streaks"),
        ("commit", "skipped", None),
    ], result={"teg_num": 19, "round_num": 2, "records_added": 1, "committed": False,
               "cache_errors": [{"step": "streaks", "error": "bad streaks"}]}))
    finalize_jobs.claim("tok")
    finalize_jobs.run_finalize("tok")
    s = finalize_jobs.read_status("tok")
    assert s["state"] == "done"
    assert s["steps"]["validate"]["state"] == "done"
    assert s["steps"]["streaks"] == {"state": "failed", "error": "bad streaks"}
    assert s["steps"]["commit"]["state"] == "skipped"
    assert s["step"] == "streaks"
    rows = {r["key"]: r for r in finalize_jobs.step_rows(s)}
    assert rows["streaks"]["state"] == "failed" and rows["streaks"]["error"] == "bad streaks"
    assert rows["winners"]["state"] == "notrun"


def test_error_job_leaves_unreached_steps_not_run(monkeypatch):
    monkeypatch.setattr(lrmod, "finalize_live_round", _steps_fake([
        ("validate", "done", None), ("backup", "done", None), ("scores", "failed", "disk full"),
    ]))
    finalize_jobs.claim("tok")
    finalize_jobs.run_finalize("tok")
    s = finalize_jobs.read_status("tok")
    assert s["state"] == "error"
    states = {r["key"]: r["state"] for r in finalize_jobs.step_rows(s)}
    assert states["backup"] == "done"
    assert states["scores"] == "failed"
    assert states["all_data"] == "notrun" and states["commit"] == "notrun"


def test_step_rows_todo_while_active_and_current_step():
    finalize_jobs.claim("tok")
    finalize_jobs.write_status("tok", state="running", step="all_data",
                               steps={"validate": {"state": "done", "error": None},
                                      "all_data": {"state": "running", "error": None}})
    s = finalize_jobs.read_status("tok")
    states = {r["key"]: r["state"] for r in finalize_jobs.step_rows(s)}
    assert states["all_data"] == "running" and states["commit"] == "todo"
    cur = finalize_jobs.current_step(s)
    assert cur["total"] == len(lrmod.FINALIZE_STEPS)
    assert cur["index"] == [k for k, _ in lrmod.FINALIZE_STEPS].index("all_data") + 1


def test_claim_resets_steps():
    finalize_jobs.write_status("tok", state="error", steps={"validate": {"state": "done", "error": None}})
    assert finalize_jobs.claim("tok") is None
    assert finalize_jobs.read_status("tok")["steps"] == {}


def test_report_block_variants(monkeypatch):
    def readiness(result):
        monkeypatch.setattr(lrmod, "report_readiness", lambda teg, rnd=None: result)

    readiness({"ready": True, "state": "ready", "reason": None, "token": None, "round": None})
    assert finalize_jobs.report_block(19, 3) is None

    readiness({"ready": False, "state": "not_finalised", "reason": "Round 3 hasn't been finalised yet.",
               "token": "tok", "round": 3})
    assert finalize_jobs.report_block(19, 3) == {
        "message": "Round 3 hasn't been finalised yet.", "link": "/admin/live-round/tok/review"}

    readiness({"ready": False, "state": "processing", "reason": "Round 3 data still being processed.",
               "token": "tok", "round": 3})
    finalize_jobs.claim("tok")
    finalize_jobs.write_status("tok", state="running", step="all_data")
    idx = [k for k, _ in lrmod.FINALIZE_STEPS].index("all_data") + 1
    assert finalize_jobs.report_block(19, 3)["message"] == (
        f"Round 3 data still being processed, step {idx} of {len(lrmod.FINALIZE_STEPS)}.")

    readiness({"ready": False, "state": "failed", "reason": "Round 3 finalise failed at scores.",
               "token": "tok", "round": 3})
    finalize_jobs.write_status("tok", state="error")
    assert finalize_jobs.report_block(19, 3)["message"] == "Round 3 finalise failed at scores."


def test_claim_after_done_keeps_success_record(tmp_path, monkeypatch):
    monkeypatch.setattr(finalize_jobs, "_store_path", lambda rel: tmp_path / rel)
    finalize_jobs.write_status("tokD", state="done", committed=True)
    existing = finalize_jobs.claim("tokD")
    assert existing["state"] == "done"
    assert finalize_jobs.read_status("tokD")["state"] == "done"


def test_active_status_from_another_process_is_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(finalize_jobs, "_store_path", lambda rel: tmp_path / rel)
    finalize_jobs.write_status("tokB", state="running")
    assert finalize_jobs.is_active(finalize_jobs.read_status("tokB"))
    monkeypatch.setattr(finalize_jobs, "BOOT_ID", "a-new-process")
    assert not finalize_jobs.is_active(finalize_jobs.read_status("tokB"))
    assert finalize_jobs.claim("tokB") is None  # retry allowed at once


# --- Results show before the GitHub sync -------------------------------------

def test_commit_start_clears_caches_and_publishes_results(monkeypatch):
    clears, seen = [], {}
    monkeypatch.setattr(deps, "clear_all_data_caches", lambda: clears.append(1))

    def fake(token, progress=None):
        progress("validate", "done")
        seen["before"] = finalize_jobs.results_published(token)
        progress("commit", "running")
        seen["during"] = finalize_jobs.results_published(token)
        seen["clears_during"] = len(clears)
        progress("commit", "done")
        return {"teg_num": 19, "round_num": 1, "records_added": 1, "committed": True}

    monkeypatch.setattr(lrmod, "finalize_live_round", fake)
    finalize_jobs.claim("tok")
    finalize_jobs.run_finalize("tok")
    assert seen == {"before": False, "during": True, "clears_during": 1}
    # Done: the registry now says finalized, so the job no longer needs to.
    assert finalize_jobs.results_published("tok") is False


def test_failed_commit_unpublishes_and_clears_caches(monkeypatch):
    clears = []
    monkeypatch.setattr(deps, "clear_all_data_caches", lambda: clears.append(1))

    def fake(token, progress=None):
        progress("commit", "running")
        progress("commit", "failed", "GitHub down")
        raise RuntimeError("GitHub down")

    monkeypatch.setattr(lrmod, "finalize_live_round", fake)
    finalize_jobs.claim("tok")
    finalize_jobs.run_finalize("tok")
    assert finalize_jobs.read_status("tok")["state"] == "error"
    assert finalize_jobs.results_published("tok") is False
    assert len(clears) == 2  # at commit start, and again after the failure


def test_banners_switch_to_results_while_syncing(monkeypatch):
    live = lambda tok, r: {"kind": "live", "token": tok, "teg_num": 19, "round_num": r}
    published = {"a"}
    monkeypatch.setattr(finalize_jobs, "results_published", lambda tok: tok in published)

    assert deps._with_results_published([live("a", 1)]) == [
        {"kind": "results", "teg_num": 19, "round_num": 1}]
    # Another round still live: live banners only, as the registry does.
    assert deps._with_results_published([live("a", 1), live("b", 2)]) == [live("b", 2)]
    published.clear()
    assert deps._with_results_published([live("a", 1)]) == [live("a", 1)]
    assert deps._with_results_published([]) == []
