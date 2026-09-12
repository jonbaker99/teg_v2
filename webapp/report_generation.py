"""Admin-triggered remote report generation — the clubhouse use case.

Tournament and round reports (the newspaper-style storyline-first pipeline)
have so far only run as local CLI scripts
(`scripts/storyline_full_report_experiment.py`,
`scripts/storyline_round_report_experiment.py`), with the output synced to the
Railway volume by hand afterwards. This module lets `/admin/reports` run the
same pipeline from inside the webapp process, triggered by a button, so a
report is ready to read minutes after the round ends — no laptop required.

State machine per (TEG, round-or-None): `queued -> running -> pushing ->
done | done_local_only | error`. State lives in a JSON file, not an in-memory
dict, because a run takes minutes and the admin's phone screen may lock and
unlock mid-poll — see `webapp/README.md`'s admin section for why this differs
from the volume-sync jobs' in-memory `_sync_jobs` (admin.py), which only ever
run for seconds.

The pipeline writes its artefacts to a CWD-relative `data/commentary/` (see
`teg_analysis.reporting.paths.output_dir`), which on Railway is NOT the
mounted volume the live site reads from (`data/` is excluded from the Docker
image; the volume is mounted separately at runtime) — so every run here ends
with a staging copy into the real store before the report is visible at
`/teg-reports`, followed by a push to GitHub as the sync-of-record.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from teg_analysis.io import _get_local_path, _get_volume_path, _is_railway, push_files
from teg_analysis.reporting import llm
from teg_analysis.reporting.paths import output_dir

logger = logging.getLogger(__name__)

#: States in which a run is still (or recently was) doing something. A status
#: file in one of these blocks a new run for the same key until it finishes or
#: goes stale.
ACTIVE_STATES = ("queued", "running", "pushing")

#: An "active" status older than this is treated as abandoned (worker died
#: mid-run, e.g. a Railway redeploy) rather than still in flight.
STALE_AFTER_SECONDS = 1800  # 30 min


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_path(rel: str) -> Path:
    """Path to `rel` in the real data store — the volume on Railway, the repo
    working tree locally. Mirrors `teg_analysis.io.sync._store_path`."""
    return Path(_get_volume_path(rel)) if _is_railway() else _get_local_path(rel)


def status_key(teg: int, round_num: Optional[int]) -> str:
    return f"teg_{teg}" if round_num is None else f"teg_{teg}_round_{round_num}"


def status_path(teg: int, round_num: Optional[int]) -> Path:
    # Leading underscore keeps this out of `sync._REPORT_FILE_PATTERNS` and
    # SYNC_FOLDERS listings — this is local run state, never pushed or pulled.
    return _store_path(f"data/commentary/_generation_status/{status_key(teg, round_num)}.json")


def read_status(teg: int, round_num: Optional[int]) -> Optional[dict]:
    path = status_path(teg, round_num)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Could not read report-generation status {path}: {e}")
        return None


def write_status(teg: int, round_num: Optional[int], **fields) -> dict:
    """Merge `fields` into the status file for (teg, round_num), refreshing
    `updated_at`. Creates the file (with sensible defaults) on first write."""
    path = status_path(teg, round_num)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_status(teg, round_num) or {
        "teg": teg, "round": round_num,
        "kind": "tournament" if round_num is None else "round",
        "state": None, "message": None, "error": None, "files": [],
        "committed": False, "started_at": None, "finished_at": None,
    }
    existing.update(fields)
    existing["updated_at"] = _now()
    path.write_text(json.dumps(existing, indent=2))
    return existing


def is_active(status: Optional[dict]) -> bool:
    """Whether `status` represents a run still in flight (not stale)."""
    if not status or status.get("state") not in ACTIVE_STATES:
        return False
    updated_at = status.get("updated_at")
    if not updated_at:
        return True
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)).total_seconds()
    except ValueError:
        return True
    return age < STALE_AFTER_SECONDS


def artefact_names(teg: int, round_num: Optional[int]) -> list[str]:
    """The four storyline-first filenames for this report, matching
    `teg_analysis.reporting.paths._artefact_names`'s storyline-first half."""
    stem = status_key(teg, round_num)
    return [f"{stem}_storyline_plan.json", f"{stem}_report_storylinedraft.md",
            f"{stem}_report_storylinefirst.md", f"{stem}_report_storylinefirst_styled.md"]


