"""Selective two-way sync between GitHub and the app's data store.

UI-agnostic port of the legacy ``streamlit/admin_volume_management.py`` GitHub-sync
tab. Nothing here touches Streamlit/FastAPI — every function takes/returns plain
values so the same logic can be driven from a script or a webapp route.

On Railway the "store" is the mounted volume (``/mnt/data_repo``); locally it is
the repo working tree. Operations are byte-level so parquet/csv/md round-trip
safely:

  * **pull** — copy selected files from GitHub down to the store.
  * **push** — copy selected files from the store up to GitHub (single batch commit).

Status is derived from presence + size only (no per-file commit-time lookups), so
the listing stays a single GitHub API call per folder and is responsive.
"""

import base64
import difflib
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .github_operations import GITHUB_REPO, _get_github_branch, batch_commit_to_github
from . import volume_operations

logger = logging.getLogger(__name__)

# Folders eligible for sync (GitHub paths, also used relative to the store).
SYNC_FOLDERS = [
    "data",
    "data/commentary",
    "data/commentary/drafts",
    "data/commentary/round_reports",
]

# Where pre-overwrite backups of store files are kept (one dated dir per pull).
SYNC_BACKUP_ROOT = "data/backups/sync"


def is_railway() -> bool:
    """True when running on Railway (store is the volume, not the working tree)."""
    return bool(volume_operations._is_railway())


def _repo():
    """Return ``(repo, branch)`` for the configured GitHub repository."""
    from github import Github

    token = os.getenv("GITHUB_TOKEN")
    g = Github(token)
    return g.get_repo(GITHUB_REPO), _get_github_branch()


def _store_path(rel_path: str) -> Path:
    """Path to ``rel_path`` in the app's data store (volume on Railway, else local)."""
    if volume_operations._is_railway():
        return Path(volume_operations._get_volume_path(rel_path))
    return volume_operations._get_local_path(rel_path)


def store_label() -> str:
    """Human label for where the store lives (for the UI)."""
    if volume_operations._is_railway():
        return f"Railway volume ({volume_operations._get_volume_path('')})"
    return f"local filesystem ({volume_operations._get_local_path('')})"


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def list_github_files(folder: str) -> dict[str, int]:
    """Map filename -> size for files directly under ``folder`` on GitHub.

    Returns an empty dict if the folder doesn't exist on GitHub.
    """
    repo, branch = _repo()
    try:
        contents = repo.get_contents(folder, ref=branch)
    except Exception:
        return {}

    # A single file path returns a ContentFile, not a list.
    if not isinstance(contents, list):
        contents = [contents]

    return {item.name: int(item.size or 0) for item in contents if item.type == "file"}


def list_store_files(folder: str) -> dict[str, int]:
    """Map filename -> size for files directly under ``folder`` in the store."""
    base = _store_path(folder)
    if not base.exists():
        return {}
    return {
        child.name: child.stat().st_size
        for child in base.iterdir()
        if child.is_file()
    }


# Status ordering: actionable rows first, "in sync" last.
_STATUS_ORDER = {
    "Only on GitHub": 0,
    "Only in store": 1,
    "Different size": 2,
    "Same size": 3,
}


def build_sync_status(folder: str) -> list[dict]:
    """Compare a folder across GitHub and the store.

    Returns a list of rows ``{name, gh_size, store_size, on_github, on_store,
    status}`` sorted with actionable differences first.
    """
    gh = list_github_files(folder)
    store = list_store_files(folder)

    rows = []
    for name in sorted(set(gh) | set(store)):
        on_gh = name in gh
        on_store = name in store
        if on_gh and not on_store:
            status = "Only on GitHub"
        elif on_store and not on_gh:
            status = "Only in store"
        elif gh.get(name) != store.get(name):
            status = "Different size"
        else:
            status = "Same size"
        rows.append({
            "name": name,
            "gh_size": gh.get(name),
            "store_size": store.get(name),
            "on_github": on_gh,
            "on_store": on_store,
            "status": status,
        })

    rows.sort(key=lambda r: (_STATUS_ORDER.get(r["status"], 9), r["name"]))
    return rows


