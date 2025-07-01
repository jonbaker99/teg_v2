import streamlit as st
import pandas as pd
import logging
import os
from pathlib import Path
from typing import Optional
from utils import (
    process_round_for_all_scores,
    get_google_sheet,
    reshape_round_data,
    load_and_prepare_handicap_data,
    summarise_existing_rd_data,
    update_all_data,
    check_for_complete_and_duplicate_data,
    read_file, 
    write_file,
    ALL_SCORES_PARQUET,
    HANDICAPS_CSV,
    ALL_DATA_PARQUET,
    ALL_DATA_CSV_MIRROR
)

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Session State
def initialize_session_state():
    default_states = {
        "data_loaded": False,
        "rounds_with_18_holes": None,
        "continue_processing": False,
        "overwrite_data": False,
        "overwrite_step_done": False,
        "integrity_check_done": False,
        "integrity_summary": None
    }
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# Optional: Enable Debugging Mode
DEBUG_MODE = False
if DEBUG_MODE:
    st.write("### Session State:", st.session_state)

# Function Definitions

#@st.cache_data(show_spinner=False)
def load_google_sheet(sheet_name: str, worksheet_name: str) -> pd.DataFrame:
    """
    Load data from a specified Google Sheet and worksheet.
    """
    logger.info("Fetching data from Google Sheets.")
    return get_google_sheet(sheet_name, worksheet_name)

#@st.cache_data(show_spinner=False)
def load_handicap_data(path: str) -> pd.DataFrame:
    """
    Load and prepare handicap data.
    """
    logger.info("Loading handicap data.")
    return load_and_prepare_handicap_data(path)

