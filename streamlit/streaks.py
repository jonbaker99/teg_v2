# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np

# Import data loading functions from main utils
from utils import load_datawrapper_css, load_all_data

# Import streak analysis helper functions
from helpers.streak_analysis_processing import (
    prepare_good_streaks_data,
    prepare_bad_streaks_data,
    prepare_current_good_streaks_data,
    prepare_current_bad_streaks_data
)


# === CONFIGURATION ===
st.title("Streaks")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load streak data
# Purpose: TEG 50 is excluded for accurate streak analysis as it's a special case
all_data = load_all_data(exclude_teg_50=True)

# Cache all streak table calculations for performance
@st.cache_data
def get_all_streak_tables(all_data):
    """
    Cache all streak table calculations together for instant radio button switching.
    Only recalculates when underlying data changes.
    All tables are sorted alphabetically by Player name.
    """
    # Get all streak tables
    tables = {
        'good_max': prepare_good_streaks_data(all_data),
        'bad_max': prepare_bad_streaks_data(all_data),
        'good_current': prepare_current_good_streaks_data(all_data),
        'bad_current': prepare_current_bad_streaks_data(all_data)
    }

    # Sort all tables alphabetically by Player
    for key, table in tables.items():
        if 'Player' in table.columns:
            tables[key] = table.sort_values('Player').reset_index(drop=True)

    return tables

# Calculate all streak tables once
streak_tables = get_all_streak_tables(all_data)


# === USER INTERFACE ===
# Radio button to choose between max and current streaks
streak_type = st.radio(
    "Select streak type:",
    ["Max", "Current"],
    horizontal=True
)

# Create main tab structure for streaks
tab_labels = ["Good Streaks", "Bad Streaks"]
tabs = st.tabs(tab_labels)

# Display streak statistics in tabs
for i, tab in enumerate(tabs):
    with tab:
        if i == 0:
            # Good streaks tab - select from cached tables
            if streak_type == "Max":
                good_streaks_summary = streak_tables['good_max']
            else:
                good_streaks_summary = streak_tables['good_current']

            # Display good streaks summary table
            st.write(
                good_streaks_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
            st.caption("*: current streak is maximum streak")

        elif i == 1:
            # Bad streaks tab - select from cached tables
            if streak_type == "Max":
                bad_streaks_summary = streak_tables['bad_max']
            else:
                bad_streaks_summary = streak_tables['bad_current']

            # Display bad streaks summary table
            st.write(
                bad_streaks_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
            st.caption("*: current streak is maximum streak")

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
add_custom_navigation_links(__file__, layout="horizontal", separator=" | ")
                