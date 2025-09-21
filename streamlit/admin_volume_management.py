# streamlit/admin_volume_management.py
# Volume Management Page for Railway GitHub Sync

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
import time

# Import from utils
from utils import (
    read_from_github, 
    write_to_github,
    get_current_branch,
    GITHUB_REPO,
    clear_all_caches
)

# === PAGE CONFIGURATION ===
st.set_page_config(page_title="Volume Management", layout="wide")
st.title("🔄 Volume Management")
st.markdown("Manage Railway volume sync with GitHub data storage")

# === ENVIRONMENT CHECK ===
if not os.getenv('RAILWAY_ENVIRONMENT'):
    st.error("❌ This page only works on Railway (volume not available locally)")
    st.info("💡 On local development, files are read directly from your local filesystem")
    st.stop()

# === HELPER FUNCTIONS ===

@st.cache_data(ttl=300)  # Cache for 5 minutes to avoid excessive API calls
def get_github_files_list():
    """Dynamically discover data files from GitHub data/ folder (files only, no subfolders)"""
    try:
        from github import Github
        
        token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
        g = Github(token)
        repo = g.get_repo(GITHUB_REPO)
        
        # Get all contents of the data/ directory
        contents = repo.get_contents("data", ref=get_current_branch())
        
        # Filter for files only (exclude directories) and common data formats
        github_files = []
        for item in contents:
            # Only include files (not directories) directly in data/ folder
            if item.type == "file":
                # Include common data file extensions
                if item.name.endswith(('.csv', '.parquet', '.json', '.xlsx')):
                    # Get commit info for last modified date
                    try:
                        commits = repo.get_commits(path=f"data/{item.name}", sha=get_current_branch())
                        last_commit = commits[0] if commits.totalCount > 0 else None
                        modified_date = last_commit.commit.committer.date.strftime('%Y-%m-%d %H:%M:%S') if last_commit else "Unknown"
                    except:
                        modified_date = "Unknown"
                    
                    github_files.append({
                        "name": item.name,
                        "path": f"data/{item.name}",
                        "size": item.size,
                        "modified": modified_date,
                        "sha": item.sha[:8]
                    })
        
        # Sort by name for consistent display
        return sorted(github_files, key=lambda x: x["name"])
        
    except Exception as e:
        st.error(f"Could not fetch GitHub file list: {e}")
        return []

