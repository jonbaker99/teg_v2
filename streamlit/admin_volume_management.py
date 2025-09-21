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

@st.cache_data(ttl=60)  # Cache for 1 minute to avoid excessive API calls
def get_data_files_list():
    """Get list of all data files to manage"""
    return [
        "data/all-scores.parquet",
        "data/all-data.parquet", 
        "data/all-data.csv",
        "data/handicaps.csv",
        "data/round_info.csv",
        "data/players.csv",
        "data/sc-data-by-r.csv",
        "data/teg-all-data-long.csv",
        "data/future_tegs.csv",
        "data/teg_winners.csv",
        "data/completed_tegs.csv",
        "data/in_progress_tegs.csv"
    ]

def get_github_file_info(file_path):
    """Get GitHub file information"""
    try:
        from github import Github
        
        token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
        g = Github(token)
        repo = g.get_repo(GITHUB_REPO)
        
        try:
            github_file = repo.get_contents(file_path, ref=get_current_branch())
            return {
                "exists": True,
                "size": github_file.size,
                "modified": github_file.last_modified.strftime('%Y-%m-%d %H:%M:%S'),
                "modified_timestamp": github_file.last_modified.timestamp(),
                "sha": github_file.sha[:8]
            }
        except:
            return {
                "exists": False,
                "size": 0,
                "modified": "N/A",
                "modified_timestamp": 0,
                "sha": "N/A"
            }
            
    except Exception as e:
        st.error(f"GitHub API error: {e}")
        return None

def get_volume_file_info(file_path):
    """Get volume file information"""
    volume_path = f"/mnt/data_repo/{file_path}"
    
    try:
        if os.path.exists(volume_path):
            stat = os.stat(volume_path)
            return {
                "exists": True,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                "modified_timestamp": stat.st_mtime,
                "path": volume_path
            }
        else:
            return {
                "exists": False,
                "size": 0,
                "modified": "N/A",
                "modified_timestamp": 0,
                "path": volume_path
            }
    except Exception as e:
        return {
            "exists": False,
            "size": 0,
            "modified": f"Error: {e}",
            "modified_timestamp": 0,
            "path": volume_path
        }

def sync_single_file_from_github(file_path):
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
        
        return True, f"✅ Successfully synced {file_path}"
        
    except Exception as e:
        return False, f"❌ Error syncing {file_path}: {str(e)}"

def sync_all_files_from_github():
    """Pull all data files from GitHub to volume"""
    results = {"success": [], "errors": []}
    
    for file_path in get_data_files_list():
        success, message = sync_single_file_from_github(file_path)
        if success:
            results["success"].append(file_path)
        else:
            results["errors"].append(message)
    
    return results

def clear_volume_cache():
    """Clear all files from Railway volume"""
    try:
        import shutil
        volume_base = "/mnt/data_repo"
        
        if os.path.exists(volume_base):
            shutil.rmtree(volume_base)
            return True, f"✅ Volume cleared: {volume_base}"
        else:
            return True, f"ℹ️ Volume already empty: {volume_base}"
            
    except Exception as e:
        return False, f"❌ Error clearing volume: {e}"

# === QUICK ACTIONS SECTION ===
st.markdown("### 🚀 Quick Actions")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📥 Pull All from GitHub", type="primary", use_container_width=True):
        with st.spinner("Syncing all files from GitHub..."):
            results = sync_all_files_from_github()
            clear_all_caches()  # Clear Streamlit caches
            
        if results["success"]:
            st.success(f"✅ Successfully synced {len(results['success'])} files")
            with st.expander("View synced files"):
                for file in results["success"]:
                    st.success(f"  • {file}")
        
        if results["errors"]:
            st.error(f"❌ {len(results['errors'])} errors occurred")
            with st.expander("View errors"):
                for error in results["errors"]:
                    st.error(f"  • {error}")
        
        # Auto-refresh the status table
        time.sleep(1)
        st.rerun()

with col2:
    if st.button("🗑️ Clear Volume", use_container_width=True):
        success, message = clear_volume_cache()
        if success:
            clear_all_caches()
            st.info(message)
        else:
            st.error(message)
        time.sleep(1)
        st.rerun()