def remove_duplicates(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicates from existing_df based on TEGNum and Round present in new_df.
    """
    logger.info("Identifying duplicates.")
    duplicates = existing_df.merge(
        new_df,
        on=['TEGNum', 'Round'],
        how='inner',
        indicator=True
    )
    if not duplicates.empty:
        logger.info(f"Found {len(duplicates)} duplicates. Removing them.")
        existing_df = existing_df.merge(
            new_df,
            on=['TEGNum', 'Round'],
            how='left',
            indicator=True
        )
        existing_df = existing_df[existing_df['_merge'] == 'left_only'].drop(columns=['_merge'])
    else:
        logger.info("No duplicates found.")
    return existing_df, duplicates

# Streamlit App Title
st.title("🏌️‍♂️ TEG Round Data Processing")
#st.write(st.secrets)
try:
    # Step 1: Load Data
    if not st.session_state.data_loaded:
        if st.button("🔄 Load Data", key="load_data_btn"):
            with st.spinner("Loading data from Google Sheets..."):
                df = load_google_sheet("TEG Round Input", "Scores")
                st.success("✅ Data loaded from Google Sheets.")

                # Reshape to Long Format
                long_df = reshape_round_data(df, ['TEGNum', 'Round', 'Hole', 'Par', 'SI'])
                st.info("🔄 Data reshaped to long format.")

                # Filter Scores
                long_df = long_df.dropna(subset=['Score'])[long_df['Score'] != 0]
                st.info("📊 Filtered out scores that are 0 or blank.")

                # Check for 18 Holes
                rounds_with_18_holes = long_df.groupby(['TEGNum', 'Round', 'Pl']).filter(lambda x: len(x) == 18)

                if rounds_with_18_holes.empty:
                    st.error("❌ No valid rounds found. Please check the data and try again.")
                    st.stop()

                # Update Session State
                st.session_state.rounds_with_18_holes = rounds_with_18_holes
                st.session_state.data_loaded = True
                st.success("✅ Data loaded and processed successfully.")

    # Step 2: Show Summary and Continue/Cancel Buttons
    if st.session_state.data_loaded and not st.session_state.continue_processing and not st.session_state.overwrite_step_done:
        summary_df = st.session_state.rounds_with_18_holes.groupby(['TEGNum', 'Round', 'Pl'])['Score'].sum().reset_index()
        summary_pivot = summary_df.pivot(index='Pl', columns=['Round', 'TEGNum'], values='Score').fillna('-')

        st.write("### 📊 Score Summary by Player, Round, and TEG:")
        st.dataframe(summary_pivot)

        # Continue and Cancel Buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➡️ Continue", key="continue_btn"):
                st.session_state.continue_processing = True
                st.success("➡️ Proceeding to process the data...")
        with col2:
            if st.button("❌ Cancel", key="cancel_btn"):
                st.warning("❌ Process cancelled by user.")
                # Reset relevant session state
                st.session_state.data_loaded = False
                st.session_state.rounds_with_18_holes = None
                st.stop()

    # Step 3: Check for Existing Data Upon Continuing
    if st.session_state.continue_processing and not st.session_state.overwrite_step_done:
        st.write("### 🔍 Checking for Existing Data...")

        with st.spinner("📂 Loading all-scores.parquet..."):
            try:
                all_scores_df = read_file(ALL_SCORES_PARQUET)
                if all_scores_df is None:
                    st.error("Failed to load all-scores.parquet - file returned None")
                    st.stop()
                st.write(f"✓ Loaded all-scores.parquet: {all_scores_df.shape}")  # Debug info
                st.success("📂 Loaded all-scores.parquet.")
            except FileNotFoundError:
                st.warning(f"⚠️ File not found: {ALL_SCORES_PARQUET}. Creating a new empty DataFrame.")
                all_scores_df = pd.DataFrame()
            except Exception as e:
                st.error(f"An error occurred while reading {ALL_SCORES_PARQUET}: {e}")
                st.stop()

        # Identify New TEG & Round Combinations
        new_tegs_rounds = st.session_state.rounds_with_18_holes[['TEGNum', 'Round']].drop_duplicates()

        # Ensure consistent data types
        all_scores_df['TEGNum'] = all_scores_df['TEGNum'].astype(str).str.strip()
        all_scores_df['Round'] = all_scores_df['Round'].astype(str).str.strip()
        new_tegs_rounds['TEGNum'] = new_tegs_rounds['TEGNum'].astype(str).str.strip()
        new_tegs_rounds['Round'] = new_tegs_rounds['Round'].astype(str).str.strip()

        # Identify duplicates
        all_scores_df, duplicates = remove_duplicates(all_scores_df, new_tegs_rounds)

        if not duplicates.empty and not st.session_state.overwrite_data:
            st.write("### ⚠️ Existing Data Found:")
            st.write(summarise_existing_rd_data(duplicates))

            # Overwrite and Cancel Overwrite Buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Overwrite", key="overwrite_btn"):
                    st.session_state.overwrite_data = True
                    st.success("✅ Overwrite confirmed. Proceeding to remove duplicates...")
            with col2:
                if st.button("🚫 Cancel Overwrite", key="cancel_overwrite_btn"):
                    st.warning("🚫 Overwrite process cancelled by user.")
                    # Reset relevant session state
                    st.session_state.overwrite_data = False
                    st.session_state.continue_processing = False
                    st.stop()

        # Proceed with processing if no duplicates or overwrite is confirmed
        if (duplicates.empty or st.session_state.overwrite_data):
            # Remove duplicates if overwrite is confirmed
            if st.session_state.overwrite_data:
                with st.spinner("🗑️ Removing duplicates..."):
                    all_scores_df, _ = remove_duplicates(all_scores_df, new_tegs_rounds)
                    st.success("🗑️ Duplicates removed successfully.")
                # Reset overwrite flag
                st.session_state.overwrite_data = False

            # Load Handicap Data
            with st.spinner("⛳ Loading handicap data..."):
                hc_long = load_and_prepare_handicap_data(HANDICAPS_CSV)
                st.success("⛳ Handicap data loaded.")

            # Process Rounds
            with st.spinner("🔄 Processing rounds..."):
                processed_rounds = process_round_for_all_scores(st.session_state.rounds_with_18_holes, hc_long)
                st.success("🔄 Rounds processed successfully.")

            if not processed_rounds.empty:
                # Append the processed data to all-scores
                all_scores_df = pd.concat([all_scores_df, processed_rounds], ignore_index=True)
                st.write(f"✅ Appended {len(processed_rounds)} new records to all-scores.")

                # Save the updated all-scores data
                write_file(ALL_SCORES_PARQUET, all_scores_df, 
                    f"Updated data with {len(processed_rounds)} new records")
                st.success(f"✅ Updated data saved to {ALL_SCORES_PARQUET}.")

                # Run the update_all_data process
                with st.spinner("💾 Updating all-data..."):
                    update_all_data(ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR)
                    st.success("💾 All-data updated and CSV created.")
            else:
                st.warning("⚠️ No new records to append.")

            # Reset session state flags to allow for a new process
            st.session_state.continue_processing = False
            st.session_state.overwrite_step_done = False
            st.session_state.data_loaded = False
            st.session_state.rounds_with_18_holes = None

except Exception as e:
    logger.error(f"An unexpected error occurred: {e}")
    st.error(f"⚠️ An unexpected error occurred: {e}")

# Step 4: Data Integrity Check Button
st.write("---")
st.write("### 🔍 Data Integrity Check")
if st.button("🔍 Run Data Integrity Check", key="integrity_check_btn"):
    with st.spinner("🔍 Running data integrity checks..."):
        summary = check_for_complete_and_duplicate_data(ALL_SCORES_PARQUET, ALL_DATA_PARQUET)

        # Evaluate the summary dictionary to determine if there are issues
        issues_found = False
        issue_messages = []

        if not summary['incomplete_scores'].empty:
            issues_found = True
            issue_messages.append("❗ Incomplete data found in **all-scores.csv**.")

        if not summary['duplicate_scores'].empty:
            issues_found = True
            issue_messages.append("❗ Duplicate data found in **all-scores.csv**.")

        if not summary['incomplete_data'].empty:
            issues_found = True
            issue_messages.append("❗ Incomplete data found in **all-data.parquet**.")

        if not summary['duplicate_data'].empty:
            issues_found = True
            issue_messages.append("❗ Duplicate data found in **all-data.parquet**.")

        if issues_found:
            st.error("⚠️ **Data Integrity Issues Detected:**")
            for msg in issue_messages:
                st.error(msg)
            # Optionally, display detailed tables
            if not summary['incomplete_scores'].empty:
                st.write("#### 📌 Incomplete Scores in all-scores.csv:")
                st.dataframe(summary['incomplete_scores'])
            if not summary['duplicate_scores'].empty:
                st.write("#### 📌 Duplicate Scores in all-scores.csv:")
                st.dataframe(summary['duplicate_scores'])
            if not summary['incomplete_data'].empty:
                st.write("#### 📌 Incomplete Data in all-data.parquet:")
                st.dataframe(summary['incomplete_data'])
            if not summary['duplicate_data'].empty:
                st.write("#### 📌 Duplicate Data in all-data.parquet:")
                st.dataframe(summary['duplicate_data'])
        else:
            st.success("✅ **Data Integrity Check Passed. No issues found.**")
