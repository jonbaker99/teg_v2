# streamlit/admin_volume_management.py
# Two-way Data Sync: GitHub <-> Railway Volume

import os
import io
import time
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple, Optional, List

import requests
import pandas as pd
import streamlit as st

# === IMPORTS FROM YOUR UTILS (reused when available) ===
try:
    from utils import (
        read_from_github,        # Optional helper (not required)
        write_to_github,         # Optional helper (not required)
        get_current_branch,      # Required or we'll fallback to env/default
        GITHUB_REPO,             # Required or we'll fallback to env
        clear_all_caches         # Optional helper; we'll fallback to st.cache_data.clear()
    )
except Exception:
    # Minimal fallbacks if utils aren't importable (keeps this page self-contained)
    read_from_github = None
    write_to_github = None
    def get_current_branch() -> str:
        return os.getenv("GIT_BRANCH") or os.getenv("RAILWAY_GIT_BRANCH") or "main"
    GITHUB_REPO = os.getenv("GITHUB_REPO", "your-org/your-repo")
    def clear_all_caches():
        st.cache_data.clear()

# === PAGE CONFIG ===
st.set_page_config(page_title="Data sync: GitHub ↔ Railway volume", page_icon="🔁")
st.title("🔁 Data sync: GitHub ↔ Railway volume")
st.caption("Keep your Railway volume and the GitHub `data/` folder in step, in **both** directions.")

# === ENVIRONMENT GUARD ===
if not os.getenv("RAILWAY_ENVIRONMENT"):
    st.error("❌ This page only works on Railway (volume not available locally).")
    st.info("💡 On local development, files are read directly from your local filesystem; no Railway volume attached.")
    st.stop()

# === CONSTANTS & CONFIG ===
# Where the Railway volume is mounted. Adjust if you've mounted elsewhere.
VOLUME_BASE = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/mnt/data_repo")  # e.g., "/mnt/data_repo"
# Base path for data in GitHub
DATA_BASE = "data"
API_BASE = "https://api.github.com"
# For Contents API calls (create/update/list)
GH_ACCEPT = "application/vnd.github+json"

# Available folders to sync
AVAILABLE_FOLDERS = [
    "data",                      # Root data folder
    "data/commentary",           # Commentary reports (production)
    "data/commentary/drafts",    # Commentary drafts
]

# === AUTH ===
def _get_token() -> Optional[str]:
    return os.getenv("GITHUB_TOKEN") or st.secrets.get("GITHUB_TOKEN")

def _headers() -> Dict[str, str]:
    token = _get_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}", "Accept": GH_ACCEPT}

# === BRANCH / REPO RESOLUTION ===
def _get_repo_and_branch() -> Tuple[str, str]:
    repo = GITHUB_REPO or os.getenv("GITHUB_REPO", "")
    branch = get_current_branch() if callable(get_current_branch) else (os.getenv("GIT_BRANCH") or "main")
    return repo, branch

# === TIME HELPERS ===
def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _parse_github_date(s: str) -> datetime:
    # e.g. "2025-10-06T09:41:33Z"
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

# === GITHUB LISTING ===
@st.cache_data(ttl=300)
def list_github_files(folder_path: str) -> pd.DataFrame:
    """List files under GitHub folder path with last commit timestamp and size."""
    repo, branch = _get_repo_and_branch()
    token = _get_token()
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN (set in env or st.secrets).")

    # 1) List directory contents for specified folder
    r = requests.get(
        f"{API_BASE}/repos/{repo}/contents/{folder_path}?ref={branch}",
        headers=_headers(),
        timeout=30,
    )
    if r.status_code == 404:
        # No directory found
        return pd.DataFrame(columns=["File", "GitHub modified", "GitHub size", "GitHub path"])
    r.raise_for_status()
    entries = r.json()

    files = []
    for item in entries:
        if item.get("type") != "file":
            continue
        name = item["name"]
        size = int(item.get("size") or 0)
        path = item["path"]

        # 2) Get last commit for that path (per_page=1)
        c = requests.get(
            f"{API_BASE}/repos/{repo}/commits",
            params={"path": path, "per_page": 1, "sha": branch},
            headers=_headers(),
            timeout=30,
        )
        if c.status_code == 200 and isinstance(c.json(), list) and c.json():
            commit = c.json()[0]
            dt = commit["commit"]["committer"]["date"]  # ISO string
            modified = _parse_github_date(dt)
        else:
            modified = None

        files.append(
            {
                "File": name,
                "GitHub modified": modified,
                "GitHub size": size,
                "GitHub path": path,
            }
        )

    df = pd.DataFrame(files)
    if df.empty:
        df = pd.DataFrame(columns=["File", "GitHub modified", "GitHub size", "GitHub path"])
    return df

