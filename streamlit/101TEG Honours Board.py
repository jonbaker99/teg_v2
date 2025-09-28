# === IMPORTS ===
import streamlit as st
import pandas as pd

# Import data loading functions from main utils
from utils import load_all_data, get_teg_winners, get_trophy_full_name, load_datawrapper_css
from utils_win_tables import summarise_teg_wins, compress_ranges
from utils import add_custom_navigation_links

# Import history-specific helper functions
from helpers.history_data_processing import (
    calculate_trophy_jacket_doubles, 
    get_eagles_data,
    get_holes_in_one_data
)


# === NAVIGATION LINKS ===
# 
# st.markdown("")
# links_html = add_custom_navigation_links(
#     __file__, layout="horizontal", separator=" | ", render=False
# )
# st.markdown(
#     f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
#     unsafe_allow_html=True
# )

# === CONFIGURATION ===
st.title("TEG Honours Board")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load complete TEG data (excludes incomplete TEGs and TEG 50)
# Purpose: Historical analysis requires only completed tournaments for accurate records
# TEG 50 excluded as it's a special case that shouldn't affect historical statistics
all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)

# Load winners data for all completed TEGs
# Purpose: Core dataset showing Trophy, Green Jacket, and Wooden Spoon winners by TEG
winners_with_year = get_teg_winners(all_data)
winners_clean = winners_with_year.drop(columns=['Year'])  # Version without year for processing

# Define competition categories for consistent processing
competitions = ['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']


# === DATA PROCESSING ===
# calculate_trophy_jacket_doubles() - Finds rare Trophy+Green Jacket double winners
# Returns both summary table and total count for display
doubles_table, doubles_count = calculate_trophy_jacket_doubles(winners_clean)


# === HONOURS BOARD ===
# Create tabs for each competition plus doubles, eagles, and holes in one
long_labels = [get_trophy_full_name(comp) for comp in competitions]
all_tabs = st.tabs(long_labels + ["Doubles", "Eagles", "Holes in One"])

# Display summary tables for each competition
for i, (comp, tab) in enumerate(zip(competitions, all_tabs[:3])):
    with tab:
        # summarise_teg_wins() - Creates summary table with win counts and TEG lists
        summary_table = summarise_teg_wins(winners_clean, comp)
        
        # Format TEG names for display (remove 'TEG' prefix, compress ranges)
        summary_table['TEGs'] = summary_table['TEGs'].str.replace('TEG ', '')
        # compress_ranges() - Converts "1,2,3" to "1-3" for cleaner display
        summary_table['TEGs'] = summary_table['TEGs'].apply(compress_ranges, out_sep=", ")
        
        # Display formatted table
        st.write(
            summary_table.to_html(
                index=False, 
                justify='left', 
                classes='datawrapper-table wins-table'
            ), 
            unsafe_allow_html=True
        )
        
        # Add footnote for Green Jacket special case
        if comp == 'Green Jacket':
            st.caption('*Green Jacket awarded in TEG 5 for best stableford round; DM had best gross score')

# Display doubles summary in final tab
with all_tabs[3]:
    st.caption(f"There have been {doubles_count} trophy / jacket doubles")
    st.write(
        doubles_table.to_html(
            index=False, 
            justify='left', 
            classes='datawrapper-table'
        ), 
        unsafe_allow_html=True
    )

# Display Eagles tab
with all_tabs[4]:
    eagles_data = get_eagles_data(all_data)
    if eagles_data.empty:
        st.info("No eagles have been scored on a TEG")
    else:
        st.write(
            eagles_data.to_html(
                index=False, 
                justify='left', 
                classes='datawrapper-table table-left-align'
            ), 
            unsafe_allow_html=True
        )

# Display Holes in One tab
with all_tabs[5]:
    holes_in_one_data = get_holes_in_one_data(all_data)
    if holes_in_one_data.empty:
        st.markdown("No holes in one have been scored on a TEG")
    else:
        st.write(
            holes_in_one_data.to_html(
                index=False, 
                justify='left', 
                classes='datawrapper-table table-left-align'
            ), 
            unsafe_allow_html=True
        )

# Add footnote for historical context
# st.caption('*Green Jacket awarded in TEG 5 for best stableford round; DM had best gross score')

# === NAVIGATION LINKS ===
# from utils import add_custom_navigation_links
# st.markdown("**Related links:**")

st.markdown("")
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)