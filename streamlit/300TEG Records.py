# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import get_ranked_teg_data, get_best, get_ranked_round_data, get_ranked_frontback_data, create_stat_section

# Import display helper functions and CSS
# Using helpers/ subdirectory - no conflict with utils.py
from helpers.display_helpers import MEASURE_TITLES, format_record_value, prepare_records_display
from helpers.records_css import load_records_page_css


# === DATA LOADING ===
# Load ranked TEG data (complete TEGs only, excludes TEG 50)
# Purpose: For historical TEG-level records analysis - need complete tournaments only
tegs_ranked = get_ranked_teg_data()

# Load ranked round data (complete TEGs only, excludes TEG 50)  
# Purpose: For round-level records analysis - need complete tournaments for fair comparison
rounds_ranked = get_ranked_round_data()

# Load ranked 9-hole data (complete TEGs only, excludes TEG 50)
# Purpose: For front/back 9 records analysis - need complete tournaments for fair comparison
frontback_ranked = get_ranked_frontback_data()


# === PAGE CONFIGURATION ===
st.title("TEG Records")

# Load page-specific CSS styling
load_records_page_css()

# === PAGE CONTENT STRUCTURE ===

# Page navigation/contents
st.markdown('---')
st.markdown("### Contents")
st.markdown('1. Best TEGs')
st.markdown('2. Best Rounds') 
st.markdown('3. Best 9s')
st.markdown('---')


# === BEST TEG RECORDS SECTION ===
st.subheader('Best TEGs')

# Display best records for each TEG-level measure
for measure in ['GrossVP', 'NetVP', 'Stableford']:
    # get_best() - Extracts top record for specified measure
    best_records = get_best(tegs_ranked, measure_to_use=measure, top_n=1)
    
    # Format the record for display
    title = MEASURE_TITLES[measure]  # "Best Gross", "Best Net", etc.
    value = format_record_value(best_records[measure].iloc[0], measure)
    display_data = prepare_records_display(best_records, 'teg')
    
    # create_stat_section() - Creates formatted HTML display card
    st.markdown(create_stat_section(title, value, display_data, "| "), unsafe_allow_html=True)


# === BEST ROUND RECORDS SECTION ===
st.markdown('---')
st.subheader('Best Rounds')

# Display best records for each round-level measure  
for measure in ['GrossVP', 'Sc', 'NetVP', 'Stableford']:
    # get_best() - Extracts top record for specified measure
    best_records = get_best(rounds_ranked, measure_to_use=measure, top_n=1)
    
    # Format the record for display
    title = MEASURE_TITLES[measure]
    value = format_record_value(best_records[measure].iloc[0], measure) 
    display_data = prepare_records_display(best_records, 'round')
    
    # create_stat_section() - Creates formatted HTML display card
    st.markdown(create_stat_section(title, value, display_data, "| "), unsafe_allow_html=True)


# === BEST 9-HOLE RECORDS SECTION ===
st.markdown('---')
st.subheader('Best 9s')

# Display best records for each 9-hole measure
for measure in ['GrossVP', 'Sc', 'NetVP', 'Stableford']:
    # get_best() - Extracts top record for specified measure  
    best_records = get_best(frontback_ranked, measure_to_use=measure, top_n=1)
    
    # Format the record for display
    title = MEASURE_TITLES[measure]
    value = format_record_value(best_records[measure].iloc[0], measure)
    display_data = prepare_records_display(best_records, 'frontback')
    
    # create_stat_section() - Creates formatted HTML display card  
    st.markdown(create_stat_section(title, value, display_data, "| "), unsafe_allow_html=True)