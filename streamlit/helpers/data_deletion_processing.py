"""Data processing functions for tournament data deletion operations.

This module provides functions for managing the data deletion workflow,
including state management, data backups, and safe data deletion with
validation.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils import read_file, write_file, backup_file, clear_all_caches, update_teg_status_files, update_streaks_cache, update_commentary_caches, update_bestball_cache


# State constants for deletion workflow
STATE_INITIAL = "initial"
STATE_PREVIEW = "preview" 
STATE_CONFIRMED = "confirmed"


def initialize_deletion_state(force_reset: bool = False):
    """Initializes or resets the session state for the data deletion workflow.

    This function manages the multi-step data deletion process using session
    state to ensure a clean state between operations and prevent accidental
    data loss.

    Args:
        force_reset (bool, optional): If True, forces a reset of all state
            variables. Defaults to False.
    """
    if force_reset or 'delete_page_state' not in st.session_state:
        st.session_state.delete_page_state = STATE_INITIAL
        st.session_state.scores_df = None
        st.session_state.selected_teg = None
        st.session_state.selected_rounds = []


def load_scores_data():
    """Loads tournament scores data into the session state.

    This function loads the main scores dataset for deletion operations and
    uses the session state to avoid repeated file reads.
    """
    from utils import ALL_SCORES_PARQUET
    
    st.session_state.scores_df = read_file(ALL_SCORES_PARQUET)


def get_available_tegs_and_rounds(scores_df: pd.DataFrame) -> tuple[list, callable]:
    """Gets the available TEGs and their rounds for selection.

    This function provides the available options for data deletion, ordering
    the TEGs in reverse chronological order and enabling dynamic round
    selection based on the chosen TEG.

    Args:
        scores_df (pd.DataFrame): The tournament scores data.

    Returns:
        tuple: A tuple containing:
            - teg_nums (list): A list of available TEG numbers.
            - get_rounds_for_teg (callable): A function that returns the
              available rounds for a given TEG.
    """
    teg_nums = sorted(scores_df['TEGNum'].unique(), reverse=True)
    
    def get_rounds_for_teg(selected_teg):
        """Get available rounds for a specific TEG."""
        return sorted(scores_df[scores_df['TEGNum'] == selected_teg]['Round'].unique())
    
    return teg_nums, get_rounds_for_teg


def create_timestamped_backups() -> tuple[str, str]:
    """Creates timestamped backups of the main data files before deletion.

    This function creates safety backups before any data deletion operation,
    using timestamps to ensure unique filenames and provide a recovery path.

    Returns:
        tuple: A tuple containing the paths to the backed-up scores and data
        files.
    """
    from utils import ALL_SCORES_PARQUET, ALL_DATA_PARQUET
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create backup file paths in backups directory
    scores_backup_path = f"data/backups/all_scores_backup_{timestamp}.parquet"
    backup_file(ALL_SCORES_PARQUET, scores_backup_path)
    
    data_backup_path = f"data/backups/all_data_backup_{timestamp}.parquet"
    backup_file(ALL_DATA_PARQUET, data_backup_path)
    
    return scores_backup_path, data_backup_path


def preview_deletion_data(scores_df: pd.DataFrame, selected_teg: int, selected_rounds: list) -> pd.DataFrame:
    """Creates a preview of the data that will be deleted.

    This function shows the user exactly what data will be removed before
    confirmation, providing a final safety check before an irreversible
    operation.

    Args:
        scores_df (pd.DataFrame): The tournament scores data.
        selected_teg (int): The selected TEG number.
        selected_rounds (list): The selected round numbers.

    Returns:
        pd.DataFrame: A DataFrame containing the rows that will be deleted.
    """
    deletion_filter = (
        (scores_df['TEGNum'] == selected_teg) & 
        (scores_df['Round'].isin(selected_rounds))
    )
    
    scores_to_delete = scores_df[deletion_filter]
    
    return scores_to_delete


def execute_data_deletion(selected_teg: int, selected_rounds: list):
    """Executes the complete data deletion workflow.

    This function performs the entire deletion process, including creating
    backups, filtering the data, removing the selected data from all relevant
    files, updating the CSV mirror, and clearing caches.

    Args:
        selected_teg (int): The TEG number to delete.
        selected_rounds (list): The round numbers to delete.
    """
    from utils import ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR
    
    # Create safety backups first
    scores_backup_path, data_backup_path = create_timestamped_backups()
    st.info(f"Backups created:\\n- {scores_backup_path}\\n- {data_backup_path}")

    # Load both main data files
    scores_df = st.session_state.scores_df
    
    try:
        data_df = read_file(ALL_DATA_PARQUET)
    except Exception as e:
        st.error(f"Error reading ALL_DATA_PARQUET: {e}")
        return

    # Create deletion filter
    deletion_filter = (
        (scores_df['TEGNum'] == selected_teg) & 
        (scores_df['Round'].isin(selected_rounds))
    )
    
    # Remove selected data from both datasets
    filtered_scores_df = scores_df[~deletion_filter]
    filtered_data_df = data_df[~((data_df['TEGNum'] == selected_teg) & (data_df['Round'].isin(selected_rounds)))]

    # Collect all files for batch commit to GitHub
    import os
    batch_files = []
    is_railway = os.getenv('RAILWAY_ENVIRONMENT')

    # Update all data files with filtered data
    deletion_message = f"Deleted TEG {selected_teg}, Rounds {selected_rounds}"
    file_info = write_file(ALL_SCORES_PARQUET, filtered_scores_df, deletion_message, defer_github=is_railway)
    if file_info:
        batch_files.append(file_info)

    file_info = write_file(ALL_DATA_PARQUET, filtered_data_df, deletion_message, defer_github=is_railway)
    if file_info:
        batch_files.append(file_info)

    # Recreate CSV mirror from updated parquet data
    file_info = write_file(ALL_DATA_CSV_MIRROR, filtered_data_df, f"Recreated CSV mirror after deletion", defer_github=is_railway)
    if file_info:
        batch_files.append(file_info)

    # Update TEG status files to reflect completion changes
    status_files = update_teg_status_files(defer_github=is_railway)
    if status_files:
        batch_files.extend(status_files)

    # Update streaks cache with latest data
    streaks_file = update_streaks_cache(defer_github=is_railway)
    if streaks_file:
        batch_files.append(streaks_file)

    # Update commentary caches with latest data
    commentary_files = update_commentary_caches(defer_github=is_railway)
    if commentary_files:
        batch_files.extend(commentary_files)

    # Update bestball cache with latest data
    bestball_file = update_bestball_cache(defer_github=is_railway)
    if bestball_file:
        batch_files.append(bestball_file)

    # Batch commit all files to GitHub in single commit (Railway only)
    if is_railway and batch_files:
        with st.spinner(f"🚀 Pushing {len(batch_files)} files to GitHub..."):
            from utils import batch_commit_to_github
            batch_commit_to_github(batch_files, deletion_message)
            st.success(f"🚀 Pushed {len(batch_files)} files to GitHub in single commit.")

    # Clear all caches to reflect changes
    st.cache_data.clear()
    clear_all_caches()

    st.success("Data has been successfully deleted and files have been updated.")


def validate_deletion_selection(selected_rounds: list) -> bool:
    """Validates that the deletion selection is valid.

    This function ensures that the user has selected at least one round for
    deletion to prevent accidental empty deletion operations.

    Args:
        selected_rounds (list): The list of selected round numbers.

    Returns:
        bool: True if the selection is valid, False otherwise.
    """
    return len(selected_rounds) > 0