with col3:
    if st.button("🔄 Refresh Status", use_container_width=True):
        # Clear the cache and refresh
        get_data_files_list.clear()
        st.rerun()

with col4:
    if st.button("🧹 Clear App Cache", use_container_width=True):
        clear_all_caches()
        st.success("App caches cleared!")

# === FILE STATUS TABLE ===
st.markdown("### 📊 File Status Comparison")

try:
    # Build status data
    status_data = []
    
    for file_path in get_data_files_list():
        github_info = get_github_file_info(file_path)
        volume_info = get_volume_file_info(file_path)
        
        if github_info is None:
            continue
            
        # Determine sync status
        if not github_info["exists"] and not volume_info["exists"]:
            status = "❌ Missing"
            status_priority = 4
        elif not volume_info["exists"]:
            status = "⬇️ Pull needed"
            status_priority = 3
        elif not github_info["exists"]:
            status = "⚠️ Volume only"
            status_priority = 2
        elif github_info["modified_timestamp"] > volume_info["modified_timestamp"]:
            status = "⬇️ GitHub newer"
            status_priority = 3
        elif volume_info["modified_timestamp"] > github_info["modified_timestamp"]:
            status = "⬆️ Volume newer"
            status_priority = 1
        else:
            status = "✅ In sync"
            status_priority = 0
            
        status_data.append({
            "File": file_path.replace("data/", ""),
            "Status": status,
            "GitHub Modified": github_info["modified"],
            "Volume Modified": volume_info["modified"],
            "GitHub Size": f"{github_info['size']:,} bytes" if github_info["exists"] else "N/A",
            "Volume Size": f"{volume_info['size']:,} bytes" if volume_info["exists"] else "N/A",
            "GitHub SHA": github_info["sha"],
            "Full Path": file_path,
            "Status Priority": status_priority
        })
    
    if status_data:
        df = pd.DataFrame(status_data)
        
        # Sort by status priority (most important first)
        df = df.sort_values("Status Priority", ascending=False)
        
        # Display main columns
        display_df = df[["File", "Status", "GitHub Modified", "Volume Modified"]].copy()
        
        # Style the dataframe
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "File": st.column_config.TextColumn("File", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "GitHub Modified": st.column_config.TextColumn("GitHub Modified", width="medium"),
                "Volume Modified": st.column_config.TextColumn("Volume Modified", width="medium")
            },
            hide_index=True
        )
        
        # Summary metrics
        st.markdown("### 📈 Summary")
        status_counts = df['Status'].value_counts()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            sync_count = status_counts.get('✅ In sync', 0)
            st.metric("In Sync", sync_count)
            
        with col2:
            pull_count = (status_counts.get('⬇️ GitHub newer', 0) + 
                         status_counts.get('⬇️ Pull needed', 0))
            st.metric("Need Pull", pull_count)
            
        with col3:
            volume_count = status_counts.get('⬆️ Volume newer', 0)
            st.metric("Volume Newer", volume_count)
            
        with col4:
            missing_count = status_counts.get('❌ Missing', 0)
            st.metric("Missing", missing_count)
            
        with col5:
            total_files = len(df)
            st.metric("Total Files", total_files)
    
    else:
        st.warning("No file status data available")
        
except Exception as e:
    st.error(f"Error generating file status: {e}")
    st.exception(e)

# === INDIVIDUAL FILE ACTIONS ===
st.markdown("### 🎯 Individual File Actions")

