# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Import data loading functions from main utils
from utils import load_all_data, load_datawrapper_css

# Import streak analysis helper functions
from helpers.streak_analysis_processing import (
    prepare_streak_data_for_display
)


# === CONFIGURATION ===
st.title('Longest Streaks')

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load TEG data excluding TEG 50 for accurate streak analysis
# Purpose: TEG 50 is a special case that shouldn't affect career streak calculations
# Streaks require chronological order across entire career for accurate tracking
all_data = load_all_data(exclude_teg_50=True)


# === USER INTERFACE ===
# prepare_streak_data_for_display() - Calculates consecutive achievements and finds maximum streaks
# This function handles the complete workflow:
# 1. Tracks running streaks for multiple score types (birdies, pars, etc.)
# 2. Uses Career Count to maintain chronological order across all tournaments  
# 3. Summarizes maximum streak length for each player and achievement type
streak_summary = prepare_streak_data_for_display(all_data)

# Display streak summary table
st.write(
    streak_summary.to_html(
        index=False, 
        justify='left', 
        classes='datawrapper-table'
    ), 
    unsafe_allow_html=True
)