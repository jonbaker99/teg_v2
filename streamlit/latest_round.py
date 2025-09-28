# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_ranked_round_data, load_all_data, load_datawrapper_css
from make_charts import create_round_graph

# Import latest round helper functions
from helpers.latest_round_processing import (
    get_round_metric_mappings,
    initialize_round_selection_state,
    update_session_state_defaults,
    create_round_selection_reset_function,
    get_teg_and_round_options,
    create_metric_tabs_data,
    prepare_round_context_display
)


# === CONFIGURATION ===
st.subheader("Chosen Round in context")
st.markdown('Shows how latest or selected rounds and TEGs compare to other rounds')

# Load CSS styling for consistent table appearance
load_datawrapper_css()

# initialize_round_selection_state() - Sets up session state for TEG/round selection
initialize_round_selection_state()


# === DATA LOADING ===
# Load ranked round data for context analysis
# Purpose: Provides ranking context to show how selected rounds compare to all other rounds
df_round = get_ranked_round_data()
df_round = df_round.sort_values(by=['TEGNum', 'Round'])

# Load all data including incomplete TEGs for cumulative charts
# Purpose: Round analysis benefits from current tournament data for up-to-date context
all_data = load_all_data(exclude_incomplete_tegs=False)

# update_session_state_defaults() - Sets session state to latest round if not initialized
update_session_state_defaults(df_round)

# create_round_selection_reset_function() - Creates callback for "Latest Round" button
reset_round_selection = create_round_selection_reset_function(df_round)


# === USER INTERFACE ===
# Round selection controls
col1, col2, col3 = st.columns(3)

with col1:
    # get_teg_and_round_options() - Gets available TEG options
    teg_options, _ = get_teg_and_round_options(df_round, st.session_state.teg_r)
    teg_index = teg_options.index(st.session_state.teg_r)
    teg_r = st.selectbox("Select TEG (Round)", options=teg_options, index=teg_index, key='teg_r_select')
    st.session_state.teg_r = teg_r

with col2:
    # get_teg_and_round_options() - Gets available round options for selected TEG
    _, round_options = get_teg_and_round_options(df_round, teg_r)
    rd_index = round_options.index(st.session_state.rd_r) if st.session_state.rd_r in round_options else 0
    rd_r = st.selectbox("Select Round", options=round_options, index=rd_index, key='rd_r_select')
    st.session_state.rd_r = rd_r

with col3:
    st.button("Latest Round", on_click=reset_round_selection)

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
        
        # prepare_round_context_display() - Creates context table for selected round
        context_display = prepare_round_context_display(df_round, teg_r, rd_r, metric, friendly_metric)
        st.write(
            context_display.to_html(
                index=False, 
                justify='left', 
                classes='jb-table-test, datawrapper-table'
            ), 
            unsafe_allow_html=True
        )

        # create_round_graph() - Creates cumulative performance chart through selected round
        st.markdown(f"#### Cumulative {friendly_metric} through round")
        cum_metric = f'{metric} Cum Round'
        fig_rd = create_round_graph(
            all_data, 
            chosen_teg=teg_r, 
            chosen_round=rd_r, 
            y_series=cum_metric,
            title=friendly_metric,
            y_axis_label=f'Cumulative {friendly_metric}'
        )
        st.plotly_chart(fig_rd, use_container_width=True, config=dict({'displayModeBar': False}))

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