# === VOLUME LISTING ===
@st.cache_data(ttl=60)
def list_volume_files(folder_path: str) -> pd.DataFrame:
    """List files on the Railway volume for specified folder path."""
    # Convert GitHub path (data/commentary) to volume path (/mnt/data_repo/data/commentary)
    p = Path(VOLUME_BASE) / folder_path
    if not p.exists():
        return pd.DataFrame(columns=["File", "Volume modified", "Volume size", "Volume path", "Relative path"])

    rows = []
    for child in p.iterdir():
        if child.is_file():
            stat = child.stat()
            # Store relative path from folder_path for comparison with GitHub
            rows.append(
                {
                    "File": child.name,
                    "Volume modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    "Volume size": stat.st_size,
                    "Volume path": str(child),
                    "Relative path": f"{folder_path}/{child.name}",
                }
            )
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["File", "Volume modified", "Volume size", "Volume path", "Relative path"])
    return df

def _status_row(row) -> str:
    """Derive status classification comparing GitHub vs Volume (NaN-safe)."""
    # sizes are coerced to ints in merged_status(), so these are safe:
    gsz = int(row.get("GitHub size", 0))
    vsz = int(row.get("Volume size", 0))

    gdt = row.get("GitHub modified")
    vdt = row.get("Volume modified")

    if pd.isna(row.get("GitHub path")) and not pd.isna(row.get("Volume path")):
        return "Only on volume"
    if pd.isna(row.get("Volume path")) and not pd.isna(row.get("GitHub path")):
        return "Only on GitHub"

    # If either date missing, lean on size diff
    if (gdt is None or pd.isna(gdt)) or (vdt is None or pd.isna(vdt)):
        if gsz != vsz:
            return "Different size"
        return "Check required"

    # Time comparison tolerance (seconds)
    tol = 2
    delta = (gdt - vdt).total_seconds()

    if abs(delta) <= tol and gsz == vsz:
        return "Match"
    if delta > tol:
        return "Newer on GitHub"
    if delta < -tol:
        return "Newer on volume"
    if gsz != vsz:
        return "Different size"
    return "Check required"

