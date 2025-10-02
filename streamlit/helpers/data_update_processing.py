"""
Data processing functions for TEG data update operations.

This module contains functions for:
- Processing and validating Google Sheets data
- Checking for duplicate data  
- State management for data update workflow
- Data integrity validation
"""

import streamlit as st
import pandas as pd
import logging
from utils import (
    reshape_round_data,
    read_file,
    write_file,
    process_round_for_all_scores,
    load_and_prepare_handicap_data,
    update_all_data,
    update_streaks_cache,
    update_commentary_caches,
    update_bestball_cache,
    summarise_existing_rd_data,
    update_teg_status_files,
    clear_all_caches,
    ALL_SCORES_PARQUET,
    HANDICAPS_CSV,
    ALL_DATA_PARQUET,
    ALL_DATA_CSV_MIRROR
)

# Configure logging
logger = logging.getLogger(__name__)

# State constants for the update workflow
STATE_INITIAL = "initial"
STATE_DATA_LOADED = "data_loaded" 
STATE_PROCESSING = "processing"
STATE_OVERWRITE_CONFIRM = "overwrite_confirm"


def initialize_update_state(force_reset=False):
    """
    Initialize or reset the session state for data update page.
    
    Args:
        force_reset (bool): Force reset of all state variables
        
    Purpose:
        Manages the multi-step data update workflow using Streamlit session state
        Ensures clean state between different update operations
    """
    if force_reset or 'page_state' not in st.session_state:
        st.session_state.page_state = STATE_INITIAL
        st.session_state.new_data_df = None
        st.session_state.existing_data_df = None
        st.session_state.duplicates_df = None


def process_google_sheets_data(raw_df):
    """
    Process and validate data loaded from Google Sheets.
    
    Args:
        raw_df (pd.DataFrame): Raw data from Google Sheets
        
    Returns:
        pd.DataFrame: Processed data with only complete 18-hole rounds
        
    Purpose:
        Transforms wide-format Google Sheets data into long format
        Filters out incomplete rounds and invalid scores
        Ensures data quality before processing
    """
    # reshape_round_data() - Converts wide format to long format by hole
    long_df = reshape_round_data(raw_df, ['TEGNum', 'Round', 'Hole', 'Par', 'SI'])
    
    # Remove invalid scores (NaN or 0)
    long_df = long_df.dropna(subset=['Score'])[long_df['Score'] != 0]
    
    # Filter to only include complete 18-hole rounds
    # Ensures data integrity by rejecting incomplete scorecards
    rounds_with_18_holes = long_df.groupby(['TEGNum', 'Round', 'Pl']).filter(lambda x: len(x) == 18)
    
    return rounds_with_18_holes


def check_for_duplicate_data():
    """
    Check for duplicate data at hole level between existing data and new data.

    Returns:
        bool: True if duplicates exist, False otherwise

    Side effects:
        Sets session state variables:
        - existing_data_df: The existing data
        - duplicates_df: Duplicate records found at hole level
        - new_data_keys: Unique hole-level keys from new data for comparison
    """
    try:
        st.session_state.existing_data_df = read_file(ALL_SCORES_PARQUET)
    except FileNotFoundError:
        st.session_state.existing_data_df = pd.DataFrame(columns=['TEGNum', 'Round', 'Hole', 'Pl'])

    # Create hole-level keys for comparison (TEG, Round, Hole, Player)
    new_data_keys = st.session_state.new_data_df[['TEGNum', 'Round', 'Hole', 'Pl']].drop_duplicates()

    # Ensure NUMERIC types for both dataframes
    if not st.session_state.existing_data_df.empty:
        st.session_state.existing_data_df['TEGNum'] = pd.to_numeric(st.session_state.existing_data_df['TEGNum'])
        st.session_state.existing_data_df['Round'] = pd.to_numeric(st.session_state.existing_data_df['Round'])
        st.session_state.existing_data_df['Hole'] = pd.to_numeric(st.session_state.existing_data_df['Hole'])

    new_data_keys['TEGNum'] = pd.to_numeric(new_data_keys['TEGNum'])
    new_data_keys['Round'] = pd.to_numeric(new_data_keys['Round'])
    new_data_keys['Hole'] = pd.to_numeric(new_data_keys['Hole'])

    # Find duplicates at hole level
    duplicates = st.session_state.existing_data_df.merge(
        new_data_keys,
        on=['TEGNum', 'Round', 'Hole', 'Pl'],
        how='inner'
    )

    # Store the actual duplicate keys (only records that exist in both datasets)
    duplicate_keys_only = duplicates[['TEGNum', 'Round', 'Hole', 'Pl']].drop_duplicates()

    st.session_state.duplicates_df = duplicates
    st.session_state.duplicate_keys_only = duplicate_keys_only
    st.session_state.all_new_data_keys = new_data_keys

    return not duplicates.empty