def claim(teg: int, round_num: Optional[int]) -> Optional[str]:
    """Reserve (teg, round_num) for a new run.

    Returns an error message (and touches nothing) if a run is already active
    for this key; otherwise writes a fresh `queued` status and returns None.
    """
    existing = read_status(teg, round_num)
    if is_active(existing):
        label = f"TEG {teg}" + (f" R{round_num}" if round_num else "")
        return f"A report for {label} is already generating (started {existing.get('started_at', '?')})."
    write_status(teg, round_num, state="queued", message="Queued.", error=None,
                files=[], committed=False, started_at=_now(), finished_at=None)
    return None


def stage_artefacts_to_store(teg: int, round_num: Optional[int]) -> list[str]:
    """Copy the pipeline's CWD-relative output into the real store.

    The pipeline always writes under `output_dir()` (CWD-relative
    `data/commentary`), which in local dev *is* the store, but on Railway is
    an ephemeral path inside the container — the real store is the mounted
    volume. Returns the artefact names actually found and staged.
    """
    src_dir = Path(output_dir(create=False))
    staged = []
    for name in artefact_names(teg, round_num):
        src = src_dir / name
        if not src.is_file():
            logger.warning(f"Report generation: expected artefact missing: {src}")
            continue
        dest = _store_path(f"data/commentary/{name}")
        if src.resolve() != dest.resolve():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        staged.append(name)
    return staged


def generate_report(teg: int, round_num: Optional[int]) -> None:
    """The background task: run the pipeline, stage the output, push to GitHub.

    Never raises — every failure is recorded in the status file instead, so a
    bad run can't silently die with no trace for the admin page to show.
    """
    kind = "tournament" if round_num is None else "round"
    label = f"TEG {teg}" + (f" R{round_num}" if round_num else "")
    write_status(teg, round_num, state="running",
                message="Generating (storylines -> draft -> voice)...")

    if llm.get_provider() == llm.PROVIDER_API and not llm.has_api_key():
        write_status(teg, round_num, state="error",
                    error="No ANTHROPIC_API_KEY configured on this service.",
                    finished_at=_now())
        return

    t0 = time.monotonic()
    try:
        if round_num is None:
            from scripts.storyline_full_report_experiment import run_one as run_tournament
            run_tournament(teg, start_from="storylines", stop_after="voice")
        else:
            from scripts.storyline_round_report_experiment import run_one as run_round
            run_round(teg, round_num, start_from="storylines", stop_after="voice")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Report generation failed for {label}: {e}", exc_info=True)
        write_status(teg, round_num, state="error", error=f"{type(e).__name__}: {e}",
                    finished_at=_now())
        return
    logger.info(f"Report generation for {label} took {time.monotonic() - t0:.0f}s")

    try:
        staged = stage_artefacts_to_store(teg, round_num)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Staging report artefacts failed for {label}: {e}", exc_info=True)
        write_status(teg, round_num, state="error",
                    error=f"Generated, but copying into the store failed: {e}",
                    finished_at=_now())
        return

    names = artefact_names(teg, round_num)
    required = {names[0], names[3]}  # storyline_plan.json, report_storylinefirst_styled.md
    if not required.issubset(staged):
        write_status(teg, round_num, state="error", files=staged,
                    error=f"Generation finished, but required artefact(s) were not written: "
                          f"{sorted(required - set(staged))}",
                    finished_at=_now())
        return

    from webapp import deps
    deps.clear_all_data_caches()  # report now readable at /teg-reports

    write_status(teg, round_num, state="pushing", message="Committing to GitHub...", files=staged)

    commit_message = f"Add {kind} report for TEG {teg}" + (f" R{round_num}" if round_num else "")
    try:
        outcome = push_files("data/commentary", staged, commit_message=commit_message)
        if outcome["failed"]:
            write_status(teg, round_num, state="done_local_only", committed=outcome["committed"],
                        error=f"Report is live on the site, but the GitHub push partly failed: "
                              f"{outcome['failed']}",
                        finished_at=_now())
        else:
            write_status(teg, round_num, state="done", message="Report ready and committed.",
                        committed=True, error=None, finished_at=_now())
    except Exception as e:  # noqa: BLE001
        logger.error(f"GitHub push failed for {label}: {e}", exc_info=True)
        write_status(teg, round_num, state="done_local_only",
                    error=f"Report is live on the site, but the GitHub push failed: {e}. "
                          f"Retry from /admin/volume-sync (push data/commentary).",
                    finished_at=_now())
