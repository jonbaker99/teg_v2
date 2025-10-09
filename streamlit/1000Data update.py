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


# === COMMENTARY GENERATION SECTION ===
# This section allows users to generate round and tournament commentary reports
# for the rounds that were just updated. It appears after data is processed.

st.write("---")
st.write("### 📝 Generate Commentary Reports")

# Check if we have captured changed rounds from the data update
if hasattr(st.session_state, 'changed_rounds') and st.session_state.changed_rounds:
    # Display what rounds were changed
    st.write("**Changed Rounds Detected:**")

    # Create a formatted display of changed rounds
    changed_summary = []
    for teg in sorted(st.session_state.changed_rounds.keys()):
        rounds = st.session_state.changed_rounds[teg]
        rounds_str = ', '.join(map(str, sorted(rounds)))
        changed_summary.append(f"• TEG {teg}: Rounds {rounds_str}")

    for line in changed_summary:
        st.write(line)

    st.write("")  # Add some spacing

    # ====== OPTION 1: Generate All Reports ======
    st.write("#### 🚀 Generate All Reports")
    st.write("Generate all round and tournament reports in one go.")

    if st.button("Generate All Reports", type="primary", use_container_width=True, key="gen_all"):
        with st.status("Generating commentary reports...", expanded=True) as status:
            try:
                from helpers.commentary_generator import generate_reports_for_changes, ProgressTracker

                # Create progress tracker
                progress_tracker = ProgressTracker(status)

                # Generate reports with progress tracking
                results = generate_reports_for_changes(st.session_state.changed_rounds, progress_tracker)

                # Display results
                st.write("")  # Spacing
                st.write("**Results:**")

                # Round reports
                if results['round_reports']:
                    st.write(f"✅ **Round Reports Generated: {len(results['round_reports'])}**")
                    for teg, rnd in results['round_reports']:
                        st.write(f"   • TEG {teg}, Round {rnd}")
                else:
                    st.write("ℹ️ No round reports generated")

                # Tournament reports
                if results['tournament_reports']:
                    st.write(f"✅ **Tournament Reports Generated: {len(results['tournament_reports'])}**")
                    for teg in results['tournament_reports']:
                        st.write(f"   • TEG {teg} (moved to production)")
                else:
                    st.write("ℹ️ No tournament reports generated (no completed TEGs)")

                # Permanent failures (after retry)
                if results.get('failed_items'):
                    st.write(f"❌ **Permanent Failures (after retry): {len(results['failed_items'])}**")
                    st.write("The following reports could not be generated even after retry:")
                    for item_type, teg, rnd in results['failed_items']:
                        if item_type == 'round':
                            st.write(f"   • Round Report: TEG {teg}, Round {rnd}")
                        else:
                            st.write(f"   • Tournament Report: TEG {teg}")
                    st.info("💡 You can try generating these individually using the buttons below")

                # Errors (shown for reference, but retried reports excluded)
                if results['errors'] and not results.get('failed_items'):
                    st.write(f"⚠️ **Transient Errors (recovered on retry): {len(results['errors'])}**")
                    for err in results['errors']:
                        st.warning(f"   {err}")

                # Update status
                if results.get('failed_items'):
                    status.update(
                        label=f"Completed with {len(results['failed_items'])} permanent failure(s)",
                        state="error"
                    )
                elif results['errors']:
                    status.update(
                        label=f"Completed (recovered from {len(results['errors'])} error(s) via retry)",
                        state="complete"
                    )
                else:
                    status.update(
                        label="All reports generated successfully!",
                        state="complete"
                    )

            except Exception as e:
                st.error(f"❌ Commentary generation failed: {str(e)}")
                logger.error(f"Commentary generation error: {e}", exc_info=True)
                status.update(label="Commentary generation failed", state="error")

    st.write("---")

    # ====== OPTION 2: Individual Round Reports ======
    st.write("#### 🔵 Individual Round Reports")
    with st.expander("Generate individual round reports", expanded=False):
        for teg in sorted(st.session_state.changed_rounds.keys()):
            st.write(f"**TEG {teg}:**")
            rounds = sorted(st.session_state.changed_rounds[teg])
            cols = st.columns(len(rounds))

            for idx, round_num in enumerate(rounds):
                with cols[idx]:
                    if st.button(f"Round {round_num}", key=f"r_{teg}_{round_num}", use_container_width=True):
                        with st.status(f"Generating TEG {teg} Round {round_num}...", expanded=True) as status:
                            try:
                                from helpers.commentary_generator import generate_reports_for_changes, ProgressTracker

                                # Create single round dict
                                single_round = {teg: [round_num]}

                                # Create progress tracker
                                tracker = ProgressTracker(status)

                                # Generate single round report
                                result = generate_reports_for_changes(single_round, tracker)

                                if result['round_reports']:
                                    st.success(f"✅ Round report generated: TEG {teg}, Round {round_num}")
                                    status.update(label="Round report complete!", state="complete")
                                elif result['errors']:
                                    st.error(f"❌ Error: {result['errors'][0]}")
                                    status.update(label="Generation failed", state="error")

                            except Exception as e:
                                st.error(f"❌ Failed: {str(e)}")
                                status.update(label="Generation failed", state="error")

    st.write("---")

    # ====== OPTION 3: Individual Tournament Reports ======
    st.write("#### 🏆 Individual Tournament Reports")
    with st.expander("Generate individual tournament reports", expanded=False):
        from helpers.commentary_generator import is_tournament_complete

        completed_tegs = [t for t in st.session_state.changed_rounds.keys() if is_tournament_complete(t)]

        if completed_tegs:
            cols = st.columns(len(completed_tegs))
            for idx, teg in enumerate(completed_tegs):
                with cols[idx]:
                    if st.button(f"TEG {teg}", key=f"t_{teg}", use_container_width=True):
                        with st.status(f"Generating TEG {teg} Tournament Report...", expanded=True) as status:
                            try:
                                from helpers.commentary_generator import generate_reports_for_changes, ProgressTracker

                                # Create single TEG dict (with empty rounds since we only want tournament report)
                                # We need the rounds for the function, but it will skip them and generate tournament
                                single_teg = {teg: []}

                                # Create progress tracker
                                tracker = ProgressTracker(status)

                                # Generate tournament report
                                result = generate_reports_for_changes(single_teg, tracker)

                                if result['tournament_reports']:
                                    st.success(f"✅ Tournament report generated and moved to production: TEG {teg}")
                                    status.update(label="Tournament report complete!", state="complete")
                                elif result['errors']:
                                    st.error(f"❌ Error: {result['errors'][0]}")
                                    status.update(label="Generation failed", state="error")

                            except Exception as e:
                                st.error(f"❌ Failed: {str(e)}")
                                status.update(label="Generation failed", state="error")
        else:
            st.info("No completed tournaments in changed data")

    # Add some helpful info
    st.info("💡 **Tip**: Round reports are saved to `data/commentary/round_reports/`. "
            "Tournament reports (for completed TEGs) are moved to `data/commentary/`.")

else:
    st.info("No changed rounds detected. Upload and process data first, then you can generate commentary reports.")


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