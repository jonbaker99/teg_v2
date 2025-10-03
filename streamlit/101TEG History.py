"""Streamlit page for displaying the complete history of TEG winners.

This page provides a comprehensive overview of all TEG events, including past
winners, in-progress tournaments, and future planned events. It displays a
summary table with the winners of the "TEG Trophy," "Green Jacket," and "HMM
Wooden Spoon" for each TEG.

The page uses helper functions to:
- Load cached winner data for fast performance.
- Automatically calculate and display winners for any completed TEGs that are
  missing from the cache.
- Provide an option to save newly calculated winners to the cache.
- Display a complete history table including completed, in-progress, and
  future TEGs.
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import load_datawrapper_css

# Import history-specific helper functions
from helpers.history_data_processing import (
    prepare_complete_history_table_fast,
    load_cached_winners,
    calculate_and_save_missing_winners
)


# === CONFIGURATION ===
st.title("TEG History")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === PAGE DESCRIPTION ===
st.markdown("TEG locations and winners by year")


# === DATA LOADING ===
# Load cached winners with missing ones calculated automatically
cached_winners, missing_teg_nums = load_cached_winners()

# Prepare complete history table using combined data
history_display_table = prepare_complete_history_table_fast(cached_winners)


# === TEG HISTORY TABLE ===
# Format display table with area information
h_tab_3 = history_display_table.copy()
history_display_table['Area'] = history_display_table['Area'].str.split(",").str[0].str.strip()

h_tab_3['Area'] = history_display_table['Area']
h_tab_3["TEG"] = (
    "<span class='teg-label'>" + h_tab_3["TEG"].astype(str) + "</span>"
    "<span class='area-label'>" + h_tab_3["Area"].astype(str) + "</span>"
)
cols = ["TEG", "TEG Trophy", "Green Jacket", "HMM Wooden Spoon"]

# Display complete historical table with all winners by TEG
st.write(
    h_tab_3[cols].to_html(
        index=False,
        justify="left",
        classes="datawrapper-table history-table full-width hist2",
        escape=False   # important so spans render
    ),
    unsafe_allow_html=True
)

# Add footnote for historical context
st.caption('*Green Jacket awarded in TEG 5 for best stableford round; DM had best gross score')

# Display save prompt below table if there are calculated winners
if missing_teg_nums:
    st.markdown("---")
    st.info(f"📊 Winners calculated for TEGs {sorted(missing_teg_nums)} are shown above but not yet saved to cache.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Calculated Winners to Cache"):
            with st.spinner("Saving winners to cache..."):
                calculate_and_save_missing_winners(missing_teg_nums)
            st.success("Winners saved! Page will refresh automatically.")
            st.rerun()

    with col2:
        st.caption("Or use the data update process to refresh all winner information.")

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

