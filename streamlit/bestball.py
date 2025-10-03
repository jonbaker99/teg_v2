"""Streamlit page for analyzing bestball and worstball scores.

This page displays the best and worst team performances for each round,
calculated using bestball (best score per hole) and worstball (worst score
per hole) formats. It allows users to:
- Switch between bestball and worstball views.
- Filter the data by TEG to analyze specific tournaments.
- Customize the sorting order and number of rows to display.

The page uses helper functions to:
- Load pre-calculated bestball and worstball data.
- Format the data for a clean and readable table display.
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading and utility functions from main utils
from utils import read_file, load_datawrapper_css, get_teg_filter_options, filter_data_by_teg, BESTBALL_PARQUET

# Import bestball analysis helper functions
from helpers.bestball_processing import format_team_scores_for_display


# === CONFIGURATION ===
st.title("Bestballs & Worstballs")
st.caption("Shows best & worst bestball / worstball across all players in a round")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load pre-calculated bestball/worstball data from the cache file
# Purpose: Improves performance by avoiding live calculations
try:
    all_bestball_data = read_file(BESTBALL_PARQUET)
except FileNotFoundError:
    st.error(f"Bestball data file not found at `{BESTBALL_PARQUET}`. Please run a data update to generate it.")
    st.stop()

# get_teg_filter_options() - Creates TEG dropdown options including "All TEGs" from the loaded data
tegnum_options = get_teg_filter_options(all_bestball_data)


# === USER INTERFACE ===

# === VIEW SWITCHER (Bestball / Worstball) ===
view_mode = st.segmented_control(
    "View",
    ("Bestball", "Worstball"),
    default="Bestball",
    key="bb_view_mode",
)

with st.expander("More display options"):

    # TEG filtering selection
    selected_tegnum = st.selectbox('Select TEG', tegnum_options, index=0)

    # Place sort_order and n_keep in two columns
    col1, col2 = st.columns(2)  # adjust ratios if you want them wider/narrower

    with col1:
        sort_order = st.segmented_control(
            "Sort order:",
            ('Normal', 'Reversed'),
            default='Normal'
        )

    with col2:
        n_keep = st.number_input(
            "Number of rows to show",
            min_value=1,
            max_value=100,
            value=3,
            step=1
        )

best_or_worst = "Best" if (view_mode == "Bestball") == (sort_order == "Normal") else "Worst"
sort_by_best = best_or_worst == "Best"

# filter_data_by_teg() - Applies TEG filter to the cached bestball data
filtered_data = filter_data_by_teg(all_bestball_data, selected_tegnum)

# Separate bestball and worstball data from the filtered set
bestball_data = filtered_data[filtered_data['Format'] == 'Bestball']
worstball_data = filtered_data[filtered_data['Format'] == 'Worstball']


# format_team_scores_for_display() - Formats team scores with proper sorting and vs-par notation
bestball_output = format_team_scores_for_display(bestball_data, sort_by_best)
worstball_output = format_team_scores_for_display(worstball_data, sort_by_best)

# Apply n_keep limit
bestball_output = bestball_output.head(n_keep).drop(columns = "TEGNum")
worstball_output = worstball_output.head(n_keep).drop(columns = "TEGNum")



# Pick the right slice based on the segmented control
data_map = {
    "Bestball": bestball_data,
    "Worstball": worstball_data,
}
selected_data = data_map[view_mode]

# Format, limit rows, and hide TEGNum for display
output = (
    format_team_scores_for_display(selected_data, sort_by_best)
      .head(n_keep)
      .drop(columns="TEGNum", errors="ignore")
)

st.markdown(f"**{best_or_worst} {view_mode.lower()}**")
st.write(
    output.to_html(
        index=False,
        justify="left",
        classes="datawrapper-table left-3rd full-width",
    ),
    unsafe_allow_html=True,
)

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)