@st.cache_data(ttl=60)
def merged_status(folder_path: str) -> pd.DataFrame:
    gh = list_github_files(folder_path)
    vol = list_volume_files(folder_path)

    merged = pd.merge(
        gh, vol, how="outer", on="File", suffixes=("", "")
    )  # columns already distinct (GitHub/Volume prefixes in names)

    if merged.empty:
        return pd.DataFrame(
            columns=[
                "File", "GitHub modified", "GitHub size", "GitHub path",
                "Volume modified", "Volume size", "Volume path", "Status"
            ]
        )

    # Ensure proper dtypes
    # Dates → datetime (tz-aware)
    for col in ["GitHub modified", "Volume modified"]:
        if col in merged.columns:
            merged[col] = pd.to_datetime(merged[col], utc=True, errors="coerce")

    # Sizes → numeric, NaN→0, int
    for col in ["GitHub size", "Volume size"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype(int)

    # Derive status
    merged["Status"] = merged.apply(_status_row, axis=1)

    # Sort: most actionable first
    order = pd.CategoricalDtype(
        categories=[
            "Only on volume", "Newer on volume",
            "Only on GitHub", "Newer on GitHub",
            "Different size", "Check required", "Match"
        ],
        ordered=True,
    )
    merged["Status"] = merged["Status"].astype(order)
    merged = merged.sort_values(["Status", "File"]).reset_index(drop=True)
    return merged

# === LOW-LEVEL GITHUB CONTENT OPS (REST) ===
def gh_get_contents_path(gh_path: str) -> Optional[Dict]:
    repo, branch = _get_repo_and_branch()
    r = requests.get(
        f"{API_BASE}/repos/{repo}/contents/{gh_path}",
        params={"ref": branch},
        headers=_headers(),
        timeout=30,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def gh_download_bytes(gh_path: str) -> bytes:
    data = gh_get_contents_path(gh_path)
    if not data:
        raise FileNotFoundError(f"GitHub path not found: {gh_path}")
    if data.get("encoding") == "base64" and "content" in data:
        return base64.b64decode(data["content"])
    # Fallback to download_url if provided
    dl = data.get("download_url")
    if not dl:
        raise RuntimeError(f"No content available for {gh_path}")
    r = requests.get(dl, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.content

def gh_put_file(gh_path: str, content_bytes: bytes, message: str) -> Tuple[bool, str]:
    """Create or update file using Contents API; detects existing file for sha."""
    repo, branch = _get_repo_and_branch()
    existing = gh_get_contents_path(gh_path)
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": branch,
    }
    if isinstance(existing, dict) and existing.get("sha"):
        payload["sha"] = existing["sha"]

    r = requests.put(
        f"{API_BASE}/repos/{repo}/contents/{gh_path}",
        headers=_headers(),
        json=payload,
        timeout=60,
    )
    if r.status_code in (200, 201):
        return True, ("Updated" if "sha" in payload else "Created") + f" {gh_path}"
    try:
        detail = r.json()
    except Exception:
        detail = r.text
    return False, f"GitHub API error {r.status_code}: {detail}"

# === FILE OPS (VOLUME) ===
def vol_write_bytes(relative_path: str, raw: bytes) -> None:
    """Write bytes to volume using full relative path (e.g., 'data/commentary/file.md')"""
    out = Path(VOLUME_BASE) / relative_path
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        f.write(raw)

def vol_read_bytes(relative_path: str) -> bytes:
    """Read bytes from volume using full relative path (e.g., 'data/commentary/file.md')"""
    p = Path(VOLUME_BASE) / relative_path
    if not p.exists():
        raise FileNotFoundError(str(p))
    return p.read_bytes()

# === FOLDER SELECTION ===
selected_folder = st.selectbox(
    "Select folder to sync",
    options=AVAILABLE_FOLDERS,
    index=0,
    help="Choose which folder to synchronize between GitHub and Railway volume"
)

st.divider()

# === SUMMARY / CONTEXT BOX ===
repo, branch = _get_repo_and_branch()
info1, info2, info3, info4 = st.columns([2.2, 1.5, 2, 2])
info1.metric("GitHub repo", repo)
info2.metric("Branch", branch)
info3.metric("Volume path", f"{VOLUME_BASE}/{selected_folder}")
info4.metric("Auth", "✅ Token found" if _get_token() else "❌ Missing GITHUB_TOKEN")

st.divider()

# === STATUS TABLE ===
st.subheader("Status overview")
with st.popover("How statuses are decided"):
    st.markdown(
        """
- **Only on volume**: Exists on the Railway volume but not in GitHub → good candidate to push.
- **Newer on volume**: Volume last-modified is newer → push to GitHub.
- **Only on GitHub**: Exists on GitHub but not on volume → pull to volume.
- **Newer on GitHub**: GitHub last-modified is newer → pull to volume.
- **Different size**: Sizes differ; push or pull based on what you trust.
- **Check required**: Couldn’t determine; inspect and choose.
- **Match**: Same size and near-identical modified time.
        """
    )

merged = merged_status(selected_folder)
if merged.empty:
    st.info(f"No files found in GitHub `{selected_folder}/` or on the Railway volume.")
else:
    df_show = merged.copy()
    # Pretty datetime for display (localise to browser later; keep UTC for consistency)
    for col in ["GitHub modified", "Volume modified"]:
        if col in df_show.columns:
            df_show[col] = df_show[col].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    st.dataframe(
        df_show.drop(columns=["GitHub path", "Volume path"], errors="ignore"),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# === GITHUB -> VOLUME (PULL) ===
st.subheader("⬇️ GitHub → Volume")
st.caption(f"Copy selected files from GitHub `{selected_folder}/` down to the Railway volume.")

if merged.empty:
    st.info("No files to pull.")
else:
    pull_default = merged["Status"].isin(
        ["Only on GitHub", "Newer on GitHub", "Different size", "Check required"]
    )

    pull_editor = st.data_editor(
        merged.assign(**{"Pull to Volume": pull_default}),
        hide_index=True,
        use_container_width=True,
        column_config={
            "GitHub size": st.column_config.NumberColumn(format="%d"),
            "Volume size": st.column_config.NumberColumn(format="%d"),
            "Pull to Volume": st.column_config.CheckboxColumn(),
        },
        disabled=[
            "File", "GitHub modified", "Volume modified",
            "GitHub size", "Volume size", "Status"
        ],
        key="pull_table",
    )

    to_pull = pull_editor[pull_editor["Pull to Volume"] == True]["File"].tolist()

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.write("Selected to pull:", ", ".join(to_pull) or "—")
    do_pull = col_b.button(
        f"Pull selected ({len(to_pull)})",
        type="primary",
        use_container_width=True,
        disabled=(len(to_pull) == 0),
    )

    if do_pull:
        if not _get_token():
            st.error("Missing GITHUB_TOKEN; cannot pull from GitHub.")
        else:
            ok, fails = 0, []
            with st.spinner("Pulling from GitHub…"):
                for fname in to_pull:
                    # Construct full path: selected_folder/filename
                    gh_path = f"{selected_folder}/{fname}"
                    try:
                        raw = gh_download_bytes(gh_path)
                        # Write to volume with full relative path
                        vol_write_bytes(gh_path, raw)
                        ok += 1
                    except Exception as e:
                        fails.append(f"{fname}: {e}")

            # Clear caches so the status view reflects the updated state
            list_github_files.clear()
            list_volume_files.clear()
            merged_status.clear()
            clear_all_caches()

            st.toast(f"Pulled {ok} file(s) to volume")
            if fails:
                with st.expander("Some files failed"):
                    for msg in fails:
                        st.error(msg)
            time.sleep(0.6)
            st.rerun()

st.divider()

# === VOLUME -> GITHUB (PUSH) ===
st.subheader("⬆️ Volume → GitHub")
st.caption(f"Copy selected files from the Railway volume up to GitHub `{selected_folder}/` folder.")

if merged.empty:
    st.info("No files to push.")
else:
    push_default = merged["Status"].isin(
        ["Only on volume", "Newer on volume", "Different size", "Check required"]
    )

    push_editor = st.data_editor(
        merged.assign(**{"Push to GitHub": push_default}),
        hide_index=True,
        use_container_width=True,
        column_config={
            "GitHub size": st.column_config.NumberColumn(format="%d"),
            "Volume size": st.column_config.NumberColumn(format="%d"),
            "Push to GitHub": st.column_config.CheckboxColumn(),
        },
        disabled=[
            "File", "GitHub modified", "Volume modified",
            "GitHub size", "Volume size", "Status"
        ],
        key="push_table",
    )

    to_push = push_editor[push_editor["Push to GitHub"] == True]["File"].tolist()

    col_m, col_btn = st.columns([3, 2])
    commit_message = col_m.text_input(
        "Commit message",
        value=f"Sync from Railway volume on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        help="Used for all selected files."
    )
    do_push = col_btn.button(
        f"Push selected ({len(to_push)})",
        type="primary",
        use_container_width=True,
        disabled=(len(to_push) == 0),
    )

    if do_push:
        if not _get_token():
            st.error("Missing GITHUB_TOKEN; cannot push to GitHub.")
        else:
            ok, fails = 0, []
            with st.spinner("Pushing to GitHub…"):
                for fname in to_push:
                    try:
                        # Construct full path: selected_folder/filename
                        full_path = f"{selected_folder}/{fname}"
                        raw = vol_read_bytes(full_path)
                        success, msg = gh_put_file(full_path, raw, commit_message)
                        if success:
                            ok += 1
                        else:
                            fails.append(f"{fname}: {msg}")
                    except Exception as e:
                        fails.append(f"{fname}: {e}")

            # Clear caches so the status view reflects the updated state
            list_github_files.clear()
            list_volume_files.clear()
            merged_status.clear()
            clear_all_caches()

            st.toast(f"Pushed {ok} file(s) to GitHub")
            if fails:
                with st.expander("Some files failed"):
                    for msg in fails:
                        st.error(msg)
            time.sleep(0.6)
            st.rerun()

# === FOOTER TIPS ===
with st.expander("Tips & notes"):
    st.markdown(
        """
- Set **`GITHUB_TOKEN`** in Railway variables or in `st.secrets` with `repo` scope.
- Repo/branch are taken from your `utils` (`GITHUB_REPO`, `get_current_branch()`), or from
  env vars `GITHUB_REPO` / `GIT_BRANCH`.
- Statuses are computed using **last-commit time (GitHub)** vs **file mtime (volume)** and **size**.
- If you often work Volume → GitHub, keep the push section selected by default (as configured).
- Use the **status table** to eyeball anything flagged as _Different size_ or _Check required_.
        """
    )