# ---------------------------------------------------------------------------
# Byte-level transfer
# ---------------------------------------------------------------------------

def github_download_bytes(path: str) -> bytes:
    """Download a single file's bytes from GitHub (handles large/blob files)."""
    repo, branch = _repo()
    content = repo.get_contents(path, ref=branch)
    if isinstance(content, list):
        raise IsADirectoryError(f"{path} is a directory, not a file")
    if content.content:
        return base64.b64decode(content.content)
    # Files >1MB come back with empty content — fetch the git blob instead.
    blob = repo.get_git_blob(content.sha)
    return base64.b64decode(blob.content)


# ---------------------------------------------------------------------------
# Timestamps + overwrite-conflict detection
# ---------------------------------------------------------------------------

def _store_mtime(rel_path: str):
    """Last-modified time of a store file (UTC), or None if absent."""
    p = _store_path(rel_path)
    if not p.exists():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)


def github_commit_time(path: str):
    """Last-commit time for a path on GitHub (UTC), or None if unknown."""
    try:
        repo, branch = _repo()
        commits = repo.get_commits(path=path, sha=branch)
        dt = commits[0].commit.committer.date
    except Exception:  # noqa: BLE001 - treat any lookup failure as "unknown"
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def detect_pull_conflicts(folder: str, names: list[str]) -> list[dict]:
    """Files where pulling would overwrite a *newer* store copy with GitHub's.

    Returns ``[{name, store_time, gh_time}, ...]`` (only when both times are known
    and the store copy is newer than GitHub).
    """
    conflicts = []
    for name in names:
        rel = f"{folder}/{name}"
        st = _store_mtime(rel)
        gh = github_commit_time(rel)
        if st and gh and st > gh:
            conflicts.append({"name": name, "store_time": st, "gh_time": gh})
    return conflicts


def detect_push_conflicts(folder: str, names: list[str]) -> list[dict]:
    """Files where pushing would overwrite a *newer* GitHub copy with the store's."""
    conflicts = []
    for name in names:
        rel = f"{folder}/{name}"
        st = _store_mtime(rel)
        gh = github_commit_time(rel)
        if st and gh and gh > st:
            conflicts.append({"name": name, "store_time": st, "gh_time": gh})
    return conflicts


# ---------------------------------------------------------------------------
# Pre-action preview + diff
# ---------------------------------------------------------------------------

# Extensions we can show a textual diff for. Everything else (parquet, etc.) is
# treated as binary — size + timestamp only, no line-level diff.
_DIFFABLE_EXTS = {".csv", ".md", ".txt", ".json"}


def build_sync_preview(action: str, folder: str, names: list[str]) -> list[dict]:
    """Describe what ``action`` ('pull' or 'push') will do to each selected file.

    For each file returns ``{name, outcome, source_size, dest_size, store_time,
    gh_time, newer, is_conflict, diffable}`` where:

      * ``outcome`` is ``'create'`` (file doesn't exist on the destination yet) or
        ``'overwrite'`` (an existing destination copy will be replaced).
      * ``newer`` is ``'store'`` / ``'github'`` / ``'same'`` / ``'unknown'`` — which
        side was modified more recently (so the user can see what they'd lose).
      * ``is_conflict`` is True when the action would overwrite the *newer* copy
        (store newer on a pull, GitHub newer on a push).
      * ``diffable`` is True when a textual diff is available (see ``file_diff``).

    One GitHub API call lists the folder; ``github_commit_time`` is then queried
    per selected file (bounded by the selection size).
    """
    gh_sizes = list_github_files(folder)
    store_sizes = list_store_files(folder)

    rows = []
    for name in names:
        rel = f"{folder}/{name}"
        on_gh = name in gh_sizes
        on_store = name in store_sizes
        st_time = _store_mtime(rel)
        gh_time = github_commit_time(rel)

        if action == "pull":  # GitHub -> store, so the store copy is the destination
            outcome = "overwrite" if on_store else "create"
            source_size, dest_size = gh_sizes.get(name), store_sizes.get(name)
        else:  # push: store -> GitHub, GitHub copy is the destination
            outcome = "overwrite" if on_gh else "create"
            source_size, dest_size = store_sizes.get(name), gh_sizes.get(name)

        if st_time and gh_time:
            if st_time > gh_time:
                newer = "store"
            elif gh_time > st_time:
                newer = "github"
            else:
                newer = "same"
        else:
            newer = "unknown"

        # A conflict is overwriting the newer copy: store newer on pull, GitHub
        # newer on push.
        is_conflict = (
            outcome == "overwrite"
            and ((action == "pull" and newer == "store")
                 or (action == "push" and newer == "github"))
        )

        rows.append({
            "name": name,
            "outcome": outcome,
            "source_size": source_size,
            "dest_size": dest_size,
            "store_time": st_time,
            "gh_time": gh_time,
            "newer": newer,
            "is_conflict": is_conflict,
            "diffable": Path(name).suffix.lower() in _DIFFABLE_EXTS,
        })
    return rows


