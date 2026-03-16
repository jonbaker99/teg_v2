"""GitHub API operations for data persistence.

This module provides functions for reading from and writing to GitHub repositories.
It supports CSV, Parquet, and text files with automatic formatting and encoding.
"""

import os
import base64
import logging
from io import BytesIO, StringIO
from typing import Union

import pandas as pd

# Conditional Streamlit import for UI-independent operation
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    st = None
    HAS_STREAMLIT = False

from github import Github, InputGitTreeElement

logger = logging.getLogger(__name__)

# GitHub configuration
GITHUB_REPO = "jonbaker99/teg_v2"


def _get_github_branch() -> str:
    """Get the current git branch for GitHub operations.

    Returns the branch from Railway environment variable if available,
    otherwise tries to determine from local git config.

    Returns:
        str: The git branch name
    """
    import subprocess

    # Railway provides this variable automatically
    branch = os.getenv('RAILWAY_GIT_BRANCH')
    if branch:
        logger.info(f"Using branch from RAILWAY_GIT_BRANCH env var: {branch}")
        return branch

    # For local development, try to get the branch from the local git repo
    try:
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
        logger.info(f"Determined git branch locally: {branch}")
        return branch
    except Exception:
        # Fallback for local if git is not available or other issues
        logger.warning("Could not determine git branch locally. Defaulting to 'main'.")
        return 'main'


def read_from_github(file_path: str) -> Union[pd.DataFrame, str]:
    """Reads a file from the GitHub repository.

    This function reads a file from the specified path in the GitHub repository.
    It handles both CSV and Parquet files, decoding them appropriately.

    Args:
        file_path (str): The path to the file in the GitHub repository.

    Returns:
        pd.DataFrame or str: A pandas DataFrame if the file is a CSV or
        Parquet file, otherwise the decoded content of the file as a string.
    """
    token = os.getenv('GITHUB_TOKEN') or (st.secrets.get('GITHUB_TOKEN') if HAS_STREAMLIT and st is not None else None)
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)
    content = repo.get_contents(file_path, ref=_get_github_branch())

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


def read_text_from_github(file_path: str) -> str:
    """Reads a text file from the GitHub repository.

    This function is optimized for reading text files (e.g., .md, .txt, .json)
    from the GitHub repository. It returns the content as a decoded string.

    Args:
        file_path (str): The path to the file in the GitHub repository.

    Returns:
        str: The decoded content of the file as a string.
    """
    token = os.getenv('GITHUB_TOKEN') or (st.secrets.get('GITHUB_TOKEN') if HAS_STREAMLIT and st is not None else None)
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)
    content = repo.get_contents(file_path, ref=_get_github_branch())

    # Decode and return as string
    return base64.b64decode(content.content).decode('utf-8')


def write_text_to_github(file_path: str, content: str, commit_message: str = "Update text file"):
    """Writes a text file to the GitHub repository.

    This function writes string content to the specified file path in the GitHub
    repository. If the file already exists, it will be updated. Otherwise,
    a new file will be created.

    Args:
        file_path (str): The path to the file in the GitHub repository.
        content (str): The text content to write to the file.
        commit_message (str, optional): The commit message to use for the
            write operation. Defaults to "Update text file".
    """
    token = os.getenv('GITHUB_TOKEN') or (st.secrets.get('GITHUB_TOKEN') if HAS_STREAMLIT and st is not None else None)
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)

    # Encode string content to bytes then base64
    content_bytes = content.encode('utf-8')
    encoded_content = base64.b64encode(content_bytes).decode('utf-8')

    branch = _get_github_branch()

    # Try to get existing file (to get SHA for update)
    try:
        existing_file = repo.get_contents(file_path, ref=branch)
        # Update existing file
        repo.update_file(
            file_path,
            commit_message,
            encoded_content,
            existing_file.sha,
            branch=branch
        )
        logger.info(f"Updated {file_path} in GitHub")
    except Exception:
        # File doesn't exist, create new
        repo.create_file(
            file_path,
            commit_message,
            encoded_content,
            branch=branch
        )
        logger.info(f"Created {file_path} in GitHub")


def write_to_github(file_path: str, data: Union[pd.DataFrame, str], commit_message: str = "Update data"):
    """Writes a file to the GitHub repository.

    This function writes data to the specified file path in the GitHub
    repository. It can handle both pandas DataFrames (CSV or Parquet) and
    string data. If the file already exists, it will be updated. Otherwise,
    a new file will be created.

    Args:
        file_path (str): The path to the file in the GitHub repository.
        data (pd.DataFrame or str): The data to write to the file.
        commit_message (str, optional): The commit message to use for the
            write operation. Defaults to "Update data".
    """
    token = os.getenv('GITHUB_TOKEN') or (st.secrets.get('GITHUB_TOKEN') if HAS_STREAMLIT and st is not None else None)
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)

    branch = _get_github_branch()

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
        repo.update_file(file_path, commit_message, content, file.sha, branch=branch)
    except Exception:
        repo.create_file(file_path, commit_message, content, branch=branch)

    if HAS_STREAMLIT and st is not None:
        st.cache_data.clear()


def batch_commit_to_github(files_data: list, commit_message: str = "Batch update data"):
    """Commits multiple files to GitHub in a single commit.

    This function optimizes GitHub API usage by creating a single commit with
    multiple file changes, which is significantly faster for bulk updates than
    committing each file individually.

    Args:
        files_data (list): A list of dictionaries, where each dictionary
            contains the `file_path` and `data` for a file to be committed.
            Example: `[{'file_path': 'data/file.csv', 'data': df}, ...]`.
        commit_message (str, optional): The commit message for the batch
            update. Defaults to "Batch update data".
    """
    token = os.getenv('GITHUB_TOKEN') or (st.secrets.get('GITHUB_TOKEN') if HAS_STREAMLIT and st is not None else None)
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)
    branch = _get_github_branch()

    # Get the current commit SHA
    ref = repo.get_git_ref(f"heads/{branch}")
    base_tree = repo.get_git_commit(ref.object.sha).tree

    # Prepare all file contents and create blobs
    tree_elements = []
    for file_info in files_data:
        file_path = file_info['file_path']
        data = file_info['data']

        # Prepare content based on file type
        if isinstance(data, pd.DataFrame):
            if file_path.endswith('.csv'):
                content = data.to_csv(index=False)
            elif file_path.endswith('.parquet'):
                buffer = BytesIO()
                data.to_parquet(buffer, index=False)
                content = buffer.getvalue()
        else:
            content = data

        # Create blob for this file
        # PyGithub expects base64-encoded content for binary files
        if isinstance(content, bytes):
            blob = repo.create_git_blob(base64.b64encode(content).decode('utf-8'), 'base64')
        else:
            blob = repo.create_git_blob(content, 'utf-8')

        # Create tree element referencing the blob
        tree_elements.append(
            InputGitTreeElement(
                path=file_path,
                mode='100644',
                type='blob',
                sha=blob.sha
            )
        )

    # Create new tree with all changes
    new_tree = repo.create_git_tree(tree_elements, base_tree)

    # Create commit
    parent = repo.get_git_commit(ref.object.sha)
    new_commit = repo.create_git_commit(commit_message, new_tree, [parent])

    # Update reference
    ref.edit(new_commit.sha)

    logger.info(f"Batch committed {len(files_data)} files to GitHub in single commit")
    if HAS_STREAMLIT and st is not None:
        st.cache_data.clear()
