import streamlit as st
import os
from pathlib import Path
from utils import (
    is_running_on_railway, 
    get_github_client, 
    GITHUB_REPO, 
    GITHUB_BRANCH,
    get_base_directory,
    read_file,
    write_file
)

st.set_page_config(layout="wide")
st.title("🔧 GitHub Debug Tool")

# Environment Check
st.header("Environment Check")
st.write(f"Running on Railway: {is_running_on_railway()}")
st.write(f"Base Directory: {get_base_directory()}")
st.write(f"GitHub Repo: {GITHUB_REPO}")
st.write(f"GitHub Branch: {GITHUB_BRANCH}")

# GitHub Token Check
st.header("GitHub Token Check")
github_token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
if github_token:
    st.success("✅ GitHub token found")
    st.write(f"Token length: {len(github_token)} characters")
    st.write(f"Token starts with: {github_token[:10]}...")
else:
    st.error("❌ GitHub token not found")
    st.write("Available environment variables:")
    for key, value in os.environ.items():
        if 'GITHUB' in key or 'RAILWAY' in key:
            st.write(f"{key}: {value[:10] if value else 'None'}...")

# GitHub Client Test
st.header("GitHub Client Test")
if st.button("Test GitHub Client"):
    try:
        g = get_github_client()
        if g:
            user = g.get_user()
            st.success(f"✅ GitHub client working - User: {user.login}")
            
            repo = g.get_repo(GITHUB_REPO)
            st.success(f"✅ Repository access working - {repo.full_name}")
            
            branch = repo.get_branch(GITHUB_BRANCH)
            st.success(f"✅ Branch access working - {branch.name}")
        else:
            st.info("ℹ️ GitHub client not available (not running on Railway)")
    except Exception as e:
        st.error(f"❌ GitHub client error: {str(e)}")

# File Path Test
st.header("File Path Test")
test_files = [
    "data/all-scores.csv",
    "data/handicaps.csv", 
    "data/all-data.parquet",
    "data/round_info.csv"
]

for file_path in test_files:
    st.subheader(f"Testing: {file_path}")
    
    if st.button(f"Test Read: {file_path}", key=f"read_{file_path}"):
        try:
            # Test with string path
            data = read_file(file_path)
            st.success(f"✅ Successfully read {file_path}")
            st.write(f"Data shape: {data.shape if hasattr(data, 'shape') else 'N/A'}")
        except Exception as e:
            st.error(f"❌ Error reading {file_path}: {str(e)}")

# Write Test
st.header("Write Test")
if st.button("Test Write to GitHub"):
    try:
        import pandas as pd
        test_data = pd.DataFrame({
            'test_col': ['test_value'],
            'timestamp': [pd.Timestamp.now()]
        })
        
        test_file = "data/test_file.csv"
        write_file_to_storage(test_file, test_data, 'csv', "Test write from debug tool")
        st.success(f"✅ Successfully wrote test file: {test_file}")
        
        # Try to read it back
        read_data = read_file(test_file)
        st.success(f"✅ Successfully read back test file")
        st.dataframe(read_data)
        
    except Exception as e:
        st.error(f"❌ Error in write test: {str(e)}")

# Path Conversion Test
st.header("Path Conversion Test")
test_paths = [
    Path("data/all-scores.csv"),
    "data/all-scores.csv",
    Path(get_base_directory()) / "data" / "all-scores.csv",
    str(Path(get_base_directory()) / "data" / "all-scores.csv")
]

for i, test_path in enumerate(test_paths):
    st.write(f"Test path {i+1}: {test_path} (type: {type(test_path)})")
    
    if isinstance(test_path, Path):
        try:
            relative_path = test_path.relative_to(get_base_directory())
            st.write(f"  → Relative path: {relative_path}")
        except ValueError as e:
            st.write(f"  → Error getting relative path: {e}")
    
    # Test the conversion logic from read_file
    try:
        if isinstance(test_path, Path):
            github_path = str(test_path.relative_to(get_base_directory())).replace('\\', '/')
        else:
            github_path = str(test_path).replace('\\', '/')
            if github_path.startswith('/'):
                github_path = github_path[1:]
            base_dir_str = str(get_base_directory()).replace('\\', '/')
            if github_path.startswith(base_dir_str):
                github_path = github_path[len(base_dir_str):].lstrip('/')
        
        st.write(f"  → GitHub path: {github_path}")
    except Exception as e:
        st.write(f"  → Error in conversion: {e}")
