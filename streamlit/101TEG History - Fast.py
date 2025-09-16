# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import load_datawrapper_css

# Import history-specific helper functions
from helpers.history_data_processing import (
    prepare_complete_history_table_fast,
    load_cached_winners
)


# === CONFIGURATION ===
st.title("TEG History (Fast)")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === PAGE DESCRIPTION ===
st.markdown("TEG locations and winners by year - **Optimized version using cached data**")

# Show performance info
with st.expander("Performance Info"):
    st.write("This page uses pre-computed winners data for fast loading.")
    st.write("Data source: `data/teg_winners.csv`")
    st.write("Falls back to calculation if cache missing.")


# === DATA LOADING (FAST VERSION) ===
# Load cached winners data first
cached_winners = load_cached_winners()

if cached_winners is not None:
    st.success(f"✓ Loaded cached data for {len(cached_winners)} completed TEGs")
else:
    st.warning("⚠️ No cached data found - falling back to calculation")

# Prepare complete history table using cached data
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

# === DEBUG INFO ===
if st.checkbox("Show debug info"):
    st.subheader("Data Structure")
    st.write("Columns:", list(history_display_table.columns))
    st.write("Shape:", history_display_table.shape)

    st.subheader("Raw Data")
    st.dataframe(history_display_table)

    if cached_winners is not None:
        st.subheader("Cached Winners Data")
        st.dataframe(cached_winners)