# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Import data loading functions from main utils
from utils import score_type_stats, max_scoretype_per_round, load_datawrapper_css

# Import scoring achievements helper functions
from helpers.scoring_achievements_processing import (
    get_scoring_achievement_fields,
    create_achievement_tab_labels,
    prepare_achievement_table_data,
    create_section_title
)

# Import streak analysis helper functions
from helpers.streak_analysis_processing import (
    prepare_streak_data_for_display,
    prepare_inverse_streak_data_for_display
)


# === CONFIGURATION ===
st.title("Eagles, Birdies etc.")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load career scoring achievement statistics
# Purpose: Provides comprehensive career totals for eagles, birdies, pars, and poor scores
# Includes both achievement counts and frequency ratios (holes per achievement)
scoring_stats = score_type_stats()

# Load single-round achievement maximums
# Purpose: Shows best single-round performances for comparison
max_by_round = max_scoretype_per_round()

# Load streak data for the new streaks tab
# Purpose: TEG 50 is excluded for accurate streak analysis as it's a special case
from utils import load_all_data
all_data = load_all_data(exclude_teg_50=True)


# === USER INTERFACE ===
# get_scoring_achievement_fields() - Defines achievement categories and their metrics
chart_fields_all = get_scoring_achievement_fields()

# Create consolidated tab structure
tab_labels = ["Number of Eagles etc", "Most in a round", "Streaks"]
tabs = st.tabs(tab_labels)

# Display achievement statistics in tabs
for i, tab in enumerate(tabs):
    with tab:
        if i == 0:
            # Consolidated career achievements tab with radio button controls
            # st.markdown("**Number of chosen score in career**")

            # Create radio button options
            score_type_options = ["Eagles", "Birdies", "Pars or Better", "Triple Bogey+"]
            selected_score_type = st.radio(
                "Select score type:",
                score_type_options,
                index=1,  # Default to Birdies
                horizontal=True
            )

            # Map radio button selection to chart_fields
            score_type_mapping = {
                "Eagles": chart_fields_all[0],
                "Birdies": chart_fields_all[1],
                "Pars or Better": chart_fields_all[2],
                "Triple Bogey+": chart_fields_all[3]
            }

            # Get the selected chart fields
            selected_chart_fields = score_type_mapping[selected_score_type]

            # create_section_title() - Creates clean section title from field names
            section_title = create_section_title(selected_chart_fields)
            st.markdown(f"**Career {section_title}**")

            # prepare_achievement_table_data() - Formats table with proper sorting and display formatting
            formatted_table = prepare_achievement_table_data(scoring_stats, selected_chart_fields)
            st.write(
                formatted_table.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )

        elif i == 1:
            # Single-round maximums tab
            st.markdown("**Most in a round**")
            st.write(
                max_by_round.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
        else:
            # Longest streaks tab
            st.markdown("**Longest Streaks WITH Score Type**")

            # prepare_streak_data_for_display() - Calculates consecutive achievements and finds maximum streaks
            # This function handles the complete workflow:
            # 1. Tracks running streaks for multiple score types (birdies, pars, etc.)
            # 2. Uses Career Count to maintain chronological order across all tournaments
            # 3. Summarizes maximum streak length for each player and achievement type
            streak_summary = prepare_streak_data_for_display(all_data)

            # Display streak summary table
            st.write(
                streak_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )

            # Add spacing between tables
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("**Longest Streaks WITHOUT Score Type**")

            # prepare_inverse_streak_data_for_display() - Calculates consecutive holes without achievements
            # This function handles the complete inverse workflow:
            # 1. Tracks running streaks for multiple inverse score types (without birdies, without pars, etc.)
            # 2. Uses Career Count to maintain chronological order across all tournaments
            # 3. Summarizes maximum inverse streak length for each player and achievement type
            inverse_streak_summary = prepare_inverse_streak_data_for_display(all_data)

            # Display inverse streak summary table
            st.write(
                inverse_streak_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )