"""Background deletion of rounds, so the ~40 s write doesn't hold a web request.

`execute_data_deletion` backs up, rewrites all-scores/all-data, rebuilds the
derived caches and pushes one GitHub commit -- far too long for one phone
request. Same pattern as `webapp.finalize_jobs`: state lives in a JSON status
file in the store (not an in-memory dict), so a reload or a locked phone can
resume polling.

State machine: `queued -> running -> done | error`. Only one deletion runs at a
time (the pipeline's `_update_lock` forces it), so there is a single status
file. `claim` gives single-flight; `run_deletion` is the background task and
never raises -- every failure lands in the status file for the page to show.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Optional

from webapp.finalize_jobs import BOOT_ID
from webapp.report_generation import _age_seconds, _now, _store_path

logger = logging.getLogger(__name__)

ACTIVE_STATES = ("queued", "running")

#: Deletion takes ~40 s, so an "active" status older than this means the worker
#: died mid-run (e.g. a Railway redeploy), not that it is still going.
STALE_AFTER_SECONDS = 600  # 10 min

INTERRUPTED_MESSAGE = ("The deletion was interrupted. Check the round is gone on the site, "
                       "then retry if needed.")
BUSY_MESSAGE = "Another update is running. Try again in a minute."


def status_path() -> Path:
    # Local run state, never pushed or pulled: `data/_delete_status/` is not in
    # `sync.SYNC_FOLDERS` (which list files directly under a folder only), and
    # the leading underscore mirrors finalize_jobs' `_finalize_status`.
    return _store_path("data/_delete_status/current.json")


def read_status() -> Optional[dict]:
    path = status_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Could not read delete status {path}: {e}")
        return None


def write_status(**fields) -> dict:
    """Merge `fields` into the status file, refreshing `updated_at`."""
    path = status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_status() or {
        "teg": None, "rounds": [], "state": None, "message": None, "error": None,
        "result": None, "step": None, "steps": {}, "started_at": None, "finished_at": None,
    }
    existing.update(fields)
    existing["updated_at"] = _now()
    existing["boot_id"] = BOOT_ID
    # Atomic replace: the page polls every 2 s while the worker rewrites this
    # file per step, and a half-written file must never read as "no run".
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(existing, indent=2))
    os.replace(tmp, path)
    return existing


def is_active(status: Optional[dict]) -> bool:
    """Whether `status` is a run still in flight (not stale)."""
    if not status or status.get("state") not in ACTIVE_STATES:
        return False
    if status.get("boot_id") not in (None, BOOT_ID):
        return False  # written by a process that has since died
    age = _age_seconds(status.get("updated_at"))
    return True if age is None else age < STALE_AFTER_SECONDS


def error_message(status: Optional[dict]) -> Optional[str]:
    """The message to show for a failed or abandoned (stale) run, else None."""
    if not status:
        return None
    if status.get("state") == "error":
        return status.get("error") or "Deletion failed."
    if status.get("state") in ACTIVE_STATES and not is_active(status):
        return INTERRUPTED_MESSAGE
    return None


_claim_lock = threading.Lock()


def claim(teg, rounds) -> Optional[dict]:
    """Reserve the deletion slot for a new run.

    Returns the existing status (touching nothing) if a deletion is already in
    flight; otherwise writes a fresh `queued` status and returns None. A
    finished `done` or `error` status never blocks a new claim.
    """
    # Sync route handlers run concurrently in the threadpool, so the
    # read-then-write must not interleave (one process on Railway).
    with _claim_lock:
        existing = read_status()
        if is_active(existing):
            return existing
        write_status(teg=int(teg), rounds=[int(r) for r in rounds], state="queued",
                     message="Queued.", error=None, result=None, step=None, steps={},
                     started_at=_now(), finished_at=None)
    return None


def _progress_recorder():
    """A `progress(step, state, error)` callback that persists each step to the
    status file, so a reload or a locked phone still sees the checklist."""
    steps: dict = {}

    def record(step: str, state: str, error: Optional[str] = None) -> None:
        steps[step] = {"state": state, "error": error}
        fields = {"steps": dict(steps)}
        if state == "running":
            fields["step"] = step
        write_status(**fields)

    return record


def step_rows(status: Optional[dict]) -> list[dict]:
    """The checklist for `status`: one row per `DELETION_STEPS` entry.

    Row `state` is done / running / todo / failed / skipped / notrun. A step the
    run never reached is `todo` while the job is in flight, `notrun` once it has
    ended (or was abandoned).
    """
    from teg_analysis.analysis.data_update import DELETION_STEPS

    recorded = (status or {}).get("steps") or {}
    live = is_active(status)
    rows = []
    for i, (key, label) in enumerate(DELETION_STEPS, start=1):
        rec = recorded.get(key) or {}
        state = rec.get("state") or ("todo" if live else "notrun")
        if state == "running" and not live:
            state = "notrun"  # the run ended (or died) mid-step
        rows.append({"key": key, "label": label, "index": i, "state": state,
                     "error": rec.get("error")})
    return rows


def current_step(status: Optional[dict]) -> Optional[dict]:
    """The step a live job is on ({"index", "total", "label"}), else None."""
    from teg_analysis.analysis.data_update import DELETION_STEPS

    key = (status or {}).get("step")
    for i, (k, label) in enumerate(DELETION_STEPS, start=1):
        if k == key:
            return {"index": i, "total": len(DELETION_STEPS), "label": label}
    return None


def _json_safe(result: dict) -> dict:
    """The deletion result with Paths turned into strings, ready for JSON."""
    return json.loads(json.dumps(result, default=str))


def run_deletion(teg, rounds) -> None:
    """The background task: delete the rounds, clear caches, record the outcome.

    Never raises -- a failure is recorded in the status file instead.
    """
    from teg_analysis.analysis.data_update import UpdateInProgressError, execute_data_deletion
    from webapp import deps

    def _record_error(error: str) -> None:
        try:
            write_status(state="error", error=error, message=None, finished_at=_now())
        except Exception:  # noqa: BLE001 -- status store itself is broken; nothing left to do
            logger.error("Could not record deletion failure", exc_info=True)

    try:
        write_status(state="running", message="Removing the rounds and rebuilding the site's stats…")
        result = execute_data_deletion(int(teg), [int(r) for r in rounds],
                                       progress=_progress_recorder())
    except UpdateInProgressError:
        _record_error(BUSY_MESSAGE)
        return
    except Exception as e:  # noqa: BLE001
        logger.error(f"Deletion failed: {e}", exc_info=True)
        _record_error(f"Deletion failed: {e}")
        return

    # The rounds are gone and committed by now: a cache-clear failure must not
    # report the deletion itself as failed.
    try:
        deps.clear_all_data_caches()
    except Exception:  # noqa: BLE001
        logger.error("Cache clear after deletion failed", exc_info=True)
    try:
        write_status(state="done", message="Deleted.", error=None,
                     result=_json_safe(result), finished_at=_now())
    except Exception as e:  # noqa: BLE001
        logger.error(f"Could not record deletion result: {e}", exc_info=True)
        _record_error(f"Deleted, but the result could not be recorded: {e}")
