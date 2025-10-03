"""Streamlit page for updating TEG round data from Google Sheets.

This page provides a user interface for loading, validating, and processing new
golf round data. It uses a state machine to guide the user through a safe
data update workflow, which includes:
- Loading data from a specified Google Sheet.
- Summarizing the new data for user confirmation.
- Detecting and handling duplicate records.
- Executing the data update and refreshing all related data caches.

The page also includes a data integrity check to validate the consistency of
the main data files.
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd
import logging

# Import data loading and file operations from main utils
from utils import (
    get_google_sheet,
    check_for_complete_and_duplicate_data,
    summarise_existing_rd_data,
    clear_all_caches,
    ALL_SCORES_PARQUET,
    ALL_DATA_PARQUET
)

# Import data update workflow functions
from helpers.data_update_processing import (
    initialize_update_state,
    process_google_sheets_data,
    check_for_duplicate_data,
    analyze_hole_level_differences,
    execute_data_update,
    create_data_summary_display,
    STATE_INITIAL,
    STATE_DATA_LOADED,
    STATE_PROCESSING,
    STATE_OVERWRITE_CONFIRM
)


# === CONFIGURATION ===
st.title("🏌️‍♂️ TEG Round Data Processing")

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the state machine for data update workflow
initialize_update_state()


# === STATE MACHINE WORKFLOW ===
# This page uses a 4-state workflow to safely process golf round data:
# 1. INITIAL - User can load data from Google Sheets
# 2. DATA_LOADED - Show data summary and get user confirmation  
# 3. OVERWRITE_CONFIRM - Handle duplicate data conflicts
# 4. PROCESSING - Execute the actual data update


# === STATE 1: INITIAL - LOAD DATA ===
if st.session_state.page_state == STATE_INITIAL:
    st.write("Click the button below to load new round data from Google Sheets.")
    
    if st.button("🔄 Load Data"):
        with st.spinner("Loading and processing data from Google Sheets..."):
            # get_google_sheet() - Loads data from "TEG Round Input" Google Sheet
            raw_df = get_google_sheet("TEG Round Input", "Scores")
            
            # process_google_sheets_data() - Validates and filters to complete 18-hole rounds
            processed_df = process_google_sheets_data(raw_df)

            if processed_df.empty:
                st.error("❌ No valid rounds with 18 holes found. Please check the data and try again.")
            else:
                # Store processed data and advance to confirmation state
                st.session_state.new_data_df = processed_df
                st.session_state.page_state = STATE_DATA_LOADED
                st.rerun()


# === STATE 2: DATA LOADED - USER CONFIRMATION ===
elif st.session_state.page_state == STATE_DATA_LOADED:
    st.write("### 📊 New Data Summary")
    
    # create_data_summary_display() - Shows pivot table of loaded data for verification
    summary_pivot = create_data_summary_display(st.session_state.new_data_df)
    st.dataframe(summary_pivot)

    st.write("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("➡️ Process This Data"):
            # check_for_duplicate_data() - Detects conflicts with existing data
            if check_for_duplicate_data():
                st.session_state.page_state = STATE_OVERWRITE_CONFIRM
            else:
                st.session_state.page_state = STATE_PROCESSING
            st.rerun()
            
    with col2:
        if st.button("❌ Cancel"):
            # Reset state machine to start over
            initialize_update_state(force_reset=True)
            st.rerun()
        
    # Manual cache refresh option (for development/debugging)
    if st.button("🔄 Manual Cache Refresh"):
        # clear_all_caches() - Clears all Streamlit data caches
        clear_all_caches()
        st.success("All caches cleared successfully")


# === STATE 3: DUPLICATE DATA CONFIRMATION - HANDLE DUPLICATES ===
elif st.session_state.page_state == STATE_OVERWRITE_CONFIRM:
    st.write("## Duplicate Data Found")
    st.write("Some data already exists in the system at hole level. Please review the differences and choose how to proceed.")

    # Analyze differences between existing and new data
    differences_df, has_differences = analyze_hole_level_differences()

    if has_differences:
        st.write("**Differences Found:**")
        st.write("The following scores differ between existing data and Google Sheets data:")
        st.dataframe(differences_df)
    else:
        st.write("**No Differences Found:** All duplicate data has identical scores between existing data and Google Sheets.")

    # Show summary of duplicate data
    st.write("**Summary of Duplicate Data:**")
    existing_summary = summarise_existing_rd_data(st.session_state.duplicates_df)
    st.dataframe(existing_summary)

    st.write("**Choose Action:**")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Overwrite All Data"):
            st.session_state.page_state = STATE_PROCESSING
            # execute_data_update() - Processes data with overwrite=True
            execute_data_update(overwrite=True)
            initialize_update_state(force_reset=True)  # Reset for next run

    with col2:
        if st.button("➕ Write New Data Only"):
            st.session_state.page_state = STATE_PROCESSING
            # execute_data_update() - Processes only non-duplicate data
            execute_data_update(new_data_only=True)
            initialize_update_state(force_reset=True)  # Reset for next run

    with col3:
        if st.button("❌ Skip Update"):
            # Return to initial state without processing
            initialize_update_state(force_reset=True)
            st.rerun()


# === STATE 4: PROCESSING - EXECUTE UPDATE ===
elif st.session_state.page_state == STATE_PROCESSING:
    with st.spinner("Processing and saving data..."):
        # execute_data_update() - Main data processing without overwrite
        execute_data_update(overwrite=False)
        initialize_update_state(force_reset=True)  # Reset for next run
        st.success("✅ Data successfully processed and saved!")


# === DATA INTEGRITY CHECK SECTION ===
# This section is always available regardless of workflow state
# Provides independent data validation functionality

st.write("---")
st.write("### 🔍 Data Integrity Check")

if st.button("🔍 Run Data Integrity Check"):
    with st.spinner("🔍 Running data integrity checks..."):
        # check_for_complete_and_duplicate_data() - Validates data consistency across files
        summary = check_for_complete_and_duplicate_data(ALL_SCORES_PARQUET, ALL_DATA_PARQUET)
        issues_found = any(not df.empty for df in summary.values())

        if issues_found:
            st.error("⚠️ **Data Integrity Issues Detected:**")
            for name, df in summary.items():
                if not df.empty:
                    st.write(f"#### 📌 {name.replace('_', ' ').title()}:")
                    st.dataframe(df)
        else:
            st.success("✅ **Data Integrity Check Passed. No issues found.**")

if st.button("🔄 Clear Cache"):
    st.cache_data.clear()
    st.success("All caches cleared!")
    st.rerun()  # Refresh the page