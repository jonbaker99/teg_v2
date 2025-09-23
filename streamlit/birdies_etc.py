# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Import data loading functions from main utils
from utils import score_type_stats, max_scoretype_per_round, load_datawrapper_css

# Import scoring achievements helper functions
from helpers.scoring_achievements_processing import (
    get_scoring_achievement_fields,
    create_achievement_tab_labels,
    prepare_achievement_table_data,
    create_section_title
)



# === CONFIGURATION ===
st.title("Eagles, Birdies etc.")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load career scoring achievement statistics
# Purpose: Provides comprehensive career totals for eagles, birdies, pars, and poor scores
# Includes both achievement counts and frequency ratios (holes per achievement)
scoring_stats = score_type_stats()

# Load single-round achievement maximums
# Purpose: Shows best single-round performances for comparison
max_by_round = max_scoretype_per_round()



# === USER INTERFACE ===
# get_scoring_achievement_fields() - Defines achievement categories and their metrics
chart_fields_all = get_scoring_achievement_fields()

# Create single-level tab structure
tab_labels = ["Eagles", "Birdies", "Pars", "Triple Bogey+", "Most in Round"]
tabs = st.tabs(tab_labels)

# Map score type tabs to chart_fields
score_type_mapping = {
    "Eagles": chart_fields_all[0],
    "Birdies": chart_fields_all[1],
    "Pars": chart_fields_all[2],
    "Triple Bogey+": chart_fields_all[3]
}

# Display content in each tab
for i, tab in enumerate(tabs):
    with tab:
        if i < 4:  # Score type tabs (Eagles, Birdies, Pars or Better, Triple Bogey+)
            tab_name = tab_labels[i]

            # Get the chart fields for this score type
            selected_chart_fields = score_type_mapping[tab_name]

            # create_section_title() - Creates clean section title from field names
            section_title = create_section_title(selected_chart_fields)
            st.markdown(f"**Career {section_title}**")

            # prepare_achievement_table_data() - Formats table with proper sorting and display formatting
            formatted_table = prepare_achievement_table_data(scoring_stats, selected_chart_fields)
            st.write(
                formatted_table.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )

        else:  # "Most in Round" tab
            # Single-round maximums tab
            # Reorder columns: Eagles, Birdies, Pars, TBPs
            # Also rename 'Pars_or_Better' to 'Pars'
            reordered_table = max_by_round[['Player', 'Eagles', 'Birdies', 'Pars_or_Better', 'TBPs']].copy()
            reordered_table = reordered_table.rename(columns={'Pars_or_Better': 'Pars'})

            st.write(
                reordered_table.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
