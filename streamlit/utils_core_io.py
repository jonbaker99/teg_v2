"""
Core I/O utilities for TEG data analysis.

Environment-aware file operations that handle both local development and Railway deployment.
These functions provide the foundation for all data reading and writing operations.
"""

import os
import pandas as pd
import streamlit as st
from pathlib import Path
import logging

# Import helper utilities for dependencies
from utils_helper_utilities import get_current_branch, get_base_directory

# Configure logging
logger = logging.getLogger(__name__)

# Get BASE_DIR from helper utilities
BASE_DIR = get_base_directory()

def read_from_github(file_path):
    """
    Simple GitHub file reading with proper base64 decoding.
    
    Parameters:
        file_path (str): Path to file in GitHub repository
        
    Returns:
        pd.DataFrame or str: File content as DataFrame or string
        
    Purpose:
        Reads files from GitHub API for Railway deployment environment.
        Handles both CSV and Parquet files with proper encoding.
    """
    from github import Github
    from io import BytesIO, StringIO
    import base64
    
    token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
    g = Github(token)
    repo = g.get_repo("jonbaker99/teg_v2")  # Direct repo reference
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
    """
    Write data to GitHub repository.
    
    Parameters:
        file_path (str): Path to file in GitHub repository
        data (pd.DataFrame or str): Data to write
        commit_message (str): Commit message for the change
        
    Purpose:
        Writes files to GitHub API for Railway deployment environment.
        Handles both DataFrame and string data with proper encoding.
    """
    from github import Github
    from io import BytesIO

    token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN')
    g = Github(token)
    repo = g.get_repo("jonbaker99/teg_v2")  # Direct repo reference

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

def read_file(file_path: str) -> pd.DataFrame:
    """
    Reads a data file (CSV or Parquet) from the appropriate source (local or GitHub).
    The function determines the file type from its extension.
    
    Parameters:
        file_path (str): Path to the file to read
        
    Returns:
        pd.DataFrame: The file contents as a DataFrame
        
    Purpose:
        Main file reading function that automatically detects environment
        and uses appropriate method (local files or GitHub API).
        Used throughout the codebase for all data loading operations.
    """
    if os.getenv('RAILWAY_ENVIRONMENT'):
        return read_from_github(file_path)
    else:
        local_path = BASE_DIR / file_path
        if file_path.endswith('.csv'):
            return pd.read_csv(local_path)
        elif file_path.endswith('.parquet'):
            return pd.read_parquet(local_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

def write_file(file_path: str, data: pd.DataFrame, commit_message: str = "Update data"):
    """
    Writes a DataFrame to a file (CSV or Parquet) in the appropriate location (local or GitHub).
    The function determines the file type from its extension.
    
    Parameters:
        file_path (str): Path to the file to write
        data (pd.DataFrame): Data to write
        commit_message (str): Commit message for GitHub operations
        
    Purpose:
        Main file writing function that automatically detects environment
        and uses appropriate method (local files or GitHub API).
        Used by data processing and update operations.
    """
    if os.getenv('RAILWAY_ENVIRONMENT'):
        write_to_github(file_path, data, commit_message)
    else:
        local_path = BASE_DIR / file_path
        if file_path.endswith('.csv'):
            data.to_csv(local_path, index=False)
        elif file_path.endswith('.parquet'):
            data.to_parquet(local_path, index=False)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

def backup_file(source_path, backup_path):
    """
    Create a backup of a file.
    
    Parameters:
        source_path (str): Path to source file
        backup_path (str): Path for backup file
        
    Purpose:
        Creates file backups before potentially destructive operations.
        Used by data update and processing workflows for safety.
    """
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Read and write with new name (to backups branch)
        data = read_from_github(source_path)
        write_to_github(backup_path, data, f"Backup of {source_path}")
    else:
        import shutil
        backup_full_path = BASE_DIR / backup_path
        backup_full_path.parent.mkdir(parents=True, exist_ok=True)  # create folders if needed
        shutil.copy(BASE_DIR / source_path, backup_full_path)

def save_to_parquet(df: pd.DataFrame, output_file: str) -> None:
    """
    Save DataFrame to a Parquet file.

    Parameters:
        df (pd.DataFrame): DataFrame containing the updated golf data.
        output_file (str): Path to save the Parquet file.
        
    Purpose:
        Convenience function for saving data in Parquet format.
        Used by data processing pipelines for efficient storage.
    """
    write_file(output_file, df, "Save to parquet")
    logger.info(f"Data successfully saved to {output_file}")