def file_diff(folder: str, name: str, max_lines: int = 400) -> dict:
    """Unified diff of a file's store copy vs its GitHub copy.

    Returns ``{diffable, identical, lines, truncated, reason}``. Diffs run from
    store -> GitHub regardless of action (a stable, readable direction); the UI
    labels which side is which. Binary/unknown extensions return
    ``diffable=False`` with a ``reason``. A missing side is shown as empty so the
    diff reads as a full add/remove.
    """
    rel = f"{folder}/{name}"
    if Path(name).suffix.lower() not in _DIFFABLE_EXTS:
        return {"diffable": False, "reason": "binary (no text diff)"}

    def _decode(raw: bytes | None):
        if raw is None:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    try:
        gh_raw = github_download_bytes(rel)
    except Exception:  # noqa: BLE001 - absent on GitHub or fetch failed
        gh_raw = None
    sp = _store_path(rel)
    store_raw = sp.read_bytes() if sp.exists() else None

    store_text = _decode(store_raw)
    gh_text = _decode(gh_raw)
    if (store_raw is not None and store_text is None) or \
       (gh_raw is not None and gh_text is None):
        return {"diffable": False, "reason": "not valid UTF-8 text"}

    if store_raw is not None and gh_raw is not None and store_raw == gh_raw:
        return {"diffable": True, "identical": True, "lines": [], "truncated": False}

    diff = difflib.unified_diff(
        (store_text or "").splitlines(),
        (gh_text or "").splitlines(),
        fromfile=f"store/{rel}",
        tofile=f"github/{rel}",
        lineterm="",
    )
    lines = list(diff)
    truncated = len(lines) > max_lines
    return {
        "diffable": True,
        "identical": False,
        "lines": lines[:max_lines],
        "truncated": truncated,
    }


# ---------------------------------------------------------------------------
# Store backups + restore
# ---------------------------------------------------------------------------

