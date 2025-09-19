# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np

# Import data loading functions from main utils
from utils import load_datawrapper_css, load_all_data

# Import streak analysis helper functions
from helpers.streak_analysis_processing import (
    prepare_good_streaks_data,
    prepare_bad_streaks_data,
    prepare_current_good_streaks_data,
    prepare_current_bad_streaks_data
)


# === CONFIGURATION ===
st.title("Streaks")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load streak data
# Purpose: TEG 50 is excluded for accurate streak analysis as it's a special case
all_data = load_all_data(exclude_teg_50=True)


# === USER INTERFACE ===
# Radio button to choose between max and current streaks
streak_type = st.radio(
    "Select streak type:",
    ["Max", "Current"],
    horizontal=True
)

# Create main tab structure for streaks
tab_labels = ["Good Streaks", "Bad Streaks"]
tabs = st.tabs(tab_labels)

# Display streak statistics in tabs
for i, tab in enumerate(tabs):
    with tab:
        if i == 0:
            # Good streaks tab
            if streak_type == "Max":
                # prepare_good_streaks_data() - Combines positive streaks from both regular and inverse calculations
                # This function displays:
                # - Birdies [or better] - consecutive birdies
                # - Pars [or better] - consecutive pars or better
                # - No +2s - consecutive holes better than double bogey
                # - No TBPs - consecutive holes without triple bogey or worse
                good_streaks_summary = prepare_good_streaks_data(all_data)
            else:
                # prepare_current_good_streaks_data() - Shows what good streaks players are currently on
                # This function displays current values for:
                # - Birdies [or better] - current consecutive birdies
                # - Pars [or better] - current consecutive pars or better
                # - No +2s - current consecutive holes better than double bogey
                # - No TBPs - current consecutive holes without triple bogey or worse
                good_streaks_summary = prepare_current_good_streaks_data(all_data)

            # Display good streaks summary table
            st.write(
                good_streaks_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
            st.caption("*: current streak is maximum streak")

        elif i == 1:
            # Bad streaks tab
            if streak_type == "Max":
                # prepare_bad_streaks_data() - Combines negative streaks from both regular and inverse calculations
                # This function displays:
                # - No eagles - consecutive holes without eagles
                # - No birdies - consecutive holes without birdies
                # - Bogey or worse - consecutive holes of bogey or worse
                # - Double Bogey or worse - consecutive holes of double bogey or worse
                # - TBP - consecutive triple bogeys or worse
                bad_streaks_summary = prepare_bad_streaks_data(all_data)
            else:
                # prepare_current_bad_streaks_data() - Shows what bad streaks players are currently on
                # This function displays current values for:
                # - No eagles - current consecutive holes without eagles
                # - No birdies - current consecutive holes without birdies
                # - Bogey or worse - current consecutive holes of bogey or worse
                # - Double Bogey or worse - current consecutive holes of double bogey or worse
                # - TBP - current consecutive triple bogeys or worse
                bad_streaks_summary = prepare_current_bad_streaks_data(all_data)

            # Display bad streaks summary table
            st.write(
                bad_streaks_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
            st.caption("*: current streak is maximum streak")
                