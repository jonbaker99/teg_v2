"""Background finalise of a live round, so the ~40 s write doesn't hold a web request.

`finalize_live_round` writes the round into all-scores, rebuilds the derived
caches and pushes to GitHub -- far too long for one phone request. Same pattern
as `webapp.report_generation`: state lives in a JSON status file in the store
(not an in-memory dict), so a locked phone or a page reload can resume polling.

State machine per live-round token: `queued -> running -> done | error`.
`claim` gives single-flight; `run_finalize` is the background task and never
raises -- every failure lands in the status file for the review page to show.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Optional

from webapp.report_generation import _age_seconds, _now, _store_path

logger = logging.getLogger(__name__)

ACTIVE_STATES = ("queued", "running")

#: Finalise takes ~40 s, so an "active" status older than this means the worker
#: died mid-run (e.g. a Railway redeploy), not that it is still going.
STALE_AFTER_SECONDS = 600  # 10 min

#: Identifies this server process. Railway runs one process, so an active status
#: written by a different boot belongs to a worker that died (e.g. a redeploy)
#: and is stale at once, rather than blocking a retry for STALE_AFTER_SECONDS.
BOOT_ID = uuid.uuid4().hex

INTERRUPTED_MESSAGE = ("The finalise run was interrupted (the server may have restarted). "
                       "It is safe to retry.")


def status_path(token: str) -> Path:
    # Local run state, never pushed or pulled: `data/live_rounds/` is not in
    # `sync.SYNC_FOLDERS` (which list files directly under a folder only), and
    # the leading underscore mirrors report_generation's `_generation_status`.
    return _store_path(f"data/live_rounds/_finalize_status/{Path(token).name}.json")


def read_status(token: str) -> Optional[dict]:
    path = status_path(token)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Could not read finalize status {path}: {e}")
        return None


def write_status(token: str, **fields) -> dict:
    """Merge `fields` into the token's status file, refreshing `updated_at`."""
    path = status_path(token)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_status(token) or {
        "token": token, "teg": None, "round": None, "state": None, "message": None,
        "error": None, "cache_errors": [], "records_added": None, "committed": False,
        "step": None, "steps": {}, "started_at": None, "finished_at": None,
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
        return status.get("error") or "Finalize failed."
    if status.get("state") in ACTIVE_STATES and not is_active(status):
        return INTERRUPTED_MESSAGE
    return None


_claim_lock = threading.Lock()


def claim(token: str) -> Optional[dict]:
    """Reserve `token` for a new run.

    Returns the existing status (touching nothing) if a run is already in
    flight or has already finished successfully, so a late second tap can't
    replace the success record with a refusal; otherwise writes a fresh
    `queued` status and returns None.
    """
    # Sync route handlers run concurrently in the threadpool, so the
    # read-then-write must not interleave (one process on Railway, so a
    # process-wide lock is enough).
    with _claim_lock:
        existing = read_status(token)
        if is_active(existing) or (existing or {}).get("state") == "done":
            return existing
        write_status(token, teg=None, round=None, state="queued", message="Queued.", error=None,
                     cache_errors=[], records_added=None, committed=False,
                     step=None, steps={}, started_at=_now(), finished_at=None)
    return None


def _progress_recorder(token: str):
    """A `progress(step, state, error)` callback that persists each step to the
    status file, so a reload or a locked phone still sees the checklist."""
    steps: dict = {}

    def record(step: str, state: str, error: Optional[str] = None) -> None:
        steps[step] = {"state": state, "error": error}
        fields = {"steps": dict(steps)}
        if state == "running":
            fields["step"] = step
        write_status(token, **fields)

    return record


def step_rows(status: Optional[dict]) -> list[dict]:
    """The checklist for `status`: one row per `FINALIZE_STEPS` entry.

    Row `state` is done / running / todo / failed / skipped / notrun. A step the
    run never reached is `todo` while the job is in flight, `notrun` once it has
    ended (or was abandoned).
    """
    from teg_analysis.analysis.live_round import FINALIZE_STEPS

    recorded = (status or {}).get("steps") or {}
    live = is_active(status)
    rows = []
    for i, (key, label) in enumerate(FINALIZE_STEPS, start=1):
        rec = recorded.get(key) or {}
        state = rec.get("state") or ("todo" if live else "notrun")
        if state == "running" and not live:
            state = "notrun"  # the run ended (or died) mid-step
        rows.append({"key": key, "label": label, "index": i, "state": state,
                     "error": rec.get("error")})
    return rows


def current_step(status: Optional[dict]) -> Optional[dict]:
    """The step a live job is on ({"index", "total", "label"}), else None."""
    from teg_analysis.analysis.live_round import FINALIZE_STEPS

    key = (status or {}).get("step")
    for i, (k, label) in enumerate(FINALIZE_STEPS, start=1):
        if k == key:
            return {"index": i, "total": len(FINALIZE_STEPS), "label": label}
    return None


def report_block(teg: int, round_num: Optional[int]) -> Optional[dict]:
    """Why a report can't be generated yet, or None when it can.

    Returns {"message", "link"}. One helper so the page and the server-side
    check on POST show identical text. Fails open if readiness can't be read,
    so a registry hiccup never blocks a report for a sheet-imported round.
    """
    from teg_analysis.analysis.live_round import FINALIZE_STEPS, report_readiness

    try:
        ready = report_readiness(teg, round_num)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not check report readiness for TEG {teg} round {round_num}: {e}")
        return None
    if ready.get("ready"):
        return None

    token = ready.get("token")
    message = ready.get("reason") or "The round data isn't ready yet."
    if token:
        job = read_status(token)
        step = current_step(job) if is_active(job) else None
        if step:
            message = (f"Round {ready.get('round')} data still being processed, "
                       f"step {step['index']} of {len(FINALIZE_STEPS)}.")
    link = f"/admin/live-round/{token}/review" if token else None
    return {"message": message, "link": link}


def run_finalize(token: str) -> None:
    """The background task: finalise the round, clear caches, record the outcome.

    Never raises -- a failure is recorded in the status file instead.
    """
    from teg_analysis.analysis.live_round import (
        finalize_live_round, ConflictsUnresolvedError, LiveRoundInactiveError, LiveRoundNotFoundError,
    )
    from webapp import deps

    try:
        write_status(token, state="running",
                     message="Writing scores and rebuilding the site's stats…")
        result = finalize_live_round(token, progress=_progress_recorder(token))
        deps.clear_all_data_caches()
        steps = [str(ce.get("step", "")) for ce in (result.get("cache_errors") or [])]
        steps = [s for s in steps if s]
        if result.get("cache_errors") and not steps:
            steps = ["unknown"]
        write_status(token, state="done", message="Finalised.", error=None,
                     teg=result.get("teg_num"), round=result.get("round_num"),
                     records_added=result.get("records_added"),
                     committed=bool(result.get("committed")),
                     cache_errors=steps, finished_at=_now())
    except (ConflictsUnresolvedError, LiveRoundInactiveError, LiveRoundNotFoundError, ValueError) as e:
        write_status(token, state="error", error=str(e), message=None, finished_at=_now())
    except Exception as e:  # noqa: BLE001
        logger.error(f"Live round finalize failed: {e}", exc_info=True)
        try:
            write_status(token, state="error", error=f"Finalize failed: {e}", message=None,
                         finished_at=_now())
        except Exception:  # noqa: BLE001 -- status store itself is broken; nothing left to do
            logger.error("Could not record finalize failure", exc_info=True)