def backup_store_file(rel_path: str, timestamp: str) -> str | None:
    """Copy a store file into the dated sync-backup dir before it's overwritten.

    Args:
        rel_path: File to back up, e.g. ``'data/round_info.csv'``.
        timestamp: Shared per-operation stamp (groups one pull's backups).

    Returns:
        The backup's relative path, or None if the source doesn't exist.
    """
    src = _store_path(rel_path)
    if not src.exists():
        return None
    backup_rel = f"{SYNC_BACKUP_ROOT}/{timestamp}/{rel_path}"
    dest = _store_path(backup_rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return backup_rel


def list_sync_backups() -> list[dict]:
    """List store backups, newest first.

    Returns ``[{timestamp, original, backup_rel, size}, ...]`` where ``original``
    is the path the backup would restore to.
    """
    base = _store_path(SYNC_BACKUP_ROOT)
    if not base.exists():
        return []

    rows = []
    for ts_dir in sorted((d for d in base.iterdir() if d.is_dir()),
                         key=lambda d: d.name, reverse=True):
        for f in sorted(ts_dir.rglob("*")):
            if f.is_file():
                original = f.relative_to(ts_dir).as_posix()
                rows.append({
                    "timestamp": ts_dir.name,
                    "original": original,
                    "backup_rel": f"{SYNC_BACKUP_ROOT}/{ts_dir.name}/{original}",
                    "size": f.stat().st_size,
                })
    return rows


def backups_for(original_rel: str) -> list[dict]:
    """Backups whose restore target is ``original_rel`` (newest first)."""
    return [b for b in list_sync_backups() if b["original"] == original_rel]


def restore_backup(backup_rel: str, *, backup_current: bool = True) -> str:
    """Restore a backup file back to its original location in the store.

    By default the *current* store copy is backed up first (``backup_current``),
    so a restore is itself reversible — the replaced file lands under a fresh
    dated dir alongside the other backups. Does **not** push to GitHub (use Push
    afterwards if you want the restored version on GitHub).

    Returns the original path that was restored.
    """
    if not backup_rel.startswith(f"{SYNC_BACKUP_ROOT}/"):
        raise ValueError(f"Not a sync backup path: {backup_rel}")

    src = _store_path(backup_rel)
    if not src.exists():
        raise FileNotFoundError(backup_rel)

    # Strip "data/backups/sync/<timestamp>/" to recover the original rel path.
    rest = backup_rel[len(f"{SYNC_BACKUP_ROOT}/"):]
    original_rel = rest.split("/", 1)[1]

    # Back up the file we're about to overwrite so the restore is reversible too.
    if backup_current:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_store_file(original_rel, timestamp)

    dest = _store_path(original_rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return original_rel


# ---------------------------------------------------------------------------
# Volume browsing + delete
# ---------------------------------------------------------------------------

def _safe_rel(rel: str) -> str:
    """Normalise a store-relative path and reject traversal outside the store."""
    rel = (rel or "").strip().strip("/")
    parts = []
    for part in rel.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("Path traversal is not allowed")
        parts.append(part)
    return "/".join(parts)


def list_store_dir(rel: str = "") -> dict:
    """List one directory in the store for the volume browser.

    Returns ``{path, parent, entries}`` where ``entries`` is a list of
    ``{name, rel, is_dir, size, mtime}`` (directories first, then files, each
    alphabetical). ``parent`` is the rel path one level up, or None at the root.
    """
    rel = _safe_rel(rel)
    base = _store_path(rel) if rel else _store_path("")
    parent = None
    if rel:
        parent = rel.rsplit("/", 1)[0] if "/" in rel else ""

    entries: list[dict] = []
    if base.exists() and base.is_dir():
        for child in base.iterdir():
            child_rel = f"{rel}/{child.name}" if rel else child.name
            is_dir = child.is_dir()
            stat = child.stat()
            entries.append({
                "name": child.name,
                "rel": child_rel,
                "is_dir": is_dir,
                "size": None if is_dir else stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            })
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return {"path": rel, "parent": parent, "entries": entries}


def read_store_file(rel: str) -> bytes:
    """Return the raw bytes of a store file (for download). Validates the path."""
    rel = _safe_rel(rel)
    p = _store_path(rel)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(rel)
    return p.read_bytes()


def delete_store_file(rel: str) -> dict:
    """Delete a single store file, backing it up first so it stays restorable.

    The backup lands under the same dated sync-backup tree used by pulls, so it
    shows up in the **Backups / restore** panel on the GitHub-sync page. Does
    **not** touch GitHub. Refuses directories and anything under the backup root.

    Returns ``{deleted: rel, backup_rel: str|None}``.
    """
    rel = _safe_rel(rel)
    if rel.startswith(SYNC_BACKUP_ROOT):
        raise ValueError("Refusing to delete from the backup area")
    p = _store_path(rel)
    if not p.exists():
        raise FileNotFoundError(rel)
    if p.is_dir():
        raise IsADirectoryError(f"{rel} is a directory")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_rel = backup_store_file(rel, timestamp)
    p.unlink()
    return {"deleted": rel, "backup_rel": backup_rel}


# ---------------------------------------------------------------------------
# Pull / push orchestrators
# ---------------------------------------------------------------------------

def pull_files(folder: str, names: list[str]) -> dict:
    """Copy ``names`` from GitHub ``folder`` down to the store.

    Each existing store file is backed up (under a single dated dir) *before* it
    is overwritten, so a pull is always reversible via :func:`restore_backup`.

    Returns ``{pulled: int, failed: [(name, error), ...], backups: [rel, ...]}``.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pulled = 0
    failed: list[tuple[str, str]] = []
    backups: list[str] = []
    for name in names:
        path = f"{folder}/{name}"
        try:
            raw = github_download_bytes(path)
            # Back up the current store copy before clobbering it.
            backup_rel = backup_store_file(path, timestamp)
            if backup_rel:
                backups.append(backup_rel)
            dest = _store_path(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            pulled += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"Pull failed for {path}: {e}", exc_info=True)
            failed.append((name, str(e)))
    return {"pulled": pulled, "failed": failed, "backups": backups}


def push_files(folder: str, names: list[str], commit_message: str = None) -> dict:
    """Copy ``names`` from the store up to GitHub ``folder`` in a single commit.

    Returns ``{pushed: int, failed: [(name, error), ...], committed: bool}``.
    """
    if commit_message is None:
        commit_message = f"Sync {len(names)} file(s) from store to GitHub"

    files_data = []
    failed: list[tuple[str, str]] = []
    for name in names:
        rel = f"{folder}/{name}"
        try:
            raw = _store_path(rel).read_bytes()
            files_data.append({"file_path": rel, "data": raw})
        except Exception as e:  # noqa: BLE001
            logger.error(f"Push read failed for {rel}: {e}", exc_info=True)
            failed.append((name, str(e)))

    committed = False
    if files_data:
        batch_commit_to_github(files_data, commit_message)
        committed = True

    return {"pushed": len(files_data), "failed": failed, "committed": committed}


# ---------------------------------------------------------------------------
# Report files: GitHub -> store convenience
# ---------------------------------------------------------------------------
#
# Tournament/round reports are generated by an *offline* pipeline and reach
# GitHub via a plain git push, not through the app's write path — so the app
# never sees them change. ``webapp/routes/reports.py`` reads them through the
# volume-aware ``read_text_file`` (volume-first, GitHub fallback + cache), so a
# *new* report is pulled and cached on first view automatically. What that path
# cannot do is refresh a *regenerated* report — same filename, new content —
# because the volume already has a (now stale) cached copy. This helper is that
# refresh lever: it re-pulls every report file from GitHub, overwriting the
# store copy (with a backup first, via :func:`pull_files`).

# The report files served by webapp/routes/reports.py, per folder. We sync only
# these (not every draft/version .md that shares the folder) to keep the set small.
_REPORT_FILE_PATTERNS = {
    "data/commentary": re.compile(
        r"^teg_\d+_(report_styled|round_\d+_report_styled)\.md$"),
    "data/commentary/drafts": re.compile(
        r"^teg_\d+_(main_report|satire)\.md$"),
    "data/commentary/round_reports": re.compile(
        r"^(TEG\d+_R\d+_report|teg_\d+_round_\d+_report)\.md$"),
}


def sync_report_files() -> dict:
    """Re-pull every report file from GitHub to the store, overwriting.

    Only files matching the report naming conventions (see
    ``_REPORT_FILE_PATTERNS``) are pulled; existing store copies are backed up
    before being overwritten (via :func:`pull_files`). This is the refresh lever
    for a *regenerated* report — the case ``read_text_file``'s volume cache
    would otherwise keep serving stale.

    Returns:
        ``{pulled: int, failed: [(name, error), ...], folders: {folder: count}}``.
    """
    total_pulled = 0
    failed: list[tuple[str, str]] = []
    per_folder: dict[str, int] = {}

    for folder, pattern in _REPORT_FILE_PATTERNS.items():
        names = sorted(n for n in list_github_files(folder) if pattern.match(n))
        if not names:
            continue
        outcome = pull_files(folder, names)
        total_pulled += outcome["pulled"]
        failed.extend(outcome["failed"])
        per_folder[folder] = outcome["pulled"]

    return {"pulled": total_pulled, "failed": failed, "folders": per_folder}
