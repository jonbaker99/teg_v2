# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_round_data, get_9_data, get_worst

# Import worst performance helper functions
from helpers.worst_performance_processing import (
    get_performance_measure_titles,
    load_worst_performance_custom_css,
    create_worst_performance_section,
    get_filtered_teg_data
)

# Import display helper functions and CSS -> reuse from records page
from helpers.records_css import load_records_page_css



# === CONFIGURATION ===
st.title("TEG Worsts")

# Page contents navigation
'---'
st.markdown("### Contents")
st.markdown('1. Worst TEGs')
st.markdown('2. Worst Rounds')
st.markdown('3. Worst 9s')
'---'

# Load page-specific CSS styling
load_records_page_css()


# === DATA LOADING ===
# Load TEG data excluding TEG 2 for meaningful worst performance analysis
# Purpose: TEG 2 is considered anomalous and excluded from worst performance comparisons
teg_data = get_filtered_teg_data()

# Load round data for worst round analysis
# Purpose: Provides individual round performance data for worst round identification
round_data = get_round_data()

# Load 9-hole data for worst 9-hole segment analysis  
# Purpose: Enables analysis of worst front/back 9 performances
frontback_data = get_9_data()

# get_performance_measure_titles() - Gets measure title mappings for display
measure_titles = get_performance_measure_titles()


# === USER INTERFACE ===
# Worst TEGs section
st.subheader('Worst TEGs')
for measure in ['GrossVP', 'NetVP', 'Stableford']:
    # get_worst() - Finds worst performance records for specified measure
    worst_records = get_worst(teg_data, measure_to_use=measure, top_n=1)
    
    # create_worst_performance_section() - Creates formatted stat section for display
    stat_section_html = create_worst_performance_section(worst_records, measure, 'teg', measure_titles)
    st.markdown(stat_section_html, unsafe_allow_html=True)

st.caption('Excludes TEG 2')
'---'

# Worst Rounds section
st.subheader('Worst Rounds')
for measure in ['GrossVP', 'Sc', 'NetVP', 'Stableford']:
    # get_worst() - Finds worst round performance records for specified measure
    worst_records = get_worst(round_data, measure_to_use=measure, top_n=1)
    
    # create_worst_performance_section() - Creates formatted stat section for display
    stat_section_html = create_worst_performance_section(worst_records, measure, 'round', measure_titles)
    st.markdown(stat_section_html, unsafe_allow_html=True)

'---'

# Worst 9s section
st.subheader('Worst 9s')
for measure in ['GrossVP', 'Sc', 'NetVP', 'Stableford']:
    # get_worst() - Finds worst 9-hole performance records for specified measure
    worst_records = get_worst(frontback_data, measure_to_use=measure, top_n=1)
    
    # create_worst_performance_section() - Creates formatted stat section for display  
    stat_section_html = create_worst_performance_section(worst_records, measure, 'frontback', measure_titles)
    st.markdown(stat_section_html, unsafe_allow_html=True)