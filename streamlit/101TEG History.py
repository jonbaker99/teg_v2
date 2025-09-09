# === IMPORTS ===
import streamlit as st
import pandas as pd
import altair as alt

# Import data loading functions from main utils
from utils import load_all_data, get_teg_winners, get_trophy_full_name, load_datawrapper_css
from utils_win_tables import summarise_teg_wins, compress_ranges

# Import history-specific helper functions
from helpers.history_data_processing import (
    process_winners_for_charts,
    calculate_trophy_jacket_doubles, 
    prepare_history_table_display,
    create_bar_chart
)


# === CONFIGURATION ===
st.title("TEG History")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === PAGE NAVIGATION ===
st.markdown('---')
st.markdown("#### Contents")
st.markdown('1. TEG Honours Board')
st.markdown('2. Winners by TEG')
st.markdown('---')


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
# process_winners_for_charts() - Transforms raw winners into chart-ready format
# Returns sorted datasets for each competition and scaling information
chart_data = process_winners_for_charts(winners_clean)

# calculate_trophy_jacket_doubles() - Finds rare Trophy+Green Jacket double winners
# Returns both summary table and total count for display
doubles_table, doubles_count = calculate_trophy_jacket_doubles(winners_clean)

# prepare_history_table_display() - Creates compact historical table format
# Combines TEG name and year for cleaner display
history_display_table = prepare_history_table_display(winners_with_year)


# === SECTION 1: WINS BY PLAYER ===
st.markdown("#### TEG Honours Board")

# Create tabs for each competition plus doubles
long_labels = [get_trophy_full_name(comp) for comp in competitions]
all_tabs = st.tabs(long_labels + ["Doubles"])

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

st.divider()


# === SECTION 2: TEG HISTORY TABLE ===
st.markdown("#### Winners by TEG")


# history_display_table_2 = history_display_table.copy()
h_tab_3 = history_display_table.copy()
history_display_table['Area'] =  history_display_table['Area'].str.split(",").str[0].str.strip()

# Display complete historical table with all winners by TEG
# st.write(
#     history_display_table.to_html(
#         index=False, 
#         justify='left', 
#         classes='datawrapper-table history-table full-width'
#     ), 
#     unsafe_allow_html=True
# )

# history_display_table_2['Area'] =  history_display_table_2['Area'].str.split(",").str[0].str.strip()
# history_display_table_2["TEG"] = history_display_table_2['TEG'] + "<br>" + history_display_table_2['Area']
# history_display_table_2 = history_display_table_2.drop(columns=['Area'])

# st.write(
#     history_display_table_2.to_html(
#         index=False, 
#         classes='datawrapper-table history-table full-width',
#         escape=False
#     ), 
#     unsafe_allow_html=True
# )


h_tab_3['Area'] = history_display_table['Area']
h_tab_3["TEG"] = (
    "<span class='teg-label'>" + h_tab_3["TEG"].astype(str) + "</span>"
    "<span class='area-label'>" + h_tab_3["Area"].astype(str) + "</span>"
)
cols = ["TEG", "TEG Trophy", "Green Jacket", "HMM Wooden Spoon"]

st.write(
    h_tab_3[cols].to_html(
        index=False,
        justify="left",
        classes="datawrapper-table history-table full-width hist2",
        escape=False   # important so spans render
    ),
    unsafe_allow_html=True
)



# #reset teg col
# h_tab_3["TEG"] = history_display_table['TEG']
# # Extract inside the parentheses (the year)
# h_tab_3["Year"] = h_tab_3["TEG"].str.extract(r'\((\d{4})\)')
# # Extract before the parentheses
# h_tab_3["TEG"] = h_tab_3["TEG"].str.extract(r'^(.*?)\s*\(')

# h_tab_3["TEG"] = (
#     "<span class='teg-label'>" + h_tab_3["TEG"].astype(str) + "</span>"
#     "<span class='area-label'>" + h_tab_3["Area"].astype(str) + "," + h_tab_3['Year'].astype(str) + "</span>"
#     # "<span class='area-label'>" + h_tab_3["Area"].astype(str) + "</span>"
# )

# st.write(
#     h_tab_3[cols].to_html(
#         index=False,
#         justify="left",
#         classes="datawrapper-table history-table full-width hist2",
#         escape=False   # important so spans render
#     ),
#     unsafe_allow_html=True
# )




# Add footnote for historical context
st.caption('*Green Jacket awarded in TEG 5 for best stableford round; DM had best gross score')

st.divider()