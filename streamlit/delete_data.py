# === IMPORTS ===
import streamlit as st
import pandas as pd
from datetime import datetime

# Import data deletion helper functions
from helpers.data_deletion_processing import (
    initialize_deletion_state,
    load_scores_data,
    get_available_tegs_and_rounds,
    preview_deletion_data,
    execute_data_deletion,
    validate_deletion_selection,
    STATE_INITIAL,
    STATE_PREVIEW,
    STATE_CONFIRMED
)

# === CONFIGURATION ===
st.title("🗑️ Delete Tournament Data")

# initialize_deletion_state() - Sets up session state for deletion workflow
initialize_deletion_state()


# === DATA LOADING ===
# Load tournament scores data if not already in session state
# Purpose: Provides data for TEG and round selection in deletion workflow
if st.session_state.scores_df is None:
    with st.spinner("Loading data..."):
        # load_scores_data() - Loads main scores dataset into session state
        load_scores_data()


# === USER INTERFACE - STATE MACHINE WORKFLOW ===
# This page uses a 3-state workflow for safe data deletion:
# 1. INITIAL - User selects TEG and rounds to delete
# 2. PREVIEW - Show deletion preview and get final confirmation
# 3. CONFIRMED - Execute deletion with backups


# === STATE 1: INITIAL - DATA SELECTION ===
if st.session_state.delete_page_state == STATE_INITIAL:
    # get_available_tegs_and_rounds() - Gets available options for selection
    teg_nums, get_rounds_for_teg = get_available_tegs_and_rounds(st.session_state.scores_df)
    
    selected_teg = st.selectbox("Select TEG to delete data for:", teg_nums)
    
    if selected_teg:
        rounds = get_rounds_for_teg(selected_teg)
        st.write("Select Rounds to delete:")
        selected_rounds = [r for r in rounds if st.checkbox(f"Round {r}", key=f"round_{r}")]

        if st.button("Preview Deletion"):
            # validate_deletion_selection() - Ensures at least one round is selected
            if not validate_deletion_selection(selected_rounds):
                st.warning("Please select at least one round to delete.")
            else:
                st.session_state.selected_teg = selected_teg
                st.session_state.selected_rounds = selected_rounds
                st.session_state.delete_page_state = STATE_PREVIEW
                st.rerun()


# === STATE 2: PREVIEW - CONFIRMATION ===
elif st.session_state.delete_page_state == STATE_PREVIEW:
    st.subheader("Deletion Preview")
    st.write(f"**TEG:** {st.session_state.selected_teg}")
    st.write(f"**Rounds:** {', '.join(map(str, st.session_state.selected_rounds))}")

    # preview_deletion_data() - Shows exactly what data will be deleted
    scores_to_delete = preview_deletion_data(
        st.session_state.scores_df, 
        st.session_state.selected_teg, 
        st.session_state.selected_rounds
    )
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
            # Reset to initial state without deleting
            initialize_deletion_state(force_reset=True)
            st.rerun()


# === STATE 3: CONFIRMED - EXECUTE DELETION ===
elif st.session_state.delete_page_state == STATE_CONFIRMED:
    with st.spinner("Backing up and deleting data..."):
        # execute_data_deletion() - Performs complete deletion workflow with backups
        execute_data_deletion(st.session_state.selected_teg, st.session_state.selected_rounds)
    
    # Reset state for next deletion operation
    initialize_deletion_state(force_reset=True)
    st.success('Data deleted', icon="✅")
    st.success("♻️ All caches cleared")
