"""Streamlit page for detailed scoring analysis.

This page provides a deep dive into various scoring metrics, including:
- Average scores by par value (Par 3, 4, 5).
- Career scoring statistics for eagles, birdies, pars, and triple bogeys.
- Single-round records for the most of each score type.
- Longest streaks for different scoring achievements.

The page uses helper functions to:
- Load and process the complete dataset.
- Calculate and format scoring statistics.
- Display the data in clear, readable tables.
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np

# Import data loading and processing functions from main utils
from utils import score_type_stats, load_all_data, max_scoretype_per_round, load_datawrapper_css

# Import scoring-specific helper functions
from helpers.scoring_data_processing import (
    format_vs_par_value, 
    prepare_average_scores_by_par, 
    format_scoring_stats_columns,
    calculate_multi_score_running_sum, 
    summarize_multi_score_running_sum
)


# === CONFIGURATION ===
st.title("Scoring")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === PAGE NAVIGATION ===
st.markdown('---')
st.markdown("### Contents")
st.markdown('1. Average score by par')
st.markdown('2. Number of eagles, birdies etc.')
st.markdown('3. Most birdies etc. in a round')
st.markdown('4. Longest streaks')
st.markdown('---')


# === DATA LOADING ===
# Load all data including incomplete TEGs (excludes TEG 50)
# Purpose: Scoring analysis needs all available shot data for comprehensive statistics
# Including incomplete TEGs gives more complete picture of scoring patterns
all_data_with_incomplete = load_all_data(exclude_incomplete_tegs=False)

# Load career scoring statistics
# Purpose: Pre-calculated stats for eagles, birdies, pars, etc. by player
scoring_stats = score_type_stats()

# Load maximum scores per round data
# Purpose: Shows best single-round performances for each score type
max_by_round = max_scoretype_per_round()


# === SECTION 1: AVERAGE SCORE BY PAR ===
st.subheader('Average score by Par')

# prepare_average_scores_by_par() - Calculates and formats avg performance by par value
avg_scores_table = prepare_average_scores_by_par(all_data_with_incomplete)

# Display formatted table using consistent datawrapper styling
st.write(
    avg_scores_table.to_html(
        classes='dataframe, datawrapper-table', 
        index=False, 
        justify='left'
    ), 
    unsafe_allow_html=True
)

st.markdown('---')


# === SECTION 2: CAREER SCORING STATISTICS ===
st.subheader("Career Eagles, Birdies, Pars and Triple Bogey+")

# Define score types and their corresponding data fields
scoring_categories = [
    ['Eagles', 'Holes_per_Eagle'],
    ['Birdies', 'Holes_per_Birdie'], 
    ['Pars_or_Better', 'Holes_per_Par_or_Better'],
    ['TBPs', 'Holes_per_TBP']
]

# Create tab labels with readable names
tab_labels = [category[0].replace("_", " ") for category in scoring_categories]
tabs = st.tabs(tab_labels)

# Display statistics in tabs for better organization
for i, tab in enumerate(tabs):
    with tab:
        chart_fields = scoring_categories[i]
        section_title = chart_fields[0].replace("_", " ")
        st.markdown(f"**Career {section_title}**")
        
        # Extract relevant columns and sort by performance
        table_df = scoring_stats[['Player'] + chart_fields].sort_values(
            by=chart_fields, 
            ascending=[False, True]  # More occurrences first, then fewer holes per occurrence
        )
        
        # format_scoring_stats_columns() - Formats numbers and handles infinite values
        table_df = format_scoring_stats_columns(table_df)
        
        # Display formatted table
        st.write(
            table_df.to_html(
                index=False, 
                justify='left', 
                classes='datawrapper-table'
            ), 
            unsafe_allow_html=True
        )

st.markdown('---')


# === SECTION 3: SINGLE ROUND MAXIMUMS ===
st.subheader('Most of each type of score in a single round')

# max_scoretype_per_round() - Pre-calculated maximum achievements in single rounds
# Display the pre-formatted table
st.write(
    max_by_round.to_html(
        index=False, 
        justify='left', 
        classes='datawrapper-table'
    ), 
    unsafe_allow_html=True
)

st.markdown('---')


# === SECTION 4: LONGEST STREAKS ANALYSIS ===
st.subheader('Longest Streaks by Player')

# Load clean dataset for streak analysis (excludes TEG 50 for consistency)
# Purpose: Streak analysis requires chronological order, excludes anomalous TEG 50
all_data_for_streaks = load_all_data(exclude_teg_50=True)

# calculate_multi_score_running_sum() - Adds running streak calculations to data
# This function tracks consecutive achievements (birdies, pars, etc.) 
streaks_data = calculate_multi_score_running_sum(all_data_for_streaks)

# summarize_multi_score_running_sum() - Creates final summary of longest streaks
# Extracts maximum streak length for each player and score type
streak_summary = summarize_multi_score_running_sum(streaks_data)

# Display final streaks table
st.write(
    streak_summary.to_html(
        index=False, 
        justify='left', 
        classes='datawrapper-table'
    ), 
    unsafe_allow_html=True
)