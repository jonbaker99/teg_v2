# === IMPORTS ===
import streamlit as st
import pandas as pd
import numpy as np

# Import data loading functions from main utils
from utils import load_datawrapper_css, load_all_data, read_file, STREAKS_PARQUET

# Import streak analysis helper functions
from helpers.streak_analysis_processing import (
    prepare_good_streaks_data,
    prepare_bad_streaks_data,
    prepare_current_good_streaks_data,
    prepare_current_bad_streaks_data,
    calculate_window_streaks,
    prepare_record_best_streaks_data,
    prepare_record_worst_streaks_data
)


# === CONFIGURATION ===
# === PAGE LAYOUT CONFIGURATION ===
from utils import get_page_layout
layout = get_page_layout(__file__)
st.set_page_config(layout=layout)
st.title("Streaks")

# Load CSS styling for consistent table appearance
load_datawrapper_css()


# === DATA LOADING ===
# Load streak data
# Purpose: TEG 50 is excluded for accurate streak analysis as it's a special case
all_data = load_all_data(exclude_teg_50=True)

# Cache all streak table calculations for performance
@st.cache_data
def get_all_streak_tables(all_data):
    """
    Cache all streak table calculations together for instant radio button switching.
    Only recalculates when underlying data changes.
    All tables are sorted alphabetically by Player name.
    """
    # Get all streak tables
    tables = {
        'good_max': prepare_good_streaks_data(all_data),
        'bad_max': prepare_bad_streaks_data(all_data),
        'good_current': prepare_current_good_streaks_data(all_data),
        'bad_current': prepare_current_bad_streaks_data(all_data)
    }

    # Sort all tables alphabetically by Player
    for key, table in tables.items():
        if 'Player' in table.columns:
            tables[key] = table.sort_values('Player').reset_index(drop=True)

    return tables

# Calculate all streak tables once
streak_tables = get_all_streak_tables(all_data)


# === USER INTERFACE ===
# Create main tab structure for streaks
tab_labels = ["Streaks by Player", "Record Streaks", "Streak detail"]
tabs = st.tabs(tab_labels)

# Display streak statistics in tabs
for i, tab in enumerate(tabs):
    with tab:
        if i == 0:
            # Streaks by Player tab - good vs bad, max vs current
            st.write("**Select streak type:**")

            streak_category = st.segmented_control(
                "Good / Bad",
                ["Good", "Bad"],
                default="Good",
                key="streak_category",
                label_visibility="collapsed"
            )

            streak_type = st.segmented_control(
                "Max / Current",
                ["Max", "Current"],
                default="Max",
                key="streak_type",
                label_visibility="collapsed"
            )

            # Select appropriate table based on controls
            if streak_category == "Good":
                if streak_type == "Max":
                    streaks_summary = streak_tables['good_max']
                else:
                    streaks_summary = streak_tables['good_current']
            else:  # Bad
                if streak_type == "Max":
                    streaks_summary = streak_tables['bad_max']
                else:
                    streaks_summary = streak_tables['bad_current']

            # Display streaks summary table
            st.write(
                streaks_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
            st.caption("*: current streak is maximum streak")

        elif i == 1:
            # Record Streaks tab - All-time records for each streak type
            st.write("All-time record streaks for each streak type across all players and tournaments.")

            # Create subtabs for Best and Worst streaks
            record_tabs = st.tabs(["Best Streaks", "Worst Streaks"])

            with record_tabs[0]:
                # Best (good) streaks records
                best_streaks = prepare_record_best_streaks_data(all_data)
                st.write(
                    best_streaks.to_html(
                        index=False,
                        justify='left',
                        classes='datawrapper-table table-left-align centre-2nd'
                    ),
                    unsafe_allow_html=True
                )
                st.caption("*: current streak is record streak")

            with record_tabs[1]:
                # Worst (bad) streaks records
                worst_streaks = prepare_record_worst_streaks_data(all_data)
                st.write(
                    worst_streaks.to_html(
                        index=False,
                        justify='left',
                        classes='datawrapper-table table-left-align centre-2nd'
                    ),
                    unsafe_allow_html=True
                )
                st.caption("*: current streak is record streak")

        elif i == 2:
            # Streak detail tab - TEG/Round level analysis
            st.write("Select filters to analyze streaks within a specific window (TEG, Round, or Player).")
            st.write("Leave filters blank to see all data.")

            # Load and prepare data for window analysis
            streaks_df = read_file(STREAKS_PARQUET)
            df = streaks_df.merge(
                all_data[['HoleID', 'TEG', 'TEGNum', 'Round', 'Pl', 'Player']],
                on=['HoleID', 'Pl']
            )
            df = df.sort_values(['Pl', 'TEGNum', 'Round', 'Career Count'])

            # Create filter dropdowns
            col1, col2, col3 = st.columns(3)

            with col1:
                # Get unique TEGs sorted by TEGNum
                teg_options = ['All'] + sorted(df['TEG'].unique(), key=lambda x: int(x.split()[1]))
                selected_teg = st.selectbox('TEG', teg_options)

            with col2:
                # Get unique rounds sorted numerically
                round_options = ['All'] + sorted(df['Round'].unique())
                selected_round = st.selectbox('Round', round_options)

            with col3:
                # Get unique players sorted by Pl
                player_options = ['All'] + sorted(df['Pl'].unique())
                selected_player = st.selectbox('Player', player_options)

            # Apply filters
            filtered_df = df.copy()

            if selected_teg != 'All':
                filtered_df = filtered_df[filtered_df['TEG'] == selected_teg]

            if selected_round != 'All':
                filtered_df = filtered_df[filtered_df['Round'] == selected_round]

            if selected_player != 'All':
                filtered_df = filtered_df[filtered_df['Pl'] == selected_player]

            # Display filter summary
            filter_summary = []
            if selected_teg != 'All':
                filter_summary.append(f"TEG: {selected_teg}")
            if selected_round != 'All':
                filter_summary.append(f"Round: {selected_round}")
            if selected_player != 'All':
                player_name = filtered_df['Player'].iloc[0] if len(filtered_df) > 0 else selected_player
                filter_summary.append(f"Player: {player_name}")

            if filter_summary:
                st.write(f"**Showing streaks for:** {', '.join(filter_summary)}")
            else:
                st.write("**Showing streaks for:** All data (career-level)")

            st.write(f"*Analyzing {len(filtered_df)} holes*")

            # Calculate and display results
            if len(filtered_df) > 0:
                with st.spinner("Calculating adjusted streaks..."):
                    results_df = calculate_window_streaks(filtered_df)

                if len(results_df) > 0:
                    # Display results table
                    st.write(
                        results_df.to_html(
                            index=False,
                            justify='left',
                            classes='datawrapper-table table-left-align centre-3rd'
                        ),
                        unsafe_allow_html=True
                    )
                else:
                    st.info("No streak data available for the selected filters.")
            else:
                st.warning("No data matches the selected filters.")

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
                