def analyze_hole_level_differences():
    """
    Analyze differences between existing data and new data for duplicate hole-level records.

    Returns:
        tuple: (differences_df, has_differences)
        - differences_df: DataFrame with columns [Pl, TEG, Round, Hole, Score (existing), Score (google sheets)]
        - has_differences: bool indicating if any score differences were found

    Prerequisites:
        Requires session state variables set by check_for_duplicate_data():
        - existing_data_df: Existing data
        - new_data_df: New data from Google Sheets
        - duplicates_df: Duplicate records found
    """
    if st.session_state.duplicates_df.empty:
        return pd.DataFrame(), False

    # Get the duplicate hole-level keys
    duplicate_keys = st.session_state.duplicates_df[['TEGNum', 'Round', 'Hole', 'Pl']].drop_duplicates()

    # Get existing scores for duplicate records
    existing_duplicates = st.session_state.existing_data_df.merge(
        duplicate_keys,
        on=['TEGNum', 'Round', 'Hole', 'Pl'],
        how='inner'
    )[['TEGNum', 'Round', 'Hole', 'Pl', 'Sc']].rename(columns={'Sc': 'Score_existing'})

    # Get new scores for duplicate records
    new_duplicates = st.session_state.new_data_df.merge(
        duplicate_keys,
        on=['TEGNum', 'Round', 'Hole', 'Pl'],
        how='inner'
    )[['TEGNum', 'Round', 'Hole', 'Pl', 'Score']].rename(columns={'Score': 'Score_new'})

    # Merge to compare scores
    comparison = existing_duplicates.merge(
        new_duplicates,
        on=['TEGNum', 'Round', 'Hole', 'Pl'],
        how='inner'
    )

    # Find rows where scores differ
    differences = comparison[comparison['Score_existing'] != comparison['Score_new']].copy()

    # Format for display with requested column names
    if not differences.empty:
        differences_display = differences[['Pl', 'TEGNum', 'Round', 'Hole', 'Score_existing', 'Score_new']].copy()
        differences_display.columns = ['Pl', 'TEG', 'Round', 'Hole', 'Score (existing)', 'Score (google sheets)']

        # Sort for easy reading
        differences_display = differences_display.sort_values(['TEG', 'Round', 'Pl', 'Hole'])

        return differences_display, True
    else:
        return pd.DataFrame(), False


