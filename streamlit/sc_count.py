# === IMPORTS ===
import streamlit as st
import pandas as pd
import plotly.express as px

# Import data loading functions from main utils
from utils import load_all_data, load_datawrapper_css, datawrapper_table

# Import score count analysis helper functions
from helpers.score_count_processing import (
    get_filtering_options,
    apply_teg_and_par_filters,
    count_scores_by_player,
    create_percentage_distribution_chart,
    prepare_score_count_display,
    prepare_chart_data_with_special_handling
)


# === CONFIGURATION ===
st.title('Count of score by player')

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load all TEG data including incomplete tournaments for current analysis
# Purpose: Score distribution analysis benefits from complete current data for pattern recognition
all_data = load_all_data(exclude_incomplete_tegs=False)

# get_filtering_options() - Creates dropdown options for TEG and par filtering
tegnum_options, par_options = get_filtering_options(all_data)


# === USER INTERFACE ===
# Filtering controls
selected_tegnum = st.selectbox('Filter by TEG (optional)', tegnum_options, index=0)
selected_par = st.selectbox('Filter by par (optional)', par_options, index=0)

# apply_teg_and_par_filters() - Applies user-selected filters and creates descriptive labels
filtered_data, teg_desc, par_desc = apply_teg_and_par_filters(all_data, selected_tegnum, selected_par)

# count_scores_by_player() - Creates score distribution matrices for both score types
count_gvp = count_scores_by_player(filtered_data, 'GrossVP')
count_sc = count_scores_by_player(filtered_data, 'Sc')

# Display results in tabs
tab1, tab2 = st.tabs(["Scores", "Scores vs Par"])

with tab1:
    st.markdown('### Count of gross score by player')
    st.caption(f'{teg_desc} | {par_desc}')
    
    # prepare_score_count_display() - Formats score count data for table display
    score_display_data = prepare_score_count_display(count_sc, 'Sc', 'Score')
    datawrapper_table(score_display_data, css_classes='full-width')
    
    # create_percentage_distribution_chart() - Creates percentage distribution chart
    score_chart = create_percentage_distribution_chart(score_display_data, teg_desc, par_desc)
    st.plotly_chart(score_chart)

with tab2:
    st.markdown('### Count of Gross vs Par by player')
    st.caption(f'{teg_desc} | {par_desc}')
    
    # prepare_score_count_display() - Formats vs-par data for table display
    vspar_display_data = prepare_score_count_display(count_gvp, 'GrossVP', 'vs Par')
    datawrapper_table(vspar_display_data, css_classes='full-width')
    
    # prepare_chart_data_with_special_handling() - Handles "=" to 0 conversion for charting
    vspar_chart_data = prepare_chart_data_with_special_handling(vspar_display_data, 'GrossVP')
    
    # create_percentage_distribution_chart() - Creates percentage distribution chart
    vspar_chart = create_percentage_distribution_chart(vspar_chart_data, teg_desc, par_desc)
    st.plotly_chart(vspar_chart)