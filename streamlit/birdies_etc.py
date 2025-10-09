"""Streamlit page for analyzing scoring achievements like eagles, birdies, and pars.

This page provides a detailed breakdown of various scoring achievements,
allowing users to explore career totals, single-round bests, and single-TEG
bests. It uses a tabbed interface to separate these different views for a
clear and organized user experience.

The page uses helper functions to:
- Load and process scoring statistics.
- Create and format display tables for different achievement types.
- Handle user selections for different scoring categories.
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Import data loading functions from main utils
from utils import score_type_stats, max_scoretype_per_round, load_datawrapper_css, max_scoretype_per_teg

# Import scoring achievements helper functions
from helpers.scoring_achievements_processing import (
    get_scoring_achievement_fields,
    create_achievement_tab_labels,
    prepare_achievement_table_data,
    create_section_title
)



# === CONFIGURATION ===
# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)
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

# Load single-teg achievement maximums
# Purpose: Shows best single-round performances for comparison
max_by_teg = max_scoretype_per_teg()


# === USER INTERFACE ===
# get_scoring_achievement_fields() - Defines achievement categories and their metrics
chart_fields_all = get_scoring_achievement_fields()

# Map score type tabs to chart_fields
score_type_mapping = {
    "Eagles": chart_fields_all[0],
    "Birdies": chart_fields_all[1],
    "Pars": chart_fields_all[2],
    "Triple Bogey+": chart_fields_all[3],
}

# Create a new tab structure
tab1, tab2, tab3 = st.tabs(["Career Totals", "Most in a Round", "Most in a TEG"])

with tab1:
    # Use a segmented control to select the score type
    score_type_options = list(score_type_mapping.keys())
    selected_score_type = st.segmented_control(
        "Select score type:",
        score_type_options,
        label_visibility="collapsed",
        default="Eagles",
    )

    # Get the chart fields for the selected score type
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

with tab2:
    # Single-round maximums tab
    reordered_table = max_by_round[['Player', 'Eagles', 'Birdies', 'Pars_or_Better', 'TBPs']].copy()
    reordered_table = reordered_table.rename(columns={'Pars_or_Better': 'Pars'})
    st.write(
        reordered_table.to_html(index=False, justify='left', classes='datawrapper-table'),
        unsafe_allow_html=True
    )

with tab3:
    # Single-TEG maximums tab
    reordered_table = max_by_teg[['Player', 'Eagles', 'Birdies', 'Pars_or_Better', 'TBPs']].copy()
    reordered_table = reordered_table.rename(columns={'Pars_or_Better': 'Pars'})
    st.write(
        reordered_table.to_html(index=False, justify='left', classes='datawrapper-table'),
        unsafe_allow_html=True
    )

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
st.markdown("")
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)
