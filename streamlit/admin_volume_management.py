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
    """Read file content from volume or GitHub with better error handling"""
    try:
        if source == "volume":
            volume_path = f"/mnt/data_repo/{file_path}"
            
            # Check if file exists and has content
            if not os.path.exists(volume_path):
                st.error(f"File not found: {volume_path}")
                return None
            
            # Check file size
            file_size = os.path.getsize(volume_path)
            if file_size == 0:
                st.error(f"File is empty: {file_path}")
                return None
            
            if file_path.endswith('.csv'):
                # Try reading with different encodings and error handling
                try:
                    return pd.read_csv(volume_path, encoding='utf-8')
                except UnicodeDecodeError:
                    return pd.read_csv(volume_path, encoding='latin-1')
                except pd.errors.EmptyDataError:
                    st.error(f"CSV file appears to be empty or corrupted: {file_path}")
                    return None
                except Exception as e:
                    st.error(f"Error reading CSV: {str(e)}")
                    # Try to show first few lines of the file for debugging
                    try:
                        with open(volume_path, 'r', encoding='utf-8') as f:
                            first_lines = f.read(500)
                        st.text(f"First 500 characters of file:\n{first_lines}")
                    except:
                        pass
                    return None
                    
            elif file_path.endswith('.parquet'):
                return pd.read_parquet(volume_path)
            else:
                st.error(f"Unsupported file type: {file_path}")
                return None
                
        else:  # GitHub
            # Enhanced GitHub reading with better CSV handling
            try:
                data = read_from_github(file_path)
                
                # If we got a DataFrame, return it
                if isinstance(data, pd.DataFrame):
                    return data
                
                # If we got string data (shouldn't happen with current read_from_github), try to parse
                if isinstance(data, str):
                    from io import StringIO
                    return pd.read_csv(StringIO(data))
                    
                return data
                
            except pd.errors.EmptyDataError:
                st.error(f"GitHub file appears to be empty: {file_path}")
                return None
            except Exception as e:
                st.error(f"Error reading from GitHub: {str(e)}")
                
                # Try to get raw content for debugging
                try:
                    from github import Github
                    token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
                    g = Github(token)
                    repo = g.get_repo(GITHUB_REPO)
                    file_content = repo.get_contents(file_path, ref=get_current_branch())
                    
                    import base64
                    raw_content = base64.b64decode(file_content.content).decode('utf-8')
                    
                    st.text("Raw file content (first 500 chars):")
                    st.text(raw_content[:500])
                    
                except Exception as debug_e:
                    st.error(f"Could not fetch raw content for debugging: {debug_e}")
                
                return None
            
    except Exception as e:
        st.error(f"Error reading {file_path} from {source}: {str(e)}")
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
        st.markdown(f"**{len(github_files)} files found**")
        
        # Create DataFrame for GitHub files
        github_df = pd.DataFrame([
            {
                "File": f["name"],
                "Size": f"{f['size']:,} bytes",
                "Modified": f["modified"],
                "Pull": False  # Checkbox column
            }
            for f in github_files
        ])
        
        # Display editable table with checkboxes
        edited_github = st.data_editor(
            github_df,
            column_config={
                "File": st.column_config.TextColumn("File", width="medium"),
                "Size": st.column_config.TextColumn("Size", width="small"),
                "Modified": st.column_config.TextColumn("Modified", width="medium"),
                "Pull": st.column_config.CheckboxColumn("Pull", width="small")
            },
            hide_index=True,
            use_container_width=True,
            key="github_files_table"
        )
        
        # Pull selected files button
        selected_for_pull = edited_github[edited_github['Pull'] == True]
        if len(selected_for_pull) > 0:
            if st.button(f"📥 Pull {len(selected_for_pull)} Selected Files", type="primary"):
                success_count = 0
                error_messages = []
                
                with st.spinner(f"Pulling {len(selected_for_pull)} files..."):
                    for _, row in selected_for_pull.iterrows():
                        # Find the file path
                        file_info = next((f for f in github_files if f["name"] == row["File"]), None)
                        if file_info:
                            success, message = pull_file_from_github(file_info["path"])
                            if success:
                                success_count += 1
                            else:
                                error_messages.append(message)
                    
                    clear_all_caches()
                
                if success_count > 0:
                    st.success(f"✅ Successfully pulled {success_count} files")
                
                if error_messages:
                    st.error(f"❌ {len(error_messages)} errors occurred")
                    with st.expander("View errors"):
                        for error in error_messages:
                            st.error(error)
                
                time.sleep(1)
                st.rerun()
        
        # Individual file management dropdown
        st.markdown("**Individual File Actions:**")
        selected_github_file = st.selectbox(
            "Choose file to view:",
            options=[f["name"] for f in github_files],
            key="github_file_selector"
        )
        
        if selected_github_file:
            col_view, col_pull = st.columns(2)
            
            with col_view:
                if st.button("👁️ View File", key="view_github_individual"):
                    file_info = next((f for f in github_files if f["name"] == selected_github_file), None)
                    if file_info:
                        data = read_file_content(file_info["path"], source="github")
                        if data is not None:
                            st.markdown(f"**{selected_github_file}** ({data.shape[0]} rows × {data.shape[1]} cols)")
                            st.dataframe(data.head(10), use_container_width=True)
                            if len(data) > 10:
                                st.caption(f"Showing first 10 rows of {len(data)} total")
            
            with col_pull:
                if st.button("📥 Pull File", key="pull_github_individual"):
                    file_info = next((f for f in github_files if f["name"] == selected_github_file), None)
                    if file_info:
                        with st.spinner(f"Pulling {selected_github_file}..."):
                            success, message = pull_file_from_github(file_info["path"])
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                        
                        time.sleep(1)
                        st.rerun()
    else:
        st.info("No data files found in GitHub")

