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
    calculate_window_streaks
)


# === CONFIGURATION ===
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
# Radio button to choose between max and current streaks
streak_type = st.radio(
    "Select streak type:",
    ["Max", "Current"],
    horizontal=True
)

# Create main tab structure for streaks
tab_labels = ["Good Streaks", "Bad Streaks", "Streak detail"]
tabs = st.tabs(tab_labels)

# Display streak statistics in tabs
for i, tab in enumerate(tabs):
    with tab:
        if i == 0:
            # Good streaks tab - select from cached tables
            if streak_type == "Max":
                good_streaks_summary = streak_tables['good_max']
            else:
                good_streaks_summary = streak_tables['good_current']

            # Display good streaks summary table
            st.write(
                good_streaks_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
            st.caption("*: current streak is maximum streak")

        elif i == 1:
            # Bad streaks tab - select from cached tables
            if streak_type == "Max":
                bad_streaks_summary = streak_tables['bad_max']
            else:
                bad_streaks_summary = streak_tables['bad_current']

            # Display bad streaks summary table
            st.write(
                bad_streaks_summary.to_html(
                    index=False,
                    justify='left',
                    classes='datawrapper-table'
                ),
                unsafe_allow_html=True
            )
            st.caption("*: current streak is maximum streak")

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
                            classes='datawrapper-table'
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
                