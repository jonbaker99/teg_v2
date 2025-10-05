# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import load_all_data, get_teg_winners, load_datawrapper_css

# Import history-specific helper functions
from helpers.history_data_processing import (
    prepare_complete_history_table
)


# === CONFIGURATION ===
st.title("TEG History")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === PAGE DESCRIPTION ===
st.markdown("TEG locations and winners by year")


# === DATA LOADING ===
# Load complete TEG data (excludes incomplete TEGs and TEG 50)
# Purpose: Historical analysis requires only completed tournaments for accurate records
# TEG 50 excluded as it's a special case that shouldn't affect historical statistics
all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)

# Load winners data for all completed TEGs
# Purpose: Core dataset showing Trophy, Green Jacket, and Wooden Spoon winners by TEG
winners_with_year = get_teg_winners(all_data)

# === DATA PROCESSING ===
# prepare_complete_history_table() - Creates comprehensive history including TBC entries
# Includes completed TEGs with winners, plus incomplete/future TEGs with TBC
history_display_table = prepare_complete_history_table(winners_with_year)


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