# === VOLUME FILES SECTION ===
with col_volume:
    st.markdown("### 📁 Railway Volume Files")
    
    volume_files = get_volume_files_list()
    
    if volume_files:
        st.markdown(f"**{len(volume_files)} files found**")
        
        # Create DataFrame for volume files
        volume_df = pd.DataFrame([
            {
                "File": f["name"],
                "Size": f"{f['size']:,} bytes",
                "Modified": f["modified"]
            }
            for f in volume_files
        ])
        
        # Display simple table
        st.dataframe(
            volume_df,
            column_config={
                "File": st.column_config.TextColumn("File", width="medium"),
                "Size": st.column_config.TextColumn("Size", width="small"),
                "Modified": st.column_config.TextColumn("Modified", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Individual file management dropdown
        st.markdown("**File Actions:**")
        selected_volume_file = st.selectbox(
            "Choose file to manage:",
            options=[f["name"] for f in volume_files],
            key="volume_file_selector"
        )
        
        if selected_volume_file:
            col_view, col_download, col_delete = st.columns(3)
            
            with col_view:
                if st.button("👁️ View", key="view_volume_individual"):
                    file_info = next((f for f in volume_files if f["name"] == selected_volume_file), None)
                    if file_info:
                        data = read_file_content(file_info["path"], source="volume")
                        if data is not None:
                            st.markdown(f"**{selected_volume_file}** ({data.shape[0]} rows × {data.shape[1]} cols)")
                            st.dataframe(data.head(10), use_container_width=True)
                            if len(data) > 10:
                                st.caption(f"Showing first 10 rows of {len(data)} total")
            
            with col_download:
                if st.button("💾 Download", key="download_volume_individual"):
                    file_info = next((f for f in volume_files if f["name"] == selected_volume_file), None)
                    if file_info:
                        try:
                            with open(file_info['full_path'], 'rb') as f:
                                file_bytes = f.read()
                            
                            st.download_button(
                                label=f"📥 {selected_volume_file}",
                                data=file_bytes,
                                file_name=selected_volume_file,
                                mime='application/octet-stream',
                                key="download_button_individual"
                            )
                        except Exception as e:
                            st.error(f"Error preparing download: {e}")
            
            with col_delete:
                if st.button("🗑️ Delete", key="delete_volume_individual"):
                    if st.session_state.get('confirm_delete_individual', False):
                        file_info = next((f for f in volume_files if f["name"] == selected_volume_file), None)
                        if file_info:
                            success, message = delete_volume_file(file_info["path"])
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        
                        st.session_state['confirm_delete_individual'] = False
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state['confirm_delete_individual'] = True
                        st.warning("⚠️ Click again to confirm")
    else:
        st.info("No files found in volume")

# === BULK ACTIONS FOR GITHUB FILES ===
# Removed - replaced with checkbox functionality in the table above

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
    s
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