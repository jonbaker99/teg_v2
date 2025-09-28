import streamlit as st
import pandas as pd
import numpy as np

from utils import (
    load_all_data, 
    datawrapper_table, 
    load_datawrapper_css
)

# Import eclectic calculation functions from utils
from eclectic_utils import calculate_eclectic_by_dimension

# === CONFIGURATION ===
st.title("Eclectic Records")
st.caption("Best eclectic scores by TEG and Course")

load_datawrapper_css()

# === DATA LOADING ===
all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

# === HELPER FUNCTIONS ===
def get_overall_top_eclectics(data, dimension, top_n=3):
    """Get the overall top N eclectics across all players, including ties"""
    all_results = []
    players = sorted(data['Player'].unique())
    
    for player in players:
        player_data = data[data['Player'] == player]
        if player_data.empty:
            continue
            
        eclectics, actual_dimension = calculate_eclectic_by_dimension(player_data, dimension)
        if eclectics.empty:
            continue
            
        eclectics['Player'] = player
        all_results.append(eclectics)
    
    if not all_results:
        return pd.DataFrame()
    
    # Combine all results and get top N including ties
    combined_results = pd.concat(all_results, ignore_index=True)
    combined_results = combined_results.sort_values('Total')
    
    # Get the Nth best score to include all ties
    if len(combined_results) >= top_n:
        nth_score = combined_results.iloc[top_n-1]['Total']
        return combined_results[combined_results['Total'] <= nth_score]
    else:
        return combined_results

def get_personal_best_eclectics(data, dimension):
    """Get each player's best eclectic(s), including ties"""
    all_results = []
    players = sorted(data['Player'].unique())
    
    for player in players:
        player_data = data[data['Player'] == player]
        if player_data.empty:
            continue
            
        eclectics, actual_dimension = calculate_eclectic_by_dimension(player_data, dimension)
        if eclectics.empty:
            continue
            
        # Get all eclectics tied for best score for this player
        best_score = eclectics['Total'].min()
        best_eclectics = eclectics[eclectics['Total'] == best_score]
        best_eclectics['Player'] = player
        all_results.append(best_eclectics)
    
    if not all_results:
        return pd.DataFrame()
    
    return pd.concat(all_results, ignore_index=True).sort_values(['Total', 'Player'])

def format_eclectic_display_table(df):
    """Format eclectics table for display - summary columns only"""
    if df.empty:
        return pd.DataFrame()
    
    # Get the dimension column name (TEG, Course, etc.)
    dimension_col = [col for col in df.columns if col not in ['Player', 'Total', 'Rounds'] and not isinstance(col, int)][0]
    
    # Select only summary columns - no hole-by-hole details
    display_cols = ['Player', dimension_col, 'Total', 'Rounds']
    
    formatted_df = df[display_cols].copy()
    
    # Format numeric columns
    for col in ['Total', 'Rounds']:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].apply(lambda x: int(x) if pd.notna(x) else '-')
    
    return formatted_df

# === MAIN CONTENT ===

tab1, tab2 = st.tabs(["TEGs", "Courses"])

with tab1:
    # st.markdown("### Best TEG Eclectics")
    
    st.markdown("#### Top 3 TEG Eclectics")
    # st.caption("Best 3 TEG eclectics across all players (including ties)")
    
    overall_top_tegs = get_overall_top_eclectics(all_data, 'TEGNum', top_n=3)
    if not overall_top_tegs.empty:
        formatted_top_tegs = format_eclectic_display_table(overall_top_tegs)
        datawrapper_table(formatted_top_tegs, css_classes='left-second bold-3rd')
    else:
        st.warning("No TEG data available.")
    
    st.markdown('')
    st.markdown("#### Personal Best TEGs")
    # st.caption("Each player's best TEG eclectic (including ties)")
    
    pb_tegs = get_personal_best_eclectics(all_data, 'TEGNum')
    if not pb_tegs.empty:
        formatted_pb_tegs = format_eclectic_display_table(pb_tegs)
        datawrapper_table(formatted_pb_tegs, css_classes='left-second bold-3rd')
    else:
        st.warning("No TEG data available.")

with tab2:
    # st.header("Course Eclectics")
    
    st.markdown("#### Top 3 Course Eclectics")
    # st.caption("Best 3 course eclectics across all players (including ties)")
    
    overall_top_courses = get_overall_top_eclectics(all_data, 'Course', top_n=3)
    if not overall_top_courses.empty:
        formatted_top_courses = format_eclectic_display_table(overall_top_courses)
        datawrapper_table(formatted_top_courses, css_classes='left-second bold-3rd')
    else:
        st.warning("No course data available.")
    
    st.markdown("")
    st.markdown("#### Personal Best Course Eclectics")
    # st.caption("Each player's best course eclectic (including ties)")
    
    pb_courses = get_personal_best_eclectics(all_data, 'Course')
    if not pb_courses.empty:
        formatted_pb_courses = format_eclectic_display_table(pb_courses)
        datawrapper_table(formatted_pb_courses, css_classes='left-second bold-3rd')
    else:
        st.warning("No course data available.")

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
add_custom_navigation_links(__file__, layout="horizontal", separator=" | ")