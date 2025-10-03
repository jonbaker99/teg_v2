"""Streamlit page for managing data synchronization between GitHub and Railway.

This page provides an administrative interface to manage the data volume on
Railway, ensuring that it stays in sync with the authoritative `data/` folder
in the GitHub repository. It allows users to:
- View a comparison of files between GitHub and the Railway volume.
- Sync selected files from GitHub to the volume.
- Delete files from the volume.
- Preview the content of files from both sources.
"""
# streamlit/admin_volume_management.py
import os
from datetime import datetime
import time
from pathlib import Path
import pandas as pd
import streamlit as st

from utils import (
    read_from_github,
    write_to_github,  # not used here but you may later
    get_current_branch,
    GITHUB_REPO,
    clear_all_caches,
)

st.set_page_config(page_title="Volume Management", layout="wide")

# ---- Guards ---------------------------------------------------------------
st.title("🔄 Data sync: GitHub → Railway volume")
st.caption("Keep your volume in step with the authoritative `data/` folder in GitHub.")

if not os.getenv("RAILWAY_ENVIRONMENT"):
    st.error("This page only works on Railway (volume not available locally).")
    st.info("In local dev, files are read directly from your filesystem.")
    st.stop()

VOLUME_ROOT = "/mnt/data_repo"
VOLUME_DATA = f"{VOLUME_ROOT}/data"

# ---- Data fetch -----------------------------------------------------------
@st.cache_data(ttl=300)
def get_github_files_list():
    from github import Github
    token = os.getenv("GITHUB_TOKEN") or st.secrets.get("GITHUB_TOKEN")
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)
    contents = repo.get_contents("data", ref=get_current_branch())

    rows = []
    for item in contents:
        if item.type != "file":
            continue
        if not item.name.endswith((".csv", ".parquet", ".json", ".xlsx")):
            continue
        # last commit date
        try:
            commits = repo.get_commits(path=f"data/{item.name}", sha=get_current_branch())
            last_commit = commits[0] if commits.totalCount > 0 else None
            gh_modified = (
                last_commit.commit.committer.date.strftime("%Y-%m-%d %H:%M:%S")
                if last_commit
                else "Unknown"
            )
        except Exception:
            gh_modified = "Unknown"

        rows.append(
            dict(
                file=item.name,
                gh_path=f"data/{item.name}",
                gh_size=item.size,
                gh_modified=gh_modified,
                gh_sha=item.sha[:8],
            )
        )
    return pd.DataFrame(rows).sort_values("file")

def get_volume_files_list():
    rows = []
    if os.path.exists(VOLUME_DATA):
        for fname in os.listdir(VOLUME_DATA):
            fpath = os.path.join(VOLUME_DATA, fname)
            if not os.path.isfile(fpath):
                continue
            if not fname.endswith((".csv", ".parquet", ".json", ".xlsx")):
                continue
            stat = os.stat(fpath)
            rows.append(
                dict(
                    file=fname,
                    vol_path=f"data/{fname}",
                    vol_full=fpath,
                    vol_size=stat.st_size,
                    vol_modified=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                )
            )
    return pd.DataFrame(rows).sort_values("file") if rows else pd.DataFrame(rows)

def diff_files(gh_df: pd.DataFrame, vol_df: pd.DataFrame) -> pd.DataFrame:
    df = pd.merge(gh_df, vol_df, on="file", how="outer", validate="m:1")
    def status(row):
        if pd.isna(row.get("gh_path")):            return "Only on volume"
        if pd.isna(row.get("vol_path")):           return "Missing on volume"
        # Compare modified timestamps when both exist
        try:
            gh = pd.to_datetime(row["gh_modified"])
            vol = pd.to_datetime(row["vol_modified"])
            if gh > vol:                            return "Newer on GitHub"
            if vol > gh:                            return "Newer on volume"
            if int(row.get("gh_size", -1)) != int(row.get("vol_size", -2)):
                return "Different size"
            return "Match"
        except Exception:
            return "Check required"
    df["Status"] = df.apply(status, axis=1)
    # Nice display columns
    display = df[
        [
            "file",
            "gh_modified",
            "vol_modified",
            "gh_size",
            "vol_size",
            "Status",
        ]
    ].rename(
        columns={
            "file": "File",
            "gh_modified": "GitHub modified",
            "vol_modified": "Volume modified",
            "gh_size": "GitHub size",
            "vol_size": "Volume size",
        }
    )
    return display

