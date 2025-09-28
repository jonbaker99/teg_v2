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
    prepare_chart_data_with_special_handling,
    convert_counts_to_percentages,
    create_stacked_bar_chart,
    format_percentage_for_display
)


# === CONFIGURATION ===
st.title('Scoring distribution')

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

# Display mode control
display_mode = st.radio(
    "Display mode:",
    ["Count", "Percentage"],
    index=1,  # Default to Percentage
    horizontal=True
)

# apply_teg_and_par_filters() - Applies user-selected filters and creates descriptive labels
filtered_data, teg_desc, par_desc = apply_teg_and_par_filters(all_data, selected_tegnum, selected_par)

# count_scores_by_player() - Creates score distribution matrices for both score types
count_gvp = count_scores_by_player(filtered_data, 'GrossVP')
count_sc = count_scores_by_player(filtered_data, 'Sc')

# Display results in tabs
tab1, tab2 = st.tabs(["Scores", "Scores vs Par"])

with tab1:
    # Dynamic title and data based on display mode
    if display_mode == "Count":
        st.markdown('### Count of gross score by player')
        display_data = count_sc
        is_percentage_mode = False
    else:
        st.markdown('### Percentage of gross score by player')
        display_data = convert_counts_to_percentages(count_sc)
        is_percentage_mode = True

    st.caption(f'{teg_desc} | {par_desc}')

    # prepare_score_count_display() - Formats score count data for table display
    score_display_data = prepare_score_count_display(display_data, 'Sc', 'Score', is_percentage_mode)
    datawrapper_table(score_display_data, css_classes='full-width table-right-align')

    # For charts, always use numeric data (not formatted)
    chart_data = prepare_score_count_display(count_sc, 'Sc', 'Score', False)  # Always use counts for charts

    # create_percentage_distribution_chart() - Creates percentage distribution chart
    score_chart = create_percentage_distribution_chart(chart_data, teg_desc, par_desc)
    st.plotly_chart(score_chart)

    # Add stacked bar chart
    stacked_chart = create_stacked_bar_chart(count_sc, teg_desc, par_desc, 'Sc')
    st.plotly_chart(stacked_chart)

with tab2:
    # Dynamic title and data based on display mode
    if display_mode == "Count":
        st.markdown('### Count of Gross vs Par by player')
        display_data_gvp = count_gvp
        is_percentage_mode_gvp = False
    else:
        st.markdown('### Percentage of Gross vs Par by player')
        display_data_gvp = convert_counts_to_percentages(count_gvp)
        is_percentage_mode_gvp = True

    st.caption(f'{teg_desc} | {par_desc}')

    # prepare_score_count_display() - Formats vs-par data for table display
    vspar_display_data = prepare_score_count_display(display_data_gvp, 'GrossVP', 'vs Par', is_percentage_mode_gvp)
    datawrapper_table(vspar_display_data, css_classes='full-width table-right-align')

    # For charts, always use numeric data (not formatted)
    vspar_chart_raw = prepare_score_count_display(count_gvp, 'GrossVP', 'vs Par', False)  # Always use counts for charts

    # prepare_chart_data_with_special_handling() - Handles "=" to 0 conversion for charting
    vspar_chart_data = prepare_chart_data_with_special_handling(vspar_chart_raw, 'GrossVP')

    # create_percentage_distribution_chart() - Creates percentage distribution chart
    vspar_chart = create_percentage_distribution_chart(vspar_chart_data, teg_desc, par_desc)
    st.plotly_chart(vspar_chart)

    # Add stacked bar chart
    stacked_chart_gvp = create_stacked_bar_chart(count_gvp, teg_desc, par_desc, 'GrossVP')
    st.plotly_chart(stacked_chart_gvp)

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
add_custom_navigation_links(__file__, layout="horizontal", separator=" | ")