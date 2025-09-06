# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np

# Import data loading functions from main utils
from utils import get_ranked_teg_data, get_ranked_round_data, load_datawrapper_css

# Import best performance helper functions
from helpers.best_performance_processing import (
    get_measure_name_mappings,
    prepare_best_teg_table,
    prepare_best_round_table,
    prepare_round_data_with_identifiers
)


# === CONFIGURATION ===
st.title('Top TEGs and Rounds')

# Load CSS styling for consistent table appearance
load_datawrapper_css()

# Set default number of records to display
DEFAULT_TOP_N = 3


# === DATA LOADING ===
# Load ranked TEG performance data for all competitions
# Purpose: Provides tournament-level performance rankings across all scoring measures
teg_data_ranked = get_ranked_teg_data()

# Load ranked round performance data for individual round analysis
# Purpose: Enables analysis of best individual round performances across all players
rd_data_ranked = get_ranked_round_data()

# prepare_round_data_with_identifiers() - Adds TEG|Round format for cleaner display
rd_data_formatted = prepare_round_data_with_identifiers(rd_data_ranked)


# === USER INTERFACE ===
# get_measure_name_mappings() - Gets user-friendly names and internal measure mappings
name_mapping, inverted_name_mapping = get_measure_name_mappings()
friendly_names = list(name_mapping.keys())

# Measure selection radio buttons
selected_friendly_name = st.radio("Choose a measure:", friendly_names, horizontal=True)
selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)

# Number of results to show
n_keep = st.number_input(
    "Number of TEGs / Rounds to show",
    min_value=1,
    max_value=100,
    value=DEFAULT_TOP_N,
    step=1
)

# prepare_best_teg_table() - Creates formatted table of top TEG performances
best_tegs_table = prepare_best_teg_table(teg_data_ranked, selected_measure, selected_friendly_name, n_keep)

# prepare_best_round_table() - Creates formatted table of top round performances  
best_rounds_table = prepare_best_round_table(rd_data_formatted, selected_measure, selected_friendly_name, n_keep)

# Display results in tabs
tab1, tab2 = st.tabs(["Best TEGs", "Best Rounds"])

with tab1:
    st.markdown(f'### Top {n_keep} TEGs: {selected_friendly_name}')
    st.write(
        best_tegs_table.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second'
        ), 
        unsafe_allow_html=True
    )

with tab2:
    st.markdown(f'### Top {n_keep} Rounds: {selected_friendly_name}')
    st.write(
        best_rounds_table.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second'
        ), 
        unsafe_allow_html=True
    )