def execute_data_update(overwrite=False, new_data_only=False):
    """
    Execute the main data update process.

    Args:
        overwrite (bool): Whether to overwrite existing duplicate data
        new_data_only (bool): Whether to process only non-duplicate data

    Purpose:
        Core data processing function that:
        1. Handles overwrite logic if duplicates exist
        2. Processes raw rounds into calculated scoring data
        3. Updates main data files
        4. Triggers cache refresh
    """
    existing_df = st.session_state.existing_data_df
    new_data_df = st.session_state.new_data_df

    if overwrite:
        # Remove existing data that will be replaced (using hole-level matching now)
        if hasattr(st.session_state, 'duplicate_keys_only') and not st.session_state.duplicate_keys_only.empty:
            duplicate_keys = st.session_state.duplicate_keys_only
            existing_df = existing_df.merge(duplicate_keys, on=['TEGNum', 'Round', 'Hole', 'Pl'], how='left', indicator=True)
            existing_df = existing_df[existing_df['_merge'] == 'left_only'].drop(columns=['_merge'])

    elif new_data_only:
        # Filter new data to exclude duplicates (process only non-duplicate data)
        if hasattr(st.session_state, 'duplicate_keys_only') and not st.session_state.duplicate_keys_only.empty:
            duplicate_keys = st.session_state.duplicate_keys_only
            # Remove duplicate records from new data, keeping only truly new records
            new_data_df = new_data_df.merge(duplicate_keys, on=['TEGNum', 'Round', 'Hole', 'Pl'], how='left', indicator=True)
            new_data_df = new_data_df[new_data_df['_merge'] == 'left_only'].drop(columns=['_merge'])

    # load_and_prepare_handicap_data() - Load player handicap data for scoring calculations
    hc_long = load_and_prepare_handicap_data(HANDICAPS_CSV)
    
    # process_round_for_all_scores() - Convert raw scores to calculated metrics (GrossVP, Stableford, etc.)
    processed_rounds = process_round_for_all_scores(new_data_df, hc_long)

    if not processed_rounds.empty:
        # Ensure consistent data types before combining datasets
        existing_df['TEGNum'] = pd.to_numeric(existing_df['TEGNum'])
        existing_df['Round'] = pd.to_numeric(existing_df['Round'])
        processed_rounds['TEGNum'] = pd.to_numeric(processed_rounds['TEGNum'])
        processed_rounds['Round'] = pd.to_numeric(processed_rounds['Round'])

        # Combine existing and new data
        final_df = pd.concat([existing_df, processed_rounds], ignore_index=True)
        
        # write_file() - Save updated dataset to main scores file
        write_file(ALL_SCORES_PARQUET, final_df, f"Updated data with {len(processed_rounds)} new records")
        st.success(f"✅ Updated data saved to {ALL_SCORES_PARQUET}.")

        # Update derivative datasets and clear caches
        with st.spinner("💾 Updating all-data..."):
            # update_all_data() - Regenerates master dataset with new records
            update_all_data(ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR)
            st.success("💾 All-data updated and CSV created.")

        # Update TEG status files to reflect completion changes
        with st.spinner("📊 Updating TEG status files..."):
            update_teg_status_files()
            st.success("📊 TEG status files updated.")

        # Update streaks cache with latest data
        with st.spinner("🏁 Updating streaks cache..."):
            update_streaks_cache()
            st.success("🏁 Streaks cache updated.")

        # Update commentary caches with latest data
        with st.spinner("📝 Updating commentary caches..."):
            update_commentary_caches()
            st.success("📝 Commentary caches updated.")

        # Update bestball cache with latest data
        with st.spinner("🏀 Updating bestball cache..."):
            update_bestball_cache()
            st.success("🏀 Bestball cache updated.")

        # Clear all caches to reflect changes
        st.cache_data.clear()
        clear_all_caches()
    else:
        st.warning("⚠️ No new records to append.")


def create_data_summary_display(new_data_df):
    """
    Create summary display of loaded data for user confirmation.
    
    Args:
        new_data_df (pd.DataFrame): Newly loaded data
        
    Returns:
        pd.DataFrame: Pivot table showing scores by player and round
        
    Purpose:
        Provides clear summary view of what data will be processed
        Allows user to verify data looks correct before proceeding
    """
    # Group by key dimensions and sum scores for overview
    summary_df = new_data_df.groupby(['TEGNum', 'Round', 'Pl'])['Score'].sum().reset_index()
    
    # Create pivot table for easy visual verification
    summary_pivot = summary_df.pivot(index='Pl', columns=['Round', 'TEGNum'], values='Score').fillna('-')
    
    return summary_pivot