def get_volume_files_list():
    """Get list of all files in Railway volume data/ folder"""
    volume_data_path = "/mnt/data_repo/data"
    volume_files = []
    
    try:
        if os.path.exists(volume_data_path):
            for item in os.listdir(volume_data_path):
                item_path = os.path.join(volume_data_path, item)
                
                # Only include files (not directories)
                if os.path.isfile(item_path):
                    # Include common data file extensions
                    if item.endswith(('.csv', '.parquet', '.json', '.xlsx')):
                        stat = os.stat(item_path)
                        volume_files.append({
                            "name": item,
                            "path": f"data/{item}",
                            "full_path": item_path,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
        
        # Sort by name for consistent display
        return sorted(volume_files, key=lambda x: x["name"])
        
    except Exception as e:
        st.error(f"Could not read volume files: {e}")
        return []

def pull_file_from_github(file_path):
    """Pull a single file from GitHub to volume"""
    try:
        # Read from GitHub
        data = read_from_github(file_path)
        
        # Write to volume
        volume_path = f"/mnt/data_repo/{file_path}"
        os.makedirs(os.path.dirname(volume_path), exist_ok=True)
        
        if file_path.endswith('.csv'):
            data.to_csv(volume_path, index=False)
        elif file_path.endswith('.parquet'):
            data.to_parquet(volume_path, index=False)
        
        return True, f"✅ Successfully pulled {file_path}"
        
    except Exception as e:
        return False, f"❌ Error pulling {file_path}: {str(e)}"

def delete_volume_file(file_path):
    """Delete a file from the volume"""
    try:
        volume_path = f"/mnt/data_repo/{file_path}"
        if os.path.exists(volume_path):
            os.remove(volume_path)
            return True, f"✅ Deleted {file_path} from volume"
        else:
            return False, f"❌ File {file_path} not found in volume"
    except Exception as e:
        return False, f"❌ Error deleting {file_path}: {str(e)}"

def read_file_content(file_path, source="volume"):
    """Read file content from volume or GitHub"""
    try:
        if source == "volume":
            volume_path = f"/mnt/data_repo/{file_path}"
            if file_path.endswith('.csv'):
                return pd.read_csv(volume_path)
            elif file_path.endswith('.parquet'):
                return pd.read_parquet(volume_path)
        else:  # GitHub
            return read_from_github(file_path)
    except Exception as e:
        st.error(f"Error reading {file_path}: {e}")
        return None

# === QUICK ACTIONS ===
st.markdown("### 🚀 Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📥 Pull All from GitHub", type="primary", use_container_width=True):
        github_files = get_github_files_list()
        
        if github_files:
            success_count = 0
            error_messages = []
            
            with st.spinner(f"Pulling {len(github_files)} files from GitHub..."):
                for file_info in github_files:
                    success, message = pull_file_from_github(file_info["path"])
                    if success:
                        success_count += 1
                    else:
                        error_messages.append(message)
                
                clear_all_caches()  # Clear caches after sync
            
            if success_count > 0:
                st.success(f"✅ Successfully pulled {success_count} files and cleared caches")
            
            if error_messages:
                st.error(f"❌ {len(error_messages)} errors occurred")
                with st.expander("View errors"):
                    for error in error_messages:
                        st.error(error)
        else:
            st.warning("No files found in GitHub to pull")
        
        time.sleep(1)
        st.rerun()

with col2:
    if st.button("🗑️ Clear All Volume Files", use_container_width=True):
        if st.session_state.get('confirm_clear_all', False):
            try:
                import shutil
                volume_data_path = "/mnt/data_repo/data"
                if os.path.exists(volume_data_path):
                    shutil.rmtree(volume_data_path)
                    clear_all_caches()
                    st.success("✅ All volume files cleared")
                else:
                    st.info("ℹ️ Volume already empty")
                st.session_state['confirm_clear_all'] = False
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error clearing volume: {e}")
        else:
            st.session_state['confirm_clear_all'] = True
            st.warning("⚠️ Click again to confirm clearing ALL volume files")

with col3:
    if st.button("🔄 Refresh Lists", use_container_width=True):
        get_github_files_list.clear()
        st.rerun()

# === TWO-COLUMN LAYOUT ===
col_github, col_volume = st.columns(2)

# === GITHUB FILES SECTION ===
with col_github:
    st.markdown("### ☁️ GitHub Data Files")
    
    github_files = get_github_files_list()
    
    if github_files:
        st.markdown(f"**{len(github_files)} files found in GitHub data/ folder**")
        
        # Display GitHub files list
        for i, file_info in enumerate(github_files):
            with st.container():
                st.markdown(f"**📄 {file_info['name']}**")
                
                col_info, col_actions = st.columns([2, 1])
                
                with col_info:
                    st.caption(f"Size: {file_info['size']:,} bytes | Modified: {file_info['modified']}")
                    st.caption(f"SHA: {file_info['sha']}")
                
                with col_actions:
                    # Pull individual file
                    if st.button("⬇️ Pull", key=f"pull_gh_{i}", help=f"Pull {file_info['name']} to volume"):
                        with st.spinner(f"Pulling {file_info['name']}..."):
                            success, message = pull_file_from_github(file_info["path"])
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                        
                        time.sleep(1)
                        st.rerun()
                    
                    # View file from GitHub
                    if st.button("👁️ View", key=f"view_gh_{i}", help=f"Preview {file_info['name']} from GitHub"):
                        data = read_file_content(file_info["path"], source="github")
                        if data is not None:
                            st.markdown(f"**GitHub: {file_info['name']}** ({data.shape[0]} rows × {data.shape[1]} cols)")
                            st.dataframe(data.head(10), use_container_width=True)
                            if len(data) > 10:
                                st.caption(f"Showing first 10 rows of {len(data)} total")
                
                st.markdown("---")
    else:
        st.info("No data files found in GitHub")

# === VOLUME FILES SECTION ===
with col_volume:
    st.markdown("### 📁 Railway Volume Files")
    
    volume_files = get_volume_files_list()
    
    if volume_files:
        st.markdown(f"**{len(volume_files)} files found in volume**")
        
        # Display volume files list
        for i, file_info in enumerate(volume_files):
            with st.container():
                st.markdown(f"**📄 {file_info['name']}**")
                
                col_info, col_actions = st.columns([2, 1])
                
                with col_info:
                    st.caption(f"Size: {file_info['size']:,} bytes | Modified: {file_info['modified']}")
                    st.caption(f"Path: {file_info['full_path']}")
                
                with col_actions:
                    # View file from volume
                    if st.button("👁️ View", key=f"view_vol_{i}", help=f"Preview {file_info['name']} from volume"):
                        data = read_file_content(file_info["path"], source="volume")
                        if data is not None:
                            st.markdown(f"**Volume: {file_info['name']}** ({data.shape[0]} rows × {data.shape[1]} cols)")
                            st.dataframe(data.head(10), use_container_width=True)
                            if len(data) > 10:
                                st.caption(f"Showing first 10 rows of {len(data)} total")
                    
                    # Download file
                    if st.button("💾 Download", key=f"download_vol_{i}", help=f"Download {file_info['name']} from volume"):
                        try:
                            with open(file_info['full_path'], 'rb') as f:
                                file_bytes = f.read()
                            
                            st.download_button(
                                label=f"📥 {file_info['name']}",
                                data=file_bytes,
                                file_name=file_info['name'],
                                mime='application/octet-stream',
                                key=f"dl_btn_{i}"
                            )
                        except Exception as e:
                            st.error(f"Error preparing download: {e}")
                    
                    # Delete file
                    if st.button("🗑️ Delete", key=f"delete_vol_{i}", help=f"Delete {file_info['name']} from volume"):
                        if st.session_state.get(f'confirm_delete_{i}', False):
                            success, message = delete_volume_file(file_info["path"])
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                            
                            st.session_state[f'confirm_delete_{i}'] = False
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.session_state[f'confirm_delete_{i}'] = True
                            st.warning("⚠️ Click again to confirm")
                
                st.markdown("---")
    else:
        st.info("No files found in volume")

# === BULK ACTIONS FOR GITHUB FILES ===
if github_files:
    st.markdown("### 📦 Bulk GitHub Actions")
    
    # Multi-select for GitHub files
    selected_files = st.multiselect(
        "Select GitHub files to pull:",
        options=[f["name"] for f in github_files],
        format_func=lambda x: f"📄 {x}",
        help="Select multiple files to pull at once"
    )
    
    if selected_files:
        if st.button(f"📥 Pull Selected ({len(selected_files)} files)", type="secondary"):
            success_count = 0
            error_messages = []
            
            with st.spinner(f"Pulling {len(selected_files)} selected files..."):
                for file_name in selected_files:
                    # Find the full path for this file
                    file_info = next((f for f in github_files if f["name"] == file_name), None)
                    if file_info:
                        success, message = pull_file_from_github(file_info["path"])
                        if success:
                            success_count += 1
                        else:
                            error_messages.append(message)
                
                clear_all_caches()  # Clear caches after sync
            
            if success_count > 0:
                st.success(f"✅ Successfully pulled {success_count} selected files")
            
            if error_messages:
                st.error(f"❌ {len(error_messages)} errors occurred")
                with st.expander("View errors"):
                    for error in error_messages:
                        st.error(error)
            
            time.sleep(1)
            st.rerun()

# === HELP SECTION ===
with st.expander("ℹ️ How to Use Volume Management"):
    st.markdown("""
    **GitHub Files (Left Column):**
    - **⬇️ Pull**: Download individual file from GitHub to volume
    - **👁️ View**: Preview file contents directly from GitHub
    
    **Volume Files (Right Column):**
    - **👁️ View**: Preview file contents from volume  
    - **💾 Download**: Download file to your computer
    - **🗑️ Delete**: Remove file from volume (requires confirmation)
    
    **Quick Actions:**
    - **📥 Pull All from GitHub**: Download all GitHub data files to volume
    - **🗑️ Clear All Volume Files**: Remove all files from volume (requires confirmation)
    - **🔄 Refresh Lists**: Update both file lists
    
    **Bulk Actions:**
    - **Select multiple GitHub files**: Use checkboxes to pull multiple files at once
    
    **File Management:**
    - Volume files are cached for fast app performance
    - GitHub files are the authoritative source
    - After pulling files, app caches are automatically cleared
    """)

# === TECHNICAL INFO ===
with st.expander("🔧 Technical Information"):
    st.markdown(f"""
    **Environment:**
    - Railway Environment: `{os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}`
    - GitHub Repository: `{GITHUB_REPO}`
    - Current Branch: `{get_current_branch()}`
    - Volume Mount: `/mnt/data_repo/`
    
    **Volume Status:**
    - Volume exists: `{os.path.exists('/mnt/data_repo')}`
    - Data folder exists: `{os.path.exists('/mnt/data_repo/data')}`
    - Volume writable: `{os.access('/mnt/data_repo', os.W_OK) if os.path.exists('/mnt/data_repo') else 'N/A'}`
    
    **File Discovery:**
    - GitHub files: Discovered via API from data/ folder
    - Volume files: Scanned from /mnt/data_repo/data/
    - Supported formats: .csv, .parquet, .json, .xlsx
    - Subfolders: Excluded from sync
    """)