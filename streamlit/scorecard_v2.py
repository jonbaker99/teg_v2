# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# Import data loading functions from main utils
from utils import load_all_data, get_scorecard_data, get_teg_metadata, format_date_for_scorecard

# Import scorecard generation functions (existing utilities)
from scorecard_utils import (
    load_scorecard_css,
    generate_single_round_html,
    generate_tournament_html,
    generate_round_comparison_html,
    generate_single_round_html_mobile,
    generate_tournament_html_mobile,
    generate_round_comparison_html_mobile
)

# Import scorecard-specific helper functions
from helpers.scorecard_data_processing import (
    prepare_scorecard_selection_options,
    get_round_options_for_tournament,
    validate_and_prepare_single_round_data,
    get_scorecard_type_mapping,
    determine_control_states,
    prepare_tournament_display_data,
    initialize_scorecard_session_state
)


# === CONFIGURATION ===
st.title('Scorecards')

# Initialize session state for scorecard functionality
initialize_scorecard_session_state()

# Load scorecard-specific CSS styling
css_loaded = load_scorecard_css()
if not css_loaded:
    st.warning("CSS not loaded - scorecard will not display correctly")


# === DATA LOADING ===
# Load all hole-by-hole data including incomplete TEGs
# Purpose: Scorecard display needs all available rounds, including tournaments in progress
# This allows users to view scorecards for current/incomplete tournaments
all_data = load_all_data(exclude_incomplete_tegs=False)

# Prepare selection options for dropdown menus
selection_options = prepare_scorecard_selection_options(all_data)


# === USER INTERFACE - SCORECARD TYPE AND SELECTION ===
with st.expander("Scorecard selection", expanded=True):

    # Scorecard layout selection
    scorecard_layout = st.segmented_control(
        "Scorecard layout",
        options=["Desktop", "Mobile"],
        default="Desktop"
    )

    # Get scorecard type mappings
    tab_names, display_names = get_scorecard_type_mapping()

    # Scorecard type selection radio buttons
    selected_tab_display = st.radio(
        "Choose scorecard type:",
        display_names,
        horizontal=False,
        key='scorecard_tab_selector'
    )

    # Convert display name back to internal tab name
    selected_tab = tab_names[display_names.index(selected_tab_display)]

    # Determine which controls should be enabled/disabled
    control_states = determine_control_states(selected_tab)

    # Selection controls in three columns
    st.caption("Scorecard selection")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Player selection (disabled for round comparison view)
        selected_pl = st.selectbox(
            'Player', 
            selection_options['players'], 
            disabled=control_states['player_disabled'],
            key='page_player'
        )

    with col2:
        # Tournament selection (always enabled)
        selected_tegnum = st.selectbox(
            'Tournament', 
            selection_options['tournaments'], 
            index=len(selection_options['tournaments'])-1,  # Default to most recent
            key='page_tegnum'
        )

    with col3:
        # Round selection (disabled for tournament view)
        round_options = get_round_options_for_tournament(all_data, selected_tegnum)
        selected_round = st.selectbox(
            'Round', 
            round_options,
            disabled=control_states['round_disabled'],
            index=len(round_options)-1,  # Default to most recent
            key='page_round'
        )


# === SCORECARD DISPLAY LOGIC ===

# === SINGLE PLAYER ROUND SCORECARD ===
if selected_tab == "1 Round / 1 Player":

    # get_scorecard_data() - Loads hole-by-hole data for specific player/round
    rd_data = get_scorecard_data(selected_tegnum, selected_round, selected_pl)

    # validate_and_prepare_single_round_data() - Ensures complete 18-hole data
    is_valid, prepared_data, error_message = validate_and_prepare_single_round_data(rd_data)

    if not is_valid:
        st.error(error_message)
    else:
        # Generate scorecard based on selected layout
        if scorecard_layout == "Desktop":
            scorecard_html = generate_single_round_html(selected_pl, selected_tegnum, selected_round)
        else:
            scorecard_html = generate_single_round_html_mobile(selected_pl, selected_tegnum, selected_round)
        st.markdown(scorecard_html, unsafe_allow_html=True)


# === TOURNAMENT VIEW (ONE PLAYER, ALL ROUNDS) ===
elif selected_tab == "1 Player / All Rounds":

    # get_scorecard_data() - Loads all round data for specific player/tournament
    tournament_data = get_scorecard_data(selected_tegnum, player_code=selected_pl)

    if len(tournament_data) == 0:
        st.error("No data found for the selected player and tournament.")
    else:
        # prepare_tournament_display_data() - Extracts player/tournament names for display
        display_info = prepare_tournament_display_data(tournament_data)

        # Generate scorecard based on selected layout
        if scorecard_layout == "Desktop":
            tournament_html = generate_tournament_html(selected_pl, selected_tegnum)
        else:
            tournament_html = generate_tournament_html_mobile(selected_pl, selected_tegnum)
        st.markdown(tournament_html, unsafe_allow_html=True)


# === ROUND COMPARISON (ALL PLAYERS, ONE ROUND) ===
elif selected_tab == "1 Round / All Players":

    # get_scorecard_data() - Loads data for all players in specific round
    comparison_data = get_scorecard_data(selected_tegnum, selected_round)

    if len(comparison_data) == 0:
        st.error("No data found for the selected tournament and round.")
    else:
        # Generate scorecard based on selected layout
        if scorecard_layout == "Desktop":
            comparison_html = generate_round_comparison_html(selected_tegnum, selected_round)
        else:
            comparison_html = generate_round_comparison_html_mobile(selected_tegnum, selected_round)
        st.markdown(comparison_html, unsafe_allow_html=True)