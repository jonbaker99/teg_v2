"""Admin-triggered remote report generation — the clubhouse use case.

Tournament and round reports (the newspaper-style storyline-first pipeline)
have so far only run as local CLI scripts
(`scripts/storyline_full_report_experiment.py`,
`scripts/storyline_round_report_experiment.py`), with the output synced to the
Railway volume by hand afterwards. This module lets `/admin/reports` run the
same pipeline from inside the webapp process, triggered by a button, so a
report is ready to read minutes after the round ends — no laptop required.

State machine per (TEG, round-or-None): `queued -> running -> pushing ->
done | done_local_only | error`. While running, a `phase` field (one of
`PHASES`) says which step is in flight, so the admin page can show progress
instead of one opaque spinner. State lives in a JSON file, not an in-memory
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
import threading
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

#: Steps of one run, in order: (key, label). `generate_report` records the
#: current key in the status file's `phase` field; `phase_rows` turns that into
#: per-step done/active/todo/failed for the templates.
PHASES: tuple[tuple[str, str], ...] = (
    ("storylines", "Storylines"), ("draft", "Draft"), ("voice", "Voice pass"),
    ("publish", "Publish to site"), ("push", "Commit to GitHub"),
)

#: "Generated recently" window for the regenerate confirmation.
RECENT_SECONDS = 6 * 3600  # 6 h

#: How long a finished run stays in the running-reports panel.
ENDED_VISIBLE_SECONDS = 15 * 60  # 15 min

#: An "active" status older than this is treated as abandoned (worker died
#: mid-run, e.g. a Railway redeploy) rather than still in flight.
STALE_AFTER_SECONDS = 1800  # 30 min


def _now() -> str:
    # Whole seconds: older iOS Safari can't parse microseconds in `new Date()`.
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _store_path(rel: str) -> Path:
    """Path to `rel` in the real data store — the volume on Railway, the repo
    working tree locally. Mirrors `teg_analysis.io.sync._store_path`."""
    return Path(_get_volume_path(rel)) if _is_railway() else _get_local_path(rel)


def report_label(teg: int, round_num: Optional[int]) -> str:
    """Human label: "TEG 19 R2" for a round, "TEG 19 tournament" otherwise."""
    return f"TEG {teg} R{round_num}" if round_num else f"TEG {teg} tournament"


def phase_label(key: Optional[str]) -> Optional[str]:
    """Label for a PHASES key; None if `key` is None or unknown."""
    return dict(PHASES).get(key)


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
        "state": None, "phase": None, "message": None, "error": None, "files": [],
        "committed": False, "started_at": None, "finished_at": None,
    }
    existing.update(fields)
    existing["updated_at"] = _now()
    path.write_text(json.dumps(existing, indent=2))
    return existing


def _age_seconds(iso: Optional[str], now: Optional[datetime] = None) -> Optional[float]:
    """Seconds since ISO timestamp `iso`; None if missing or unparseable."""
    if not iso:
        return None
    try:
        then = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return ((now or datetime.now(timezone.utc)) - then).total_seconds()


def is_active(status: Optional[dict], now: Optional[datetime] = None) -> bool:
    """Whether `status` represents a run still in flight (not stale).
    `now` is only for tests."""
    if not status or status.get("state") not in ACTIVE_STATES:
        return False
    updated_at = status.get("updated_at")
    if not updated_at:
        return True
    age = _age_seconds(updated_at, now)
    return True if age is None else age < STALE_AFTER_SECONDS


def phase_rows(status: Optional[dict], now: Optional[datetime] = None) -> list[dict]:
    """One {"key", "label", "state"} per PHASES entry, state being
    done / active / todo / failed, derived from the status file.
    `now` is only for tests."""
    keys = [k for k, _ in PHASES]
    state = (status or {}).get("state")
    marks = ["todo"] * len(keys)
    phase = (status or {}).get("phase")
    idx = keys.index(phase) if phase in keys else None
    if state == "done":
        marks = ["done"] * len(keys)
    elif state == "done_local_only":
        marks = ["done"] * (len(keys) - 1) + ["failed"]
    elif state in ACTIVE_STATES and is_active(status, now):
        if state != "queued" and idx is not None:
            marks = ["done"] * idx + ["active"] + ["todo"] * (len(keys) - idx - 1)
    elif state == "error" or state in ACTIVE_STATES:  # error, or stale (abandoned)
        at = idx or 0
        marks = ["done"] * at + ["failed"] + ["todo"] * (len(keys) - at - 1)
    return [{"key": k, "label": lbl, "state": m} for (k, lbl), m in zip(PHASES, marks)]


def list_statuses() -> list[dict]:
    """Every status file in the status directory; unreadable ones are skipped."""
    directory = status_path(0, None).parent
    if not directory.is_dir():
        return []
    out = []
    for path in sorted(directory.glob("*.json")):
        try:
            out.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not read report-generation status {path}: {e}")
    return out


def running_reports(now: Optional[datetime] = None) -> list[dict]:
    """Active runs plus ones that ended within ENDED_VISIBLE_SECONDS, oldest
    first, each enriched with label / active / stale / phases / phase_label."""
    out = []
    for s in list_statuses():
        active = is_active(s, now)
        stale = not active and s.get("state") in ACTIVE_STATES
        if not active:
            # A stale run has no finished_at: it "ended" when it went stale,
            # STALE_AFTER_SECONDS after its last sign of life (updated_at).
            age = _age_seconds(s.get("updated_at") if stale else s.get("finished_at"), now)
            if age is not None and stale:
                age -= STALE_AFTER_SECONDS
            if age is None or age > ENDED_VISIBLE_SECONDS:
                continue
        if s.get("teg") is None:  # malformed file: skip rather than 500 the page
            continue
        out.append({**s, "label": report_label(s["teg"], s.get("round")), "active": active,
                    "stale": stale, "phases": phase_rows(s, now),
                    "phase_label": phase_label(s.get("phase"))})
    return sorted(out, key=lambda r: r.get("started_at") or "")


def confirmation_needed(teg: int, round_num: Optional[int],
                        now: Optional[datetime] = None) -> Optional[dict]:
    """Why the admin should confirm before (re)generating this report, or None.

    "running": a run is in flight. "recent": one finished within RECENT_SECONDS.
    """
    s = read_status(teg, round_num)
    label = report_label(teg, round_num)
    if is_active(s, now):
        return {"reason": "running", "status": s, "label": label,
                "phase_label": phase_label(s.get("phase"))}
    if s and s.get("state") in ("done", "done_local_only"):
        age = _age_seconds(s.get("finished_at"), now)
        if age is not None and age < RECENT_SECONDS:
            return {"reason": "recent", "status": s, "label": label}
    return None


def fmt_hhmm(iso: Optional[str]) -> str:
    """"HH:MM" (UTC) from an ISO timestamp; "?" if missing or unparseable."""
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return "?"
    if dt.tzinfo is None:  # naive = UTC, as in _age_seconds
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%H:%M")


def artefact_names(teg: int, round_num: Optional[int]) -> list[str]:
    """The storyline-first filenames for this report, matching
    `teg_analysis.reporting.paths._artefact_names`'s storyline-first half plus
    the D3 verify artefact `restyle_voice` writes alongside it."""
    stem = status_key(teg, round_num)
    return [f"{stem}_storyline_plan.json", f"{stem}_report_storylinedraft.md",
            f"{stem}_report_storylinefirst.md", f"{stem}_report_storylinefirst_styled.md",
            f"{stem}_verify.json"]


_claim_lock = threading.Lock()


def claim(teg: int, round_num: Optional[int]) -> Optional[str]:
    """Reserve (teg, round_num) for a new run.

    Returns an error message (and touches nothing) if a run is already active
    for this key; otherwise writes a fresh `queued` status and returns None.
    """
    # Sync route handlers run concurrently in the threadpool, so the
    # read-then-write must not interleave. Railway runs one process, so a
    # process-wide lock is enough.
    with _claim_lock:
        existing = read_status(teg, round_num)
        if is_active(existing):
            label = report_label(teg, round_num)
            return (f"A report for {label} is already generating "
                    f"(started {fmt_hhmm(existing.get('started_at'))} UTC).")
        write_status(teg, round_num, state="queued", phase=None, message="Queued.", error=None,
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


def _run_stage(teg: int, round_num: Optional[int], stage: str) -> None:
    """Run exactly one pipeline stage. Lazy import keeps the heavy pipeline
    (and `scripts/`) off the webapp's startup path. Later stages reuse the
    previous stage's output from disk, so this makes the same LLM calls as
    one whole-run call would."""
    if round_num is None:
        from scripts.storyline_full_report_experiment import run_one as run_tournament
        run_tournament(teg, start_from=stage, stop_after=stage)
    else:
        from scripts.storyline_round_report_experiment import run_one as run_round
        run_round(teg, round_num, start_from=stage, stop_after=stage)


#: Pipeline stages run one at a time so each can be reported as a phase.
_STAGE_MESSAGES = {
    "storylines": "Choosing the storylines...",
    "draft": "Drafting the report...",
    "voice": "Applying the house voice...",
}


def generate_report(teg: int, round_num: Optional[int]) -> None:
    """The background task: run the pipeline, stage the output, push to GitHub.

    Progress is recorded as a `phase` in the status file: storylines, draft,
    voice, publish, push. On failure the failing phase stays in the file.

    Never raises — every failure is recorded in the status file instead, so a
    bad run can't silently die with no trace for the admin page to show.
    """
    kind = "tournament" if round_num is None else "round"
    label = report_label(teg, round_num)
    write_status(teg, round_num, state="running", phase=None,
                message="Generating (storylines -> draft -> voice)...")

    if llm.get_provider() == llm.PROVIDER_API and not llm.has_api_key():
        write_status(teg, round_num, state="error",
                    error="No ANTHROPIC_API_KEY configured on this service.",
                    finished_at=_now())
        return

    t0 = time.monotonic()
    try:
        for stage, message in _STAGE_MESSAGES.items():
            write_status(teg, round_num, state="running", phase=stage, message=message)
            _run_stage(teg, round_num, stage)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Report generation failed for {label}: {e}", exc_info=True)
        write_status(teg, round_num, state="error", error=f"{type(e).__name__}: {e}",
                    finished_at=_now())
        return
    logger.info(f"Report generation for {label} took {time.monotonic() - t0:.0f}s")

    write_status(teg, round_num, state="running", phase="publish",
                message="Publishing to the site...")
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

    write_status(teg, round_num, state="pushing", phase="push",
                message="Committing to GitHub...", files=staged)

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