# ---- Actions --------------------------------------------------------------
def pull_file_from_github(file_path: str):
    try:
        data = read_from_github(file_path)
        volume_path = f"{VOLUME_ROOT}/{file_path}"
        os.makedirs(os.path.dirname(volume_path), exist_ok=True)
        if file_path.endswith(".csv"):
            data.to_csv(volume_path, index=False)
        elif file_path.endswith(".parquet"):
            data.to_parquet(volume_path, index=False)
        elif file_path.endswith(".json"):
            data.to_json(volume_path, orient="records")
        else:
            # best-effort raw write fallback
            try:
                data.to_csv(volume_path, index=False)
            except Exception:
                return False, f"Unsupported format for {file_path}"
        return True, f"Synced {file_path} → volume"
    except Exception as e:
        return False, str(e)

def delete_volume_file(file_path: str):
    try:
        vpath = f"{VOLUME_ROOT}/{file_path}"
        if os.path.exists(vpath):
            os.remove(vpath)
            return True, f"Deleted {file_path} from volume"
        return False, f"File not found: {file_path}"
    except Exception as e:
        return False, str(e)

def read_file_preview(file_path: str, source: str):
    try:
        if source == "GitHub":
            data = read_from_github(file_path)
            return data if isinstance(data, pd.DataFrame) else None
        else:
            vpath = f"{VOLUME_ROOT}/{file_path}"
            if file_path.endswith(".csv"):
                return pd.read_csv(vpath)
            if file_path.endswith(".parquet"):
                return pd.read_parquet(vpath)
            if file_path.endswith(".json"):
                return pd.read_json(vpath)
            return None
    except Exception:
        return None

# ---- Header / summary -----------------------------------------------------
gh = get_github_files_list()
vol = get_volume_files_list()
merged = diff_files(gh, vol)

left, right = st.columns([3, 2])
with left:
    st.subheader("Files")
    st.caption(
        f"GitHub branch: **{get_current_branch()}** · Repo: **{GITHUB_REPO}** · "
        f"GitHub files: **{len(gh)}** · Volume files: **{len(vol)}**"
    )
with right:
    c1, c2 = st.columns(2)
    if c1.button("🔁 Refresh", use_container_width=True):
        get_github_files_list.clear()
        st.rerun()
    # Danger button uses confirm flag
    if c2.button("🗑️ Clear entire volume", use_container_width=True):
        st.session_state["confirm_clear_all"] = True

if st.session_state.get("confirm_clear_all"):
    st.warning("This will remove **all** files from the volume. Click again to confirm.")
    cc1, cc2 = st.columns([1, 1])
    if cc1.button("Confirm delete", type="primary"):
        import shutil
        if os.path.exists(VOLUME_DATA):
            shutil.rmtree(VOLUME_DATA)
        clear_all_caches()
        st.session_state["confirm_clear_all"] = False
        st.toast("Volume cleared")
        time.sleep(0.6)
        st.rerun()
    if cc2.button("Cancel"):
        st.session_state["confirm_clear_all"] = False

# ---- Tabs -----------------------------------------------------------------
tab_files, tab_preview, tab_help = st.tabs(["Files", "Preview", "Help"])

