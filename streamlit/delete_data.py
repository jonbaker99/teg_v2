import streamlit as st
import pandas as pd
from datetime import datetime
from utils import (
    read_file,
    write_file,
    backup_file,
    ALL_SCORES_PARQUET,
    ALL_DATA_PARQUET,
    ALL_DATA_CSV_MIRROR,
    BASE_DIR
)

# Define states for the deletion process
STATE_INITIAL = "initial"
STATE_PREVIEW = "preview"
STATE_CONFIRMED = "confirmed"

def initialize_state(force_reset=False):
    """Initializes or resets the session state for the delete page."""
    if force_reset or 'delete_page_state' not in st.session_state:
        st.session_state.delete_page_state = STATE_INITIAL
        st.session_state.scores_df = None
        st.session_state.selected_teg = None
        st.session_state.selected_rounds = []

def load_data():
    """Loads the necessary data files into session state."""
    st.session_state.scores_df = read_file(ALL_SCORES_PARQUET)

def perform_deletion():
    """Performs the backup and deletion of the selected data."""
    # Create backups first
    scores_backup_path, parquet_backup_path = create_backup()
    st.info(f"Backups created:\n- {scores_backup_path}\n- {parquet_backup_path}")

    # Load all data files
    scores_df = st.session_state.scores_df
    data_df = read_file(ALL_DATA_CSV_MIRROR)
    parquet_df = read_file(ALL_DATA_PARQUET)

    # Filter out the selected data
    teg_to_delete = st.session_state.selected_teg
    rounds_to_delete = st.session_state.selected_rounds
    
    scores_df = scores_df[~((scores_df['TEGNum'] == teg_to_delete) & (scores_df['Round'].isin(rounds_to_delete)))]
    data_df = data_df[~((data_df['TEGNum'] == teg_to_delete) & (data_df['Round'].isin(rounds_to_delete)))]
    parquet_df = parquet_df[~((parquet_df['TEGNum'] == teg_to_delete) & (parquet_df['Round'].isin(rounds_to_delete)))]

    # Save the updated data
    write_file(ALL_SCORES_PARQUET, scores_df, f"Deleted TEG {teg_to_delete}, Rounds {rounds_to_delete}")
    write_file(ALL_DATA_CSV_MIRROR, data_df, f"Deleted TEG {teg_to_delete}, Rounds {rounds_to_delete}")
    write_file(ALL_DATA_PARQUET, parquet_df, f"Deleted TEG {teg_to_delete}, Rounds {rounds_to_delete}")
    
    st.success("Data has been successfully deleted and files have been updated.")
    st.cache_data.clear()

def create_backup():
    """Creates timestamped backups of the scores and data files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Construct relative paths for GitHub
    scores_backup_path = f"data/backups/all_scores_backup_{timestamp}.parquet"
    backup_file(ALL_SCORES_PARQUET, scores_backup_path)
    
    parquet_backup_path = f"data/backups/all_data_backup_{timestamp}.parquet"
    backup_file(ALL_DATA_PARQUET, parquet_backup_path)
    
    return scores_backup_path, parquet_backup_path

# --- App UI Starts Here ---

st.title("🗑️ Delete Tournament Data")
initialize_state()

# Load data if it's not already in the session state
if st.session_state.scores_df is None:
    with st.spinner("Loading data..."):
        load_data()

# --- STATE 1: INITIAL ---
# Always show the selection interface in the initial state
if st.session_state.delete_page_state == STATE_INITIAL:
    teg_nums = sorted(st.session_state.scores_df['TEGNum'].unique(), reverse=True)
    selected_teg = st.selectbox("Select TEG to delete data for:", teg_nums)
    
    if selected_teg:
        rounds = sorted(st.session_state.scores_df[st.session_state.scores_df['TEGNum'] == selected_teg]['Round'].unique())
        st.write("Select Rounds to delete:")
        selected_rounds = [r for r in rounds if st.checkbox(f"Round {r}", key=f"round_{r}")]

        if st.button("Preview Deletion"):
            if not selected_rounds:
                st.warning("Please select at least one round to delete.")
            else:
                st.session_state.selected_teg = selected_teg
                st.session_state.selected_rounds = selected_rounds
                st.session_state.delete_page_state = STATE_PREVIEW
                st.rerun()

# --- STATE 2: PREVIEW ---
elif st.session_state.delete_page_state == STATE_PREVIEW:
    st.subheader("Deletion Preview")
    st.write(f"**TEG:** {st.session_state.selected_teg}")
    st.write(f"**Rounds:** {', '.join(map(str, st.session_state.selected_rounds))}")

    scores_to_delete = st.session_state.scores_df[
        (st.session_state.scores_df['TEGNum'] == st.session_state.selected_teg) & 
        (st.session_state.scores_df['Round'].isin(st.session_state.selected_rounds))
    ]
    st.write(f"Rows to be deleted from all_scores.parquet: **{len(scores_to_delete)}**")
    st.dataframe(scores_to_delete)

    st.warning("⚠️ This action will permanently delete the selected data.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirm Deletion"):
            st.session_state.delete_page_state = STATE_CONFIRMED
            st.rerun()
    with col2:
        if st.button("🚫 Cancel"):
            initialize_state(force_reset=True)
            st.rerun()

# --- STATE 3: CONFIRMED & DELETING ---
elif st.session_state.delete_page_state == STATE_CONFIRMED:
    with st.spinner("Backing up and deleting data..."):
        perform_deletion()
    initialize_state(force_reset=True)
    st.success('Data deleted', icon="✅")
