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
# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)
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
# Score type selector (affects all tabs)
score_field_option = st.segmented_control(
    'Score type',
    ['Scores', 'Scores vs Par', 'Stableford Points'],
    default='Stableford Points'
)

# Map display name to field name
field_mapping = {
    'Scores': 'Sc',
    'Scores vs Par': 'GrossVP',
    'Stableford Points': 'Stableford'
}
selected_field = field_mapping[score_field_option]
display_name_mapping = {
    'Sc': 'Score',
    'GrossVP': 'vs Par',
    'Stableford': 'Stableford'
}
selected_display_name = display_name_mapping[selected_field]

# Filtering controls
player_options = ['All players'] + sorted(all_data['Pl'].unique().tolist())
selected_player = st.selectbox('Filter by player (optional)', player_options, index=0)
selected_tegnum = st.selectbox('Filter by TEG (optional)', tegnum_options, index=0)
selected_par = st.segmented_control('Filter by par (optional)', par_options, default=par_options[0])

# Display mode control
display_mode = st.radio(
    "Display mode:",
    ["Count", "Percentage"],
    index=1,  # Default to Percentage
    horizontal=True
)

# Apply filters
# apply_teg_and_par_filters() - Applies user-selected filters and creates descriptive labels
filtered_data, teg_desc, par_desc = apply_teg_and_par_filters(all_data, selected_tegnum, selected_par)

# Apply player filter if selected
if selected_player != 'All players':
    filtered_data = filtered_data[filtered_data['Pl'] == selected_player]
    player_desc = selected_player
else:
    player_desc = 'All players'

# count_scores_by_player() - Creates score distribution matrix for selected score type
count_data = count_scores_by_player(filtered_data, selected_field)

# Display results in tabs
tab1, tab2 = st.tabs(["By Player", "By TEG"])

with tab1:
    # By Player tab - shows distribution of selected score type across players
    if display_mode == "Count":
        st.markdown(f'### Count of {score_field_option} by player')
        display_data = count_data
        is_percentage_mode = False
    else:
        st.markdown(f'### Percentage of {score_field_option} by player')
        display_data = convert_counts_to_percentages(count_data)
        is_percentage_mode = True

    st.caption(f'{player_desc} | {teg_desc} | {par_desc}')

    # prepare_score_count_display() - Formats score count data for table display
    table_display_data = prepare_score_count_display(display_data, selected_field, selected_display_name, is_percentage_mode)
    datawrapper_table(table_display_data, css_classes='full-width table-right-align')

    # For charts, always use numeric data (not formatted)
    chart_data = prepare_score_count_display(count_data, selected_field, selected_display_name, False)

    # Handle special case for vs par charting
    if selected_field == 'GrossVP':
        chart_data = prepare_chart_data_with_special_handling(chart_data, 'GrossVP')

    # create_percentage_distribution_chart() - Creates percentage distribution chart
    chart = create_percentage_distribution_chart(chart_data, teg_desc, par_desc)
    st.plotly_chart(chart)

with tab2:
    # By TEG tab - shows distribution of selected score type across TEGs
    if display_mode == "Count":
        st.markdown(f'### Count of {score_field_option} by TEG')
    else:
        st.markdown(f'### Percentage of {score_field_option} by TEG')

    # Use filtered data (respects par filter but not player filter for this view)
    teg_filtered_data, _, _ = apply_teg_and_par_filters(all_data, selected_tegnum, selected_par)

    # Apply player filter if selected
    if selected_player != 'All players':
        teg_filtered_data = teg_filtered_data[teg_filtered_data['Pl'] == selected_player]

    # Create crosstab of TEGNum vs selected score field
    if display_mode == "Count":
        crosstab = pd.crosstab(teg_filtered_data['TEGNum'], teg_filtered_data[selected_field])
    else:
        crosstab = pd.crosstab(teg_filtered_data['TEGNum'], teg_filtered_data[selected_field], normalize='index') * 100
        crosstab = crosstab.round(1)

    # Prepare for display
    display_data_teg = crosstab.reset_index()
    display_data_teg.columns.name = None

    # Format column headers for GrossVP
    if selected_field == 'GrossVP':
        from utils import format_vs_par
        new_cols = {col: format_vs_par(col) if col != 'TEGNum' else col for col in display_data_teg.columns}
        display_data_teg = display_data_teg.rename(columns=new_cols)

    # Format values based on display mode
    if display_mode == "Percentage":
        for col in display_data_teg.columns:
            if col != 'TEGNum':
                display_data_teg[col] = display_data_teg[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0.0%")
    else:
        # Convert counts to integers for cleaner display
        for col in display_data_teg.columns:
            if col != 'TEGNum':
                display_data_teg[col] = display_data_teg[col].apply(lambda x: int(x) if pd.notna(x) else 0)

    # Rename TEGNum column
    display_data_teg = display_data_teg.rename(columns={'TEGNum': 'TEG'})

    st.caption(f'{player_desc} | {par_desc}')
    datawrapper_table(display_data_teg, css_classes='full-width table-right-align')

# === NAVIGATION LINKS ===
from utils import add_custom_navigation_links
st.markdown("")
links_html = add_custom_navigation_links(
    __file__, layout="horizontal", separator=" | ", render=False
)
st.markdown(
    f'<div class="nav-list"><span class="nav-label">Related links:</span> {links_html}</div>',
    unsafe_allow_html=True
)