# File selector for individual actions
if 'status_data' in locals() and status_data:
    # Create options with status indicators
    file_options = []
    for item in status_data:
        status_emoji = item["Status"].split()[0]
        file_options.append(f"{status_emoji} {item['File']}")
    
    selected_display = st.selectbox(
        "Select file for individual actions:",
        file_options,
        help="Files are sorted by priority (issues first)"
    )
    
    # Extract the actual file path
    selected_file_name = selected_display.split(" ", 1)[1]  # Remove emoji
    selected_file_path = f"data/{selected_file_name}"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(f"⬇️ Pull {selected_file_name}", use_container_width=True):
            with st.spinner(f"Pulling {selected_file_name}..."):
                success, message = sync_single_file_from_github(selected_file_path)
            
            if success:
                st.success(message)
            else:
                st.error(message)
            
            time.sleep(1)
            st.rerun()

    with col2:
        if st.button(f"👁️ View {selected_file_name}", use_container_width=True):
            try:
                volume_path = f"/mnt/data_repo/{selected_file_path}"
                
                # Try volume first, fallback to GitHub
                if os.path.exists(volume_path):
                    if selected_file_path.endswith('.csv'):
                        data = pd.read_csv(volume_path)
                    else:
                        data = pd.read_parquet(volume_path)
                    st.info(f"📁 Showing from volume: {data.shape[0]} rows × {data.shape[1]} columns")
                else:
                    data = read_from_github(selected_file_path)
                    st.info(f"☁️ Showing from GitHub: {data.shape[0]} rows × {data.shape[1]} columns")
                
                st.dataframe(data.head(10), use_container_width=True)
                
                if len(data) > 10:
                    st.caption(f"Showing first 10 rows of {len(data)} total rows")
                
            except Exception as e:
                st.error(f"❌ Error viewing {selected_file_name}: {e}")

    with col3:
        if st.button(f"ℹ️ Info {selected_file_name}", use_container_width=True):
            # Show detailed file information
            github_info = get_github_file_info(selected_file_path)
            volume_info = get_volume_file_info(selected_file_path)
            
            col_gh, col_vol = st.columns(2)
            
            with col_gh:
                st.markdown("**GitHub Info:**")
                if github_info and github_info["exists"]:
                    st.text(f"Size: {github_info['size']:,} bytes")
                    st.text(f"Modified: {github_info['modified']}")
                    st.text(f"SHA: {github_info['sha']}")
                else:
                    st.text("File not found in GitHub")
            
            with col_vol:
                st.markdown("**Volume Info:**")
                if volume_info["exists"]:
                    st.text(f"Size: {volume_info['size']:,} bytes")
                    st.text(f"Modified: {volume_info['modified']}")
                    st.text(f"Path: {volume_info['path']}")
                else:
                    st.text("File not found in volume")

# === HELP SECTION ===
with st.expander("ℹ️ How to Use Volume Management"):
    st.markdown("""
    **Quick Actions:**
    - **📥 Pull All from GitHub**: Downloads all data files to volume for fast access
    - **🗑️ Clear Volume**: Removes all volume files (next access will reload from GitHub)  
    - **🔄 Refresh Status**: Updates the file comparison table
    - **🧹 Clear App Cache**: Clears Streamlit's data caches
    
    **File Status Meanings:**
    - **✅ In sync**: GitHub and volume have same timestamp
    - **⬇️ GitHub newer**: GitHub file modified after volume file (pull recommended)
    - **⬇️ Pull needed**: File exists on GitHub but not in volume
    - **⬆️ Volume newer**: Volume file modified after GitHub (unusual - check for unsaved changes)
    - **❌ Missing**: File doesn't exist in either location
    - **⚠️ Volume only**: File exists in volume but not GitHub (unusual)
    
    **Individual Actions:**
    - **⬇️ Pull**: Download specific file from GitHub to volume
    - **👁️ View**: Preview file contents (tries volume first, then GitHub)
    - **ℹ️ Info**: Show detailed file information and timestamps
    
    **When to Use:**
    - **After laptop changes**: Use "Pull All" or individual "Pull" buttons
    - **Fresh deployment**: Use "Pull All" to populate volume cache
    - **Troubleshooting**: Use "Clear Volume" to reset and start fresh
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
    - Volume writable: `{os.access('/mnt/data_repo', os.W_OK) if os.path.exists('/mnt/data_repo') else 'N/A'}`
    
    **File Operations:**
    - This page only manages volume ↔ GitHub sync
    - App updates still use standard write_file() function
    - Volume serves as high-speed cache for GitHub data
    """)