"""
Data processing functions for tournament data deletion operations.

This module contains functions for:
- Managing deletion workflow state machine
- Creating data backups before deletion
- Performing safe data deletion with validation
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils import read_file, write_file, backup_file, clear_all_caches, update_teg_status_files, update_streaks_cache


# State constants for deletion workflow
STATE_INITIAL = "initial"
STATE_PREVIEW = "preview" 
STATE_CONFIRMED = "confirmed"


def initialize_deletion_state(force_reset=False):
    """
    Initialize or reset session state for data deletion workflow.
    
    Args:
        force_reset (bool): Force reset of all state variables
        
    Purpose:
        Manages the multi-step data deletion workflow using session state
        Ensures clean state between different deletion operations
        Prevents accidental data loss through controlled state management
    """
    if force_reset or 'delete_page_state' not in st.session_state:
        st.session_state.delete_page_state = STATE_INITIAL
        st.session_state.scores_df = None
        st.session_state.selected_teg = None
        st.session_state.selected_rounds = []


def load_scores_data():
    """
    Load tournament scores data into session state.
    
    Purpose:
        Loads main scores dataset for deletion operations
        Uses session state to avoid repeated file reads
        Provides data for TEG and round selection
    """
    from utils import ALL_SCORES_PARQUET
    
    st.session_state.scores_df = read_file(ALL_SCORES_PARQUET)


def get_available_tegs_and_rounds(scores_df):
    """
    Get available TEGs and their rounds for selection.
    
    Args:
        scores_df (pd.DataFrame): Tournament scores data
        
    Returns:
        tuple: (teg_nums, rounds_by_teg_function) for UI selection
        
    Purpose:
        Provides available options for data deletion
        Orders TEGs in reverse chronological order (most recent first)
        Enables dynamic round selection based on selected TEG
    """
    teg_nums = sorted(scores_df['TEGNum'].unique(), reverse=True)
    
    def get_rounds_for_teg(selected_teg):
        """Get available rounds for a specific TEG."""
        return sorted(scores_df[scores_df['TEGNum'] == selected_teg]['Round'].unique())
    
    return teg_nums, get_rounds_for_teg


def create_timestamped_backups():
    """
    Create timestamped backups of main data files before deletion.
    
    Returns:
        tuple: (scores_backup_path, data_backup_path) for confirmation display
        
    Purpose:
        Creates safety backups before any data deletion operations
        Uses timestamps to ensure unique backup file names
        Provides recovery path in case deletion needs to be reversed
    """
    from utils import ALL_SCORES_PARQUET, ALL_DATA_PARQUET
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create backup file paths in backups directory
    scores_backup_path = f"data/backups/all_scores_backup_{timestamp}.parquet"
    backup_file(ALL_SCORES_PARQUET, scores_backup_path)
    
    data_backup_path = f"data/backups/all_data_backup_{timestamp}.parquet"
    backup_file(ALL_DATA_PARQUET, data_backup_path)
    
    return scores_backup_path, data_backup_path


def preview_deletion_data(scores_df, selected_teg, selected_rounds):
    """
    Create preview of data that will be deleted.
    
    Args:
        scores_df (pd.DataFrame): Tournament scores data
        selected_teg (int): Selected TEG number
        selected_rounds (list): Selected round numbers
        
    Returns:
        pd.DataFrame: Data rows that will be deleted
        
    Purpose:
        Shows user exactly what data will be removed before confirmation
        Enables validation that correct data is selected for deletion
        Provides final safety check before irreversible operation
    """
    deletion_filter = (
        (scores_df['TEGNum'] == selected_teg) & 
        (scores_df['Round'].isin(selected_rounds))
    )
    
    scores_to_delete = scores_df[deletion_filter]
    
    return scores_to_delete


def execute_data_deletion(selected_teg, selected_rounds):
    """
    Execute the complete data deletion workflow.
    
    Args:
        selected_teg (int): TEG number to delete
        selected_rounds (list): Round numbers to delete
        
    Purpose:
        Performs the complete deletion workflow:
        1. Creates backups for safety
        2. Loads and filters both main data files
        3. Removes selected data from all relevant files
        4. Updates CSV mirror file
        5. Clears caches to reflect changes
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

    # Update all data files with filtered data
    deletion_message = f"Deleted TEG {selected_teg}, Rounds {selected_rounds}"
    write_file(ALL_SCORES_PARQUET, filtered_scores_df, deletion_message)
    write_file(ALL_DATA_PARQUET, filtered_data_df, deletion_message)
    
    # Recreate CSV mirror from updated parquet data
    write_file(ALL_DATA_CSV_MIRROR, filtered_data_df, f"Recreated CSV mirror after deletion")
    
    # Update TEG status files to reflect completion changes
    update_teg_status_files()

    # Update streaks cache with latest data
    update_streaks_cache()

    # Clear all caches to reflect changes
    st.cache_data.clear()
    clear_all_caches()

    st.success("Data has been successfully deleted and files have been updated.")


def validate_deletion_selection(selected_rounds):
    """
    Validate that deletion selection is valid.
    
    Args:
        selected_rounds (list): Selected round numbers
        
    Returns:
        bool: True if selection is valid, False otherwise
        
    Purpose:
        Ensures user has selected at least one round for deletion
        Prevents accidental empty deletion operations
    """
    return len(selected_rounds) > 0