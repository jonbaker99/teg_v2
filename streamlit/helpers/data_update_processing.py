"""Data processing functions for TEG data update operations.

This module provides functions for processing and validating Google Sheets data,
checking for duplicate data, managing the data update workflow state, and
ensuring data integrity.
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


def initialize_update_state(force_reset: bool = False):
    """Initializes or resets the session state for the data update page.

    This function manages the multi-step data update workflow using Streamlit
    session state to ensure a clean state between different update operations.

    Args:
        force_reset (bool, optional): If True, forces a reset of all state
            variables. Defaults to False.
    """
    if force_reset or 'page_state' not in st.session_state:
        st.session_state.page_state = STATE_INITIAL
        st.session_state.new_data_df = None
        st.session_state.existing_data_df = None
        st.session_state.duplicates_df = None


def process_google_sheets_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Processes and validates data loaded from Google Sheets.

    This function transforms wide-format Google Sheets data into a long format,
    filters out incomplete rounds and invalid scores, and ensures data quality
    before further processing.

    Args:
        raw_df (pd.DataFrame): The raw data from Google Sheets.

    Returns:
        pd.DataFrame: The processed data containing only complete 18-hole
        rounds.
    """
    # reshape_round_data() - Converts wide format to long format by hole
    long_df = reshape_round_data(raw_df, ['TEGNum', 'Round', 'Hole', 'Par', 'SI'])
    
    # Remove invalid scores (NaN or 0)
    long_df = long_df.dropna(subset=['Score'])[long_df['Score'] != 0]
    
    # Filter to only include complete 18-hole rounds
    # Ensures data integrity by rejecting incomplete scorecards
    rounds_with_18_holes = long_df.groupby(['TEGNum', 'Round', 'Pl']).filter(lambda x: len(x) == 18)
    
    return rounds_with_18_holes


def check_for_duplicate_data() -> bool:
    """Checks for duplicate data at the hole level.

    This function compares the new data with existing data to identify any
    duplicate entries at the hole level.

    Returns:
        bool: True if duplicates are found, False otherwise.
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


def analyze_hole_level_differences() -> tuple[pd.DataFrame, bool]:
    """Analyzes differences between existing and new data for duplicate records.

    This function compares the scores of duplicate records at the hole level
    to identify any discrepancies.

    Returns:
        tuple: A tuple containing:
            - differences_df (pd.DataFrame): A DataFrame showing the
              differences.
            - has_differences (bool): True if any differences were found,
              False otherwise.
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


def execute_data_update(overwrite: bool = False, new_data_only: bool = False):
    """Executes the main data update process.

    This is the core data processing function that handles the overwrite
    logic, processes raw rounds into calculated scoring data, updates the main
    data files, and triggers a cache refresh.

    Args:
        overwrite (bool, optional): Whether to overwrite existing duplicate
            data. Defaults to False.
        new_data_only (bool, optional): Whether to process only non-duplicate
            data. Defaults to False.
    """
    existing_df = st.session_state.existing_data_df
    new_data_df = st.session_state.new_data_df

    # Capture changed rounds for optional commentary generation
    # This doesn't affect the data update flow - errors are logged but don't block
    try:
        changed_rounds = new_data_df[['TEGNum', 'Round']].drop_duplicates()
        changed_rounds_dict = {}
        for _, row in changed_rounds.iterrows():
            teg = int(row['TEGNum'])
            round_num = int(row['Round'])
            if teg not in changed_rounds_dict:
                changed_rounds_dict[teg] = []
            changed_rounds_dict[teg].append(round_num)
        st.session_state.changed_rounds = changed_rounds_dict
        logger.info(f"Captured changed rounds: {changed_rounds_dict}")
    except Exception as e:
        logger.warning(f"Could not capture changed rounds for commentary: {e}")
        # Don't fail the data update if this fails

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

        # Collect all files for batch commit to GitHub
        import os
        batch_files = []
        is_railway = os.getenv('RAILWAY_ENVIRONMENT')

        # write_file() - Save updated dataset to main scores file
        file_info = write_file(ALL_SCORES_PARQUET, final_df, f"Updated data with {len(processed_rounds)} new records", defer_github=is_railway)
        if file_info:
            batch_files.append(file_info)
        st.success(f"✅ Updated data saved to {ALL_SCORES_PARQUET}.")

        # Update derivative datasets and clear caches
        with st.spinner("💾 Updating all-data..."):
            # update_all_data() - Regenerates master dataset with new records (returns file infos)
            update_files = update_all_data(ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR, defer_github=is_railway)
            if update_files:
                batch_files.extend(update_files)
            st.success("💾 All-data updated and CSV created.")

        # Update TEG status files to reflect completion changes
        with st.spinner("📊 Updating TEG status files..."):
            status_files = update_teg_status_files(defer_github=is_railway)
            if status_files:
                batch_files.extend(status_files)
            st.success("📊 TEG status files updated.")

        # Update streaks cache with latest data
        with st.spinner("🏁 Updating streaks cache..."):
            streaks_file = update_streaks_cache(defer_github=is_railway)
            if streaks_file:
                batch_files.append(streaks_file)
            st.success("🏁 Streaks cache updated.")

        # Update commentary caches with latest data
        with st.spinner("📝 Updating commentary caches..."):
            commentary_files = update_commentary_caches(defer_github=is_railway)
            if commentary_files:
                batch_files.extend(commentary_files)
            st.success("📝 Commentary caches updated.")

        # Update bestball cache with latest data
        with st.spinner("🏀 Updating bestball cache..."):
            bestball_file = update_bestball_cache(defer_github=is_railway)
            if bestball_file:
                batch_files.append(bestball_file)
            st.success("🏀 Bestball cache updated.")

        # Batch commit all files to GitHub in single commit (Railway only)
        if is_railway and batch_files:
            with st.spinner(f"🚀 Pushing {len(batch_files)} files to GitHub..."):
                from utils import batch_commit_to_github
                batch_commit_to_github(batch_files, f"Data update: {len(processed_rounds)} new records + cache updates")
                st.success(f"🚀 Pushed {len(batch_files)} files to GitHub in single commit.")

        # Clear all caches to reflect changes
        st.cache_data.clear()
        clear_all_caches()
    else:
        st.warning("⚠️ No new records to append.")


def create_data_summary_display(new_data_df: pd.DataFrame) -> pd.DataFrame:
    """Creates a summary display of the loaded data for user confirmation.

    This function provides a clear summary view of the data that will be
    processed, allowing the user to verify that it is correct before
    proceeding.

    Args:
        new_data_df (pd.DataFrame): The newly loaded data.

    Returns:
        pd.DataFrame: A pivot table showing scores by player and round.
    """
    # Group by key dimensions and sum scores for overview
    summary_df = new_data_df.groupby(['TEGNum', 'Round', 'Pl'])['Score'].sum().reset_index()
    
    # Create pivot table for easy visual verification
    summary_pivot = summary_df.pivot(index='Pl', columns=['Round', 'TEGNum'], values='Score').fillna('-')
    
    return summary_pivot