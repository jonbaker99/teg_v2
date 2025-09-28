# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import load_all_data, load_datawrapper_css, get_teg_filter_options, filter_data_by_teg

# Import bestball analysis helper functions
from helpers.bestball_processing import (
    prepare_bestball_data,
    calculate_bestball_scores,
    calculate_worstball_scores,
    format_team_scores_for_display
)


# === CONFIGURATION ===
st.title("Bestballs & Worstballs")
st.caption("Shows best & worst bestball / worstball across all players in a round")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load TEG data excluding TEG 50 but including incomplete tournaments for current analysis
# Purpose: Team format analysis benefits from current tournament data for up-to-date comparisons
all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

# prepare_bestball_data() - Adds TEG|Round|Hole identifiers for team format calculations
prepared_data = prepare_bestball_data(all_data)

# get_teg_filter_options() - Creates TEG dropdown options including "All TEGs"
tegnum_options = get_teg_filter_options(prepared_data)


# === USER INTERFACE ===
# TEG filtering selection
selected_tegnum = st.selectbox('Select TEG', tegnum_options, index=0)

# filter_data_by_teg() - Applies TEG filter to tournament data
filtered_data = filter_data_by_teg(prepared_data, selected_tegnum)

# Best/Worst ranking selection
best_or_worst = st.radio("Rank by best or worst:", ('Best', 'Worst'), horizontal=True)
sort_by_best = (best_or_worst == 'Best')

# calculate_bestball_scores() - Computes team scores using best score per hole
bestball_data = calculate_bestball_scores(filtered_data)

# calculate_worstball_scores() - Computes team scores using worst score per hole
worstball_data = calculate_worstball_scores(filtered_data)

# format_team_scores_for_display() - Formats team scores with proper sorting and vs-par notation
bestball_output = format_team_scores_for_display(bestball_data, sort_by_best)
worstball_output = format_team_scores_for_display(worstball_data, sort_by_best)

# Display results in tabs
tab1, tab2 = st.tabs(["Bestball", "Worstball"])

with tab1:
    st.markdown(f'**{best_or_worst} bestball**')
    st.write(
        bestball_output.to_html(
            index=False, 
            justify='left', 
            classes='datawrapper-table left-3rd full-width'
        ), 
        unsafe_allow_html=True
    )

with tab2:
    st.markdown(f'**{best_or_worst} worstball**')
    st.write(
        worstball_output.to_html(
            index=False,
            justify='left',
            classes='datawrapper-table left-3rd full-width'
        ),
        unsafe_allow_html=True
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