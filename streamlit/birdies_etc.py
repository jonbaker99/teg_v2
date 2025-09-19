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

# Create consolidated tab structure
tab_labels = ["Number of Eagles etc", "Most in round"]
tabs = st.tabs(tab_labels)

# Display achievement statistics in tabs
for i, tab in enumerate(tabs):
    with tab:
        if i == 0:
            
            # Career achievements tab with sub-tabs for each score type
            eagles_tab, birdies_tab, pars_tab, tbp_tab = st.tabs(["Eagles", "Birdies", "Pars or Better", "Triple Bogey+"])

            # Map score type tabs to chart_fields
            score_type_mapping = {
                "Eagles": chart_fields_all[0],
                "Birdies": chart_fields_all[1],
                "Pars or Better": chart_fields_all[2],
                "Triple Bogey+": chart_fields_all[3]
            }

            # Create content for each sub-tab
            for tab_name, tab in [("Eagles", eagles_tab), ("Birdies", birdies_tab), ("Pars or Better", pars_tab), ("Triple Bogey+", tbp_tab)]:
                with tab:
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

        elif i == 1:
            # Single-round maximums tab
            st.write(
                max_by_round.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