with tab_files:
    # Select rows to sync (to volume)
    st.markdown("#### Sync planner")
    # Status chips explanation
    with st.popover("What the statuses mean"):
        st.markdown(
            "- **Missing on volume**: not present in volume → will sync\n"
            "- **Newer on GitHub**: GitHub newer → should sync\n"
            "- **Newer on volume**: volume newer → check if expected\n"
            "- **Match**: no action needed\n"
            "- **Only on volume**: not in GitHub → usually delete or ignore"
        )

    # Pre-select sensible rows to sync (missing or newer on GitHub or different size)
    default_select = merged["Status"].isin(
        ["Missing on volume", "Newer on GitHub", "Different size", "Check required"]
    )
    selected_rows = st.data_editor(
        merged.assign(**{"Sync to volume": default_select}),
        hide_index=True,
        use_container_width=True,
        column_config={
            "GitHub size": st.column_config.NumberColumn(format="%d"),
            "Volume size": st.column_config.NumberColumn(format="%d"),
            "Sync to volume": st.column_config.CheckboxColumn(),
        },
        disabled=["File", "GitHub modified", "Volume modified", "GitHub size", "Volume size", "Status"],
        key="sync_table",
    )

    # Primary call-to-action
    to_sync = selected_rows[selected_rows["Sync to volume"] == True]["File"].tolist()
    cta_col1, cta_col2 = st.columns([1, 5])
    if cta_col1.button(f"⬇️ Sync selected ({len(to_sync)})", type="primary", use_container_width=True, disabled=(len(to_sync) == 0)):
        errors = []
        ok = 0
        with st.spinner("Syncing files…"):
            for fname in to_sync:
                gh_row = gh[gh["file"] == fname].iloc[0]
                success, msg = pull_file_from_github(gh_row["gh_path"])
                if success:
                    ok += 1
                else:
                    errors.append(f"{fname}: {msg}")
            clear_all_caches()
        st.toast(f"Synced {ok} file(s)")
        if errors:
            with st.expander("Some files failed"):
                for e in errors:
                    st.error(e)
        time.sleep(0.6)
        st.rerun()

    # Row-level actions
    st.markdown("#### Volume housekeeping")
    hc1, hc2 = st.columns([2, 3])
    victim = hc1.selectbox(
        "Delete a volume file",
        options=sorted(vol["file"].tolist()) if not vol.empty else [],
        index=0 if (not vol.empty) else None,
        placeholder="Choose file",
    )
    if hc2.button("🗑️ Delete selected volume file", disabled=(not victim)):
        key = "confirm_delete_one"
        if not st.session_state.get(key):
            st.session_state[key] = True
            st.warning("Click again to confirm deletion.")
        else:
            ok, msg = delete_volume_file(f"data/{victim}")
            st.session_state[key] = False
            if ok:
                st.toast("File deleted")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(msg)

with tab_preview:
    st.markdown("#### Quick preview (first 10 rows)")
    c1, c2, c3 = st.columns([3, 2, 2])
    fname = c1.selectbox(
        "File",
        options=sorted(set(merged["File"].dropna().tolist())),
        placeholder="Choose a file",
    )
    source = c2.radio("Source", ["GitHub", "Volume"], horizontal=True)
    if c3.button("Preview", use_container_width=True, disabled=(not fname)):
        path = f"data/{fname}"
        df = read_file_preview(path, source)
        if df is None:
            st.error("Could not read the file.")
        else:
            st.caption(f"{fname} · {len(df):,} rows × {df.shape[1]} cols")
            st.dataframe(df.head(10), use_container_width=True)

with tab_help:
    st.markdown(
        """
**How this works**
-updated jb


- GitHub (`data/`) is the **authoritative** source.  
- **Sync to volume** copies selected GitHub files to the Railway volume.  
- Use **Delete** only for files that shouldn’t exist on the volume.  
- Caches clear automatically after a sync.
"""
    )
    st.code(
        f"""Environment
- Railway: {os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}
- Repo: {GITHUB_REPO}
- Branch: {get_current_branch()}
- Volume: {VOLUME_ROOT}"""
    )
