"""
GitHub integration utilities for TEG application.

This module isolates GitHub API dependencies to prevent import cascade failures.
Functions here require PyGithub library and GitHub authentication.
"""

import os
import base64
import pandas as pd
from io import BytesIO, StringIO
import streamlit as st


def read_from_github(file_path):
    """Simple GitHub file reading with proper base64 decoding"""
    from github import Github
    from utils_helper_utilities import get_current_branch
    from utils import GITHUB_REPO
    
    token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)
    content = repo.get_contents(file_path, ref=get_current_branch())
    
    if file_path.endswith('.csv'):
        # Decode the base64 content first
        decoded_content = base64.b64decode(content.content).decode('utf-8')
        return pd.read_csv(StringIO(decoded_content))
    elif file_path.endswith('.parquet'):
        # For parquet files, decode to bytes
        decoded_bytes = base64.b64decode(content.content)
        return pd.read_parquet(BytesIO(decoded_bytes))
    else:
        # For other files, return decoded string
        return base64.b64decode(content.content).decode('utf-8')


def write_to_github(file_path, data, commit_message="Update data"):
    """Write data to GitHub repository"""
    from github import Github
    from utils_helper_utilities import get_current_branch
    from utils import GITHUB_REPO

    token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)

    branch = get_current_branch()

    # Prepare content
    if isinstance(data, pd.DataFrame):
        if file_path.endswith('.csv'):
            content = data.to_csv(index=False)
        elif file_path.endswith('.parquet'):
            buffer = BytesIO()
            data.to_parquet(buffer, index=False)
            content = buffer.getvalue()
    else:
        content = data

    # Try update, fallback to create
    try:
        file = repo.get_contents(file_path, ref=branch)
        repo.update_file(file_path, commit_message, content, file.sha, branch=get_current_branch())
    except:
        repo.create_file(file_path, commit_message, content, branch=get_current_branch())

    st.cache_data.clear()