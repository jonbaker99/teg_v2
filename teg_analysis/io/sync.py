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
import logging
import os
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
# Pull / push orchestrators
# ---------------------------------------------------------------------------

def pull_files(folder: str, names: list[str]) -> dict:
    """Copy ``names`` from GitHub ``folder`` down to the store.

    Returns ``{pulled: int, failed: [(name, error), ...]}``.
    """
    pulled = 0
    failed: list[tuple[str, str]] = []
    for name in names:
        path = f"{folder}/{name}"
        try:
            raw = github_download_bytes(path)
            dest = _store_path(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            pulled += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"Pull failed for {path}: {e}", exc_info=True)
            failed.append((name, str(e)))
    return {"pulled": pulled, "failed": failed}


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
