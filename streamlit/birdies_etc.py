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


# === CONFIGURATION ===
st.title("Career Eagles, Birdies, Pars and Triple Bogey+")

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


# === USER INTERFACE ===
# get_scoring_achievement_fields() - Defines achievement categories and their metrics
chart_fields_all = get_scoring_achievement_fields()

# create_achievement_tab_labels() - Creates user-friendly tab labels
tab_labels = create_achievement_tab_labels(chart_fields_all)

# Add additional tab for single-round maximums
tab_labels.append("Most in a single round")
tabs = st.tabs(tab_labels)

# Display achievement statistics in tabs
for i, tab in enumerate(tabs):
    with tab:
        if i < len(chart_fields_all):
            # Career achievement tabs
            chart_fields = chart_fields_all[i]
            
            # create_section_title() - Creates clean section title from field names
            section_title = create_section_title(chart_fields)
            st.markdown(f"**Career {section_title}**")
            
            # prepare_achievement_table_data() - Formats table with proper sorting and display formatting
            formatted_table = prepare_achievement_table_data(scoring_stats, chart_fields)
            st.write(
                formatted_table.to_html(
                    index=False, 
                    justify='left', 
                    classes='datawrapper-table'
                ), 
                unsafe_allow_html=True
            )
        else:
            # Single-round maximums tab
            st.markdown("**Most in a single round**")
            st.write(
                max_by_round.to_html(
                    index=False, 
                    justify='left', 
                    classes='datawrapper-table'
                ), 
                unsafe_allow_html=True
            )