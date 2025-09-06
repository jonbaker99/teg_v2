# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_ranked_teg_data, load_datawrapper_css

# Import latest round/TEG helper functions (shared helper file)
from helpers.latest_round_processing import (
    get_round_metric_mappings,
    initialize_teg_selection_state,
    update_teg_session_state_defaults,
    create_teg_selection_reset_function,
    get_teg_options,
    create_metric_tabs_data,
    prepare_teg_context_display
)


# === CONFIGURATION ===
st.subheader("TEG context")
st.markdown('Shows how latest or selected TEG compares to other TEGs')

# Load CSS styling for consistent table appearance
load_datawrapper_css()

# initialize_teg_selection_state() - Sets up session state for TEG selection
initialize_teg_selection_state()


# === DATA LOADING ===
# Load ranked TEG data for context analysis
# Purpose: Provides ranking context to show how selected TEG compares to all other TEGs
df_teg = get_ranked_teg_data().sort_values(by='TEGNum')

# update_teg_session_state_defaults() - Sets session state to latest TEG if not initialized
update_teg_session_state_defaults(df_teg)

# create_teg_selection_reset_function() - Creates callback for "Latest TEG" button
reset_teg_selection = create_teg_selection_reset_function(df_teg)


# === USER INTERFACE ===
# TEG selection controls
col1, col2 = st.columns(2)

with col1:
    # get_teg_options() - Gets available TEG options
    teg_options = get_teg_options(df_teg)
    teg_index = teg_options.index(st.session_state.teg_t)
    teg_t = st.selectbox("Select TEG", options=teg_options, index=teg_index, key='teg_t_select')
    st.session_state.teg_t = teg_t

with col2:
    st.button("Latest TEG", on_click=reset_teg_selection)

# Metric tabs setup
metrics = ['Sc', 'Stableford', 'GrossVP', 'NetVP']

# create_metric_tabs_data() - Prepares metric names and friendly labels for tabs
metrics, friendly_metrics = create_metric_tabs_data(metrics)
tabs = st.tabs(friendly_metrics)

# get_round_metric_mappings() - Gets mapping for metric name conversion
name_mapping, inverted_name_mapping = get_round_metric_mappings()

# Display metric-specific analysis in each tab
for tab, friendly_metric in zip(tabs, friendly_metrics):
    with tab:
        st.markdown(f"#### {friendly_metric}")
        
        # Convert friendly name back to internal metric name
        metric = name_mapping.get(friendly_metric, friendly_metric)
        
        # prepare_teg_context_display() - Creates context table for selected TEG
        context_display = prepare_teg_context_display(df_teg, teg_t, metric, friendly_metric)
        st.write(
            context_display.to_html(
                index=False, 
                justify='left', 
                classes='jb-table-test, datawrapper-table full-width'
            ), 
            unsafe_allow_html=True
        )
