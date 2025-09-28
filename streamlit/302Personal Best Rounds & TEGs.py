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
    prepare_round_data_with_identifiers,
    prepare_pb_teg_summary_table,
    prepare_pb_round_summary_table
)


# === CONFIGURATION ===
st.title('Personal Bests & Worsts')

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

# Prepare summary tables
pb_teg_summary = prepare_pb_teg_summary_table(teg_data_ranked)
pb_round_summary = prepare_pb_round_summary_table(rd_data_ranked)


# === USER INTERFACE ===
# get_measure_name_mappings() - Gets user-friendly names and internal measure mappings
name_mapping, inverted_name_mapping = get_measure_name_mappings()
friendly_names = list(name_mapping.keys())

# Initialize session state for selected measure if not already set
# Also handle migration from old column names to new ones
if 'selected_measure' not in st.session_state:
    st.session_state.selected_measure = friendly_names[0]  # Default to first measure
elif st.session_state.selected_measure not in friendly_names:
    # Handle migration from old names
    name_migration = {'Gross vs Par': 'Gross', 'Net vs Par': 'Net'}
    if st.session_state.selected_measure in name_migration:
        st.session_state.selected_measure = name_migration[st.session_state.selected_measure]
    else:
        st.session_state.selected_measure = friendly_names[0]  # Default to first measure

# Display tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["PB Summary", "Best TEGs", "Best Rounds", "Worst TEGs", "Worst Rounds"])

with tab1:
    # Create subtabs within PB Summary
    pb_rounds_tab, pb_tegs_tab = st.tabs(["Best Rounds", "Best TEGs"])

    with pb_rounds_tab:
        st.markdown('#### Personal Best Rounds')
        # st.markdown('Each player\'s best performance across all four measures for individual rounds.')
        st.write(
            pb_round_summary.to_html(
                escape=False,
                index=False,
                justify='left',
                classes='datawrapper-table table-left-align pb-table'
            ),
            unsafe_allow_html=True
        )

    with pb_tegs_tab:
        st.markdown('#### Personal Best TEGs')
        # st.markdown('Each player\'s best performance across all four measures for complete TEGs.')
        st.write(
            pb_teg_summary.to_html(
                escape=False,
                index=False,
                justify='left',
                classes='datawrapper-table table-left-align pb-table'
            ),
            unsafe_allow_html=True
        )

# Tabs with measure selection that syncs across all tabs
with tab2:
    # Radio button that updates session state
    selected_friendly_name = st.radio(
        "Choose a measure:", 
        friendly_names, 
        horizontal=True, 
        key="best_tegs_radio",
        index=friendly_names.index(st.session_state.selected_measure)
    )
    
    # Update session state when radio button changes
    if selected_friendly_name != st.session_state.selected_measure:
        st.session_state.selected_measure = selected_friendly_name
        st.rerun()
    
    selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
    personal_best_tegs = prepare_personal_best_teg_table(teg_data_ranked, selected_measure, selected_friendly_name)
    
    st.markdown(f'### Personal Best TEGs: {selected_friendly_name}')
    st.write(
        personal_best_tegs.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second left-4th left-5th'
        ), 
        unsafe_allow_html=True
    )

with tab3:
    # Radio button that syncs with session state
    selected_friendly_name = st.radio(
        "Choose a measure:", 
        friendly_names, 
        horizontal=True, 
        key="best_rounds_radio",
        index=friendly_names.index(st.session_state.selected_measure)
    )
    
    # Update session state when radio button changes
    if selected_friendly_name != st.session_state.selected_measure:
        st.session_state.selected_measure = selected_friendly_name
        st.rerun()
    
    selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
    personal_best_rounds = prepare_personal_best_round_table(rd_data_formatted, selected_measure, selected_friendly_name)
    
    st.markdown(f'### Personal Best Rounds: {selected_friendly_name}')
    st.write(
        personal_best_rounds.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second left-4th left-5th'
        ), 
        unsafe_allow_html=True
    )

with tab4:
    # Radio button that syncs with session state
    selected_friendly_name = st.radio(
        "Choose a measure:", 
        friendly_names, 
        horizontal=True, 
        key="worst_tegs_radio",
        index=friendly_names.index(st.session_state.selected_measure)
    )
    
    # Update session state when radio button changes
    if selected_friendly_name != st.session_state.selected_measure:
        st.session_state.selected_measure = selected_friendly_name
        st.rerun()
    
    selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
    personal_worst_tegs = prepare_personal_worst_teg_table(teg_data_ranked, selected_measure, selected_friendly_name)
    
    st.markdown(f'### Personal Worst TEGs: {selected_friendly_name}')
    st.write(
        personal_worst_tegs.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second left-4th left-5th'
        ), 
        unsafe_allow_html=True
    )

with tab5:
    # Radio button that syncs with session state
    selected_friendly_name = st.radio(
        "Choose a measure:", 
        friendly_names, 
        horizontal=True, 
        key="worst_rounds_radio",
        index=friendly_names.index(st.session_state.selected_measure)
    )
    
    # Update session state when radio button changes
    if selected_friendly_name != st.session_state.selected_measure:
        st.session_state.selected_measure = selected_friendly_name
        st.rerun()
    
    selected_measure = name_mapping.get(selected_friendly_name, selected_friendly_name)
    personal_worst_rounds = prepare_personal_worst_round_table(rd_data_formatted, selected_measure, selected_friendly_name)
    
    st.markdown(f'### Personal Worst Rounds: {selected_friendly_name}')
    st.write(
        personal_worst_rounds.to_html(
            escape=False, 
            index=False, 
            justify='left', 
            classes='datawrapper-table narrow-first left-second left-4th left-5th'
        ), 
        unsafe_allow_html=True
    )

# Add note about TEG 2 exclusion
st.caption("Note: TEG 2 is excluded from all TEG-level analysis as it only had 3 rounds compared to the standard 4 rounds.")

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)