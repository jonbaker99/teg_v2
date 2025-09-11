# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np

# Import data loading functions from main utils
from utils import get_ranked_teg_data, get_ranked_round_data, load_datawrapper_css

# Import personal best performance helper functions
from helpers.best_performance_processing import (
    get_measure_name_mappings,
    prepare_personal_best_teg_table,
    prepare_personal_best_round_table,
    prepare_personal_worst_teg_table,
    prepare_personal_worst_round_table,
    prepare_round_data_with_identifiers
)


# === CONFIGURATION ===
st.title('Personal Best and Worst TEGs and Rounds')

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load ranked TEG performance data for personal best analysis
# Purpose: Provides tournament-level performance rankings to find each player's best TEG
teg_data_ranked = get_ranked_teg_data()

# Load ranked round performance data for personal best round analysis
# Purpose: Enables finding each player's best individual round performance
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

# prepare_personal_best_teg_table() - Creates table with each player's best TEG performance
personal_best_tegs = prepare_personal_best_teg_table(teg_data_ranked, selected_measure, selected_friendly_name)

# prepare_personal_best_round_table() - Creates table with each player's best round performance
personal_best_rounds = prepare_personal_best_round_table(rd_data_formatted, selected_measure, selected_friendly_name)

# prepare_personal_worst_teg_table() - Creates table with each player's worst TEG performance
personal_worst_tegs = prepare_personal_worst_teg_table(teg_data_ranked, selected_measure, selected_friendly_name)

# prepare_personal_worst_round_table() - Creates table with each player's worst round performance
personal_worst_rounds = prepare_personal_worst_round_table(rd_data_formatted, selected_measure, selected_friendly_name)

# Display results in tabs
tab1, tab2, tab3, tab4 = st.tabs(["Best TEGs", "Best Rounds", "Worst TEGs", "Worst Rounds"])

with tab1:
    st.markdown(f'### Personal Best TEGs: {selected_friendly_name}')
    st.write(
        personal_best_tegs.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second'
        ), 
        unsafe_allow_html=True
    )

with tab2:
    st.markdown(f'### Personal Best Rounds: {selected_friendly_name}')
    st.write(
        personal_best_rounds.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second'
        ), 
        unsafe_allow_html=True
    )

with tab3:
    st.markdown(f'### Personal Worst TEGs: {selected_friendly_name}')
    st.write(
        personal_worst_tegs.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second'
        ), 
        unsafe_allow_html=True
    )

with tab4:
    st.markdown(f'### Personal Worst Rounds: {selected_friendly_name}')
    st.write(
        personal_worst_rounds.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second'
        ), 
        unsafe_allow_html=True
    )

# Add note about TEG 2 exclusion
st.caption("Note: TEG 2 is excluded from all TEG-level analysis as it only had 3 rounds compared to the standard 4 rounds.")