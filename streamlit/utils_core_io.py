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
        from utils_github import read_from_github
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
        from utils_github import write_to_github
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
        from utils_github import read_from_github, write_to_github
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