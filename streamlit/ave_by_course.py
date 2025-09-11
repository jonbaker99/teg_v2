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

# Display results in tabs
tab1, tab2, tab3, tab4 = st.tabs(["Summary by course", "Averages", "Bests", "Worsts"])

with tab1:
    datawrapper_table(course_summary, css_classes='full-width')

with tab2:
    datawrapper_table(mean_course_data, css_classes='full-width')

with tab3:
    datawrapper_table(min_course_data, css_classes='full-width')

with tab4:
    datawrapper_table(max_course_data, css_classes='full-width')
