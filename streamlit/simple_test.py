import streamlit as st
import os
from utils import (
    is_running_on_railway, 
    get_github_client, 
    GITHUB_REPO, 
    GITHUB_BRANCH,
    ALL_SCORES_FILE,
    HANDICAPS_FILE
)

st.title("Simple GitHub Test")

# Check environment
st.write(f"Running on Railway: {is_running_on_railway()}")
st.write(f"GitHub Repo: {GITHUB_REPO}")
st.write(f"GitHub Branch: {GITHUB_BRANCH}")

# Check token with better error handling
try:
    token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
    if token:
        st.success("✅ Token found")
    else:
        st.error("❌ No token found")
except Exception as e:
    st.warning("⚠️ Could not access secrets (this is normal for local development)")
    st.write(f"Error: {str(e)}")
    token = os.getenv('GITHUB_TOKEN')  # Try just environment variable
    if token:
        st.success("✅ Token found in environment variable")
    else:
        st.error("❌ No GITHUB_TOKEN environment variable found")

# Test GitHub client
if st.button("Test GitHub"):
    try:
        g = get_github_client()
        if g:
            user = g.get_user()
            st.success(f"✅ Connected as {user.login}")
            
            repo = g.get_repo(GITHUB_REPO)
            st.success(f"✅ Repository: {repo.full_name}")
            
            # Test file access
            try:
                content = repo.get_contents(ALL_SCORES_FILE, ref=GITHUB_BRANCH)
                # Handle case where get_contents returns a list
                if isinstance(content, list):
                    if content:
                        content = content[0]  # Take the first file
                        st.success(f"✅ File found: {ALL_SCORES_FILE}")
                        st.write(f"File size: {content.size} bytes")
                    else:
                        st.error(f"❌ No files found at: {ALL_SCORES_FILE}")
                else:
                    st.success(f"✅ File found: {ALL_SCORES_FILE}")
                    st.write(f"File size: {content.size} bytes")
            except Exception as e:
                st.error(f"❌ File not found: {ALL_SCORES_FILE}")
                st.write(f"Error: {e}")
        else:
            st.info("ℹ️ GitHub client not available (not running on Railway)")
    except Exception as e:
        st.error(f"❌ GitHub error: {e}")

# Instructions for local development
if not is_running_on_railway():
    st.markdown("---")
    st.header("Local Development Setup")
    st.write("To test GitHub functionality locally, you can:")
    st.write("1. Set the GITHUB_TOKEN environment variable")
    st.write("2. Create a .streamlit/secrets.toml file with your GitHub token")
    st.write("3. Or test on Railway where environment variables are configured")
    
    st.code("""
# Option 1: Set environment variable
set GITHUB_TOKEN=your_github_token_here

# Option 2: Create .streamlit/secrets.toml
[secrets]
GITHUB_TOKEN = "your_github_token_here"
    """) 