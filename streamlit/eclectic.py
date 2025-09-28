import streamlit as st
import pandas as pd
import numpy as np

from utils import (
    load_all_data, 
    datawrapper_table, 
    load_datawrapper_css,
    load_course_info
)

from eclectic_utils import (
    calculate_eclectic_by_dimension,
    format_eclectic_table
)

# === CONFIGURATION ===
st.title("Eclectic Scores")
st.caption("The eclectic score takes the best score on each hole from multiple rounds")

load_datawrapper_css()

# === DATA LOADING ===
all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
course_info = load_course_info()

# === HELPER FUNCTIONS ===
def get_selection_options(all_data, course_info):
    """Get options for dropdowns"""
    players = sorted(all_data['Player'].unique().tolist())
    tegs = sorted(all_data['TEGNum'].unique().tolist(), reverse=True)
    courses = sorted(course_info['Course'].unique().tolist())
    
    return players, tegs, courses

def filter_data_for_eclectic(all_data, selected_player, selected_teg, selected_course):
    """Filter data based on selections"""
    filtered = all_data.copy()
    
    if selected_player != 'All Players':
        filtered = filtered[filtered['Player'] == selected_player]
    
    if selected_teg != 'All TEGs':
        # Extract TEG number from "TEG X" format
        teg_num = int(selected_teg.replace('TEG ', ''))
        filtered = filtered[filtered['TEGNum'] == teg_num]
    
    if selected_course != 'All Courses':
        filtered = filtered[filtered['Course'] == selected_course]
    
    return filtered


# === USER INTERFACE ===
players, tegs, courses = get_selection_options(all_data, course_info)

st.subheader("Selections")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Players**")
    player_options = ['All Players'] + players
    selected_player = st.selectbox("Select Player", player_options, index=0)

with col2:
    st.markdown("**TEGs**")
    teg_options = ['All TEGs'] + [f'TEG {teg}' for teg in tegs]
    selected_teg = st.selectbox("Select TEG", teg_options, index=0)

with col3:
    st.markdown("**Courses**")
    course_options = ['All Courses'] + courses
    selected_course = st.selectbox("Select Course", course_options, index=0)

st.subheader("Comparison")

# Determine which options are available based on selections
player_enabled = selected_player == 'All Players'
teg_enabled = selected_teg == 'All TEGs'
course_enabled = selected_course == 'All Courses'

# Build options in fixed order - always show all options
all_display_options = ["Player", "TEG", "Course", "Heroes vs. Wildcats", "Combined"]

# Map all options - available ones plus single selections
option_mapping = {}

# Player option: available if "All Players" OR if specific player selected
if player_enabled or selected_player != 'All Players':
    option_mapping["Player"] = "Player"

# TEG option: available if "All TEGs" OR if specific TEG selected  
if teg_enabled or selected_teg != 'All TEGs':
    option_mapping["TEG"] = "TEGNum"

# Course option: available if "All Courses" OR if specific course selected
if course_enabled or selected_course != 'All Courses':
    option_mapping["Course"] = "Course"

# Teams and Combined options are always available
option_mapping["Heroes vs. Wildcats"] = "Teams"
option_mapping["Combined"] = "Combined"

# Check if any options are available
available_options = list(option_mapping.keys())

if available_options:
    selected_option = st.radio(
        "Compare eclectics by:",
        all_display_options,
        horizontal=True,
        help="Choose what to compare - each row will show the eclectic for one Player/TEG/Course"
    )
    
    # Map back to the actual dimension
    if selected_option in option_mapping:
        comparison_dimension = option_mapping[selected_option]
    else:
        comparison_dimension = None
else:
    st.radio(
        "Compare eclectics by:",
        all_display_options,
        horizontal=True,
        disabled=True,
        help="Select 'All' in at least one dropdown above to enable comparison"
    )
    comparison_dimension = None


# === CALCULATIONS ===
filtered_data = filter_data_for_eclectic(all_data, selected_player, selected_teg, selected_course)

if filtered_data.empty:
    st.warning("No data matches your selections. Please adjust your filters.")
elif comparison_dimension is None:
    st.info("Select comparison options above to view eclectic scores.")
else:
    eclectic_results, actual_dimension = calculate_eclectic_by_dimension(filtered_data, comparison_dimension)
    
    if eclectic_results.empty:
        st.warning("No eclectic scores could be calculated with your selections.")
    else:
        formatted_results = format_eclectic_table(eclectic_results, actual_dimension)
        
        st.subheader("Eclectic Scores")
        
        # Show summary info
        total_rounds = len(filtered_data.groupby(['Player', 'TEGNum', 'Round']))
        st.caption(f"Based on {total_rounds} rounds from your selections")
        
        # Display table
        datawrapper_table(formatted_results, css_classes='full-width eclectic bold-2nd')

# === NAVIGATION LINKS ===
from utils import add_navigation_links
add_navigation_links(__file__)