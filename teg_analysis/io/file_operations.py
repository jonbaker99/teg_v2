"""Environment-aware file I/O operations.

This module provides high-level file operations (read/write) that work seamlessly
across both Railway production and local development environments. It includes
support for CSV, Parquet, and text files with automatic caching to Railway volumes.
"""

import os
import logging
from pathlib import Path
import pandas as pd

from . import volume_operations
from .github_operations import read_from_github, read_text_from_github, write_text_to_github, write_to_github

logger = logging.getLogger(__name__)


def read_file(file_path: str) -> pd.DataFrame:
    """Reads a file from the local filesystem or a mounted volume.

    This function reads a file from a mounted volume if running on Railway,
    or from the local filesystem if running locally. If the file is not
    found in the volume on Railway, it caches it from GitHub.

    Args:
        file_path (str): The path to the file.

    Returns:
        pd.DataFrame: The content of the file as a pandas DataFrame.

    Raises:
        ValueError: If the file type is not supported.
    """
    if volume_operations._is_railway():
        volume_path = volume_operations._get_volume_path(file_path)

        # Simple check: does file exist in volume?
        if os.path.exists(volume_path):
            # Fast path: read from volume (NO API calls)
            try:
                if file_path.endswith('.csv'):
                    return pd.read_csv(volume_path)
                elif file_path.endswith('.parquet'):
                    return pd.read_parquet(volume_path)
                else:
                    raise ValueError(f"Unsupported file type: {file_path}")
            except Exception as e:
                logger.warning(f"Error reading from volume {volume_path}: {e}")
                # If volume read fails, fall back to GitHub
                pass

        # File not cached or volume read failed: download and cache
        try:
            data = read_from_github(file_path)

            # Cache to volume for next time
            volume_operations._ensure_volume_dir(volume_path)

            if file_path.endswith('.csv'):
                data.to_csv(volume_path, index=False)
            elif file_path.endswith('.parquet'):
                data.to_parquet(volume_path, index=False)

            logger.info(f"Cached {file_path} to volume for future reads")
            return data

        except Exception as e:
            logger.error(f"Error reading {file_path} from GitHub: {e}")
            raise
    else:
        # Local development unchanged
        local_path = volume_operations._get_local_path(file_path)
        if file_path.endswith('.csv'):
            return pd.read_csv(local_path)
        elif file_path.endswith('.parquet'):
            return pd.read_parquet(local_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")


def write_file(file_path: str, data: pd.DataFrame, commit_message: str = "Update data", defer_github: bool = False):
    """Writes a file to the local filesystem or a mounted volume.

    This function writes a file to a mounted volume and optionally to GitHub
    if running on Railway, or to the local filesystem if running locally.

    Args:
        file_path (str): The path to the file.
        data (pd.DataFrame): The data to write.
        commit_message (str, optional): The commit message for the GitHub
            commit. Defaults to "Update data".
        defer_github (bool, optional): If True, the GitHub push is deferred
            for a batch commit. Defaults to False.

    Returns:
        dict or None: A dictionary with file information for batch commits
        if `defer_github` is True, otherwise None.

    Raises:
        ValueError: If the file type is not supported.
    """
    if volume_operations._is_railway():
        # Write to volume first (fast local write)
        volume_path = volume_operations._get_volume_path(file_path)

        try:
            volume_operations._ensure_volume_dir(volume_path)

            if file_path.endswith('.csv'):
                data.to_csv(volume_path, index=False)
            elif file_path.endswith('.parquet'):
                data.to_parquet(volume_path, index=False)
            else:
                raise ValueError(f"Unsupported file type: {file_path}")

            logger.info(f"Successfully wrote {file_path} to volume")

        except Exception as e:
            logger.error(f"Error writing to volume {volume_path}: {e}")
            # Continue to GitHub write even if volume fails

        # Write to GitHub (for cross-environment sync) unless deferred
        if not defer_github:
            try:
                write_to_github(file_path, data, commit_message)
                logger.info(f"Successfully wrote {file_path} to GitHub")
            except Exception as e:
                logger.error(f"Error writing to GitHub: {e}")
                raise  # Re-raise GitHub errors as they're critical
        else:
            # Return file info for later batch commit
            logger.info(f"Deferred GitHub push for {file_path}")
            return {'file_path': file_path, 'data': data}

    else:
        # Local development unchanged
        local_path = volume_operations._get_local_path(file_path)
        if file_path.endswith('.csv'):
            data.to_csv(local_path, index=False)
        elif file_path.endswith('.parquet'):
            data.to_parquet(local_path, index=False)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")



def read_text_file(file_path: str) -> str:
    """Reads a text file from the local filesystem or a mounted volume.

    This function reads text files (e.g., .md, .txt, .json) from a mounted volume
    if running on Railway, or from the local filesystem if running locally.
    If the file is not found in the volume on Railway, it fetches from GitHub
    and caches it to the volume.

    Args:
        file_path (str): The path to the text file.

    Returns:
        str: The content of the file as a string.
    """
    if volume_operations._is_railway():
        volume_path = volume_operations._get_volume_path(file_path)

        # Simple check: does file exist in volume?
        if os.path.exists(volume_path):
            # Fast path: read from volume (NO API calls)
            try:
                with open(volume_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Error reading from volume {volume_path}: {e}")
                # If volume read fails, fall back to GitHub
                pass

        # File not cached or volume read failed: download and cache
        try:
            content = read_text_from_github(file_path)

            # Cache to volume for next time
            volume_operations._ensure_volume_dir(volume_path)
            with open(volume_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Cached {file_path} to volume for future reads")
            return content

        except Exception as e:
            logger.error(f"Error reading {file_path} from GitHub: {e}")
            raise
    else:
        # Local development
        local_path = volume_operations._get_local_path(file_path)
        return local_path.read_text(encoding='utf-8')


def write_text_file(file_path: str, content: str, commit_message: str = "Update text file", defer_github: bool = False):
    """Writes a text file to the local filesystem or a mounted volume.

    This function writes text files to a mounted volume and optionally to GitHub
    if running on Railway, or to the local filesystem if running locally.

    Args:
        file_path (str): The path to the text file.
        content (str): The text content to write.
        commit_message (str, optional): The commit message for the GitHub
            commit. Defaults to "Update text file".
        defer_github (bool, optional): If True, the GitHub push is deferred
            for a batch commit. Defaults to False.

    Returns:
        dict or None: A dictionary with file information for batch commits
        if `defer_github` is True, otherwise None.
    """
    if volume_operations._is_railway():
        # Write to volume first (fast local write)
        volume_path = volume_operations._get_volume_path(file_path)

        try:
            volume_operations._ensure_volume_dir(volume_path)
            with open(volume_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Successfully wrote {file_path} to volume")

        except Exception as e:
            logger.error(f"Error writing to volume {volume_path}: {e}")
            # Continue to GitHub write even if volume fails

        # Write to GitHub (for cross-environment sync) unless deferred
        if not defer_github:
            try:
                write_text_to_github(file_path, content, commit_message)
                logger.info(f"Successfully wrote {file_path} to GitHub")
            except Exception as e:
                logger.error(f"Error writing to GitHub: {e}")
                raise  # Re-raise GitHub errors as they're critical
        else:
            # Return file info for later batch commit
            logger.info(f"Deferred GitHub push for {file_path}")
            return {'file_path': file_path, 'content': content}

    else:
        # Local development
        local_path = volume_operations._get_local_path(file_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        local_path.write_text(content, encoding='utf-8')



def backup_file(source_path: str, backup_path: str):
    """Creates a backup of a file.

    This function creates a backup of a file by copying it to a new location.
    It handles both Railway and local environments.

    Args:
        source_path (str): The path to the source file.
        backup_path (str): The path to the backup file.
    """
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Read and write with new name (to backups branch)
        data = read_from_github(source_path)
        write_to_github(backup_path, data, f"Backup of {source_path}")
    else:
        import shutil
        local_path = volume_operations._get_local_path(source_path)
        backup_full_path = volume_operations._get_local_path(backup_path)
        backup_full_path.parent.mkdir(parents=True, exist_ok=True)  # create folders if needed
        shutil.copy(local_path, backup_full_path)


def check_for_complete_and_duplicate_data(df: pd.DataFrame, expected_players: list = None) -> dict:
    """Check data completeness and for duplicates.

    This function validates that all expected players have data and checks
    for duplicate records in the dataset.

    Args:
        df (pd.DataFrame): The data to validate.
        expected_players (list, optional): List of expected player codes.

    Returns:
        dict: Dictionary with validation results including 'complete', 'duplicates', etc.
    """
    result = {
        'complete': True,
        'duplicate_count': 0,
        'missing_players': [],
        'duplicate_records': []
    }

    # Check for duplicates
    duplicates = df[df.duplicated(keep=False)]
    result['duplicate_count'] = len(duplicates)
    if len(duplicates) > 0:
        result['duplicate_records'] = duplicates.to_dict('records')

    # Check for expected players if provided
    if expected_players and 'player_code' in df.columns:
        found_players = set(df['player_code'].unique())
        missing = set(expected_players) - found_players
        if missing:
            result['complete'] = False
            result['missing_players'] = list(missing)

    return result
