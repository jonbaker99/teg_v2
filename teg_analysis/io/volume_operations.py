"""Railway volume and local environment management.

This module provides helper functions for managing file paths and directories
across Railway production and local development environments. It includes
environment detection and path construction utilities.
"""

import os
from pathlib import Path


def _is_railway() -> bool:
    """Check if running on Railway environment.

    Returns:
        bool: True if running on Railway, False for local development
    """
    return bool(os.getenv('RAILWAY_ENVIRONMENT'))


def _get_volume_path(file_path: str) -> str:
    """Get Railway volume path for file.

    Args:
        file_path (str): Relative file path (e.g., 'data/file.csv')

    Returns:
        str: Absolute volume path (e.g., '/mnt/data_repo/data/file.csv')
    """
    return f"/mnt/data_repo/{file_path}"


def _get_local_path(file_path: str) -> Path:
    """Get local filesystem path for file.

    Args:
        file_path (str): Relative file path (e.g., 'data/file.csv')

    Returns:
        Path: Absolute local path based on BASE_DIR

    Note:
        Requires BASE_DIR to be imported from the calling context.
    """
    # Import here to avoid circular imports
    from pathlib import Path
    BASE_DIR = Path.cwd().parent if Path.cwd().name == "streamlit" else Path.cwd()
    return BASE_DIR / file_path


def _ensure_volume_dir(volume_path: str) -> None:
    """Ensure parent directory exists for volume path.

    Args:
        volume_path (str): Full path to file in volume
    """
    os.makedirs(os.path.dirname(volume_path), exist_ok=True)


def clear_volume_cache(file_path: str = None) -> str:
    """Clears the volume cache for a specific file or all files.

    This function is useful for forcing a refresh from GitHub. It clears the
    cache on the mounted volume in a Railway environment.

    Args:
        file_path (str, optional): The path to the file to clear from the
            cache. If None, the entire volume cache is cleared. Defaults to
            None.

    Returns:
        str: A message indicating the result of the operation.
    """
    if not os.getenv('RAILWAY_ENVIRONMENT'):
        return "Not running on Railway - no volume to clear"

    try:
        if file_path:
            # Clear specific file
            volume_path = f"/mnt/data_repo/{file_path}"
            if os.path.exists(volume_path):
                os.remove(volume_path)
                return f"Cleared volume cache for {file_path}"
            else:
                return f"File {file_path} not found in volume cache"
        else:
            # Clear entire volume
            import shutil
            volume_base = "/mnt/data_repo"
            if os.path.exists(volume_base):
                shutil.rmtree(volume_base)
                return "Cleared entire volume cache"
            else:
                return "Volume cache already empty"

    except Exception as e:
        return f"Error clearing volume cache: {e}"
