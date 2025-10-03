"""Streamlit page for analyzing player performance by course.

This page provides a detailed analysis of player performance by course,
allowing users to filter by geographical area and view various statistics,
including course records, averages, and best/worst performances.

The page uses helper functions to:
- Load and filter the data.
- Calculate and format performance metrics.
- Display the data in clear, readable tables.
"""
# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Import data loading functions from main utils
from utils import get_round_data, load_course_info, load_datawrapper_css, datawrapper_table

# Import course analysis helper functions
from helpers.course_analysis_processing import (
    prepare_area_filter_options,
    filter_data_by_area,
    calculate_course_round_counts,
    create_course_performance_table,
    create_course_summary_table
)


# === CONFIGURATION ===
st.title('Course averages and records')

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load round data excluding TEG 50 but including incomplete TEGs for current analysis
# Purpose: Course analysis benefits from including current tournament data for up-to-date averages
all_rd_data = get_round_data(ex_50=True, ex_incomplete=False)

# Load course information for area filtering
# Purpose: Enables geographical analysis by grouping courses into regions/areas
course_info = load_course_info()

# prepare_area_filter_options() - Creates area dropdown options including "ALL AREAS"
area_options, all_area_label = prepare_area_filter_options(course_info)


# === USER INTERFACE ===
# Area filtering selection
selected_area = st.selectbox('Filter by area:', area_options)

# filter_data_by_area() - Applies geographical filter to round data
filtered_rd_data = filter_data_by_area(all_rd_data, course_info, selected_area, all_area_label)

# calculate_course_round_counts() - Counts rounds played at each course
course_count = calculate_course_round_counts(filtered_rd_data)

# create_course_performance_table() - Creates formatted performance matrices
# Average performance by course and player
mean_course_data = create_course_performance_table(filtered_rd_data, 'mean')

# Best performance by course and player  
min_course_data = create_course_performance_table(filtered_rd_data, 'min')

# Worst performance by course and player
max_course_data = create_course_performance_table(filtered_rd_data, 'max')

# create_course_summary_table() - Combines key statistics for overview
course_summary = create_course_summary_table(course_count, mean_course_data, min_course_data, max_course_data)

# Create course records table - showing best score for each course with ties
def create_course_records_table(filtered_data):
    records_data = []

    for course in filtered_data['Course'].unique():
        course_data = filtered_data[filtered_data['Course'] == course]
        min_score = course_data['Sc'].min()

        best_rounds = course_data[course_data['Sc'] == min_score]

        for _, round_data in best_rounds.iterrows():
            # Combine Score + Gross v Par
            gross_v_par = f"+{int(round_data['GrossVP'])}" if round_data['GrossVP'] > 0 else str(int(round_data['GrossVP']))
            combined_score = f"{int(round_data['Sc'])} ({gross_v_par})"

            # Combine TEG + Round
            teg_round = f"{round_data['TEG']} R{int(round_data['Round'])}"

            records_data.append({
                'Course': course,
                'Score': combined_score,
                'Player': round_data['Player'],
                'Date': round_data['Date'],
                'TEG / Round': teg_round
            })

    records_df = pd.DataFrame(records_data)
    # Sort by Score (numeric part) ascending, then by Date ascending
    records_df['_sort_score'] = records_df['Score'].str.extract('(\d+)').astype(int)
    records_df = records_df.sort_values(['_sort_score', 'Date'])
    records_df = records_df.drop('_sort_score', axis=1)

    return records_df

# Create net course records table - showing best net vs par for each course with ties
def create_net_course_records_table(filtered_data):
    records_data = []

    for course in filtered_data['Course'].unique():
        course_data = filtered_data[filtered_data['Course'] == course]
        min_net_vp = course_data['NetVP'].min()

        best_rounds = course_data[course_data['NetVP'] == min_net_vp]

        for _, round_data in best_rounds.iterrows():
            # Format Net v Par
            net_v_par = f"+{int(round_data['NetVP'])}" if round_data['NetVP'] > 0 else str(int(round_data['NetVP']))

            # Combine TEG + Round
            teg_round = f"{round_data['TEG']} R{int(round_data['Round'])}"

            records_data.append({
                'Course': course,
                'Net vs Par': net_v_par,
                'Player': round_data['Player'],
                'Date': round_data['Date'],
                'TEG / Round': teg_round
            })

    records_df = pd.DataFrame(records_data)
    # Sort by Net vs Par ascending, then by Date ascending
    records_df['_sort_score'] = records_df['Net vs Par'].str.replace('+', '').astype(int)
    records_df = records_df.sort_values(['_sort_score', 'Date'])
    records_df = records_df.drop('_sort_score', axis=1)

    return records_df

# Create course records summary table - showing how many courses each player holds records for
def create_course_records_summary(filtered_data):
    player_courses = {}

    for course in filtered_data['Course'].unique():
        course_data = filtered_data[filtered_data['Course'] == course]
        min_score = course_data['Sc'].min()

        # Get all players who achieved the minimum score on this course
        record_holders = course_data[course_data['Sc'] == min_score]['Player'].unique()

        for player in record_holders:
            if player not in player_courses:
                player_courses[player] = set()
            player_courses[player].add(course)

    # Convert to DataFrame
    summary_data = []
    for player, courses in player_courses.items():
        summary_data.append({
            'Player': player,
            'Records held': len(courses)
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values(['Records held', 'Player'], ascending=[False, True])

    return summary_df

# Create net course records summary table - showing how many net courses each player holds records for
def create_net_course_records_summary(filtered_data):
    player_courses = {}

    for course in filtered_data['Course'].unique():
        course_data = filtered_data[filtered_data['Course'] == course]
        min_net_vp = course_data['NetVP'].min()

        # Get all players who achieved the minimum net vs par on this course
        record_holders = course_data[course_data['NetVP'] == min_net_vp]['Player'].unique()

        for player in record_holders:
            if player not in player_courses:
                player_courses[player] = set()
            player_courses[player].add(course)

    # Convert to DataFrame
    summary_data = []
    for player, courses in player_courses.items():
        summary_data.append({
            'Player': player,
            'Net Records held': len(courses)
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values(['Net Records held', 'Player'], ascending=[False, True])

    return summary_df

course_records = create_course_records_table(filtered_rd_data)
course_records_summary = create_course_records_summary(filtered_rd_data)
net_course_records = create_net_course_records_table(filtered_rd_data)
net_course_records_summary = create_net_course_records_summary(filtered_rd_data)

# Display results in tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Course Records", "Net Records", "Summary by course", "Averages", "Bests", "Worsts"])

with tab1:
    st.markdown("**Course Records (Gross)**")
    datawrapper_table(course_records, css_classes='full-width table-left-align')

    st.divider()

    st.markdown("**Summary by Player**")
    datawrapper_table(course_records_summary)

with tab2:
    st.markdown("**Course Records (Net)**")
    datawrapper_table(net_course_records, css_classes='full-width table-left-align')

    st.divider()

    st.markdown("**Net Records Summary by Player**")
    datawrapper_table(net_course_records_summary)

with tab3:
    datawrapper_table(course_summary, css_classes='full-width')

with tab4:
    datawrapper_table(mean_course_data, css_classes='full-width')

with tab5:
    datawrapper_table(min_course_data, css_classes='full-width')

with tab6:
    datawrapper_table(max_course_data, css_classes='full-width')

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)
