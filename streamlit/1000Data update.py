import streamlit as st
import pandas as pd
import logging
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

# Define the states for our state machine
STATE_INITIAL = "initial"
STATE_DATA_LOADED = "data_loaded"
STATE_PROCESSING = "processing"
STATE_OVERWRITE_CONFIRM = "overwrite_confirm"

def initialize_state(force_reset=False):
    """Initializes or resets the session state for this page."""
    if force_reset or 'page_state' not in st.session_state:
        st.session_state.page_state = STATE_INITIAL
        st.session_state.new_data_df = None
        st.session_state.existing_data_df = None
        st.session_state.duplicates_df = None

def process_loaded_data(df):
    """Reshapes and filters the data loaded from Google Sheets."""
    long_df = reshape_round_data(df, ['TEGNum', 'Round', 'Hole', 'Par', 'SI'])
    long_df = long_df.dropna(subset=['Score'])[long_df['Score'] != 0]
    rounds_with_18_holes = long_df.groupby(['TEGNum', 'Round', 'Pl']).filter(lambda x: len(x) == 18)
    return rounds_with_18_holes

def check_for_duplicates():
    """Checks if the new data already exists in the main scores file."""
    try:
        st.session_state.existing_data_df = read_file(ALL_SCORES_PARQUET)
    except FileNotFoundError:
        st.session_state.existing_data_df = pd.DataFrame(columns=['TEGNum', 'Round'])

    new_tegs_rounds = st.session_state.new_data_df[['TEGNum', 'Round']].drop_duplicates()
    
    # Ensure consistent types for merging
    st.session_state.existing_data_df['TEGNum'] = st.session_state.existing_data_df['TEGNum'].astype(str)
    st.session_state.existing_data_df['Round'] = st.session_state.existing_data_df['Round'].astype(str)
    new_tegs_rounds['TEGNum'] = new_tegs_rounds['TEGNum'].astype(str)
    new_tegs_rounds['Round'] = new_tegs_rounds['Round'].astype(str)

    duplicates = st.session_state.existing_data_df.merge(new_tegs_rounds, on=['TEGNum', 'Round'], how='inner')
    st.session_state.duplicates_df = duplicates
    return not duplicates.empty

def run_update_process(overwrite=False):
    """The main data processing and saving logic."""
    existing_df = st.session_state.existing_data_df
    new_data_df = st.session_state.new_data_df

    if overwrite:
        new_tegs_rounds = new_data_df[['TEGNum', 'Round']].drop_duplicates()
        existing_df = existing_df.merge(new_tegs_rounds, on=['TEGNum', 'Round'], how='left', indicator=True)
        existing_df = existing_df[existing_df['_merge'] == 'left_only'].drop(columns=['_merge'])

    hc_long = load_and_prepare_handicap_data(HANDICAPS_CSV)
    processed_rounds = process_round_for_all_scores(new_data_df, hc_long)

    if not processed_rounds.empty:
        # Ensure consistent data types before concatenation
        existing_df['TEGNum'] = pd.to_numeric(existing_df['TEGNum'])
        existing_df['Round'] = pd.to_numeric(existing_df['Round'])
        processed_rounds['TEGNum'] = pd.to_numeric(processed_rounds['TEGNum'])
        processed_rounds['Round'] = pd.to_numeric(processed_rounds['Round'])

        final_df = pd.concat([existing_df, processed_rounds], ignore_index=True)
        
        write_file(ALL_SCORES_PARQUET, final_df, f"Updated data with {len(processed_rounds)} new records")
        st.success(f"✅ Updated data saved to {ALL_SCORES_PARQUET}.")

        with st.spinner("💾 Updating all-data..."):
            update_all_data(ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR)
            st.success("💾 All-data updated and CSV created.")
    else:
        st.warning("⚠️ No new records to append.")

# --- App UI Starts Here ---

st.title("🏌️‍♂️ TEG Round Data Processing")
initialize_state()

# --- STATE 1: INITIAL ---
if st.session_state.page_state == STATE_INITIAL:
    st.write("Click the button below to load new round data from Google Sheets.")
    if st.button("🔄 Load Data"):
        with st.spinner("Loading and processing data from Google Sheets..."):
            raw_df = get_google_sheet("TEG Round Input", "Scores")
            processed_df = process_loaded_data(raw_df)

            if processed_df.empty:
                st.error("❌ No valid rounds with 18 holes found. Please check the data and try again.")
            else:
                st.session_state.new_data_df = processed_df
                st.session_state.page_state = STATE_DATA_LOADED
                st.rerun()

# --- STATE 2: DATA LOADED, AWAITING CONFIRMATION ---
elif st.session_state.page_state == STATE_DATA_LOADED:
    st.write("### 📊 New Data Summary")
    summary_df = st.session_state.new_data_df.groupby(['TEGNum', 'Round', 'Pl'])['Score'].sum().reset_index()
    summary_pivot = summary_df.pivot(index='Pl', columns=['Round', 'TEGNum'], values='Score').fillna('-')
    st.dataframe(summary_pivot)

    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➡️ Process This Data"):
            if check_for_duplicates():
                st.session_state.page_state = STATE_OVERWRITE_CONFIRM
            else:
                st.session_state.page_state = STATE_PROCESSING
            st.rerun()
    with col2:
        if st.button("❌ Cancel"):
            initialize_state(force_reset=True)
            st.rerun()

# --- STATE 3: OVERWRITE CONFIRMATION ---
elif st.session_state.page_state == STATE_OVERWRITE_CONFIRM:
    st.warning("⚠️ Existing Data Found!")
    st.write("The following data already exists in the system. Do you want to overwrite it?")
    st.dataframe(summarise_existing_rd_data(st.session_state.duplicates_df))
    
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, Overwrite"):
            st.session_state.page_state = STATE_PROCESSING
            run_update_process(overwrite=True)
            initialize_state(force_reset=True) # Reset for next run
            st.success("✅ Data successfully overwritten and updated!")

    with col2:
        if st.button("🚫 No, Cancel"):
            initialize_state(force_reset=True)
            st.rerun()

# --- STATE 4: PROCESSING ---
elif st.session_state.page_state == STATE_PROCESSING:
    with st.spinner("Processing and saving data..."):
        run_update_process(overwrite=False)
        initialize_state(force_reset=True) # Reset for next run
        st.success("✅ Data successfully processed and saved!")

# --- Data Integrity Check (Always available) ---
st.write("---")
st.write("### 🔍 Data Integrity Check")
if st.button("🔍 Run Data Integrity Check"):
    with st.spinner("🔍 Running data integrity checks..."):
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
