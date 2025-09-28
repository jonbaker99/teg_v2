# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Import data loading functions from main utils
from utils import load_all_data, load_datawrapper_css, get_teg_filter_options, filter_data_by_teg

# Import par analysis helper functions
from helpers.par_analysis_processing import (
    calculate_par_performance_matrix,
    format_par_performance_table
)


# === CONFIGURATION ===
st.title('Average score by Par')

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load all TEG data including incomplete tournaments for current analysis
# Purpose: Par analysis benefits from including current tournament data for up-to-date performance
all_data = load_all_data(exclude_incomplete_tegs=False)

# get_teg_filter_options() - Creates TEG dropdown options including "All TEGs"
tegnum_options = get_teg_filter_options(all_data)


# === USER INTERFACE ===
# TEG filtering selection
selected_tegnum = st.selectbox('Select TEG', tegnum_options, index=0)

# filter_data_by_teg() - Applies TEG filter to tournament data
filtered_data = filter_data_by_teg(all_data, selected_tegnum)

# calculate_par_performance_matrix() - Creates player-by-par performance matrix
par_performance_matrix = calculate_par_performance_matrix(filtered_data)

# format_par_performance_table() - Formats table with vs-par notation and column names
formatted_par_table = format_par_performance_table(par_performance_matrix)

# Display formatted performance table
st.write(
    formatted_par_table.to_html(
        classes='dataframe, datawrapper-table full-width', 
        index=False, 
        justify='left'
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